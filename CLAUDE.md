# Projects location

All my projects live in `C:\Users\User\Documents\Projects`.

- When I refer to an existing project by name, look for it in this folder first.
- When I ask to create a new project, create it as a new subfolder here unless I give a different path.

# Git commits and pushes

Never commit or push on your own initiative. Finishing a task, fixing a bug, or making changes is not a reason to commit.

- **Commit** only when I explicitly ask for it, e.g. "Create a commit to this branch" or "Commit only the changes related to the feature". Commit exactly what I asked for and nothing more.
- **Push** only when I explicitly ask for it, e.g. "Push changes to origin" or "Create a commit and push to origin". A request to commit is NOT a request to push. After committing, stop and leave the push to me.
- The same applies to anything else that publishes or rewrites history: force-push, creating or merging PRs, pushing tags, rebasing or amending commits that were already pushed.
- If you think a commit or push would be useful, suggest it in one line and wait for my answer.

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
