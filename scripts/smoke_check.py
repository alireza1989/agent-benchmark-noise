"""Stop before the long runs if the one-trial smoke test hit an API or setup error.

    python scripts/smoke_check.py jobs/smoke

A failed task is fine here. An error means the key, model name or Docker setup needs fixing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load import read_job  # noqa: E402

rows = read_job(sys.argv[1])
for r in rows:
    tokens = r["input_tokens"] + r["output_tokens"]
    print(f"smoke: {r['task']} {r['bucket']}, {tokens:,} tokens, ${r['cost_usd']:.3f}, {r['seconds'] / 60:.1f} min")
    if r["bucket"] in ("API error", "infra error") or tokens == 0:
        sys.exit(f"stopping: {r['exception']}. See {sys.argv[1]}/{r['trial']}/exception.txt")
