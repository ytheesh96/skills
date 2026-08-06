---
name: kanban-worker
description: Detailed Hermes Kanban worker lifecycle, evidence handoffs, workspace safety, and blocker handling.
version: 3.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [kanban, multi-agent, collaboration, workflow, evidence]
    related_skills: [kanban-orchestrator]
---

# Kanban Worker

Use this skill when a durable Hermes Kanban task needs deeper worker guidance.
The dispatcher supplies the task identity and workspace; this skill keeps the
worker's execution bounded and makes the handoff verifiable.

## Orient before acting

1. Call `kanban_show` for the assigned task before reading unrelated files.
2. Read the task body, parent handoffs, comments, prior attempts, and acceptance
   criteria. Treat the body and durable comments as the source of truth.
3. Confirm the explicit `board`, stable `tenant`, workspace path, branch, and
   authority limits. Do not substitute an implicit board or a remembered path.
4. Inspect the repository and relevant source before changing anything. If the
   requested fact is retrievable, look it up instead of asking the foreground.

Completion criterion: the worker can state the exact deliverable, allowed
scope, verification command, and blocker boundary before making a mutation.

## Work in the allocated workspace

Use `$HERMES_KANBAN_WORKSPACE` as the working directory. Respect its kind:

- `scratch`: isolated temporary evidence or a disposable prototype;
- `dir`: shared persistent state; coordinate through comments and avoid racing
  other workers;
- `worktree`: an isolated Git checkout; keep branch and commit evidence clear.

Do not create a replacement checkout or install large dependency trees merely
because a workspace is inconvenient. If the dispatcher-provided workspace is
missing or invalid, comment the concrete setup failure and block rather than
improvising outside the assigned scope.

## Execute one bounded lane

- Implement only the task's stated outcome. Do not broaden it because a nearby
  improvement is tempting.
- Create no follow-up task and mutate no parent/child topology. The foreground
  owns `kanban_create`, `kanban_link`, graph expansion, reassignment, review
  routing, acceptance, and closure.
- Preserve the task's `board` on every Kanban operation and preserve its stable
  `tenant` wherever the operation accepts that scope, including task creation
  and list queries. Do not invent unsupported keyword arguments on comments,
  blockers, or completions.
- Keep secrets out of comments, summaries, logs, and artifacts. Redact tokens,
  private paths, and personal data before returning evidence.
- If a consequential product, API, scientific, architecture, or safety choice
  is unresolved, record the facts and alternatives, then use `kanban_block`
  with `kind="needs_input"`; do not implement against a guessed choice.

Completion criterion: every changed file and external side effect is within
the task body, and no graph mutation was delegated to the worker.

## Verify before handoff

Run the smallest meaningful checks first, then the repository's required gate.
Report exact commands and actual results. A useful coding handoff includes:

```python
kanban_complete(
    board=board,
    summary="<observable result and residual risk>",
    metadata={
        "changed_files": ["<path>"],
        "tests_run": ["<exact command>"],
        "tests_passed": ["<exact result>"],
        "artifacts": ["<verified path or URL>"],
        "decisions": ["<locked choice or none>"],
    },
)
```

Before completing, verify that every claimed artifact exists, every test result
is from this run, and the workspace status is understood. For work that still
needs a human or external review gate, add a durable proof comment containing
the changed files, commit/branch, exact tests, residual risks, and clean/dirty
status, then call `kanban_block` with the precise gate. Do not label an
unverified implementation complete.

Completion criterion: a downstream worker or foreground agent can reproduce
the reported result from the handoff without relying on chat history.

## Block and recover honestly

Use `kanban_block` only for a real blocker:

- `dependency`: another task's handoff is required;
- `needs_input`: a human choice or clarification is required;
- `capability`: credentials, access, or a tool is unavailable;
- `transient`: a bounded external failure may clear on retry.

Include the exact evidence, attempted commands, and the smallest unblock
instruction. Do not use a blocker as a review queue or as a substitute for
reporting partial work. If a transient retry is safe, retry once with a clear
diagnostic; otherwise preserve the evidence and stop.

## Tenant and notification boundaries

When `$HERMES_TENANT` is set, use that value consistently for the task's
Kanban operations and avoid writing unscoped durable memory. A successful card
creation or completion is not proof that the foreground is subscribed; report
the returned subscription/notification field rather than promising a chat ping.

## Compact handoff checklist

- [ ] `kanban_show` read the current task and parent context.
- [ ] Board, tenant, workspace, and authority limits are explicit.
- [ ] Only in-scope files and effects were changed.
- [ ] Focused tests/builds/checks ran and their real output is recorded.
- [ ] Artifacts and commits are verified, with no secrets exposed.
- [ ] Follow-up work is described for the foreground, not created here.
- [ ] `kanban_complete` or `kanban_block` uses the correct durable boundary.
