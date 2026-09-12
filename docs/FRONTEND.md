# Frontend contract

Read [DESIGN.md](../DESIGN.md), [API](API.md) and [security](SECURITY.md). Implementation model: Luna Max, selected by the user or explicitly authorised delegation.

## Surface and ownership

Django templates, HTML/CSS, HTMX and minimal JavaScript. No React/Next, client-side auth store or separate frontend deployment. Pages: registration/login, catalogue, cart/checkout, confirmation/history and protected analytics.

Use a shared base template, reusable forms/product components and named HTMX fragments. Confirm actual template/static paths during scaffolding. Backend owns routes, permission checks and business logic; frontend owns presentation and interactions. Agree fragment contracts first.

## Design and states

Adapt the cream/green design reference with the project's own branding and licensed assets/fonts. Keep visual values in DESIGN and use shared CSS tokens with consistent units. Do not add rewards, careers or drink features from reference examples.

Define loading, empty, validation and dependency-error states. Label payments as simulated. Catalogue stock is indicative; explain sold-out checkout outcomes. Preserve the checkout request key across uncertain retries; button disabling is not server-side idempotency.

Analytics shows reporting period, units, refresh time, formula/flag reason and zero-sales/insufficient-history messages. Do not label historical output current.

## Accessibility and verification

Use semantic forms, labels, visible keyboard focus, meaningful alt text, sufficient contrast and responsive layouts. Announce relevant HTMX updates and preserve sensible focus. Escape untrusted data rather than rendering it as HTML.

Verify actual Django routes over HTTP in a live app, including a complete workflow and an error case. Template inspection or static HTML is not proof of Django/HTMX behaviour. Record viewport and steps for visual evidence. Backend tests remain necessary; do not change unrelated backend logic just to obtain a screenshot.
