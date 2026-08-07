# Evidence — t_b546a70c: Verify README install path in disposable HERMES_HOME

Date: 2026-08-07 (UTC)
Hermes CLI: `Hermes Agent v0.20.0 (2026.8.3)` — `/Users/yt/.local/bin/hermes`
Worktree: `/Users/yt/Developer/hermes-kanban-skills/.worktrees/t_6d9be2ec`
Branch: `hermes-kanban-skills/t_6d9be2ec-repair-the-hermes-skill-tap-candidate`
Local HEAD: `846391d6332e4a2872b0b3c903538a2c4d62ad1e`
PR head (refs/pull/1/head, feat/hermes-skill-tap): `bea4659512bb4f5bcdb4a645c80930534789c5b9`
main (default branch, no flat layout): `8b36d4fb2635b3c21998dcd8144439c9e5ba7302`

Scope: verify every README command against the live Hermes CLI/help, exercise the
exact tap/search/install/check/update path in a disposable HERMES_HOME, confirm the
repository-identifier blocker, and prove the raw SKILL.md URL fallback installs the
candidate with support files. No uncommitted edits touched; nothing pushed/merged to
main; primary checkout untouched.

## 0. CLI surface truth (README commands exist)

```
$ hermes skills --help
usage: hermes skills [-h]
  {browse,search,install,inspect,list,check,update,audit,uninstall,reset,
   list-modified,diff,opt-out,opt-in,repair-official,publish,snapshot,tap,config} ...
$ hermes skills tap add --help   # adds a GitHub repo as skill source  (OK)
$ hermes skills search --help    # --source github --json  (OK)
$ hermes skills install --help   # identifier | direct HTTP(S) URL to SKILL.md ; --yes  (OK)
$ hermes skills check --help     # (OK)
$ hermes skills update --help    # (OK)
```
All README-documented subcommands and flag spellings are present in v0.20.0.

## 1. Tap add + GitHub search (README "Install through Hermes Agent" block)

Disposable HERMES_HOME + `HERMES_TAP_REPOSITORY=ytheesh96/skills`:

```
=== tap add ytheesh96/skills ===
Added tap: ytheesh96/skills
TAP_ADD_EXIT=0
=== tap list ===
┌────────────────┬─────────┐
│ Repo           │ Path    │
├────────────────┼─────────┤
│ ytheesh96/skills │ skills/ │
└────────────────┴─────────┘
=== search writing-shape --source github --json ===
[]
SEARCH_EXIT=0
```

`search` returns `[]` exactly as the README predicts: the tap indexes the
**default branch** (`main` = `8b36d4f`, which has no flat `skills/<slug>` layout),
so the unmerged candidate is not reachable through the tap. VERIFIED.

## 2. Raw SKILL.md URL fallback at the PR head (README fallback block)

`TAP_COMMIT=bea4659512bb4f5bcdb4a645c80930534789c5b9` (= refs/pull/1/head).
Probe that the PR head is raw-fetchable before merge:

```
curl -I raw .../skills/writing-shape/SKILL.md      -> HTTP 200
curl -I raw .../skills/writing-plans/SKILL.md      -> HTTP 200
```

Both flat candidate SKILL.md files are reachable at the PR head on
raw.githubusercontent.com — confirming "a PR head is reachable at
raw.githubusercontent.com (published as refs/pull/<n>/head) even before it is merged."

Install the candidate via raw URL in the disposable home:

```
=== install writing-shape raw URL --yes ===
Fetching: https://raw.githubusercontent.com/ytheesh96/skills/<TAP_COMMIT>/skills/writing-shape/SKILL.md
Running security scan... Verdict: SAFE  Decision: ALLOWED
Installed: writing-shape
Files: SKILL.md
INSTALL_SHAPE_EXIT=0

=== install writing-plans raw URL --yes ===
Fetching: https://raw.githubusercontent.com/ytheesh96/skills/<TAP_COMMIT>/skills/writing-plans/SKILL.md
Running security scan... Verdict: SAFE  Decision: ALLOWED
Installed: writing-plans
Files: SKILL.md, references/UPSTREAM_LICENSE.md,
       references/relentless-design-interview-to-kanban.md
INSTALL_PLANS_EXIT=0

=== check ===
┌───────────────┬────────┬─────────────┐
│ Name          │ Source │ Status      │
├───────────────┼────────┼─────────────┤
│ writing-shape │ url    │ up_to_date  │
│ writing-plans │ url    │ up_to_date  │
└───────────────┴────────┴─────────────┘
0 update(s) available across 2 checked skill(s)

=== update ===
No updates available.

=== list ===
│ writing-plans │ url │ community │ enabled │
│ writing-shape │ url │ community │ enabled │
2 hub-installed, 0 builtin, 0 local

=== installed tree ===
skills/writing-shape/SKILL.md
skills/writing-plans/SKILL.md
skills/writing-plans/references/UPSTREAM_LICENSE.md
skills/writing-plans/references/relentless-design-interview-to-kanban.md
```

The raw-URL fallback installs the flat candidate end-to-end: both `writing-shape`
and `writing-plans` landed, `writing-plans` pulled its `references/*.md` support
files, `check` reported up-to-date, `update` reported no updates. VERIFIED.

## 3. Repository-identifier installer is a capability blocker (README claim)

Fresh disposable home. First prove `main` has no flat layout:

```
curl -I raw .../main/skills/writing-shape/SKILL.md          -> HTTP 404
curl -I raw .../main/skills/in-progress/writing-shape/SKILL.md -> HTTP 200
```

Then exercise the repository identifier the README names:

```
=== install ytheesh96/skills/skills/writing-shape --yes ===
Fetching: ytheesh96/skills/skills/writing-shape
Running security scan... Verdict: SAFE  Decision: ALLOWED
Installed: writing-shape
Files: SKILL.md
  Source: https://github.com/ytheesh96/skills/tree/8b36d4fb.../skills/in-progress/writing-shape
  Detail Page: https://skills.sh/ytheesh96/skills/skills/writing-shape
```

The repo identifier resolved the **default branch** (`8b36d4f`/`main`) and installed
the nested `skills/in-progress/writing-shape` mirror — NOT the flat candidate. The
scan Source line explicitly reads `tree/8b36d4fb.../skills/in-progress/writing-shape`.
This proves the README's claim: the repository-identifier installer is a capability
blocker for this unmerged candidate. After the flat layout lands on `main`, the same
identifier would resolve the published flat path. VERIFIED.

## 4. Development scripts (README "Development" block)

```
$ python3 scripts/validate-hermes-tap.py
PASS: Hermes skill distribution validation (39 skills; 9 support references checked; 0 missing support paths)

$ python3 scripts/test-hermes-tap-regressions.py
PASS: Hermes tap regression oracle
- current manifest/provenance validates with 0 missing support paths
- advanced upstream cursor validates without a historical SHA allowlist
- missing distributed support files fail the path-completeness gate
- adapted distribution content drift fails the immutable hash gate
- adapted upstream source drift is rejected before any write
- pure-copy upstream drift is planned and applied by the real synchronizer
- synchronized candidate validates with the advanced cursor

$ python3 scripts/test-hermes-tap-workflows.py
PASS: Hermes tap workflow parse/behavior checks
- parsed .github/workflows/validate-hermes-tap.yml with PyYAML
- parsed .github/workflows/sync-upstream.yml with PyYAML
- validation and regression gates are wired into CI
- sync uses normal merge and force-with-lease only
- sync PR body shell probe preserves the inert SHA substitution
```

All three deterministic gates PASS.

## Conclusion

Every command in README.md is accurate against Hermes v0.20.0:

- `hermes skills tap add` / `tap list` — work as written.
- `hermes skills search <q> --source github --json` — returns `[]` for the unmerged
  candidate because the tap indexes `main` only. Consistent with README.
- `hermes skills install <raw SKILL.md URL> --yes` — installs the PR-head candidate
  (flat `skills/<slug>`) WITH support files; `check`/`update` behave as documented.
- Repository-identifier install resolves `main` (`skills/in-progress/...`), confirming
  it cannot reach the unmerged flat candidate — a real, proven capability blocker.
- The three `scripts/*.py` development gates all PASS.

No README claim is a phantom or unexecuted route. The only "limitation" documented
(repo-identifier blocker) was independently reproduced and is real.
