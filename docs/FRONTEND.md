# Frontend contract

Read [DESIGN.md](../DESIGN.md), [API](API.md) and [security](SECURITY.md). Implementation model: Luna Max, selected by the user or explicitly authorised delegation.

## Surface and ownership

Django templates, HTML/CSS, HTMX and minimal JavaScript. No React/Next, client-side auth store or separate frontend deployment. Pages: registration/login, catalogue, cart/checkout, confirmation/history and protected analytics.

Use a shared base template, reusable forms/product components and named HTMX fragments. Foundation paths are src/templates/ and src/static/; settings and build-time WhiteNoise collection are ready. See [integration contracts](API.md#foundation-handover-to-frontend-and-later-backend-tasks). All business URL names are registered and implemented; API.md is the authoritative route list. The storefront (catalogue, cart, checkout, order history, operator list, auth pages, 404/503) uses the VoiceBox layer in `src/static/css/site.css` with a light and a dark theme: it follows `prefers-color-scheme`, and a header control (`data-theme-toggle`) overrides it and stores the choice in `localStorage`. Decisions, superseded choices and known issues are in [storefront-redesign](plans/storefront-redesign.md). Backend owns routes, permission checks and business logic; frontend owns presentation and interactions. Agree fragment contracts first.

## Design and states

Adapt the VoiceBox design reference — black, white and one red accent, square corners, no shadows, 2px borders — with the project's own branding and licensed assets and fonts. Keep visual values in DESIGN and use shared CSS tokens with consistent units; token names follow DESIGN.md's palette tables. Red is a fill, a rule or a mark, never small text: it reaches only 3.61:1 on the page ground, so red that has to be read uses the darker `--color-secondary-ink`. Do not add article, byline, commenting or blog features from reference examples.

Define loading, empty, validation and dependency-error states. Label payments as simulated. Catalogue stock is indicative; explain sold-out checkout outcomes. Preserve the checkout request key across uncertain retries; button disabling is not server-side idempotency.

Analytics shows reporting period, units, refresh time, formula/flag reason and zero-sales/insufficient-history messages. Do not label historical output current.

## Accessibility and verification

Use semantic forms, labels, visible keyboard focus, meaningful alt text, sufficient contrast and responsive layouts. Announce relevant HTMX updates and preserve sensible focus. Escape untrusted data rather than rendering it as HTML.

Verify actual Django routes over HTTP in a live app, including a complete workflow and an error case. Template inspection or static HTML is not proof of Django/HTMX behaviour. Record viewport and steps for visual evidence. Backend tests remain necessary; do not change unrelated backend logic just to obtain a screenshot.
