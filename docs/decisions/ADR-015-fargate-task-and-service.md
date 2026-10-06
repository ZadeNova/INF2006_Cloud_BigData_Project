# ADR-015: The Fargate task and service

**Status:** drafted by the writing session for review (6 October 2026). Settings are the starting values; the load runs measure them. Prices are from memory and unverified.

## Decision

- **Task:** 2 vCPU and 4 GB (`task_cpu = 2048`, `task_memory = 4096`), x86_64, one container named `web`, started from the image **digest** that the `ec2/` stack also runs. Network mode `awsvpc`.
- **Roles:** the lab's `LabRole` is both the execution role (pulls the image, writes logs) and the task role (the app reads Secrets Manager). The lab forbids creating IAM roles. `config/secrets.py` already accepts the task role as a credential source.
- **Network:** public subnets, a public IP on the task, no NAT gateway. The task's security group (from the shared module) accepts port 8000 from the ALB only.
- **Service:** one task wanted at the start; rolling update that starts the new task before stopping the old one (minimum healthy 100%, maximum 200%); deployment **circuit breaker with rollback**; a 120 s health-check grace period; `wait_for_steady_state` so an apply that leaves a failing service fails.
- **Stop time:** 30 s (`stopTimeout`), the same as the ALB's deregistration delay, so a stopping task finishes its requests.
- **Logs:** the `awslogs` driver into the module's log group (7 days), stream prefix `web`.
- **Left out:** ECS Exec and Container Insights.

## Options considered

| Option | Why not |
|---|---|
| Smaller task (0.5 or 1 vCPU) | The comparison matches compute: the `c5.large` has 2 vCPU and 4 GiB, and a mismatch would be the first thing a reviewer questions |
| ARM (Graviton) tasks | Cheaper, but the image and the `c5.large` are x86_64; a different architecture would confound the result |
| Fargate Spot | Tasks can be reclaimed at any time, which breaks the repeated, comparable runs |
| A NAT gateway and private subnets | About USD 1 a day plus data for no gain in the comparison; the ALB-only security group already keeps the task unreachable (ADR-007) |
| Container Insights | A charge per metric and per GB of logs; the ALB's healthy-host count and the service's own CPU and memory metrics are enough, and the capture script falls back to them |
| ECS Exec | Needs extra permissions on the role and gives a shell on a task; jobs run as one-off tasks and logs are in CloudWatch |
| Secrets injected by ECS (`secrets` in the task definition) | The app already fetches its own secret at start-up, as on EC2; two mechanisms would be a difference in the comparison |
| Docker health check in the task | The ALB check is the one that matters for routing, and the image has no `curl` |
| **The settings above (chosen)** | Matched to variant A wherever the platform allows |

## Driver

The comparison plan: same image, same database, same ALB behaviour, matched compute, one change (what runs the container). The shop's own load is small (about 15 concurrent visitors at peak), so the size is chosen for a fair comparison, not for capacity.

## Consequences

- **Cost.** About USD 0.099 an hour for one task (2 vCPU at about USD 0.0405 and 4 GB at about USD 0.0044 per hour), against about USD 0.085 for the `c5.large`. Unverified; the runbook records the measured cost of each session.
- **Faster start, different behaviour.** A task is expected to become healthy in about one to two minutes, an instance in three to four. That is a measured result, not a setting.
- **Security group cleanup.** A stopped task's network interface can linger for a short time, so destroying the stack may wait on the security group. Terraform retries; the README's troubleshooting says so.
- **Quota unknown.** The Fargate vCPU quota cannot be read in the lab; the maximum is 2 tasks (4 vCPU) and the first scale-out is the real test.
- **Deploy safety:** a bad image stops at the circuit breaker and returns to the old task; a failed first apply fails the apply.

## Evidence that will back it

`terraform plan`, the task definition (digest equal to the `ec2/` stack's), the service reaching steady state, `smoke.sh` 8 of 8, logs in `/inf2006-grp21-fargate/app`, a stopped task replaced by the service, the measured start time.

## Revisit when

The lab refuses `LabRole` as a task or execution role, the Fargate quota blocks a second task, or the pilot shows the task size is the limit.
