"""Small statistics helpers for benchmark results. Standard library only.

Every function takes plain lists so you can check it by hand.
"""

import itertools
import math
import random

Z95 = 1.959964  # two-sided 95%
Z80 = 0.841621  # one-sided, for 80% power


def mean(xs):
    return sum(xs) / len(xs)


def sd(xs):
    """Sample standard deviation (divides by n - 1)."""
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def wilson(successes, n, z=Z95):
    """Wilson score interval for a pass rate. Better than mean +/- 1.96 SE for small n."""
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centre - half), min(1.0, centre + half))


def normal_ci(p, n, z=Z95):
    """The usual mean +/- 1.96 standard errors. Shown only to compare with Wilson."""
    half = z * math.sqrt(p * (1 - p) / n)
    return (p - half, p + half)


def clustered_se(scores_by_task):
    """Standard error of the overall mean when each task was run several times.

    Attempts on the same task are not independent, so they are grouped (clustered) by task.
    This is the cluster-robust form in Miller (2024), equation 4.
    """
    all_scores = [s for runs in scores_by_task.values() for s in runs]
    n = len(all_scores)
    m = mean(all_scores)
    return math.sqrt(sum(sum(s - m for s in runs) ** 2 for runs in scores_by_task.values())) / n


def naive_se(scores_by_task):
    """Standard error if you wrongly treat every attempt as an independent question."""
    all_scores = [s for runs in scores_by_task.values() for s in runs]
    n = len(all_scores)
    m = mean(all_scores)
    return math.sqrt(sum((s - m) ** 2 for s in all_scores) / (n - 1) / n)


def icc(scores_by_task):
    """One-way intraclass correlation, ICC(1,1), for tasks with the same number of attempts.

    Near 1: a task's result is mostly decided by the task (it passes every time or never).
    Near 0: results flip between attempts as if by chance.
    """
    rows = list(scores_by_task.values())
    k = len(rows[0])
    assert all(len(r) == k for r in rows), "every task needs the same number of attempts"
    n = len(rows)
    grand = mean([s for r in rows for s in r])
    msb = k * sum((mean(r) - grand) ** 2 for r in rows) / (n - 1)
    msw = sum((s - mean(r)) ** 2 for r in rows for s in r) / (n * (k - 1))
    if msb + (k - 1) * msw == 0:
        return float("nan")
    return (msb - msw) / (msb + (k - 1) * msw)


def mcnemar_exact(only_a, only_b):
    """Exact two-sided McNemar test for two single runs on the same tasks.

    only_a: tasks run A passed and run B failed. only_b: the reverse.
    Tasks that both passed or both failed carry no information about the difference.
    """
    n = only_a + only_b
    if n == 0:
        return 1.0
    k = min(only_a, only_b)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def sign_flip_test(diffs, max_exact=20, n_random=200_000, seed=0):
    """Paired permutation test on per-task differences.

    If the change did nothing, each task's difference is as likely to be +d as -d.
    Flip the signs every possible way and count how often the mean is as far from 0 as observed.
    """
    obs = abs(sum(diffs))
    nz = [d for d in diffs if d != 0]
    if not nz:
        return 1.0
    if len(nz) <= max_exact:
        hits = total = 0
        for signs in itertools.product((1, -1), repeat=len(nz)):
            total += 1
            if abs(sum(s * d for s, d in zip(signs, nz))) >= obs - 1e-12:
                hits += 1
        return hits / total
    rng = random.Random(seed)
    hits = sum(abs(sum(d if rng.random() < 0.5 else -d for d in nz)) >= obs - 1e-12 for _ in range(n_random))
    return (hits + 1) / (n_random + 1)


def bootstrap_mean_ci(xs, n_boot=10_000, seed=0, level=0.95):
    """Percentile bootstrap interval for a mean, resampling tasks with replacement."""
    rng = random.Random(seed)
    n = len(xs)
    means = sorted(mean([xs[rng.randrange(n)] for _ in range(n)]) for _ in range(n_boot))
    lo = means[int((1 - level) / 2 * n_boot)]
    hi = means[int((1 + level) / 2 * n_boot) - 1]
    return (lo, hi)


def variance_parts(scores_by_task):
    """Split the variance of a single-attempt score into two parts, for one configuration.

    within: how much one task's result changes between attempts (sampling noise), averaged over tasks.
    between: how much tasks differ in their true pass rate (which tasks you happened to pick).
    Uses the small-K correction from Wang (2026): divide by K - 1 within each task.
    """
    rows = list(scores_by_task.values())
    within = mean([sum((s - mean(r)) ** 2 for s in r) / (len(r) - 1) for r in rows])
    k = mean([len(r) for r in rows])
    task_means = [mean(r) for r in rows]
    between = max(0.0, sd(task_means) ** 2 - within / k)
    return {"within": within, "between": between}


def tasks_needed(delta, sd_diff, z_a=Z95, z_b=Z80):
    """Tasks needed to detect a true difference delta with 80% power at the 5% level (paired)."""
    return math.ceil(((z_a + z_b) * sd_diff / delta) ** 2)


def detectable_difference(n, sd_diff, z_a=Z95, z_b=Z80):
    """Smallest true difference you'd detect 80% of the time with n tasks (paired)."""
    return (z_a + z_b) * sd_diff / math.sqrt(n)


def sd_diff_for_attempts(within_a, within_b, omega2, k):
    """Standard deviation of a per-task difference when each side averages k attempts.

    omega2 is the variance of the true per-task difference between the two configurations.
    For two identical configurations it is 0 and only sampling noise is left (Miller 2024, eq. 9).
    """
    return math.sqrt(omega2 + within_a / k + within_b / k)
