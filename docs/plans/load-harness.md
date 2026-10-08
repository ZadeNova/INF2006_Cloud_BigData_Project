# Plan: load-testing harness for the EC2 (A) and Fargate (B) comparison

Written 3 October 2026 by the reviewing session (R), which owns the harness ([aws-ecs-comparison.md](aws-ecs-comparison.md) section 1, rule 2). **Status: decisions locked and plan approved by the user on 3 October 2026; harness implemented in `tests/load/` and verified locally the same day (section 15 lists where the build differs from this plan). Not yet run against AWS.**

[aws-ecs-comparison.md](aws-ecs-comparison.md) is the source of truth for the experiment design and is not contradicted here. This plan adds the load harness, the workload model and the run campaign.

## 1. Scope and boundaries

- **Builds:** `tests/load/` (Locust file, run wrapper, account setup, AWS capture, analysis, pinned requirements, `.env.example`, README), an evidence template, and this plan.
- **Does not touch:** backend code, templates, migrations, `src/Dockerfile`, `requirements.txt` (backend freeze), or `src/infrastructure/**` (writing session). What the harness needs from infrastructure is in section 10.
- **Does not run AWS.** The user runs every cloud run and every command that starts, stops or kills a resource. R verifies only locally (section 11).
- **Targets only our hosts.** The harness refuses any base URL that is not `shop-ec2.fourtytwofactors.me`, `shop-fargate.fourtytwofactors.me`, `localhost` or `127.0.0.1`. Third-party assets (the Google Fonts links in `base.html`) are never fetched.
- **Order of work.** The harness is built once for both variants. **A is run first; B is run when its stack is healthy** on the same image digest. If B is not ready in time, the report says B is designed and unmeasured.
- **Tool.** Locust (chosen in [TESTING.md](../TESTING.md)). k6 is used only if Locust cannot generate the load from one in-region instance, which is not expected (about 60 to 100 HTTP requests per second at the top level).
- **Method.** One user, one implementer: R writes the code and explains it, the user reviews it; R adds a labelled Claude self-review and reports findings before fixing anything.

### Conflicts found while reading the repository (resolved)

| # | Brief says | Repository says | Resolution |
|---|---|---|---|
| C1 | Send a fresh idempotency key per checkout | [API.md](../API.md): the key is session-derived and not submitted; `GET /checkout/` creates it, a successful `POST` clears it | Each checkout is `GET /checkout/` then `POST` with `review`; a new key per order follows from the server. No app change |
| C2 | Make sure the ladder does not trip the WAF | [ADR-012](../decisions/ADR-012-alarms-and-login-rate-limit.md): 20 `POST /login/` per IP per 5 min. With 10% of visits logging in, one IP sends about 1.6, 16 and 162 logins per 5 min at 10, 100 and 1,000 users | Every recorded load run uses the rule in **count** mode (already the deployed default and allowed by ADR-012), recorded in the run metadata. Block mode is for the security demo only |
| C3 | Output as `LOAD-...` | Comparison plan section 13 says `RES-...` | `LOAD-*` for pilot, ladder, saturation and Singapore; `RES-03-*` for scale-out and replacement |

## 2. Decisions (locked 3 October 2026)

| ID | Decision |
|---|---|
| D1 | **Static assets.** The first page action of each visit fetches the same-origin CSS and JS that page references, as a cache-cold browser would; later actions assume a warm cache. The `.glb` 3D models (about 1.3 MB each) are not fetched (bandwidth would dominate; data transfer is a documented limitation) |
| D2 | **WAF** in count mode for every recorded load run, recorded per run, with the rule's counted requests reported |
| D3 | **Capacity pinned at one unit** (min = max = 1) for pilot, ladder and saturation, so results are per unit of compute; autoscaling (1 to 2, target 300) is enabled only for the scale-out run and two units are pinned for the replacement run. Needs pinning variables (section 10) |
| D4 | **State drift.** The carts of the accounts a run used are emptied through the app before the next run (untimed, identical for both variants). Orders and stock decrements are accepted and recorded per run |
| D5 | **Run order.** All of A, then all of B (no interleaving); the report states time-of-day and drift as limitations |
| D6 | **Visit mix:** 90% window shoppers, 7.5% cart abandoners, 2.5% buyers (section 4) |
| D7 | **No operator traffic** in the load runs (analytics is exercised by its own evidence) |
| D8 | **Output names:** `evidence/raw/LOAD-<variant>-<type>-r<n>_<date>/` and `evidence/raw/RES-03-<variant>-<scaleout\|replace>-r<n>_<date>/`; results in `evidence/test-performance.md`, RES-03 rows linked from `evidence/test-resilience.md` |
| D9 | **Warm-up** of 2 minutes is kept as a safeguard (cold database buffers, first connections, load-balancer adjustment, the user ramp). The latency-over-time plot decides whether a cold-start effect existed; either result is reported |
| D10 | p99 is always recorded and shown with its sample count; it is quoted only where there are at least 1,000 samples |

## 3. Questions, metrics, thresholds and weights

**Questions the data must answer**
1. At matched compute (c5.large against Fargate 2 vCPU / 4 GB), do A and B differ in latency, throughput or errors at each ladder level?
2. What is one unit's practical capacity and maximum throughput, as a multiple of the assumed SME peak (0.4 dynamic pages/s)?
3. How long does each variant take to scale out from 1 to 2 units?
4. How long does each take to replace a killed unit, and how many requests fail meanwhile?
5. What does 1,000 requests cost on each at equal capacity?
6. Is the database a bottleneck (RDS pilot gate)?

**Client-side metrics** (per-request log, measurement window only): p50, p95, p99 per page action and overall; throughput; unexpected-error rate; stock-conflict rate (separate, not an error); orders created; achieved against intended action rate; late starts.

**Server-side metrics** (CloudWatch, 1-minute, the run's exact window): ALB `RequestCount`, `TargetResponseTime`, `HTTPCode_Target_5XX_Count`, `HTTPCode_Target_4XX_Count`, `HealthyHostCount`; A: ASG desired and in-service, EC2 CPU; B: running tasks, ECS CPU and memory; RDS CPU, `DatabaseConnections`, `FreeableMemory`, `CPUCreditBalance` (and surplus credits); WAF `CountedRequests`.

**Thresholds (accepted by the user)**

| Rule | Value | Basis |
|---|---|---|
| Page-action p95 | under 800 ms | Google rates a server response under 800 ms "good" |
| Page-action p99 | under 1.8 s, only with at least 1,000 samples | Google rates over 1.8 s "poor" |
| `POST /checkout/` p95 | under 2 s | project scope (proposed objective) |
| Unexpected errors | under 1% | project scope (proposed objective) |
| Practical capacity | highest saturation step that meets the p95 and error rules, decided before the run; the knee (where throughput stops growing) is reported separately as maximum throughput | method |
| Automatic abort (safety) | after the first 60 s: errors above 20% or p95 above 10 s, sustained 60 s. Scale-out and replacement runs: errors above 50% for 120 s only | 10 s is the limit of user attention (Nielsen) |
| Run validity (fail = rerun; the failed run is kept and marked) | generator CPU at most 70% over any 30 s (own margin); clock offset under 50 ms; one variant under load; healthy targets as intended at measurement start; same image digest, RDS class and WAF mode as the campaign | own margins |
| Overload flag (a result, not invalid) | achieved action rate below 95% of intended | own margin |
| **RDS pilot gate** | On one saturated unit RDS CPU at most **40%**, which projects to about 80% with the two units of the scale-out and replacement runs (linear extrapolation, stated as such). In any recorded run RDS CPU above 80% marks that run "database-limited". If the pilot fails, size up for CPU before the recorded runs. Note: `db.t4g.medium` has the same vCPU count as `db.t4g.small` (verify in the RDS console), so it adds memory, not CPU; a CPU fix needs a larger class. The t4g class is also burstable (baseline about 20% CPU per vCPU): a run whose CPU credit balance reaches zero, or that uses surplus credits, is flagged "credit-limited" because RDS CPU alone would not show the throttling | own margin; comparison plan section 3 |

Sources: Google Core Web Vitals TTFB guidance (corewebvitals.io); Nielsen Norman Group response-time limits; project scope.

**Comparison weights (locked by the user, 3 October 2026, before any recorded run)**

| Criterion | Measured by | Weight |
|---|---|---|
| Operational burden | Terraform lines and resources, boot-to-healthy time, steps to patch (not from this harness; partly judgement) | 25 |
| Replacement time and error window | kill to healthy again; failed requests | 25 |
| Steady-state latency | p95 at levels 10 and 100 | 20 |
| Cost | USD per 1,000 requests at capacity | 15 |
| Scale-out time | alarm to new healthy target | 10 |
| Capacity per unit | practical capacity from the saturation run | 5 |

Reasoning: one operator, always open, normal load far below one unit's capacity, a monthly cost gap of a few dollars. **Scoring:** for each criterion the better variant scores 10 and the other 10 x (best / value) (inverted for higher-is-better metrics); if the A and B min-max ranges across repeats overlap, both score 10 (a difference inside the noise does not count). The report shows the table so a reader can apply other weights.

## 4. Workload model

**One virtual user is one concurrent visitor slot.** It runs visits back to back; each visit starts with an empty cookie jar. Pacing is constant: page action *k* of a visit starts at *t0 + 36k* seconds, so the arrival rate is fixed by the user count. If an action takes longer than 36 s the next starts immediately and a **late start** is counted. Each user's first action is offset by a random 0 to 36 s so 1,000 users do not move in lock-step. A **page action** is one user step: a GET, or a form POST plus the redirect the browser follows (each HTTP request is logged separately).

| Visit type | Share | Page actions | Steps |
|---|---|---|---|
| Window shopper | 90% | 5 | `/` (302 to `/products/`), product detail, `/products/`, product detail, product detail |
| Cart abandoner | 7.5% | 6 | `/`, product detail, `GET /login/`, `POST /login/` (to the detail page), `POST /cart/items/` with `next`, `GET /cart/`; leaves |
| Buyer | 2.5% | 8 | The abandoner steps, then `GET /checkout/`, `POST /checkout/` (302 to `/orders/<id>/`) |

Mean 5.15 actions per visit (plan: about 5), a 185 s visit (plan: about 3 minutes), checkout requests about 1% of requests (plan: about 1%), 2.5% of visits ending in an order (plan: 2 to 3%; fashion benchmarks 1.5 to 3%). Add-to-cart is 10% of visits, above the 5 to 8% benchmark band (a conservative choice for load), and 75% of carts are abandoned, consistent with Baymard's 70% and Dynamic Yield's 78%. These are assumptions anchored to US/Shopify benchmarks, not facts about a Singapore SME. Logins are 10% of visits, one per visit. Products are chosen at random from the links on the page just loaded; the size is a random enabled option not flagged "only N left" (stock above 10).

| Users | Page actions/s | Visits/h | Logins per 5 min | Orders per 10 min | ALB requests per target per min (one unit, with D1) |
|---|---|---|---|---|---|
| 1 | 0.03 | 19 | 0.2 | 0.1 | 3 |
| 10 | 0.28 | 195 | 1.6 | 0.8 | 34 |
| 100 | 2.8 | 1,950 | 16 | 8 | 340 |
| 1,000 | 28 | 19,500 | 162 | 81 | 3,370 |

The saturation run uses the same mix with **no think time**.

**Repeatability.** One integer seed (default 42, recorded). Each user draws from `random.Random(f"{seed}:{user_index}")`, with user indices unique across Locust worker processes, so A and B and all repeats see the same visit sequences. Timing and live stock still vary, which is what repeats measure.

**Django behaviour.** Every form is fetched before it is posted and its `csrfmiddlewaretoken` is sent, with `Referer` and `Origin` set to our own HTTPS origin. Cookies persist within a visit. Redirects after a POST are checked (302 and `Location`), then followed as a browser would.

**Content validation.** A 200 error page is a failure.

| Request | Success when |
|---|---|
| `/products/` | 200 and at least 5 distinct `/products/<id>/` links (as `smoke.sh`) |
| Product detail | 200, a `product_id` select with an enabled option, a CSRF token |
| `GET /login/`, `GET /checkout/` | 200 and a CSRF token; checkout also a 64-hex `review` value |
| `POST /login/` | 302 to the requested `next` (a 200 means the login failed) |
| `POST /cart/items/` | 302 to `next`, and the followed page shows the "added to your cart" message |
| `GET /cart/` | 200 and at least one cart line |
| `POST /checkout/` | 302 to `/orders/<id>/`, whose page says the order is confirmed |
| Checkout 409 with the stock message, or an add refused for stock | **Stock conflict**: counted separately, not an error |
| Anything else (5xx, 503 page, timeout, connection error, idempotency 409, 200 "cart changed") | **Unexpected error** |

**Test accounts.** Imported customers have unusable passwords, so a separate setup command registers `loadtest-0001` and up through `/register/` (untimed, once; the accounts live in the shared RDS, so both variants use them). One password for all, from the environment. Pool: 1,100 accounts; user *i* always uses account *i*, so no two users share a cart. Setup is idempotent. Load orders are dated October 2026; the analytics refresh uses the fixed cutoff 2026-01-02, so they never enter the analytics evidence.

## 5. Open versus closed model

Locust is closed-model: a user waits for a response before the next request. Constant pacing fixes the arrival rate only while the server keeps up. When it falls behind, late starts reduce the real arrival rate and the percentiles understate what an open stream of visitors would see (coordinated omission). The harness reports intended and achieved rates and late starts per run, flags overloaded runs, and the README states the limitation. The saturation run is deliberately closed with no think time: it finds the throughput ceiling and the knee, not user-perceived latency.

## 6. Run types

All parameters are recorded in the run metadata; lengths are identical for A and B. The ladder keeps all four levels of the comparison plan.

| Type | Capacity (D3) | Load | Length | Repeats per variant |
|---|---|---|---|---|
| `smoke` (local) | n/a | 2 users, 3 s pacing, fixed visit sequence buyer / abandoner / shopper (section 15) | 75 s | as needed |
| `pilot` (RDS gate) | one unit | 1,000 users | as the ladder's 1,000 step | 1, on A only (not a comparison run) |
| `ladder` | one unit | 1, 10, 100, 1,000 users; spawn 1, 1, 2, 5 users/s | ramp + 120 s warm-up + measure 600 s (levels 1, 10) or 300 s (100, 1,000) | 3 per level |
| `saturation` | one unit | no think time; 1, 2, 4, 8, 16, 32, 64, 128, 256 users, 120 s per step (first 30 s of each step discarded); stops at the abort rule | up to 14 min | 1 (3 if time allows) |
| `scaleout` | autoscaling 1 to 2 | 10 users for 180 s, step to 200 users (set from the pilot), hold 900 s, back to 10 users for 300 s | 23 min plus returning to one unit | 3 (2 if time is short) |
| `replace` | two units pinned | 100 users; the user kills one unit at 300 s; hold to 1,200 s | 20 min | 3 (2 if time is short) |
| `singapore` | one unit | 10 users, from the laptop outside the region | as the ladder's 10 step | 1 per variant |

Estimated AWS time per variant: pilot 0.3 h (A only), ladder 2 h, saturation 0.4 h, scale-out 1.5 h, replacement 1 h, Singapore 0.2 h, resets and gaps about 1 h: **about 5 to 6 h for A**, a similar amount for B. `run.py` prints the expected duration and approximate cost before each run and asks for confirmation. Prices come from `prices.json` and are checked by the user.

## 7. Scale-out and replacement timings

AWS records the timestamps; nothing is read off graphs.

| Moment | Source |
|---|---|
| t0: load step starts | Locust log (UTC) |
| t1: scaling alarm enters ALARM | CloudWatch alarm history |
| t2: scaling action begins | A: ASG scaling activities; B: ECS service events |
| t3: unit running | EC2 launch time / ECS task start |
| t4: target first healthy | the **target-health watcher** (polls `describe-target-health` every 5 s, logs each state change) |

**Scale-out time = t4 - t1** (the plan's definition); t4 - t0 is also reported. Most of the detection delay is the scaling policy's alarm evaluation, not the platform; boot-to-healthy is where A and B differ. **Replacement time** = kill command (logged by the **kill helper**, which the user runs) to the healthy count returning to 2. **Error window** = first to last failed request after the kill, from the request log. Service events are exported before teardown because ECS loses them with the service.

## 8. Cost per 1,000 requests

`prices.json` holds the hourly prices (c5.large, Fargate vCPU-hour and GB-hour, ALB hour and LCU, WAF), each with its source and the date checked; the user verifies them. Cost per 1,000 requests = (compute + ALB cost per hour at the run's average unit count) / (requests per hour) x 1,000, reported at the saturation knee (equal capacity) and at each ladder level. RDS is shared and identical, so it is shown separately. Data transfer is not measured (comparison plan limitation).

## 9. Harness layout and data flow

```
tests/load/
  README.md            one command per run type, setup, limitations, results transfer
  requirements.in      direct dependencies (Locust, boto3)
  requirements.txt     every package pinned by exact version
  .env.example         LOAD_BASE_URL, LOADTEST_PASSWORD, LOADTEST_PREFIX
  .gitignore           .env, out/
  locustfile.py        visitor user, load shapes, per-request log, generator-CPU sampler, abort rule
  run.py               runs one run type: host allow-list, prints time and cost, writes run.json, launches Locust
  accounts.py          create (registration) and reset-carts, never timed
  aws_capture.py       export (CloudWatch, scaling activities, service events, alarm history, stack.json),
                       watch (target health), kill (one unit); laptop only, needs lab credentials
  analyze.py           raw files -> per-run, per-level and comparison tables, timings, scores; deterministic, stdlib only
  prices.json
  selftest.py          unit checks for redaction, percentiles and window maths
```

No harness file is named `test_*.py`: `tests/` is mounted into the CI container, `pytest /app/tests` collects `test_*.py` recursively, and Locust is not in the app image.

**Flow per run.** On the generator: `accounts.py reset-carts`, then `run.py <type> --variant <ec2|fargate> --repeat <n>` writes `out/<run-id>/`. Results move to the laptop through the existing S3 bucket (`exports/load/`). On the laptop: `aws_capture.py export <run-dir>` adds the AWS data, redacts, and copies the run into `evidence/raw/`. Raw files are never edited afterwards; `analyze.py` reads only `evidence/raw/` and rerunning it gives identical output.

**Files per run.** Locust `stats.csv`, `stats_history.csv` (`--csv-full-history`), `failures.csv`, `exceptions.csv`, `report.html`; `requests-w<k>.csv` (one row per HTTP request: UTC timestamp, user, visit, action, method, name, status, latency, bytes, outcome class); `generator_cpu.csv`; `run.json`; from the laptop `stack.json`, `cloudwatch/*.csv`, `events.json`, and `targets.jsonl` for scale-out and replacement.

**Measurement window and statistics.** Percentiles and rates come from `requests-*.csv` inside [ramp end + warm-up, + measure length), not Locust's whole-run totals. Percentiles use nearest-rank and each table shows *n*; p99 is shown only with at least 1,000 samples and p95 with at least 100 (level 1 gives about 17 samples per run, so its figure is the p50 across the three repeats). Per variant and level: median of the repeats with min and max. The comparison table puts A and B side by side with the B/A ratio and the section 3 scores. Invalid runs are listed with the reason and excluded; overloaded, database-limited and aborted runs are reported as results.

**Run metadata** (`run.json`, plus `stack.json`): run ID, variant, type, level, repeat; UTC start, ramp end, measurement start and end, end; exit status and abort reason; git commit and dirty flag; harness, Locust and Python versions; seed; the exact command line; generator location, instance type and clock offset; visit mix and pacing; from AWS at export: image digest, instance type or task size, desired/min/max, RDS class, WAF rule action and limit.

**Redaction** before anything reaches `evidence/raw/`: 12-digit account IDs (including inside ARNs) become `<ACCOUNT>`, public IPv4 addresses become `<PUBLIC-IP>`; private addresses and our hostnames stay. No passwords, cookies or CSRF tokens are ever logged. CloudWatch keeps 1-minute data for only about 15 days, so every run is exported before teardown.

**Generator.** In-region (us-east-1) on its own instance, never the laptop except the Singapore run. Locust runs with `--processes 2`. UTC everywhere; the clock offset comes from `chronyc tracking`.

## 10. What the harness needs from infrastructure (hand to the writing session)

1. **Load generator** in its own folder (for example `src/infrastructure/loadgen/`) so it is up only for test sessions: one AL2023 `c5.large` in a `base/` public subnet with a public IP, `LabInstanceProfile` (Session Manager, and S3 for moving the harness and results), a security group with **no inbound rules**, IMDSv2 required, user data installing `python3.12`, `python3.12-pip`, `git` and `tmux`, tag `Stack = loadgen`, output the instance ID.
2. **EC2 stack:** detailed monitoring on the launch template (1-minute instance CPU); ASG group metrics at 1-minute granularity (`GroupDesiredCapacity`, `GroupInServiceInstances`, `GroupPendingInstances`, `GroupTerminatingInstances`); variables to pin min, max and desired for fixed-capacity runs (D3). The launch-template change needs an instance refresh before the recorded runs.
3. **Fargate stack,** when written: the same outputs as `ec2/` (`hostname`, `target_group_arn`, `image_digest`, `web_acl_name`) plus `cluster_name`, `service_name`, `task_definition_arn`, `subnet_ids`, `security_group_ids` and `log_group_name` (for the one-off tasks of `aws_capture.py cpu`); the same scaling metric, target and limits as A; the same pinning variables; Container Insights optional (otherwise the harness uses `HealthyHostCount` and service events).
4. **Nice to have:** `alb_arn_suffix` and `target_group_arn_suffix` on both stacks, `db_instance_identifier` on `base/` (the capture script can derive them). **Not added** (review INF-010, INF-017): the capture script derives all three itself, so the outputs would be dead code.
5. **No WAF change:** load runs use the existing `count` default.

## 11. Local verification (before any AWS run)

Against the local Docker Compose stack with the dataset imported (`http://127.0.0.1:8000`; local mode has no HTTPS redirect, so `http` is allowed for localhost only): `accounts.py create --count 5`, a 60 s `smoke` run with 2 users and 10 s pacing that forces at least one login, add-to-cart and checkout, `accounts.py reset-carts`, then `analyze.py` on the output, plus `selftest.py`. Checks: CSRF and login work, an order is created and its page validates, a stock conflict is classified correctly if one can be provoked cheaply, every output file is produced and redacted, and the analysis runs from raw files alone. Nothing long or heavy runs locally. `aws_capture.py`, the generator and real scaling stay untested until the first cloud session, and the report says so.

## 12. Not measured, and why

- **Read replica.** Not used: the frozen app has one database connection and no read routing, sessions and carts need read-your-writes consistency, the database sees a few percent of one vCPU at the top level, and a replica is not high availability. The pilot is the test: if RDS CPU is above the gate on a saturated unit, size up first. The report names the replica as the scaling path with the pilot's numbers.
- Data transfer cost, ECS on EC2 and operator-dashboard load are outside the comparison.

## 13. Deliverables and order of work

1. This plan, approved.
2. `tests/load/` as in section 9, built in small steps with explanations; the user reviews each file.
3. `evidence/test-performance.md`: the evidence template, one entry per case with objective, setup, command/steps, expected result, actual result, date and artefact path (LOAD-01 pilot, LOAD-02 ladder, LOAD-03 saturation, LOAD-04 Singapore latency; RES-03 rows per D8).
4. Local verification (section 11) and a labelled Claude self-review, findings reported before fixing.
5. After approval: update the [TESTING.md](../TESTING.md) status line ("Locust load tests do not exist yet") and its "instance or task" wording, and the implementation plan status; hand section 10 to the user.

## 14. Open items

- [ ] User approves this plan.
- [ ] User hands section 10 to the writing session and tells R when the generator and the Fargate stack exist.
- [ ] Locust and boto3 versions pinned at implementation (latest stable that day, recorded).
- [ ] Scale-out step level (default 200 users) confirmed from the pilot.
- [ ] Verify in the RDS console which classes add CPU, not only memory.
- [ ] A recorded browser session (HAR) would confirm D1's static-request count (comparison plan open item).

## 15. As built: differences from sections 1 to 14 (3 October 2026)

The plan was approved and then built; these are the places where the code does something the text above does not say, or says differently. The code and `tests/load/README.md` are authoritative.

1. **Two account pools, not one.** Abandoners log in as `<prefix>-a-NNNN` and buyers as `<prefix>-b-NNNN` (1,100 of each, 2,200 in all), so a buyer's cart is always empty when it starts. Virtual user *i* uses account *i* modulo the pool.
2. **Cart cleanup is untimed and logged apart.** An abandoner's cart is emptied through the app once it holds more than 10 lines, and a buyer's cart after a stock-conflict checkout. These requests are logged with outcome `cleanup` and excluded from every statistic and from the abort rule's error count. `accounts.py reset-carts --from-run <run folder>` (D4) logs in only the accounts that added to a cart during that run; `--all` resets every account.
3. **Latency is measured per dynamic HTTP request**, static files reported separately, and `POST /checkout/` is its own series. The page-action thresholds in section 3 are applied to that per-request figure. Latency includes failed responses; connection failures with no response are errors and have no latency.
4. **Validation of the product detail page.** Anonymous: 200 and the log-in link. Logged in: 200, an add-to-cart form with a CSRF token and at least one enabled size (none enabled counts as a stock conflict, not an error).
5. **Smoke run.** 3 s pacing and a fixed visit sequence replace "10 s pacing" so a 75 s run reliably covers login, add to cart and checkout.
6. **One new shared file, `common.py`** (target allow-list, HTML parsing, redaction, percentiles, price helpers), so the logic exists once for `locustfile.py`, `accounts.py`, `analyze.py` and `aws_capture.py`.
7. **Files a run folder contains**, beyond section 9: `timing.json` (start and end in UTC), `abort.json` (only when aborted), `alarm_history.json`, `scaling_activities.json` (A) or `ecs_events.json` (B), `kill.json` and `targets.jsonl` (replacement and scale-out runs). `aws_capture.py watch` and `kill` write to `tests/load/aws-out/<run id>/` on the laptop and `export` merges them into `evidence/raw/<run id>/`.
8. **The abort rule's error and latency figures come from Locust's own statistics**, which count content-validation failures as failures, so it uses the same definition of error as the analysis.
9. **`prices.json` is unverified.** The figures were written from memory on 3 October and the file says so; `analyze.py` and `run.py` print that warning until the user sets `verified_by_user` to true.
10. **Schedules are fixed in `run.py`**, not configurable per run, so A and B always get the same test. The only schedule option is `--users-high` for the scale-out step (default 200).
11. **Replacement is graceful on both variants (review INF-002, 6 October 2026).** `aws_capture.py kill` asks the Auto Scaling group to terminate the instance (drained from the target group first, then replaced) on A, and stops one task on B (ECS drains, then SIGTERM). The test measures a planned replacement, not a crash; the report says so. `kill.json` records `mode: graceful`.
12. **Run validity from `stack.json` (INF-003).** `analyze.py` marks a run invalid when its image digest, RDS class or WAF mode differs from the campaign's (the value most runs agree on), when min/max capacity is not the pinned value for its run type, when `stack.json` describes the other variant, or when the healthy targets at the start of measurement are not as intended (from `alb_healthy_hosts`). Missing `stack.json` or healthy-host data is flagged, not invalid.
13. **Error window bounded (INF-004).** For a replacement run it covers the errors from the kill until healthy again plus 30 s (to the end of the run if it never recovered); later errors are counted apart (`errors_later`).
14. **Database figures per step (INF-014):** the saturation table shows RDS CPU and credit balance for each step's own window.
15. **CPU model (INF-016):** `aws_capture.py cpu --variant ...` records the processor model once per variant per session; `export` adds it to each run as `cpu.json` and the report prints it.
16. **No `RunningTaskCount` query:** Container Insights is off (ADR-015), so that series was always empty and was removed. **`LOAD_DOMAIN`** sets the domain of the allowed hostnames (default `fourtytwofactors.me`) for another account.
17. **Healthy targets at the start (INF-020).** Scale-out and replacement runs read the count from the watcher's `targets.jsonl` (exact, timestamped); the single-unit runs use the CloudWatch `HealthyHostCount` average, whose zone aggregation is confirmed on the first pilot. **`--reference`** (INF-018) states the campaign's fixed values; the report lists every distinct value found. A CPU model recorded more than 12 h from the run is flagged (INF-021).
