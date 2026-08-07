# Overlay record: ask-matt

Adapted from upstream Matt Pocock's skill router.

Base source: https://github.com/mattpocock/skills/blob/main/skills/engineering/ask-matt/SKILL.md
Upstream base commit: `8b36d4fb2635b3c21998dcd8144439c9e5ba7302`
Runtime base: `8f2712725af78c98c9ef7cdd447d14cb9348428d`

Public overlay: `ask-matt` is the router that maps every user-reachable skill
and how they relate. It is re-pointed to the Hermes Kanban task model: all
stale `/to-tickets` references are rewritten to `/to-tasks`, and the
tracker-model prose is rewritten to the Kanban-only model (per the
Kanban-as-issue-tracker decision). Matt Pocock's MIT terms are preserved in the
source repository attribution.
