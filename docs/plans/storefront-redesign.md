# Storefront redesign and dark mode

Frontend-only implementation of the reviewed design deck. Snapshot date: 22 September 2026, branch `UIUX`. This is a plan, not a contract: visual reference lives in [DESIGN.md](../../DESIGN.md), the frontend surface rules in [FRONTEND.md](../FRONTEND.md), and route/permission behaviour in [API.md](../API.md). Where this file and a contract disagree, the contract wins.

## Why

The frontend foundation (home page, tokens, states, HTMX preview) was built and independently reviewed. The storefront pages that followed — catalogue, cart, checkout, order history, confirmation, operator list — were wired up afterwards and reuse the foundation's preview components. An audit of the running app at 1280px and 390px found six defects, three of them blocking:

1. No page container on any shop page. Only `foundation/home.html` wraps itself in `.page-shell`, so every other page renders flush to the viewport edge.
2. `.operator-row` declares a fixed six-track grid shared by four tables. The cart supplies five cells and checkout four, leaving one or two dead tracks; `min-width: 60rem` forces horizontal scroll.
3. That same minimum makes the cart unusable on a phone: Remove and the line total sit off-screen with no affordance.
4. Subtotals and totals render as `.form-note` (1.2rem, ink-soft) while page titles inherit the marketing `h1` clamp and render up to 7.4rem.
5. Quantity inputs have no visible label; stock status is carried by a colour-only dot with a `title` attribute.
6. The header still carries foundation-preview chrome (Overview, Patterns, States anchors, a status chip, a System status button) alongside Shop, Cart and Orders, and wraps to two lines below about 1100px.

## Scope

Frontend-owned only: templates, CSS, minimal JavaScript. No view, model, form, URL or migration changes, so this sits outside the mandatory backend review gate in [AGENTS.md](../../AGENTS.md).

### Colour and dark mode

The user's standing constraint was to keep the colour scheme unchanged, then explicitly asked for dark mode. Resolution:

- **Light theme tokens stay byte-identical.** Every existing `--color-*` value on `:root` is preserved exactly.
- **Dark mode adds a second set**, derived from the same hues rather than invented. The accent is the existing accent lightened along its own hue (`hsl(159, 73%, 27%)` becomes `hsl(159, 55%, 62%)`), because the light accent only reaches 3.3:1 on a dark canvas and fails AA for text.
- Default follows `prefers-color-scheme`; a header control overrides it and persists the choice. An inline head script applies the stored choice before first paint.

### Typography

`site.css` names Inter but never loads it, so every page currently falls back to Segoe UI or Helvetica. [DESIGN.md](../../DESIGN.md) names Inter and Manrope as the approved substitutes for the reference's proprietary face. Manrope takes headings; Inter takes body and every number, where its tabular figures do real work. Both self-hosted is out of scope for this task; they load from Google Fonts with `display=swap` and the existing stack as fallback.

### Icons

The templates carry no icons today. Phosphor (MIT) regular-weight glyphs ship as one SVG sprite at `src/static/img/icons.svg`, referenced with `<use>`. One family, one weight, no hand-drawn paths.

## Batches

Each batch is independently shippable.

| # | Name | Files |
|---|---|---|
| 1 | Frame and tokens | `site.css` (tokens, dark mode, page frame, type scale), `base.html` |
| 2 | Cart and checkout | `cart/_content.html`, `cart/detail.html`, `orders/checkout.html`, `site.css`, `site.js` |
| 3 | Catalogue and orders | `catalogue/_product_card.html`, `catalogue/product_list.html`, `catalogue/manage_list.html`, `orders/list.html`, `orders/detail.html` |
| 4 | Shell and states | `base.html`, `404.html`, `503.html`, `registration/login.html`, `accounts/register.html`, `accounts/_form_fields.html` |

## Component decisions

- **One primary button.** Spruce fill. No second fill colour is introduced; the main action earns attention through size, isolation and position.
- **Summary panel** is the one new shared component. Cart and checkout both use it; it owns the total, the caveat and the forward action.
- **Quantity stepper** replaces the bare 60px spinner and its wrapping Update button. The label is real. Changing the value posts through the existing HTMX endpoint, so Update disappears.
- **Stock signal** carries a shape, a word and a number instead of a coloured dot.
- **Cart badge** renders from `user.cart.items.count` in the template. `Cart.DoesNotExist` subclasses `ObjectDoesNotExist`, whose `silent_variable_failure` is true, so a user with no cart row renders empty rather than erroring. This keeps the change frontend-owned; a context processor would be cleaner but is a backend module and would trip the review gate.
- **Foundation-preview chrome** moves from the header to the footer under a "Project evidence" heading, so marking evidence stays reachable without competing with Shop, Cart and Orders.
- **Radius scale** is four steps: pill for interactive, 16 for the summary panel, 12 for cards, 8 for media, inputs and chips.

## What must not change

- The home page (`foundation/home.html`) and its component classes. It is reviewed evidence; it inherits the new tokens and must render correctly in both themes, but its markup stays.
- Views, models, forms, URLs, migrations, checkout idempotency and the review fingerprint.
- HTMX endpoints, targets and swap semantics.
- Six strings asserted by the test suite: `"indicative"`, `"no longer available"`, `"changed"`, `"haven't placed any orders"`, `id="cart-content"`, `"This path is not ready yet."`

## Verification

- Targeted suites: `tests/test_frontend.py`, `test_catalogue.py`, `test_cart.py`, `test_orders.py`, `test_accounts.py`.
- Live HTTP walk of the whole purchase flow at 1440px and 390px, in both themes, per the frontend contract's requirement that template inspection is not proof of Django/HTMX behaviour.
- Contrast spot-checks on the dark palette.
