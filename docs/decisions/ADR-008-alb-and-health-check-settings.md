# ADR-008: ALB, TLS and health-check settings

**Status:** implemented; the stacks it describes were applied and measured on 8 and 9 October 2026 (first drafted 1 October 2026). The numeric values are the ones in `src/infrastructure/modules/web-entry/alb.tf`; the 8 and 9 October runs used them.

## Decision

One internet-facing ALB per stack in the public subnets, with `sg-alb` accepting 443 and 80 from anywhere. Port 80 only redirects (301) to 443. Port 443 uses the shared ACM certificate and `ELBSecurityPolicy-TLS13-1-2-2021-06` (TLS 1.2 and 1.3). The target group is HTTP on 8000 with no stickiness; the health check is `GET /health/`, expecting 200, **every 10 s, timeout 5 s, healthy after 2, unhealthy after 3**; deregistration delay 30 s. The ASG health type is `ELB` with a 300 s grace period. Invalid header fields are dropped. The hostname is an alias record to the ALB.

## Options considered

| Option | Why not |
|---|---|
| HTTP only | The scope requires HTTPS end to end for the customer |
| Stickiness | Sessions and carts are in PostgreSQL; stickiness would hide the shared-state result the scope requires |
| ASG health type `EC2` | A running instance with a dead app would never be replaced |
| Default health check (30 s, 5 and 2) | A failed instance is detected in about 150 s; the chosen values detect it in about 30 s |
| **Values above (chosen)** | Detection in about 30 s (3 failures at 10 s); recovery then dominated by the 300 s grace period and boot time, which are what the replacement test measures |

## Driver (shop scenario)

A shop that is always open needs a failed instance replaced quickly and without a person; the time from failure to healthy again is a measured result (scale-out and replacement time).

## Consequences

- Health-check frequency adds a few requests per second per target; negligible at the project's scale.
- `/health/` is exempt from the HTTPS redirect and accepts the probe host, so the redirect never fails the check (checked in `config/settings.py` and `config/middleware.py`).
- The grace period must stay longer than boot to the first healthy response, or the ASG would replace an instance still booting; revisit if boot gets slower.
- Draining takes up to 30 s, so scale-in and replacement take at least that long.

## Evidence that will back it

Target group `describe-target-health` healthy; `curl -I http://<host>` returning 301; `curl -vI https://<host>` showing TLS 1.3 and the certificate; killing the instance and recording the time to a new healthy target.

## Revisit when

The replacement or scale-out measurements show detection or the grace period dominating, or the app's boot time changes.
