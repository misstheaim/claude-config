---
name: analyze-coordinator
description: Analyse a finished /coordinator run (light workflow - one ticket at a time, no reviewer, no automated tests) and produce a short HTML effectiveness report - how well the subagents worked, how often the run was interrupted, how efficiently the coordinator processed results, and what it cost in tokens - ending with the weaknesses, bottlenecks and concrete improvements to the coordinator skills. Use when the user asks to analyse, evaluate, review or report on a coordinator run or its cost. Reads local transcripts and the coordinator's event log; changes nothing.
disable-model-invocation: true
argument-hint: "[repo path] [--run run-YYYY-MM-DD-HHMM] [--session SESSION_ID]"
---

# Analyse a coordinator run

Arguments: `$ARGUMENTS` (all optional; by default: the repo in the current folder and its newest run).

You evaluate how a `/coordinator` run went and where the setup should improve. The coordinator is the light version: tickets run one at a time, there's no reviewer subagent and no automated tests, and a PR merges once build and lint pass, git is clean, the implementer reports the work done and there are no conflicts. Judge it by that design: a missing review or missing tests is expected, not a weakness. Propose bringing back reviews or tests only if the numbers show real damage (e.g. reverts, repeated build breaks after merge), and then say it's a trade-off against token cost. Older runs of the full workflow (archived in `~/.claude/archive/`) still have reviewers, triage and findings; analyse those as before. **You change nothing**: no edits to skills, repos or GitHub. Improvements are proposals for the user.

## Where the data is

- **Event log** (judgments): `<git-common-dir>/coordinator/run-<…>.events.jsonl`, written by the coordinator (format: `~/.claude/skills/coordinator/references/events.md`). Reviews and triage (full-workflow runs only), escalations, waits, final gates, conflicts, stopped tickets, wave handoffs. Everything mechanical (which subagent worked on which ticket and in what role, fix rounds, PRs, CI) comes from the transcripts instead; merges come from the `merged` events that `ship.sh` writes, or from the transcripts (`gh pr merge`, or a `ship.sh` call ending in `RESULT: 0 merged`).
- **Run log** (context): `run-<…>.md` next to it, the coordinator's own notes and decisions.
- **Transcripts** (facts): `~/.claude/projects/<sanitized repo path>/<session>.jsonl` for each coordinator session (one per wave), and `<session>/subagents/agent-<id>.jsonl` + `.meta.json` for each subagent: token usage per API call, models, timing, tool calls and errors, permission prompts, interrupts, compactions.

**Don't read transcripts into your context.** They're megabytes. The script below extracts everything; open a transcript only for a targeted look (e.g. `grep` one agent's failed tool calls) when a number needs explaining.

## 1. Collect

```bash
python ~/.claude/skills/analyze-coordinator/scripts/collect.py --repo <repo> [--run <name>] [--session <id> ...]
```

It writes `<run>.metrics.json` next to the run log and prints a summary. Costs use API list prices (in the script's `PRICES`); on a subscription they're an API-equivalent estimate, so say so. If it reports missing data (no event log, sessions not found, unpriced models), carry on with what's there and list the gaps in the report.

Read the metrics JSON. Also look for earlier `*.metrics.json` in the same folder: if there are any, compare (cost per merged ticket, interruptions per ticket, fix rounds, coordinator share) and call out trends.

## 2. Analyse

Work through these questions with numbers from the metrics. The thresholds are starting points for judging, not facts; say when a number is borderline.

**Outcomes**
- Tickets merged versus stopped, and why the stopped ones stopped. Cost and cycle time per merged ticket.

**Subagents**
- Per role (implementer, fixer, and reviewer in full-workflow runs): cost, API calls, duration, tool errors, outcomes (`partial` = hit its turn limit, `question` = escalated).
- Implementers: how often did a ticket they reported done fail the final gate or CI, and how many fix rounds did that cause? Which models and effort levels did well or badly for their ticket tier? Did any write or run tests despite the rules (wasted tokens)?
- Reviewers (full-workflow runs only): findings per review, and how many the coordinator rejected (a high rejection rate means a noisy reviewer). Review cost relative to implementation (aim ≤ 60%).
- Fixers: were they used for mechanical rounds, and did their fixes hold?

**Interruptions** (aim: no technical escalations, about one user wait per wave besides the handoff)
- Escalations by kind and by who resolved them. A `technical` escalation means an implementer asked something it should have decided.
- Waits on the user, permission prompts (these point to a missing allowlist) and user interrupts.

**How the coordinator processed results**
- The coordinator's share of total cost (aim < 25%).
- Context growth per session and any compactions. A steep slope means it's reading too much itself.
- Final gate failures and their causes, CI failures, review paths and re-reviews (full-workflow runs), conflicts and how they were resolved, idle time between tickets.

**Token cost**
- Cost by role and model, cache hit ratio (aim > 85%), cache-write share (high = cold starts or resumes after the cache expired).
- Logging overhead: event appends that used a tool call of their own (should be 0).
- Model and effort fit: Opus or high effort on work that went smoothly at a lower tier elsewhere, or a cheap tier that caused rework.

## 3. Conclude

Decide the verdict (`good`, `mixed` or `poor`) and pick out:
- **Strengths:** what to keep (2–4 items).
- **Weaknesses:** each with its evidence (numbers) and its impact.
- **Bottlenecks:** where time, tokens or user attention concentrated.
- **Improvements:** at most 6, ranked. Each one names the exact change and where it goes (e.g. `coordinator/SKILL.md §5`, `agents/ticket-implementer.md`, `implement-ticket` "Decide or escalate", `decompose-feature/references/ticket-template.md`, `settings.json` allowlist), plus the expected effect. Prefer changes that remove a whole class of cost or interruption over tuning one ticket.

Don't invent problems to fill the lists: a clean run gets a short report.

## 4. Report

1. Write the findings as JSON (shape documented at the top of `scripts/render.py`) to a file next to the metrics.
2. Render: `python ~/.claude/skills/analyze-coordinator/scripts/render.py <metrics.json> <findings.json> <run>.report.html`, saved next to the run log. It writes two files:
   - `<run>.report.html`, the visual report for the user;
   - `<run>.report.md`, the same findings plus all the data behind them as plain Markdown. This is the file to hand to a later session that improves the coordinator.
3. In the reply: the verdict, the 3 most important findings with their numbers, the top improvements, and both paths (say the `.md` is the one to pass to an improvement session). Offer in one line to publish the page as a private artifact for viewing in the browser. Don't apply any improvement unless the user asks.
