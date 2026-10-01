# Archive

Finished or superseded planning records, moved out of the working set on 1 October 2026 with `git mv`, so their history is intact. Nothing here governs current work. Review logs stay in [docs/reviews/](../reviews/) because they are evidence of the independent-review process.

Why files were archived: the plan or guide describes work that is complete, or its decisions were carried into a live document. Seven plans stay in [docs/plans/](../plans/) because source code, tests or active work still point to them.

## AWS (retired; content merged)

The live AWS documents are [AWS_INFRASTRUCTURE.md](../AWS_INFRASTRUCTURE.md) (the contract), [the AWS plan](../plans/aws-ecs-comparison.md) (decisions, design and schedule; section 13 carries forward everything from these files that still holds) and [the AWS runbook](../../evidence/aws-build-runbook.md) (procedures, lab capability record and the as-built log).

- [aws-probe-fixes.md](plans/aws-probe-fixes.md): AWS probe fixes: W-01 and W-02, and a usage guide
- [aws-terraform-stage-0.md](plans/aws-terraform-stage-0.md): Stage 0 guide: install Terraform and pin the provider
- [aws-terraform-stage-1.md](plans/aws-terraform-stage-1.md): Stage 1 guide: network, security groups, storage, secrets, logs and alerts
- [aws-terraform-stage-2.md](plans/aws-terraform-stage-2.md): Stage 2 plan: RDS, and the first app instance for one-off jobs
- [aws-terraform.md](plans/aws-terraform.md): AWS infrastructure in Terraform
- [backend-aws-readiness.md](plans/backend-aws-readiness.md): Backend remediation and AWS integration preparation
- [cloud-independent-prep.md](plans/cloud-independent-prep.md): Cloud-independent prep
- [deploy-readiness.md](plans/deploy-readiness.md): Deploy readiness (B6 app-side items 1 to 3)
- [doc-sync-aws-stage2.md](plans/doc-sync-aws-stage2.md): Documentation sync after AWS stages 0 to 2 (30 September 2026)
- [AWS_CAPABILITY_CHECK.md](AWS_CAPABILITY_CHECK.md): how to run the read-only capability probe (the tool is `src/tools/aws_capability_check.py`)
- [aws-capability-record.md](aws-capability-record.md): the raw probe results (summarised in the runbook)

## Completed plans

- [analytics-pagination-size-select.md](plans/analytics-pagination-size-select.md): Analytics list pagination, and the size picker styled per DESIGN.md
- [analytics-status.md](plans/analytics-status.md): Analytics: status and remaining work
- [astra-review.md](plans/astra-review.md): Astra review brief
- [backend-completion-roadmap.md](plans/backend-completion-roadmap.md): Backend and dataset completion roadmap
- [batch-03-cart.md](plans/batch-03-cart.md): Batch 3 — persistent cart (add / update / remove)
- [batch-05-order-history.md](plans/batch-05-order-history.md): Batch 5 — order history
- [batch-06a-data-import.md](plans/batch-06a-data-import.md): Batch 6a — dataset acceptance, import and seed
- [batch-06a-dataset-generator.md](plans/batch-06a-dataset-generator.md): Batch 6a (alternative) — deterministic dataset generator
- [batch-06c-dashboard.md](plans/batch-06c-dashboard.md): Batch 6c — operator analytics dashboard
- [batch-06d-ml-segmentation.md](plans/batch-06d-ml-segmentation.md): Batch 06d: Optional ML customer segmentation
- [catalogue-filter-detail.md](plans/catalogue-filter-detail.md): Manage-products filter and product detail page
- [code-review-fixes.md](plans/code-review-fixes.md): Code review fixes: CR-001, CR-002, CR-008, CR-009, CR-010, CR-011
- [dashboard-theme-alignment.md](plans/dashboard-theme-alignment.md): Dashboard theme alignment (option A)
- [data-ml-evidence-rerun.md](plans/data-ml-evidence-rerun.md): DATA-01 / DATA-02 evidence rerun on the shoe dataset
- [doc-drift-fixes.md](plans/doc-drift-fixes.md): Documentation drift after the ML merge: F-05 and S-005
- [doc-sync-contracts-threat-map.md](plans/doc-sync-contracts-threat-map.md): Doc sync: API context, review gate, tracker, naming and threat map
- [doc-sync-marker-facing.md](plans/doc-sync-marker-facing.md): Doc sync: marker-facing README, manifest, ML reproduction and test counts
- [docs-alignment.md](plans/docs-alignment.md): Documentation alignment
- [evidence-kit.md](plans/evidence-kit.md): Evidence kit: a frictionless workflow for the evidence writer
- [ml-feature-tenure-fix.md](plans/ml-feature-tenure-fix.md): ML feature fix (review finding M-03)
- [ml-holdout-evaluation.md](plans/ml-holdout-evaluation.md): ML hold-out and subsample evaluation (review findings M-02, M-05)
- [opus-review-fixes.md](plans/opus-review-fixes.md): Opus review fixes: OPUS-001, OPUS-002, OPUS-003
- [sec-001-log-message-fix.md](plans/sec-001-log-message-fix.md): SEC-001 fix (round 2 repeat): stop `django.security` log messages leaking user input
- [self-review-cdn-ci-fixes.md](plans/self-review-cdn-ci-fixes.md): Self-review fixes: vendored model-viewer and shoe-dataset tests in CI
- [shoe-baseline-gate-fixes.md](plans/shoe-baseline-gate-fixes.md): Shoe-baseline gate fixes: G-001 and G-002
- [shoe-dataset-handoff.md](plans/shoe-dataset-handoff.md): Shoe dataset handoff
- [shoe-dataset-remap.md](plans/shoe-dataset-remap.md): Shoe dataset remap
- [storefront-redesign.md](plans/storefront-redesign.md): Storefront redesign and dark mode
- [test-trim-shoe-baseline.md](plans/test-trim-shoe-baseline.md): Test trim after the shoe-baseline gate
- [test-trim.md](plans/test-trim.md): Test trim (25 September 2026)
- [threat-control-map.md](plans/threat-control-map.md): Threat-control map: research and plan
- [two-small-defects.md](plans/two-small-defects.md): Two small defects: checkout subtotal and `--band-ink-soft`

To restore a file: `git mv docs/archive/plans/<name>.md docs/plans/` and rerun a link check.
