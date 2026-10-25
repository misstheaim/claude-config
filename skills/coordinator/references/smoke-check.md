# Wave smoke check

Part of the coordinator skill (`../SKILL.md`): read this file when you reach this step. `<skill-dir>` is the coordinator skill's folder.

Before the handoff, one subagent checks that what this wave merged actually works when the product runs. It's a **smoke check, not a test suite**: a short happy-path pass that the new pieces are there and do their main job. It doesn't cover edge cases, add tests to the repo or commit anything, so it stays within the light workflow.

- **When:** after the wave's last ticket merges or stops, once per wave. **Skip it** only when the merged tickets changed nothing that runs (docs, plan, specs or CI config only), or nothing merged. Log the skip with its reason.
- **What it checks:** for each ticket merged in this wave, the user-visible result of its acceptance criteria. New UI elements (views, panels, menus, commands, settings, status items, pages) are present and respond. New CLI commands, endpoints or hooks run and return what they should. The product starts without errors.
- **Only this wave:** no regression pass. Earlier waves' checks are never re-run, read or edited. If a ticket here changed older behaviour, that change is part of the ticket and gets checked as such. A regression in code this wave didn't touch can slip through; that's accepted, so the check's cost stays flat however many waves came before.
- **Where:** its own worktree, `<repo>/.claude/worktrees/smoke`, detached at `origin/<base>` after the wave's merges. Prepare it with one call: `bash <skill-dir>/scripts/smoke-worktree.sh --base <base> --wave <N>`. The script creates the worktree on first use and resets it on later waves (tracked files back to `origin/<base>`; `node_modules` and build output stay, so later waves start faster). It adds `.claude/worktrees/` to `<git-common-dir>/info/exclude` if needed, so the persistent worktree never makes the main checkout look dirty. It also records the main checkout's state and prints `SMOKE_WORKTREE`, `SMOKE_HARNESS`, `SMOKE_WAVE_DIR` and `SMOKE_AT` (the commit under test).
- **Harness**, in `<git-common-dir>/coordinator/` (not committed, shared by every worktree):
  - `smoke-harness/lib/`: the shared launcher (build and start the product with a temp `HOME`, its own `package.json` or similar) and a README on using it. The agent reuses it and may update it when the product's startup changes.
  - `smoke-harness/wave-<N>/`: this wave's check scripts and logs. The agent writes only here and in `lib/`.
  - `smoke-archive/wave-<N>/`: finished waves with a `RESULT` file, moved there by `--finish` (below). Kept for the user's reference only: never mention it in the prompt, and never re-run it. Prepare also archives leftovers: unfinished waves' folders and the files of the older single-folder harness (`smoke-archive/legacy/`).
- **Dispatch:** `subagent_type: "general-purpose"`, `model: "sonnet"`, `effort: "medium"`, **no isolation** (worktree isolation would refuse the harness folder, and auto-cleanup would throw the harness away). The worktree, the rules and the check afterwards replace the isolation. The prompt starts with `Smoke check wave <N>:` and gives:
  - the smoke worktree path and the commit under test, the `lib/` and wave folder paths, and the project's run commands from the workflow (e.g. the "Run locally" row of `docs/development.md`);
  - each merged ticket in one or two lines: what changed and what to check, taken from its PR and acceptance criteria;
  - the rules:
    - **first, `cd` into the smoke worktree** and run every command from there, using absolute paths;
    - check only the tickets listed here, not features from earlier waves;
    - work only in the smoke worktree, `lib/`, the wave folder and temp dirs. **The main checkout (`<main checkout path>`) and the ticket worktrees are off limits:** never read from, write to or run git in them;
    - never commit, push, open PRs or change branches; in the smoke worktree, never edit tracked files (build output and `node_modules` are fine);
    - never touch the user's real config or home: use temp dirs, e.g. a temp `HOME`, `CLAUDE_CONFIG_DIR` or the project's own override such as `COMPOSER_HOME`;
    - don't fix product code; report what's broken instead;
    - start the product through `lib/` (create it if it's empty, update it if startup changed, keep its README current); write this wave's checks in the wave folder; keep long output in log files there;
  - the report, at most about 40 lines: one line per check, marked `PASS`, `FAIL` or `NOT CHECKABLE` (with why). For each FAIL, steps to reproduce and whether it looks like a product bug or a harness problem. Then the `lib/` changes, if any.
- **Check the boundary and archive afterwards:** `bash <skill-dir>/scripts/smoke-worktree.sh --finish --wave <N> --result pass|fail` (chain it onto your next command). It compares the main checkout with the state recorded before the dispatch, then moves the wave folder to `smoke-archive/` with its result. If it prints `CHANGED`, the agent broke its rules. Restore the main checkout (`git checkout -- <path>` for tracked files; remove only files that the diff shows are new), note it in the handoff, and treat that smoke result as unreliable.
- **Results:**
  - **All pass:** note it in the handoff.
  - **A product bug in code merged during this run:** create a follow-up issue (see "Follow-ups" in `../SKILL.md` §8) with the reproduction steps, and list it as an open item for the next session to run first. Don't fix it in this session.
  - **The product doesn't start at all:** create the follow-up as above, and also call it out first in the handoff message.
  - **Unconfirmed or harness-only problems:** list them under "open items" in the handoff, without a ticket. The user decides.
- **Log it:** the result, the `lib/` changes, the archive path and what couldn't be checked go into the wave handoff in the run log, plus one `smoke_check` event chained onto the handoff's command.
