# Storefront redesign and dark mode

Frontend-only implementation of the reviewed design deck. Snapshot date: 24 September 2026, reconciled with `main` at `f5c6557`. This is a plan and decision record, not a contract: visual values live in [DESIGN.md](../../DESIGN.md), the frontend surface rules in [FRONTEND.md](../FRONTEND.md), and route/permission behaviour in [API.md](../API.md). Where this file and a contract disagree, the contract wins.

## History: two passes

The redesign landed in two commits on branch `UIUX`, and the second replaced the first one's visual language:

| Pass | Commit | Date | What it did |
|---|---|---|---|
| 1 | `d07b235` | 22 Sep 2026 | Fixed the six layout defects below, added the storefront CSS layer, dark mode, icon sprite, cart stepper and summary panel, on the original Starbucks-derived look (green accent, cream surfaces, rounded corners). |
| 2 | `d147c9d` | 23 Sep 2026 | Re-implemented the whole look against **VoiceBox** (black, white, one red; square; flat), added motion, replaced `DESIGN.md`, and added a presentation-only statistics preview. |

**Pass 2 is the current design.** Decisions that only belonged to pass 1 are listed under [Superseded](#superseded-pass-1-decisions) so nobody implements from them. The layout defects and structural fixes from pass 1 still stand.

## Why

The frontend foundation (home page, tokens, states, HTMX preview) was built and independently reviewed. The storefront pages that followed — catalogue, cart, checkout, order history, confirmation, operator list — were wired up afterwards and reuse the foundation's preview components. An audit of the running app at 1280px and 390px found six defects, three of them blocking:

1. No page container on any shop page. Only `foundation/home.html` wraps itself in `.page-shell`, so every other page renders flush to the viewport edge.
2. `.operator-row` declares a fixed six-track grid shared by four tables. The cart supplies five cells and checkout four, leaving one or two dead tracks; `min-width: 60rem` forces horizontal scroll.
3. That same minimum makes the cart unusable on a phone: Remove and the line total sit off-screen with no affordance.
4. Subtotals and totals render as `.form-note` (1.2rem, secondary text) while page titles inherit the marketing `h1` clamp and render up to 7.4rem.
5. Quantity inputs have no visible label; stock status is carried by a colour-only dot with a `title` attribute.
6. The header still carries foundation-preview chrome (Overview, Patterns, States anchors, a status chip, a System status button) alongside Shop, Cart and Orders, and wraps to two lines below about 1100px.

## Scope

Frontend-owned only: templates, CSS, minimal JavaScript. Pass 1 changed no view, model, form, URL or migration, so it sits outside the mandatory backend review gate in [AGENTS.md](../../AGENTS.md).

**Pass 2 added one deliberate exception:** the statistics preview, a design comp of the operator dashboard. It adds a view `config.views.statistics_preview`, the route `foundation/statistics/` (name `statistics-preview`) and two tests in `tests/test_frontend.py`. It has no data, no permission check and reads no analytics table (a test asserts zero queries), and the page says on its face that every number is invented. It is not the real dashboard: that is `/analytics/` (batch 6c, built independently on `CL/Analytics`).

## Visual language (pass 2, current)

Authoritative values are in `DESIGN.md` and the token block at the top of `site.css`; this is the summary.

- **VoiceBox:** black, white and a single red. Every corner is square (`--card-radius`, `--panel-radius`, `--chip-radius` and `--pill-radius` are all `0`), no shadows (`--card-shadow: none`), 2px structural borders (`--border-structural`). Hierarchy comes from weight, scale and black/white contrast, not elevation.
- **Red is a fill, a rule or a mark, not small text.** `--color-secondary` (`#ef4444`) reaches only 3.61:1 on the page ground; text that must be red uses `--color-secondary-ink` (6.20:1). Status text is one shade darker than `DESIGN.md`'s own values, which sit near 3:1 on their tints.
- **Token names follow `DESIGN.md`'s palette tables.** Rules are meant to use role tokens (`--action-fill`, `--on-action`, `--band-fill`, `--band-ink`, `--surface-header`, `--card-border` and others) rather than palette values, because a fill and its ink flip in opposite directions between themes: re-pointing a token restyles the site. `--on-action` is separate from `--band-ink` because the primary button and an always-dark band invert in opposite directions.
- **Typography:** Archivo Black for display, Work Sans for body, Space Mono for figures and labels that need tabular alignment (for example `.stat-tile__value`). Loaded from Google Fonts with `display=swap` and the existing stack as fallback; self-hosting is out of scope. All three are SIL Open Font License.
- **Icons:** Phosphor (MIT) regular-weight glyphs as one SVG sprite at `src/static/img/icons.svg`, referenced with `<use>` through `templates/_icon.html`. One family, one weight, no hand-drawn paths. Unchanged from pass 1.

### Dark mode

- Default follows `prefers-color-scheme`; a header control (`data-theme-toggle`) overrides it and persists the choice in `localStorage`. An inline head script applies the stored choice before first paint.
- The dark palette inverts the neutrals (`--color-primary` `#fafafa`, background `#0a0a0a`, surface `#141414`, raised `#1c1c1c`) and keeps the red's hue: the fill token stays `#ef4444` (5.26:1 on the dark ground) while red text and the error colour lift to `#f87171`.
- Dark tokens are declared twice on purpose: once under `@media (prefers-color-scheme: dark)` guarded by `:root:not([data-theme="light"])`, once under `:root[data-theme="dark"]`. Anything that changes a token must change both.

### Motion

Added in pass 2 (`site.js`, `site.css`). When an HTMX cart swap changes the subtotal, the figure inverts instantly and releases over 420ms (`is-updated`), and only when the value actually changed. Under `prefers-reduced-motion` everything that moves is removed but opacity and colour changes are kept, because they carry meaning (what is in flight, what just changed).

## Batches

Each batch is independently shippable. Batches 1 to 4 are pass 1; batch 5 is pass 2.

| # | Name | Files |
|---|---|---|
| 1 | Frame and tokens | `site.css` (tokens, dark mode, page frame, type scale), `base.html` |
| 2 | Cart and checkout | `cart/_content.html`, `cart/detail.html`, `orders/checkout.html`, `site.css`, `site.js` |
| 3 | Catalogue and orders | `catalogue/_product_card.html`, `catalogue/product_list.html`, `catalogue/manage_list.html`, `orders/list.html`, `orders/detail.html` |
| 4 | Shell and states | `base.html`, `404.html`, `503.html`, `registration/login.html`, `accounts/register.html`, `accounts/_form_fields.html` |
| 5 | VoiceBox restyle | `DESIGN.md`, `docs/FRONTEND.md`, `PROJECT_SCOPE_INF2006.md` (design-reference wording), `site.css` (token and rule rewrite), `site.js` (motion), `base.html` (fonts), `foundation/statistics.html`, `config/views.py`, `config/urls.py`, `tests/test_frontend.py` |

## Component decisions

- **Buttons** come from the design system's variants (`.button--dark`, `--light`, `--outline-*`, `--compact`, `--lg`, `--block`). The primary action is the `--action-fill` fill (black in light, near-white in dark), turning red on hover; the main action still earns attention through size, isolation and position.
- **Summary panel** is the one new shared component from pass 1. Cart and checkout both use it; it owns the total, the caveat and the forward action.
- **Quantity stepper** (`.stepper`) replaces the bare 60px spinner and its wrapping Update button. The label is real. Changing the value posts through the existing HTMX endpoint, so Update disappears.
- **Stock signal** carries a shape, a word and a number instead of a coloured dot: an icon plus "Out of stock", "Only N left" or "In stock · N".
- **Cart badge** renders from `user.cart.items.count` in the template. `Cart.DoesNotExist` subclasses `ObjectDoesNotExist`, whose `silent_variable_failure` is true, so a user with no cart row renders empty rather than erroring. This keeps the change frontend-owned; a context processor would be cleaner but is a backend module and would trip the review gate.
- **Foundation-preview chrome** moves from the header to the footer under a "Project evidence" heading, so marking evidence stays reachable without competing with Shop, Cart and Orders.

## What must not change

- The home page (`foundation/home.html`) and its component classes. It is reviewed evidence; it inherits the tokens and must render correctly in both themes, but its markup stays.
- Views, models, forms, URLs, migrations, checkout idempotency and the review fingerprint (the statistics preview is the single recorded exception, above).
- HTMX endpoints, targets and swap semantics.
- Six strings asserted by the test suite: `"indicative"`, `"no longer available"`, `"changed"`, `"haven't placed any orders"`, `id="cart-content"`, `"This path is not ready yet."`
- The statistics preview must keep saying its numbers are invented and must keep making zero queries.

## Verification

- Targeted suites: `tests/test_frontend.py` (includes the statistics preview tests), `test_catalogue.py`, `test_cart.py`, `test_orders.py`, `test_accounts.py`.
- Live HTTP walk of the whole purchase flow at 1440px and 390px, in both themes, per the frontend contract's requirement that template inspection is not proof of Django/HTMX behaviour. Recorded for pass 1 (381 tests, tracker entry of 22 September); **not recorded for pass 2**, so the VoiceBox restyle has no documented walk yet.
- Contrast spot-checks on the dark palette.

## Known issues and open items

- **`--band-ink-soft` is undefined in light mode.** It is declared only in the two dark blocks but used by six rules, so in light mode those declarations fall back to inherited colour. Not yet fixed; anything new should avoid the token until it is defined in `:root`.
- **`DESIGN.md`'s original source and licence are not recorded.** `PROJECT_SCOPE_INF2006.md` lists this as an outstanding attribution task; `DESIGN.md` section 7 says only that the project owner supplied it.
- **The real dashboard and the statistics comp are separate work.** `/analytics/` was written and reviewed against the pre-VoiceBox palette and aligned to the tokens afterwards ([dashboard-theme-alignment.md](dashboard-theme-alignment.md)). Whether the comp's layout (static SVG chart, four stat tiles including "Orders" and "Average order") should replace the dashboard's markup is undecided, as is whether the backend supplies those two figures.

## Superseded (pass 1 decisions)

Kept so the history is legible. Do not implement from these:

- **Colour:** "light theme tokens stay byte-identical" to the original green scheme, and the dark accent derived from that green (`hsl(159, 73%, 27%)` to `hsl(159, 55%, 62%)`). Replaced by the VoiceBox palette.
- **Typography:** Manrope for headings and Inter for body and numbers. Replaced by Archivo Black, Work Sans and Space Mono.
- **Primary button:** "Spruce fill, no second fill colour". Replaced by `--action-fill`.
- **Radius scale:** pill for interactive, 16 for the summary panel, 12 for cards, 8 for media, inputs and chips. Replaced by square corners everywhere.
