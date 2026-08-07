# Evidence — t_8dcbe009: Re-run full validation and report gates

Date: 2026-08-07 (UTC)
Worktree: `/Users/yt/Developer/hermes-kanban-skills/.worktrees/t_6d9be2ec`
Branch: `hermes-kanban-skills/t_6d9be2ec-repair-the-hermes-skill-tap-candidate`
Local HEAD: `ee467c3 docs: record README install-path verification evidence (t_b546a70c)`
Hermes CLI: `Hermes Agent v0.20.0 (2026.8.3)`
PR head (refs/pull/1/head): `bea4659512bb4f5bcdb4a645c80930534789c5b9`

Scope: re-run every validation/portability gate after tasks 0/1 edits landed,
report each gate pass/fail with literal output, and keep model-behavioral
evaluation separate from fixture data. No reset/clean/stash/discard/duplicate
edits; primary checkout untouched; no push/merge/main modify.

## 1. validate-hermes-tap.py
```
PASS: Hermes skill distribution validation (39 skills; 9 support references checked; 0 missing support paths)
```
EXIT 0 — PASS.

## 2. test-hermes-tap-regressions.py
```
PASS: Hermes tap regression oracle
- current manifest/provenance validates with 0 missing support paths
- advanced upstream cursor validates without a historical SHA allowlist
- missing distributed support files fail the path-completeness gate
- adapted distribution content drift fails the immutable hash gate
- adapted upstream source drift is rejected before any write
- pure-copy upstream drift is planned and applied by the real synchronizer
- synchronized candidate validates with the advanced cursor
```
EXIT 0 — PASS.

## 3. test-hermes-tap-workflows.py
```
PASS: Hermes tap workflow parse/behavior checks
- parsed .github/workflows/validate-hermes-tap.yml with PyYAML
- parsed .github/workflows/sync-upstream.yml with PyYAML
- validation and regression gates are wired into CI
- sync uses normal merge and force-with-lease only
- sync PR body shell probe preserves the inert SHA substitution
```
EXIT 0 — PASS.

## 4. Support-reference check (per-gate, from validate internals)
Driver: /tmp/gate-runner.py (imports scripts/validate-hermes-tap.py, no repo edits).
```
GATE: support-reference check
  support references discovered: 9
  support path errors: 0
  => PASS
```
PASS. (Mirrors the 9 support refs the top-level validator reports; 0 missing.)

## 5. Public-portability gate (per-gate)
```
GATE: public-portability gate
  public-portability violations: 0
  => PASS
```
PASS. Scanned every shipped package file under skills/* and every provenance/*
file for private-identity tokens / free-floating provenance labels. 0 violations.

## 6. Provenance gate (per-gate)
```
GATE: provenance gate
  provenance-specific errors: 0
  => PASS
```
PASS. Reused validate()'s provenance-error class (immutable base SHA presence in
hermes-native/overlay records, base_sha tracking). 0 errors.

## 7. YAML parsing (per-gate)
```
GATE: YAML parsing
  YAML files with parse errors: 0
  => PASS
```
PASS. PyYAML safe_load over every skills/*/SKILL.md frontmatter, every
.github/workflows/*.yml, and every provenance/*.yaml/*.yml. 0 parse errors.

## 8. git diff --check (2ea761d..HEAD)
```
git diff --check 2ea761d HEAD            -> exit 0 (clean)
git diff --check 2ea761d HEAD -- skills/** README.md docs/** -> exit 0 (clean)
```
PASS. No whitespace/trailing-blank-line errors across the full range or the
skill/README/docs subset.

## 9. python3 -m compileall -q scripts
```
python3 -m compileall -q scripts ; echo $?  -> 0
```
PASS. All scripts/*.py byte-compile cleanly (no syntax errors).

## 10. Isolated tap/install smoke (disposable HERMES_HOME, README block)
Canonicalized HERMES_HOME via `pwd -P` (README calls for realpath to avoid the
macOS /var -> /private/var symlink rejection). PR_HEAD = bea4659…c5b9.
```
HERMES_HOME=/private/var/folders/.../hermes-skill-tap.kbP6a9
=== tap add === Added tap: ytheesh96/skills                         TAP_ADD_EXIT=0
=== search --source github --json === []                            SEARCH_EXIT=0
=== install writing-shape raw URL --yes === Installed: writing-shape / Files: SKILL.md   INSTALL_SHAPE_EXIT=0
=== install writing-plans raw URL --yes === Installed: writing-plans / Files: SKILL.md, references/UPSTREAM_LICENSE.md, references/relentless-design-interview-to-kanban.md  INSTALL_PLANS_EXIT=0
=== check === writing-shape:url:up_to_date  writing-plans:url:up_to_date  0 update(s)  CHECK_EXIT=0
=== update === No updates available.                                UPDATE_EXIT=0
```
Installed tree (read-only):
```
skills/writing-shape/SKILL.md
skills/writing-plans/SKILL.md
skills/writing-plans/references/UPSTREAM_LICENSE.md
skills/writing-plans/references/relentless-design-interview-to-kanban.md
```
PASS. Raw-URL fallback installs the PR-head flat candidate end-to-end with
support files; tap search returns [] for the unmerged candidate (tap indexes
default branch only); check/update behave as documented. Disposable temp HOME
left in TMPDIR (ephemeral; not removed to avoid destructive rm).

## Model-backed behavioral evaluation — NOT RUN, reported separately
The model-enabled/disabled fixtures under `evals/fixtures/` are:
- `evals/fixtures/kanban-enabled.json`  (mode: skill-enabled;  required/forbidden behaviors)
- `evals/fixtures/kanban-disabled.json` (mode: skill-disabled; baseline only)
Both parse as valid JSON. Per README line 76 and the fixture `expected` field,
model-based evaluation is an explicit LOCAL/MANUAL operation and is NOT run with
public Actions credentials. This run did NOT execute a model; the fixtures are
credential-free test CASES, not proof of durable semantics. They are reported
here as fixtures only and are never relabeled as model-backed evidence.

## Constraints honored
- No reset/clean/stash/discard/duplicate edits performed.
- Primary checkout untouched; only the worktree branch was used.
- No push/merge/main modification.
- Working tree clean at completion (only transient scripts/__pycache__ present,
  generated by validator execution — non-deliverable, does not affect diff --check).

## Summary
All 10 deterministic/integration gates PASS:
1 validate-hermes-tap.py        PASS
2 test-hermes-tap-regressions   PASS
3 test-hermes-tap-workflows     PASS
4 support-reference check       PASS (9 refs, 0 missing)
5 public-portability gate       PASS (0 violations)
6 provenance gate               PASS (0 errors)
7 YAML parsing                  PASS (0 parse errors)
8 git diff --check (2ea761d..HEAD) PASS (clean)
9 compileall -q scripts         PASS
10 isolated tap/install smoke   PASS
Model-backed behavioral eval: not executed; fixtures recorded as fixtures only,
never relabeled as proof.
