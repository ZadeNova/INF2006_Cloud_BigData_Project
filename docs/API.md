# Route and interaction contract

Status: GET/HEAD /health/ (URL name health), the presentation-only GET/HEAD / foundation preview, the presentation-only GET/HEAD /foundation/design-notes/ fragment and the presentation-only 503 failure preview are implemented. GET/POST /register/, GET/POST /login/ and POST /logout/ (accounts:register/login/logout) and GET /products/ (catalogue:product_list) are also implemented. Cart, checkout, order history and analytics routes below remain reserved contracts for follow-up tasks, not callable endpoints. Django HTML/HTMX is the baseline, not a separate REST service.

| Method / route | Access | Behaviour |
|---|---|---|
| GET, POST `/register/` | Public | Registration form and validation |
| GET, POST `/login/` | Public | Framework session authentication |
| POST `/logout/` | Authenticated | Invalidate session; CSRF required |
| GET `/products/` | Public | Paginated active catalogue; indicative stock |
| GET `/cart/` | Authenticated | Owner's persistent cart |
| POST `/cart/items/` | Authenticated | Add product/positive quantity |
| POST `/cart/items/<id>/update/` | Owner | Replace quantity with bounds validation |
| POST `/cart/items/<id>/delete/` | Owner | Remove item |
| POST `/checkout/` | Authenticated | Request ID/fingerprint and atomic simulated checkout |
| GET `/orders/` | Authenticated | Owner's order history |
| GET `/orders/<id>/` | Owner | Persisted order confirmation/detail |
| GET `/analytics/` | Operator | Period-labelled sales/inventory analytics |
| GET, HEAD `/health/` | Infrastructure | Process liveness: 200 JSON {"status":"ok"}, no-store, no DB query; explicit allowed-host validation |
| GET, HEAD `/` | Public preview | Presentation-only frontend foundation page; no account, catalogue or checkout data |
| GET, HEAD `/foundation/design-notes/` | Public preview | Presentation-only HTMX fragment; no business state or user data |
| GET, HEAD `/foundation/design-notes-unavailable/` | Public preview | Presentation-only 503 HTMX failure fragment used to verify retry/error presentation; no business state or user data |

## Inputs and responses

Use Django forms/validation and CSRF on all browser mutations, including HTMX. GET does not mutate business state. Standard HTML uses forms and redirects after successful POST; HTMX returns documented fragments or redirects. Finalise form field names and fragment IDs before splitting backend/frontend work.

Validate quantities, pagination bounds, reporting periods and product availability. Derive identity/prices/totals server-side. Normal unauthenticated navigation redirects to login with a safe return path. Handle HTMX session expiry explicitly so login HTML does not appear inside a cart fragment.

Use 403 for forbidden operator/CSRF access, 404 for inaccessible foreign cart/order objects, 409 for stock/idempotency conflicts and 503 for temporary dependency unavailability. Form errors may re-render at 200 with field messages; tests must check behaviour, not status alone. Configure handling of non-2xx HTMX fragments explicitly.

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

These names cannot be reversed until their follow-up URL modules exist. Do not add fake authentication or cart routes merely to render the shell. Checkout/history/analytics names and payload details will be finalized with their backend tasks before dependent frontend integration.

Future cart HTMX responses target id cart-content using outerHTML and template cart/_content.html; full HTML uses cart/detail.html. Backend will pass cart and validated form/errors, derive totals/prices/owner, and keep the fragment wrapper stable. Authentication expiry should return an HX-Redirect to login rather than login HTML in the fragment. Error fragment handling (including 409/503) must be explicitly wired and tested by the later backend/frontend integration. This is a contract, not implemented HTMX behaviour.

Health validates DJANGO_ALLOWED_HOSTS and remains exempt from HTTPS redirection for internal probes; it exposes no dependency diagnostics, credentials or sessions. Use python manage.py check_database for operator readiness: exit 0 with database/migrations status, nonzero sanitized error for unavailable PostgreSQL or unapplied migrations. Do not use database readiness as an ASG replacement trigger during a shared RDS outage. Actual ALB probe Host/allowed-host handling is a later infrastructure integration gate.

The later catalogue/cart backend must select an explicit demo fixture namespace server-side and reject cross-namespace cart contents before checkout. Do not accept a namespace from a browser as authority; actual namespace selection follows dataset/fixture acceptance.
