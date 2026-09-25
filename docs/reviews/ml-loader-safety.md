# ML loader safety — Phase 1

Date: 25 September 2026. Status: Phase 1 implementation and independent review complete; local commit preparation.

## Baseline and scope

- Branch `erfan/analytics`; starting HEAD `edabbc344e971f9090356c6de315d65c5972e0ba` (Phase 0 local commit). Fresh `git fetch origin` succeeded; origin remains `e58e3a1c670bfad87c3cb9821cd3d95f25617057`. `git rev-list --left-right --count HEAD...origin/erfan/analytics` returned `1 0`; no incoming commits, pull, merge or rebase needed.
- Phase 0 commit and [review record](phase-0-baseline-alignment.md) confirm reported 20 passing fake-CLI tests for implementer and independent reviewer, with no unresolved actionable findings. Those checks are historical evidence, not rerun by Phase 1.
- Initial index empty. Inherited unfinished tracked edits: `analytics/README.md`, `analytics/segment_customers.py`, `docs/ANALYTICS.md`, `docs/IMPLEMENTATION_PLAN.md`, `docs/SCHEMA.md`, `src/reporting/management/commands/load_customer_segments.py`, `tests/test_customer_segments_command.py`; this review file was untracked. All are part of the bounded Phase 1 candidate, subject to completion and independent review. Initial copies saved outside the repository at `C:/Users/limch/AppData/Local/Temp/inf2006-phase1-4d8ce87dfb0f4faea73bb6a4edd11b6b` distinguish inherited edits from this task's changes. No other initial changes found.
- Scope: F-02/M-09 validation, F-03 and M-10 extraction eligibility, READY-003 coherent complete imports and atomic concurrent replacement. [B1 plan](../plans/backend-aws-readiness.md), [finding dispositions](backend-aws-readiness.md), [original review](../latest-opus5.5-review.md), [analytics contract](../ANALYTICS.md#segment-import-safety-contract), [schema](../SCHEMA.md), [testing](../TESTING.md) and [backend gate](../DEVELOPMENT.md#backend-review-gate).

## Ownership and policy

Implementer `/root/phase1_implementer`: explicitly `gpt-6-astra` / `low`, owns extraction, loader, focused tests and necessary contract documentation. Coordinator owns this log, tracker, selective staging and local commit. Separate fresh-context `gpt-6-astra` / `medium` reviewer will be read-only; no coordinator review substitutes for that gate.

Eligibility is at least one completed order in the run inventory namespace strictly before cutoff, excluding staff, superusers and `store_operator` members, without requiring CustomerProfile. Current source records are checked at import time; changes in eligibility require regeneration. Cohort IDs do not prove original RFM values. Immutable feature-snapshot and model-artifact identity are deferred. Same-run/same-version atomic replacement is the explicit policy, including different valid payloads under the same identity; versions remain independent. Empty clusters and valid negative silhouette scores remain allowed.

Excluded: safe-reference presentation, balanced lists, freshness states, cluster naming/evaluation/preprocessing, saved artifacts/Lambda, Secrets Manager/TLS/bootstrap, Terraform/AWS and unrelated cleanup. This phase cannot close all of B1, M-10 or ML readiness. Next bounded Phase 2 proposal: safe customer references and balanced segment-list presentation/query behavior with the corresponding focused tests and review.

## Verification and independent review

Actual checks and review are recorded below. No push or deployment authorised or performed.

### Implementation verification and frozen snapshot

Astra Low completed the inherited draft, added deterministic customer ordering, lossless JSON decimal parsing, the actual auth.User integer bound, PostgreSQL-compatible text validation, and focused integration/concurrency coverage. New file: `analytics/tests/test_segment_loader_integration.py`. No model change or migration.

Before startup, implementer ran `docker ps -a --format '{{.Names}} {{.Image}} {{.Status}}'`, `docker volume ls`, and `docker network ls`. Pre-existing `inf2006-ml-loader-db-1` and its resources were untouched. Task-created project `inf2006-phase1-20260925` has container `inf2006-phase1-20260925-db-1`, network `inf2006-phase1-20260925_default`, tmpfs database storage (no named volume), and loopback port 57702. Compose file: `C:/Users/limch/AppData/Local/Temp/inf2006-phase1-20260925/compose.yaml`. Startup: `docker compose -p inf2006-phase1-20260925 -f "$env:TEMP/inf2006-phase1-20260925/compose.yaml" up -d --wait db`.

Environment: DJANGO_ENV=local; DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,testserver; POSTGRES_DB and POSTGRES_USER=phase1_loader; POSTGRES_HOST=127.0.0.1; POSTGRES_PORT=57702; PYTHONPATH=src;tests; PYTHONDONTWRITEBYTECODE=1. Disposable task-only POSTGRES_PASSWORD and DJANGO_SECRET_KEY were supplied in process environment and are intentionally omitted. No repository .env was printed.

Exact check commands from repository root:

```powershell
.\.venv\Scripts\python.exe src/manage.py collectstatic --noinput --verbosity 0
.\.venv\Scripts\python.exe -m pytest -q -c src/pytest.ini -p no:cacheprovider --tb=short tests/test_customer_segments_command.py tests/test_analytics_queries.py tests/test_analytics_dashboard.py analytics/tests/test_segment_loader_integration.py analytics/tests/test_segment_customers.py
.\.venv\Scripts\python.exe src/manage.py check
.\.venv\Scripts\python.exe src/manage.py makemigrations --check --dry-run
git diff --check
```

- Initial focused attempt: 1 failed, 7 passed, 37 errors due to fixture orders missing existing order-origin identifiers; fixtures corrected.
- Focused rerun (above pytest invocation excluding two reporting regression modules and `--tb=short`): **45 passed in 17.01s**.
- Broadened attempt: 92 passed, 9 failed because the host lacked collected static manifest. `collectstatic` generated previously absent ignored `src/staticfiles`; no application workaround.
- Final exact suite above: **101 passed in 14.73s**. Django check: no issues. Migration-drift check: no changes. Whitespace check passed (CRLF normalisation warnings only).
- Not run: full suite, full dataset/model evaluation, application Docker build, hosted CI, AWS or deployment. Producer fit/evaluation behavior is unchanged; loader acceptance of valid negative silhouette is covered.

Frozen implementation SHA-256 (working bytes; baseline-to-candidate includes inherited edits):

| Path | SHA-256 |
|---|---|
| analytics/segment_customers.py | F4E34301BDD597B37D94D340EFD94A8DE92892EDE8016ABC20970FAEC2B1C7C2 |
| src/reporting/management/commands/load_customer_segments.py | 4512867C07200921A3D64B310ABC5FEAB3E0CB21DBEC0ED78FFDCAC77BC21777 |
| tests/test_customer_segments_command.py | AD91DF58EA2DB49FF21A2113EBEE50A047F107ACC2052E003B159FBEA199160A |
| analytics/tests/test_segment_loader_integration.py | CB7E9C6F6581CE5443E5D74DC0C9C90CBD2E4D4BE3032BEEA9B417BE2F3A04F1 |
| analytics/README.md | C7A503B522BB6798370851522DC042CE9F6E48D76B002009CF9CE84352F5050F |
| docs/ANALYTICS.md | 4DA397BE277C0933AE53005D4880313C0C93E1A1A93F2C86ADAA0458A3955290 |
| docs/SCHEMA.md | 6DFCA5A6F835FA4072D12EC9F0125AAAB1FCE2AB40A5C7BF60E5EFBB65F95143 |

### Round 1 — Independent (fresh session)

Reviewer `/root/phase1_reviewer`, explicitly `gpt-6-astra` / `medium`, read-only and separate from implementer. Assigned complete frozen task diff, new integration file, contracts, findings, policy/exclusions and actual checks/unrun checks. Outcome: **no unresolved actionable findings**. Coordinator log/tracker metadata is outside the implementation freeze.

Reviewer independently verified all seven frozen hashes and reproduced the same five-module PostgreSQL command: **101 passed in 12.11s**. Initial sandbox execution could not create pytest temporary files; approved escalation permitted the successful run against only the task database. `git diff --check edabbc3` passed. Reviewer did not independently rerun Django check or migration drift; those are implementer results. Full suite, dataset evaluation, image build, hosted CI and AWS remain unrun.

Review covered producer/loader compatibility, SQL/ORM eligibility parity, types/database bounds, metadata and cohort coherence, rollback/concurrency, sanitized errors, simplicity/dead code, test duplication and accurate documentation. No Low fix/re-review cycle required.

| ID | Severity | File/line | Required spec / evidence | Issue and expected correction | Low fix / verification | Re-review outcome |
|---|---|---|---|---|---|---|
| None | - | Frozen seven-path implementation and contract snapshot | Phase 1 contract and independent 101-test PostgreSQL run | No unresolved actionable findings | Not required | Gate clear |

This closes only F-02/M-09 loader validation, F-03 eligibility, M-10 extraction eligibility, and the bounded READY-003 coherence/completeness/replacement policy. Presentation privacy, balanced lists and broader B1/M-10/readiness remain open. No immutable snapshot, feature-value equivalence, model-artifact or model-quality claim is made.

## Final staging and cleanup

Coordinator selectively staged exactly nine Phase 1 paths (the seven frozen files plus this log and tracker). All seven staged implementation/contract blobs match the independently reviewed working-byte hashes after Git CRLF-to-LF normalization; no behavior or dependency changed during staging. `git diff --cached --check` passed. Staged scope was inspected; added-line scanning found no private keys, AWS access-key IDs, credential-bearing PostgreSQL URLs or secret environment assignments. Test credentials are omitted from this record.

After reviewer checks, Astra Low ran `docker compose -p inf2006-phase1-20260925 -f "$env:TEMP/inf2006-phase1-20260925/compose.yaml" down`, removing only this task's container/network and tmpfs database. It verified the resolved recursive-delete target was exactly the workspace's `src/staticfiles` before removing that previously absent task-generated directory. Pre-existing `inf2006-ml-loader-db-1` remained healthy; its network and both pre-existing named database volumes were preserved. Initial backup and temporary Compose definition remain outside the repository. No unrelated initial working-tree changes existed. No push or deployment performed.
