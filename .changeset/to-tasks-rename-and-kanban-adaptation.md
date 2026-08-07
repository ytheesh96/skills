---
"mattpocock-skills": patch
---

Rename the `to-tickets` skill to `to-tasks` and adapt the Hermes skill tap to a Kanban-native workflow.

- Rename `skills/to-tickets` → `skills/to-tasks` (git mv) and rewrite `SKILL.md` so the task tracker is **Hermes Kanban** rather than GitHub Issues: the board slug and tenant resolve from the per-repo Kanban config, and each approved slice is published as a board card via `kanban_create` in dependency order.
- One `kanban_create` per approved vertical slice, declaring its blocking edges; slices land in `triage` with no status assumptions rather than opening issues directly.
- Update all in-repo references (`ask-matt` router, `CONTEXT.md` glossary, `triage`/`setup` skills, docs pages) from `to-tickets` to `to-tasks` and from "ticket(s)" to "task(s)", while preserving the wayfinder term "decision ticket".
