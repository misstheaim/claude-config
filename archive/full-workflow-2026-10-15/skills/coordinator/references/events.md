# Coordinator event log

The coordinator appends one JSON object per line to `run-<YYYY-MM-DD-HHMM>.events.jsonl`, next to the run log (`<git-common-dir>/coordinator/`). The `analyze-coordinator` skill joins these events with the session transcripts.

**Only judgment is logged.** Everything the transcripts already show is derived from them by the analyzer: dispatches (Agent calls: ticket from `#<n>` in the prompt, role from the agent type, model, effort, agent ID), resumes (SendMessage calls), fix rounds (fixer dispatches, later implementer dispatches and resumes per ticket, minus continuations after an `agent_return` or `escalation`), PRs created and merged (`gh pr create` / `gh pr merge`), CI waits (`gh pr checks`), tokens, timing, tool errors, permission prompts. The events record what the transcripts can't: the coordinator's decisions and their reasons.

## Writing events without extra turns

A tool call of its own costs a full context re-read. So an event never gets its own tool call:
- **Chain it** onto a command you run anyway, e.g. `gh pr merge … && printf '%s\n' '<json>' >> "$EVENTS"`, or append it to the command that starts the next step.
- **Or send it in the same message** as the next tool call (e.g. together with the `SendMessage` of a fix round).
- **Several events at once** go in one append: `printf '%s\n' '<json1>' '<json2>' >> "$EVENTS"`.

Rules: append only, never edit or delete lines; each line valid JSON; every event has `ts` (ISO 8601 UTC) and `event`; leave out fields you don't know. `ticket` is the issue number as an integer.

## Events

| `event` | When | Fields |
|---|---|---|
| `session_start` | Preflight, once per session | `wave`, `continuing` (bool) |
| `baseline` | After the baseline check | `result`: `pass` / `fail` / `skipped`, `known_failures` (int) |
| `wave_start` | With the wave's first dispatch | `wave`, `tickets` (list of ints) |
| `agent_return` | Only when a subagent did **not** return a finished report | `ticket`, `agent_id`, `outcome`: `question` / `partial` (hit maxTurns) / `error` |
| `escalation` | A question that needed a decision | `ticket`, `kind`: `business` / `blocker` / `destructive` / `technical`, `resolved_by`: `coordinator` / `user` |
| `user_wait` | You stop and wait for the user | `reason`: `escalation` / `gate` / `concern` / `fable` / `baseline` / `checkpoint`, `ticket` (if any) |
| `review` | After the review (full) or your own check (light), or when a ticket gets no review at all (skipped) | `ticket`, `path`: `full` / `light` / `skipped`, `reason` (on skipped: one line, e.g. `spike report only`), `findings`: `{"critical":0,"high":0,"medium":0,"low":0,"nit":0}`, `verification_failures` (int), `tampering` (int) |
| `triage` | With the review event | `ticket`, `fix`, `reject`, `followup`, `ask` (ints) |
| `final_gate` | After the final gate, for every ticket that merges | `ticket`, `result`: `pass` / `fail`, `cause` (on fail: `tests` / `build` / `lint` / `dirty` / `commit` / `conflict` / `e2e`; `ship.sh` uses the gate's name) |
| `merged` | Right after the ticket's PR merges (`ship.sh` writes it) | `ticket`, `pr` (int), `refs` (bool: a `--no-close` PR, the issue stays open) |
| `conflict` | Each merge conflict or cross-ticket test failure | `ticket`, `kind`: `merge` / `tests` / `spec` (contradicting test cases, not the behaviour spec), `class` (e.g. `implementation-bug`, `brittle-test`), `resolved_by`: `coordinator` / `user` |
| `ticket_stopped` | A ticket is handed to the user | `ticket`, `reason`: `fix-rounds` / `failed-twice` / `spec-conflict` / `escalation` / `other` |
| `spec` | After the wave spec update, or its skip | `wave`, `result`: `updated` / `no-change` / `missing` (no spec yet), `mismatches` (int, on updated), `choice` (on the first missing: `separate-session` / `declined`). While the spec is missing, every handoff logs `missing` |
| `wave_handoff` | At the wave handoff | `wave`, `merged` (list of ints), `open` (list of ints) |
| `run_finished` | When the scope is done | `merged` (int), `stopped` (int) |

**Required for every merged ticket:** a `review` event (with `path: "skipped"` and a `reason` if nothing reviewed it) and a `final_gate` event. The analyzer reports a merged ticket without them as an incomplete log.

A typical ticket produces four events: `review` and `triage` (yours, in one append), then `final_gate` and `merged`, which `scripts/ship.sh` appends itself when called with `--events`.
