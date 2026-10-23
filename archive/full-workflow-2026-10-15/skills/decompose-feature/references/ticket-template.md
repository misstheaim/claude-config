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

Story-level test cases (`<area>.S<n>-TC..`) live in the ticket of the story's last task.

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

## Spec changes
How the behaviour spec (`docs/spec/<area>.md`) must read once this is merged. The code must match these; the spec itself is updated after the merge.
- `<AREA>-012` new: <statement>
- `<AREA>-004` changed: <new statement>

<or "None (no behaviour change)">

## Test cases
Every case must be implemented as an automated test and pass. Don't change a case's expected behaviour; if one looks wrong, report it.

| ID | Kind | Level | Given / When / Then | Covers |
|---|---|---|---|---|
| <area>.T<n>-TC01 | happy | <unit\|integration\|e2e> | Given ..., when ..., then ... | AC1 |
| <area>.T<n>-TC02 | edge | ... | ... | AC2 |

<or "None (<reason>)", with a `Verify:` line on each acceptance criterion>

## Dependencies
Blocked by #N. <or "None">

## Plan
`docs/plans/<area>.md`, task <area>.T<n>

## Suggested model
**<Tier and version>** (confidence: <High|Medium|Low>). <one-line reason>
```
