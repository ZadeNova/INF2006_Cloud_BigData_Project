# LOAD-ec2-saturation-r1_2026-10-08

**What this run was:** Saturation of one instance: ten steps of 120 s at 1, 2, 4, 8, 16, 32, 64, 128, 256 and 512 users, no think time, capacity pinned to 1 / 1 / 1.

| Item | Value |
|---|---|
| Run id | `LOAD-ec2-saturation-r1_2026-10-08` |
| Variant | A (EC2 with an Auto Scaling group) |
| Type | `saturation` |
| Started / ended (UTC) | 2026-10-08T18:20:57.968Z / 2026-10-08T18:41:00.237Z |
| Command | `run.py saturation --variant ec2 --base-url https://shop-ec2.fourtytwofactors.me --repeat 1 --location us-east-1` |
| Image digest | `sha256:fa72e949b47de9cb5c6378608072cb3b376503de8dc11bbb34b98940ea8cb481` (see `stack.json`) |
| Headline numbers (from `analyze.py`) | Practical capacity 16 users (46.54 page actions/s); maximum throughput 118.8 requests/s at 512 users; 0 errors at every step; RDS CPU at most 10.46 percent, instance CPU about 94 percent from 18:28 UTC. |

## The six key files

| # | File | What it holds |
|---|---|---|
| 1 | `run.json` | what was run: schedule, seed, commit, `git_dirty_harness`, exact command, generator, start and end |
| 2 | `stack.json` | what it ran on: image digest, database class, capacity (min, max, desired), WAF mode, export window |
| 3 | `timing.json` | the run's start and end times (epoch and UTC) |
| 4 | `targets.jsonl` | target health over time (only the initial record; the ALB metric shows a brief dip at 18:39 UTC in `cloudwatch/alb_healthy_hosts.csv`) |
| 5 | `locust_stats.csv` | Locust's per-request-name summary (counts, failures, percentiles). The per-request log `requests-33827.csv, requests-33828.csv` is what `analyze.py` reads |
| 6 | `cloudwatch/` and `alarm_history.json`, `scaling_activities.json` | one-minute CloudWatch metrics (load balancer, CPU, RDS, WAF) as CSV; the alarm state changes; Auto Scaling activities (none expected; capacity was pinned) |

Everything else in the folder (`cpu.json`, `generator_cpu.csv`, `locust_failures.csv`, `locust_exceptions.csv`, `locust_stats_history.csv`, `report.html`) is supporting detail. No file in this folder was edited or renamed after export.

**Notes:** `run.json` records `git_dirty_harness: true`: the 512-user step was edited into `run.py` on the generator and committed afterwards.

**Reproduce the numbers:** from the repository root run `python tests/load/analyze.py --raw evidence/raw` (read-only; add `--out some-file.md` to write the tables to a file); the rows for `LOAD-ec2-saturation-r1_2026-10-08` are the headline numbers above and match [evidence/load-summary.md](../../load-summary.md).
