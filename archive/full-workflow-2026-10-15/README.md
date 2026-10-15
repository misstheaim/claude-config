# Archived: full coordinator workflow (2026-10-15)

The full versions of the coordinator workflow, archived when it was replaced by lighter versions to save tokens:
- `skills/coordinator`: parallel tickets, a reviewer subagent per ticket, test case verification, fix-round triage.
- `skills/analyze-coordinator`: the run analyzer for that coordinator.
- `skills/decompose-feature`: decomposition with test cases (`references/test-cases.md`, Phase 4.5).
- `skills/implement-ticket`: implementation with test cases as automated tests.
- `agents/`: `ticket-implementer`, `ticket-reviewer`, `ticket-fixer`, `test-designer`.

Nothing here is loaded: Claude Code only reads skills from `~/.claude/skills/` and agents from `~/.claude/agents/`.

To restore, copy the folders back over the light versions:

    cp -r archive/full-workflow-2026-10-15/skills/* skills/
    cp archive/full-workflow-2026-10-15/agents/* agents/

The archive is tracked in the `~/.claude` git repo (see `.gitignore`), so it travels with the rest of the config once committed.
