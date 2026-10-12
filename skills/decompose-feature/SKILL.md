---
name: decompose-feature
description: PERSONAL PROJECTS ONLY. Decompose a large feature or new project into a multi-level hierarchy (epics, stories, session-sized tasks) with a detailed plan document. Use only when the user explicitly asks to decompose or break down a big feature or project into many smaller tickets, and only for the user's personal projects (their own GitHub account), never for enterprise or company work. Do NOT use for creating, writing or editing a single ticket or issue, for bug reports, or for planning or implementing one task.
argument-hint: "[feature or project description]"
---

# Decompose a feature into tickets

Your job is to turn a big feature or a new project into a **well-designed high-level plan, split into pieces that separate Claude sessions will implement later**. Treat it as writing a plan whose points will each be executed by a different session that has none of today's context.

The plan's quality is the goal; the tickets are only its output. **Do not rush to tickets.** Most of the work is understanding the feature with the user.

Feature or project: `$ARGUMENTS` (if empty, ask what to decompose).

## Personal projects only

This skill is only for the user's **personal** projects. A personal project is one owned by the user's own GitHub account (or a new project they are starting for themselves), not by a company organization, a company Jira board or any other enterprise setup.

**Before anything else, confirm that this is a personal project.** Check what you can (the repo owner from `gh repo view`, the folder, what the user said), then ask the user to confirm it explicitly, even if it looks obvious. If it is enterprise or company work, or the user doesn't confirm, stop: tell them this skill is for personal projects only, and do not analyse, plan or create anything with it.

## Phase 1: Understand the context

- **Existing codebase:** analyse it, especially the parts the feature touches: architecture, layers, conventions, data model, existing similar features, tests, build and deploy setup. Note the concrete files and modules each part of the feature will change.
- **Empty folder / new project:** research current best practices on the web for the stack and the domain (project structure, libraries, auth, testing, deployment). Cite what you base recommendations on.
- Look for an existing GitHub repo and Project for this work (`gh repo view`, `gh project list --owner <owner>`), so you know where tickets will go.

Give the user a short summary of what you found before moving on.

## Phase 2: Shape the feature with the user

Discuss, don't decide alone. Over as many rounds as needed:
- Ask about the goal, users, scope (what is in and out of the first version), constraints, non-functional needs (performance, security, offline, scale), and what "done" means.
- For every significant design decision (architecture, data model, libraries, API shape, UI approach, hosting), present the reasonable **alternatives** with concrete **pros and cons** for this project, and say which one you **recommend and why**. Wait for the user's choice.
- Raise risks, unknowns and things that need a spike (a short research task) early.
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
- **Split until every leaf is session-sized.** That is the main test: if a piece could not realistically be finished, tested and reviewed in a single session, split it further, into sub-stories or tasks. Add a level (story under story) only when a story is still too big; don't add levels for their own sake.
- **Good stories** are independent, valuable on their own, small enough to estimate and testable (INVEST).
- **Good tasks:**
  - have one clear outcome and acceptance criteria that can be checked;
  - are self-contained: a fresh session must be able to do it from the ticket and the plan document alone;
  - touch one area where possible (backend, frontend, …). Split a cross-area piece into one task per area, linked by dependencies;
  - prefer thin vertical slices that keep the app working after each task, over "build all layers first".
- **Dependencies and order:** record which task blocks which, and mark which tasks can run in parallel. Put foundations (schema, contracts, shared components) first.
- **Area of every task** (one per task): `frontend`, `backend`, `database`, `cloud` (infrastructure, CI/CD, hosting), `assets` (images, icons, sounds, content), `design` (UX/UI design, mockups), `testing`, `docs`. Add another area only if none fits.

## Phase 4: Write the plan document

Write a large, detailed Markdown document using `references/plan-template.md`:
- Existing project: `docs/plans/<feature-slug>.md` in the repo.
- New project: `docs/plans/<project-slug>.md` inside the new project folder.

It must be complete enough that each implementing session can rely on it: context, decisions with rationale, architecture, data model, API contracts, the full hierarchy with every task's details, dependencies, risks and open questions.

Walk the user through it and refine it until they are satisfied. Do not create anything on GitHub yet.

## Phase 5: Independent review (once)

When the user confirms the plan is ready for tickets:
1. Launch **one** subagent with the Agent tool: `subagent_type: "general-purpose"`, `model: "opus"`. It starts with a clean context, so its prompt must contain everything it needs and nothing more:
   - the absolute path of the plan document and of the project;
   - its role: an independent senior reviewer who must not edit any files;
   - what to check: gaps and missing work, wrong or risky design decisions, tasks too large for one session or too vague to implement without today's conversation, wrong dependencies or ordering, missing tests or acceptance criteria, contradictions with the codebase;
   - what to return: a list of issues (each with severity, location in the plan, and a concrete fix) and a list of improvements, ordered by importance.
2. Weigh its output yourself: say which points you agree with, which you don't, and why.
3. Present this to the user and ask for final confirmation, updating the plan with what they accept.

If the user asks for more changes afterwards, make them **without** running the reviewer again, unless the user explicitly asks for another review.

## Phase 6: Create the tickets

Default target: GitHub Issues in the project's repo, added to its GitHub Project. Commands and label colours are in `references/github.md`.

- **Missing repo or Project:** if the project has no GitHub repo, or the repo has no GitHub Project, never create one silently. Ask the user whether to create it, and agree on its settings first (see "Creating a repo or Project" in `references/github.md`). Propose a value for every setting, with the recommended one, so the user can just confirm or change it:
  - **Repo:** owner (personal account or an organization), name, visibility (private recommended), description, `.gitignore` template, license, README, and whether to connect the local folder as `origin`.
  - **Project:** owner, title, visibility, and the repo to link it to.
  Pushing code to a new repo still follows the push rule in CLAUDE.md: only when the user asks.
- **Before creating the first ticket in this session, ask for approval**, showing: the repo and its owner (so the user can confirm once more that it is their personal repo), the GitHub Project (or that one would be created), the labels to create, and the number of epics, stories and tasks. After that approval, create the rest in this session without asking again.
- Create top-down (epics, then stories, then tasks), so parents exist before children. Link every child to its parent as a sub-issue, and record "blocked by" dependencies.
- Every issue gets a `type:` label and every task gets one `area:` label (these give each area its colour).
- Use `references/ticket-template.md` for issue bodies.
- After creating them, write the issue numbers back into the plan document's hierarchy, and give the user the link to the epic (or the Project board) and a summary table.

Git rules from CLAUDE.md still apply: don't commit or push the plan document unless the user asks.

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
