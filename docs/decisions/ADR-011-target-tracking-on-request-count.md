# ADR-011: Scale on requests per instance (target tracking), 1 to 2 instances

**Status:** drafted by the writing session for review (1 October 2026). The target value is a starting point to be tuned from the load rehearsal and recorded.

## Decision

An Auto Scaling target-tracking policy on `ALBRequestCountPerTarget` with a target of **300 requests per instance per minute** (variable `scale_target_requests`), instance warm-up 240 s, minimum 1, maximum **2**. Scale-in uses the policy's default cooldown, so one instance returns after a sustained quiet period.

## Options considered

| Option | Why not |
|---|---|
| Scale on CPU | CPU lags the load and depends on the instance type; request count scales with demand directly and is the same metric the Fargate variant can use, which keeps the comparison fair |
| Step scaling with alarms | More settings to justify for the same result |
| Scheduled scaling | The workload is not predictable by the clock |
| Fixed two instances | Costs always, and shows no scaling |
| Maximum above 2 | More cost; one extra instance already demonstrates scale-out and the effect of a second target |
| **Target tracking, requests per target (chosen)** | One number to defend; works with the ALB's own metric |

## Driver (shop scenario)

At the design peak of about 15 concurrent visitors (about 0.4 dynamic pages per second), one instance is enough: scaling gives burst headroom and replacement, not capacity the shop needs. The target is set low enough that the load test can trigger it with realistic client counts, and the report says so.

## Consequences

- A new instance takes about 3 to 4 minutes to become healthy (Docker install, image pull), so scale-out is measured in minutes; this is a reported result, and the warm-up must stay longer than boot.
- Two instances share one database; sessions and carts are in PostgreSQL, so any instance serves any request.
- The maximum of 2 caps the cost of a runaway load test.

## Evidence that will back it

The load run showing the group going from 1 to 2 instances, the time from trigger to a healthy second target, the ALB request-count and instance-count graphs, and scale-in afterwards.

## Revisit when

The rehearsal shows the target too high to trigger, or too low so it scales on ordinary use.
