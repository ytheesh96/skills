---
name: wayfinder
description: Use when a large, foggy plan needs a durable Kanban map.
version: 3.0.0
author: Matt Pocock; adapted for Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [planning, decisions, wayfinder, kanban]
    related_skills: [loop-triage, kanban-orchestrator]
---

# Wayfinder

A loose idea has arrived—too large for one agent session, with no clear route
to the **destination**. Wayfinding finds that route instead of charging at the
destination. It charts one durable **shared map** in Hermes Kanban, then works
its decision tasks until nothing important remains undecided.

## Plan, don't do

Wayfinder is planning by default. A task resolves a question; it is not a slice
of the eventual build. The map is done when another session can implement the
result without guessing. Production changes are never part of the current
Wayfinding phase unless the user explicitly starts a later implementation
workflow after the map closes.

The foreground owns the destination, human choices, topology, acceptance, and
closure. Workers gather evidence, prototype, or perform a prerequisite; they do
not choose for the user or create follow-up work.

## Current durable-flow contract

- `delegate_task` is for ephemeral single or parallel subagents. It has no
  durable `mode="loop"` or `mode="durable"` contract.
- Durable maps use `kanban_create`, `kanban_link`, `kanban_list`, `kanban_show`,
  `kanban_comment`, `kanban_block`, `kanban_unblock`, and `kanban_complete`.
- Use one explicit board for the whole map. Resolve the board from the target
  environment or user request; never assume a local board name. Pass it on
  every Kanban call.
- Give the map a stable `tenant` slug and reuse it on every task. The tenant is
  the map namespace; dependency edges define execution order.
- A foreground `kanban_create` result must report `subscribed: true` before you
  promise that completion or blocking will re-enter the current chat. If it is
  false, the task is still durable, but inspect it manually instead of claiming
  automatic return.

## The map

The canonical map is one tenant-scoped Kanban dependency graph plus one blocked
**map closeout** task. Do not duplicate it in a session todo list or a second
planning document.

| Wayfinder concept | Hermes representation |
|---|---|
| Map | One explicit board + tenant-scoped task graph |
| Map index/closeout | A blocked Kanban task containing Destination, Notes, fog, and scope |
| Ticket | One bounded Kanban task |
| Blocking | `parents=[...]` at creation; `kanban_link(parent_id, child_id)` for an existing pending task |
| Frontier | Dependency-satisfied `ready`/`running` tasks |
| Resolution | Worker summary/comments plus foreground acceptance |
| Human decision | Worker calls `kanban_block(kind="needs_input")`; foreground asks, comments the answer, then unblocks |

Put this low-resolution context in the map closeout task body:

```markdown
## Destination
<what the map is finding its way to>

## Notes
<constraints, named skills, board, tenant, and any execution override>

## Decisions so far
<initially empty; append accepted outcomes as concise task comments>

## Not yet specified
<in-scope fog that is not sharp enough to become a task>

## Out of scope
<work deliberately beyond this destination>
```

Completed task summaries are the detailed decision record. Keep the closeout as
an index: append only concise accepted decisions with `kanban_comment`, and put
the complete planning handoff in its final `kanban_complete` summary. In
user-facing narration, refer to tasks by title rather than bare IDs.

Do not make the blocked closeout task a parent of executable research or
decision tasks; that would gate the entire map forever. Instead, make the
current terminal decision/synthesis tasks parents of the closeout. As new final
leaves become precise, link them into the closeout while it is still blocked.

## Task types

Each task contains one question, enough context to work independently, its exit
criterion, and any real dependencies.

- **Research** (AFK): inspect code, documentation, APIs, or other evidence that
  can settle a factual uncertainty.
- **Prototype** (AFK then HITL): create the smallest disposable artifact that
  makes a behavior or appearance choice concrete; the user reacts in the
  foreground.
- **Decision / grilling** (HITL): gather viable options and consequences. If a
  human preference remains, block with one grounded question instead of
  answering for the user.
- **Task** (AFK or HITL): perform manual work required before a decision can be
  made. It may unblock the route, but must not quietly deliver the destination.

One worker session resolves one task. Independent Research tasks may run in
parallel; `parents` control the rest.

## Fog of war

The map is deliberately incomplete.

- Create a task when its question is precise now, even if it has parents.
- Keep it under **Not yet specified** when the question itself is still fuzzy.
- Put it under **Out of scope** when it lies beyond the destination.

Resolving a task may clear more fog. The foreground—not a worker—adds newly
sharp tasks and wires their dependencies. Never create vague tasks merely to
make the map look complete.

## Invocation

### Chart the map

Use this mode when the user invokes `/wayfinder` with a loose idea.

1. **Name the destination.** Inspect retrievable facts first, then ask the user
   only for choices that evidence cannot answer.
2. **Map breadth-first.** Surface the open decisions, first answerable questions,
   fog, and out-of-scope boundary. If the whole route fits one foreground
   session and no fog remains, do not create a durable map; explain that the map
   is unnecessary and handle the bounded request directly when authorized.
3. **Fix routing before creation.** Resolve the explicit board, one stable tenant
   slug, and real configured assignee profiles. Choose a profile for each lane
   only after discovering that it exists; never assume names from another
   installation.
4. **Create the first sharp generation.** Call `kanban_create` once per task.
   Independent calls may be issued in parallel. Create parents first, capture
   their returned task IDs, then create each dependent with those IDs in
   `parents`. Never create a dependency child as an independent ready task and
   hope to link it before the dispatcher claims it.
5. **Create the blocked closeout.** Give it the same board and tenant, put the
   low-resolution map context in its body, set `initial_status="blocked"`, and
   set its `parents` to the current terminal decision/synthesis leaves.
6. **Verify the durable write.** For every result, check task ID, explicit board,
   status, and `subscribed`. Use `kanban_show` on the closeout and at least one
   executable task to verify bodies and parent edges.
7. **Stop.** Charting may launch bounded evidence tasks; it does not hand-resolve
   them or begin production implementation.

Current-tool example (one call per task):

```python
research = kanban_create(
    title="Establish the current system boundary",
    assignee="<verified-profile>",
    body=(
        "Type: Research. Question: what is the current supported boundary? "
        "Return sourced constraints and unresolved uncertainty; do not implement."
    ),
    board="<explicit-board>",
    tenant="wayfinder-<stable-slug>",
    workspace_kind="scratch",
)

choice = kanban_create(
    title="Choose the supported boundary",
    assignee="<verified-profile>",
    body=(
        "Type: Decision. Read the parent handoff, compare viable options and "
        "consequences, and block with one exact question if user preference remains."
    ),
    parents=[research["task_id"]],
    board="<explicit-board>",
    tenant="wayfinder-<stable-slug>",
    workspace_kind="scratch",
)

closeout = kanban_create(
    title="Accept the Wayfinder planning handoff",
    assignee="<verified-profile>",
    body="<Destination / Notes / Decisions / Not yet specified / Out of scope>",
    parents=[choice["task_id"]],
    board="<explicit-board>",
    tenant="wayfinder-<stable-slug>",
    initial_status="blocked",
    workspace_kind="scratch",
)
```

### Work through the map

Use this mode when Wayfinder is invoked with an existing map or when a subscribed
Kanban boundary re-enters the foreground.

1. **Orient to destination and frontier.** Call `kanban_list` with the map's
   explicit board and tenant, then `kanban_show` only for tasks whose full body,
   comments, or run evidence is needed.
2. **Review the returned boundary.** Accept sound evidence, request bounded
   rework, or take a blocked human decision to the user. Do not let a worker
   decide taste, risk, priority, or irreversible trade-offs.
3. **Expand only newly clear fog.** Create each new task with `kanban_create`,
   passing the resolved task IDs in `parents`. Use `kanban_link` only when both
   tasks already exist and the child is still safely pending/blocked. Never add
   a prerequisite to running or completed work; create a successor instead.
4. **Handle human decisions in the foreground.** Ask the worker's exact blocked
   question, record the user's answer with `kanban_comment`, then call
   `kanban_unblock`. Confirm the resumed task status.
5. **Maintain the closeout index.** Comment one-line accepted outcomes and link
   newly added terminal leaves into the blocked closeout.
6. **Close only when the map is genuinely complete.** `kanban_list` must show no
   unfinished in-scope task, no unresolved human decision, and no remaining
   in-scope fog. Then call `kanban_complete` on the blocked closeout with the
   implementation-ready planning handoff. Implementation is a separate Kanban
   workflow unless Notes explicitly authorized otherwise.

---

Adapted from [Matt Pocock's Wayfinder skill](https://github.com/mattpocock/skills/blob/main/skills/engineering/wayfinder/SKILL.md), © 2026 Matt Pocock, under the MIT License. See `references/UPSTREAM_LICENSE.md`.
