# Overlay record: wayfinder

Adapted from upstream Matt Pocock's decision-mapping skill.

Base source: https://github.com/mattpocock/skills/blob/main/skills/engineering/wayfinder/SKILL.md
Upstream base commit: `8b36d4fb2635b3c21998dcd8144439c9e5ba7302`
Runtime base: `8f2712725af78c98c9ef7cdd447d14cb9348428d`

Public overlay (v4 delta): The v3 skill modelled the map as a single
`wayfinder:map` issue in an external issue tracker. It carried a separate
*blocked closeout* — a resolution comment, then close the issue, then append
one line to the map's hand-maintained "Decisions so far" index — and assumed
a fixed local installation and assignee.

v4 moves the map to a **first-class Kanban task** — the `/wayfinder` card
itself — and replaces the single-session charting pass with an
**orchestrator-charted loop**: the board's orchestrator charts each
generation as parent tasks of the four types, then ends its run blocking on
them via parent edges; when those parents complete the map re-promotes and
is re-charted (next generation, or a declaration that the fog has cleared).
There is no separate index — task topology is the index — and resolution is
written back as map comments instead of index maintenance.

Three corrections from the v4 self-hosting test run are encoded in the v4
skill text:

- **Live orchestrator profile (flaw #1).** The map is assigned at creation to
  the board's *current* `orchestrator_profile`, resolved at file time — never
  a hard-coded profile name. A wayfinder map outlives any config moment, so a
  baked-in name goes stale when the board's orchestrator changes (observed:
  a stale card was re-claimed by the old profile 51s after the operator
  switched orchestrators mid-flight).
- **Explicit workspace pinning (flaw #2).** Every wayfinder-created task pins
  its workspace explicitly to the repo worktree
  (`workspace_kind="dir"` + `workspace_path`); an unpinned `scratch` workspace
  was auto-projected into an unrelated project's worktree, so the resolved
  workspace is verified in the create response rather than assumed.
- **Durability (flaw #3).** A map's must-survive context — the flaw log and
  locked decisions — lives in the task *body* (or a pinned child task), never
  only in a comment, because comments are not durable across refile/duplicate
  (a refiled card arrived with its flaw-log comment dropped).

The bundled `references/UPSTREAM_LICENSE.md` preserves Matt Pocock's MIT terms.
