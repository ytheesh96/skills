# Matt Pocock Skills

A collection of agent skills (slash commands and behaviors) loaded by Claude Code. Skills are organized into buckets and consumed by per-repo configuration emitted by `/setup-matt-pocock-skills`.

## Language

**Issue tracker**:
Hermes Kanban — one board per repo. The tool that hosts a repo's issues; skills like `to-tasks`, `to-spec`, and `triage` read from and write to it.
_Avoid_: listing Jira, Asana, Trello, or GitHub Projects as live options; backlog manager, backlog backend, issue host

**Issue**:
A single tracked unit of work inside an **Issue tracker** — a Hermes Kanban card/task (a bug, feature, spec, or slice produced by `to-tasks`).
_Avoid_: ticket (use only when quoting external systems that call them tickets, or for a **Decision ticket** — see below)

**Decision ticket**:
A `wayfinder` planning term — a unit holding a *question* whose resolution is a decision, not a slice of a build to execute. It resolves questions and is distinct from a **task**; `wayfinder` introduces the term, then uses "ticket".

**Triage role**:
A triage-phase state of an **Issue**, mapped to a native Hermes Kanban status: `needs-triage` → `triage`; `needs-info` → `blocked` (`needs_input`); `ready-for-agent` → `ready`; `ready-for-human` → `blocked` (`capability`); `wontfix` → `archived`.

## Relationships

- An **Issue tracker** holds many **Issues**
- An **Issue** carries one **Triage role** at a time
- A **Decision ticket** is an **Issue** (a child of a `wayfinder:map`)

## Flagged ambiguities

- "backlog" was previously used to mean both the *tool* hosting issues and the *body of work* inside it — resolved: the tool is the **Issue tracker**; "backlog" is no longer used as a domain term.
- "backlog backend" / "backlog manager" — resolved: collapsed into **Issue tracker**.
