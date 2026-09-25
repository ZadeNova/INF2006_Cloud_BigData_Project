# INF2006: E-Commerce Core with Sales and Inventory Analytics

A small ecommerce service for customers to browse products, manage a cart and place simulated orders, with an operator dashboard that explains sales trends and inventory replenishment needs. The project demonstrates secure AWS deployment, persistent cloud data, reproducible analytics, and measured scaling and recovery.

**Status (24 September 2026):** The application runs locally in Docker. Registration/login, catalogue, persistent cart, idempotent checkout, order history, the imported dataset, the analytics refresh and the operator dashboard are implemented and were independently reviewed as recorded in [docs/reviews/](docs/reviews/). The storefront was redesigned after that (VoiceBox look, dark mode) and the dashboard was re-themed to match; those changes have had no independent review or documented browser walkthrough yet. **Nothing is deployed to AWS**: there is no Terraform, no load test and no scaling, recovery or monitoring evidence, and most submission evidence files are still templates. See the [implementation tracker](docs/IMPLEMENTATION_PLAN.md) for current progress.

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

Implemented locally (not yet deployed):

- Registration, login/logout and shared database-backed sessions.
- Product catalogue and persistent shopping cart.
- Simulated checkout with server-side prices, transactional stock updates and duplicate-request protection.
- Owner-only order confirmation and history.
- Operator-only sales and inventory dashboard at `/analytics/` with reporting dates, freshness and interpretable replenishment flags.
- A narrow operator addition beyond the brief: activate or deactivate a product at `/products/manage/`.
- Included descriptive customer segmentation (RFM K-means): trained offline by `analytics/segment_customers.py`, loaded per analytics run by `load_customer_segments`, shown as a panel on the dashboard when a run has assignments. It is descriptive only on synthetic data, its evaluation metrics are not yet recorded in `evidence/`, and it has not been through the independent review gate.

Not implemented: AWS deployment, S3 import, the scheduler for the analytics refresh, optional saved-model inference, and load tests. ML uses an explicitly triggered batch workflow; EventBridge Scheduler and Lambda are not selected.

Payments are simulated; no real payment-card data is collected. Analytics is required; descriptive customer-segmentation ML is included. ElastiCache is conditional on a justified, affordable implementation. CloudFront, NoSQL, real payment integration and marketplace expansion are outside the baseline.

## Analytics and data

The required analytics reports daily/category sales, top-selling products, previous-seven-complete-day average sales, estimated stock coverage and replenishment flags. Calculations use completed orders and historical line prices, with independently checked fixtures and documented limitations.

Selected historical source: the [Ecommerce Sales Dataset from Analytics Engineering](https://www.analyticsengineering.com/datasets/ecommerce-sales) (customers, products, orders and order items; CC BY 4.0). Switched 22 September 2026 from the original selection, LaelaZ/synthetic-ecommerce on Hugging Face, after its gated access was never granted. Downloaded, checksummed and committed under `data/raw/`; row counts confirmed exact against the publisher's data dictionary. Integrity profiling (`analytics/profile_dataset.py`, output in [data/PROFILE.md](data/PROFILE.md)) passed with zero rejected rows, the import (`import_dataset`) and the analytics refresh ran on the full data, and an independent pandas recomputation (`analytics/verify_refresh.py`) found zero mismatches; see [evidence/test-data-ai.md](evidence/test-data-ai.md). The patterns in this dataset are weak, so results are descriptive only. Only synthetic data is permitted by this project's chosen data policy; the publisher states this dataset is fully synthetic.

Generate missing stock snapshots, lead times and demo account/cart fixtures separately. Preserve source identities, document date alignment and prevent reimports from overwriting live state. See the [data pipeline contract](docs/DATA_PIPELINE.md), [data documentation](data/README.md) and [analytics contract](docs/ANALYTICS.md).

## Planned technology and architecture

| Area | Selection |
|---|---|
| Backend | Django |
| Frontend | Django templates, HTML/CSS, HTMX and minimal JavaScript |
| Database | PostgreSQL in Docker locally; Amazon RDS on AWS |
| Serving and packaging | Gunicorn, WhiteNoise, Docker and Docker Compose |
| Analytics | Django management commands/SQL; pandas where useful |
| Infrastructure | Terraform, EC2, ALB, Auto Scaling Group, private S3, CloudWatch, ECR, SNS, CloudTrail, WAF, Secrets Manager (planned) |
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

See [the Docker quickstart](src/README.md) for local configuration, startup, tests and the management commands (`seed_demo`, `import_dataset`, `refresh_analytics`, `snapshot_inventory`, `check_database`). The local run is the only supported environment today; no AWS deployment exists yet.

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
| [Project scope](PROJECT_SCOPE_INF2006.md) | Requirements, phase dates, risks, rubric coverage and team roles |
| [Implementation tracker](docs/IMPLEMENTATION_PLAN.md) | Current status, next tasks and blockers |
| [Design reference](DESIGN.md) / [frontend contract](docs/FRONTEND.md) | Visual direction, pages, interactions and accessibility |
| [Schema](docs/SCHEMA.md) / [API](docs/API.md) | Data constraints, checkout semantics and route contracts |
| [Data pipeline](docs/DATA_PIPELINE.md) / [analytics](docs/ANALYTICS.md) | Provenance, import behaviour, metrics and validation |
| [Architecture](docs/ARCHITECTURE.md) / [infrastructure](docs/AWS_INFRASTRUCTURE.md) | Component responsibilities, AWS deployment and operations |
| [Security](docs/SECURITY.md) / [testing](docs/TESTING.md) | Controls, verification and evidence requirements |
| [Development](docs/DEVELOPMENT.md) | Coding workflow, Git conventions and independent review gate |
| [Planning review](docs/reviews/planning-suite-review.md) | Outstanding contract clarifications and resolution record |

Backend implementation uses Astra Low and independent Astra Medium diff review. Low fixes logged findings; a repeated unresolved issue after its fix attempt stops the task for user-controlled Medium escalation. Frontend work uses Luna Max. Detailed assignment and targeted-reading rules are in AGENTS.md.

## Testing and submission evidence

The automated suite under [tests/](tests/README.md) covers functional workflows, security controls, concurrent checkout and analytics correctness on real PostgreSQL (392 passed in a local Docker run on 25 September 2026 after the test trim on `f72a872`; re-run and record before citing). Data verification is in [analytics](analytics/README.md) and [evidence/test-data-ai.md](evidence/test-data-ai.md). Still planned: scaling, recovery/session continuity, private S3 access and monitoring. The other files in [evidence](evidence/README.md) are templates, not completed test evidence.

Keep [project_manifest.yaml](project_manifest.yaml) aligned with delivered functionality and stable evidence paths. Submission requires an 8-12 page report, runnable source, data documentation, repeatable analytics, test evidence, [contributions](TEAM_CONTRIBUTIONS.md) and [AI/source declarations](AI_USE_DECLARATION.md). No credentials, personal data or secret-containing Terraform state belong in the repository or ZIP.

## Repository layout

```text
AGENTS.md                    Agent entry point
PROJECT_SCOPE_INF2006.md      Agreed scope and delivery phases
DESIGN.md                    Visual reference
README.md                    Human/marker entry point
project_manifest.yaml        Submission metadata and evidence index
docs/                        Contracts, tracker and review records
src/                         Django application (infrastructure code not yet written)
data/                        Raw dataset, profile, provenance and data dictionary
analytics/                   Dataset profiler, independent refresh verifier and reproduction notes
tests/                       Automated pytest suite (real PostgreSQL)
evidence/                    Dated results (data/analytics done) and templates (the rest)
TEAM_CONTRIBUTIONS.md         Contribution record
AI_USE_DECLARATION.md         Tools, verification, licences and attribution
```

The final `report.pdf` and required implementation/evidence artefacts are delivery outputs, not all present yet.

## Current limitations and continuation

- AWS: a teammate-reported read-only probe (25 September 2026) reached the probed lab APIs, but creating resources, exact costs and HTTPS (a domain is being purchased) remain unverified. The infrastructure will be provisioned with Terraform ([plan](docs/plans/aws-terraform.md)); nothing is deployed.
- Cloud evidence (deployment, scaling, recovery, monitoring, storage) is not started. Functional and security evidence files record no run yet, although the automated tests exist; a recorded live walkthrough of the redesigned storefront is also outstanding.
- The redesign and the dashboard re-theme (24 September 2026) are not independently reviewed and have no recorded browser walkthrough yet. See [storefront redesign](docs/plans/storefront-redesign.md).
- The imported dataset has weak weekly variation and 32–40% of products without recent sales, so dashboard figures demonstrate the mechanism, not real demand. See [data/README.md](data/README.md).
- Synthetic data supports reproducible demonstrations, not validated claims about real customer demand.
- Scope coverage does not guarantee a grade; assessment depends on verifiable implementation and evidence.

After INF2006 submission, preserve the exact ZIP and tag the commit. INF2003 will extend that baseline with local Docker databases, substantial NoSQL functionality and database benchmarking, removing AWS dependencies and isolated ML. That expansion is outside the current development scope.
