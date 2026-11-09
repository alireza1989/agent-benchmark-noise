import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import stats  # noqa: E402


def close(a, b, tol=1e-3):
    return abs(a - b) < tol


def test_wilson_matches_scipy():
    # scipy.stats.binomtest(81, 263).proportion_ci(method="wilson") gives 0.2553 to 0.3662
    lo, hi = stats.wilson(81, 263)
    assert close(lo, 0.2553, 1e-3) and close(hi, 0.3662, 1e-3)


def test_wilson_never_leaves_0_1():
    lo, hi = stats.wilson(20, 20)
    assert hi == 1.0 and 0.8 < lo < 0.9
    lo, hi = stats.normal_ci(1.0, 20)
    assert lo == hi == 1.0  # the normal interval collapses to a point, Wilson does not


def test_clustered_equals_se_of_task_means_when_balanced():
    data = {"a": [1, 1, 1], "b": [0, 0, 0], "c": [1, 0, 1], "d": [0, 1, 0]}
    means = [stats.mean(r) for r in data.values()]
    # population-style SE of task means: sqrt(sum((m - M)^2)) / n_tasks
    m = stats.mean(means)
    expected = math.sqrt(sum((x - m) ** 2 for x in means)) / len(means)
    assert close(stats.clustered_se(data), expected, 1e-9)
    assert stats.clustered_se(data) > stats.naive_se(data)


def test_icc_extremes():
    assert close(stats.icc({"a": [1, 1, 1], "b": [0, 0, 0], "c": [1, 1, 1]}), 1.0)
    assert stats.icc({"a": [1, 0], "b": [0, 1], "c": [1, 0], "d": [0, 1]}) < 0


def test_mcnemar():
    assert stats.mcnemar_exact(0, 0) == 1.0
    assert close(stats.mcnemar_exact(5, 0), 0.0625)
    assert close(stats.mcnemar_exact(3, 3), 1.0)


def test_sign_flip_matches_hand_count():
    # diffs +1, +1, +1: 8 sign patterns, |sum| >= 3 in 2 of them
    assert close(stats.sign_flip_test([1, 1, 1]), 0.25)
    assert stats.sign_flip_test([0, 0]) == 1.0


def test_power_round_trip():
    n = stats.tasks_needed(0.05, 0.4)
    assert stats.detectable_difference(n, 0.4) <= 0.05 < stats.detectable_difference(n - 1, 0.4)
    # Miller (2024) example: omega^2 = 1/9, delta = 0.03 -> about 969 questions
    assert abs(stats.tasks_needed(0.03, math.sqrt(1 / 9)) - 969) <= 2


def test_variance_parts_identical_tasks():
    parts = stats.variance_parts({"a": [1, 0, 1, 0], "b": [1, 0, 1, 0]})
    assert close(parts["between"], 0.0) and close(parts["within"], 1 / 3)
