# Worktree Note — Bounded Correction Evidence (task t_2cce5c21)

This note is the durable record required by task t_2cce5c21. It captures the
local commit identity, the fully bounded correction scope, literal results from
the upstream tasks, and the remaining capability limitations. It is committed
alongside the evidence artifact so downstream workers and reviewers can verify
the worktree state without re-deriving it.

## Commit identity

- Parent base SHA (bounded correction root): `2ea761d869638590f7ec4b93abca2168a059300c`
- Final commit SHA (HEAD):               `4722ab767c3a421a74373cd402396ad9c87ad4a2`
- Final tree SHA (HEAD^{tree}):          `7dd7c62d0b2ab240f1ddc8d980bfd74e4d94c9e8`
- Branch: `hermes-kanban-skills/t_6d9be2ec-repair-the-hermes-skill-tap-candidate`

No push, no merge, `main` not modified, branch protection not changed.

## Bounded correction scope (2ea761d..4722ab7)

36 files changed, +1990 / -1017:

- `.github/workflows/sync-upstream.yml`
- `.github/workflows/validate-hermes-tap.yml`
- `README.md`
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

Plus the two commits layered on top of the inherited candidate `bea4659`:
- `bea4659` docs: clarify pre-merge tap install boundary
- `4722ab7` docs: correct README pre-merge install claim (PR head is raw-fetchable)

## Upstream attribution (Matt Pocock / MIT) — preserved

The distribution preserves upstream attribution. `hermes-skill-manifest.json`
carries `source.kind/path/base_sha` and `upstream_base_sha` for every entry, and
the adaptation policy is one of
`{upstream-flat-copy, hermes-kanban-adaptation, hermes-support-path-adaptation}`.
`skills/wayfinder/references/UPSTREAM_LICENSE.md` and
`skills/writing-plans/references/UPSTREAM_LICENSE.md` were added to carry the
upstream MIT license text. `scripts/validate-hermes-tap.py` enforces the
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
- Merge NOT authorized; final gate `t_5dd91694` stays with default profile / foreground.

### t_8f2f29ea — independent review of kanban SKILL.md diffs (HEAD = bea4659)
- Review verdict: PASS. Working tree clean; 239 insertions / 831 deletions across
  `kanban-orchestrator/SKILL.md` (681 changed) + `kanban-worker/SKILL.md` (389 changed);
  net condensation + person-strip.
- 0 genuine person-specific leaks on added lines (2 scan hits were false
  positives: public skill names + generic Hermes loop/API terminology).
- Reusable semantics preserved: `kanban_create/show/link/complete/block/unblock/
  comment/list`, block kinds `dependency|needs_input|capability|transient`,
  workspace kinds `scratch|dir|worktree`, board+tenant, worker_context handoff,
  evidence handoffs, foreground↔worker boundary.
- No dangling refs to removed private files; `git diff --check HEAD` clean.
- No edits made (review only).

## Remaining capability limitations (honest, not overclaimed)

1. **No model-backed behavioral evaluation.** The static validators exercise no
   model. SKILL.md *intended* behavior is asserted only as contract text presence,
   not observed runtime behavior. A genuine model-backed evaluation is a separate
   task that would load each SKILL.md into a live agent harness.
2. **Repo-identifier capability blocker.** `skills tap` resolution resolves the
   upstream default branch (`main` `8b36d4fb`), not the candidate PR head. The raw
   default-branch flat path 404s; the raw PR-head flat path 200s. The README was
   corrected (commit `4722ab7`) to document the pre-merge raw-PR-head-URL install
   path. This is a CLI limitation, not a defect in the committed candidate.
3. **Merge / upstream PR / final acceptance not performed here.** Merge to `main`,
   the upstream PR, and final acceptance (`t_5dd91694`) are owned by a separate
   reviewer lane. This task only commits locally and records evidence.
4. **`scripts/__pycache__/` is transient and NOT gitignored.** It was generated by
   the validation scripts and removed (not committed) to keep the worktree clean.
   Re-running the validators will regenerate it; it does not affect any committed
   artifact.

## Acceptance checklist

- [x] Local commit created (HEAD = `4722ab767c3a421a74373cd402396ad9c87ad4a2`)
- [x] Clean worktree (`git status --porcelain` empty after commit)
- [x] Parent SHA `2ea761d...`, final commit/tree SHAs recorded
- [x] Changed paths recorded
- [x] Literal commands/results from prior tasks recorded
- [x] Remaining capability limitations recorded
- [x] Matt Pocock / MIT attribution preserved (verified via manifest + UPSTREAM_LICENSE.md)
