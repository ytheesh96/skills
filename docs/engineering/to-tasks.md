## What it does

`to-tasks` takes a plan, a [spec](https://www.aihero.dev/ai-coding-dictionary/spec), or the conversation you are in, and breaks it into a set of **[tasks](https://www.aihero.dev/ai-coding-dictionary/task)** on Hermes Kanban. Each task declares its **blocking edges** — the other tasks that have to finish before it can start. The board slug and tenant resolve from the per-repo Kanban config that [setup-matt-pocock-skills](https://aihero.dev/skills-setup-matt-pocock-skills) wrote for this repository; `to-tasks` does not hard-code a tracker.

Every task is a **tracer bullet**: a narrow but complete path through every layer of the change — schema, API, UI, tests — that can be demoed on its own the moment it lands. That is the constraint that makes it behave differently from the obvious way to split work, which is to cut one layer at a time and integrate at the end. It also sizes each task to fit in a single fresh [context window](https://www.aihero.dev/ai-coding-dictionary/context-window), because the thing that will pick the task up is a [session](https://www.aihero.dev/ai-coding-dictionary/session) that has never seen your spec.

## When to reach for it

You invoke this by typing `/to-tasks` — the [agent](https://www.aihero.dev/ai-coding-dictionary/agent) won't reach for it on its own.

| Where you are | What to run |
| --- | --- |
| You have a spec and the build spans several sessions | `/to-tasks`, or `/to-tasks #<spec_card>` |
| The plan is only in the conversation, never written up | `/to-tasks` reads the thread directly — no spec needed |
| The whole change fits in one context window | [implement](https://aihero.dev/skills-implement) — skip the tasks |
| Nothing is decided yet | [grill-with-docs](https://aihero.dev/skills-grill-with-docs), then [to-spec](https://aihero.dev/skills-to-spec) |
| A [wayfinder](https://aihero.dev/skills-wayfinder) map has cleared | [to-spec](https://aihero.dev/skills-to-spec) first, to collapse the map, then `/to-tasks` |

Tasks that `to-tasks` produced are agent-ready by construction. Don't run [triage](https://aihero.dev/skills-triage) over them — triage is for work that arrived from someone else.

## Prerequisites

`to-tasks` publishes into Hermes Kanban, so [setup-matt-pocock-skills](https://aihero.dev/skills-setup-matt-pocock-skills) must have configured a board for this repo — it records the board slug, tenant convention, notifier/subscription expectation, and the triage-role → status mapping. `to-tasks` resolves the board slug and tenant from that config; if the config is missing it stops and tells you to run the setup skill first.

## Tracer bullets, not layers

A **horizontal** slice ships one layer of the change. Nothing works until every layer has landed, and each task's acceptance criteria have to reach into work that another task owns. A **vertical** slice — the tracer bullet — ships one thin path through all the layers at once, so it is verifiable alone and owns everything it grades.

This is the rule people break most often, and the consequences are well documented. One team ran a 26-task stack sliced by layer — corpus, producer, aggregator, selector — and got roughly twenty agent runs per closed task, about three quarters of them rework. Their own post-mortem traced every failure class back to the horizontal slicing rather than to the implementations.

Two things happen before anything is published. `to-tasks` looks for prefactoring — "make the change easy, then make the easy change" — and orders that work first. Then it presents the breakdown as a numbered list and quizzes you on it: is the granularity right, are the blocking edges real, should anything merge or split. Nothing reaches the board until you approve, and that quiz is the place to push back.

## Blocking edges

The edges are the point of the artifact. On Hermes Kanban they are native: each approved task is published as a board card with its blockers passed in `parents=[...]`, so the board wires the dependency itself. A task with no blockers needs no `parents` and can start immediately; a task whose blockers are all done sits on the **frontier** — `ready` — and the dispatcher can pick it up.

| Where the edges live | How you work them |
| --- | --- |
| Hermes Kanban board card | Native `parents=[...]` edges; any task whose parents are all `done` promotes to `ready` and is on the frontier |
| The quiz, before publish | Named as "Blocked by" on each proposed task — your chance to correct them before anything is created |

The edges live in the card either way. `to-tasks` produces the artifact and publishes it in dependency order (blockers first); running it — one session at a time, or a fleet driven by the dispatcher — is your job, not the skill's.

## The wide-refactor exception

One shape breaks the tracer-bullet rule. A **wide refactor** is a single mechanical change — rename a column, retype a shared symbol — whose **blast radius** fans across the whole codebase, so one edit breaks thousands of call sites and no vertical slice can land green.

`to-tasks` sequences that as **expand–contract** instead:

- **Expand** — add the new form beside the old, so nothing breaks.
- **Migrate** — move call sites over in batches sized by blast radius (per package, per directory), one task per batch, each blocked by the expand. The board stays green because the old form still exists.
- **Contract** — delete the old form once no caller remains, in a task blocked by every migrate batch.

Where even the batches can't stay green alone, they share an integration branch and all block a final integrate-and-verify task. Green is promised only there.

## Common questions

**It produced twelve tasks for a three-line change.**

Over-decomposition is the most reported friction on this skill, and it is consistent across practitioners: the [model](https://www.aihero.dev/ai-coding-dictionary/model) defaults to atomic units and loses the grouping that would make them meaningful. The quiz step exists for exactly this — ask it to merge, and it will. The deeper answer is that the tasks have a floor: if the whole change fits in one context window, you don't need this skill at all. Go straight to [implement](https://aihero.dev/skills-implement).

**The tasks came out one per layer — all the schema in one, all the API in another.**

This is the failure the vertical-slice rule is written against, and the skill still produces it sometimes. Catch it at the quiz step by asking one question per task: what can I demo when this is done? A task with no answer is a horizontal slice. Some people add a "demo path" line to each task for this reason, and report it nudges the model toward vertical decomposition.

**It kept truncating when it tried to read my spec.**

A very large spec can outgrow what a board card serves back cleanly, and there is no local copy to fall back on — the agent then burns [tool calls](https://www.aihero.dev/ai-coding-dictionary/tool-call) re-fetching chunks and never reaches the end. Don't [clear](https://www.aihero.dev/ai-coding-dictionary/clearing) or [compact](https://www.aihero.dev/ai-coding-dictionary/compaction) between `/to-spec` and `/to-tasks`. Run them in the same context window and the spec never has to be fetched back at all.

**The acceptance criteria graded nothing — some passed before any work was done.**

The card template asks for criteria and says nothing about whether they can fail, so this happens. Three shapes recur: a criterion already true at the base commit, a criterion that can only be satisfied by work another task owns, and one that restates the request rather than deriving from the artifact. Vertical slicing prevents most of it — a slice that delivers behaviour which didn't exist before is red at the base commit by construction — but the check is worth doing by hand. For each criterion, name the observation that would show it false, and confirm it fails at the commit the implementer starts from.

**The tasks are published. How do I actually run them?**

The skill stops at the artifact, and there is no auto-dispatch mode. On Hermes Kanban the board does the dispatch: cards land in `triage` with no status assumptions, and the dispatcher promotes a card to `ready` when its `parents` are all `done`. Open the frontier — the `ready` tasks whose blockers are cleared — and run one per fresh context, cleared between them. [implement](https://aihero.dev/skills-implement) does not reliably close or check off the card when it finishes, so the card's state is yours to update once the work lands.

## It's working if

- Every task has an answer to "what can I demo when this is done?" — and the answer is behaviour, not a layer.
- The list comes back to you numbered, with a "Blocked by" line on each, before anything is published.
- The task at the top has no blockers and can be started immediately.
- Nothing in a task body is a file path or a line number, except a snippet a prototype produced.
- Each task reads like something a fresh session could finish without you in the room.
- Prefactoring, where it found any, is at the front of the order rather than mixed into feature tasks.
- Each card lands in `triage` and declares its blockers in `parents=[...]`, so the board — not prose — owns the dependency graph.

## Where it fits

`to-tasks` is a step in the main build chain:

```txt
grill-with-docs → to-spec → to-tasks → implement → code-review
```

Upstream is [to-spec](https://aihero.dev/skills-to-spec), which hands it a settled spec to slice against — keep both in one unbroken context window. Downstream is [implement](https://aihero.dev/skills-implement), which builds one task per fresh session, driving [tdd](https://aihero.dev/skills-tdd) for the tests and closing with [code-review](https://aihero.dev/skills-code-review). When you're unsure which skill or flow fits, [ask-matt](https://aihero.dev/skills-ask-matt) routes you.
