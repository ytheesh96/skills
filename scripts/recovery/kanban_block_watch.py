#!/usr/bin/env python3
"""kanban_block_watch.py - read-only detector for blocked Kanban tasks.

Stdlib only. No hermes CLI, no LLM. Watches every board under
HERMES_HOME/kanban/boards/<slug>/kanban.db for:

  1. task_events of blocking kinds (blocked/gave_up/timed_out/crashed/
     spawn_auto_blocked) whose id is past the per-board cursor, where the
     owning task's tenant matches a configured prefix; AND
  2. tasks currently in status='blocked' whose tenant matches, that were not
     present in the baseline fingerprint (catches a block set without a
     corresponding event, e.g. a direct status write).

When a NEW actionable block appears it appends exactly ONE line beginning with
"KANBAN_BLOCKED_WAKE" to wake.log and ONE JSON record to alerts.jsonl.

The FIRST run on a board baselines: records the event cursor and the existing
blocked fingerprint and appends NOTHING (it never pages historical blocks such
as t_b0a472ca).

State is kept per board (scope = board slug) under
HERMES_HOME/state/kanban-block-watch/<scope>.json as:
    {"last_seen_event_id": int, "active_blocked_fingerprints": [task_ids]}

The board databases are opened read-only at the SQL level (SELECT only) and
never mutated.
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

# --- Configuration -----------------------------------------------------------

# Tenant prefixes that put a task "in scope". Anything matching is watched.
TENANT_PREFIXES = ["wayfinder-"]

# task_events.kind values that indicate a task became (or stayed) blocked.
BLOCK_KINDS = (
    "blocked",
    "gave_up",
    "timed_out",
    "crashed",
    "spawn_auto_blocked",
)

# State location. HERMES_HOME is overridable (used by the test harness); it
# defaults to Path.home() / ".hermes" (the user's Hermes home).
HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
BOARDS_DIR = HERMES_HOME / "kanban" / "boards"
STATE_DIR = HERMES_HOME / "state" / "kanban-block-watch"
WAKE_LOG = STATE_DIR / "wake.log"
ALERTS_FILE = STATE_DIR / "alerts.jsonl"


# --- Discovery ---------------------------------------------------------------

def boards():
    """Yield (slug, db_path) for each board directory containing kanban.db."""
    if not BOARDS_DIR.is_dir():
        return
    for child in sorted(BOARDS_DIR.iterdir()):
        if not child.is_dir():
            continue
        db = child / "kanban.db"
        if db.is_file():
            yield child.name, db


def tenant_match(tenant):
    if not tenant:
        return False
    return any(tenant.startswith(p) for p in TENANT_PREFIXES)


# --- State -------------------------------------------------------------------

def state_path(scope):
    return STATE_DIR / f"{scope}.json"


def load_state(scope):
    path = state_path(scope)
    if path.is_file():
        try:
            with path.open() as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                return data
        except (ValueError, OSError):
            pass
    return {"last_seen_event_id": 0, "active_blocked_fingerprints": []}


def save_state(scope, state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = state_path(scope)
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w") as fh:
        json.dump(state, fh, indent=2, sort_keys=True)
    tmp.replace(path)


# --- Queries -----------------------------------------------------------------

def query_board(db_path):
    """Read-only snapshot of one board.

    Returns (max_event_id, blocked_rows, block_events) where:
      max_event_id : highest task_events.id (0 if none)
      blocked_rows : list of {id, tenant, title} for status='blocked' rows
                     whose tenant matches a prefix
      block_events : list of {event_id, task_id, kind, tenant} for every
                     block-kind event whose tenant matches a prefix
    """
    # Plain connect (no read-only URI, no cache=shared). SELECT-only, so the
    # board is never mutated. Short timeout avoids hanging on a busy writer.
    conn = sqlite3.connect(str(db_path), timeout=2.0)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        try:
            cur.execute("SELECT 1 FROM tasks LIMIT 1")
        except sqlite3.Error:
            # Uninitialized / empty board (e.g. a 0-byte kanban.db with no
            # tables). Treat as a board with no tasks and no events.
            return 0, [], []

        cur.execute("SELECT MAX(id) AS m FROM task_events")
        row = cur.fetchone()
        max_event_id = row["m"] if row and row["m"] is not None else 0

        cur.execute("SELECT id, tenant, title FROM tasks WHERE status = 'blocked'")
        blocked_rows = [
            {"id": r["id"], "tenant": r["tenant"], "title": r["title"]}
            for r in cur.fetchall()
            if tenant_match(r["tenant"])
        ]

        placeholders = ",".join("?" for _ in BLOCK_KINDS)
        cur.execute(
            f"""
            SELECT e.id AS event_id, e.task_id AS task_id, e.kind AS kind,
                   t.tenant AS tenant
            FROM task_events e
            LEFT JOIN tasks t ON e.task_id = t.id
            WHERE e.kind IN ({placeholders})
            """,
            list(BLOCK_KINDS),
        )
        block_events = [
            {
                "event_id": r["event_id"],
                "task_id": r["task_id"],
                "kind": r["kind"],
                "tenant": r["tenant"],
            }
            for r in cur.fetchall()
            if tenant_match(r["tenant"])
        ]
        return max_event_id, blocked_rows, block_events
    finally:
        conn.close()


# --- Processing --------------------------------------------------------------

def process_board(slug, db_path, is_baseline):
    """Process one board. Returns a summary dict. May raise sqlite3.Error."""
    max_event_id, blocked_rows, block_events = query_board(db_path)
    state = load_state(slug)
    cursor = state.get("last_seen_event_id", 0)
    baseline_blocked = set(state.get("active_blocked_fingerprints", []))

    current_blocked_ids = {r["id"] for r in blocked_rows}
    current_blocked_map = {r["id"]: r for r in blocked_rows}

    # Block-kind events that arrived after the cursor.
    new_event_task_ids = {
        e["task_id"] for e in block_events if e["event_id"] > cursor
    }
    # Blocked rows present now that were not in the baseline fingerprint.
    fingerprint_new = current_blocked_ids - baseline_blocked

    candidates = new_event_task_ids | fingerprint_new
    # Actionable only if the task is currently blocked.
    newly_blocked = candidates & current_blocked_ids

    woke = False
    if not is_baseline and newly_blocked:
        woke = True
        ids_sorted = sorted(newly_blocked)
        ts = int(time.time())
        compact = " ".join(
            f"{tid}({(current_blocked_map.get(tid, {}).get('title') or '')[:40]})"
            for tid in ids_sorted
        )
        line = f"KANBAN_BLOCKED_WAKE {ts} board={slug} {compact}"
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with WAKE_LOG.open("a") as fh:
            fh.write(line + "\n")
        alert = {
            "ts": ts,
            "board": slug,
            "tasks": [
                {
                    "id": tid,
                    "title": current_blocked_map.get(tid, {}).get("title"),
                }
                for tid in ids_sorted
            ],
        }
        with ALERTS_FILE.open("a") as fh:
            fh.write(json.dumps(alert) + "\n")

    save_state(
        slug,
        {
            "last_seen_event_id": max_event_id,
            "active_blocked_fingerprints": sorted(current_blocked_ids),
        },
    )

    return {
        "slug": slug,
        "max_event_id": max_event_id,
        "cursor": cursor,
        "blocked_now": len(current_blocked_ids),
        "pending_events": len([e for e in block_events if e["event_id"] > cursor]),
        "woke": woke,
        "baseline": is_baseline,
    }


# --- Commands ----------------------------------------------------------------

def cmd_status():
    print(f"HERMES_HOME      : {HERMES_HOME}")
    print(f"TENANT_PREFIXES  : {', '.join(TENANT_PREFIXES)}")
    print(f"BOARDS_DIR       : {BOARDS_DIR}")
    print(f"STATE_DIR        : {STATE_DIR}")
    print("Boards:")
    found = False
    for slug, db_path in boards():
        found = True
        try:
            max_event_id, blocked_rows, block_events = query_board(db_path)
        except sqlite3.Error as exc:
            if "no such table" in str(exc):
                # Uninitialized / empty board (e.g. a 0-byte kanban.db).
                print(f"  - {slug}: (empty / uninitialized)")
            else:
                print(f"  - {slug}: ERROR {exc}")
            continue
        state = load_state(slug)
        cursor = state.get("last_seen_event_id", 0)
        pending = len([e for e in block_events if e["event_id"] > cursor])
        print(
            f"  - {slug}: cursor={cursor} max_event={max_event_id} "
            f"pending_events={pending} blocked_now={len(blocked_rows)}"
        )
    if not found:
        print("  (no boards found)")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Watch Kanban boards for newly blocked tasks."
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print board/state summary and exit without waking.",
    )
    parser.add_argument(
        "--board",
        default=None,
        help="Limit processing to a single board slug.",
    )
    args = parser.parse_args(argv)

    if args.status:
        cmd_status()
        return 0

    for slug, db_path in boards():
        if args.board and slug != args.board:
            continue
        try:
            is_baseline = not state_path(slug).is_file()
            process_board(slug, db_path, is_baseline)
        except sqlite3.Error as exc:
            print(f"board {slug}: sqlite error {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
