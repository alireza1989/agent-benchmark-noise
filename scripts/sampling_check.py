"""Two quick checks on the model itself, before any agent runs. Costs well under one cent.

    python scripts/sampling_check.py

1. Ask for temperature 0. Many guides say to do this for reproducible evals.
2. Send the exact same request 10 times and count how many different answers come back.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-5-5")
URL = "https://api.anthropic.com/v1/messages"
PROMPT = ("Reply with one bash command and nothing else: print how many lines the file "
          "data.csv has, not counting the header line.")
OUT = Path(__file__).resolve().parent.parent / "results" / "sampling.json"


def call(body):
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST", headers={
        "x-api-key": os.environ["ANTHROPIC_API_KEY"],
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def answer(msg):
    text = "".join(b.get("text", "") for b in msg.get("content", []) if b.get("type") == "text")
    return text.strip().strip("`").removeprefix("bash").strip()


def main():
    base = {"model": MODEL, "max_tokens": 2000, "messages": [{"role": "user", "content": PROMPT}]}

    t0_status, msg = call({**base, "temperature": 0})
    print(f"temperature 0: HTTP {t0_status}")
    if t0_status != 200:
        print(f"  {msg.get('error', {}).get('message')}")

    answers, models, usage = [], set(), Counter()
    for _ in range(10):
        status, msg = call(base)
        if status != 200:
            sys.exit(f"HTTP {status}: {msg}")
        answers.append(answer(msg))
        models.add(msg.get("model"))
        for k in ("input_tokens", "output_tokens"):
            usage[k] += msg.get("usage", {}).get(k, 0)
    counts = Counter(answers)
    print(f"\nsame request 10 times ({', '.join(sorted(models))}): {len(counts)} different answers")
    for text, n in counts.most_common():
        print(f"  {n:2d}x  {text}")
    print(f"\ntokens used: {usage['input_tokens']} in, {usage['output_tokens']} out")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"model": sorted(models), "answers": answers, "usage": usage,
                               "temperature_0_status": t0_status}, indent=2))


if __name__ == "__main__":
    main()
