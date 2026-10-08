# INF2006: E-Commerce Core with Sales and Inventory Analytics

A small ecommerce service for customers to browse products, manage a cart and place simulated orders, with an operator dashboard that explains sales trends and inventory replenishment needs. The project demonstrates secure AWS deployment, persistent cloud data, reproducible analytics, and measured scaling and recovery.

**Status (1 October 2026):** The application runs locally in Docker as 42Factors, a small online shoe shop. Registration/login, the shoe catalogue with sizes, persistent cart, idempotent checkout, order history, the imported dataset, the analytics refresh, the operator dashboard and the descriptive customer segmentation are implemented; earlier work was independently reviewed as recorded in [docs/reviews/](docs/reviews/), and the latest changes (shoe catalogue onward) are awaiting their logged independent review. Local functional, security and data/AI evidence was recorded on 26 September 2026, including a human browser walkthrough of the redesigned storefront; see [evidence/](evidence/README.md). **AWS (1 October 2026):** variant A (EC2 behind an HTTPS load balancer, with RDS PostgreSQL 17) is deployed with Terraform and verified at `https://shop-ec2.fourtytwofactors.me`: dataset imported with zero rejects, least-privilege database logins tested, scaling policy, alarms and a WAF login rate limit applied. The stack is torn down between work sessions to save credit. No load test, scaling, recovery or monitoring evidence is recorded yet, and variant B (ECS on Fargate) is not built ([how to run it](src/infrastructure/README.md), [build record](evidence/aws-build-runbook.md)). See the [implementation tracker](docs/IMPLEMENTATION_PLAN.md) for current progress.

**Module:** INF2006 Cloud Computing & Big Data

**Submission:** 11 October 2026, 23:59 Singapore time

**Team:** Five members; two primary developers and three members supporting testing, reporting and administration.

## Team members

To be completed by the team. Keep final details consistent with the manifest and contribution record.

| Name | Student ID | Role |
|---|---|---|
| TODO | TODO | TODO |
| TODO | TODO | TODO |
| TODO | TODO | TODO |
| TODO | TODO | TODO |
| TODO | TODO | TODO |

## Features

Implemented, running locally in Docker; variant A was also deployed to AWS on 1 October 2026 and is torn down between sessions (see the status above):

- Registration, login/logout and shared database-backed sessions.
- Shoe catalogue: 20 shoe models, each sold in 10 US sizes (7 to 11.5) with its own stock, with 3D previews and a product detail page; persistent shopping cart.
- Simulated checkout with server-side prices, transactional stock updates and duplicate-request protection.
- Owner-only order confirmation and history.
- Operator-only sales and inventory dashboard at `/analytics/` with reporting dates, freshness and interpretable replenishment flags.
- A narrow operator addition beyond the brief: search, filter and activate or deactivate individual sizes at `/products/manage/`.
- Included descriptive customer segmentation (RFM K-means): trained offline by `analytics/segment_customers.py`, loaded per analytics run by `load_customer_segments`, shown as a panel on the dashboard when a run has assignments. It is descriptive only on synthetic data. Its evaluation is recorded in [evidence/test-data-ai.md](evidence/test-data-ai.md): separation and seed stability, 80% subsample stability, and a 90-day hold-out check showing the segments do not predict later repurchase on this synthetic data.

Not implemented: the Fargate variant, the scheduler for the analytics refresh, optional saved-model inference, and load tests. ML uses an explicitly triggered batch workflow; Lambda is not selected; EventBridge Scheduler is an optional side quest after the evidence runs.

Payments are simulated; no real payment-card data is collected. Analytics is required; descriptive customer-segmentation ML is included. ElastiCache is conditional on a justified, affordable implementation. CloudFront, NoSQL, real payment integration and marketplace expansion are outside the baseline.

## Analytics and data

The required analytics reports daily/category sales, top-selling products, previous-seven-complete-day average sales, estimated stock coverage and replenishment flags. Calculations use completed orders and historical line prices, with independently checked fixtures and documented limitations.

Selected historical source: the [Ecommerce Sales Dataset from Analytics Engineering](https://www.analyticsengineering.com/datasets/ecommerce-sales) (customers, products, orders and order items; CC BY 4.0). Switched 22 September 2026 from the original selection, LaelaZ/synthetic-ecommerce on Hugging Face, after its gated access was never granted. Downloaded, checksummed and committed under `data/raw/`; row counts confirmed exact against the publisher's data dictionary. Integrity profiling (`analytics/profile_dataset.py`, output in [data/PROFILE.md](data/PROFILE.md)) passed with zero rejected rows, the import (`import_dataset`) and the analytics refresh ran on the full data, and an independent pandas recomputation (`analytics/verify_refresh.py`) found zero mismatches; see [evidence/test-data-ai.md](evidence/test-data-ai.md). The application imports a derived shoe dataset built from the unchanged raw files by `analytics/build_shoe_dataset.py` (same customers, orders and lines, re-pointed to 200 shoe products); the import, refresh and pandas recomputation were rerun on it with zero mismatches. The patterns in this dataset are weak, so results are descriptive only. Only synthetic data is permitted by this project's chosen data policy; the publisher states this dataset is fully synthetic.

Generate missing stock snapshots, lead times and demo account/cart fixtures separately. Preserve source identities, document date alignment and prevent reimports from overwriting live state. See the [data pipeline contract](docs/DATA_PIPELINE.md), [data documentation](data/README.md) and [analytics contract](docs/ANALYTICS.md).

## Planned technology and architecture

| Area | Selection |
|---|---|
| Backend | Django |
| Frontend | Django templates, HTML/CSS, HTMX and minimal JavaScript |
| Database | PostgreSQL in Docker locally; Amazon RDS on AWS |
| Serving and packaging | Gunicorn, WhiteNoise, Docker and Docker Compose |
| Analytics | Django management commands/SQL; pandas where useful |
| Infrastructure | Terraform, EC2, ALB, Auto Scaling Group, private S3, CloudWatch, ECR, SNS, CloudTrail, WAF, Secrets Manager; ECS on Fargate is variant B, not yet built |
| Access and secrets | IAM roles and selected Secrets Manager; unavailable access blocks deployment |
| Verification | pytest/pytest-django, Locust and documented workflow/recovery tests |

```text
Browser -> HTTPS ALB -> Django containers in EC2 Auto Scaling Group -> private RDS
                            |
                            +-> packaged static assets via WhiteNoise

Private S3 -> validated dataset import -> RDS -> analytics summaries -> operator dashboard
CloudWatch <- sanitised application logs and infrastructure metrics
```

Application instances share database sessions and carts; no sticky sessions. Baseline autoscaling uses ALB request count per target. A final labelled architecture image, including trust boundaries, is planned at `evidence/architecture.png`; it is not yet supplied.

See [architecture](docs/ARCHITECTURE.md) and [AWS infrastructure](docs/AWS_INFRASTRUCTURE.md) for boundaries, deployment gates and trade-offs. RDS Single-AZ and one-instance normal operation are budget compromises; they do not provide uninterrupted availability. Failure demonstrations require two healthy application instances.

## Getting started

See [the Docker quickstart](src/README.md) for local configuration, startup, tests and the management commands (`seed_demo`, `import_dataset`, `refresh_analytics`, `snapshot_inventory`, `check_database`). A marker needs only Docker: the local run, tests and analytics need no AWS access. The AWS deployment is Terraform plus a few scripts in `src/infrastructure/`; **[src/infrastructure/README.md](src/infrastructure/README.md) has the exact commands** to bring variant A up and down, or to build everything in a new account (cloud steps need a Learner Lab account and cost money; marking does not need them).

With Docker Desktop running, use standard Compose commands from the repository root. On a fresh clone, first generate local secrets once (existing configuration is preserved):

```powershell
python src/tools/init_env.py
```

```powershell
docker compose up --build  # First run or after code changes
docker compose up          # Normal startup using the existing image
docker compose down        # Stop; preserve database data
```

Open http://127.0.0.1:8000/ (default port). Add `-d` to run in the background. A one-off local migration service completes before web starts. Use `--build` after pulling code/dependency/migration changes. See [the Docker quickstart](src/README.md) for tests, configuration and a Docker-only initializer alternative. No dev.py wrapper is required.

For development, begin with:

1. [AGENTS.md](AGENTS.md): task routing, targeted reading and model/review rules.
2. Relevant sections of [PROJECT_SCOPE_INF2006.md](PROJECT_SCOPE_INF2006.md): agreed requirements and boundaries.
3. [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md): current task, blockers and phase status.
4. Only the relevant feature contracts listed below.

The delivered application must run locally without paid AWS access for marking. Cloud deployment will require verified student-account permissions, available credits, region and an HTTPS certificate arrangement. Treat USD 40 per member as separate balances, not a pooled deployment budget. Develop locally and capture cloud evidence in bounded sessions before teardown.

## Continuous integration

[GitHub Actions CI](.github/workflows/ci.yml) runs on pull requests and pushes to `main`. It builds the pinned Docker image and checks migrations, Django configuration and the pytest suite against disposable PostgreSQL. No AWS credentials are required. See [testing guidance](docs/TESTING.md#continuous-integration) for coverage and limitations, and the repository's Actions tab for each run's result.

## Documentation index

| Document | Purpose |
|---|---|
| [**Project guide**](docs/GUIDE.md) | Start here if you are new: where the evidence is, how to check a claim, and what every shell and Python script does |
| [Project scope](PROJECT_SCOPE_INF2006.md) | Requirements, phase dates, risks, rubric coverage and team roles |
| [Implementation tracker](docs/IMPLEMENTATION_PLAN.md) | Current status, next tasks and blockers |
| [Design reference](DESIGN.md) / [frontend contract](docs/FRONTEND.md) | Visual direction, pages, interactions and accessibility |
| [Schema](docs/SCHEMA.md) / [API](docs/API.md) | Data constraints, checkout semantics and route contracts |
| [Data pipeline](docs/DATA_PIPELINE.md) / [analytics](docs/ANALYTICS.md) | Provenance, import behaviour, metrics and validation |
| [Architecture](docs/ARCHITECTURE.md) / [infrastructure](docs/AWS_INFRASTRUCTURE.md) / [AWS comparison plan](docs/plans/aws-ecs-comparison.md) | Component responsibilities, AWS contract and operations, and the EC2 versus Fargate plan with its decisions |
| [Security](docs/SECURITY.md) / [testing](docs/TESTING.md) | Controls, verification and evidence requirements |
| [Development](docs/DEVELOPMENT.md) | Coding workflow, Git conventions and independent review gate |
| [Planning review](docs/reviews/planning-suite-review.md) | Outstanding contract clarifications and resolution record |

Backend implementation uses Astra Low and an independent diff review by Astra Medium or a fresh-session Claude Opus 5.5 ([review gate](docs/DEVELOPMENT.md#backend-review-gate)). Low fixes logged findings; a repeated unresolved issue after its fix attempt stops the task for user-controlled escalation. Frontend work uses Luna Max. Detailed assignment and targeted-reading rules are in AGENTS.md.

## Testing and submission evidence

The automated suite under [tests/](tests/README.md) covers functional workflows, security controls, concurrent checkout and analytics correctness on real PostgreSQL; the latest recorded full-suite result is kept in [tests/README.md](tests/README.md). Local functional, security and data/AI evidence is recorded in [evidence/](evidence/README.md), with data verification also in [analytics](analytics/README.md). The cloud build is recorded in [aws-build-runbook.md](evidence/aws-build-runbook.md). Still planned: scaling, recovery/session continuity, monitoring and the deployed security checks; [test-resilience.md](evidence/test-resilience.md) and [monitoring.md](evidence/monitoring.md) are still templates.

Keep [project_manifest.yaml](project_manifest.yaml) aligned with delivered functionality and stable evidence paths. Submission requires an 8-12 page report, runnable source, data documentation, repeatable analytics, test evidence, [contributions](TEAM_CONTRIBUTIONS.md) and [AI/source declarations](AI_USE_DECLARATION.md). No credentials, personal data or secret-containing Terraform state belong in the repository or ZIP.

## Repository layout

```text
AGENTS.md                    Agent entry point
PROJECT_SCOPE_INF2006.md      Agreed scope and delivery phases
DESIGN.md                    Visual reference
README.md                    Human/marker entry point
project_manifest.yaml        Submission metadata and evidence index
docs/                        Contracts, tracker and review records
src/                         Django application; Terraform in src/infrastructure/
data/                        Raw dataset, profile, provenance and data dictionary
analytics/                   Shoe dataset builder, profiler, refresh verifier, ML segmentation and evaluation
tests/                       Automated pytest suite (real PostgreSQL)
evidence/                    Dated results (data/analytics done) and templates (the rest)
TEAM_CONTRIBUTIONS.md         Contribution record
AI_USE_DECLARATION.md         Tools, verification, licences and attribution
```

The final `report.pdf` and required implementation/evidence artefacts are delivery outputs, not all present yet.

## Current limitations and continuation

- AWS: `base/` (network, private RDS PostgreSQL 17, Route 53 zone, ACM certificate, ECR, S3 settings, secrets, alarm topic) and variant A (`ec2/`) are applied in the team's Learner Lab account (1 October 2026); variant B is not built. The lab denies creating IAM roles, so instances run as the lab's `LabRole`, and it denies one S3 API call that the standard bucket resource needs, so the bucket is created with the CLI and its settings stay in Terraform. Records: [how to run it](src/infrastructure/README.md), [plan](docs/plans/aws-ecs-comparison.md), [decisions](docs/decisions/), [build runbook](evidence/aws-build-runbook.md).
- Cloud evidence so far is the build and its acceptance checks in the build runbook (HTTPS at the stack's hostname, database jobs, least-privilege denials, dataset import, smoke test). Load, scaling, recovery and monitoring evidence is not yet recorded. Local functional and security evidence is recorded; resilience and monitoring evidence are not.
- The storefront redesign and dashboard re-theme have a recorded human browser walkthrough (FUNC-02) but no independent code review. See [storefront redesign](docs/archive/plans/storefront-redesign.md).
- The source dataset has little weekly pattern, and the shoe mapping, sizes and prices are synthetic choices; in the shoe run 9 of 200 products had no recent sales. Dashboard figures demonstrate the mechanism, not real demand. See [data/README.md](data/README.md).
- Synthetic data supports reproducible demonstrations, not validated claims about real customer demand.
- Scope coverage does not guarantee a grade; assessment depends on verifiable implementation and evidence.

After INF2006 submission, preserve the exact ZIP and tag the commit. INF2003 will extend that baseline with local Docker databases, substantial NoSQL functionality and database benchmarking, removing AWS dependencies and isolated ML. That expansion is outside the current development scope.
