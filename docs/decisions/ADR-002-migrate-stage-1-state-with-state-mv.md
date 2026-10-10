# ADR-002: Migrate stage 1 into `base/` with `terraform state mv`, recreate the rest, gate on a clean plan

**Status:** implemented; the stacks it describes were applied and measured on 8 and 9 October 2026 (first drafted 1 October 2026). Implements [ADR-001](ADR-001-split-terraform-into-base-and-stacks.md). Script: `src/infrastructure/scripts/migrate-state.sh`.

## Decision

Of the 38 managed stage 1 resources, 28 move into `base/` with `terraform state mv`; 10 are destroyed and recreated in the stacks (`sg-alb`, `sg-app`, their seven rules including `sg-db`'s rule from `sg-app`, and the app log group). The script backs the state up before and after the destroy, moves, and then **stops unless `terraform plan` in `base/` shows no resource changes**. Run while `base/` holds only the moved resources, so "no changes" is literal. The two data sources are not moved; they are read again.

## Options considered

| Option | Why not |
|---|---|
| Destroy and recreate all of stage 1 | Loses the four secret values and the pushed image, and the SNS email confirmation |
| Move everything, including `sg-app` | Two stacks cannot share one `sg-app` (each stack's ALB and instances must be the only members), so one stack would still need a new one |
| Delete the 10 from state only (`state rm`) | Leaves them in AWS; the stacks would then fail on duplicate names |
| `moved` blocks | They work inside one state, not across folders |
| **`state mv` plus a destroy of the 10 (chosen)** | Keeps everything that holds data or a manual step; the 10 are attached to nothing, so recreating them is free |

## Driver (shop scenario)

The secret values and image were set by hand and the SNS subscription needed a click; those are the expensive-to-redo parts and they all move. Nothing in the 10 holds data or traffic yet.

## Safety

- The destroy plan is checked against the expected list of 10 and must contain nothing else; the user types `yes`.
- A destroy before the move, so a failed gate leaves nothing to undo in AWS; `rollback` restores the post-destroy backup.
- The gate counts the no-op resources against the base state and fails on any other action.
- The old `.tf` files stay in place until the gate passes (the destroy plan needs their configuration); a follow-up commit deletes them.
- Backups are local `terraform.tfstate.<date>.*.bak` files (git-ignored); copy them off the laptop.

## Evidence that will back it

The gate output (28 resources, no changes) pasted into the runbook entry, with the commit SHA.

## Revisit when

Never repeated: this is a one-time migration. The script is kept as the record of how it was done.
