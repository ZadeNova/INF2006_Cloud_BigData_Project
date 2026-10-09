# Performance and scaling evidence (load tests)

**Status (9 October 2026):** both variants were measured, one repeat each: variant A (EC2) on 8 October 2026 and variant B (ECS on Fargate) on 9 October 2026 (UTC): scale-out, replacement and saturation. The "Expected result" cells were written before any run and are unchanged. The harness is described in [tests/load/README.md](../tests/load/README.md); plan, decisions, thresholds and weights are in [docs/plans/load-harness.md](../docs/plans/load-harness.md). All tables from the raw files are generated in [load-summary.md](load-summary.md) by `python tests/load/analyze.py --raw evidence/raw --out evidence/load-summary.md`. Each run folder has a `README.md` naming its key files. **Every A-versus-B difference is indicative, n = 1**; this file records both variants side by side and does not choose between them (that decision is in [docs/decisions/](../docs/decisions/)).

## Results at a glance

| Case | What it proves | Result on A (EC2) | Result on B (Fargate) | Date (UTC) | Key artefact A | Key artefact B |
|---|---|---|---|---|---|---|
| RES-03a scale-out | The service adds a second healthy unit by itself after a load step | **PASS** for scale-out: alarm 299 s after the step, scaling action 64 s after the alarm, second unit healthy 161 s after the alarm (460 s after the step), 0 errors. Scale-in not observed | **PASS** for scale-out: alarm 305 s after the step, scaling action 67 s after the alarm, second unit healthy 101 s after the alarm (407 s after the step), 0 errors. Scale-in observed after the run (task stopped 03:03:08 UTC) | A 2026-10-08; B 2026-10-09 | `raw/RES-03-ec2-scaleout-r1_2026-10-08/` | `raw/RES-03-fargate-scaleout-r1_2026-10-09/` |
| RES-03b replacement | One of two units removed under 100 users is replaced without failed requests | **PASS**: removal seen in 2 s, two healthy again in 114 s, error window 0 s, 0 errors. Graceful removal, not a crash | **PASS**: removal seen in 18 s, two healthy again in 50 s, error window 0 s, 0 errors. Graceful removal, not a crash | A 2026-10-08; B 2026-10-09 | `raw/RES-03-ec2-replace-r1_2026-10-08/` | `raw/RES-03-fargate-replace-r1_2026-10-09/` |
| LOAD-03 saturation | Capacity of one unit and its limiting resource | **Measured**: practical capacity 16 users (46.54 page actions/s), maximum 118.8 requests/s at 512 users, 0 errors at every step; instance CPU about 94 percent, RDS CPU at most 10.46 percent | **Measured**: practical capacity 8 users (44.01 page actions/s), maximum 105.5 requests/s at 512 users, 0 errors at every step; task CPU about 94 to 96 percent, RDS CPU at most 9.09 percent | A 2026-10-08; B 2026-10-09 | `raw/LOAD-ec2-saturation-r1_2026-10-08/` | `raw/LOAD-fargate-saturation-r1_2026-10-09/` |
| LOAD-01 RDS pilot (1,000 users) | The database is not the bottleneck | **Not run.** The saturation run read RDS CPU instead: 10.46 percent at most while one unit was saturated | **Not run.** The saturation run read RDS CPU instead: 9.09 percent at most while one unit was saturated | A 2026-10-08; B 2026-10-09 | `raw/LOAD-ec2-saturation-r1_2026-10-08/cloudwatch/rds_cpu_max_stat.csv` | `raw/LOAD-fargate-saturation-r1_2026-10-09/cloudwatch/rds_cpu_max_stat.csv` |
| LOAD-02 ladder (1, 10, 100, 1,000 users, 3 repeats) | Latency at matched compute | **Not run** (dropped for time; LOAD-03 replaced it) | **Not run** (dropped for time; LOAD-03 replaced it) | | | |
| LOAD-04 Singapore latency | Cost of hosting in us-east-1 for a Singapore customer | **Not run** | **Not run** | | | |

No rerun or failed-attempt run folders exist: each run was run once and [load-summary.md](load-summary.md) marks all of them "valid". The FUNC-03 smoke runs (`raw/LOAD-ec2-smoke-r1_2026-10-08/`, `raw/LOAD-fargate-smoke-r1_2026-10-09/`) are reported in [test-functional.md](test-functional.md). Failed attempts that are not run folders (a failed `up.sh ec2`, a failed capacity-pin plan on B because of uncommitted changes, another on B with AccessDenied errors) are listed in [raw/INDEX.md](raw/INDEX.md).

## Honest limits of these results

| Limit | Effect |
|---|---|
| One repeat per condition (n = 1) | Every A-versus-B difference is "indicative, n = 1". The min-max tie rule cannot apply and no weighted total is quoted as a decision. |
| Replacement is a graceful removal (ADR-017) | It shows drain, replacement and error window, not crash detection. |
| Database state: CPU credits and cache not reset; shop data reset at different points | Credits stayed at 576 on both variants. Orders and carts were reset with `tests/load/reset_state.py` (`raw/OPS_*_reset-*`): A before its saturation run, B only after it, so B's saturation run started with the orders of B's earlier runs still present (the pre-reset counts are in `raw/OPS_2026-10-09_fargate_reset-dry.txt`). |
| 3D models not fetched | The app serves 12 model files (about 15 MB); the load test does not request them, so real pages are heavier than the load test's. |
| Ladder dropped; saturation edited on the generator | Saturation used steps 1, 2, 4, 8, 16, 32, 64, 128, 256, 512 users, edited into `run.py` on the generator, so the saturation `run.json` files show `git_dirty_harness: true`. B's scale-out and replacement runs also show `true`; A's do not. The harness commit on the laptop (`0276f52`) was changed afterwards to match the steps. |
| Scaling target set before any data | 300 requests per target per minute is 5 requests per second, a small fraction (about 4 to 5 percent) of the measured ceilings of 118.8 (A) and 105.5 (B) requests per second; scale-out fired at 14.56 percent (A) and 14.04 percent (B) CPU at most. |
| Different CPU models | A: Intel Xeon Platinum 8124M at 3.0 GHz. B: Intel Xeon Platinum 8259CL at 2.5 GHz (read from a one-off task; the tasks that served the load may differ). A possible contributing explanation for B's roughly 10 percent lower ceiling; not separable from the platform at n = 1. |
| Generator in us-east-1, WAF in count mode for the runs, one source IP | Latency excludes the internet path to Singapore. The WAF block test (SEC-17) was run on B only, after its saturation run, because the WAF is one shared module. |
| Prices are list prices | `tests/load/prices.json` was checked on 9 October 2026 and confirmed by the user (`verified_by_user: true`). They are on-demand list prices; the Learner Lab is billed in credits, and storage, data transfer, load-balancer capacity units and WAF requests are excluded. |

## Conditions common to every recorded run

Fill once per campaign; a change of any item means the affected runs are rerun or marked superseded (AGENTS.md: the image is pinned).

| Item | Value | Recorded on A | Recorded on B |
|---|---|---|---|
| Image digest (both variants) | `sha256:fa72e949b47de9cb5c6378608072cb3b376503de8dc11bbb34b98940ea8cb481` (tag `release-c19d547`) | `image_digest` in every A `stack.json`; `raw/PRE_2026-10-08_image.txt`; `raw/SESSION_2026-10-08_ec2_ids.txt` | the same digest in every B `stack.json`; `raw/SESSION_2026-10-09_fargate_ids.txt` |
| Git commit of the harness / infrastructure | Harness at run time (`git_commit` in `run.json`) | scale-out, replacement and saturation `81c0e2a` (saturation dirty); smoke `74d394a` (dirty). Infrastructure applied from `74d394a` (up), `4e06901` (pins), `3c910b8` (teardown) | scale-out, replacement and saturation `81c0e2a` (all dirty); smoke `33963c5` (dirty). Infrastructure applied from `33963c5` (up) and `e4bc928` (later pins, teardown) |
| RDS instance class, engine version, Multi-AZ | `db.t4g.small`, PostgreSQL 17.9, Multi-AZ off | `stack.json`; `raw/SEC-09_2026-10-08_ec2_rds.txt` | `stack.json`; `raw/SEC-09_2026-10-09_fargate_rds.txt` |
| Region | us-east-1 | `run.json` generator location | `run.json` generator location |
| A: instance type; B: task size | A c5.large (2 vCPU, 4 GiB); B Fargate 2 vCPU / 4 GB | `instance_type` in `stack.json` | `task_cpu` 2048 and `task_memory_mb` 4096 in `stack.json` |
| Capacity during saturation | one unit (min = max = 1) | saturation `stack.json`: min 1, max 1, desired 1 | saturation `stack.json`: min 1, max 1, desired 1 |
| Scale-out load step (`--users-high`) | 200 users | scale-out `run.json` stages: 10, 200, 10 users | scale-out `run.json` stages: 10, 200, 10 users |
| WAF rule on `POST /login/` | count mode, limit 20 per 5 min per IP | `waf_login_action: Count`, `waf_login_limit: 20` in every `stack.json` | the same in every run `stack.json`; block mode only for SEC-17 (`raw/OPS_2026-10-09_fargate_pin-1-1-1-block_*`) |
| Load generator (type, region, clock offset) | c5.large, us-east-1, one Locust process | clock offset -0.001 ms (scale-out, replacement) and 0.002 ms (saturation) | clock offset -0.0 ms (scale-out), -0.006 ms (replacement), 0.0 ms (saturation) |
| Workload | 90% window shoppers, 7.5% cart abandoners, 2.5% buyers; 36 s think time (scale-out, replacement) and no think time (saturation, by design); seed 42 | `plan` block and `seed` in `run.json` | `plan` block and `seed` in `run.json` |
| CPU model of the serving unit | A: Intel Xeon Platinum 8124M @ 3.00 GHz; B: Intel Xeon Platinum 8259CL @ 2.50 GHz; 2 vCPU each | `raw/RES-03-ec2-scaleout-r1_2026-10-08/cpu.json` | `raw/RES-03-fargate-scaleout-r1_2026-10-09/cpu.json` |
| Thresholds | p95 under 800 ms; p99 under 1.8 s (at least 1,000 samples); checkout p95 under 2 s; errors under 1% | applied by `analyze.py` | applied by `analyze.py` |
| Comparison weights (locked 3 October 2026) | operational burden 25, replacement and error window 25, latency 20, cost 15, scale-out 10, capacity 5 | `WEIGHTS` in `tests/load/analyze.py` | `WEIGHTS` in `tests/load/analyze.py` |
| Prices verified by (name, date) | **Verified by the user, 9 October 2026** against the AWS pricing pages (Fargate, load balancer, public IPv4) and public price trackers (c5.large, RDS db.t4g.small); `verified_by_user: true` | `tests/load/prices.json` | `tests/load/prices.json` |

Three of the A run folders (smoke, scale-out, replacement) contain `<ACCOUNT>` in place of some averages in `locust_stats.csv`, `locust_stats_history.csv` and `report.html`: the redaction rule then mistook a 12-digit decimal fraction for an account number. Fixed in `tests/load/common.py` in commit `0276f52`; the saturation export on A and all B exports are clean. The request logs `requests-*.csv`, which `analyze.py` reads, are not affected; `raw/` was not edited.

## Checklist before every recorded run (identical on both variants, review EVD-010)

Read it aloud before each run; the run's own files record most of it (`run.json`, `stack.json`, `targets.jsonl`).

1. Only the variant under test is up and taking load; the generator is the same instance for A and B.
2. Capacity pinned for the run type with `evidence.sh <variant> pin` (ladder 1 1 1; replacement 2 2 2; scale-out 1 2 1), WAF `count`. `pin` waits for the healthy count; start the run **3 minutes** after it prints "Healthy".
3. `aws_capture.py watch` started on the laptop **before** `run.py`, for every run type (not only scale-out and replacement), so every run has its exact healthy-target record.
4. Lab credentials refreshed (`labcreds`) before every scale-out or replacement run; the session timer shows at least the run length plus 25 minutes.
5. Carts reset from the previous run (`accounts.py reset-carts --from-run out/<previous run id>`).
6. Scale-out always with `--users-high 200` (the default; fixed now because the pilot is not run first).
7. The kill command typed and ready (`aws_capture.py kill --variant <v> --run-id <ID>`) before a replacement run starts.
8. After the run: copy the run folder to the laptop and `aws_capture.py export` it **before** any further pin, apply or `down`.

## Campaign 1 scope (decided 8 October 2026, after the readiness review)

The plan's full matrix (three repeats of four ladder levels, saturation and Singapore on each variant, about 13 to 15 hours of lab time) does not fit the time left. Campaign 1 runs the same reduced set on both variants, in the same order: scale-out r1, replacement r1, **saturation r1** (chosen on 9 October, with the lab window running out, in place of ladder u100 and u10: it finds one unit's capacity and failure point and gives p95 at every step, light load included). The ladder, repeats (r2), Singapore and the 1,000-user RDS pilot are added only if time allows, always on both variants. Consequences, stated in the report:

- With one repeat per condition the min-max tie rule cannot apply, so every A-against-B difference is labelled **indicative, n = 1**, and the weighted total is not quoted as a decision without a second repeat.
- The RDS pilot gate (LOAD-01) is replaced by reading RDS CPU in the saturation run on one unit; the database headroom at 1,000 users is not measured.
- Without the ladder, the steady-state latency criterion is judged from the saturation steps (p95 at 1 to 16 users) and the scale-out run's light-load phase; there is no think-time latency at 10 and 100 users, and the report says so.
- Costs use list prices checked on 9 October 2026 (`tests/load/prices.json`); the lab's own closing balance (USD 9.8 of 50 used) is the real spend.

## Cases

### LOAD-01: RDS pilot gate

| Field | |
|---|---|
| Objective | Show the database is not the bottleneck at the 1,000-user step on one unit |
| Setup | Variant A, one unit, WAF in count mode, accounts created, carts reset |
| Command / steps | `python run.py pilot --variant ec2 --base-url $LOAD_BASE_URL --repeat 1 --location us-east-1` |
| Expected result | RDS CPU at most 40% on one saturated unit (projects to about 80% with two units); connections and freeable memory not trending to the limit |
| Actual result | **Not run.** The 1,000-user pilot was replaced by reading RDS CPU in the saturation run (campaign scope above). With one unit saturated, RDS CPU was at most 10.46 percent (`cloudwatch/rds_cpu_max_stat.csv`, 18:40 UTC), RDS connections at most 2 (`rds_connections.csv`) and freeable memory stayed between 9.84e8 and 9.94e8 bytes (`rds_freeable_memory.csv`). The criterion (at most 40 percent on one saturated unit) is met by this observation, but at the 118.8 requests per second one unit can serve, not at 1,000 users. **Variant B:** with one task saturated, RDS CPU was at most 9.09 percent (`cloudwatch/rds_cpu_max_stat.csv`, 06:31 UTC), RDS connections at most 2 and freeable memory between 9.87e8 and 9.97e8 bytes; the same conclusion, with the same limit. |
| Date | A 2026-10-08, B 2026-10-09 (observations inside the saturation runs) |
| Artefact path | `evidence/raw/LOAD-ec2-saturation-r1_2026-10-08/cloudwatch/rds_cpu_max_stat.csv` (no `LOAD-ec2-pilot-*` folder exists); B: `evidence/raw/LOAD-fargate-saturation-r1_2026-10-09/cloudwatch/rds_cpu_max_stat.csv` |
| Interpretation / next step | Database headroom at 1,000 users is not measured; stated as a limitation. |

### LOAD-02: Ladder, A and B (1, 10, 100, 1,000 users, 3 repeats each)

| Field | |
|---|---|
| Objective | Compare latency, throughput and errors of A and B at matched compute at four load levels |
| Setup | One variant under load at a time, one unit each, same digest and RDS; 120 s warm-up discarded; fixed length per level |
| Command / steps | `python run.py ladder --level <N> --variant <ec2\|fargate> --base-url <host> --repeat <1..3> --location us-east-1` for each level and repeat |
| Expected result (unproven) | Similar steady-state speed at matched size; 1,000 users is far beyond the SME story and may breach the thresholds (a stress result, not a defect) |
| Actual result | **Not run.** Dropped for time on 9 October 2026; LOAD-03 (saturation) replaced it. [load-summary.md](load-summary.md) shows an empty ladder table. Same on A and B. |
| Date | — (A and B) |
| Artefact path | `evidence/raw/LOAD-<variant>-ladder-u<N>-r<n>_<date>/` |
| Interpretation / next step | There is no think-time latency at 10 or 100 users. Latency at light load is read from the first saturation steps (p95 22 ms at 1 user, 27 ms at 2, 51 ms at 4, 115 ms at 8) and from the light-load phase of the scale-out run, on both variants (B: p95 23 ms at 1 user, 28 ms at 2, 53 ms at 4, 202 ms at 8). |

### LOAD-03: Saturation (capacity of one unit)

| Field | |
|---|---|
| Objective | Find the practical capacity (highest step meeting the limits) and the maximum throughput of one unit |
| Setup | One unit, no think time, steps of 1, 2, 4, 8, 16, 32, 64, 128, 256, 512 users for 120 s (first 30 s of each step discarded) |
| Command / steps | `python run.py saturation --variant <ec2\|fargate> --base-url <host> --repeat <n> --location us-east-1` |
| Expected result | Throughput rises then flattens; p95 and errors rise past the knee. Report capacity as page actions/s and as a multiple of 0.4 dynamic pages/s |
| Actual result | **Variant B** (one Fargate task, 2 vCPU / 4 GB): run valid, not aborted, 0 errors at every step. Practical capacity: **8 users, 44.01 page actions/s**. Maximum throughput **105.5 requests/s** at 512 users. **Variant A** (one `c5.large`): run valid, not aborted, 0 errors at every step. Practical capacity (highest step meeting p95 under 800 ms and errors under 1 percent): **16 users, 46.54 page actions/s**. Maximum throughput **118.8 requests/s** at 512 users. Assumed SME peak for comparison: 0.4 dynamic pages/s. Per-step table below. |
| Date | A: 2026-10-08, 18:20:58 to 18:41:00 UTC. B: 2026-10-09, 06:23:24 to 06:43:26 UTC |
| Artefact path | A: `evidence/raw/LOAD-ec2-saturation-r1_2026-10-08/`. B: `evidence/raw/LOAD-fargate-saturation-r1_2026-10-09/` |
| Interpretation / next step | **The application instance limited it, not the database.** Instance CPU rose from 8 percent in the first minute to 89.5 percent at 18:26 and stayed near 94 percent from 18:28 to the end (maximum 94.55 percent, `cloudwatch/ec2_cpu.csv`), while RDS CPU never exceeded 10.46 percent and the CPU credit balance stayed at 576 (`rds_cpu_credit_balance.csv`). Throughput flattened at about 100 to 119 requests/s from 2 users on, and p95 rose from 22 ms (1 user) to 13,906 ms (512 users) with no errors: the shop queued requests rather than failing them. The generator was not the limit: mean CPU per step 6.5 to 14.9 percent, one 1-second sample at 100 percent when the 512-user step started (`generator_cpu.csv`; `analyze.py` reports a rolling peak of 20 percent). Not measured: a second unit under saturation, and the 3D models. |

Per-step results, copied from [load-summary.md](load-summary.md) (no think time; first 30 s of each step discarded):

| Users | Requests/s | Actions/s | p50 ms | p95 ms | Errors | RDS CPU max (this step) | RDS credits min (this step) |
|---|---|---|---|---|---|---|---|
| 1 | 65.3 | 29.58 | 10 | 22 | 0.00% | 9% | n/a |
| 2 | 100.1 | 45.33 | 12 | 27 | 0.00% | 9% | n/a |
| 4 | 115.6 | 52.44 | 25 | 51 | 0.00% | 9% | 576.0 |
| 8 | 104.9 | 47.43 | 46 | 115 | 0.00% | 9% | n/a |
| 16 | 102.9 | 46.54 | 94 | 783 | 0.00% | 9% | 576.0 |
| 32 | 101.5 | 45.98 | 188 | 1444 | 0.00% | 9% | n/a |
| 64 | 110.2 | 50.08 | 369 | 1595 | 0.00% | 9% | n/a |
| 128 | 114.3 | 51.07 | 794 | 3083 | 0.00% | 9% | 576.0 |
| 256 | 111.4 | 51.26 | 1741 | 6856 | 0.00% | 9% | n/a |
| 512 | 118.8 | 51.74 | 3005 | 13906 | 0.00% | 10% | 576.0 |

Variant B, same run type (copied from [load-summary.md](load-summary.md)):

| Users | Requests/s | Actions/s | p50 ms | p95 ms | Errors | RDS CPU max (this step) | RDS credits min (this step) |
|---|---|---|---|---|---|---|---|
| 1 | 60.9 | 27.61 | 11 | 23 | 0.00% | 8% | 576.0 |
| 2 | 97.2 | 44.03 | 12 | 28 | 0.00% | 8% | 576.0 |
| 4 | 98.4 | 44.59 | 26 | 53 | 0.00% | 8% | n/a |
| 8 | 97.3 | 44.01 | 49 | 202 | 0.00% | 9% | 576.0 |
| 16 | 87.0 | 39.47 | 104 | 1204 | 0.00% | 9% | n/a |
| 32 | 91.9 | 41.53 | 219 | 1540 | 0.00% | 9% | 576.0 |
| 64 | 99.9 | 45.13 | 423 | 1816 | 0.00% | 9% | 576.0 |
| 128 | 103.6 | 47.79 | 914 | 3259 | 0.00% | 9% | n/a |
| 256 | 95.3 | 42.52 | 2237 | 9489 | 0.00% | 9% | 576.0 |
| 512 | 105.5 | 43.02 | 3385 | 14399 | 0.00% | 9% | n/a |

**A against B at the points a reader will look for** (all from the two tables; n = 1): practical capacity 16 users (A) and 8 users (B); maximum throughput 118.8 and 105.5 requests/s; p95 at 8 users 115 ms (A) and 202 ms (B); p95 at 16 users 783 ms (A) and 1204 ms (B); p95 at 512 users 13906 ms (A) and 14399 ms (B); errors 0.00 percent at every step on both. The B 8-user step passes (202 ms); the B 16-user step fails the 800 ms limit.

**Limiting resource on B.** The task, not the database: task CPU was 30.7 percent in the first minute, 89.6 percent at 06:27 and 06:28, and 93 to 96 percent from 06:29 to the end (maximum 96.07 percent, `cloudwatch/ecs_cpu_max.csv`), while RDS CPU never exceeded 9.09 percent and the credit balance stayed at 576. The generator was not the limit: one 1-second sample reached 84.9 percent in `generator_cpu.csv`; `analyze.py` reports a rolling peak of 19 percent.

**Health under overload, both variants (an addition to the expectation).** At the 512-user step the single unit failed load-balancer health checks on both variants. A: `alb_unhealthy_hosts.csv` averages 0.5 and `alb_healthy_hosts.csv` 0.5 in the 18:39 UTC minute; `targets.jsonl` holds only the initial record, so the dip was not seen by `watch`, and Auto Scaling did not replace the instance. B: `targets.jsonl` shows the task `unhealthy` at 06:42:08, `healthy` at 06:42:35, `unhealthy` again at 06:43:17 and `healthy` at 06:43:33; `ecs_events.json` records at 06:43:30 "Amazon ECS replaced 1 tasks due to an unhealthy status", the replacement registered at 06:44:08 and the original task stopped at 06:44:54, after the run ended (06:43:26). Neither event changed the request-log error count (0).

**Expected versus actual.** Throughput rose then flattened, as expected. Latency rose past the knee, as expected. Errors did not rise: the expectation that errors would increase past the knee was not met (0.00 percent at 512 users; no target 5xx datapoints in `cloudwatch/alb_target_5xx.csv`). The step at 16 users passes only narrowly (p95 783 ms against the 800 ms limit); the next step, 32 users, fails (1,444 ms). One repeat, so 16 users (A) and 8 users (B) are indicative, n = 1. B shows the same shape: throughput flat from about 2 users, latency rising, no errors.

### LOAD-04: Latency from Singapore

| Field | |
|---|---|
| Objective | Quantify the extra latency for a Singapore customer of hosting in us-east-1 |
| Setup | 10 users from the laptop outside the region against the same stack as the in-region 10-user ladder run |
| Command / steps | `python run.py singapore --variant <ec2\|fargate> --base-url <host> --repeat 1 --location singapore-laptop` |
| Expected result | Several hundred ms added per request compared with the in-region run |
| Actual result | **Not run** (A and B). |
| Date | — |
| Artefact path | `evidence/raw/LOAD-<variant>-singapore-r1_<date>/` |
| Interpretation / next step | Production would use `ap-southeast-1` |

### RES-03a: Scale-out (1 to 2 units)

| Field | |
|---|---|
| Objective | Measure the time from the scaling alarm to a second healthy target, and show the group growing and shrinking |
| Setup | Autoscaling 1 to 2, target 300 requests per unit per minute (ADR-011); `watch` running on the laptop |
| Command / steps | `python aws_capture.py watch ...` (laptop), `python run.py scaleout --variant <v> --base-url <host> --repeat <n> --location us-east-1` (generator), then `aws_capture.py export` |
| Expected result | Alarm after the load step, then a new unit healthy about 3 to 4 minutes later (A); scale-in after the load falls |
| Actual result | Variant A: detection **299 s**, alarm to scaling action **64 s**, alarm to healthy **161 s**, load step to healthy **460 s**; 0 errors in 11,643 requests; no target 5xx. The group went from 1 to 2 instances without a person. **Scale-in was not observed**: the group was still at 2 when the export ended (timeline below). **Variant B:** detection **305 s**, alarm to scaling action **67 s**, alarm to healthy **101 s**, load step to healthy **407 s**; 0 errors in 11,627 requests; no target 5xx. The service went from 1 to 2 tasks without a person. **Scale-in was observed after the run**: the extra task was stopped at 03:03:08 UTC, 18 minutes after the load fell (`raw/SESSION_2026-10-09_fargate_service-events.txt`; the run folder's own export ended before it). |
| Date | A: 2026-10-08, run 16:48:08 to 17:11:10 UTC. B: 2026-10-09, run 02:27:15 to 02:50:17 UTC |
| Artefact path | A: `evidence/raw/RES-03-ec2-scaleout-r1_2026-10-08/`. B: `evidence/raw/RES-03-fargate-scaleout-r1_2026-10-09/` |
| Interpretation / next step | Most of the detection delay is the scaling policy, not the platform; boot to healthy is where A and B differ. The new instance was healthy 161 s after the alarm, a little faster than the 3 to 4 minutes expected. The policy is far more sensitive than the instance needs: 300 requests per target per minute (ADR-011) is about 4 percent of the 118.8 requests/s ceiling measured in LOAD-03, and instance CPU peaked at 14.56 percent (`cloudwatch/ec2_cpu.csv`, 16:57). The expected scale-in did not happen within the run: the load fell to 10 users at 17:06:08 and the run ended at 17:11:10, five minutes later, and the next step (`raw/OPS_2026-10-08_ec2_pin-2-2-2-count_plan.txt`) found the desired capacity already at 2. AWS target tracking waits for a long run of low readings before it removes an instance (AWS documentation, not shown in these files), which would explain it, but a longer low phase was not run to confirm. On B the scale-in did occur, 17 to 18 minutes after the load fell (03:03:08 against the step-down at 02:45:15); A's window for observing it ended earlier, when the group was pinned to 2 at 17:19 (13 minutes after the load fell). So "A did not scale in" is not shown; "A had not scaled in within 13 minutes" is. **A against B:** alarm timing is the same within 6 s (299 s, 305 s) and the action delay is the same within 3 s (64 s, 67 s), as expected from one shared scaling policy; what differs is the time from the scaling action to a healthy second unit (A: 16:57:11 to 16:58:48; B: 02:36:28 to 02:37:01.9), the part that includes booting an instance on A. Indicative, n = 1. |

Timeline, variant A (UTC, 2026-10-08):

| Time | Event | Source |
|---|---|---|
| 16:48:08 | Run starts, 10 users | `run.json` |
| 16:51:08 | Load step to 200 users (180 s into the run) | `run.json` markers |
| 16:56:07 | `AlarmHigh` goes OK to ALARM (299 s after the step) | `alarm_history.json` |
| 16:57:11 | Auto Scaling launches instance `i-00ad88ffb01cb28b9`, desired 1 to 2 (64 s after the alarm) | `scaling_activities.json` |
| 16:57:18 | Target registered, state `initial` | `targets.jsonl` |
| 16:58:48 | 2 of 2 targets healthy (161 s after the alarm, 460 s after the step) | `targets.jsonl`, `cloudwatch/alb_healthy_hosts.csv` |
| 17:02:07 | `AlarmHigh` back to OK | `alarm_history.json` |
| 17:06:08 | Load falls to 10 users | `run.json` markers |
| 17:11:10 | Run ends; desired capacity still 2 when exported at 17:14 | `run.json`, `stack.json`, `cloudwatch/asg_desired.csv` |

Timeline, variant B (UTC, 2026-10-09):

| Time | Event | Source |
|---|---|---|
| 02:27:15 | Run starts, 10 users | `run.json` |
| 02:30:15 | Load step to 200 users (180 s into the run) | `run.json` markers |
| 02:35:20.7 | `AlarmHigh` goes OK to ALARM (305 s after the step) | `alarm_history.json` |
| 02:36:28 | ECS starts task `407d188c…`, desired 1 to 2 (67 s after the alarm) | `ecs_events.json` |
| 02:36:56.8 | Task registered in the target group | `ecs_events.json` |
| 02:37:01.9 | 2 of 2 targets healthy (101 s after the alarm, 407 s after the step) | `targets.jsonl` |
| 02:41:20.7 | `AlarmHigh` back to OK | `alarm_history.json` |
| 02:45:15 | Load falls to 10 users | `run.json` markers |
| 02:50:17 | Run ends | `run.json` |
| 03:03:08 | ECS stops task `407d188c…` (scale-in) | `raw/SESSION_2026-10-09_fargate_service-events.txt` (printed as 11:03:08 +08:00) |

### RES-03b: Replacement of a killed unit

| Field | |
|---|---|
| Objective | Measure time to two healthy units again and the error window after one unit is lost |
| Setup | Two units pinned, 100 users, `watch` running; the user kills one unit about 5 minutes in |
| Command / steps | `run.py replace ...` (generator); at the prompt `python aws_capture.py kill --variant <v> --run-id <ID>` (laptop); `export` |
| Expected result | Detection about 30 s after the kill (ADR-008), replacement dominated by boot time and the grace period; a short burst of errors |
| Actual result | Variant A: kill to detected **2 s**, replacement **114 s**, error window **0 s**, errors in the window **0**, errors later in the run **0**; 7,474 requests. Detection (2 s) is much faster than the 30 s expected, because a graceful removal drains the target at once; a crash would wait for the health check. No burst of errors, which is within the expectation "a short burst of errors or none". **Variant B:** kill to detected **18 s**, replacement **50 s**, error window **0 s**, errors in the window **0**, errors later in the run **0**; 7,474 requests. Detection is 18 s because ECS began draining the task 16 s after the stop call (`ecs_events.json`: deregistered at 03:17:50.5, kill at 03:17:34.5); the replacement task was started in the same second as the deregistration. No burst of errors. |
| Date | A: 2026-10-08, run 17:23:18 to 17:43:20 UTC. B: 2026-10-09, run 03:12:27 to 03:32:30 UTC |
| Artefact path | A: `evidence/raw/RES-03-ec2-replace-r1_2026-10-08/`. B: `evidence/raw/RES-03-fargate-replace-r1_2026-10-09/` |
| Interpretation / next step | Also evidence for the signature demo "instance or task lost" in [TESTING.md](../docs/TESTING.md). This is a **graceful removal** (ADR-017): the load balancer stops sending new requests to the instance first, so zero errors is the expected outcome and does not show how a crash would behave. Auto Scaling started the replacement within seconds of the removal (17:29:51); the rest of the 114 s is the new instance booting, pulling the image and passing two health checks (healthy threshold 2, interval 10 s in `modules/web-entry/alb.tf`). RES-04 (session continuity) has not been analysed from the request log; the 0 errors are indirect evidence only (A and B). **A against B:** two healthy units again after 114 s (A) and 50 s (B); the replacement was started 13 s (A) and 17 s (B) after the removal, so the difference is the time from "started" to "healthy" (A: 17:29:51 to 17:31:31.7, an instance boot; B: 03:17:51.4 to 03:18:24.5, a task start). Removal was seen in 2 s (A) and 18 s (B). Neither variant failed a request. Indicative, n = 1. |

Timeline, variant A (UTC, 2026-10-08):

| Time | Event | Source |
|---|---|---|
| 17:23:18 | Run starts, 100 users, 2 healthy units | `run.json`, `targets.jsonl` |
| 17:29:37.9 | Graceful removal of `i-00ad88ffb01cb28b9` (300 s into the run) | `kill.json` |
| 17:29:39.8 | Target `draining`, 1 of 2 healthy (kill to detected: 2 s) | `targets.jsonl` |
| 17:29:51 | Auto Scaling starts replacement `i-0375a1086e96bad06` | `scaling_activities.json` |
| 17:30:22 | New target `unhealthy` while it boots (`cloudwatch/alb_unhealthy_hosts.csv` shows 1 at 17:30) | `targets.jsonl` |
| 17:31:31.7 | 2 of 2 healthy (replacement 114 s after the removal) | `targets.jsonl` |
| 17:43:20 | Run ends, 0 errors | `run.json`, [load-summary.md](load-summary.md) |

Timeline, variant B (UTC, 2026-10-09):

| Time | Event | Source |
|---|---|---|
| 03:12:27 | Run starts, 100 users, 2 healthy units | `run.json`, `targets.jsonl` |
| 03:17:34.5 | Graceful stop of task `46220bb4…` (300 s marker; typed a few seconds later) | `kill.json` |
| 03:17:50.5 | Task deregistered, connections draining | `ecs_events.json` |
| 03:17:51.4 | ECS starts replacement task `f49c1b51…` | `ecs_events.json` |
| 03:17:52.7 | Target `draining`, 1 of 2 healthy (kill to detected: 18 s) | `targets.jsonl` |
| 03:18:19.8 | Replacement registered in the target group | `ecs_events.json` |
| 03:18:24.5 | 2 of 2 healthy (replacement 50 s after the stop) | `targets.jsonl` |
| 03:32:30 | Run ends, 0 errors | `run.json`, [load-summary.md](load-summary.md) |

## Summary and decision

One repeat per condition on each variant; the full generated tables are in [load-summary.md](load-summary.md). Side by side, from the cases above:

| Question | Answer from the A runs | Answer from the B runs | Not shown (either variant) |
|---|---|---|---|
| Does it scale out by itself? | Yes: second unit healthy 460 s after a load step, 161 s after the alarm (RES-03a) | Yes: second unit healthy 407 s after a load step, 101 s after the alarm (RES-03a) | Behaviour when CPU, not request count, is the trigger. Scale-in: seen on B after the run, not seen on A in its 13-minute window |
| Does it survive losing a unit? | Yes, for a graceful removal: 114 s to two healthy units, 0 errors (RES-03b) | Yes, for a graceful removal: 50 s to two healthy units, 0 errors (RES-03b) | A crash; session continuity (RES-04) analysed from the request log |
| How much does one unit serve? | 46.54 page actions/s at the practical limit (16 users), 118.8 requests/s at most; instance CPU limits it, the database does not (LOAD-03) | 44.01 page actions/s at the practical limit (8 users), 105.5 requests/s at most; task CPU limits it, the database does not (LOAD-03) | Two units under saturation; the 1,000-user database pilot; 3D models |
| What happens at 512 users on one unit? | 0 errors, p95 13906 ms; the instance failed health checks for part of one minute and was not replaced | 0 errors, p95 14399 ms; the task failed health checks twice and ECS replaced it | What a real overload would do to customers (the load test never stops sending) |

The weighted comparison of A and B is **not made here**: with one repeat per condition no A-versus-B difference can be called more than indicative (n = 1), and the operational-burden figures (Terraform lines and resources, boot-to-healthy time, steps to patch) come from outside the harness and are supplied to `analyze.py` with `--operational`; they were not supplied in this pass. The architecture decision is recorded in [docs/decisions/](../docs/decisions/).

## Limitations

Closed-model load generation (coordinated omission); static files fetched once per visit but 3D models not fetched; data transfer not measured; one generator IP with the WAF in count mode; a visit mix based on public benchmarks, not a measured shop; state drift between runs (orders and stock are recorded, carts reset); prices unverified until the user checks `tests/load/prices.json`.
