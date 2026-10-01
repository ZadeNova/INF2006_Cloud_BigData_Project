# Backend delta review by Claude Opus 5.5 (owner-accepted reviewer)

Task ID `opus-delta-review`. A review of the backend-owned changes made after the last Astra-cleared state, requested by the project owner on 24 September 2026. **This is not an Astra review.** The gate in [AGENTS.md](../../AGENTS.md) and [DEVELOPMENT.md](../DEVELOPMENT.md#backend-review-gate) names Astra Medium; the project owner formally accepted Claude Opus 5.5 as the reviewer for this delta on 24 September 2026 (a recorded deviation from the documented process, owner's decision).

## Independence, stated plainly

- The reviewer is the same model family that wrote most of the reviewed diff (the review fixes and the checkout subtotal change were written with Claude Sonnet 5/Opus 5.5 in the same working session).
- The review ran in that same session, **not a fresh context**, so the reviewer knew why each change was made. It is therefore weaker than an independent review and should be described that way in the report and in `AI_USE_DECLARATION.md`.
- Findings below are what this reviewer could establish by reading the diff and running checks. Absence of a finding is not evidence that an independent reviewer would find nothing.

## Scope

- **Base and head:** `origin/CL/Analytics` (`6ecc0e7`, the Astra-cleared dashboard state) to `24a31dc`, restricted to backend-owned files: `src/config/urls.py`, `src/config/views.py`, `src/orders/views.py`, `src/compose.yaml`, and the tests that changed with them (`tests/test_frontend.py`, `test_orders.py`, `test_accounts.py`, `test_analytics_dashboard.py`). No migrations changed in this range.
- **Also read, outside the mandatory gate:** the storefront templates, `site.js`, `analytics.js` and the vendored HTMX, during the codebase review the same day.
- **Not reviewed here:** anything already cleared by Astra (checkout service, cart, import, refresh, dashboard queries and view), visual appearance, and anything on AWS.
- **The auto-merge itself** (`fc40b34`, `CL/Analytics` into the UIUX-carrying branch) was checked by diffing the final Python against `CL/Analytics`: the only differences are the intentional ones below plus `statistics_preview`, which comes from `main`'s UIUX commit. No unintended source change.

## Result

**No blocking findings.** Two advisory (P3) items and one note were raised; all three were fixed the same day (see Resolution).

## Checks run

- Full suite at `5d5c896`: **440 passed** (Docker, real PostgreSQL). Later commits are documentation only.
- `manage.py check`: no issues. `makemigrations --check --dry-run`: no changes.
- Read the complete Python diff above (four source files, about 45 changed lines).
- Live HTTP checks on a disposable project: `/` gives 302 to `/products/`; `/foundation/` gives 200; `/register/`, a 404 page and `/analytics/` behave as expected; no CDN reference remains in served pages.
- Checked call sites: no reference to the removed `home` view function remains in `src/` or `tests/`; the only remaining use of the `home` URL name is the brand link in `base.html` (the logout redirect uses the literal path `/`).

## Findings

| ID | Sev | Location | Finding | Recommendation |
|---|---|---|---|---|
| OPUS-001 | P3 | `src/config/urls.py:8` | `RedirectView` answers every HTTP method with a redirect. Before this change `/` was a `require_safe` view, so `POST /` returned 405. Now a POST, PUT or DELETE to `/` returns 302 (or 403 from CSRF middleware for a bare POST). No security or data effect, but it loosens an earlier contract and nothing tests it. | Pass `http_method_names=["get", "head"]` to `RedirectView.as_view(...)` and add a test that `POST /` is 405. |
| OPUS-002 | P3 | `src/templates/orders/checkout.html:65-68` | The subtotal now leaves out deactivated lines, but the summary row still reads "N products" with N counting every line, next to a total that excludes some. The cart page deliberately avoids putting both on one row (see the comment in `cart/_content.html`). With one deactivated line a shopper sees "2 products S$20.00" for a basket that shows three lines. | Either count only available lines in that row or reuse the cart's wording ("Items in your cart" without a price). Presentation only. |
| OPUS-003 | note | `src/templates/base.html:40`, `settings.py:103` | The brand link and `LOGOUT_REDIRECT_URL` still target `/`, so each now costs one extra redirect before reaching the catalogue. Harmless. | Optional: point both at `catalogue:product_list`. |

Checked and found sound: `RedirectView` with `pattern_name` returns a temporary redirect and resolves the URL by name, so it follows any future path change; the `foundation/` route cannot shadow `foundation/design-notes/` or `foundation/statistics/`; `cart_subtotal(items)` receives the list `_prepare` already fetched with `select_related("product")`, so the change adds no queries; `item.line_total` is `quantity * product.price`, identical to the arithmetic it replaces; when an order can succeed (every line active and in stock) the displayed total equals the order total, and when it cannot, `Place order` still refuses the whole order; the fingerprint still covers every line including deactivated ones, so the replay and change-detection rules are untouched; the `:z` label on the data mount only relabels the repository's `data/` directory and is ignored without SELinux; the new tests fail without their fixes (the subtotal test failed at 27.50 against 20.00 before the change).

## Resolution (24 September 2026)

The owner asked for OPUS-001 to OPUS-003 to be fixed; plan [opus-review-fixes.md](../archive/plans/opus-review-fixes.md).

| ID | Fix | Regression |
|---|---|---|
| OPUS-001 | `RedirectView` restricted to GET and HEAD | `test_the_site_root_lands_on_the_catalogue` now also asserts HEAD is 302 and POST is 405 |
| OPUS-002 | The checkout row reads "N available product(s)", counted from active lines (`available_count` in the view context) | the deactivated-line test asserts `available_count == 1` and the row text |
| OPUS-003 | Brand link goes to the catalogue; `LOGOUT_REDIRECT_URL` is `/products/` | the logout test expects `/products/`; a live check showed the brand link `/products/`, GET and HEAD `/` 302, POST `/` 405 |

After the fixes: full suite **440 passed**, `manage.py check` clean, `makemigrations --check` no changes. The fixes were made by the same author as the code they amend, and were not re-reviewed by anyone else; they are 15 lines.

## Limitations

Same-session, same-family review (see above). No browser check of the cart stepper (`hx-sync`), the 404 reload, or the register page after the help-text change. No `EXPLAIN`, load or concurrency run for this delta (none of it touches locking or queries). Nothing was run against AWS.

## Status

Reviewed; no blocking findings; OPUS-001 to OPUS-003 fixed and tested. **Gate treated as CLEARED for this delta by the project owner's acceptance of Claude Opus 5.5 as reviewer (24 September 2026)**, a deviation from the Astra-only gate and not independent of the author (see above). The fixes themselves had no second review.
