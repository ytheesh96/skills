# Provenance records

`hermes-skill-manifest.json` separates two kinds of lineage:

- `upstream.base_sha` is the current sync cursor and may advance when the
  upstream repository is merged.
- `upstream.initial_base_sha` and each entry's `source.base_sha` are immutable
  lineage anchors. Sync must never rewrite them.
- `source.path` points to a committed upstream source file or a committed
  source record in this repository. It is not a free-form label.
- Adapted entries carry `source.overlay_path`, a committed record describing
  the public-safe overlay. Pure upstream copies have no overlay.

The validator checks every path, SHA shape, distribution file, support file,
frontmatter, adaptation policy, and public portability boundary. The sync
script advances only the current cursor and refuses to overwrite an adapted
source without a maintainer decision.
