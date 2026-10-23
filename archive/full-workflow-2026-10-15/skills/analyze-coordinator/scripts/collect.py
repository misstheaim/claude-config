"""Collect metrics for one coordinator run from Claude Code transcripts and the coordinator's event log.

Usage:
  python collect.py [--repo PATH] [--run NAME] [--session ID ...] [--out FILE]

  --repo     the repo the coordinator ran in (default: current directory)
  --run      run log name (e.g. run-2026-10-14-0900) or path; default: newest in <git-common-dir>/coordinator/
  --session  coordinator session id(s) to analyse instead of discovering them
  --out      where to write metrics JSON (default: <run>.metrics.json next to the run log, or ./metrics.json)

Prints a short summary; the full data goes to the JSON file. Reads transcripts locally, never sends anything anywhere.
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

# USD per million tokens, API list prices (claude-api skill, cached 2026-10-06).
# Cache writes: 1.25x input (5 min TTL), 2x input (1 h TTL).
PRICES = {
    "claude-fable-5-1": {"in": 10.00, "out": 50.00, "read": 0.25},
    "claude-opus-5-5": {"in": 4.00, "out": 20.00, "read": 0.20},
    "claude-sonnet-5-5": {"in": 2.00, "out": 10.00, "read": 0.20},
    "claude-haiku-5-5": {"in": 0.10, "out": 0.50, "read": 0.01},
}

ROLE_BY_AGENT_TYPE = {
    "ticket-implementer": "implementer",
    "ticket-reviewer": "reviewer",
    "ticket-fixer": "fixer",
    "test-designer": "test-designer",
    "spec-writer": "spec",
    "Explore": "explorer",
}


TICKET_RE = re.compile(r"Ticket #(\d+)|issue #(\d+)|#(\d+)")


def ticket_from(text):
    m = TICKET_RE.search(text or "")
    if not m:
        return None
    return int(next(g for g in m.groups() if g))


def minutes(a, b):
    a, b = parse_ts(a), parse_ts(b)
    return round((b - a).total_seconds() / 60, 1) if a and b else None


def parse_ts(s):
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def price_for(model):
    if not model:
        return None
    for key, p in PRICES.items():
        if model.startswith(key):
            return p
    return None


def cost_of(u, model):
    p = price_for(model)
    if not p:
        return None
    return (
        u["input"] * p["in"]
        + u["output"] * p["out"]
        + u["cache_write_5m"] * p["in"] * 1.25
        + u["cache_write_1h"] * p["in"] * 2.0
        + u["cache_read"] * p["read"]
    ) / 1_000_000


def empty_usage():
    # thinking stays None until a transcript reports it (subagent transcripts often don't)
    return {"input": 0, "output": 0, "thinking": None, "cache_write_5m": 0, "cache_write_1h": 0, "cache_read": 0}


def add_usage(acc, u):
    for k in acc:
        v = u.get(k)
        if v is not None:
            acc[k] = (acc[k] or 0) + v


def sanitize(path):
    return re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(path))


def parse_transcript(path):
    """Summarise one transcript JSONL (main session or subagent)."""
    usage_by_model = defaultdict(empty_usage)
    thinking_missing = set()  # models with at least one message that doesn't report thinking tokens
    seen_msgs = set()
    calls = []  # per API call: context size (for growth charts)
    t_first = t_last = None
    tool_calls = Counter()
    tool_errors = 0
    human_msgs = 0
    interrupts = 0
    perm_prompts = 0
    perm_rejects = 0
    compactions = 0
    agent_calls = {}  # tool_use_id -> input summary
    agent_results = {}  # tool_use_id -> agentId
    send_messages = Counter()  # agent id/name -> count
    skill_invocations = []
    bash_calls = {}  # tool_use_id -> {ts, cmd, msg}
    results = {}  # tool_use_id -> {ts, text, is_error}
    msg_tools = defaultdict(list)  # assistant message id -> tool_use ids
    tool_names = {}  # tool_use_id -> tool name
    bad_lines = 0

    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                bad_lines += 1
                continue
            ts = parse_ts(d.get("timestamp"))
            if ts:
                t_first = t_first or ts
                t_last = ts
            typ = d.get("type")
            if typ == "assistant":
                m = d.get("message", {})
                mid = m.get("id") or d.get("requestId") or d.get("uuid")
                model = m.get("model")
                if mid not in seen_msgs and model and model != "<synthetic>":
                    seen_msgs.add(mid)
                    u = m.get("usage") or {}
                    cc = u.get("cache_creation") or {}
                    w5 = cc.get("ephemeral_5m_input_tokens")
                    w1 = cc.get("ephemeral_1h_input_tokens")
                    if w5 is None and w1 is None:
                        w5, w1 = u.get("cache_creation_input_tokens", 0), 0
                    rec = {
                        "input": u.get("input_tokens", 0) or 0,
                        "output": u.get("output_tokens", 0) or 0,
                        "thinking": (u.get("output_tokens_details") or {}).get("thinking_tokens"),
                        "cache_write_5m": w5 or 0,
                        "cache_write_1h": w1 or 0,
                        "cache_read": u.get("cache_read_input_tokens", 0) or 0,
                    }
                    add_usage(usage_by_model[model], rec)
                    if rec["thinking"] is None:
                        thinking_missing.add(model)
                    calls.append({
                        "ts": d.get("timestamp"),
                        "context": rec["input"] + rec["cache_read"] + rec["cache_write_5m"] + rec["cache_write_1h"],
                        "model": model,
                    })
                for c in m.get("content") or []:
                    if isinstance(c, dict) and c.get("type") == "tool_use":
                        name = c.get("name", "?")
                        tool_calls[name] += 1
                        inp = c.get("input") or {}
                        msg_tools[mid].append(c.get("id"))
                        tool_names[c.get("id")] = name
                        if name in ("Bash", "PowerShell"):
                            bash_calls[c.get("id")] = {"ts": d.get("timestamp"), "cmd": str(inp.get("command") or ""), "msg": mid}
                        if name == "Agent":
                            agent_calls[c.get("id")] = {
                                "description": inp.get("description"),
                                "subagent_type": inp.get("subagent_type"),
                                "model": inp.get("model"),
                                "effort": inp.get("effort"),
                                "isolation": inp.get("isolation"),
                                "prompt": str(inp.get("prompt") or "")[:600],
                                "ts": d.get("timestamp"),
                            }
                        elif name == "SendMessage":
                            send_messages[str(inp.get("to"))] += 1
                        elif name == "Skill":
                            skill_invocations.append(inp.get("skill"))
            elif typ == "user":
                if (d.get("origin") or {}).get("kind") == "human":
                    human_msgs += 1
                pd = d.get("permissionDecision") or {}
                src = str(pd.get("source", ""))
                content = (d.get("message") or {}).get("content")
                answered = {tool_names.get(c.get("tool_use_id")) for c in content if isinstance(c, dict)} if isinstance(content, list) else set()
                # answering an AskUserQuestion also records a user decision, but it's a question, not a permission prompt
                if src.startswith("user") and "AskUserQuestion" not in answered:
                    perm_prompts += 1
                    if pd.get("decision") == "reject":
                        perm_rejects += 1
                text = content if isinstance(content, str) else json.dumps(content) if content else ""
                if "[Request interrupted" in text:
                    interrupts += 1
                if isinstance(content, list):
                    for b in content:
                        if isinstance(b, dict) and b.get("type") == "tool_result":
                            if b.get("is_error"):
                                tool_errors += 1
                            rc = b.get("content")
                            rtext = rc if isinstance(rc, str) else json.dumps(rc) if rc else ""
                            results[b.get("tool_use_id")] = {"ts": d.get("timestamp"), "text": rtext[:2000], "is_error": bool(b.get("is_error"))}
                            tur = d.get("toolUseResult")
                            if isinstance(tur, dict) and tur.get("agentId"):
                                agent_results[b.get("tool_use_id")] = tur["agentId"]
            elif typ == "system" and d.get("subtype") == "compact_boundary":
                compactions += 1

    for model in thinking_missing:
        usage_by_model[model]["thinking"] = None  # a partial count would look like a real (too low) number
    total = empty_usage()
    cost = 0.0
    cost_known = True
    models = {}
    for model, u in usage_by_model.items():
        add_usage(total, u)
        c = cost_of(u, model)
        if c is None:
            cost_known = False
        else:
            cost += c
        models[model] = {"usage": u, "cost": c}

    return {
        "path": path,
        "start": t_first.isoformat() if t_first else None,
        "end": t_last.isoformat() if t_last else None,
        "duration_min": round((t_last - t_first).total_seconds() / 60, 1) if t_first and t_last else None,
        "api_calls": len(seen_msgs),
        "usage": total,
        "cost": round(cost, 4),
        "cost_complete": cost_known,
        "models": models,
        "max_context": max((c["context"] for c in calls), default=0),
        "context_series": downsample([c["context"] for c in calls], 200),
        "tool_calls": dict(tool_calls),
        "tool_errors": tool_errors,
        "human_msgs": human_msgs,
        "interrupts": interrupts,
        "permission_prompts": perm_prompts,
        "permission_rejects": perm_rejects,
        "compactions": compactions,
        "agent_calls": agent_calls,
        "agent_results": agent_results,
        "send_messages": dict(send_messages),
        "skills": skill_invocations,
        "bash_calls": bash_calls,
        "results": results,
        "msg_tools": dict(msg_tools),
        "bad_lines": bad_lines,
    }


def downsample(values, n):
    if len(values) <= n:
        return values
    step = len(values) / n
    return [max(values[int(i * step):int((i + 1) * step)] or [0]) for i in range(n)]


def git_common_dir(repo):
    try:
        out = subprocess.run(["git", "-C", repo, "rev-parse", "--git-common-dir"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return out if os.path.isabs(out) else os.path.normpath(os.path.join(repo, out))


def load_events(path):
    events, bad = [], 0
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except ValueError:
                    bad += 1
    return events, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--run")
    ap.add_argument("--session", action="append", default=[])
    ap.add_argument("--out")
    args = ap.parse_args()

    repo = os.path.abspath(args.repo)
    notes = []

    # --- run log and events
    run_dir = None
    common = git_common_dir(repo)
    if common:
        run_dir = os.path.join(common, "coordinator")
    run_log = events_path = None
    if args.run:
        base = args.run if os.path.isabs(args.run) else os.path.join(run_dir or repo, args.run)
        base = re.sub(r"(\.events\.jsonl|\.md)$", "", base)
        run_log, events_path = base + ".md", base + ".events.jsonl"
    elif run_dir and os.path.isdir(run_dir):
        logs = sorted(glob.glob(os.path.join(run_dir, "run-*.md")))
        if logs:
            run_log = logs[-1]
            events_path = run_log[:-3] + ".events.jsonl"
    events, bad_events = load_events(events_path)
    if not run_log or not os.path.exists(run_log):
        notes.append("No coordinator run log found; analysing transcripts only.")
    if not events:
        notes.append("No event log (or it's empty): the coordinator's judgments (reviews, triage, escalations, waits, final gates, conflicts, stopped tickets) are missing. Tickets, roles, fix rounds, merges and costs still come from the transcripts.")
    if bad_events:
        notes.append(f"{bad_events} malformed line(s) in the event log were skipped.")

    event_agent_ids = {e.get("agent_id") for e in events if e.get("agent_id")}
    ev_times = [parse_ts(e.get("ts")) for e in events if parse_ts(e.get("ts"))]
    window = (min(ev_times), max(ev_times)) if ev_times else None

    # --- coordinator sessions
    proj_dir = os.path.join(os.path.expanduser("~"), ".claude", "projects", sanitize(repo))
    session_files = []
    if args.session:
        for sid in args.session:
            hits = glob.glob(os.path.join(os.path.expanduser("~"), ".claude", "projects", "*", sid + ".jsonl"))
            if hits:
                session_files.append(hits[0])
            else:
                notes.append(f"Session {sid} not found.")
    elif os.path.isdir(proj_dir):
        for f in glob.glob(os.path.join(proj_dir, "*.jsonl")):
            with open(f, encoding="utf-8") as fh:
                text = fh.read()
            is_coord = "<command-name>/coordinator" in text or any(a in text for a in event_agent_ids)
            if not is_coord:
                continue
            if window:
                mtime = dt.datetime.fromtimestamp(os.path.getmtime(f), dt.timezone.utc)
                if mtime < window[0] - dt.timedelta(hours=1):
                    continue
            session_files.append(f)
    else:
        notes.append(f"Transcript folder not found: {proj_dir}")

    sessions, agents = [], []
    for sf in sorted(session_files):
        s = parse_transcript(sf)
        s["session_id"] = os.path.basename(sf)[:-6]
        sub_dir = os.path.join(sf[:-6], "subagents")
        # Subagents can spawn their own (e.g. an implementer's Explore agents), so look up
        # Agent calls in every transcript of the session, not only the coordinator's.
        parsed = []
        for af in sorted(glob.glob(os.path.join(sub_dir, "**", "agent-*.jsonl"), recursive=True)):
            meta = {}
            mf = af[:-len(".jsonl")] + ".meta.json"
            if os.path.exists(mf):
                with open(mf, encoding="utf-8") as fh:
                    meta = json.load(fh)
            parsed.append((af, meta, parse_transcript(af)))
        all_calls = dict(s["agent_calls"])
        tool_by_agent = {aid: tid for tid, aid in s["agent_results"].items()}
        for _, _, p in parsed:
            all_calls.update(p["agent_calls"])
            tool_by_agent.update({aid: tid for tid, aid in p["agent_results"].items()})
        for af, meta, a in parsed:
            aid = os.path.basename(af)[len("agent-"):-len(".jsonl")]
            call = all_calls.get(meta.get("toolUseId") or tool_by_agent.get(aid), {})
            a.update({
                "agent_id": aid,
                "session_id": s["session_id"],
                "agent_type": meta.get("agentType") or call.get("subagent_type"),
                "description": meta.get("description") or call.get("description"),
                "requested_model": meta.get("model") or call.get("model"),
                "effort": call.get("effort"),
                "resumes": s["send_messages"].get(aid, 0),
                "prompt_ticket": ticket_from(call.get("prompt")),
                "dispatched_ts": call.get("ts"),
            })
            for k in ("context_series", "agent_calls", "agent_results", "bash_calls", "results", "msg_tools"):
                a.pop(k, None)
            agents.append(a)
        sessions.append(s)

    if not sessions:
        notes.append("No coordinator session transcripts found.")

    # --- join events onto agents
    dispatch = {e["agent_id"]: e for e in events if e.get("event") == "dispatch" and e.get("agent_id")}
    returns = defaultdict(list)
    for e in events:
        if e.get("event") == "agent_return" and e.get("agent_id"):
            returns[e["agent_id"]].append(e.get("outcome"))
    for a in agents:
        de = dispatch.get(a["agent_id"], {})
        a["ticket"] = a.pop("prompt_ticket") if a.get("prompt_ticket") is not None else de.get("ticket")
        a["role"] = ROLE_BY_AGENT_TYPE.get(a["agent_type"] or "") or de.get("role") or a["agent_type"] or "other"
        a["outcomes"] = returns.get(a["agent_id"], [])
    unmatched = [a["agent_id"] for a in agents if a["ticket"] is None and a["role"] in ("implementer", "reviewer", "fixer")]
    if unmatched:
        notes.append(f"{len(unmatched)} ticket subagent(s) have no ticket number in their prompt: {', '.join(unmatched[:8])}.")

    # --- mechanical facts from the coordinator transcripts
    prs, merges, ci_runs = {}, [], []
    event_appends = standalone_appends = 0
    for s in sessions:
        for tid, bc in s["bash_calls"].items():
            cmd, res = bc["cmd"], s["results"].get(tid, {})
            if "gh pr create" in cmd:
                n = ticket_from(re.search(r"--title\s+[\"']?([^\"']*)", cmd).group(1) if re.search(r"--title\s+[\"']?([^\"']*)", cmd) else cmd)
                m = re.search(r"/pull/(\d+)", res.get("text", ""))
                if n is not None and m:
                    prs[int(m.group(1))] = n
            m = re.search(r"gh pr merge\s+(\d+)", cmd)
            if m and not res.get("is_error"):
                merges.append({"pr": int(m.group(1)), "ts": res.get("ts") or bc["ts"]})
            # ship.sh merges inside the script: its last line names the ticket and the PR
            m = "ship.sh" in cmd and re.search(r"RESULT: 0 merged #(\d+) -> PR #(\d+)", res.get("text", ""))
            if m:
                prs[int(m.group(2))] = int(m.group(1))
                merges.append({"pr": int(m.group(2)), "ts": res.get("ts") or bc["ts"]})
            if "gh pr checks" in cmd:
                ci_runs.append({"ticket": None, "minutes": minutes(bc["ts"], res.get("ts")), "failed": res.get("is_error", False)})
            if ".events.jsonl" in cmd:
                event_appends += 1
                rest = re.sub(r"(printf|echo)\s[^;&|]*>>\s*\S+", "", cmd)
                rest = re.sub(r"[;&|\s]+", "", rest)
                if len(s["msg_tools"].get(bc["msg"], [])) == 1 and not rest:
                    standalone_appends += 1

    # --- aggregates
    coord_cost = sum(s["cost"] for s in sessions)
    agent_cost = sum(a["cost"] for a in agents)
    total_cost = coord_cost + agent_cost
    by_role = defaultdict(lambda: {"cost": 0.0, "agents": 0, "usage": empty_usage()})
    by_role["coordinator"]["cost"] = coord_cost
    by_role["coordinator"]["agents"] = len(sessions)
    for s in sessions:
        add_usage(by_role["coordinator"]["usage"], s["usage"])
    for a in agents:
        r = by_role[a["role"]]
        r["cost"] += a["cost"]
        r["agents"] += 1
        add_usage(r["usage"], a["usage"])
    by_model = defaultdict(lambda: {"cost": 0.0, "usage": empty_usage()})
    for x in sessions + agents:
        for model, mu in x["models"].items():
            by_model[model]["cost"] += mu["cost"] or 0
            add_usage(by_model[model]["usage"], mu["usage"])

    total_usage = empty_usage()
    for x in sessions + agents:
        add_usage(total_usage, x["usage"])
    input_side = total_usage["input"] + total_usage["cache_read"] + total_usage["cache_write_5m"] + total_usage["cache_write_1h"]

    # tickets
    tickets = defaultdict(lambda: {"agents": [], "cost": 0.0, "events": Counter(), "fix_rounds": 0, "findings": Counter(),
                                   "first_ts": None, "merged_ts": None, "outcome": "open", "escalations": 0})
    esc_by_ticket = Counter(e.get("ticket") for e in events if e.get("event") == "escalation")
    for a in agents:
        if a["ticket"] is not None:
            t = tickets[a["ticket"]]
            t["agents"].append({"id": a["agent_id"], "role": a["role"], "cost": a["cost"]})
            t["cost"] += a["cost"]
            if a["dispatched_ts"] and (t["first_ts"] is None or a["dispatched_ts"] < t["first_ts"]):
                t["first_ts"] = a["dispatched_ts"]
            if a["role"] == "fixer":
                t["fix_rounds"] += 1
            elif a["role"] == "implementer":
                # fix rounds go to fresh implementers now; older runs resumed the original one
                t["fix_rounds"] += a["resumes"] + 1
                t["implementers"] = t.get("implementers", 0) + 1
    impl_ids = {a["agent_id"] for a in agents if a["role"] == "implementer"}
    returns = Counter((e.get("ticket"), e.get("outcome")) for e in events
                      if e.get("event") == "agent_return" and any(str(e.get("agent_id") or "?").startswith(i[:8]) for i in impl_ids))
    for n, t in tickets.items():
        if t.pop("implementers", 0):
            t["fix_rounds"] -= 1  # the first implementer dispatch is the implementation itself
        # continuations after a question or an interruption (resumed or fresh) aren't fix rounds
        not_fixes = max(esc_by_ticket.get(n, 0), returns[(n, "question")]) + returns[(n, "partial")] + returns[(n, "error")]
        t["fix_rounds"] = max(0, t["fix_rounds"] - not_fixes)
    for mg in merges:
        n = prs.get(mg["pr"])
        if n is not None:
            t = tickets[n]
            t["merged_ts"], t["outcome"], t["pr"] = mg["ts"], "merged", mg["pr"]
    for e in events:
        n = e.get("ticket")
        if n is None:
            continue
        t = tickets[n]
        ev = e.get("event")
        t["events"][ev] += 1
        ts = e.get("ts")
        if ev == "review":
            for k, v in (e.get("findings") or {}).items():
                t["findings"][k] += int(v or 0)
        if ev == "escalation":
            t["escalations"] += 1
        if ev == "merged" and t["outcome"] != "merged":  # ship.sh writes it; a transcript merge, if found, wins
            t["merged_ts"], t["outcome"], t["pr"] = ts, "merged", e.get("pr")
        if ev == "ticket_stopped":
            t["outcome"], t["stop_reason"] = "stopped", e.get("reason")
    for t in tickets.values():
        a, b = parse_ts(t["first_ts"]), parse_ts(t["merged_ts"])
        t["cycle_min"] = round((b - a).total_seconds() / 60, 1) if a and b else None
        t["events"] = dict(t["events"])
        t["findings"] = dict(t["findings"])
        t["cost"] = round(t["cost"], 4)

    ev_count = Counter(e.get("event") for e in events)
    escal = Counter((e.get("kind"), e.get("resolved_by")) for e in events if e.get("event") == "escalation")
    waits = Counter(e.get("reason") for e in events if e.get("event") == "user_wait")
    fix_by = Counter()
    for a in agents:
        if a["role"] == "fixer":
            fix_by["fixer"] += 1
    fix_by["implementer"] = sum(t["fix_rounds"] for t in tickets.values()) - fix_by["fixer"]
    fix_by = +fix_by
    gates = Counter(e.get("result") for e in events if e.get("event") == "final_gate")
    gate_causes = Counter(e.get("cause") for e in events if e.get("event") == "final_gate" and e.get("result") == "fail")
    conflicts = Counter((e.get("kind"), e.get("resolved_by")) for e in events if e.get("event") == "conflict")
    review_paths = Counter(e.get("path") for e in events if e.get("event") == "review")
    review_skips = Counter(e.get("reason") or "?" for e in events if e.get("event") == "review" and e.get("path") == "skipped")
    triage = Counter()
    for e in events:
        if e.get("event") == "triage":
            for k in ("fix", "reject", "followup", "ask"):
                triage[k] += int(e.get(k) or 0)
    findings = Counter()
    for e in events:
        if e.get("event") == "review":
            for k, v in (e.get("findings") or {}).items():
                findings[k] += int(v or 0)

    merged = [n for n, t in tickets.items() if t["outcome"] == "merged"]
    stopped = [n for n, t in tickets.items() if t["outcome"] == "stopped"]

    # --- heuristic flags (signals for the analyst, not conclusions)
    flags = []

    def flag(sev, fid, msg):
        flags.append({"severity": sev, "id": fid, "message": msg})

    if total_cost and coord_cost / total_cost > 0.35:
        flag("serious", "coordinator-share", f"The coordinator itself is {coord_cost / total_cost:.0%} of the cost; it should mostly delegate.")
    for s in sessions:
        if s["compactions"]:
            flag("warning", "compaction", f"Session {s['session_id'][:8]} was compacted {s['compactions']} time(s): the wave handoff came too late.")
        if s["max_context"] > 300_000:
            flag("warning", "context", f"Session {s['session_id'][:8]} reached {s['max_context']:,} tokens of context.")
    writes = total_usage["cache_write_5m"] + total_usage["cache_write_1h"]
    if input_side and writes / input_side > 0.25:
        flag("warning", "cache-writes", f"{writes / input_side:.0%} of input tokens were cache writes: likely cache expiry between resumes, or many cold-started agents.")
    tech = sum(v for (k, r), v in escal.items() if k == "technical")
    if tech:
        flag("warning", "technical-escalations", f"{tech} technical escalation(s): implementers asked about things they should decide themselves.")
    user_waits = sum(waits.values())
    if merged and user_waits / max(len(merged), 1) > 0.5:
        flag("warning", "user-waits", f"{user_waits} waits on the user for {len(merged)} merged ticket(s).")
    perm = sum(x["permission_prompts"] for x in sessions + agents)
    if perm:
        flag("warning", "permission-prompts", f"{perm} permission prompt(s) needed a human during the run.")
    intr = sum(x["interrupts"] for x in sessions + agents)
    if intr:
        flag("warning", "interrupts", f"The user interrupted {intr} time(s).")
    for n, t in tickets.items():
        if t["fix_rounds"] >= 2:
            flag("warning", "fix-rounds", f"Ticket #{n} needed {t['fix_rounds']} fix rounds.")
        rev = sum(x["cost"] for x in t["agents"] if x["role"] == "reviewer")
        imp = sum(x["cost"] for x in t["agents"] if x["role"] == "implementer")
        if imp and rev > imp:
            flag("warning", "review-cost", f"Ticket #{n}: review cost ${rev:.2f} exceeds implementation cost ${imp:.2f}.")
    if gates.get("fail"):
        flag("serious", "final-gate", f"{gates['fail']} final gate failure(s): {dict(gate_causes)}.")
    for a in agents:
        if "partial" in a["outcomes"]:
            flag("warning", "max-turns", f"Agent {a['agent_id']} ({a['role']}, #{a['ticket']}) hit its turn limit.")
        if a["tool_errors"] >= 5:
            flag("warning", "tool-errors", f"Agent {a['agent_id']} ({a['role']}) had {a['tool_errors']} failed tool calls.")
    for n, t in tickets.items():
        if t["outcome"] == "merged" and not t["events"].get("final_gate"):
            notes.append(f"Ticket #{n} merged without a final_gate event (event log incomplete).")
        if not t["events"].get("review"):
            if any(x["role"] == "reviewer" for x in t["agents"]):
                notes.append(f"Ticket #{n} had a reviewer but no review event (event log incomplete).")
            elif t["outcome"] == "merged":
                notes.append(f"Ticket #{n} merged without a review event; log path \"skipped\" with a reason (event log incomplete).")
    if standalone_appends:
        flag("warning", "event-overhead", f"{standalone_appends} of {event_appends} event appends used a tool call of their own (an extra turn each); chain them onto other commands.")
    if stopped:
        flag("critical", "stopped", f"{len(stopped)} ticket(s) stopped: {', '.join('#' + str(n) for n in stopped)}.")
    for x in [*sessions, *agents]:
        if not x["cost_complete"]:
            notes.append("Some models have no price in the table; their cost is missing from the totals.")
            break

    # behaviour spec: one update per handoff (light) or per wave (full), its mismatches and its cost
    spec_events = [e for e in events if e.get("event") == "spec"]
    spec_results = Counter(e.get("result") for e in spec_events)
    spec_mismatches = sum(int(e.get("mismatches") or 0) for e in spec_events)
    spec_choice = next((e.get("choice") for e in reversed(spec_events) if e.get("choice")), None)
    spec_cost = by_role["spec"]["cost"] if "spec" in by_role else 0.0
    handoffs_without_spec = 0
    for s in sessions:
        a, b = parse_ts(s["start"]), parse_ts(s["end"])
        if not (a and b):
            continue
        inside = [e for e in events if (t := parse_ts(e.get("ts"))) and a <= t <= b]
        ends = any(e.get("event") in ("wave_handoff", "run_finished") for e in inside)
        if ends and not any(e.get("event") == "spec" for e in inside):
            handoffs_without_spec += 1
    if handoffs_without_spec and spec_events:
        flag("warning", "spec-update-missing", f"{handoffs_without_spec} session(s) handed off without a `spec` event: the spec update was skipped or not logged.")
    if spec_mismatches:
        flag("warning", "spec-mismatches", f"{spec_mismatches} spec mismatch(es): merged code didn't do what its tickets' spec changes said "
             f"(vague deltas in the plan, or implementers drifting from them) for {len(merged)} merged ticket(s).")
    if spec_cost and agent_cost and spec_cost / agent_cost > 0.15:
        flag("warning", "spec-cost", f"Spec writers cost ${spec_cost:.2f}, {spec_cost / agent_cost:.0%} of all subagent cost; an update should cost about what a smoke check does.")
    if spec_results.get("missing"):
        notes.append(f"The project has no behaviour spec yet (choice: {spec_choice or 'not recorded'}); spec changes in the tickets aren't landing anywhere.")
    spec_stats = {"results": dict(spec_results), "mismatches": spec_mismatches, "choice": spec_choice,
                  "cost": round(spec_cost, 4), "handoffs_without_update": handoffs_without_spec}

    out = {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "repo": repo,
        "run_log": run_log,
        "events_file": events_path if events else None,
        "pricing_note": "API list prices (USD per million tokens); on a Claude subscription this is an API-equivalent estimate, not a bill.",
        "totals": {
            "cost": round(total_cost, 4),
            "coordinator_cost": round(coord_cost, 4),
            "subagent_cost": round(agent_cost, 4),
            "usage": total_usage,
            "cache_hit_ratio": round(total_usage["cache_read"] / input_side, 3) if input_side else None,
            "sessions": len(sessions),
            "subagents": len(agents),
            "tickets_merged": len(merged),
            "tickets_stopped": len(stopped),
            "cost_per_merged_ticket": round(total_cost / len(merged), 4) if merged else None,
            "wall_clock_min": round(sum(s["duration_min"] or 0 for s in sessions), 1),
            "human_messages": sum(s["human_msgs"] for s in sessions),
            "user_waits": user_waits,
            "permission_prompts": perm,
            "interrupts": intr,
            "tool_errors": sum(x["tool_errors"] for x in sessions + agents),
        },
        "by_role": {k: {**v, "cost": round(v["cost"], 4)} for k, v in by_role.items()},
        "by_model": {k: {**v, "cost": round(v["cost"], 4)} for k, v in by_model.items()},
        "event_logging": {"appends": event_appends, "standalone_appends": standalone_appends},
        "ci": {"runs": len(ci_runs), "failed": sum(1 for c in ci_runs if c["failed"]),
               "minutes": round(sum(c["minutes"] or 0 for c in ci_runs), 1)},
        "events": {
            "counts": dict(ev_count),
            "spec": spec_stats,
            "escalations": [{"kind": k, "resolved_by": r, "count": v} for (k, r), v in escal.items()],
            "user_waits": dict(waits),
            "fix_rounds_by": dict(fix_by),
            "final_gates": dict(gates),
            "final_gate_fail_causes": dict(gate_causes),
            "conflicts": [{"kind": k, "resolved_by": r, "count": v} for (k, r), v in conflicts.items()],
            "review_paths": dict(review_paths),
            "review_skip_reasons": dict(review_skips),
            "findings": dict(findings),
            "triage": dict(triage),
            "reject_rate": round(triage["reject"] / sum(triage.values()), 3) if sum(triage.values()) else None,
        },
        "sessions": [{k: v for k, v in s.items() if k not in ("agent_calls", "agent_results", "bash_calls", "results", "msg_tools")} for s in sessions],
        "agents": agents,
        "tickets": {str(k): v for k, v in sorted(tickets.items(), key=lambda kv: str(kv[0]))},
        "flags": flags,
        "notes": notes,
    }

    out_path = args.out or (run_log[:-3] + ".metrics.json" if run_log and os.path.isdir(os.path.dirname(run_log)) else "metrics.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)

    t = out["totals"]
    print(f"metrics: {out_path}")
    print(f"sessions {t['sessions']}, subagents {t['subagents']}, merged {t['tickets_merged']}, stopped {t['tickets_stopped']}")
    print(f"cost ${t['cost']:.2f} (coordinator ${t['coordinator_cost']:.2f}, subagents ${t['subagent_cost']:.2f}), cache hit {t['cache_hit_ratio']}")
    print(f"flags {len(flags)}, notes {len(notes)}")
    for n in notes:
        print("note:", n)


if __name__ == "__main__":
    sys.exit(main())
