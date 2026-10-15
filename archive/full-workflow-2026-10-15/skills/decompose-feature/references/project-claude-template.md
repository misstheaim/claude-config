# Project CLAUDE.md template

Keep it short: it loads into every session. Facts that change often or need detail live in `docs/development.md` and the plan, not here.

```markdown
# <Project name>

<One paragraph: what the project is, for whom, and its current milestone.>

## Stack

- <language, framework, database, hosting, test framework, with versions>

## Workflow (must follow)

- **Base branch: `develop`.** Create every ticket branch from the latest `origin/develop` (`git fetch origin develop` first). Hotfix tickets (label `hotfix`) branch from the latest `origin/main` instead.
- PRs target `develop`, except release and hotfix PRs, which target `main`.
- Never commit directly to `main` or `develop`. Never merge into `main` or `release/*`, push tags or publish releases without the owner's explicit approval.
- Full workflow, commands and requirements:

@docs/development.md

## Plan and tickets

- Plan: `docs/plans/<slug>.md` (decisions, architecture, every task's details).
- Tickets: GitHub issues in `<OWNER/REPO>`, GitHub Project `<title>`. Each task ticket's test cases must all pass as automated tests before it closes.

## Conventions

- <project structure: where code, tests and assets go>
- <architecture rules from the plan's decisions, e.g. "UI never calls the database directly">
- <test naming and location; test case IDs in test names>

## Gotchas

<Non-obvious things learned while working on the project. Add them as they come up.>
```
