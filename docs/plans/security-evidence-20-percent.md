# Plan: security evidence, the high-value 20%

Written 1 October 2026 by the security session. Scope: rubric criterion "Security and responsible cloud practice" (15 marks). Time is short, so only the steps that turn existing work into verifiable evidence come first. Backend, `src/Dockerfile`, `requirements.txt` and `src/infrastructure/**` are not edited (backend freeze; Terraform belongs to another session).

## Steps, in order

1. **Record the unrecorded local cases.** Run the tests already cited in the threat-control map for T7 and T8 to T12 and T17 (`test_settings.py`, `test_secrets.py`, `test_health.py`, `test_request_logging.py`, `test_import.py`) in local Docker. Add them to `evidence/test-security.md` as SEC-12 onward, each with setup, command, expected result (written before the run), actual result, date, commit and raw file. Rerun SEC-ALL at the current commit.
2. **Run the scans once, locally, as pinned containers.** Raw output in `evidence/raw/SCAN-*`. Tools: gitleaks (working tree and history), pip-audit, bandit, hadolint, Trivy (built image and `src/infrastructure/` config), and `manage.py check --deploy` in production-mode settings.
3. **Triage.** `evidence/security-scan-triage.md`: every finding is fixed, accepted with a reason, or a false positive. Nothing is hidden. A finding in a frozen area stops work and is reported to the user. A finding in `src/infrastructure/**` goes to the Terraform session.
4. **Update the map and the security record.** Add a test-ID column and a supply-chain threat. Add an honest accepted row for IAM least privilege under the Learner Lab. Mark the infrastructure paths that the base/ec2/fargate split will change. Add a command to every case.
5. **Later, not now:** the CI jobs (they only encode commands proven in step 2), and the cloud script for SEC-09 to SEC-11 once the stack is deployed.

## Defaults taken because the user is busy

The tool set above; CI gating to be decided at step 5; local Docker may be built and started because the checks need it.

## Not claimed

No cloud control is claimed until it is run against the deployed stack. Expected scan findings are guesses until the raw output exists.

## Status (1 October 2026)

Steps 1 to 4 done: SEC-12 to SEC-16 and the SEC-ALL rerun recorded; SCAN-01 to SCAN-07 run locally and triaged ([security-scan-triage.md](../../evidence/security-scan-triage.md)); the map extended to T19 and commands added to every case. Step 5 not started (CI jobs, cloud script for SEC-09 to SEC-11). Four findings are open and belong to other owners (listed in the triage file). Nothing committed.
