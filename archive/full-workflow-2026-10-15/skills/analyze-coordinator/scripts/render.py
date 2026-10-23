"""Render a coordinator effectiveness report as one self-contained HTML file.

Usage:
  python render.py METRICS.json FINDINGS.json OUT.html

Writes OUT.html (the visual report) and OUT.md next to it: the same findings and data as plain Markdown,
meant to be handed to a later session that improves the coordinator.

METRICS.json comes from collect.py. FINDINGS.json is written by the analyst (the model) with this shape:
  {
    "verdict": "good" | "mixed" | "poor",
    "summary": "2-4 sentences",
    "strengths": ["..."],
    "weaknesses": [{"title": "...", "evidence": "...", "impact": "..."}],
    "bottlenecks": [{"title": "...", "evidence": "..."}],
    "improvements": [{"priority": "high" | "medium" | "low", "title": "...", "change": "...",
                       "where": "file or section", "expected_effect": "..."}]
  }
"""
import html
import os
import json
import sys

E = html.escape

CSS = """
.viz-root {
  color-scheme: light;
  --page: #f9f9f7; --surface-1: #fcfcfb; --border: rgba(11,11,11,0.10);
  --text-primary: #0b0b0b; --text-secondary: #52514e; --text-muted: #898781;
  --grid: #e1e0d9; --axis: #c3c2b7; --series-1: #2a78d6;
  --good: #0ca30c; --warning: #fab219; --serious: #ec835a; --critical: #d03b3b;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) .viz-root {
    color-scheme: dark;
    --page: #0d0d0d; --surface-1: #1a1a19; --border: rgba(255,255,255,0.10);
    --text-primary: #f0efec; --text-secondary: #c3c2b7; --text-muted: #898781;
    --grid: #2c2c2a; --axis: #383835; --series-1: #3987e5;
  }
}
:root[data-theme="dark"] .viz-root {
  color-scheme: dark;
  --page: #0d0d0d; --surface-1: #1a1a19; --border: rgba(255,255,255,0.10);
  --text-primary: #f0efec; --text-secondary: #c3c2b7; --text-muted: #898781;
  --grid: #2c2c2a; --axis: #383835; --series-1: #3987e5;
}
* { box-sizing: border-box; }
body { margin: 0; background: #f9f9f7; }
@media (prefers-color-scheme: dark) { body { background: #0d0d0d; } }
.viz-root { background: var(--page); color: var(--text-primary); min-height: 100vh;
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; padding: 24px 16px 48px; }
main { max-width: 1040px; margin: 0 auto; }
h1 { font-size: 24px; margin: 0 0 4px; }
h2 { font-size: 18px; margin: 32px 0 12px; }
h3 { font-size: 15px; margin: 0 0 8px; }
.sub { color: var(--text-secondary); margin: 0; }
.muted { color: var(--text-muted); font-size: 13px; }
.card { background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 16px; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-top: 20px; }
.tile .v { font-size: 26px; font-weight: 600; font-variant-numeric: tabular-nums; }
.tile .l { color: var(--text-secondary); font-size: 13px; }
.grid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; }
.verdict { display: inline-flex; align-items: center; gap: 6px; font-weight: 600; padding: 2px 10px;
  border-radius: 999px; border: 1px solid var(--border); }
.dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; flex: none; }
ul.items { margin: 0; padding-left: 18px; }
ul.items li { margin: 6px 0; }
.ev { color: var(--text-secondary); font-size: 14px; }
.tbl { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 14px; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--grid); white-space: nowrap; }
th { color: var(--text-secondary); font-weight: 500; }
td.num, th.num { text-align: right; }
.flag { display: flex; gap: 8px; align-items: baseline; margin: 6px 0; }
.flag .lbl { font-size: 12px; font-weight: 600; text-transform: uppercase; color: var(--text-secondary); min-width: 64px; }
.imp { padding: 12px 0; border-bottom: 1px solid var(--grid); }
.imp:first-child { padding-top: 0; }
.imp:last-child { border-bottom: 0; padding-bottom: 0; }
.imp-head { display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; }
.imp p { margin: 6px 0; color: var(--text-secondary); font-size: 14px; }
.imp dl { display: grid; grid-template-columns: max-content 1fr; gap: 4px 12px; margin: 0; font-size: 14px; }
.imp dt { color: var(--text-muted); }
.imp dd { margin: 0; min-width: 0; overflow-wrap: anywhere; }
.pill { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 600; text-transform: uppercase;
  color: var(--text-secondary); padding: 1px 8px; border-radius: 999px; border: 1px solid var(--border); flex: none; }
@media (max-width: 520px) { .imp dl { grid-template-columns: 1fr; } .imp dt { margin-top: 4px; } }
svg text { fill: var(--text-secondary); font-size: 12px; }
svg .val { fill: var(--text-primary); }
"""

STATUS = {"good": "var(--good)", "warning": "var(--warning)", "serious": "var(--serious)", "critical": "var(--critical)"}
ICON = {"good": "✓", "warning": "!", "serious": "!!", "critical": "✕"}
VERDICT = {"good": ("good", "Effective"), "mixed": ("warning", "Mixed"), "poor": ("critical", "Ineffective")}


def money(x):
    return "—" if x is None else (f"${x:,.2f}" if x >= 0.01 or x == 0 else f"${x:.4f}")


def tok(x):
    if x is None:
        return "—"
    return f"{x / 1e6:.2f}M" if x >= 1e6 else f"{x / 1e3:.1f}k" if x >= 1e3 else str(x)


def bar_chart(rows, fmt=money, label_w=110):
    """rows: [(label, value)] -> horizontal single-series bar chart (inline SVG)."""
    rows = [r for r in rows if r[1]]
    if not rows:
        return '<p class="muted">No data.</p>'
    w, bh, gap, right = 400, 18, 10, 64
    plot = w - label_w - right
    vmax = max(v for _, v in rows) or 1
    h = len(rows) * (bh + gap) + 4
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="bar chart">']
    for i, (lab, v) in enumerate(rows):
        y = i * (bh + gap) + 2
        bw = max(2, v / vmax * plot)
        out.append(f'<g><title>{E(str(lab))}: {E(fmt(v))}</title>'
                   f'<text x="{label_w - 8}" y="{y + bh - 5}" text-anchor="end">{E(str(lab))[:22]}</text>'
                   f'<path d="M{label_w},{y} h{bw - 4} a4,4 0 0 1 4,4 v{bh - 8} a4,4 0 0 1 -4,4 h-{bw - 4} z" fill="var(--series-1)"/>'
                   f'<text class="val" x="{label_w + bw + 6}" y="{y + bh - 5}">{E(fmt(v))}</text></g>')
    out.append(f'<line x1="{label_w}" x2="{label_w}" y1="0" y2="{h}" stroke="var(--axis)"/></svg>')
    return "".join(out)


def line_chart(values, title):
    if len(values) < 2:
        return '<p class="muted">Not enough API calls to chart.</p>'
    w, h, l, r, t, b = 980, 200, 56, 12, 10, 24
    vmax = max(values) or 1
    pw, ph = w - l - r, h - t - b
    xs = [l + i / (len(values) - 1) * pw for i in range(len(values))]
    ys = [t + ph - v / vmax * ph for v in values]
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{E(title)}">']
    for frac in (0, 0.5, 1):
        y = t + ph - frac * ph
        out.append(f'<line x1="{l}" x2="{w - r}" y1="{y}" y2="{y}" stroke="var(--grid)"/>'
                   f'<text x="{l - 6}" y="{y + 4}" text-anchor="end">{tok(int(vmax * frac))}</text>')
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    out.append(f'<polyline points="{pts}" fill="none" stroke="var(--series-1)" stroke-width="2" stroke-linejoin="round"/>')
    step = max(1, len(values) // 40)
    for i in range(0, len(values), step):
        out.append(f'<circle cx="{xs[i]:.1f}" cy="{ys[i]:.1f}" r="8" fill="transparent"><title>call {i + 1}: {tok(values[i])} tokens</title></circle>')
    out.append(f'<text x="{l}" y="{h - 6}">first call</text><text x="{w - r}" y="{h - 6}" text-anchor="end">last call</text></svg>')
    return "".join(out)


def kv(d):
    if not d:
        return "—"
    if isinstance(d, list):
        return ", ".join(f'{x.get("kind")} → {x.get("resolved_by")}: {x.get("count")}' for x in d)
    return ", ".join(f"{k}: {v}" for k, v in d.items())


def table(headers, rows, num_cols=()):
    th = "".join(f'<th class="{"num" if i in num_cols else ""}">{E(h)}</th>' for i, h in enumerate(headers))
    body = "".join("<tr>" + "".join(f'<td class="{"num" if i in num_cols else ""}">{c}</td>' for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<div class="tbl"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in r) + " |" for r in rows]
    return "\n".join(out)


def spec_summary(ev):
    s = ev.get("spec") or {}
    if not s.get("results"):
        return "-"
    return f'{kv(s["results"])}; {s["mismatches"]} mismatches; ${s["cost"]:.2f}' + (f'; choice: {s["choice"]}' if s.get("choice") else "")


def markdown(m, f, html_path):
    t, ev, u = m["totals"], m["events"], m["totals"]["usage"]
    run_log = m.get("run_log") or ""
    L = [f"# Coordinator run analysis: {os.path.basename(run_log) or 'transcripts only'}", "",
         "Input for a coordinator-improvement session: the findings and the data behind them. "
         "Apply only the improvements the user picks; the files named under \"Where\" are in `~/.claude/`.", "",
         "**Two versions:** the coordinator workflow exists as a light version (`~/.claude/skills/`, `~/.claude/agents/`) "
         "and a full one (`~/.claude/archive/full-workflow-2026-10-15/`). When applying an improvement, also apply it to "
         "the other version if it has the same feature or problem; leave it out where it doesn't fit (e.g. a test-related "
         "fix has no place in the light version, which has no tests). Keep shared files identical (`ship.sh`).", "",
         f"- Repo: `{m['repo']}`", f"- Generated: {m['generated']}", f"- HTML report: `{html_path}`",
         f"- Run log: `{run_log or 'none'}`", f"- Event log: `{m.get('events_file') or 'none'}`",
         f"- Costs: {m['pricing_note']}", "",
         f"## Verdict: {f.get('verdict', '?')}", "", f.get("summary", ""), ""]
    if f.get("improvements"):
        L += ["## Improvements (ranked)", ""]
        order = {"high": 0, "medium": 1, "low": 2}
        for i, x in enumerate(sorted(f["improvements"], key=lambda x: order.get(x.get("priority"), 3)), 1):
            L += [f"### {i}. {x.get('title', '')} ({x.get('priority', '?')})", "",
                  f"- **Change:** {x.get('change', '')}", f"- **Where:** {x.get('where', '')}",
                  f"- **Expected effect:** {x.get('expected_effect', '')}", ""]
    if f.get("weaknesses"):
        L += ["## Weaknesses", ""] + [f"- **{w.get('title', '')}**: {w.get('evidence', '')} Impact: {w.get('impact', '')}" for w in f["weaknesses"]] + [""]
    if f.get("bottlenecks"):
        L += ["## Bottlenecks", ""] + [f"- **{b.get('title', '')}**: {b.get('evidence', '')}" for b in f["bottlenecks"]] + [""]
    if f.get("strengths"):
        L += ["## Keep (working well)", ""] + [f"- {x}" for x in f["strengths"]] + [""]
    L += ["## Key numbers", "", md_table(["Metric", "Value"], [
        ["Total cost", money(t["cost"])],
        ["Coordinator / subagents", f'{money(t["coordinator_cost"])} / {money(t["subagent_cost"])}'],
        ["Tickets merged / stopped", f'{t["tickets_merged"]} / {t["tickets_stopped"]}'],
        ["Cost per merged ticket", money(t["cost_per_merged_ticket"])],
        ["Sessions / subagents", f'{t["sessions"]} / {t["subagents"]}'],
        ["Session time span", f'{t["wall_clock_min"]:.0f} min'],
        ["Cache hit ratio", "-" if t["cache_hit_ratio"] is None else f'{t["cache_hit_ratio"]:.1%}'],
        ["Tokens: input / cache read / cache write / output / thinking",
         f'{tok(u["input"])} / {tok(u["cache_read"])} / {tok(u["cache_write_5m"] + u["cache_write_1h"])} / {tok(u["output"])} / {tok(u["thinking"])}'],
        ["User waits / permission prompts / interrupts", f'{t["user_waits"]} / {t["permission_prompts"]} / {t["interrupts"]}'],
        ["Tool errors", t["tool_errors"]],
        ["CI", f'{m["ci"]["runs"]} runs, {m["ci"]["failed"]} failed, {m["ci"]["minutes"]:.0f} min'],
        ["Event appends (with own tool call)", f'{m["event_logging"]["appends"]} ({m["event_logging"]["standalone_appends"]})'],
    ]), ""]
    L += ["## Cost by role", "", md_table(["Role", "Agents", "Cost", "Cache read", "Cache write", "Output"],
          [[k, v["agents"], money(v["cost"]), tok(v["usage"]["cache_read"]), tok(v["usage"]["cache_write_5m"] + v["usage"]["cache_write_1h"]), tok(v["usage"]["output"])]
           for k, v in sorted(m["by_role"].items(), key=lambda kv_: -kv_[1]["cost"])]), ""]
    L += ["## Cost by model", "", md_table(["Model", "Cost"],
          [[k, money(v["cost"])] for k, v in sorted(m["by_model"].items(), key=lambda kv_: -kv_[1]["cost"])]), ""]
    if m.get("tickets"):
        L += ["## Tickets", "", md_table(["Ticket", "Outcome", "Cycle", "Fix rounds", "Findings", "Escalations", "Cost"],
              [[f"#{n}", v["outcome"] + (f' ({v.get("stop_reason")})' if v.get("stop_reason") else ""),
                f'{v["cycle_min"]:.0f} min' if v["cycle_min"] is not None else "-", v["fix_rounds"], kv(v["findings"]),
                v["escalations"], money(v["cost"])] for n, v in m["tickets"].items()]), ""]
    if m.get("agents"):
        L += ["## Subagents", "", md_table(["Agent", "Role", "Ticket", "Model", "Effort", "Calls", "Duration", "Resumes", "Tool errors", "Outcome", "Cost"],
              [[a["agent_id"], a["role"], f'#{a["ticket"]}' if a["ticket"] is not None else "-", a["requested_model"] or "-",
                a.get("effort") or "-", a["api_calls"], f'{a["duration_min"]:.0f} min' if a["duration_min"] is not None else "-",
                a["resumes"], a["tool_errors"], ", ".join(a["outcomes"]) or "-", money(a["cost"])]
               for a in sorted(m["agents"], key=lambda a: -a["cost"])]), ""]
    L += ["## Coordinator sessions", "", md_table(["Session", "Start", "Calls", "Duration", "Max context", "Compactions", "Human msgs", "Permission prompts", "Cost"],
          [[s["session_id"], (s["start"] or "")[:16], s["api_calls"], f'{s["duration_min"] or 0:.0f} min', tok(s["max_context"]),
            s["compactions"], s["human_msgs"], s["permission_prompts"], money(s["cost"])] for s in m["sessions"]]), ""]
    L += ["## Process", "", md_table(["Metric", "Value"], [
        ["Escalations", kv(ev["escalations"])], ["User waits", kv(ev["user_waits"])], ["Review paths", kv(ev["review_paths"])], ["Review skipped because", kv(ev.get("review_skip_reasons"))],
        ["Findings", kv(ev["findings"])], ["Triage", kv(ev.get("triage"))],
        ["Reviewer reject rate", ev.get("reject_rate") if ev.get("reject_rate") is not None else "-"],
        ["Fix rounds by", kv(ev["fix_rounds_by"])], ["Final gates", kv(ev["final_gates"])],
        ["Gate failure causes", kv(ev["final_gate_fail_causes"])], ["Conflicts", kv(ev["conflicts"])],
        ["Spec updates", spec_summary(ev)]]), ""]
    if m["flags"]:
        L += ["## Automatic signals", ""] + [f'- [{x["severity"]}] {x["message"]}' for x in m["flags"]] + [""]
    if m["notes"]:
        L += ["## Data notes", ""] + [f"- {n}" for n in m["notes"]] + [""]
    return "\n".join(L)


def main():
    m = json.load(open(sys.argv[1], encoding="utf-8"))
    f = json.load(open(sys.argv[2], encoding="utf-8"))
    t = m["totals"]
    status, vlabel = VERDICT.get(f.get("verdict"), ("warning", "Mixed"))
    parts = []
    run = (m.get("run_log") or "").replace("\\", "/").split("/")[-1] or "transcripts only"
    parts.append(f'<h1>Coordinator run report</h1><p class="sub">{E(m["repo"])} · {E(run)} · generated {E(m["generated"][:16].replace("T", " "))} UTC</p>')

    tiles = [
        (money(t["cost"]), "Total cost (API-equivalent)"),
        (str(t["tickets_merged"]), "Tickets merged"),
        (str(t["tickets_stopped"]), "Tickets stopped"),
        (money(t["cost_per_merged_ticket"]), "Cost per merged ticket"),
        (f'{t["wall_clock_min"]:.0f} min', "Session time span"),
        (str(t["user_waits"] + t["permission_prompts"] + t["interrupts"]), "Human interruptions"),
        ("—" if t["cache_hit_ratio"] is None else f'{t["cache_hit_ratio"]:.0%}', "Cache hit ratio"),
        (str(t["subagents"]), "Subagents"),
    ]
    parts.append('<div class="tiles">' + "".join(f'<div class="card tile"><div class="v">{E(v)}</div><div class="l">{E(l)}</div></div>' for v, l in tiles) + "</div>")

    # assessment
    parts.append('<h2>Assessment</h2><div class="card">')
    parts.append(f'<span class="verdict"><span class="dot" style="background:{STATUS[status]}"></span>{ICON[status]} {E(vlabel)}</span>')
    parts.append(f'<p>{E(f.get("summary", ""))}</p>')
    if f.get("strengths"):
        parts.append('<h3>Working well</h3><ul class="items">' + "".join(f"<li>{E(s)}</li>" for s in f["strengths"]) + "</ul>")
    parts.append("</div>")
    if f.get("weaknesses") or f.get("bottlenecks"):
        parts.append('<div class="grid2" style="margin-top:12px">')
        if f.get("weaknesses"):
            parts.append('<div class="card"><h3>Weaknesses</h3><ul class="items">' + "".join(
                f'<li><b>{E(w.get("title", ""))}</b><div class="ev">{E(w.get("evidence", ""))}</div><div class="ev">Impact: {E(w.get("impact", ""))}</div></li>'
                for w in f["weaknesses"]) + "</ul></div>")
        if f.get("bottlenecks"):
            parts.append('<div class="card"><h3>Bottlenecks</h3><ul class="items">' + "".join(
                f'<li><b>{E(b.get("title", ""))}</b><div class="ev">{E(b.get("evidence", ""))}</div></li>' for b in f["bottlenecks"]) + "</ul></div>")
        parts.append("</div>")
    if f.get("improvements"):
        order = {"high": 0, "medium": 1, "low": 2}
        prio = {"high": "critical", "medium": "warning", "low": "good"}
        items = "".join(
            f'<div class="imp"><div class="imp-head"><span class="pill"><span class="dot" style="background:{STATUS[prio.get(i.get("priority"), "warning")]}"></span>'
            f'{E(i.get("priority", "?"))}</span><b>{E(i.get("title", ""))}</b></div>'
            f'<p>{E(i.get("change", ""))}</p>'
            f'<dl><dt>Where</dt><dd><code>{E(i.get("where", ""))}</code></dd>'
            f'<dt>Expected effect</dt><dd>{E(i.get("expected_effect", ""))}</dd></dl></div>'
            for i in sorted(f["improvements"], key=lambda i: order.get(i.get("priority"), 3)))
        parts.append(f'<h2>Suggested improvements</h2><div class="card">{items}</div>')

    # cost
    roles = sorted(m["by_role"].items(), key=lambda kv: -kv[1]["cost"])
    models = sorted(m["by_model"].items(), key=lambda kv: -kv[1]["cost"])
    parts.append('<h2>Where the tokens went</h2><div class="grid2">')
    parts.append(f'<div class="card"><h3>Cost by role</h3>{bar_chart([(k, v["cost"]) for k, v in roles])}</div>')
    parts.append(f'<div class="card"><h3>Cost by model</h3>{bar_chart([(k.replace("claude-", ""), v["cost"]) for k, v in models])}</div></div>')
    u = t["usage"]
    parts.append('<div class="card" style="margin-top:12px">' + table(
        ["Role", "Agents", "Cost", "Input", "Cache read", "Cache write", "Output", "Thinking"],
        [[E(k), v["agents"], money(v["cost"]), tok(v["usage"]["input"]), tok(v["usage"]["cache_read"]),
          tok(v["usage"]["cache_write_5m"] + v["usage"]["cache_write_1h"]), tok(v["usage"]["output"]), tok(v["usage"]["thinking"])] for k, v in roles]
        + [["<b>Total</b>", t["subagents"] + t["sessions"], f'<b>{money(t["cost"])}</b>', tok(u["input"]), tok(u["cache_read"]),
            tok(u["cache_write_5m"] + u["cache_write_1h"]), tok(u["output"]), tok(u["thinking"])]],
        num_cols=(1, 2, 3, 4, 5, 6, 7)) + f'<p class="muted">{E(m["pricing_note"])} Thinking "—" means the transcripts do not report it (usually subagents); the total counts only what was reported.</p></div>')

    # tickets
    tickets = m.get("tickets") or {}
    if tickets:
        parts.append('<h2>Tickets</h2><div class="grid2">')
        parts.append(f'<div class="card"><h3>Cost per ticket</h3>{bar_chart([("#" + n, v["cost"]) for n, v in sorted(tickets.items(), key=lambda kv: -kv[1]["cost"])[:15]])}</div>')
        parts.append('<div class="card"><h3>Outcomes</h3>' + table(
            ["Ticket", "Outcome", "Cycle", "Fix rounds", "Findings", "Escal.", "Cost"],
            [["#" + E(n), E(v["outcome"] + (f' ({v.get("stop_reason")})' if v.get("stop_reason") else "")),
              f'{v["cycle_min"]:.0f} min' if v["cycle_min"] is not None else "—", v["fix_rounds"],
              sum(v["findings"].values()), v["escalations"], money(v["cost"])] for n, v in tickets.items()],
            num_cols=(2, 3, 4, 5, 6)) + "</div></div>")

    # subagents
    if m["agents"]:
        parts.append('<h2>Subagents</h2><div class="card">' + table(
            ["Agent", "Role", "Ticket", "Model", "Effort", "Calls", "Duration", "Resumes", "Tool errors", "Outcome", "Cost"],
            [[E(a["agent_id"][:10]), E(a["role"]), "#" + str(a["ticket"]) if a["ticket"] is not None else "—",
              E((a["requested_model"] or "").replace("claude-", "")), E(a.get("effort") or "—"), a["api_calls"],
              f'{a["duration_min"]:.0f} min' if a["duration_min"] is not None else "—", a["resumes"], a["tool_errors"],
              E(", ".join(a["outcomes"]) or "—"), money(a["cost"])] for a in sorted(m["agents"], key=lambda a: -a["cost"])],
            num_cols=(5, 6, 7, 8, 10)) + "</div>")

    # coordinator sessions
    parts.append('<h2>Coordinator sessions</h2>')
    for s in m["sessions"]:
        parts.append(f'<div class="card" style="margin-bottom:12px"><h3>Session {E(s["session_id"][:8])} · {E((s["start"] or "")[:16].replace("T", " "))}</h3>'
                     f'<p class="muted">{s["api_calls"]} API calls · {s["duration_min"] or 0:.0f} min · max context {tok(s["max_context"])} · '
                     f'compactions {s["compactions"]} · human messages {s["human_msgs"]} · permission prompts {s["permission_prompts"]} · '
                     f'interrupts {s["interrupts"]} · cost {money(s["cost"])}</p>'
                     f'<h3>Context size per API call</h3>{line_chart(s["context_series"], "context size per call")}</div>')

    # interruptions & process
    ev = m["events"]
    rows = [[E(x["kind"] or "?"), E(x["resolved_by"] or "?"), x["count"]] for x in ev["escalations"]]
    rows += [["wait: " + E(k or "?"), "user", v] for k, v in ev["user_waits"].items()]
    rows += [["permission prompts", "user", t["permission_prompts"]], ["user interrupts", "user", t["interrupts"]]]
    parts.append('<h2>Interruptions and process</h2><div class="grid2">')
    parts.append('<div class="card"><h3>Interruptions</h3>' + table(["Kind", "Resolved by", "Count"], rows, num_cols=(2,)) + "</div>")
    proc = [["Review path", E(kv(ev["review_paths"]))], ["Review skipped because", E(kv(ev.get("review_skip_reasons")))], ["Findings", E(kv(ev["findings"]))],
            ["Fix rounds by", E(kv(ev["fix_rounds_by"]))], ["Final gates", E(kv(ev["final_gates"]))],
            ["Gate failure causes", E(kv(ev["final_gate_fail_causes"]))],
            ["Conflicts", E(kv(ev["conflicts"]))], ["Spec updates", E(spec_summary(ev))], ["Tool errors", t["tool_errors"]],
            ["CI", E(f'{m["ci"]["runs"]} runs, {m["ci"]["failed"]} failed, {m["ci"]["minutes"]:.0f} min waiting')],
            ["Event appends", E(f'{m["event_logging"]["appends"]} ({m["event_logging"]["standalone_appends"]} with their own tool call)')]]
    parts.append('<div class="card"><h3>Process</h3>' + table(["Metric", "Value"], proc) + "</div></div>")

    # flags & notes
    if m["flags"]:
        parts.append('<h2>Automatic signals</h2><div class="card">' + "".join(
            f'<div class="flag"><span class="dot" style="background:{STATUS.get(x["severity"], "var(--warning)")}"></span>'
            f'<span class="lbl">{ICON.get(x["severity"], "!")} {E(x["severity"])}</span><span>{E(x["message"])}</span></div>' for x in m["flags"]) + "</div>")
    if m["notes"]:
        parts.append('<h2>Data notes</h2><div class="card"><ul class="items">' + "".join(f"<li>{E(n)}</li>" for n in m["notes"]) + "</ul></div>")

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Coordinator Run Report</title><style>{CSS}</style></head>
<body><div class="viz-root"><main>{"".join(parts)}</main></div></body></html>"""
    with open(sys.argv[3], "w", encoding="utf-8") as fh:
        fh.write(page)
    md_path = sys.argv[3][:-5] + ".md" if sys.argv[3].endswith(".html") else sys.argv[3] + ".md"
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(markdown(m, f, sys.argv[3]))
    print(sys.argv[3])
    print(md_path)


if __name__ == "__main__":
    main()
