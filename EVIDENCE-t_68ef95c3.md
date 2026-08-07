# Validation & Portability Gate Evidence — t_68ef95c3

Worktree: `hermes-kanban-skills/t_6d9be2ec-repair-the-hermes-skill-tap-candidate`
Run date: 2026-08-06 (UTC from system clock)
Runner: elephant (kanban worker)

All commands run from the worktree root:
`cd /Users/yt/Developer/hermes-kanban-skills/.worktrees/t_6d9be2ec`

---

## 1. Core deterministic gates

### 1.1 `python3 scripts/validate-hermes-tap.py`
```
PASS: Hermes skill distribution validation (39 skills; 9 support references checked; 0 missing support paths)
EXIT=0
```
Covers: manifest shape, upstream SHA/license/attribution, per-skill provenance
(source.kind/path/base_sha, upstream_base_sha tracking, adaptation.policy
in {upstream-flat-copy, hermes-kanban-adaptation, hermes-support-path-adaptation}),
distribution_sha256 for adapted entries, **public-portability sweep over every
file in `skills/`** (150 files) and provenance files, retired-API scan in fenced
blocks, required-durable-semantics per skill, and LICENSE presence.

### 1.2 `python3 scripts/test-hermes-tap-regressions.py`
```
PASS: Hermes tap regression oracle
- current manifest/provenance validates with 0 missing support paths
- advanced upstream cursor validates without a historical SHA allowlist
- missing distributed support files fail the path-completeness gate
- adapted distribution content drift fails the immutable hash gate
- adapted upstream source drift is rejected before any write
- pure-copy upstream drift is planned and applied by the real synchronizer
- synchronized candidate validates with the advanced cursor
EXIT=0
```
Exercises the real `sync-upstream-flat.py` synchronizer on synthetic upstream
advances: pure-copy refresh + cursor advance + re-validate, and adapted-drift
rejection fail-closed (no manifest/distribution write).

### 1.3 `python3 scripts/test-hermes-tap-workflows.py`
```
PASS: Hermes tap workflow parse/behavior checks
- parsed .github/workflows/validate-hermes-tap.yml with PyYAML
- parsed .github/workflows/sync-upstream.yml with PyYAML
- validation and regression gates are wired into CI
- sync uses normal merge and force-with-lease only
- sync PR body shell probe preserves the inert SHA substitution
EXIT=0
```
Covers YAML validity (PyYAML) of both workflows + safety invariants (no
unscoped force-push; quoted/inert printf PR body; gates wired in CI).

---

## 2. Aggregate / extracted checks

### 2.1 Support-reference count
`validate-hermes-tap.support_reference_count(root)` => **9** support references
checked across the 39 manifest distributions; validator reports 0 missing
support paths.

### 2.2 Public-portability / provenance sweep (explicit, independent of validator)
- Re-ran `check_public_portability` over all 150 files under `skills/`:
  **scanned 150 skill files; 0 portability violations**.
- Re-checked manifest policy/kind gate across 39 entries:
  `entries: 39; policy/kind issues: []`.

### 2.3 YAML parsing (all repo YAML)
Parsed every `.yml`/`.yaml` in repo (excluding `.git/`) with PyYAML:
**`YAML files parsed OK`** (no failures). (Also covered by 1.3 via the two
workflow files.)

### 2.4 `git diff --check`
`git diff --check` => **EXIT=0** (no whitespace / trailing-newline errors on the
worktree diff). Only untracked file in tree is `scripts/__pycache__/` (gitignored
content, not part of deliverable).

### 2.5 `python3 -m compileall -q scripts`
`compileall` over `scripts/` => **EXIT=0** (validate-hermes-tap.py,
test-hermes-tap-regressions.py, test-hermes-tap-workflows.py,
sync-upstream-flat.py all byte-compile clean).

---

## 3. Isolated tap / install smoke

Ran `scripts/link-skills.sh` against a **throwaway HOME** (`/tmp/htap-smoke-<ts>`,
no live profile touched):
```
EXIT(link)=0
linked (emitted) lines: 148
claude skills unique dirs: 39
agents skills unique dirs: 39
broken symlinks: 0
links outside repo: 0
```
Notes: `link-skills.sh` discovers every `SKILL.md` (incl. upstream source
sub-paths), so it emits 148 `linked` lines; `ln -sfn` overwrites collisions,
leaving exactly **39** final symlinks per harness, all resolving to a real
`SKILL.md`, all pointing inside the repo. Cleanup of the temp dir left to
operator to avoid destructive rm inside the worktree shell.

---

## 4. Model-backed behavioral evaluation — SEPARATE, NO OVERCLAIM

**Finding:** none of the validation gates exercise a model. Static audit of
`scripts/*.py` found **0 imports** of any LLM client (openai / anthropic /
litellm / bedrock / gemini) and **0** `chat.completions` / `message=...role`
/ `completion(` / `invoke(` calls. The only regex hits for model-ish tokens were
false positives on `HEX_SHA.fullmatch` in the validator.

Therefore:
- Every gate above is a **deterministic static/structural check** (manifest
  contract, SHA/portability/provenance, YAML syntax, whitespace, byte-compile,
  symlink integrity).
- There is **no model inference, no behavioral scoring, no end-to-end agent
  run** produced by these scripts.
- The 39 skills' *intended* model behavior is defined by their `SKILL.md`
  `description`/`policy` frontmatter and the `REQUIRED_SEMANTICS` tokens the
  validator asserts are *present in text* — that is contract presence, not a
  runtime behavior proof.
- **No fixture was relabeled as model proof.** The regression oracle uses
  synthetic manifest/upstream mutations only; it proves the validator/sync
  contracts fail-closed, not any agent behavior.

If a genuine model-backed evaluation is required, it is a separate task: it
would need to load each SKILL.md into a live agent harness and assert observed
tool/behavior, which this task's scripts do not perform.

---

## 5. Acceptance summary

| Gate | Result |
|------|--------|
| validate-hermes-tap.py | PASS (39 skills, 9 support refs, 0 missing) |
| test-hermes-tap-regressions.py | PASS (7 oracle checks) |
| test-hermes-tap-workflows.py | PASS (PyYAML + invariants) |
| support-reference check | 9 refs, 0 missing |
| public-portability / provenance | 0 violations (150 files) |
| YAML parsing (all repo YAML) | OK |
| git diff --check | clean (EXIT=0) |
| compileall scripts | OK (EXIT=0) |
| isolated tap/install smoke | 39/39 symlinks intact, 0 broken, 0 out-of-repo |
| model behavioral evaluation | N/A for these scripts — no model invoked (reported separately, no overclaim) |

All gates pass. No documented blockers. Evidence captured in this file.
