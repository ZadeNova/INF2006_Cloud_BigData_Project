# ADR-007: Variant A compute: `c5.large`, one instance, public subnets, no NAT

**Status:** drafted by the writing session for review (1 October 2026).

## Decision

Variant A runs Docker on one Amazon Linux 2023 `c5.large` (2 vCPU, 4 GiB, non-burstable), launched by an Auto Scaling group (min = max = desired = 1 for now) from a launch template, in the two public subnets with a public IPv4 address and no NAT gateway. `sg-app` accepts only port 8000 from `sg-alb`, there is no port 22, IMDSv2 is required (hop limit 2 so containers reach the role credentials), the root volume is encrypted gp3 16 GB, and the image runs by digest. The CPU-credit setting is applied only to burstable (`t`) types.

## Options considered

| Option | Why not |
|---|---|
| `t3.small` (the stage 2 default) | Burstable: under a long load test it slows to its baseline, which would confound the comparison with Fargate |
| Larger types | Cost with no benefit at these loads; matched compute is the point |
| Private subnets with NAT or VPC endpoints | A NAT gateway is about USD 0.045 per hour plus data; endpoints cost per hour too. Neither is justified for a short lab sprint; the trade-off is stated in the report |
| Several instances from the start | Scaling is shown by the policy, not by pre-provisioning |
| **`c5.large`, public subnets, one instance (chosen)** | Matches Fargate 2 vCPU / 4 GB; no credit effects; cheapest secure network |

## Driver (shop scenario)

At about 15 concurrent visitors one small instance carries normal load, so the instance is sized for a fair comparison, not for the shop. The lab has no Singapore region and a small budget, so the cheapest secure network is chosen and its limits are stated.

## Consequences

- Instances have public IPs but nothing can connect in; production would use private subnets with NAT or endpoints.
- `c5.large` is untested in the lab; the fallback is `c5a.large` or `m5.large`, and the results say so.
- The AMI follows "latest Amazon Linux 2023": known drift, stated in the write-up.

## Evidence that will back it

`describe-instances` showing the type, IMDSv2 `required` and no key pair; `describe-security-groups` showing no port 22; the instance healthy behind the ALB.

## Revisit when

The lab refuses the type, or the pilot shows the instance, not the database, limits a run in a way a larger size would change.
