"""Draw the data figures in the post as SVG, from results/summary.json.

    python scripts/figures.py
"""

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import stats as S  # noqa: E402

OUT = ROOT / "figures"
INK, MUTED, GRID, BG, FAIL = "#000000", "#5a5a5a", "#e3e3e3", "#ffffff", "#e9e9e9"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
FONT = "Rubik, Helvetica, Arial, sans-serif"


def text(x, y, s, size=22, fill=INK, anchor="start", weight=400):
    s = str(s).replace("&", "&amp;").replace("<", "&lt;")
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{s}</text>')


def line(x1, y1, x2, y2, stroke=GRID, width=1.5, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{width}"{d}/>'


def svg(width, height, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}" role="img"><title>{title}</title>'
            f'<rect width="{width}" height="{height}" fill="{BG}"/>{"".join(body)}</svg>')


def short(job):
    kind, n = job.rsplit("-", 1)
    return ("Limits on " if kind == "limits" else "Limits off ") + n


def fig_grid(s):
    """Every trial: one row per task, one column per run."""
    runs = [r["job"] for r in s["runs"]]
    grid = s["grid"]
    tasks = sorted(s["tasks"], key=lambda t: (-sum(grid[j].get(t) in ("passed", "timed out, passed") for j in runs), t))
    x0, y0, cw, ch, gap = 470, 150, 104, 34, 6
    sep = 26  # space between the limits-on and limits-off columns
    n_on = sum(j.startswith("limits") for j in runs)
    colx = [x0 + i * (cw + gap) + (sep if i >= n_on else 0) for i in range(len(runs))]
    b = [text(40, 50, "20 tasks, 5 runs, same agent and model", 26, weight=500),
         text(40, 84, "Each square is one trial. Only the resource limits change between the two groups.", 20, MUTED)]
    for i, j in enumerate(runs):
        b.append(text(colx[i] + cw / 2, y0 - 16, short(j), 18, MUTED, "middle"))
    for r, t in enumerate(tasks):
        y = y0 + r * (ch + gap)
        name = t if len(t) <= 34 else t[:32] + "…"
        b.append(text(x0 - 16, y + ch / 2 + 7, name, 18, INK, "end"))
        for i, j in enumerate(runs):
            bk = grid[j].get(t, "missing")
            fill = BLUE if bk in ("passed", "timed out, passed") else ORANGE if bk not in ("failed", "timed out, failed") else FAIL
            b.append(f'<rect x="{colx[i]:.1f}" y="{y:.1f}" width="{cw}" height="{ch}" rx="4" fill="{fill}"/>')
            if bk.startswith("timed out"):
                b.append(text(colx[i] + cw / 2, y + ch / 2 + 6, "timeout", 15, BG if fill == BLUE else INK, "middle"))
    yl = y0 + len(tasks) * (ch + gap) + 30
    keys = [(BLUE, "passed"), (FAIL, "failed")]
    if any(bk not in ("passed", "failed", "timed out, passed", "timed out, failed") for g in grid.values() for bk in g.values()):
        keys.append((ORANGE, "error, scored as a fail"))
    for k, (fill, label) in enumerate(keys):
        x = 470 + k * 170
        b.append(f'<rect x="{x}" y="{yl}" width="26" height="26" rx="4" fill="{fill}"/>')
        b.append(text(x + 36, yl + 20, label, 18, MUTED))
    totals_y = yl + 70
    b.append(text(x0 - 16, totals_y, "score", 18, INK, "end", 500))
    for i, run in enumerate(s["runs"]):
        b.append(text(colx[i] + cw / 2, totals_y, f"{run['score']:.0%}", 20, INK, "middle", 500))
    return svg(1100, totals_y + 30, b, "Pass and fail for every trial: 20 tasks by 5 runs")


def fig_intervals(s):
    """Each run's score with the Wilson interval, and the usual +/-1.96 SE interval for comparison."""
    rows = [(short(r["job"]), r["score"], r["wilson"], r["normal"]) for r in s["runs"]]
    p = s["pooled"]
    rows.insert(len([r for r in s["runs"] if r["job"].startswith("limits")]),
                (f"Limits on, all {p['k']} runs", p["mean"],
                 [p["mean"] - S.Z95 * p["se_clustered"], p["mean"] + S.Z95 * p["se_clustered"]], None))
    x0, w, y0, rh = 400, 620, 150, 70
    lo_all = min([r[2][0] for r in rows] + [r[3][0] for r in rows if r[3]])
    vmin = max(0.0, math.floor(lo_all * 10) / 10 - 0.1)  # start the axis just below the lowest interval
    sx = lambda v: x0 + (max(vmin, min(1.1, v)) - vmin) / (1.05 - vmin) * w  # noqa: E731
    b = [text(40, 50, "Each score with its 95% interval", 26, weight=500),
         text(40, 84, "Blue: Wilson interval (one run) or clustered by task (all runs). Grey: the usual ±1.96 standard errors.", 19, MUTED)]
    yb = y0 + len(rows) * rh
    ticks = [round(vmin + i * 0.1, 1) for i in range(int(round((1.0 - vmin) / 0.1)) + 1)]
    for v in ticks:
        b.append(line(sx(v), y0 - 20, sx(v), yb - 20, INK if v == 1.0 else GRID, 2 if v == 1.0 else 1.5))
        b.append(text(sx(v), yb + 10, f"{v:.0%}", 18, MUTED, "middle"))
    for i, (label, m, ci, nci) in enumerate(rows):
        y = y0 + i * rh
        b.append(text(x0 - 100, y + 6, label, 20, INK, "end", 500 if "all" in label else 400))
        b.append(text(x0 - 24, y + 6, f"{m:.0%}", 20, INK, "end", 500))
        if nci:
            b.append(line(sx(nci[0]), y + 18, sx(nci[1]), y + 18, "#a3a3a3", 6))
        b.append(line(sx(ci[0]), y, sx(ci[1]), y, BLUE, 8))
        b.append(f'<circle cx="{sx(m):.1f}" cy="{y}" r="9" fill="{INK}"/>')
    return svg(1100, yb + 40, b, "Scores of each run with 95% intervals")


def fig_power(s):
    """Smallest true difference you'd reliably detect, by number of tasks and attempts per task."""
    within, omega2 = s["pooled"]["within"], s.get("paired", {}).get("omega2", 0.0)
    x0, y0, w, h = 130, 215, 900, 440
    nmin, nmax, ymax = 10, 1000, 0.6
    sx = lambda n: x0 + (math.log10(n) - math.log10(nmin)) / (math.log10(nmax) - math.log10(nmin)) * w  # noqa: E731
    sy = lambda v: y0 + h - min(v, ymax) / ymax * h  # noqa: E731
    b = [text(40, 50, "How big a difference can you detect?", 26, weight=500),
         text(40, 84, "Smallest true difference found 80% of the time at p < 0.05, using the noise measured here", 19, MUTED)]
    for v in (0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6):
        b.append(line(x0, sy(v), x0 + w, sy(v)))
        b.append(text(x0 - 14, sy(v) + 6, f"{v * 100:.0f} pts", 17, MUTED, "end"))
    for n in (10, 20, 50, 100, 200, 500, 1000):
        b.append(line(sx(n), y0, sx(n), y0 + h))
        b.append(text(sx(n), y0 + h + 30, n, 17, MUTED, "middle"))
    b.append(text(x0 + w / 2, y0 + h + 62, "number of tasks (log scale)", 18, MUTED, "middle"))
    b.append(line(x0, sy(0.05), x0 + w, sy(0.05), INK, 2, "6 6"))
    b.append(text(x0 + w - 6, sy(0.05) - 10, "5 points", 17, INK, "end"))
    b.append(line(sx(20), y0, sx(20), y0 + h, INK, 2, "6 6"))
    b.append(text(sx(20) + 8, y0 + 22, f"{len(s['tasks'])} tasks, as in this post", 17, INK))
    for k, colour in ((1, ORANGE), (3, BLUE), (5, AQUA)):
        sdd = S.sd_diff_for_attempts(within, within, omega2, k)
        pts = [(sx(n), sy(S.detectable_difference(n, sdd))) for n in range(nmin, nmax + 1, 2)]
        b.append(f'<polyline fill="none" stroke="{colour}" stroke-width="4" points="'
                 + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + '"/>')
        n5 = S.tasks_needed(0.05, sdd)
        label = f"{k} attempt{'s' if k > 1 else ''} per task: {n5:,} tasks needed to detect 5 points"
        ly = 122 + (k // 2) * 32
        b.append(f'<rect x="40" y="{ly - 9}" width="26" height="8" fill="{colour}"/>')
        b.append(text(76, ly, label, 18, INK))
    return svg(1100, y0 + h + 90, b, "Smallest detectable difference by number of tasks")


def fig_paired(s):
    """The limits-off minus limits-on difference, with unpaired and paired 95% intervals."""
    q = s["paired"]
    rows = [("Unpaired", q["diff"], q["se_unpaired"], "#a3a3a3"),
            ("Paired by task", q["diff"], q["se_paired"], BLUE)]
    x0, w, y0, rh = 300, 700, 150, 80
    lim = 0.4
    sx = lambda v: x0 + (max(-lim, min(lim, v)) + lim) / (2 * lim) * w  # noqa: E731
    b = [text(40, 50, "Limits off minus limits on, with 95% intervals", 26, weight=500),
         text(40, 84, "Same data both times. Pairing compares each task with itself.", 19, MUTED)]
    yb = y0 + len(rows) * rh
    for v in (-0.4, -0.2, 0, 0.2, 0.4):
        b.append(line(sx(v), y0 - 30, sx(v), yb - 20, INK if v == 0 else GRID, 2 if v == 0 else 1.5))
        b.append(text(sx(v), yb + 10, f"{v * 100:+.0f} pts" if v else "0", 18, MUTED, "middle"))
    for i, (label, m, se, colour) in enumerate(rows):
        y = y0 + i * rh
        lo, hi = m - S.Z95 * se, m + S.Z95 * se
        b.append(text(x0 - 20, y + 7, label, 20, INK, "end"))
        b.append(line(sx(lo), y, sx(hi), y, colour, 10))
        b.append(f'<circle cx="{sx(m):.1f}" cy="{y}" r="9" fill="{INK}"/>')
        b.append(text(sx(hi) + 14, y + 7, f"{100 * lo:+.0f} to {100 * hi:+.0f}", 18, MUTED))
    return svg(1100, yb + 40, b, "Difference between the two settings with unpaired and paired intervals")


def main():
    s = json.loads((ROOT / "results" / "summary.json").read_text())
    OUT.mkdir(exist_ok=True)
    figs = {"fig2-grid": fig_grid, "fig3-intervals": fig_intervals, "fig4-paired": fig_paired, "fig5-power": fig_power}
    for name, fn in figs.items():
        if name == "fig4-paired" and "paired" not in s:
            continue
        (OUT / f"{name}.svg").write_text(fn(s))
        print(f"wrote figures/{name}.svg")


if __name__ == "__main__":
    main()
