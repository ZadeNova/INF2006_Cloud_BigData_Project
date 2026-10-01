# AWS capability record

Generated 2026-09-25 07:28 UTC. Region: `us-east-1`. Read-only probe: list/describe calls and EC2 dry runs only; nothing was created.

| Area | Check | Result | Detail |
|---|---|---|---|
| Identity | sts get-caller-identity | allowed | account ending 6569, principal assumed-role/voclabs |
| Network | availability zones (need 2) | allowed | 6 zones |
| Network | VPCs | allowed | 1 VPCs, default VPC present |
| Network | create a VPC (dry run) | allowed | permitted |
| Compute | instance types offered | allowed | t3.medium, t3.micro, t3.small |
| Compute | Amazon Linux 2023 AMI lookup (SSM parameter) | allowed | found |
| Compute | launch an instance (dry run) | allowed | permitted |
| Compute | running on-demand standard vCPU quota | denied | aws: [ERROR]: An error occurred (AccessDeniedException) when calling the GetServiceQuota operation: User: arn:aws:sts::<account>:assumed-role/voclabs/<session> |
| Load balancing | ALBs (list) | allowed | 0 existing |
| Scaling | Auto Scaling groups (list) | allowed | 0 existing |
| Database | RDS instances (list) | allowed | 0 existing |
| Database | default PostgreSQL engine version | allowed | 18.3 |
| Storage | S3 buckets (list) | allowed | 0 existing |
| IAM | instance profiles (list) | allowed | EMR_EC2_DefaultRole, LabInstanceProfile |
| IAM | roles (list, service-linked hidden) | allowed | c228096a5751007l16687146t1w061745-LabEksClusterRole-V1Ut0EDmlUQH, c228096a5751007l16687146t1w061745666-LabEksNodeRole-JRx5X0SfCrDQ, c228096a5751007l16687146t1w0617456665-LambdaSLRRole-a7PMg3154UMv, EMR_AutoScaling_DefaultRole, EMR_DefaultRole, EMR_EC2_DefaultRole, EMR_Notebooks_DefaultRole, LabRole |
| Secrets | Secrets Manager (list) | allowed | 0 existing |
| HTTPS | ACM certificates (list) | allowed | 0 existing |
| HTTPS | Route 53 hosted zones (list) | allowed | 0 existing |
| Registry | ECR repositories (list) | allowed | 0 existing |
| Management | SSM managed instances (list) | allowed | 0 managed |
| Monitoring | CloudWatch log groups (list) | allowed | 3 shown |
| Monitoring | CloudWatch alarms (list) | allowed | 0 shown |
| Monitoring | SNS topics (list) | allowed | 1 existing |
| Cost | AWS Budgets (list) | allowed | 0 existing |

## How to read this

- **allowed** means the call succeeded (or the EC2 dry run said it would have). **denied** means the lab's policy refused it. **error** is anything else, so read the detail.
- Listing a service proves its API is reachable, **not** that creating it is permitted. Creation of the ALB, Auto Scaling group, RDS instance, S3 bucket, IAM role and ACM certificate is only proved by a Terraform plan and apply in stages 2 and 3 of the setup order.
- Remaining balance is not available from the API. Read it from the lab page and record it here: `USD ____` on `____`.
- Instance profiles and role names above are the ones Terraform must reference instead of creating, if role creation is denied.

## Decisions this feeds

- **HTTPS:** ACM plus Route 53 allowed means a trusted certificate on a domain the team controls may be possible. Otherwise see the options in `docs/plans/cloud-independent-prep.md` (B4).
- **Image source:** ECR allowed means push the image there; otherwise build it on the instance or load it from S3.
- **Secrets:** Secrets Manager denied means the database password and `DJANGO_SECRET_KEY` come from the launch configuration instead; record that limitation.
- **Management access:** SSM allowed means no SSH is needed, which is the recommended arrangement.

## Stage 1 lab checks (29 September 2026)

Active probe: a throwaway `t3.micro` instance (`LabInstanceProfile`, default VPC, tagged `Purpose=stage1-lab-check`, not `Project=inf2006-grp21`), used only to test creation/use permissions that a list call cannot prove. Launched, checked, and terminated within the same session; not part of the Terraform-managed stack. Region `us-east-1`.

| Area | Check | Result | Detail |
|---|---|---|---|
| Identity | instance identity under `LabInstanceProfile` | allowed | `assumed-role/LabRole/<instance-id>` from inside the instance, confirming instances run as `LabRole`, not the `voclabs` console user |
| Management | SSM agent registration | allowed | `PingStatus: Online` within 1–2 minutes of launch, no SSH key or port 22 |
| Management | SSM interactive session (`start-session`) | allowed | required installing the local `session-manager-plugin`; the AWS CLI alone is not sufficient on the client side |
| Secrets | create a secret from the instance | allowed | `secretsmanager:CreateSecret` |
| Secrets | retrieve a secret from the instance | allowed | `secretsmanager:GetSecretValue`; this is the exact call the app's startup secret loader makes |
| Secrets | delete a secret, `--force-delete-without-recovery` | allowed | immediate deletion, no 30-day hold, matching `recovery_window_in_days = 0` in `secrets.tf` |
| WAF | create a regional Web ACL | allowed | `wafv2:CreateWebACL`, default action Allow, no rules (permission test only) |
| WAF | delete a Web ACL | allowed | `wafv2:DeleteWebACL` |
| Cost | create an AWS Budget | allowed | `budgets:CreateBudget`, USD 1.00 monthly, then `DescribeBudgets` returned it with `HealthStatus: HEALTHY` |
| Cost | delete an AWS Budget | allowed | `budgets:DeleteBudget` |
| Cost | lab balance at time of check | — | USD 0.20 of USD 50.00 used, per the Learner Lab page (not available from the API) |

**Not tested:** whether a running instance survives a Learner Lab session boundary (session timeout vs. resource lifecycle). Deferred to natural observation during stage 3/5, when a real ASG instance runs continuously for multiple days, rather than run as a separate dedicated test.

**Result:** every stage 1 open item under "lab checks" (secret retrieval with `LabInstanceProfile`, Session Manager, WAF, budget) is now confirmed allowed. No blockers found for stage 1 or the stage 4 WAF rule.
