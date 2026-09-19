# Project evidence plan

Status: **plan only, to be handled later.** Nothing in this file is evidence. It records what evidence the submission needs, where each item comes from, what can be produced now versus later, and who leads it. Rules: [testing](../TESTING.md), [scope §12–13](../../PROJECT_SCOPE_INF2006.md), and the [evidence README](../../evidence/README.md). Placeholder or planned results must never be presented as run results; every claim in the report links to a dated artefact.

Role-based ownership (no names): the three testing/report/administration members lead test execution, evidence organisation and the report; the two developers set up tests, fix defects and provide technical context. The testing/evidence lead coordinates coverage. Record actual contributions honestly in `TEAM_CONTRIBUTIONS.md`.

## Rubric to evidence map

| Criterion (marks) | Evidence artefacts | Producible now? |
|---|---|---|
| Problem framing and architecture (15) | Problem statement and measurable objectives, architecture diagram with trust boundaries, two alternatives with trade-offs | Diagram draft and objectives: yes. Deployed parts: labelled as target until built |
| Cloud implementation and functionality (20) | Runnable ecommerce workflow, Terraform/config, deployment record, functional results | Local workflow: yes. Cloud deployment: later |
| Cloud data and analytics/AI (20) | Dataset provenance, licence and dictionary, import reconciliation, aggregation, dashboard, independent validation, limitations | After dataset access and batches 6a to 6c |
| Security and responsible cloud practice (15) | Threat-control map, redacted configuration, authentication and authorisation tests, secrets and data handling | Map and application tests: partly now. Cloud controls: later |
| Scalability, resilience and operations (15) | Scaling and recovery runs, metrics, repeated workload comparison, monitoring interpretation, cost record | Later (needs AWS) |
| Engineering quality and reproducibility (10) | Structure, pinned dependencies, local run, test scripts, valid manifest paths, clean-machine rehearsal | Mostly now, rehearsal last |
| Team contribution and communication (5) | Contribution matrix, ownership, attribution, concise report | Ongoing |

## Required artefacts

Each test file records: objective, setup, command or steps, expected result, actual result, date, artefact path. Prefer text or config exports to screenshots. Redact account IDs, public IPs and tokens. No credentials, production data or personal data.

| File | Content | Status today | Earliest real run |
|---|---|---|---|
| `evidence/architecture.png` | Users, components, cloud services, trust boundaries, data stores, observability, data flows | TODO | Draft now; final after deployment |
| `evidence/threat-control-map.md` | Threats mapped to controls, where implemented, and proof | TODO (template) | Rows for implemented controls now |
| `evidence/test-functional.md` | End-to-end workflow: register, log in, browse, cart, checkout, order history, operator page | Template plus foundation-only notes | Local now; cloud after deployment |
| `evidence/test-security.md` | Negative tests with expected and actual results | Template plus foundation-only notes | Application tests now; cloud controls later |
| `evidence/test-data-ai.md` | Analytics fixtures, independent recomputation, results and limits | Template | After 6b |
| `evidence/data-validation.md` | Source counts, integrity checks, transformations, import reconciliation | Not created | After 6a |
| `evidence/test-resilience.md` | Scaling baseline and autoscaling, instance failure, session continuity, safe checkout retry | Template | Cloud phase |
| `evidence/monitoring.md` | What is monitored, query or dashboard export, sanitised logs, interpretation | Template | Cloud phase |
| `evidence/storage.md` | S3 object provenance, access-control tests, import reconciliation | Not created | Cloud phase |
| `evidence/session-continuity.md` | Cross-instance authentication and cart, failure tests | Not created | Cloud phase |
| `evidence/costs.md` | Actual cost record with raw results and redacted configuration | Not created | Cloud phase |

The manifest lists the first five test/evidence files and `threat-control-map.md`; `data-validation.md`, `storage.md`, `session-continuity.md` and `costs.md` are planned additions in scope §13, so the manifest must be extended (without removing or renaming required fields) if they are kept.

## C1: threat-control map (seed list, to be verified before use)

Threats already addressed by code, with where to look. Each row needs a real test reference and a run date before it goes into the map; "where" is a pointer, not proof.

| Threat | Control | Where |
|---|---|---|
| Password compromise, weak passwords | Framework hashing, four password validators | `src/config/settings.py` (`AUTH_PASSWORD_VALIDATORS`) |
| Session theft or fixation | Database sessions, HttpOnly, SameSite=Lax, Secure and HSTS when not local | `settings.py` session and `SECURE_*` settings |
| CSRF on browser and HTMX mutations | `CsrfViewMiddleware`, POST-only mutation routes | `settings.py`, views, `tests/test_cart.py`, `tests/test_orders.py` |
| Foreign cart or order access | Owner-scoped lookups (404 for foreign objects) | `src/cart/views.py`, `src/orders/views.py`, tests per app |
| Customer using operator functions | Permission-gated views (403) | `src/catalogue/views.py`, `tests/test_catalogue.py` |
| Price or total tampering | Owner, prices and totals derived server-side; no client-supplied price | `src/orders/services.py` |
| Duplicate or concurrent checkout, overselling | Idempotency key and fingerprint, row locks, DB constraints | `src/orders/services.py`, concurrent tests in `tests/test_orders.py` |
| Imported accounts used to log in | Unusable passwords, explicit profile mapping | Import command (6a, not yet built) |
| Non-operator reads analytics | Permission on the analytics view | 6c (not yet built) |
| Host header abuse, open redirect | Allowed hosts, safe `next` handling | `settings.py`, `tests/test_accounts.py` |
| Cloud controls (private RDS and S3, security groups, IAM, secrets) | To be designed and evidenced | Cloud phase |

Known unimplemented control from the security contract: sanitised request logging (see [cloud-independent-prep](cloud-independent-prep.md) B2).

## C2 and C3: diagrams

- **ER diagram** from the actual models (accounts, catalogue, cart, orders, reporting). One diagram serves both modules (INF2003 baseline rule 8): it needs one-to-many, many-to-one and many-to-many relationships, so check whether the current models show many-to-many before INF2003 relies on it.
- **Architecture diagram** (`evidence/architecture.png`): show trust boundaries, data stores and data flows including the analytics refresh path. Mark anything not yet deployed as planned. Provide alternatives considered (for example a managed container service versus ASG on EC2) for the "two alternatives" criterion.

## C4: test results to record now

The application currently has 135 automated tests (checked at commit `a11247b`) plus the foundation results in `docs/reviews/`. When the testing members run them, record the command, date, environment and full outcome in `test-functional.md` and `test-security.md`, citing the specific tests behind each claim. A count of passing tests is not a security or functional claim on its own; tie each test to the behaviour it proves.

## C5: manifest and declarations

`project_manifest.yaml` still holds placeholders: group ID, title, problem statement, provider, members, service and deployment model, components, `data_ai` method, evaluation and reproducible command, and secrets handling. Fill each only when its content exists. `AI_USE_DECLARATION.md` and `TEAM_CONTRIBUTIONS.md` must record what was actually done and verified, by role and by person as applicable.

## Report and packaging

Eight headings (scope §13): problem and users, solution and architecture, cloud choices and trade-offs, implementation and security, analytics with evaluation and limits, testing and scaling results, cost and operations, contribution and reflection. 8 to 12 pages excluding references and appendices. Packaging checks (later): ZIP structure `Group_Gxxx_INF2006_Project.zip`, manifest paths resolve, no secrets or personal data, clean-machine rehearsal by a teammate from the README, exact commit tagged for INF2003.

## Order of work

1. Now to Phase 2: architecture and ER diagram drafts, threat-control seed rows tied to real tests, functional and security results for what is implemented.
2. After 6a and 6b: `data-validation.md` and `test-data-ai.md` from actual command output.
3. Cloud phase: resilience, monitoring, storage, session continuity, costs; then finalise the diagram.
4. Final week: report, manifest, declarations, clean-machine rehearsal, package check.
