# ADR-018: The final architecture is variant B (ECS on Fargate); variant A stays as the evaluated alternative

**Status:** decided by the user on 9 October 2026, after both variants were measured. Group 21, INF2006.

## Decision

The 42Factors shop runs as **variant B**: the Django container on **Amazon ECS with Fargate**, behind an Application Load Balancer (HTTPS, TLS 1.3/1.2 policy, 80 to 443 redirect, WAF rate rule on `POST /login/`), with **RDS PostgreSQL** (`db.t4g.small`, private), Secrets Manager, ECR, S3, Route 53, ACM and CloudWatch. Variant A (EC2 + Auto Scaling group) was built from the same shared module and measured under the same harness. It remains in the repository as the **evaluated alternative**; the final-architecture instructions ([REPRODUCE_CLOUD.md](../REPRODUCE_CLOUD.md)) use B only.

Service model: containers on a managed compute platform (PaaS-leaning; the team owns the image, the platform owns the hosts). Deployment model: public cloud, single region (the Learner Lab only offers us-east-1; production would use ap-southeast-1).

## Why B

The decision driver is the **operator**: a small shop with 1 to 3 engineers and no dedicated operations person. Both variants served the measured load with **zero errors**, so the choice does not rest on capacity.

| Evidence (indicative, one repeat each) | A: EC2 + ASG | B: ECS Fargate | Source |
|---|---|---|---|
| Errors across all runs | 0 | 0 | [load-summary.md](../../evidence/load-summary.md) |
| Replacement of a killed unit, to healthy | 114 s | **50 s** | RES-03 replace |
| Scale-out, alarm to healthy | 161 s | **101 s** | RES-03 scale-out |
| Errors during replacement | 0 | 0 | RES-03 replace |
| Practical capacity, one unit (page actions/s) | **46.5** | 44.0 | saturation |
| Maximum throughput, one unit (requests/s) | **118.8** | 105.5 | saturation |
| Price per unit-hour (list, unverified) | **$0.085** | $0.099 | `tests/load/prices.json` |
| Price per 1,000 requests at the ceiling | **$0.00027** | $0.00035 | same |
| Hosts to patch, AMI, SSM access | yes | **none** | design |

B is ahead where a small team feels it (no operating system to patch, faster recovery and scale-out). A is ahead on raw ceiling and price. Both ceilings are about **100 times the assumed peak** of the shop.

## Weighted comparison and how sensitive it is

Weights were locked on 3 October 2026 (before any run) in [docs/plans/load-harness.md](../plans/load-harness.md). Scores use the harness formula (best value = 10, other = 10 x best / value; a tie scores 10 each). Operational burden is a **judgement** supplied by the user, not a measurement: **A 7, B 9** (less developer setup on Fargate, easier to scale, better for a small company). With one repeat per condition every difference is **indicative, n = 1**, so the total is shown to explain the choice, not to prove it.

| Criterion | Weight | A | B |
|---|---|---|---|
| Operational burden (judgement 7 vs 9) | 25 | 7.8 | 10 |
| Replacement time and error window | 25 | 7.2 | 10 |
| Steady-state latency (low-load p95 within 5%, tie) | 20 | 10 | 10 |
| Cost per 1,000 requests | 15 | 10 | 8.0 |
| Scale-out time | 10 | 6.3 | 10 |
| Capacity per unit | 5 | 10 | 9.5 |
| **Weighted total (out of 10)** | | **8.4** | **9.7** |

| If we change the inputs | A | B | Reading |
|---|---|---|---|
| As above | 8.4 | 9.7 | B ahead |
| Operational burden treated as equal | 8.9 | 9.7 | B still ahead (recovery and scale-out) |
| Operational burden and replacement both neutral | 9.6 | 9.7 | **Tie** (0.1 apart, far inside the noise of n = 1) |
| Cost weight raised to 40, others scaled down in proportion | 8.9 | 9.2 | B still ahead, narrowly |
| Cost only (weight 100) | 10 | 8.0 | A ahead |

**Honest reading:** B wins because of operating burden and recovery speed. Remove both and the two are equal. That is exactly the argument for B for a small team, and it is also why the choice would reverse for a team that already runs fleets of instances and counts every cent.

## Alternatives considered (and not chosen)

| Alternative | Why not |
|---|---|
| **A: EC2 + Auto Scaling group** | Measured, sound, slightly cheaper and higher ceiling. Not chosen: hosts to patch, slower recovery, more to set up by hand. Kept as the comparison. |
| **AWS Lambda / API Gateway** | The Django app is a long-running web process with a connection pool; a rewrite for cold starts and connection limits buys nothing at this scale. |
| **Amazon EKS** | A control plane to run for a single service; far above a 1 to 3 engineer team's need. |
| **Elastic Beanstalk / App Runner** | Hide the networking and scaling choices the project must show, and the Learner Lab restricts some of their roles. |

## Growth path (not tested beyond what is stated)

One task carries about 100 requests/s (about 3,000 browsing shoppers at a 36 s think time, an estimate). Beyond the measured range the first things to change, in order: raise `max_capacity` (a variable); pre-scale for campaigns (scale-out took 101 s); **the database** (`db.t4g.small`, single AZ, burstable, never load-tested past one task): RDS Proxy, a larger class, Multi-AZ, then a read replica; move static files and the `.glb` models (about 15 MB, served from the app) to S3 and CloudFront; private subnets with NAT, WAF in block mode, and least-privilege IAM roles (the lab forbids custom roles, so both variants use `LabRole`). **Untested:** more than 2 tasks, and any database ceiling.

## Consequences and limits

- B must stand alone from a fresh account: [ADR-019](ADR-019-variant-b-sets-up-its-own-database.md). Its Fargate database jobs are tested offline with a stubbed `aws`; a run in AWS and a from-nothing rebuild are not part of the evidence unless stated in [REPRODUCE_CLOUD.md](../REPRODUCE_CLOUD.md).
- Both variants ran on the same image digest, RDS class and gunicorn settings (2 sync workers, frozen Dockerfile). The 2 workers, not the CPU, set the per-task ceiling.
- CPU credits and caches cannot be reset between variants (the RDS credit balance stayed at 576). A ran on 8 October and B on 9 October: time of day and CPU model differ (Xeon 8124M vs 8259CL).
- The harness does not fetch the `.glb` models (decision D1), so bandwidth is not measured.
