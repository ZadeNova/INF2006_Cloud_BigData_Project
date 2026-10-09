# LOAD-fargate-saturation-r1_2026-10-09

**What this run was:** Saturation of one task (2 vCPU, 4 GB): ten steps of 120 s at 1, 2, 4, 8, 16, 32, 64, 128, 256 and 512 users, no think time, capacity pinned to 1 / 1 / 1.

| Item | Value |
|---|---|
| Run id | `LOAD-fargate-saturation-r1_2026-10-09` |
| Variant | B (ECS on Fargate) |
| Type | `saturation` |
| Started / ended (UTC) | 2026-10-09T06:23:23.999Z / 2026-10-09T06:43:26.106Z |
| Command | `run.py saturation --variant fargate --base-url https://shop-fargate.fourtytwofactors.me --repeat 1 --location us-east-1` |
| Image digest | `sha256:fa72e949b47de9cb5c6378608072cb3b376503de8dc11bbb34b98940ea8cb481` (see `stack.json`) |
| Headline numbers (from `analyze.py`) | Practical capacity 8 users (44.01 page actions/s); maximum throughput 105.5 requests/s at 512 users; 0 errors at every step; RDS CPU at most 9.09 percent, task CPU 93 to 96 percent from 06:29 UTC. At 512 users the task failed health checks twice and ECS replaced it (see `ecs_events.json` and `targets.jsonl`). |

## The six key files

| # | File | What it holds |
|---|---|---|
| 1 | `run.json` | what was run: schedule, seed, commit, `git_dirty_harness`, exact command, generator, start and end |
| 2 | `stack.json` | what it ran on: image digest, database class, capacity (min, max, desired), WAF mode, export window |
| 3 | `timing.json` | the run's start and end times (epoch and UTC) |
| 4 | `targets.jsonl` | target health over time, including the two `unhealthy` records at 512 users |
| 5 | `locust_stats.csv` | Locust's per-request-name summary (counts, failures, percentiles). The per-request log `requests-2572.csv, requests-2573.csv` is what `analyze.py` reads |
| 6 | `cloudwatch/` and `alarm_history.json`, `ecs_events.json` | one-minute CloudWatch metrics (load balancer, CPU, RDS, WAF) as CSV; the alarm state changes; the ECS service events, including "replaced 1 tasks due to an unhealthy status" at 06:43:30 UTC |

Everything else in the folder (`cpu.json`, `generator_cpu.csv`, `locust_failures.csv`, `locust_exceptions.csv`, `locust_stats_history.csv`, `report.html`) is supporting detail. No file in this folder was edited or renamed after export.

**Notes:** `run.json` records `git_dirty_harness: true` (the steps were edited into `run.py` on the generator).

**Reproduce the numbers:** from the repository root run `python tests/load/analyze.py --raw evidence/raw` (read-only; add `--out some-file.md` to write the tables to a file); the rows for `LOAD-fargate-saturation-r1_2026-10-09` are the headline numbers above and match [evidence/load-summary.md](../../load-summary.md).
