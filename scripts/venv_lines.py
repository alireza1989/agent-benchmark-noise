"""Show how the agent created virtual environments in reproducibility-and-envsetup, run by run.

    python scripts/venv_lines.py jobs

The task's test looks for the literal text "python -m venv" in repro.sh. This prints the first
line that creates a virtual environment in the last repro.sh the agent wrote, and whether the trial passed.
"""

import json
import sys
from pathlib import Path

TASK = "reproducibility-and-envsetup"
RUNS = ["limits-1", "limits-2", "limits-3", "nolimits-1", "nolimits-2"]


def main(jobs_dir):
    for run in RUNS:
        trial = next(Path(jobs_dir, run).glob(f"{TASK}__*"))
        steps = json.loads((trial / "agent" / "trajectory.json").read_text())["steps"]
        writes = [c["arguments"].get("keystrokes", "") for s in steps for c in (s.get("tool_calls") or [])
                  if "repro.sh" in c["arguments"].get("keystrokes", "") and "-m venv" in c["arguments"].get("keystrokes", "")]
        venv = next((ln.strip() for ln in writes[-1].splitlines() if "-m venv" in ln), "?") if writes else "?"
        reward = json.loads((trial / "result.json").read_text())["verifier_result"]["rewards"]["reward"]
        print(f"{run:11s} {venv:37s} {'passed' if reward >= 1 else 'failed'}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "jobs")
