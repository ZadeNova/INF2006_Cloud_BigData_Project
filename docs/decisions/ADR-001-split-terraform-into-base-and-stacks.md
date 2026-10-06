# ADR-001: Split Terraform into `base/`, `ec2/` and `fargate/`, one local state each

**Status:** drafted by the writing session for review (1 October 2026). Numbering is provisional: `docs/decisions/` did not exist, so this starts at 001. **Partly superseded by [ADR-014](ADR-014-shared-web-entry-module.md) (6 October 2026):** the rule "no child modules" no longer applies to the shared front door; the rest (three folders, one local state each) stands.

## Decision

`src/infrastructure/` holds three independent Terraform folders. `base/` owns what both variants share and stays up between experiments (VPC, subnets, `sg-db`, Route 53 zone, certificate, RDS, ECR, S3 settings, secrets, SNS). `ec2/` and `fargate/` each own their ALB, `sg-alb`, `sg-app`, compute, scaling, alias record and log group, and read `base/` through `terraform_remote_state` on the local backend. One folder, one state file; no workspaces, no child modules, no symlinks; `versions.tf` and `providers.tf` repeat in each folder.

## Options considered

| Option | Why not |
|---|---|
| One folder, a `variant` switch | One state: destroying one variant risks the other and the shared database. A switch hides which resources a variant really needs, and the comparison counts those |
| Workspaces | Same code and one backend: the variants differ in resources, not only in values |
| Shared child module | Adds indirection for about three resources; the project's own rule is no speculative abstraction |
| Remote state in S3 | Rejected earlier: a committed backend breaks `terraform init` for a reviewer without the team's account |
| **Three folders (chosen)** | A stack can be created and destroyed without touching the database; `base/` survives between runs |

## Driver (shop scenario)

The comparison needs each variant built, loaded and destroyed repeatedly against **one** database, so the database and the registry must outlive both stacks, and a destroy of one stack must not be able to reach the other. The shop needs only one database (about 2 to 3 queries per second at peak), so sharing it is realistic.

## Consequences

- One-way dependency: `base/` never reads a stack, so a stack can be destroyed first. `base/outputs.tf` is the interface.
- Resources that must name a stack-owned resource live in the stack, not in `base/`: `sg-db`'s rule allowing 5432 from `sg-app` is created in each stack against `sg-db`'s ID from `base/`.
- Per-stack counts (files, resources, lines) are an input to the "operational burden" measurement.
- Cost: provider and version files are repeated in three places.

## Evidence that will back it

Plan in each folder shows no resources from the other; `terraform destroy` in a stack leaves `base/` unchanged (`terraform plan` in `base/` shows no changes afterwards).

## Revisit when

A third stack appears (then consider a module), or the repeated boilerplate drifts between folders.
