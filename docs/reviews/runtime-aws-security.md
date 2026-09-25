# Runtime and AWS security preparation

Date: 25 September 2026. Status: in progress; no completed review gate or AWS readiness claim.

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

Pending. Exact frozen paths, hashes, commands, actual results, findings and unrun checks will be recorded per checkpoint. No tests or image build have yet been executed in this Phase 5 pass.

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
