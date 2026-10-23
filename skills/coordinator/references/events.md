# Coordinator event log

The coordinator appends one JSON object per line to `run-<YYYY-MM-DD-HHMM>.events.jsonl`, next to the run log (`<git-common-dir>/coordinator/`). The `analyze-coordinator` skill joins these events with the session transcripts.

**Only judgment is logged.** Everything the transcripts already show is derived from them by the analyzer: dispatches (Agent calls: ticket from `#<n>` in the prompt, role from the agent type, model, effort, agent ID), resumes (SendMessage calls), fix rounds (fixer dispatches, later implementer dispatches and resumes per ticket, minus continuations after an `agent_return` or `escalation`), PRs created and merged (`gh pr create` / `gh pr merge`, or a `ship.sh` call's `RESULT: 0 merged` line), CI waits (`gh pr checks`), tokens, timing, tool errors, permission prompts. The events record what the transcripts can't: the coordinator's decisions and their reasons.

## Writing events without extra turns

A tool call of its own costs a full context re-read. So an event never gets its own tool call:
- **Chain it** onto a command you run anyway, e.g. `gh pr merge … && printf '%s\n' '<json>' >> "$EVENTS"`, or append it to the command that starts the next step.
- **Or send it in the same message** as the next tool call (e.g. together with the `SendMessage` of a fix round).
- **Several events at once** go in one append: `printf '%s\n' '<json1>' '<json2>' >> "$EVENTS"`.

Rules: append only, never edit or delete lines; each line valid JSON; every event has `ts` (ISO 8601 UTC) and `event`; leave out fields you don't know. `ticket` is the issue number as an integer.

**Values are exact.** Enum values are lowercase, exactly as listed below (`pass`, never `PASS` or `Pass`). Required fields are never `null` or `""`:
- `session_start.wave`: the wave this session starts or continues (an integer);
- `final_gate.cause`: one of the listed causes when `result` is `fail` (`null` only on `pass`);
- `smoke_check.reason`: when `result` is `skipped`.

A `final_gate` with `result: fail` is followed by another `final_gate` for the same ticket once it passes.

## Events

| `event` | When | Fields |
|---|---|---|
| `session_start` | Preflight, once per session | `wave`, `continuing` (bool) |
| `baseline` | After the baseline check | `result`: `pass` / `fail` / `skipped`, `known_failures` (int) |
| `wave_start` | With the wave's first dispatch | `wave`, `tickets` (list of ints) |
| `agent_return` | Only when a subagent did **not** return a finished report | `ticket`, `agent_id`, `outcome`: `question` / `partial` (hit maxTurns) / `error` |
| `escalation` | A question that needed a decision | `ticket`, `kind`: `business` / `blocker` / `destructive` / `technical`, `resolved_by`: `coordinator` / `user` |
| `user_wait` | You stop and wait for the user | `reason`: `escalation` / `gate` / `concern` / `fable` / `baseline` / `checkpoint`, `ticket` (if any) |
| `final_gate` | After the final gate, for every ticket that merges | `ticket`, `result`: `pass` / `fail`, `cause` (on fail: `build` / `lint` / `dirty` / `commit` / `conflict` / `ci`) |
| `merged` | Right after the ticket's PR merges (`ship.sh` writes it) | `ticket`, `pr` (int), `refs` (bool: a `--no-close` PR, the issue stays open) |
| `conflict` | Each merge conflict or post-rebase build failure | `ticket`, `kind`: `merge` / `build` (the build breaks only after rebasing onto newly merged work), `resolved_by`: `coordinator` / `user` |
| `ticket_stopped` | A ticket is handed to the user | `ticket`, `reason`: `fix-rounds` / `failed-twice` / `conflict` / `escalation` / `other` |
| `smoke_check` | After the wave smoke check (or its skip), chained onto the handoff command | `wave`, `result`: `pass` / `fail` / `skipped`, `failures` (int), `followups` (list of ints), `reason` (on skipped) |
| `spec` | After the spec update at a handoff or the run's end, or its skip | `wave`, `result`: `updated` / `no-change` / `missing` (no spec yet), `mismatches` (int, on updated), `choice` (on the first missing: `separate-session` / `declined`). While the spec is missing, every handoff logs `missing` |
| `wave_handoff` | At the wave handoff | `wave`, `merged` (list of ints), `open` (list of ints) |
| `run_finished` | When the scope is done | `merged` (int), `stopped` (int) |

**Required for every merged ticket:** a `final_gate` event. The analyzer reports a merged ticket without it as an incomplete log.

A typical ticket produces two events, `final_gate` and `merged`, which `scripts/ship.sh` appends itself when called with `--events`. A re-run that only finishes the cleanup of an already merged PR writes `merged` again (with the PR's merge time); the analyzer counts a ticket's merge once.
