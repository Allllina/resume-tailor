#!/usr/bin/env bash
# `make status` — one-screen project state. Built for the controller agent +
# the maintainer to glance at without grepping 5 files.
#
# Fast (<3s): no pytest, no LLM. For deeper checks use `make status-deep`.
#
# Sections:
#   1. Git (branch + last commit + dirty count)
#   2. Architecture audit (RED/YELLOW counts, no full output)
#   3. Architecture debt (open count by severity)
#   4. Recent incidents (count + last 3 IDs)
#   5. STATUS.md self-hosted axis
#
# Exit: always 0; this is informational. CI uses architecture_audit.py
# directly with --fail-on-violations for gating.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

c_dim=$'\033[2m'; c_b=$'\033[1m'; c_g=$'\033[32m'; c_y=$'\033[33m'; c_r=$'\033[31m'; c_0=$'\033[0m'

hr() { printf "${c_dim}%s${c_0}\n" "──────────────────────────────────────────────────────────────"; }

hr
printf "${c_b}Resume_Optimizer status${c_0}  ${c_dim}$(date +%Y-%m-%d\ %H:%M)${c_0}\n"
hr

# ── 1. Git
branch=$(git branch --show-current 2>/dev/null || echo "(detached)")
last=$(git log -1 --format='%h %s' 2>/dev/null || echo "(no commits)")
dirty=$(git status -s 2>/dev/null | wc -l | tr -d ' ')
printf "${c_b}Git${c_0}\n"
printf "  branch    %s\n" "$branch"
printf "  last      %s\n" "$last"
if [ "$dirty" -gt 0 ]; then
  printf "  dirty     ${c_y}%s file(s) uncommitted${c_0}\n" "$dirty"
else
  printf "  dirty     ${c_g}clean${c_0}\n"
fi
echo

# ── 2. Architecture audit (parse counts from script output, don't dump full)
printf "${c_b}Architecture audit${c_0}\n"
audit_out=$(python3 scripts/architecture_audit.py 2>/dev/null || echo "")
red=$(echo "$audit_out" | grep -c '^### ❌' || true)
yel=$(echo "$audit_out" | grep -c '^### ⚠️' || true)
grn=$(echo "$audit_out" | grep -c '^### ✅' || true)
printf "  ${c_g}✅ %s${c_0}  ${c_y}⚠️  %s${c_0}  ${c_r}❌ %s${c_0}\n" "$grn" "$yel" "$red"
if [ "$red" -gt 0 ]; then
  echo "$audit_out" | awk '/^### ❌/{f=1; print "  " $0; next} /^### / && f {f=0} f {print "    " $0}' | head -8
fi
echo

# ── 3. Architecture debt
printf "${c_b}Architecture debt${c_0}  ${c_dim}docs/ARCHITECTURE_DEBT.md${c_0}\n"
if [ -f docs/ARCHITECTURE_DEBT.md ]; then
  open_line=$(grep -E "^\*\*Open items:\*\*" docs/ARCHITECTURE_DEBT.md | head -1 || echo "(unknown)")
  printf "  %s\n" "$(echo "$open_line" | sed 's/\*\*//g')"
  high_ids=$(awk '/^\| D[0-9]+ \|/ && / high /' docs/ARCHITECTURE_DEBT.md | awk -F'|' '{gsub(/ /, "", $2); printf $2 " "}')
  if [ -n "$high_ids" ]; then
    printf "  high      %s\n" "$high_ids"
  fi
fi
echo

# ── 4. Recent incidents
printf "${c_b}Incidents${c_0}  ${c_dim}docs/INCIDENTS.md${c_0}\n"
if [ -f docs/INCIDENTS.md ]; then
  inc_count=$(grep -cE "^### INC-[0-9]+" docs/INCIDENTS.md || echo 0)
  printf "  total     %s\n" "$inc_count"
  printf "  recent    "
  grep -E "^### INC-[0-9]+" docs/INCIDENTS.md | tail -3 | awk -F' — ' '{sub(/^### /, "", $1); printf "%s  ", $1}'
  echo
fi
echo

# ── 5. STATUS.md spec coverage
printf "${c_b}Spec coverage${c_0}  ${c_dim}docs/STATUS.md${c_0}\n"
if [ -f docs/STATUS.md ]; then
  upd=$(grep -E "^\*\*Last updated:\*\*" docs/STATUS.md | head -1 | sed 's/\*\*Last updated:\*\* //; s/\*\*//g')
  printf "  updated   %s\n" "$upd"
  axis=$(grep -E "[Ss]elf-hosted deployab" docs/STATUS.md | head -1 | grep -oE "[0-9]+/10" | head -1)
  if [ -n "$axis" ]; then
    printf "  selfhost  %s\n" "$axis"
  fi
fi
echo

hr
printf "${c_dim}For tests:           make test-quick (unit) or make test (full ~40s)${c_0}\n"
printf "${c_dim}For full audit:      python3 scripts/architecture_audit.py${c_0}\n"
printf "${c_dim}For dispatch rules:  cat docs/SUBAGENT_DISPATCH_TEMPLATE.md${c_0}\n"
hr
