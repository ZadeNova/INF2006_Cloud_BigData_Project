# Architecture contract

Status: planned, not deployed. Read the [scope](../PROJECT_SCOPE_INF2006.md).

## Flows and responsibilities

- Browser -> HTTPS ALB -> Django/Gunicorn containers in EC2 ASG -> private RDS PostgreSQL.
- Django renders templates and HTMX fragments. WhiteNoise serves packaged, versioned static assets. No independent frontend service.
- Private S3 -> authorised validation/import command -> PostgreSQL -> aggregation command -> summary tables -> protected dashboard.
- CloudWatch collects sanitised logs and infrastructure metrics.
- Django database sessions and persistent carts are shared by all instances with shared signing configuration. Stickiness disabled.

Foundation package paths: src/config/ holds project configuration/WSGI; src/accounts/, src/catalogue/, src/cart/, src/orders/ and src/reporting/ are domain packages. Frontend-owned directories are src/templates/ and src/static/. Local Docker web/db configuration and framework migrations are verified in batch 2; custom schema, health and business behaviour remain separate work. The local Compose deployment is not evidence of AWS deployment. Use explicit business functions callable from views/commands; avoid signals that deduct stock during historical import.

Configuration selects local PostgreSQL/files or AWS RDS/S3 without duplicate business implementations. Backend validates all state transitions; frontend presents outcomes.

## Failure boundaries and alternatives

Replaceable app instances do not guarantee invisible failures. Retry uncertain checkout with the same key. Single-AZ RDS and the designated analytics scheduler remain shared availability limitations. Never confirm an order when the database commit is uncertain.

If adopted, ElastiCache serves disposable catalogue/analytics reads with bounded expiry and explicit database fallback. Cache outage increases database load; this does not classify the whole app as CP/AP.

- One Django deployment reduces integration work compared with a separate SPA/API.
- Managed RDS demonstrates cloud persistence; local Docker PostgreSQL supports reproducibility and INF2003.
- ALB/ASG provide measurable app scaling. Queues/microservices are outside baseline.
- CloudFront omitted for current workload/budget; private S3 retained for datasets/exports.

Create the submission diagram during implementation with users, services, trust boundaries, flows and observability. Planned output: `evidence/architecture.png`; do not claim it exists before creation. INF2003 extends the preserved submission later.
