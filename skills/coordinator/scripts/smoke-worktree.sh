#!/usr/bin/env bash
# Prepare the coordinator's smoke worktree: <main checkout>/.claude/worktrees/smoke, detached at origin/<base>.
#
# Usage: smoke-worktree.sh --base BRANCH [--repo-dir PATH]
#
# Creates the worktree on first use and resets it on later waves. Tracked files go back to origin/<base>;
# untracked and ignored files (node_modules, build output) stay, so later waves start faster. It also records
# a fingerprint of the main checkout's state, so the coordinator can check after the smoke check that the
# agent didn't change anything there (smoke-worktree.sh --verify).
#
# Prints, on success:
#   SMOKE_WORKTREE=<path>
#   SMOKE_HARNESS=<git-common-dir>/coordinator/smoke-harness
# Usage for the check afterwards: smoke-worktree.sh --verify [--repo-dir PATH]  ->  "MAIN_CHECKOUT: unchanged" or a
# list of what changed (exit 1).
set -uo pipefail

BASE="" DIR="." VERIFY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --base) BASE="$2"; shift 2 ;;
    --repo-dir) DIR="$2"; shift 2 ;;
    --verify) VERIFY=1; shift ;;
    *) echo "unknown argument: $1"; exit 2 ;;
  esac
done

COMMON=$(cd "$DIR" && cd "$(git rev-parse --git-common-dir)" && pwd) || { echo "not a git repo: $DIR"; exit 2; }
MAIN=$(dirname "$COMMON")
STATE="$COMMON/coordinator/smoke-main-state.txt"
fingerprint() { git -C "$MAIN" rev-parse HEAD; git -C "$MAIN" status --porcelain; }

if [ $VERIFY -eq 1 ]; then
  [ -f "$STATE" ] || { echo "MAIN_CHECKOUT: no fingerprint recorded"; exit 2; }
  if diff -q "$STATE" <(fingerprint) >/dev/null; then
    echo "MAIN_CHECKOUT: unchanged"
  else
    echo "MAIN_CHECKOUT: CHANGED during the smoke check:"
    diff "$STATE" <(fingerprint) | sed 's/^/  /'
    exit 1
  fi
  exit 0
fi

[ -n "$BASE" ] || { echo "required: --base"; exit 2; }
WT="$MAIN/.claude/worktrees/smoke"
# The smoke worktree persists between waves; keep it (and agent worktrees) out of the main checkout's status,
# or the next preflight sees an untracked .claude/ and the base no longer looks clean. Local only, never committed.
if ! git -C "$MAIN" check-ignore -q .claude/worktrees/smoke/x; then
  mkdir -p "$COMMON/info" && printf '%s\n' '.claude/worktrees/' >> "$COMMON/info/exclude"
  echo "added .claude/worktrees/ to $COMMON/info/exclude"
fi
git -C "$MAIN" fetch -q origin "$BASE" || { echo "git fetch origin $BASE failed"; exit 2; }
if [ -e "$WT/.git" ]; then
  git -C "$WT" reset -q --hard && git -C "$WT" checkout -q --detach "origin/$BASE" || { echo "could not reset $WT"; exit 2; }
else
  git -C "$MAIN" worktree prune
  git -C "$MAIN" worktree add -q --detach "$WT" "origin/$BASE" || { echo "could not create $WT"; exit 2; }
fi
mkdir -p "$COMMON/coordinator/smoke-harness"
fingerprint > "$STATE"
echo "SMOKE_WORKTREE=$WT"
echo "SMOKE_HARNESS=$COMMON/coordinator/smoke-harness"
echo "SMOKE_AT=$(git -C "$WT" rev-parse --short HEAD)"
