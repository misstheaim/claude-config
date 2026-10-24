---
name: decompose-feature
description: PERSONAL PROJECTS ONLY. Decompose a new project or a feature into a hierarchy (epics, stories, session-sized tasks) with a hierarchical plan (a main plan plus one plan per area, each task carrying its deltas to the behaviour spec) and GitHub tickets; a large project can be decomposed one area per session. A new project also gets its docs/development.md (Git Flow branching, releases), CLAUDE.md and an empty behaviour spec. Large features get the full process; small features (about 3 tasks or fewer) take a light path that still discusses the design with the user, updates the plan and creates the tickets, but skips the heavy analysis and the reviewer subagent. Use when the user asks to decompose, break down, plan into tickets or add a new feature to a project's plan, and only for the user's personal projects (their own GitHub account), never for enterprise or company work. Do NOT use for editing an existing ticket, for bug reports or a single already-understood ticket (create-ticket), or for implementing a task.
argument-hint: "[feature or project description | area <name>]"
---

# Decompose a feature into tickets

Your job is to turn a big feature or a new project into a **well-designed high-level plan, split into pieces that separate Claude sessions will implement later**. Treat it as writing a plan whose points will each be executed by a different session that has none of today's context.

The plan's quality is the goal; the tickets are only its output. **Do not rush to tickets.** Most of the work is understanding the feature with the user.

Feature or project: `$ARGUMENTS` (if empty, ask what to decompose). `area <name>` decomposes one area of a project whose main plan already exists (see "Plan layout").

## Personal projects only

This skill is only for the user's **personal** projects. A personal project is one owned by the user's own GitHub account (or a new project they are starting for themselves), not by a company organization, a company Jira board or any other enterprise setup.

**Before anything else, confirm that this is a personal project.** Check what you can (the repo owner from `gh repo view`, the folder, what the user said), then ask the user to confirm it explicitly, even if it looks obvious. If it is enterprise or company work, or the user doesn't confirm, stop: tell them this skill is for personal projects only, and do not analyse, plan or create anything with it.

## Phase 1: Understand the context

- **Behaviour spec:** if the project has `docs/spec/README.md`, read it and the area files the feature touches **first**. It says how the product behaves now, so you don't have to rediscover that from the code; read the code for how it's built.
- **Existing plan:** find the plan layout (see "Plan layout"): a main plan with area plans, or an older single plan document.
- **Existing codebase:** analyse it, especially the parts the feature touches: architecture, layers, conventions, data model, existing similar features, tests, build and deploy setup. Note the concrete files and modules each part of the feature will change.
- **Empty folder / new project:** research current best practices on the web for the stack and the domain (project structure, libraries, auth, testing, deployment). Cite what you base recommendations on.
- Look for an existing GitHub repo and Project for this work (`gh repo view`, `gh project list --owner <owner>`), so you know where tickets will go.

Give the user a short summary of what you found before moving on.

## Choose the path: full or light

Size the feature right after Phase 1 and tell the user which path you are taking and why (they can override it).

**Light path** when all of these hold:
- the work fits in about **3 tasks or fewer**;
- it needs no new architecture: it reuses the existing stack, modules and patterns, with at most one new module;
- the project already has a plan, or the feature is simple enough to need only a short one.

Otherwise (a new project, a feature that needs several stories, new architecture, or a spike) take the **full path**: Phases 2 to 6 as written below.

### Light path

Spend effort in proportion to the feature. A small feature still needs a conversation and tickets, but not a big design process.
1. **Discuss (short Phase 2):** ask only the questions whose answers change the design or the scope, usually 2 to 4, with a recommended option for each. Raise real risks. Don't walk through alternatives for decisions that already follow from the plan.
2. **Place it in the hierarchy:** attach it to the existing epic it belongs to, as a new story, or add tasks to an existing story. Create a new epic only when the feature fits under none of them. Don't create an epic and a story for one or two tasks if an existing parent fits.
3. **Update the existing plans** instead of writing new ones: the area plan(s) the feature belongs to get the new decisions (continue the numbering), a short design section, the new items in the hierarchy and the task details in the same format as the other tasks, **with their spec changes**; the main plan gets cross-area decisions and the tasks in its order of work. An older single plan document is updated in place. If the project has no plan, write a short main plan with only the sections the feature needs.
4. **Write the test cases yourself (short Phase 4.5):** no test designer subagent, unless the user asks for one. Follow `references/test-cases.md`, then check your cases against its rules as a separate pass. Show them to the user with the tasks.
5. **Skip Phase 5:** no reviewer subagent, unless the user asks for one. Review your own tasks against the "Good tasks" rules instead.
6. **Create the tickets (Phase 6):** same rules: approval first, then the template, labels, sub-issue links, blocked-by links on existing issues, adding them to the Project, and writing the numbers back into the plan.

## Phase 2: Shape the feature with the user

Discuss, don't decide alone. Over as many rounds as needed:
- Ask about the goal, users, scope (what is in and out of the first version), constraints, non-functional needs (performance, security, offline, scale), and what "done" means.
- For every significant design decision (architecture, data model, libraries, API shape, UI approach, hosting), present the reasonable **alternatives** with concrete **pros and cons** for this project, and say which one you **recommend and why**. Wait for the user's choice.
- Raise risks, unknowns and things that need a spike (a short research task) early.
- **New project:** agree on the releases: which milestones (e.g. MVP, 1.0) and their versions (Semantic Versioning; recommend `0.1.0` for an MVP and `1.0.0` for the first stable release), and what goes into each. Explain the branching workflow from `references/development-template.md` (Git Flow: `main` holds only released, tagged code; `develop` integrates every ticket PR; short-lived `release/*` and `hotfix/*` branches) and confirm it, or agree on a simpler one if the user prefers.
- Keep a running list of decisions taken; it goes into the plan (cross-area decisions into the main plan, the rest into the area plans).

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
  - the project skeleton for the chosen stack, with build, lint and test commands that work and one passing smoke test;
  - the **README**: what the project is, requirements, setup, how to run, test and lint, the project structure, and links to `docs/development.md` and the plan;
  - the real commands in `docs/development.md` and `CLAUDE.md`, replacing the planned ones.

  Keep it small enough for one Sonnet session: CI, environments and deployment go into their own tasks. Mark any manual step (an account, a secret, an install) in the ticket.
- **Milestones:** every task belongs to one milestone (release) from the plan.
- **Split until every leaf is session-sized.** That is the main test: if a piece could not realistically be finished, tested and reviewed in a single session, split it further, into sub-stories or tasks. Add a level (story under story) only when a story is still too big; don't add levels for their own sake.
- **Good stories** are independent, valuable on their own, small enough to estimate and testable (INVEST).
- **Good tasks:**
  - have one clear outcome and acceptance criteria that can be checked, numbered `AC1`, `AC2`, ... (test cases are added in Phase 4.5 and refer to them);
  - are self-contained: a fresh session must be able to do it from the ticket and its area plan alone;
  - touch one area where possible (backend, frontend, …). Split a cross-area piece into one task per area, linked by dependencies;
  - prefer thin vertical slices that keep the app working after each task, over "build all layers first";
  - list their **spec changes**: how each item of the behaviour spec reads after the task (new, changed, removed), or "none" when no behaviour changes. Format: `~/.claude/skills/init-spec/references/spec-format.md`. Reserve new IDs per area, continuing after the highest one in `docs/spec/` and in the open plans. A task whose behaviour can't be written as spec statements isn't clear enough yet.
- **Dependencies and order:** record which task blocks which, and mark which tasks can run in parallel. Put foundations (schema, contracts, shared components) first.
- **Area of every task** (one per task): `frontend`, `backend`, `database`, `cloud` (infrastructure, CI/CD, hosting), `assets` (images, icons, sounds, content), `design` (UX/UI design, mockups), `testing`, `docs`. Add another area only if none fits.

## Phase 4: Write the plan

Write the plan in the layout below. It must be complete enough that each implementing session can rely on it: context, decisions with rationale, architecture, data model, API contracts, the full hierarchy with every task's details and spec changes, dependencies, risks and open questions.

### Plan layout

- **Main plan** `docs/plans/README.md` (`references/plan-template.md`): the goal, the areas with links, cross-area decisions, the contracts between areas, the milestones and the **order of work** for every area's tasks.
- **Area plans** `docs/plans/<area>.md` (`references/area-plan-template.md`): one per area (`review`, `cli`, `settings`, …, matching the spec's areas and the `area:` labels where they fit): the area's design, its hierarchy and every task's details. Task names carry the area: `review.T3`.
- **A small project** (one or two areas, about 15 tasks or fewer) may keep its areas inline in the main plan and split them out when it grows.
- **An older single plan document** (`docs/plans/<slug>.md`): keep using it on the light path. On the full path, offer to move it into this layout first; if the user declines, add to it as it is.

### Large projects: one area per session

When the project has several areas that each need real design work, don't design them all in one session: the context grows too big and the later areas get less care.
1. **This session** writes the main plan only: goal, areas and what each owns, cross-area decisions, the contracts between areas, milestones and a rough order. Agree on it with the user, and get it on the base branch (a `docs/` PR, as in Phase 6) so area sessions see it.
2. **Then suggest one session per area:** `/clear`, then `/decompose-feature area <name>`, starting with the areas others depend on.
3. **An area session** reads the main plan and that area's spec file, runs Phases 2 to 6 for the area only (its own discussion, area plan, test cases, review and tickets), and then updates the main plan: the area's status and epic, its tasks in the order of work and the milestones. It never changes a cross-area contract alone; if one needs to change, it asks the user and updates the main plan first.

### New project: workflow files

A new project also gets three more files in its folder, written now from the plan's decisions:
- **`docs/development.md`** from `references/development-template.md`: requirements, the planned commands, the branching workflow, the milestones with their versions, and the release, hotfix and approval rules. Adapt it to what was agreed; don't leave template placeholders in it.
- **`CLAUDE.md`** at the project root from `references/project-claude-template.md`: what the project is, the stack, the workflow rules (base branch `develop`, hotfixes from `main`), an import of `docs/development.md`, where the plan and tickets live, the **"Behaviour spec" rules**, and the conventions from the plan's decisions.
- **`docs/spec/README.md`**, the behaviour spec's index, from `~/.claude/skills/init-spec/references/spec-format.md`: the overview and the areas from the plan (no area files yet), the glossary, "How to edit this spec", and under the areas the line "Nothing is implemented yet." Each area file is created by the first spec update that has behaviour for it.

An existing project without a `docs/development.md` or `CLAUDE.md`: offer to write them the same way, adapted to how the project already works; don't impose a new branching model on it.

**An existing project's spec:**
- **Has one:** make sure its `CLAUDE.md` has the "Behaviour spec" section (add it with the plan if not).
- **Has none:** don't write one here. Tell the user the plan's spec changes need a spec to land in, and suggest `/init-spec` in a separate session (it scans the code, one agent per area, and can cost several dollars on a big project); the coordinator also offers it at a wave end. The spec changes stay in the plan and the tickets either way.

Walk the user through the plan (and these files) and refine them until they are satisfied. Do not create anything on GitHub yet.

## Phase 4.5: Design the test cases

When the user is satisfied with the plan, have the test cases written by someone other than you or the implementers. They are what the coordinator later checks each ticket against, and a ticket closes only when all of them pass.
1. Launch the **test designer subagent** described in `references/test-cases.md` (once, for the whole plan).
2. Weigh its output against the rules in that file. Add the tables you accept to the plan's task details, adjusted where needed.
3. Present to the user: a short coverage summary (cases per task, happy/edge/error counts, tasks with no cases and why), and every **problem** it found, including tasks that hit the 6-case limit and the suggested split: untestable criteria with proposed rewrites, contradictions between tasks, undefined behaviour. Resolve each problem with the user and update the plan.

## Phase 5: Independent review (once)

When the user confirms the plan is ready for tickets:
1. Launch **one** subagent with the Agent tool: `subagent_type: "general-purpose"`, `model: "opus"`. It starts with a clean context, so its prompt must contain everything it needs and nothing more:
   - the absolute paths of the project, the main plan and the area plan(s) written in this session, and of the spec (`docs/spec/`) if there is one;
   - its role: an independent senior reviewer who must not edit any files;
   - the absolute path of `references/test-cases.md`;
   - what to check: gaps and missing work, wrong or risky design decisions, tasks too large for one session or too vague to implement without today's conversation, wrong dependencies or ordering, contradictions with the codebase; and the test cases: acceptance criteria without a case, risky behaviour with no case, cases that should be merged or dropped (the rules aim for 2–5 per task, at most 6), cases that test implementation details or are non-deterministic, and cases in different tasks that can't both pass; and the spec changes: a behaviour-changing task without them, statements that are vague or describe implementation, IDs that collide or skip, changes that contradict the current spec without saying so;
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
  1. the initial commit on `main`: `.gitignore`, `CLAUDE.md`, `docs/development.md`, the plans and `docs/spec/README.md`, nothing else (the README comes with the bootstrap task); this is `main`'s state until the first release;
  2. push `main`, create `develop` from it and push it;
  3. make `develop` the repo's default branch, so PRs target it and `Closes #<n>` closes issues when a ticket PR merges.

  **The plan goes into the initial commit in its final form,** issue numbers included: implementers and reviewers work in worktrees created from the remote, so they only see what's pushed. So the order is: create the repo, then the labels, milestones and issues, write the issue numbers into the plan, and only then make the initial commit and push.
- **Existing project:** the plans (and `docs/development.md` or `CLAUDE.md`, if they changed) must also reach the base branch before implementation starts, for the same reason. After the tickets exist and their numbers are in the plan, propose a `docs/` branch with a PR into the base branch as part of the approval below (commit message e.g. `docs: add <feature> plan`).
- **Milestones:** create one GitHub milestone per release in the plan (new project, or a feature that adds a release), and assign every task to its milestone. Include them in the approval below.
- **Before creating the first ticket in this session, ask for approval**, showing: the repo and its owner (so the user can confirm once more that it is their personal repo), the GitHub Project (or that one would be created), the labels and milestones to create, the number of epics, stories and tasks, and the commit, push and PR steps that put the plan on the remote (the initial push, or the plan PR). After that approval, create the rest in this session without asking again.
- Create top-down (epics, then stories, then tasks), so parents exist before children. Link every child to its parent as a sub-issue, and record "blocked by" dependencies.
- Every issue gets a `type:` label and every task gets one `area:` label (these give each area its colour).
- Use `references/ticket-template.md` for issue bodies. Copy each task's spec changes and test cases into its ticket; the ticket is what the implementer reads.
- After creating them, write the issue numbers back into the area plans' hierarchies and the main plan's order of work. Then do the approved commit and push (the initial push, or the plan PR), and give the user the link to the epic (or the Project board) and a summary table.

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
