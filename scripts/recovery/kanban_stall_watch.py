#!/usr/bin/env python3
"""Cross-board Kanban stall watchdog.

Detects the failure Vaitheesh hits repeatedly: a board where NOTHING is
actively being worked on, yet work remains. This happens when a graph blocks
(needs_input / review REQUEST-CHANGES) and the human is never told, so
dependent successors sit in `todo` forever behind the blocked parent.

Designed for Hermes cron with no_agent=True:
  - EMPTY stdout  => silent, nothing is wrong (nothing is sent to the user)
  - non-empty     => delivered verbatim as the alert message
  - non-zero exit => cron sends an error alert (so a broken watchdog is loud)

It NEVER mutates the board. Read-only: it lists tasks and reports.

Three detectors, all read-only:

1. Board stall (preserved): no task `running` AND work remains pending.
   Grace 15m, re-alert every 6h, per board.

2. Stale running (added): a task still marked `running` whose worker is
   evidently dead or wedged — heartbeat >15m old OR claim expired OR worker
   PID no longer alive. Re-alert every 6h, per task, in a SEPARATE state
   namespace so it never collides with the board-stall bookkeeping.

3. Aging triage (added): a board with triage cards created >10m ago, which
   suggests the auto-decomposer is down. Re-alert every 6h, per board, in
   its own state namespace.

Staleness / triage signals live in SQLite columns (claim_expires,
worker_pid, last_heartbeat_at, created_at) that the CLI JSON does NOT
serialize, so detectors 2 and 3 read each board's kanban.db directly. This
also sidesteps the gotcha where `hermes kanban --board <slug>` ignores
--board whenever HERMES_KANBAN_DB is set in the environment.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
HERMES_HOME = Path(os.environ.get("HERMES_HOME", HOME / ".hermes")).expanduser()
STATE_DIR = HERMES_HOME / "state" / "kanban-stall-watch"
STATE_PATH = STATE_DIR / "state.json"

HERMES_BIN = os.environ.get("HERMES_BIN") or str(HERMES_HOME / "hermes-agent" / "venv" / "bin" / "hermes")
if not Path(HERMES_BIN).exists():
    HERMES_BIN = "hermes"

# Re-alert cadence per finding while the SAME condition persists (seconds).
REPEAT_SECONDS = 6 * 3600
# A board must look stalled for at least this long before alerting, so we do
# not fire during the gap between one worker exiting and the next being claimed.
GRACE_SECONDS = 15 * 60

# Addition 1: a `running` task whose most recent heartbeat is older than this
# is treated as stale (worker wedged or silently dead).
STALE_RUNNING_SECONDS = 15 * 60
# Addition 2: triage cards older than this are "aging" (decomposer likely down).
AGING_TRIAGE_SECONDS = 10 * 60

ACTIVE = {"running"}
PENDING = {"blocked", "ready", "todo", "review", "triage", "scheduled"}

# Separate state namespaces so the new detectors never disturb the
# board-stall bookkeeping (which stores state keyed by board slug).
NS_STALE_RUNNING = "__stale_running__"
NS_AGING_TRIAGE = "__aging_triage__"

# Wake bridge: when an alert fires, ALSO append a compact summary to wake.log
# so the foreground-owned `tail -F wake.log` bridge (watch_patterns=
# ["KANBAN_BLOCKED_WAKE"]) can deliver it to the desktop/TUI. Best-effort:
# a failed write must never crash the watchdog or change the stdout contract.
WAKE_DIR = HERMES_HOME / "state" / "kanban-block-watch"
WAKE_PATH = WAKE_DIR / "wake.log"
WAKE_TOKEN = "KANBAN_BLOCKED_WAKE"


def run(args: list[str], timeout: int = 60) -> tuple[int, str]:
    try:
        p = subprocess.run(
            [HERMES_BIN, *args],
            capture_output=True, text=True, timeout=timeout,
        )
        return p.returncode, (p.stdout or "")
    except subprocess.TimeoutExpired:
        return 124, ""
    except Exception:
        return 1, ""


def list_boards() -> list[str]:
    code, out = run(["kanban", "boards"])
    if code != 0:
        return []
    boards: list[str] = []
    for line in out.splitlines():
        s = line.strip()
        if not s or s.upper().startswith("SLUG") or s.startswith("Current board"):
            continue
        if s.startswith("Switch boards"):
            continue
        s = s.lstrip("●").strip()
        parts = s.split()
        if parts:
            slug = parts[0]
            if slug and not slug.startswith("-"):
                boards.append(slug)
    return boards


def board_tasks(board: str) -> list[dict]:
    code, out = run(["kanban", "--board", board, "list", "--json"])
    if code != 0 or not out.strip():
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        for key in ("tasks", "items", "rows"):
            if isinstance(data.get(key), list):
                return data[key]
        return []
    return data if isinstance(data, list) else []


# --------------------------------------------------------------------------
# SQLite-backed helpers (used by the stale-running and aging-triage detectors)
# --------------------------------------------------------------------------

def boards_root() -> Path:
    return HERMES_HOME / "kanban" / "boards"


def board_db_path(slug: str) -> Path | None:
    """Resolve a board slug to its kanban.db, mirroring Hermes' own path rules.

    - `default` may live at <root>/kanban/boards/default/kanban.db (metadata
      dir) or, for pre-boards installs, <root>/kanban.db.
    - Every other board lives at <root>/kanban/boards/<slug>/kanban.db.
    Returns None when no DB file exists (e.g. a board with no tasks yet).
    """
    root = boards_root()
    if slug == "default":
        for cand in (root / "default" / "kanban.db", HERMES_HOME / "kanban.db"):
            if cand.exists():
                return cand
        return None
    p = root / slug / "kanban.db"
    return p if p.exists() else None


def _query(db_path: Path, sql: str, params: tuple = ()) -> list[dict]:
    """Read-only single-shot query. Returns [] on any failure (never raises)."""
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            con.row_factory = sqlite3.Row
            rows = con.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            con.close()
    except Exception:
        return []


def pid_alive(pid) -> bool | None:
    """Return True if the PID exists on this host, False if it is gone.

    None means "cannot determine" (no pid, or an OS error we don't trust) —
    callers should not flag a task as stale on a None alone.
    """
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return None
    if pid <= 0:
        return None
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists; we just lack signal permission. Treat as alive.
        return True
    except Exception:
        return None


def detect_stale_running(now: int, slugs: list[str], prev_ns: dict) -> tuple[list[str], dict]:
    """Addition 1: per running task, flag if heartbeats stalled / claim
    expired / worker PID dead. Returns (report_lines, updated_namespace)."""
    report: list[str] = []
    ns: dict = {}
    for slug in slugs:
        db = board_db_path(slug)
        if not db:
            continue
        rows = _query(
            db,
            "SELECT id, title, assignee, worker_pid, last_heartbeat_at, "
            "claim_expires, started_at FROM tasks WHERE status='running'",
        )
        for t in rows:
            tid = t.get("id")
            hb = t.get("last_heartbeat_at") or t.get("started_at") or 0
            reasons: list[str] = []
            if hb and now - hb > STALE_RUNNING_SECONDS:
                reasons.append(f"last heartbeat {(now - hb) // 60}m ago")
            exp = t.get("claim_expires")
            if exp and now > exp:
                reasons.append("claim expired")
            alive = pid_alive(t.get("worker_pid"))
            if alive is False:
                reasons.append(f"PID {t.get('worker_pid')} not running")
            if not reasons:
                continue

            prev = prev_ns.get(tid, {})
            first_seen = prev.get("first_seen", now)
            last_alert = prev.get("last_alert", 0)
            ns[tid] = {"first_seen": first_seen, "last_alert": last_alert}
            if now - last_alert < REPEAT_SECONDS:
                continue

            title = (t.get("title") or "")[:70]
            who = t.get("assignee", "?")
            head = f"*{slug}* — {tid} running but stale (worker may be dead) [{who}]: {title}"
            report.append(head + "\n    " + "; ".join(reasons))
            ns[tid]["last_alert"] = now
    return report, ns


def detect_aging_triage(now: int, slugs: list[str], prev_ns: dict) -> tuple[list[str], dict]:
    """Addition 2: per board, flag if triage cards are older than 10m.

    Returns (report_lines, updated_namespace)."""
    report: list[str] = []
    ns: dict = {}
    cutoff = now - AGING_TRIAGE_SECONDS
    for slug in slugs:
        db = board_db_path(slug)
        if not db:
            continue
        rows = _query(
            db,
            "SELECT id, title, assignee, created_at FROM tasks "
            "WHERE status='triage' AND created_at < ?",
            (cutoff,),
        )
        if not rows:
            continue

        prev = prev_ns.get(slug, {})
        first_seen = prev.get("first_seen", now)
        last_alert = prev.get("last_alert", 0)
        ns[slug] = {"first_seen": first_seen, "last_alert": last_alert}
        if now - last_alert < REPEAT_SECONDS:
            continue

        n = len(rows)
        lines = [f"*{slug}* — {n} triage cards aging (auto-decomposer may be down)"]
        for t in rows[:6]:
            tid = t.get("id")
            age = (now - (t.get("created_at") or now)) // 60
            lines.append(f"    ▱ {tid} triage {age}m old")
        report.append("\n".join(lines))
        ns[slug]["last_alert"] = now
    return report, ns


def load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: dict) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = STATE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        tmp.replace(STATE_PATH)
    except OSError:
        # Disk full etc. Never crash the watchdog on state persistence.
        pass


def append_wake(summary: str, detail: list[str]) -> None:
    """Best-effort append of one KANBAN_BLOCKED_WAKE token line + detail.

    Called only when an alert actually fires. Never raises: a failed write
    (disk full, permission) is swallowed so the watchdog still exits 0.
    Exactly one token line is written per alert batch; detail lines are
    indented and must not contain the token.
    """
    try:
        WAKE_DIR.mkdir(parents=True, exist_ok=True)
        lines = [f"{WAKE_TOKEN} {summary.rstrip()}"]
        for d in detail:
            # Indent so it is unambiguously a detail line, not a token line.
            d = ("    " + d.strip()).rstrip()
            if WAKE_TOKEN in d:
                # Guard: token must never appear on a non-token line.
                d = d.replace(WAKE_TOKEN, "[REDACTED]")
            lines.append(d)
        payload = "\n".join(lines) + "\n"
        with WAKE_PATH.open("a", encoding="utf-8") as fh:
            fh.write(payload)
    except OSError:
        pass


def main() -> int:
    now = int(time.time())
    state = load_state()
    boards = list_boards()
    if not boards:
        print("Kanban stall watch: could not enumerate boards (hermes kanban boards failed).")
        return 1

    report: list[str] = []
    new_state: dict = {}

    for board in boards:
        tasks = board_tasks(board)
        if not tasks:
            continue

        running = [t for t in tasks if str(t.get("status", "")).lower() in ACTIVE]
        blocked = [t for t in tasks if str(t.get("status", "")).lower() == "blocked"]
        waiting = [t for t in tasks if str(t.get("status", "")).lower() in PENDING]

        prev = state.get(board, {})

        if running or not waiting:
            # Healthy: work in flight, or genuinely nothing left to do.
            continue

        first_seen = prev.get("first_seen") or now
        last_alert = prev.get("last_alert", 0)
        new_state[board] = {"first_seen": first_seen, "last_alert": last_alert}

        if now - first_seen < GRACE_SECONDS:
            continue
        if now - last_alert < REPEAT_SECONDS:
            continue

        stalled_min = (now - first_seen) // 60
        lines = [f"*{board}* — no task running, {len(waiting)} waiting (stalled ~{stalled_min}m)"]
        for t in blocked[:6]:
            tid = t.get("id", "?")
            title = (t.get("title") or "")[:70]
            who = t.get("assignee", "?")
            lines.append(f"  ⊘ {tid} [{who}] {title}")
        gated = [t for t in waiting if str(t.get("status", "")).lower() in {"todo", "ready"}]
        for t in gated[:4]:
            tid = t.get("id", "?")
            title = (t.get("title") or "")[:70]
            lines.append(f"  ◻ {tid} waiting: {title}")
        report.append("\n".join(lines))
        new_state[board]["last_alert"] = now

    # Preserve state for boards still stalled but not yet alerting.
    for b, v in new_state.items():
        state[b] = v
    for b in list(state.keys()):
        if b not in new_state and b not in (NS_STALE_RUNNING, NS_AGING_TRIAGE):
            state.pop(b, None)

    # --- Addition 1 & 2: SQLite-backed detectors (separate namespaces) ---
    stale_lines, stale_ns = detect_stale_running(now, boards, state.get(NS_STALE_RUNNING, {}))
    aging_lines, aging_ns = detect_aging_triage(now, boards, state.get(NS_AGING_TRIAGE, {}))
    report.extend(stale_lines)
    report.extend(aging_lines)
    state[NS_STALE_RUNNING] = stale_ns
    state[NS_AGING_TRIAGE] = aging_ns
    save_state(state)

    if not report:
        return 0  # silent

    # Wake bridge: one token line (plus indented detail) per alert batch.
    # Build a compact summary: alerting boards, finding count, first task ids.
    boards_hit = sorted({m.group(1) for m in re.finditer(r"\*\s*([A-Za-z0-9_\-]+)\s*\*", "".join(report))})
    tids = []
    for m in re.finditer(r"\b(t_[A-Za-z0-9_]+)\b", "".join(report)):
        if m.group(1) not in tids:
            tids.append(m.group(1))
    summary = f"{len(boards_hit)} board(s), {len(report)} finding(s)"
    if boards_hit:
        summary += ": " + ",".join(boards_hit)
    if tids:
        summary += " | ids: " + " ".join(tids[:6])
    append_wake(summary, report)

    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    print(f"⚠️ Kanban watchdog alert ({stamp})\n")
    print("\n\n".join(report))
    if any(line.startswith("*") and "no task running" in line for line in report):
        print("\nThese graphs cannot advance on their own. Unblock, answer, or terminalize them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
