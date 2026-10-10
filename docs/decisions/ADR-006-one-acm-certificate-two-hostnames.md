# ADR-006: One ACM certificate for the two shop hostnames, validated in Terraform

**Status:** implemented; the stacks it describes were applied and measured on 8 and 9 October 2026 (first drafted 1 October 2026).

## Decision

`base/` owns one ACM certificate with `shop-ec2.fourtytwofactors.me` as its name and `shop-fargate.fourtytwofactors.me` as the alternative name, validated by DNS (CNAME records in the Route 53 zone, created by Terraform). `certificate_arn` is output only after validation completes. Each stack attaches it to its HTTPS listener and creates the alias record for its own hostname.

## Options considered

| Option | Why not |
|---|---|
| One certificate per stack | A destroyed stack would drop its certificate and need validation again, which is slow and sits in the middle of every run |
| Wildcard `*.fourtytwofactors.me` | One record, but valid for any future hostname; this project needs exactly two |
| Email validation | Manual and not repeatable |
| Manual DNS validation at Namecheap | The fallback in ADR-003 only if delegation fails |
| **One certificate in `base/`, two names (chosen)** | Issued once, survives stack teardown, free, no manual step |

## Driver (shop scenario)

The comparison creates and destroys stacks repeatedly; HTTPS must work at each stack's own name the moment its ALB exists, and TLS termination at the ALB is a required part of both variants.

## Consequences

- `terraform apply` in `base/` blocks until ACM reports ISSUED, which needs the Namecheap name servers to be live. It fails by timeout if they are not.
- Adding a third hostname changes the certificate; `create_before_destroy` keeps an attached ALB from blocking the replacement.
- The validation records are never removed between runs.

## Evidence that will back it

`aws acm describe-certificate` showing `ISSUED` and both names; `curl -vI https://shop-ec2.fourtytwofactors.me` showing the certificate chain once a stack is up.

## Revisit when

A hostname is added or removed, or delegation fails (use the manual fallback in ADR-003).
