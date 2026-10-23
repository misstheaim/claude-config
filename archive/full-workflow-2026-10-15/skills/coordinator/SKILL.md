---
name: coordinator
description: Coordinator mode, started only manually with /coordinator. Works through a repo's GitHub task tickets - picks unblocked tickets in plan order, has subagents implement them with the implement-ticket skill in isolated worktrees, has a separate reviewer subagent review each change, sends accepted findings to a fresh implementer, and commits, pushes, opens and merges PRs in that one repo once every test case passes and nothing is concerning, pausing at spikes, concerns and checkpoints.
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
- **Tooling:** check `gh auth status`. Load the `SendMessage` tool now (via ToolSearch if it's deferred); you need it to resume interrupted subagents (§3). Check that the agent types `ticket-implementer`, `ticket-reviewer`, `ticket-fixer` and `spec-writer` exist (`~/.claude/agents/`); if they don't, use `general-purpose` with the content of those files added to each prompt.
- **Run log:** look in `<git-common-dir>/coordinator/` (`git rev-parse --git-common-dir`; inside `.git`, so it's never committed and every worktree shares it).
  - **Continuing:** if the newest log has the same scope and isn't marked finished, this session continues that run (normally after a wave handoff, §8). Read it first, and reuse what it records (workflow in use, known baseline failures, the Fable choice, the user's decisions) without asking again. Open items it lists come first.
  - **New run:** otherwise create `run-<YYYY-MM-DD-HHMM>.md`. It's the coordinator's memory for this run; see "Run log" below.
  - **Event log:** next to it, append to `run-<YYYY-MM-DD-HHMM>.events.jsonl` (same name as the run log; create it on a new run). Write `session_start` in the same command that creates or reads the run log. See "Event log" below.
- **Dev tools on the machine:** find the toolchain the repo needs (from `docs/development.md`, a README "Requirements" section, or project files such as `package.json`, `go.mod`, `*.csproj`), and check each tool with its version command.
  - **If anything is missing, stop** and give the user the exact install commands. Never install system software yourself: this mode's authority covers only the GitHub repo.
  - Project-level dependencies such as `npm ci` and `go mod download` are fine; the subagents run them as part of their tickets.
- **Base branch:** resolve it (see the arguments) and tell the user which one you'll use.
- **Empty repo:** if the repo has no commits on its base branch, stop. Ask the user to do the bootstrap ticket first (e.g. with `/implement-ticket`) and push it, so PRs have a base branch.
- **Starting point:** `git fetch origin <base>`; the local base branch is clean and fast-forwards to `origin/<base>`. If it isn't, stop and ask.
- **Baseline check:** skip it when continuing a run and `origin/<base>` is still at the commit the wave handoff recorded (the final gates already proved it green). Also skip it when the project has no working commands yet because its bootstrap ticket is still open: run that ticket first, alone, and treat its final gate as the baseline. Otherwise, on `origin/<base>`, run the workflow's build, lint and full test suite once. If anything fails, **stop** and report the failures: every ticket's final gate would fail on them, and implementers would be blamed for problems they didn't cause. Continue only after the user fixes them or tells you which failures to treat as known (record those in the run log).
- **Plan:** find the plan the tickets reference: a main plan `docs/plans/README.md` with area plans `docs/plans/<area>.md`, or an older single document `docs/plans/<slug>.md`. It must be on `origin/<base>`, with the issue numbers in it: subagents work in worktrees created from the remote and only see what's pushed. If it's missing there or the local copy differs, stop and ask the user to push it (through a PR) first. The main plan's "Order of work" (waves) decides the order; without one, use the dependency graph, then issue number.
- **Behaviour spec:** one check, no reading: is `docs/spec/README.md` on `origin/<base>` (`git cat-file -e origin/<base>:docs/spec/README.md`)? Note it in the run log. The spec writer reads the spec itself. Without a spec, check `<git-common-dir>/coordinator/spec-declined` (the user said no for this project) and the run log's spec choice; both decide whether the wave end offers to create one (§8).
- **Build the queue:**
  - open issues labelled `type:task` within the scope;
  - drop tickets that already have an open PR or a branch named after them, and report them as "in progress elsewhere".
- **Fable tickets:** a ticket whose "Suggested model" is Fable can't run as suggested. Unless the run log already records the choice, ask the user once, for all of them: run with Opus, or leave them out of this run (e.g. to split them, or to do them in a separate session the user starts).
- **Show the user** the queue in wave order with the first wave highlighted, marking the tickets that have no test cases (they'll get a goal check instead, §4), the tickets with another base (they'll stop before merging, §6) and the Fable tickets. Then start. Don't wait for approval unless something looks wrong or there are Fable tickets.

### Run log

Your context can be compacted during a long run, and in-flight state lost with it. Keep it in the run log instead of relying on memory:
- **What goes in:** the workflow in use, known baseline failures, and one entry per ticket in flight (ticket, model, implementer agent ID, reviewer agent ID and the `origin/<base>` commit it reviewed against, each agent's last-turn time and context size, branch, worktree path, fix rounds, state, triage decisions), updated **after every state change**.
- **The spec choice** (§8, "Wave spec update"): `none yet`, `separate session` or `declined`, so the offer isn't repeated.
- **The user's decisions** during the run go into the log, and also as a comment on each affected ticket, so later sessions see them too.
- **After a compaction** (or whenever you're unsure of the state), re-read the log before acting.
- **At a wave handoff** (§8): the waves done, `origin/<base>`'s current commit, the next wave's tickets, open items waiting on the user, and the follow-ups created. Mark the log **finished** when the scope is done.
- **A stopped ticket** (§9) keeps its worktree, and with it the ticket notes, so a later session can continue it. The log records the worktree path.

### Ticket notes

Each implementer keeps `<worktree>/.scratch/ticket-notes.md`: the ticket's status, approach, criteria and test case status, decisions (including what was tried and dropped, and how review findings were handled), gotchas and a short log, capped at about 800 lines (about 20k tokens) (`ticket-implementer` defines it). It holds the implementer's working context that its report doesn't bring back to you, so a fresh agent on the ticket (a review follow-up round, a recovery, a conflict fix) can pick up where the last one stopped instead of starting from your brief alone.
- **Point every fresh implementer and fixer at it** (§3): an implementer reads it first, so your brief stays short; a fixer only appends a log line.
- **Reviewers don't get it:** they judge the code independently, and their prompt doesn't mention it.
- **Don't read it yourself** as routine; reports, reviews and the diff are your view. Read only its Status section when an agent died without a usable report and you need it for a recovery brief.
- **It's deleted with the worktree** after the PR merges (§6). Notes never go into a commit; `.scratch/` is ignored.

### Event log

Besides the run log (for you), keep a machine-readable event log for the `analyze-coordinator` skill. Log **only your judgments**; the analyzer reads everything mechanical (dispatches, resumes, PRs, merges, CI, tokens) from the transcripts. The full spec is `references/events.md`; you don't need to read it, the list below is enough.

- **Events:** `session_start` {wave, continuing}, `baseline` {result, known_failures}, `wave_start` {wave, tickets}, `agent_return` {ticket, agent_id, outcome: question/partial/error; only when it's not a finished report}, `escalation` {ticket, kind: business/blocker/destructive/technical, resolved_by: coordinator/user}, `user_wait` {reason, ticket}, `review` {ticket, path: full/light/skipped, reason (when skipped), findings: {critical,high,medium,low,nit}, verification_failures, tampering}, `triage` {ticket, fix, reject, followup, ask}, `final_gate` {ticket, result, cause}, `conflict` {ticket, kind: merge/tests/spec, class, resolved_by}, `ticket_stopped` {ticket, reason}, `spec` {wave, result: updated/no-change/missing, mismatches, choice: separate-session/declined (when missing)}, `wave_handoff` {wave, merged, open}, `run_finished` {merged, stopped}. Every line also has `ts` (ISO 8601 UTC) and `event`.
- **Every merged ticket has a `review` and a `final_gate` event.** When a ticket gets no review at all (e.g. a spike's report-only PR or a plan update), log `review` with `path: "skipped"` and a one-line `reason`. `ship.sh` appends `final_gate` and `merged` when you pass `--events` (§6); write them yourself only when you ship by hand.
- **Never spend a tool call on an event.** Chain the append onto a command you run anyway (`… && printf '%s
' '<json>' >> "$EVENTS"`), or put it in the same message as your next tool call. Events that happen together go in one `printf` with several lines.
- **Every ticket subagent's prompt starts with `Ticket #<n>:`**, so the analyzer can match the subagent to its ticket. A spec writer's prompt starts with `Spec update wave <N>:`, `Spec init <area>:` or `Spec verify:` instead.
- Append only; never edit, delete or read the log back.

### Context hygiene

- Run builds and test suites with their output redirected to a log file next to the run log; read only the summary and the failures.
- Ask subagents for compact reports (their agent definitions already do), and don't paste full diffs or logs into your own replies.

### Asking the user

The user may come back to a question after a long break, without the run's context. Make every question (`AskUserQuestion` or plain text) self-contained:
- **Open with 1-2 sentences** that give the situation and define any domain or project term the question relies on (e.g. what a "snapshot" is in this codebase). Don't assume the user remembers ticket numbers, test case IDs or earlier findings; say what they are.
- **State each option's consequence:** what changes, what it costs, what it rules out later. In `AskUserQuestion`, put it in the option's description.
- **Recommendation first:** put the option you recommend first, with "(Recommended)" at the end of its label, and say why in one line.

## 2. Pick the next tickets

**Ready** means:
- the ticket is open;
- every `blocked_by` issue is closed (check `gh api repos/<repo>/issues/<n>/dependencies/blocked_by`);
- every blocker's PR is merged.

Take up to `parallel` ready tickets from the current wave.

**Don't run overlapping tickets together.** Before dispatching a batch, compare the tickets' "Files / modules" notes (and the parts of the codebase they obviously touch). Tickets that would change the same files or the same contract run one after another, not in parallel: parallel agents can't see each other's decisions. Note the reason in the run log.

**Hard gates.** Do not dispatch these; stop and talk to the user instead:
- **Spikes** (title starts with "Spike", or the body says owner-assisted / needs the user):
  1. Dispatch only the automatable part, telling the subagent to stop before the manual part. If that part is mostly measurement plus a report (benchmarks, timings, compatibility checks), consider `sonnet` with `effort: "medium"` even when the ticket suggests Opus. Keep the suggested model when the spike has to design or judge something.
  2. Then present the findings and the manual steps, and **discuss them with the user**. **Batch spike decisions:** when several spikes run in the same wave, don't stop after each one. Keep the other tickets going, wait until every spike's report is in, then ask all their questions in one checkpoint (one `user_wait`): one `AskUserQuestion` call with up to 4 questions, or several calls back to back if there are more. Ask early only when a spike's answer blocks the rest of the wave.
  3. After the user agrees, update the plan and the affected tickets. Commit the plan update through the normal PR flow.
- **Unclear tickets** (no testable acceptance criteria, or a dependency on a pending design decision): ask.

## 3. Dispatch

For each ticket, launch one implementer subagent with the Agent tool:
- **`subagent_type: "ticket-implementer"`**. Its definition carries the standing rules (worktree only, no commits, fixed test cases, compact reports, follow-up rounds).
- **`isolation: "worktree"`**, so parallel tickets never share a working tree.
- **`model`** from the ticket's "Suggested model": Haiku → `haiku`, Sonnet → `sonnet`, Opus → `opus`. Fable → `opus` only if the user chose that in preflight. Without one, use `sonnet`. **Never pass `fable`.**
- **`effort`** by the same tier, to keep thinking tokens in proportion: Haiku → `low`, Sonnet → `medium`, Opus → `high`.
- **Prompt:** "Ticket #<n>: implement GitHub issue #<n> in <repo> --autonomous, branching from the latest `origin/<base>`. The project's workflow is in its CLAUDE.md and docs/development.md. Read only the plan sections the ticket cites." Add any user decisions from this run that affect the ticket.

**Questions from implementers.** Implementers run in autonomous mode and decide technical questions themselves ("Autonomous: decide or escalate" in `implement-ticket`) and return only business decisions, real blockers or destructive actions. When one returns a question anyway:
- **Technical, or settled by the ticket, plan or workflow:** answer it yourself, with your best judgment where nothing settles it. Don't pass it to the user.
- **Business or product decision, or a blocker only the user can remove:** ask the user. Collect such questions across tickets in flight and ask them together.

Then send the answer per "Resume or dispatch fresh" below (an agent that stopped with a question hasn't finished), and record the decision in the run log and on the ticket. Also skim each report's "Decisions made"; challenge one only if it contradicts the plan or the ticket.

**Keep track of every ticket in flight** in the run log: ticket number, implementer agent ID (from the Agent result), model, branch, worktree path, reviewer agent ID, and the fix-round count. For each agent, also note the time of its last turn, its context size (the token total its last result reports) and whether it finished. The worktree stays after an agent returns, because it has changes.

**Resume or dispatch fresh.**
- **Finished agents are never resumed.** Once an implementer, fixer or reviewer has returned its final report and you've moved on (review, fixes, re-check, CI), every later round on that ticket goes to a **fresh agent** with a compact brief (below), never a `SendMessage`.
- **Interrupted agents** (stopped by an error, a limit, or with a question before finishing): resume with `SendMessage` if its context is under about **200k tokens** **or** less than **5 minutes** have passed since its last turn (its prompt cache is still warm, so even a large history is cheap to resume). Dispatch a fresh agent with a recovery brief (below) only when both fail: the context is over 200k **and** more than 5 minutes have passed.
- **A scope or design change** (e.g. the ticket's approach has to be redesigned) always gets a fresh agent.

A fresh agent has the same type and model and works on the same worktree and branch (no isolation). Its prompt starts with `Ticket #<n>:`, then the worktree path, branch and base. A fresh **implementer** also gets the line "Read `.scratch/ticket-notes.md` first: the previous agent's notes on this ticket." Then:
- **Compact brief** (follow-up round): the diff so far (`git diff --stat origin/<base>...`), and the findings with the agreed fixes, or the decision it needs. For an implementer, leave the approach to the notes; describe it in a few lines only if the worktree has no notes. A fresh reviewer gets a few lines on the approach (it doesn't read the notes) plus the earlier findings and how each was handled.
- **Recovery brief** (interrupted agent): why it stopped (the error or question, and the answer if there is one), what's done (from its last output and the diff), and what's left (the remaining steps and test cases). Check the worktree state yourself (`git status`, `git diff --stat`) rather than trusting the interrupted agent's last words or its notes.

The fresh agent becomes the ticket's owner; update its agent ID in the run log.

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

1. **Launch one reviewer** with the Agent tool: `subagent_type: "ticket-reviewer"`, no worktree isolation, `effort: "high"`. It does both the verification and the review, so you don't repeat its work. **Model:** budget Opus against usage limits (never `fable`):
   - **Default: `sonnet`.** This covers tickets implemented on Haiku or Sonnet, and scaffold, docs or contract tickets (project setup, interfaces, schemas, API definitions) whatever their tier.
   - **`opus` only for Opus-tier tickets**, i.e. tickets whose implementer ran on Opus.
   - **Exception:** anything touching auth, payments, data migrations or security-sensitive code gets `opus`, whatever its tier or size.

   Its prompt starts with `Ticket #<n>:` and contains: the repo, worktree path, branch and base (`origin/<base>`), the plan path, the workflow's commands, a log directory next to the run log for its command output, the path `~/.claude/skills/decompose-feature/references/test-cases.md`, and, for a ticket without test cases, your goal-check checklist.

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
   - **A fresh implementer** (`subagent_type: "ticket-implementer"`, same model as the original, no isolation, the compact brief from §3) when any fix needs understanding of the change: logic bugs, missing behaviour, failing test cases, design problems.
   - **A fresh fixer** (`subagent_type: "ticket-fixer"`, no isolation) when **every** fix is mechanical and small (renames, a missing null check, a lint error, a small test tweak): `model: "haiku"`, `effort: "low"`; use `sonnet` with `effort: "medium"` if a fix needs a little reasoning. Its prompt starts with `Ticket #<n>:`, then the worktree path, the base, and each fix with file, location and the exact change.

   One round goes to one agent: if the findings are mixed, send them all to a fresh implementer.
4. **Send the fixes** in one message: the numbered findings with the agreed fix, plus "Apply only these, run lint and the tests the fixes affect (the coordinator runs the full suite at the end), and report."5. **Re-check:**
   - Read the fixer's report and the changed hunks yourself.
   - Dispatch a fresh `ticket-reviewer` (same model, with the compact brief from §3, including its predecessor's findings and how each was handled) only if a `high`/`critical` finding was fixed or the fixes went beyond small local changes.
6. **Limit:** at most **2 fix rounds** per ticket. If findings remain after that, stop that ticket and ask the user, with what's still open.

Other tickets in flight may continue while one waits. Keep the triage (fixed / rejected with reason / follow-up, and who fixed it) in the run log for the PR and the wave summary.

## 6. Ship it

The mechanical tail runs in **one script call**: `<skill-dir>/scripts/ship.sh` (bash; on Windows through the Bash tool, Git Bash). In order, it commits the ticket's changes, brings the branch up to date with `origin/<base>` (rebase while unpushed, merge once pushed, never a force-push) and runs the **final gate**: every gate command with output to a log file, then `git status --porcelain` must be empty. It appends the `final_gate` event itself, and the `merged` event right after the merge. Then it pushes, opens the PR (or reuses the open one) and waits until CI checks are **registered and all passed**: "no checks" never counts as green while the base has workflows. Last, it merges with the workflow's method, deletes the remote branch, fast-forwards the local base, removes the worktree (a lock left by an exited agent is cleared; a worktree locked by a live process or a folder Windows keeps busy is reported, with the ticket notes deleted), closes the issue if it's still open, and appends the DONE line to the run log. It's idempotent: after a fix round, a conflict resolution, a CI timeout or a killed run, run the same command again. If the PR is already merged (a run killed between the merge and the cleanup), a re-run only finishes the cleanup, and gates that already passed on the same commit (e.g. before a `--no-merge` stop) aren't run again. Waiting for CI stops within a time budget (`--budget`, default 540 s) with exit 22 instead of being killed. It also prints the files in the change (vs `origin/<base>`), so you can see what was committed.

**Merge strictly one PR at a time:** never run two `ship.sh` calls at once. Each later ticket goes through the final gate again against the base branch as it was just updated. Other tickets' implementers and reviewers keep working meanwhile.

1. **One Bash call:** write the PR body file (next to the run log, in `logs/`) and run the script in the same command, with `timeout: 600000`:

   ```bash
   cat > "$LOGS/pr-<n>.md" <<'EOF'
   <the user's PR template: Summary, Changes, Testing (the test cases with results, or the goal-check checklist; the review triage in a few lines), Ticket: Closes #<n>>
   EOF
   bash <skill-dir>/scripts/ship.sh --worktree <path> --ticket <n> --base <base> --repo <owner/repo> \
     --message "feat(#<n>): <summary>" --title "#<n> <Title>" --body-file "$LOGS/pr-<n>.md" \
     --gate build="<workflow build command>" --gate lint="<workflow lint command>" --gate tests="<workflow full test suite>" \
     --merge-method <squash|merge|rebase> --events "$EVENTS" --runlog "<run log>"
   ```

   - Commit message, PR title and template follow the user's conventions. There's one `--gate name=command` per workflow command, and the **full** test suite is always one of them (the one full run after the implementer's own). Each runs from the worktree root, so use `cd <dir> && …` or `--prefix` inside it. Name them `build`, `lint` and `tests` (several of one kind: `tests`, `tests`, …), because the name becomes the `final_gate` event's `cause`.
   - **A long suite:** the gates aren't covered by the time budget. If build, lint and the full suite together may take more than about 6 minutes, run the call with `run_in_background: true` and `--budget 3600`, and act on its result when you're notified.
   - Run it from the main checkout, only after the review and its fix rounds (§5) are done and every other condition in "When a ticket is done" holds; the script checks the rest. If the printed file list shows a file that doesn't belong to the ticket, don't let it merge unnoticed: fix it in a fix round.
   - **UI tickets whose base moved since the review** (`origin/<base>` has moved past the commit you noted in the run log when the reviewer started): add `--no-merge`. At exit 40 the PR is green on the updated branch: repeat the UI end-to-end check on it (the reviewer's §5 check, run by you or a fresh reviewer), then run the same command without `--no-merge`.
   - **A `Refs #<n>` PR** (e.g. a plan update for a ticket that stays open): add `--no-close`, so the merge doesn't close the issue.
   - **A docs PR with no ticket** (the spec update, `init-spec`): `--doc <name>` instead of `--ticket`. Gates are optional, it writes no events and closes no issue.
   - **Ticket base isn't the run's base** (e.g. a hotfix into `main`): add `--no-merge`. The script stops at a green PR (exit 40). Show it to the user with the steps the workflow prescribes after merging (e.g. tag, release, merge `main` back into the run's base), and ask for approval. After approval, run it again without `--no-merge` (with that branch's merge method) and do the approved steps. Tags and releases need their own explicit approval in that same request.
2. **Act on the last line**, `RESULT: <code> <word> …`:

   | Code | Meaning | What you do |
   |---|---|---|
   | 0 `merged` | done | Log `✓ #<n> <title> → PR #<m> merged (<k> test cases passed)` in your reply. Don't message the ticket's subagents after this. |
   | 3 `conflict` | rebase or merge onto `origin/<base>` stopped, left in progress | Resolve as in §7a (finish with `git rebase --continue` or a merge commit), then re-run. |
   | 10 `gate-failed` | a gate (named, with a log tail) failed, or git is dirty | `tests` failing now that passed in the implementer's and reviewer's runs means another ticket is involved: §7b. Anything else: fix round (§5). Then re-run. |
   | 11 `commit-failed` | `git add`/`git commit` failed (its output is printed); a git or setup problem, not the code | No fix round. Read the git output, fix the cause (e.g. a hook, an index lock, a bad path), then re-run. |
   | 20 `ci-failed` | a check failed (names and links printed) | Fix round (§5) or stop and ask, then re-run. |
   | 21 `ci-not-registered` | workflows exist, but no check appeared | Look at the PR's Actions tab (`gh run list`); re-run once. If it's still missing, stop and ask. Never merge by hand. |
   | 22 `ci-timeout` | checks still running when the time budget ran out (nothing half done) | Re-run; it reuses the PR and keeps waiting. After 3 timeouts in a row, check the run (`gh run list`) and stop and ask if it's stuck. |
   | 30 `merge-failed` | GitHub refused the merge | Usually a conflict that just landed on the base: re-run (it merges `origin/<base>` into the branch and goes through the gate again), or resolve as in §7a. |
   | 40 `ready` | `--no-merge`: green PR, not merged | The UI re-check or the approval above. |
   | 2 `usage` | bad arguments or nothing to ship | Fix the call. |

If the script can't be used (it's missing, or the project needs a step it doesn't cover), do the same steps by hand in this order, with the same rules.

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
4. **Re-run `ship.sh`** (§6): its final gate runs this ticket's test cases and the full suite, which includes the merged ticket's test cases.
5. **Review the resolution:**
   - If it went beyond mechanically combining both sides (you changed logic to make them fit), have the reviewer from §5 check the resolution diff once.
   - Mention the resolution in the PR.

**Stop and ask the user** when:
- keeping both intents is impossible and one behaviour has to win (that's a test case conflict, §7b);
- the resolution would change an agreed test case;
- tests still fail after a resolution and the cause isn't clear.

### 7b. Failing tests and contradicting test cases

A conflict here is any of: tests (this ticket's or others') that pass alone but fail after rebasing onto newly merged work, or an implementer reporting that a test case contradicts another ticket or the codebase.

**Analyse before acting:**
- run the failing tests and read them;
- find which tickets' test cases and code are involved (`git log`, the test case IDs in test names);
- compare the cases against each other and the plan.

Then classify it:
- **Implementation bug in this ticket:** send it to a fresh implementer as a fix round, with the analysis.
- **Bug in code merged earlier in this run:** if the fix is small and needed for this ticket's cases, include it as a fix round and say so in the PR. Otherwise open a follow-up bug issue and stop this ticket if it's blocked.
- **Brittle test code** (shared state, test order, fixtures, time, randomness): fix the test code through a fresh implementer, keeping every case's expected behaviour unchanged.
- **Test case conflict** (logged as `kind: spec` / `spec-conflict`, names from before the behaviour spec): two agreed test cases can't both pass, or a later task changes behaviour an earlier case asserts without updating it. **Stop that ticket and ask the user.** Show both cases, the root cause, and the options with your recommendation. After the decision, update the affected tickets' test cases **and spec changes**, and send the plan update through the normal PR flow. The behaviour spec itself follows at the wave's spec update.
- **Unclear cause:** ask the user with what you found. Don't guess.

Never edit, delete or skip an agreed test case to resolve a conflict without the user's decision.

## 8. Checkpoints and reporting

- **End of every wave, in every checkpoint mode: hand off and end the session.** A coordinator's context grows with every ticket, and each turn re-sends all of it, so a fresh session per wave is much cheaper. After the last ticket of a wave merges:
  1. run the wave spec update (below);
  2. write the wave handoff into the run log (see "Run log");
  3. post the wave summary below;
  4. end with this message, filled in, and stop:

     > **Wave <N> is finished.** To keep token use low, clear this session with `/clear`, then run `/coordinator <the same arguments>` to start wave <N+1> (<k> tickets). The new session continues from the run log. <Anything to decide first, if there is.> If you have feedback first (a revert, follow-up tickets, plan changes), tell me before clearing and I'll record it for the next session.

  If the user replies with feedback or decisions, write them into the run log as open items (the next session applies them first), confirm in one line, and repeat the `/clear` instruction. Don't start the next wave in this session.
- **The wave summary** includes:
  - the merged PRs with links, what each changed in one line, and their test case counts;
  - the review findings that were fixed, rejected or turned into follow-ups;
  - any conflicts resolved, deviations or follow-up issues;
  - the spec update: the PR and the items added, changed and retired, the mismatches (deltas the code doesn't match), or why there was none (no spec yet, and the choice);
  - what the next wave contains;
  - **milestones ready for release:** when the last open ticket of a milestone merges, say so, and list the release steps from the project workflow (e.g. cut `release/X.Y.Z`, merge into `main`, tag). Don't run them; they need the user's approval.
  
- **`checkpoint=wave`** (default): pauses only at the wave handoff, hard gates and concerns. **`checkpoint=ticket`:** also pause after every merge. **`checkpoint=none`:** no extra pauses inside a wave; the wave handoff still ends the session.
### Wave spec update

The behaviour spec (`docs/spec/`, format: `~/.claude/skills/init-spec/references/spec-format.md`) says how the product behaves now. Implementers never edit it; you bring it up to date once per wave, from the merged code, before the handoff.

**The project has a spec:**
1. **Skip** only when the tickets merged since the last spec update changed nothing but docs, plans, specs or CI config (you know this from their diffs; no need to read the spec). Other commits, such as a hotfix, are picked up by the next update, which covers everything since `Synced to`. Log `spec` with `result: no-change`.
2. **Worktree:** `git worktree add -b docs/spec-wave-<N> <repo>/.claude/worktrees/spec origin/<base>` (remove an old one at that path first), then `mkdir -p` its `.scratch/`. `.claude/worktrees/` must be in `<git-common-dir>/info/exclude`, so the main checkout doesn't look dirty; add it once if it isn't.
3. **Dispatch one `spec-writer`** (`model: "sonnet"`, `effort: "medium"`, no isolation). Its prompt starts with `Spec update wave <N>:` and gives the worktree, the base, the target commit (`origin/<base>`), and each ticket merged since the last spec update: number, PR, one line on what changed, and its spec change IDs from the ticket. Add the wave's review findings that turned into follow-ups, so known broken behaviour goes under "Known issues".
4. **Check its report and the scope of its change** (`git -C <worktree> status --porcelain`, one call; don't read the spec diff, the report already says what each mismatch is): only `docs/spec/` changed, and the report covers every merged ticket's spec changes or explains why not. A **mismatch** (the code doesn't do what a ticket's delta said) is a review finding that came too late: if it looks like a bug, create a follow-up issue (see "Follow-ups"); if the code's behaviour is fine and the delta was wrong, note it for the plan. List both in the wave summary.
5. **Ship it** without a review, in one call: write the PR body (the user's template with the item counts and mismatches under Summary, no `Closes` line and no Ticket section) and run `<skill-dir>/scripts/ship.sh --doc spec-wave-<N> --worktree <repo>/.claude/worktrees/spec --base <base> --repo <owner/repo> --title "Update spec for wave <N>" --message "docs: update spec for wave <N>" --body-file <file> --runlog "<run log>"` with the merge method, no gates (docs only) and no `--events`. Chain the `spec` event (`result: updated`, the mismatch count) onto it.

**The project has no spec** (`docs/spec/README.md` isn't on `origin/<base>`): unless `<git-common-dir>/coordinator/spec-declined` exists or the run log already records a choice, offer to create one, once per run, as part of the handoff (a `user_wait` with reason `checkpoint`). Explain in two sentences what the spec is (how the product behaves now, one file per area, kept current after each wave, and what the plans' spec changes land in) and what creating it costs (the `init-spec` skill: one Sonnet agent per area reading that part of the code, plus a verification pass; roughly $0.5-2 per area). It always runs in its own session, never in this one: its scan would land in your context. Options:
- **Create it in a separate session** (recommended): record it in the run log; the user runs `/clear` and `/init-spec` (on Sonnet is enough) before the next `/coordinator`, or whenever they like. Don't offer it again in this run; remind them in one line in each handoff while the spec is missing.
- **Not for this project:** write `<git-common-dir>/coordinator/spec-declined` (local, never committed) so no later run asks again; deleting it re-enables the offer.

Log `spec` with `result: missing` at every handoff while the spec is missing, with the `choice` the first time; the analyzer uses it to tell a missing spec from a skipped update. The tickets' spec changes stay in the plan either way; the first spec update after the spec exists picks up everything merged since its `Synced to`.

- **Follow-ups:** findings outside a ticket's scope become new issues (type `task`, the right `area` label, linked to the same story, with test cases where they fit) only if the user agreed, or if they're clearly bugs in code merged during this run. List them in the summary.

## 9. Stop when

- the scope is done: append `run_finished` (in the same command that marks the run log finished), mark the run log finished and give a final summary with every PR, the open follow-ups and the remaining blocked tickets;
- a wave is finished: hand off as in §8;
- the user interrupts or asks to stop;
- the same ticket has failed twice, or used up its fix rounds;
- nothing ready remains because everything left is blocked by gates or concerns. Report what's waiting on the user.

GitHub is the source of truth (closed issues and merged PRs), so a later run with the same scope picks up where this one stopped.
