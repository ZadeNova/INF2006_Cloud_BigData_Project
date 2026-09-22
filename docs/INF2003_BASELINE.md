# INF2003 baseline guardrails

Status: guidance, not requirements. Nothing in this document is an INF2006 task, and INF2003 features must not be implemented in this delivery (see AGENTS.md shared rules; NoSQL and marketplace features still need a scope decision). Consult this file only when a change touches one of the seams below. Requirements stay in the [scope](../PROJECT_SCOPE_INF2006.md); status stays in the [implementation plan](IMPLEMENTATION_PLAN.md).

## Why this exists

INF2003 (Database Systems) is a separate module whose project will be built on the submitted INF2006 baseline. It needs a relational database and a non-relational database, an ER diagram with different relationship kinds, advanced SQL/DBMS features, a rigorous SQL vs NoSQL comparison with performance analysis, and a locally runnable application with a user manual. The INF2006 baseline is frozen and tagged at submission (11 Oct 2026); INF2003 work happens afterwards on a separate branch or repository. The guardrails below are cheap conventions that keep the later extension easy. They are not a reason to add abstractions or features now.

## What INF2003 removes and what it keeps

| Removed for INF2003 (INF2006-only) | Kept as the INF2003 baseline |
|---|---|
| AWS, Terraform, HTTPS/ALB/ASG configuration, CloudWatch metrics and alarms (INF2003 is not hosted) | Django app, PostgreSQL schema, constraints and triggers |
| ML/forecasting component and its stored predictions | Analytics aggregation SQL (the relational half of the later comparison) |
| Deployment-specific evidence and the INF2006 submission package | Docker Compose local run path, Locust load scripts, raw dataset files |

## Planned INF2003 expansion (do not implement here)

| Feature | Expected impact on this baseline |
|---|---|
| Merchants | New model; `Product` gains a merchant reference; the `store_operator` role becomes per-merchant; checkout, order lines and analytics may need per-merchant handling |
| Reviews and ratings | New model referencing product and user (verified purchase via `OrderItem`); candidate MongoDB collection; aggregate rating may be denormalised |
| Product variants | Highest impact: `CartItem`, `OrderItem`, `InventorySnapshot` and `DailyProductSales` all reference `Product`, and checkout locks `Product` rows; stock and price may move to a variant |
| Flexible product attributes | Candidate experiment: EAV vs PostgreSQL JSONB vs MongoDB documents |
| Wishlist | New many-to-many between user and product; low impact |
| MongoDB product/catalogue documents | A second store; AGENTS.md forbids NoSQL until a scope decision is made |
| Advanced SQL, MongoDB aggregation, indexes | Reuses the analytics workload; existing indexes include `order_owner_date` and `order_reporting_window` |
| Controlled SQL vs MongoDB comparison | The selected dataset is about 100,000 orders and 237,537 line items (the source was switched on 22 September 2026; see `PROJECT_SCOPE_INF2006.md` §5) — roughly 8x the earlier estimate and a more credible base for measurable differences, so a seeded scale-up may no longer be needed. Confirm against the actual benchmark design rather than assuming either way; this size shows index and query-plan differences, not large-scale effects |

## Rules for INF2006 work

1. **Isolate infrastructure.** Terraform stays in one dedicated subdirectory under `src/` (per [AWS infrastructure](AWS_INFRASTRUCTURE.md)). Nothing else in the tree may depend on it.
2. **The app runs without AWS.** Any code that touches an AWS service (metrics emission, S3 dataset loading) sits behind configuration with a local fallback: metric calls no-op when unconfigured, and the import command accepts a local path as well as S3. This also serves the INF2006 requirement that a marker can run offline.
3. **Keep ML removable.** Training and evaluation live offline in `analytics/` with their own requirements, results are loaded into one dedicated table by a management command, and the web image does not depend on ML libraries. Removal means deleting a module and a table.
4. **Write analytics as clean, parameterized SQL.** Prefer a database view over completed sale lines (created with `RunSQL`, like the existing triggers) so the cancelled/refunded exclusion lives in one place. Keep queries in `.sql` files or one documented module and test them against the hand-checkable fixtures. Keep checkout and cart on the ORM; do not rewrite tested transactional code in raw SQL.
5. **Preserve raw data.** Keep the downloaded raw files unchanged, including tables INF2006 does not import (for example events), and keep `data/DATA_DICTIONARY.md` accurate.
6. **Keep business logic in explicit service functions** (the existing [architecture](ARCHITECTURE.md) convention) so a second datastore can later be added behind them. Do not add a repository layer or abstraction speculatively.
7. **Keep the local run path working.** Docker Compose must continue to build and run the app locally, and load scripts must take a configurable base URL with no AWS assumptions.
8. **Produce one ER diagram** from the actual models. INF2006 needs an architecture diagram anyway, and INF2003 requires an ER diagram showing one-to-many, many-to-one and many-to-many relationships.
9. **Do not add speculative columns, tables or flags** for INF2003. Extend the schema in INF2003 with migrations, using the impacts above as a guide.
