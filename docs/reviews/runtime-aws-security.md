# Runtime and AWS security preparation

Date: 25 September 2026. Status: checkpoints A, B and C independently cleared; bounded local application preparation complete. Deployed AWS readiness remains open.

## Baseline and ownership

Branch `erfan/analytics`; clean starting HEAD `4b3a37c19b38b85ecf5adf7fd2b6344a708ef6f9`. Fresh `git fetch origin` succeeded; `origin/erfan/analytics` remains `89019b4bc10a22d7ce8d40769582652bd35030e7`, six local commits and zero incoming commits. No rebase, backup reference or commit mapping was needed. `git status` reports no active Git operation; the pre-existing `REBASE_HEAD` file is preserved.

Phase 4 implementation `3c75f4d` and its completed ML contract remain intact. HEAD adds only tracker/review verification metadata. Prior 69-test, pinned-runtime and 18-customer integration results in [Phase 4 review](ml-batch-handoff.md) are historical, not newly executed here.

Coordinator owns Git, this record, finding dispositions and tracker. Implementer `/root/runtime_implementer`: explicitly assigned `gpt-6-astra`, reasoning `low`; no staging, commit or push permission. Independent reviewer will be separately assigned `gpt-6-astra`, reasoning `medium`, read-only, with fresh bounded context. No substitute model is authorised.

## Scope and interface discovery

Prepare production TLS, bootstrap privilege safety, one role-based Secrets Manager startup interface, strict host/proxy/liveness boundaries, image exclusions and a concrete infrastructure handoff. Preserve explicit local mode, shared PostgreSQL sessions/carts/signing configuration, the completed explicit ML batch workflow and ML/web dependency isolation.

No tracked Terraform files or existing secret-delivery implementation were found in this checkout. Existing interfaces include the vendored RDS CA bundle, Django production verify-full TLS, Gunicorn on port 8000, database-independent `/health/`, and local Compose's one-off migration service. The handoff must define configuration/schema without inventing deployed secret identifiers, domains, permissions or endpoints.

Checkpoints: A database TLS and bootstrap safety; B secrets/configuration and application startup; C packaging and deployment handoff. Freeze each coherent implementation snapshot for independent review before committing. Relevant original findings: READY-002/004/005/007/009 and the upstream bootstrap follow-up in [backend AWS readiness](backend-aws-readiness.md). READY-005/009 already have bounded Phase 0 corrections; do not duplicate them or imply AWS verification.

Terraform edits, provisioning, real secret retrieval, shared/AWS database bootstrap, push, ML algorithm changes, lifecycle UI and immutable snapshots are excluded. Lifecycle/lifetime copy and accepted-dataset reevaluation remain deferred. WAF, SNS, CloudTrail, Secrets Manager IAM, ALB and RDS behavior require deployed evidence.

## Review rounds and verification

The following chronological entries record frozen paths, hashes, commands, actual results, findings and unrun checks per checkpoint. At initialization no tests or image build had been executed; later entries supersede that initial state.

## Checkpoint A — frozen round 1

Independent (fresh session) reviewer `/root/runtime_reviewer`, explicitly assigned `gpt-6-astra` / `medium`, read-only. Boundary: baseline `4b3a37c19b38b85ecf5adf7fd2b6344a708ef6f9` to the 14 working-tree paths below, including three new files. No upstream semantic resolutions. Coordinator metadata files are additional task changes, not implementation. B/C secrets, health/proxy and packaging work is intentionally pending.

A implements one PostgreSQL connection policy across Django, analytics and bootstrap, plus separate migration-owner/runtime roles. PostgreSQL 17 requires retained ADMIN-only master-to-managed-role membership for non-superuser reruns; inherited and SET ROLE access are disabled after temporary creation, and unexpected broader memberships are refused. Existing unsafe roles/ownership are refused before password changes.

### Newly executed A verification (implementer)

Host `.venv` Python 3.12.10, psycopg 3.3.5. Dedicated PostgreSQL 17:

```powershell
docker run -d --name inf2006-runtime-a-db -e POSTGRES_PASSWORD=<disposable-only> -p 127.0.0.1:55439:5432 postgres:17-bookworm@sha256:051f7b7b3abdd564d5d1bd1e8c4b9c1b6e77087d1dd22020ede611c096a272e0
$env:PYTHONPATH='src'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:BOOTSTRAP_TEST_DSN='<disposable-admin-DSN>'
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider -o addopts='' --confcutdir=tests tests/test_database_policy.py tests/test_db_bootstrap.py
```

**13 passed in 7.10s.** Placeholders above redact task-only fixture configuration; no real secret or shared database was used. Unique test roles/databases are removed by fixture cleanup. Actual application migrations ran as schema owner, runtime auth/Product DML exercised triggers, and `check_database` succeeded. DDL, TEMP and SET ROLE were denied. Membership, administrative attributes, schema CREATE and foreign database ownership refusal paths preserve passwords. The thirteenth check independently proves CLI error redaction using a synthetic sentinel.

Initial self-test: 10 passed / 2 failed. PostgreSQL GRANT SET implicitly enabled inheritance; fixed with explicit INHERIT FALSE and final SET FALSE. A fixture reconnect omitted its disposable password; corrected. These were implementer self-test failures before independent review, not review finding resets.

Existing test environment: dedicated `runtime_test_owner` database and non-superuser CREATEDB `runtime_test_runner` within the same disposable container, `DJANGO_ENV=local`, synthetic signing key, allowed hosts `localhost,127.0.0.1,testserver`, host `127.0.0.1`, port `55439`, CA path the absolute vendored bundle. With this task-only environment:

```powershell
.venv/Scripts/python.exe -m pytest -q -c src/pytest.ini -p no:cacheprovider tests/test_settings.py tests/test_health.py
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider -o addopts='' --confcutdir=analytics/tests analytics/tests/test_segment_customers.py
git diff --check
```

Settings/health: **19 passed in 3.49s**, five expected missing-built-staticfiles warnings. Pure ML: **16 passed in 16.55s**. Whitespace check passed (Git line-ending notices only). Resource retained temporarily for later task verification; no pre-existing container, database, volume or dataset changed.

Unrun at this checkpoint: final image build, pinned Python 3.13 execution, actual TLS handshake/RDS/ALB, hosted CI, full suite, Terraform and all AWS permissions/deployment. Local policy checks are not deployed evidence.

### A frozen SHA-256 values

| Path | Working-file SHA-256 |
|---|---|
| src/config/settings.py | e06881511bdd2fa8c09abc03f4590359ec02fd90859f708fffaf3c2ecf128753 |
| src/config/database.py | 6cc3392aaa2a20625f094bded19bf36c26852bbcf80b46fb1d43d8359a9f27e1 |
| src/tools/db_bootstrap.py | d5a94a693bd9209134cbd7753ea939d5507d64c7afc0fa192c32faeeddeeb9d3 |
| analytics/segment_customers.py | ad2bacae39729a7a58b92eb434290a63fd62bd90548953550290cbeeabd6c4cd |
| analytics/verify_refresh.py | 7988ed02ed7a5e9b237a5ed013dd41a6ec654a50f69d212650a1ccf5e1d84bf0 |
| analytics/README.md | 8f13fd80801024ed445249cc2243f73c41b5fb3c2cbdc68790fb3e533c64daba |
| tests/test_settings.py | 848947c75a929b8d616f0933ba08c3b636ba5c2e58d0c7c112b6da9a20f1e32e |
| tests/test_database_policy.py | 2869dc92ab301910c590da9519ab090b66fc1625bde99f7cdcee51df75a29ff3 |
| tests/test_db_bootstrap.py | 660a3cd4e35e3f56d42eced7d18fa6cdf97ef512850365a83ec62bafc1c72e85 |
| docs/AWS_INFRASTRUCTURE.md | 9f906c9944b5a2583571e006983cb8022f65ed045b750afa60bf457e82e1b9ed |
| docs/SECURITY.md | 94be8dd9ca505b962744c24afe2e2adae11e0d8838dad74957493bf39138a84c |
| docs/ARCHITECTURE.md | 3220417d3fb9a05fa672a9d04eca0502c7ad39b94cf017974c517a3732c3a287 |
| docs/plans/deploy-readiness.md | a601ee63a2394b99f3f57d90576d8f0721ab8b99838ca7cc80415c5afef2eab1 |
| src/README.md | 9da0d7ca186df9066a94daeee60e962e323042526ecbd742affaaa101df426ea |

### A round 1 — findings; gate open

Independent (fresh session) `/root/runtime_reviewer`, `gpt-6-astra` / `medium`, reviewed the complete frozen A diff and direct consumers. Five actionable findings:

| ID | Severity | File/line | Required spec / evidence | Issue and expected correction | Low fix / verification | Re-review outcome |
|---|---|---|---|---|---|---|
| RAS-001 | P1 | src/config/database.py:35 | Production certificate/hostname verification; libpq ignores sslmode on Unix sockets | Leading `@` abstract-socket host passes production policy. Reject it in environment and DSN paths; one focused regression. | Pending | Pending |
| RAS-002 | P2 | src/tools/db_bootstrap.py:28-37,114 | Runtime cannot create temporary objects; refuse unsafe existing state before password changes | Explicit runtime TEMP grant survives PUBLIC revoke. Refuse explicit runtime TEMP before mutation, distinguishing normal PUBLIC defaults. Verify unchanged passwords. | Pending | Pending |
| RAS-003 | P2 | src/tools/db_bootstrap.py:28-52,120-121 | Runtime future tables receive only intended DML privileges | Existing owner global/public default ACL can retain TRUNCATE or other excessive runtime/PUBLIC grants. Inspect relevant default ACLs and refuse before mutation; one future-table regression. | Pending | Pending |
| RAS-004 | P2 | tests/test_database_policy.py:6; tests/test_db_bootstrap.py:41-45 | Preserve supported Compose/CI layout | Repository-relative CA/manage.py paths become invalid `/app/src/...` under `/app/tests` mount. Derive paths from imported application/configuration; verify container layout. | Pending | Pending |
| RAS-005 | P3 | analytics/README.md:246,285 | Preserve unrelated documentation | Two historical ranges became mojibake. Restore original `31.67–39.75%` and `Phases 1–2`. | Pending | Pending |

Reviewer independently reproduced abstract-socket policy acceptance without connecting; policy tests **7 passed in 0.58s** with `--capture=sys`, bytecode/cache disabled. Ordinary pytest capture initially failed due to sandbox temporary-directory restrictions; memory capture succeeded. `git diff --check` passed. Reviewer did not run PostgreSQL/bootstrap mutations, real TLS, container/full-suite/AWS verification. PostgreSQL references: [libpq connection parameters](https://www.postgresql.org/docs/17/libpq-connect.html), [default privilege semantics](https://www.postgresql.org/docs/17/sql-alterdefaultprivileges.html).

All five findings go to the original Low implementer. Stable IDs are retained. Any repeated unresolved finding after this fix attempt stops Phase 5 for user-selected implementation escalation under DEVELOPMENT.md; no automatic upgrade or further Low retry.

### A Low remediation — frozen round 2

Original Astra Low implementer corrected RAS-001–005 once. Abstract-socket environment/DSN input is rejected centrally. Explicit runtime TEMP ACLs and excessive migration-owner global/public default ACLs are refused before password mutation. Tests locate CA/manage.py from the imported application module, supporting repository and `/app` layouts. Original Unicode ranges restored; AWS contract describes TEMP/default ACL refusals.

New verification: host focused policy/bootstrap **16 passed in 6.56s**; pinned Python **3.13.15** in supported `/app` + `/app/tests` layout: **16 passed in 7.02s**, including real migrations/runtime DML and non-superuser PostgreSQL 17 bootstrap. Same task database container retained. The focused default-privilege regression proves unsafe future-table access, refusal with passwords unchanged, then absence of that access after the fixture operator removes the unsafe defaults. Exact original Unicode codepoints verified; `git diff --check` passed. These are local tests; no AWS/real TLS/full-suite claim.

Complete 14-path A boundary refrozen below. Coordinator-owned records remain outside implementation behavior. Same independent reviewer must assess the whole revised diff and each stable finding; repeated unresolved defect triggers mandatory stop.

| Path | Revised working-file SHA-256 |
|---|---|
| src/config/settings.py | e06881511bdd2fa8c09abc03f4590359ec02fd90859f708fffaf3c2ecf128753 |
| src/config/database.py | 2eb4d94f15a36ae8c4f461f2afca8e4881ae16f5bbe71b53dd6e17ce9144eb77 |
| src/tools/db_bootstrap.py | 4fe0bfccc0ed3e07ab2efe4574dd6e47a67a82c4748dcfa10a90b2177bdc8218 |
| analytics/segment_customers.py | ad2bacae39729a7a58b92eb434290a63fd62bd90548953550290cbeeabd6c4cd |
| analytics/verify_refresh.py | 7988ed02ed7a5e9b237a5ed013dd41a6ec654a50f69d212650a1ccf5e1d84bf0 |
| analytics/README.md | f1fb62c190ab590c3a5a41131593508ab6adbace5575b778bc6b4f7e7d5cea04 |
| tests/test_settings.py | 848947c75a929b8d616f0933ba08c3b636ba5c2e58d0c7c112b6da9a20f1e32e |
| tests/test_database_policy.py | 5859b3fa2cb16a28b631d18d1c6965f3dcdf4e8037eaf0b903a1199f26dc763e |
| tests/test_db_bootstrap.py | 5f5c268b22b00aa72bab0517ad53d7d8d74a49a110cec4896e37d52e0657e954 |
| docs/AWS_INFRASTRUCTURE.md | c1c145046c22cf77062cfbc72fe539cad8da4be03321132371fab43a6efe36bd |
| docs/SECURITY.md | 94be8dd9ca505b962744c24afe2e2adae11e0d8838dad74957493bf39138a84c |
| docs/ARCHITECTURE.md | 3220417d3fb9a05fa672a9d04eca0502c7ad39b94cf017974c517a3732c3a287 |
| docs/plans/deploy-readiness.md | a601ee63a2394b99f3f57d90576d8f0721ab8b99838ca7cc80415c5afef2eab1 |
| src/README.md | 9da0d7ca186df9066a94daeee60e962e323042526ecbd742affaaa101df426ea |

Pinned-layout command (existing dependency image, source mounted read-only; not a final image build):

```powershell
docker run --rm --network container:inf2006-runtime-a-db --mount type=bind,source=<workspace>/src,target=/app,readonly --mount type=bind,source=<workspace>/tests,target=/app/tests,readonly --workdir /app -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/app -e BOOTSTRAP_TEST_DSN=<task-admin-DSN-on-localhost-5432> sha256:8f2604a3255a264d915f08d73b23d968a23b470161543c4d077003a52686246c python -c 'import sys,pytest; print(sys.version); sys.exit(pytest.main(["-q","-c","/dev/null","-p","no:cacheprovider","--confcutdir=/app/tests","/app/tests/test_database_policy.py","/app/tests/test_db_bootstrap.py"]))'
```

The executed tag `inf2006-foundation-app` was resolved to the immutable image ID shown above. It supplies Python/dependencies only; frozen working files supply the tested implementation. No temporary script was used. Task-only DSN omitted from the record; source/test mounts are read-only. Container removed automatically with `--rm`.

### A round 2 — RAS-001–005 resolved; new RAS-006

Same Independent (fresh session) Astra Medium reviewer checked the full revised boundary and all 14 hashes. RAS-001–005 are **resolved**, with no repeated unresolved defect. Independent nonmutating subset: **9 passed, 7 deselected in 0.51s**; Unicode and `git diff --check` passed. PostgreSQL/container results remain implementer-reported; no independent database mutations or AWS execution.

| ID | Severity | File/line | Required spec / evidence | Issue and expected correction | Low fix / verification | Re-review outcome |
|---|---|---|---|---|---|---|
| RAS-006 | P2 | src/tools/db_bootstrap.py:50-53,135 | Existing runtime sequence access limited to USAGE/SELECT | Existing sequences are excluded from object ACL preflight. UPDATE survives additive grants and permits setval. Refuse effective UPDATE on public sequences before password changes; one refusal/password-preservation regression. | Pending | Pending |

RAS-006 concerns existing sequence ACLs, distinct from resolved RAS-003 future-object default ACLs. [PostgreSQL setval privilege requirement](https://www.postgresql.org/docs/17/functions-sequence.html). Original Low receives this new finding for one remediation attempt, followed by complete-diff re-review under the same stop rule.

### A RAS-006 Low remediation — frozen round 3

Effective UPDATE on existing public sequences now fails preflight before password changes; CASE on relkind ensures PostgreSQL only calls the sequence privilege function for sequences. One regression grants UPDATE through PUBLIC and verifies refusal with both passwords unchanged.

Same focused commands as round 2: host **17 passed in 6.43s**; Python 3.13.15 supported container layout **17 passed in 7.78s**. Initial implementer self-check 15 passed / 2 failed because SQL evaluation called the function on non-sequences despite a WHERE filter; CASE corrected evaluation before this freeze. `git diff --check` passed. No resource/B/C changes.

Only two working hashes changed; all other round-2 hashes remain applicable:

| Path | Round-3 SHA-256 |
|---|---|
| src/tools/db_bootstrap.py | 209ca94d942f029d062934119126a501e2861d086f85ac0d9a9d7db4b798998e |
| tests/test_db_bootstrap.py | 29e5e7e63793502887d51775e97c065004545d6f303131a486d73b370cc1b41a |

### A round 3 — independent gate clear

Same Independent (fresh session) reviewer `/root/runtime_reviewer`, `gpt-6-astra` / `medium`: **RAS-001–006 resolved, no unresolved actionable findings or new findings**. Full A boundary reassessed, all 14 frozen hashes matched. Independent nonmutating subset **9 passed, 8 deselected in 0.65s**; `git diff --check` passed. Gate clearance covers A only; B/C and deployed verification remain open. PostgreSQL and Python 3.13 container checks above are implementer-executed, not independently rerun. No repeated unresolved finding triggered escalation.

### A final checks and local commit preparation

Pinned Python 3.13.15 Django checks passed: `check` reported no issues (0 silenced); `makemigrations --check --dry-run` reported no changes. Both commands used:

```powershell
docker run --rm --network container:inf2006-runtime-a-db --mount type=bind,source=<workspace>/src,target=/app,readonly --workdir /app -e PYTHONDONTWRITEBYTECODE=1 -e DJANGO_ENV=local -e DJANGO_SECRET_KEY=<synthetic-fixture-key> -e DJANGO_ALLOWED_HOSTS=localhost -e POSTGRES_DB=runtime_test_owner -e POSTGRES_USER=runtime_test_runner -e POSTGRES_PASSWORD=<task-fixture-password> -e POSTGRES_HOST=127.0.0.1 -e POSTGRES_PORT=5432 sha256:8f2604a3255a264d915f08d73b23d968a23b470161543c4d077003a52686246c python manage.py <check-or-makemigrations-arguments>
```

No implementation changed after round 3. Coordinator completion metadata updates only this record, tracker and original readiness dispositions. A local checkpoint commit is authorised after scoped staged-content inspection. B/C remain pending and nothing is pushed or deployed.

Coordinator staged verification: exactly 18 task paths; all 14 reviewed implementation/contract/test hashes matched. Staged bytes match working bytes after newline normalization; all decode as UTF-8. Added-text AWS-key/private-key pattern scan found no matches; no generated artifacts or credential files staged. This scoped scan is not an exhaustive secret-detection claim. `git diff --cached --check` passed and no unstaged changes remained. Final inspection changes no implementation.

## Checkpoint B — startup configuration and ALB boundary

A local commit: `e4cc1d6b35ea3243bab84d98d61738f16ba8b31a`, verified descriptive body and clean post-commit tree (seven commits ahead of fetched origin). B baseline is this commit. No push/deployment.

Astra Low continues with one role-based Secrets Manager startup loader, a documented strict secret schema without real identifiers, local environment compatibility, sanitised failures, narrow configured probe Host/path/method handling and minimal release identity in existing logging. Runtime and migration use separately permissioned secret values with the same ordinary application schema; only the one-off bootstrap path may receive bootstrap credentials. IAM must keep migration/bootstrap secrets unavailable to the web role. No competing profile framework or application-side rotation machinery is required.

B implementation/review pending. C image/context verification and concrete final infrastructure handoff remain pending.

### B frozen round 1

Baseline `e4cc1d6b35ea3243bab84d98d61738f16ba8b31a`; 20 implementation/test/contract paths below, including three new files. A behavior remains in scope for regression review. Coordinator record changes are metadata. No C packaging changes yet.

Implemented one cached startup secret loader with strict caller schemas, bounded role-based retrieval, sanitised errors, no production plaintext fallback and no AWS imports/calls in local mode. Production standalone DSNs are explicitly refused to avoid a second credential source; local DSNs remain supported. Added exact configured private-IP:8000 GET/HEAD health exception, strict normal Host validation and release startup JSON event. Only required SDK pins added; existing dependency pins unchanged.

Implementer verification: host **69 passed / 1 failed** (pre-existing logging assertion expects Unix separators; Windows formatter emits backslash). Initial host run 59 passed / 10 failed because local staticfiles were absent; existing collect_static.py generated task-only ignored staticfiles before rerun. Supported Linux Python 3.13.15: **70 passed in 17.25s**, `pip check` clean. Initial dependency-image run 68 passed / 2 failed because that older image lacked the CA-path environment default; explicitly setting the documented CA path produced the passing rerun. Final C image build remains pending.

Container `inf2006-runtime-b-check`, dependency image `sha256:8f2604a3255a264d915f08d73b23d968a23b470161543c4d077003a52686246c`, user 0 for temporary dependency installation, network `container:inf2006-runtime-a-db`. Read-only mounts `<workspace>/src:/app`, `<workspace>/tests:/app/tests`, `<workspace>/analytics:/work/analytics`; workdir `/app`. Environment: `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=/app`, `DJANGO_ENV=local`, synthetic signing key, allowed hosts `localhost,127.0.0.1,testserver`, DB `runtime_test_owner`, user `runtime_test_runner`, task-only password, host `127.0.0.1`, port `5432`, CA `/app/certs/rds-global-bundle.pem`, task-only admin DSN for bootstrap fixtures. No real AWS credentials/secret values used.

Inside that disposable container:

```sh
python -m venv --system-site-packages /tmp/checks
/tmp/checks/bin/python -m pip install -q -r /app/requirements.txt -r /work/analytics/requirements.txt
/tmp/checks/bin/python -m pip check
/tmp/checks/bin/python -m pytest -q -c /app/pytest.ini -p no:cacheprovider /app/tests/test_secrets.py /app/tests/test_settings.py /app/tests/test_health.py /app/tests/test_request_logging.py /app/tests/test_database_policy.py /app/tests/test_db_bootstrap.py /work/analytics/tests/test_startup_credentials.py
```

Pinned Django `check`: no issues; `makemigrations --check --dry-run`: no changes (4.70s combined), same A command shape using current source and local fixture environment. `git diff --check` passed. Dependency test container is stopped and retained temporarily; only task-created staticfiles/resource cleanup pending. No final image, hosted CI, real TLS handshake, AWS or full-suite results claimed.

| Path | B working-file SHA-256 |
|---|---|
| analytics/README.md | fcb6f8833585bdc9a5f746764aa233b6fbc0ff910c061dfa6334fb5c52d7ad3d |
| analytics/requirements.txt | 0e1d4279256bd6e6b264f9301f90a24773ba81938f177f06c9d9b8f4b7bb4f38 |
| analytics/segment_customers.py | 39b2ceed50258ecdea9510807db274c34d5a141a86e73744e3e6cf95438007b5 |
| analytics/verify_refresh.py | 1d4d52f0a143414021780700b025808faaf58a05dff1883087c664458b422be1 |
| analytics/tests/test_startup_credentials.py | 77459aa1916e34bb7f4aee6bc6293c90f7a440ffbaf2ac34d555d29466d4d103 |
| docs/API.md | 447a1d6d11574afe6f538b00363e13d42d82245833e95548d8d5c6b7f5d3f8a2 |
| docs/AWS_INFRASTRUCTURE.md | cbee147f69a4d56b3c2f6b61f3a34e4229e48d94e9bff153a56f77c258a8429f |
| docs/SECURITY.md | 7eb578e152dd885ea833365cd29ba0ef2f3c8384511afe8346d6d8bf303bb7ab |
| src/README.md | 431f2af27cf276dce0de333ef47019b6c143b7b7e2ac5a4f4fec76b3ab236f57 |
| src/config/middleware.py | e13e7b72c5914f648fe1c8b9c5a8f5a2809d61115e8277081e8295350d3ff7eb |
| src/config/settings.py | 19e1c02207b8b38c7204ae18f88d1a8f0fc1cac0bc8c410355a7d2fe48f81d73 |
| src/config/views.py | a4323dc492d0ea2d4d07f1bab73b138610d04fa951c7d58fdfe4d532d2c4ddf9 |
| src/config/wsgi.py | e91aaddfee2f8663f5253e8b8341b3fcd4b81bdc10b89fd43f3ab2f7599d906e |
| src/config/secrets.py | 91cf81162a5ad1f99de21e37e70724f517fcf365c9b279eadd3432b1598c1491 |
| src/requirements.in | 0ce6edc1799e6eaa6d58a3c6b58e25bdbb7f246a833f3132f1d2717abe1e2946 |
| src/requirements.txt | c96b6826225abc5329195f9558e7769ab304f0ac3f45c67aba20bc6c1d867753 |
| src/tools/db_bootstrap.py | f3f244efcfa8af7295f74051204adbd97d84766b64311796e71b09c8c0bedde9 |
| tests/test_health.py | 7fe3621f172ecfd20b0495a8a140627a9860af3cddd378b6ac4c08a6d3ce2862 |
| tests/test_settings.py | b657d0bae6f42eb35d62de500c1f8cb5cfeba048b12731c6940b766b1cf1388a |
| tests/test_secrets.py | 6f0838b5271ad28b4fc91dd47af3f9d8ede9558f3a926e9137bf9433a0e46dab |

B host-only failure identifier: `tests/test_request_logging.py::test_a_controlled_failure_can_be_correlated_without_leaking_its_message` expects `cart/views.py`; the unchanged formatter produces Windows path separators. It passed in the supported Linux run. Analytics caller tests load both standalone modules by importlib path under `/work/analytics`; `PYTHONPATH=/app` only. Bootstrap subprocesses use the same combined pinned environment. No unrelated portability fix was introduced.

### B round 1 — RAS-007; gate open

Independent (fresh session) Astra Medium reviewer inspected all 20 frozen paths/direct consumers, verified every hash and retained RAS-001–006 as resolved. Fake-secret/policy/standalone checks independently **19 passed in 2.36s**; `git diff --check` passed. No database mutation, AWS call, real TLS or final-image execution.

| ID | Severity | File/line | Required spec / evidence | Issue and expected correction | Low fix / verification | Re-review outcome |
|---|---|---|---|---|---|---|
| RAS-007 | P2 | src/config/middleware.py:32; settings middleware order | SECURITY request-ID correlation for sanitised security failures | First middleware rejects Host before existing request logger assigns ID. Reviewer reproduced 400 with no response X-Request-ID and null security-event ID; prior order retains both. Let existing logging wrap normal Host validation, retain narrow DB-independent health exception, add one correlation regression. | Pending | Pending |

Low receives RAS-007 for one remediation attempt. Same finding unresolved after re-review triggers the mandatory manual-escalation stop.

### B RAS-007 Low remediation — frozen round 2

Middleware order now keeps DatabaseUnavailable outermost, then existing RequestLogging, then HealthProbe and Security. Existing exception recording/503 handling remains intact; request IDs exist before normal Host rejection. The probe remains before redirect and inside DB-independent logging. One focused regression asserts rejected-Host response, request event and sanitised DisallowedHost event share the supplied valid request ID with HTTPS redirect enabled. AWS contract wording changed from first to early middleware.

`docker start -a inf2006-runtime-b-check` reran the documented pinned dependency setup and current-source suite: `pip check` clean; **71 passed in 17.39s**. Includes existing database-outage/exception logging tests, health/proxy tests and A/startup regressions. `git diff --check` passed. No new resources or C changes.

B boundary now has 21 implementation/test/contract files. Only these hashes changed or were added; other B round-1 hashes remain applicable:

| Path | B round-2 SHA-256 |
|---|---|
| src/config/settings.py | 23ce81ec448aafebf8dc333ecded9207f1b49c8c55e82c90e8123d5cd106d4c0 |
| tests/test_request_logging.py | 71edec6b7fc97f222e33cae46337f3b8b57f288b3fae249bef811853ede58af9 |
| docs/AWS_INFRASTRUCTURE.md | ab0c03012798c86a9e274aa44cd71f7c60c25c1e169b074980cf4c138394687e |

### B round 2 — independent gate clear

Same Independent (fresh session) Astra Medium reviewer: **RAS-007 resolved; no unresolved actionable findings or new findings**. All 21 frozen hashes matched and complete B boundary reassessed. Request logging wraps Host/security validation; database exception ordering and DB-independent probe remain intact. RAS-001–006 remain closed.

Independent rejected-Host HTTP/security-event correlation reproduced successfully with HTTPS redirect enabled; two focused health/proxy tests passed. The logging pytest case could not initialize its database fixture without configured DB access, so the reviewer used a direct nonmutating reproduction instead. `git diff --check` passed. Implementer's 71-test Linux result was not independently rerun; no AWS, database mutation, actual TLS or final-image claim.

B gate clear only; C packaging/final-image and deployed verification remain open. Coordinator updates only completion metadata before scoped staging and local commit.

B coordinator staged verification: exactly 24 task paths; all 21 frozen implementation/test/contract hashes match. Staged content matches working text after newline normalization, decodes as UTF-8, and contains no AWS-key/private-key pattern matches in additions. No generated/static/credential files staged; no unstaged tracked changes. `git diff --cached --check` passed. Scoped scan is not exhaustive secret detection. Only coordinator metadata changed after independent clearance.

## Checkpoint C — packaging and final handoff

B local commit: `4f77fdd45e6d9c47734deefaa18cc7af6384f056`, descriptive body verified and clean post-commit tree (eight ahead of fetched origin). C baseline is this commit. No push/deployment.

Astra Low now owns Docker/Git build exclusions, disposable sentinel context verification, final web image build/inspection, bounded local TLS handshake checks, affected backend/analytics regressions and the final canonical infrastructure handoff. Coordinator retains review/tracker/Git ownership. All test resources are task-created; cleanup must preserve unrelated resources, data and volumes. Actual AWS/IAM/ALB/RDS verification remains excluded and open.

### C frozen round 1

Baseline `4f77fdd45e6d9c47734deefaa18cc7af6384f056`; seven files below. Packaging changes exclude infrastructure, nested sensitive state/plans/tfvars, local secrets/private keys, caches and virtual environments. Git keeps safe examples/provider lockfiles. New manual helper `tests/verify_runtime_image.py` durably defines the 16 harmless sentinels, image assertions and fake-secret/local TLS procedure; executable reproduction is in `tests/README.md`. Terraform remains untouched.

### Newly executed final-image verification (implementer)

- Sentinel build from a disposable copy of tracked `src/` only: all 16 markers absent from actual image filesystem; safe `.env.example` and exact vendored CA hash retained; UID 10001; numpy/pandas/sklearn/scipy absent.
- Clean `docker build -t inf2006-runtime-final src` succeeded. Image metadata: `USER 10001:10001`, `8000/tcp`, unchanged Gunicorn CMD. Audit helper passed against clean image too.
- Final image local ID: `sha256:d28a64e0ad38f48ce3eaf14e5569922a08938e8b632f1fc3f5003bb6db3edf8c`. `docker image inspect inf2006-runtime-final --format '{{.Id}} {{json .RepoDigests}} {{json .RepoTags}}'` returned that ID, `["inf2006-runtime-final@sha256:d28a64e0ad38f48ce3eaf14e5569922a08938e8b632f1fc3f5003bb6db3edf8c"]`, and `["inf2006-runtime-final:latest"]`. These are local descriptors, not ECR publication or a verified registry digest.
- Production-policy TLS with fake secret retrieval against isolated PostgreSQL 17: successful trusted certificate handshake, rejected wrong hostname and rejected unrelated CA. Before review, coordinator requested tightening negative evidence from any OperationalError to the specific libpq hostname/trust reasons. Revised helper passed all three in **2.30s**, suppressing raw errors. Private test key stayed inside its temporary server container; only public certificate copied out. No real AWS retrieval or TLS verification disablement.
- Final-image runtime checks without source overlay (tests mounted only): **69 passed in 8.71s**. This exercises actual packaged code/dependencies/default CA configuration.
- Affected analytics/batch/loader/reconciliation checks in isolated analytics environment atop final image: **71 passed in 5.20s**, `pip check` clean. Initial run 69 passed / 2 failed because `/work/src` recipe-fingerprint checkout input was not mounted; adding the documented read-only checkout path fixed the runner. No application correction was needed.
- Default Gunicorn CMD started in task container `inf2006-runtime-c-web` using synthetic local fixture settings; live `/health/` returned 200/no-store, UID 10001 confirmed, two sanitised worker startup release events observed.
- Packaged-source comparison: **119 runtime/source files byte-identical** to working files; only `src/README.md` differs because final handoff documentation followed image build. No runtime differences; no rebuild solely to embed its own image identity.
- `git check-ignore --no-index` matched sensitive tfvars/state/plans and did not match Terraform source, provider lock or safe example paths. `git diff --check` passed.

Durable commands use fresh scratch paths; actual scratch was `C:/Users/limch/AppData/Local/Temp/inf2006-runtime-c-_vkoenbd`. Task containers/images/scratch/staticfiles are retained only until review/cleanup; pre-existing `inf2006-ml-loader-db-1` and its data/volumes must remain untouched. Final image will be retained for handoff. No full-suite, hosted CI, load, ALB/RDS, real Secrets Manager/IAM, WAF/SNS/CloudTrail, ECR push or deployment result is claimed.

| Path | C frozen SHA-256 |
|---|---|
| .gitignore | 28af9e2f45bd43e9e52cddbbe1975dbb07c615b1fce0bdcd991a69a64157d375 |
| src/.dockerignore | fc0b7cec89e8ecfba8bfb8982f855839725edc1bb85414d42b122029fe8e39b8 |
| tests/verify_runtime_image.py | f7e73d67a514ef6181ef9480d3e2839a2e1e62abef769b36e8455d7c16415c97 |
| tests/README.md | 3a7ae5aba9c91cc81f64341364b3355c900d66011cb6b83940f9b6e7cdc8b75a |
| docs/AWS_INFRASTRUCTURE.md | bd8311c8f992b8fdd97d44d6c406f733e658e5b2fdeff7aabb573e7242765371 |
| docs/plans/deploy-readiness.md | 35f657fdd72a8800cdb4452c07687609f8ed9ace9d5be474c3835abb156a88bb |
| src/README.md | efbd8c29da3de42073854190743a870567186b9c3926cb14c02be91eb0619aa9 |

C exact test selections (fixture environment as in B; task-only values are not real secrets):

```sh
# Final image, only tests mounted read-only at /app/tests; network container:inf2006-runtime-a-db.
# PYTHONPATH=/app; local DB runtime_test_owner/runtime_test_runner, localhost:5432.
python -m pytest -q -p no:cacheprovider /app/tests/test_secrets.py /app/tests/test_settings.py /app/tests/test_health.py /app/tests/test_request_logging.py /app/tests/test_database_policy.py /app/tests/test_db_bootstrap.py
# Analytics container based on final image, tests:/app/tests, analytics:/work/analytics,
# src:/work/src all read-only; PYTHONPATH=/app:/app/tests; OMP_NUM_THREADS=1, OPENBLAS_NUM_THREADS=1.
python -m venv --system-site-packages /tmp/checks
/tmp/checks/bin/python -m pip install -q -r /work/analytics/requirements.txt
/tmp/checks/bin/python -m pip check
/tmp/checks/bin/python -m pytest -q -c /app/pytest.ini -p no:cacheprovider /work/analytics/tests/test_segment_customers.py /work/analytics/tests/test_segment_loader_integration.py /work/analytics/tests/test_verify_refresh.py /work/analytics/tests/test_startup_credentials.py /app/tests/test_customer_segments_command.py
```

Runtime used `docker run --rm` with actual final image; no `/app` source overlay. Analytics container names `inf2006-runtime-c-analytics` (initial runner failure) and `inf2006-runtime-c-analytics2` (corrected/pass), user 0 only for isolated dependency environment. Bootstrap DSN supplied only for focused runtime bootstrap fixtures.

Live smoke: `docker run -d --name inf2006-runtime-c-web --network container:inf2006-runtime-a-db` with local fixture environment, allowed hosts `localhost,127.0.0.1`, release `runtime-c-smoke`, final image and no command override. Check:

```sh
docker exec inf2006-runtime-c-web python -c 'import urllib.request,os; r=urllib.request.urlopen("http://127.0.0.1:8000/health/",timeout=2); assert r.status==200 and r.read()==b"{\"status\": \"ok\"}" and r.headers["Cache-Control"]=="no-store"; assert os.getuid()==10001; print("PASS")'
```

`docker logs --tail 6 inf2006-runtime-c-web` showed two worker startup events with release `runtime-c-smoke` and environment `local`, no secret payloads.

Cleanup inventory: `inf2006-runtime-a-db`, `inf2006-runtime-b-check`, `inf2006-runtime-c-tls-db`, `inf2006-runtime-c-analytics`, `inf2006-runtime-c-analytics2`, `inf2006-runtime-c-web`; task-created PostgreSQL anonymous volumes; scratch path above; task-created `src/staticfiles`; image `inf2006-runtime-c-sentinel`. No task-specific network was created. Preserve final image and pre-existing stopped `inf2006-ml-loader-db-1` plus all unrelated volumes/networks/data.

### C round 1 — independent gate clear

Independent (fresh session) `/root/runtime_reviewer`, explicitly `gpt-6-astra` / `medium`, reviewed the complete seven-file C diff and relevant consumers. **No actionable findings; RAS-001–007 remain resolved.** All seven frozen hashes matched. Independent helper syntax, Git sensitive/safe-file pattern checks and `git diff --check` passed.

Reviewer Docker-engine access was unavailable in its read-only sandbox. Image audits, TLS handshakes, final-image tests and live Gunicorn results remain implementer-executed evidence, not independently rerun. This limitation does not turn local evidence into AWS proof. All three bounded application-preparation review gates are clear; actual deployment/integration remains open.

Coordinator authorised removal only of recorded task resources after review, preserving the final image, pre-existing container and unrelated data. Cleanup and final scoped commit verification follow below.

### Cleanup and completion

After C gate clearance, Low removed exactly the six recorded task containers with `docker rm -f -v` (web/dependency/analytics containers before their network-namespace database containers). Both task PostgreSQL anonymous volumes were identified before removal and verified absent afterward. Removed only the task sentinel image. Native PowerShell resolved and checked the exact task TEMP scratch and workspace `src/staticfiles` paths, confirmed no link target, then used `Remove-Item -LiteralPath -Recurse`; both paths are absent. No broad pruning or network changes.

Pre-existing stopped `inf2006-ml-loader-db-1` remains unchanged (ID `24543c8a4ae58f7c3090a4766f53494341c50ae7e2986fefcfe14a0a4dd3e337`), as do unrelated images/resources. Final image `sha256:d28a64e0ad38f48ce3eaf14e5569922a08938e8b632f1fc3f5003bb6db3edf8c` remains available locally. All seven reviewed C hashes still matched after cleanup.

Bounded Phase 5 application preparation is complete locally, with independent gates clear for A/B/C and RAS-001–007 resolved. The infrastructure owner has the [canonical handoff](../AWS_INFRASTRUCTURE.md#image-and-infrastructure-owner-handoff): image/startup/port, required nonsecret settings and secret schemas, role/migration separation, CA/TLS, probe and proxy boundary, log fields/failure conditions and remaining deployed checks. READY-004 packaging is locally verified; READY-007 runtime behavior is locally prepared, not AWS-verified. No Terraform changed, no real secret retrieved, nothing pushed or deployed.

Remaining application work: lifecycle UI and lifetime-period copy, separately scoped immutable snapshots, accepted-dataset reevaluation, and other tracker-owned application work. Remaining deployed checks include lab permissions/region/budget/certificate, ECR publication/digest, least-privilege Secrets Manager/KMS and database access/denial, real RDS TLS, ALB Host/HTTPS/network behavior, coordinated migration/readiness, shared sessions/carts/signing across instances, logs/alarms/SNS, WAF/CloudTrail, scaling/recovery and required S3 evidence. Full suite, hosted CI and load tests were not run in this task. Overall AWS readiness remains open.

C coordinator staged verification: exactly ten reviewed task/metadata paths; all seven frozen C hashes match. Staged bytes match working text after newline normalization and decode as UTF-8. Scoped added-text AWS-key/private-key scan found no matches; all 12 added local Markdown link targets exist. No generated/static/credential artifacts or unrelated changes staged; no unstaged changes. `git diff --cached --check` passed. Final completion metadata does not change reviewed implementation or handoff contracts.
