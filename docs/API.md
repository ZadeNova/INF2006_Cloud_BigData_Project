# Route and interaction contract

Status: GET/HEAD /health/ (URL name health), the presentation-only GET/HEAD / foundation preview, the presentation-only GET/HEAD /foundation/design-notes/ fragment and the presentation-only 503 failure preview are implemented. GET/POST /register/, GET/POST /login/ and POST /logout/ (accounts:register/login/logout) and GET /products/ (catalogue:product_list) are also implemented. GET /products/manage/ and POST /products/manage/<id>/toggle-active/ (catalogue:manage_list/product_toggle_active) are a deliberate, narrow scope addition beyond the assessed brief — see PROJECT_SCOPE_INF2006.md's "Outside INF2006" note and docs/IMPLEMENTATION_PLAN.md for status. GET /cart/, POST /cart/items/, POST /cart/items/<id>/update/ and POST /cart/items/<id>/delete/ (cart:detail/add/update/delete) are also implemented, including the HTMX fragment/HX-Redirect contract described below. GET/POST /checkout/, GET /orders/<id>/ and GET /orders/ (orders:checkout/detail/list) are also implemented, per docs/plans/batch-04-checkout.md and docs/plans/batch-05-order-history.md. GET /analytics/ (reporting:dashboard) is specified below, including its query parameters and HTMX fragment, but not implemented; it remains a reserved contract for a follow-up task, not a callable endpoint. Django HTML/HTMX is the baseline, not a separate REST service.

| Method / route | Access | Behaviour |
|---|---|---|
| GET, POST `/register/` | Public | Registration form and validation |
| GET, POST `/login/` | Public | Framework session authentication |
| POST `/logout/` | Authenticated | Invalidate session; CSRF required |
| GET `/products/` | Public | Paginated active catalogue; indicative stock |
| GET `/products/manage/` | Operator | All products including inactive ones; scope addition beyond the assessed brief |
| POST `/products/manage/<id>/toggle-active/` | Operator | Set a product's active state explicitly via `active=true`/`active=false`; CSRF required; no create/edit |
| GET `/cart/` | Authenticated | Owner's persistent cart |
| POST `/cart/items/` | Authenticated | Add product/positive quantity |
| POST `/cart/items/<id>/update/` | Owner | Replace quantity with bounds validation |
| POST `/cart/items/<id>/delete/` | Owner | Remove item |
| GET, POST `/checkout/` | Authenticated | Review page that renders a fingerprint of the displayed cart lines; POST with CSRF and that `review` value, verified against the locked cart; session-derived idempotency key; atomic simulated checkout |
| GET `/orders/` | Authenticated | Owner's paginated order history, most recent first |
| GET `/orders/<id>/` | Owner | Persisted order confirmation/detail |
| GET `/analytics/` | Operator | Period-labelled sales/inventory analytics from the latest completed run; optional `range` and `compare` query parameters; HTMX requests receive only the `#analytics-panel` fragment. See [analytics](ANALYTICS.md#dashboard-get-analytics-operator-only) |
| GET, HEAD `/health/` | Infrastructure | Process liveness: 200 JSON {"status":"ok"}, no-store, no DB query; explicit allowed-host validation |
| GET, HEAD `/` | Public preview | Presentation-only frontend foundation page; no account, catalogue or checkout data |
| GET, HEAD `/foundation/design-notes/` | Public preview | Presentation-only HTMX fragment; no business state or user data |
| GET, HEAD `/foundation/design-notes-unavailable/` | Public preview | Presentation-only 503 HTMX failure fragment used to verify retry/error presentation; no business state or user data |

## Inputs and responses

Use Django forms/validation and CSRF on all browser mutations, including HTMX. GET does not mutate business state. Standard HTML uses forms and redirects after successful POST; HTMX returns documented fragments or redirects. Finalise form field names and fragment IDs before splitting backend/frontend work.

Validate quantities, pagination bounds, reporting periods and product availability. Derive identity/prices/totals server-side. Normal unauthenticated navigation redirects to login with a safe return path. Handle HTMX session expiry explicitly so login HTML does not appear inside a cart fragment.

Use 403 for forbidden operator/CSRF access, 404 for inaccessible foreign cart/order objects, 409 for stock/idempotency conflicts and 503 for temporary dependency unavailability. The 503 is implemented for database failures by `config.middleware.DatabaseUnavailableMiddleware`: `OperationalError` and `InterfaceError` only (connection failures, timeouts, deadlocks), a database-free page with `Retry-After: 5` and `Cache-Control: no-store`, no exception text; integrity and programming errors remain 500. HTMX requests receive the same 503 and `site.js` shows an inline notice, since HTMX does not swap error responses. Checkout keeps its idempotency key across a 503 so a retry resolves any committed order. Form errors may re-render at 200 with field messages; tests must check behaviour, not status alone. Configure handling of non-2xx HTMX fragments explicitly.

Equivalent checkout replay returns the existing order; changed payload with the same key conflicts. Preserve the key after uncertain network outcomes. Never create a new key automatically solely because a response timed out. See [schema](SCHEMA.md).

Return only public/owner/operator-appropriate fields. Authorise before accessing cached operator results; never share personalised fragments across users.

## Foundation handover to frontend and later backend tasks

Paths: src/templates/base.html is the shared shell and the presentation-only foundation preview lives at src/templates/foundation/home.html; future page templates live under accounts/, registration/, catalogue/ and cart/ inside src/templates/. Shared assets live in src/static/ (css/site.css and js/site.js); HTMX 2.0.4 is loaded from a version-pinned jsDelivr URL in the shell. Django app-template discovery and WhiteNoise manifest static storage are configured; rebuild the Docker image after changing templates/static files. No authentication, catalogue, cart, checkout or analytics views were created by the foundation preview. Template inheritance reserves title, content, head and scripts blocks. Luna Max owns presentation and live visual verification.

Reserved integration contracts (to implement and verify in the named backend follow-up):

| Follow-up | Reserved URL name / template | Form or query fields |
|---|---|---|
| Authentication | accounts:register / accounts/register.html | username, password1, password2; framework password validation |
| Authentication | accounts:login / registration/login.html | username, password, optional safe next |
| Authentication | accounts:logout | POST with CSRF; no owner/user ID supplied |
| Catalogue | catalogue:product_list / catalogue/product_list.html | page: positive integer; backend-bounded pagination |
| Cart | cart:detail / cart/detail.html | GET owner cart; no owner ID supplied |
| Cart add | cart:add | product_id, quantity integer 1..999 |
| Cart update | cart:update | URL item ID, quantity integer 1..999 |
| Cart delete | cart:delete | URL item ID; POST with CSRF |
| Checkout | orders:checkout / orders/checkout.html | GET renders the review page with a hidden `review` field (64-character lowercase hex fingerprint of the displayed lines, price excluded); POST with CSRF and `review`. The idempotency key is session-derived, not submitted. A missing or malformed `review` redirects to the review page; a well-formed value that no longer matches the locked cart is rejected as changed (200, nothing written); the same key with a different `review` conflicts (409) |
| Order detail | orders:detail / orders/detail.html | URL order ID; GET, owner-only |
| Order history | orders:list / orders/list.html | GET owner's orders; page: positive integer; backend-bounded pagination (10 per page) |
| Analytics | reporting:dashboard / reporting/dashboard.html, fragment reporting/_panel.html | GET, operator only; `range`: one of `7d`, `30d` (default), `90d`, `mtd`, `ytd`; `compare`: `1` to enable, absent otherwise; no user, run or date fields from the client |

These names cannot be reversed until their follow-up URL modules exist. Do not add fake authentication or cart routes merely to render the shell. The analytics dashboard contract is described in the next section; the operator permission and any custom from/to range are finalized in its backend task before dependent frontend integration.

Analytics dashboard HTMX contract (reserved, not implemented): filter and preset controls use `hx-get` with `hx-target="#analytics-panel"`, `hx-swap="outerHTML"` and `hx-push-url="true"`. Full HTML uses reporting/dashboard.html; an HTMX request (`HX-Request: true`) receives only reporting/_panel.html, whose `id="analytics-panel"` wrapper stays stable. Invalid `range` re-renders at 200 with the default range and a visible message. The client never supplies a run ID or dates; the server reads the latest completed run and derives the span from the whitelisted `range`. Session expiry returns an HX-Redirect to login, and a non-operator receives 403; both must be handled explicitly rather than swapped into the panel.

Future cart HTMX responses target id cart-content using outerHTML and template cart/_content.html; full HTML uses cart/detail.html. Backend will pass cart and validated form/errors, derive totals/prices/owner, and keep the fragment wrapper stable. Authentication expiry should return an HX-Redirect to login rather than login HTML in the fragment. Error fragment handling (including 409/503) must be explicitly wired and tested by the later backend/frontend integration. This is a contract, not implemented HTMX behaviour.

Health validates DJANGO_ALLOWED_HOSTS and remains exempt from HTTPS redirection for internal probes; it exposes no dependency diagnostics, credentials or sessions. Use python manage.py check_database for operator readiness: exit 0 with database/migrations status, nonzero sanitized error for unavailable PostgreSQL or unapplied migrations. Do not use database readiness as an ASG replacement trigger during a shared RDS outage. Actual ALB probe Host/allowed-host handling is a later infrastructure integration gate.

The later catalogue/cart backend must select an explicit demo fixture namespace server-side and reject cross-namespace cart contents before checkout. Do not accept a namespace from a browser as authority; actual namespace selection follows dataset/fixture acceptance.
