---
name: wayfinder
description: Use when a large, foggy plan needs a durable Kanban map that is itself a first-class task, charted by the board's orchestrator across many runs.
version: 4.0.0
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
its decision and build tasks until nothing important remains undecided.

In v4 the map is **not** a separate index document or a blocked closeout task
that parents the work. The map *is* a Kanban task created at invocation, and the
board's orchestrator charts it across many runs by creating parent tasks of four
types. Fog clears generation by generation.

## Plan, don't do

Wayfinder is planning by default. A task resolves a question; it is not a slice
of the eventual build. The map is done when another session can implement the
result without guessing. Production changes are never part of the current
Wayfinding phase unless the human explicitly starts a later implementation
workflow after the map closes.

The human owns the destination, human choices, topology, acceptance, and
closure. Workers (orchestrator included) gather evidence, prototype, or perform
a prerequisite; they do not choose for the human or create follow-up work beyond
what the charting contract authorizes.

## Durable-flow contract

The durable map is one tenant-scoped Kanban dependency graph whose root is the
map task itself. Do not duplicate it in a session todo list or a second planning
document.

- Use one explicit **board** for the whole map. Resolve the board from the
  target environment or the human request; never assume a local board name. Pass
  it on every Kanban call.
- Give the map a stable **tenant** slug and reuse it on every task. The tenant is
  the map namespace; dependency edges define execution order.
- The canonical durable primitives are `kanban_create`, `kanban_list`,
  `kanban_show`, `kanban_block`, `kanban_unblock`, `kanban_link`, and
  `kanban_complete`. Wayfinder orchestrates these; the charting run uses
  `kanban_create` to lay down parents, `kanban_link` to wire parent edges,
  `kanban_block(kind="dependency")` to park the map between charting runs, and
  `kanban_complete` at fan-out. `kanban_unblock` clears a block when an edge is
  repaired post-hoc (e.g. a parent edge added to an already-blocked task).
- A foreground `kanban_create` result must report `subscribed: true` before you
  promise that completion or blocking will re-enter the current chat. If it is
  false, the task is still durable, but inspect it manually instead of claiming
  automatic return.

## The six contract points

1. **The map IS a Kanban task from invocation.** Filed `ready` with
   `skills=["wayfinder"]` and `assignee` set to the board's **current
   `orchestrator_profile`, resolved live at creation time**—never a hard-coded
   profile name. A map outlives any config moment; it re-charts over days, so a
   baked-in assignee goes stale. If the board's orchestrator profile is
   unreadable, fail closed and ask the human which profile should own charting;
   do not guess and do not fall back to a remembered name. The triage/decomposer
   path is bypassed for wayfinder maps—the attached skill is the charting brain.
2. **Charting runs.** The board's orchestrator picks up the map task, creates
   parent tasks of the four types (title prefix `[RESEARCH]` / `[PROTOTYPE]` /
   `[DECISION]` / `[OPERATION]` plus a `Type:` body line), links each as a
   PARENT of the map (the map waits via parent edges), then ends its run with
   `kanban_block(kind="dependency")`. When all parents complete, the map
   re-promotes to `ready`; the orchestrator re-charts the next generation or
   declares the fog cleared.
3. **No separate index—topology is the index.** The map body keeps only
   Destination / Notes / fog / out-of-scope. Per charting run: update the fog
   list; as parents complete, append one-line resolution `kanban_comment`s on
   the map (write-back-to-the-map, without index maintenance).
4. **Human-in-the-loop via assignee, never via block.** Tasks needing the
   installation's human operator live (grilling sessions, acceptances, real-world
   errands) are created with `assignee="<human-operator-handle>"` and a
   `Type: Decision` (or `Operation`) body line. Do NOT `kanban_block` to surface
   human work. The operator works them in the foreground via `/wayfinder
   <task-id>`. (Triage's `ready-for-human → blocked(kind=capability)` stays
   scoped to incoming triage work—"needs a human" ≠ "needs the operator live".)
5. **Skill attaches.** `wayfinder` on the map; `prototype` on `[PROTOTYPE]`
   tasks; decision/grilling tasks carry the `Type:` line instead of an attach
   (inert on undispatchable tasks anyway).
6. **Completion fan-out.** When the fog is cleared, the final charting run
   creates `to-spec` and `to-tasks` as CHILD tasks of the map with
   `skills=["to-spec"]` / `skills=["to-tasks"]` attached, BOTH
   `assignee="<human-operator-handle>"` (HITL spec draft + quiz), then
   `kanban_complete`s the map with the planning handoff.

## Task types and titles

Each parent task the orchestrator creates carries one question, enough context
to work independently, its exit criterion, and any real dependencies. Use the
title prefix and a `Type:` body line so the topology is self-describing:

- **`[RESEARCH]` / `Type: Research`** (AFK): inspect code, docs, APIs, or other
  evidence that can settle a factual uncertainty.
- **`[PROTOTYPE]` / `Type: Prototype`** (AFK then HITL): the smallest disposable
  artifact that makes a behavior or appearance choice concrete; the human reacts
  in the foreground. Attach `prototype`.
- **`[DECISION]` / `Type: Decision`** (HITL): gather viable options and
  consequences. If a human preference remains, create a task assigned to the
  operator with the exact question rather than answering for them.
- **`[OPERATION]` / `Type: Operation`** (AFK or HITL): perform manual work
  required before a decision can be made. It may unblock the route but must not
  quietly deliver the destination.

One worker session resolves one task. Independent Research tasks may run in
parallel; `parents` control the rest.

## Fog of war

The map is deliberately incomplete.

- Create a task when its question is precise now, even if it has parents.
- Keep it under the map's fog list when the question itself is still fuzzy.
- Put it under **Out of scope** when it lies beyond the destination.

Resolving a task may clear more fog. The foreground—not a worker—adds newly
sharp tasks and wires their dependencies. Never create vague tasks merely to
make the map look complete.

## Invocation modes

### Chart an existing map

Use this mode when an existing map task is in `ready`/`running` and the
orchestrator is picking it up to chart the next generation.

1. **Orient.** `kanban_show` the map; read Destination / Notes / fog /
   out-of-scope from the body (authoritative—not comments).
2. **Resolve the board and tenant live.** Take the board and tenant from the
   map task's own fields; never re-derive or assume them.
3. **Chart the next generation.** For each sharp question, `kanban_create` a
   parent task with the correct `[TYPE]` prefix and `Type:` body line, the same
   board and tenant, an explicit `workspace_kind` + `workspace_path` pinned to the
   repo worktree (see Pitfalls #2), and `parents=[map["task_id"]]`. Independent
   calls may be issued in parallel; capture returned IDs.
4. **Park the map.** End the run with `kanban_block(kind="dependency")` so the
   map waits on the new parents.
5. **Verify the durable write.** For every created task check task ID, resolved
   board, status, `subscribed`, and—critically—the **resolved workspace** (it may
   differ from what you asked for; check, don't assume). `kanban_show` the map to
   confirm parent edges.

Example (one call per task; resolve `orchestrator_profile` live for the map, and
pin every child's workspace explicitly):

```python
research = kanban_create(
    title="[RESEARCH] Establish the current system boundary",
    assignee="<verified-profile>",
    body=(
        "Type: Research. Question: what is the current supported boundary? "
        "Return sourced constraints and unresolved uncertainty; do not implement."
    ),
    parents=[map["task_id"]],
    board=map["board"],
    tenant=map["tenant"],
    workspace_kind="dir",
    workspace_path="<repo-worktree-path>",
)

choice = kanban_create(
    title="[DECISION] Choose the supported boundary",
    assignee="<verified-profile>",
    body=(
        "Type: Decision. Read the parent handoff, compare viable options and "
        "consequences; if user preference remains, create a task assigned to the "
        "human operator with one exact question."
    ),
    parents=[research["task_id"], map["task_id"]],
    board=map["board"],
    tenant=map["tenant"],
    workspace_kind="dir",
    workspace_path="<repo-worktree-path>",
)

# Park the map while parents run:
kanban_block(kind="dependency")
```

### Work the frontier

Use this mode when a worker (orchestrator or a dispatched profile) is resolving
one parent task, or when a subscribed Kanban boundary re-enters the foreground.

1. **Orient to destination and frontier.** `kanban_list` with the map's board and
   tenant, then `kanban_show` only for tasks whose full body, comments, or run
   evidence is needed.
2. **Review the returned boundary.** Accept sound evidence, request bounded
   rework, or take a blocked human decision to the operator. Do not let a worker
   decide taste, risk, priority, or irreversible trade-offs.
3. **Expand only newly clear fog.** Create each new task with `kanban_create`,
   passing resolved parent IDs in `parents`. Use `kanban_link` only when both
   tasks already exist and the child is still safely pending/blocked. Never add a
   prerequisite to running or completed work; create a successor instead.
4. **Write back to the map.** As parents complete, append one-line resolution
   `kanban_comment`s on the map and update its fog list; do not maintain a
   separate index.
5. **Re-promote or close.** When all parents of the map complete, the board
   re-promotes the map to `ready`; the orchestrator re-charts or, at the final
   run, fans out (see below).

### Adopt a human-assigned task via `/wayfinder <task-id>`

Use this mode when the human operator picks up a task the charting run assigned
to them (a `Type: Decision` grilling session or a `Type: Operation` errand).

1. **Open the task.** `/wayfinder <task-id>` loads the task body and its parent
   handoff. The operator works it in the foreground—no `kanban_block` was used to
   surface it.
2. **Resolve and record.** Perform the grilling session or errand, then record
   the outcome with `kanban_comment` on the task so the map's resolution log
   captures it.
3. **Complete the task.** `kanban_complete` the task with the concrete result.
   If the task was the last open parent of the map, the map re-promotes for its
   final charting run.

## Completion fan-out

When the fog is cleared (no unfinished in-scope task, no unresolved human
decision, no remaining in-scope fog), the final charting run:

1. Creates `to-spec` and `to-tasks` as **CHILD** tasks of the map with
   `skills=["to-spec"]` / `skills=["to-tasks"]` attached, BOTH
   `assignee="<human-operator-handle>"`.
2. `kanban_complete`s the map with the implementation-ready planning handoff.
   Implementation is a separate Kanban workflow unless Notes explicitly
   authorized otherwise.

## Pitfalls

**#1 — A hard-coded orchestrator assignee goes stale.** Baking a profile name
into the map card means a later config change leaves the map claimed by the old
profile. Always resolve the board's **current** `orchestrator_profile` at
creation time; fail closed and ask if it is unreadable. Never store a profile
name in the contract or the card.

**#2 — A `scratch` workspace can be auto-projected into an unrelated project.**
When the board has a default project, an implicit `workspace_kind="scratch"`
becomes a worktree under that project, stranding the charting worker far from
the repo. Always pass explicit `workspace_kind="dir"` + `workspace_path` on
wayfinder-created tasks, and **verify the created card's resolved workspace** in
the create response—it may differ from what you asked for. Check, don't assume.

**#3 — Comments are not durable across refile.** Duplicating or refiling a map
can drop its comment thread, so flaw logs and locked decisions that live only in
comments are lost. Keep the map's must-survive context (destination, contract
points, fog, flaw log) in the task **body**, not only in comments. Mirror live
entries as `kanban_comment`s if convenient, but treat the body as authoritative.

**#4 — Task deletion ≠ run termination.** Deleting a card does not kill its
run; an orphan run can keep going and even mint new cards. After deleting a card,
verify its run died and sweep the tenant for orphan-created cards before
proceeding.

**#5 — Map done-criteria must not exceed the charting profile's capability.** A
restricted orchestrator cannot run validators or symlink checks, so
tool-verified evidence cannot be a map-completion criterion. Map completion =
"fog charted + fan-out filed + flaw log recorded"; build evidence (e.g. validator
exit 0) gates the implementation/operation children's acceptance, not the map.

**#6 — Charting runs must resolve the map's board reliably.** Pin the board on
every call (env via the task/board variables, or an explicit `board=` argument)
so a spawned charting run never writes to the wrong board.

---

Adapted from [Matt Pocock's Wayfinder skill](https://github.com/mattpocock/skills/blob/main/skills/engineering/wayfinder/SKILL.md), © 2026 Matt Pocock, under the MIT License. See `references/UPSTREAM_LICENSE.md`.
