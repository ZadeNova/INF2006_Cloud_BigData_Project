# ADR-003: Route 53 hosted zone in `base/`, delegated from Namecheap, time-boxed

**Status:** drafted by the writing session for review (1 October 2026).

## Decision

`base/` creates the Route 53 hosted zone for `fourtytwofactors.me`, and later the certificate and its DNS validation records. Each stack adds an alias record for its own hostname (`shop-ec2.`, `shop-fargate.`). The order is fixed: (1) create the zone and see whether the lab allows it; (2) only then set the four Route 53 name servers at Namecheap and wait for delegation (`dig NS`); (3) validate the certificate in Terraform. If the lab denies the zone, or delegation does not work by the time the ALB is ready, fall back to manual ACM validation and one CNAME per ALB at Namecheap. The zone is kept until final teardown.

## Options considered

| Option | Why not |
|---|---|
| Records at Namecheap only | Every recreated ALB means a manual DNS edit, and the validation record is a manual step too; both break "one command per stack" |
| **Route 53 zone, Terraform alias records (chosen)** | A recreated ALB needs no DNS change; validation is automatic |
| Subdomain-only delegation | Same effort at Namecheap with no benefit for one domain |

## Driver (shop scenario)

The comparison creates and destroys each stack's ALB many times; a hostname that follows the ALB automatically removes a manual step from every run and from the cloud reproduction guide. Cost is about USD 0.50 per month.

## Consequences

- Changing the name servers at Namecheap before the zone exists, or switching back after, makes Namecheap's own records stop or start applying, and delegation takes time to propagate.
- A destroyed and recreated zone gets new name servers: do not destroy it between runs.
- `force_destroy = true` so the final teardown cannot be blocked by leftover records.

## Evidence that will back it

`terraform apply` output showing the zone, `dig NS fourtytwofactors.me` returning the four Route 53 servers, and the certificate status `ISSUED`.

## Revisit when

The lab denies hosted-zone creation (use the fallback and record it), or delegation is not working in time.
