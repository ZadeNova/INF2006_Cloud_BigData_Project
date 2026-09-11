# INF2006 Project Scope: E-Commerce Core with Sales and Inventory Analytics

**Status:** Agreed planning baseline, 11 September 2026  
**Team:** Five members  
**Deadline:** Sunday, 11 October 2026, 11:59 PM, Singapore time  
**Budget:** User-reported AWS student accounts accessed through Canvas, USD 40 credits per member  
**Decision:** Analytics is required. Customer-segmentation ML is optional.  
**Data:** LaelaZ synthetic-ecommerce is the selected source, subject to downloaded-file validation; generate missing application fields separately.  
**Progression:** The submitted INF2006 application becomes the foundation for INF2003, which expands its database functionality locally.

## 1. Purpose and intended outcome

Build a small ecommerce application where a customer can register, browse products, manage a cart, complete a simulated checkout, and view their orders. A store operator can use a protected analytics page to identify sales trends and products requiring replenishment attention.

The project demonstrates a secure, working AWS deployment with persistent data, reproducible analytics, measured scaling and recovery, and traceable evidence. It targets strong performance across the assessment rubric; no feature list can guarantee an A or A+.

The user problem is twofold: customers need reliable order placement, and a small store operator needs understandable sales and inventory information. Technical choices must support these workflows.

## 2. Scope boundaries

### Required

- Registration, login, logout, product browsing, cart, checkout, order confirmation and order history.
- Correct server-side pricing, inventory updates, duplicate-request handling and access control.
- Sales and inventory analytics, including explainable replenishment flags.
- AWS deployment, S3 object storage, infrastructure configuration, monitoring, security controls and scaling/recovery evidence.
- Reproducible dataset import, supplemental data generation, processing and testing.
- Complete submission package, report and contribution records.

### Optional, only after the required work passes

- Customer segmentation using a small scikit-learn model.
- Minor interface refinements that improve clarity or accessibility.

### Outside INF2006

- Real payment processing or storing payment-card details.
- Fraud detection, recommendation engines, reviews, seller marketplaces or delivery integration.
- Full product-management tooling; the operator page is read-only and products are seeded.
- MongoDB, database-engine benchmarking and extensive catalogue/search features.
- SQS, ElastiCache, Kubernetes or a separate ML microservice unless a later measured need justifies a deliberate scope revision.

## 3. Locked technology stack

| Area | Selection | Reason |
|---|---|---|
| Backend | Django | Integrated authentication, ORM, migrations, templates and validation |
| Frontend | Django templates, HTML/CSS, HTMX and minimal JavaScript | One deployable application and a small number of pages |
| Database | PostgreSQL; Amazon RDS in AWS | Transactions, constraints and straightforward local portability |
| Web serving | Gunicorn + WhiteNoise with versioned static assets packaged in the image | Same production static-file configuration across replaceable application instances |
| Packaging | Docker; Docker Compose locally | Same application runs with local PostgreSQL and RDS |
| Analytics | Django management commands and SQL, with pandas where useful | Reproducible transformations without a separate platform |
| Optional ML | scikit-learn | Small offline-trained model; no dedicated inference infrastructure |
| Infrastructure | Terraform | Reviewable, repeatable provisioning and teardown |
| Cloud | EC2, ALB, Auto Scaling Group, RDS, S3, CloudWatch | Deployment, routing, elasticity, database/object storage and operations |
| Secrets/access | IAM instance role and Secrets Manager where permitted | Avoid credentials in code and limit access |
| Testing | pytest/pytest-django and Locust | Correctness, security, analytics and controlled load tests |

Pin supported dependency and image versions during week one. Do not change frameworks after the core workflow is underway. Student-account permissions for AWS services are an early verification task, not an assumed entitlement.

### Frontend design reference

Use the selected Starbucks-inspired `DESIGN.md` as a visual reference for cream surfaces, green accents, rounded cards and pill buttons. Its intended project location is the repository root; the supplied reference was read from Downloads. Implement styling through reusable Django templates and shared CSS. Use the project's own branding and appropriately licensed imagery/fonts, with a system font or Inter instead of proprietary fonts. Standardise inconsistent rem/pixel values and verify focus states, contrast, labels and mobile layouts. Design examples do not add rewards, careers or drink-customisation features to this scope. Record source attribution.

## 4. Application features and correctness

### Customer workflow

1. Register and authenticate using Django's session-based authentication.
2. Browse a seeded product list with names, categories, prices and indicative stock.
3. Add, update or remove cart items.
4. Submit checkout with a request identifier.
5. Receive a saved order confirmation and access personal order history.

### Checkout rules

- Use a simulated payment result; make this clear in the interface.
- Derive prices, totals and user identity on the server. Never trust a submitted total or another user's identifier.
- Store monetary values as decimals and record unit price at purchase.
- Create the order, order items and stock updates in one database transaction.
- Use row locking or conditional updates so concurrent purchases cannot make stock negative. Acquire multiple product locks in a consistent order.
- Use an idempotency key scoped to the authenticated user. Repeated equivalent requests return the original outcome; reuse with a different cart is rejected.
- Failed checkout leaves no partial order or stock deduction.
- A cart does not reserve stock. Recheck availability during checkout.
- Only the order owner can retrieve an order. Only an authorised operator can access analytics.

### Data model

| Entity | Required information |
|---|---|
| User / CustomerProfile | Django authentication and permissions; imported customer reference, signup date, channel and country where applicable |
| Product | External reference, name, category, current price/cost, stock quantity, replenishment lead time, active flag |
| Cart / CartItem | Owner, product and positive quantity; persistent shared state |
| Order | Owner, status, total, timestamp, idempotency key and request fingerprint |
| OrderItem | Order, product, positive quantity and historical unit price |
| DailyProductSales | Business date, product, units and sales amount; unique date/product pair |
| AnalyticsRun | Run ID, processing window, status, timestamps, processed counts and summary version |

Use foreign keys, uniqueness and check constraints. Protect historical orders when products are retired. Separate payment/transaction tables are not necessary for a simulated checkout unless their distinct purpose is established.

## 5. Required analytics: sales-driven inventory planning

The operator dashboard answers: **What sold, which products are running low, and why should the operator pay attention?**

| Output | Method | Operator use |
|---|---|---|
| Daily sales and category performance | Sum units and historical line-item amounts from completed orders | Understand sales trends |
| Top-selling products | Rank by completed units sold over a selected period | Identify high-demand items |
| Recent average daily sales | Completed units over the previous 7 complete business days divided by 7 | Explain the sales rate |
| Estimated stock coverage | Current stock divided by average daily sales | Estimate days remaining under unchanged sales behaviour |
| Replenishment flag | Coverage less than or equal to configured lead time | Prioritise a stock check |

Display the processing timestamp, period, units, formula and reason for each flag. Use Singapore business dates consistently; store timestamps with timezone awareness. For zero sales, display 'No recent sales; coverage unavailable'. If there is insufficient history, identify it rather than silently changing the denominator.

Example: 35 units sold over 7 complete days gives 5 units/day. Stock of 30 gives 6 days of coverage. With a 7-day replenishment lead time, the product is flagged.

### Processing pipeline

**RDS orders and products -> repeatable aggregation command -> daily summaries -> protected dashboard**

- Validate input fields and exclude cancelled, rejected or otherwise incomplete orders from completed-sales metrics.
- Recompute and upsert the relevant daily summaries. A repeated run must not double-count.
- Recompute affected periods when historical statuses change; document the supported refresh window.
- Prevent overlapping runs with a database-backed job lock and publish summaries transactionally or through a completed run version.
- Run the command from one designated scheduler, not from every autoscaled web instance. Use the existing initial web host for the short scheduled demonstration if necessary, document this scheduler limitation, and make recovery/re-running explicit. A separate always-on worker is outside the budget baseline.
- Define deterministic seed and analytics commands during implementation, for example `python manage.py seed_demo --seed 42` and `python manage.py refresh_analytics --as-of <date>`. These are planned interfaces, not existing commands.

### Selected dataset and provenance

Use [LaelaZ / synthetic-ecommerce on Hugging Face](https://huggingface.co/datasets/LaelaZ/synthetic-ecommerce) as the selected historical source. The publisher states that every row is synthetic, generated through a seeded NumPy process, with no real people or scraped data. The published licence is MIT. These are publisher statements, not the team's independent audit: inspect and validate the downloaded release before accepting it.

| Source table | Published rows | Relevant fields |
|---|---:|---|
| customers | 2,000 | customer_id, signup_date, channel, country |
| products | 120 | product_id, product_name, category, unit_price, unit_cost |
| orders | 12,000 | order_id, customer_id, order_ts, status |
| order_items | 30,120 | order_item_id, order_id, product_id, quantity, unit_price |
| events | 59,599 | event_id, session_id, customer_id, event_type, event_ts |

Published order coverage is January-December 2024. Files are Parquet. Actual counts, ranges and fields must be recorded after download. Browsing events are optional input and do not commit the team to a funnel feature. The catalogue uses SKU-style names; fictional display names can be added without changing product identity.

Record the source URL, downloaded revision/date, file checksums, licence notice, schema, row counts and every transformation in `data/README.md` and `data/DATA_DICTIONARY.md`. Preserve original files separately from transformed data. Review generation provenance where accessible; do not state that the generator has been independently audited unless that work is completed. Do not substitute anonymised real data: the team's selected policy is synthetic-only.

### Where to download the dataset

- Dataset card and provenance: https://huggingface.co/datasets/LaelaZ/synthetic-ecommerce
- Download browser (Files tab): https://huggingface.co/datasets/LaelaZ/synthetic-ecommerce/tree/main
- Download the original Parquet files for customers, products, orders and order_items. Events are optional for this scope. Retain the dataset card and applicable licence notice alongside the source records.
- Preserve these inputs under `data/raw/` locally, record the selected repository revision and SHA-256 checksums, then upload the same validated inputs to the private S3 data bucket for the cloud import demonstration.
- Generate missing stock, lead times, fictional display names and demo account/cart records separately. Do not assume historical customer records contain working application credentials.

Dataset selection is a planning decision; downloading, inspecting and validating the files remains Phase 1 work. The publisher states the data is fully synthetic; this scope does not claim an independent generator audit.

### Mapping into the application

Design the application schema around its workflow and map the dataset into it; do not copy a flat source schema or treat external IDs as globally unique application IDs.

| Dataset information | Application mapping / treatment |
|---|---|
| customer_id and customer attributes | CustomerProfile/source reference; link to a synthetic Django account where required |
| product_id, category, price and cost | Product with a unique source reference; convert monetary values to the documented decimal precision |
| order_id, customer_id, order_ts, status | Order linked to the mapped customer; preserve external reference and source timestamps |
| order-item product, quantity and price | OrderItem linked to the mapped order/product; retain historical unit price |
| completed, cancelled, refunded | Explicit application status mapping; only completed orders enter completed-sales totals |
| Missing stock and lead times | Generate a dated inventory snapshot and documented lead-time assumptions |
| Missing credentials and carts | Generate separate demo accounts/carts; imported accounts have unusable passwords by default |

Use source name plus external ID for idempotent imports. Reject/quarantine malformed records with a summary rather than silently fixing or dropping them. Validate primary-key uniqueness, foreign keys, positive quantities, finite monetary values, allowed statuses and customer/order chronology. Calculate order totals from line items. Preserve rounding rules and reconcile totals after conversion.

Inventory is a generated snapshot, not a quantity inferred merely by subtracting a year of sales. Record its effective date. Historical import must not invoke live checkout and deduct stock again. New demo checkouts deduct from the selected starting stock normally. Synthetic customer records are not real accounts; any generated contact identifiers use reserved example domains and must not trigger outbound email.

### Dates and reporting modes

Default to preserving original timestamps and a reproducible historical reporting cutoff (for example 1 January 2025, using the seven preceding complete days). Pair historical stock-coverage calculations with the generated inventory snapshot at that cutoff. Do not combine current stock with 2024 sales while labelling the result current coverage.

A live-demo fixture may shift all related customer/order/event dates by one recorded constant offset. Choose it so no imported event falls after the demo cutoff, preserve relative intervals, and record the source/target date anchors. Specify an assumed timezone for naive source timestamps; do not silently claim the source used Singapore time. Apply the same convention to signup dates, analytics windows and inventory snapshots.

Keep original historical data, date-shifted demo fixtures and performance fixtures distinguishable. The dashboard must identify its reporting period and data freshness; a new live order must not silently enter a historical evaluation window. Tests use a fixed clock/cutoff.

### Dataset size and supplemental generation

The brief states no minimum row count. The selected 12,000 orders and 30,120 line items are a reasonable starting scale for INF2006 analytics. Increase volume only when an experiment needs it; millions of stored rows are not necessary to demonstrate request-driven autoscaling.

Maintain three fixtures: a tiny independently hand-checkable correctness fixture, the validated imported historical dataset, and an isolated/resettable load-test fixture with sufficient stock and repeatable shoppers. Record seed, counts, date range and distribution assumptions for all generated additions. Larger fixtures must preserve valid relationships and plausible skew, not duplicate IDs or arbitrarily copy records.

If the selected download fails provenance, licence or integrity checks, use a documented fully synthetic generator with equivalent tables. Record the change rather than silently swapping datasets. Selection is complete; validation and import remain implementation tasks.

### Analytics validation and limitations

Verify known sales totals, historical prices after a price change, cancelled-order exclusion, zero-sales handling, date boundaries, replenishment thresholds and repeat-run idempotency. Compare the output with independently calculated expected values.

The selected dataset has deliberately simplified synthetic relationships; it does not establish real market behaviour, price elasticity or seasonality. Explain that sales are not necessarily unmet demand; stockouts suppress sales, short histories are unstable, and recent sales and fixed lead times do not guarantee future conditions. Demonstrate operational usefulness in the simulated scenario without claiming validated commercial demand prediction.

## 6. Optional ML: customer segmentation

Only start after required analytics, checkout and AWS smoke deployment work, and only if it will not displace evidence preparation.

- Calculate recency, completed-order frequency and spending at a fixed cutoff.
- Scale features and fit a small K-means model offline.
- Compare a few cluster counts, silhouette scores, cluster sizes/profiles and stability across seeds.
- Exclude customers without adequate purchase history or label them separately.
- Interpret groups after inspecting their profiles; cluster IDs do not inherently mean loyal or at-risk customers.
- Show summaries on the operator page. Store the model/version or batch results; no separate inference service is required.
- Document that the selected synthetic dataset cannot establish real customer behaviour. Check whether repeat purchasing and variation are sufficient before attempting clustering. Do not report classification accuracy without true class labels.

The complete submission must meet the required analytics criterion even if ML is omitted.

## 7. AWS architecture and budget constraints

### Baseline architecture

- **Dynamic pages and HTMX requests:** Browser -> HTTPS ALB -> Django containers in EC2 Auto Scaling Group -> private RDS PostgreSQL.
- **Static assets:** Browser -> HTTPS ALB -> application static-file handler (WhiteNoise). Package identical content-hashed CSS, JavaScript and product images into every application image.
- **Data pipeline:** Private S3 data bucket -> authorised import/validation command -> RDS -> analytics summaries. S3 may also hold versioned analytics exports accessible only to authorised tooling.

S3 remains required for dataset/export object storage. Block public access, restrict IAM permissions to needed objects/actions, and record source checksums and versions. Do not store sessions in S3. Preserve a local dataset-input/export option for reproducibility and INF2003.

CloudFront is excluded from the current implementation. Discuss it as an alternative for edge caching and reducing static-origin traffic; its omission reflects this workload, budget and deadline, not a claim that CDNs require geographically distributed users. An ElastiCache product-data cache remains a candidate, subject to explicit scope selection, lab support and measured value; it is not required for session continuity.

CloudWatch receives sanitised application and infrastructure metrics/logs. The application obtains configuration through permitted secure mechanisms. Sessions and carts use PostgreSQL rather than instance-local state. New instances must run the same image, dependencies and shared Django signing configuration.

| Component | Required behaviour |
|---|---|
| VPC/subnets | ALB across two allowed Availability Zones; RDS in private DB subnets, not publicly accessible |
| EC2/ASG | Initial/minimum capacity 1; test maximum 2 by default, up to 3 only after quota and cost checks |
| ALB | Health-checked targets, secure ingress and request distribution |
| RDS | Smallest suitable permitted PostgreSQL configuration, bounded connections, migrations and backups |
| Scaling | Target tracking using `ALBRequestCountPerTarget`, calibrated from a one-instance benchmark; record warmup and scale-in behaviour |
| S3 | Private dataset/export bucket; documented object versions/checksums, restricted IAM access and retention |
| CloudWatch | Instance count, latency, request errors, application outcomes and one actionable alert/query |
| IAM/secrets | Instance profile rather than embedded AWS keys; restricted secret access where the lab permits |
| Terraform | Deployment and teardown instructions; lab-provided roles referenced rather than recreated where necessary |

To avoid a continuously billed NAT gateway, the budget baseline may place EC2 in public subnets with application ingress allowed only from the ALB security group. RDS remains private. Public IPs do not imply open application ports. Compare this with private application subnets plus NAT/endpoints in the report and document the trade-off. Do not permit broad SSH access; use a lab-supported management method.

### Shared sessions and replaceable application servers

Use Django database-backed sessions for the baseline:

```python
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_SECURE = True       # HTTPS deployment
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
```

- The browser stores an opaque session ID in its session cookie, not a trusted user ID supplied by the client.
- Django stores session data, the authenticated-user reference and expiry in the shared RDS `django_session` table. Django's authentication machinery verifies the session and user.
- Persist carts in Cart/CartItem tables linked to the authenticated user. Avoid keeping authoritative carts only in a process or serialised mutable session blob.
- Disable ALB target-group stickiness. Every app instance uses the same RDS database, session engine, Django SECRET_KEY, compatible code and cookie configuration. Load shared secrets securely; do not generate a different signing key per instance.
- Schedule `clearsessions` through the designated maintenance runner. Configure and document session expiry and logout behaviour.
- Keep authoritative user state off EC2 memory, local files and EBS volumes. Instances are replaceable but still share infrastructure dependencies; this is not complete failure isolation.
- Cache-only sessions are outside the baseline: eviction or cache failure could destroy login state. If measurements later justify it, Django `cached_db` sessions can add a shared cache in front of database storage. Validate backend outage behaviour, timeouts, invalidation and logout before adopting it; a cache-miss fallback alone is not proof of outage tolerance.

Session persistence does not guarantee invisible failures. An in-flight request can fail when its server dies, health-check detection takes time, and one-instance operation has downtime until replacement. For the continuity demonstration, temporarily run at least two healthy instances across allowed Availability Zones before terminating one. RDS Single-AZ remains a shared availability limitation.

Required continuity test: log in, add cart items, prove requests reach different instances without stickiness, terminate one instance, then retry through the ALB. Confirm the session remains authenticated and the cart survives. During a checkout-interruption test, reuse the idempotency key and verify exactly one order regardless of whether the original request committed before the connection failed. Record transient errors and recovery delay rather than claiming zero impact. Graceful scale-in should use target deregistration/draining; it does not prevent errors from an abrupt crash.

### Week-one account and HTTPS checkpoint

Confirm permitted region, EC2 types, ASG capacity, RDS, ALB, S3, bucket policies, CloudWatch, Terraform credentials, instance profiles, secret access and certificate capabilities in the actual Canvas lab. Do not assume IAM role creation, Secrets Manager or ACM operations are available. Record restrictions and agree a supported alternative with the instructor if necessary; never claim a control was implemented when it was not.

For trusted browser HTTPS at ALB, confirm access to a certificate for a hostname the team/institution controls and the ability to validate or import it. The AWS-generated ALB hostname alone does not solve certificate ownership. If no trusted hostname is available, resolve the supported demonstration arrangement in week one; a private test certificate requires explicit client trust and a documented limitation. Do not silently downgrade credential handling to public HTTP.

### Budget plan

- Treat USD 40 per member as separate balances, not a pooled USD 200 deployment allowance.
- Select one permitted integration account. Other members develop locally or perform isolated, authorised experiments in their own accounts; do not share account credentials.
- Develop locally with Docker PostgreSQL; provision AWS for short deployment, load-test and evidence sessions.
- Before each cloud session, estimate regional EC2, RDS, ALB, IPv4, S3 storage/requests/versions, logs and any secrets/network charges using current prices and remaining lab credits.
- Working cap: plan at most USD 30 of the integration account's initial USD 40, preserving roughly USD 10 for final verification. Recalculate against the actual remaining balance. This is a spending target, not a service-price estimate.
- Restrict ASG maximum capacity and test duration. Set short log retention and capture evidence before teardown.
- Track credit usage at session start/end. Alerts are notifications, not guaranteed spending caps.
- Tear down lab resources after evidence sessions, including ALB and unused storage/snapshots as appropriate. Stopping EC2 alone does not stop all charges.
- Clean up unused S3 objects/versions after preserving required evidence and data; do not assume these disappear when compute is stopped.
- Verify behaviour when a lab session ends; do not assume resources are deleted or all billing stops.

RDS Single-AZ and ASG minimum 1 are budget compromises. Do not claim database failover or uninterrupted high availability; measure actual application interruption and recovery.

## 8. Security controls and named threats

| Threat | Control and validation |
|---|---|
| Unauthenticated checkout | Django authentication; reject unauthenticated requests |
| Access to another customer's order | Server-side owner filtering; test user A against user B's order |
| Operator data exposure | Explicit operator permission; deny normal users |
| Price or quantity manipulation | Server-side product lookup, decimal totals and positive quantity validation |
| CSRF against session-based actions | Django CSRF protection and appropriate cookie settings; test missing/invalid token |
| Duplicate checkout/retries | Unique idempotency key and atomic processing |
| Credential leakage | No secrets in source, images, logs or submitted Terraform state; secure runtime configuration |
| Public data-bucket exposure | S3 Block Public Access and least-privilege bucket/IAM policies; test anonymous access denial |
| Unrestricted DB access | Private RDS, security group restricted to app tier, non-superuser application role |

Configure production settings: debug disabled, allowed hosts, secure session cookies under HTTPS, password hashing and trusted proxy handling. Use a migration role separately from normal runtime privileges where practical. Document lab-imposed IAM limitations honestly.

## 9. Test plan and success criteria

The brief requires functional, security, data/AI and scale/resilience/recovery tests, plus operational evidence. The following is the required project evidence plan, not a claim that tests have already passed.

| Test | Procedure | Expected evidence |
|---|---|---|
| Functional | Register, login, browse, cart, checkout and view own order | Correct totals, persisted order/items and stock reduction |
| Checkout correctness | Concurrent requests, insufficient stock and repeated idempotency keys | No negative stock, partial orders or duplicate purchases |
| Security | Invalid session, CSRF, foreign order access, operator access and manipulated price | Requests fail safely or server values prevail; no unauthorised change |
| Data import and analytics | Validate downloaded tables and relationships; import twice; run a hand-checkable fixture at a fixed cutoff and rerun analytics | Traceable import counts/rejections, no duplicate imports, exact totals, correct date/status handling, coverage and flags, no double-counting |
| Scaling | Identical seeded workload with fixed capacity then autoscaling | Healthy instance count, p50/p95 latency, completed throughput, errors, scale-out delay and scale-in record |
| Recovery / session continuity | With two healthy instances and stickiness disabled, log in, create cart state, terminate one instance during traffic and retry checkout | Surviving login/cart, cross-instance requests, replacement timeline, transient errors and exactly one order after an equivalent retry |
| Object storage | Import the pinned dataset from private S3 and compare checksum/counts; attempt anonymous access | Authorised read succeeds, data reconciles and anonymous data access is denied |
| Operations | Trigger a controlled error condition or instance-recovery alert | Dated metric/log export and alert/query interpretation |

Define the load rate and numeric latency/error targets after the initial one-instance measurement and before the final comparison. A proposed starting service objective is p95 checkout below 2 seconds and unexpected errors below 1% at a declared supported load; calibrate and document revisions before evaluation. Expected sold-out rejections must be reported separately, not hidden as successful purchases or unexplained errors.

Measure dynamic browse/checkout requests separately from static assets. If a product cache is later added, compare cached and uncached workloads without conflating them with changes in instance count.

Run the load generator outside the app instances. Use a fixed shopper/request mix, valid authentication and CSRF handling, adequate stock and unique purchase IDs. Monitor the load generator itself. Sustain each phase long enough for scaling decisions, startup and health checks. Separate scaling and failure phases so causes are clear.

Correctness expectations are strict: no unauthorised access, no negative stock, no duplicate persisted purchase for an equivalent idempotent retry, and analytics matching expected fixtures. Performance improvement is an experimental result, not a promise. If RDS becomes the bottleneck or scaling adds little benefit, diagnose it and report the limitation.

For every test record objective, setup, exact command/steps, expected result, actual result, date and artefact path. Include raw outputs and interpretation; screenshots or video alone are insufficient.

## 10. Delivery phases and four-week timeline

The phases below are completion gates, not five additional weeks. Members work in parallel, and deployment, testing and evidence collection begin in Phase 1.

| Phase | Dates (2026) | Main work | Completion gate |
|---|---|---|---|
| 1. Foundation and feasibility | 11-17 September | Assign ownership; confirm AWS services, credits and HTTPS; validate dataset and schema mapping; scaffold Django, Docker and Terraform; perform the first AWS deployment | Local and cloud app reach their databases; source data is accepted or replaced with a documented synthetic generator; core account/HTTPS blockers resolved |
| 2. Working ecommerce and analytics | 18-24 September | Implement authentication, persistent carts, transactional/idempotent checkout and order history; import from S3; build and validate sales/inventory analytics | End-to-end workflow works in AWS; correctness, access-control and analytics fixtures pass |
| 3. Scaling, recovery and measured improvements | 25 September-1 October | Exercise ALB/ASG, session continuity and monitoring; run security, load and failure tests; evaluate a small cache only if permissions, cost and time permit | Dated evidence exists for required test categories; failures and bottlenecks are understood; freeze features on 1 October |
| 4. Reproduction and submission assembly | 2-8 October | Fix defects; rehearse clean local setup; complete report, manifest, evidence links, attribution and contributions | A different teammate reproduces the application and analytics and locates evidence for each assessment claim |
| 5. Final verification and handover | 9-11 October | Check ZIP, secrets and required paths; preserve evidence; submit; archive exact submission and tag its commit | Submit by 11 October at 23:59 Singapore time; preserve the baseline for later INF2003 expansion |

ElastiCache remains conditional, not a prerequisite for completing these phases. Optional ML must not delay required analytics or testing. Evidence is collected during each phase. INF2003 implementation begins after INF2006 submission, with its separate proposal work reserved before the 4 October deadline.

### Weekly milestone detail

| Period | Required milestone | Exit condition |
|---|---|---|
| 11-17 September | Verify AWS permissions, budget and HTTPS; scaffold Django/Compose/Terraform; dataset acceptance checks, schema/import mapping, supplemental seeds, auth and first AWS smoke deployment | App reaches database locally and in AWS; no unresolved core deployment dependency |
| 18-24 September | Complete S3-backed dataset import, shared-session continuity, storefront, correct checkout, analytics pipeline/page and access controls | Functional and analytics tests pass locally; full workflow runs in AWS |
| 25 September-1 October | Finalise ASG/ALB/monitoring; run scaling, recovery and security experiments; draft report | Dated evidence for all minimum categories; remaining failures understood |
| 2-8 October | Feature freeze; resolve defects; reproduce from clean setup; finish report, declarations and manifest | Another teammate can run local instructions and locate every claim's evidence |
| 9-11 October | Submission preflight and contingency buffer | Verified ZIP submitted by 11 October, 11:59 PM |

Optional ML is dropped if required work is behind schedule. No new features after 1 October. INF2003's progress report is due 4 October at 11:30 PM, so reserve time for its database expansion plan without adding those features here.

## 11. Five-person ownership plan

Assign names at the team meeting. Each owner also supplies tests, evidence and report notes; evidence is not one person's last-week cleanup task.

| Member | Primary ownership | Required collaboration |
|---|---|---|
| 1 | Django schema, checkout and inventory correctness | Review analytics calculations with member 3 |
| 2 | Templates/HTMX, auth flows, cart and operator interface | Review access controls with member 4 |
| 3 | Dataset provenance/import, supplemental generator, analytics pipeline and validation; optional ML | Integrate with members 1 and 2 |
| 4 | Terraform, AWS networking/compute/data, S3, secrets and security configuration | Pair with member 5 on deployment and teardown |
| 5 | Load/recovery tests, monitoring, evidence integration and packaging checks | Review infrastructure; coordinate reproducibility rehearsal |

Use cross-review for critical changes. Record commits, artefacts, test ownership and reflections for every member. Infrastructure/security and checkout owners should pair on integration early because these are schedule-critical.

## 12. Assessment rubric coverage

| Criterion | Marks | Planned evidence |
|---|---:|---|
| Problem framing and architecture | 15 | User need, measurable objectives, architecture/trust-boundary diagram, two alternatives and trade-offs |
| Cloud implementation and functionality | 20 | Runnable ecommerce workflow, Terraform/config, deployment record, functional results |
| Cloud data and analytics/AI | 20 | Identified synthetic dataset, licence, dictionary, reproducible import/supplemental generator and aggregation, useful dashboard, independent validation and limitations |
| Security and responsible cloud practice | 15 | Threat-control map, redacted configuration, authentication/authorisation tests, secrets and data handling |
| Scalability, resilience and operations | 15 | Implemented scaling/recovery, metrics, repeated workload comparison, monitoring interpretation and cost record |
| Engineering quality and reproducibility | 10 | Structured code, dependency pinning, local run, test scripts, valid manifest paths and clean-machine rehearsal |
| Team contribution and communication | 5 | Contribution matrix, specific ownership, attribution and concise report |

Analytics satisfies the stated analytics/AI route without ML. Strong marks depend on credible results and evidence, not AWS service count or frontend complexity. Distinguish the minimum requirements from the stronger validation this team plans to supply.

## 13. Submission package and evidence map

Submit `Group_Gxxx_INF2006_Project.zip`, replacing Gxxx with the assigned group ID.

```text
README.md
project_manifest.yaml
report.pdf
src/                         # application, infrastructure, dependencies, .env.example
data/                        # synthetic/sample data and data dictionary
analytics/
evidence/
tests/
TEAM_CONTRIBUTIONS.md
AI_USE_DECLARATION.md
video_link.txt               # optional presentation link; not primary evidence
```

`data/` includes source/sample data, `README.md`, `DATA_DICTIONARY.md`, licence/attribution, revision/checksums, mapping and date-transformation notes, and supplemental-generation instructions. `analytics/` includes commands/scripts, requirements and reproduction instructions. The scope document is planning material, not a substitute for the final report.

Use the existing manifest schema without removing or renaming required fields. Planned evidence paths:

- `evidence/architecture.png`
- `evidence/test-functional.md`
- `evidence/test-security.md`
- `evidence/test-data-ai.md`
- `evidence/data-validation.md` with source counts, integrity checks, transformations and import reconciliation
- `evidence/test-resilience.md`
- `evidence/monitoring.md`
- `evidence/threat-control-map.md`
- `evidence/storage.md` with S3 object provenance, access-control tests and import reconciliation
- `evidence/session-continuity.md` with cross-instance authentication/cart and failure tests
- `evidence/costs.md` plus linked raw test results and redacted configuration

The report must be 8-12 pages excluding references/appendices and follow the brief's eight headings:

1. Problem, users and success criteria
2. Solution overview and architecture
3. Cloud service/deployment choices and trade-offs
4. Implementation, data design and security controls
5. Analytics or AI/ML feature: data, method, evaluation and limitations
6. Testing, scalability/resilience and monitoring results
7. Cost, sustainability and operational considerations
8. Team contribution, ethical considerations and reflection

Provide a runnable local mode using Docker PostgreSQL, synthetic seed data and placeholder configuration. A marker must not need paid AWS access to inspect the submission. Preserve real cloud deployment evidence separately; local execution does not prove AWS deployment.

Exclude passwords, tokens, credentials, private URLs, personal data and secret-containing Terraform state. Redact account IDs/public IPs as instructed by the brief. Declare AI assistance, source code, licences and verification. Cloud resources may be decommissioned after evidence capture; the brief explicitly permits assessment through retained configuration and evidence.

## 14. INF2003 continuation

After submission, save the exact INF2006 ZIP and tag the commit, for example `inf2006-submission`. Start the database expansion from that baseline.

- Keep Django, templates/design reference, ecommerce entities, validated dataset mappings/import tooling, checkout correctness, supplemental seeds and useful analytics.
- Replace RDS with PostgreSQL in Docker, serve assets locally, read datasets/exports from local storage and remove AWS-specific operational integrations, including S3 dependencies.
- Remove the optional ML function for the local INF2003 scope without breaking checkout or retained analytics.
- Add MongoDB through a separate data-access module and expand appropriate document-oriented workflows.
- Extend SQL and NoSQL modelling, CRUD, constraints, aggregation, indexes and controlled benchmarks. Add documented synthetic reviews, richer attributes or other missing entities as required; the INF2006 dataset is a foundation, not a ceiling on the schema.
- Define substantial database work for both stores. Avoid two authoritative copies of orders unless consistency management is an intentional, tested feature. A separate NoSQL order implementation can instead support equivalent-operation comparisons.
- For benchmarks, record hardware/container limits, versions, data sizes, indexes, consistency requirements, workload, warmup and repeated results. Compare equivalent operations; report different responsibilities separately. Large row counts alone do not demonstrate database knowledge.
- Prepare a separate INF2003 report, presentation and run instructions.

The ecommerce domain can support INF2003's excellent-band expectations, but the INF2006 submission does not guarantee an INF2003 grade. INF2003 requires its own substantial implementation and evidence, plus proposal (10%), presentation (25%), final report (25%) and project quality/implementation (40%); peer review also affects outcomes. Benchmarking supports analysis but is not a substitute for modelling and working functionality.

Do not implement INF2003 extensions during the cloud deadline. Confirm permitted cross-module reuse and member attribution with lecturers, particularly if membership differs. The briefs do not by themselves establish approval for shared assessed work.

## 15. Risk register and mitigation

These are planning risks, not confirmed implementation failures. Owners refer to the five-person ownership plan; review status at each phase gate.

| Risk | Impact | Mitigation / decision rule | Owner and verification |
|---|---|---|---|
| AWS lab permissions or insufficient credits | Deployment blocked or resources lost before evidence capture | Verify actual service/role permissions and remaining balance in Phase 1; budget against one integration account; develop locally and tear down paid resources after evidence sessions | Members 4 and 5: account capability record, cost estimate and deployment smoke test |
| HTTPS hostname/certificate unresolved | Secure browser authentication cannot be demonstrated as planned | Resolve supported hostname, certificate and validation arrangement in Phase 1; document any instructor-supported test limitations | Member 4: working HTTPS and secure-cookie verification |
| Four-week scope creep | Incomplete required workflow or submission | Freeze core functionality; omit optional ML first; add ElastiCache only if affordable and testable; no new features after 1 October | All owners: phase gates and feature-freeze review |
| Synthetic dataset provenance or integrity fails validation | Unreliable analytics or unsuitable source data | Record source revision, licence and checksums; validate IDs, relationships, monetary values and chronology; use a documented fully synthetic generator if the source fails acceptance | Member 3: data acceptance and reconciliation output |
| Historical sales and stock dates do not align | Misleading stock-coverage and replenishment flags | Pair sales windows with dated generated inventory snapshots; document any uniform date shift; separate historical, live-demo and load fixtures | Members 1 and 3: fixed-date analytics tests and freshness labels |
| Concurrent checkout or retry errors | Overselling, partial writes or duplicate orders | Use database transactions, row locks or conditional updates, constraints and user-scoped idempotency; obtain final stock/prices from RDS | Members 1 and 5: concurrent, sold-out and interrupted-checkout tests |
| Cache outage or stale data, if ElastiCache is adopted | Slow requests, excess RDS load or misleading cached views | Limit caching to disposable read results; use expiry and post-commit invalidation; short connection/read timeouts, explicit database fallback and temporary bypass after repeated cache failures; retain sessions/carts/orders in RDS | Members 1, 4 and 5: cache-disabled, warm-cache and cache-outage comparisons at fixed app capacity; document supported fallback load |
| Shared infrastructure failures | App instances recover but database or scheduler remains unavailable | State Single-AZ RDS and the designated scheduler limitation; demonstrate app failure with two healthy instances; document scheduler restart/re-run; never confirm checkout if the authoritative database is unavailable | Members 3, 4 and 5: failure timeline, session continuity and repeatable analytics recovery |
| Autoscaling does not improve the measured workload | Unsupported performance claims | Measure a fixed-capacity baseline; monitor DB and load-generator limits; sustain traffic through startup/warmup; separate cache, scaling and failure experiments; report bottlenecks honestly | Members 4 and 5: latency, throughput, errors, instance counts and interpretation |
| Weak or late assessment evidence | Working features cannot receive associated evidence credit | Each owner saves dated commands, expected/actual results and redacted outputs as work is completed; verify manifest links and rehearse on a clean machine | All owners; member 5 coordinates the evidence audit |
| INF2003 reuse or attribution assumptions | Later submission may not meet module expectations | Confirm lecturer policy and membership attribution; archive the exact INF2006 submission; document substantive database additions separately | Team: policy clarification and baseline tag before continuation |

Cache fallback is graceful degradation, not unlimited availability: RDS must absorb additional reads during an outage. If RDS is also unavailable, return a controlled temporary-unavailability response. Browsing and analytics may tolerate bounded staleness; checkout must preserve authoritative transaction correctness. Avoid labelling the whole application CP or AP solely because it uses a cache.

## 16. Sources and outstanding decisions

Primary assessment source: `INF2006_Team_Project_Brief_2026.pdf`, sections 4-10 and Appendix A, supplied by the user. Continuation dates and requirements: `INF2003_project_description.pdf`, supplied by the user.

Dataset and design references:

- [Selected synthetic dataset and published provenance/licence](https://huggingface.co/datasets/LaelaZ/synthetic-ecommerce)
- [Published dataset files](https://huggingface.co/datasets/LaelaZ/synthetic-ecommerce/tree/main)
- Selected `DESIGN.md` supplied by the user, adapted for this project; record its original source and relevant asset licences.

Technical references:

- [AWS ALB HTTPS listener requirements](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/create-https-listener.html)
- [AWS ALB certificates and domain names](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/https-listener-certificates.html)
- [AWS target tracking and warmup](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-target-tracking.html)
- [Django database and cached database sessions](https://docs.djangoproject.com/en/6.0/topics/http/sessions/)
- [AWS VPC pricing, including network-related charges](https://aws.amazon.com/vpc/pricing/)

Week-one decisions still requiring actual account evidence: permitted services/roles, integration account, region, instance classes, available credit balance, HTTPS hostname/certificate and exact deployment cost estimate. Team names, group ID and the numeric tested workload must be filled in during implementation. No cloud resources have been provisioned by writing this scope.
