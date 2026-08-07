## What it does

`triage` works through the cards on your project's Hermes Kanban board, moving each one through a small state machine of **triage roles** — a category role and a state role — and leaving behind either an agent-ready brief, a specific question for the reporter, or an archived card with a recorded reason.

It is only for cards **you didn't create**. Raw bug reports, incoming feature requests, an external pull request that arrived unannounced — work that landed on the board from outside, in whatever shape the reporter left it. Tasks that [to-tasks](https://aihero.dev/skills-to-tasks) produced are already agent-ready by construction, and running `triage` over them is wasted work at best. The rule is flat: `/triage` is only for incoming cards, not for cards you created yourself.

The second thing that separates it from sorting by hand: it recommends and waits. It tells you its category and state call with reasoning, plus what it found in the codebase, and applies nothing until you direct it.

## When to reach for it

You invoke this by typing `/triage` and then describing what you want in plain language — the [agent](https://www.aihero.dev/ai-coding-dictionary/agent) won't reach for it on its own. "Show me anything that needs my attention", "let's look at #42", "move #42 to ready".

| What you have | Where to go |
| --- | --- |
| A board full of raw reports from other people | `/triage` |
| A rough idea of your own, nothing written down | [grill-with-docs](https://aihero.dev/skills-grill-with-docs) |
| A settled conversation to turn into a [spec](https://www.aihero.dev/ai-coding-dictionary/spec) | [to-spec](https://aihero.dev/skills-to-spec) |
| A spec to split into agent-ready tasks | [to-tasks](https://aihero.dev/skills-to-tasks) |
| A confirmed bug that needs a root cause, not a label | [diagnosing-bugs](https://aihero.dev/skills-diagnosing-bugs) |

## Prerequisites

`triage` reads and writes your Hermes Kanban board, so [setup-matt-pocock-skills](https://aihero.dev/skills-setup-matt-pocock-skills) has to have configured that board — its slug, tenant, notifier, and the triage-role → status mapping — first. The role names below are **canonical**; the board status strings they map to live in `docs/agents/issue-tracker.md`. If that doc is missing, run the setup skill.

The board config also decides whether external pull requests count as a request surface. That flag defaults to off and is no longer a setup question — flip it in `docs/agents/issue-tracker.md` if you want PRs in scope.

## The state machine

Every triaged card ends up carrying exactly one category role and one state role. Two categories: `bug` (something is broken) and `enhancement` (new feature or improvement). Five states, each mapping onto a Hermes Kanban status (the board is the issue tracker):

| Triage role | Board status | Means |
| --- | --- | --- |
| `needs-triage` | `triage` | You need to evaluate it. Where an unlabeled card normally lands first. |
| `needs-info` | `blocked(kind=needs_input)` | Waiting on the reporter. Returns to `triage` when they reply. |
| agent-ready | `ready` | Fully specified, with an agent brief attached; an [AFK](https://www.aihero.dev/ai-coding-dictionary/afk) agent can pick it up. |
| human-implementation | `blocked(kind=capability)` | The same brief, plus why this can't be delegated — judgment, external access, manual testing. |
| `wontfix` | `archived` | Closed, with the reason recorded. |

The `human-implementation` role maps to `blocked(kind=capability)`, **not** `blocked(kind=needs_input)` — it means the work is understood but requires a human, not that it is waiting on a question. A `blocked(kind=needs_input)` card is always the `needs-info` role.

That is the whole vocabulary, and the "exactly one state role" invariant is what keeps the queries simple. It is also the most-requested area of the [skill](https://www.aihero.dev/ai-coding-dictionary/skill): users have asked for a sixth state for work that is specified but blocked on another card, for `deferred` work gated on a future trigger, and for a terminal `implemented` state. None of those has shipped as a separate status — the native board statuses already cover them (`blocked(kind=needs_input)` for "waiting on another card", `ready` left open after the work lands for "implemented, awaiting verification", which you then close to `done`). See the questions below.

`wontfix` splits three ways, and the difference matters because only one of them writes to the knowledge base:

| Why you're closing it | What happens |
| --- | --- |
| Already implemented | A comment pointing at where it already lives. Nothing is written to `.out-of-scope/` — it's a built feature, not a rejected one, and filing it there would poison the dedup checks. |
| Rejected bug | Polite explanation, then archive. |
| Rejected enhancement | A file in `.out-of-scope/`, linked from the closing comment, then archive. |

`.out-of-scope/` is one markdown file per rejected **concept**, not per card, written as a short design document rather than a database row: what was rejected, why, and every card that has asked for it. `triage` reads the whole directory before it evaluates anything, and matches by concept rather than keyword — "night theme" matches `dark-mode.md`. When it hits a match it surfaces the old decision and asks whether you still feel the same way, instead of re-litigating the request from scratch.

## Verify before you brief

Before any [grilling](https://www.aihero.dev/ai-coding-dictionary/grilling), `triage` checks that the claim actually holds. For a bug, it reproduces it from the reporter's steps. For a PR, it checks the branch out and runs the relevant tests. Then it reports which of three things happened: confirmed, with the code path; failed to reproduce; or not enough detail to try, which is itself the strongest `needs-info` signal there is.

It runs two more checks against the codebase in the same pass — **redundancy** (is this already implemented, searched by domain concept rather than by the reporter's wording?) and **prior rejection** (does `.out-of-scope/` already say no?). Both are cheap, and both produce a `wontfix` when they hit.

All of it exists to make one artifact good: the **agent brief**, the structured comment posted when a card reaches the `ready` status. Once it's posted, the brief is the contract and the original report is only context. Briefs are written to be **durable** rather than precise, because a card can sit at `ready` for weeks while the code moves underneath it. So they name types, signatures and behavioural contracts, and never file paths or line numbers. A confirmed reproduction makes a far stronger brief than a guess does.

## A PR is not a board card

External pull requests are **not** board cards. Where the tracker used to treat a PR as an issue with attached code, this tap instead has a human file a card describing the external contribution; the PR itself is reviewed separately. A brief on such a card describes what's left to do, not how to build the thing from nothing. Discovery surfaces only *external* PRs (the board config defines who counts as external) — a collaborator's in-flight PR is not triage work. An explicitly named PR is always triaged regardless of author.

## Common questions

**I ran `/to-spec` and `/to-tasks`, and now those tasks are sitting there untriaged. Do I run `/triage` over them?**

No. They are already agent-ready — `to-tasks` publishes each task as a board card with its blockers declared in `parents=[...]`, and the dispatcher promotes a card to `ready` once every parent is `done`, precisely so an AFK runner picks them up without another pass. The user who hit this had run the spec flow, seen cards sitting in `triage`, and found their AFK runner ignoring everything. `triage` is the on-ramp for work that arrives from outside; the spec flow is the lane for work you originate. They meet at `ready`, not before.

**Is `triage` still relevant now that there's a `to-spec` → `to-tasks` → `implement` flow?**

Only if you have inbound work. `triage` predates that spine and does a different job: it is the lane for reports other people filed. If everything on your board came out of your own planning, you will rarely open it. If you maintain anything public, or your team files bugs at you, it is the front door. The main use is open-source repos taking cards from external contributors.

**My task isn't reaching `ready` even though I finished the work.**

Known open edge. `setup-matt-pocock-skills` writes the triage-role → status mapping into `docs/agents/issue-tracker.md`, but the statuses are native board states, not labels it creates for you. A card sits at `ready` only when every card in its `parents=[...]` is `done`; a single open blocker keeps it in `triage` or `blocked`. Check the card's parent edges before assuming the runner is misbehaving. If the mapping itself looks wrong, edit `docs/agents/issue-tracker.md` and re-run setup.

**Five states aren't enough — what about blocked, or deferred, or implemented?**

This is the most-filed gap on the skill, in three shapes, and the native board statuses already answer each: an card that is fully specified but waiting on another card to close is exactly `blocked(kind=needs_input)`; trigger-gated future work that is intended but not actionable yet is a card left in `triage` with a note; and "implemented, awaiting verification" is a card left at `ready` after the work lands, which you close to `done` once verified. Matt has agreed the blocked case is real and the native `blocked(kind=...)` vocabulary covers it. The workaround people use is a repo-local extra status alongside the category, which keeps the canonical state slot occupied by something honest at the cost of the skill not knowing about it. One community derivative goes further, adding `needs-slicing`, `tracking` and effort labels — that works, but it is theirs, not the skill's.

**How is this different from `/diagnosing-bugs`?**

The verification step here is deliberately shallow — enough to answer "is this real, and roughly where does it live", not to find a root cause. When a bug won't reproduce from the reporter's steps in a few minutes, the honest move is `needs-info`, or [diagnosing-bugs](https://aihero.dev/skills-diagnosing-bugs) if you want to chase it now. Neither skill's text currently mentions the other; a user found that seam, and it is still open.

**Can I point it at my whole backlog and let it run?**

You can ask, but watch what it reads. The "show what needs attention" pass is a cheap listing meant for *selection* — you pick one, and then it gathers full [context](https://www.aihero.dev/ai-coding-dictionary/context) on the one you picked. Run it across twenty cards at once and an agent can quietly fall back to that cheap listing as its evidence base, which returns card bodies but not comments. A user hit exactly this: three cards already carried a comment saying "already fixed, recommend archiving", and all three got fresh agent briefs instead. If you want a bulk pass, say explicitly that comments must be read per card.

**Does it work with Linear, or anything other than Hermes Kanban?**

No — this tap fixes the tracker to Hermes Kanban. The board is the only issue medium; there is no GitHub Issues, GitLab, or local-markdown fallback. The community has run the upstream skills against Linear, GitLab, and plain markdown under `.scratch/`, but those paths are not part of this tap. A common split there is Linear for issues and planning, GitHub for code and PRs: in this tap both live on the one board.

## It's working if

- Every card it touches ends with exactly one category role and one state role — never zero, never two states in conflict.
- It gives you a recommendation with reasoning and stops, rather than relabelling and moving on.
- The bug got reproduced, or the PR got checked out and run, before anything reached `ready`.
- The briefs it writes name types and behaviours, and contain no file paths and no line numbers.
- A request that was rejected six months ago comes back, and it says so and quotes the old reason instead of triaging it fresh.
- Every comment it posts while a card is in `triage` opens with `> *This was generated by AI during triage.*`

## Where it fits

`triage` is an **on-ramp**, not a step in the main chain. The main flow runs from an idea you had — grill, spec, tasks, implement, review — and `triage` is the parallel lane for work that arrived instead. It merges at the same place: a card at `ready` with a brief on it, which [implement](https://aihero.dev/skills-implement) picks up exactly as it would a task from [to-tasks](https://aihero.dev/skills-to-tasks). When a request needs sharpening before it can be briefed, `triage` runs [grilling](https://aihero.dev/skills-grilling) and [domain-modeling](https://aihero.dev/skills-domain-modeling) together, a round of questions at a time, so decisions land in `CONTEXT.md` and the ADRs as they're made. When you're not sure which lane you are in, [ask-matt](https://aihero.dev/skills-ask-matt) routes you.
