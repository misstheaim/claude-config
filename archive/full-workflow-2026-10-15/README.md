# Archived: full coordinator workflow (2026-10-15)

The full versions of the coordinator workflow, archived when it was replaced by lighter versions to save tokens:
- `skills/coordinator`: parallel tickets, a reviewer subagent per ticket, test case verification, fix-round triage.
- `skills/analyze-coordinator`: the run analyzer for that coordinator.
- `skills/decompose-feature`: decomposition with test cases (`references/test-cases.md`, Phase 4.5).
- `skills/implement-ticket`: implementation with test cases as automated tests.
- `skills/init-spec`: creates the behaviour spec (`docs/spec/`) for a project that has code but no spec (one writer per area, then a verification pass); `references/spec-format.md` defines the spec for every skill.
- `agents/`: `ticket-implementer`, `ticket-reviewer`, `ticket-fixer`, `test-designer`, `spec-writer`.

`skills/coordinator/scripts/ship.sh` (added 2026-10-23): the same script as the light coordinator's, used by §6 with the full test suite as a gate. Keep the two copies identical when changing it.

Behaviour spec (added 2026-10-23, after archiving): the decomposer writes a main plan plus area plans with spec deltas on every task, the coordinator updates `docs/spec/` from the merged code after each wave (and offers `init-spec` when there's no spec), and implementers never edit the spec under the coordinator.

Flat per-session cost (added 2026-10-25, same as the light versions): the run log keeps only the current and previous session (older ones in `run-<id>.history.md`), standing decisions and facts live in a capped `decisions.md` shared by all runs, the analyzer works from a digest printed by `collect.py` instead of reading the metrics JSON, and finished waves collapse into a `Done:` line in the main plan's order of work (shipped with the wave spec update).

Shared with the light workflow, not archived: `skills/create-ticket` (added 2026-10-25) reads the ticket template and `github.md` from whichever `decompose-feature` is installed, and adds test cases only when that is the full version. `implement-ticket` in both versions updates the spec and the plan on the user's approval in interactive mode (step 8).

Nothing here is loaded: Claude Code only reads skills from `~/.claude/skills/` and agents from `~/.claude/agents/`.

To restore, copy the folders back over the light versions:

    cp -r archive/full-workflow-2026-10-15/skills/* skills/
    cp archive/full-workflow-2026-10-15/agents/* agents/

The archive is tracked in the `~/.claude` git repo (see `.gitignore`), so it travels with the rest of the config once committed.
