# ML local release readiness — Phase 6

Dates: 25–26 September 2026, Asia/Singapore (verification crossed midnight). Status: local implementation, verification and independent review complete. Nothing pushed or deployed.

## Baseline, ownership and scope

Clean baseline `430e4c85eae7d770b7a0c7fbdbe6bada05d2604b` on `erfan/analytics`. Fresh `git fetch origin` succeeded; origin remained `89019b4bc10a22d7ce8d40769582652bd35030e7` (nine local, zero incoming commits). No rebase, backup branch or semantic conflict resolution was needed; no unrelated starting changes existed.

Backend `/root/backend_low`: explicit `gpt-6-astra` / `low`; frontend/visual verifier `/root/frontend`: explicit `gpt-5.6-luna` / `max`. Coordinator owns Git, contracts, evidence, tracker and review records. Required independent reviewer: fresh-context, read-only `gpt-6-astra` / `medium`; implementers do not stage/commit/push. No Terraform/AWS edits, shared database/volume changes or accepted dataset changes.

Relevant contracts: [development gate](../DEVELOPMENT.md#backend-review-gate), [analytics lifecycle](../ANALYTICS.md#segment-display-and-lifecycle-contract), [API](../API.md#analytics-backend-context), [schema](../SCHEMA.md), [security](../SECURITY.md), [testing](../TESTING.md), [frontend](../FRONTEND.md), [design](../../DESIGN.md), [runtime handoff](../AWS_INFRASTRUCTURE.md#image-and-infrastructure-owner-handoff). Preserve [original finding IDs](backend-aws-readiness.md), especially S-006/M-04. Phase 1–5 integration contracts: [loader](ml-loader-safety.md), [serving](ml-segment-serving.md), [quality](ml-quality-evaluation.md), [batch](ml-batch-handoff.md), [runtime](runtime-aws-security.md).

## Display and consistency contract

Use existing selected run/cutoff and `segment_overview.model_version`. Loaded assignments identify their own run, cutoff and recipe version; full recipe identity is in a keyboard-operable disclosure. RFM is lifetime completed-order history strictly before cutoff, independently of dashboard range/compare filters. No assignments means "No segmentation results loaded for this run". No older fallback, invented running/failed/stale state or batch-status model. Persistence does not retain batch ID, so no fitted-model/immutable-artifact claim. Invalid replacement retains valid loaded results. Safe CUS references, balanced sample limits and operator permissions remain.

The view's eager overview/sample reads now take the loader's existing run lock together, preventing concurrent replacement from mixing publications. Existing whole-context pruning retries remain. One real PostgreSQL reader/loader regression covers that defect; one own-run/filter test plus extended existing render assertions covers the display. Query count remains constant with dataset size: 17 in transaction-wrapped tests vs previous 14 (lock plus savepoint/release). No schema, migration or training-policy change.

## Dataset and complete workflow

All six raw CSV SHA-256 values independently match `evidence/ml-quality-evaluation.json`. Accepted Analytics Engineering Ecommerce Sales & Returns v1.0.0 remains unchanged; `data/derived/shoes` is absent. Retain the existing aggregate evaluation; later accepted feature-changing data requires reevaluation. This is not immutable feature provenance.

Isolated import accepted 20,000 customers, 1,200 products, 100,000 orders and 237,537 lines; zero rejects. Inventory `import-v1-9884d29e2bf9a64778c63858230ebd71223569b293c28c8acb895b1920e10d0f` matches the evaluation. Completed run `0d42256e-fc61-4410-b434-a04d6f74a8d8`, cutoff `2026-01-01T16:00:00Z`, published 65,589 daily rows from 71,079 lines. Independent pandas/raw-table and coverage-target verification: 29,898 completed orders in the reporting window; all daily-row/unit/sales/coverage mismatch counts zero; maximum money difference 0.00; 307 flagged and 431 no-recent-sales products.

Pinned training under SELECT-only `phase6_reader` produced 19,766 assignments, k=2, silhouette 0.4347, seed ARI 0.984. Import loaded all 19,766. Recipe `rfm-v3-ef86b30f1c76ca4e093bd20319478e1fb8b88bb41dd70d046a79c931e3bdfd34`; batch `fade785eec25e49e2f87c800ee77353993c03e866a57aa3c692a3dbf582dc56a`; export SHA-256 `d0f6f363a633730311cb1dadeffd0a0b8521dae486de847ac5bcdd2522dd21be`. Customer exports stay outside Git.

Actual failure/recovery checks:

- A nonexistent explicit training run exited 1 and retained the valid output hash.
- First import failed safely because root-owned mode0600 output was unreadable by app UID10001. Correcting ownership of that exact private file allowed exact-file retry without retraining.
- After loading, an altered source envelope with recomputed batch digest was rejected. Persisted assignment digest remained `190c02aebccd6b4212715050eeabc4b4f17a6af53cb6d8efabe2e9e22823b60b`; original exact-file replay succeeded with the same digest.
- A newer completed run `ea38129f-9e74-4be1-b639-03907c574b76` was refreshed with the same cutoff/counts and no assignments. The older loaded run remains retained (zero pruned), enabling a real no-fallback browser check.

## Executed checks and image history

| Check | Actual result |
|---|---|
| Focused host dashboard/query/loader | 111 passed in 12.27s after collectstatic; initial 102-pass/9-render-failure attempt lacked the task static manifest. Setup corrected, not suppressed. |
| Pinned Python 3.13 pure ML | 16 passed in 2.38s, no Django installed. |
| Pinned web + ephemeral analytics environment | 54 passed in 5.77s (strict loader, verifier, command tests). |
| Standalone startup-credential boundary | 2 passed in 1.43s in pinned app/analytics environment. |
| Separate disposable bootstrap server | 9 passed in 3.76s, including all eight opt-in cases skipped by the general app suite and one overlapping redaction case. |
| Django system/migration checks | Clean; no missing migrations. |
| Gunicorn/readiness | Actual image CMD; `/health/` 200/status ok, database OK/migrations applied. Rechecked after recreations. |
| Web/ML isolation | numpy/pandas/scipy/sklearn absent in web image; ML dependencies only in separate pinned tools/ephemeral check environment. |
| Full-data workflow/recovery | Passed as above; unchanged evaluation retained. |

Counts overlap and must not be summed as unique coverage. Phase 5 TLS/sentinel results remain historical; unchanged security code did not justify repeating all experiments. No real AWS test is inferred.

Images were rebuilt whenever browser verification required an asset correction. Intermediate local IDs and full-suite results:

| Intermediate image ID (`sha256:` prefix) | Result / reason superseded |
|---|---|
| `15a876232f2c268b74a720f79654743fe6cb52f251ebd7fb715b80550052e67d` | 472 passed/8 opt-in skips, 37.87s; actual swap did not focus heading. |
| `2a9bbcc6d6a4bb359f05682263fb90d916f36907c8b7281faedd1c96edb73bf3` | 472 passed/8 opt-in skips, 28.83s; focus worked but mobile heading was hidden. |
| `c50cac51d9abf2a0c8c5e43e9ab99505543f2bb336f8b397739b58de4109484d` | 472 passed/8 opt-in skips, 32.09s; ring visible but actual 194px mobile header exceeded CSS anchor offset. |
| `96a8e034d72c77ad0e836d5ebba64efe07675e604e66a12e2b75162dede949cb` | 472 passed/8 opt-in skips, 30.08s; native focus scrolling conflicted with measured adjustment. |
| `d01f3b2be9485470052af51956387e21230ad5f3f7167d88219495469a17ceb4` | 472 passed/8 opt-in skips, 34.48s; focus browser pass, then MLR-001 history-redraw finding. |

Final image, after measured-header correction: `inf2006-phase6-final`, local Docker ID **`sha256:db198bc83e76aa59e4070568c5d39685da7471d95cc5086c62af888f133c2907`**, not an ECR manifest digest. Final-image suite **472 passed, 8 opt-in skips in 27.45s**; all eight skipped cases passed separately. Final packaged CSS SHA-256 `caddb0bf8d51eac39e7b3de6b3e5c8f8680af04e2d55c969954461f493f35309`; JS `ad1b45de9faca60d998d01662b3bee3f871647fe73c91d2b05891b0b5d9e445f`. Packaged runtime files match the frozen checkout without source overlays; health passed after recreation. All eight bootstrap skips passed separately; backend/ML/test bytes stayed unchanged through asset-only rebuilds.

Stable tested SHA-256 values: `src/reporting/views.py` `8b1e2180b83d9c40938a8db9dc0ea51ce137ffe01d504b5e3f680333ee62550e`; `src/templates/reporting/_panel.html` `78db6c2d149ab65f65dc86331501d2ee2b7eadd3e62057882b63af414036d10c`; `tests/test_analytics_dashboard.py` `39c2270c09c6e600579c1eb77f7a151defa3a78d12484e2e81d9af50177f2da8`; `tests/test_customer_segments_command.py` `8682cfa7d21981d7773efc6eee09527eae297fe86a6795f87a800172fd63a18a`. Source identity is baseline plus frozen diff/hashes until the containing commit exists; no preexisting commit/ECR digest is invented.

## Live browser verification

Luna used the actual authenticated app at `http://127.0.0.1:58006/analytics/` via CUA. Its visible-tab wrapper was unavailable, but an own task browser tab worked; coordinator opening a separate temporary tab did not substitute for Luna verification. No screenshots are committed; screenshot/DOM observations were inline tool results.

Verified loaded and initial unavailable states, full UUID/cutoff/recipe disclosure, lifetime-period copy, 19,766 total customers, CUS references and balanced sample wording. Desktop viewport 1280x720 (content 1265); mobile 390x844 (content/scroll width 375, no horizontal overflow). Loaded light/dark appearances passed. Keyboard Enter opens recipe disclosure with SUMMARY focus. Initial page active element BODY confirms no startup focus steal. Actual 7D/90D interactions changed URL/filter metadata and focused the replacement H2.

F-04 original startup behavior was code-traced, not reproduced before editing. Browser checks found actual range-swap focus failure with the initial correction; Luna replaced the obsolete htmx:load handler with a single scoped afterSwap handler. Initial chart drawing stays on DOMContentLoaded. Subsequent mobile checks found hidden focus behind the sticky header; scoped normal focus/ring/anchor offset was insufficient for the actual header height. The final correction preserves scroll during focus, measures header/heading and adjusts only an obscured focused heading with existing spacing; native automatic focus scrolling is disabled so it cannot override that adjustment. Final visibility/newer-unavailable retest passed as recorded below; no unrelated frontend polish is claimed.

## Command receipt and resource boundaries

Task scratch `C:/Users/limch/AppData/Local/Temp/inf2006-phase6-20260925`; `C` below denotes `docker compose -p inf2006-phase6-20260925 -f <task-scratch>/compose.yaml`, not a checked-in command. Private task environment: local mode; random signing/app/admin/operator credentials; app role `phase6_app` NOSUPERUSER/CREATEDB for pytest, database `phase6`, loopback DB port57706; namespace `synthetic/revision-a/demo/v1`; source UUID `66666666-6666-4666-8666-666666666666`. Trainer SELECT-only role `phase6_reader`. Main/second bootstrap PostgreSQL are disposable tmpfs; no existing volumes touched. Local CREATEDB is not a production privilege claim. Private env.json can be imported into the process for host checks without printing values.

```text
.venv/Scripts/python.exe -B -m pytest -q -c src/pytest.ini -p no:cacheprovider --tb=short tests/test_analytics_dashboard.py tests/test_analytics_queries.py tests/test_customer_segments_command.py
.venv/Scripts/python.exe -B src/manage.py import_dataset --source data/raw --namespace synthetic/revision-a/demo/v1
.venv/Scripts/python.exe -B src/manage.py refresh_analytics --as-of 2026-01-02 --namespace synthetic/revision-a/demo/v1 --inventory-version import-v1-9884d29e2bf9a64778c63858230ebd71223569b293c28c8acb895b1920e10d0f
docker build -t inf2006-phase6-final src
C up -d web
C run --rm --no-deps web python manage.py check
C run --rm --no-deps web python manage.py makemigrations --check --dry-run
C run --rm --no-deps web pytest -q -p no:cacheprovider /app/tests
C exec -T web python manage.py check_database
docker exec inf2006-phase6-analytics python analytics/segment_customers.py --run-id 0d42256e-fc61-4410-b434-a04d6f74a8d8 --output /output/segments.json
C run --rm --no-deps web python manage.py load_customer_segments --run-id 0d42256e-fc61-4410-b434-a04d6f74a8d8 --input /output/segments.json
C run --rm --no-deps web python /work/analytics/export_coverage.py --run-id 0d42256e-fc61-4410-b434-a04d6f74a8d8 --output /output/coverage.json
docker exec inf2006-phase6-analytics python analytics/verify_refresh.py --run-id 0d42256e-fc61-4410-b434-a04d6f74a8d8 --coverage-target /output/coverage.json
```

Pure ML used the exact pinned Python3.13/requirements/pytest command in `.github/workflows/ci.yml`, read-only repo mount and `-c /dev/null`. Django-dependent checks used the built web image, read-only `/work` and `/app/tests`, ephemeral virtualenv, `PYTHONPATH=/app:/app/tests`, `PYTHONDONTWRITEBYTECODE=1`, `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`:

```sh
python -m venv --system-site-packages /tmp/analytics-env
/tmp/analytics-env/bin/pip install -q -r /work/analytics/requirements.txt
/tmp/analytics-env/bin/python -m pytest -q -c /app/pytest.ini -p no:cacheprovider /work/analytics/tests/test_segment_loader_integration.py /work/analytics/tests/test_verify_refresh.py /app/tests/test_customer_segments_command.py
/tmp/analytics-env/bin/python -m pytest -q -c /app/pytest.ini -p no:cacheprovider /work/analytics/tests/test_startup_credentials.py
# Separate disposable bootstrap server with private BOOTSTRAP_TEST_DSN:
python -m pytest -q -p no:cacheprovider /app/tests/test_db_bootstrap.py
```

Source overlays are absent from the served app. Test-only read-only mounts are separate; ML packages never enter the web image. Cleanup is held until browser/review completion; retain final image, preserve preexisting stopped `inf2006-ml-loader-db-1` and unrelated resources.

## Independent gate and remaining limits

Independent fresh-context Astra Medium review is complete in the rounds below. Freeze includes baseline-to-working-tree tracked changes and this new record; no untracked implementation may be omitted. Require stable finding IDs/severity/locations, own-run/version consistency, permissions/query behavior, Phase1–5 compatibility, evidence truthfulness, dead code, complexity and duplicated-test assessment. Repeated unresolved backend issue after Low remediation stops for user-selected escalation.

Hosted CI for the exact revision is unverified; no push to trigger it. Scoped tests/tools/runbook inspection found no existing supported Locust/load-smoke workload, so load remains unrun; no substitute framework/capacity claim. Direct manifest paths exist except `evidence/architecture.png`; existing project/team/report placeholders remain submission gaps. Unrelated frontend S-001/002/003/004/008/W-04 remain open. Immutable feature snapshots and optional saved-model inference remain deferred. Actual ECR/IAM/Secrets Manager/KMS/RDS/ALB/HTTPS/S3/WAF/CloudTrail/CloudWatch/SNS/ASG checks remain joint infrastructure gates, not proven by local readiness; use the [joint checklist](../AWS_INFRASTRUCTURE.md#joint-integration-checklist-after-phase-6).


### Independent review round 1 — frozen candidate

Review boundary: baseline `430e4c85eae7d770b7a0c7fbdbe6bada05d2604b` through all 17 tracked task changes plus this new review record (18 paths). No semantic rebase resolutions. The exact SHA-256 snapshot is held in the private task scratch `review-snapshot.json`; staged behavior must match it except later coordinator review/completion metadata. Git newline normalization is checked separately when staging; recorded SHA-256 values describe tested checkout/image bytes.

All backend/release checks above passed; final dynamic-focus browser observation is still pending and is not claimed passed at review dispatch. Reviewer must assess code/evidence now, and any subsequent behavioral change requires renewed review. No actionable finding has yet been reported or resolved by this dispatch.


### Round 1 outcome — MLR-001 open

Reviewer `/root/reviewer`, explicitly `gpt-6-astra` / `medium`, **Independent (fresh session)**, read-only. All 18 frozen hashes matched; independent focused PostgreSQL suite **111 passed in 12.57s**; diff whitespace check passed. Initial reviewer test invocation was blocked by constrained-language environment setup/unwritable sandbox temp, then native environment setup and approved escalated invocation succeeded. No approval rejection or source edit. Full-image/bootstrap/full-data/ML/browser receipts were reviewed, not independently rerun. No other actionable findings: eager lock boundary, run isolation, pruning retries, permissions/privacy/sample bounds and focused test scope passed review.

| ID | Severity | File/line | Required spec / evidence | Issue and correction | Fix / verification | Re-review |
|---|---|---|---|---|---|---|
| MLR-001 | P2 | `src/static/js/analytics.js:259–267` at round 1 | Existing analytics navigation/history contract; packaged HTMX `Ve`/`Kt` restores cloned DOM and emits load/historyRestore without afterSwap | afterSwap-only redraw omits Back/Forward chart restoration; cloned canvas has no bitmap and DOMContentLoaded does not fire again. Restore history/load chart drawing separately from actual-swap-only focus. Code-traced; live reproduction pending. | Assigned to frontend Luna Max; no backend fix required. Verify 7D → 30D → Back → Forward charts/data plus no startup focus theft. | Resolved in round 2; final Luna live history verification passed |

Final pre-review browser receipt (no source change): newer run unavailable with no old totals/recipe at desktop/mobile. Desktop 1280x720: initial BODY focus, 30D swap H2 top167.2/bottom213.4 vs header bottom100.6; mobile390x844 after smooth scroll settled1.2s: H2 top202.6/bottom259.8 vs header bottom194.4. Focus ring visible, correct range URL, no overflow. Loaded appearance was checked before the last JS-only focus adjustment with unchanged templates/CSS. History navigation was not checked then; MLR-001 remains open despite these passes.


### MLR-001 correction in progress

Luna added one `htmx:historyRestore` handler that calls the existing chart drawing function on the restored analytics panel and never calls focus/announcement. Actual swap-only focus and initial drawing are unchanged. No new frontend framework or duplicated behavior test was added. Node syntax, rebuilt-image and live Back/Forward verification are recorded when complete; no pass inferred merely from this code change. Backend source/tests remain unchanged from round 1.


MLR-001 static checks: `node --check src/static/js/analytics.js` and `git diff --check` passed. Rebuilt `db198bc8` image contains the corrected JS (hash above), health passed, full suite472 passed/8 opt-in skips in27.45s; the eight opt-in cases retain separate passing evidence. Original Luna browser session lost its available browser after cleanup, including one reset attempt; history retest not claimed from that session. A fresh explicitly assigned `gpt-5.6-luna` / `max` visual verifier `/root/history_verifier` is attempting the bounded history sequence; this is the same required model/tier, not a coordinator substitution.


### Independent review round 2 — frozen corrected candidate

Same reviewer tier and exact baseline; full18-path revised candidate (not only the four-line fix). Snapshot `review-snapshot-round2.json` in task scratch. MLR-001 correction is frontend-owned; backend bytes/tests are unchanged. Final image/check result above is current. Fresh-Luna actual history retest remains pending at dispatch; later receipt will be assessed as supplemental evidence without altering source.


### Round 2 outcome — code gate clear

Same independent fresh-context reviewer `/root/reviewer`, explicit Astra Medium, reviewed the complete revised 18-path candidate against `430e4c8`; all round 2 hashes matched. **MLR-001 resolved; no unresolved actionable findings.** The history callback redraws without focus; initial drawing and swap-only focus remain. Independent Node syntax and Git diff checks passed; round 1 111 passing PostgreSQL tests remain applicable because backend/test bytes are unchanged. No new correctness/security/dead-code/complexity/duplicated-test finding.

Live Back/Forward verification is still pending at this review outcome. This is code-review clearance, not a claim that the frontend execution gate passed. Final-image/ML/data results remain implementer-executed evidence. Hosted CI/load/AWS remain unverified. Coordinator holds completion/commit pending the actual browser result or an explicitly recorded capability limitation.


### Final live verification and gate clearance — 26 September 2026

Fresh visual verifier `/root/history_verifier`, explicitly `gpt-5.6-luna` / `max`, succeeded via CUA on final `db198bc83` image. Default rendered viewport 1259×711. Initial BODY/AXWebArea focus; 30D span 03 Dec 2025–01 Jan 2026, sales S$1,495,546.56, units 7,899. Click7D: span26 Dec 2025–01 Jan 2026, sales S$330,351.30, units1,712; both trend line and category bars visibly drawn. Click30D restored its matching URL/span/values and both charts. Browser Back restored7D, then Forward restored30D, with correct data and both charts visibly redrawn in screenshots. History navigation left BODY/AXWebArea focus. At exact390×844, 30D→7D HTMX focused the outlined heading visibly below the sticky header with correct values. Viewport reset afterward; no source/Git edits. These are Luna-executed checks, not reviewer/coordinator browser claims. Old-session browser access failure did not waive verification.

Independent reviewer acknowledged this receipt closes MLR-001's live boundary: **MLR-001 resolved; no remaining review blockers or actionable findings.** No further implementation review is required unless behavior changes. Backend own-run, permission, loader compatibility and release evidence gate is clear. Existing pure-ML/bootstrap/full-data receipts remain scoped as implementer-executed; reviewer independently ran111 focused tests and static checks.

Bounded S-006/M-04 display and F-04 focus issues are resolved. Hosted CI, load tooling/results, deployed AWS security/availability and incomplete submission artifacts remain separate open gates; unrelated frontend findings and immutable snapshots are not claimed complete. Final source corresponds to the six tested runtime/test hashes above, plus the final reviewed JS; Git LF normalization is validated during staging. The containing commit identifies this final reviewed source.


## Completion metadata and cleanup

The same independent reviewer inspected the six final metadata updates and found no claim error or new blocker; no redundant tests for documentation-only changes. Coordinator hash comparison found no runtime/test changes since round 2. All local Markdown link targets resolve. Manifest's architecture PNG is still absent and explicitly listed as a submission gap; YAML additions are quoted scalars inspected by coordinator/reviewer (no YAML parser was available).

Astra Low removed exactly the four Phase 6 containers (project web/database, analytics tool container and separate bootstrap server), task network, task-created `src/staticfiles` and `C:/Users/limch/AppData/Local/Temp/inf2006-phase6-20260925`. Resolved path containment/no-link checks preceded native PowerShell deletion. The temporary hash manifests, private configuration and customer exports were ephemeral and are now removed; the aggregate identities/results in this record remain. All 26 pre-existing volumes, stopped `inf2006-ml-loader-db-1` and its network were preserved. Final image `sha256:db198bc83e76aa59e4070568c5d39685da7471d95cc5086c62af888f133c2907` and Phase 5 image remain available locally; no image pruning or unrelated cleanup occurred. Task browser viewport overrides were reset and temporary tabs closed.

No Terraform edits, push, ECR publication or deployment occurred. The joint AWS checklist remains the next infrastructure handoff, not a claim that AWS is verified.


Coordinator staged verification: exactly18 reviewed task paths, no unrelated/customer-export/credential/generated files. All six runtime/test raw hashes match round2; staged blobs equal working files after CRLF→LF normalization. Staged whitespace check passed; added-text scans found zero AWS access keys, private keys or credential-bearing PostgreSQL URLs. Completion/cleanup metadata is the only post-review change, with no behavior change. No unstaged task source remained before commit.
