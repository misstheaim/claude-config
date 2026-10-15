# <Feature / project name>: implementation plan

> Status: Draft | In review | Approved | Tickets created
> Last updated: <YYYY-MM-DD>
> Root issue: <#N or "n/a">

## 1. Context and goal

- **Problem / motivation:** why this is being built.
- **Users and main use cases:** who uses it and how.
- **Goal:** what is true when it's done.
- **In scope / out of scope:** for this version.

## 2. Current state

Existing project: relevant architecture, modules, conventions and files this feature touches (with paths).
New project: the chosen stack and the best practices it follows (with sources).

## 3. Decisions

| # | Decision | Chosen option | Alternatives considered | Why |
|---|---|---|---|---|
| D1 | | | | |

## 4. Architecture and design

- Components and how they interact (a diagram in Mermaid if it helps).
- **Data model:** entities, fields, relations, migrations.
- **API contracts:** endpoints, request/response shapes, errors.
- **UI:** screens, flows, states (loading, empty, error).
- **Security, performance and other non-functional requirements.**
- **Testing strategy:** unit, integration, end-to-end; what each level covers; how time, randomness and external services are controlled in tests.

## 5. Work breakdown

Hierarchy overview:

```
[Epic] <name> (#N)
├── [Story] <name> (#N)
│   ├── [Task][backend] <name> (#N)
│   └── [Task][frontend] <name> (#N)
└── [Story] <name> (#N)
    └── ...
```

Then, for every task:

### T<n>. <Task title>  `area` · parent: <story> · issue: #N
- **Goal:** one sentence.
- **Details:** what to build, files and modules to touch, contracts to follow.
- **Acceptance criteria:**
  - [ ] AC1: ...
- **Test cases:** (format and rules: `references/test-cases.md` of the decompose-feature skill)

  | ID | Kind | Level | Given / When / Then | Covers |
  |---|---|---|---|---|
  | T<n>-TC01 | happy | | | AC1 |

- **Depends on:** T<n>, ... (or none). **Can run in parallel with:** T<n>, ...
- **Suggested model:** <tier> (confidence: <level>). <reason>

## 6. Order of work

Phases or waves of tasks that can start once their dependencies are done.

**Releases:** each milestone, its version and the tasks in it.

| Milestone | Version | Tasks | Goal |
|---|---|---|---|
| <MVP> | <0.1.0> | T1–T8 | <one line> |

## 7. Risks and open questions

| Risk / question | Impact | Mitigation / owner |
|---|---|---|

## 8. Review notes

Summary of the test design (problems found and how they were resolved) and of the independent review: accepted points and points rejected (with the reason).
