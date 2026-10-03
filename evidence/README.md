# evidence/

Named, dated evidence artefacts cited by `project_manifest.yaml` and `report.pdf`. FUNC-01 and FUNC-02 have now been run on the `hermann-evidence` branch at the `origin/erfan/merge-quarantine` source. The AWS build started on 28 September 2026: its stage records are in [aws-build-runbook.md](aws-build-runbook.md). The deployed AWS test cases and the remaining local cases are still pending.

Last covered commit: `ee334cf`

## Index

| Case | Title | File | Environment | Status | Date |
|---|---|---|---|---|---|
| FUNC-01 | Automated workflow suite: accounts, catalogue, cart, checkout and order history | [test-functional.md](test-functional.md) | Local Docker | PASS | 2026-09-26 |
| FUNC-02 | Manual browser walkthrough: register, browse, cart, checkout, order history, operator toggle and dashboard | [test-functional.md](test-functional.md) | Local Docker | PASS | 2026-09-26 |
| SEC-01 | T1 broken access control / IDOR on orders and cart items | [test-security.md](test-security.md) | Local Docker | PASS | 2026-09-26 |
| SEC-02 | T2 privilege escalation to operator functions | [test-security.md](test-security.md) | Local Docker | PASS | 2026-09-26 |
| SEC-03 | T3 cross-site request forgery (CSRF) | [test-security.md](test-security.md) | Local Docker | PASS | 2026-09-26 |
| SEC-04 | T4 price, owner and quantity tampering | [test-security.md](test-security.md) | Local Docker | PASS | 2026-09-26 |
| SEC-05 | T5 duplicate checkout and overselling under concurrency | [test-security.md](test-security.md) | Local Docker | PASS | 2026-09-26 |
| SEC-06 | T6 stored cross-site scripting (XSS) | [test-security.md](test-security.md) | Local Docker | PASS | 2026-09-26 |
| SEC-07 | T7 weak passwords; partial control because there is no throttling or MFA | [test-security.md](test-security.md) | Local Docker | PASS | 2026-09-26 |
| SEC-08 | T8 secrets and personal data kept out of logs | [test-security.md](test-security.md) | Local Docker | PASS | 2026-09-26 |
| SEC-12 to SEC-16 | T7, T8, T10, T11, T12, T17 local controls: production settings, secret loading, health and Host handling, request logging, unusable imported passwords | [test-security.md](test-security.md) | Local Docker | PASS | 2026-10-01 |
| SEC-ALL rerun | The 25 SEC-01 to SEC-08 test IDs rerun on the current commit | [test-security.md](test-security.md) | Local Docker | PASS | 2026-10-01 |
| SCAN-01 to SCAN-07 | gitleaks, bandit, pip-audit, `check --deploy`, hadolint, Trivy image and IaC scans with triage | [security-scan-triage.md](security-scan-triage.md) | Local Docker (not CI) | Run; findings triaged, 4 open | 2026-10-01 |
| SEC-09 | Cloud: RDS and S3 are not publicly reachable | [test-security.md](test-security.md) | AWS | NOT RUN YET as a test case (the runbook records an anonymous S3 request returning 403 on 2026-09-29; RDS was built in `base/` on 2026-10-01 but its reachability has not been tested as a case) | — |
| SEC-10 | Cloud: HTTPS is enforced | [test-security.md](test-security.md) | AWS | NOT RUN YET as a test case (the runbook records HTTPS 200, HTTP 301 to HTTPS, a verifying certificate and HSTS from `smoke.sh` on 2026-10-01) | — |
| SEC-11 | Cloud: runtime secrets come from Secrets Manager | [test-security.md](test-security.md) | AWS | NOT RUN YET as a test case (the runbook records the runtime secrets matching their schema and `check_database` passing as the runtime login on 2026-10-01) | — |
| THREAT | T1–T17 threats mapped to controls, implementation and evidence | [threat-control-map.md](threat-control-map.md) | Local Docker and AWS | Map filled and extended to T19: local rows rest on SEC-01..08 and SEC-12..16 PASS plus the scans; cloud rows PLANNED | 2026-10-01 |
| DATA-01 | Analytics refresh reconciled against an independent pandas check | [test-data-ai.md](test-data-ai.md) | Local Docker | PASS (existing prior record; not rerun here) | 2026-09-22 |
| DATA-01 | Rerun on the derived shoe dataset the application now imports | [test-data-ai.md](test-data-ai.md#shoe-dataset-rerun--26-september-2026) | Local Docker | PASS | 2026-09-26 |
| DATA-02 | ML customer segmentation on the shoe dataset: tests, training, strict import and operator dashboard | [test-data-ai.md](test-data-ai.md#shoe-dataset-rerun--26-september-2026) | Local Docker | PASS | 2026-09-26 |
| DATA-02 | ML hold-out (90-day time split) and 80% subsample stability evaluation; segments show no predictive difference on this synthetic data | [test-data-ai.md](test-data-ai.md#hold-out-and-subsample-evaluation-m-02-m-05) | Local Docker | PASS (evaluation ran; result recorded as measured) | 2026-09-26 |
| DATA-02 | ML feature fix (review M-03): `log_rfm_aov` recipe compared, adopted as default, retrained, imported and shown on the dashboard | [test-data-ai.md](test-data-ai.md#feature-fix-m-03) | Local Docker | PASS | 2026-09-26 |
| RES-01 | Database outage returns a clean 503 while the health check stays up | [test-resilience.md](test-resilience.md) | Local Docker | NOT RUN YET | — |
| RES-02 | Live local database outage and recovery | [test-resilience.md](test-resilience.md) | Local Docker | NOT RUN YET | — |
| RES-03 | Cloud scaling or recovery mechanism | [test-resilience.md](test-resilience.md) | AWS | PLANNED | — |
| MON-01 | Local structured JSON request logs: export and status/path summary | [monitoring.md](monitoring.md) | Local Docker | NOT RUN YET | — |
| MON-02 | CloudWatch Logs Insights query and 5xx alarm test | [monitoring.md](monitoring.md) | AWS | PLANNED | — |

## Other required artefacts

| File | Contents | Status |
|---|---|---|
| [aws-build-runbook.md](aws-build-runbook.md) | One dated entry per build step: commits, plans, acceptance checks, problems, lab balance (stage 1 on 2026-09-29; the state split, variant A and its operations on 2026-10-01) | In progress (infrastructure owner) |
| `architecture.png` | Architecture diagram showing users, application components, cloud services, trust boundaries, data stores, observability and data flows | TODO (report lead) |
| [raw/](raw/) | Raw command output named `<CASE-ID>_<YYYY-MM-DD>.<ext>`; screenshots, if needed, named `<CASE-ID>_<YYYY-MM-DD>_<n>.png` | Contains current FUNC-01/FUNC-02 and DATA-01/DATA-02 output |

## Status words

- `PASS`: the command or step ran and matched the expected result written before it ran.
- `FAIL`: it ran and did not match; keep the failure, explain it and add a later rerun after a fix.
- `NOT RUN YET`: not run in a recorded session, or it could not run.
- `PLANNED`: depends on work not available yet, such as the AWS deployment.

## Evidence rules

- Every actual result comes from a command run in the recorded session and saved unchanged in `raw/`, except for cut lines marked `…` and redactions marked `<REDACTED>`.
- Write the expected result before running the command and do not change it after seeing the output.
- Dates come from `date +%F`; commit hashes come from `git rev-parse --short HEAD`.
- Re-runs add a new dated row; earlier results remain.
- Manual steps record only what the human reports.
- Use `Local Docker` and `AWS` explicitly; local checks do not prove hosted behavior.
- Prefer text/config exports to screenshots. Screenshots are supplements and need captions and written descriptions.
- Redact account IDs, public IPs, tokens, credentials, private URLs and personal data. Do not include production data or secrets.
- Do not run `aws` or `terraform` commands from the evidence-writer workflow.
- The evidence writer does not write `Verified by`; the human reviewer adds it.
- The evidence writer does not fix application code. A failing command is recorded as `FAIL` and reported to the code owner.
