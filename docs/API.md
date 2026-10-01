# Route and interaction contract

Status: GET/HEAD /health/ (URL name health), GET / (URL name home, a 302 redirect to the catalogue since 24 September 2026), the presentation-only GET/HEAD /foundation/ foundation preview (URL name foundation-preview), the presentation-only GET/HEAD /foundation/design-notes/ fragment and the presentation-only 503 failure preview are implemented. GET/POST /register/, GET/POST /login/ and POST /logout/ (accounts:register/login/logout), GET /products/ (catalogue:product_list), and GET /products/<id>/ (catalogue:product_detail) are implemented. GET /products/manage/ and POST /products/manage/<id>/toggle-active/ (catalogue:manage_list/product_toggle_active) are a deliberate, narrow scope addition beyond the assessed brief — see PROJECT_SCOPE_INF2006.md's "Outside INF2006" note and docs/IMPLEMENTATION_PLAN.md for status. GET /cart/, POST /cart/items/, POST /cart/items/<id>/update/ and POST /cart/items/<id>/delete/ (cart:detail/add/update/delete) are also implemented, including the HTMX fragment/HX-Redirect contract described below. GET/POST /checkout/, GET /orders/<id>/ and GET /orders/ (orders:checkout/detail/list) are also implemented, per docs/plans/batch-04-checkout.md and docs/archive/plans/batch-05-order-history.md. GET /analytics/ (reporting:dashboard) is implemented locally with protected full-page and HTMX panel responses, range/compare controls, vendored charts and sealed-run context. See the analytics backend context below and docs/reviews/analytics-dashboard.md for verification and limitations. GET /foundation/statistics/ (name `statistics-preview`) is a presentation-only design comp of the operator dashboard with invented numbers and no database access; it is not the analytics page. Django HTML/HTMX is the baseline, not a separate REST service.

| Method / route | Access | Behaviour |
|---|---|---|
| GET, POST `/register/` | Public | Registration form and validation |
| GET, POST `/login/` | Public | Framework session authentication |
| POST `/logout/` | Authenticated | Invalidate session; CSRF required |
| GET `/products/` | Public | Paginated shoe models (12 per page) that have an active size; each card lists its active sizes as a `product_id` select posting to `cart:add`; sold-out sizes disabled; indicative stock |
| GET `/products/<id>/` | Public | Shoe detail page with size dropdown and add-to-cart flow for active sizes |
| GET `/products/manage/` | Operator | All products including inactive ones, with query filters (`q` name search, `category`, `status` = all/active/inactive; unknown values mean all) shown as a search box and filter chips; pager keeps the filters; scope addition beyond the assessed brief |
| POST `/products/manage/<id>/toggle-active/` | Operator | Set a product's active state explicitly via `active=true`/`active=false`; optional `next` returns to the filtered manage page (accepted only for a `/products/manage/` path on this host); CSRF required; no create/edit |
| GET `/cart/` | Authenticated | Owner's persistent cart |
| POST `/cart/items/` | Authenticated | Add product/positive quantity; with a `next` that is a `/products/` page on this host (not `/products/manage/`), redirects back there with a success or error message bar instead of to the cart |
| POST `/cart/items/<id>/update/` | Owner | Replace quantity with bounds validation |
| POST `/cart/items/<id>/delete/` | Owner | Remove item |
| GET, POST `/checkout/` | Authenticated | Review page that renders a fingerprint of the displayed cart lines; POST with CSRF and that `review` value, verified against the locked cart; session-derived idempotency key; atomic simulated checkout |
| GET `/orders/` | Authenticated | Owner's paginated order history, most recent first |
| GET `/orders/<id>/` | Owner | Persisted order confirmation/detail |
| GET `/analytics/` | Operator | Period-labelled sales/inventory analytics from the latest completed run; optional `range`, `compare`, `coverage_page` and `customers_page` query parameters; HTMX requests receive only the `#analytics-panel` fragment. See [analytics](ANALYTICS.md#dashboard-get-analytics-operator-only) |
| GET, HEAD `/health/` | Infrastructure | Process liveness: 200 JSON {"status":"ok"}, no-store, no DB query; explicit allowed-host validation except the configured exact ALB probe Host for this safe-method path only (see [runtime boundary](AWS_INFRASTRUCTURE.md#secrets-manager-startup-and-alb-boundary)) |
| GET `/` | Public | 302 redirect to `/products/`; the storefront is the landing page (review finding CR-008) |
| GET, HEAD `/foundation/` | Public preview | Presentation-only frontend foundation page, moved from `/` unchanged; no account, catalogue or checkout data |
| GET, HEAD `/foundation/design-notes/` | Public preview | Presentation-only HTMX fragment; no business state or user data |
| GET, HEAD `/foundation/design-notes-unavailable/` | Public preview | Presentation-only 503 HTMX failure fragment used to verify retry/error presentation; no business state or user data |
| GET, HEAD `/foundation/statistics/` | Public preview | Presentation-only design comp of the operator dashboard; every figure is invented, no database queries (asserted by a test) |

## Inputs and responses

Use Django forms/validation and CSRF on all browser mutations, including HTMX. GET does not mutate business state. Standard HTML uses forms and redirects after successful POST; HTMX returns documented fragments or redirects. Finalise form field names and fragment IDs before splitting backend/frontend work.

Validate quantities, pagination bounds, reporting periods and product availability. Derive identity/prices/totals server-side. Normal unauthenticated navigation redirects to login with a safe return path. Handle HTMX session expiry explicitly so login HTML does not appear inside a cart fragment.

Use 403 for forbidden operator/CSRF access, 404 for inaccessible foreign cart/order objects, 409 for stock/idempotency conflicts and 503 for temporary dependency unavailability. The 503 is implemented for database failures by `config.middleware.DatabaseUnavailableMiddleware`: `OperationalError` and `InterfaceError` only (connection failures, timeouts, deadlocks), a database-free page with `Retry-After: 5` and `Cache-Control: no-store`, no exception text; integrity and programming errors remain 500. HTMX requests receive the same 503 and `site.js` shows an inline notice, since HTMX does not swap error responses. Checkout keeps its idempotency key across a 503 so a retry resolves any committed order. Form errors may re-render at 200 with field messages; tests must check behaviour, not status alone. Configure handling of non-2xx HTMX fragments explicitly.

Equivalent checkout replay returns the existing order; changed payload with the same key conflicts. Preserve the key after uncertain network outcomes. Never create a new key automatically solely because a response timed out. See [schema](SCHEMA.md).

Return only public/owner/operator-appropriate fields. Authorise before accessing cached operator results; never share personalised fragments across users.

## Foundation handover to frontend and later backend tasks

Paths: src/templates/base.html is the shared shell and the presentation-only foundation preview lives at src/templates/foundation/home.html; page templates live under accounts/, registration/, catalogue/, cart/, orders/ and reporting/ inside src/templates/. Shared assets live in src/static/ (css/site.css, js/site.js and js/analytics.js, plus vendored Chart.js); HTMX 2.0.4 is vendored at src/static/vendor/htmx/ and model-viewer 4.1.0 (the catalogue's 3D previews) at src/static/vendor/model-viewer/ (no CDN; source and checksums in their READMEs). Django app-template discovery and WhiteNoise manifest static storage are configured; rebuild the Docker image after changing templates/static files. The foundation preview itself created no business views; those were added by the later batches listed above. Template inheritance reserves title, content, head and scripts blocks. Luna Max owns presentation and live visual verification.

Integration contracts (implementation status is recorded above):

| Follow-up | Reserved URL name / template | Form or query fields |
|---|---|---|
| Authentication | accounts:register / accounts/register.html | username, password1, password2; framework password validation |
| Authentication | accounts:login / registration/login.html | username, password, optional safe next |
| Authentication | accounts:logout | POST with CSRF; no owner/user ID supplied |
| Catalogue | catalogue:product_list / catalogue/product_list.html | page: positive integer; backend-bounded pagination; context `shoes` (ShoeModel with prefetched active SKUs in `sizes`) |
| Catalogue detail | catalogue:product_detail / catalogue/product_detail.html | URL shoe-model ID; 404 unless the model has an active size in the demo namespace; context `shoe` (ShoeModel with prefetched active SKUs in `sizes`) |
| Cart | cart:detail / cart/detail.html | GET owner cart; no owner ID supplied |
| Cart add | cart:add | product_id, quantity integer 1..999 |
| Cart update | cart:update | URL item ID, quantity integer 1..999 |
| Cart delete | cart:delete | URL item ID; POST with CSRF |
| Checkout | orders:checkout / orders/checkout.html | GET renders the review page with a hidden `review` field (64-character lowercase hex fingerprint of the displayed lines, price excluded); POST with CSRF and `review`. The idempotency key is session-derived, not submitted. A missing or malformed `review` redirects to the review page; a well-formed value that no longer matches the locked cart is rejected as changed (200, nothing written); the same key with a different `review` conflicts (409) |
| Order detail | orders:detail / orders/detail.html | URL order ID; GET, owner-only |
| Order history | orders:list / orders/list.html | GET owner's orders; page: positive integer; backend-bounded pagination (10 per page) |
| Analytics | reporting:dashboard / reporting/dashboard.html, fragment reporting/_panel.html | GET, operator only; `range`: one of `7d`, `30d` (default), `90d`, `mtd`, `ytd`; `compare`: `1` to enable, absent otherwise; no user, run or date fields from the client |

The URL modules above now exist, including reporting:dashboard. Analytics uses reporting.view_analytics, granted idempotently to store_operator by seed_demo after migrations. Namespace selection uses settings.DEMO_NAMESPACE only. Custom from/to ranges are out of scope; browser-supplied namespace, run, cutoff and date values have no authority.

Analytics dashboard HTMX contract (implemented locally): filter and preset controls use `hx-get` with `hx-target="#analytics-panel"`, `hx-swap="outerHTML"` and `hx-push-url="true"`. Full HTML uses reporting/dashboard.html; an HTMX request (`HX-Request: true`) receives only reporting/_panel.html, whose `id="analytics-panel"` wrapper stays stable. Invalid `range` re-renders at 200 with the default range and a visible message. The client never supplies a run ID or dates; the server reads the latest completed run and derives the span from the whitelisted `range`. Session expiry returns an HX-Redirect to login, and a non-operator receives 403; failed panel requests retain the current panel and receive an inline alert. The vendored Chart.js 4.4.7 UMD build is loaded from `src/static/vendor/chartjs/`, and chart payloads use Django `json_script`.

Cart HTMX responses target id cart-content using outerHTML and template cart/_content.html; full HTML uses cart/detail.html. The backend passes the cart and validated form/errors, derives totals/prices/owner, and keeps the fragment wrapper stable. Authentication expiry returns an HX-Redirect to login rather than login HTML in the fragment. This is implemented and covered by tests/test_cart.py and tests/test_security_negative.py; the 503 notice is shown by site.js (see above). Browser-level verification of the current redesign is not yet recorded.

Health validates DJANGO_ALLOWED_HOSTS and remains exempt from HTTPS redirection for internal probes; it exposes no dependency diagnostics, credentials or sessions. Use python manage.py check_database for operator readiness: exit 0 with database/migrations status, nonzero sanitized error for unavailable PostgreSQL or unapplied migrations. Do not use database readiness as an ASG replacement trigger during a shared RDS outage. Actual ALB probe Host/allowed-host handling is a later infrastructure integration gate.

The later catalogue/cart backend must select an explicit demo fixture namespace server-side and reject cross-namespace cart contents before checkout. Do not accept a namespace from a browser as authority; actual namespace selection follows dataset/fixture acceptance.

## Analytics backend context

`AnalyticsDashboardView` returns `TemplateResponse` with `reporting/dashboard.html` normally and `reporting/_panel.html` only for `HX-Request: true`. Both templates keep an identical `#analytics-panel` wrapper. All view responses use never-cache/no-store; GET is the only supported method (including no implicit HEAD/OPTIONS). Anonymous GET redirects to login, anonymous HTMX GET returns 200 with `HX-Redirect`, and authenticated users lacking `reporting.view_analytics` receive 403, including HTMX.

Only `range`, `compare`, `coverage_page` and `customers_page` are read from the browser. The two page parameters page the replenishment list (every product in the run's inventory) and the segment customer list (the top 50), 10 rows each; invalid or out-of-range values fall back to the nearest valid page, and pager links keep the other parameters. `range` defaults to `30d`; invalid values fall back to it and populate `range_message`, which the template must show. Only the exact value `compare=1` enables comparison. The view selects one latest completed run for `settings.DEMO_NAMESPACE`, then calls the existing reporting range/query functions. It never reads live stock or aggregates orders. If retention removes the selected run during reads, the entire context is rebuilt from the latest completed run, with at most three attempts; repeated pruning returns a no-store 503 asking the operator to retry.

| Context key | Meaning / frontend responsibility |
|---|---|
| `run` | Selected AnalyticsRun, or `None`; use its cutoff, finished_at and summary_version for freshness/version labels. Its inventory is already loaded. |
| `range_key`, `range_keys`, `range_message`, `compare` | Validated selection, permitted keys, visible validation message (empty when valid), exact comparison toggle |
| `empty_message` | Nonempty when no completed run exists. Render a successful empty panel and skip the data sections below. |
| `latest_complete_date`, `span`, `granularity` | Singapore *L*, inclusive selected Span (start/end/length), daily or weekly |
| `summary`, `series`, `categories`, `sizes`, `top_sellers` | Existing query result types: Summary, list of BucketSales, CategorySales, SizeSales (smallest size first) and TopSeller; sellers are shoe models (all sizes together), capped at 10 |
| `comparison_span`, `comparison_available` | Previous equal-length Span when requested, otherwise None; availability requires complete window/history support |
| `comparison_summary`, `comparison_series`, `comparison_categories`, `comparison_sizes`, `comparison_top_sellers` | Corresponding query values when available, otherwise None/empty lists. Series uses shifted selected buckets; align by index. Show insufficient history when requested but unavailable, and n/a for differences against zero. Do not compare inventory metrics. |
| `sales_cards` | Two presentation cards (Sales value, Units sold), each with `label`, `value` and a `metric` holding `state` (off, insufficient, na or available), `previous`, `delta`, `percent` and `kind` (money or units) |
| `trend_chart`, `trend_rows` | Chart payload (labels, values, units, optional comparison values/units) and table rows pairing each selected bucket with its comparison bucket by index |
| `category_rows`, `category_chart` | Rows align the union of selected and prior categories (selected query order, then prior-only query order), zero-filling absent sides when comparison is available. Each row has selected/comparison CategorySales; comparison is None when unavailable/off. Chart labels/values/units use the same order, with comparison values/units or None. |
| `size_rows`, `size_chart` | Rows align the union of selected and prior sizes, smallest first, zero-filling a missing side; chart labels (`US 9.5`) and units follow the same order, with comparison units or None |
| `coverage_page`, `coverage`, `coverage_pager` | Every CoverageRow of the run's sealed inventory in query-defined urgency order, paged 10 per page by `coverage_page`; `coverage` is the current page's rows and `coverage_pager` holds the page plus previous/next URLs that keep the other parameters. Fixed seven-date metrics independent of range. `avg_daily_units` is set to None for insufficient_history; templates must label that state and show no numeric average, coverage or flag. No-sales status is unavailable. |
| `coverage_counts` | Counts across the entire sealed inventory, keyed by flagged, ok, unavailable and insufficient_history, including zeros |
| `segment_overview` | Latest selected model for this run, or None; contains model_version, full group counts and RFM/sales summaries, unaffected by the sample cap. None means no results loaded for this run, never an older-run fallback or inferred running/failed state. Label own run/cutoff and lifetime history independently of dashboard filters. |
| `segment_customers_page`, `segment_customers`, `customers_pager` | Bounded balanced sample of SegmentCustomer rows (at most 50), paged 10 per page by `customers_page` for display only; None, an empty list and None when no segments are loaded. customer_reference is CUS-<User PK>, with segment_label and RFM values, never login usernames. Show sample count separately from overview totals; see [serving contract](ANALYTICS.md#segment-serving-contract). |
| `run_short_id`, `cutoff_label`, `refreshed_label` | Presentation labels: first block of the run's summary_version, and the cutoff and finish time in Singapore time (`Unknown` when finished_at is missing) |

Data-section keys are present only when `run` is not None. Query result fields remain defined in `src/reporting/queries.py`; sales amounts are Decimal, dates are date objects. Format them for tables and use `json_script` for chart payloads. No safe-marked product names or executable JSON are supplied. Templates must not traverse per-product relations; the provided rows contain the display fields. Table caps do not affect inventory counts. Full rendering/query budgets and chart payload safety still require frontend verification.
