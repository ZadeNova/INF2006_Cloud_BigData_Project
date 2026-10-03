# Final independent audit: ML/backend Phases 0–6

Date: 26 September 2026. Reviewed snapshot: `2c8b7dfe44f220644034d7bb393999c9dc6475df`, branch `erfan/analytics`. Starting working tree clean. Comparison base `89019b4`; no fetch/rebase, implementation edits, commits or push in this audit.

## Scope and independence

User requested a final independent review against the original Opus and additional ML/backend findings before deciding whether to authorise a push. Reviewer `/root/final_ml_audit`, explicitly `gpt-6-astra` / `medium`, Independent (fresh session), read-only, received bounded task context without implementing conversation history. Coordinator reconciled evidence and performed separate checks. References: [original Opus review](../archive/latest-opus5.5-review.md), [additional findings](backend-aws-readiness.md), and phase review records linked by the tracker.

Reviewer inspected final producer/loader/shared contract, serving queries/view/template integration, evaluation, TLS/secrets/bootstrap/startup policies, CI and relevant contracts/review records. This is a final integration audit, not a new exhaustive audit of every unrelated application feature.

## Finding and gate result

| ID | Severity | Location | Evidence and correction | Outcome |
|---|---|---|---|---|
| FINAL-ML-001 / MLH-002 | P3 | `analytics/segment_customers.py:29–33`; `analytics/tests/test_startup_credentials.py:28` | Phase 5 restored the trainer-only `connect(database_url=None)` interface removed under Phase 4 MLH-002. Trainer main at line 291 and evaluator at line 126 call only `connect()`; trainer has no URL CLI option, as README line 53 documents. Only the startup test exercises the parameter. Remove this unused trainer parameter/branch and adjust its test; preserve the verifier's genuinely supported URL path and shared TLS policy. | Actionable recurrence; not fixed in this read-only audit. |

No new security or functional correctness defect was identified in the inspected changes. This is unnecessary code/test coupling, not a credential bypass or broken batch workflow. Nonetheless, the no-unresolved-actionable-findings gate is not clear. Preserve MLH-002 identity rather than treating it as a new Low retry. Under the repository recurrence stop rule, implementation awaits user manual Astra Medium or fresh-session Opus 5.5 escalation and subsequent independent review. No fixes were attempted.

## Original finding reconciliation

| IDs | Final bounded disposition |
|---|---|
| M-01 / F-01 | Resolved: profile-relative descriptive labels, no forced churn/loyalty interpretation. |
| M-02 | Temporal predictive validation unrun; consciously excluded from descriptive scope. |
| M-03 | Bounded baseline/log-frequency comparison completed; correlated-volume and tenure limitations disclosed. |
| M-04 | Lifetime-to-cutoff definition/display resolved; no tenure correction claimed. |
| M-05 | Seed-stability contract satisfied; resampling enhancement explicitly unrun. |
| M-06 | Aggregate evaluation retained with metrics, profiles and provenance. |
| M-07 | Negative silhouettes retained; undefined metrics distinct. |
| M-08 | Recipe/configuration provenance and completed-output batch digest implemented for batch design. |
| F-02 / M-09 | Strict type/range/finite validation, sanitized database failures and atomic replacement implemented. |
| F-03 / M-10 | Matching eligible cohorts, privileged-user exclusion and CUS display references implemented. |
| M-11 | Dedicated output and environment/role credential runbook implemented; no root writable-repository workflow required. |
| F-06 / M-12 | Local collection/test/CI configuration gaps addressed; hosted execution still unverified. |
| F-04 | Actual-swap focus and history chart redraw implemented; browser execution remains recorded Phase 6 evidence. |
| F-05 / S-005 | Documentation/preview corrections retained; historical records distinguished from current dispositions. |
| S-006 | Own-run loaded/unavailable display and consistent summary/sample reads implemented; no fabricated orchestration state. |
| S-007 | Removed upstream; no recurrence identified. |
| W-01 / W-02 | Redaction, timeout and Markdown escaping corrections retained; actual cloud probe unverified. |
| W-03 | WAF-owned deployed control/test remains open. |
| S-001/002/003/004/008; W-04 | Outside bounded ML remediation and still open. W-04 is a backend-view pagination UX issue, so not every whole-repository backend finding is resolved. |
| READY-001 | Bounded balanced sampling implemented. |
| READY-002 | Production TLS policy implemented locally; real RDS remains unverified. |
| READY-003 | Coherent cohort/import/recovery contract implemented; no immutable feature-value proof. |
| READY-004 | Docker exclusions implemented with recorded sentinel/image evidence; publication unverified. |
| READY-005 / READY-009 | Secret/service/capability contracts reconciled; real permissions and HTTPS remain gates. |
| READY-006 | Superseded by explicit retrain/export/import; no Scheduler/Lambda; saved-model inference optional. |
| READY-007 | Secret/startup/health/role/migration contracts prepared locally; actual AWS integration open. |
| READY-008 | Stable ordering and feasible/actual-label candidate validation implemented. |
| READY-010 | Current accepted raw data matches retained evaluation; future accepted feature-changing revision requires reevaluation. |

Immutable snapshots, predictive validation, resampling and saved-model inference are not claimed completed. Existing unrelated frontend and submission gaps remain outside this gate.

## Fresh checks and limits

- Independent reviewer: non-mutating AST parsing of 29 changed Python files passed.
- Coordinator: `.venv/Scripts/python.exe -B -m pytest -q -c src/pytest.ini -p no:cacheprovider -p no:django analytics/tests/test_segment_customers.py` — 16 passed in 7.48s. One expected unknown `DJANGO_SETTINGS_MODULE` warning because Django plugin was explicitly disabled. Host environment, not a fresh pinned-container run.
- Coordinator: `git diff --check 89019b4..HEAD` passed.
- Coordinator: all six raw CSV hashes match `evidence/ml-quality-evaluation.json`.
- Coordinator: current views, panel template, dashboard test and loader test hashes match recorded Phase 6 values.
- Prior full suite, PostgreSQL, TLS, image, browser and end-to-end results were inspected as historical receipts, not rerun here. No AWS checks or hosted CI verification.
- CI currently triggers pull requests or pushes to main. A push to erfan/analytics alone does not trigger it.

## Recommendation

Do not claim all findings resolved or gate clear yet. Resolve FINAL-ML-001 / MLH-002 through the required escalation/review path before unconditional push clearance. Actual AWS release and final submission readiness are separate open gates. User push approval has not been given. Nothing pushed, deployed or committed by this audit.

## User-authorized Low correction and independent re-review — 26 September 2026

### Exception, baseline and ownership

The user explicitly authorized **one additional Astra Low remediation attempt** for the recurring FINAL-ML-001 / MLH-002 despite the earlier correction. This is a task-specific exception to the manual escalation requirement, not a reset of finding identity. If independent review finds this issue unresolved after this attempt, stop without another retry or automatic upgrade.

Baseline remains `2c8b7dfe44f220644034d7bb393999c9dc6475df` on `erfan/analytics`. Initial working tree contained only the pre-existing tracker modification and this untracked audit; both preserved. `git fetch origin` succeeded: origin advanced from `89019b4` to `e786c45`, leaving 10 local and 1 incoming commit. Incoming `e786c45` is AWS planning/documentation work across nine paths; no merge, rebase or upstream changes mixed into this fix.

Implementer `/root/implement_fix`, explicitly `gpt-6-astra` / `low`, made one correction in `analytics/segment_customers.py` and `analytics/tests/test_startup_credentials.py`. Coordinator owns this audit, tracker, staging and commit. No frontend work required.

### Correction and checks

Trainer now exposes only `connect()`, retaining DB-only `load_environment(DB_FIELDS)` and shared `connection_parameters(environ=env)`. Removed its unused URL parameter/branch. Both entrypoints retain production secret-delivery and verify-full assertions; URL-refusal coverage now applies only to the verifier. Verifier implementation and its supported local URL interface remain unchanged. Scoped callers in trainer main and evaluator use no arguments.

Implementer-executed commands from repository root, using the existing host virtual environment, `PYTHONPATH=src;tests`, `DJANGO_ENV=local` and `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1`:

```powershell
.venv/Scripts/python.exe -B -m pytest -q -c src/pytest.ini -p no:cacheprovider -p no:django analytics/tests/test_startup_credentials.py analytics/tests/test_segment_customers.py
# 18 passed in 2.15s; expected unknown DJANGO_SETTINGS_MODULE warning with Django plugin disabled.
.venv/Scripts/python.exe -B -m pytest -q -c src/pytest.ini -p no:cacheprovider analytics/tests/test_startup_credentials.py analytics/tests/test_segment_loader_integration.py analytics/tests/test_verify_refresh.py tests/test_customer_segments_command.py
# 56 passed in 11.82s.
.venv/Scripts/python.exe -B analytics/segment_customers.py --help
.venv/Scripts/python.exe -B analytics/evaluate_segments.py --help
.venv/Scripts/python.exe -B analytics/verify_refresh.py --help
git diff --check
# All four exited 0.
```

Integration used a newly created `postgres:17-bookworm` container, `inf2006-final-ml-fix-20260926`, tmpfs `/var/lib/postgresql/data`, database `mlfix`, loopback port 63636 and a random process-local fixture password supplied through environment. Creation command: `docker run -d --name inf2006-final-ml-fix-20260926 --tmpfs /var/lib/postgresql/data -e POSTGRES_PASSWORD -e POSTGRES_DB=mlfix -p 127.0.0.1::5432 postgres:17-bookworm`. Readiness: `docker exec inf2006-final-ml-fix-20260926 pg_isready -U postgres -d mlfix`. Host tests used local Django fixture settings and this server's postgres test role. Cleanup `docker rm -f inf2006-final-ml-fix-20260926` succeeded; pre-existing stopped container and shared volumes preserved. No real AWS secrets retrieved.

Additional implementer in-memory smoke passed: trainer signature has zero parameters; evaluator aliases that same function; explicit local environment supplies expected database/disabled local TLS; verifier accepts a local URL. These are focused smoke checks, not a full CLI training/evaluation run.

Changing producer bytes intentionally changes future recipe identity. Existing passing `test_replay_replacement_and_versions_are_independent` reimports a valid completed fixture export with non-current producer hashes, preserving old-export retry semantics. No historical evaluation/export evidence rewritten. Full application suite, fresh pinned analytics environment, full-cohort evaluation/export, actual CLI training/evaluation against full source, real AWS/IAM/RDS/TLS, image build, hosted CI and browser checks were not rerun. Production secret delivery used mocked retrieval.

### Frozen review snapshot

Review scope: baseline-to-working-tree changes in the two source/test paths, tracker and this complete newly added audit (including original historical findings). Source/test SHA-256 on disk:

| Path | SHA-256 |
|---|---|
| analytics/segment_customers.py | fdb79560bd66e398fe72b4cc1d4ab3deb07c83ce2f186ae1b93aa21ecadb9b72 |
| analytics/tests/test_startup_credentials.py | b85e23a1ef068b0f448023d0ba61b9141df46c6a4093edaeb193257fce1c3347 |

Independent fresh-context Astra Medium review pending; no completion or commit claimed at this freeze. Original audit finding and recommendation above remain the historical pre-correction result.
### Independent outcome — bounded gate clear

Reviewer `/root/independent_review`, explicitly `gpt-6-astra` / `medium`, **Independent (fresh session)**, read-only with no implementing conversation history or delegation, checked the complete four-path snapshot against `2c8b7df`, including the untracked audit. All four frozen on-disk hashes matched (tracker `b3f4794872542742bc0cb83236eba7ec1003b46912945e883947287867c98c46`; audit before this outcome `2b80b5fce0453b9577687503284f96e17a454ef4374d6cb3a4985e53c5135ef8`).

| ID | Severity | Correction / verification | Independent outcome |
|---|---|---|---|
| FINAL-ML-001 / MLH-002 | P3 | Removed trainer parameter/branch and obsolete test coupling; retained no-argument trainer/evaluator calls, secret delivery/shared TLS, verifier URL support/refusal and loader old-export compatibility | **Resolved. No new actionable findings.** |

Independent startup credential rerun: `.venv/Scripts/python.exe -B -m pytest -q -c src/pytest.ini --capture=sys -p no:cacheprovider -p no:django analytics/tests/test_startup_credentials.py` — **2 passed**, expected Django-setting warning. Independent `git diff --check` passed; no source or Git mutations. Attempted combined 18-test rerun stopped before collection because sandbox temporary directories were unavailable; startup-only rerun avoided filesystem capture. Reviewer inspected the implementer's 18-test, 56-test and CLI/smoke receipts; did not independently rerun the full suites. No limitation is recorded as a successful check.

Final bounded ML/backend review gate is now **clear**, following the user's single extra Low attempt and fresh-context Medium review. This supersedes the pre-correction recommendation above; original review history is preserved. Whole-repository unrelated findings, real AWS permissions/HTTPS/IAM/RDS/WAF and deployed integration, hosted CI/load evidence, immutable snapshots and submission gaps remain deferred/open exactly as recorded earlier. No push or deployment authorized or performed.

Coordinator checked local Markdown file targets (none missing), confirmed historical evaluation has no diff, and preserved source/test hashes through review. Only outcome/status metadata changes follow the frozen review. The authorized local commit includes this audit and the correction; its Git commit identity is the durable reference rather than a self-referential hash in this file.