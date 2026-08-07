# Overlay record: to-tasks

Adapted from upstream Matt Pocock's task-splitting skill.

Base source: https://github.com/mattpocock/skills/blob/main/skills/engineering/to-tickets/SKILL.md
Upstream base commit: `8b36d4fb2635b3c21998dcd8144439c9e5ba7302`
Runtime base: `8f2712725af78c98c9ef7cdd447d14cb9348428d`

Public overlay: `to-tickets` is renamed `to-tasks` and republished as Hermes Kanban
cards instead of a local/issue-tracker file. Each approved slice becomes one
`kanban_create` in dependency order, landing in `triage` with no hard-coded
assignee; blocking edges are expressed as `parents=[blocker ids]` and the body
template carries What to build / Acceptance criteria / Blocked by (titles).
The board slug and tenant resolve from the per-repo Kanban config written by
`setup-matt-pocock-skills`. The bundled `references/UPSTREAM_LICENSE.md`
preserves Matt Pocock's MIT terms.
