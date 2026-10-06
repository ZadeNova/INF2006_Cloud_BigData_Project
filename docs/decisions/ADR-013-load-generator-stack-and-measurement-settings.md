# ADR-013: A separate load-generator stack, one-minute monitoring and capacity pinning

**Status:** drafted by the writing session for review (6 October 2026). Written to the requirements in [load-harness.md](../plans/load-harness.md) section 10. Prices are from memory and unverified.

## Decision

- **`src/infrastructure/loadgen/`** is a third Terraform folder with its own state: one `c5.large` Amazon Linux 2023 instance in a `base/` public subnet with a public IP, `LabInstanceProfile`, **no inbound rules** (HTTPS out only), IMDSv2 required, 16 GB encrypted root volume, and user data that installs `python3.12`, `python3.12-pip`, `git` and `tmux`. Tag `Stack = loadgen`. A shell is opened with Session Manager; the harness and results move through the project bucket. It is up only during test sessions.
- **`ec2/` measurement settings.** Detailed monitoring on the launch template (instance metrics every minute, not every five). Auto Scaling group metrics at one-minute granularity: `GroupDesiredCapacity`, `GroupInServiceInstances`, `GroupPendingInstances`, `GroupTerminatingInstances`.
- **Capacity pinning.** Variables `min_capacity`, `max_capacity` and `desired_capacity` (the same names in `ec2/` and `fargate/`; defaults 1, 2, 1, the ADR-011 values), checked so min is at most desired is at most max. Setting all three to the same number gives a fixed-capacity run.
- **No extra outputs:** the capture script derives the load balancer, target group and database identifiers itself (review INF-010), so none were added.
- **The WAF is not changed:** load runs keep the `count` default.

## Options considered

| Option | Why not |
|---|---|
| Generate load from the laptop | The home connection and Wi-Fi would be in every latency figure, and 1,000 users would saturate it; the run would not measure the app |
| Run the generator on an app instance | It takes CPU from the thing being measured |
| Put the generator in `base/` | `base/` stays up between sessions; the generator should cost money only while it is used, and a stack can be destroyed without touching the database |
| A burstable generator (`t3`) | CPU credits would limit the generator in the middle of a run; the harness fails a run when generator CPU exceeds 70% |
| Five-minute instance metrics | A scale-out or replacement lasting two to four minutes would be one or two points on the graph |
| Pin capacity by editing the `.tf` before each run | An edited file is not a recorded commit; a variable value is shown in the plan and in the run's metadata |
| **Separate stack, detailed monitoring, pinning variables (chosen)** | Matches what the harness records and keeps the two variants comparable |

## Driver

The comparison is only as good as its measurements: the generator must not be the bottleneck or the noise, and the evidence needs timelines fine enough to show a scale-out. The scale assumption for the shop is small (about 15 concurrent visitors at peak); the 1,000-user levels exist to find where each variant saturates, not to size the shop.

## Consequences

- **Cost.** A `c5.large` is about USD 0.085 an hour while up. Detailed monitoring adds a small per-instance charge (about USD 2.10 per instance per month, about 3 US cents a day). Group metrics at one-minute granularity are free to publish. All unverified; the runbook records the measured cost of each session.
- **New instances only.** The monitoring setting reaches instances launched from the new template version. An instance already running keeps five-minute metrics until it is replaced (`start-instance-refresh`). With the stack torn down between sessions, the next `up.sh` launches new instances.
- **Applying `ec2/` resets the desired capacity** to the variable's value, even if scaling had moved it. That is intended for pinning, and it means an apply during a session returns the group to the variable's value.
- **A fixed run is a real pin:** with min, max and desired equal, the target-tracking policy still exists but cannot change the count. Free-scaling runs use the defaults.
- **The generator keeps its AMI** (`ignore_changes = [ami]`), so a new Amazon Linux release cannot replace it in the middle of a campaign. Replace on purpose with `terraform apply -replace=aws_instance.loadgen`.
- **Clock check.** The harness checks time sync with `chronyc tracking`. That relies on the Amazon Time Sync Service (link-local address) being reachable through the security group; AWS documents that security groups do not filter it, but it is unverified until the first session.
- Load from one IP meets the login rate rule only in `count` mode, which records and never blocks.

## Evidence that will back it

`terraform plan` showing `loadgen/` and the `ec2/` changes, the instance ID, a Session Manager shell on the generator with the tools installed (`/var/lib/loadgen-ready` present), one-minute CPU and group-capacity points in CloudWatch during a run, and `stack.json` of a run showing the pinned min, max and desired.

## Revisit when

The pilot shows the generator above 70% CPU (use a larger instance and say so in the results), or the lab refuses the instance type or detailed monitoring.
