# Testing and evidence contract

Status: planned suite; evidence templates are not results. Use pytest/pytest-django and Locust after establishing dependencies/commands. Run checks relevant to changes; broaden when dependencies, failures or risks justify it.

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

## Evidence and final gate

Every record includes objective, setup/versions, exact commands/steps, inputs/seed, expected/actual result, date, raw artefact links and interpretation. Report failed/unrun checks honestly. Never fabricate metrics.

Preserve required project_manifest.yaml keys/relative paths. Required categories map to evidence/test-functional.md, test-security.md, test-data-ai.md and test-resilience.md; monitoring has a separate entry. Link additional results from these records.

A different teammate reproduces local application and analytics without paid AWS access. Validate manifest paths, required ZIP contents, report headings/page limits, contributions and attribution. Preserve dated cloud proof before teardown. Do not claim a CI gate exists until implemented.

## Team ownership

The three testing/report/admin members share repeatable test execution, result checking, defect reporting and retesting; a testing/evidence lead coordinates coverage. The two developers implement automated checks and load scripts, provide reproducible setup, support controlled cloud/concurrency experiments and fix defects. Testers record actual commands, inputs, expected/actual outcomes and evidence; they do not need to claim implementation ownership. Coordinate cloud load/failure tests with developers against the intended test environment and budget.

## Independent backend review

Backend-owned changes must pass the [development review gate](DEVELOPMENT.md#backend-review-gate): independent Astra Medium diff review, logged findings, Astra Low fixes and Medium re-review. Repeated unresolved findings after Low remediation stop the task for the user's manual Medium escalation. Tests and review are complementary; neither replaces the other. Record actual checks and attach regression coverage where meaningful for each fix. The coordinator keeps detailed review rounds under `docs/reviews/<task-id>.md` and links them from the tracker. Review logs are engineering records, not substitutes for the brief's required dated test evidence.
