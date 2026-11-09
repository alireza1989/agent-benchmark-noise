"""Read Harbor job folders into one row per trial.

Every trial folder has a result.json written by Harbor. This module only reads them.
"""

import json
from datetime import datetime
from pathlib import Path

# Same buckets as the triage script in the Harbor post (alireza1989/harbor-benchmarking-example).
VERIFIER_BROKEN = {"RewardFileNotFoundError", "RewardFileEmptyError",
                   "VerifierOutputParseError", "VerifierTimeoutError"}
API_ERRORS = {"RateLimitError", "APIConnectionError", "InternalServerError", "ServiceUnavailableError",
              "Timeout", "APIError", "ApiUsageLimitError", "AgentAuthenticationError", "ModelNotFoundError",
              "BadRequestError"}


def _time(s):
    # Python before 3.11 can't read a trailing "Z", so spell out the UTC offset.
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def bucket(exc, reward):
    if reward is None:
        if exc in VERIFIER_BROKEN:
            return "verifier broken"
        if exc in API_ERRORS:
            return "API error"
        return "infra error"
    if exc == "AgentTimeoutError":
        return "timed out, passed" if reward >= 1 else "timed out, failed"
    return "passed" if reward >= 1 else "failed"


def read_trial(path):
    r = json.loads(Path(path).read_text())
    rewards = (r.get("verifier_result") or {}).get("rewards") or None
    reward = None if rewards is None else float(next(iter(rewards.values())))
    exc = (r.get("exception_info") or {}).get("exception_type")
    agent = r.get("agent_result") or {}
    start, end = _time(r.get("started_at")), _time(r.get("finished_at"))
    env = (r.get("config") or {}).get("environment") or {}
    return {
        "task": r["task_name"].split("/")[-1],
        "trial": r["trial_name"],
        "reward": reward,
        # An error that stops the verifier counts as a failure, and is reported separately.
        "score": 0.0 if reward is None else reward,
        "exception": exc,
        "bucket": bucket(exc, reward),
        "input_tokens": agent.get("n_input_tokens") or 0,
        "cache_tokens": agent.get("n_cache_tokens") or 0,
        "output_tokens": agent.get("n_output_tokens") or 0,
        "cost_usd": agent.get("cost_usd") or 0.0,
        "seconds": (end - start).total_seconds() if start and end else None,
        "started_at": r.get("started_at"),
        "cpu_policy": env.get("cpu_enforcement_policy"),
        "memory_policy": env.get("memory_enforcement_policy"),
        "agent": (r.get("agent_info") or {}).get("name"),
        "agent_version": (r.get("agent_info") or {}).get("version"),
        "model": ((r.get("agent_info") or {}).get("model_info") or {}).get("name"),
    }


def read_job(job_dir):
    job_dir = Path(job_dir)
    rows = [read_trial(p) for p in sorted(job_dir.glob("*/result.json"))]
    for row in rows:
        row["job"] = job_dir.name
    return rows


def job_finished(job_dir):
    p = Path(job_dir) / "result.json"
    return p.exists() and json.loads(p.read_text()).get("finished_at") is not None


def by_task(rows):
    """{task: [score, score, ...]} in the order the jobs were given."""
    out = {}
    for row in rows:
        out.setdefault(row["task"], []).append(row["score"])
    return out
