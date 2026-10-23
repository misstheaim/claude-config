# Ticket templates

Titles: short and specific, in imperative or outcome form. No type prefix; the `type:` label says it.

## Epic

```markdown
## Goal
<what this epic delivers and why>

## Scope
- In: ...
- Out: ...

## Plan
Full details: `docs/plans/<area>.md` (main plan: `docs/plans/README.md`)

Stories are linked as sub-issues.
```

## Story

```markdown
## Outcome
<what a user or the system can do when this is done>

## Acceptance criteria
- [ ] AC1: ...

## Plan
`docs/plans/<area>.md`, section <n>

Tasks are linked as sub-issues.
```

## Task

The task will be implemented by a fresh session with no other context, so the body must stand on its own.

```markdown
## Goal
<one sentence>

## Context
<why this task exists and how it fits the story; the relevant decisions>

## Implementation notes
- Files / modules: `path/...`
- Contracts to follow: <API shape, schema, component props>
- Approach: <the agreed design, in a few bullets>

## Acceptance criteria
- [ ] AC1: ...
- [ ] AC2: ...

<Each criterion must be checkable without automated tests: in the code, with a command, or by a manual step. Add a `Verify:` note where how to check it isn't obvious.>

## Spec changes
How the behaviour spec (`docs/spec/<area>.md`) must read once this is merged. The code must match these; the spec itself is updated after the merge.
- `<AREA>-012` new: <statement>
- `<AREA>-004` changed: <new statement>

<or "None (no behaviour change)">

## Dependencies
Blocked by #N. <or "None">

## Plan
`docs/plans/<area>.md`, task <area>.T<n>

## Suggested model
**<Tier and version>** (confidence: <High|Medium|Low>). <one-line reason>
```
