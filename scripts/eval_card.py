"""Write an evaluation card: every setting someone needs to reproduce or compare these runs.

    python scripts/eval_card.py jobs > results/eval-card.md

It reads Harbor's own records (lock.json, config.json, result.json) plus results/host.json and
results/summary.json, so nothing is typed in by hand.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(p):
    return json.loads(Path(p).read_text())


def main(jobs_dir):
    host = load(ROOT / "results" / "host.json")
    summary = load(ROOT / "results" / "summary.json")
    jobs = [p for p in Path(jobs_dir).iterdir() if (p / "lock.json").exists() and p.name.split("-")[0] in ("limits", "nolimits")]
    jobs.sort(key=lambda j: min(load(t)["started_at"] for t in j.glob("*/result.json")))
    lock = load(jobs[0] / "lock.json")
    trial = load(next(jobs[0].glob("*/result.json")))
    starts = [load(p)["started_at"] for j in jobs for p in j.glob("*/result.json")]
    ends = [load(p)["finished_at"] for j in jobs for p in j.glob("*/result.json")]
    digests = {t["task"]["name"].split("/")[-1]: t["task"].get("digest") for t in lock["trials"]}
    agent = trial["agent_info"]
    model = agent.get("model_info") or {}
    try:
        import litellm
        max_out = litellm.get_model_info(f"{model.get('provider')}/{model.get('name')}").get("max_output_tokens")
    except Exception:
        max_out = None

    lines = [
        "# Evaluation card",
        "",
        "## What was measured",
        f"- Benchmark: OpenThoughts-TBLite, commit `{host['tblite_commit']}`, {len(summary['tasks'])} tasks "
        "picked with `scripts/pick_tasks.py` (seed 2026) and kept by `scripts/preflight.py`",
        "- Score: share of trials where the task's tests pass (reward 1). Errors count as failures and are listed below.",
        f"- Runs: {', '.join(j.name for j in jobs)}, one attempt per task per run, in that order",
        f"- Time window: {min(starts)} to {max(ends)} (UTC)",
        "",
        "## Agent and model",
        f"- Harness: Harbor {lock['harbor']['version']}, agent `{agent['name']}` version {agent['version']}",
        f"- Model: `{model.get('name')}` from provider `{model.get('provider')}` (Anthropic API, called through LiteLLM {host.get('litellm')})",
        "- Sampling: no temperature sent, so the API default applies (the API rejected temperature 0, see results/sampling.txt)",
        "- Effort and thinking: not set, so the model default applies (adaptive thinking)",
        f"- max_tokens per call: LiteLLM default for this model ({max_out:,})" if max_out else "- max_tokens per call: LiteLLM default",
        "",
        "## Environment",
        f"- Docker {host['docker_version']} on {host['os']} ({host['arch']}), {host['cpus']} CPUs and "
        f"{host['memory_gb']:.1f} GB for Docker",
        f"- Trials at once: {lock['n_concurrent_trials']}",
        f"- Retries: {lock['retry']['max_retries']} (a failed trial is not rerun)",
        f"- Timeouts: task defaults, multiplier {trial['config']['timeout_multiplier']}",
        "- Resources, `limits` runs: each task's declared CPUs and memory are hard limits (Harbor's default on Docker)",
        "- Resources, `nolimits` runs: `--cpus ignore --memory ignore`, so containers share the whole Docker machine",
        "- Network: task defaults. 55 of the 100 TBLite verifiers download tools while grading, so grading needs internet access.",
        "",
        "## Results",
        "| Run | Passed | Score | 95% Wilson interval | Timeouts or errors | Cost |",
        "|---|---|---|---|---|---|",
    ]
    for r in summary["runs"]:
        errs = sum(v for k, v in r["buckets"].items() if k not in ("passed", "failed"))
        lines.append(f"| {r['job']} | {int(r['passed'])}/{r['n']} | {r['score']:.0%} | "
                     f"{r['wilson'][0]:.0%} to {r['wilson'][1]:.0%} | {errs} | ${r['cost_usd']:.2f} |")
    p = summary["pooled"]
    lines += [
        "",
        f"- All `limits` runs together: {p['mean']:.1%}, clustered standard error {p['se_clustered']:.1%} "
        f"({p['n_trials']} trials on {len(summary['tasks'])} tasks); solved every time: {p['always']}, never: {p['never']}",
    ]
    if "paired" in summary:
        q = summary["paired"]
        lines.append(f"- `nolimits` minus `limits`, paired by task: {100 * q['diff']:+.1f} points, 95% bootstrap interval "
                     f"{100 * q['boot'][0]:+.1f} to {100 * q['boot'][1]:+.1f}, sign-flip p = {q['p']:.2f}")
    lines += [
        f"- Total cost: ${summary['cost']['usd']:.2f} for {summary['cost']['trials']} trials",
        "",
        "## Task digests (from Harbor's lock.json)",
    ]
    lines += [f"- `{t}` {digests.get(t, '?')}" for t in summary["tasks"]]
    lines += [
        "",
        "## Known limits",
        f"- {len(summary['tasks'])} tasks is small: with one run per side, a true difference under about "
        f"{100 * summary['power'][0]['mde_20']:.0f} points is likely to be missed (section 5 of analyze.py).",
        "- One machine and one time window (above). Another Docker host, provider or day may give different results.",
        "- OpenThoughts-TBLite and its tasks are public, so the model may have seen them in training.",
    ]
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "jobs")
