# Security control test

- **Objective:** TODO (validate against a named threat)
- **Setup:** TODO
- **Command/steps:** TODO
- **Expected result:** TODO
- **Actual result:** TODO
- **Date:** TODO
- **Artefact path:** TODO

Foundation-only evidence (12 September 2026): [environment and DB role tests](../docs/reviews/foundation-batch-2.md), [health/Host/readiness tests](../docs/reviews/foundation-batch-4.md). Automated negative tests for authentication, ownership, CSRF, operator access, forged fields and quantity manipulation exist (`tests/test_security_negative.py` and per-app modules) but no run is recorded in this file yet; cloud security demonstrations have not been run.


## Phase 6 local regression check — 25–26 September 2026

The rebuilt final-image application suite passed 472 tests, including existing authentication, ownership, CSRF, operator access and runtime-boundary cases. Eight opt-in bootstrap cases skipped in that run all passed on a separate disposable PostgreSQL server (bootstrap module: 9 passes including one overlapping redaction case). See [release setup, source/image identity and commands](../docs/reviews/ml-local-release-readiness.md). Existing negative tests were reused; no duplicated security matrix was added. This does not verify AWS IAM, Secrets Manager/KMS permissions, ALB/TLS/network boundaries, WAF, CloudTrail or private S3 access.
