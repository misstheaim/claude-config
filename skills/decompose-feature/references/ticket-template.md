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
Full details: `docs/plans/<slug>.md`

Stories are linked as sub-issues.
```

## Story

```markdown
## Outcome
<what a user or the system can do when this is done>

## Acceptance criteria
- [ ] AC1: ...

## Plan
`docs/plans/<slug>.md`, section <n>

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

## Dependencies
Blocked by #N. <or "None">

## Plan
`docs/plans/<slug>.md`, task T<n>

## Suggested model
**<Tier and version>** (confidence: <High|Medium|Low>). <one-line reason>
```
