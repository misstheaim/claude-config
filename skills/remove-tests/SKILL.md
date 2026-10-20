---
name: remove-tests
description: Convert a project started with the full coordinator workflow to the light one (no automated tests) - remove automated tests, test tooling and test steps in CI from the code, remove test instructions from the project docs, and close or clean up the testing tickets on GitHub, all on one branch and PR into the base branch. Run manually before the first light /coordinator run on such a project.
disable-model-invocation: true
argument-hint: "[repo path] [--base <branch>]"
---

# Remove automated tests from a project

Arguments: `$ARGUMENTS` (all optional; by default: the repo in the current folder, and the base branch from its `docs/development.md` or `CLAUDE.md`).

The project was planned and partly built with the full coordinator workflow: test case tables in tickets, testing tickets, automated tests, test tooling, and CI that runs tests. The light workflow (`/coordinator`, `implement-ticket`) doesn't write or run tests. This skill removes all of that, so a light run hits no failing tests, testing tickets or test instructions.

**Keep build and lint working.** They're the light coordinator's only merge checks, so the project must build and pass lint at the end, and CI that runs build or lint stays unless the user decides otherwise.

The phases run in order. Phase 1 is read-only; nothing changes on GitHub before the user approves in Phase 2.

## Phase 1: Inventory (read-only)

1. **Repo and base:** `gh repo view --json nameWithOwner,defaultBranchRef`. The base is `--base`, otherwise the one the project's `docs/development.md` or `CLAUDE.md` names (usually `develop`), otherwise the default branch. `git fetch origin <base>` and inspect `origin/<base>`, not the local checkout.
2. **No ticket in flight:** stop if open ticket PRs (`gh pr list -R <repo> --state open`) or ticket worktrees (`git worktree list`) exist. Removing tests under a ticket that's being worked on breaks it. Tell the user what's open and let them finish or drop it first. A run log left unfinished at a wave handoff is fine: the light coordinator continues it.
3. **Tests in the code:** find everything that exists only for automated tests:
   - test files and folders by the stack's conventions (e.g. `tests/`, `test/`, `__tests__/`, `e2e/`, `cypress/`, `*.test.*`, `*.spec.*`, `test_*.py`, `*_test.go`, `src/test/`), fixtures, mocks, snapshots and test helpers;
   - test tooling config (e.g. `jest`/`vitest`/`playwright`/`cypress` configs, `conftest.py`, `pytest.ini`, the `[tool.pytest]` section, coverage config, a `tsconfig` used only by tests);
   - test dependencies and scripts in the manifests (`package.json` `test*` scripts and devDependencies, `requirements-dev.txt`, `pyproject.toml` extras, Gradle/Maven test dependencies, and so on);
   - references to removed paths elsewhere: `tsconfig` includes, lint configs, `.gitignore`, Dockerfiles, Makefiles.

   **Don't remove something just because its name says test.** Check with a grep that product code doesn't import it (a shared fixture, a `testUtils` used by the app, a `test` route in the app). Anything in doubt goes on the list as "unsure" with the reason.
4. **CI:** for each file in `.github/workflows/` (and any other CI config), list its jobs and steps and mark each as test (unit/integration/e2e runs, coverage upload, test reports), build/lint, or other (deploy, release). Note workflows that do nothing but tests.
5. **Docs:** test instructions in the README, `docs/development.md` (the test command row, "full test suite" rules, the test case rule in "Tickets, PRs and tests", the hotfix "add a test" step, the CI section), the project `CLAUDE.md` (test framework, test naming, the "test cases must pass" rule), and the plan document (testing strategy, test case tables, test design summary). The light versions of these files are in `~/.claude/skills/decompose-feature/references/` (`development-template.md`, `project-claude-template.md`, `plan-template.md`); match their wording.
6. **Tickets:** with `gh issue list -R <repo> --state open --limit 500 --json number,title,labels,body`, sort the open issues into:
   - **testing tickets:** their whole outcome is tests or test infrastructure (label `area:testing`, or a title and body only about tests);
   - **mixed tickets:** real work plus a "Test cases" section or instructions to write tests;
   - **parents left empty:** epics and stories whose only open children are testing tickets.

   For each testing ticket, also note which open tickets it blocks (`gh api repos/<repo>/issues/<n>/dependencies/blocking`), so the user sees what gets unblocked.

## Phase 2: Plan and approval

Show the user a short plan: files and folders to delete (grouped, with counts), dependencies and scripts to remove, the "unsure" items, each CI workflow with what happens to it, doc changes, and the tickets in each group. Then ask the open decisions together with `AskUserQuestion`, recommended option first, each with one line of context and the consequence:

- **CI:**
  - **Remove the test jobs and steps only (Recommended):** CI keeps running build and lint, which the light coordinator waits for before merging. Workflows that only ran tests are deleted.
  - **Delete CI entirely:** nothing checks a merge except the coordinator's local build and lint, and the coordinator stops waiting for CI.
- **Testing tickets:**
  - **Close as not planned (Recommended):** `gh issue close <n> --reason "not planned"` with a comment saying the project dropped automated tests. Reversible, and the history stays.
  - **Delete:** `gh issue delete`; needs admin rights and can't be undone.
- **Mixed tickets:** remove the "Test cases" sections and test instructions from their bodies (Recommended; implementers then don't read them), or leave the bodies as they are (implementers skip them anyway).
- **Unsure items:** each one kept or removed (only if there are any).

Then ask for approval of the exact remote changes, by name: the branch to push, the PR into `<base>` and its merge (squash, or the project's merge method), and the issue closes, deletes and body edits with their numbers. Approval covers that list only.

## Phase 3: Make the changes on a branch

1. Create the branch from the latest base, in a worktree so the user's checkout is untouched: `git fetch origin <base>`, then `git worktree add <repo>/../<repo-name>-remove-tests -b chore/remove-automated-tests origin/<base>`. Work only there.
2. Delete the test files, folders and tooling config. Remove the test dependencies and scripts, then update the lockfile with the project's package manager (e.g. `npm install`, `uv lock`), never by hand.
3. Fix every reference to what was removed (`tsconfig`, lint config, `.gitignore`, Dockerfiles, Makefiles).
4. Edit the CI workflows as decided.
5. Update the docs to match the light templates: the README, `docs/development.md`, `CLAUDE.md`, and the plan (remove the testing strategy, the test case tables and the test design summary; keep everything else, including issue numbers).
6. **Check:** install, then build and lint. Fix whatever the removal broke without changing product behaviour. If a fix would change product code beyond removing a reference, stop and ask.
7. Commit in the user's conventions, e.g. `chore: remove automated tests and test tooling`, with a body listing what was removed.

## Phase 4: Remote changes (as approved)

1. Push the branch and open a PR into `<base>` with the user's PR template: what was removed and why, the CI change, and how it was checked (build and lint results). Title e.g. `Remove automated tests`.
2. Wait for CI on the PR if it still exists, and merge with the approved method. If CI fails, fix it on the branch first; don't merge red.
3. Testing tickets: close or delete as decided. Close parents left empty the same way.
4. Mixed tickets: edit their bodies as decided (`gh issue edit <n> --body-file <file>`, with the file written from the current body minus the test parts).
5. Remove the worktree (`git worktree remove`) and delete the local branch once merged.

Never force-push, change repo settings, or touch `main` or `release/*` branches. Tests that are already on `main` leave it with the next release.

## Report

End with: the PR link and merge status, counts of files, dependencies and CI jobs removed, the build and lint results, the tickets closed, deleted or edited (numbers), tickets that are now unblocked, and anything left for the user (unsure items kept, manual steps). Then say the project is ready for `/coordinator`.
