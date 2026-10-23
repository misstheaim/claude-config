# Main plan template (`docs/plans/README.md`)

The main plan describes the whole project and links to one area plan per area (`references/area-plan-template.md`). Cross-area things live here: the goal, the areas, decisions that span areas, the contracts between areas, milestones and the **order of work**. Everything inside one area lives in its area plan.

A small project (one or two areas, about 15 tasks or fewer) may keep its areas inline, as `## Area: <name>` sections at the end of this file in the area plan's format, and split them out once it grows.

```markdown
# <Project name>: plan

> Status: Draft | In review | Approved | Tickets created
> Last updated: <YYYY-MM-DD>
> Behaviour spec: `docs/spec/README.md` (what is implemented now; this plan says what will change)

## 1. Context and goal

- **Problem / motivation:** why this is being built.
- **Users and main use cases:** who uses it and how.
- **Goal:** what is true when it's done.
- **In scope / out of scope:** for this version.

## 2. Current state

Existing project: the architecture, its parts and conventions (with paths), and the current behaviour by reference to the spec's areas. New project: the chosen stack and the best practices it follows (with sources).

## 3. Areas

| Area | Plan | Spec | Owns | Epic | Status |
|---|---|---|---|---|---|
| <review> | [review.md](review.md) | `docs/spec/review.md` | <what it's responsible for, one line> | #N | planned / decomposed / tickets created |

## 4. Decisions (cross-area)

| # | Decision | Chosen option | Alternatives considered | Why |
|---|---|---|---|---|
| D1 | | | | |

Area plans number their own decisions (`review.D1`).

## 5. Architecture

- Components and how they interact (a diagram in Mermaid if it helps).
- **Contracts between areas:** APIs, file formats, protocols, shared data model. An area plan may refine its side, never change a contract alone.
- **Non-functional requirements:** security, performance, offline, scale.
- **Testing strategy:** unit, integration, end-to-end; what each level covers; how time, randomness and external services are controlled in tests.

## 6. Order of work

Waves of tasks across all areas, each starting once its dependencies are done. Tasks are named by area (`review.T3`) and issue.

| Wave | Tasks | Notes |
|---|---|---|
| 1 | review.T1 (#N), cli.T1 (#N) | <bootstrap, spikes, why this order> |

**Releases:** each milestone, its version and its tasks.

| Milestone | Version | Tasks | Goal |
|---|---|---|---|
| <MVP> | <0.1.0> | <review.T1-T6, cli.T1-T3> | <one line> |

## 7. Risks and open questions (cross-area)

| Risk / question | Impact | Mitigation / owner |
|---|---|---|

## 8. Review notes

Summary of the test design and of the independent reviews (per session): accepted points and points rejected (with the reason).
```
