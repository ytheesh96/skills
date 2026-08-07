---
name: kanban-orchestrator
description: Decompose durable work into explicit Hermes Kanban tasks, dependencies, and review gates without doing worker-owned implementation.
version: 3.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [kanban, multi-agent, orchestration, routing, dependencies]
    related_skills: [kanban-worker, wayfinder, foreground-owned-loop-orchestration]
---

# Kanban Orchestrator

Use this skill when the current agent owns the foreground plan and must route
durable work through Hermes Kanban. The orchestrator decides scope, topology,
assignees, acceptance, and closure. Workers execute bounded tasks and return
evidence; they do not create their own follow-up graph.

## Durable contract

- Use one explicit `board` and one stable `tenant` for the whole graph. Pass
  `board` on every supported Kanban call and pass `tenant` wherever the tool
  accepts it; never depend on an implicit current-board choice.
- Create durable work with `kanban_create`. Use `parents` when creating a
  dependent task and `kanban_link` only for an existing pending task.
- Read state with `kanban_list` and `kanban_show`. Record evidence and routing
  decisions with `kanban_comment`.
- A worker uses `kanban_complete` for a verified handoff and `kanban_block` for
  a genuine dependency, human, capability, or transient blocker. The
  foreground handles the decision and calls `kanban_unblock` when appropriate.
- Do not replace durable graph work with an ephemeral `delegate_task`, and do
  not invent retired durable APIs or hidden loop modes.

## Decide whether to decompose

1. State the user-visible outcome and the authority boundary.
2. Inspect the repository, source, or existing task graph before asking for
   facts that are retrievable.
3. Keep a request in the foreground when one session can finish it without
   unresolved decisions, independent lanes, or durable handoff requirements.
4. Decompose when the work has independent evidence lanes, a human decision,
   a dependency chain, a long-running task, or a review boundary.
5. Freeze the acceptance contract before creating cards. Every card must have a
   bounded objective, an owner, inputs, an exit criterion, and its real
   authority limits.

Completion criterion: the choice to stay direct or create a durable graph is
explicit, and every graph task has a checkable reason to exist.

## Build the graph

Create the smallest useful graph in dependency order:

1. Create one root or synthesis task when the user needs a durable index.
2. Create independent research or execution tasks in parallel where safe.
3. Capture each returned task ID before creating its dependents. Put the IDs in
   `parents`; never create an unblocked child and race a later link.
4. Add a decision task when evidence must be compared or the user must choose.
   The card must contain the exact question, alternatives, criteria, and
   consequence of guessing wrong.
5. Add a review or closeout task only when it has real acceptance work. Keep a
   closeout blocked until its terminal evidence tasks finish, and do not make
   the closeout a parent of the work it is meant to summarize.
6. Use `idempotency_key` for retries of the same purpose. A retry must inspect
   the existing card before creating another one.

Completion criterion: every dependency edge is represented by `parents` or a
verified `kanban_link`, every task has the same board and tenant, and no
duplicate purpose card was created.

## Assignee and workspace routing

- Discover the profiles configured in the target environment before assigning
  work. Use profile names that actually exist; never bake a maintainer's local
  profile names into a public card or this skill.
- A card body must identify the authoritative repository, source, or workspace,
  the allowed actions, prohibited actions, and the evidence to return.
- Choose `scratch` for isolated evidence, `dir` only when a shared persistent
  directory is explicitly part of the contract, and `worktree` when the
  dispatcher has allocated a Git worktree. Record the chosen kind in the card.
- Do not force a skill that the target profile does not have. If specialized
  guidance is needed, put the relevant contract in the card body or verify the
  target profile first.

Completion criterion: each assignee, board, tenant, workspace kind, and forced
skill is either verified from the environment or intentionally left out.

## Dispatch and monitor

Creation is not proof of execution. After graph mutation:

1. Check the result for the task ID, explicit board, tenant, status, and any
   subscription/notification field returned by the runtime.
2. Call `kanban_show` on the root and at least one executable task to verify the
   stored body and parent edges.
3. Use `kanban_list` to inspect the dependency frontier. A `ready` row is not
   proof that a worker is running; require a fresh run/heartbeat when the
   runtime exposes those fields.
4. Treat `blocked` as a real gate. Ask the exact human question in the
   foreground, comment the answer on the task, call `kanban_unblock`, and
   verify the resumed state.
5. If a worker returns a partial result, route a narrowly scoped successor or
   rework card. Do not silently widen the original card or dispatch a duplicate.

Completion criterion: the durable graph has been read back after creation, and
any claim about progress is backed by current task/run evidence.

## Review and closeout

The foreground owns acceptance. A worker's summary is evidence, not approval.
Before closing a root or closeout task, verify:

- all in-scope children are terminal or have an explicit accepted exception;
- required tests, builds, source checks, and artifact paths are named and
  actually reported;
- no unresolved human question or capability gate is hidden in prose;
- follow-up work is either a linked task or explicitly out of scope; and
- the final summary is implementation-ready and names residual risk.

Use a proof-oriented comment for non-trivial work:

```python
kanban_comment(
    board=board,
    task_id=task_id,
    body=(
        "changed_files: <path>\n"
        "tests_run: <exact command>\n"
        "evidence: <result or artifact>\n"
        "residual_risks: <none or bounded risk>"
    ),
)
```

Then use `kanban_complete` only for a genuinely accepted handoff. If a human
or external gate remains, keep the task blocked and state exactly what would
unblock it.

## Minimal creation shape

```python
root = kanban_create(
    title="<bounded outcome>",
    assignee="<verified-profile>",
    body=(
        "Goal: <observable result>. "
        "Inputs: <source or parent evidence>. "
        "Acceptance: <exact checks and artifacts>. "
        "Limits: <actions this worker must not take>."
    ),
    board=board,
    tenant=tenant,
    workspace_kind="scratch",
    idempotency_key="<stable-purpose>",
)

child = kanban_create(
    title="<dependent outcome>",
    assignee="<verified-profile>",
    body="Read the parent handoff; return only the stated evidence.",
    parents=[root["task_id"]],
    board=board,
    tenant=tenant,
    workspace_kind="scratch",
)
```

The example is a shape, not a command to copy blindly. Resolve the actual
board, tenant, profile, workspace, and acceptance checks before calling it.
