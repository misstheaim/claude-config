---
name: implement-ticket
description: Implement one existing ticket (GitHub issue, or a Jira-style ticket the session can read) end to end in the current repo - read it, check it's unblocked, create the branch, implement, test, verify the acceptance criteria, and stop before committing with a report. Use when the user asks to implement, work on, pick up or start a specific ticket or issue, e.g. "implement #46", "work on issue 12", "start PROJ-123", and when a coordinator dispatches a ticket to a subagent. Do NOT use for creating, writing or decomposing tickets, for bugs with no ticket, or for reviewing someone else's PR.
argument-hint: "<ticket: #46 | 46 | issue URL | PROJ-123> [extra instructions]"
---

# Implement a ticket

Ticket and extra instructions: `$ARGUMENTS` (if empty, ask which ticket).

Implement exactly one ticket, the way a careful developer would, then stop and hand back a report. The ticket is the spec: stay inside its scope.

**Running as a subagent** (e.g. dispatched by the coordinator): you can't ask the user. Wherever this skill says "ask", stop instead and return the question with the options, your recommendation and what you've done so far.

## 1. Read the ticket

- **Identify it.**
  - `#46`, `46` or an issue URL means a GitHub issue. The repo comes from the URL, or from `gh repo view --json nameWithOwner` in the current folder.
  - A key like `PROJ-123` means Jira or another tracker. Read it with a connected tool if one exists; otherwise ask the user to paste it.
- **Read everything:**
  - `gh issue view <n> -R <repo> --json number,title,body,labels,milestone,state,comments`;
  - the parent issue (`gh api repos/<repo>/issues/<n>/parent`, if it exists) for context;
  - the plan or spec sections the ticket cites, **only those**. Plans are long; open other sections only when the ticket points you there or something is unclear.
- **Comments can change the spec.** Treat later comments as amendments to the body.
- **Test cases:** note the ticket's "Test cases" table (IDs like `T3-TC01`). They were written before implementation, by someone other than you, and the ticket is done only when every one of them passes as an automated test.

## 2. Check that it's ready

Stop and report, without changing anything, when:
- **The ticket is closed** or already has an open PR (`gh pr list -R <repo> --search "<n>"`).
- **A blocker is still open.** Check `gh api repos/<repo>/issues/<n>/dependencies/blocked_by` and any "Blocked by #N" in the body. List the open blockers.
- **The requirements are too vague** to know when the ticket is done. Ask the specific questions instead of guessing.
- **The ticket needs the user's hands** (manual steps, interactive sessions, credentials). Prepare everything that can be automated, then pause with exact step-by-step instructions for the user.

**Suggested model:** if the ticket has a "Suggested model" section naming a different tier from the current model, mention it once at the start. You can't switch models yourself.

## 3. Prepare the branch

- **Working tree must be clean** (`git status --porcelain`). If it isn't, stop and ask; never stash or discard the user's changes on your own.
- **Find the base branch:** the one given in the extra instructions or by the coordinator. Otherwise decide it for the situation, from the user's instructions, the project's workflow (the repo's CLAUDE.md or `docs/development.md`), the kind of ticket (e.g. a hotfix for a released version) and what recent PRs target (`gh pr list -R <repo> --state merged --limit 10 --json baseRefName`). If it's unclear, ask.
- **Always start from its latest version:** `git fetch origin <base>`, then `git switch -c <branch> origin/<base>`. Never branch from a local copy or from whatever is checked out. Fetching is fine; never push.
- Name the base branch in the report, so the PR targets it.
- **Name the branch** by the user's conventions (their CLAUDE.md wins). Default: `<type>/<number>-<short-kebab-title>`, where the type is:
  - `fix/` for bugs;
  - `refactor/`, `docs/` or `chore/` when the labels or title say so;
  - otherwise `feature/`.
- **If the branch already exists,** ask whether to continue on it.

## 4. Implement

- **Learn the conventions first:** the code around the change, the repo's CLAUDE.md, and its existing tests and build scripts. Write code that matches.
- **Larger tickets:** write a short plan of a few bullets in your reply before coding. Ask only if a real decision is left open.
- **Stay in scope:**
  - Do what the goal and acceptance criteria require, and nothing more.
  - Things you notice that are outside the ticket go into the report as follow-ups, not into the code.
- **When the ticket conflicts with the codebase or the plan,** follow neither silently. Pick the safer option, explain the conflict in the report, or ask if it's significant.

## 5. Verify

- **Test cases:** implement **every** case in the ticket's table as an automated test at the level it names, and put the case ID in the test name or a comment next to it, so it can be traced (e.g. `T3-TC02 expired token is rejected`).
  - The test must assert what the case's "Then" says, with its specific values. Don't weaken, skip or loosen it to make it pass.
  - **Never change a case's expected behaviour.** If a case looks wrong, contradicts another case or the codebase, or can't be implemented as written, implement the rest and report it under "Deviations" with the reason and what you'd propose. Don't decide it yourself.
  - No test cases in the ticket: write tests for the acceptance criteria yourself, and say so in the report.
- **Other tests:** add tests for any other logic you add.
- **Checks:** run the repo's build, lint and **full** test suite, not only your new tests, and fix what you broke. Report failures that existed before your change separately.
- **Acceptance criteria:** check each one and record evidence (a test name, command output, or "needs manual check: <how>"). Never mark a criterion met without evidence.

## 6. Report and stop

End with:
- **Summary:** what was done, in 2–4 sentences.
- **Acceptance criteria:** each one with ✅ met (evidence), ❌ not met (why), or 🖐 needs manual check (steps).
- **Changes:** main files touched.
- **Test cases:** a table with every case: `ID | test name (file) | ✅ pass / ❌ fail / ⚠ not implemented (why)`.
- **Tests:** what ran and the results, including failures.
- **Deviations and follow-ups:** anything that differs from the ticket, plus out-of-scope findings.
- **Ready to commit:** a proposed commit message and PR title in the user's conventions. Default commit: `feat(#<n>): <summary>`. Default PR title: `#<n> <Title>`, with `Closes #<n>` in the body.

**Then stop.** Without an explicit request from the user, do not:
- commit or push;
- open a PR;
- comment on, label, move or close the ticket.

When the user asks for any of these, follow their conventions and PR template. Commit only this ticket's changes.

## 7. Follow-up rounds

When you're resumed later (for example by a coordinator sending review findings to fix), you keep your context and your worktree:
- Fix exactly what the message asks for; don't make other changes. If you disagree with a requested fix, say why instead of applying it.
- Re-run the build, lint and the tests the fixes affect. Run the full suite too, unless the message says the caller runs it.
- End with a short report: each requested fix with what you changed (or why not), the updated test case table, and the test results. Then stop again, still without committing.
