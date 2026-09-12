# Route and interaction contract

Status: proposed routes, not implemented endpoints. Django HTML/HTMX is the baseline, not a separate REST service. Finalise route names in the first implementation and update this contract.

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
| GET `/health/` | Infrastructure | Lightweight app readiness; final dependency policy documented in infrastructure |

## Inputs and responses

Use Django forms/validation and CSRF on all browser mutations, including HTMX. GET does not mutate business state. Standard HTML uses forms and redirects after successful POST; HTMX returns documented fragments or redirects. Finalise form field names and fragment IDs before splitting backend/frontend work.

Validate quantities, pagination bounds, reporting periods and product availability. Derive identity/prices/totals server-side. Normal unauthenticated navigation redirects to login with a safe return path. Handle HTMX session expiry explicitly so login HTML does not appear inside a cart fragment.

Use 403 for forbidden operator/CSRF access, 404 for inaccessible foreign cart/order objects, 409 for stock/idempotency conflicts and 503 for temporary dependency unavailability. Form errors may re-render at 200 with field messages; tests must check behaviour, not status alone. Configure handling of non-2xx HTMX fragments explicitly.

Equivalent checkout replay returns the existing order; changed payload with the same key conflicts. Preserve the key after uncertain network outcomes. Never create a new key automatically solely because a response timed out. See [schema](SCHEMA.md).

Return only public/owner/operator-appropriate fields. Authorise before accessing cached operator results; never share personalised fragments across users.
