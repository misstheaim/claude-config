# Behaviour spec format

The spec describes how the product behaves **now**: only what's implemented and merged into the base branch. What will change lives in the plan, as **spec deltas** on its tasks (`decompose-feature`). After the code is in, the spec is updated to match: by the coordinator's spec update after a wave, by `implement-ticket` in an interactive session, or by whoever changes behaviour in a session without a skill (the project's CLAUDE.md says so).

**The code is the source of truth.** Every statement in the spec must hold in the code on the base branch. When a plan delta, a ticket or an older statement disagrees with the code, the spec follows the code and the difference is reported.

## Layout

```
docs/spec/README.md        the index: the whole product in brief, the areas, the glossary, how to edit
docs/spec/<area>.md        the behaviour of one area
```

Areas follow the plan's areas (and the issues' `area:` labels) where the project has them, so the plan for an area produces deltas for the spec file of the same name. A product area, not a code folder: "review", "settings", "plugin", "cli". Split an area file that grows past about 600 lines into sub-areas (`review-tree.md`, `review-codelens.md`) and list each in the index.

## What goes in (behaviour, not implementation)

- what a user sees and can do: screens, views, commands, menus, settings with their defaults, messages, states (empty, loading, error);
- external contracts: CLI commands and flags, APIs and endpoints, file formats and locations, protocols between components, environment variables;
- rules and limits: validation, ordering, sizes, timeouts, permissions, what happens on errors;
- invariants that must survive refactors ("a decision is never lost when the store is rebuilt").

**Leave out** class and function names, internal module structure, refactors and performance internals (unless a user-visible limit). They change without changing behaviour. The plan and the code hold them.

## `docs/spec/README.md`

```markdown
# <Product>: behaviour spec

> What <product> does **now**: only implemented behaviour. Planned changes are in `docs/plans/`, as spec deltas on their tasks.
> Synced to: `<short sha>` (<YYYY-MM-DD>): every change on `<base>` up to this commit is reflected here.

## Overview

<One paragraph: what the product is, for whom, its parts and how they fit.>

## Areas

| Area | File | Covers |
|---|---|---|
| Review | [review.md](review.md) | <one line> |

## Glossary

| Term | Meaning |
|---|---|
| <term the spec uses> | <one line> |

## How to edit this spec

- Describe behaviour, never implementation: what a user or another component observes.
- One item per behaviour: `### <AREA>-<NNN> <short name>`, then 1-6 lines of plain statements with concrete values (defaults, limits, exact messages where they matter), then `Since: #<issue>` (and `Changed: #<issue>, ...` later).
- **New behaviour:** a new item with the next free ID of its area. **Changed:** edit the item in place and add the issue to `Changed:`. **Removed:** delete the item and add its ID to the area's `Retired IDs` line. IDs are never reused.
- Update the spec in the same change as the code. Tickets run by the `/coordinator` are the exception: it updates the spec after each wave.
- Every statement must be true in the code on `<base>`. If you find one that isn't, fix it.
```

Leave `Synced to` alone when you edit the spec by hand alongside a code change; the coordinator's spec update sets it.

## `docs/spec/<area>.md`

```markdown
# <Area name>

<2-5 lines: what this area is for and how a user meets it.>

> Code: `<folder or entry point>`, `<…>` (pointers for orientation, not part of the contract)

## Behaviour

### <AREA>-001 <short name>
<Plain statements. "When the user …, the view shows …". Defaults and limits as numbers.>
Since: #<issue>

### <AREA>-002 <short name>
…
Since: #<issue> · Changed: #<issue>

## Known issues

- <Behaviour that is confirmed broken, with its follow-up issue: "Reset leaves the hunk highlighted (#153)". Removed once fixed.>

Retired IDs: <AREA>-007
```

- **IDs:** the area's short uppercase name and a 3-digit number, e.g. `REVIEW-012`, `CLI-003`. Group items under `###` order by number; add `##` sub-headings inside `Behaviour` when an area has distinct parts.
- **`Since:`** the issue that introduced the behaviour. A spec written from existing code (`init-spec`) uses `Since: before spec` when it can't tell.
- **Size:** most items are 1-4 lines. A spec is read often; keep it skimmable.

## Spec deltas (in the plan and the tickets)

Each task that changes behaviour lists its deltas, so the spec update afterwards is mechanical:

```markdown
- **Spec changes** (`docs/spec/<area>.md`):
  - `REVIEW-012` new: <the statement as it will read in the spec>
  - `REVIEW-004` changed: <the new statement>
  - `REVIEW-002` removed: <why>
```

Or `- **Spec changes:** none (no behaviour change)`. New IDs continue the area's numbering, counting IDs already reserved in other open plans (search `docs/plans/` and `docs/spec/` for `<AREA>-`).

## Section for the project's CLAUDE.md

Every project with a spec carries this section in its CLAUDE.md, so a session that changes behaviour without any skill keeps the spec current:

```markdown
## Behaviour spec

- `docs/spec/README.md` describes how the product behaves **now**, one file per area; the plans in `docs/plans/` describe what will change.
- **Any change to behaviour updates the spec in the same change**: the affected items in `docs/spec/<area>.md` (new item with the next free ID, edit in place, or retire the ID). Format and rules: "How to edit this spec" in `docs/spec/README.md`.
- Exception: ticket implementers run by `/coordinator` don't edit `docs/spec/`; the coordinator updates it after each wave.
```
