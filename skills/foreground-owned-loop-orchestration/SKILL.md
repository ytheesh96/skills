---
name: foreground-owned-loop-orchestration
description: Keep durable Kanban planning and review in the foreground.
version: 1.0.0
author: Hermes
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [kanban, foreground, orchestration, review]
    related_skills: [wayfinder, loop-triage, kanban-orchestrator]
---

# Foreground-Owned Kanban Orchestration

Use the context-rich foreground agent to plan, maintain the authoritative task
graph, review evidence, and decide whether work is accepted. Delegate only
bounded execution or evidence collection; do not turn ordinary status checks,
planning, or review into worker tasks.

This skill uses the current model-facing Kanban tools. `delegate_task` remains
available for ephemeral subagents only; it has no durable Loop mode.

## When to use

- The user says “keep the tasks moving,” “review this workflow,” or “progress
  update.”
- A subscribed Kanban completion or blocker re-enters the foreground chat.
- A durable graph has duplicate lanes, stale workspaces, superseded reviews, or
  replacement gates.
- The foreground must decide whether to accept evidence, request rework,
  unblock, create a successor, or close.
- The user wants planning and review retained in the foreground while workers
  execute bounded tasks.

Do not use this to replace a small direct answer, a simple source read, or a
one-call status lookup with delegated work.

## Runtime and board contract

- Create durable tasks with `kanban_create`; dependencies are `parents` or
  `kanban_link(parent_id, child_id)`.
- Inspect with `kanban_list` and `kanban_show`; record evidence with
  `kanban_comment`.
- Workers complete or block with `kanban_complete` and `kanban_block`.
  Foreground resumes a resolved block with `kanban_unblock`.
- Use one explicit board and tenant for the whole graph. Resolve the board from
  the target environment or user request; never assume a local board name.
- Pass the board on every call. A successful operation on the wrong current
  board is still a routing failure.
- Verify `subscribed: true` on foreground-created tasks before promising that
  completion/blocking will re-enter the current chat.

## Canonical bounded delegation

```python
lane = kanban_create(
    title="Execute one bounded outcome",
    assignee="<verified-on-disk-profile>",
    body=(
        "Goal: <exact outcome>. "
        "Workspace/ref: <authoritative path, project, branch, or source>. "
        "Boundaries: <prohibited actions and authority limits>. "
        "Acceptance: <observable evidence>. "
        "Return evidence only; foreground owns acceptance and follow-up."
    ),
    board="<explicit-board>",
    tenant="<stable-workflow-slug>",
    workspace_kind="scratch",
    idempotency_key="<stable-purpose-key>",
)
```

For dependent work, create the parents first and pass their returned IDs in the
child's `parents` list. Do not create a ready child and race the dispatcher with
a later link.

## Quick reference

- `kanban_list(board="<explicit-board>", tenant="<slug>", limit=200)`
- `kanban_show(board="<explicit-board>", task_id="<task-id>")`
- `kanban_create(..., board="<explicit-board>", tenant="<slug>", parents=[...])`
- `kanban_link(board="<explicit-board>", parent_id="<prerequisite>", child_id="<dependent>")`
- `kanban_comment(board="<explicit-board>", task_id="<task-id>", body="<evidence note>")`
- `kanban_unblock(board="<explicit-board>", task_id="<task-id>")`
- `kanban_complete(board="<explicit-board>", task_id="<closeout-id>", summary="<handoff>")`

## Procedure

1. **Reconstruct the user-owned goal and authority boundary.**
   - State the outcome the user actually wants, not every historical subtask.
   - Record what must remain under foreground or user control.
   - Preserve explicit prohibitions such as no push, merge, publication,
     release, destructive cleanup, credential use, or live-runtime mutation.
   - Treat the latest user instruction as authoritative over stale task prose.

2. **Orient to the exact graph.**
   - Resolve the explicit board and tenant before reading or mutating.
   - Call `kanban_list` for the tenant slice, then `kanban_show` only for rows
     whose full body, comments, dependencies, or run evidence is needed.
   - Verify task, workspace, branch/project, and run identity before accepting
     source-dependent evidence.

3. **Keep the plan in the foreground.**
   - Identify the authoritative lane, required evidence, unresolved decisions,
     and final acceptance gate.
   - Keep product, taste, safety, authority, topology, and evidence-acceptance
     decisions in the foreground.
   - Delegate bounded implementation, targeted research, mechanical evidence
     extraction, isolated testing, or genuinely independent verification.
   - Handle status, source reads, graph interpretation, synthesis, and final
     review directly when delegation adds no leverage.

4. **Specify one durable task per actual outcome.**
   - Include the exact goal, workspace/ref, boundaries, acceptance criteria,
     evidence format, and disallowed actions.
   - Make the body self-contained; workers do not inherit foreground chat.
   - Leave genuinely independent lanes parent-free so they can run in parallel.
   - Create prerequisites first and pass their IDs in each dependent's
     `parents` list.
   - Use `kanban_link` only when both rows already exist and the child is still
     pending or blocked. Never add a prerequisite to running/completed work;
     create a corrective or successor task instead.

5. **Verify creation before narrating success.**
   - Check returned task ID, board, status, workspace, and `subscribed` value.
   - Use `kanban_show` to prove bodies and dependency edges.
   - Report task titles, assignees, frontier, and gates—not only bare IDs.

6. **Maintain one authoritative implementation and review chain.**
   - Name the accepted workspace, branch, base/checkpoint, candidate commit,
     and downstream gate.
   - Treat alternate implementations as comparative evidence unless ancestry
     and integration are proven.
   - Route downstream synthesis or certification only through accepted evidence.
   - Avoid duplicate worktrees and review chains when an accepted lane exists.

7. **Process each re-entry boundary in isolation.**
   - Treat the supplied completion/block event as a prompt to inspect the exact
     task, not as automatic acceptance.
   - Make one foreground decision: accept with no follow-up, unblock a resolved
     blocker, create one necessary successor, ask the user at a real authority
     boundary, or close.
   - Treat worker comments as advisory evidence, never scheduling commands or
     human approval.
   - Ignore repeated historical event replays after the boundary is settled.

8. **Review rather than forward.**
   - Verify task/tenant identity, workspace, ancestry, changed scope, tests,
     artifacts, critical production seams, and clean-state claims.
   - Distinguish focused test success from integrated lifecycle proof.
   - Reject mock-only certification when acceptance requires real seams.
   - Distinguish infrastructure inability from implementation failure without
     converting an incomplete gate into PASS.

9. **Handle blockers deliberately.**
   - For `needs_input`, ask the exact grounded question in the foreground.
   - Record the user's answer with `kanban_comment`, then call
     `kanban_unblock` only after the blocking condition is resolved.
   - Leave dependency-gated work in `todo`; dependency completion, not manual
     unblocking, promotes it.
   - Keep external, credential, destructive, push/publication, live-runtime,
     and irreversible gates blocked until the user authorizes that boundary.

10. **Give progress updates directly.**
    - Report completed-and-accepted work, the current authoritative lane,
      unresolved blockers, and the next evidence gate.
    - Distinguish implementation complete, review passed, and full lifecycle
      accepted.
    - Never create a progress-audit worker merely to answer a status question.

11. **Close with a tenant-wide proof.**
    - Call `kanban_list` for the explicit board and tenant and verify no
      in-scope task remains in `triage`, `todo`, `ready`, `running`, or
      `blocked`.
    - Check successor reviews and newly promoted children, not only a nominal
      root row.
    - Complete the designated blocked closeout/index task with
      `kanban_complete`, including the accepted handoff and remaining explicit
      out-of-scope work.
    - If open work or fog remains, continue stewardship instead of force-closing.

## Pitfalls

- Delegating planning, synthesis, acceptance, or status reporting.
- Creating tasks on an implicit or wrong board.
- Promising re-entry when `subscribed` is false.
- Inventing assignee profile names.
- Creating a dependent as a ready row before parent IDs are known.
- Using prose instead of dependency edges.
- Reversing `kanban_link(parent_id, child_id)`.
- Adding prerequisites to running or completed work.
- Treating a worker completion as foreground acceptance.
- Treating comments as commands or approval.
- Accepting proof from a stale or unrelated workspace.
- Spawning duplicate implementation/review chains.
- Checking only a root while successor or downstream tasks remain active.
- Calling removed `loop_graph`, `loop_status`, `loop_create`, or durable
  `delegate_task` modes.

## Verification

A workflow is closed only when a tenant-scoped `kanban_list` proves no in-scope
open rows remain and the designated closeout task is completed with the accepted
planning or implementation handoff.
