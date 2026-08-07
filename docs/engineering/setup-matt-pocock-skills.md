## What it does

`setup-matt-pocock-skills` answers two questions about one repo — where the Hermes Kanban board that serves as the issue tracker lives, and where the domain docs sit — and records the answers as markdown files under `docs/agents/`.

Those files are the only thing that varies between repos. The skills themselves are identical everywhere; they read `docs/agents/issue-tracker.md` at run time and do what it says. That is why the set is not tied to one board layout, and why no skill file ever needs editing to point it somewhere else. Invoking it with "link the skills to a custom board" works as long as that board is Hermes Kanban — the tracker is fixed to one medium by this tap.

It is a prompt-driven skill, not a deterministic script. It reads your `git remote`, your existing `CLAUDE.md`, your existing `CONTEXT.md`, proposes what it found, and waits for you to confirm before writing anything.

## When to reach for it

You invoke this by typing `/setup-matt-pocock-skills` — the [agent](https://www.aihero.dev/ai-coding-dictionary/agent) won't reach for it on its own. It is deliberately marked non-invokable, so no other skill can fire it for you.

Reach for it once per repo, before the first use of any other engineering skill. If [triage](https://aihero.dev/skills-triage), [to-spec](https://aihero.dev/skills-to-spec), [to-tasks](https://aihero.dev/skills-to-tasks) or [wayfinder](https://aihero.dev/skills-wayfinder) start guessing where your issues go, or apply board statuses your board doesn't have, they have not been set up here yet. A repo already halfway through a project is a fine place to run it; the skill reads what is already there and no earlier work is wasted.

## Prerequisites

It writes into the repo you run it in:

| It writes | Where |
| --- | --- |
| `issue-tracker.md` | `docs/agents/` |
| `domain.md` | `docs/agents/` |
| An `## Agent skills` block | whichever of `CLAUDE.md` / `AGENTS.md` already exists |

All of it is committed markdown. There is no user-level or global mode: the config lives in the repo, so every repo gets its own copy.

## The two decisions

It leads each section with the recommended answer, and skips whatever exploration already settled. Most runs are two confirmations and done.

| Decision | What it proposes | When it actually asks |
| --- | --- | --- |
| **Issue tracker (Hermes Kanban)** | the board this repo uses, plus its tenant and notifier | always — this is the one real choice |
| **Triage roles → board status** | the authoritative mapping (`needs-triage`→`triage`, `needs-info`→`blocked(kind=needs_input)`, agent-ready→`ready`, human-implementation→`blocked(kind=capability)`, `wontfix`→`archived`) | only if the `triage` skill is installed |
| **Domain docs** | single-context: one `CONTEXT.md` plus `docs/adr/` at the root | only if it spots monorepo signals, and then it offers a multi-context `CONTEXT-MAP.md` |

The tracker is fixed to Hermes Kanban — there is no GitHub Issues, GitLab, or local-markdown menu. You supply only the two repo-specific facts the board needs:

- **Board slug** — the board this repo's cards live on (e.g. `default`, or a named board). Resolve it at run time from `HERMES_KANBAN_BOARD` / `HERMES_KANBAN_DB`; if unset, Hermes uses the active/current board.
- **Tenant** — the namespace this repo's board lives under. Record the convention you want (e.g. the repo slug); it resolves from the per-repo config at publish time.
- **Notifier / subscription** — the maintainer receives board activity through their Hermes **gateway notifier** (the agent's own delivery channel — Telegram/Discord/etc. wired to the gateway), not a third-party issue-tracker webhook. No separate issue-tracker integration is needed.

The triage-role → board-status mapping is **authoritative and fixed by this tap** (it lives in `docs/agents/issue-tracker.md` and in the `triage` skill) — do not re-open it as a menu. You may record overrides only if the repo's board already uses different status strings; otherwise write the table as given.

## Common questions

**Do I have to use Hermes Kanban?**

Yes — this tap fixes the issue tracker to Hermes Kanban. The board is the only issue medium; there is no GitHub Issues, GitLab, or local-markdown fallback. The community has run the upstream skills against Linear, GitLab, and plain markdown under `.scratch/`, but those paths are not part of this tap. A common split there is Linear for issues and planning, GitHub for code and PRs: in this tap both live on the one board.

**Do I need to re-run it after updating the skills?**

Asked directly after v1.1, Matt said yes. The skill's own closing message is softer — it tells you re-running is only needed to switch boards or start over. Both are defensible and the reason for the gap is real: the seed templates change between versions, so a `docs/agents/issue-tracker.md` written by an older release can go stale against the skills now reading it. If a downstream skill starts doing something the docs describe differently, re-running is the cheap fix.

**It wrote to `CLAUDE.md`, but I'm on Codex.**

Known gap, still open. The file-selection rule is "edit `CLAUDE.md` if it exists, else `AGENTS.md`" — it checks which file exists, not which [harness](https://www.aihero.dev/ai-coding-dictionary/harness) is running. A repo with a `CLAUDE.md` left over from Claude Code will get its `## Agent skills` block somewhere Codex never reads. Two workarounds are in circulation: move the block to `AGENTS.md` by hand, or keep `AGENTS.md` canonical and make `CLAUDE.md` a one-line pointer at it. If neither file exists, the skill asks you which to create rather than picking, which has confused people who expected it to just decide.

**It didn't create my board statuses.**

It doesn't. `docs/agents/issue-tracker.md` records the triage-role → board-status mapping — it tells `/triage` which native board status corresponds to each role. The statuses are native to Hermes Kanban, not labels the skill must create. If your board already uses the canonical status strings, the mapping is an identity table and there is nothing to configure. That is the intended common case, not a missing step.

**Can I configure the other skills' behaviour here — [grilling](https://www.aihero.dev/ai-coding-dictionary/grilling) cadence, question format, tone?**

No. It configures two things: board, doc layout. There have been direct requests to make it the home for per-user preferences, and the standing answer is that skills stay opinionated: *"Config is death."* Preferences belong in your `CLAUDE.md` as plain instructions, which every skill already reads.

**Can I keep the config in `~/.claude` instead of committing it to every repo?**

Not today. There is an open request for exactly this from someone running the skills across many repos, and no user-level mode exists. Every repo carries its own `docs/agents/`.

**Isn't it strange to have a skill that configures the other skills?**

One long-standing complaint says yes, in these words: *"having a skill to set up the other skill does not feel right to me — that means the LLM is configuring its own skills."* The trade is real and acknowledged: the alternative to a setup step is duplicating board instructions into every skill that touches issues. The output is inspectable, editable markdown, which is the mitigation — you can read every file it wrote and change it by hand, and day-to-day tweaks are exactly that, not another run.

## It's working if

- `docs/agents/issue-tracker.md` and `docs/agents/domain.md` exist.
- An `## Agent skills` section appears in the instruction file your harness actually reads, with a one-line summary pointing at each of those files.
- The board slug and tenant it recorded match the board you really use, and the status strings match statuses that really exist on that board.
- After it, `/to-tasks` publishes without asking you where issues live, and `/triage` applies the board statuses from the mapping rather than inventing them.
- Nothing in the skill files themselves changed. If setup edited a `SKILL.md`, something went wrong.

## Where it fits

`setup-matt-pocock-skills` is the **run-once setup** for the engineering flow, the precondition everything else assumes rather than a step in the chain. Its neighbours are its readers: [triage](https://aihero.dev/skills-triage), which applies the role→status mapping written here; [to-spec](https://aihero.dev/skills-to-spec) and [to-tasks](https://aihero.dev/skills-to-tasks), which publish into the Hermes Kanban board named here; and [wayfinder](https://aihero.dev/skills-wayfinder), which reads the board config to know how maps and child tasks are stored. The domain-doc layout it records is the one [domain-modeling](https://aihero.dev/skills-domain-modeling) fills in later — it creates `CONTEXT.md` and ADRs lazily, when a term or decision actually gets resolved, so an empty repo after setup is the expected state. For which skill to reach for next, [ask-matt](https://aihero.dev/skills-ask-matt) routes the whole set.
