# Performance and scaling evidence (load tests)

**Status: TEMPLATE. No case below has been run on AWS; every "Actual result" is empty on purpose.** Placeholder text is not a result. The harness is built and verified locally ([tests/load/README.md](../tests/load/README.md)); plan, decisions, thresholds and weights are in [docs/plans/load-harness.md](../docs/plans/load-harness.md).

How to fill a case: run the command, let `aws_capture.py export` copy the run into `evidence/raw/<run id>/`, run `analyze.py`, paste the relevant table rows under "Actual result", and write the interpretation. A failed or invalid run is recorded too, with its diagnosis and the next step. Results are capacity per unit of compute and a multiple of the assumed SME peak (about 0.4 dynamic pages/s), never "what the shop needs". Redact account IDs and public IPs (the export does this).

## Conditions common to every recorded run

Fill once per campaign; a change of any item means the affected runs are rerun or marked superseded (AGENTS.md: the image is pinned).

| Item | Value |
|---|---|
| Image digest (both variants) | |
| Git commit of the harness / infrastructure | |
| RDS instance class, engine version, Multi-AZ | |
| Region | us-east-1 |
| A: instance type; B: task size | c5.large (2 vCPU, 4 GiB); Fargate 2 vCPU / 4 GB |
| Capacity during ladder and saturation | one unit (min = max = 1) |
| Scale-out load step (`--users-high`) | 200 users, both variants |
| WAF rule on `POST /login/` | count mode, limit 20 per 5 min per IP |
| Load generator (type, region, clock offset) | |
| Workload | 90% window shoppers, 7.5% cart abandoners, 2.5% buyers; 36 s think time; seed 42 |
| Thresholds | p95 under 800 ms; p99 under 1.8 s (at least 1,000 samples); checkout p95 under 2 s; errors under 1% |
| Comparison weights (locked 3 October 2026) | operational burden 25, replacement and error window 25, latency 20, cost 15, scale-out 10, capacity 5 |
| Prices verified by (name, date) | |

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
- Costs are flagged unverified until `tests/load/prices.json` is checked against the AWS price pages.

## Cases

### LOAD-01: RDS pilot gate

| Field | |
|---|---|
| Objective | Show the database is not the bottleneck at the 1,000-user step on one unit |
| Setup | Variant A, one unit, WAF in count mode, accounts created, carts reset |
| Command / steps | `python run.py pilot --variant ec2 --base-url $LOAD_BASE_URL --repeat 1 --location us-east-1` |
| Expected result | RDS CPU at most 40% on one saturated unit (projects to about 80% with two units); connections and freeable memory not trending to the limit |
| Actual result | |
| Date | |
| Artefact path | `evidence/raw/LOAD-ec2-pilot-r1_<date>/` |
| Interpretation / next step | |

### LOAD-02: Ladder, A and B (1, 10, 100, 1,000 users, 3 repeats each)

| Field | |
|---|---|
| Objective | Compare latency, throughput and errors of A and B at matched compute at four load levels |
| Setup | One variant under load at a time, one unit each, same digest and RDS; 120 s warm-up discarded; fixed length per level |
| Command / steps | `python run.py ladder --level <N> --variant <ec2\|fargate> --base-url <host> --repeat <1..3> --location us-east-1` for each level and repeat |
| Expected result (unproven) | Similar steady-state speed at matched size; 1,000 users is far beyond the SME story and may breach the thresholds (a stress result, not a defect) |
| Actual result | paste the ladder and comparison tables from `analyze.py` |
| Date | |
| Artefact path | `evidence/raw/LOAD-<variant>-ladder-u<N>-r<n>_<date>/` |
| Interpretation / next step | |

### LOAD-03: Saturation (capacity of one unit)

| Field | |
|---|---|
| Objective | Find the practical capacity (highest step meeting the limits) and the maximum throughput of one unit |
| Setup | One unit, no think time, steps of 1, 2, 4, 8, 16, 32, 64, 128, 256 users for 120 s (first 30 s of each step discarded) |
| Command / steps | `python run.py saturation --variant <ec2\|fargate> --base-url <host> --repeat <n> --location us-east-1` |
| Expected result | Throughput rises then flattens; p95 and errors rise past the knee. Report capacity as page actions/s and as a multiple of 0.4 dynamic pages/s |
| Actual result | |
| Date | |
| Artefact path | `evidence/raw/LOAD-<variant>-saturation-r<n>_<date>/` |
| Interpretation / next step | Say whether the database or the app limited it (RDS CPU in the table) |

### LOAD-04: Latency from Singapore

| Field | |
|---|---|
| Objective | Quantify the extra latency for a Singapore customer of hosting in us-east-1 |
| Setup | 10 users from the laptop outside the region against the same stack as the in-region 10-user ladder run |
| Command / steps | `python run.py singapore --variant <ec2\|fargate> --base-url <host> --repeat 1 --location singapore-laptop` |
| Expected result | Several hundred ms added per request compared with the in-region run |
| Actual result | |
| Date | |
| Artefact path | `evidence/raw/LOAD-<variant>-singapore-r1_<date>/` |
| Interpretation / next step | Production would use `ap-southeast-1` |

### RES-03a: Scale-out (1 to 2 units)

| Field | |
|---|---|
| Objective | Measure the time from the scaling alarm to a second healthy target, and show the group growing and shrinking |
| Setup | Autoscaling 1 to 2, target 300 requests per unit per minute (ADR-011); `watch` running on the laptop |
| Command / steps | `python aws_capture.py watch ...` (laptop), `python run.py scaleout --variant <v> --base-url <host> --repeat <n> --location us-east-1` (generator), then `aws_capture.py export` |
| Expected result | Alarm after the load step, then a new unit healthy about 3 to 4 minutes later (A); scale-in after the load falls |
| Actual result | detection, alarm to scaling action, scale-out time and load-step-to-healthy from the timings table |
| Date | |
| Artefact path | `evidence/raw/RES-03-<variant>-scaleout-r<n>_<date>/` |
| Interpretation / next step | Most of the detection delay is the scaling policy, not the platform; boot to healthy is where A and B differ |

### RES-03b: Replacement of a killed unit

| Field | |
|---|---|
| Objective | Measure time to two healthy units again and the error window after one unit is lost |
| Setup | Two units pinned, 100 users, `watch` running; the user kills one unit about 5 minutes in |
| Command / steps | `run.py replace ...` (generator); at the prompt `python aws_capture.py kill --variant <v> --run-id <ID>` (laptop); `export` |
| Expected result | Detection about 30 s after the kill (ADR-008), replacement dominated by boot time and the grace period; a short burst of errors |
| Actual result | kill-to-detected, replacement time, error window and errors after the kill from the timings table |
| Date | |
| Artefact path | `evidence/raw/RES-03-<variant>-replace-r<n>_<date>/` |
| Interpretation / next step | Also evidence for the signature demo "instance or task lost" in [TESTING.md](../docs/TESTING.md) |

## Summary and decision

Paste `evidence/load-summary.md` (generated by `analyze.py`) or link it, then state which variant the weighted score favours, which criteria were measured and which were not, and what the result does not show. The operational-burden figures (Terraform lines and resources, boot-to-healthy time, steps to patch) come from outside the harness and are supplied to `analyze.py` with `--operational`.

## Limitations

Closed-model load generation (coordinated omission); static files fetched once per visit but 3D models not fetched; data transfer not measured; one generator IP with the WAF in count mode; a visit mix based on public benchmarks, not a measured shop; state drift between runs (orders and stock are recorded, carts reset); prices unverified until the user checks `tests/load/prices.json`.
