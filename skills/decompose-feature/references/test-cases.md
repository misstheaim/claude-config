# Test cases

Test cases turn a task's acceptance criteria into concrete checks, written **before** implementation by someone other than the implementer. The implementer turns each one into an automated test; the coordinator closes a ticket only when every one of them passes.

Used by `decompose-feature` (Phase 4.5 and the light path). Tickets without test cases get a goal check from the coordinator instead.

## Format

Each task gets a "Test cases" table, in the plan and in the ticket body:

```markdown
| ID | Kind | Level | Given / When / Then | Covers |
|---|---|---|---|---|
| T3-TC01 | happy | integration | Given a valid reset token, when POST /reset with a new password, then 204 and the user can log in with the new password | AC1 |
| T3-TC02 | edge | unit | Given a token that expired 1 second ago, when it is validated, then it is rejected with `TOKEN_EXPIRED` | AC2 |
| T3-TC03 | error | integration | Given a token that was already used, when POST /reset, then 409 and the password is unchanged | AC2 |
```

- **ID:** `T<task>-TC<nn>` for tasks, `S<story>-TC<nn>` for story-level cases. IDs never change once tickets exist; a removed case keeps its ID, struck through.
- **Kind:** `happy` (the main expected use), `edge` (boundaries and unusual but valid input), `error` (invalid input, failures, forbidden actions).
- **Level:** `unit`, `integration` or `e2e`, following the plan's testing strategy.
- **Given / When / Then:** observable behaviour with **specific expected values** (status codes, error codes, exact outputs), never "works correctly". Inputs that behave the same way go into one case as an `Examples:` list (e.g. `Examples: "", "   ", null → VALIDATION_ERROR`), which becomes one parametrized test.
- **Covers:** the acceptance criteria it checks (`AC1`, `AC2`, ... in the order they appear in the task).

## Rules

- **Fewer, sharper cases.** Aim for **2–5 cases per task**. One case per distinct behaviour, never one per input value: group same-behaving inputs with `Examples:`. One case may cover several acceptance criteria.
- **Upper limit: 6 cases per task.** Needing more means the task is probably too big. Write the 6 most important, and report the task under "problems found" with a suggested split.
- **Coverage:** every acceptance criterion is covered by at least one case. Every task with test cases has at least one `happy` case and at least one `edge` or `error` case.
- **Edge and error cases need a reason:** add one only when a plausible bug would break it, or the plan or an acceptance criterion names it. Don't add cases just because a category exists. Categories worth checking for such risks: empty or missing input, boundaries, invalid formats, repeated calls, permissions and other users' data, concurrency, failure of a dependency, large inputs.
- **Test behaviour, not implementation:** no private function names, no internal structure, nothing that forces one design. A case must survive a reasonable refactoring.
- **Deterministic and independent:** no reliance on wall-clock time, test order or another ticket's internals. Say how time, randomness or external services are controlled when it matters.
- **Cross-ticket consistency:** when several tasks touch the same contract (API, schema, event, component props), their cases must expect the same behaviour. A case must not assert something a later task in the plan changes on purpose; if that's the intent, the later task updates the earlier case explicitly.
- **Story-level cases:** an integration or e2e case for a story's acceptance criteria is assigned to the story's last task (the one that completes the story), and listed in that task's table with its `S<n>-TC<nn>` ID.
- **Where test cases don't fit** (docs, design, assets, spikes, pure configuration): write `Test cases: none (<reason>)`, and make sure each acceptance criterion has a `Verify:` line saying how it's checked (a command, a file that must exist, a manual step).

## Test designer subagent

Launch one subagent with the Agent tool: `subagent_type: "test-designer"` (defined in `~/.claude/agents/test-designer.md`: read-only, Opus, follows this file). If that agent type isn't available, use `general-purpose` with `model: "opus"`. It starts with a clean context, so its prompt must contain:
- the absolute path of the plan document and of the project;
- the absolute path of this file, with the instruction to follow its format and rules;
- its role: an independent test designer who **does not edit any files or tickets**, and returns its output as text;
- its task: write test cases for every task where they fit, read the codebase where needed to make expected values concrete, and check consistency across tasks;
- what to return:
  1. a "Test cases" table per task (or `none (<reason>)`);
  2. **problems found**: acceptance criteria too vague to test (with a proposed rewrite), contradictions between tasks or with the codebase, behaviour the plan leaves undefined (with the question to ask the user).

The calling agent weighs the output, applies what it agrees with, and brings the problems to the user. The designer's tables are a proposal, not a decision.
