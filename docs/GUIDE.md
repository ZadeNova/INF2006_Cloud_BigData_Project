# Project guide: what is where, and what every script does

> Final architecture: variant B (ECS on Fargate), ADR-018. Variant A (EC2) = evaluated alternative.

For team members and markers who open this project for the first time. No cloud account is needed to read the evidence or run the application; the cloud scripts are documented so you can see exactly what was done and repeat it if you have a Learner Lab account.

**Status (9 October 2026):** the scripts below are all written. The cloud scripts (`evidence.sh`, the load harness against AWS) ran on variant A on 8 October and on variant B (the `fargate/` stack) on 9 October 2026. The current index of what was run, with results, is [evidence/README.md](../evidence/README.md). The test records in `evidence/` say which cases have been run and which are still planned.

## 1. Pick your path

Installing the tools on a new machine (Windows, macOS, Linux) and the offline run, with measured timings: [SETUP.md](SETUP.md).

| You are | You want | Start here |
|---|---|---|
| A marker with only Docker | Run the shop and its tests on your machine | [Section 2](#2-run-it-on-your-machine-no-cloud-account-needed) |
| A marker reading evidence | Check a claim in the report | [Section 4](#4-where-the-evidence-is-and-how-to-check-a-claim), starting at [evidence/README.md](../evidence/README.md) |
| A teammate with a Learner Lab account | Start or stop the AWS stacks | [src/infrastructure/README.md](../src/infrastructure/README.md) (quick start at the top) |
| A teammate running the evidence session | Collect the cloud evidence | [docs/plans/evidence-session.md](plans/evidence-session.md) |
| Anyone | Know what a script does | Sections [5](#5-shell-scripts) and [6](#6-python-scripts) |

## 2. Run it on your machine (no cloud account needed)

You need Docker with Compose 2.20 or newer. From the repository root:

```bash
python3 src/tools/init_env.py          # once: writes random local secrets to src/.env (never printed)
docker compose up --build              # starts the database and the shop at http://127.0.0.1:8000/
docker compose run --rm web pytest -q -p no:cacheprovider /app/tests     # the automated tests
docker compose run --rm web python manage.py check_database              # is the database reachable, are migrations applied
```

Loading the demo shoes and the analytics dashboard needs a few more commands: see [src/README.md](../src/README.md), section "Demo data". Everything runs in containers; nothing is installed on your machine apart from Docker.

## 3. The repository at a glance

```text
README.md, project_manifest.yaml     entry point and the machine-readable summary of the submission
report.pdf                           the report (headings required by the brief)
TEAM_CONTRIBUTIONS.md, AI_USE_DECLARATION.md
src/                                 the shop (Django), the Dockerfile and compose.yaml, tools/, and infrastructure/
  infrastructure/                    Terraform and the scripts that start and stop AWS (section 5)
data/                                the dataset, the derived shoe dataset, DATA_DICTIONARY.md
analytics/                           offline analysis and machine-learning scripts (section 6)
tests/                               automated tests (pytest) and tests/load/, the load-test harness
evidence/                            dated test records and their raw output (section 4)
docs/                                contracts, decisions (index: docs/decisions/README.md), plans, and review logs
```

## 4. Where the evidence is, and how to check a claim

Evidence has three layers. Every claim in the report points at one of them.

| Layer | Where | What it is |
|---|---|---|
| 1. Test records | `evidence/test-functional.md`, `test-security.md`, `test-data-ai.md`, `test-resilience.md`, `test-performance.md`, `monitoring.md`, `threat-control-map.md` | One entry per test case: objective, setup, command, **expected** result (written before the run), **actual** result, date, artefact path |
| 2. Raw output | `evidence/raw/` | The unedited output each entry cites, with its date, commit and exact command in the first lines |
| 3. Build record | `evidence/aws-build-runbook.md` | Dated entries for every AWS apply: what was built, from which commit, what failed, what it cost |

The index of cases and their status is [evidence/README.md](../evidence/README.md). Status words: `PASS` (ran and matched the expectation written first), `FAIL` (kept and explained), `PARTIAL` (part of the expectation met, the gap stated), `NOT RUN`.

### Reading a raw file name

Raw files are named `<CASE>_<UTC date>_<variant>_<step>.txt`, for example `SEC-17_2026-10-08_ec2_burst.txt`. `ec2` is variant A (EC2 with an Auto Scaling group) and `fargate` is variant B (containers on ECS Fargate). Both serve the same shop from the same image and database.

| Prefix | Meaning |
|---|---|
| `FUNC-` | Functional workflow: register, cart, checkout, order history |
| `SEC-`, `SCAN-` | Security controls and automated scans (secrets, dependencies, image, infrastructure code) |
| `DATA-` | Analytics and machine learning checks |
| `RES-`, `LOAD-` | Scale-out, replacement and load runs: each is a **folder** (see below) |
| `MON-` | Monitoring: log samples, saved log queries, an alarm and its email |
| `PRE-` | Pre-flight checks before an AWS session (image present, roles allowed, alarm email confirmed) |
| `OPS-` | Timed `up`, `down` and capacity changes, for the operations section of the report |
| `SESSION-` | Resource IDs kept so metrics can be found after a stack is torn down |

A load or scale-out run folder, such as `RES-03-ec2-scaleout-r1_2026-10-08/`, holds the request log (`requests-*.csv`), Locust statistics, `run.json` (what was run: times, commit, exact command), `stack.json` (what it ran on: image digest, capacity, database class, WAF mode), `targets.jsonl` (target health over time), and after export `cloudwatch/*.csv` (1-minute metrics), `alarm_history.json` and `scaling_activities.json` (or `ecs_events.json` for Fargate).

### How AWS data and logs reach this folder

| What | Where it starts | How it gets to `evidence/raw/` |
|---|---|---|
| Application logs, saved log queries | CloudWatch Logs (deleted with the stack, 7-day retention) | `evidence.sh <variant> logs` runs the queries and saves the results (`MON-01`, `MON-02`, `SEC-18`) |
| Metrics (CPU, latency, healthy targets, database, WAF) | CloudWatch | `aws_capture.py export` writes `cloudwatch/*.csv` into each run folder |
| Alarm history and the SNS email | CloudWatch, the operator's inbox | `evidence.sh <variant> alarm` saves the history as text; the two emails are cropped screenshots |
| Scaling activity, ECS events | Auto Scaling, ECS | `aws_capture.py export`, into the run folder |
| Load results | the load-generator instance | copied to S3 and the laptop, then exported |
| Security configuration (database private, buckets private, security groups, secrets) | AWS APIs | `evidence.sh <variant> security` saves the API output as text |

### Redaction

Every file written by `evidence.sh` or `aws_capture.py export` is redacted when it is saved: 12-digit account IDs become `<ACCOUNT>`, public IP addresses `<PUBLIC-IP>`, email addresses `<EMAIL>`. Passwords, access keys, Terraform state and `.tfvars` files are never copied into the repository. A marker therefore sees the real commands and results with only those values replaced. Screenshots are supplements: each has a text file beside it that carries the same fact.

### Checking a claim in three steps

1. In the report or manifest, follow the path to the test record, for example `evidence/test-security.md`, case SEC-17.
2. In that case, read the **expected** result and the **actual** result, and open the raw file it names.
3. In the raw file, the first lines give the date, commit and command, the last line the exit code; compare the output with the expectation. A failed or surprising result is kept and explained, never removed.

## 5. Shell scripts

All are in `src/infrastructure/scripts/` unless stated. Each prints a usage line when run without arguments. **Credentials** means Learner Lab credentials in your shell (`labcreds`, see the infrastructure README); they expire after about four hours.

### Day-to-day (what a person types)

| Script | What it does | Credentials | Changes AWS |
|---|---|---|---|
| `status.sh` | Checks your tools and credentials, shows what each stack has built and whether AWS agrees, and prints the next command. Run it first | optional | no |
| `up.sh base` | One-time set-up of a new account: S3 bucket, `terraform.tfvars`, the shared base (network, database, DNS, certificate, registry, secrets, alerts) | yes | yes |
| `up.sh ec2` / `up.sh fargate` | Starts a variant: picks the image, shows the Terraform plan, asks you to type `yes`, applies, runs the database jobs it needs, then the smoke test | yes | yes (costs money) |
| `up.sh loadgen` | Starts the load-generator machine used for benchmarks | yes | yes (costs money) |
| `down.sh <ec2\|fargate\|loadgen>` | Destroys that stack and lists anything billable left behind. The shared base stays | yes | **destroys** |
| `smoke.sh <ec2\|fargate\|hostname>` | Eight outside-in checks: health page, HTTP redirects to HTTPS, certificate, login and product pages, product list not empty, three security headers. PASS/FAIL per line | **no** | no |

### Helpers (called by the scripts above; use directly for a faster or partial run)

| Script | What it does |
|---|---|
| `tf.sh <folder> plan\|apply` | The only way Terraform is run here: format and validate, save a plan, record the commit, and apply only that saved plan from that commit. Refuses uncommitted changes, an image mismatch between the variants, and a Fargate command that no longer matches the Dockerfile |
| `push-image.sh [sha]` | Builds the application image only if its tag is missing, pushes it to the registry, adds a `release-<sha>` tag, and records the tag for the stacks |
| `secrets.sh fill\|check` | Completes the secrets in Secrets Manager, or checks them. Prints key names and match/DIFFER only, never a value |
| `jobs.sh ec2 <job>` | Runs one database job on the instance through Session Manager: `bootstrap` (roles), `migrate`, `trainer-sql`, `restart`, `check`, `import` (the dataset from S3), `operator` (the operator login), `refresh` (analytics), or `all` |
| `jobs.sh fargate <job>` | The same for Fargate, as a one-off container task: `bootstrap`, `migrate`, `check`, `import`, `operator`, `refresh`, or `all`. Only `trainer-sql` and `restart` stay on variant A (the trainer login serves the offline ML training, not the shop) |

### Evidence recording: `evidence.sh`

One script records the cloud evidence, the same way for both variants, into `evidence/raw/` (dated, redacted, nothing overwritten). Procedure: [docs/plans/evidence-session.md](plans/evidence-session.md).

| Command | Records |
|---|---|
| `evidence.sh preflight` | `PRE-`: image in the registry, the lab role can run Fargate tasks, service-linked roles, Fargate quota, alarm email confirmed |
| `evidence.sh <v> up` / `down` | `OPS-`: the timed start and stop |
| `evidence.sh <v> security` | `SEC-09` database and storage private, `SEC-10` HTTPS enforced, `SEC-11` secrets from Secrets Manager, plus resource IDs |
| `evidence.sh <v> func` | `FUNC-03`: the buy-a-pair visit run against the live shop, exported, with a summary |
| `evidence.sh <v> pin MIN MAX DESIRED count\|block` | `OPS-`: sets capacity and the WAF mode, applies, waits until the targets are healthy |
| `evidence.sh <v> alarm` | `MON-03`: forces an alarm, waits for OK, saves the history (the email screenshots are added by hand) |
| `evidence.sh <v> waf` | `SEC-17`: a login-guessing burst against the WAF in block mode |
| `evidence.sh <v> logs` | `MON-01`, `MON-02`, `SEC-18`: log sample, saved queries, a search for secrets in the logs |
| `evidence.sh rec NAME COMMAND...` | Any other command, recorded the same way |

### Run automatically (you never type these)

| Script | When it runs |
|---|---|
| `src/infrastructure/loadgen/user_data.sh` | On first boot of the load-generator machine: installs Python 3.12, git and tmux |
| `src/infrastructure/ec2/user_data.sh.tftpl` | On every boot of an application instance: pulls the image and starts the container |
| `src/docker/10-local-role.sh` | The first time the local database container starts: creates the limited application database role |
| `.github/workflows/ci.yml` | On each push to GitHub: builds the image and runs migrations, checks and the test suite |

## 6. Python scripts

Python tools are grouped by what they are for. "Needs" says what must be installed.

### The shop (inside the Docker image)

| Script | What it does |
|---|---|
| `src/tools/init_env.py` | Creates the local configuration `src/.env` once, with random secrets, without printing them or replacing an existing file |
| `src/tools/db_bootstrap.py` | Creates the two database roles (schema owner and runtime) on a new database. Run by `jobs.sh bootstrap`, never at boot |
| `src/tools/collect_static.py` | Gathers the shop's CSS, JavaScript and images while the image is built |
| `src/tools/aws_capability_check.py` | Read-only probe of what the Learner Lab allows. Creates nothing; writes a Markdown record |
| `manage.py` commands | `check_database` (is the database reachable and migrated), `seed_demo` (demo products and operator; safe to repeat), `import_dataset --source --namespace` (loads the dataset), `snapshot_inventory --as-of` (seals stock as a version), `refresh_analytics --as-of` (builds the dashboard figures), `load_customer_segments --run-id --input` (loads the machine-learning segments) |

### Analytics and machine learning (`analytics/`, outside the web image)

Needs: the pinned `analytics/requirements.txt` (pandas, scikit-learn). Setup and reproduction: [analytics/README.md](../analytics/README.md).

| Script | What it does |
|---|---|
| `profile_dataset.py` | Checks the raw CSVs for integrity and writes `data/PROFILE.md` |
| `build_shoe_dataset.py` | Rebuilds the shoe dataset in `data/derived/shoes/` from the unchanged raw files (same input gives byte-identical output) |
| `export_coverage.py` | Exports the production analytics figures to a file, as the target to check |
| `verify_refresh.py` | Recomputes those figures independently from the raw tables with pandas and compares: zero mismatches is the pass |
| `segment_customers.py` | Customer segmentation (RFM with K-means) for one analytics run, written to a JSON file |
| `evaluate_segments.py`, `evaluate_holdout.py` | Compare segmentation recipes, and test stability (80% subsamples) and whether segments predict later purchases (90-day hold-out). Aggregates only, no customer rows |
| `data/raw/starter/analysis.py` | The dataset publisher's starter profile, kept for reference; not part of the pipeline |

### The load-test harness (`tests/load/`)

Needs: `tests/load/requirements.txt` (Locust, boto3; Python 3.12 or 3.14). `analyze.py` and `common.py` use only the standard library. Full instructions: [tests/load/README.md](../tests/load/README.md).

| Script | What it does | Run from |
|---|---|---|
| `run.py` | Runs one test of one type (`smoke`, `pilot`, `ladder`, `saturation`, `scaleout`, `replace`, `singapore`) on a fixed schedule; prints the expected duration and cost and asks first; writes a run folder | the load generator (or the laptop for `smoke` and `singapore`) |
| `locustfile.py` | The simulated visitors (shopper, cart abandoner, buyer). Started by `run.py`; not run directly | (by `run.py`) |
| `accounts.py` | `create` makes the synthetic test accounts through the normal registration form; `reset-carts` empties their carts between runs | generator or laptop |
| `aws_capture.py` | `watch` records target health over time; `kill` removes one unit gracefully (asks first); `cpu` records the processor model; `export` copies CloudWatch, scaling and alarm data into the run folder and redacts it | the laptop (holds the lab credentials) |
| `analyze.py` | Turns run folders into tables: latency, throughput, errors, scale-out and replacement times, cost per 1,000 requests, weighted comparison. Offline | any machine |
| `selftest.py` | Checks the harness's own logic with no network (15 checks) | any machine |
| `common.py` | Shared rules: allowed target hosts, redaction, percentiles | (imported) |

### Test helpers

| Script | What it does |
|---|---|
| `tests/verify_runtime_image.py` | Manual local check of the built image and TLS; no AWS calls |
| `tests/db_helpers.py`, `tests/analytics_helpers.py` | Shared builders for the tests; not tests themselves |

## 7. One cloud session in one picture

```text
labcreds  ->  status.sh  ->  evidence.sh preflight
                                   |
             evidence.sh ec2 up    |          (same steps again for fargate)
                  |                |
        evidence.sh ec2 security / func
                  |
   run.py (on the generator)  +  aws_capture.py watch (laptop)  ->  run folder
                  |                                                    |
        copy to S3 / laptop  ->  aws_capture.py export  ->  evidence/raw/<RUN-ID>/
                  |
        evidence.sh ec2 alarm / waf / logs   ->  evidence/raw/MON-*, SEC-*
                  |
        evidence.sh ec2 down
                  |
   analyze.py  ->  evidence/load-summary.md   ->  test records filled in  ->  report
```

## 8. What is safe to run

| Kind | Commands |
|---|---|
| **Read-only, any time** | `status.sh`, `smoke.sh`, `analyze.py`, `selftest.py`, `aws_capability_check.py`, `jobs.sh <v> check`, `secrets.sh check` |
| **Changes AWS and costs money while it runs** | `up.sh`, `evidence.sh <v> up\|pin\|waf\|alarm`, `run.py` against a stack, `aws_capture.py kill` |
| **Destroys** | `down.sh`, and the final teardown of the shared base (documented separately in the infrastructure README) |
| **Local only, free** | everything in Section 2, and the `analytics/` scripts |

## 9. Quick answers

- **I have no AWS account. Can I still check everything?** Yes: the test records and raw files are the evidence, the local run and tests are in Section 2, and `analyze.py` and `selftest.py` run offline. The cloud stacks are torn down between sessions on purpose.
- **Why two variants?** The team compared the same shop on EC2 with an Auto Scaling group and on ECS Fargate before choosing one; the method and weights were fixed first ([docs/plans/aws-ecs-comparison.md](plans/aws-ecs-comparison.md)). Decisions are in `docs/decisions/ADR-*`.
- **Why are some results labelled "indicative, n = 1"?** One repeat per condition fits the lab window; with so few repeats a difference between A and B may be noise. The test records state this wherever it applies.
- **A test failed. Is it hidden?** No. Failures are kept with a diagnosis and next step, as the brief asks.
- **Where is the architecture diagram?** At `evidence/architecture.png` once it is drawn (not there yet as of 8 October); its labels will match the Terraform resource names. Until then [docs/ARCHITECTURE.md](ARCHITECTURE.md) describes the same components in text.
