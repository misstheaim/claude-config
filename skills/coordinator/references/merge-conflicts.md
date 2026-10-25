# Merge conflicts

Part of the coordinator skill (`../SKILL.md`): read this file when you reach this step. `<skill-dir>` is the coordinator skill's folder.

Try to resolve them yourself before involving anyone.
1. **Update the branch:**
   - **Not pushed yet:** rebase onto `origin/<base>`.
   - **Already pushed** (the PR exists): merge `origin/<base>` into the ticket branch, commit the merge, and push normally. Never rebase a pushed branch, since that needs a force-push.
2. **Understand both sides:** this ticket's change and its intent, and the change on the base branch (`git log -p origin/<base>` and the merged PR and ticket behind it).
3. **Resolve** so that **both** intents survive: combine the changes rather than taking one side, and regenerate generated files (lockfiles, migration snapshots, generated clients) with the project's tools instead of hand-merging them. If combining them needs real code changes beyond the conflict hunks, give that to a fresh implementer as a fix round, with both intents.
4. **Re-run `ship.sh`** (§6), which runs the final gate again, and mention the resolution in the PR.

**Stop and ask the user** when keeping both intents is impossible and one behaviour has to win, or the build still fails after a resolution and the cause isn't clear.
