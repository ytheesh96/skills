# Relentless design interview pattern for implementation plans

Use this pattern before creating implementation cards for safety-sensitive or architecture-changing work.

## Interview rules

- Ask one question at a time with a recommended answer first.
- If a question can be answered by reading the codebase, inspect the codebase instead of asking.
- Walk dependency order: product surface → backend/API boundary → data model → mutation semantics → safety/confirmation UX → scope/profile/board boundaries → testing/adoption/restart policy.
- Convert each answer into explicit acceptance criteria, not vague preferences.
- At the end, synthesize the locked decisions before creating cards.

## Kanban card synthesis pattern

Create one root card with the full decision record and definition of done, then child cards at reviewable boundaries. For a Desktop/backend feature, a useful split is:

1. Backend typed API/service.
2. Desktop route/inbox shell.
3. Action dialogs/evidence drawer.
4. Tests, smoke fixtures, and minimal parity surfaces.
5. Adoption, packaging/restart, docs, screenshots.

## Safety/adoption prompts to resolve explicitly

- Which checkout/repo is authoritative for live work?
- Are there dirty files or alternate dev checkouts that must not be touched?
- Is code auto-adoption allowed after tests?
- Are process restarts allowed automatically, and under what gate?
- What review gates should the work itself dogfood?
