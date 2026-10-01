# Analytics list pagination, and the size picker styled per DESIGN.md

Written 26 September 2026, branch `quarantine`. Status: **approved by the user 26 September 2026 (analytics restyle dropped; pagination only); implemented 26 September 2026 (sections 1 to 3); not committed.**

The user asked for two things:

- The catalogue size dropdown should follow the Inputs section of [DESIGN.md](../../../DESIGN.md).
- The two long lists on `/analytics/` should be paginated.

## 1. Size dropdown (DESIGN.md, Inputs)

| Property | Value | Current value |
|---|---|---|
| Label | 12px, weight 700, uppercase, letter-spacing 0.06em, text primary, 6px below | 11.5px secondary grey |
| Height | 44px | 46px |
| Border | 2px `--color-border-medium` | 2px `--color-border-medium` |
| Radius | 0 | 0 |
| Padding | 8px 14px | 10px 12px |
| Text | 14px Work Sans | inherited |
| Arrow | Custom square caret drawn in `currentColor`, with `appearance: none`, so the browser's rounded native arrow is gone | Native arrow |
| Focus | Border `--color-border-strong` plus the existing focus ring | Ring only |
| Disabled options | Tertiary text | Unchanged |
| Hover | Border strong, matching card and row hover (border colour only, `--dur-fast`) | |

The change is new rules on `.size-select`, plus a `.size-field__label` modifier (or a reused input label rule if one exists). It uses tokens only, no literal colours, so dark mode works.

## 2. Analytics page: pagination only (user decision, 26 September 2026)

The restyle to the statistics preview was **dropped by the user**. The only change on `/analytics/` is paging the two long lists, 10 rows per page:

| List | Now | After |
|---|---|---|
| Replenishment | The 25 most urgent sizes | **All** sizes in the run's inventory (200 for the shoe run), same urgency order, 10 per page |
| Customer segments | Top 50 (25 per segment), one table | The same top 50, 10 per page |

- **View** (`reporting/views.py`): new GET parameters `coverage_page` and `customers_page`. Django's `Paginator.get_page` runs over the lists the queries already return, so there are no new queries and no query changes. An invalid or out-of-range page falls back to the nearest valid page, not a 404, because both lists share one panel. The `insufficient_history` presentation rule still applies per row. This is backend-owned and goes through the review gate.
- **Template** (`_panel.html`): each table gets a pager in the catalogue's `.pager` markup, with Previous, "Page X of Y" and Next.
  - Links keep `range`, `compare` and the other list's page, and use the existing HTMX pattern (`hx-get`, `hx-target="#analytics-panel"`, `hx-push-url`).
  - `hx-swap="outerHTML show:#<table heading>:top"` keeps the table in view after the swap.
  - Range and compare links reset both pages to 1.
  - Copy: "Showing X–Y of N".
- Nothing else on the page changes.

## Tests

- **Dashboard:** replenishment shows 10 rows per page and page 2 continues the urgency order. The flagged/unavailable counts stay whole-inventory. The customer list pages through the top 50. An invalid page shows page 1. Pager links keep `range` and `compare`. The query count is unchanged.
- **Catalogue:** the size select still renders (markup unchanged; CSS only).
- Run the dashboard and catalogue tests, then the full suite once.

## Verification

- HTTP and browser check on the main stack (`127.0.0.1:8000`, shoe run): page through both lists with HTMX, and confirm the browser's back button restores the page.
- Screenshot the size dropdown in both themes.

## Ownership

- The size dropdown CSS is frontend-owned: Luna / Max per [AGENTS.md](../../../AGENTS.md), implemented in this session. That is a model mismatch, reported here.
- The pagination view change is backend-owned and needs the review gate.

## 3. Analytics fonts and styling follow the site (user request, 26 September 2026)

Keep the layout and sections. Only restyle the analytics block of `site.css`, and swap classes in the templates where the site already has the component, so the page follows DESIGN.md and the "VoiceBox layer" conventions the rest of the site uses:

- **Headings:**
  - Archivo Black at weight 400 (the face has no 600; the current 600 renders a faux bold).
  - h2 set in uppercase at one section size.
  - The page header uses the site's `page__header`/`page__title`/`page__lead`, as on Products and Orders.
  - The decorative red ✦ "Reporting" block is removed (DESIGN.md: no decorative imagery).
- **Figures in Space Mono:** card values and deltas, table numbers, run and date metadata, rank numbers, as prices and totals are elsewhere.
- **Labels:** uppercase Work Sans 700 with the caps tracking, as on `field-label` and the table heads: card labels, table heads, "Range" and data-table toggles.
- **Components reused from the site:**
  - Range links become `chip`/`chip--on`.
  - Status labels and the "Daily"/"Completed value" tags become `badge` variants: flagged `badge--warning` (DESIGN.md keeps low stock out of red), on track `badge--completed`, no recent sales and insufficient `badge--neutral`.
  - The status chip becomes `badge--completed`.
- **Charts:**
  - Chart.js ticks use Space Mono, legends Work Sans.
  - Point, legend and tooltip markers are square (`pointStyle: "rect"`).
  - Tooltips have square corners (`cornerRadius: 0`).
- No behaviour, context or URL change. Unused `analytics-*` rules are deleted.
