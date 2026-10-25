---
name: analyze-coordinator
description: Analyse a finished /coordinator run and produce a short HTML effectiveness report - how well the subagents worked, how often the run was interrupted, how efficiently the coordinator processed results, and what it cost in tokens - ending with the weaknesses, bottlenecks and concrete improvements to the coordinator skills. Use when the user asks to analyse, evaluate, review or report on a coordinator run or its cost. Reads local transcripts and the coordinator's event log; changes nothing.
disable-model-invocation: true
argument-hint: "[repo path] [--run run-YYYY-MM-DD-HHMM] [--session SESSION_ID]"
---

# Analyse a coordinator run

Arguments: `$ARGUMENTS` (all optional; by default: the repo in the current folder and its newest run).

You evaluate how a `/coordinator` run went and where the setup should improve. **You change nothing**: no edits to skills, repos or GitHub. Improvements are proposals for the user.

## Where the data is

- **Event log** (judgments): `<git-common-dir>/coordinator/run-<…>.events.jsonl`, written by the coordinator (format: `~/.claude/skills/coordinator/references/events.md`). Reviews and triage, escalations, waits, final gates, conflicts, stopped tickets, wave handoffs. Everything mechanical (which subagent worked on which ticket and in what role, fix rounds, PRs, CI) comes from the transcripts instead; merges come from the `merged` events that `ship.sh` writes, or from the transcripts (`gh pr merge`, or a `ship.sh` call ending in `RESULT: 0 merged`).
- **Run log** (context): `run-<…>.md` next to it, the coordinator's current state and the last two sessions' notes; older sessions are in `run-<…>.history.md`. The user's decisions and durable facts are in `decisions.md` (shared by all runs). Read the history only for a question about an older session.
- **Transcripts** (facts): `~/.claude/projects/<sanitized repo path>/<session>.jsonl` for each coordinator session (one per wave), and `<session>/subagents/agent-<id>.jsonl` + `.meta.json` for each subagent: token usage per API call, models, timing, tool calls and errors, permission prompts, interrupts, compactions.

**Don't read transcripts into your context.** They're megabytes. The script below extracts everything; open a transcript only for a targeted look (e.g. `grep` one agent's failed tool calls) when a number needs explaining.

## 1. Collect

```bash
python ~/.claude/skills/analyze-coordinator/scripts/collect.py --repo <repo> [--run <name>] [--session <id> ...]
```

It writes `<run>.metrics.json` next to the run log and prints a **digest**: totals, flags, notes, per-session and per-ticket tables, the outlier agents, and a trends table of the last 10 runs, built from the earlier `*.metrics.json` in the same folder. Costs use API list prices (in the script's `PRICES`); on a subscription they're an API-equivalent estimate, so say so. If it reports missing data (no event log, sessions not found, unpriced models), carry on with what's there and list the gaps in the report.

**Work from the digest.** Don't read the metrics JSON or the earlier ones whole: they grow with every run. When a number needs explaining, pull just that part, e.g. `python -c "import json; m=json.load(open('<metrics>')); print([a for a in m['agents'] if a['ticket'] == 84])"`. Call out the trends that matter (cost per merged ticket, interruptions, fix rounds, coordinator share, review cost).

## 2. Analyse

Work through these questions with numbers from the metrics. The thresholds are starting points for judging, not facts; say when a number is borderline.

**Outcomes**
- Tickets merged versus stopped, and why the stopped ones stopped. Cost and cycle time per merged ticket.

**Subagents**
- Per role (implementer, reviewer, fixer, spec): cost, API calls, duration, tool errors, outcomes (`partial` = hit its turn limit, `question` = escalated). Spec writers (wave updates, and `init-spec` runs inside a coordinator session) are overhead: compare a wave update with the wave's ticket cost, and the `spec` events' mismatches with the deltas merged. The metrics' `events.spec` has the updates, mismatches and spec cost: mismatches point at vague spec changes in the plan (a `decompose-feature` improvement) or implementers drifting from them (`implement-ticket`); a spec that stays missing run after run is worth one line in the report.
- Implementers: how many fix rounds and findings did their work cause? Which models and effort levels did well or badly for their ticket tier?
- Reviewers: findings per review, and how many the coordinator rejected (a high rejection rate means a noisy reviewer). Review cost relative to implementation (aim ≤ 60%).
- Fixers: were they used for mechanical rounds, and did their fixes hold?

**Interruptions** (aim: no technical escalations, about one user wait per wave besides the handoff)
- Escalations by kind and by who resolved them. A `technical` escalation means an implementer asked something it should have decided.
- Waits on the user, permission prompts (these point to a missing allowlist) and user interrupts.

**How the coordinator processed results**
- The coordinator's share of total cost (aim < 25%).
- Context growth per session and any compactions. A steep slope means it's reading too much itself.
- Light versus full review paths, re-reviews, final gate failures and their causes, conflicts and how they were resolved.

**Token cost**
- Cost by role and model, cache hit ratio (aim > 85%), cache-write share (high = cold starts or resumes after the cache expired).
- Logging overhead: event appends that used a tool call of their own (should be 0).
- Model and effort fit: Opus or high effort on work that went smoothly at a lower tier elsewhere, or a cheap tier that caused rework.

## 3. Conclude

Decide the verdict (`good`, `mixed` or `poor`) and pick out:
- **Strengths:** what to keep (2–4 items).
- **Weaknesses:** each with its evidence (numbers) and its impact.
- **Bottlenecks:** where time, tokens or user attention concentrated.
- **Improvements:** at most 6, ranked. Each one names the exact change and where it goes (e.g. `coordinator/SKILL.md §5`, `agents/ticket-reviewer.md`, `implement-ticket` "Decide or escalate", `decompose-feature/references/test-cases.md`, `settings.json` allowlist), plus the expected effect. Prefer changes that remove a whole class of cost or interruption over tuning one ticket.

Don't invent problems to fill the lists: a clean run gets a short report.

## 4. Report

1. Write the findings as JSON (shape documented at the top of `scripts/render.py`) to a file next to the metrics.
2. Render: `python ~/.claude/skills/analyze-coordinator/scripts/render.py <metrics.json> <findings.json> <run>.report.html`, saved next to the run log. It writes two files:
   - `<run>.report.html`, the visual report for the user;
   - `<run>.report.md`, the same findings plus all the data behind them as plain Markdown. This is the file to hand to a later session that improves the coordinator.
3. In the reply: the verdict, the 3 most important findings with their numbers, the top improvements, and both paths (say the `.md` is the one to pass to an improvement session). Offer in one line to publish the page as a private artifact for viewing in the browser. Don't apply any improvement unless the user asks.
