---
name: create-ticket
description: Create one ticket (or a few closely related ones) for work that's already understood - a bug, a small change, a follow-up, a chore - in any project, following that project's own rules. Detects how the project works and adapts - the decompose-feature conventions (plan, spec deltas, type/area labels, sub-issues, suggested model) in the user's personal projects built with it, the documented or observed conventions of any other project (issue templates, CONTRIBUTING, existing tickets, Jira), or a sensible default when there are none. Use when the user asks to create, write, file, open or add a ticket, issue or bug report, e.g. "create a ticket for the login timeout", "file a bug for this", "add an issue to fix X". Do NOT use for decomposing a feature or project into many tickets or designing a feature (decompose-feature), for editing an existing ticket, or for implementing one (implement-ticket).
argument-hint: "<what the ticket is for> [repo=OWNER/REPO | tracker=jira PROJ] [parent=#N]"
---

# Create a ticket

Request: `$ARGUMENTS` (if empty, ask what the ticket is for).

Write the ticket a developer, or a fresh Claude session with none of today's context, can pick up and finish. The work should already be understood: this skill turns it into a good ticket, it doesn't design a feature.

**Every step adapts to the project.** Projects differ: some have a plan, a spec, `docs/development.md`, issue templates or a Jira workflow, others have none of these. Don't assume any of them exists, and never add a section, label or link whose source the project doesn't have. Find out how this project works, then follow it.

## 1. Check the scope

- **One ticket, or a few closely related ones** (a bug and its follow-up, a change split by area): continue.
- **The work needs design decisions, or is a story's worth of tasks** (new architecture, several modules, open product questions): say so and stop.
  - Personal project: recommend `/decompose-feature` (its light path handles about 3 tasks with a short design discussion).
  - Enterprise project: offer an epic or story ticket with the open questions listed in it, or a split the user agrees on.

## 2. Find the project and the tracker

- **Project:** the current folder, or the one the user names (`C:\Users\User\Documents\Projects\<name>`). Repo: `gh repo view --json nameWithOwner,owner,defaultBranchRef`.
- **Personal or enterprise:** personal when the repo is owned by the user's own GitHub account; enterprise when it belongs to a company organization or a company tracker (Jira board). If you can't tell, ask. It decides two things: whether the decompose-feature conventions can apply at all, and whether the ticket gets a "Suggested model" (personal only, per CLAUDE.md).
- **Tracker:** what the user said wins. Otherwise look for it: the project's CLAUDE.md, CONTRIBUTING or `docs/` naming one (Jira, Linear, Azure DevOps), ticket keys like `PROJ-123` in recent branch names and commits (`git log --oneline -30`), or GitHub Issues being enabled and in use.
  - **GitHub Issues:** `gh`. Check `gh auth status` for the `project` scope if the repo uses a GitHub Project.
  - **Another tracker with a connected tool** (a Jira connector, for example): use it.
  - **No tool for it:** write the ticket ready to paste, field by field, and skip the creation steps.

## 3. Learn the project's rules

Read cheapest first, and stop once the picture is clear:
1. **The user's instructions** in this conversation.
2. **Documented rules:** the project's `CLAUDE.md` (and the files it imports), `CONTRIBUTING.md`, `docs/development.md`, and anything they point to about tickets: required fields, title style, labels, definition of done, language.
3. **Issue templates:** `.github/ISSUE_TEMPLATE/*` (forms or markdown), `.github/ISSUE_TEMPLATE.md`. Pick the one that fits (bug, feature, task).
4. **Tracker setup:** `gh label list`, milestones (`gh api repos/<repo>/milestones --jq '.[].title'`), the GitHub Project (`gh project list --owner <owner>`); for Jira, the project's issue types, required fields and components.
5. **Existing tickets:** the last 15 (`gh issue list -R <repo> --state all --limit 15 --json number,title,labels,milestone`), and the bodies of 3-5 recent ones of the same kind. Note the title style, sections, labels, language, and how they link parents and dependencies.
6. **Plan and spec:** whether `docs/plans/` (a main plan `README.md` with area plans, or an older single document) and `docs/spec/README.md` exist on the base branch.

Then **choose the approach** and tell the user in 2-3 lines which one and why:

- **A. Decompose-feature conventions:** a personal project where the decomposer's traces are present: a plan in `docs/plans/`, `type:`/`area:` labels, or tickets in its template (Goal, Context, Implementation notes, Spec changes, Plan). Follow §5A.
- **B. The project's own conventions:** documented rules, issue templates or a consistent pattern in existing tickets. Follow them (§5B). This is always the approach in enterprise projects, even if they look similar to the decomposer's.
- **C. Default:** nothing usable found. Use the default ticket (§5C), and match whatever little exists (label names, title style).

**When sources disagree:** the user's instructions, then the project's documented rules and templates, then the decomposer conventions (A only), then the pattern in existing tickets, then the default. A personal decomposer project can still have its own rules in CLAUDE.md; those win over the template.

**Use only what exists.** Under A, a project without a spec gets no "Spec changes" section (say why in one line); without a plan, no "Plan" reference and no plan update; without milestones, no milestone. Under B and C, never bring in the decomposer's labels, sections or spec deltas.

## 4. Understand the work

- **Check for duplicates:** `gh issue list -R <repo> --state all --search "<keywords>"` (or the tracker's search). If one exists, show it and ask whether to update it instead (this skill doesn't edit tickets) or create a new one.
- **Read the code it touches,** enough to name the files and modules and describe the approach. For a broad search, use an `Explore` subagent with `model: "sonnet"` and ask for a compact answer (paths, lines, a few lines of explanation).
- **Read the context that exists:** the spec items for the behaviour involved (`docs/spec/<area>.md`), the plan's area section, related tickets.
- **Bugs:** find the steps to reproduce, the expected and actual behaviour, and, from the code, the likely cause. Say which parts are confirmed and which are guesses.
- **Ask only what changes the ticket:** scope, expected behaviour, priority, where it belongs (parent, milestone). Usually 0-3 questions, each with your recommended answer. Decide technical details yourself and put them in the implementation notes.

## 5. Write the ticket

**Always**, whatever the approach:
- a short, specific title in the project's style;
- self-contained: someone without today's conversation can do it from the ticket (and the plan or spec section it cites);
- acceptance criteria that can be checked, numbered `AC1`, `AC2`, ...;
- concrete pointers: files, modules, commands, links to related tickets;
- one session's work. If it isn't, split it, or go back to §1.

### 5A. Decompose-feature conventions

Read `~/.claude/skills/decompose-feature/references/ticket-template.md` and `references/github.md` there, and follow them:
- **Body:** the task template. A bug still uses it: the steps to reproduce, expected and actual behaviour go in Context.
- **Tests, as the installed decomposer says:** the light version (no `references/test-cases.md` next to the template) plans no tests, so no test cases; acceptance criteria are checked in the code, with a command, or by a manual step. The full version (restored from the archive, with `references/test-cases.md`) gets the test case table it describes.
- **Labels:** `type:task` (the coordinator queues only tasks) and exactly one `area:` label from the repo's existing ones. Add `hotfix` only for an urgent fix to a released version.
- **Parent:** the story or epic it belongs to, as a sub-issue (`gh issue list -R <repo> --label type:story --state open`, then epics). Recommend one; create no new epic or story for a single ticket.
- **Dependencies:** blocked-by links on the issues it waits for, plus "Blocked by #N" in the body.
- **Milestone:** the one its parent's tasks are in, or the one the user picks.
- **Spec changes** (only with `docs/spec/`): how each item reads afterwards, in the format of `~/.claude/skills/init-spec/references/spec-format.md`. New IDs continue after the highest one of the area in `docs/spec/` and in `docs/plans/`. A bug fix that restores the specified behaviour: "None (restores `<ID>`)", and drop its line from the area's "Known issues" if it's there.
- **Plan update** (only with `docs/plans/`): the coordinator orders tickets by the plan and its implementers read the plan, so the task goes in too. Add it to its area plan (the hierarchy in §5 and a task entry `<area>.T<next>` in the area plan's format, with the issue number) and to the main plan's order of work (the earliest wave after its dependencies). An older single plan document is updated in place.
- **Suggested model:** per CLAUDE.md, sized to the task.

### 5B. The project's own conventions

- Use its template or the sections its recent tickets use, in its language and title style. Fill every required field; when you can't, ask the user for it.
- Its labels, issue types, components and priorities, only existing ones. If a label you'd need doesn't exist, ask instead of creating it.
- Tests, definition of done, estimates: as its rules and tickets do. The "no automated tests" rule of the user's own workflow doesn't apply here.
- Link parents and dependencies the way its tickets do.
- **No "Suggested model"** in enterprise projects. A personal project with its own conventions gets one.

### 5C. Default

```markdown
## Context
<why this is needed; for a bug: steps to reproduce, expected, actual, environment>

## Goal
<one or two sentences: the outcome>

## Implementation notes
- Files / modules: `path/...`
- Approach: <a few bullets>

## Acceptance criteria
- [ ] AC1: ...

## Related
<linked tickets, docs, logs; or omit>
```

Plus "Suggested model" in a personal project. Labels only if fitting ones exist (`bug`, `enhancement`).

## 6. Approval

Creating a ticket changes a remote tracker, so ask first, showing:
- where: the tracker, repo or project, and (GitHub) the Project board;
- the title and the full body;
- labels, milestone, parent, blocked-by links, and any label the project's rules need created (under A, from the colours in `github.md`);
- under A with a plan: the plan changes, and how they reach the base branch (next step).

After approval, create exactly that. Without a tracker tool, hand over the paste-ready ticket instead and stop.

## 7. Create and finish

- **GitHub:** write the body to a scratchpad file and use the commands in `~/.claude/skills/decompose-feature/references/github.md`: create the issue, add it to the Project, link the parent as a sub-issue and the blockers. A `422` can mean too fast: wait and retry once.
- **Other trackers:** through the connected tool, with the fields agreed.
- **Plan (A only):** write the issue number into the plan entries. The coordinator only sees the plan on `origin/<base>`, so propose a `docs/` branch from the latest base and a PR into it (commit `docs(#<n>): add <task> to plan`, base branch per the project's workflow). That's a commit, push and PR, so it needs the user's explicit go-ahead, as one batch; it can go with the §6 approval. If the user declines, say that the coordinator will place the ticket by its dependencies instead of the plan, and its implementer won't find a plan entry.
- **Report:** the ticket link, its labels, parent and milestone, and the PR link if there is one.
