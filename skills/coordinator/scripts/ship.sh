#!/usr/bin/env bash
# Ship one coordinator ticket: commit -> update onto the base -> final gate -> push -> PR -> CI -> merge -> clean up.
#
# Usage:
#   ship.sh --worktree PATH --ticket N --base BRANCH --title "PR title" --body-file FILE \
#           --gate build="npm --prefix extension run build" --gate lint="cd helper && golangci-lint run" \
#           [--message "feat(#N): summary"] [--repo OWNER/REPO] [--merge-method squash|merge|rebase] \
#           [--events FILE] [--runlog FILE] [--logdir DIR] [--ci-register-timeout SEC] [--budget SEC] [--no-merge] [--no-close]
#
# --no-close: merge but leave the issue open (a "Refs #N" PR, e.g. a plan update for a ticket that isn't done).
#
# Idempotent: re-run it after a fix round, a conflict resolution, a CI timeout or a killed run and it picks up
# where it stopped (an existing commit, pushed branch, open PR or already merged PR is reused).
# Run it from the main checkout, not from the worktree.
#
# Time: the whole run stays within --budget seconds (default 540), under the Bash tool's 600 s limit. Waiting for
# CI stops at the budget with exit 22; nothing is half done then, so a re-run just keeps waiting.
#
# Exit codes (the last line printed is always "RESULT: <code> <word> ..."):
#   0  merged             PR merged, local base fast-forwarded, worktree removed (or reported busy)
#   2  usage              bad arguments, or nothing to ship
#   3  conflict           rebase/merge onto origin/<base> stopped on conflicts; left in progress in the worktree
#   10 gate-failed        a gate command failed, or git isn't clean after the commit (cause: gate name or "dirty")
#   11 commit-failed      git add/commit failed (a git or setup problem, not the code); its output is printed
#   20 ci-failed          a CI check failed
#   21 ci-not-registered  the repo has workflows but no check appeared on the PR in time
#   22 ci-timeout         checks still running when the budget ran out; re-run to keep waiting
#   30 merge-failed       gh pr merge refused (e.g. GitHub sees a conflict)
#   40 ready              --no-merge: PR is green and waits for the user's approval
set -uo pipefail

die() { echo "RESULT: $1 $2${3:+ $3}"; exit "$1"; }
log() { echo "ship: $*"; }

WT="" TICKET="" BASE="" TITLE="" BODY="" MSG="" REPO="" METHOD="squash" EVENTS="" RUNLOG="" LOGDIR=""
REG_TIMEOUT=120 BUDGET=540 NO_MERGE=0 NO_CLOSE=0
GATES=()
while [ $# -gt 0 ]; do
  case "$1" in
    --worktree) WT="$2"; shift 2 ;;
    --ticket) TICKET="$2"; shift 2 ;;
    --base) BASE="$2"; shift 2 ;;
    --title) TITLE="$2"; shift 2 ;;
    --body-file) BODY="$2"; shift 2 ;;
    --message) MSG="$2"; shift 2 ;;
    --repo) REPO="$2"; shift 2 ;;
    --merge-method) METHOD="$2"; shift 2 ;;
    --gate) GATES+=("$2"); shift 2 ;;
    --events) EVENTS="$2"; shift 2 ;;
    --runlog) RUNLOG="$2"; shift 2 ;;
    --logdir) LOGDIR="$2"; shift 2 ;;
    --ci-register-timeout) REG_TIMEOUT="$2"; shift 2 ;;
    --budget) BUDGET="$2"; shift 2 ;;
    --no-merge) NO_MERGE=1; shift ;;
    --no-close) NO_CLOSE=1; shift ;;
    *) die 2 usage "unknown argument: $1" ;;
  esac
done
[ -n "$WT" ] && [ -n "$TICKET" ] && [ -n "$BASE" ] && [ -n "$TITLE" ] && [ -n "$BODY" ] && [ ${#GATES[@]} -gt 0 ] \
  || die 2 usage "required: --worktree --ticket --base --title --body-file and at least one --gate"
[ -d "$WT" ] || die 2 usage "worktree not found: $WT"
[ -f "$BODY" ] || die 2 usage "body file not found: $BODY"
case "$METHOD" in squash|merge|rebase) ;; *) die 2 usage "bad --merge-method: $METHOD" ;; esac

g() { git -C "$WT" "$@"; }
[ -n "$REPO" ] || REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner) || die 2 usage "can't resolve the repo"
COMMON=$(cd "$WT" && cd "$(git rev-parse --git-common-dir)" && pwd)
MAIN=$(dirname "$COMMON")
[ -n "$LOGDIR" ] || LOGDIR="$COMMON/coordinator/logs"
mkdir -p "$LOGDIR"
BR=$(g symbolic-ref --short HEAD) || die 2 usage "worktree is on a detached HEAD"
[ "$BR" != "$BASE" ] || die 2 usage "worktree is on the base branch itself"
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
left() { echo $((BUDGET - SECONDS)); }  # seconds left of the budget (SECONDS counts from the script's start)
event() { [ -z "$EVENTS" ] || printf '%s\n' "$1" >> "$EVENTS"; }
gate_event() { # result cause
  if [ "$1" = pass ]; then event "{\"ts\":\"$(now)\",\"event\":\"final_gate\",\"ticket\":$TICKET,\"result\":\"pass\",\"cause\":null}"
  else event "{\"ts\":\"$(now)\",\"event\":\"final_gate\",\"ticket\":$TICKET,\"result\":\"fail\",\"cause\":\"$2\"}"; fi
}

# Is the process with this (OS-level) pid still running? On Windows the lock holds a Windows pid, which
# Git Bash's kill can't see, so ask tasklist there.
pid_alive() { # pid
  if command -v tasklist >/dev/null 2>&1; then
    MSYS_NO_PATHCONV=1 tasklist /FI "PID eq $1" /NH 2>/dev/null | grep -qw "$1"
  else
    kill -0 "$1" 2>/dev/null
  fi
}

# Remove the merged ticket's worktree and local branch; prints what happened. Claude Code locks the worktrees
# of isolated agents ("claude agent <id> (pid N)"), and a plain remove refuses a locked one: unlock it only when
# that process has exited. A folder that Windows keeps busy (a process has it open) is left behind once git's
# record of it is pruned.
remove_worktree() {
  local reason pid
  if git -C "$MAIN" worktree remove --force "$WT" 2>/dev/null; then
    git -C "$MAIN" branch -q -D "$BR" 2>/dev/null || true
    echo "worktree removed"; return
  fi
  reason=$(git -C "$WT" rev-parse --git-dir 2>/dev/null | xargs -I{} cat "{}/locked" 2>/dev/null)
  if [ -n "$reason" ]; then
    pid=$(printf '%s' "$reason" | sed -n 's/.*pid \([0-9][0-9]*\).*/\1/p')
    if [ -z "$pid" ] || pid_alive "$pid"; then
      rm -f "$WT/.scratch/ticket-notes.md"
      echo "worktree locked ($reason; holder alive or unknown), remove later: $WT (ticket notes deleted)"; return
    fi
    git -C "$MAIN" worktree unlock "$WT" 2>/dev/null
    if git -C "$MAIN" worktree remove --force "$WT" 2>/dev/null; then
      git -C "$MAIN" branch -q -D "$BR" 2>/dev/null || true
      echo "worktree removed (stale lock of pid $pid cleared)"; return
    fi
  fi
  # Remove failed part-way (files in use): drop git's record if the folder is no longer a worktree.
  git -C "$MAIN" worktree prune 2>/dev/null
  if git -C "$MAIN" worktree list --porcelain | grep -qxF "worktree $(cd "$WT" 2>/dev/null && pwd -W 2>/dev/null || echo "$WT")"; then
    rm -f "$WT/.scratch/ticket-notes.md"
    echo "worktree busy, remove later: $WT (ticket notes deleted)"
  else
    git -C "$MAIN" branch -q -D "$BR" 2>/dev/null || true
    echo "worktree record pruned and branch deleted; folder busy, delete later: $WT"
  fi
}

# After the merge: delete the remote branch, fast-forward the local base, remove the worktree, close the issue.
cleanup_after_merge() { # pr
  local pr="$1" clean="worktree removed" state
  git -C "$MAIN" push -q origin --delete "$BR" 2>/dev/null || true
  git -C "$MAIN" fetch -q origin "$BASE"
  if [ "$(git -C "$MAIN" symbolic-ref --short HEAD 2>/dev/null)" = "$BASE" ]; then
    git -C "$MAIN" merge -q --ff-only "origin/$BASE" || log "WARNING: local $BASE did not fast-forward"
  else
    git -C "$MAIN" fetch -q origin "$BASE:$BASE" 2>/dev/null || log "WARNING: local $BASE did not fast-forward"
  fi
  clean=$(remove_worktree)
  state=$(gh issue view "$TICKET" -R "$REPO" --json state -q .state 2>/dev/null)
  if [ "$state" = "OPEN" ] && [ $NO_CLOSE -eq 0 ]; then
    gh issue close "$TICKET" -R "$REPO" -c "Done in PR #$pr" >/dev/null 2>&1 && log "closed issue #$TICKET"
  fi
  [ -z "$RUNLOG" ] || printf '%s\n' "- #$TICKET | DONE: PR #$pr merged ($(now)). $clean" >> "$RUNLOG"
  log "$clean"
  die 0 merged "#$TICKET -> PR #$pr"
}

# 0. A previous run may have merged and then been killed before cleaning up: finish only the cleanup.
MERGED_PR=$(gh pr list -R "$REPO" --head "$BR" --state merged --json number -q '.[0].number' 2>/dev/null)
if [ -n "$MERGED_PR" ]; then
  [ -z "$(g status --porcelain)" ] || die 2 usage "PR #$MERGED_PR for $BR is already merged, but the worktree has new changes: ship them on a new branch"
  log "PR #$MERGED_PR is already merged; finishing the cleanup"
  cleanup_after_merge "$MERGED_PR"
fi

# 1. In-progress rebase or merge from an earlier run: the coordinator resolves it first (SKILL.md section 7).
gdir=$(g rev-parse --git-dir)
case "$gdir" in /*|?:*) ;; *) gdir="$WT/$gdir" ;; esac
if [ -d "$gdir/rebase-merge" ] || [ -d "$gdir/rebase-apply" ] || [ -f "$gdir/MERGE_HEAD" ]; then
  die 3 conflict "a rebase or merge is still in progress in $WT: $(g diff --name-only --diff-filter=U | tr '\n' ' ')"
fi

# 2. Commit the ticket's changes.
if [ -n "$(g status --porcelain)" ]; then
  [ -n "$MSG" ] || die 2 usage "uncommitted changes and no --message"
  # .scratch/ holds agent logs and ticket notes: never part of a commit, even if it isn't ignored.
  # When it is ignored, git add rejects the exclude pathspec (exit 1), so only pass it when needed.
  lf="$LOGDIR/ship-$TICKET-commit.log"
  pathspec=(-- .)
  g check-ignore -q .scratch/x || pathspec+=(':(exclude).scratch')
  { g add -A "${pathspec[@]}" && g commit -q -m "$MSG"; } >"$lf" 2>&1
  rc=$?
  if [ $rc -ne 0 ]; then
    gate_event fail commit
    echo "--- git add/commit exited $rc; output ($lf):"; tail -n 30 "$lf"
    die 11 commit-failed "git add/commit exited $rc (log: $lf); nothing to fix in the code"
  fi
  log "committed: $(g log -1 --format='%h %s')"
fi

# 3. Bring the branch up to date with origin/<base>: rebase while unpushed, merge once pushed (never force-push).
g fetch -q origin "$BASE" || die 2 usage "git fetch origin $BASE failed"
[ "$(g rev-list --count "origin/$BASE..HEAD")" -gt 0 ] || die 2 usage "nothing to ship: no commits ahead of origin/$BASE"
PUSHED=0
git -C "$WT" ls-remote --exit-code --heads origin "$BR" >/dev/null 2>&1 && PUSHED=1
if [ "$(g rev-list --count "HEAD..origin/$BASE")" -gt 0 ]; then
  if [ $PUSHED -eq 0 ]; then
    g rebase -q "origin/$BASE" >/dev/null 2>&1 || die 3 conflict "rebase onto origin/$BASE stopped: $(g diff --name-only --diff-filter=U | tr '\n' ' ')"
    log "rebased onto origin/$BASE"
  else
    g merge -q --no-edit "origin/$BASE" >/dev/null 2>&1 || die 3 conflict "merge of origin/$BASE stopped: $(g diff --name-only --diff-filter=U | tr '\n' ' ')"
    log "merged origin/$BASE into $BR"
  fi
fi
echo "ship: files in this change (vs origin/$BASE):"
g diff --name-status "origin/$BASE...HEAD" | head -n 40 | sed 's/^/  /'

# 4. Final gate: every gate command from the worktree root, output to a log; then git must be clean.
for spec in "${GATES[@]}"; do
  name="${spec%%=*}"; cmd="${spec#*=}"
  lf="$LOGDIR/ship-$TICKET-$name.log"
  if ! (cd "$WT" && bash -c "$cmd") >"$lf" 2>&1; then
    gate_event fail "$name"
    echo "--- last 30 lines of $lf"; tail -n 30 "$lf"
    die 10 gate-failed "$name (log: $lf)"
  fi
  log "gate $name: pass"
done
if [ -n "$(g status --porcelain)" ]; then
  gate_event fail dirty
  g status --porcelain | head -20
  die 10 gate-failed "dirty: the gate left changes in the worktree"
fi
gate_event pass

# 5. Push and open the PR (or reuse the open one).
g push -q -u origin "$BR" 2>/dev/null || die 2 usage "git push failed"
PR=$(gh pr list -R "$REPO" --head "$BR" --state open --json number -q '.[0].number')
if [ -z "$PR" ]; then
  url=$(gh pr create -R "$REPO" --base "$BASE" --head "$BR" --title "$TITLE" --body-file "$BODY") || die 2 usage "gh pr create failed"
  PR="${url##*/}"
  log "opened PR #$PR"
else
  log "reusing PR #$PR"
fi

# 6. CI: wait until checks are registered AND all passed. "No checks" is never treated as green while workflows exist.
HAS_CI=0
[ -n "$(g ls-tree --name-only "origin/$BASE" .github/workflows/ 2>/dev/null)" ] && HAS_CI=1
if [ $HAS_CI -eq 1 ]; then
  waited=0
  while :; do
    # gh exits non-zero while checks are pending or absent; only the printed count matters
    n=$(gh pr checks "$PR" -R "$REPO" --json name -q 'length' 2>/dev/null | head -n 1)
    case "$n" in ''|*[!0-9]*) n=0 ;; esac
    [ "$n" -gt 0 ] && break
    [ $waited -ge "$REG_TIMEOUT" ] && die 21 ci-not-registered "PR #$PR has no checks after ${REG_TIMEOUT}s"
    [ "$(left)" -le 40 ] && die 22 ci-timeout "PR #$PR: time budget used up while waiting for checks to appear; re-run"
    sleep 10; waited=$((waited + 10))
  done
  while :; do
    buckets=$(gh pr checks "$PR" -R "$REPO" --json bucket -q '.[].bucket' 2>/dev/null)
    if echo "$buckets" | grep -qE '^(fail|cancel)$'; then
      gh pr checks "$PR" -R "$REPO" --json name,bucket,link -q '.[] | select(.bucket=="fail" or .bucket=="cancel") | "\(.name): \(.link)"'
      die 20 ci-failed "PR #$PR"
    fi
    echo "$buckets" | grep -q '^pending$' || break
    # keep about 40 s for the merge and the cleanup
    [ "$(left)" -le 40 ] && die 22 ci-timeout "PR #$PR checks still running after ${SECONDS}s; re-run to keep waiting"
    sleep 15
  done
  log "CI: $(echo "$buckets" | grep -c '^pass$') passed"
else
  log "CI: no workflows on origin/$BASE, skipped"
fi

if [ $NO_MERGE -eq 1 ]; then
  die 40 ready "PR #$PR is green and waits for approval: $(gh pr view "$PR" -R "$REPO" --json url -q .url)"
fi

# 7. Merge, then clean up.
gh pr merge "$PR" -R "$REPO" "--$METHOD" >/dev/null 2>&1 || die 30 merge-failed "gh pr merge refused PR #$PR: $(gh pr view "$PR" -R "$REPO" --json mergeable,mergeStateStatus -q '"\(.mergeable) \(.mergeStateStatus)"')"
log "merged PR #$PR ($METHOD)"
cleanup_after_merge "$PR"
