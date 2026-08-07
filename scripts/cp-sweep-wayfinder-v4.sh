#!/usr/bin/env bash
# cp-sweep-wayfinder-v4.sh — converge exactly 5 stale per-profile v4.0.0 wayfinder
# copies to the corrected v4.0.0 tap (SKILL.md + references/UPSTREAM_LICENSE.md).
#
# SAFETY MODEL:
#   - Explicit ALLOW-LIST of exactly 5 target profile dirs. Nothing else is ever touched.
#   - The 2 v5.4.0 independent forks (global ~/.hermes/skills/... + orchestrator
#     ~/.hermes/profiles/orchestrator/...) are NOT in the list and are therefore
#     unreachable by this script.
#   - Ephemeral/backup dirs (~/.hermes/evals, ~/.hermes/kanban/boards/*/workspaces,
#     ~/.hermes/backups, ~/.hermes/profiles/elephant/kanban-recovery) are never
#     referenced.
#   - Copies BOTH skills/wayfinder/SKILL.md and skills/wayfinder/references/
#     UPSTREAM_LICENSE.md from the tap.
#   - A defensive shape check refuses any destination that is not a
#     .../skills/software-development/wayfinder dir, even if the allow-list were
#     edited by mistake.
#
# DRY-RUN GUARANTEE:
#   --dry-run performs ZERO filesystem writes. It prints the exact cp commands that
#   WOULD run (and would list the mkdir that WOULD run) but touches nothing.
#
# Usage:
#   ./cp-sweep-wayfinder-v4.sh --dry-run     # print the exact cp commands, do nothing
#   ./cp-sweep-wayfinder-v4.sh               # execute for real
#
# Env overrides:
#   TAP_ROOT=/abs/path   Source tap root (defaults to repo root via script location).
set -euo pipefail

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
elif [[ -n "${1:-}" ]]; then
  echo "ERROR: unknown argument '$1' (only --dry-run is supported)" >&2
  exit 2
fi

# Tap source of truth (repo worktree). Override with TAP_ROOT=/path if needed.
TAP_ROOT="${TAP_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SRC_SKILL="$TAP_ROOT/skills/wayfinder/SKILL.md"
SRC_LICENSE="$TAP_ROOT/skills/wayfinder/references/UPSTREAM_LICENSE.md"

# Explicit allow-list: the exact 5 per-profile v4.0.0 copies to converge.
# (Hard-coded on purpose — see SAFETY MODEL above.)
TARGETS=(
  "$HOME/.hermes/profiles/research-worker/skills/software-development/wayfinder"
  "$HOME/.hermes/profiles/peacock/skills/software-development/wayfinder"
  "$HOME/.hermes/profiles/reviewer-qa/skills/software-development/wayfinder"
  "$HOME/.hermes/profiles/bme/skills/software-development/wayfinder"
  "$HOME/.hermes/profiles/elephant/skills/software-development/wayfinder"
)

# Sanity: tap sources must exist (read-only check, safe in dry-run).
if [[ ! -f "$SRC_SKILL" ]]; then
  echo "ERROR: tap source missing: $SRC_SKILL" >&2
  exit 1
fi
if [[ ! -f "$SRC_LICENSE" ]]; then
  echo "ERROR: tap license missing: $SRC_LICENSE" >&2
  exit 1
fi

MODE_LABEL="$( [[ $DRY_RUN -eq 1 ]] && echo '[DRY-RUN]' || echo '[EXECUTE]' )"
echo "== cp-sweep-wayfinder-v4 $MODE_LABEL =="
echo "tap:    $SRC_SKILL"
echo "license: $SRC_LICENSE"
echo "targets: ${#TARGETS[@]}"
echo

count=0
for dst in "${TARGETS[@]}"; do
  # Defensive shape check — refuses anything that is not a wayfinder skill dir.
  if [[ "$dst" != */skills/software-development/wayfinder ]]; then
    echo "REFUSE (not a wayfinder skill dir): $dst" >&2
    continue
  fi
  if [[ ! -d "$dst" ]]; then
    echo "SKIP (missing dir): $dst" >&2
    continue
  fi

  cmd_mkdir="mkdir -p \"$dst/references\""
  cmd_cp_skill="cp \"$SRC_SKILL\" \"$dst/SKILL.md\""
  cmd_cp_license="cp \"$SRC_LICENSE\" \"$dst/references/UPSTREAM_LICENSE.md\""

  if [[ $DRY_RUN -eq 1 ]]; then
    # Print exactly what WOULD run. No filesystem writes at all.
    echo "# -> $dst"
    echo "$cmd_mkdir"
    echo "$cmd_cp_skill"
    echo "$cmd_cp_license"
  else
    eval "$cmd_mkdir"
    eval "$cmd_cp_skill"
    eval "$cmd_cp_license"
  fi
  count=$((count + 1))
done

echo
echo "== copied $count target dir (expect 5); 10 file copies total (2 x 5) =="
echo "== v5.4.0 forks (global + orchestrator) were NEVER referenced and remain untouched =="
echo "== ephemeral/backup dirs were NEVER referenced =="
if [[ $DRY_RUN -eq 1 ]]; then
  echo "DRY-RUN complete — no files were written. Re-run without --dry-run to execute."
else
  echo "EXECUTE complete."
fi
