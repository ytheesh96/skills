---
name: kanban-worker
description: Pitfalls, examples, and edge cases for Hermes Kanban workers. The lifecycle itself is auto-injected into every worker's system prompt as KANBAN_GUIDANCE (from agent/prompt_builder.py); this skill is what you load when you want deeper detail on specific scenarios.
version: 2.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [kanban, multi-agent, collaboration, workflow, pitfalls]
    related_skills: [kanban-orchestrator]
---

# Kanban Worker — Pitfalls and Examples

## Durable operation contract

Workers use one explicit `board` and stable `tenant` for every operation.
The foreground creates each task once with `kanban_create`, supplies `parents`
or uses `kanban_link`, and inspects state with `kanban_list` and `kanban_show`.
Human decisions use `kanban_block` and `kanban_unblock`; workers do not own
graph mutation, follow-ups, acceptance, or closure.

> You're seeing this skill because the task or profile explicitly loaded deeper Kanban operating detail. The core lifecycle is always injected into workers through `KANBAN_GUIDANCE`; this skill adds handoff shapes, retry diagnostics, and edge cases.

## Workspace handling

For durable handoff rules, especially when a useful report is produced in a scratch workspace, see `references/artifact-durability.md`.

For local repository/worktree cleanup tasks, workers may use local git branches, commits, patch backups, worktrees, and resets when explicitly authorized; dirty workspaces are cleanup targets, not general development bases. See `references/git-cleanup-workspaces.md`.

For comparing Kanban worktrees/branches, answering "was this done on main?", or summarizing which features live in which worktree, combine ancestry, reflog, patch-equivalence, and changed-file inspection; present a visual branch map before dense prose when the user is confused. See `references/worktree-feature-inventory.md`.

For Kanban worker completions/blocks that should return to a foreground session, Loop, or Work Map, use native foreground handoff / Attention Queue triage rather than cron monitors. See `references/foreground-handoff-loops.md`.

Your workspace kind determines how you should behave inside `$HERMES_KANBAN_WORKSPACE`:

| Kind | What it is | How to work |
|---|---|---|
| `scratch` | Fresh tmp dir, yours alone | Read/write freely; it gets GC'd when the task is archived. |
| `dir:<path>` | Shared persistent directory | Other runs will read what you write. Treat it like long-lived state. Path is guaranteed absolute (the kernel rejects relative paths). |
| `worktree` | Git worktree at the resolved path | The dispatcher should create the worktree before you start. If `.git` is missing, block as a workspace setup failure instead of improvising. Commit work here. |

For Loop/Kanban worktrees, do not run `npm install` or copy `node_modules`
inside the worktree unless the task explicitly authorizes dependency repair.
Worktrees should reuse dependency directories linked from the source checkout when available. If dependencies are missing or stale, leave a concrete follow-up suggestion in `kanban_comment` and block rather than creating a multi-GB per-worktree install.

## Tenant isolation

If `$HERMES_TENANT` is set, the task belongs to a tenant namespace. When reading or writing persistent memory, prefix memory entries with the tenant so context doesn't leak across tenants:

- Good: `business-a: Acme is our biggest customer`
- Bad (leaks): `Acme is our biggest customer`

## Epistemic decision cards

When a worker is assigned an uncertain product, API, market, scientific, architecture, or strategic choice, use `loop-epistemic-workflows`. For consequential decisions, prefer durable Kanban subgraphs over hidden one-agent reasoning.

If consequential fuzziness emerges during execution, do not guess and do not implement down a guessed path. Put an uncertainty packet in `kanban_comment` (decision question, facts, alternatives, criteria, consequence of guessing wrong, affected task ids, and scope), then call `kanban_block`. The foreground decides whether to create an epistemic subgraph and supplies resume instructions.

When you are one lane in an epistemic graph, return structured claims, evidence, confidence, risks, rejected alternatives, and what would change your conclusion. Do not create or route other lanes yourself.

## Good summary + metadata shapes

The `kanban_complete(summary=..., metadata=...)` handoff is how downstream workers read what you did. Patterns that work:

**Coding task:**
```python
kanban_complete(
    summary="shipped rate limiter — token bucket, keys on user_id with IP fallback, 14 tests pass",
    metadata={
        "changed_files": ["rate_limiter.py", "tests/test_rate_limiter.py"],
        "tests_run": 14,
        "tests_passed": 14,
        "decisions": ["user_id primary, IP fallback for unauthenticated requests"],
    },
)
```

**Coding task that needs review:**

Workers report evidence; the foreground owns review routing. When implementation is ready, make it durable, add a proof-packet comment, then cross a completion boundary. Do not call removed review-routing tools, create reviewer tasks, or leave prose instructions for another worker to execute.

Preferred pattern:

1. Commit the coherent implementation and tests locally; do not push unless the task explicitly authorizes it.
2. Add a structured proof-packet comment: changed files, commit/branch/worktree, exact tests, residual risks, and final workspace status.
3. Call `kanban_complete(summary=..., metadata=...)`. The completion delivers the comment to the foreground, which decides whether to accept it or create review/fix follow-up work.
4. If the task body explicitly requires a human/external decision before it can be terminal, add the proof packet and call a genuine `kanban_block(reason=...)` instead. Do not use a dependency wait as a review queue.

```python
import json

kanban_comment(
    body="review suggestion:\n" + json.dumps({
        "changed_files": ["rate_limiter.py", "tests/test_rate_limiter.py"],
        "tests_run": 14,
        "tests_passed": 14,
        "commit": "<verified local commit>",
        "workspace_status": "clean",
        "review_scope": "user_id/IP fallback choice and merge safety",
    }, indent=2),
)
kanban_complete(
    summary="rate limiter implemented in a clean local commit; 14/14 tests pass",
    metadata={
        "changed_files": ["rate_limiter.py", "tests/test_rate_limiter.py"],
        "tests_run": 14,
        "tests_passed": 14,
        "workspace_status": "clean",
    },
)
```

Use `kanban_complete` only when the assigned implementation or artifact is genuinely finished and its workspace state is accounted for.

**Research task:**
```python
kanban_complete(
    summary="3 competing libraries reviewed; vLLM wins on throughput, SGLang on latency, Tensorrt-LLM on memory efficiency",
    metadata={
        "sources_read": 12,
        "recommendation": "vLLM",
        "benchmarks": {"vllm": 1.0, "sglang": 0.87, "trtllm": 0.72},
    },
)
```

**Review task:**
```python
kanban_complete(
    summary="reviewed PR #123; 2 blocking issues found (SQL injection in /search, missing CSRF on /settings)",
    metadata={
        "pr_number": 123,
        "findings": [
            {"severity": "critical", "file": "api/search.py", "line": 42, "issue": "raw SQL concat"},
            {"severity": "high", "file": "api/settings.py", "issue": "missing CSRF middleware"},
        ],
        "approved": False,
    },
)
```

Shape `metadata` so downstream parsers (reviewers, aggregators, schedulers) can use it without re-reading your prose.

## Git/worktree completion hygiene

Treat workspace cleanliness as part of the deliverable, not later janitorial work.

1. Before the terminal board call, inspect the workspace with `git status --short --branch` through the `terminal` tool.
2. Commit coherent source, test, and documentation changes locally. Never mix unrelated inherited edits into that commit and never push without explicit authority.
3. Classify every untracked path. Commit intended repository content; pass user-facing deliverables through top-level `artifacts=[absolute paths]`; remove only disposable files created by this task. Do not delete ambiguous or inherited content.
4. If tracked, staged, or unexplained untracked changes remain, add the exact status as a `kanban_comment` and call `kanban_block` instead of claiming clean completion.
5. Include `branch`, verified local `commit`, and `workspace_status` in completion metadata. Use `workspace_status: "clean"` only when the status command produced no entries; otherwise enumerate the declared artifact paths.

A completed worker should leave either a clean worktree or a durable, explicit blocker explaining why it could not. This keeps managed worktrees eligible for safe removal while preserving all commits and task attachments.

## Follow-up suggestions

Leaf workers do not create, claim, link, assign, or review-route Kanban tasks. Put any proposed follow-up in `kanban_comment`, then cross a completion or genuine non-dependency block boundary so the foreground can evaluate and commit graph changes. Do not pass `created_cards` from a leaf worker.

## Block reasons that get answered fast

Bad: `"stuck"` — the human has no context.

Good: one sentence naming the specific decision you need. Leave longer context as a comment instead.

```python
kanban_comment(
    task_id=os.environ["HERMES_KANBAN_TASK"],
    body="Full context: I have user IPs from Cloudflare headers but some users are behind NATs with thousands of peers. Keying on IP alone causes false positives.",
)
kanban_block(reason="Rate limit key choice: IP (simple, NAT-unsafe) or user_id (requires auth, skips anonymous endpoints)?")
```

The block message is what appears in the dashboard / gateway notifier. The comment is the deeper context a human reads when they open the task.

## Heartbeats worth sending

Good heartbeats name progress: `"epoch 12/50, loss 0.31"`, `"scanned 1.2M/2.4M rows"`, `"uploaded 47/120 videos"`.

Bad heartbeats: `"still working"`, empty notes, sub-second intervals. Every few minutes max; skip entirely for tasks under ~2 minutes.

## Retry scenarios

If you open the task and `kanban_show` returns `runs: [...]` with one or more closed runs, you're a retry. The prior runs' `outcome` / `summary` / `error` tell you what didn't work. Don't repeat that path. Typical retry diagnostics:

- `outcome: "timed_out"` — the previous attempt hit `max_runtime_seconds`. You may need to chunk the work or shorten it.
- `outcome: "crashed"` — OOM or segfault. Reduce memory footprint.
- `outcome: "spawn_failed"` + `error: "..."` — usually a profile config issue (missing credential, bad PATH). Ask the human via `kanban_block` instead of retrying blindly.
- `outcome: "reclaimed"` + `summary: "task archived..."` — operator archived the task out from under the previous run; you probably shouldn't be running at all, check status carefully.
- `outcome: "blocked"` — a previous attempt blocked; the unblock comment should be in the thread by now.

## Operator triage: review-required blockers

When a user asks to triage blocked tasks whose reason starts with `review-required:`, act as the human review gate rather than only reporting status. For review-lane/routing/dispatcher cards, also use `references/review-gate-routing-triage.md` so you check every dispatch surface, board override wiring, and return-to-assignee semantics instead of approving only from tests.

Fast pattern:

1. Inspect each blocked card with `hermes kanban --board <board> show <id> --json`; read the latest summary, review handoff comment, changed files, tests claimed, parents/children, and residual risks.
2. Determine whether it is a legitimate human/external gate or a worker that used `kanban_block(reason="review-required: ...")` for ordinary review. Inspect the proof packet and task history. If the implementation is durable and reviewable, the foreground should accept it or create active review/fix follow-up work; the worker must not attempt review routing itself.
3. Re-run the narrow verification the worker claimed, from the correct repo/worktree. For code changes this usually means targeted tests plus compile/typecheck/lint/build commands named in the handoff. For live integration/config cleanup, also verify the live state that acceptance criteria mention, redacting secrets.
4. Do a small independent review pass: inspect the changed files/diff, scan for obvious security issues (secrets, shell/eval/deserialization/path writes), and confirm the implementation matches the card’s acceptance criteria. Treat test fixture tokens as false positives after inspection, not automatic blockers.
5. If the change is acceptable, unblock with a concise `review-approved:` reason that names the evidence (tests/build/live checks). If the user is asking why the graph stalled rather than asking you to approve, explicitly report whether the card should have been moved to `status=review` / `assignee=reviewer-qa` and name the wrong tool/event that prevented it. If issues remain, leave the card blocked and add an actionable comment with exact files/failing commands/expected fix.
6. After unblocking or rerouting review gates, check whether dependent todo cards became ready and run/trigger a dispatch pass if the operator expects the board to continue.

Do not unblock solely because a worker reported tests passing; verify enough yourself to make the unblock meaningful. If an approval layer prevents the unblock/reroute command, report the exact command/reason for the operator to run rather than claiming the task was unblocked.

For UI/API bridge review-required cards, add one narrow contract probe beyond the worker's happy-path tests: exercise the exact frontend query/helper arguments against the backend validation boundary, and compare backend enum/status values against frontend normalization. Common blocker shape: a frontend passes a sentinel like `0` or an unrecognized terminal state (`spawn_failed`, `gave_up`, `timed_out`) while the backend validates `ge=1` or the UI maps only generic `failed`/`error`. Passing unit/typecheck suites do not override a directly reproducible 422 or wrong attention/count mapping; leave the card blocked and name the exact frontend line, backend validation line, and missing regression test.

Two extra review pitfalls from Worktree/Obsidian artifact cards:

- **Claimed test files can disappear even when the worker log shows tests passed.** Before approving a `review-required` block, check that every claimed test file still exists, then rerun the exact test runner from the live environment. If the runner imports a missing helper (for example `ModuleNotFoundError` for a claimed test module), leave the card blocked even when screenshots or generated artifacts look good.
- **Shared worktrees can move after the review target is finalized.** A review card may already have been accepted/committed while a downstream card is now running in the same worktree and adding new dirty changes. If live `git status` or test results disagree with the card history, inspect the task events/commits first. For the prior review scope, test an isolated clean snapshot such as `git archive HEAD | tar -x -C /tmp/review-scope` (symlink existing `node_modules` if needed) rather than judging the accepted card against unrelated follow-on edits. If the task is already terminal (`done`/`archived`), do not try to `complete` it again; add a clarifying comment with the verification evidence instead.
- **Board selection can be confused by inherited operator environment.** In TUI/gateway sessions, `HERMES_KANBAN_BOARD` may already be set. For CLI fallback on a non-current board, explicitly export/set `HERMES_KANBAN_BOARD=<board>` for `create`, `show`, `comment`, `runs`, and `log`, and verify the task exists with `show` or direct board `list` before telling the user it was created or reviewed. Do not trust a successful-looking create/show transcript until the target board can read the task back.

## Operator Loop task-detail edits

When a user asks to update a Loop row/task description, update the real Loop/Kanban task body — do not create a local session todo or otherwise simulate the edit. Use the Loop graph's read → patch flow for editable triage Loop nodes: read the graph with `include_nodes=true` to get the current `graph_revision` and target task id, then patch with `op: "update_node"`, the exact `task_id`, a stable `mutation_id`, and `body` for the new description. Verify by reading the updated task body (or an equivalent canonical Loop/Kanban surface) before reporting success, and name the task id/title that was changed so the operator can confirm the side panel row.

Caveat: current `loop_graph.update_node` refuses non-triage rows (`unsafe_status`) such as already-promoted `todo`/`ready`, `blocked`, or `done` Kanban tasks. For those, prefer a durable comment plus a new follow-up child card when the existing card has already completed. If the operator explicitly needs the canonical body changed, use the Kanban DB/CLI path with an audited `edited` event (or the future dedicated body-edit command if available), then verify with `hermes kanban show <id> --json` / `context` rather than pretending the Loop patch succeeded.

## Operator recovery: stale “running” tasks

When a user says board tasks look stuck, treat that as an operator/debugging workflow, not just a status question. A task can remain `running` after its worker process died or after the gateway restarted. Fast triage pattern:

1. Inspect task state, runs, logs, and diagnostics: `hermes kanban --board <board> show <id> --json`, `runs <id>`, `log <id>`, and `diagnostics`.
2. Cross-check the recorded `worker_pid` against the live process table. Stale indicators include no live PID, expired claim, no recent heartbeat, and logs ending with `Interrupted during API call` or `Interrupt detected during retry wait, aborting`.
3. If the worker PID is gone and the task is still `running`, reclaim it with a specific reason: `hermes kanban --board <board> reclaim <id> --reason "worker pid is no longer alive; log ended with interrupt/stale claim"`.
4. Run a dispatch pass, preferably dry-run first if there are many tasks: `hermes kanban --board <board> dispatch --dry-run --json`, then `dispatch --json`.
5. Verify recovery by checking new runs, live PIDs, fresh heartbeats/log movement, and `stats`. If completed parent tasks unlock ready children, run another dispatch pass so newly ready work starts.

Avoid reporting “running” at face value when the worker PID is dead; reclaim + dispatch is the safe recovery path.

## Operator recovery: Kanban dashboard 500 / board DB corruption

When the Kanban dashboard shows a generic frontend card like `Failed to load Kanban board: 500: Internal Server Error`, do not stop at the UI message. Treat it as a backend/API failure and check dashboard/gateway logs plus the specific board SQLite DB. A common actionable case is an index-only integrity failure such as `wrong # of entries in index idx_events_task`; after a reversible DB backup/checkpoint, `REINDEX; PRAGMA integrity_check;` may repair it without restoring the whole board. See `references/kanban-dashboard-db-corruption.md` for the exact triage and safe repair recipe.

## Operator recovery: TaskNotes UI/CLI status drift

When the user provides Obsidian TaskNotes DOM, screenshots, or UI evidence that disagrees with `hermes kanban` output, treat both surfaces as real and investigate the mirror layer. TaskNotes can render local task mirror notes under `TaskNotes/Tasks/`; stale duplicate mirrors with the same `hermesTaskId` can remain visible even after the canonical Hermes task is done/unblocked. The canonical mirror itself can also be stale if managed sync/event streams stopped (for example, dashboard API unavailable or running on a different endpoint): compare `status`, `hermesList`, and `hermesLastSyncedAt` against live Hermes events and inspect TaskNotes plugin sync state. Search for duplicate `hermesTaskId` values, compare canonical `<board>--<taskId>.md` notes against title-derived duplicates, and move/archive/hide stale noncanonical mirrors according to the project cleanup policy. See `references/tasknotes-mirror-drift.md` for concrete triage recipes covering both duplicate mirrors and stale canonical mirrors.

## Operator comparison: task worktree versus current branch

When the user asks to compare with work done in a Kanban worktree (for example `t_<hex>`), do not treat the current worktree HEAD as automatically identical to the task's accepted scope. Inspect the canonical task first (`hermes kanban --board <board> show <id> --json`) and compare its `workspace_path`, `branch_name`, `latest_summary`, run metadata, and recorded `final_head`/integrated commits against the live git state. Worktrees can keep receiving downstream commits after a task completed, so explicitly separate:

1. the original accepted task scope (often `base..metadata.final_head` or the commits named in the completion handoff), and
2. the current worktree branch state (`base..branch`).

Useful non-mutating comparison pattern:

- Verify both repositories/worktrees are clean enough to inspect: `git -C <path> status --short --branch`.
- Resolve identity: `git rev-parse --abbrev-ref HEAD`, `git rev-parse HEAD`, `git worktree list --porcelain`.
- Find the common base with the comparison branch: `git merge-base main <branch>`.
- List branch-only commits and patch-equivalence: `git log --oneline --reverse <base>..<branch>` and `git cherry -v main <branch>`.
- Summarize scope without flooding the chat: `git diff --shortstat <base>..<branch>`, `git diff --name-status <base>..<branch>`, and optionally `git diff --dirstat=files,0`.
- Detect adoption risk without mutating state: `git merge-tree --write-tree main <branch>` and report conflicts.
- If the task metadata recorded a final head, compare `git diff --shortstat <base>..<final_head>` versus `<final_head>..<branch>` to show what was original versus later downstream work.

In the final answer, call out whether the worktree has advanced beyond the recorded task completion, whether either side is an ancestor, which commits are still unique by patch-id, and the exact files that would conflict. Do not merge, reset, cherry-pick, or push during a comparison-only request.

## Hermes Desktop E2E runtime-root checks

When a Kanban task validates Hermes Desktop end-to-end behavior, do not conflate three different paths:

- `HERMES_DESKTOP_HERMES_ROOT` = the Hermes backend/source checkout the Desktop app should run. It must be a valid Hermes source root (for current Desktop code, at least `hermes_cli/main.py` must exist). If the user asks to test their current runtime, resolve it from `hermes --version` / the installed project path (often `~/.hermes/hermes-agent`) rather than assuming the Kanban workspace repo is the backend root.
- `HERMES_DESKTOP_CWD` = the project/repo opened by the Desktop UI for the scenario under test. This is usually a disposable fixture repo for E2E validation.
- `HERMES_HOME` = runtime config/session state. Prefer a disposable temp `HERMES_HOME` for E2E safety unless the acceptance criteria explicitly require touching the user's live runtime state.

Before launching Electron/Desktop from a worker, record which path fills each role and verify `HERMES_DESKTOP_HERMES_ROOT` is accepted by the app's source-root predicate. If the Kanban workspace is only a partial repo or a test fixture, using it as `HERMES_DESKTOP_HERMES_ROOT` can make the test exercise the wrong backend or fail over to another resolver path while still looking superficially “live.”

## Notification routing

You can configure the gateway to receive cross-profile Kanban task notifications by adding `notification_sources` to `~/.hermes/config.yaml`.
- `notification_sources: ['*']` accepts subscriptions from all profiles.
- `notification_sources: ['default', 'zilor-ppt']` or `"default,zilor-ppt"` restricts subscriptions to specified profiles.
- Omitting the key keeps the default behavior (profile isolation).

## Do NOT

- Create, claim, link, assign, or review-route follow-up tasks. Put the suggestion in `kanban_comment`; the foreground owns graph mutation.
- Modify files outside `$HERMES_KANBAN_WORKSPACE` unless the task body says to.
- Complete a task you didn't actually finish or whose workspace has unexplained dirty state. Block it instead.

## Foreground salvage and review gates

When a worker times out/gives up with useful partial work, do not keep redispatching the same broad card. The foreground orchestrator should inspect same-scope evidence, run targeted tests, clean transient artifacts, produce a commit only if safe, and then create a reviewer-QA gate with explicit outcomes. See `references/foreground-handoff-salvage.md`.


## Loop SDLC phase handoff shape for implementation cards

Use this compact Loop overlay for code, workflow, and infrastructure cards. It is a local pilot inspired by addyosmani/agent-skills 0.6.2 lifecycle/checklist patterns, paraphrased for Hermes Kanban semantics rather than imported wholesale.

Phases: `define -> plan -> build -> verify -> review -> ship`.

When a card changes code or workflow behavior, put enough evidence in the handoff for the next lane/gate:

```json
{
  "phase": "review",
  "acceptance_criteria": ["copied or paraphrased from the task/comments"],
  "changed_files": ["concrete paths only"],
  "artifacts": ["optional durable output paths"],
  "verification": [{"command": "actual command", "result": "pass|fail|skipped with reason"}],
  "rollback": ["how to revert, disable, or restore from checkpoint"],
  "residual_risks": ["known gaps, skipped checks, external decisions"]
}
```

Behavior rules:

- `DEFINE`: restate source-of-truth task goals, constraints, scope/out-of-scope, workspace, and unknowns before changing anything.
- `PLAN`: split dependency-ordered increments; create child cards for separate lanes/gates instead of scope-creeping.
- `BUILD`: keep changes small, reversible, and runnable; avoid new daemons, global config, or broad imports unless explicitly required.
- `VERIFY`: run the smallest meaningful check first, then broader tests/build/smoke checks; report real commands and outputs.
- `REVIEW`: for material code/config/workflow changes, leave the structured proof packet in `kanban_comment()` and complete the assigned work. The foreground decides whether to accept it or create review/fix follow-up work; block only for a genuine human, external, credential, or system gate.
- `SHIP`: merge, deploy, restart live services, or publish only when the card explicitly authorizes it and the rollback path is known.

Loop semantics to preserve: rows are branches/lanes/gates; task bodies are source of truth; comments are audit breadcrumbs; `blocked` is only for true human/external/system blockers; reviewer-qa gets active handoff cards instead of passive review blockers.

Linked card-body templates live in `templates/` and the one-page reference is `references/kanban-sdlc-loop.md`.

## Pitfalls

**Ad-hoc Kanban tests inside a worker can pollute the live board.** Dispatcher-spawned workers inherit `HERMES_KANBAN_DB`, `HERMES_KANBAN_BOARD`, and workspace-root env vars pinned to the real board. If you run a Python repro that does `os.environ['HERMES_HOME']=tempdir` and then calls `hermes_cli.kanban_db.connect()` / `create_task()`, the pinned `HERMES_KANBAN_DB` still wins and the repro can create real tasks (often placeholder titles like `claim me`) on the live board. For isolated repros, explicitly clear or override Kanban-specific env vars before importing/using `kanban_db`, or pass an explicit temp DB/board path through the code under test. See `references/live-board-test-pollution.md`.

**Task state can change between dispatch and your startup.** Between when the dispatcher claimed and when your process actually booted, the task may have been blocked, reassigned, or archived. Always `kanban_show` first. If it reports `blocked` or `archived`, stop — you shouldn't be running.

**Workspace may have stale artifacts.** Especially `dir:` and `worktree` workspaces can have files from previous runs. Read the comment thread — it usually explains why you're running again and what state the workspace is in.

**Don't rely on the CLI when the guidance is available.** The `kanban_*` tools work across all terminal backends (Docker, Modal, SSH). `hermes kanban <verb>` from your terminal tool will fail in containerized backends because the CLI isn't installed there. When in doubt, use the tool.

## CLI fallback (for scripting)

Every tool has a CLI equivalent for human operators and scripts:
- `kanban_show` ↔ `hermes kanban show <id> --json`
- `kanban_complete` ↔ `hermes kanban complete <id> --summary "..." --metadata '{...}'`
- `kanban_block` ↔ `hermes kanban block <id> "reason"`
- `kanban_comment` ↔ `hermes kanban comment <id> "..."`
- etc.

Use the tools from inside an agent; the CLI exists for the human at the terminal.
