# ADR-004: One RDS PostgreSQL 17 instance, `db.t4g.small`, shared by both variants

**Status:** implemented; the stacks it describes were applied and measured on 8 and 9 October 2026 (first drafted 1 October 2026). Settings below are carried from the earlier stage 2 plan; the class and sharing are the new decisions.

## Decision

One RDS instance in `base/`: PostgreSQL 17, `db.t4g.small` (2 vCPU, 2 GiB), gp3 20 GB encrypted with the AWS-managed key, private subnets only, `sg-db` only, Single-AZ by default, `rds.force_ssl = 1`, 7-day automated backups, RDS-managed master password (never in Terraform state), no initial database, PostgreSQL log exported to a 7-day log group created first. **One size for every recorded run and for the submission**; it changes only through the pilot gate in the plan (section 3), between runs.

## Options considered

| Option | Why not |
|---|---|
| `db.t4g.micro` (the old stage 2 default) | 1 GiB leaves little headroom for the 1,000-user step; a failure there would be a finding about the database, not about EC2 versus Fargate |
| `db.t4g.medium` or larger | The database sees about 2 to 3 queries per second at peak and about 200 at the top step, a few percent of one vCPU; the dataset is a few hundred MB |
| Fixed-performance class | Costs more for a load that averages low; revisit if promotions are long and frequent |
| One database per variant | The variants would differ in two ways; the comparison needs the same database |
| Read replica, Aurora Serverless v2 | The frozen app has one connection and no read routing; Aurora is a different engine from the one the bootstrap and security checks were built against |
| **`db.t4g.small`, shared (chosen)** | About USD 0.032 per hour (verify); unlimited-mode burstable never throttles and bills a small surcharge |

## Driver (shop scenario)

One small shop with one database; the comparison must not be limited or confounded by it, so it is sized once, from a measured pilot, and not changed mid-comparison.

## Consequences

- Both stacks use this database; a stack's own `sg-db` rule opens 5432 from its own `sg-app`.
- Single-AZ means a database failure takes the shop down. A Multi-AZ failover test was planned and **not run**; the single point of failure is a stated limit (README, report section 3).
- **Why one instance and not two.** A read replica spreads reads and gives no automatic failover; the app has no read routing and the measured RDS CPU was at most 10.46% (A) and 9.09% (B). Multi-AZ is the setting that fits availability (the subnet group already spans two AZs; `multi_az = true` is one change at about twice the instance charge). It was not enabled for cost and time. Automated backups (configured for 7 days, restore not tested) and a Terraform plus checksummed-dataset rebuild are the only recovery measures.
- `skip_final_snapshot`, no deletion protection and `delete_automated_backups` let teardown finish in one command; a manual snapshot during the evidence runs is the recovery evidence.
- Enhanced Monitoring is off: it needs an IAM role the lab cannot create.

## Evidence that will back it

RDS CPU, connections, free memory and credit balance read during the saturation run (the 1,000-user pilot was replaced by it; `evidence/test-performance.md` LOAD-01); `describe-db-instances` showing private, encrypted, engine 17.x, backups 7 days; `rds.force_ssl` in the parameter group.

## Revisit when

The pilot shows CPU not comfortably low (size up once, then rerun affected runs); promotions are frequent or last many hours (fixed-performance class); or the lab refuses the class (fall back to `db.t3.small` and say so).
