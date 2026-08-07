---
name: triage
description: Move cards through a state machine of triage roles on the project's Hermes Kanban board — categorise, verify, grill if needed, and write agent-ready briefs.
disable-model-invocation: true
---

# Triage

Move cards on the project's Hermes Kanban board through a small state machine of triage roles. The board **is** the issue tracker — every open issue is a card, and the triage roles below map directly onto the board's statuses.

Every comment posted to a card while it is being actively triaged **must** start with the `[TRIAGE]` prefix:

```
[TRIAGE] <your comment>
```

The prefix is required for every comment during the triage phase (while the card sits in `triage`, or while you are resolving a `blocked` state). Drop the prefix only once the card has left triage and moved into `ready` / `archived` / `blocked(kind=capability)` with no further triage questions open.

## Reference docs

- [AGENT-BRIEF.md](AGENT-BRIEF.md) — how to write durable agent briefs
- [OUT-OF-SCOPE.md](OUT-OF-SCOPE.md) — how the `.out-of-scope/` knowledge base works
- `docs/agents/issue-tracker.md` — the per-repo config: board slug, tenant, notifier, and the authoritative triage-role → status mapping table. Run `/setup-matt-pocock-skills` if that doc is missing.

## Roles

Two **category** roles (recorded as a `Category:` body line on the card — see below):

- `bug` — something is broken
- `enhancement` — new feature or improvement

Five **state** roles, each mapping onto a Hermes Kanban status:

| Triage role       | Board status            | Meaning                                                              |
| ----------------- | ----------------------- | -------------------------------------------------------------------- |
| `needs-triage`    | `triage`                | Maintainer needs to evaluate.                                        |
| `needs-info`      | `blocked(kind=needs_input)` | Waiting on reporter for more information.                         |
| `ready-for-agent` | `ready`                 | Fully specified, ready for an AFK agent to pick up.                   |
| `ready-for-human` | `blocked(kind=capability)`  | Needs human implementation (judgment, external access, design).  |
| `wontfix`         | `archived`              | Will not be actioned.                                                |

`ready-for-human` maps to `blocked(kind=capability)`, **not** `blocked(kind=needs_input)` — it means the work is understood but requires a human, not that it is waiting on a question. A `blocked(kind=needs_input)` card is always the `needs-info` role.

Every triaged card should carry exactly one category role and one state role. The category role is recorded as a `Category: bug` or `Category: enhancement` line in the card body — never rely on it being implied. If state roles conflict, flag it and ask the maintainer before doing anything else.

These are canonical role names — the actual status strings used on the board are the Hermes Kanban ones in the table above. The mapping is authoritative in `docs/agents/issue-tracker.md`; run `/setup-matt-pocock-skills` if the config was never written.

State transitions: an unlabeled card normally goes to `triage` (`needs-triage`) first; from there it moves to `blocked(kind=needs_input)` (`needs-info`), `ready` (`ready-for-agent`), `blocked(kind=capability)` (`ready-for-human`), or `archived` (`wontfix`). `blocked(kind=needs_input)` returns to `triage` once the reporter replies. The maintainer can override at any time — flag transitions that look unusual and ask before proceeding.

## Invocation

The maintainer invokes `/triage` and describes what they want in natural language. Interpret the request and act. Examples:

- "Show me anything that needs my attention"
- "Let's look at #42" (a card)
- "Move #42 to ready"
- "What's ready for agents to pick up?"

## Show what needs attention

Query the board and present three buckets, oldest first:

1. **Unlabeled** — never triaged (no `Category:` line and still in `triage`).
2. **`triage`** — evaluation in progress.
3. **`blocked(kind=needs_input)` with reporter activity since the last triage notes** — needs re-evaluation.

Show counts and a one-line summary per item. Let the maintainer pick.

## Triage a specific card

1. **Gather context.** Read the full card (body, comments, current status, labels, author, dates). Parse any prior triage notes (prefixed `[TRIAGE]`) so you don't re-ask resolved questions. Explore the codebase using the project's domain glossary, respecting ADRs in the area. Run two checks against the codebase: (a) **redundancy** — search for an existing implementation of the requested behavior by domain concept (not just the request's wording), and report where you looked. If found, it's an already-implemented `archived` (`wontfix`, step 5). (b) **prior rejection** — read `.out-of-scope/*.md` and surface any that resembles this request.

2. **Recommend.** Tell the maintainer your category and state recommendation with reasoning, plus a brief codebase summary relevant to the request — including whether it's already implemented. Wait for direction. When you apply the category, write the `Category: bug` or `Category: enhancement` line into the card body.

3. **Verify the claim.** Before any grilling, check that the claim holds up. For a bug, reproduce it from the reporter's steps. Report what happened: confirmed (with code path), failed, or insufficient detail (a strong `blocked(kind=needs_input)` signal). A confirmed verification makes a much stronger agent brief.

4. **Grill (if needed).** If the request needs fleshing out, run the `/grilling` and `/domain-modeling` skills together — grill it into shape a round of questions at a time, sharpening domain terms and updating `CONTEXT.md`/ADRs inline as decisions land. Keep every question in a `[TRIAGE]`-prefixed comment.

5. **Apply the outcome:**
   - `ready` (`ready-for-agent`) — post an agent brief comment ([AGENT-BRIEF.md](AGENT-BRIEF.md)).
   - `blocked(kind=capability)` (`ready-for-human`) — same structure as an agent brief, but note why it can't be delegated (judgment calls, external access, design decisions, manual testing).
   - `blocked(kind=needs_input)` (`needs-info`) — post triage notes (template below) as a `[TRIAGE]` comment.
   - `archived` (`wontfix`) — archive, with the comment depending on *why*:
     - **Already implemented** — the change already exists in the codebase. Point to where it lives; do **not** write to `.out-of-scope/` (that KB is for *rejected* requests, not built ones).
     - **Rejected (bug)** — polite explanation, then archive.
     - **Rejected (enhancement)** — write to `.out-of-scope/`, link to it from a comment, then archive ([OUT-OF-SCOPE.md](OUT-OF-SCOPE.md)).
   - `triage` (`needs-triage`) — apply the role. Optional `[TRIAGE]` comment if there's partial progress.

## Quick state override

If the maintainer says "move #42 to ready", trust them and apply the status directly. Confirm what you're about to do (status change, comment, archive), then act. Skip grilling. If moving to `ready` without a grilling session, ask whether they want to write an agent brief.

## Needs-info template

```markdown
## Triage Notes

**What we've established so far:**

- point 1
- point 2

**What we still need from you (@reporter):**

- question 1
- question 2
```

Capture everything resolved during grilling under "established so far" so the work isn't lost. Questions must be specific and actionable, not "please provide more info". Post this as a `[TRIAGE]`-prefixed comment when the card is in `blocked(kind=needs_input)`.

## Resuming a previous session

If prior `[TRIAGE]` notes exist on the card, read them, check whether the reporter has answered any outstanding questions, and present an updated picture before continuing. Don't re-ask resolved questions.
