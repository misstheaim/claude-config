---
name: init-spec
description: Create the behaviour spec (docs/spec/: an index plus one file per area) for a project that already has code but no spec, by scanning the codebase with one spec-writer subagent per area, and add the spec rules to the project's CLAUDE.md. Use when the user asks to create, initialise or backfill a project's spec, including after the coordinator suggested it. Always its own session, never inside a coordinator run. Do NOT use for updating an existing spec after a change (the coordinator's spec update and the project's CLAUDE.md rules do that).
disable-model-invocation: true
argument-hint: "[area <name>,<name>] [repo=OWNER/REPO] [base=BRANCH]"
---

# Create a project's behaviour spec

Arguments: `$ARGUMENTS`

The spec says how the product behaves **now**; the format is `references/spec-format.md` (read it first). New projects get an empty spec from `decompose-feature`; this skill backfills one for a project that was built without it. It can cost a lot on a big codebase, so it splits the work: one `spec-writer` subagent per area, each reading only its part of the code. You only plan, dispatch and write the small index.

- **area:** only write these areas (e.g. to finish a partial spec or redo one area). Default: every area without a file.
- **repo / base:** as in `/coordinator`: the current folder's repo, and the base branch from the project's workflow (`CLAUDE.md`, `docs/development.md`) or what recent PRs target. If it's unclear, ask.

**Run it in its own session**, not inside a `/coordinator` run: the scan and the writers' reports would otherwise land in the coordinator's large context. The orchestration here is light, so this session can run on Sonnet (`/model sonnet`).

## 1. Preflight

- `git fetch origin <base>`. The spec describes `origin/<base>`, never local or unmerged work.
- **Existing spec:** if `docs/spec/README.md` is on `origin/<base>`, write only the areas it lacks (or the `area` argument), and keep its IDs.
- **Agent type:** check that `spec-writer` exists (`~/.claude/agents/`); if it doesn't, use `general-purpose` with that file's content in each prompt.

## 2. Choose the areas

Take them, cheapest source first:
1. the plan's areas (the main plan's area list, `docs/plans/<area>.md` files, or the area sections of an older single plan);
2. the issues' `area:` labels (`gh label list -R <repo>`), keeping the product areas (not `docs`, `cloud`, `design`);
3. only if neither gives usable areas: one `Explore` subagent (`model: "sonnet"`), asked for the product's areas of user-visible behaviour, each with its folders and entry points (commands, views, CLI, endpoints, settings), in at most 30 lines.

**Check the areas against the code.** The plan names areas; only the code says what exists. List the source folders (`git ls-files` per top-level folder, then one level down where a folder is big) and map each to an area:
- code that maps to no area (a hotfix, a helper built outside the plan) joins the area it serves, or becomes its own;
- an area with no code behind it (planned, never built) gets no file: nothing in it is implemented.

From that mapping, note each area's folders and entry points (by file names, without reading code). Size them: an area should be one writer's job. Split a big one by sub-area; merge tiny ones. Give each an ID prefix (`REVIEW`, `CLI`).

**Show the user** the areas with their folders and a cost estimate (about $0.3-1.5 per area on Sonnet), and wait for confirmation.

## 3. Worktree

Create a docs branch in its own worktree from the latest base, and its scratch folder:

```bash
git worktree add -b docs/init-spec <repo>/.claude/worktrees/spec origin/<base>
```

then `mkdir -p <repo>/.claude/worktrees/spec/.scratch`. `.claude/worktrees/` and `.scratch/` must be in `<git-common-dir>/info/exclude`; add them if they aren't.

## 4. Write the areas

Dispatch one `spec-writer` per area (`model: "sonnet"`, `effort: "medium"`, no isolation), up to 3 at once. Each prompt starts with `Spec init <area>:` and gives the worktree path, the base and target commit (`origin/<base>`), the area's folders and entry points, and its ID prefix. **No plan text**: a writer that has read the intended behaviour tends to confirm it instead of observing the code. Writers in parallel each write only their own file. Don't read their files yourself; their reports are enough.

## 5. Index and CLAUDE.md

Write `docs/spec/README.md` yourself from the template in `references/spec-format.md`: the overview (from the README and the plan), the area table from the writers' reports, the glossary, "How to edit this spec", and `Synced to:` the target commit.

Add the **"Behaviour spec" section** from `references/spec-format.md` to the project's `CLAUDE.md` in the same branch, unless it's already there. Without it, sessions that change behaviour outside the skills won't update the spec.

## 6. Ship it

Commit (`docs: add behaviour spec`), push, open a PR into `<base>` with a short summary (areas, item counts, what couldn't be checked), merge with the workflow's method without waiting for CI (the light workflow uses CI only for release builds), and remove the worktree. The user's rules apply: show the commit, push, PR and merge as one batch and ask before running it.

## 7. Report

The areas with their item counts, the mismatches and things the writers couldn't check, and the PR link. Mention that from now on the coordinator updates the spec at each handoff, and sessions without skills follow the CLAUDE.md rule.
