# Worktree Note — Bounded Correction Evidence (task t_362daecc)

This note is the durable record required by task t_362daecc. It captures the
local commit identity, the fully bounded correction scope, literal results from
the upstream validation tasks, and the remaining capability limitations. It is
committed into the worktree branch so downstream workers and reviewers can verify
the worktree state without re-deriving it.

## Commit identity

- Parent base SHA (bounded correction root): `2ea761d869638590f7ec4b93abca2168a059300c`
- Bounded-correction tip (final corrected commit): `ee467c34a83ea5042f9f09fa597dd69dcde8d412`
- Bounded-correction tip tree (HEAD^{tree} of `ee467c3`): `24ee302d8f5339b9f227a45beb1b758e23b599e8`
- Evidence commit (this task, `t_362daecc`): layered on top of `ee467c3`; its
  live SHA is `git rev-parse HEAD` on the branch
  `hermes-kanban-skills/t_6d9be2ec-repair-the-hermes-skill-tap-candidate`.
  (The evidence commit SHA is intentionally not pinned inside this note because
  amending the note changes the enclosing tree; verify with `git rev-parse HEAD`.)

No push, no merge, `main` not modified, branch protection not changed. The
primary repo checkout at `/Users/yt/Developer/hermes-kanban-skills` still sits at
`2ea761d` (branch `feat/hermes-skill-tap`) and was never touched.

## Bounded correction scope (2ea761d..ee467c3)

39 files changed, +2474 / -1017:

- `.github/workflows/sync-upstream.yml`
- `.github/workflows/validate-hermes-tap.yml`
- `EVIDENCE-t_68ef95c3.md`
- `EVIDENCE-t_b546a70c.md`
- `README.md`
- `WORKTREE_NOTE.md`
- `hermes-skill-manifest.json`
- `provenance/README.md`
- `provenance/overlays/foreground-owned-loop-orchestration.md`
- `provenance/overlays/kanban-orchestrator.md`
- `provenance/overlays/kanban-worker.md`
- `provenance/overlays/teach.md`
- `provenance/overlays/wayfinder.md`
- `provenance/overlays/wizard.md`
- `provenance/overlays/writing-plans.md`
- `provenance/sources/foreground-owned-loop-orchestration.md`
- `provenance/sources/kanban-orchestrator.md`
- `provenance/sources/kanban-worker.md`
- `provenance/sources/writing-plans.md`
- `scripts/sync-upstream-flat.py`
- `scripts/test-hermes-tap-regressions.py`
- `scripts/test-hermes-tap-workflows.py`
- `scripts/validate-hermes-tap.py`
- `skills/diagnosing-bugs/scripts/hitl-loop.template.sh`
- `skills/foreground-owned-loop-orchestration/SKILL.md`
- `skills/git-guardrails-claude-code/scripts/block-dangerous-git.sh`
- `skills/kanban-orchestrator/SKILL.md`
- `skills/kanban-worker/SKILL.md`
- `skills/teach/SKILL.md`
- `skills/teach/references/teach/GLOSSARY-FORMAT.md`
- `skills/teach/references/teach/LEARNING-RECORD-FORMAT.md`
- `skills/teach/references/teach/MISSION-FORMAT.md`
- `skills/teach/references/teach/RESOURCES-FORMAT.md`
- `skills/wayfinder/SKILL.md`
- `skills/wayfinder/references/UPSTREAM_LICENSE.md`
- `skills/wizard/SKILL.md`
- `skills/wizard/scripts/template.sh`
- `skills/writing-plans/references/UPSTREAM_LICENSE.md`
- `skills/writing-plans/references/relentless-design-interview-to-kanban.md`

Plus the two human-accepted README commits layered on top of the inherited
candidate `bea4659`:

- `bea4659` docs: clarify pre-merge tap install boundary
- `4722ab7` docs: correct README pre-merge install claim (PR head is raw-fetchable)

This commit (`t_362daecc`) adds `EVIDENCE-t_8dcbe009.md` (the gate re-run
evidence from the parent task) and this refreshed note. `EVIDENCE-t_8dcbe009.md`
is untracked prior-artifact evidence, not part of the 39-file correction range;
it is recorded here for durability.

## Upstream attribution (Matt Pocock / MIT) — preserved

The distribution preserves upstream attribution. `hermes-skill-manifest.json`
carries `source.kind/path/base_sha` and `upstream_base_sha` for every entry, and
the adaptation policy is one of
`{upstream-flat-copy, hermes-kanban-adaptation, hermes-support-path-adaptation}`.
`skills/wayfinder/references/UPSTREAM_LICENSE.md` and
`skills/writing-plans/references/UPSTREAM_LICENSE.md` carry the upstream MIT
license text. `scripts/validate-hermes-tap.py` enforces the
attribution/license/SHA contract (distribution_sha256 for adapted entries,
public-portability sweep over `skills/`, retired-API scan). No attribution was
stripped by this correction.

## Literal commands/results from upstream tasks

### t_68ef95c3 — validation & portability gates (all PASS, exit 0)
- `python3 scripts/validate-hermes-tap.py`
  `PASS: Hermes skill distribution validation (39 skills; 9 support references checked; 0 missing support paths)`
- `python3 scripts/test-hermes-tap-regressions.py`
  `PASS: Hermes tap regression oracle` (7 oracle checks incl. real
  `sync-upstream-flat.py` synchronizer fail-closed on adapted drift)
- `python3 scripts/test-hermes-tap-workflows.py`
  `PASS: Hermes tap workflow parse/behavior checks` (PyYAML + force-with-lease/
  shell-probe invariants)
- `check_public_portability` over 150 files under `skills/`: `0 portability violations`
- all-repo YAML parse (PyYAML): `YAML files parsed OK`
- `git diff --check`: `EXIT=0`
- `python3 -m compileall -q scripts`: `EXIT=0`
- isolated `scripts/link-skills.sh` smoke against throwaway HOME:
  `39/39 symlinks intact, 0 broken, 0 out-of-repo`
- Model-backed behavioral evaluation: N/A — scripts import NO LLM client
  (0 openai/anthropic/litellm/bedrock/gemini imports); static-only evidence,
  no fixture relabeled as model proof.

### t_6a07f1b1 — README install path in disposable HERMES_HOME (Hermes v0.20.0)
- Applied human-accepted README correction as commit `4722ab7` on top of `bea4659`.
- Re-exercised every README install path verbatim (live board env vars unset):
  `skills tap add`, `skills search --source github` (returns `[]`),
  `skills install <raw PR-head URL> writing-shape`,
  `skills install <raw PR-head URL> writing-plans` (with `references/*.md`
  support files), `skills check` (up_to_date), `skills update` (no updates) — all pass.
- Repo-identifier capability blocker proven: resolution targets upstream
  default branch `main` `8b36d4fb` (nested in-progress mirror), NOT the PR-head
  candidate. Raw default-branch flat path => HTTP 404; raw PR-head flat path =>
  HTTP 200. `validate-hermes-tap.py` PASS (39 skills, 0 missing).
- Merge NOT authorized; final gate owned by a separate reviewer lane.

### t_8dcbe009 — full validation re-run after tasks 0/1 edits (10 gates, all PASS)
Re-ran every validation/portability gate against the worktree after the task-0/1
edits landed. All 10 gates PASS (exit 0):

1. `python3 scripts/validate-hermes-tap.py`
   `PASS: Hermes skill distribution validation (39 skills; 9 support references checked; 0 missing support paths)`
2. `python3 scripts/test-hermes-tap-regressions.py`
   `PASS: Hermes tap regression oracle` (7 oracle checks)
3. `python3 scripts/test-hermes-tap-workflows.py`
   `PASS: Hermes tap workflow parse/behavior checks` (PyYAML + CI wiring)
4. per-gate support-reference check: `support references discovered: 9; support path errors: 0 => PASS`
5. per-gate public-portability gate: `public-portability violations: 0 => PASS`
6. per-gate provenance gate: `provenance-specific errors: 0 => PASS`
7. per-gate YAML parsing: `YAML files with parse errors: 0 => PASS`
8. `git diff --check 2ea761d HEAD` and subset `skills/** README.md docs/**`:
   `exit 0 (clean)`
9. `python3 -m compileall -q scripts ; echo $?` -> `0`
10. isolated tap/install smoke (disposable HERMES_HOME, README block):
    `tap add => Added tap: ytheesh96/skills (exit 0)`,
    `search --source github --json => [] (exit 0)`,
    `install writing-shape raw URL --yes => Installed: writing-shape (exit 0)`,
    `install writing-plans raw URL --yes => Installed: writing-plans incl.
     references/UPSTREAM_LICENSE.md, references/relentless-design-interview-to-kanban.md (exit 0)`,
    `check => writing-shape:url:up_to_date writing-plans:url:up_to_date 0 update(s) (exit 0)`,
    `update => No updates available. (exit 0)`.

Model-backed behavioral evaluation: **NOT RUN.** The fixtures under
`evals/fixtures/` (`kanban-enabled.json`, `kanban-disabled.json`) are
credential-free test CASES. Per the README they require an explicit
LOCAL/MANUAL model run, not public Actions credentials. This task did NOT execute
a model; the fixtures are reported as fixtures only and are never relabeled as
model-backed evidence.

## Remaining capability limitations (honest, not overclaimed)

1. **No model-backed behavioral evaluation.** The static validators exercise no
   model. SKILL.md *intended* behavior is asserted only as contract-text presence,
   not observed runtime behavior. A genuine model-backed evaluation is a separate
   task that would load each SKILL.md into a live agent harness. The
   `evals/fixtures/*.json` files are recorded as fixtures, never as proof.
2. **Repo-identifier capability blocker.** `skills tap` resolution resolves the
   upstream default branch (`main` `8b36d4fb`), not the candidate PR head. The raw
   default-branch flat path 404s; the raw PR-head flat path 200s. The README was
   corrected (commit `4722ab7`) to document the pre-merge raw-PR-head-URL install
   path. This is a CLI limitation, not a defect in the committed candidate.
3. **Merge / upstream PR / final acceptance not performed here.** Merge to `main`,
   the upstream PR, and final acceptance are owned by a separate reviewer lane.
   This task only commits locally and records evidence.
4. **`scripts/__pycache__/` is transient and NOT gitignored.** It is generated by
   the validators at run time and left in the worktree (non-deliverable; it does
   not affect any committed artifact or `git diff --check`). Re-running the
   validators will regenerate it.

## Acceptance checklist

- [x] Local commit created (bounded-correction tip HEAD = `ee467c3`; evidence commit layered on top — run `git rev-parse HEAD` for the live SHA)
- [x] Clean worktree after commit (`git status --porcelain` empty except transient `scripts/__pycache__/`)
- [x] Parent SHA `2ea761d...`, final commit/tree SHAs recorded
- [x] Changed paths recorded (39 files in 2ea761d..ee467c3)
- [x] Literal commands/results from prior tasks recorded (incl. t_8dcbe009 10-gate re-run)
- [x] Remaining capability limitations recorded (incl. model eval NOT run)
- [x] Matt Pocock / MIT attribution preserved (verified via manifest + UPSTREAM_LICENSE.md)
