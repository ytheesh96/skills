# Overlay record: setup-matt-pocock-skills

Adapted from upstream Matt Pocock's setup skill.

Base source: https://github.com/mattpocock/skills/blob/main/skills/engineering/setup-matt-pocock-skills/SKILL.md
Upstream base commit: `8b36d4fb2635b3c21998dcd8144439c9e5ba7302`
Runtime base: `8f2712725af78c98c9ef7cdd447d14cb9348428d`

Public overlay: `setup-matt-pocock-skills` writes the per-repo Kanban
configuration that adapted skills depend on. It is re-pointed to the Hermes
Kanban task model so the board slug and tenant resolve from the per-repo Kanban
config rather than an external issue tracker. Matt Pocock's MIT terms are
preserved in the source repository attribution.
