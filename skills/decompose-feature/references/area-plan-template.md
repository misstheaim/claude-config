# Area plan template (`docs/plans/<area>.md`)

One file per area, linked from the main plan (`references/plan-template.md`). It holds everything an implementing session needs for that area: its design, its tasks and how each task changes the behaviour spec. The order of work stays in the main plan.

```markdown
# <Project name> · <Area>: plan

> Main plan: [README.md](README.md) · Spec: `docs/spec/<area>.md` · Epic: #N
> Status: Draft | In review | Approved | Tickets created
> Last updated: <YYYY-MM-DD>

## 1. Goal and scope

What this area delivers, for whom, what's in and out of this version, and how it depends on other areas (by the contracts in the main plan, §5).

## 2. Current state

The code it touches (paths, conventions), and the current behaviour by spec ID (`REVIEW-003`, `REVIEW-007`), not restated.

## 3. Decisions

| # | Decision | Chosen option | Alternatives considered | Why |
|---|---|---|---|---|
| <area>.D1 | | | | |

## 4. Design

- Components and how they interact.
- **Data model:** entities, fields, relations, migrations.
- **API and contracts:** this area's side of the main plan's contracts; its own endpoints, commands, formats.
- **UI:** screens, flows, states (loading, empty, error).
- **Security, performance and other non-functional requirements.**

## 5. Work breakdown

```
[Epic] <area> (#N)
├── [Story] <name> (#N)
│   ├── [Task][backend] <name> (#N)
│   └── [Task][frontend] <name> (#N)
└── ...
```

Then, for every task:

### <area>.T<n>. <Task title>  `area` · parent: <story> · issue: #N
- **Goal:** one sentence.
- **Details:** what to build, files and modules to touch, contracts to follow.
- **Acceptance criteria:**
  - [ ] AC1: ...
- **Spec changes** (`docs/spec/<area>.md`; format: `init-spec/references/spec-format.md`):
  - `<AREA>-012` new: <the statement as it will read in the spec>
  - `<AREA>-004` changed: <the new statement>
  <or "none (no behaviour change)">
- **Depends on:** <area>.T<n>, other areas' tasks by name (or none). **Can run in parallel with:** ...
- **Suggested model:** <tier> (confidence: <level>). <reason>

## 6. Risks and open questions

| Risk / question | Impact | Mitigation / owner |
|---|---|---|
```
