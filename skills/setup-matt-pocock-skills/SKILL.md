---
name: setup-matt-pocock-skills
description: Configure this repo for the engineering skills — set up its Hermes Kanban issue tracker and domain doc layout. Run once before first use of the other engineering skills.
disable-model-invocation: true
---

# Setup Matt Pocock's Skills

Scaffold the per-repo configuration that the engineering skills assume:

- **Issue tracker** — where issues live. This tap fixes it to **Hermes Kanban**: every open issue is a board card/task, and there is no second medium (no GitHub Issues, no local markdown).
- **Domain docs** — where `CONTEXT.md` and ADRs live, and the consumer rules for reading them.

This is a prompt-driven skill, not a deterministic script. Explore, present what you found, confirm with the user, then write.

## Process

### 1. Explore

Look at the current repo to understand its starting state. Read whatever exists; don't assume:

- `git remote -v` and `.git/config` — is this a GitHub/GitLab repo? (Informational only — the issue tracker is Hermes Kanban regardless.)
- `AGENTS.md` and `CLAUDE.md` at the repo root — does either exist? Is there already an `## Agent skills` section in either?
- `CONTEXT.md` and `CONTEXT-MAP.md` at the repo root
- `docs/adr/` and any `src/*/docs/adr/` directories
- `docs/agents/` — does this skill's prior output already exist?
- `.scratch/` — sign that a local-markdown issue tracker convention was previously in use (this tap replaces it with Hermes Kanban)
- Is the `triage` skill installed? (a `triage` skill folder alongside this one, or `triage` in your available skills.) This decides whether Section B runs at all.
- Monorepo signals — a `pnpm-workspace.yaml`, a `workspaces` field in `package.json`, or a populated `packages/*` with its own `src/`. Present only in a genuinely large multi-package repo; their absence means single-context, which is almost every repo.

### 2. Present findings and ask

Summarise what's present and what's missing. Then take the sections in order — one section, one answer, then the next.

Lead each section with the recommended answer so the user can accept it in a word. Give a one-line explainer only when the choice genuinely branches; skip the section entirely when exploration already settled it (Section B when `triage` isn't installed, Section C when there's no monorepo).

**Section A — Issue tracker (Hermes Kanban).**

> Explainer: The "issue tracker" is where issues live for this repo. Skills like `to-tasks`, `triage`, and `to-spec` read from and write to it — they call the Hermes Kanban board, not `gh` or a markdown file. Pick the board this repo actually uses.

This tap fixes the issue tracker to **Hermes Kanban**. Ask only for the two repo-specific facts the board needs, then write `docs/agents/issue-tracker.md` from the inline template below (the template is self-contained — pasted under "Write", no external file to read):

- **Board slug** — the board this repo's cards live on (e.g. `default`, or a named board). Resolve it at runtime from `HERMES_KANBAN_BOARD` / `HERMES_KANBAN_DB`; if unset, Hermes uses the active/current board.
- **Tenant** — the namespace this repo's board lives under. Record the convention the user wants (e.g. the repo slug); it resolves from the per-repo config at publish time.
- **Notifier / subscription** — the maintainer receives board activity through their Hermes **gateway notifier** (the agent's own delivery channel — Telegram/Discord/etc. wired to the gateway), not a third-party issue-tracker webhook. Note that no separate issue-tracker integration is needed.

The triage-role → board-status mapping is **authoritative and fixed by this tap** (it lives inline in the template and in the `triage` skill) — do not re-open it as a menu. You may record overrides only if the repo's board already uses different status strings; otherwise write the table as given.

**Section B — Triage roles.** Skip this section entirely if the `triage` skill isn't installed (exploration told you) — an uninstalled skill needs no roles.

If it is installed, show the user the triage-role → board-status mapping that this tap fixes (the table in the `docs/agents/issue-tracker.md` template below) and confirm it matches their board. Ask exactly one question:

> Does your board already use different status strings than the defaults? (recommended: **no** — write the mapping as-is.)

On **yes**, collect the overrides so `triage` applies the existing statuses instead of the defaults. The mapping lives in `docs/agents/issue-tracker.md`; there is no separate `triage-labels.md` (it was merged into that doc).

**Section C — Domain docs.** Default to **single-context** — one `CONTEXT.md` + `docs/adr/` at the repo root. This fits almost every repo; write it without asking.

Offer **multi-context** — a root `CONTEXT-MAP.md` pointing to per-context `CONTEXT.md` files — only when exploration found monorepo signals. Then confirm which layout they want.

### 3. Confirm and edit

Show the user a draft of:

- The `## Agent skills` block to add to whichever of `CLAUDE.md` / `AGENTS.md` is being edited (see step 4 for selection rules)
- The contents of `docs/agents/issue-tracker.md` and `docs/agents/domain.md`

Let them edit before writing.

### 4. Write

**Pick the file to edit:**

- If `CLAUDE.md` exists, edit it.
- Else if `AGENTS.md` exists, edit it.
- If neither exists, ask the user which one to create — don't pick for them.

Never create `AGENTS.md` when `CLAUDE.md` already exists (or vice versa) — always edit the one that's already there.

If an `## Agent skills` block already exists in the chosen file, update its contents in-place rather than appending a duplicate. Don't overwrite user edits to the surrounding sections.

The block:

```markdown
## Agent skills

### Issue tracker

Issues live on this repo's Hermes Kanban board. See `docs/agents/issue-tracker.md`.

### Domain docs

[one-line summary of layout — "single-context" or "multi-context"]. See `docs/agents/domain.md`.
```

Then write the docs files. **`docs/agents/issue-tracker.md`** is written from the inline template below — self-contained, no external link to read. **`docs/agents/domain.md`** is written from its inline template (step 5).

#### `docs/agents/issue-tracker.md` — inline template

```markdown
# Issue Tracker: Hermes Kanban

The issue tracker for this repo is **Hermes Kanban**. Every open issue is a board
card/task; there is no second medium (no GitHub Issues, no local markdown). Skills
like `/triage`, `/to-tasks`, and `/to-spec` read from and write to this board.

## Board

- **Board slug:** `<board-slug>` — e.g. `default`, or a named board. Resolve at
  runtime from `HERMES_KANBAN_BOARD` / `HERMES_KANBAN_DB`; if unset, Hermes uses
  the active/current board.
- **Tenant:** `<tenant>` — the namespace this repo's board lives under (set
  per-repo; resolves from this config at publish time).

## Notifier / subscription

- Board activity reaches the maintainer through their Hermes **gateway notifier**
  (the agent's own delivery channel — Telegram/Discord/etc. wired to the gateway),
  not a third-party issue-tracker webhook.
- To get notified on new cards or status changes, subscribe via the gateway
  notifier for this tenant; there is no separate issue-tracker integration to
  configure.

## Triage roles → board status (authoritative)

Two **category** roles, recorded as a `Category:` body line on each card:

| Category role | Card body line      |
| ------------- | ------------------- |
| `bug`         | `Category: bug`     |
| `enhancement` | `Category: enhancement` |

Five **state** roles, each mapping onto a Hermes Kanban status:

| Triage role       | Board status               | Meaning                                                             |
| ----------------- | -------------------------- | ------------------------------------------------------------------- |
| `needs-triage`    | `triage`                   | Maintainer needs to evaluate this card.                             |
| `needs-info`      | `blocked(kind=needs_input)`  | Waiting on the reporter for more information.                    |
| `ready-for-agent` | `ready`                    | Fully specified, ready for an AFK agent to pick up.                 |
| `ready-for-human` | `blocked(kind=capability)`   | Requires human implementation (judgment, external access, design). |
| `wontfix`         | `archived`                 | Will not be actioned.                                               |

`ready-for-human` maps to `blocked(kind=capability)`, **not**
`blocked(kind=needs_input)` — it means the work is understood but needs a human,
not that it is waiting on a question. A `blocked(kind=needs_input)` card is always
the `needs-info` role.

When a skill mentions a triage role (e.g. "apply the AFK-ready status"), use the
corresponding board status from this table.

PRs are **not** board cards — a human files a card for external contributions; do
not create board cards from pull requests automatically.
```

### 5. Write — domain docs

Write `docs/agents/domain.md` from this inline template (the consumer rules are stable across repos; only the layout branch differs):

```markdown
# Domain Docs

How the engineering skills should consume this repo's domain documentation when
exploring the codebase.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root, or
- **`CONTEXT-MAP.md`** at the repo root if it exists — it points at one
  `CONTEXT.md` per context. Read each one relevant to the topic.
- **`docs/adr/`** — read ADRs that touch the area you're about to work in. In
  multi-context repos, also check `src/<context>/docs/adr/` for context-scoped
  decisions.

If any of these files don't exist, **proceed silently**. Don't flag their absence;
don't suggest creating them upfront. The `/domain-modeling` skill creates them
lazily when terms or decisions actually get resolved.

## File structure

Single-context repo (most repos):

```
/
├── CONTEXT.md
├── docs/adr/
│   ├── 0001-event-sourced-orders.md
│   └── 0002-postgres-for-write-model.md
└── src/
```

Multi-context repo (presence of `CONTEXT-MAP.md` at the root):

```
/
├── CONTEXT-MAP.md
├── docs/adr/                          ← system-wide decisions
└── src/
    ├── ordering/
    │   ├── CONTEXT.md
    │   └── docs/adr/                  ← context-specific decisions
    └── billing/
        ├── CONTEXT.md
        └── docs/adr/
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a
hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to
synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal — either you're
inventing language the project doesn't use (reconsider) or there's a real gap (note
it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than
silently overriding:

> _Contradicts ADR-0007 (event-sourced orders) — but worth reopening because…_
```

### 6. Done

Tell the user the setup is complete and which engineering skills will now read from these files. Mention they can edit `docs/agents/*.md` directly later — re-running this skill is only necessary if they want to switch issue trackers or restart from scratch.
