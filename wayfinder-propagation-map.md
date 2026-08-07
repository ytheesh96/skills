# Wayfinder Skill — Propagation Map (kanban t_ff47dc2d)

Research question: is the live wayfinder skill a symlink into this repo or an
independent copy, and how do edits to `skills/wayfinder/SKILL.md` propagate to
the running skill?

Verified 2026-08-07. **No files were modified** during this research.

## Verdict 1 — Symlink vs independent copy

- `~/.hermes/skills/software-development/wayfinder` -> **independent copy**
  (real directory; `readlink -f` resolves to itself, not into the repo).
- All six per-profile copies ->
  `profiles/{research-worker,orchestrator,peacock,reviewer-qa,bme,elephant}/skills/software-development/wayfinder`
  -> **independent copies** (real directories; none are symlinks).
- A recursive symlink scan found **zero** symlinks in the entire wayfinder
  install tree (dirs or SKILL.md files).
- Neither `~/.claude/skills/wayfinder` nor `~/.agents/skills/wayfinder` exists,
  so `link-skills.sh` has never populated those targets for wayfinder.

## Verdict 2 — Is `scripts/link-skills.sh` the propagation mechanism?

No — not for these paths.

`scripts/link-skills.sh` is the repo's only propagation script. It targets
**only** `~/.claude/skills` and `~/.agents/skills`, and it creates **symlinks
into the repo** (a `git pull` then keeps them current). It does **NOT** cover
`~/.hermes/skills/...` or any per-profile path.

The `~/.hermes` install tree was therefore created by a **different** mechanism
(the Hermes skill installer / `hermes skills install`, or a manual copy) and is a
**real copy with no auto-sync back to the repo**. A `git pull` in this repo will
**not** touch any live install — the copies are frozen snapshots.

## Verdict 3 — Version divergence (lineage, not just drift)

This is not a single drifted copy. Three distinct SKILL.md lineages are live
simultaneously. Verified via `version:` header + md5:

| Install path                                                  | version | md5 (short)     | notes |
|---------------------------------------------------------------|---------|-----------------|-------|
| repo tap (worktree) `skills/wayfinder/SKILL.md`              | 3.0.0   | 85ba221d        | repo source-of-truth candidate |
| `~/.hermes/skills/software-development/wayfinder` (GLOBAL)   | 5.4.0   | d5bf45cd        | most-evolved; triage/orchestrator-handoff model |
| `profiles/orchestrator/.../wayfinder`                        | 5.4.0   | d5bf45cd        | byte-identical to global |
| `profiles/{research-worker,peacock,reviewer-qa,bme,elephant}/.../wayfinder` | 2.0.0 | cb9542c0 | "Loop map" wording; older/separate fork |

Consequence for the running agent: the **research-worker** session actually
loads **v2.0.0** (its available-skills entry reads "durable Loop map", which is
the v2.0.0 wording), NOT the global v5.4.0. So "the installed skill" is
ambiguous — there are three live lineages, and the one this agent runs is v2.0.0.

## Verdict 4 — Exact maintainer push command (today)

There is **no automatic command**. `link-skills.sh` does not target the
`~/.hermes` tree. To push a repo edit to a live copy the maintainer must
manually copy (or re-run `hermes skills install`):

    cp skills/wayfinder/SKILL.md ~/.hermes/skills/software-development/wayfinder/SKILL.md
    cp skills/wayfinder/SKILL.md ~/.hermes/profiles/<profile>/skills/software-development/wayfinder/SKILL.md   # once per profile

(Long-term: extend `link-skills.sh` to target `~/.hermes/skills` + per-profile
dirs with symlinks, or adopt `hermes skills install` with a pinned commit.)

## Verdict 5 — Must the v4 rewrite also hit the installed copies?

Yes. The agent loads from the installed copy, not the repo tap. Any v4 (or v6)
rewrite must be applied to **every path the running profile resolves**, or the
live skill stays on its current lineage. Keeping them in sync going forward
requires one of:

  (a) symlink-based install targeting `~/.hermes/skills` + per-profile dirs
      (link-skills.sh currently does not); or
  (b) a documented manual re-copy / `hermes skills install` step after every
      repo edit; or
  (c) adopting `hermes skills install` with a pinned commit so installs are
      deterministic and re-runnable.

## Reconciliation fork (for [DECISION] — Vaitheesh)

Because this is lineage divergence, not mere copy drift, three options:

- **Option A — repo-true.** Treat repo tap v3.0.0 as canonical. Rewrite -> v4
  in the repo, then push v4 to all installs. Discards the v5.4.0 (triage /
  orchestrator-handoff) and v2.0.0 (Loop) evolutions unless explicitly merged.

- **Option B — adopt-5.4.0.** Treat the installed global v5.4.0 as the
  more-evolved lineage (triage orchestrator-handoff, capability-restricted
  orchestrator, auto-decompiler, needs_input, foreground spec-compilation card).
  Reconcile the repo tap up to v5.4.0 first, then iterate v5.4.0 -> v6 for the
  planned rewrite. Keeps the most feature-complete behavior live.

- **Option C — multi-lineage.** Recognize v2.0.0 (Loop map) and v5.4.0 (Kanban /
  triage) as deliberately separate products. Do not force-merge; pick which
  lineage the v4/v6 rewrite targets and document the other as a distinct fork.

## Evidence boundary

Version/lineage facts verified via md5 + `version:` header reads on 2026-08-07;
symlink status via `ls -la` / `readlink -f` / recursive `find -type l`. No files
were modified. Sync-mechanism claims about `link-skills.sh` are read directly
from its source; claims about install origin of `~/.hermes` are inferred from the
absence of symlinks and the absence of a covering script (not from an install
log, which was not found).
