# agent-benchmark-noise

Companion code for the blog post on measuring benchmark noise for models and agent harnesses
on [alidarbehani.com](https://alidarbehani.com).

It runs one agent on 20 tasks from [OpenThoughts-TBLite](https://github.com/open-thoughts/OpenThoughts-TBLite)
five times with [Harbor](https://github.com/harbor-framework/harbor), changing nothing between runs except
the container resource limits, and then works out how much of the score is noise.

## What you need

- Docker with at least 4 CPUs and 8 GB of memory
- `git` and [`uv`](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- An Anthropic API key in a file called `.env` (copy `.env.example`)

The full run is about 100 agent trials with Claude Haiku 5.5. On my MacBook Pro (Apple Silicon, Docker
Desktop with 10 CPUs and 7.7 GB) the task check took 15 minutes, the five runs took 1 hour 40 minutes, and
the model calls cost $1.31.

## Run it

```bash
git clone https://github.com/alireza1989/agent-benchmark-noise
cd agent-benchmark-noise
./run_all.sh --analyze      # redo the post's analysis from the runs in jobs/, no API key needed
```

`jobs/` holds the runs from the post: every trial's transcript, test output, tokens and cost. So
`./run_all.sh --analyze` reproduces every number in the post, and you can read any transcript it mentions.

To do your own runs, move the post's runs and results out of the way first. Otherwise `run_all.sh` sees
them and skips every job as already done.

```bash
mv jobs jobs-post && mv results results-post
cp .env.example .env        # then put your key in it
./run_all.sh --preflight    # check the tasks work on your machine, no API calls
./run_all.sh                # everything else
```

`run_all.sh` skips any job that already finished, so you can stop it and run it again later.
`./run_all.sh --analyze` redoes only the analysis, the evaluation card and the figures.

## What it does

| Step | Script | Output |
|---|---|---|
| Pick 28 candidate tasks that declare CPU or memory limits (seed 2026) | `scripts/pick_tasks.py` | `results/candidates.txt` |
| Run each candidate's reference solution (`oracle`) and an agent that does nothing (`nop`) | `harbor run` | `jobs/preflight-*` |
| Keep the first 20 tasks where the oracle passes and nop fails | `scripts/preflight.py` | `results/tasks.txt` |
| Ask the model for temperature 0, then send one request 10 times | `scripts/sampling_check.py` | `results/sampling.txt` |
| One agent trial end to end, to catch key or setup errors | `scripts/smoke_check.py` | `jobs/smoke` |
| Five runs, alternating: limits on, off, on, off, on | `harbor run` | `jobs/limits-*`, `jobs/nolimits-*` |
| Error bars, A/A comparisons, paired test, how many tasks you'd need, cost | `scripts/analyze.py` | `results/analysis.txt`, `results/summary.json` |
| Every setting needed to reproduce the runs | `scripts/eval_card.py` | `results/eval-card.md` |
| How the agent created virtual environments in `reproducibility-and-envsetup`, run by run | `scripts/venv_lines.py` | `results/venv-lines.txt` |
| The data figures in the post | `scripts/figures.py` | `figures/*.svg` |

`scripts/stats.py` holds the statistics (Wilson interval, clustered standard error, McNemar test, sign-flip
test, bootstrap, ICC, power). It uses only the Python standard library, and `tests/test_stats.py` checks it
against SciPy and hand-worked examples: `python -m pytest -q tests`.

## Settings

| Variable | Default | What it changes |
|---|---|---|
| `MODEL` | `anthropic/claude-haiku-5-5` | Any LiteLLM model name Harbor's `terminus-2` agent accepts |
| `N_CONCURRENT` | `3` | Trials at once. Keep it the same for every run you compare. |

Versions are pinned in `requirements.txt` (Harbor 0.24.0, LiteLLM 1.106.2) and the benchmark is pinned to
the OpenThoughts-TBLite commit that Harbor's registry uses for `openthoughts-tblite@2.0`.

## Results from the post

Harbor 0.24.0, LiteLLM 1.106.2, Claude Haiku 5.5, October 25, 2026. `results/` has the full output.

- Task check: the reference solution failed on 5 of 28 candidates on my Mac (a chip-specific checksum, an
  unpinned `redis`, an `npm install` crash while grading, and two task bugs). The first 20 that worked were kept.
- Three identical runs with limits on scored 90%, 80% and 80%. Two runs with limits off scored 90% and 90%.
- Limits off minus limits on, paired by task: +6.7 points, sign-flip p = 0.31. Five of those points come from
  `reproducibility-and-envsetup`, whose test looks for the literal text `python -m venv`. The agent wrote
  `python3 -m venv` in all three limits-on runs and `python -m venv` in both limits-off runs.
- With one run per setup, 20 tasks can only reliably detect a difference of about 23 points. Detecting 5 points
  needs about 419 tasks at one attempt each, or 140 at three.
- One trial (`build-system-task-ordering`, limits-2) ran 416 turns and cost $0.37 of the $1.31 total.

The agent's runs are random, so yours will differ. That's the point.

## License

Code is MIT. OpenThoughts-TBLite is Apache 2.0 and is downloaded at run time, not stored here.
