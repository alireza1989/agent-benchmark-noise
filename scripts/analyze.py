"""Print every number in the post from the Harbor job folders, and save them to results/summary.json.

    python scripts/analyze.py jobs

Expects runs named limits-1, limits-2, ... (task limits on) and nolimits-1, ... (limits off).
"""

import itertools
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stats as S  # noqa: E402
from load import by_task, read_job  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TASKS = Path(os.environ.get("TASKS_FILE", ROOT / "results" / "tasks.txt")).read_text().split()


def pct(x):
    return f"{100 * x:.1f}%"


def runs(jobs_dir, config):
    found = sorted((p for p in Path(jobs_dir).iterdir() if re.fullmatch(rf"{config}-\d+", p.name)),
                   key=lambda p: int(p.name.rsplit("-", 1)[1]))
    out = []
    for p in found:
        rows = [r for r in read_job(p) if r["task"] in TASKS]
        if rows:
            out.append((p.name, rows))
    return out


def run_table(name, rows):
    n, passed = len(rows), sum(r["score"] for r in rows)
    lo, hi = S.wilson(passed, n)
    nlo, nhi = S.normal_ci(passed / n, n)
    buckets = {}
    for r in rows:
        buckets[r["bucket"]] = buckets.get(r["bucket"], 0) + 1
    cost = sum(r["cost_usd"] for r in rows)
    secs = [r["seconds"] for r in rows if r["seconds"] is not None]
    print(f"  {name:11s} {int(passed):2d}/{n}  {pct(passed / n):>6s}   Wilson {pct(lo)} to {pct(hi)}"
          f"   (+/-1.96 SE: {pct(nlo)} to {pct(nhi)})   ${cost:.2f}   median {sorted(secs)[len(secs) // 2] / 60:.1f} min")
    return {"job": name, "n": n, "passed": passed, "score": passed / n, "wilson": [lo, hi],
            "normal": [nlo, nhi], "buckets": buckets, "cost_usd": cost, "started_at": min(r["started_at"] for r in rows)}


def main(jobs_dir):
    summary = {"tasks": TASKS}
    limits, nolimits = runs(jobs_dir, "limits"), runs(jobs_dir, "nolimits")

    print("1. Each run on its own (errors count as failures)")
    summary["runs"] = [run_table(name, rows) for name, rows in limits + nolimits]
    summary["grid"] = {name: {r["task"]: r["bucket"] for r in rows} for name, rows in limits + nolimits}
    print("\n   What happened in each trial:")
    for row in summary["runs"]:
        print(f"  {row['job']:11s} " + ", ".join(f"{v} {k}" for k, v in sorted(row["buckets"].items())))

    print("\n2. Same setup, different runs (A/A)")
    grid = {name: {r["task"]: r["score"] for r in rows} for name, rows in limits}
    pairs = []
    for (a, ra), (b, rb) in itertools.combinations(grid.items(), 2):
        only_a = sum(1 for t in TASKS if ra.get(t, 0) > rb.get(t, 0))
        only_b = sum(1 for t in TASKS if rb.get(t, 0) > ra.get(t, 0))
        diff = (sum(rb.values()) - sum(ra.values())) / len(TASKS)
        p = S.mcnemar_exact(only_a, only_b)
        pairs.append({"a": a, "b": b, "diff": diff, "only_a": only_a, "only_b": only_b, "p": p})
        print(f"  {b} minus {a}: {100 * diff:+.0f} points. {only_a + only_b} tasks flipped "
              f"({only_a} passed only in {a}, {only_b} only in {b}). McNemar p = {p:.2f}")
    summary["aa_pairs"] = pairs

    print("\n3. All limits runs together")
    lim = by_task([r for _, rows in limits for r in rows])
    k = len(limits)
    allscores = [s for v in lim.values() for s in v]
    m, se_c, se_n = S.mean(allscores), S.clustered_se(lim), S.naive_se(lim)
    always = sum(1 for v in lim.values() if min(v) >= 1)
    never = sum(1 for v in lim.values() if max(v) <= 0)
    icc = S.icc(lim)
    parts = S.variance_parts(lim)
    print(f"  {len(allscores)} trials on {len(lim)} tasks: {pct(m)}")
    print(f"  standard error if every trial counted as independent: {pct(se_n)}")
    print(f"  standard error grouped by task (clustered):           {pct(se_c)}")
    print(f"  95% interval, clustered: {pct(m - S.Z95 * se_c)} to {pct(m + S.Z95 * se_c)}")
    print(f"  solved in all {k} runs: {always}   never solved: {never}   sometimes: {len(lim) - always - never}")
    print(f"  pass^{k} (solved every time): {pct(always / len(lim))}")
    print(f"  ICC: {icc:.2f}   variance within a task: {parts['within']:.3f}   between tasks: {parts['between']:.3f}")
    summary["pooled"] = {"k": k, "n_trials": len(allscores), "mean": m, "se_clustered": se_c, "se_naive": se_n,
                         "always": always, "never": never, "icc": icc, **parts,
                         "per_task": {t: lim.get(t, []) for t in TASKS}}

    if nolimits:
        print("\n4. Limits off versus limits on, paired by task")
        nol = by_task([r for _, rows in nolimits for r in rows])
        d = [S.mean(nol[t]) - S.mean(lim[t]) for t in TASKS]
        md, sd_d = S.mean(d), S.sd(d)
        se_paired = sd_d / len(d) ** 0.5
        m_on = S.mean([S.mean(lim[t]) for t in TASKS])
        m_off = S.mean([S.mean(nol[t]) for t in TASKS])
        se_unpaired = (S.sd([S.mean(lim[t]) for t in TASKS]) ** 2 / len(TASKS)
                       + S.sd([S.mean(nol[t]) for t in TASKS]) ** 2 / len(TASKS)) ** 0.5
        boot = S.bootstrap_mean_ci(d)
        p = S.sign_flip_test(d)
        changed = sorted(((t, x) for t, x in zip(TASKS, d) if x != 0), key=lambda z: -abs(z[1]))
        infra_on = sum(1 for _, rows in limits for r in rows if r["bucket"] in ("infra error", "verifier broken"))
        infra_off = sum(1 for _, rows in nolimits for r in rows if r["bucket"] in ("infra error", "verifier broken"))
        n_on = sum(len(rows) for _, rows in limits)
        n_off = sum(len(rows) for _, rows in nolimits)
        print(f"  limits on: {pct(m_on)} ({len(limits)} runs)   limits off: {pct(m_off)} ({len(nolimits)} runs)")
        print(f"  difference: {100 * md:+.1f} points")
        print(f"  standard error, unpaired: {pct(se_unpaired)}   paired: {pct(se_paired)}")
        print(f"  95% interval, unpaired: {100 * (md - S.Z95 * se_unpaired):+.1f} to {100 * (md + S.Z95 * se_unpaired):+.1f} points"
              f"   paired: {100 * (md - S.Z95 * se_paired):+.1f} to {100 * (md + S.Z95 * se_paired):+.1f} points")
        print(f"  95% bootstrap interval for the difference: {100 * boot[0]:+.1f} to {100 * boot[1]:+.1f} points")
        print(f"  sign-flip test p = {p:.2f}")
        print(f"  infra or verifier errors: {infra_on}/{n_on} with limits, {infra_off}/{n_off} without")
        print("  tasks whose average changed:")
        for t, x in changed:
            print(f"    {t:45s} {100 * x:+.0f} points  (on {lim[t]}, off {nol[t]})")
        omega2 = max(0.0, sd_d ** 2 - S.variance_parts(lim)["within"] / len(limits)
                     - S.variance_parts(nol)["within"] / len(nolimits))
        summary["paired"] = {"mean_on": m_on, "mean_off": m_off, "diff": md, "sd_diff": sd_d,
                             "se_paired": se_paired, "se_unpaired": se_unpaired, "boot": boot, "p": p,
                             "infra_on": infra_on, "n_on": n_on, "infra_off": infra_off, "n_off": n_off,
                             "per_task_diff": dict(zip(TASKS, d)), "omega2": omega2,
                             "per_task_off": {t: nol.get(t, []) for t in TASKS}}

    print("\n5. How many tasks would you need?")
    within = parts["within"]
    omega2 = summary.get("paired", {}).get("omega2", 0.0)
    print(f"  measured: variance within a task {within:.3f}, true task-to-task spread of the change {omega2:.3f}")
    print(f"  attempts per task | smallest difference {len(TASKS)} tasks can detect | tasks needed for 5 points | for 10 points")
    power = []
    for kk in (1, 3, 5):
        sdd = S.sd_diff_for_attempts(within, within, omega2, kk)
        mde = S.detectable_difference(len(TASKS), sdd)
        n5, n10 = S.tasks_needed(0.05, sdd), S.tasks_needed(0.10, sdd)
        power.append({"k": kk, "sd_diff": sdd, "mde_20": mde, "n_5": n5, "n_10": n10})
        print(f"  {kk:17d} | {100 * mde:{30 + len(str(len(TASKS)))}.0f} points | {n5:24d} | {n10:12d}")
    summary["power"] = power

    allrows = [r for _, rows in limits + nolimits for r in rows]
    cost = sum(r["cost_usd"] for r in allrows)
    solved = sum(r["score"] for r in allrows)
    toks = sum(r["input_tokens"] for r in allrows), sum(r["cache_tokens"] for r in allrows), sum(r["output_tokens"] for r in allrows)
    print(f"\n6. Cost: {len(allrows)} trials, ${cost:.2f} total, ${cost / len(allrows):.3f} per trial, "
          f"${cost / max(solved, 1):.3f} per solved trial")
    print(f"   tokens: {toks[0]:,} input ({toks[1]:,} of them read from cache), {toks[2]:,} output")
    summary["cost"] = {"trials": len(allrows), "usd": cost, "solved": solved, "input_tokens": toks[0],
                       "cache_tokens": toks[1], "output_tokens": toks[2]}

    (ROOT / "results" / "summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "jobs")
