# ADR-014: One shared module for the web front door, used by both variants

**Status:** implemented; the stacks it describes were applied and measured on 8 and 9 October 2026 (first drafted 6 October 2026). Supersedes the "no child modules" part of [ADR-001](ADR-001-split-terraform-into-base-and-stacks.md); the rest of ADR-001 stands.

## Decision

A Terraform child module, `src/infrastructure/modules/web-entry/`, holds everything the two variants have in common in front of the application: the `sg-alb` and `sg-app` security groups and their rules (including the stack's own rule on `base/`'s `sg-db`), the ALB, its HTTPS and redirect listeners, the target group and its health check, the WAF web ACL and its association, the three alarms and two saved log queries, the stack's log group, and the Route 53 alias record. `ec2/` and `fargate/` each call it and add only their own compute and scaling. The module also outputs one **map of application environment variables** (allowed hosts, CSRF origins, proxy trust, HSTS and the like), which the EC2 user data and the Fargate task definition both read.

The module takes the target type (`instance` for the Auto Scaling group, `ip` for Fargate `awsvpc`) and everything else that differs by stack (name prefix, hostname, stack tag) as inputs. Each folder still has its own provider, versions file, state and `terraform apply`.

## Options considered

| Option | Why not |
|---|---|
| Copy the front door into `fargate/` (the ADR-001 position) | About 350 lines would exist twice. A change to a health-check setting could reach one stack and not the other, which would put an unrecorded difference into a comparison whose whole value is that the variants differ only in compute |
| One root folder with a variant switch (`count` or workspaces) | The two stacks could not be applied and destroyed on their own, and a plan would show both |
| Make `base/` own the ALB and WAF | Both variants would share one ALB, so they could not be tested one at a time, and `base/` would have to read a stack (breaks ADR-001) |
| **Shared module, one call per stack (chosen)** | Same code by construction; each stack file is short enough to read in one sitting |

## Driver

The comparison plan requires the same ALB design, health check, scaling metric, WAF rule and application settings on both variants. A module makes that true by construction instead of by discipline, and ADR-001 named this situation as its revisit trigger (a third stack and the risk of drift). It also makes the report's claim checkable: the entry layer is one block of code.

## Consequences

- **Resource addresses change** (they gain a `module.web_entry.` prefix). `ec2/` is destroyed between sessions and its state is empty, so this needs no state migration. It does mean `ec2/` must be applied again and re-verified, which was already needed for the ADR-013 settings.
- **Each stack's inputs are explicit.** A reader sees what differs between A and B in the two module calls and the compute files.
- **The application environment exists once**, so a setting cannot drift between EC2 and Fargate. The Fargate health-probe override (a separate decision) adds the one variable that is set at run time.
- **Indirection:** one more directory to open. The module has a short README of its inputs and outputs.
- **Provider configuration stays in each folder;** the module declares required providers only, so it never configures one.
- **Review:** the module and the refactored `ec2/` go through the independent review gate before anything is claimed as verified.

## Evidence that will back it

`terraform plan` in `ec2/` and in `fargate/` showing the same set of module resources, and a diff of the two plans' module portions that shows only the name prefix, the hostname and the target type differing. `smoke.sh` 8 of 8 on both.

## Revisit when

A third stack needs a different front door, or the module's inputs grow until a reader cannot tell what differs between the variants.
