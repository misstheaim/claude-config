# Projects location

All my projects live in `C:\Users\User\Documents\Projects`.

- When I refer to an existing project by name, look for it in this folder first.
- When I ask to create a new project, create it as a new subfolder here unless I give a different path.

# Push back when you disagree

Evaluate my requests critically instead of just carrying them out. If you have a well-founded concern, raise it before or while doing the work.

- Speak up when a request goes against good practice, won't achieve what I'm after, has a better alternative, conflicts with earlier decisions or instructions, or carries risk I may not have seen. This applies to everything, including changes to this file.
- Only disagree when you're confident and can explain why: give the concrete reason and, when there is one, the alternative you'd recommend. Don't invent objections or add caveats to every answer.
- Then let me decide. If I still want it my way, do it as asked.
- Don't open with agreement or praise ("Great idea!"); just answer.

# Changes to remote sources

Always ask for my approval before any action that changes something outside this machine: GitHub (repos, issues, PRs, labels, Projects, comments, releases, settings), other APIs and services, cloud resources, databases that aren't local, package registries, documents, messages, and so on.

- **Allowed without asking:** read-only calls such as GET requests, fetching, searching, listing, viewing and `git fetch`.
- **Needs approval:** anything that creates, updates, deletes, sends, publishes or triggers something (POST/PUT/PATCH/DELETE, `gh ... create/edit/delete/close/merge`, deploys, running remote jobs).
- When asking, say exactly what will change and where (service, repo or resource, and the action).
- An explicit request from me for that specific action counts as approval (e.g. "push to origin", "create the issues"). Approval for a clearly described batch (e.g. "create these 12 issues") covers that batch only, not later actions.
- If you're unsure whether a call changes something, treat it as a change and ask.

# Git commits and pushes

Never commit or push on your own initiative. Finishing a task, fixing a bug, or making changes is not a reason to commit.

- **Commit** only when I explicitly ask for it, e.g. "Create a commit to this branch" or "Commit only the changes related to the feature". Commit exactly what I asked for and nothing more.
- **Push** only when I explicitly ask for it, e.g. "Push changes to origin" or "Create a commit and push to origin". A request to commit is NOT a request to push. After committing, stop and leave the push to me.
- The same applies to anything else that publishes or rewrites history: force-push, creating or merging PRs, pushing tags, rebasing or amending commits that were already pushed.
- If you think a commit or push would be useful, suggest it in one line and wait for my answer.

# Exception: coordinator mode

When I run the `/coordinator` skill, the permissions documented in that skill apply for that run, overriding the two sections above, but only within them:

- **Scope:** only the run's target GitHub repo.
- **Allowed without asking:** branches, commits, pushes, PRs, merges into the run's base branch with the project's merge method (squash by default), issue edits and comments, and Project items. Merges into any other branch (e.g. `main` or `release/*`) still need my approval.
- **Unchanged:** everything else (other repos and services, force-push, repo settings, releases, tags) still needs my approval as usual.
- **Duration:** the exception ends when the run ends. It never applies to `/implement-ticket` or any other session.

# Fable model

Never use the Fable model without my explicit permission for that specific use: not for subagents (`model: "fable"` or a full `claude-fable-*` id), custom agent definitions, `claude --model` commands, or anything else that runs on it. Ask first, saying what it's for and why a lower tier won't do. A PreToolUse hook (`~/.claude/hooks/fable_guard.py`) also asks me before such calls.

- Naming Fable as a ticket's "Suggested model" is fine; it's a suggestion, not a use.
- The coordinator never uses Fable at all, even with permission (see its skill).

# Base branch for new branches

Before creating a feature branch, always fetch the latest base branch and create the new branch from its remote version:

```bash
git fetch origin <base>
git switch -c <new-branch> origin/<base>
```

- **Base branch:** decide it for the situation. Use what I said, the project's workflow (its CLAUDE.md or `docs/development.md`), the kind of work (e.g. a hotfix for a released version) and what the repo's recent PRs target. If it's still unclear, ask.
- Never branch from a stale local copy or from whatever branch happens to be checked out.
- PRs target the same base branch.
- Fetching is read-only, so it needs no approval.

# Git naming conventions

Use these formats for every commit, branch and PR so they stay consistent.

## Ticket codes

If the work is tied to a ticket on a board (Jira, GitHub Issues, etc.), include its code in the branch name, the commit messages and the PR title.
- Jira-style: `PROJ-123`. GitHub issue: `#42` in commits and PR titles, `42` in branch names.
- Find the ticket from what I said, or from the current branch name. If it's unclear whether a ticket exists, ask. Never invent one.
- If there is no ticket, leave the code out entirely (no placeholders).

## Branches

Format: `<type>/<TICKET>-<short-kebab-description>`, or `<type>/<short-kebab-description>` with no ticket.
- `feature/` for new functionality, `fix/` for bug fixes. For other work use `refactor/`, `docs/` or `chore/`.
- Examples: `feature/PROJ-123-user-login`, `fix/42-null-avatar-crash`, `fix/null-avatar-crash`.

## Commit messages

Conventional Commits, with the ticket as the scope:
`<type>(<TICKET>): <short summary>`, or `<type>: <short summary>` with no ticket.
- Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `style`, `build`, `ci`.
- Summary: imperative mood, lowercase, no trailing period, about 72 characters max.
- Add a body only when the "why" isn't obvious from the summary.
- Examples: `feat(PROJ-123): add user login form`, `fix(#42): handle missing avatar url`, `chore: update dependencies`.

## Pull requests

- Title: NOT the commit format (no `feat:`/`fix:` prefix). Use `<TICKET> <short description>`, or just `<short description>` with no ticket.
  - Examples: `PROJ-123 Add user login`, `#42 Handle missing avatar url`, `Update dependencies`.
- Description template:

```markdown
## Summary
<1-3 sentences: what this PR does and why>

## Changes
- <main change>
- <main change>

## Testing
<how it was verified: tests run, manual steps>

## Ticket
<link or code, e.g. PROJ-123 / Closes #42; omit this section if there is no ticket>
```

- For GitHub issues, use `Closes #42` so the issue closes automatically when the PR is merged.
- Creating a PR follows the same rule as pushing: only when I explicitly ask.

# Model suggestion in tickets (personal projects only)

When I ask you to create a ticket for new functionality in one of my **personal** projects, add a "Suggested model" section to the ticket, sized to the scope of the task.

- **Personal vs enterprise:** a personal project is one owned by my own GitHub account, not by a company organization or a company Jira board. If you can't tell which it is, ask. Never add this section to enterprise tickets.
- **Pick the tier by scope** (always use the latest version of each tier):

| Tier | Current model | Use for |
|---|---|---|
| Haiku | Haiku 5.5 | Trivial, mechanical changes: copy edits, config tweaks, renames, a single small function |
| Sonnet | Sonnet 5.5 | Typical features and bug fixes in one area of the code, with clear requirements |
| Opus | Opus 5.5 | Features across several modules, design decisions, tricky debugging, larger refactors |
| Fable | Fable 5.1 | The hardest work: architecture from scratch, large migrations, long autonomous runs, problems that stumped a lower tier |

- **Confidence:** High, Medium or Low, with a one-line reason. Use Low when the requirements are vague or the codebase is unfamiliar, and mention which tier you'd fall back to.
- Format:

```markdown
## Suggested model
**Sonnet 5.5** (confidence: High). Self-contained form + API endpoint, clear requirements, follows existing patterns.
```

# Tool suggestions

Now and then, think about whether a tool I'm not using would clearly help with the current task, and if so, mention it.

- "Tools" means anything: Claude Code features (artifacts, `/code-review`, skills, subagents, hooks, MCP connectors) and external products (Docker, cloud services, GitHub Actions, frameworks, libraries, packages, Photoshop, Blender, 3ds Max, etc.).
- Suggest only when the benefit is real and specific to what I'm doing right now, e.g. an artifact when a visual page would make the result much easier to understand or share. Don't suggest what I already use.
- Keep it rare: at most once every several responses, and never the same suggestion twice in a session.
- Format: one short sentence at the end of a response, e.g. "Tip: a GitHub Actions workflow could run these tests on every push." No details unless I ask.
