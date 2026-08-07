#!/usr/bin/env python3
"""Cross-board Kanban foreground-notify subscription synchronizer.

Recovery tool for the "foreground notifications dropped" failure mode: tasks on
a board that should page the human in their active terminal session, but never
got a `default`-owned notify subscription (so terminal events are delivered
nowhere). This script finds those tasks and adds the missing subscription.

Designed for Hermes cron with no_agent=True:
  - EMPTY stdout  => silent, everything is already in sync (nothing sent)
  - one line      => one newly-created subscription (delivered verbatim)
  - non-zero exit => hard failure (cron sends an error alert)

It is ADDITIVE ONLY. It never mutates a task, never unsubscribes anything, and
never touches the board DB outside `notify-subscribe`. Idempotent: re-running
when everything is already subscribed produces empty stdout and exit 0.

Scope: tasks whose tenant starts with 'wayfinder-' on any board, in any of the
active statuses (triage, todo, ready, running, review, blocked, scheduled).

The foreground delivery handle (platform + chat-id + thread-id) is CLONED from
the most recent `default`-owned subscription already on the board -- we never
hardcode a session id. If no `default`-owned subscription exists anywhere, there
is nothing to clone from, so we exit 0 silently.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
HERMES_HOME = Path(os.environ.get("HERMES_HOME", HOME / ".hermes")).expanduser()

HERMES_BIN = os.environ.get("HERMES_BIN") or str(HERMES_HOME / "hermes-agent" / "venv" / "bin" / "hermes")
if not Path(HERMES_BIN).exists():
    HERMES_BIN = "hermes"

# Tenant prefix that marks the workstream we are repairing.
TENANT_PREFIX = "wayfinder-"

# Statuses considered "active" -- a task still in flight that should be able to
# page the human when it reaches a terminal event.
ACTIVE_STATUSES = {"triage", "todo", "ready", "running", "review", "blocked", "scheduled"}

NOTIFIER_PROFILE = "default"

# Dispatcher-spawned workers (and other pinned callers) can inherit these env
# vars, which silently redirect every `hermes kanban --board X` read to the
# wrong DB. We MUST never let them leak into our subprocess calls, or the scan
# enumerates the pinned board instead of the real per-board DBs.
_ENV_BLOCKLIST = {"HERMES_KANBAN_DB", "HERMES_KANBAN_BOARD", "HERMES_KANBAN_WORKSPACES_ROOT"}
CLEAN_ENV = {k: v for k, v in os.environ.items() if k not in _ENV_BLOCKLIST}

# Foreground delivery handle, written by the foreground desktop session. Preferred
# over clone-newest when present (see load_pinned_handle). This is a ROOT-level
# delivery concept (notifier_profile=default => root default profile), so the pin
# lives in the root Hermes home. Resolved via HERMES_HOME (which defaults to
# ~/.hermes) so the script works on a fresh clone without a hard-coded path.
PIN_PATH = HERMES_HOME / "state" / "foreground-notify-target.json"


def run(args: list[str], timeout: int = 60) -> tuple[int, str]:
    """Run a hermes CLI invocation. Returns (returncode, stdout).

    On timeout returns (124, ""). On any other exception returns (1, "") so a
    broken subprocess is reported as a hard failure rather than crashing the
    script. The subprocess env is CLEAN_ENV -- the pinned board env vars are
    stripped so a pinned caller can never redirect our reads.
    """
    try:
        p = subprocess.run(
            [HERMES_BIN, *args],
            capture_output=True, text=True, timeout=timeout, env=CLEAN_ENV,
        )
        return p.returncode, (p.stdout or "")
    except subprocess.TimeoutExpired:
        return 124, ""
    except Exception:
        return 1, ""


def load_pinned_handle() -> dict | None:
    """Return the foreground pin-file handle, or None if absent/unusable.

    The pin file (`state/foreground-notify-target.json`) is written by the
    foreground desktop session and names the exact delivery target. When present
    and well-formed we prefer it over clone-newest so delivery is deterministic
    rather than dependent on whatever newest default-owned sub happens to exist.
    """
    if not PIN_PATH.exists():
        return None
    try:
        data = json.loads(PIN_PATH.read_text())
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    platform = str(data.get("platform", "") or "")
    chat_id = str(data.get("chat_id", "") or "")
    if not platform or not chat_id:
        return None
    return {
        "platform": platform,
        "chat_id": chat_id,
        "thread_id": str(data.get("thread_id", "") or ""),
    }


def list_boards() -> list[str]:
    """Enumerate board slugs via `hermes kanban boards list --json`."""
    code, out = run(["kanban", "boards", "list", "--json"])
    if code != 0 or not out.strip():
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    slugs: list[str] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        if entry.get("archived"):
            continue
        slug = entry.get("slug")
        if slug:
            slugs.append(str(slug))
    return slugs


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


def global_notify_list() -> list[dict]:
    """All notification subscriptions across all boards (`notify-list --json`)."""
    code, out = run(["kanban", "notify-list", "--json"])
    if code != 0 or not out.strip():
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def task_notify_list(board: str, task_id: str) -> list[dict]:
    code, out = run(["kanban", "--board", board, "notify-list", task_id, "--json"])
    if code != 0 or not out.strip():
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def learn_foreground_handle(subs: list[dict]) -> dict | None:
    """Return the most recent `default`-owned subscription handle, or None.

    A handle is {platform, chat_id, thread_id}. We clone from the newest
    default-owned subscription by created_at so we never hardcode a session id.
    """
    owned = [
        s for s in subs
        if isinstance(s, dict) and str(s.get("notifier_profile", "")) == NOTIFIER_PROFILE
    ]
    if not owned:
        return None
    owned.sort(key=lambda s: s.get("created_at", 0), reverse=True)
    newest = owned[0]
    return {
        "platform": str(newest.get("platform", "")),
        "chat_id": str(newest.get("chat_id", "")),
        "thread_id": str(newest.get("thread_id", "") or ""),
    }


def has_default_subscription(subs: list[dict]) -> bool:
    return any(
        isinstance(s, dict) and str(s.get("notifier_profile", "")) == NOTIFIER_PROFILE
        for s in subs
    )


def subscribe(board: str, task_id: str, handle: dict) -> tuple[bool, str]:
    """Create a default-owned subscription. Returns (ok, detail)."""
    args = [
        "kanban", "--board", board, "notify-subscribe", task_id,
        "--platform", handle["platform"],
        "--chat-id", handle["chat_id"],
        "--notifier-profile", NOTIFIER_PROFILE,
    ]
    if handle["thread_id"]:
        args += ["--thread-id", handle["thread_id"]]
    code, out = run(args)
    ok = code == 0
    return ok, (out.strip() if out.strip() else f"rc={code}")


def main() -> int:
    # 1. Resolve the foreground delivery handle.
    #    Prefer the pin file (written by the foreground desktop session) when it
    #    is present and well-formed; fall back to cloning the newest
    #    default-owned subscription across all boards. If neither yields a usable
    #    handle, there is nothing to deliver to -- exit 0 silently.
    handle = load_pinned_handle()
    if handle is None:
        all_subs = global_notify_list()
        handle = learn_foreground_handle(all_subs)
    if handle is None:
        return 0
    if not handle["platform"] or not handle["chat_id"]:
        # Malformed handle: cannot safely subscribe anything.
        print("kanban_subscribe_sync: no usable default-owned handle to clone.", file=sys.stderr)
        return 1

    # 2. Enumerate boards. A failure here is a hard failure.
    boards = list_boards()
    if not boards:
        print("kanban_subscribe_sync: could not enumerate boards (hermes kanban boards failed).", file=sys.stderr)
        return 1

    created: list[str] = []
    failures: list[str] = []

    # 3. For each board, find candidate tasks and ensure each has a default sub.
    for board in boards:
        tasks = board_tasks(board)
        candidates = [
            t for t in tasks
            if isinstance(t, dict)
            and str(t.get("tenant", "")).startswith(TENANT_PREFIX)
            and str(t.get("status", "")).lower() in ACTIVE_STATUSES
        ]
        for t in candidates:
            task_id = str(t.get("id", ""))
            if not task_id:
                continue
            subs = task_notify_list(board, task_id)
            if has_default_subscription(subs):
                continue
            ok, detail = subscribe(board, task_id, handle)
            if ok:
                thread = f" thread={handle['thread_id']}" if handle["thread_id"] else ""
                created.append(
                    f"+ {board}/{task_id} -> platform={handle['platform']} "
                    f"chat_id={handle['chat_id']}{thread} notifier={NOTIFIER_PROFILE}"
                )
            else:
                failures.append(f"{board}/{task_id}: {detail}")

    # 4. Emit one line per created subscription; report failures to stderr.
    for line in created:
        print(line)

    if failures:
        for f in failures:
            print(f"kanban_subscribe_sync: subscribe failed: {f}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
