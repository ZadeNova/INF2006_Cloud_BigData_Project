# Testing and evidence contract

Status: the pytest suite exists and runs in CI (layout and the latest recorded full-suite result in [tests/README.md](../tests/README.md)); Locust load tests do not exist yet; evidence templates are not results. Use pytest/pytest-django and Locust. Run checks relevant to changes; broaden when dependencies, failures or risks justify it.

| Area | Required behaviour/evidence |
|---|---|
| Functional | Registration/login, catalogue, cart, checkout and owner history persist correctly |
| Checkout | Independent PostgreSQL transactions do not oversell; retries create one order; no partial writes |
| Security | Ownership, operator, CSRF, server pricing and session controls reject invalid actions |
| Data/analytics | Integrity/repeated imports, independent fixtures, date boundaries and repeat refresh agree |
| Scaling | Fixed-capacity vs ASG comparison: latency, throughput, errors, health/capacity and delay |
| Recovery | Two healthy instances, cross-instance sessions/cart, terminate one, same-key checkout retry; record transient errors |
| Storage | Pinned private S3 input reconciles checksums/counts; anonymous denial |
| Operations | Controlled failure produces identifiable metrics/logs and an interpreted query/alert |
| Optional cache | Fixed app capacity: disabled, warmed and unavailable; include fallback DB pressure |

Separate correctness and load fixtures. Locking tests use real independent PostgreSQL transactions/connections; SQLite or mocks cannot prove concurrency. Fix clock/cutoff and seeds for analytics. Load tests use valid sessions/CSRF, sufficient stock and unique purchase IDs; distinguish sold-out responses from unexpected errors.

Run/monitor load generators outside app instances. Keep workloads comparable and separate cache, scaling and failure phases. Establish supported load and numerical objectives before final comparison. The scope's p95 checkout below two seconds and unexpected errors below 1% are proposed objectives, not achieved results.

Verify frontend workflows through actual Django HTTP routes, including error/keyboard states. Screenshots alone do not demonstrate behaviour.

## Signature evidence demos

**Planned 25 September 2026; subject to change** as the cloud build, lab permissions, budget and time settle. None has been run. They turn behaviour the local suite already proves into cloud evidence an ecommerce service is uniquely placed to show, and each feeds the brief's required test records (functional, security, data/AI, resilience) and the monitoring record. Write the Locust scenarios before the first cloud session so every run uses the same workload. Record each run in the evidence format below; a failed run is still recorded with its diagnosis and next step.

| # | Demo | Setup | Steps | Expected result | Record | Builds on |
|---|---|---|---|---|---|---|
| 1 | **Last-pairs stampede** | 2 healthy instances behind the ALB; one product with stock 5; 50 distinct logged-in synthetic customers, each with that product in their cart | Locust fires all 50 checkouts at once, each with its own idempotency key | Exactly 5 completed orders, stock 0 and never negative, the other 45 get the sold-out response rather than errors; requests served by both instances | `evidence/test-resilience.md` (correctness under load) and `evidence/test-functional.md` | `test_concurrent_checkouts_different_users_racing_last_unit_of_stock` |
| 2 | **Instance lost mid-checkout** | 2 healthy instances; a customer with a cart open on the review page | Submit checkout, terminate the instance that served it during or immediately after the request, resubmit the same review (same idempotency key) | Exactly one order; session and cart still valid on the surviving instance; ASG launches a replacement. Record transient errors and the time to two healthy targets again | `evidence/test-resilience.md` | Database-backed sessions; `test_concurrent_checkouts_same_idempotency_key_create_exactly_one_order` |
| 3 | **Database outage handled** | Stack running, alarm on ALB 5xx (and/or target health) wired to SNS email | Reboot the RDS instance while a light Locust load runs | Users get the 503 page, not a traceback; `/health/` stays 200 so instances are not replaced; the alarm fires and the email arrives; service recovers without intervention. Record the timeline: reboot, first 503, alarm, recovery | `evidence/monitoring.md` and `evidence/test-resilience.md` | `DatabaseUnavailableMiddleware`, `503.html`, `test_db_unavailable.py` |
| 4 | **Attack table against the deployed service** | HTTPS deployment, two customer accounts, WAF rate rule on the ALB | Run each attack over HTTPS: another customer's order URL; checkout with forged price/owner fields; a state-changing POST without a CSRF token; a burst of `/login/` requests above the rate limit; an anonymous request for an object in each private S3 bucket | 404; forged fields ignored and the server price used; 403; WAF blocks the burst (WAF log/metric shows it); S3 `AccessDenied` | `evidence/test-security.md`, rows in `evidence/threat-control-map.md` | `test_order_detail_returns_404_for_foreign_order_200_for_owner`, `test_checkout_ignores_forged_price_owner_total_and_status_fields`, `test_a_mutation_without_a_valid_csrf_token_is_rejected_and_changes_nothing`. The login rate limit is new (WAF; the app has no throttling) |
| 5 | **Analytics you can trust** | Dataset imported into RDS from the private S3 bucket | Checksums and row counts reconcile against `data/`; `refresh_analytics` in the cloud matches independent pandas recomputation; descriptive ML reports candidate separation, sizes/profiles and seed stability on the accepted revision | Zero reconciliation or recomputation mismatches; cluster quality and limitations reported without predictive claims (M-02 temporal prediction is not required for this descriptive scope) | `evidence/test-data-ai.md` | `analytics/verify_refresh.py`, `analytics/evaluate_segments.py`, the Phase 3 evidence already in that file |

Also record for each cloud run: date, commit, instance count and type, and the cost of the session from the lab balance, so the report's cost section uses measured figures. Redact account IDs, public IPs and pre-signed URLs from every artefact.

## Continuous integration

[CI](../.github/workflows/ci.yml) builds the application (including packaged static files), waits for healthy PostgreSQL, applies migrations, runs Django system checks, checks for missing migrations with `makemigrations --check --dry-run`, and runs the existing pytest suite at `/app/tests`. Each command must succeed. The job uses the Compose non-superuser application role and an isolated, disposable database; it requires no repository secrets or AWS credentials. Cleanup removes only the CI project's containers and volume.

CI runs on pull requests and pushes to main. Inspect the GitHub Actions run for the tested commit and actual result; a local pass does not prove the hosted runner passed. This job does not deploy or verify AWS, browser workflows, load, or recovery, and branch protection must be configured separately if a passing check is to be required before merge.

The dedicated analytics job runs pure ML tests in a pinned Python container with only analytics dependencies and pinned pytest. It separately runs, in its own PostgreSQL Compose project with application settings and `/app/tests` imports, the SQL/verifier/strict-loader tests and the derived shoe dataset build tests (which need no database). All modules must collect and pass; no missing-Django skip is used. Analytics packages install into an ephemeral virtual environment, leaving the production image unchanged. Exact local equivalents are in [analytics/README.md](../analytics/README.md#ml-quality-evaluation).

## Evidence and final gate

Every record includes objective, setup/versions, exact commands/steps, inputs/seed, expected/actual result, date, raw artefact links and interpretation. Report failed/unrun checks honestly. Never fabricate metrics.

Preserve required project_manifest.yaml keys/relative paths. Required categories map to evidence/test-functional.md, test-security.md, test-data-ai.md and test-resilience.md; monitoring has a separate entry. Link additional results from these records.

A different teammate reproduces local application and analytics without paid AWS access. Validate manifest paths, required ZIP contents, report headings/page limits, contributions and attribution. Preserve dated cloud proof before teardown. CI runs the suite but is not a required merge gate unless branch protection is configured.

## Team ownership

The three testing/report/admin members share repeatable test execution, result checking, defect reporting and retesting; a testing/evidence lead coordinates coverage. The two developers implement automated checks and load scripts, provide reproducible setup, support controlled cloud/concurrency experiments and fix defects. Testers record actual commands, inputs, expected/actual outcomes and evidence; they do not need to claim implementation ownership. Coordinate cloud load/failure tests with developers against the intended test environment and budget.

## Independent backend review

Backend-owned changes must pass the [development review gate](DEVELOPMENT.md#backend-review-gate): an independent diff review by Astra Medium or Claude Opus 5.5 (fresh session by default; a same-session review only as a logged exception, per the reviewer tiers there), logged findings, Astra Low fixes and re-review by the same reviewer tier. Repeated unresolved findings after Low remediation stop the task for the user's manual Medium escalation. Tests and review are complementary; neither replaces the other. Record actual checks and attach regression coverage where meaningful for each fix. The coordinator keeps detailed review rounds under `docs/reviews/<task-id>.md` and links them from the tracker. Review logs are engineering records, not substitutes for the brief's required dated test evidence.
