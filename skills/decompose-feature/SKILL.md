---
name: decompose-feature
description: PERSONAL PROJECTS ONLY. Decompose a new project or a feature into a hierarchy (epics, stories, session-sized tasks) with a plan document and GitHub tickets; a new project also gets its docs/development.md (Git Flow branching, releases) and CLAUDE.md. No test cases or automated tests are planned. Large features get the full process; small features (about 3 tasks or fewer) take a light path that still discusses the design with the user, updates the plan and creates the tickets, but skips the heavy analysis and the reviewer subagent. Use when the user asks to decompose, break down, plan into tickets or add a new feature to a project's plan, and only for the user's personal projects (their own GitHub account), never for enterprise or company work. Do NOT use for editing an existing ticket, for bug reports, or for implementing a task.
argument-hint: "[feature or project description]"
---

# Decompose a feature into tickets

Your job is to turn a big feature or a new project into a **well-designed high-level plan, split into pieces that separate Claude sessions will implement later**. Treat it as writing a plan whose points will each be executed by a different session that has none of today's context.

The plan's quality is the goal; the tickets are only its output. **Do not rush to tickets.** Most of the work is understanding the feature with the user.

**No automated tests.** The implementation workflow (`implement-ticket`, `/coordinator`) doesn't write or run tests. So don't create test cases, testing tasks, a testing strategy, test commands or instructions to write tests, in the plan, the tickets or the project files. Acceptance criteria are checked by reading the code, running a command, or a manual step.

Feature or project: `$ARGUMENTS` (if empty, ask what to decompose).

## Personal projects only

This skill is only for the user's **personal** projects. A personal project is one owned by the user's own GitHub account (or a new project they are starting for themselves), not by a company organization, a company Jira board or any other enterprise setup.

**Before anything else, confirm that this is a personal project.** Check what you can (the repo owner from `gh repo view`, the folder, what the user said), then ask the user to confirm it explicitly, even if it looks obvious. If it is enterprise or company work, or the user doesn't confirm, stop: tell them this skill is for personal projects only, and do not analyse, plan or create anything with it.

## Phase 1: Understand the context

- **Existing codebase:** analyse it, especially the parts the feature touches: architecture, layers, conventions, data model, existing similar features, tests, build and deploy setup. Note the concrete files and modules each part of the feature will change.
- **Empty folder / new project:** research current best practices on the web for the stack and the domain (project structure, libraries, auth, deployment). Cite what you base recommendations on.
- Look for an existing GitHub repo and Project for this work (`gh repo view`, `gh project list --owner <owner>`), so you know where tickets will go.

Give the user a short summary of what you found before moving on.

## Choose the path: full or light

Size the feature right after Phase 1 and tell the user which path you are taking and why (they can override it).

**Light path** when all of these hold:
- the work fits in about **3 tasks or fewer**;
- it needs no new architecture: it reuses the existing stack, modules and patterns, with at most one new module;
- the project already has a plan document, or the feature is simple enough to need only a short one.

Otherwise (a new project, a feature that needs several stories, new architecture, or a spike) take the **full path**: Phases 2 to 6 as written below.

### Light path

Spend effort in proportion to the feature. A small feature still needs a conversation and tickets, but not a big design process.
1. **Discuss (short Phase 2):** ask only the questions whose answers change the design or the scope, usually 2 to 4, with a recommended option for each. Raise real risks. Don't walk through alternatives for decisions that already follow from the plan.
2. **Place it in the hierarchy:** attach it to the existing epic it belongs to, as a new story, or add tasks to an existing story. Create a new epic only when the feature fits under none of them. Don't create an epic and a story for one or two tasks if an existing parent fits.
3. **Update the existing plan document** instead of writing a new one: add the new decisions (continue the numbering), a short design section, the new items in the hierarchy, the task details in the same format as the other tasks (leaving out any test cases or testing strategy the older plan has), and the order of work. If the project has no plan document, write a short one with only the sections the feature needs.
4. **Skip Phase 5:** no reviewer subagent, unless the user asks for one. Review your own tasks against the "Good tasks" rules instead.
5. **Create the tickets (Phase 6):** same rules: approval first, then the template, labels, sub-issue links, blocked-by links on existing issues, adding them to the Project, and writing the numbers back into the plan.

## Phase 2: Shape the feature with the user

Discuss, don't decide alone. Over as many rounds as needed:
- Ask about the goal, users, scope (what is in and out of the first version), constraints, non-functional needs (performance, security, offline, scale), and what "done" means.
- For every significant design decision (architecture, data model, libraries, API shape, UI approach, hosting), present the reasonable **alternatives** with concrete **pros and cons** for this project, and say which one you **recommend and why**. Wait for the user's choice.
- Raise risks, unknowns and things that need a spike (a short research task) early.
- **New project:** agree on the releases: which milestones (e.g. MVP, 1.0) and their versions (Semantic Versioning; recommend `0.1.0` for an MVP and `1.0.0` for the first stable release), and what goes into each. Explain the branching workflow from `references/development-template.md` (Git Flow: `main` holds only released, tagged code; `develop` integrates every ticket PR; short-lived `release/*` and `hotfix/*` branches) and confirm it, or agree on a simpler one if the user prefers.
- Keep a running list of decisions taken; it goes into the plan document.

Only move on when the feature is clear enough that you could explain every part of it to a developer who wasn't in the conversation.

## Phase 3: Build the hierarchy

Use three levels (GitHub sub-issues link them):

| Level | What it is | Example |
|---|---|---|
| **Epic** | A large feature or major area, delivering a big outcome | "User accounts" |
| **Story** | A sub-feature that delivers user-visible or system value on its own, written as an outcome | "Users can reset their password by email" |
| **Task** | One concrete piece of work that **one Claude session (Sonnet or Opus) can finish** | "Add password-reset token table and EF Core migration" |

Rules:
- **Root:** when adding a feature to an existing project, create one epic for the whole feature as the root, and link everything under it. For a new project there is no single root: the top-level epics (plus a "Project setup" epic for scaffolding, CI, environments) form the first level.
- **Bootstrap task (new project):** the first task of the "Project setup" epic, alone in the first wave, blocking everything else. It makes the repo ready for development:
  - the project skeleton for the chosen stack, with build, lint and run commands that work;
  - the **README**: what the project is, requirements, setup, how to build, run and lint, the project structure, and links to `docs/development.md` and the plan;
  - the real commands in `docs/development.md` and `CLAUDE.md`, replacing the planned ones.

  Keep it small enough for one Sonnet session: CI, environments and deployment go into their own tasks. Mark any manual step (an account, a secret, an install) in the ticket.
- **Milestones:** every task belongs to one milestone (release) from the plan.
- **Split until every leaf is session-sized.** That is the main test: if a piece could not realistically be finished and checked in a single session, split it further, into sub-stories or tasks. Add a level (story under story) only when a story is still too big; don't add levels for their own sake.
- **Good stories** are independent, valuable on their own, small enough to estimate and checkable (INVEST).
- **Good tasks:**
  - have one clear outcome and acceptance criteria that can be checked without automated tests (in the code, with a command, or by a manual step), numbered `AC1`, `AC2`, ...;
  - are self-contained: a fresh session must be able to do it from the ticket and the plan document alone;
  - touch one area where possible (backend, frontend, …). Split a cross-area piece into one task per area, linked by dependencies;
  - prefer thin vertical slices that keep the app working after each task, over "build all layers first".
- **Dependencies and order:** record which task blocks which, and mark which tasks can run in parallel. Put foundations (schema, contracts, shared components) first.
- **Area of every task** (one per task): `frontend`, `backend`, `database`, `cloud` (infrastructure, CI/CD, hosting), `assets` (images, icons, sounds, content), `design` (UX/UI design, mockups), `docs`. Add another area only if none fits.

## Phase 4: Write the plan document

Write a large, detailed Markdown document using `references/plan-template.md`:
- Existing project: `docs/plans/<feature-slug>.md` in the repo.
- New project: `docs/plans/<project-slug>.md` inside the new project folder.

It must be complete enough that each implementing session can rely on it: context, decisions with rationale, architecture, data model, API contracts, the full hierarchy with every task's details, dependencies, risks and open questions.

### New project: workflow files

A new project also gets two files in its folder, written now from the plan's decisions:
- **`docs/development.md`** from `references/development-template.md`: requirements, the planned commands, the branching workflow, the milestones with their versions, and the release, hotfix and approval rules. Adapt it to what was agreed; don't leave template placeholders in it.
- **`CLAUDE.md`** at the project root from `references/project-claude-template.md`: what the project is, the stack, the workflow rules (base branch `develop`, hotfixes from `main`), an import of `docs/development.md`, where the plan and tickets live, and the conventions from the plan's decisions.

An existing project without a `docs/development.md` or `CLAUDE.md`: offer to write them the same way, adapted to how the project already works; don't impose a new branching model on it.

Walk the user through the plan (and these files) and refine them until they are satisfied. Do not create anything on GitHub yet.

## Phase 5: Independent review (once)

When the user confirms the plan is ready for tickets:
1. Launch **one** subagent with the Agent tool: `subagent_type: "general-purpose"`, `model: "opus"`. It starts with a clean context, so its prompt must contain everything it needs and nothing more:
   - the absolute path of the plan document and of the project;
   - its role: an independent senior reviewer who must not edit any files;
   - what to check: gaps and missing work, wrong or risky design decisions, tasks too large for one session or too vague to implement without today's conversation, wrong dependencies or ordering, contradictions with the codebase, and acceptance criteria that can't be checked without automated tests;
   - what to return: a list of issues (each with severity, location in the plan, and a concrete fix) and a list of improvements, ordered by importance.
2. Weigh its output yourself: say which points you agree with, which you don't, and why.
3. Present this to the user and ask for final confirmation, updating the plan with what they accept.

If the user asks for more changes afterwards, make them **without** running the reviewer again, unless the user explicitly asks for another review.

## Phase 6: Create the tickets

Default target: GitHub Issues in the project's repo, added to its GitHub Project. Commands and label colours are in `references/github.md`.

- **Missing repo or Project:** if the project has no GitHub repo, or the repo has no GitHub Project, never create one silently. Ask the user whether to create it, and agree on its settings first (see "Creating a repo or Project" in `references/github.md`). Propose a value for every setting, with the recommended one, so the user can just confirm or change it:
  - **Repo:** owner (personal account or an organization), name, visibility (private recommended), description, `.gitignore` template, license, README, whether to connect the local folder as `origin`, and the branch setup (see next bullet).
  - **Project:** owner, title, visibility, and the repo to link it to.
  Pushing code to a new repo still follows the push rule in CLAUDE.md: only when the user asks.
- **New project branch setup** (see "Branches" in `references/github.md`). Propose it together with the repo settings, as one clearly listed batch that the user approves or changes:
  1. the initial commit on `main`: `.gitignore`, `CLAUDE.md`, `docs/development.md` and the plan, nothing else (the README comes with the bootstrap task); this is `main`'s state until the first release;
  2. push `main`, create `develop` from it and push it;
  3. make `develop` the repo's default branch, so PRs target it and `Closes #<n>` closes issues when a ticket PR merges.

  **The plan goes into the initial commit in its final form,** issue numbers included: implementers work in worktrees created from the remote, so they only see what's pushed. So the order is: create the repo, then the labels, milestones and issues, write the issue numbers into the plan, and only then make the initial commit and push.
- **Existing project:** the plan (and `docs/development.md` or `CLAUDE.md`, if they changed) must also reach the base branch before implementation starts, for the same reason. After the tickets exist and their numbers are in the plan, propose a `docs/` branch with a PR into the base branch as part of the approval below (commit message e.g. `docs: add <feature> plan`).
- **Milestones:** create one GitHub milestone per release in the plan (new project, or a feature that adds a release), and assign every task to its milestone. Include them in the approval below.
- **Before creating the first ticket in this session, ask for approval**, showing: the repo and its owner (so the user can confirm once more that it is their personal repo), the GitHub Project (or that one would be created), the labels and milestones to create, the number of epics, stories and tasks, and the commit, push and PR steps that put the plan on the remote (the initial push, or the plan PR). After that approval, create the rest in this session without asking again.
- Create top-down (epics, then stories, then tasks), so parents exist before children. Link every child to its parent as a sub-issue, and record "blocked by" dependencies.
- Every issue gets a `type:` label and every task gets one `area:` label (these give each area its colour).
- Use `references/ticket-template.md` for issue bodies; the ticket is what the implementer reads.
- After creating them, write the issue numbers back into the plan document's hierarchy. Then do the approved commit and push (the initial push, or the plan PR), and give the user the link to the epic (or the Project board) and a summary table.

Git rules from CLAUDE.md still apply: commits, pushes and PRs happen only as part of the batch the user approved.

## Phase 7: Get the repository ready (new projects)

After the tickets exist, a new project still can't be developed on: there's no skeleton, no working commands and no README, and the coordinator's baseline check would have nothing to run. So **suggest finishing the bootstrap ticket now**.
- **Offer it when it's simple enough:** Haiku or Sonnet tier, no open questions, and no manual steps that need the user. Otherwise say why, and leave it for a separate session.
- **Recommend a fresh session for it.** This session's context is large after the planning, and implementing here would carry all of it along. Suggest `/clear`, then `/implement-ticket #<n>`. If the user prefers to continue here, use the `implement-ticket` skill in this session.
- **Getting it merged:** `implement-ticket` stops before committing. To make the repo ready, the bootstrap change must reach the base branch: commit, push, a PR into `develop` (or the project's base branch) and its merge. Each of these needs the user's request or approval, per CLAUDE.md. Propose them as one listed batch.
- **When it's merged,** tell the user the repository is ready, and what comes next:
  - run `/coordinator milestone <first milestone>` to work through the tickets automatically (optional);
  - or implement tickets one at a time with `/implement-ticket #<n>`.

## Suggested model

Add a "Suggested model" section to every **task** ticket, sized to the task's scope.
- **Tier by scope** (always use the latest version of each tier):

| Tier | Current model | Use for |
|---|---|---|
| Haiku | Haiku 5.5 | Trivial, mechanical changes: copy edits, config tweaks, renames, a single small function |
| Sonnet | Sonnet 5.5 | Typical features and bug fixes in one area of the code, with clear requirements |
| Opus | Opus 5.5 | Features across several modules, design decisions, tricky debugging, larger refactors |
| Fable | Fable 5.1 | The hardest work: architecture from scratch, large migrations, long autonomous runs, problems that stumped a lower tier |

- **Confidence:** High, Medium or Low, with a one-line reason. Use Low when the requirements are vague or the codebase is unfamiliar, and name the tier to fall back to.
- A task that needs Fable usually means it is too big: try to split it first.
