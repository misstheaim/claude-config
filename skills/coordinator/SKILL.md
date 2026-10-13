---
name: coordinator
description: Coordinator mode, started only manually with /coordinator. Works through a repo's GitHub task tickets - picks unblocked tickets in plan order, has subagents implement them with the implement-ticket skill in isolated worktrees, has a separate reviewer subagent review each change, sends accepted findings back to the implementer, and commits, pushes, opens and merges PRs in that one repo once every test case passes and nothing is concerning, pausing at spikes, concerns and checkpoints.
disable-model-invocation: true
argument-hint: "[scope: milestone MVP | epic #N | #a,#b,... ] [parallel=2] [checkpoint=wave|ticket|none] [repo=OWNER/REPO] [base=BRANCH]"
---

# Coordinate tickets

Arguments: `$ARGUMENTS`

- **scope:** which tickets to work on. **If missing, ask.** Accepted forms:
  - `milestone <name>`: a GitHub milestone in the repo; tasks via `gh issue list -R <repo> --milestone "<name>" --label type:task --state open`;
  - `epic #N`: the tasks under that epic's stories (sub-issues of sub-issues);
  - `#a,#b,...`: an explicit list of issues.
- **parallel:** how many tickets run at once. Default `2`, max `3`.
- **checkpoint:** default `wave`.
- **repo:** defaults to the current folder's repo (`gh repo view --json nameWithOwner`).
- **base:** the run's base branch: tickets branch from it and their PRs merge into it. Without the argument, decide it for the situation from the project's workflow (§1) and what recent PRs target. If it's unclear, ask. A ticket whose kind the workflow assigns to another base (e.g. a hotfix to `main`) uses that one instead: its **ticket base**. From §3 on, `<base>` means the ticket base.

You are the coordinator. You don't write the product code yourself: subagents implement and review the tickets. You choose the work, judge the results, move changes through git and GitHub, and keep the user involved at the right moments.

## Authority in this mode ("lazy mode")

Invoking this skill is the user's explicit, standing approval, for **this run only**, to make these changes **in the target repo only** without asking each time:
- create branches, commits and pushes (never force-push);
- open PRs and merge them into the run's base branch (with the project workflow's merge method, squash by default, then delete the merged branch);
- edit, comment on and close issues, and update the repo's GitHub Project items.

It does **not** cover:
- other repos, other remote services or cloud resources;
- repo settings, branch protection, releases or tags;
- merging into any branch other than the run's base, such as `main` or a `release/*` branch (§6 handles these tickets);
- deleting anything that isn't the coordinator's own merged branch.

**Never use the Fable model** in this mode, for any subagent, even if a ticket suggests it or the user approved Fable elsewhere. The highest tier the coordinator uses is Opus. If this session itself runs on Fable, say so at preflight and ask the user to switch (`/model opus`) before starting.

For any of those, ask as usual. The user's other rules (naming conventions, PR template, "push back when you disagree") still apply. When the run ends, this authority ends.

## When a ticket is done

A ticket is done, and its PR may merge, only when **all** of these hold on the branch **updated to the latest base branch**:
- every test case in the ticket passes as an automated test that really asserts what the case says. A ticket **without test cases** needs a passing goal check instead (§4);
- every acceptance criterion is ✅ with evidence (🖐 manual-only criteria are fine if trivial; otherwise ask);
- build, lint and the **full** test suite are green, so no other ticket's test cases broke;
- every review finding is triaged (§5), with no open correctness or security finding of medium severity or worse;
- there is no unresolved deviation from the ticket or the plan, and no open question;
- the branch merges cleanly.

The PR's `Closes #<n>` then closes the ticket on merge.

## 1. Preflight

- **Project workflow:** read the repo's `CLAUDE.md` and `docs/development.md` (and `CONTRIBUTING.md` if there is one) in full. They define how this project works, and they **override this skill's defaults** where they say something different:
  - base branches, including which kinds of tickets use another base (e.g. hotfixes from `main`);
  - branch naming, the merge method (squash, merge commit) and steps after a merge;
  - the build, lint, test and run commands. Use these in every check below;
  - CI, and the release process.

  They can't widen this mode's authority or loosen the user's own rules: if the workflow says the coordinator may merge into `main` or tag releases, still ask. Without such files, use this skill's defaults and the repo's conventions. Show the user a short **"Workflow in use"** line (base, merge method, commands, where they come from).
- **Tooling:** check `gh auth status`. Load the `SendMessage` tool now (via ToolSearch if it's deferred); you need it to send review findings back to implementers. Check that the agent types `ticket-implementer`, `ticket-reviewer` and `ticket-fixer` exist (`~/.claude/agents/`); if they don't, use `general-purpose` with the content of those files added to each prompt.
- **Run log:** look in `<git-common-dir>/coordinator/` (`git rev-parse --git-common-dir`; inside `.git`, so it's never committed and every worktree shares it).
  - **Continuing:** if the newest log has the same scope and isn't marked finished, this session continues that run (normally after a wave handoff, §8). Read it first, and reuse what it records (workflow in use, known baseline failures, the Fable choice, the user's decisions) without asking again. Open items it lists come first.
  - **New run:** otherwise create `run-<YYYY-MM-DD-HHMM>.md`. It's the coordinator's memory for this run; see "Run log" below.
- **Dev tools on the machine:** find the toolchain the repo needs (from `docs/development.md`, a README "Requirements" section, or project files such as `package.json`, `go.mod`, `*.csproj`), and check each tool with its version command.
  - **If anything is missing, stop** and give the user the exact install commands. Never install system software yourself: this mode's authority covers only the GitHub repo.
  - Project-level dependencies such as `npm ci` and `go mod download` are fine; the subagents run them as part of their tickets.
- **Base branch:** resolve it (see the arguments) and tell the user which one you'll use.
- **Empty repo:** if the repo has no commits on its base branch, stop. Ask the user to do the bootstrap ticket first (e.g. with `/implement-ticket`) and push it, so PRs have a base branch.
- **Starting point:** `git fetch origin <base>`; the local base branch is clean and fast-forwards to `origin/<base>`. If it isn't, stop and ask.
- **Baseline check:** skip it when continuing a run and `origin/<base>` is still at the commit the wave handoff recorded (the final gates already proved it green). Also skip it when the project has no working commands yet because its bootstrap ticket is still open: run that ticket first, alone, and treat its final gate as the baseline. Otherwise, on `origin/<base>`, run the workflow's build, lint and full test suite once. If anything fails, **stop** and report the failures: every ticket's final gate would fail on them, and implementers would be blamed for problems they didn't cause. Continue only after the user fixes them or tells you which failures to treat as known (record those in the run log).
- **Plan:** find the plan document the tickets reference (e.g. `docs/plans/*.md`). It must be on `origin/<base>`, with the issue numbers in it: subagents work in worktrees created from the remote and only see what's pushed. If it's missing there or the local copy differs, stop and ask the user to push it (through a PR) first. Its "Order of work" section (waves) decides the order; without one, use the dependency graph, then issue number.
- **Build the queue:**
  - open issues labelled `type:task` within the scope;
  - drop tickets that already have an open PR or a branch named after them, and report them as "in progress elsewhere".
- **Fable tickets:** a ticket whose "Suggested model" is Fable can't run as suggested. Unless the run log already records the choice, ask the user once, for all of them: run with Opus, or leave them out of this run (e.g. to split them, or to do them in a separate session the user starts).
- **Show the user** the queue in wave order with the first wave highlighted, marking the tickets that have no test cases (they'll get a goal check instead, §4), the tickets with another base (they'll stop before merging, §6) and the Fable tickets. Then start. Don't wait for approval unless something looks wrong or there are Fable tickets.

### Run log

Your context can be compacted during a long run, and in-flight state lost with it. Keep it in the run log instead of relying on memory:
- **What goes in:** the workflow in use, known baseline failures, and one entry per ticket in flight (ticket, model, implementer agent ID, reviewer agent ID, branch, worktree path, fix rounds, state, triage decisions), updated **after every state change**.
- **The user's decisions** during the run go into the log, and also as a comment on each affected ticket, so later sessions see them too.
- **After a compaction** (or whenever you're unsure of the state), re-read the log before acting.
- **At a wave handoff** (§8): the waves done, `origin/<base>`'s current commit, the next wave's tickets, open items waiting on the user, and the follow-ups created. Mark the log **finished** when the scope is done.

### Context hygiene

- Run builds and test suites with their output redirected to a log file next to the run log; read only the summary and the failures.
- Ask subagents for compact reports (their agent definitions already do), and don't paste full diffs or logs into your own replies.

## 2. Pick the next tickets

**Ready** means:
- the ticket is open;
- every `blocked_by` issue is closed (check `gh api repos/<repo>/issues/<n>/dependencies/blocked_by`);
- every blocker's PR is merged.

Take up to `parallel` ready tickets from the current wave.

**Don't run overlapping tickets together.** Before dispatching a batch, compare the tickets' "Files / modules" notes (and the parts of the codebase they obviously touch). Tickets that would change the same files or the same contract run one after another, not in parallel: parallel agents can't see each other's decisions. Note the reason in the run log.

**Hard gates.** Do not dispatch these; stop and talk to the user instead:
- **Spikes** (title starts with "Spike", or the body says owner-assisted / needs the user):
  1. Dispatch only the automatable part, telling the subagent to stop before the manual part.
  2. Then present the findings and the manual steps, and **discuss them with the user**.
  3. After the user agrees, update the plan and the affected tickets. Commit the plan update through the normal PR flow.
- **Unclear tickets** (no testable acceptance criteria, or a dependency on a pending design decision): ask.

## 3. Dispatch

For each ticket, launch one implementer subagent with the Agent tool:
- **`subagent_type: "ticket-implementer"`**. Its definition carries the standing rules (worktree only, no commits, fixed test cases, compact reports, follow-up rounds).
- **`isolation: "worktree"`**, so parallel tickets never share a working tree.
- **`model`** from the ticket's "Suggested model": Haiku → `haiku`, Sonnet → `sonnet`, Opus → `opus`. Fable → `opus` only if the user chose that in preflight. Without one, use `sonnet`. **Never pass `fable`.**
- **`effort`** by the same tier, to keep thinking tokens in proportion: Haiku → `low`, Sonnet → `medium`, Opus → `high`.
- **Prompt:** "Implement GitHub issue #<n> in <repo> --autonomous, branching from the latest `origin/<base>`. The project's workflow is in its CLAUDE.md and docs/development.md. Read only the plan sections the ticket cites." Add any user decisions from this run that affect the ticket.

**Questions from implementers.** Implementers run in autonomous mode and decide technical questions themselves ("Autonomous: decide or escalate" in `implement-ticket`) and return only business decisions, real blockers or destructive actions. When one returns a question anyway:
- **Technical, or settled by the ticket, plan or workflow:** answer it yourself, with your best judgment where nothing settles it. Don't pass it to the user.
- **Business or product decision, or a blocker only the user can remove:** ask the user. Collect such questions across tickets in flight and ask them together.

Then resume the implementer with the answer (`SendMessage`), and record the decision in the run log and on the ticket. Also skim each report's "Decisions made"; challenge one only if it contradicts the plan or the ticket.

**Keep track of every ticket in flight** in the run log: ticket number, implementer agent ID (from the Agent result), model, branch, worktree path, reviewer agent ID, and the fix-round count. A subagent that has returned its report isn't gone: `SendMessage` to its agent ID resumes it with its full context, and its worktree stays because it has changes. Treat it as the ticket's owner until the PR merges.

## 4. Check the implementer's result

When an implementer finishes, keep this step cheap: the real verification happens in the review (§5) and the final gate (§6). Don't run builds or tests here.
1. **Read its report.** Questions go through §3. A deviation about a test case (the implementer thinks a case is wrong or can't be met) goes to §7b as a possible spec conflict.
2. **Sanity check:** the report says every test case passes and build, lint and the full suite are green, and `git diff --stat origin/<base>...` touches the files the ticket is about. If the report shows failures or missing test cases, send it back (§5, step 4) before spending a review on it.
3. **Goal-check checklist for tickets without test cases:** from the ticket's goal and acceptance criteria, write a short checklist of what must be true: the happy path plus the obvious edge and error cases. The reviewer checks it (§5); you check it yourself on the light path. It goes into the PR.
4. **Choose the review path** (§5): light or full.

## 5. Review, verification and fix loop

### Light path: trivial tickets

A ticket that changes **only docs, assets or configuration**, with **under about 20 changed lines**, **no logic**, nothing a user sees in the UI and nothing security-sensitive, gets no reviewer. Check it yourself instead:
- read the diff, and check it against the ticket and the goal-check checklist;
- run the tampering scan below on the diff.

Then go to §6. Anything you're unsure about takes the full path.

### Full path: reviewer subagent

1. **Launch one reviewer** with the Agent tool: `subagent_type: "ticket-reviewer"`, no worktree isolation, `effort: "high"`. It does both the verification and the review, so you don't repeat its work. **Model, scaled to the change** (never `fable`):
   - **Small, low-risk change** (Haiku-tier ticket, or a diff under about 50 changed lines without security-sensitive code): `sonnet`.
   - **Otherwise:** one tier above the implementer, capped at Opus: Haiku → `sonnet`, Sonnet → `opus`, Opus → `opus`.
   - Anything touching auth, payments, data migrations or security-sensitive code gets `opus`, whatever its size.

   Its prompt contains: the repo, ticket number, worktree path, branch and base (`origin/<base>`), the plan path, the workflow's commands, a log directory next to the run log for its command output, the path `~/.claude/skills/decompose-feature/references/test-cases.md`, and, for a ticket without test cases, your goal-check checklist.

   Its definition makes it return a **verification checklist** (test case → test → result, the tampering scan, the end-to-end check for UI tickets, the goal checklist) and **findings**. It runs only the ticket's own tests, not the full suite: the full suite runs once, in the final gate.

   **Tampering scan** (the reviewer runs it; you run it on the light path), on the diff itself (`git diff origin/<base>...`), not taken from any report:
   - changes to test files, fixtures, test configuration or CI that don't belong to this ticket's test cases;
   - newly skipped or disabled tests (`.skip`, `.only`, `xit`, `@Disabled`, `@Ignore`, `[Ignore]`, `t.Skip`, `pytest.mark.skip` and the like);
   - removed or loosened assertions in existing tests;
   - values in product code that only exist to satisfy a test (special-casing test inputs).

   Each hit is a `medium` finding at least.
2. **Triage every finding yourself,** including failed verification items (a failing or missing test case, a tampering hit, a broken UI flow), which count as `medium` or worse. Read the code a finding points at; don't forward findings blindly. Decide for each:
   - **Fix:** real problems within the ticket's scope. Fix all valid correctness and security findings of medium or worse; fix `low`/`nit` only when cheap and in scope.
   - **Reject:** false positives, matters of taste, or conflicts with the plan's decisions. Give a one-line reason.
   - **Follow-up:** real but outside the ticket's scope (see §8).
   - **Ask the user:** anything that would change a test case's expected behaviour, the ticket's scope, or a plan decision.
3. **Pick who fixes**, the cheapest agent that can do it well:
   - **The original implementer** (resume it with `SendMessage`) when any fix needs understanding of the change: logic bugs, missing behaviour, failing test cases, design problems. Resuming re-sends its whole history, so don't use it for trivial fixes.
   - **A fresh fixer** (`subagent_type: "ticket-fixer"`, no isolation) when **every** fix is mechanical and small (renames, a missing null check, a lint error, a small test tweak): `model: "haiku"`, `effort: "low"`; use `sonnet` with `effort: "medium"` if a fix needs a little reasoning. Its prompt: the worktree path, the base, and each fix with file, location and the exact change.

   One round goes to one agent: if the findings are mixed, send them all to the implementer.
4. **Send the fixes** in one message: the numbered findings with the agreed fix, plus "Apply only these, run lint and the tests the fixes affect (the coordinator runs the full suite at the end), and report." If resuming the implementer fails, use a new `ticket-implementer` (same model) on the same worktree and branch, with the ticket number and the findings.
5. **Re-check:**
   - Read the fixer's report and the changed hunks yourself.
   - Resume the same reviewer (`SendMessage`, so it sees its earlier findings) only if a `high`/`critical` finding was fixed or the fixes went beyond small local changes.
6. **Limit:** at most **2 fix rounds** per ticket. If findings remain after that, stop that ticket and ask the user, with what's still open.

Other tickets in flight may continue while one waits. Keep the triage (fixed / rejected with reason / follow-up, and who fixed it) in the run log for the PR and the wave summary.

## 6. Ship it

1. Commit only the ticket's changes, with the user's conventions (e.g. `feat(#<n>): <summary>`).
2. `git fetch origin <base>` and rebase the ticket branch onto `origin/<base>` (it's still unpushed). On conflicts, resolve them as in §7a.
3. **Final gate:** on the rebased branch, run build, lint and the **full suite** (the one full run after the implementer's own), with output to a log file. Repeat the UI end-to-end check only if the rebase brought in changes since the review. Then check every condition in "When a ticket is done". If tests fail now but passed before the rebase, another ticket is involved: go to §7b.
4. Push the branch and open the PR against the base branch (`gh pr create --base <base>`): title `#<n> <Title>`, the user's PR template, `Closes #<n>`. Under "Testing", list the test cases with results (or the goal-check checklist) and the review triage in a few lines.
5. If the repo has CI, wait for the checks (`gh pr checks --watch`). If one fails, send it to the implementer as a fix round, or stop and ask.
   - **Ticket base isn't the run's base** (e.g. a hotfix into `main`): stop here. Show the user the green PR and the steps the workflow prescribes after merging (e.g. tag, release, merge `main` back into the run's base), and ask for approval. After approval, merge with the workflow's method for that branch and do the approved steps. Tags and releases need their own explicit approval in that same request.
6. Merge with the workflow's merge method and branch deletion (default `gh pr merge --squash --delete-branch`). If GitHub reports a conflict (the base moved after the push), resolve it as in §7a and retry. Then fast-forward the local base branch and remove the worktree. Don't message the ticket's subagents after this.
   - `Closes #<n>` only closes the issue when the base is the repo's default branch. If the issue is still open after the merge, close it yourself: `gh issue close <n> -R <repo> -c "Done in PR #<m>"`.
7. Log one line: `✓ #<n> <title> → PR #<m> merged (<k> test cases passed)`.

Merge strictly one PR at a time. Each later ticket goes through the final gate again against the base branch as it was just updated.

## 7. Conflicts between tickets

### 7a. Merge conflicts

Try to resolve them yourself before involving anyone.
1. **Update the branch:**
   - **Not pushed yet:** rebase onto `origin/<base>`.
   - **Already pushed** (the PR exists): merge `origin/<base>` into the ticket branch, commit the merge, and push normally. Never rebase a pushed branch, since that needs a force-push. The squash-merge keeps the history clean anyway.
2. **Understand both sides** of each conflict:
   - this ticket's change and its intent;
   - the change on the base branch, from `git log -p origin/<base>` and the merged PR and ticket behind it.
3. **Resolve** so that **both** intents survive:
   - Combine the changes; don't simply take one side.
   - Regenerate generated files (lockfiles, migration snapshots, generated clients) with the project's tools instead of hand-merging them.
4. **Re-run the final gate** (§6, step 3): this ticket's test cases, and the full suite, which includes the merged ticket's test cases.
5. **Review the resolution:**
   - If it went beyond mechanically combining both sides (you changed logic to make them fit), have the reviewer from §5 check the resolution diff once.
   - Mention the resolution in the PR.

**Stop and ask the user** when:
- keeping both intents is impossible and one behaviour has to win (that's a spec conflict, §7b);
- the resolution would change an agreed test case;
- tests still fail after a resolution and the cause isn't clear.

### 7b. Failing tests and contradicting test cases

A conflict here is any of: tests (this ticket's or others') that pass alone but fail after rebasing onto newly merged work, or an implementer reporting that a test case contradicts another ticket or the codebase.

**Analyse before acting:**
- run the failing tests and read them;
- find which tickets' test cases and code are involved (`git log`, the test case IDs in test names);
- compare the cases against each other and the plan.

Then classify it:
- **Implementation bug in this ticket:** send it back to its implementer as a fix round, with the analysis.
- **Bug in code merged earlier in this run:** if the fix is small and needed for this ticket's cases, include it as a fix round and say so in the PR. Otherwise open a follow-up bug issue and stop this ticket if it's blocked.
- **Brittle test code** (shared state, test order, fixtures, time, randomness): fix the test code through the implementer, keeping every case's expected behaviour unchanged.
- **Spec conflict:** two agreed test cases can't both pass, or a later task changes behaviour an earlier case asserts without updating it. **Stop that ticket and ask the user.** Show both cases, the root cause, and the options with your recommendation. After the decision, update the affected tickets' test cases and send the plan update through the normal PR flow.
- **Unclear cause:** ask the user with what you found. Don't guess.

Never edit, delete or skip an agreed test case to resolve a conflict without the user's decision.

## 8. Checkpoints and reporting

- **End of every wave, in every checkpoint mode: hand off and end the session.** A coordinator's context grows with every ticket, and each turn re-sends all of it, so a fresh session per wave is much cheaper. After the last ticket of a wave merges:
  1. write the wave handoff into the run log (see "Run log");
  2. post the wave summary below;
  3. end with this message, filled in, and stop:

     > **Wave <N> is finished.** To keep token use low, clear this session with `/clear`, then run `/coordinator <the same arguments>` to start wave <N+1> (<k> tickets). The new session continues from the run log. <Anything to decide first, if there is.> If you have feedback first (a revert, follow-up tickets, plan changes), tell me before clearing and I'll record it for the next session.

  If the user replies with feedback or decisions, write them into the run log as open items (the next session applies them first), confirm in one line, and repeat the `/clear` instruction. Don't start the next wave in this session.
- **The wave summary** includes:
  - the merged PRs with links, what each changed in one line, and their test case counts;
  - the review findings that were fixed, rejected or turned into follow-ups;
  - any conflicts resolved, deviations or follow-up issues;
  - what the next wave contains;
  - **milestones ready for release:** when the last open ticket of a milestone merges, say so, and list the release steps from the project workflow (e.g. cut `release/X.Y.Z`, merge into `main`, tag). Don't run them; they need the user's approval.
  
- **`checkpoint=wave`** (default): pauses only at the wave handoff, hard gates and concerns. **`checkpoint=ticket`:** also pause after every merge. **`checkpoint=none`:** no extra pauses inside a wave; the wave handoff still ends the session.
- **Follow-ups:** findings outside a ticket's scope become new issues (type `task`, the right `area` label, linked to the same story, with test cases where they fit) only if the user agreed, or if they're clearly bugs in code merged during this run. List them in the summary.

## 9. Stop when

- the scope is done: mark the run log finished and give a final summary with every PR, the open follow-ups and the remaining blocked tickets;
- a wave is finished: hand off as in §8;
- the user interrupts or asks to stop;
- the same ticket has failed twice, or used up its fix rounds;
- nothing ready remains because everything left is blocked by gates or concerns. Report what's waiting on the user.

GitHub is the source of truth (closed issues and merged PRs), so a later run with the same scope picks up where this one stopped.
