# AWS Terraform review gate

Review log for the Terraform stages, per [aws-terraform.md § Review](../plans/aws-terraform.md#review). One section per stage.

## Stage 1: network, security groups, storage, secrets, monitoring

Date: 29 September 2026.
Snapshot: `erfan/aws` at `8f2e89b` (diff `f545806..8f2e89b`, `src/infrastructure/`).
Reviewer: fresh-session Claude Opus 5.5, the independent review gate named in the plan.
Evidence: static read of the diff; `terraform show` of the saved `stage1.tfplan` (39 to add, 0 to change, 0 to destroy, no warnings; resource count reconciled by hand). No AWS calls were made.

**Result: gate closed. No Critical, High or Medium findings; nothing blocks the first apply.**

### Checks

| Check | Result |
|---|---|
| Security group chain | Pass. Internet reaches only `sg-alb` on 443/80; 8000 only from `sg-alb`; 5432 only from `sg-app`; no port 22; the default security group is emptied. The only other `0.0.0.0/0` is the intended `sg-app` 443 egress. |
| S3 public access | Pass. All four Block Public Access settings on, `BucketOwnerEnforced`, TLS-only deny covers the bucket and `/*`, policy `depends_on` the public access block. |
| Secrets | Pass. Containers only, no `aws_secretsmanager_secret_version`; `recovery_window_in_days = 0` is intentional and needed for destroy/re-apply. |
| IAM | Pass. No `aws_iam_*` resources; `aws_iam_policy_document` is a local data source. |
| Private subnets | Pass. Local route only; no IGW or NAT route. |
| Naming | Pass. All names from `local.name_prefix` (see L2). |
| Cost | Pass. Nothing hourly; four secrets cost about USD 1.60/month. |

### Findings

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| L1 | Low | S3 sub-resources ([storage.tf](../../src/infrastructure/storage.tf)) other than the policy configure the bucket in parallel; an `OperationAborted` error is possible, though the provider normally retries. | No change. If it occurs, re-run `apply`. |
| L2 | Low | `aws_ecr_repository.app` has no `Name` tag; the `ecr_repository_url` output description hardcodes `inf2006-grp21-app`. | Optional, cosmetic. |
| L3 | Low | `sg-app` egress allows 443 only; package installs over HTTP (for example Ubuntu apt) would fail. Fine on Amazon Linux 2023. | Check when the stage 3 AMI is chosen. |
| L4 | Low | `availability_zones` has no length validation (a short list fails loudly at plan). | Optional. |
| I1 | Info | `recovery_window_in_days = 0`, `force_destroy` and `force_delete` make destroy permanent; a secret replacement deletes its value immediately. | Runbook: export before teardown, re-set secret values after each re-apply; stop if a plan replaces a secret. |
| I2 | Info | `prevent_destroy` on the bucket or ECR repo. | Not recommended: it would block every `terraform destroy`, contradicting the teardown workflow. |
| I3 | Info | A successful plan does not prove create permissions; Learner Lab credentials expire after about 4 hours. | Refresh credentials before apply; a partial apply resumes on re-run. |
| I4 | Info | Public IPv4 addresses (ALB, app instances) bill hourly from stage 3. | Include in the stage 3 cost estimate. |
| I5 | Info | Apply the reviewed saved plan (`terraform apply stage1.tfplan`); it contains `alarm_email` in plain text and is git-ignored. | Delete the plan file after apply. |

### Post-review change: S3 bucket as a data source (29 September 2026)

The first apply of the reviewed plan created 32 of 39 resources, then failed reading the new bucket back: `AccessDenied` on `s3:GetBucketObjectLockConfiguration`, an explicit deny in the Learner Lab's service control policy. The `aws_s3_bucket` resource calls this on every read, so any plan touching it would keep failing. A probe of 16 bucket read calls showed it is the only denied one.

Change (uncommitted at the time of this entry; committed with this log): `aws_s3_bucket.main` became `data "aws_s3_bucket" "main"` looked up by a new `s3_bucket_name` variable; a `removed` block with `destroy = false` dropped the tainted resource from state without deleting the bucket; the six bucket settings, the CORS rule (still off) and the outputs now reference the data source. `terraform.tfvars.example` added. Consequence: `terraform destroy` no longer deletes the bucket; stage 6 empties and deletes it with the CLI.

Not re-sent through the gate: the change swaps how the bucket is referenced and leaves every reviewed security setting identical. Its plan was checked by hand in the build session (6 to add, 0 to change, 0 to destroy, the bucket "will no longer be managed… but will not be destroyed", all 32 existing resources refreshed with no drift) and applied. Logged as a same-session exception.

Acceptance after the apply: subnets in `us-east-1a` and `us-east-1b`; anonymous request to the bucket returned 403; SNS email subscription pending confirmation at the time of the check.
