# Team Contributions

Group 21. One row per member: role, artefacts/commits, test/evidence ownership, reflection. Roles
match [project_manifest.yaml](project_manifest.yaml). Commit history is the record of who changed
which files; this table lists owned artefacts rather than commit counts.

## How the work was split

The scope (section 11, agreed 11 September 2026) planned two developers and three members for testing, report and
administration, and the work followed that plan. Commit counts are not a measure of effort here: a large share of the
developers' commits are documentation and raw evidence, and testing, review, report and administration work leaves few
commits. This record therefore lists each member's artefacts and representative commits rather than counts; every commit
can be opened in the repository history.

## Shared work (all five members)

- **Report:** drafted with AI assistance (Claude Code and Codex agents; see [AI_USE_DECLARATION.md](AI_USE_DECLARATION.md)) and edited by the team.
- **Application testing:** Phua Kia Wen Hermann ran the local browser walkthrough (FUNC-02) and the testing members reviewed
  the test records in [evidence/](evidence/README.md); the developers operated the AWS sessions and the load runs.
- **Submission review:** all members have read the report; the two developers checked its numbers and paths against the evidence and the
  manifest; the primary developer gives the final approval.

## Contribution matrix

| Name | Role | Artefacts and commits (representative commits are listed under the table) | Test/evidence ownership | Reflection |
|---|---|---|---|---|
| Muhammad Erfan Bin Mohan (2500722) | Cloud lead, backend, load testing | AWS infrastructure in Terraform ([src/infrastructure/](src/infrastructure/)): network, RDS, secrets, ALB, WAF, alarms, variant A (EC2) and variant B (ECS Fargate); load harness ([tests/load/](tests/load/)); authentication, order history, checkout fixes and reporting date ranges; architecture decision records ([docs/decisions/](docs/decisions/)); project manifest | AWS deployment, load, scaling, resilience and monitoring evidence ([evidence/aws-build-runbook.md](evidence/aws-build-runbook.md), [evidence/test-performance.md](evidence/test-performance.md), [evidence/test-resilience.md](evidence/test-resilience.md), [evidence/monitoring.md](evidence/monitoring.md), [evidence/load-summary.md](evidence/load-summary.md)); AWS security reruns in [evidence/test-security.md](evidence/test-security.md) | I led the AWS side: the Terraform for both compute variants, the Locust load harness and the 8 October evidence session. The saturation run taught me to read the bottleneck from the metrics instead of guessing: instance CPU reached 94.6% while RDS stayed under 11%, so scaling the web tier was the right lever and a cache would have been wasted effort. I also learned to design around the Learner Lab limits, such as no custom IAM roles, rather than fight them. Next time I would deploy and measure the first variant end to end in week two, leaving more time for repeat runs and closing the remaining resilience gaps after both variants were tested. |
| Lim Chee Long (2500584) | Assistant cloud, backend | Local Docker and PostgreSQL foundation; dataset import with sealed inventory; operator analytics dashboard; ML segment import and RFM evaluation; production secrets loading at startup, database TLS and bootstrap role separation ([src/config/](src/config/), [src/reporting/](src/reporting/)) | Foundation, ML handoff, runtime security and local release review records ([docs/reviews/](docs/reviews/)), including [ml-local-release-readiness](docs/reviews/ml-local-release-readiness.md) and [runtime-aws-security](docs/reviews/runtime-aws-security.md) | I built the local Docker and PostgreSQL foundation, the dataset import with sealed inventory, the operator dashboard, and the secrets, database TLS and role-separation work. The most useful design lesson was keeping live stock and sealed snapshots apart, so a coverage figure never divides today's stock by last year's sales. Reviewing AI-written code against written contracts caught problems that passing tests alone would not have shown. Next time I would write the contract for each module before generating its code, and add a scheduled analytics refresh, which we left as a manual step. |
| Mohammed Syahfariz Bin Effendy (2500717) | Application testing, UI/UX, report | ML hold-out evaluation and feature fixes ([analytics/evaluate_holdout.py](analytics/evaluate_holdout.py), [analytics/segment_customers.py](analytics/segment_customers.py)); manage-products filters, product detail page and stay-on-page cart; chose which ML review findings to act on and set the adoption criteria | Data/AI evidence DATA-01 and DATA-02 ([evidence/test-data-ai.md](evidence/test-data-ai.md), [evidence/ml-holdout-evaluation.json](evidence/ml-holdout-evaluation.json)); application and UI testing | I worked on the ML hold-out evaluation, the manage-products, product detail and cart features, and the application and UI testing, and I chose which review findings to act on and set the adoption criteria. The main lesson was that the segments describe past customers faithfully but do not predict repurchase on this synthetic data, and that reporting this was better than tuning until a difference appeared. Deciding which AI review findings to fix, and which to keep as stated limitations, showed me that accepting every suggestion is not the same as good engineering. Next time I would run the hold-out test as soon as the first segments exist, so we learn early whether a feature earns its place. |
| Jun Keat Lim (2501004) | Report, UI/UX | Storefront UI/UX redesign with dark mode and motion; 3D shoe models on product pages ([src/static/models/](src/static/models/), credits in [CREDITS.md](src/static/models/CREDITS.md)); 42Factors branding; shoe catalogue with sizes; analytics pagination ([src/templates/](src/templates/), [src/static/](src/static/)) | Frontend tests ([tests/test_frontend.py](tests/test_frontend.py)); visual and UI checks of the storefront | I redesigned the storefront with dark mode and motion, added the 3D shoe models and the 42Factors branding, and built the shoe catalogue with sizes. I learned that every third-party asset needs its source and licence recorded at the moment it is added: the models are mostly CC BY with two non-commercial. Recovering the missing Dior model attribution before submission showed why the register must be complete. I also saw that front-end polish still needs tests, which is why the frontend test file exists. Next time I would keep an asset register from the first model I add and check page weight earlier. |
| Phua Kia Wen Hermann (2501300) | Application testing, report | Review of the local functional and security test records (run by AI agents), FUNC-02 browser walkthrough of the storefront and dashboard, the reproduction test of the submission package, and the stay-on-page Add to cart request. | Local functional and security evidence ([evidence/test-functional.md](evidence/test-functional.md), [evidence/test-security.md](evidence/test-security.md), raw output in [evidence/raw/](evidence/raw/)) | I reviewed the local functional and security test records, ran the FUNC-02 browser walkthrough of the storefront and dashboard, and asked for the stay-on-page Add to cart behaviour. I learned to write the expected result before running a test and to keep the raw output, so that someone who did not run it can check it, and that even the Gemini-assisted dashboard description had to be cross-checked against the database before we recorded it as matching. I also ran the reproduction test, unzipping the package on a clean machine and following the README. It showed that a fresh clone could build, start, import the dataset, refresh analytics and pass the application and analytics tests when the documented Python 3.13 container path was used. If we repeated the project I would rerun the local test records against each new build earlier and automate more of the walkthrough. |

## Representative commits

A selection that shows each member's areas; the three members with the fewest commits are listed in full (the merge
commits on the UIUX branch are omitted).

| Member | Commit | Date | Subject |
|---|---|---|---|
| Muhammad Erfan Bin Mohan (2500722) | `f545806` | 2026-09-28 | feat(infra): stage 0 Terraform scaffold and single apply-device state |
| Muhammad Erfan Bin Mohan (2500722) | `8f2e89b` | 2026-09-29 | feat(infra): stage 1 - network, security groups, storage, secrets, monitoring |
| Muhammad Erfan Bin Mohan (2500722) | `67a1a56` | 2026-10-09 | feat(infra): variant B sets up its own database |
| Muhammad Erfan Bin Mohan (2500722) | `b755745` | 2026-09-20 | fix: bind checkout to the reviewed cart (CHK-001, CHK-002) |
| Muhammad Erfan Bin Mohan (2500722) | `41ea463` | 2026-09-20 | feat: add completed-sale-lines view and reporting date ranges |
| Muhammad Erfan Bin Mohan (2500722) | `f401935` | 2026-10-09 | feat(load): reset_state.py restores shop data between variants and before the demo |
| Muhammad Erfan Bin Mohan (2500722) | `6747b7f` | 2026-10-09 | docs(evidence): RES-03 scale-out r1 and replacement r1 on variant A (EC2) |
| Muhammad Erfan Bin Mohan (2500722) | `8289681` | 2026-10-09 | docs(decisions): ADR-018 final architecture and ADR-019 variant B database setup |
| Lim Chee Long (2500584) | `8cb2691` | 2026-09-12 | ci: verify Docker foundation on pull requests and main pushes |
| Lim Chee Long (2500584) | `4704cc8` | 2026-09-22 | feat: add validated dataset import and sealed inventory |
| Lim Chee Long (2500584) | `df29b82` | 2026-09-22 | feat: verify analytics refresh independently with pandas |
| Lim Chee Long (2500584) | `6ecc0e7` | 2026-09-23 | feat: add reviewed operator analytics dashboard |
| Lim Chee Long (2500584) | `db6cfca` | 2026-09-25 | fix: enforce database TLS and bootstrap role separation |
| Lim Chee Long (2500584) | `8ee4bf2` | 2026-09-25 | feat: load production secrets at startup and bound ALB probes |
| Mohammed Syahfariz Bin Effendy (2500717) | `c50583b` | 2026-09-24 | Implement optional ML customer segmentation workflow |
| Mohammed Syahfariz Bin Effendy (2500717) | `b481f1f` | 2026-09-26 | feat(ml): add hold-out evaluation, fix RFM features and rerun data evidence |
| Mohammed Syahfariz Bin Effendy (2500717) | `3d8719c` | 2026-09-26 | feat(catalogue): add manage filters, product detail page and stay-on-page cart |
| Mohammed Syahfariz Bin Effendy (2500717) | `6a429aa` | 2026-10-09 | docs: complete the team contributions matrix and AI use declaration |
| Jun Keat Lim (2501004) | `d07b235` | 2026-09-23 | redesigned UIUX for storefront and added darkmode |
| Jun Keat Lim (2501004) | `d147c9d` | 2026-09-23 | feat: restyled the storefront to VoiceBox (black/white/red), added matching motion, and added a presentation-only statistics preview |
| Jun Keat Lim (2501004) | `2ad7b82` | 2026-09-24 | feat: added 3d models for products page |
| Jun Keat Lim (2501004) | `d773dac` | 2026-09-25 | fix: added more models and changed to single shoe |
| Jun Keat Lim (2501004) | `0291b29` | 2026-09-26 | feat: shoe catalogue with 10 sizes per shoe from a derived dataset |
| Jun Keat Lim (2501004) | `1c98842` | 2026-09-26 | feat: paginate analytics lists and align analytics and size picker with DESIGN.md |
| Jun Keat Lim (2501004) | `02afbb1` | 2026-09-26 | feat: rename the site to 42Factors with a pixel "67" mark and a larger header |
| Phua Kia Wen Hermann (2501300) | `2698b05` | 2026-09-26 | docs(evidence): record functional and security evidence |

AI assistance used by the team is declared in [AI_USE_DECLARATION.md](AI_USE_DECLARATION.md).
