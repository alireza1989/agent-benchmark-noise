"""Pick the candidate tasks from OpenThoughts-TBLite with a fixed seed.

    python scripts/pick_tasks.py tblite > results/candidates.txt

Only tasks that declare CPU or memory limits are eligible, because the post compares runs
with those limits and without them. On Docker, a task with no declared limits runs uncapped
either way. Tasks that ask for more than 2 CPUs or 4 GB are left out so three trials fit on
a 4 CPU, 8 GB Docker machine.
"""

import random
import sys
import tomllib
from pathlib import Path

SEED, N = 2026, 28


def memory_mb(env):
    if "memory_mb" in env:
        return int(env["memory_mb"])
    m = str(env.get("memory", "")).upper()
    if m.endswith("G"):
        return int(float(m[:-1]) * 1024)
    if m.endswith("M"):
        return int(float(m[:-1]))
    return None


def main(root):
    eligible = []
    for toml in sorted(Path(root).glob("*/task.toml")):
        cfg = tomllib.loads(toml.read_text())
        env = cfg.get("environment", {})
        cpus, mem = env.get("cpus"), memory_mb(env)
        if cpus is None and mem is None:
            continue
        if (cpus or 0) > 2 or (mem or 0) > 4096:
            continue
        diff = str(cfg.get("metadata", {}).get("difficulty", "?")).lower()
        eligible.append((toml.parent.name, cpus, mem, diff))
    picked = random.Random(SEED).sample(eligible, N)
    print(f"{len(eligible)} eligible tasks, picked {N} with seed {SEED}", file=sys.stderr)
    for name, cpus, mem, diff in picked:
        print(f"  {name:45s} {cpus} CPU  {mem} MB  {diff}", file=sys.stderr)
        print(name)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "tblite")
