#!/usr/bin/env bash
# Reproduce every run in the post. Needs Docker, git, uv, and ANTHROPIC_API_KEY in .env.
#   ./run_all.sh              everything: task check, model check, 5 runs, analysis (about 4 to 5 hours)
#   ./run_all.sh --preflight  stop after the task check (no model calls, no cost)
#   ./run_all.sh --analyze    redo the analysis, evaluation card and figures from jobs/
# Rerunning skips every job that already finished, so you can stop and continue later.
set -euo pipefail
cd "$(dirname "$0")"

MODEL=${MODEL:-anthropic/claude-haiku-5-5}
N=${N_CONCURRENT:-3}
# The commit Harbor's registry pins for openthoughts-tblite@2.0
TBLITE_COMMIT=f075e463472c7790b85793b392dff1fff20cc0e3
J=jobs
mkdir -p results "$J"

# 1. Python environment with the exact versions used in the post
if [[ ! -x .venv/bin/harbor ]]; then
  command -v uv >/dev/null || { echo "Install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
  uv venv -q --clear --python 3.12 .venv
  uv pip install -q --python .venv/bin/python -r requirements.txt
fi
source .venv/bin/activate

analyze() {
  python scripts/analyze.py "$J" | tee results/analysis.txt
  python scripts/eval_card.py "$J" > results/eval-card.md
  python scripts/venv_lines.py "$J" | tee results/venv-lines.txt
  python scripts/figures.py
}
if [[ "${1:-}" == "--analyze" ]]; then analyze; exit 0; fi

# 2. The benchmark, at a fixed commit
[[ -d tblite ]] || git clone -q https://github.com/open-thoughts/OpenThoughts-TBLite.git tblite
git -C tblite checkout -q "$TBLITE_COMMIT"
docker info >/dev/null 2>&1 || { echo "Docker isn't running"; exit 1; }
python scripts/host_info.py > results/host.json

finished() {
  [[ -f "$J/$1/result.json" ]] &&
    python -c "import json,sys; sys.exit(json.load(open('$J/$1/result.json')).get('finished_at') is None)"
}
run() {
  local name=$1; shift
  if finished "$name"; then echo "== $name: already done, skipping"; return; fi
  rm -rf "${J:?}/$name"
  echo "== $name  (started $(date -u +%H:%M) UTC)"
  harbor run -p tblite "${INCLUDE[@]}" -o "$J" --job-name "$name" -n "$N" -y -q "$@"
}
include_from() {
  INCLUDE=()
  while read -r t; do
    if [[ -n "$t" ]]; then INCLUDE+=(-i "$t"); fi
  done < "$1"
}

# 3. Pick 28 candidates, then check each one works on this machine before any model runs
python scripts/pick_tasks.py tblite > results/candidates.txt
include_from results/candidates.txt
run preflight-oracle -a oracle
run preflight-nop -a nop
python scripts/preflight.py results/candidates.txt "$J/preflight-oracle" "$J/preflight-nop" > results/tasks.txt
if [[ $(wc -l < results/tasks.txt) -lt 20 ]]; then echo "fewer than 20 tasks work on this machine, stopping"; exit 1; fi
if [[ "${1:-}" == "--preflight" ]]; then exit 0; fi

# 4. Quick checks on the model itself, then one agent trial end to end
[[ -f .env ]] || { echo "Put ANTHROPIC_API_KEY=... in .env (see .env.example)"; exit 1; }
set -a; source .env; set +a
: "${ANTHROPIC_API_KEY:?add ANTHROPIC_API_KEY to .env}"
[[ "$ANTHROPIC_API_KEY" != "sk-ant-..." ]] || { echo ".env still has the example key. Put your real key in it."; exit 1; }
[[ -f results/sampling.json ]] || python scripts/sampling_check.py | tee results/sampling.txt
INCLUDE=(-i "$(head -1 results/tasks.txt)")
run smoke -a terminus-2 -m "$MODEL"
python scripts/smoke_check.py "$J/smoke"

# 5. The five runs. Same agent, model and tasks; the only change is resource limits.
#    They alternate so time of day affects both settings the same way.
include_from results/tasks.txt
AGENT=(-a terminus-2 -m "$MODEL")
run limits-1   "${AGENT[@]}"
run nolimits-1 "${AGENT[@]}" --cpus ignore --memory ignore
run limits-2   "${AGENT[@]}"
run nolimits-2 "${AGENT[@]}" --cpus ignore --memory ignore
run limits-3   "${AGENT[@]}"

analyze
