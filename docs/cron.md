# Hermes Kanban Cron & Recovery Scripts

This document is the authoritative declaration of the background scripts that
keep the Hermes Kanban board healthy. The validator (`scripts/validate-hermes-tap.py`)
parses the table below and verifies that every declared script actually exists at
its declared repo path under `scripts/recovery/`.

| Script | Declared repo path | Purpose |
| --- | --- | --- |
| `kanban_subscribe_sync.py` | `scripts/recovery/kanban_subscribe_sync.py` | Clone the default-owned chat handle's Kanban subscriptions onto every enumerated board so a fresh board starts subscribed. |
| `kanban_block_watch.py` | `scripts/recovery/kanban_block_watch.py` | Read-only detector that watches every board's `kanban.db` for tasks stuck in `blocked` and surfaces them for recovery. |
| `kanban_stall_watch.py` | `scripts/recovery/kanban_stall_watch.py` | Read-only detector that watches every board's `kanban.db` for tasks that have stopped heartbeating past the stall timeout and surfaces them for recovery. |

All three scripts are stdlib-only (no Hermes CLI, no LLM) and resolve the Hermes
home from `HERMES_HOME` (env) or `Path.home() / ".hermes"` rather than a
hard-coded absolute path.
