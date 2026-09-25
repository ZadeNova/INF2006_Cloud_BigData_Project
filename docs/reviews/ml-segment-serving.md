# ML segment serving — Phase 2

Date: 25 September 2026. Status: implementation, focused PostgreSQL/browser verification and independent backend review complete; local commit preparation.

## Upstream integration

- Branch: erfan/analytics. Initial tree/index clean, no pre-existing rebase or merge. Tracking origin/erfan/analytics. No stash required.
- Fresh `git fetch origin` succeeded. Upstream: `89019b4bc10a22d7ce8d40769582652bd35030e7`; one incoming documentation commit adding planned signature evidence demos, none executed. `git log --left-right --cherry-mark` showed no equivalent local commits upstream.
- Requested backup retained: `CL/phase2-pre-rebase-20260925` at `eb914ef60160aa47479a48152702e3547d255369`. Created before the user's subsequent instruction to create no new branches; all work remains directly on erfan/analytics and no further branch was created.
- `git rebase origin/erfan/analytics` replayed both local commits, without skipping any. Mapping: `edabbc344e971f9090356c6de315d65c5972e0ba` -> `567c3e2807f0f652cc3ac293f18cd8dbfcea024e`; `eb914ef60160aa47479a48152702e3547d255369` -> `9734347a74b0a371cd631c45f3291f455b4fe536`.
- Both conflicts were in docs/IMPLEMENTATION_PLAN.md. Coordinator retained upstream planned demos, Phase 0/1 completion records and corrected committed/upstream verification attribution; removed the obsolete duplicate pre-commit deploy-readiness entry. No backend or frontend code conflicts occurred.
- `git range-diff e58e3a1..CL/phase2-pre-rebase-20260925 origin/erfan/analytics..9734347` shows only tracker context differences. `git diff --stat CL/phase2-pre-rebase-20260925 9734347` is exactly the upstream additions: tracker 2 lines and TESTING 14 lines. Application code, tests and historical review records preserved unchanged by rebase. Commit subjects and descriptive bodies retained.
- Phase 2 baseline: `9734347a74b0a371cd631c45f3291f455b4fe536`. Updated guidance unchanged by upstream. Prior reviews are historical evidence, not approval of this task.

## Scope and ownership

M-10 serving privacy, READY-001 balanced sample, and F-06's vacuous operator assertion only. Coordinator owns documentation, this review record, tracker and Git. Backend `/root/phase2_backend`: explicit gpt-6-astra / low, query/context/tests. Frontend `/root/phase2_frontend`: explicit gpt-5.6-luna / max, minimal template/presentation and browser verification. Independent fresh-context gpt-6-astra / medium reviewer will inspect the frozen diff read-only. Subagents may not stage, commit, rebase or push.

Agreed behavior is recorded in [segment serving contract](../ANALYTICS.md#segment-serving-contract) and [API context](../API.md#analytics-backend-context). Uniform CUS references avoid arbitrary source text and namespace collisions and support profileless shoppers. Round-robin ranked selection preserves overall50/per-label25 bounds and deterministic grouping; totals remain distinct from samples.

Architecture decision: explicitly triggered batch ML; saved-model inference optional; Scheduler/Lambda no longer selected. Narrowly reconcile active docs, preserve historical reviews and existing code outside this task. ECR/SNS/CloudTrail/WAF/Secrets Manager remain selected. Pending/failed/stale lifecycle, immutable features/artifacts, model quality and AWS readiness remain open; Phase 3 is ML quality and reproducible evaluation.

## Verification

Docker initially stopped; Astra Low started Docker Desktop hidden and inspected containers/volumes/networks before creating resources. Existing stopped inf2006-ml-loader-db-1, network and named volumes preserved. Task project inf2006-phase2-20260925 uses container inf2006-phase2-20260925-db-1, its matching default network, loopback PostgreSQL 57703 and tmpfs storage (no named volume). Temporary compose.yaml and env.ps1 reside under C:/Users/limch/AppData/Local/Temp/inf2006-phase2-20260925; task-only credentials are omitted and repository .env was not printed.

After sourcing that env.ps1, Astra Low ran from repository root:

```powershell
.\.venv\Scripts\python.exe src/manage.py migrate --noinput
.\.venv\Scripts\python.exe src/manage.py collectstatic --noinput --verbosity 0
.\.venv\Scripts\python.exe -m pytest -q -c src/pytest.ini -p no:cacheprovider --tb=short tests/test_analytics_queries.py tests/test_customer_segments_command.py analytics/tests/test_segment_loader_integration.py analytics/tests/test_segment_customers.py
.\.venv\Scripts\python.exe -m pytest -q -c src/pytest.ini -p no:cacheprovider --tb=short tests/test_analytics_dashboard.py
.\.venv\Scripts\python.exe src/manage.py check
.\.venv\Scripts\python.exe src/manage.py makemigrations --check --dry-run
git diff --check
```

Results: 82 query/Phase 1 regression tests passed in 19.69s; 25 dashboard tests passed in 14.03s, total **107 passed**. Initial dashboard attempt: 24 passed/1 failed on obsolete copy assertion; corrected to the new total/sample copy and all 25 reran successfully. Django check clean; no migration drift. Whitespace check passed (CRLF normalization warnings). Changed-line local Markdown link check: 3 checked, none missing.

Covered: 17/17/16 across three overfull groups; uneven1/5/4; cap exhaustion; groups exceeding slots; zero bound; deterministic identity ties and existing monetary order; single query; profiled/profileless CUS references and stable account rename; run/model isolation; full/HTMX privacy assertions against actual fixture values; existing operator access checks. No duplicate Phase 1 eligibility matrix added.

Browser results are recorded below. Not run: full suite, full dataset/model evaluation, Docker application build, hosted CI, AWS or deployment. No prior review result is reused as approval of the current changes.

## Independent review

Completed through round 2 below; browser gate remains separate.

### Frozen round 1 snapshot

Reviewer /root/phase2_reviewer, explicitly gpt-6-astra / medium, Independent (fresh session), read-only. Assigned all 18 changed tracked paths plus this new log, rebase identities/resolutions, contracts, results and limitations. Backend and frontend source frozen during review; only coordinator verification metadata may change. Working-byte SHA-256:

| Path | SHA-256 |
|---|---|
| PROJECT_SCOPE_INF2006.md | ada9355e500ab7b6b760a0669f3bd8373cddf5348b62cfc1b10a52155e964911 |
| README.md | 02dc0049acc3adde8342a3c32e464f8887a981295f05396836b2f706d66dfe36 |
| analytics/README.md | da7380712ab66c2755bd4c8771853d4f4c4c0a781fab73e9ba9cda9ff9d40a52 |
| docs/ANALYTICS.md | 82742ca81760d891b3aa4781d259399c97a56a35aa6665647b1118fe9549eed8 |
| docs/API.md | cc35aed0c5323ce9825601db704e5d8ba1a7f6be076aabd146e178f4e693481a |
| docs/ARCHITECTURE.md | 1fccbefecd1624cac4f8b3d4039b3a099fbf2fd8e817b4659f8344bb1719104f |
| docs/AWS_CAPABILITY_CHECK.md | 07c29a3edd205551aad7b4678ff842c4cfa1506ca6f6365d3abfcd66733e99f6 |
| docs/AWS_INFRASTRUCTURE.md | 0c713775e77987d11158e6ddac3c2a5abf99c386b907d84ff6f41e5d6bd93c0b |
| docs/IMPLEMENTATION_PLAN.md | da62ce6915c892c37681948ea348524caeb028b038d5420e285f5e9efcfc6b21 |
| docs/INF2003_BASELINE.md | cb43c79814d78751e2fe62a67b319b5362995a5733b79a0c0a4df2b38d05c29d |
| docs/SECURITY.md | 29c09d7aca787d62be73349bbe9c796e7a9a280ea67365084f52fc8370689416 |
| docs/plans/backend-aws-readiness.md | ad8dd619708f07c1f4c528db4660967fe201ed636f5aaa8253abfddab395d38b |
| docs/plans/cloud-independent-prep.md | 64d1547b1d7b0dbbb85ffb2bad1d168b129fef3a687dd4f8d9f9124b53e17878 |
| src/reporting/queries.py | f5bc2fba0a904f0bd5fdef4e22e2d48c29e612b292c4a061dc883c456f76e42c |
| src/static/css/site.css | faeb7b908c85e56399eff716e130114c9c1703cd63fd45c986fbd66d62a84183 |
| src/templates/reporting/_panel.html | 58612de6dc1e303108187b2763a00375d7369d76fd94042a4906a19e35f56bf6 |
| tests/test_analytics_dashboard.py | 8a22dd0c6380c7ab9fe209149355ab8e2137f25850cfc29826d98add5d00e5ed |
| tests/test_analytics_queries.py | f26cbf2721765acba9f2d38dcd7ada606549867809c00f294717ee88a6c5392a |

### Round 1 outcome and correction

Independent fresh-context Astra Medium reviewed all 18 tracked changed paths plus this log. Verified all five source/test hashes and rebase preservation: historical reviews/application code unchanged by integration. No actionable code, security, query-efficiency, test-duplication or template-integration findings. Independently ran query/dashboard tests against task PostgreSQL: **61 passed in 15.78s**. Initial sandbox attempt could not source environment/write temporary files, so it failed before tests; escalated execution succeeded. `git diff --check` passed. Browser verification remains frontend-owned; no independent full suite, model evaluation, Docker build, CI or AWS checks.

| ID | Severity | File/line | Required spec / evidence | Issue and expected correction | Fix / verification | Re-review outcome |
|---|---|---|---|---|---|---|
| SEG-001 | P2 | docs/plans/backend-aws-readiness.md:127 | Explicit batch ML, optional saved-model inference | AWS-ready exit still required scheduled ML publication and model path; require S3 dataset/import and explicit batch evidence, with saved-model evidence conditional | Coordinator corrected documentation-only criterion and linked current next-step ownership to tracker; source/test files unchanged | Resolved in round 2 |

Documentation is coordinator-owned; no backend fix or implementation escalation was needed. Revised complete diff submitted to the same reviewer tier. Repeated-issue rule remains in force.

### Round 2 outcome

Same independent fresh-context Astra Medium: **SEG-001 resolved; no unresolved actionable findings; backend gate clear**. Reviewed revised complete task diff and prior finding; all other 17 tracked paths match round 1 hashes. `git diff --check` passed. Source unchanged, so independent 61 passing tests remain applicable; no redundant rerun. Browser verification remains a separate pending frontend gate. No model-quality, full-suite, hosted CI, Docker-build or AWS readiness claim.

## Focused browser verification

Frontend Luna Max used Codex In-app Browser through mcp__cua_repl at `http://127.0.0.1:8765/analytics/`. Hidden task server returned authenticated HTTP 200. Default desktop viewport checked; exact pixel dimensions and mobile coverage unavailable. Task fixture run e53f1636-a297-4b15-b898-cb13289e2b8c contains 90 profileless customers, 30 per high_value/core/at_risk group. Coordinator independently queried task PostgreSQL and confirmed those three counts.

Rendered screenshot showed the populated panel, five-column table, CUS references, all three groups, full population total90 and explicit Showing50 of90 sample wording. Selected distribution17/17/16; references included CUS-2 through CUS-77. No login username column/title/data appeared. Screenshot displayed inline in the browser tool; no persisted image path was produced. No visual redesign occurred.

Limits: browser HTMX range interaction was not completed; coordinator interruption ended the browser surface before the rerun. Full/HTMX rendered privacy and access contracts passed the automated HTTP tests; those tests are not claimed as visual verification. No mobile/theme/accessibility sweep was performed. These limits do not affect the focused desktop table check.

Frontend stopped its prior PID20667 and second server session36250 and confirmed loopback port8765 closed. Disposable PostgreSQL cleanup is recorded at final staging below. Source remained frozen throughout browser and review work.

## Final staging and cleanup

Coordinator selectively staged exactly the 19 task files. All unchanged-since-review source/contract hashes match the frozen snapshot, and staged blobs equal working content after CRLF-to-LF normalization. The only post-round-1 changes are the round-2 reviewed plan correction and coordinator completion metadata in tracker/log. Staged whitespace check passed; staged additions had no private-key, AWS access-key or credential-bearing PostgreSQL URL patterns. No unrelated initial changes existed and none were discarded.

Backend ran `docker compose -p inf2006-phase2-20260925 -f "$env:TEMP/inf2006-phase2-20260925/compose.yaml" down`; task container/network removed, no volumes removed. Existing stopped inf2006-ml-loader-db-1, inf2006-ml-loader_postgres_data and inf2006-ml-loader_default preserved. Ignored src/staticfiles, created by this task's collectstatic, was removed only after exact absolute workspace containment, creation-time and ignore checks; absence verified. Teardown emitted an unset task-password interpolation warning but removal succeeded, with no secrets printed. Temporary task configuration remains outside Git.

Local checkpoint authorised after focused desktop visual verification and clear independent review. Browser HTMX/mobile and broader model/AWS gates remain explicitly unverified. Backup reference retained; nothing pushed or deployed. Next bounded Phase 3: ML quality and reproducible evaluation.
