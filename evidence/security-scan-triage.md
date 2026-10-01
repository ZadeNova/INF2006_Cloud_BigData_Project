# Security scan record and triage

Run on 2026-10-01 at commit `e6732ff` (application source unchanged since 27 September; the working tree also held uncommitted docs and infrastructure scripts, which no scan covers). All scans ran locally in Docker on the committed tree or the locally built image, not in CI. A `security` job in [ci.yml](../.github/workflows/ci.yml) runs the same tools (gitleaks, pip-audit and `check --deploy` blocking; bandit, hadolint and both Trivy scans report-only, raw output uploaded as the `security-scans` artefact). That job is written and its YAML parses, but it has **not run on GitHub yet**, so no CI result is claimed. The one gitleaks suppression lives in [.gitleaks.toml](../.gitleaks.toml), scoped to that commit and file. Raw output is unchanged in [raw/](raw/); nothing was filtered or silenced. No scan used AWS credentials.

**Dispositions:** *Fixed*, *Accepted* (reason given), *False positive* (reason given), or *Open* (needs a decision from the named owner). Backend, `src/Dockerfile` and `requirements.txt` are frozen ([AGENTS.md](../AGENTS.md)); a finding that needs a change there is reported, not fixed.

## Summary

| ID | Tool (version / image digest) | Target | Result | Raw output |
|---|---|---|---|---|
| SCAN-01 | gitleaks (`ghcr.io/gitleaks/gitleaks@sha256:c00b6bd0…bb7f`) | Git history (135 of 141 commits scanned) and the committed tree | 1 finding in history (false positive); 0 in the tree | [history](raw/SCAN-01_2026-10-01_gitleaks-history.json), [tree](raw/SCAN-01_2026-10-01_gitleaks-tree.json) |
| SCAN-02 | bandit 1.9.4 | `src/` and `analytics/` (static files and infrastructure excluded) | 98 LOW, 0 MEDIUM, 0 HIGH | [json](raw/SCAN-02_2026-10-01_bandit.json) |
| SCAN-03 | pip-audit 2.10.1 (`--no-deps`, 20 pinned requirements in `src/`; `analytics/requirements.txt` separately) | PyPI advisory data at run time | 0 known vulnerabilities in both | [src](raw/SCAN-03_2026-10-01_pip-audit-src.json), [analytics](raw/SCAN-03_2026-10-01_pip-audit-analytics.json) |
| SCAN-04 | `manage.py check --deploy`, production-mode settings | Django configuration | 2 warnings (W005, W021), 0 errors | [txt](raw/SCAN-04_2026-10-01_check-deploy.txt) |
| SCAN-05 | hadolint (`hadolint/hadolint@sha256:32dac941…12d`), default rules | `src/Dockerfile` | 0 findings | [json](raw/SCAN-05_2026-10-01_hadolint.json) |
| SCAN-06 | Trivy 0.74.0 (`ghcr.io/aquasecurity/trivy@sha256:62b1e65e…969`), vuln and secret scanners | Locally built application image (Debian 12.15 base, base digest pinned in the Dockerfile) | 279 OS findings (5 CRITICAL, 61 HIGH), 6 Python findings, 0 secrets | [json](raw/SCAN-06_2026-10-01_trivy-image.json) |
| SCAN-07 | Trivy 0.74.0, config scanner | `src/infrastructure/` as committed at `e6732ff` (old single-folder layout) | 13 findings (1 CRITICAL, 1 HIGH), 79 checks passed | [json](raw/SCAN-07_2026-10-01_trivy-iac.json) |

An earlier gitleaks attempt the same day scanned 0 commits because the container could not read the mounted repository, and so reported "no leaks". That result was invalid and was discarded; the table above is from the rerun on a clone (135 commits scanned; the other six are merge commits with no diff of their own).

## Triage

### SCAN-01 gitleaks

| Finding | Disposition | Reason |
|---|---|---|
| `generic-api-key`, `evidence/test-security.md` line 11, commit `51e4ec1` (12 September) | **False positive** | The matched text is the prose "Authentication, ownership/CSRF and cloud security demonstrations remain unrun". The rule's entropy test fired on the word-like string; the report redacts it. No credential is present. |

### SCAN-02 bandit (98 findings, all LOW)

| Rule | Count | Disposition | Reason |
|---|---|---|---|
| B101 `assert_used` | 86 | **False positive** | All in `analytics/tests/`; pytest assertions, not shipped in the application image. |
| B311 `random` | 4 | **Accepted** | `random.Random(seed)` in the synthetic-data builders (`analytics/build_shoe_dataset.py`, `src/config/dataset.py`, `seed_demo`). Seeded and deterministic by design; no security decision uses it. |
| B404, B603, B607 `subprocess` | 2, 3, 2 | **Accepted** | `analytics/evaluate_segments.py` runs `git` and `src/tools/aws_capability_check.py` runs the AWS CLI, both with fixed argument lists and no shell. Developer tools, not reachable from a web request. |
| B105 `hardcoded_password_string` | 1 | **False positive** | `analytics/tests/test_startup_credentials.py`, a test fixture setting `AWS_REGION`; no password. |

Limitation: the root `tests/` directory and the vendored JavaScript are not scanned by bandit.

### SCAN-03 pip-audit

No findings. Limitation: `--no-deps` trusts that the pinned file lists every installed package, and it audits Python packages only, not the operating system (see SCAN-06). Advisory data is as of the run date.

### SCAN-04 check --deploy

| Warning | Disposition | Reason |
|---|---|---|
| W005 `SECURE_HSTS_INCLUDE_SUBDOMAINS` not set | **Accepted** | Applying HSTS to every subdomain is not safe to assume. HSTS is already on with a deliberately short lifetime of 3600 s (comment in `src/config/settings.py`: a browser that has seen HSTS refuses HTTP and certificate-warning bypasses for that long). |
| W021 `SECURE_HSTS_PRELOAD` not set | **Accepted** | Preload needs a long HSTS lifetime and is hard to undo, which conflicts with the same decision. |

The run stubs the Secrets Manager call exactly as `tests/test_settings.py::test_production_configuration` does, and sets `DJANGO_TRUST_PROXY=true` to match deployment behind an ALB. Everything else the check covers (secure cookies, SSL redirect, debug off, secret-key strength, allowed hosts) passed.

### SCAN-05 hadolint

No findings under default rules. This says little about runtime hardening: the Dockerfile does run as a non-root user (`USER 10001:10001`) and pins its base image by digest.

### SCAN-06 Trivy image

Secrets: none found in any layer.

| Group | Count | Disposition | Reason |
|---|---|---|---|
| Debian packages with no fix available (`affected` 201, `fix_deferred` 43, `will_not_fix` 14) | 258 | **Accepted** | Debian has published no fixed package, so a rebuild cannot remove them. This includes all 5 CRITICAL (`libsqlite3-0`, three in `perl-base`, `zlib1g`). Reachability from the application was **not** analysed. Mitigations in place: non-root container user, private subnets, ingress to port 8000 from the ALB security group only (Terraform, applied). |
| Debian packages with a fix available | 21 (3 HIGH, 7 MEDIUM, 8 LOW, 3 UNKNOWN), in `libssl3`, `openssl`, `libpcre2-8-0`, `liblzma5`, `tzdata` | **Open, user decision** | Fixed by rebuilding on a newer `python:3.13-slim-bookworm` digest. That is a change to the frozen `src/Dockerfile` and produces a new image digest, so evidence on the old digest would need rerunning (AGENTS.md). Not treated as an emergency by this session; the user decides. |
| Python packages (6: `msgpack` 1.1.2, `setuptools` 70.3.0, `urllib3` 2.7.0) | 6 | **Accepted** | All three are copies **vendored inside pip 26.2.1** (listed in `pip/_vendor/vendor.txt`), not the application's libraries: the application's own `urllib3` is 2.8.0 as pinned (checked in the container). pip is not run at runtime. Removing pip from the final image would need a Dockerfile change (frozen). |

Limitation: the scan is of the image built locally from the same pinned base digest as the deployed image, not of the pushed ECR digest. ECR scan-on-push is enabled in Terraform; its findings for the deployed digest have **not** been retrieved.

### SCAN-07 Trivy IaC (committed `src/infrastructure/`, old layout)

This session does not edit `src/infrastructure/**`. Dispositions below are proposals for the Terraform session and owner. The scan evaluated the files without `terraform.tfvars` (variables `alarm_email`, `image_tag`, `s3_bucket_name` were unset); none of the findings depend on them. Rerun after the base/ec2/fargate split.

| ID | Severity | Resource | Proposed disposition | Reason |
|---|---|---|---|---|
| AWS-0104 | CRITICAL | `app_https` egress 443 to 0.0.0.0/0 (`security_groups.tf`) | **Open: Terraform owner** | Needed to reach ECR, Secrets Manager, SSM and CloudWatch without VPC interface endpoints (cost). Proposed accept with reason; outbound is limited to TCP 443 and PostgreSQL, and there is no inbound from the internet. |
| AWS-0095 | HIGH | SNS topic `alarms` is unencrypted | **Open: Terraform owner** | Likely a real fix. Caution: the AWS-managed key `alias/aws/sns` does not allow CloudWatch alarms to publish; a customer-managed key with a suitable policy would be needed. |
| AWS-0177 | MEDIUM | RDS deletion protection off | **Accepted (proposed)** | Teardown between experiments is required by the plan; final snapshot is also skipped for the same reason. |
| AWS-0176 | MEDIUM | RDS IAM database authentication off | **Accepted (proposed)** | The design authenticates with Secrets Manager credentials; the frozen application has no IAM-token login. |
| AWS-0178 | MEDIUM | VPC flow logs off | **Open: Terraform owner** | Lab permission and cost not verified. |
| AWS-0017 ×2, AWS-0098 ×4, AWS-0033 | LOW | Log groups, four secrets and the ECR repository use AWS-managed rather than customer-managed keys | **Accepted (proposed)** | Encryption at rest is still on with AWS-managed keys; customer-managed keys add cost and lab permission risk. |
| AWS-0133 | LOW | RDS Performance Insights off | **Accepted (proposed)** | Not a control. May be switched on for the database pilot run for other reasons. |

## Commands (to reproduce)

Run from the repository root; scanner images are pulled by digest. Mount with the `:z` flag on SELinux hosts and use a clone, not the working tree, for gitleaks history.

```
git clone --no-local . $TMP/clone; git archive HEAD | tar -x -C $TMP/tree
docker run --rm -v $TMP/clone:/repo:ro,z -v $OUT:/out:z <gitleaks> git /repo --redact --no-banner --exit-code 0 --report-format json --report-path /out/h.json
docker run --rm -v $TMP/tree:/repo:ro,z  -v $OUT:/out:z <gitleaks> dir /repo --redact --no-banner --exit-code 0 --report-format json --report-path /out/t.json
docker run --rm -v $TMP/tree:/work:ro,z -w /work <python:3.13-slim-bookworm@sha256:ed86c822…c6e> sh -c 'pip install pip-audit bandit; pip-audit --no-deps --disable-pip -r src/requirements.txt; pip-audit --no-deps --disable-pip -r analytics/requirements.txt; bandit -r src analytics -x src/static,src/infrastructure'
docker run --rm -i <hadolint> hadolint --format json - < src/Dockerfile
docker compose build web && docker save inf2006-foundation-app:latest -o app.tar && docker run --rm -v $TMP:/s:z <trivy> image --input /s/app.tar --scanners vuln,secret --format json
docker run --rm -v $TMP:/s:z <trivy> config --format json /s/tree/src/infrastructure
```

`check --deploy` is the first line of [raw/SCAN-04_2026-10-01_check-deploy.txt](raw/SCAN-04_2026-10-01_check-deploy.txt).
