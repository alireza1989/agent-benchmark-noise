"""Keep only the tasks that work on this machine before any model runs.

    python scripts/preflight.py results/candidates.txt jobs/preflight-oracle jobs/preflight-nop > results/tasks.txt

A task is kept when its reference solution (the oracle agent) passes and an agent that does
nothing (nop) fails. The first 20 kept tasks, in the order they were picked, are the benchmark.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load import read_job  # noqa: E402

KEEP = 20


def main(candidates, oracle_dir, nop_dir):
    names = Path(candidates).read_text().split()
    oracle = {r["task"]: r for r in read_job(oracle_dir)}
    nop = {r["task"]: r for r in read_job(nop_dir)}
    kept = []
    for name in names:
        o, n = oracle.get(name), nop.get(name)
        if o is None or n is None:
            why = "missing from a preflight job"
        elif o["bucket"] != "passed":
            why = f"oracle {o['bucket']}" + (f" ({o['exception']})" if o["exception"] else "")
        elif n["score"] > 0:
            why = "nop passed, so the tests don't check the work"
        elif len(kept) >= KEEP:
            why = "ok, not needed"
        else:
            why = "kept"
            kept.append(name)
        print(f"  {name:45s} {why}", file=sys.stderr)
    print(f"kept {len(kept)} of {len(names)} candidates", file=sys.stderr)
    print("\n".join(kept))


if __name__ == "__main__":
    main(*sys.argv[1:4])
