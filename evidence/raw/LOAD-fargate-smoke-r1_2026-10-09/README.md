# LOAD-fargate-smoke-r1_2026-10-09

**What this run was:** FUNC-03 part 1: 2 virtual users for 75 s from the laptop (buyer, abandoner, shopper visit orders) against the live shop.

| Item | Value |
|---|---|
| Run id | `LOAD-fargate-smoke-r1_2026-10-09` |
| Variant | B (ECS on Fargate) |
| Type | `smoke` |
| Started / ended (UTC) | 2026-10-09T02:04:53.281Z / 2026-10-09T02:06:08.595Z |
| Command | `run.py smoke --variant fargate --base-url https://shop-fargate.fourtytwofactors.me --repeat 1 --location laptop --yes` |
| Image digest | `sha256:fa72e949b47de9cb5c6378608072cb3b376503de8dc11bbb34b98940ea8cb481` (see `stack.json`) |
| Headline numbers (from `analyze.py`) | 104 requests, 0 errors, 2 orders placed, 0 stock conflicts. The per-action summary is `../FUNC-03_2026-10-09_fargate_summary.txt`. |

## The six key files

| # | File | What it holds |
|---|---|---|
| 1 | `run.json` | what was run: schedule, seed, commit, `git_dirty_harness`, exact command, generator, start and end |
| 2 | `stack.json` | what it ran on: image digest, database class, capacity (min, max, desired), WAF mode, export window |
| 3 | `timing.json` | the run's start and end times (epoch and UTC) |
| 4 | (none in this folder) | no target-health record was captured, so this run has only five of the six files |
| 5 | `locust_stats.csv` | Locust's per-request-name summary (counts, failures, percentiles). The per-request log `requests-287933.csv` is what `analyze.py` reads |
| 6 | `cloudwatch/` and `alarm_history.json`, `ecs_events.json` | one-minute CloudWatch metrics (load balancer, CPU, RDS, WAF) as CSV; the alarm state changes; the ECS service events in the export window (not a scaling test) |

Everything else in the folder (`cpu.json`, `generator_cpu.csv`, `locust_failures.csv`, `locust_exceptions.csv`, `locust_stats_history.csv`, `report.html`) is supporting detail. No file in this folder was edited or renamed after export.

**Notes:** There is no `targets.jsonl` in this folder: no target-health record was captured for the smoke run. `run.json` records `git_dirty_harness: true`.

**Reproduce the numbers:** from the repository root run `python tests/load/analyze.py --raw evidence/raw` (read-only; add `--out some-file.md` to write the tables to a file); the rows for `LOAD-fargate-smoke-r1_2026-10-09` are the headline numbers above and match [evidence/load-summary.md](../../load-summary.md).
