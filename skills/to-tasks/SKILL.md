---
name: to-tasks
description: Break a plan, spec, or the current conversation into a set of tracer-bullet tasks on Hermes Kanban, each declaring its blocking edges, published as board cards in dependency order.
disable-model-invocation: true
---

# To Tasks

Break a plan, spec, or conversation into a set of **tasks** — tracer-bullet vertical slices, each declaring the tasks that **block** it. The task tracker is Hermes Kanban; the board slug and tenant resolve from the per-repo Kanban config (see below).

## Process

### 1. Gather context

Work from whatever is already in the conversation context. If the user passes a reference (a spec path, an issue number or URL) as an argument, fetch it and read its full body and comments.

**Always pull the SPEC from the upstream `to-spec` handoff.** When this task is the
`to-tasks` sibling of a `to-spec` card (the usual case after a map's fog clears),
fetch the `SPEC.md` attached to the `to-spec` card and treat it as the **binding
source of truth** for the ticket breakdown — do not re-derive the contract from
scratch. If the spec is attached to the parent map/decision card instead, read it
there. Fall back to the repo path `.hermes/specs/<slug>/SPEC.md` only if no
attachment is found. The SPEC, not this card's body prose, defines scope and
acceptance criteria.

### 2. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current state of the code. Task titles and descriptions should use the project's domain glossary vocabulary, and respect ADRs in the area you're touching.

Look for opportunities to prefactor the code to make the implementation easier. "Make the change easy, then make the easy change."

### 3. Draft vertical slices

Break the work into **tracer bullet** tasks.

<vertical-slice-rules>

- Each slice cuts a narrow but COMPLETE path through every layer (schema, API, UI, tests) — vertical, NOT a horizontal slice of one layer
- A completed slice is demoable or verifiable on its own
- Each slice is sized to fit in a single fresh context window
- Any prefactoring should be done first

</vertical-slice-rules>

Give each task its **blocking edges** — the other tasks that must complete before it can start. A task with no blockers can start immediately.

**Wide refactors are the exception to vertical slicing.** A **wide refactor** is one mechanical change — rename a column, retype a shared symbol — whose **blast radius** fans across the whole codebase, so a single edit breaks thousands of call sites at once and no vertical slice can land green. Don't force it into a tracer bullet; sequence it as **expand–contract**. First expand: add the new form beside the old so nothing breaks. Then migrate the call sites over in batches sized by blast radius (per package, per directory), each batch its own task blocked by the expand, keeping CI green batch to batch because the old form still exists. Finally contract: delete the old form once no caller remains, in a task blocked by every migrate batch. When even the batches can't stay green alone, keep the sequence but let them share an integration branch that all block a final integrate-and-verify task — green is promised only there.

### 4. Quiz the user

Present the proposed breakdown as a numbered list. For each task, show:

- **Title**: short descriptive name
- **Blocked by**: which other tasks (if any) must complete first
- **What it delivers**: the end-to-end behaviour this task makes work

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the blocking edges correct — does each task only depend on tasks that genuinely gate it?
- Should any tasks be merged or split further?

Iterate until the user approves the breakdown. Do NOT publish until the user approves.

### 5. Resolve the board slug and tenant

The board slug and tenant are NOT hard-coded here. Resolve them from the per-repo Kanban config — the doc the `setup-matt-pocock-skills` skill wrote for this repository (it records the board slug, tenant convention, notifier/subscription expectation, and the triage-role → status mapping). If that config is missing, stop and tell the user to run the setup skill first.

### 6. Publish the approved tasks to Hermes Kanban

Publish one `kanban_create` per approved slice, in dependency order (blockers first). For each task:

- **Status**: land in `triage` — do NOT set `initial_status: running` and do NOT hard-code an assignee. The card parks in triage for human triage; the dispatcher promotes it to `ready` when its blockers clear. (This reconciles the upstream `ready-for-agent` label: the frontier is `ready` tasks whose parents are all done.)
- **Blocking edges**: pass the blocker task ids in `parents=[...]` so the board wires the dependency natively. A task with no blockers needs no `parents`.
- **Body**: use the task body template below — one `kanban_create` per task, never a combined card.

Work the **frontier**: any task whose blockers are all done. For a purely linear chain that means top to bottom.

Do NOT close or modify any parent issue.

After publishing, track each card with `kanban_show`. If a slice is waiting on a human decision, call `kanban_block(kind='needs_input')` rather than leaving it ambiguous. The `parents=[...]` array wires each card's dependencies natively, so a separate `kanban_link` call is not needed.

<task-body-template>

## What to build

The end-to-end behaviour this task makes work, from the user's perspective — not layer-by-layer implementation.

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2

## Blocked by

The titles of the tasks that gate this one (the edges live in `parents`), or "None — can start immediately".

</task-body-template>

In the body, avoid specific file paths or code snippets — they go stale fast. Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it and note briefly that it came from a prototype. Trim to the decision-rich parts — not a working demo, just the important bits.

## Attribution

`to-tasks` is adapted from Matt Pocock's upstream task-splitting skill (https://github.com/mattpocock/skills). Original work is MIT licensed; see `references/UPSTREAM_LICENSE.md`.
