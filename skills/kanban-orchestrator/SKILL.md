---
name: kanban-orchestrator
description: Decomposition playbook + anti-temptation rules for an orchestrator profile routing work through Kanban. The "don't do the work yourself" rule and the basic lifecycle are auto-injected into every kanban worker's system prompt; this skill is the deeper playbook when you're specifically playing the orchestrator role.
version: 3.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [kanban, multi-agent, orchestration, routing]
    related_skills: [kanban-worker]
---

# Kanban Orchestrator — Decomposition Playbook

## Durable operation contract

Every `kanban_create`, `kanban_link`, `kanban_list`, `kanban_show`,
`kanban_block`, and `kanban_unblock` call carries one explicit `board` and
stable `tenant`. Create each task once, attach `parents` at creation (or link
afterward), and keep graph changes, follow-ups, acceptance, and closure in the
foreground.

## Vaitheesh Loop branding note

For Vaitheesh-facing product language, call the foreground planning/graph UX **Loop** or **Loops**, not Work Map. Use Work Map only when quoting historical task/card titles, legacy code, or explicit internal artifacts.

For Vaitheesh-facing Loop UI, keep rows compact and avoid exposing internal graph-state labels as user-facing card badges. A Loop row badge should show the underlying task lifecycle status (for example `triage`, `ready`, `blocked`), not projection labels like `active` or `frontier`. Raw graph JSON belongs behind debug/export affordances, not in normal chat or card rows. See `references/loop-desktop-ui-preferences.md` for the concrete Desktop panel pitfall and verification pattern.

> The **core worker lifecycle** (including the `kanban_create` fan-out pattern and the "decompose, don't execute" rule) is auto-injected into every kanban process via the `KANBAN_GUIDANCE` system-prompt block. This skill is the deeper playbook when you're an orchestrator profile whose whole job is routing.

## Profiles are user-configured — not a fixed roster

Hermes setups vary widely. Some users run a single profile that does everything; some run a small fleet (`docker-worker`, `cron-worker`); some run a curated specialist team they've named themselves. There is **no default specialist roster** — the orchestrator skill does not know what profiles exist on this machine.

Before fanning out, you must ground the decomposition in the profiles that actually exist. The dispatcher silently fails to spawn unknown assignee names — it doesn't autocorrect, doesn't suggest, doesn't fall back. So a card assigned to `researcher` on a setup that only has `docker-worker` just sits in `ready` forever.

**Step 0: discover available profiles before planning.**

Use one of these:

- `hermes profile list` — prints the table of profiles configured on this machine. Run it through your terminal tool if you have one; otherwise ask the user.
- `kanban_list(assignee="<some-name>")` — sanity-check a single name. Returns an empty list (rather than an error) for an unknown assignee, so this only confirms a name you're already considering.
- **Just ask the user.** "What profiles do you have set up?" is a fine first turn when the goal needs more than one specialist.

Cache the result in your working memory for the rest of the conversation. Re-asking every turn wastes a tool call.

## When to use the board (vs. just doing the work)

Create Kanban tasks when any of these are true:

1. **Multiple specialists are needed.** Research + analysis + writing is three profiles.
2. **The work should survive a crash or restart.** Long-running, recurring, or important.
3. **The user might want to interject.** Human-in-the-loop at any step.
4. **Multiple subtasks can run in parallel.** Fan-out for speed.
5. **Review / iteration is expected.** A reviewer profile loops on drafter output.
6. **The audit trail matters.** Board rows persist in SQLite forever.
7. **The work contains a consequential uncertain choice.** Product/API/market/scientific/architecture choices should use `loop-epistemic-workflows`: create durable option-research cards, an adversarial-review card, and an adjudication card with confidence/evidence instead of letting one worker make a hidden decision.

If *none* of those apply — it's a small one-shot reasoning task — use `delegate_task` instead or answer the user directly.

## The anti-temptation rules

Your job description says "route, don't execute." The rules that enforce that:

- **Do not execute the work yourself.** Your restricted toolset usually doesn't even include terminal/file/code/web for implementation. If you find yourself "just fixing this quickly" — stop and create a task for the right specialist.
- **For any concrete task, create a Kanban task and assign it.** Every single time.
- **Split multi-lane requests before creating cards.** A user prompt can contain several independent workstreams. Extract those lanes first, then create one card per lane instead of bundling unrelated work into a single implementer card.
- **Run independent lanes in parallel.** If two cards do not need each other's output, leave them unlinked so the dispatcher can fan them out. Link only true data dependencies.
- **Never create dependent work as independent ready cards.** If a card must wait for another card, pass `parents=[...]` in the original `kanban_create` call. Do not create it first and link it later, and do not rely on prose like "wait for T1" inside the body.
- **If no specialist fits the available profiles, ask the user which profile to create or which existing profile to use.** Do not invent profile names; the dispatcher will silently drop unknown assignees.
- **Decompose, route, and summarize — that's the whole job.**

## Decomposition playbook

### Step 1 — Understand the goal

Ask clarifying questions if the goal is ambiguous. Cheap to ask; expensive to spawn the wrong fleet.

### Step 2 — Sketch the task graph

Before creating anything, draft the graph out loud (in your response to the user). Treat every concrete workstream as a candidate card:

1. Extract the lanes from the request.
2. Map each lane to one of the profiles you discovered in Step 0. If a lane doesn't fit any existing profile, ask the user which to use or create.
3. Decide whether each lane is independent or gated by another lane.
4. Create independent lanes as parallel cards with no parent links.
5. Create synthesis/review/integration cards with parent links to the lanes they depend on. A child created with unfinished parents starts in `todo`; the dispatcher promotes it to `ready` only after every parent is done.

Examples of prompts that should fan out (using placeholder profile names — substitute whatever exists on the user's setup):

- "Build an app" → one card to a design-oriented profile for product/UI direction, one or two cards to engineering profiles for implementation, plus a later integration/review card if the user has a reviewer profile.
- "Fix blockers and check model variants" → one implementation card for the blocker fixes plus one discovery/research card for config/source verification. A final reviewer card can depend on both.
- "Research docs and implement" → a docs-research card can run in parallel with a codebase-discovery card; implementation waits only if it truly needs those findings.
- "Analyze this screenshot and find the related code" → one card to a vision-capable profile for the visual analysis while another searches the codebase.

Words like "also," "finally," or "and" do not automatically imply a dependency. They often mean "make sure this is covered before reporting back." Only link tasks when one card cannot start until another card's output exists.

Show the graph to the user before creating cards. Let them correct it — including which actual profile name should own each lane.

### Step 3 — Create tasks and link

**Safe graph-building default when a live dispatcher is running:** create the whole graph in `triage` first, then link, then promote only the intended root/leaf-start cards. Parentless `todo` tasks may auto-promote to `ready` as soon as the dispatcher sees no unfinished parents, so creating parentless branch cards as normal `todo` can start workers before the dependency graph is wired. If the board has auto-decomposition enabled, switch the dashboard Orchestration pill to **Manual** or set `kanban.auto_decompose: false` before using `triage` parking; otherwise triage tasks may still be processed by the auto-decomposer.

CLI pattern:

```bash
# park everything safely
hermes kanban create "task A" --assignee worker-a --triage
hermes kanban create "task B" --assignee worker-b --triage
hermes kanban create "task C (depends on A+B)" --assignee writer --triage

# wire graph
hermes kanban link t_taskA t_taskC
hermes kanban link t_taskB t_taskC

# release only the actual starting roots
hermes kanban promote t_taskA t_taskB
```

After this, children stay non-runnable until their parents complete. If you are using API-level `kanban_create(parents=[...])` in an isolated/no-dispatch context, parent links at creation time are still fine; in an active board, prefer `--triage` graph construction to eliminate the race window.

Use the profile names from Step 0. The example below uses placeholders `<profile-A>`, `<profile-B>`, `<profile-C>` — replace them with what the user actually has.

```python
t1 = kanban_create(
    title="research: Postgres cost vs current",
    assignee="<profile-A>",  # whichever profile handles research on this setup
    body="Compare estimated infrastructure costs, migration costs, and ongoing ops costs over a 3-year window. Sources: AWS/GCP pricing, team time estimates, current Postgres bills from peers.",
    tenant=os.environ.get("HERMES_TENANT"),
)["task_id"]

t2 = kanban_create(
    title="research: Postgres performance vs current",
    assignee="<profile-A>",  # same profile, run in parallel
    body="Compare query latency, throughput, and scaling characteristics at our expected data volume (~500GB, 10k QPS peak). Sources: benchmark papers, public case studies, pgbench results if easy.",
)["task_id"]

t3 = kanban_create(
    title="synthesize migration recommendation",
    assignee="<profile-B>",  # whichever profile does synthesis/analysis
    body="Read the findings from T1 (cost) and T2 (performance). Produce a 1-page recommendation with explicit trade-offs and a go/no-go call.",
    parents=[t1, t2],
)["task_id"]

t4 = kanban_create(
    title="draft decision memo",
    assignee="<profile-C>",  # whichever profile drafts user-facing prose
    body="Turn the analyst's recommendation into a 2-page memo for the CTO. Match the tone of previous decision memos in the team's knowledge base.",
    parents=[t3],
)["task_id"]
```

`parents=[...]` gates promotion — children stay in `todo` until every parent reaches `done`, then auto-promote to `ready`. No manual coordination needed; the dispatcher and dependency engine handle it.

If the task graph has dependencies, create the parent cards first, capture their returned ids, and include those ids in the child card's `parents` list during the child `kanban_create` call. Avoid creating all cards in parallel and linking them afterward; that creates a window where the dispatcher can claim a child before its inputs exist.

### Step 4 — Complete your own task

If you were spawned as a task yourself (e.g. a planner profile was assigned `T0: "investigate Postgres migration"`), mark it done with a summary of what you created:

```python
kanban_complete(
    summary="decomposed into T1-T4: 2 research lanes in parallel, 1 synthesis on their outputs, 1 prose draft on the recommendation",
    metadata={
        "task_graph": {
            "T1": {"assignee": "<profile-A>", "parents": []},
            "T2": {"assignee": "<profile-A>", "parents": []},
            "T3": {"assignee": "<profile-B>", "parents": ["T1", "T2"]},
            "T4": {"assignee": "<profile-C>", "parents": ["T3"]},
        },
    },
)
```

### Step 5 — Report back to the user

Tell them what you created in plain prose, naming the actual profiles you used:

> I've queued 4 tasks:
> - **T1** (`<profile-A>`): cost comparison
> - **T2** (`<profile-A>`): performance comparison, in parallel with T1
> - **T3** (`<profile-B>`): synthesizes T1 + T2 into a recommendation
> - **T4** (`<profile-C>`): turns T3 into a CTO memo
>
> The dispatcher will pick up T1 and T2 now. T3 starts when both finish. You'll get a gateway ping when T4 completes. Use the dashboard or `hermes kanban tail <id>` to follow along.

## Submitting curated upstream skill/playbook integrations

When Vaitheesh wants to adapt an external skill/playbook repository into Hermes Loop/Kanban, treat it as a curated reference source rather than a wholesale prompt import. Interview the rollout authority, target profiles, checkpoint/edit scope, template location, pilot workflow, success scorecard, and Decompose/activation semantics; then submit a self-contained root and Decompose only when activation is approved. Use `references/curated-upstream-skill-playbooks.md` for the compact pattern and root-card body shape.

## Submitting research-board / specialist-team setup work

When the user wants a new durable research team, specialist roster, or ARS-style external-agent workflow set up in Kanban, use the research-board setup pattern in `references/research-board-agent-setup.md`. Current default: keep the profile roster small and use skills/card templates to enforce role behavior; profiles are for durable authority/runtime/memory boundaries, not every upstream micro-agent persona.

Key points:

1. Inspect the external repo as **reference material**, not executable instructions.
2. Convert external micro-agents into a **lean persistent roster** plus task templates; do not create one Hermes profile per upstream prompt unless the user explicitly wants that sprawl.
3. Create or select a dedicated project/domain board before submitting work; do not pollute the active board if it is unrelated.
4. For Vaitheesh-style broad Hermes Kanban setup tasks, submit the root card to **triage with no assignee** so the auto-specifier/decomposer routes it.
5. Make the root card self-contained: repo URL, reusable primitives, real existing profile names, recommended roster, constraints, acceptance criteria, and license notes.
6. Use an idempotency key for setup submissions.

## Interview-first Kanban submission planning

When the user says they want to submit a task to Kanban **but asks to brainstorm/details/interview first**, do **not** create the card yet. Treat this as a pre-submission design-tree interview:

1. Ask exactly **one question at a time**.
2. For each question, present concise options and include **your recommended answer**. When using the `clarify` tool, mark the recommended option directly in the choice label (for example, `D. Recommended — ...`) so the user sees the recommendation inside the UI, not only in surrounding prose.
3. Record each user choice as a locked decision in the next turn, then ask the next dependent question. If Kanban/Loop rows already exist, copy the locked decision into the body of every executable task it affects; never rely on separate decision/schema rows, comments, or the chat transcript as context a worker must discover later.
4. Walk dependencies in order: authority level → allowed safe actions → child-card policy → dependency shape → checkpoint scope/format → per-repo handling → final handoff → board/workspace.
5. Only submit the Kanban card after the user explicitly says to proceed/submit, or after the interview reaches the board/workspace decision and the user confirms.
6. If you accidentally submit too early and the user says cancel, archive the mistaken card immediately and verify it has no children/runs needing cleanup.

This pattern is especially important for broad cleanup/inventory tasks where a premature root card can spawn work before the user has resolved safety gates.

For broad worktree/repo cleanup inventories, use the detailed decision sequence in `references/worktree-cleanup-interview-tree.md`.

## Submitting repo goal files / plans to the board

When the user asks to "submit" a goal file, plan, or local artifact to Kanban:

1. **Do not assume the active board is the right board.** Check whether the current board matches the project/workstream. If it is unrelated, create or use a project-specific board instead of polluting the active board.
2. **Make the card self-contained.** If the source file is untracked, local-only, or may not exist in a fresh worktree, paste the relevant file content into the task body. Include the source path as context, but do not make the worker depend on that path existing.
3. **Discover and use real profiles.** Assign only to profiles that exist on disk, and prefer an orchestrator/planner profile for broad goal files that need decomposition.
4. **Use safe workspace metadata.** For repo implementation goals, set `workspace=worktree` and an explicit branch name so the dispatcher starts from an isolated workspace instead of the parent checkout.
5. **Use an idempotency key.** Goal/plan submissions are easy to double-submit from chat retries; include a stable key derived from the project + goal + date.
6. **Verify with `kanban show` or `kanban list`.** Confirm task id, board, status, assignee, workspace, and branch before reporting success.

Pitfall: a successful `kanban create` on the wrong current board is still a routing bug. Board choice is part of the task, not incidental CLI state.

### Adopting completed Kanban work into a live checkout

When a completed Kanban implementation has a reviewed local commit and the user wants to adopt it into a live/runtime checkout, do **not** jump straight to mutating `main` or restarting the app. Use an interview-first integration gate: authority boundary → base ref → isolated worktree → checkpoint → apply method → conflict policy → verification scope → smoke state → final live-adoption gate. Prefer a new sibling integration worktree from current local live `main`, a lightweight checkpoint with refs/bundle/patch/checksums, `git cherry-pick -x` for single-patch replay, focused verification, disposable `HERMES_HOME` smoke, and a clean handoff. Only mutate live `main` after explicit approval, and treat runtime restart/relaunch as a separate approval gate. See `references/live-checkout-adoption.md` for the command pattern, Desktop `NODE_ENV=test` pitfall, and smoke checklist.

### Orchestrating review-gated Kanban work from chat

When the user wants to orchestrate an existing review-gated workflow from the current chat, first interview the authority boundary and use board/code inspection for answerable facts. For a blocked task awaiting review, create an **independent ready review card** that references the blocked task and commit; do not set the blocked task as a formal parent, because that would gate the review until the task is already done. Use an idempotency key, bounded `dispatch --max 1`, and monitor through every continuation card the root/orchestrator creates.

### Session Work Maps and foreground handoff

When a foreground chat/session owns a Kanban-backed Work Map, do **not** treat cron/polling monitors as the product primitive for worker completion/block handoff. A cron monitor can be a temporary operations workaround, but the desired UX is native worker-to-foreground handoff that feels like worker-to-worker Kanban dependency handoff.

Use a `foreground_handoff` event model: worker complete/block writes a structured, durable, idempotent handoff event tied to `{work_map_root_id, session_id, owner_profile}`; Desktop/foreground consumes it into the Work Map Attention Queue; the foreground orchestrator runs `process_handoff` to resolve, create reviewer/fix follow-ups, or ask the user via `clarify` only when risk/preference/authority requires it. See `references/session-work-map-foreground-handoffs.md` for the event envelope, payload, risk flags, outcomes, idempotency keys, and UX rules.

For a low-cost temporary bridge before native foreground handoff exists, prefer an **event-triggered local watcher** over fixed-interval LLM polling: a launchd/FSEvents watcher runs a tiny SQLite detector on Kanban board DB changes, filters by tenant/root, persists event cursors/fingerprints, and wakes the foreground session only when new blocked/actionable work appears. Do not use `hermes chat --resume <session_id> -q ...` as a live-session wake; that starts a separate one-shot process rather than enqueueing into the open foreground runtime. See `references/event-triggered-foreground-block-watchers.md` for the launchd/watch-path pattern, SQL shape, and CLI-resume pitfall.

If native foreground handoff does not exist yet and the user needs loop closure now, prefer an **event-triggered local watcher** over a recurring LLM monitor: a LaunchAgent/path watcher wakes a tiny tenant-scoped SQLite detector on Kanban DB changes, the detector writes one wake line only for fresh blocked/actionable tasks, and a foreground/session bridge consumes that wake. Do **not** propose fixed-interval 3–5 minute agent/LLM polling for foreground blocked-task stewardship unless the user explicitly asks for it; it creates avoidable API cost and noise. Operational checklist: verify any existing LaunchAgent with `launchctl print`, verify the detector `--status` shows the intended board/tenant/cursor, smoke-test a harmless board-directory touch does not append a wake line, start/verify the Hermes-tracked `tail -F ...wake.log` bridge with a rare `KANBAN_BLOCKED_WAKE` watch pattern, then activate/dispatch work and let the watcher wake the session only on real blockers. See `references/event-triggered-kanban-block-watchers.md` for the launchd shape, detector queries, wake-log bridge, and verification checklist.

When the current foreground chat/session is itself the steward of a Kanban-backed Work Map, do **not** design the handoff as a fixed-interval LLM polling monitor. That is an operational workaround, not the product primitive. Worker completion/block should become a native foreground handoff: a durable, idempotent event addressed to the Work Map root/session/owner profile, consumed by foreground `process_handoff` into an Attention Queue. If native handoff is unavailable, use the event-triggered local watcher bridge in `references/event-triggered-foreground-block-watchers.md` so the detector stays cheap and only wakes the session when tasks actually become blocked. See `references/foreground-work-map-handoffs.md` for the event shape, `process_handoff` authority, and auto-review/fix-child defaults.

When building the Work Map during foreground planning/grill-me, keep first-layer branch parent tasks themselves blocked as `foreground planning hold — not ready to dispatch`; do not rely on a separate blocked planning-hold card or `todo + unassigned`. See `references/foreground-work-map-planning-holds.md` for the workaround, release checklist, and containment-vs-dependency pitfalls.

For lay-user Work Map flows, do **not** send every worker block/review card directly to the user. Treat the foreground session as a steward/triage layer: inspect the worker evidence, resolve or create follow-up work when the decision is safe and verifiable, and escalate via `clarify` with a recommended answer only for irreversible/external, credential/private-data, publish/push, live-runtime/config, ambiguous, or personal/product-taste decisions. See `references/foreground-work-map-stewardship.md` for the detailed Work Map/tool/UX pattern.

Conservative defaults:

- Do not record human approvals, force-close gates, or treat prose comments as high-risk/human approval.
- If the user says “keep the tasks moving” or similar after blocked/review handoffs, treat it as an active foreground-stewardship request: scan active statuses on the relevant board, identify safe mechanical blockers, add concise unblock reasons or route to the correct active lane, run `dispatch --dry-run --json` before real dispatch, then verify live task state/heartbeats after a short poll. Do not unblock external/irreversible gates such as push credentials or live-runtime approvals unless the user’s authorization specifically covers that boundary.
- For passive `review-required:` blockers where the implementation already left a durable proof packet, prefer converting them into active review work instead of unblocking the implementer or leaving them parked. Safe pattern: checkpoint the board DB first, add a foreground comment explaining the route, assign the task to the reviewer profile (for this setup usually `reviewer-qa`), move status to `review` with claim/run fields clear, dispatch dry-run then real dispatch, and verify the reviewer worker is running with fresh heartbeat. Keep true external gates (push credentials, live runtime restart, destructive cleanup, credentials/private data) blocked.
- If reviewer approval arrives, comment the verdict on the original card, unblock it, and dispatch the original assignee for normal closure.
- For `human-approval-required` gates, verify the gate operation's side effect on task status before assuming the original worker will resume. `record-human-approval` may complete the blocked card immediately (because the human decision is treated as the card result), so if the approval was only a precondition for live adoption/restart, either create a separate post-approval adoption card before recording the decision, or perform the approved adoption yourself and add an explicit completion comment with checkpoint/tests/restart evidence.
- If review requests changes, route narrow same-scope fixes back to the implementer; create a fix-child for risky/design/new-test-required work. For review-required cards that are blocked only because a reviewer found concrete same-scope issues, unblock the original implementer with the reviewer comment referenced so the worker can fix and return with fresh verification; do not leave the card parked after recording the request-changes comment.
- If root closure spawns integration → QA → closeout follow-ups, keep monitoring those follow-ups; a root marked `done` can mean “routed continuation,” not “all work accepted.”
- If a QA card requests changes, final closeout must wait on the post-fix re-review. A premature closeout should complete as “deferred” after creating the corrected continuation path, not produce final acceptance.
- After a remediation and its follow-up QA are accepted, sweep for stale `blocked` review-gate cards whose blocking condition is now satisfied. Verify the acceptance comment and downstream parent status with `kanban show`, then unblock the stale gate with an explicit reason so the original/root assignee can perform normal closeout instead of leaving the board falsely blocked.
- When post-fix QA/re-review cards were created after an earlier request-changes review, wire the **accepted follow-up** into every final/root gate that was waiting on the stale request-changes parent. Do not assume the original review card being `done` means acceptance; inspect `latest_summary`/metadata for accepted vs request-changes, then link the accepted follow-up QA into the publish/root gates before releasing closeout.
- If a blocked review card is accepted and unblocked, expect the original worker to perform a short closeout run before downstream QA can start. After unblocking review-required cards, run/let the dispatcher close them, then watch the next QA gate. If QA creates a request-changes follow-up, immediately link that follow-up (and any final re-review card it creates) as additional parents of the root/final gate before the root closes. If the root races into `running` before the new parent is linked or before re-review completes, reclaim it with an explicit foreground-steward reason and recheck parent links/statuses.
- When Vaitheesh says to keep a specific tenant/Loop moving, use the tenant-stewardship blocker-release pattern in `references/tenant-stewardship-blocker-release.md`: scope to tenant statuses, checkpoint the board DB, release stale blockers only after accepted fix/re-review evidence, route passive `review-required` cards into the active `reviewer-qa` lane, keep true external/live/push/credential gates blocked, and verify actual heartbeats because the gateway dispatcher may claim rows before your manual dispatch probe.
- When Vaitheesh says a grilled/submitted Loop row has been submitted or decomposed, immediately inspect the real root and tenant-scoped children before replying. Confirm root status, child ids, dependency links, entrypoint `ready/running` tasks, downstream `todo` gates, and whether a bounded dispatcher pass is needed. If dispatch exposes DB/index trouble, repair/verify the board before reporting progress; do not say “queued” from the chat transcript alone.
- For foreground-built graph/materializer work, do not add recovery escape hatches such as `append-graph --force` unless the user explicitly approved that semantic. The locked default is to refuse `running`, `done`, and `archived` roots; a force path is a separate product/safety design, not an implementation convenience.
- For final publish/root gates, distinguish “ready to push” from “complete.” If standing policy or card body requires the literal approval word `push`, release the gate only far enough for the orchestrator to block with a ready-for-push handoff; never force-complete the root or perform/promise the push without explicit authorization.
When the user asks “all tasks are done”, “X is done”, or asks “what next?”, verify every active lifecycle status (`triage`, `ready`, `running`, `review`, `blocked`, `todo`, `scheduled`) on each relevant board before agreeing. Also check root closeout cards, downstream dependency children that may have just auto-promoted, accepted follow-up QA/re-review cards that need to be linked into final gates, and any explicit monitoring/dashboard surfaces that were part of the work. If a completion triggered unintended downstream first-layer branch execution, reclaim/park those branch parents as foreground planning holds before proceeding. Report “no active work remains” only after these probes are clean.

When the user asks you to use the watcher/monitor to keep blocked tasks moving, treat that as an active foreground-stewardship request, not just infrastructure setup. Scope the watcher to the tenant/root, baseline it, start/verify the foreground wake bridge, then immediately inspect any currently blocked tenant tasks. For safe/verifiable blocks (for example `review-required` with concrete test/evidence output), verify evidence yourself, add an explicit foreground note, unblock, dispatch a bounded pass, and monitor until the task completes/blocks again or releases the next child. If a wake points at an already archived/done smoke row or other stale blocked-status fingerprint, record it as benign and keep stewarding active rows instead of treating it as a live blocker. Do not ask the user for mechanical review handoffs unless the next action crosses a real escalation boundary. See `references/event-triggered-kanban-block-watchers.md` for the detector/bridge and active steward loop.

When the user asks for a whole-job summary of a completed tenant or board slice, reconstruct the full job from the tenant task graph instead of summarizing only the root card: list all tenant tasks including archived test cards, verify every active status is empty, inspect implementation/review run metadata, follow request-changes → fix → re-review loops, and verify any produced branch/worktree or monitor/watcher current state before reporting. Use `references/completed-tenant-job-summary.md` for the closeout checklist and summary shape.

Detailed checklist and pitfalls: `references/review-gate-chat-orchestration.md`.

### Foreground Work Map handoffs

When a foreground/chat session owns a user-facing Work Map, treat worker completion/block as a native handoff back into the foreground orchestrator — not as a cron monitor or raw user-facing review card. The foreground orchestrator should consume structured handoff events, update the Work Map Attention Queue, auto-resolve low/medium verifiable issues, create reviewer/fix follow-ups when safe, and escalate only genuine user-judgment/risk decisions via `clarify` with a recommended answer. See `references/foreground-work-map-handoffs.md` for the event contract, `process_handoff` authority, design-tree Work Map model, outcome taxonomy, and publish-gate pattern.

### Integrating a QA-passed Kanban commit into live main

When a Kanban lane produces a reviewed local commit in an isolated worktree and the user asks whether/how to adopt it into the live Hermes checkout, do **not** jump straight to merging. Use the interview-first integration pattern in `references/verified-commit-live-main-integration.md`: establish authority boundary, integration base, worktree/checkpoint shape, cherry-pick provenance, conflict/failure policy, focused verification scope, disposable runtime-state smoke, final clean worktree handoff, and changelog update. Default to an isolated live-main integration worktree and stop before mutating live `main` or restarting runtime unless the user explicitly approves that next gate.

### Research/deep-research pilot validation gates

When a validation card claims a research workflow or deep-research skill setup passed because of a pilot question, verify that the pilot question was actually run. It is not enough that the validator read the source note, checked that skills/templates exist, or reused unrelated prior QA artifacts. The evidence must include artifacts for the selected question: source/evidence collection, claim/source verification or adversarial review, synthesis/adjudication, confidence/open questions, and a final answer/decision tied to that question. If those artifacts are missing, report the tooling/install gate separately from the incomplete pilot and create a focused follow-up pilot-validation card. See `references/research-pilot-validation-gate.md` for the checklist and false-positive pattern.

### Submitting post-completion E2E verification cards

When the user asks to “test end to end” after a root implementation card has completed, create a focused E2E/QA follow-up card rather than reopening the completed root or doing ad-hoc validation in chat. Good shape:

- Reference the completed root task id, title, and implementation commits/summaries so the verifier knows exactly what changed.
- Put the card in **triage with no assignee** unless the user named a profile; let the auto-specifier/decomposer route it.
- Use `workspace=dir:<repo>` when the task must validate the current shared checkout and commits as-is; use `worktree` only when isolated mutation is acceptable.
- Make the acceptance criteria explicitly E2E: real UI/Electron path if possible, nearest runnable surrogate only if the real path is blocked, exact commands/environment, artifacts/screenshots/logs when useful, cleanup steps, and PASS/finding handoff.
- Include coordination constraints: check Kanban/git status first, do not race active workers, avoid commits unless a verified fix is required, and redact secrets.
- Use an idempotency key derived from board/root-task/purpose/date to avoid duplicate QA submissions from chat retries.
- Verify the created card with `kanban show` before reporting the id/status/workspace back to the user.

### Submitting Hermes Desktop E2E validation cards

When submitting Kanban work to validate Hermes Desktop end-to-end behavior, make the card explicit about runtime roots. Include separate fields/instructions for:

- **Hermes backend/source root** (`HERMES_DESKTOP_HERMES_ROOT`): if the user wants their current runtime tested, tell the worker to resolve the active project from `hermes --version` / installed project path and verify it is a valid Hermes source root (for current Desktop, contains `hermes_cli/main.py`). Do not assume the board workspace is the Hermes backend root.
- **Desktop project cwd** (`HERMES_DESKTOP_CWD`): the repo opened in the Desktop UI, usually a disposable fixture repo for safe E2E tests.
- **Runtime state home** (`HERMES_HOME`): default to a disposable temp home for safety unless the user explicitly wants live `~/.hermes` sessions/config exercised.

This distinction matters for boards whose workspace is a development checkout, a partial repo, or a fixture: using that workspace as `HERMES_DESKTOP_HERMES_ROOT` can make a test miss the user's actual runtime while still launching a plausible Desktop app.

### Submitting dirty-workspace review / commit cards

When the user asks to submit a large dirty workspace to Kanban for review or commit, create a **review/commit card** rather than trying to clean or commit from the chat turn. Make the body operationally specific:
### Submitting dirty-workspace review / commit cards
### Submitting dirty-workspace review / commit cards

When the user asks to submit a large dirty workspace to Kanban for review or commit, create a **review/commit card** rather than trying to clean or commit from the chat turn. If the user asks to brainstorm/interview the cleanup plan first, use the **Interview-first Kanban submission planning** pattern above and do not create the card until they explicitly confirm. Make the body operationally specific:

- Name the repo/workspace path and use `workspace=dir:<absolute-repo-path>` when the reviewer must inspect the existing dirty checkout exactly as-is. Use `worktree` only when the work can safely be isolated from the dirty checkout.
- Include the related root/task ids and any active child cards observed, especially if another worker may still be mutating the same shared directory.
- Tell the reviewer to check current Kanban status/locks first and to block with a coordination note instead of racing an active worker.
- Summarize `git status`/diff shape at submission time: approximate file count, notable untracked source/test files, and suspicious temp artifacts.
- Instruct the reviewer to separate intentional source/test/docs changes from disposable screenshots/json/debug artifacts; do not blindly discard or commit temp files.
- Require repo-normal validation and exact command/output for blocked checks.
- Require a handoff with changed-files summary, validation results, whether board-move/API-policy questions remain unresolved, and commit SHA/branch if a commit was created.
- Prefer `--triage` with no assignee when the user wants the normal specifier/router to choose the right reviewer profile.

### Interview before submitting broad cleanup inventories

When the user provides a broad worktree/branch inventory or asks to submit a multi-repo cleanup plan, **do not immediately create a catch-all cleanup card** unless they explicitly say to submit now. First interview the user one decision at a time until the card authority is clear. For each question, provide a recommended answer and wait for the user's choice. Resolve at least:

- **Authority level:** planning only vs safe actions only vs full cleanup execution. Default recommendation for broad inventories is **safe actions only**: checkpoint/verify/metadata cleanup, no commits/resets/deletes/worktree removals/pushes.
- **Safe metadata cleanup gate:** for `git worktree prune`, default to dry-run, verify every candidate path is absent, then run actual prune and show post-prune worktree list.
- **Child-card policy:** default to creating unassigned triage follow-up cards only; do not assign/spawn risky cleanup directly.
- **Dependency shape:** default to independent triage cards that reference the root rather than formal children, so the root can complete after publishing the cleanup graph.
- **Checkpoint scope:** define which dirty repos get central checkpoints up front and which are only status-recorded for child cards to checkpoint later.
- **Checkpoint location/format:** prefer a central durable folder outside the repos (for example `~/.hermes/checkpoints/<inventory-date>/<repo-slug>/`) with status, tracked/staged diffs, untracked lists, optional safe untracked archive, and checksums; avoid dirtying target repos further.
- **Existing-card coordination:** if a focused cleanup card already exists for one repo, let the broad root checkpoint/record status only and defer detailed classification to the focused card.
- **High-risk vault handling:** for Obsidian vaults, prefer light path/category classification over deep private-content inspection; never bulk commit or tar broad vault contents.

If you accidentally create the wrong broad card, cancel it by archiving it immediately and verify it has no children/runs/comments before reporting back.

### Adding follow-up rows to an active Loop

When the user grills or discovers UX bugs mid-execution and asks to add follow-up tasks, package them as concrete branch/fix rows with locked decisions in the body, then link them into the final verification/closure chain before reporting. If previous verification/build cards already completed, add a comment on the closure row that their evidence predates the new follow-ups and must be rechecked. On active boards, avoid normal `todo` creation when parents are already satisfied unless immediate dispatch is intended; use `--initial-status blocked` with a foreground planning-hold reason or triage parking, then explicitly unblock/promote only after activation approval.

### Loop slash intake, scheduled parking, and triage activation

For `/loop <title>` style foreground intake, do not use `triage` as a passive parking lot. Park title-only or under-specified Loop roots in `scheduled` while the current foreground session interviews the user and rewrites the clean task body. Do **not** fork a foreground orchestrator session for normal intake; the user is already present in the current foreground chat. Forked/dedicated foreground orchestrator sessions are for review/handoff stewardship, not first-pass intake.

Recommended intake lifecycle:

```text
/loop <title> → scheduled draft
current foreground session pre-fills from visible conversation context
foreground asks one intake decision at a time
body stays in the current specify format: Goal / Approach / Acceptance criteria / Out of scope
Submit now → scheduled -> triage
triage is active: auto-decompose/specify/epistemic-subgraph may run
```

Use current foreground context aggressively for the initial prefill; use targeted lookup only when the title/context clearly points to a retrievable artifact. Do not perform broad retrieval across all sessions, the whole vault, unrelated boards, or repo history before the first intake question. If context is insufficient, recommend Clarify/interview.

Once this boundary is in place, auto-decompose on `triage` can be enabled safely: anything in `triage` is admitted for system reasoning. If a task should not be decomposed yet, it belongs in `scheduled`.

For consequential uncertainty, preserve dynamic workflow generation: create an epistemic request/subgraph whose shape is chosen by the decomposer, but enforce behavior through role skills on generated child workers. Do not rely on profile assignment alone as the "judge." Use role skills such as explorer, critic, verifier, and adjudicator, plus any needed domain skill. The invariant is dynamic graph shape + skill-enforced roles + fixed resolve contract.

### Session Work Maps / foreground orchestration

When a foreground/chat session owns a user-facing Work Map, treat it as a root-task graph: root user task → brief branch/lane/gate skeletons → auto-specified or auto-decomposed executable work → review/integration/package/publish gates. Foreground Hermes owns **intent and topology**, not detailed worker specifications. Its minimum graph-writing responsibility is a short task title plus dependency links. The triage auto-decomposer/specifier must turn each skeleton row into either a worker-complete task or a bounded child graph with bodies, acceptance criteria, assignees, workspaces, skills, and execution policy. Comments remain audit breadcrumbs only. Keep column semantics sharp: review handoffs go to `review`/`attention=needs-orchestrator`, dependency waits should not masquerade as true blockers, and `blocked` is reserved for real human/external/system gates. See `references/foreground-built-graph-materialization.md` and `references/work-map-task-graph-and-status-semantics.md`.

**Use a two-stage compile boundary.** While foreground Hermes is editing titles or topology, keep skeleton rows in `scheduled`. Submitting them to `triage` admits them to the same automatic specification/decomposition path as an individually submitted task. The foreground agent should not have to pre-author Goal / Approach / Acceptance criteria / Out of scope for every row. Those fields must exist before dispatch, but they are compiler outputs. The Loop root supplies shared goal/decision context; the compiler curates only the context each worker needs.

**Preserve dependencies through decomposition.** If foreground creates `A -> B` and triage decomposes B into `B1 -> B2`, every generated entrypoint for B must inherit B's unfinished external prerequisites: `A -> B1 -> B2 -> B(container)`. Merely keeping `A -> B(container)` is unsafe because B1 could dispatch early. Preserve the skeleton row as the stable lane/fan-in container, copy incoming external parents to generated entrypoints, link generated leaves back to the container, and keep outgoing downstream edges on the container. Validate this atomically before promotion.

**Do not accidentally dispatch planning skeletons.** Parentless `todo` is not a safe parking state on an active board. Use `scheduled` while editing. On explicit **Decompose & Run**, move/admit the intended skeletons to triage compilation only after their title/dependency graph is wired. Immediately verify generated entrypoints, inherited external prerequisites, `ready`, `running`, and `review`. Reclaim/park anything that violated the skeleton graph.

**Decompose approval is activation approval by default for Vaitheesh.** When Vaitheesh approves Decompose & Run, treat that as approval to auto-specify/decompose and dispatch dependency-satisfied compiled entrypoints unless he explicitly says preview, planning-only, hold, or do not dispatch. A non-activating UI action must be labeled clearly as **Preview graph** or **Compile without running**. See `references/decompose-without-activation.md` only for the explicit planning-only exception path.

**Rows are branches, not worker prompts at authoring time.** Foreground rows represent distinct branches/lanes/gates and may begin as title-only skeletons with dependencies. They must become worker-complete before execution, but auto-specification/decomposition—not foreground graph authoring—normally supplies the detailed body. Do not create separate planning/decision/schema rows as prerequisites workers must inspect; compile locked root/foreground decisions into each affected executable body.

**Loop roots are containers, not triage work.** Keep the root as the stable non-dispatching goal/container while its skeleton lanes compile and run. Real work belongs in compiled branch/lane/gate rows. See `references/loop-root-container-triage-pitfall.md`.

When the user wants Kanban to support normal foreground chat—a visible decision/todo map, worker attention queue, or Desktop Work Map—use `references/session-work-map-foreground-orchestration.md`. For active foreground stewardship use `references/work-map-active-stewardship-lessons.md`. For title/dependency skeleton compilation and dependency-safe auto-decomposition use `references/foreground-built-graph-materialization.md` and `references/auto-decomposer-foreground-approval.md`.

Key defaults:

- Treat **Work Map** as the lay-user concept; Kanban is the durable backing store and execution engine.
- Foreground Hermes emits a minimal skeleton graph: stable row alias/id, brief title, and `depends_on`. It does not emit the auxiliary decomposer's full worker-spec JSON.
- Materialize skeleton rows in canonical Kanban state; use `scheduled` while editing and `triage` to invoke automatic specification/decomposition.
- Keep the existing `todo` tool ephemeral; Desktop/Loop UI remains a projection over canonical Kanban tasks/links/runs rather than a separate Work Map database.
- Keep the model-facing graph mutation schema minimal and gated so it does not impose a large unconditional tool-schema cost on every session.
- Foreground Hermes may submit partial skeleton subsets once titles and dependencies are stable; unresolved branches remain `scheduled` or ephemeral.
- Auto-compilation must discover real profiles and produce worker-complete bodies, acceptance criteria, workspace/safety policy, skills, budgets, and review behavior before dispatch.
- Compile dependency-free entry skeletons after activation. Keep downstream skeletons dependency-gated with `needs_specification=true`; when parents complete, route them to `triage` with compact parent handoffs instead of promoting title-only rows directly to `ready`.
- Independent eligible skeleton rows may compile in parallel, but execution follows preserved dependency semantics.
- For incremental graph append, create skeleton rows and links atomically, compile admitted rows through triage, link generated leaves to their stable skeleton containers, and leave dispatcher/worker lifecycle untouched.
- Foreground Hermes is the review triage layer: worker review handoffs should enter a distinct **review** state/column (or equivalent existing review evidence path), not the generic blocked column and not immediate user interruptions.
- Reserve generic **blocked** for true blockers such as missing dependencies, failed prerequisites, external resources, credentials, human approval gates, or runtime/push risk. A task waiting for another task should not look identical to a task waiting for foreground/user review.
- Escalate to the user via `clarify` with a recommended answer only for irreversible/external actions, credentials/private data, publish/push, live runtime changes, product/personal taste, or ambiguity.
- For the first implementation, prefer a vertical slice: opt-in → `work_map` update → Kanban metadata persistence → inline + side-panel Desktop rendering → simulated worker attention → foreground verification.

## Submitting brainstorming / decision-session work

When the user says to submit the results of a brainstorming or decision session, do **not** submit only the first obvious item. First reconstruct the decision set from the named note/session/source, then submit the whole set or explicitly ask which subset to queue.

For Desktop-first “normal chat creates a visible Kanban-backed plan” product work, use the session-native Work Map pattern in `references/session-native-work-map.md` with the skeleton-graph compiler boundary in `references/foreground-built-graph-materialization.md`: foreground Hermes emits only brief task titles and dependencies; each admitted skeleton row then uses the ordinary triage auto-specification/decomposition path to become worker-complete. Kanban remains the only durable task graph/execution engine. Do **not** add a separate durable `work_map` database/state. Desktop presents the Work Map as a view over Kanban tasks/links/runs.

Recommended flow:

1. Locate the source artifact/session (for example a note like `one lane-one purpose.md`, a decision packet, or the previous chat transcript).
2. Extract every actionable decision and classify each as: product direction, implementation task, research/spike, cleanup/review, or documentation.
3. Decide whether the decisions belong in one root orchestrator card with a decomposition brief or several independent cards. Preserve dependencies with `--parent` links when one decision depends on another.
4. Put the source path/session id and a concise decision list in the card body so the worker does not depend on chat memory.
5. If the user says “the rest of my decisions” or corrects the scope, stop and re-enumerate the full decision set before creating more cards.
6. After creating the root card, verify it with `kanban show` and check whether updates will actually reach the user's current surface before promising notifications.
7. For ordinary one-off progress/status alerts where no foreground Work Map exists, a low-noise script-only cron monitor can be an acceptable fallback: alert only on blockers, stalls, failures/errors, or root completion; stay silent on normal progress. See `references/session-job-monitoring.md` for the reusable monitor pattern.

Pitfall: phrases like “continue with Kanban submission” often refer to a prior brainstorming packet, not the latest technical cleanup thread. Check recent session/note context before assuming the target is the most recent dirty workspace or implementation issue.

Pitfall: creating a Kanban card is not the same as subscribing the current chat to its lifecycle. If `notify-list` is empty or the job was created from CLI/triage without origin metadata, say "not by default". For one-off operations, an explicit monitor can be a temporary workaround. For Work Map / foreground-session product flows, do **not** encode polling as the primitive: use native `foreground_handoff` events and an Attention Queue instead (see `references/session-work-map-foreground-handoffs.md`).

### Post-completion high-risk cleanup decision review

When a broad cleanup/inventory root has completed and the user chooses a review option like “Option B — review high-risk decisions before authorizing real cleanup,” do **not** immediately create more cleanup cards or approve destructive actions. Produce a decision packet first:

1. Re-read the completed root card and all high-risk follow-up triage/review cards, including children created by those cards. Use `kanban show`/DB comments/run summaries to gather durable findings; do not rely only on the chat summary.
2. Recheck current git state for the relevant repos where possible (`branch`, short HEAD, `status --short --branch`) so stale triage is not presented as current state. If a path is inaccessible because of permissions, report that as a verification limit rather than guessing.
3. Separate **classification findings** from **approval decisions**. Explicitly identify which actions are destructive or irreversible: deleting directories, discarding dirty hunks, removing worktrees, deleting branches, restoring plugin bundles, cleaning vault content.
4. Recommend the narrowest next approval lane. Prefer one repo/lane at a time, with checkpoint-first, no-push, branch-preserving instructions. Do not recommend broad cleanup across vaults, live runtimes, and active product repos in one card.
5. For active dirty developer repos, classify as active work / commit-review candidates, not cleanup trash. For clean worktree candidates whose branch HEADs are not merged, recommend worktree/checkout removal only while preserving branch refs.
6. For Obsidian vaults, preserve notes/config by default and avoid bulk delete/tar/commit. Any cleanup should be a vault-only card limited to generated/log paths with explicit review gates.
7. For runtime/plugin-set decisions, treat removal of required infrastructure (for example Local REST API in an Obsidian starter vault) as a blocking product/runtime decision, not incidental cleanup.

See `references/post-cleanup-decision-review.md` for the compact decision-packet template and safety defaults.

### Submitting approved narrow cleanup follow-ups

When the user reviews a completed cleanup inventory/triage packet and says to proceed with one recommended lane, do **not** reopen the broad root or launch another bundled cleanup. Create a focused follow-up card for that single lane, verify the card, dispatch it if the user asked to proceed now, and monitor it to completion before reporting.

## Safety and git policy to repeat in monitor/fix cards

When writing Kanban cards for Vaitheesh's repo/runtime work, embed this policy explicitly instead of relying on worker memory:

- Workers may use local git freely for branches, commits, worktrees, patch bundles, restores/resets, and checkpointing.
- Workers must not push.
- Dirty workspaces may be operated on only when the child task is explicitly cleanup/classification/remediation/finalization for that workspace, and only after creating a reversible backup/checkpoint.
- New implementation work must happen from a clean branch/worktree, or only after the dirty state is checkpointed and isolated.
- Live Hermes code/config/profile/Obsidian mutations still need explicit approval plus rollback/checkpoint and verification gates.

Recommended safe shape for stale duplicate checkout cleanup:

1. Assign to an ops/review profile that exists (for this setup, `ops-steward` is appropriate for filesystem cleanup/checkpointing).
2. Use `workspace=dir:<duplicate-path>` when the worker must operate on the existing dirty checkout.
3. Require a central checkpoint under `~/.hermes/checkpoints/<lane>-<timestamp>/` with status, diffs, untracked listings, SHA256SUMS, and a `git bundle` or equivalent branch/head preservation artifact before any restore/move.
4. Require read-only re-verification that the dirty hunks are superseded or otherwise safe before restoring/resetting them.
5. Prefer reversible quarantine/move into the checkpoint folder over permanent deletion; explicitly forbid `rm -rf`, branch/tag deletion, and pushes unless a later card has explicit user approval.
6. Final verification must show the canonical checkout is untouched, old duplicate path absent or quarantined, checkpoint hashes verify, and no permanent deletion occurred.

Pitfall: if you create the card and then only tell the user it is queued, you have not fulfilled a “proceed” request. Run a dispatcher pass and watch `kanban show`/`kanban log` until the card completes or blocks, then report the real outcome.

### Cancelling submitted Kanban work

When the user asks to cancel submitted tasks:

1. Identify the exact root card(s) and their children/dependencies; do not guess IDs.
2. For any `running` child, use `hermes kanban reclaim <task_id> --reason <reason>` first so the worker stops before archival.
3. Archive the root and all known children/dependencies with `hermes kanban archive ...`.
4. Verify each archived status with `kanban show` before reporting.
5. Report any completed children separately: they cannot be un-run, but archiving prevents further routing.

## Work changelog maintenance

When Kanban work produces a meaningful completed artifact for Vaitheesh — a local commit, checkpoint, quarantine, cleanup decision, or high-risk follow-up resolution — update the user-facing work changelog before final reporting when practical. Use `references/work-changelog-handoffs.md` for the target note and entry shape. Keep changelog entries concise and evidence-backed: card id, repo/path, commit/checkpoint, verification, safety, and next action. Do not paste full task logs or sensitive vault content.

## Common patterns

**Fan-out + fan-in (research → synthesize):** N research-style cards with no parents, one synthesis card with all of them as parents.

**Parallel implementation + validation:** one implementer card makes the change while one explorer/researcher card verifies config, docs, or source mapping. A reviewer card can depend on both. Do not make the implementer own unrelated verification just because the user mentioned both in one sentence.

**Pipeline with gates:** `planner → implementer → reviewer`. Each stage's `parents=[previous_task]`. Reviewer blocks or completes; if reviewer blocks, the operator unblocks with feedback and respawns.

**Same-profile queue:** N tasks, all assigned to the same profile, no dependencies between them. By default the dispatcher may spawn multiple separate worker sessions for that same profile in parallel. If you want true serial processing, set `kanban.max_in_progress_per_profile: 1` (or another positive cap) so excess ready tasks defer to later dispatcher ticks while still sharing the profile's durable memory over time.

**Human-in-the-loop:** Any task can `kanban_block()` to wait for input. Dispatcher respawns after `/unblock`. The comment thread carries the full context.


## Loop SDLC routing overlay

For implementation/review pipelines, keep decomposition aligned to the local Loop vocabulary: `DEFINE -> PLAN -> BUILD -> VERIFY -> REVIEW -> SHIP`. This pilot is inspired by addyosmani/agent-skills 0.6.2 lifecycle/checklist patterns, paraphrased for Hermes Kanban rather than imported as a new always-on umbrella skill.

Routing rules:

- Treat each row as a branch, lane, or gate; use parent links for true dependencies and leave independent lanes parallel.
- Keep the task body as source of truth: goal, scope/out-of-scope, workspace/safety boundaries, required skills/process, acceptance criteria, verification evidence, handoff behavior, and blocked/escalation policy.
- Prefer explicit active handoffs: create reviewer-qa, fix-after-review, E2E/verification, or live-adoption/publish-gate cards when those gates are real work.
- Do not use `blocked` as a review queue. Block only for human decisions, missing credentials/private access, external systems, destructive approvals, or ambiguous production behavior.
- Do not create a broad SDLC umbrella skill or raw-import upstream agent personas unless repeated local misses prove a concrete gap.

Reusable card-body templates for orchestrator-authored tasks live in `templates/`:

- `implementation-card.md`
- `reviewer-qa-card.md`
- `fix-after-review-card.md`
- `e2e-verification-card.md`
- `live-adoption-publish-gate-card.md`

## Pitfalls

**Inventing profile names that don't exist.** The dispatcher silently fails to spawn unknown assignees — the card just sits in `ready` forever. Always assign to a profile from your Step 0 discovery; ask the user if you're unsure.

**Forcing skills a target profile does not have.** `hermes kanban create --skill ...` is resolved in the worker's profile, not the orchestrator's current profile. If a local umbrella skill exists only in `default`, a `reviewer-qa` or other profile can crash before reasoning with `Error: Unknown skill(s): ...`. Before adding `--skill`, sanity-check `hermes -p <profile> skills list` for every target profile, or omit forced skills and put the needed operating guidance directly in the card body. Recovery: create a replacement card for the same assignee without unavailable forced skills, relink downstream children from the crashed card to the replacement, archive the crashed card, then dispatch.

**Worker provider/auth mismatch.** If a lane crashes or exits without a Kanban handoff and the profile's model/provider may be wrong, fix the profile before spawning more work: inspect the profile config/auth, set the intended provider/model (for example via `hermes -p <profile> config set model.provider ...` and `model.default ...`), smoke-test that exact profile with a tiny `hermes -p <profile> chat -q 'Reply exactly: ok' --provider ... -m ... -Q`, then reclaim/retry or create a replacement only if no valid recovery row already exists. Before creating a duplicate replacement, inspect tenant links/statuses for existing recovery cards and either use the existing recovery or archive/unlink your duplicate to avoid double-spend.

**Kanban DB corruption during orchestration.** If `hermes kanban` refuses to open a board with `integrity_check` errors after create/comment/complete/dispatch, stop routing and recover before continuing. First distinguish index-only corruption from table/page corruption: back up the DB, run `PRAGMA integrity_check;` / `PRAGMA quick_check;`, and if the errors are only “wrong # of entries in index …” or “row … missing from index …”, run `REINDEX; VACUUM;` and verify `PRAGMA integrity_check` returns `ok` before re-running `hermes kanban show/list/dispatch`. If integrity errors mention malformed pages/tables or recovery is not index-only, copy the DB, run `sqlite3 kanban.db '.recover' > /tmp/recover.sql`, load into a new DB, verify `PRAGMA integrity_check` returns `ok`, then replace the board DB and re-run `hermes kanban show/list` to verify task states. If a partially created card has corrupted fields (bad status/assignee/body with NULs), repair it conservatively or archive/recreate before dispatch. Always finish with a final integrity check. For dashboard-visible “empty board but work not done” incidents, use `references/kanban-board-health-and-progress-monitoring.md`: check all boards, gateway quarantine logs, profile existence, and index-only repair (`REINDEX; VACUUM`) before concluding there is no pending work.

**Kanban dashboard shows repeated tasks across boards.** Before suspecting duplicate tasks or DB corruption, check whether the dashboard process inherited worker board-pinning env vars (`HERMES_KANBAN_DB`, `HERMES_KANBAN_BOARD`, `HERMES_KANBAN_WORKSPACES_ROOT`). The dashboard API can then ignore `?board=...` and read the same pinned DB for every board. Diagnose by comparing CLI `hermes kanban --board <slug> list` results against dashboard API/UI, then restart the dashboard with those env vars unset. See `references/kanban-dashboard-env-leakage.md` for the exact probe and safe restart workaround.

**Bundling independent lanes into one card.** If the user asks for two independent outcomes, create two cards. Example: "fix blockers and check model variants" is not one fixer task; create a fixer/engineer card for the fixes and an explorer/researcher card for the variant check, then optionally gate review on both.

**Confusing workspace isolation with lane design.** `--workspace scratch|dir:<path>|worktree|worktree:<path>` controls where a worker runs (cwd / branch / worktree isolation). It does not, by itself, enforce “one lane, one purpose.” Preserve one-lane-one-purpose by decomposing broad work into separate cards with distinct titles, acceptance criteria, assignees, and dependency links; then use per-card workspaces/branches to keep those lanes physically isolated. A single broad card with `--workspace worktree` is still a bundled lane, and multiple purpose-specific cards sharing `dir:<repo>` can still race unless the body explicitly coordinates or dependencies serialize them.

**Over-linking because of wording.** "Finally check X" may still be parallel with implementation if X is static config, docs, or source discovery. Link it after implementation only when the check depends on the implementation result.

**Forgetting dependency links.** If the task graph says `research -> implement -> review`, do not create all tasks as independent ready cards. Use parent links so implement/review cannot run before their inputs exist.

**Reassignment vs. new task.** If a reviewer blocks with "needs changes," create a NEW task linked from the reviewer's task — don't re-run the same task with a stern look. The new task is assigned to the original implementer profile.

**Argument order for links.** `kanban_link(parent_id=..., child_id=...)` — parent first. Mixing them up demotes the wrong task to `todo`.

**Don't pre-create the whole graph if the shape depends on intermediate findings.** If T3's structure depends on what T1 and T2 find, let T3 exist as a "synthesize findings" task whose own first step is to read parent handoffs and plan the rest. Orchestrators can spawn orchestrators.

**Tenant inheritance.** If `HERMES_TENANT` is set in your env, pass `tenant=os.environ.get("HERMES_TENANT")` on every `kanban_create` call so child tasks stay in the same namespace.

## Recovering stuck workers

When a worker profile keeps crashing, hallucinating, or getting blocked by its own mistakes (usually: wrong model, missing skill, broken credential), the kanban dashboard flags the task with a ⚠ badge and opens a **Recovery** section in the drawer. Three primary actions:

1. **Reclaim** (or `hermes kanban reclaim <task_id>`) — abort the running worker immediately and reset the task to `ready`. The existing claim TTL is ~15 min; this is the fast path out.
2. **Reassign** (or `hermes kanban reassign <task_id> <new-profile> --reclaim`) — switch the task to a different profile (one that exists on this setup) and let the dispatcher pick it up with a fresh worker.
3. **Change profile model** — the dashboard prints a copy-paste hint for `hermes -p <profile> model` since profile config lives on disk; edit it in a terminal, then Reclaim to retry with the new model.

Hallucination warnings appear on tasks where a worker's `kanban_complete(created_cards=[...])` claim included card ids that don't exist or weren't created by the worker's profile (the gate blocks the completion), or where the free-form summary references `t_<hex>` ids that don't resolve (advisory prose scan, non-blocking). Both produce audit events that persist even after recovery actions — the trail stays for debugging.
