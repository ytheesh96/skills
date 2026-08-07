# Overlay record: triage

Adapted from upstream Matt Pocock's triage skill.

Base source: https://github.com/mattpocock/skills/blob/main/skills/engineering/triage/SKILL.md
Upstream base commit: `8b36d4fb2635b3c21998dcd8144439c9e5ba7302`
Runtime base: `8f2712725af78c98c9ef7cdd447d14cb9348428d`

Public overlay: `triage` routes incoming work into the Hermes Kanban triage
lane instead of an external issue tracker. It is re-pointed to the Kanban task
model so each triaged item becomes a board card with the standard
What to build / Acceptance criteria / Blocked by shape. Matt Pocock's MIT terms
are preserved in the source repository attribution.
