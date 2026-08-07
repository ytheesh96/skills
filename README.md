# Hermes Agent Skills

This fork is a public Hermes Agent skill tap built from [Matt Pocock's `skills`](https://github.com/mattpocock/skills). It keeps the upstream tree reviewable while adding a direct-child distribution layout that Hermes can discover.

## What is upstream and what is Hermes-adapted?

- The original nested `skills/engineering`, `skills/productivity`, `skills/in-progress`, and `skills/misc` tree is preserved in place, with Matt Pocock's attribution and MIT license retained.
- Hermes distribution copies live at `skills/<slug>/SKILL.md`. These direct-child paths are the tap surface; the nested tree remains the upstream mirror.
- The machine-readable [`hermes-skill-manifest.json`](./hermes-skill-manifest.json) records provenance, the upstream base SHA, adaptation policy, version, and validation/evaluation cases for every distributed skill.
- Hermes-native adaptations are intentionally limited to public-safe planning/orchestration guidance. They keep planning foreground-owned, use the model-facing `kanban_*` flow, scope every durable operation to an explicit board and stable tenant, and leave decisions, graph mutation, follow-ups, acceptance, and closure with the foreground.

## Install through Hermes Agent

Hermes taps index the repository's default branch. After this flat layout is
published there, the direct-child paths under `skills/<slug>/` are searchable.
The current Hermes installer accepts a full GitHub identifier in the form
`owner/repo/path/to/skill-directory` or a direct `SKILL.md` URL; `<skill-slug>`
by itself is a search term, not an installer identifier. GitHub identifiers
resolve the repository's default branch, so they cannot install an unmerged
pull-request revision.

```bash
tmp_home="$(mktemp -d "${TMPDIR:-/tmp}/hermes-skill-tap.XXXXXX")"
tmp_home="$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$tmp_home")"
export HERMES_HOME="$tmp_home"
trap 'rm -rf "$tmp_home"' EXIT
export HERMES_TAP_REPOSITORY=ytheesh96/skills
hermes skills tap add "$HERMES_TAP_REPOSITORY"
hermes skills search writing-shape --source github --json

# Tested fallback for a published immutable commit. Set TAP_COMMIT to a
# published commit that contains this flat layout; an unmerged pull-request
# commit is not visible through a tap's default-branch index and cannot be
# fetched from raw.githubusercontent.com until it is published.
: "${TAP_COMMIT:?Set TAP_COMMIT to a published commit containing this tap layout}"
hermes skills install \
  "https://raw.githubusercontent.com/ytheesh96/skills/${TAP_COMMIT}/skills/writing-shape/SKILL.md" \
  --yes
hermes skills check
hermes skills update
```

The first command registers this fork as a tap. The exact search query uses the
GitHub tap source; while this candidate is only a pull request it returns `[]`
because the tap reads the default branch. The raw URL fallback is tested only
for a published immutable revision; the smoke installed `writing-shape`,
`check` reported it up-to-date, and `update` reported no updates. It does not
prove installation of this unmerged local candidate. Until this candidate is
published, no supported installer source can fetch its exact commit. After the
flat layout is on the default branch, use the repository identifier for the
published path (for example `ytheesh96/skills/skills/writing-shape`); before
then, the resolver may return the old default-branch indexed skill instead of
the candidate. The smoke canonicalizes the disposable `HERMES_HOME` path
because the current CLI compares canonical install roots; without that step,
macOS symlinked temporary directories can be rejected during installation.

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
python3 scripts/test-hermes-tap-regressions.py
python3 scripts/test-hermes-tap-workflows.py
```

The validation suite checks the 39 direct-child bundles, every referenced
support file, pure-copy byte parity, adapted-content hashes, committed
provenance, public portability, and current Kanban semantics. It rejects
executable references to removed durable APIs such as
`delegate_task(mode="loop")`, `delegate_task(mode="durable")`,
`loop_graph(...)`, `loop_create(...)`, `loop_status(...)`, and
`loop_block(...)`. The regression oracle advances the upstream cursor in an
isolated checkout and proves that adapted drift fails closed before a sync can
write anything.

## Attribution and license

The upstream-derived material remains attributed to Matt Pocock and is distributed under the [MIT License](./LICENSE). Hermes-native additions are marked in the manifest and are intended for public redistribution.
