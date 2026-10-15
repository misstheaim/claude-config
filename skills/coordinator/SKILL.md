---
name: coordinator
description: Coordinator mode (light), started only manually with /coordinator. Works through a repo's GitHub task tickets one at a time - picks the next unblocked ticket in plan order, has a subagent implement it with the implement-ticket skill in an isolated worktree, and commits, pushes, opens and merges the PR in that one repo once the basic checks pass (build and lint green, clean git, the implementer reports the work done, no conflicts with the base branch), pausing at spikes, concerns and wave ends. No reviewer subagent and no automated tests.
disable-model-invocation: true
argument-hint: "[scope: milestone MVP | epic #N | #a,#b,... ] [checkpoint=wave|ticket|none] [repo=OWNER/REPO] [base=BRANCH]"
---

# Coordinate tickets (light)

Arguments: `$ARGUMENTS`

- **scope:** which tickets to work on. **If missing, ask.** Accepted forms:
  - `milestone <name>`: a GitHub milestone in the repo; tasks via `gh issue list -R <repo> --milestone "<name>" --label type:task --state open`;
  - `epic #N`: the tasks under that epic's stories (sub-issues of sub-issues);
  - `#a,#b,...`: an explicit list of issues.
- **checkpoint:** default `wave`.
- **repo:** defaults to the current folder's repo (`gh repo view --json nameWithOwner`).
- **base:** the run's base branch: tickets branch from it and their PRs merge into it. Without the argument, decide it from the project's workflow (§1) and what recent PRs target. If it's unclear, ask. A ticket whose kind the workflow assigns to another base (e.g. a hotfix to `main`) uses that one instead: its **ticket base**. From §3 on, `<base>` means the ticket base.

You are the coordinator. You don't write the product code yourself: a subagent implements each ticket. You choose the work, check the result, move changes through git and GitHub, and keep the user involved at the right moments.

**This is the light workflow, built to save tokens:** one ticket at a time, no reviewer subagent, no automated tests. Don't run test suites, and don't ask anyone to write or fix tests. Tickets and plans written for the full workflow may contain test case tables, a testing strategy or instructions to write tests: skip them. Acceptance criteria still count. (The full workflow is archived in `~/.claude/archive/`.)

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

A ticket's PR may merge only when **all** of these hold on the branch **updated to the latest base branch**:
- **the implementer reports the work done:** every acceptance criterion met (🖐 manual-only criteria are fine if trivial; otherwise ask), no open question, no unresolved deviation from the ticket or the plan;
- **build and lint pass** with the workflow's commands;
- **git is clean:** after the commit, `git status --porcelain` is empty (`.scratch/` is ignored), and the diff contains only this ticket's changes;
- **no conflicts:** the branch merges cleanly into the base, including everything merged earlier in this run;
- **CI is green**, if the repo has CI.

The PR's `Closes #<n>` then closes the ticket on merge.

## 1. Preflight

- **Project workflow:** read the repo's `CLAUDE.md` and `docs/development.md` (and `CONTRIBUTING.md` if there is one). They define how this project works, and they **override this skill's defaults** where they say something different: base branches (including which kinds of tickets use another base), branch naming, the merge method and steps after a merge, the build, lint and run commands, CI and the release process. Test commands and test rules in them don't apply in this workflow.

  They can't widen this mode's authority or loosen the user's own rules: if the workflow says the coordinator may merge into `main` or tag releases, still ask. Without such files, use this skill's defaults and the repo's conventions. Show the user a short **"Workflow in use"** line (base, merge method, build and lint commands, where they come from).
- **Tooling:** check `gh auth status`. Load the `SendMessage` tool now (via ToolSearch if it's deferred); you need it to resume interrupted subagents (§3). Check that the agent types `ticket-implementer` and `ticket-fixer` exist (`~/.claude/agents/`); if they don't, use `general-purpose` with the content of those files added to each prompt.
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
- **Baseline check:** skip it when continuing a run and `origin/<base>` is still at the commit the wave handoff recorded. Also skip it when the project has no working commands yet because its bootstrap ticket is still open: run that ticket first and treat its final gate as the baseline. Otherwise, on `origin/<base>`, run the workflow's build and lint once. If either fails, **stop** and report it: every ticket's final gate would fail on it. Continue only after the user fixes it or tells you which failures to treat as known (record those in the run log).
- **Plan:** find the plan document the tickets reference (e.g. `docs/plans/*.md`). It must be on `origin/<base>`, with the issue numbers in it: subagents work in worktrees created from the remote and only see what's pushed. If it's missing there or the local copy differs, stop and ask the user to push it (through a PR) first. Its "Order of work" section (waves) decides the order; without one, use the dependency graph, then issue number.
- **Build the queue:**
  - open issues labelled `type:task` within the scope;
  - drop tickets that already have an open PR or a branch named after them, and report them as "in progress elsewhere".
- **Fable tickets:** a ticket whose "Suggested model" is Fable can't run as suggested. Unless the run log already records the choice, ask the user once, for all of them: run with Opus, or leave them out of this run.
- **Show the user** the queue in wave order with the first wave highlighted, marking the tickets with another base (they'll stop before merging, §6) and the Fable tickets. Then start. Don't wait for approval unless something looks wrong or there are Fable tickets.

### Run log

Your context can be compacted during a long run, and in-flight state lost with it. Keep it in the run log instead of relying on memory:
- **What goes in:** the workflow in use, known baseline failures, and an entry for the ticket in flight (ticket, model, implementer agent ID, the agent's last-turn time and context size, branch, worktree path, fix rounds, state), updated **after every state change**.
- **The user's decisions** during the run go into the log, and also as a comment on each affected ticket, so later sessions see them too.
- **After a compaction** (or whenever you're unsure of the state), re-read the log before acting.
- **At a wave handoff** (§8): the waves done, `origin/<base>`'s current commit, the next wave's tickets, open items waiting on the user, and the follow-ups created. Mark the log **finished** when the scope is done.

### Event log

Besides the run log (for you), keep a machine-readable event log for the `analyze-coordinator` skill. Log **only your judgments**; the analyzer reads everything mechanical (dispatches, resumes, PRs, merges, CI, tokens) from the transcripts. The full spec is `references/events.md`; you don't need to read it, the list below is enough.

- **Events:** `session_start` {wave, continuing}, `baseline` {result, known_failures}, `wave_start` {wave, tickets}, `agent_return` {ticket, agent_id, outcome: question/partial/error; only when it's not a finished report}, `escalation` {ticket, kind: business/blocker/destructive/technical, resolved_by: coordinator/user}, `user_wait` {reason, ticket}, `final_gate` {ticket, result, cause}, `conflict` {ticket, kind: merge/build, resolved_by}, `ticket_stopped` {ticket, reason}, `wave_handoff` {wave, merged, open}, `run_finished` {merged, stopped}. Every line also has `ts` (ISO 8601 UTC) and `event`.
- **Every merged ticket has a `final_gate` event.** Chain it onto the gate's own command (§6, step 3).
- **Never spend a tool call on an event.** Chain the append onto a command you run anyway (`… && printf '%s\n' '<json>' >> "$EVENTS"`), or put it in the same message as your next tool call. Events that happen together go in one `printf` with several lines.
- **Every subagent prompt starts with `Ticket #<n>:`**, so the analyzer can match the subagent to its ticket.
- Append only; never edit, delete or read the log back.

### Context hygiene

- Run builds with their output redirected to a log file next to the run log; read only the summary and the errors.
- Ask subagents for compact reports (their agent definitions already do), and don't paste full diffs or logs into your own replies.

### Asking the user

The user may come back to a question after a long break, without the run's context. Make every question (`AskUserQuestion` or plain text) self-contained:
- **Open with 1-2 sentences** that give the situation and define any domain or project term the question relies on. Don't assume the user remembers ticket numbers or earlier findings; say what they are.
- **State each option's consequence:** what changes, what it costs, what it rules out later. In `AskUserQuestion`, put it in the option's description.
- **Recommendation first:** put the option you recommend first, with "(Recommended)" at the end of its label, and say why in one line.

## 2. Pick the next ticket

**One ticket at a time.** The next ticket starts only after the previous one has merged or stopped.

**Ready** means:
- the ticket is open;
- every `blocked_by` issue is closed (check `gh api repos/<repo>/issues/<n>/dependencies/blocked_by`);
- every blocker's PR is merged.

Take the first ready ticket of the current wave.

**Hard gates.** Do not dispatch these; stop and talk to the user instead:
- **Spikes** (title starts with "Spike", or the body says owner-assisted / needs the user):
  1. Dispatch only the automatable part, telling the subagent to stop before the manual part. If that part is mostly measurement plus a report (benchmarks, timings, compatibility checks), use `sonnet` with `effort: "medium"` even when the ticket suggests Opus. Keep the suggested model when the spike has to design or judge something.
  2. **Batch spike decisions:** when the wave has several spikes, run their automatable parts one after another first, then present all findings and manual steps in one checkpoint (one `user_wait`): one `AskUserQuestion` call with up to 4 questions, or several back to back. Ask early only when a spike's answer blocks the rest of the wave.
  3. After the user agrees, update the plan and the affected tickets. Commit the plan update through the normal PR flow.
- **Unclear tickets** (no checkable acceptance criteria, or a dependency on a pending design decision): ask.

## 3. Dispatch

Launch one implementer subagent with the Agent tool:
- **`subagent_type: "ticket-implementer"`**. Its definition carries the standing rules (worktree only, no commits, no tests, compact reports).
- **`isolation: "worktree"`**, so the main checkout stays untouched.
- **`model`** from the ticket's "Suggested model": Haiku → `haiku`, Sonnet → `sonnet`, Opus → `opus`. Fable → `opus` only if the user chose that in preflight. Without one, use `sonnet`. **Never pass `fable`.**
- **`effort`** by the same tier: Haiku → `low`, Sonnet → `medium`, Opus → `high`.
- **Prompt:** "Ticket #<n>: implement GitHub issue #<n> in <repo> --autonomous, branching from the latest `origin/<base>`. The project's workflow is in its CLAUDE.md and docs/development.md. Read only the plan sections the ticket cites. Skip any test cases or test instructions; don't write or run tests." Add any user decisions from this run that affect the ticket.

**Questions from implementers.** Implementers decide technical questions themselves and return only business decisions, real blockers or destructive actions. When one returns a question anyway:
- **Technical, or settled by the ticket, plan or workflow:** answer it yourself, with your best judgment where nothing settles it. Don't pass it to the user.
- **Business or product decision, or a blocker only the user can remove:** ask the user.

Then send the answer per "Resume or dispatch fresh" below (an agent that stopped with a question hasn't finished), and record the decision in the run log and on the ticket.

**Resume or dispatch fresh.**
- **Finished agents are never resumed.** Once an implementer or fixer has returned its final report and you've moved on, every later round on that ticket goes to a **fresh agent** with a compact brief (below), never a `SendMessage`.
- **Interrupted agents** (stopped by an error, a limit, or with a question before finishing): resume with `SendMessage` if its context is under about **200k tokens** **or** less than **5 minutes** have passed since its last turn. Dispatch a fresh agent with a recovery brief only when both fail.
- **A scope or design change** always gets a fresh agent.

A fresh agent has the same type and model and works on the same worktree and branch (no isolation). Its prompt starts with `Ticket #<n>:`, then the worktree path, branch and base, and:
- **Compact brief** (fix round): a summary of the diff so far (`git diff --stat origin/<base>...` plus a few lines on the approach), and the problems to fix (build or lint errors, an unmet criterion, a CI failure), or the decision it needs.
- **Recovery brief** (interrupted agent): why it stopped (the error or question, and the answer if there is one), what's done and what's left. Check the worktree yourself (`git status`, `git diff --stat`) rather than trusting the interrupted agent's last words.

The fresh agent becomes the ticket's owner; update its agent ID in the run log.

## 4. Check the implementer's result

Keep this step cheap; don't run anything here, the final gate (§6) runs the build.
1. **Read its report.** Questions go through §3.
2. **Basic check:** the report marks every acceptance criterion met (or 🖐 trivial manual), says build and lint are green, lists no open deviation, and `git diff --stat origin/<base>...` touches the files the ticket is about, with no stray files. Skim "Decisions made"; challenge one only if it contradicts the plan or the ticket.
3. **If something's missing or failing,** start a fix round (§5).

## 5. Fix rounds

A fix round handles a failed basic check, a failed final gate or a red CI check.
- **Pick who fixes**, the cheapest agent that can do it well:
  - **A fresh fixer** (`subagent_type: "ticket-fixer"`, no isolation) when **every** fix is mechanical and small (a lint error, a missing import, a type error, a rename): `model: "haiku"`, `effort: "low"`; `sonnet` with `effort: "medium"` if a fix needs a little reasoning. Its prompt starts with `Ticket #<n>:`, then the worktree path, the base, and each fix with file, location and the exact change or error.
  - **A fresh implementer** (`subagent_type: "ticket-implementer"`, same model, no isolation, the compact brief from §3) for anything that needs understanding of the change: missing behaviour, an unmet criterion, a real build break.
- **Failing tests in CI** count as a fix round only when the product code is wrong: the fix goes into the product code, never into the tests. If a test itself looks outdated or wrong, stop and ask the user.
- **Limit:** at most **2 fix rounds** per ticket. If problems remain after that, stop the ticket and ask the user, with what's still open.

## 6. Ship it

1. Commit only the ticket's changes, with the user's conventions (e.g. `feat(#<n>): <summary>`).
2. `git fetch origin <base>` and rebase the ticket branch onto `origin/<base>` (it's still unpushed). On conflicts, resolve them as in §7.
3. **Final gate:** on the rebased branch, run the workflow's build and lint, with output to a log file, and check that `git status --porcelain` is empty. Then check every condition in "When a ticket is done". On failure: a fix round (§5).
4. Push the branch and open the PR against the base branch (`gh pr create --base <base>`): title `#<n> <Title>`, the user's PR template, `Closes #<n>`. Under "Testing": build and lint results, and the acceptance criteria as the implementer checked them, in a few lines.
5. If the repo has CI, wait for the checks (`gh pr checks --watch`). If one fails, start a fix round (§5) or stop and ask.
   - **Ticket base isn't the run's base** (e.g. a hotfix into `main`): stop here. Show the user the green PR and the steps the workflow prescribes after merging (e.g. tag, release, merge `main` back into the run's base), and ask for approval. After approval, merge with the workflow's method for that branch and do the approved steps. Tags and releases need their own explicit approval in that same request.
6. Merge with the workflow's merge method and branch deletion (default `gh pr merge --squash --delete-branch`). If GitHub reports a conflict, resolve it as in §7 and retry. Then fast-forward the local base branch and remove the worktree. Don't message the ticket's subagents after this.
   - `Closes #<n>` only closes the issue when the base is the repo's default branch. If the issue is still open after the merge, close it yourself: `gh issue close <n> -R <repo> -c "Done in PR #<m>"`.
7. Log one line: `✓ #<n> <title> → PR #<m> merged`. Then pick the next ticket (§2).

## 7. Merge conflicts

Try to resolve them yourself before involving anyone.
1. **Update the branch:**
   - **Not pushed yet:** rebase onto `origin/<base>`.
   - **Already pushed** (the PR exists): merge `origin/<base>` into the ticket branch, commit the merge, and push normally. Never rebase a pushed branch, since that needs a force-push.
2. **Understand both sides:** this ticket's change and its intent, and the change on the base branch (`git log -p origin/<base>` and the merged PR and ticket behind it).
3. **Resolve** so that **both** intents survive: combine the changes rather than taking one side, and regenerate generated files (lockfiles, migration snapshots, generated clients) with the project's tools instead of hand-merging them. If combining them needs real code changes beyond the conflict hunks, give that to a fresh implementer as a fix round, with both intents.
4. **Re-run the final gate** (§6, step 3) and mention the resolution in the PR.

**Stop and ask the user** when keeping both intents is impossible and one behaviour has to win, or the build still fails after a resolution and the cause isn't clear.

## 8. Checkpoints and reporting

- **End of every wave, in every checkpoint mode: hand off and end the session.** A coordinator's context grows with every ticket, and each turn re-sends all of it, so a fresh session per wave is much cheaper. After the last ticket of a wave merges:
  1. write the wave handoff into the run log (see "Run log");
  2. post the wave summary below;
  3. end with this message, filled in, and stop:

     > **Wave <N> is finished.** To keep token use low, clear this session with `/clear`, then run `/coordinator <the same arguments>` to start wave <N+1> (<k> tickets). The new session continues from the run log. <Anything to decide first, if there is.> If you have feedback first (a revert, follow-up tickets, plan changes), tell me before clearing and I'll record it for the next session.

  If the user replies with feedback or decisions, write them into the run log as open items (the next session applies them first), confirm in one line, and repeat the `/clear` instruction. Don't start the next wave in this session.
- **The wave summary** includes:
  - the merged PRs with links and what each changed, one line each;
  - fix rounds, conflicts resolved, deviations and follow-up issues;
  - what the next wave contains;
  - **milestones ready for release:** when the last open ticket of a milestone merges, say so, and list the release steps from the project workflow. Don't run them; they need the user's approval.
- **`checkpoint=wave`** (default): pauses only at the wave handoff, hard gates and concerns. **`checkpoint=ticket`:** also pause after every merge. **`checkpoint=none`:** no extra pauses inside a wave; the wave handoff still ends the session.
- **Follow-ups:** problems outside a ticket's scope become new issues (type `task`, the right `area` label, linked to the same story) only if the user agreed, or if they're clearly bugs in code merged during this run. List them in the summary.

## 9. Stop when

- the scope is done: append `run_finished` (in the same command that marks the run log finished), mark the run log finished and give a final summary with every PR, the open follow-ups and the remaining blocked tickets;
- a wave is finished: hand off as in §8;
- the user interrupts or asks to stop;
- the same ticket has failed twice, or used up its fix rounds;
- nothing ready remains because everything left is blocked by gates or concerns. Report what's waiting on the user.

GitHub is the source of truth (closed issues and merged PRs), so a later run with the same scope picks up where this one stopped.
