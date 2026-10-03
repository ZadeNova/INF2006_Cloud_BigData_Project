# Load-testing harness (Locust)

Measures the 42Factors shop on variant A (EC2 + Auto Scaling group) and variant B (ECS on Fargate) with the same workload, so the two can be compared fairly, and produces the scale-out and replacement evidence. Plan, decisions, thresholds and weights: [docs/plans/load-harness.md](../../docs/plans/load-harness.md). Results go in [evidence/test-performance.md](../../evidence/test-performance.md).

Results are reported as **capacity per unit of compute** and as a **multiple of the assumed SME peak** (about 15 concurrent visitors, 0.4 dynamic pages/s). They are never a claim about how much traffic the shop needs.

**Status (3 October 2026):** built and verified locally against Docker Compose. Not yet run on AWS: the load-generator instance, the Fargate stack and the pinning variables do not exist yet (plan section 10).

## What is in this folder

| File | Does |
|---|---|
| `run.py` | Runs one test type with a fixed schedule; prints expected time and cost first; writes `out/<run-id>/` |
| `locustfile.py` | The visitor (three visit kinds), constant pacing, per-request log, load shape, generator-CPU sampler, automatic abort |
| `accounts.py` | Creates the synthetic test accounts through the normal `/register/` form; empties carts between runs |
| `aws_capture.py` | Laptop only: `watch` target health, `kill` one unit, `export` CloudWatch/scaling data and redact |
| `analyze.py` | Raw run folders to summary tables, timings, cost per 1,000 requests and weighted scores |
| `selftest.py` | Checks of the harness's own logic (no network); `python selftest.py` |
| `common.py`, `prices.json` | Shared helpers; hourly prices (**unverified, see below**) |
| `requirements.in` / `.txt` | Locust and boto3, pinned by exact version. Separate from the application's requirements on purpose |

## One-time setup

All commands below run from this folder (`tests/load/`).

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt            # Python 3.12 (the generator) or 3.14 (the laptop)
cp .env.example .env                       # then edit: LOADTEST_PASSWORD, LOAD_BASE_URL
set -a; . ./.env; set +a
```

`.env` is git-ignored. Passwords and hostnames never go in the repository. **Verify `prices.json`** against the AWS price pages and set `"verified_by_user": true`; until then every cost figure is flagged as unverified.

## Verify locally (free, about 2 minutes)

```bash
docker compose up -d                       # from the repository root; import the dataset first if the catalogue is empty
python accounts.py create --base-url http://127.0.0.1:8000 --count 4
python run.py smoke --base-url http://127.0.0.1:8000 --yes
python analyze.py --raw out
python selftest.py
```

`smoke` is 2 users for 75 s with a fixed visit order (buyer, abandoner, shopper), so login, add to cart and checkout are all exercised.

## Before every cloud run

1. Only the variant under test is taking load, its targets are healthy, and both variants run **the same image digest** and the same RDS instance and class (`aws_capture.py export` records them).
2. Capacity is pinned as the run type needs: **one unit** for `pilot`, `ladder`, `saturation`, `singapore`; **autoscaling 1 to 2** for `scaleout`; **two units pinned** for `replace`. (Needs the pinning variables from plan section 10.)
3. The WAF rule on `POST /login/` is in **count** mode (`waf_login_action = "count"`); the export records the mode. One IP sends hundreds of logins in a ladder, which block mode would reject.
4. Reset carts from the previous run: `python accounts.py reset-carts --base-url $LOAD_BASE_URL --from-run out/<previous-run-id>`.
5. The generator runs **in us-east-1 on its own instance**, never on an app instance, and never on the laptop (except `singapore`). Check `chronyc tracking` shows a small offset.

## Commands, one per run type

Run these on the **generator** (`--location us-east-1`). `--repeat` is 1, 2, 3; the run id (printed first) is `LOAD-<variant>-<type>-r<n>_<UTC date>`, or `RES-03-...` for scale-out and replacement. Each command prints the expected duration and cost and asks `Start? [y/N]`.

| Run type | Command | Length | Repeats |
|---|---|---|---|
| Account setup (once, shared by both variants) | `python accounts.py create --base-url $LOAD_BASE_URL` | minutes | once |
| RDS pilot | `python run.py pilot --variant ec2 --base-url $LOAD_BASE_URL --repeat 1 --location us-east-1` | about 8 min | 1, variant A |
| Ladder | `python run.py ladder --level {1,10,100,1000} --variant ec2 --base-url $LOAD_BASE_URL --repeat N --location us-east-1` | 12 to 15 min per level | 3 per level |
| Saturation | `python run.py saturation --variant ec2 --base-url $LOAD_BASE_URL --repeat N --location us-east-1` | up to 14 min | 1 (3 if time) |
| Scale-out | `python run.py scaleout --variant ec2 --base-url $LOAD_BASE_URL --repeat N --location us-east-1` | 23 min | 3 |
| Replacement | `python run.py replace --variant ec2 --base-url $LOAD_BASE_URL --repeat N --location us-east-1` | 20 min | 3 |
| Singapore latency | `python run.py singapore --variant ec2 --base-url $LOAD_BASE_URL --repeat 1 --location singapore-laptop` (**from the laptop**) | 12 min | 1 per variant |

For variant B use `--variant fargate` and the Fargate hostname. `run.py` refuses a `--variant` that does not match the host, so A data can never be saved as B.

**Scale-out and replacement need the laptop as well** (lab credentials stay there, not on the generator):

```bash
# Laptop, before starting the run on the generator, in its own terminal:
python aws_capture.py watch --variant ec2 --run-id <RUN-ID>      # logs every target-health change; Ctrl-C afterwards
# Replacement run only, when run.py prints "NOW: kill one unit" (about 5 minutes in):
python aws_capture.py kill  --variant ec2 --run-id <RUN-ID>      # asks you to type "kill"; logs the UTC time
```

The run id is known in advance: it is printed by `run.py` at the confirmation prompt, before you answer.

## After every run

```bash
# On the generator: copy the run folder out through the project bucket (name from `terraform output s3_bucket_name` in base/)
aws s3 cp --recursive out/<RUN-ID> s3://<BUCKET>/exports/load/<RUN-ID>/
# On the laptop:
aws s3 cp --recursive s3://<BUCKET>/exports/load/<RUN-ID> out/<RUN-ID>
python aws_capture.py export --variant ec2 --run-id <RUN-ID> --run-dir out/<RUN-ID>
python analyze.py --out ../../evidence/load-summary.md     # reads evidence/raw only; rerun any time
```

`export` must run **before any teardown**: CloudWatch keeps 1-minute data for about 15 days and ECS drops service events with the service. It copies the run into `evidence/raw/<RUN-ID>/` (and refuses to overwrite one), adds `cloudwatch/*.csv`, `alarm_history.json`, `scaling_activities.json` or `ecs_events.json`, `stack.json`, then replaces account IDs with `<ACCOUNT>` and public IPs with `<PUBLIC-IP>` in every text file. Raw files are never edited afterwards. Whether the lab role may write `exports/load/` in the bucket has not been checked; if it may not, copy with Session Manager port forwarding or paste the folder through the console and note it in the evidence.

## What a run folder contains

`requests-<pid>.csv` (one row per HTTP request: UTC time, user, visit, action, method, name, status, latency, bytes, outcome, account), `generator_cpu.csv`, `locust_stats.csv`, `locust_stats_history.csv` (full history), `locust_failures.csv`, `locust_exceptions.csv`, `report.html`, `run.json` (metadata: run id, variant, level, repeat, UTC times, git commit, Locust version, seed, exact command line, generator location/type/clock offset, schedule, thresholds), `timing.json`, `abort.json` (only if aborted); after export also the AWS files above.

Outcomes in the request log: `ok`; `stock_conflict` (a stock refusal, counted apart, not an error); `error` (anything else, including a 200 page with the wrong content); `cleanup` (untimed cart emptying, excluded from all statistics); `late` (a user started an action more than 1 s after its schedule).

## How a run is judged

* **Warm-up** of 120 s after the ramp is discarded; the measurement window has a fixed length (plan section 6).
* **Invalid** (rerun; the failed run is kept): generator CPU above 70% averaged over any 30 s, clock offset above 50 ms, no requests recorded.
* **Flagged, but a result:** `aborted` (errors above 20% or p95 above 10 s for 60 s), `overloaded` (achieved page-action rate under 95% of intended), `database-limited` (RDS CPU above 80%).
* **Thresholds:** p95 under 800 ms, p99 under 1.8 s (quoted only with at least 1,000 samples), checkout p95 under 2 s, errors under 1%.
* **Repeats:** the tables show the median with the min-max range over valid repeats. A difference whose ranges overlap scores as a tie.

## Known limitations (also state them in the report)

* **Closed model.** Locust waits for each response, so when the server falls behind the real arrival rate drops and percentiles understate what an open stream of visitors would see (coordinated omission). Constant pacing fixes the arrival rate only while the server keeps up. The harness reports intended against achieved action rate and counts late starts. The saturation run is deliberately closed with no think time.
* **Static files:** the first page of each visit fetches the same-origin CSS, JS and icon sprite (about 1 MB, mostly the 3D viewer script); later pages assume a browser cache. The `.glb` 3D models are not fetched, so data transfer, which may cost more than compute in production, is not measured.
* **Login cost is real.** Django hashes passwords with PBKDF2 (about 0.3 to 0.4 s of CPU per login in the local run). Ten percent of visits log in, so this is a visible share of the load at 1,000 users.
* **State drift.** Load runs create real orders and lower stock. Carts are emptied between runs; orders and stock changes are accepted and recorded per run. Sizes flagged "only N left" are avoided, and a stock refusal is a counted `stock_conflict`.
* **One generator IP** against a WAF rate rule: count mode is used for every recorded run and recorded in `stack.json`.
* **The visit mix is an assumption** anchored to public benchmarks (plan section 4), not a measurement of any shop.
* **ALB request counts include static files and redirects**, so requests per second here exceed page actions per second.

## Verified locally and not yet verified

Verified on 3 October 2026 against local Docker: account creation (idempotent), the whole visitor flow with CSRF and login, add to cart, checkout and order confirmation (2 orders created, 0 errors), the no-think-time mode, the automatic abort (exit code 3), cart reset, refusal of a foreign host, and the analysis (deterministic across reruns). `selftest.py` passes 9 checks, including `aws_capture.py` export, kill and target-health calls against botocore's stubbed service models, which validate every parameter name and type.

**Not verified until the first AWS session:** every real AWS call and its permissions under the lab role; that metric names, dimensions and the WAF rule dimension exist as assumed; the generator instance and moving files through S3; Locust with `--processes 2` at 1,000 users and the 70% CPU limit; the ladder, saturation, scale-out and replacement schedules at full length; the p95 and capacity figures themselves; and the whole Fargate path.
