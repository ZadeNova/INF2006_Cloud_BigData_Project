# AWS build runbook

One dated entry per Terraform stage: what was applied, from which commit, the acceptance checks and their actual results, problems met, and the lab balance. Built per [aws-terraform.md](../docs/plans/aws-terraform.md). Account IDs are redacted as `<account>`; no public IP addresses or tokens are recorded.

## Stage 1: network, security groups, storage, secrets, monitoring (29 September 2026)

**Applied from:** Terraform 1.16.4, AWS provider 6.66.0, region `us-east-1`, on the single apply device (the owner's Fedora laptop).

| Step | Commit | Result |
|---|---|---|
| Plan `stage1.tfplan` | `8f2e89b` | 39 to add, 0 to change, 0 to destroy. Passed the review gate ([log](../docs/reviews/aws-terraform.md#stage-1-network-security-groups-storage-secrets-monitoring)) |
| Apply `stage1.tfplan` | `8f2e89b` | **Partial: 32 of 39 created**, then failed (below) |
| Plan `stage1b.tfplan` | fix applied from the working tree, committed afterwards (see note) | 6 to add, 0 to change, 0 to destroy; `aws_s3_bucket.main` removed from state without being destroyed; no drift on the 32 existing resources |
| Apply `stage1b.tfplan` | same | Complete. 38 resources managed; the bucket is looked up as a data source |

**Problem: S3 object lock read denied by the lab.** The first apply created the bucket, then failed reading it back:

```
Error: reading S3 Bucket (inf2006-grp21-data-<suffix>) object lock configuration:
... api error AccessDenied: User: arn:aws:sts::<account>:assumed-role/voclabs/<session>
is not authorized to perform: s3:GetBucketObjectLockConfiguration ...
with an explicit deny in a service control policy
```

The `aws_s3_bucket` resource makes this call on every read, so no later plan could succeed while Terraform managed the bucket. A probe of 16 bucket read calls with the CLI showed `GetObjectLockConfiguration` is the **only** one denied. Fix: the bucket became `data "aws_s3_bucket"` (looked up by name), a `removed` block with `destroy = false` dropped it from state, and all six bucket settings stay Terraform resources. Consequence: `terraform destroy` will not delete the bucket; stage 6 empties and deletes it with the CLI. Details in [aws-terraform-stage-1.md](../docs/plans/aws-terraform-stage-1.md#s3-bucket-created-with-the-cli-lab-constraint-29-september-2026).

**Note on the apply rule.** The plan requires applying committed code only. The bucket fix was planned and applied from the working tree before it was committed, to recover from the failed apply in the same session. It is committed immediately after, unchanged; this entry records the exception.

### Acceptance

| Check | Command | Expected | Actual |
|---|---|---|---|
| Subnets in two AZs | `aws ec2 describe-subnets --filters Name=tag:Project,Values=inf2006-grp21` | public and private subnets in `us-east-1a` and `us-east-1b` | Pass: `inf2006-grp21-public-a`/`private-a` in `us-east-1a`, `public-b`/`private-b` in `us-east-1b` |
| Anonymous S3 access denied | `curl -s -o /dev/null -w '%{http_code}' https://<bucket>.s3.amazonaws.com/anything` | 403 | Pass: 403 |
| SNS email subscription confirmed | `aws sns list-subscriptions-by-topic` | a subscription ARN, not `PendingConfirmation` | Pass, after confirming. The confirmation email was delivered to **Gmail spam**; the sender was marked not-spam so stage 4 alarm emails arrive |
| No drift after apply | `terraform plan` | no changes | Pass (the stage 1b plan refreshed all 32 existing resources with no changes) |

**Not yet done in stage 1:** push the image to ECR (step 8.5) and set the secret values that do not depend on RDS (step 8.6).

### Cost

Lab balance after stage 1: USD 0.20 of USD 50.00 used (read from the Learner Lab page, 29 September 2026; the figure updates with a delay, so same-day charges may not show yet). Nothing in stage 1 bills hourly; the four secrets cost about USD 0.05 per day together. The stack is left running between sessions.
