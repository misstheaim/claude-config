---
name: implement-ticket
description: Implement one existing ticket (GitHub issue, or a Jira-style ticket the session can read) end to end in the current repo - read it, check it's unblocked, create the branch, implement, check the build, lint and acceptance criteria, and stop before committing with a report. No automated tests. Use when the user asks to implement, work on, pick up or start a specific ticket or issue, e.g. "implement #46", "work on issue 12", "start PROJ-123", and when a coordinator dispatches a ticket to a subagent. Do NOT use for creating, writing or decomposing tickets, for bugs with no ticket, or for reviewing someone else's PR.
argument-hint: "<ticket: #46 | 46 | issue URL | PROJ-123> [--autonomous] [extra instructions]"
---

# Implement a ticket

Ticket and extra instructions: `$ARGUMENTS` (if empty, ask which ticket).

Implement exactly one ticket, the way a careful developer would, then stop and hand back a report. The ticket is the spec: stay inside its scope.

**No automated tests.** This workflow doesn't write, run or fix tests. Tickets and plans written earlier may contain test case tables, a testing strategy or instructions to write tests: skip them. Acceptance criteria still count.

## Mode: interactive or autonomous

- **Autonomous** when the arguments or the prompt include `--autonomous` (the coordinator always passes it), or when you run as a subagent: nobody can answer you mid-task.
- **Interactive** otherwise, when the user invoked the skill directly.

### Interactive (default)

The user is in the session. Ask when a real decision is open, as the steps below say: vague requirements, a conflict that matters, an existing branch, an open design choice on a larger ticket. Small technical choices are still yours; mention the notable ones in the report.

### Autonomous: decide or escalate

Every stop for a question costs a round trip. So **decide by default**, and escalate only what really isn't yours to decide.

**Decide yourself** every technical and implementation question, using the ticket, the plan's decisions, the codebase's conventions and good practice: naming, structure, libraries already in the project, error handling, internal APIs, how to fill a technical gap the ticket leaves open. When there are several reasonable options, pick the one that's simplest, most consistent with the codebase and easiest to change later. **Record the non-obvious ones** under "Decisions made" in the report.

**When stuck, try before escalating:** read more of the codebase, check the plan section, try a different approach. Two or three genuinely different attempts come before calling it stuck.

**Escalate only for:**
- **Business or product decisions:** user-visible behaviour, scope or UX that the ticket and plan don't settle; anything that would change an acceptance criterion or a plan decision; security, privacy, legal or cost trade-offs.
- **Being stuck:** the approaches above failed, or something outside your reach is missing (credentials, access, a manual step, a broken environment you mustn't touch).
- **Destructive or irreversible actions** outside your working tree.

**How to escalate:** finish everything that doesn't depend on the answer, then stop and return all open questions at once, each with the options, your recommendation and what's done so far.

In autonomous mode, every "ask" in the steps below means: escalate as above, and only if the case really is one of the three; otherwise decide and record it.

## 1. Read the ticket

- **Identify it.**
  - `#46`, `46` or an issue URL means a GitHub issue. The repo comes from the URL, or from `gh repo view --json nameWithOwner` in the current folder.
  - A key like `PROJ-123` means Jira or another tracker. Read it with a connected tool if one exists; otherwise ask the user to paste it.
- **Read it:**
  - `gh issue view <n> -R <repo> --json number,title,body,labels,milestone,state,comments`;
  - the parent issue (`gh api repos/<repo>/issues/<n>/parent`) only when the ticket's own context isn't enough;
  - the plan or spec sections the ticket cites, **only those**. Plans are long; open other sections only when the ticket points you there or something is unclear.
- **Comments can change the spec.** Treat later comments as amendments to the body.

## 2. Check that it's ready

Stop and report, without changing anything, when:
- **The ticket is closed** or already has an open PR (`gh pr list -R <repo> --search "<n>"`).
- **A blocker is still open.** Check `gh api repos/<repo>/issues/<n>/dependencies/blocked_by` and any "Blocked by #N" in the body. List the open blockers.
- **The requirements are too vague** to know when the ticket is done. Interactive: ask the specific questions instead of guessing. Autonomous: stop only if the gap is a business decision; fill a technical gap with the most reasonable choice and record it under "Decisions made".
- **The ticket needs the user's hands** (manual steps, interactive sessions, credentials). Prepare everything that can be automated, then pause with exact step-by-step instructions for the user.

**Suggested model:** if the ticket has a "Suggested model" section naming a different tier from the current model, mention it once at the start. You can't switch models yourself.

## 3. Prepare the branch

- **Working tree must be clean** (`git status --porcelain`). If it isn't, stop and ask; never stash or discard the user's changes on your own. (A coordinator's fresh worktree is always clean.)
- **Find the base branch:** the one given in the extra instructions or by the coordinator. Otherwise decide it from the user's instructions, the project's workflow (the repo's CLAUDE.md or `docs/development.md`), the kind of ticket (e.g. a hotfix for a released version) and what recent PRs target (`gh pr list -R <repo> --state merged --limit 10 --json baseRefName`). If it's unclear, ask.
- **Always start from its latest version:** `git fetch origin <base>`, then `git switch -c <branch> origin/<base>`. Never branch from a local copy or from whatever is checked out. Fetching is fine; never push.
- **Name the branch** by the user's conventions (their CLAUDE.md wins). Default: `<type>/<number>-<short-kebab-title>`, where the type is `fix/` for bugs, `refactor/`, `docs/` or `chore/` when the labels or title say so, otherwise `feature/`.
- **If the branch already exists:** interactive: ask whether to continue on it. Autonomous: continue on it if it holds only earlier work on this ticket and has no open PR; otherwise create the branch with a `-2` suffix. Say which in the report.

## 4. Implement

- **Learn the conventions first:** the code around the change, the repo's CLAUDE.md and its build scripts. Write code that matches.
- **Explore subagents for broad searches:** when a question means sweeping many files and you only need the answer (where something is defined, every caller of an API, how a pattern is used across modules), delegate it to an `Explore` subagent instead of reading it all into your own context.
  - Call it with `subagent_type: "Explore"`, `model: "haiku"` and `effort: "low"`, or with `model: "sonnet"` and `effort: "medium"` for a "very thorough" sweep. Always pass the model: without it, Explore runs on the main session's model.
  - Start its prompt with `Ticket #<n>:`, and ask for a compact answer: file paths, line numbers and a few lines of explanation, not file dumps.
  - Read the files you'll change yourself. Explore locates code; it doesn't replace understanding what you edit.
  - Don't use it for a single known file or a targeted grep; that's cheaper inline. Use only `Explore`, no other subagent types.
- **Larger tickets:** write a short plan of a few bullets in your reply before coding. Ask only if a real decision is left open (autonomous: only a business decision).
- **Stay in scope:** do what the goal and acceptance criteria require, and nothing more. Things you notice outside the ticket go into the report as follow-ups, not into the code.
- **When the ticket conflicts with the codebase or the plan,** follow neither silently. Pick the safer option and explain the conflict in the report. Interactive: ask if it's significant. Autonomous: escalate only if resolving it changes behaviour a user would notice or a plan decision.

## 5. Check

- **Build and lint:** run the repo's build and lint commands, with long output sent to a log file, and fix what you broke. Report failures that existed before your change separately. Don't run test suites.
- **Acceptance criteria:** check each one and record evidence: the code that implements it (`file:line`), a command's output, or "needs manual check: <how>". Never mark a criterion met without evidence.

## 6. Report and stop

End with:
- **Summary:** what was done, in 2–4 sentences.
- **Acceptance criteria:** each one with ✅ met (evidence), ❌ not met (why), or 🖐 needs manual check (steps).
- **Changes:** main files touched.
- **Checks:** build and lint results.
- **Decisions made:** the non-obvious technical choices you made on your own, one line each with the reason (always in autonomous mode; interactive only if there were notable ones).
- **Deviations and follow-ups:** anything that differs from the ticket, plus out-of-scope findings.
- **Ready to commit:** a proposed commit message and PR title in the user's conventions. Default commit: `feat(#<n>): <summary>`. Default PR title: `#<n> <Title>`, with `Closes #<n>` in the body.

**Then stop.** Without an explicit request from the user, do not:
- commit or push;
- open a PR;
- comment on, label, move or close the ticket.

When the user asks for any of these, follow their conventions and PR template. Commit only this ticket's changes.

## 7. Fix rounds

When you're given problems to fix on existing work (a coordinator's brief, or the user asking in the same session):
- Fix exactly what's asked; don't make other changes. If you disagree with a requested fix, say why instead of applying it.
- Re-run the build and lint.
- End with a short report: each requested fix with what you changed (or why not), and the build and lint results. Then stop again, still without committing.
