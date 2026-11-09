# Evaluation card

## What was measured
- Benchmark: OpenThoughts-TBLite, commit `f075e463472c7790b85793b392dff1fff20cc0e3`, 20 tasks picked with `scripts/pick_tasks.py` (seed 2026) and kept by `scripts/preflight.py`
- Score: share of trials where the task's tests pass (reward 1). Errors count as failures and are listed below.
- Runs: limits-1, nolimits-1, limits-2, nolimits-2, limits-3, one attempt per task per run, in that order
- Time window: 2026-10-25T23:58:22.047657Z to 2026-10-26T01:38:10.892577Z (UTC)

## Agent and model
- Harness: Harbor 0.24.0, agent `terminus-2` version 2.0.0
- Model: `claude-haiku-5-5` from provider `anthropic` (Anthropic API, called through LiteLLM 1.106.2)
- Sampling: no temperature sent, so the API default applies (the API rejected temperature 0, see results/sampling.txt)
- Effort and thinking: not set, so the model default applies (adaptive thinking)
- max_tokens per call: LiteLLM default for this model (128,000)

## Environment
- Docker 27.5.1 on Docker Desktop (aarch64), 10 CPUs and 7.7 GB for Docker
- Trials at once: 3
- Retries: 0 (a failed trial is not rerun)
- Timeouts: task defaults, multiplier 1.0
- Resources, `limits` runs: each task's declared CPUs and memory are hard limits (Harbor's default on Docker)
- Resources, `nolimits` runs: `--cpus ignore --memory ignore`, so containers share the whole Docker machine
- Network: task defaults. 55 of the 100 TBLite verifiers download tools while grading, so grading needs internet access.

## Results
| Run | Passed | Score | 95% Wilson interval | Timeouts or errors | Cost |
|---|---|---|---|---|---|
| limits-1 | 18/20 | 90% | 70% to 97% | 1 | $0.19 |
| limits-2 | 16/20 | 80% | 58% to 92% | 1 | $0.57 |
| limits-3 | 16/20 | 80% | 58% to 92% | 1 | $0.20 |
| nolimits-1 | 18/20 | 90% | 70% to 97% | 1 | $0.17 |
| nolimits-2 | 18/20 | 90% | 70% to 97% | 0 | $0.18 |

- All `limits` runs together: 83.3%, clustered standard error 6.9% (60 trials on 20 tasks); solved every time: 15, never: 1
- `nolimits` minus `limits`, paired by task: +6.7 points, 95% bootstrap interval -0.8 to +17.5, sign-flip p = 0.31
- Total cost: $1.31 for 100 trials

## Task digests (from Harbor's lock.json)
- `california-housing-api` sha256:dcffb2f3d909b425150dada11962c877500e864602690ea21cb71a0afaecc4a4
- `malicious-package-forensics` sha256:d1da6258885119e2830221bbc3b6f9ec71e5339b7d062358bc1cfd1b4ac9f657
- `reproducibility-and-envsetup` sha256:5710be79268ca2e41a72899f93d896377cd5bc721b2b01f56bc726b2a3bfa811
- `task-xxe-exploit` sha256:2aee4e1b1201d036a5cfe42e3c0697ae193a75e7684b0dcee06b485c263089c6
- `build-system-task-ordering` sha256:70426218d51e0aaae7898a399caa1078a83d5205bd5f4db517dceef484ed9d31
- `csv-json-jsonl-merger` sha256:7297201b0ed8f5dd49e1e65edb0032195e04bbd7fb8fae607d8a4a45e06810cd
- `scan-linux-persistence-artifacts` sha256:5e3068b5c4432d03086904f13e3d797b09764096681a60a4592974b1dda1552f
- `neural-architecture-search-final` sha256:f2784ca27241f77d9db7edea62f294b1f267a863850c5bcc9ccf34813ed5f329
- `sign-vector-game` sha256:20fd0097adde00f69d23e2eb85d8e861d3423144a30a528a6c94b17aeda4946c
- `db-migration-local-storage` sha256:919811881022619df630245fd82cf9aacedc0dc51da76aa1d7e9a7dccc738e80
- `api-endpoint-permission-canonicalizer` sha256:2ffa6062295c7c6bdf6cc3047a22ed1894e73181b6db4d7f90b0f85a2719669d
- `industrial-kiln-controller` sha256:fb22ceb0f72ce5dd51d4379a4602ad1625decd7e9b4e5c0df89e179301ca952f
- `bandit-delayed-feedback` sha256:92cf08d99d1ba67c8b3deffbebded451f2322731232916aa974583ab2c687b66
- `container-registry-optimization` sha256:370b738b4209216b700bda43a558466ae6589d356fbbbae6871b8f912e4f67a1
- `service-deployment-wave-planner` sha256:81c5a08297de18914fa250652486aed99c86dd998a9ee8cfc47fa5d2d76d3f03
- `submission_a63937a5_20251224_152124` sha256:dd1452432dadc3cfaada89a66507eb5a0d3cd809ce58ed10e58f378148bba852
- `rsa-jwt-token-api-redis-blacklist` sha256:cd8f2bfcd3f958c551bb9a1acaf3edd85889f4bf5c2cedb99bc388dc15872604
- `maven-slf4j-conflict` sha256:70f945e7809c3fcf6f7efcc8b028bea16c4cf2d863259fa8884d90bb3037549a
- `systemd-log-monitoring` sha256:bc0b74562950aa6613cfa736b08492f64e48f7a75da298f368fb9253b0baa045
- `convolutional-layers` sha256:f5821793108c2e325d76e77c49b6b3ed299f95a198f193c681618a8294e92a4e

## Known limits
- 20 tasks is small: with one run per side, a true difference under about 23 points is likely to be missed (section 5 of analyze.py).
- One machine and one time window (above). Another Docker host, provider or day may give different results.
- OpenThoughts-TBLite and its tasks are public, so the model may have seen them in training.
