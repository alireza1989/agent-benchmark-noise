"""Record the machine and versions the runs used, for the evaluation card.

    python scripts/host_info.py > results/host.json
"""

import importlib.metadata as md
import json
import subprocess

info = json.loads(subprocess.run(["docker", "info", "--format", "{{json .}}"],
                                 capture_output=True, text=True, check=True).stdout)
commit = subprocess.run(["git", "-C", "tblite", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
print(json.dumps({
    "docker_version": info.get("ServerVersion"),
    "os": info.get("OperatingSystem"),
    "arch": info.get("Architecture"),
    "cpus": info.get("NCPU"),
    "memory_gb": (info.get("MemTotal") or 0) / 2**30,
    "harbor": md.version("harbor"),
    "litellm": md.version("litellm"),
    "tblite_commit": commit,
}, indent=2))
