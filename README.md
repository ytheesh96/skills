# Hermes Agent Skills

This fork is a public Hermes Agent skill tap built from [Matt Pocock's `skills`](https://github.com/mattpocock/skills). It keeps the upstream tree reviewable while adding a direct-child distribution layout that Hermes can discover.

## What is upstream and what is Hermes-adapted?

- The original nested `skills/engineering`, `skills/productivity`, `skills/in-progress`, and `skills/misc` tree is preserved in place, with Matt Pocock's attribution and MIT license retained.
- Hermes distribution copies live at `skills/<slug>/SKILL.md`. These direct-child paths are the tap surface; the nested tree remains the upstream mirror.
- The machine-readable [`hermes-skill-manifest.json`](./hermes-skill-manifest.json) records provenance, the upstream base SHA, adaptation policy, version, and validation/evaluation cases for every distributed skill.
- Hermes-native adaptations are intentionally limited to public-safe planning/orchestration guidance. They keep planning foreground-owned, use the model-facing `kanban_*` flow, scope every durable operation to an explicit board and stable tenant, and leave decisions, graph mutation, follow-ups, acceptance, and closure with the foreground.

## Install through Hermes Agent

```bash
hermes skills tap add ytheesh96/skills
hermes skills search
hermes skills install <skill-slug>
hermes skills check
hermes skills update
```

The first command registers this fork as a tap. Search and install only the skills you need; `check` validates the installed skill metadata, and `update` refreshes installed skills from the tap.

## Upstream synchronization

`.github/workflows/sync-upstream.yml` checks `mattpocock/skills` weekly and supports `workflow_dispatch`. When upstream moves, it creates or refreshes an `upstream-mirror/<sha>` branch and pull request. The workflow:

1. fetches `upstream/main`;
2. performs a normal merge, so conflicts fail closed instead of overwriting Hermes adaptations;
3. identifies every mapped upstream source that changed since its manifest base;
4. refreshes only pure upstream flat copies;
5. stops for maintainer review when an adapted source drifts; and
6. never auto-merges behavior-changing skill updates.

Every pull request runs deterministic tap-layout, frontmatter, manifest, provenance/license, secret/path, and retired-API checks. The model-enabled/disabled fixtures under [`evals/fixtures`](./evals/fixtures) are credential-free test cases. Model-based evaluation is an explicit local/manual operation and is not run with public Actions credentials.

## Development

```bash
python3 scripts/validate-hermes-tap.py
```

The validation suite rejects executable references to removed durable APIs such as `delegate_task(mode="loop")`, `delegate_task(mode="durable")`, `loop_graph(...)`, `loop_create(...)`, `loop_status(...)`, and `loop_block(...)`. It also checks the current Kanban semantics in adapted orchestration skills.

## Attribution and license

The upstream-derived material remains attributed to Matt Pocock and is distributed under the [MIT License](./LICENSE). Hermes-native additions are marked in the manifest and are intended for public redistribution.
