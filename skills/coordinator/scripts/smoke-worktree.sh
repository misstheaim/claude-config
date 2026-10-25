#!/usr/bin/env bash
# Prepare the coordinator's smoke worktree: <main checkout>/.claude/worktrees/smoke, detached at origin/<base>,
# and the wave's own harness folder; afterwards, verify the boundary and archive that folder.
#
# Usage: smoke-worktree.sh --base BRANCH --wave N [--repo-dir PATH]
#        smoke-worktree.sh --finish --wave N --result pass|fail [--repo-dir PATH]
#
# Prepare creates the worktree on first use and resets it on later waves. Tracked files go back to origin/<base>;
# untracked and ignored files (node_modules, build output) stay, so later waves start faster. It also records
# a fingerprint of the main checkout's state, so --finish can check that the agent didn't change anything there.
#
# Harness layout (<git-common-dir>/coordinator/, never committed, shared by every worktree):
#   smoke-harness/lib/       shared helpers (launch the product, temp HOME); the agent may update them
#   smoke-harness/wave-<N>/  this wave's checks; the agent writes only here and in lib/
#   smoke-archive/wave-<N>/  finished waves, moved here by --finish with a RESULT file; never re-run or edited
# Prepare also archives leftovers: wave folders of unfinished waves (RESULT: unfinished) and files of the older
# single-folder harness (smoke-archive/legacy/).
#
# Prepare prints, on success:
#   SMOKE_WORKTREE=<path>
#   SMOKE_HARNESS=<git-common-dir>/coordinator/smoke-harness
#   SMOKE_WAVE_DIR=<harness>/wave-<N>
#   SMOKE_AT=<commit under test>
# --finish prints "MAIN_CHECKOUT: unchanged" or a list of what changed (exit 1), then "ARCHIVED=<path>". It archives
# either way; a CHANGED boundary is recorded in RESULT.
set -uo pipefail

BASE="" DIR="." WAVE="" RESULT="" FINISH=0
while [ $# -gt 0 ]; do
  case "$1" in
    --base) BASE="$2"; shift 2 ;;
    --repo-dir) DIR="$2"; shift 2 ;;
    --wave) WAVE="$2"; shift 2 ;;
    --result) RESULT="$2"; shift 2 ;;
    --finish) FINISH=1; shift ;;
    *) echo "unknown argument: $1"; exit 2 ;;
  esac
done
[ -n "$WAVE" ] || { echo "required: --wave"; exit 2; }

COMMON=$(cd "$DIR" && cd "$(git rev-parse --git-common-dir)" && pwd) || { echo "not a git repo: $DIR"; exit 2; }
MAIN=$(dirname "$COMMON")
STATE="$COMMON/coordinator/smoke-main-state.txt"
HARNESS="$COMMON/coordinator/smoke-harness"
ARCHIVE="$COMMON/coordinator/smoke-archive"
WT="$MAIN/.claude/worktrees/smoke"
fingerprint() { git -C "$MAIN" rev-parse HEAD; git -C "$MAIN" status --porcelain; }
# archive <wave dir> <result line>: move it to smoke-archive/ (a re-run wave gets a numbered suffix) with a RESULT file
archive() {
  local src="$1" dest="$ARCHIVE/$(basename "$1")" i=2
  while [ -e "$dest" ]; do dest="$ARCHIVE/$(basename "$src")-$i"; i=$((i + 1)); done
  mkdir -p "$ARCHIVE" && mv "$src" "$dest" && printf '%s\n' "$2" > "$dest/RESULT" && echo "ARCHIVED=$dest"
}

if [ $FINISH -eq 1 ]; then
  case "$RESULT" in pass|fail) ;; *) echo "required: --result pass|fail"; exit 2 ;; esac
  [ -f "$STATE" ] || { echo "MAIN_CHECKOUT: no fingerprint recorded"; exit 2; }
  BOUNDARY=unchanged CODE=0
  if diff -q "$STATE" <(fingerprint) >/dev/null; then
    echo "MAIN_CHECKOUT: unchanged"
  else
    echo "MAIN_CHECKOUT: CHANGED during the smoke check:"
    diff "$STATE" <(fingerprint) | sed 's/^/  /'
    BOUNDARY=CHANGED CODE=1
  fi
  if [ -d "$HARNESS/wave-$WAVE" ]; then
    archive "$HARNESS/wave-$WAVE" "result=$RESULT commit=$(git -C "$WT" rev-parse --short HEAD 2>/dev/null) main_checkout=$BOUNDARY date=$(date +%F)"
  else
    echo "no $HARNESS/wave-$WAVE to archive"
  fi
  exit $CODE
fi

[ -n "$BASE" ] || { echo "required: --base"; exit 2; }
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
mkdir -p "$HARNESS/lib"
# Leftovers: other waves' folders were never finished; anything else is the older single-folder harness.
for f in "$HARNESS"/* "$HARNESS"/.[!.]*; do
  [ -e "$f" ] || continue
  case "$(basename "$f")" in
    lib|"wave-$WAVE") ;;
    wave-*) archive "$f" "result=unfinished date=$(date +%F)" ;;
    *) mkdir -p "$ARCHIVE/legacy" && mv "$f" "$ARCHIVE/legacy/" && echo "moved old harness file to $ARCHIVE/legacy/$(basename "$f")" ;;
  esac
done
mkdir -p "$HARNESS/wave-$WAVE"
fingerprint > "$STATE"
echo "SMOKE_WORKTREE=$WT"
echo "SMOKE_HARNESS=$HARNESS"
echo "SMOKE_WAVE_DIR=$HARNESS/wave-$WAVE"
echo "SMOKE_AT=$(git -C "$WT" rev-parse --short HEAD)"
