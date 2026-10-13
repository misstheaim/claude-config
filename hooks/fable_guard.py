"""PreToolUse hook: require the user's explicit permission before anything runs on the Fable model.

Checks Agent calls (the `model` parameter, or a custom agent whose definition sets a Fable model)
and Bash commands that launch `claude` with a Fable model. Prints an "ask" decision when one is found.
"""
import json
import os
import re
import sys

FABLE = re.compile(r"\bfable\b|claude-fable", re.IGNORECASE)


def agent_definition_model(agent_type, cwd):
    """Return the `model` frontmatter of a custom agent definition, if one exists."""
    dirs = [os.path.join(os.path.expanduser("~"), ".claude", "agents")]
    if cwd:
        dirs.append(os.path.join(cwd, ".claude", "agents"))
    for base in dirs:
        for root, _, files in os.walk(base):
            for name in files:
                if not name.endswith(".md"):
                    continue
                try:
                    with open(os.path.join(root, name), encoding="utf-8") as f:
                        text = f.read(4000)
                except OSError:
                    continue
                front = text.split("---")[1] if text.startswith("---") else ""
                if re.search(r"^name:\s*" + re.escape(agent_type) + r"\s*$", front, re.MULTILINE):
                    m = re.search(r"^model:\s*(\S+)", front, re.MULTILINE)
                    return m.group(1) if m else None
    return None


def reason_for(data):
    tool = data.get("tool_name", "")
    inp = data.get("tool_input") or {}
    if tool == "Agent":
        model = str(inp.get("model") or "")
        if FABLE.search(model):
            return f"Agent call requests the Fable model ({model})."
        agent_type = inp.get("subagent_type")
        if not model and agent_type:
            defined = agent_definition_model(agent_type, data.get("cwd"))
            if defined and FABLE.search(defined):
                return f"Agent '{agent_type}' is defined with the Fable model ({defined})."
    elif tool in ("Bash", "PowerShell"):
        cmd = str(inp.get("command") or "")
        if re.search(r"\bclaude\b", cmd) and re.search(r"(--model|-m)[\s=]+\S*fable", cmd, re.IGNORECASE):
            return "Command launches Claude with the Fable model."
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    reason = reason_for(data)
    if reason:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": reason + " Fable needs the user's explicit permission.",
            }
        }))


if __name__ == "__main__":
    main()
