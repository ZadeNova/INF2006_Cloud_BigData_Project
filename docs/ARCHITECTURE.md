# Architecture contract

> Final architecture: variant B (ECS on Fargate), ADR-018. Variant A (EC2) = evaluated alternative.

> **Note (updated 9 October 2026):** this document describes both variants: A (EC2 + Auto Scaling group, the evaluated alternative) and B (ECS on Fargate). The final architecture is variant B ([ADR-018](decisions/ADR-018-final-architecture-ecs-fargate.md)).

Status (9 October 2026): `base/` and variant A (`ec2/`) were applied and verified on 1 October 2026 and the `ec2/` stack is torn down between work sessions; variant B (`fargate/`) was applied and measured on 9 October 2026 and, like variant A (8 October), is torn down; only `base/` remains. Load, scaling and recovery results (one repeat each, indicative, n = 1) are in the [evidence index](../evidence/README.md) ([runbook](../evidence/aws-build-runbook.md), [how to run it](../src/infrastructure/README.md)). Read the [scope](../PROJECT_SCOPE_INF2006.md).

## Flows and responsibilities

- Variant A, the evaluated alternative (measured on 8 October 2026): Browser -> HTTPS ALB -> Django/Gunicorn containers in EC2 ASG -> private RDS PostgreSQL.
- Variant B, the final architecture (measured on 9 October 2026): Browser -> HTTPS ALB -> Django/Gunicorn container as an ECS Fargate task -> the same private RDS PostgreSQL. Only the compute layer differs; see [AWS_INFRASTRUCTURE.md](AWS_INFRASTRUCTURE.md#variant-b-ecs-on-fargate-built-and-measured-the-final-architecture).
- Django renders templates and HTMX fragments. WhiteNoise serves packaged, versioned static assets. No independent frontend service.
- Private S3 -> authorised validation/import command -> PostgreSQL -> aggregation command -> summary tables -> protected dashboard.
- CloudWatch collects sanitised logs and infrastructure metrics; SNS alarm notifications and a regional WAF (one rate-based rule on `POST /login/`) are applied on both variants; CloudTrail is the account's default event history. Their behaviour under failure and attack was tested once per variant: see the [evidence index](../evidence/README.md).
- ECR supplies the shared application image. Secrets Manager supplies database credentials and the shared Django signing key through runtime roles; denial blocks deployment. Systems Manager Session Manager provides administration and one-off jobs without SSH.
- Included descriptive ML trains offline in `analytics/`. Selected flow: explicitly triggered offline batch -> validated assignment import -> protected dashboard. Saved-model inference and Lambda are not part of the plan (user decision, 3 October 2026); EventBridge Scheduler is an optional side quest. Local training/loading remain available and the web image has no ML dependency.
- Batch handoff uses explicit completed run/file selections and independently configured deployment/database association. The producer and loader share only a standard-library contract in `src/reporting/segment_contract.py`; training libraries remain isolated. See [batch contract](ANALYTICS.md#explicit-batch-handoff-contract) and [operations](../analytics/README.md#included-descriptive-ml-explicit-batch-handoff).
- Product images and `.glb` 3D models are static files in the image, served by WhiteNoise with hashed, cache-forever URLs; nothing is read from S3 by browsers (decided 29 September 2026). Alternative considered: private S3 media with pre-signed URLs and CORS, not selected because for a small, fixed asset set it adds a service, per-request signing and a CORS policy without benefit at this scale; at catalogue scale the assets would move to S3 behind CloudFront. See [the comparison plan, section 13](plans/aws-ecs-comparison.md).
- Django database sessions and persistent carts are shared by all instances with shared signing configuration. Stickiness disabled.

Foundation package paths: src/config/ holds project configuration/WSGI; src/accounts/, src/catalogue/, src/cart/, src/orders/ and src/reporting/ are domain packages. Frontend-owned directories are src/templates/ and src/static/. Local Docker web/db configuration and framework migrations are verified in batch 2; initial domain schema and sealed inventory persistence are supplied by batch 3; batch 4 supplies process health and separate database readiness; the business workflows (auth, catalogue, cart, checkout, order history, import, analytics refresh and dashboard) are implemented locally on top of that. The local Compose deployment is not evidence of AWS deployment. Use explicit business functions callable from views/commands; avoid signals that deduct stock during historical import.

Configuration selects local PostgreSQL/files or AWS RDS/S3 without duplicate business implementations. Backend validates all state transitions; frontend presents outcomes.

## Failure boundaries and alternatives

Replaceable app instances do not guarantee invisible failures. Retry uncertain checkout with the same key. Single-AZ RDS and the designated analytics batch runner remain shared availability limitations. Never confirm an order when the database commit is uncertain.

If adopted, ElastiCache serves disposable catalogue/analytics reads with bounded expiry and explicit database fallback. Cache outage increases database load; this does not classify the whole app as CP/AP.

- One Django deployment reduces integration work compared with a separate SPA/API.
- Managed RDS demonstrates cloud persistence; local Docker PostgreSQL supports reproducibility.
- The final architecture is variant B (ECS on Fargate, [ADR-018](decisions/ADR-018-final-architecture-ecs-fargate.md)); the ALB/ASG variant A was measured against it as the evaluated alternative ([plan](plans/aws-ecs-comparison.md)). Queues/microservices are outside baseline.
- CloudFront omitted for current workload/budget; private S3 retained for datasets and exports.
- Service-model alternatives (Lambda, EKS, Elastic Beanstalk, ECS Fargate, a separate analytics service) are argued against workload-derived decision drivers in [PROBLEM_FRAMING_AND_ARCHITECTURE.md](PROBLEM_FRAMING_AND_ARCHITECTURE.md). Provisioning is Terraform-first ([comparison plan](plans/aws-ecs-comparison.md), [decisions](decisions/)).

The submission diagram is [evidence/architecture.png](../evidence/architecture.png) (users, services, trust boundaries, flows, observability); its text version, with every label mapped to Terraform and evidence, is [evidence/architecture.md](../evidence/architecture.md).

Local startup uses root compose.yaml to include src/compose.yaml (Compose 2.20+). The one-off migrate service waits for healthy PostgreSQL; web waits for migration success. This preserves the existing local project/volume and does not change the separate AWS coordinated-migration strategy.
