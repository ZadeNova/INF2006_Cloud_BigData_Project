# RES-03-fargate-replace-r1_2026-10-09

**What this run was:** Replacement: 100 users for 20 minutes with two tasks; one is stopped gracefully 300 s into the run, and the run continues until two healthy tasks are back.

| Item | Value |
|---|---|
| Run id | `RES-03-fargate-replace-r1_2026-10-09` |
| Variant | B (ECS on Fargate) |
| Type | `replace` |
| Started / ended (UTC) | 2026-10-09T03:12:27.117Z / 2026-10-09T03:32:29.514Z |
| Command | `run.py replace --variant fargate --base-url https://shop-fargate.fourtytwofactors.me --repeat 1 --location us-east-1` |
| Image digest | `sha256:fa72e949b47de9cb5c6378608072cb3b376503de8dc11bbb34b98940ea8cb481` (see `stack.json`) |
| Headline numbers (from `analyze.py`) | 7,474 requests, 0 errors. Kill to detected 18 s, replacement 50 s (stop to two healthy), error window 0 s, errors in the window 0, errors later in the run 0. |

## The six key files

| # | File | What it holds |
|---|---|---|
| 1 | `run.json` | what was run: schedule, seed, commit, `git_dirty_harness`, exact command, generator, start and end |
| 2 | `stack.json` | what it ran on: image digest, database class, capacity (min, max, desired), WAF mode, export window |
| 3 | `timing.json` | the run's start and end times (epoch and UTC) |
| 4 | `targets.jsonl` and `kill.json` | target health over time; `kill.json` is the removal itself (time, unit, graceful) |
| 5 | `locust_stats.csv` | Locust's per-request-name summary (counts, failures, percentiles). The per-request log `requests-5254.csv, requests-5255.csv` is what `analyze.py` reads |
| 6 | `cloudwatch/` and `alarm_history.json`, `ecs_events.json` | one-minute CloudWatch metrics (load balancer, CPU, RDS, WAF) as CSV; the alarm state changes; the ECS service events (deregistered, draining, replacement started, registered) |

Everything else in the folder (`cpu.json`, `generator_cpu.csv`, `locust_failures.csv`, `locust_exceptions.csv`, `locust_stats_history.csv`, `report.html`) is supporting detail. No file in this folder was edited or renamed after export.

**Notes:** `run.json` records `git_dirty_harness: true`.

**Reproduce the numbers:** from the repository root run `python tests/load/analyze.py --raw evidence/raw` (read-only; add `--out some-file.md` to write the tables to a file); the rows for `RES-03-fargate-replace-r1_2026-10-09` are the headline numbers above and match [evidence/load-summary.md](../../load-summary.md).
