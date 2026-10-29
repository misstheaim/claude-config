"""PreToolUse hook for the guide-me skill: the user writes the code, Claude doesn't.

- Edit/Write: allowed only for documentation files (.md, .txt, ...), e.g. plans, specs, READMEs, CLAUDE.md.
- NotebookEdit: always blocked (notebooks are code).
- Bash/PowerShell: allowed for diagnosis and git, but commands that write or change files are blocked:
  output redirection, file-writing commands, in-place editors, inline interpreters, code generators,
  formatters, dependency adds, and git commands that apply patches or rewrite the working tree.

This is a best-effort denylist, not a sandbox. It blocks with exit code 2 and a reason on stderr.
"""
import json
import os
import re
import sys

DOC_EXTENSIONS = {".md", ".markdown", ".txt", ".rst", ".adoc", ".asciidoc", ".org"}
DOC_NAMES = {"license", "notice", "authors", "contributors", "copying", "changelog"}

# A command name at the start of a command: line start, after ; & | ( ` or a prefix word.
CMD = r"(?:^|[;&|(`\n{]|\b(?:xargs|sudo|exec|then|do|else|time|nohup|env|command))\s*"

BASH_RULES = [
    (CMD + r"(?:tee|cp|mv|rm|ln|touch|dd|truncate|install|patch|unzip|tar)(?=\s|$)", "writes, moves or deletes files"),
    (r"\bsed\b[^;&|\n]*\s(?:-[a-zA-Z]*i|--in-place)", "edits files in place"),
    (r"\bperl\b[^;&|\n]*\s-[a-zA-Z]*i", "edits files in place"),
    (r"\bawk\b[^;&|\n]*-i\s*inplace", "edits files in place"),
    (r"\b(?:python3?|py|node|deno|bun|ruby|perl|php)\b[^;&|\n]*\s(?:-c|-e|-p|-r|--eval|--print|eval)(?=\s|$)", "runs inline code that can write files"),
    (r"\b(?:bash|sh|zsh|pwsh|powershell)\b[^;&|\n]*\s-(?:c|command|encodedcommand)\b", "runs a nested shell"),
    (r"\bcmd(?:\.exe)?\s+/c\b", "runs a nested shell"),
    (CMD + r"eval(?=\s|$)", "runs generated code"),
    (r"(?:^|\s)--(?:fix|write)(?=\s|=|$)", "rewrites source files"),
    (r"\b(?:prettier|black|isort|autopep8|gofmt|rustfmt|clang-format)\b", "rewrites source files"),
    (r"\b(?:cargo|go)\s+fmt\b|\bruff\s+format\b|\bdotnet\s+format\b", "rewrites source files"),
    (r"\bdotnet\s+(?:new|add|remove)\b|\bmigrations\s+add\b|\bscaffold\b", "generates or changes project code"),
    (r"\b(?:rails|ng|nest)\s+(?:g|generate|new)\b|\bcreate-[\w-]+|\bnpm\s+init\b|\byarn\s+create\b", "generates project code"),
    (r"\b(?:npm|pnpm|yarn|bun)\s+(?:add|remove|uninstall|rm|un|i|install)\s+(?:-\S+\s+)*[^-\s]", "changes the project's dependencies"),
    (r"\b(?:cargo|poetry|uv|composer)\s+(?:add|remove|require)\b|\bgo\s+get\b", "changes the project's dependencies"),
    (r"\bgit\s+(?:apply|am|restore|clean)\b", "changes files in the working tree"),
    (r"\bgit\s+checkout\b[^;&|\n]*\s--(?:\s|$)|\bgit\s+checkout\s+\.(?:\s|$)", "changes files in the working tree"),
    (r"\bgit\s+reset\b[^;&|\n]*--hard\b|\bgit\s+stash\b", "changes files in the working tree"),
]

POWERSHELL_RULES = [
    (r"\b(?:Set-Content|Add-Content|Out-File|Clear-Content|New-Item|Copy-Item|Move-Item|Remove-Item|Rename-Item|Expand-Archive|Invoke-Expression)\b",
     "writes, moves or deletes files"),
    (CMD + r"(?:sc|ac|ni|cp|cpi|copy|mv|mi|move|rm|ri|del|erase|rmdir|rd|ren|rni|clc|iex)(?=\s|$)", "writes, moves or deletes files"),
    (r"\[(?:System\.)?IO\.(?:File|Directory)\]::|\.Write(?:AllText|AllLines|AllBytes)\b|\bStreamWriter\b|-OutFile\b",
     "writes files"),
]

NULL_TARGETS = {"/dev/null", "$null", "nul"}


def strip_quotes(cmd):
    """Replace quoted strings with a placeholder so their content isn't mistaken for syntax."""
    return re.sub(r"'[^']*'|\"(?:\\.|[^\"\\])*\"", "Q", cmd)


def redirect_reason(cmd):
    for m in re.finditer(r">>?(?!&)\s*([^\s;&|)]*)", strip_quotes(cmd)):
        if m.group(1).lower() not in NULL_TARGETS:
            return "redirects output into a file"
    return None


def command_reason(tool, cmd):
    rules = BASH_RULES + (POWERSHELL_RULES if tool == "PowerShell" else [])
    flags = re.IGNORECASE | re.MULTILINE
    for pattern, why in rules:
        if re.search(pattern, cmd, flags):
            return why
    return redirect_reason(cmd)


def is_doc_file(path):
    name = os.path.basename(path.replace("\\", "/")).lower()
    stem, ext = os.path.splitext(name)
    return ext in DOC_EXTENSIONS or (not ext and stem in DOC_NAMES)


def block_reason(data):
    tool = data.get("tool_name", "")
    inp = data.get("tool_input") or {}
    if tool in ("Edit", "Write"):
        path = str(inp.get("file_path") or "")
        if not is_doc_file(path):
            return (f"guide-me mode is on: you may only edit documentation files (.md, .txt, ...), not {path}. "
                    "Tell the user which file to open and what to change.")
    elif tool == "NotebookEdit":
        return "guide-me mode is on: you must not edit notebooks. Tell the user which cell to change and how."
    elif tool in ("Bash", "PowerShell"):
        cmd = str(inp.get("command") or "")
        why = command_reason(tool, cmd)
        if why:
            return (f"guide-me mode is on: this command {why}, and the user writes the code. "
                    "Tell the user which command to run and why. Edit documentation files with Edit/Write instead.")
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    reason = block_reason(data)
    if reason:
        print(reason, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
