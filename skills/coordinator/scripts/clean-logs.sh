#!/usr/bin/env bash
# Delete the coordinator's working files in <git-common-dir>/coordinator/logs/ at a session's handoff or the run's end.
#
# Usage: clean-logs.sh [--keep N,M,...] [--repo-dir PATH]
#
# The folder holds files that matter only while a ticket is in flight: PR and issue bodies, ship.sh's commit and gate
# logs and gate-pass stamps, the baseline log, one-off helper files. Nothing reads them after the PR merges.
# --keep: tickets still in flight (stopped, or waiting on the user); their files stay, i.e. every file whose name has
#   the number as a whole token (pr-72.md, ship-72-build.log, c72.md). Everything else is deleted.
# Without --keep (the run is finished) the folder is emptied.
# Prints "LOGS: deleted <k>, kept <m>".
set -uo pipefail

DIR="." KEEP=""
while [ $# -gt 0 ]; do
  case "$1" in
    --keep) KEEP="$2"; shift 2 ;;
    --repo-dir) DIR="$2"; shift 2 ;;
    *) echo "unknown argument: $1"; exit 2 ;;
  esac
done
case "$KEEP" in ''|[0-9]*) ;; *) echo "bad --keep: $KEEP (issue numbers, comma-separated)"; exit 2 ;; esac

COMMON=$(cd "$DIR" && cd "$(git rev-parse --git-common-dir)" && pwd) || { echo "not a git repo: $DIR"; exit 2; }
LOGS="$COMMON/coordinator/logs"
[ -d "$LOGS" ] || { echo "LOGS: deleted 0, kept 0"; exit 0; }

# a number as a whole token in the file name: not preceded or followed by another digit
keep_re=""
[ -z "$KEEP" ] || keep_re="(^|[^0-9])($(printf '%s' "$KEEP" | tr -d ' ' | tr ',' '|'))([^0-9]|$)"
deleted=0 kept=0
for f in "$LOGS"/* "$LOGS"/.[!.]*; do
  [ -e "$f" ] || continue
  if [ -n "$keep_re" ] && basename "$f" | grep -qE "$keep_re"; then
    kept=$((kept + 1))
  else
    rm -rf "$f" && deleted=$((deleted + 1))
  fi
done
echo "LOGS: deleted $deleted, kept $kept"
