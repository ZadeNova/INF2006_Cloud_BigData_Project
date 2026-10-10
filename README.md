# 42Factors: a small online shoe shop with a sales and inventory dashboard, deployed and measured on AWS

INF2006 Cloud Computing & Big Data · Group 21 (G021) · Submission: Sunday 11 October 2026, 23:59 Singapore time

## Problem

A small online shoe shop has two users with different problems. **Customers** need to register, browse sized products, keep a cart and place a simulated order that is never duplicated or oversold. The **store operator** needs an understandable view of sales trends and of which sizes need replenishing. 42Factors is that shop (Django, PostgreSQL, HTMX) running on synthetic data on AWS, with its scaling and recovery measured. Payments are simulated and no personal data is used.

## Status

- **Final architecture: variant B**, containers on Amazon ECS on Fargate behind an HTTPS load balancer, with a private RDS PostgreSQL database ([ADR-018](docs/decisions/ADR-018-final-architecture-ecs-fargate.md)). Variant A (EC2 + Auto Scaling group) was built from the same module and measured as the evaluated alternative. B was chosen for faster replacement (50 s against 114 s), faster scale-out and no host patching; A has the higher ceiling and the lower unit price (indicative, n = 1). Rejected as unsuited to a small Django shop: AWS Lambda, Amazon EKS, and Elastic Beanstalk or App Runner.
- Both variants were deployed with Terraform, measured (A on 8 October, B on 9 October 2026) and torn down. **Nothing here needs a live cloud account**: the configuration and the dated, redacted evidence are in the repository.
- The application and its automated suite run offline with Docker only (497 passed, 8 skipped, recorded 27 September 2026 in [tests/README.md](tests/README.md), and reproduced on a clean clone on 9 October 2026: [REPRO-01](evidence/raw/REPRO-01_2026-10-09_linux_clean-clone.txt)).

Every result below is one repeat per condition (n = 1) and indicative only.

| Measured on AWS | A: EC2 + Auto Scaling group | B: ECS on Fargate (final) |
|---|---|---|
| Load step to a second healthy unit | 460 s | 407 s |
| Removed unit replaced, to two healthy | 114 s | 50 s |
| Failed requests during the replacement run | 0 of 7,474 | 0 of 7,474 |
| Ceiling of one unit | 118.8 requests/s | 105.5 requests/s |
| Deployed security checks SEC-09, 10, 11, 18 | PASS | PASS (SEC-17 WAF block also PASS) |

## Quickstart (offline, Docker only)

Needs Docker Desktop with Compose 2.20 or later. From the repository root:

```powershell
python src/tools/init_env.py                 # once: random local secrets into the git-ignored src/.env
docker compose up --build -d --wait          # build, migrate, start PostgreSQL and the shop
docker compose run --rm web pytest -q -p no:cacheprovider /app/tests     # automated suite
```

The shop starts empty. Build the derived shoe dataset from the committed raw data (Python standard library only; `data/derived/shoes/` holds only its checksums and product map), load it, then open <http://127.0.0.1:8000/>:

```powershell
python analytics/build_shoe_dataset.py
docker compose run --rm web python manage.py import_dataset --source /app/data/derived/shoes --namespace synthetic/shoes/revision-a/demo/v1
docker compose run --rm web python manage.py seed_demo --no-products
docker compose run --rm web python manage.py refresh_analytics --as-of 2026-01-02
```

On macOS and Linux use `python3`. Stop with `docker compose down` (keeps the database).

- Operator login for `/analytics/` and the other routes: [src/README.md](src/README.md#demo-data).
- Reproduce the analytics checks offline: [analytics/README.md](analytics/README.md).
- Set up a blank machine: [docs/SETUP.md](docs/SETUP.md).

## Reproduce it

Marking needs only level 1: no cloud account and no purchase. Levels 2 and 3 are optional and need two things you must bring yourself: your own AWS Learner Lab, and **a domain you own (or a subdomain its owner delegates to you)**, because HTTPS needs a certificate that AWS validates through DNS. A domain costs about USD 1 to 3 for the first year at the cheapest registrars. This is an unavoidable cloud prerequisite: without a domain the cloud stack cannot be built, and the dated evidence in `evidence/` stands in for it. The stacks used for the evidence are torn down.

| Level | What you need | Cost | Steps |
|---|---|---|---|
| 1. Offline: the shop, tests, data, analytics and load tables from the recorded raw files | Docker, Python 3 | none | Quickstart above; [docs/SETUP.md](docs/SETUP.md) |
| 2. Cloud: variant B built from the Terraform | AWS Academy Learner Lab, a domain (or delegated subdomain) you control, Terraform, AWS CLI | about USD 3.5 per day while running, plus about USD 1.2 per day for the shared base (list prices, 9 October 2026) | [docs/REPRODUCE_CLOUD.md](docs/REPRODUCE_CLOUD.md) (also states what has and has not been proven), [src/infrastructure/README.md](src/infrastructure/README.md) |
| 3. Load test against your own stack | Level 2 plus a load-generator instance | about USD 0.1 per hour for the generator | [docs/RUN_LOADTEST.md](docs/RUN_LOADTEST.md) |

## Architecture

![Architecture of the final system (variant B, ECS on Fargate)](evidence/architecture.png)

Browser → HTTPS load balancer (WAF, ACM certificate) → one or two Fargate tasks running one Django container → private RDS PostgreSQL. There are no sticky sessions: sessions and carts live in PostgreSQL. Secrets come from Secrets Manager at start-up, the image from ECR, the dataset and exports from a private S3 bucket, and JSON logs and alarms go to CloudWatch and SNS. The diagram labels components with their AWS service names (and the Terraform name on the main request path); [evidence/architecture.md](evidence/architecture.md) maps every label to its Terraform resource, its file and its test.

Why this design and the alternatives that were rejected: [ADR-018](docs/decisions/ADR-018-final-architecture-ecs-fargate.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/AWS_INFRASTRUCTURE.md](docs/AWS_INFRASTRUCTURE.md).

## Technology

| Area | Selection |
|---|---|
| Application | Django 5.2, Gunicorn, WhiteNoise, Django templates with HTMX |
| Data | PostgreSQL 17: Docker locally, Amazon RDS on AWS |
| Analytics and ML | Django management commands and SQL; pandas for independent checks; scikit-learn K-means as an offline batch |
| Cloud | ECS on Fargate, ALB, WAF, ACM, Route 53, RDS, S3, ECR, Secrets Manager, CloudWatch, SNS |
| Infrastructure as code | Terraform (`src/infrastructure/`) |
| Verification | pytest with pytest-django on real PostgreSQL; Locust for load |

## Data and analytics

- **Source:** the Analytics Engineering Ecommerce Sales Dataset v1.0.0 (synthetic, CC BY 4.0), checksummed in `data/raw/`. `analytics/build_shoe_dataset.py` rebuilds it as 20 shoe models in 10 sizes (200 products) with the same customers, orders and lines.
- **Dashboard** (`/analytics/`, operator only): daily and category sales, top models, sales by size, 7-day average, stock coverage and replenishment flags, each with its formula and freshness. An independent pandas recomputation found 0 mismatches.
- **Segmentation:** descriptive RFM K-means, trained offline. A 90-day hold-out shows the segments do not predict repurchase on this synthetic data, and that is reported as measured.
- Details: [data/README.md](data/README.md), [data/DATA_DICTIONARY.md](data/DATA_DICTIONARY.md), [evidence/test-data-ai.md](evidence/test-data-ai.md).

## Evidence

Each record opens with a results table and gives the objective, setup, command, expected result, actual result, date and artefact path. [evidence/README.md](evidence/README.md) is the single index; `evidence/raw/` holds the unedited output behind each claim.

| Brief requirement | Record | Result |
|---|---|---|
| Functional workflow | [test-functional.md](evidence/test-functional.md) | FUNC-01 and FUNC-02 PASS locally; FUNC-03 part 1 PASS on A and B; part 2 (browser steps on AWS) not evidenced |
| Security control | [test-security.md](evidence/test-security.md), [threat-control-map.md](evidence/threat-control-map.md) | Local SEC-01 to 08 and 12 to 16 PASS; cloud SEC-09, 10, 11, 18 PASS on A and B; SEC-17 on B only; 19 threats mapped; 7 scans triaged, 4 findings open |
| Data and AI validation | [test-data-ai.md](evidence/test-data-ai.md) | DATA-01 PASS (0 mismatches); DATA-02 PASS with no predictive claim; not run on AWS |
| Scalability and resilience | [test-resilience.md](evidence/test-resilience.md), [test-performance.md](evidence/test-performance.md), [load-summary.md](evidence/load-summary.md) | Scale-out, replacement and saturation measured on A and B (n = 1); RES-04 session continuity held in the recorded sample |
| Monitoring | [monitoring.md](evidence/monitoring.md) | MON-01 PASS with one deviation; MON-02 one of two queries defective; MON-03 partial; MON-04 PASS |
| Reproduction | [REPRO-01](evidence/raw/REPRO-01_2026-10-09_linux_clean-clone.txt) | Clean clone, offline: build, 497 tests, demo data, analytics and load tables, about 2 minutes of machine time |
| Machine-readable summary | [project_manifest.yaml](project_manifest.yaml) | Every path in it exists |
| Report | [report.pdf](report.pdf) | 13 pages in total; sections 1 to 8 end on page 10 (limit 12 excluding references and appendices) |
| Declarations | [TEAM_CONTRIBUTIONS.md](TEAM_CONTRIBUTIONS.md), [AI_USE_DECLARATION.md](AI_USE_DECLARATION.md) | Review logs for AI-assisted changes: [docs/reviews/](docs/reviews/) |

## Team

| Name | Student ID | Role |
|---|---|---|
| LIM CHEE LONG | 2500584 | Assistant Cloud + Backend |
| MOHAMMED SYAHFARIZ BIN EFFENDY | 2500717 | Testing of the Application, UIUX, Report |
| MUHAMMAD ERFAN BIN MOHAN | 2500722 | Cloud Lead + Backend + Load testing |
| JUN KEAT LIM | 2501004 | Report + UIUX |
| PHUA KIA WEN HERMANN | 2501300 | Testing of the Application, Report |

## Known limitations

- **Load and recovery:** one repeat per condition; the replacement test is a graceful removal, not a crash; scale-in was not observed on A; no database failover test was run; RDS is single-AZ. The two variants ran on different CPU models and the 3D models are not fetched by the load test.
- **Database availability:** one RDS instance, Single-AZ, with automated backups configured for 7 days (no restore was tested). It is a single point of failure by design: Multi-AZ is a one-setting change at about twice the instance charge, not enabled for cost and time, and no failover was tested. A read replica was not added because it spreads reads and gives no automatic failover, and measured RDS CPU never exceeded 10.46% ([ADR-004](docs/decisions/ADR-004-one-rds-instance-db-t4g-small.md)).
- **Least privilege:** the Learner Lab forces the broad `LabRole` for every runtime role, so separation rests on security groups and separate database logins (threat T19, accepted). There is no app-level login throttling and no MFA; the WAF block was tested on B only.
- **Data:** the dataset is synthetic with weak patterns, so the dashboard shows the mechanism, not real demand. Segmentation is descriptive. Neither the segmentation nor the independent refresh check was run on AWS.
- **Monitoring:** one of two saved log queries is defective (fixed in code after the session, not re-run), and each alarm-email leg is recorded on one variant only.
- **Not done:** a scheduler for the analytics refresh (it is a manual command), saved-model inference, hosted CI verification, and the logged independent review of the latest changes (open review gates are listed in [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)).
- **Region:** the lab offers only `us-east-1`; a Singapore shop would use `ap-southeast-1`.
- **Cloud reproduction:** rebuilding the cloud stack in another account needs a domain or a delegated subdomain (see *Reproduce it*). No second-account build is recorded, and variant B's fresh-database bring-up was tested offline only ([ADR-019](docs/decisions/ADR-019-variant-b-sets-up-its-own-database.md)).

## Repository layout

```text
src/            Django application; Terraform in src/infrastructure/
data/           raw and derived datasets, provenance, data dictionary
analytics/      dataset builder, profiler, verification, segmentation, evaluation
tests/          pytest suite (real PostgreSQL) and the Locust load harness
evidence/       test records, diagram, raw/ command output
docs/           contracts, decision records (docs/decisions/), review logs, plans
```

New to the project? [docs/GUIDE.md](docs/GUIDE.md) explains where each claim is evidenced and what every script does. [AGENTS.md](AGENTS.md) is a short repository guide (the original agent instruction files are archived in [docs/archive/agent-instructions/](docs/archive/agent-instructions/)); requirements and dates are in [PROJECT_SCOPE_INF2006.md](PROJECT_SCOPE_INF2006.md); status is in [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md).
