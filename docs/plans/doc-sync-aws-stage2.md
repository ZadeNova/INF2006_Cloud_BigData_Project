# Documentation sync after AWS stages 0 to 2 (30 September 2026)

Docs only; no code, Terraform or AWS change. Written before the edits, per the repo workflow.

## Why

Between 28 and 29 September 2026 the Terraform build started: stage 0 (scaffold) and stage 1 (network, security groups, S3 settings, ECR, secrets, logs, SNS) are **applied** to the team's Learner Lab account, stage 2 (RDS and the first app instance) is **written, independently reviewed and not applied**. Several living documents still say "no Terraform", "nothing is deployed", "console first", or describe S3 media, CORS and pre-signed URLs that were dropped. This pass makes them agree with the code and with each other, and records the cross-cutting reproducibility requirement in the tracker.

## Decisions to reflect (all made by the user, 28 to 30 September)

| Decision | Detail |
|---|---|
| State | Local state on one apply device (the user's laptop). An S3 backend was considered and not chosen: a committed backend block breaks `terraform init` for a reviewer without the team's account, and the state bucket would have to survive teardown. Custody rule: backup after every apply |
| Naming | `inf2006-grp21-<component>`, one `local.name_prefix` |
| Domain | `fourtytwofactors.me` (Namecheap, GitHub Student Developer Pack); the shop is `shop.fourtytwofactors.me`; DNS stays at the registrar |
| Media | Product images and `.glb` models stay static files in the image, served by WhiteNoise; no S3 media prefixes, no pre-signed URLs, no CORS |
| S3 | One bucket (dataset, exports), created with the CLI and looked up as a data source, because the lab's service control policy denies `s3:GetBucketObjectLockConfiguration`; its settings stay in Terraform |
| Stage 2 scope | The launch template and a one-instance ASG moved from stage 3 into stage 2, so the one-off database jobs run on the first real instance |
| RDS | PostgreSQL 17, 7-day backups, RDS-managed master password, no initial database |
| ECR | Deployed images carry a `release-<sha>` tag; the lifecycle policy keeps 5 releases |
| Reproducibility | A rubric-wide requirement (see below) |

## Reproducibility, recorded in the tracker (Phase 4 and next work)

1. **Two levels.** Offline reproduction by a marker with Docker only (required; the brief forbids requiring a cloud login). Cloud reproduction from `src/infrastructure/` (documented, with prerequisites and expected cost; shown to the marker through dated evidence).
2. **One reproducibility check per remaining Terraform stage:** could someone repeat this from the docs alone?
3. **`docs/REPRODUCE_CLOUD.md`** (to be written in Phase 4): prerequisites, expected cost, command order, the CLI-created bucket, the release tag step.
4. **Build the ZIP from git** (`git archive`), never by copying the folder, so `terraform.tfstate` and `terraform.tfvars` in `src/infrastructure/` cannot enter it; check the ZIP for them.
5. **Clean-clone rehearsal** by a teammate who did not write the code (the brief's Appendix A), following only the README.
6. Manifest `run.prerequisites` and `run.commands` are run literally from a clean clone before submission.
7. Rewrite the README's AWS status when the cloud evidence exists.
8. Known drift to state in the write-up: the AMI follows "latest Amazon Linux 2023".

## Files edited

| File | Change |
|---|---|
| `docs/IMPLEMENTATION_PLAN.md` | New top entry for the AWS build; superseded console-first entry marked; resolved media question; phase table rows, Phase 1 and Phase 4 checklists, next work, open items |
| `README.md` | Status, getting-started sentence, layout line, limitations, evidence pointers |
| `docs/AWS_INFRASTRUCTURE.md` | Status, baseline (Terraform exists, one bucket, no media), naming, state decision, trainer login, budget note |
| `docs/ARCHITECTURE.md` | Status; replace the proposed S3 media/CORS integration; "datasets and exports" |
| `docs/PROBLEM_FRAMING_AND_ARCHITECTURE.md` | Diagram data-flow row: no browser-to-S3 arrow |
| `docs/plans/aws-terraform.md` | Status, decisions rows, layout, stage table, boot script section, open items |
| `docs/plans/cloud-independent-prep.md` | Status banner, names and tags, suggested order |
| `docs/plans/threat-control-map.md`, `evidence/threat-control-map.md` | T8/T9 wording and applied status |
| `evidence/README.md` | AWS build runbook row; SEC-09 partial note |
| `docs/TESTING.md` | ZIP-from-git preflight item |
| `docs/AWS_CAPABILITY_CHECK.md` | Pointer to the active lab checks |
| `src/README.md` | ECR push is done for one image |

## Deliberately not edited

- `docs/reviews/*`, other `docs/plans/*` and `docs/latest-opus5.5-review.md`: dated historical records.
- `PROJECT_SCOPE_INF2006.md`: owns requirements and dates. One discrepancy is reported to the user, not changed: the scope says USD 40 per member; the integration account's Learner Lab page shows USD 50.
- `AGENTS.md`, `DESIGN.md`, `docs/SECURITY.md`, `docs/API.md`, `docs/SCHEMA.md`, `docs/FRONTEND.md`, `docs/DATA_PIPELINE.md`, `docs/ANALYTICS.md`, `analytics/README.md`, `data/*`: no statement affected.
- `TEAM_CONTRIBUTIONS.md` and `AI_USE_DECLARATION.md`: written last, after the cloud work, so they cover all of it. Pending.
- `evidence/monitoring.md`, `test-resilience.md`, `test-security.md`: templates or evidence-writer records; filled by real runs.
- `project_manifest.yaml`: filled last; `aws_integration` stays "unverified" until deployed behaviour is recorded.

## Verification

Grep for the stale phrases listed in the analysis; check every relative link in the edited files resolves; confirm no file outside the list above changed.
