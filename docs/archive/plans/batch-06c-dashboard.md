# Batch 6c — operator analytics dashboard

Written before implementation, per `CLAUDE.md`'s "Discuss / Plan" step. Third analytics sub-batch, after [6a data](batch-06a-data-import.md) and [6b refresh and queries](../../plans/batch-06b-analytics-refresh.md). Contracts: [ANALYTICS.md](../../ANALYTICS.md) (ranges, compare, chart granularity, delivery), [API.md](../../API.md) (route, parameters, HTMX contract), [SECURITY.md](../../SECURITY.md). This file says how the page gets built; it does not restate formulas.

## Context

6b delivers the numbers (`reporting/queries.py`, `reporting/ranges.py`) and a completed `AnalyticsRun`. Nothing renders them. This batch adds `GET /analytics/` (`reporting:dashboard`) for operators: one Django view that reads the latest completed run and shows sales, top sellers, category sales, a trend chart and replenishment flags, with a range selector and an optional previous-period comparison. It never aggregates order lines and never writes.

The page can be built and tested entirely on fixture data; it does not need the dataset. There is no dashboard mockup in [DESIGN.md](../../../DESIGN.md), so this batch builds a functional, accessible page using the existing components (`.operator-table`, `.button`, `.message`, surface cards); the visual design pass is a separate later step.

## Decisions to confirm before implementation

1. **Shared HTMX login mixin.** `HtmxLoginRequiredMixin` currently lives in `src/cart/views.py`. Move it to `src/accounts/mixins.py` and import it from both apps, **recommended**: it avoids a cross-app import of a view module or a duplicate copy. Cart tests are unchanged. This touches cart code that is awaiting independent review, so the move is one isolated commit-worthy change.
2. **Permission.** Add a custom permission `reporting.view_analytics` through `AnalyticsRun.Meta.permissions` (migration `0004`, an options-only `AlterModelOptions`, no table change), granted to the `store_operator` group in `seed_demo` (idempotent, same pattern as the existing permission), **recommended**. `seed_demo` already fails clearly if migrations have not run.
3. **Access behaviour.** Anonymous: redirect to login (`HX-Redirect` for HTMX). Authenticated without the permission: 403. This follows API.md; it deliberately differs from the catalogue operator routes, which return 403 for anonymous users too.
4. **Chart.js vendoring.** Vendor a pinned Chart.js 4.x UMD build under `src/static/vendor/chartjs/` with its MIT licence file and the source version and SHA-256 recorded in a short README beside it, **recommended** (no CDN, offline runnable). Known risk: the project uses `CompressedManifestStaticFilesStorage`, which post-processes `sourceMappingURL` comments and can fail `collectstatic` (which runs at image build) if the referenced `.map` file is absent. Verify the image builds; if it fails, vendor the `.map` file too rather than editing the library.
5. **Replenishment table size.** Show the 25 most urgent products (flagged first by lowest coverage, then the rest), with counts of flagged, coverage-unavailable and insufficient-history products above the table, **recommended**. Full listing and CSV export are out of scope.
6. **No auto-refresh.** No polling in v1; the page shows its "as of" and refresh time.
7. **Compare alignment (small 6b amendment).** The comparison chart series must line up bucket by bucket with the selected series. Calendar ISO weeks do not (a span and the equal span before it clip different edge weeks). Define buckets once in `ranges.py` for the selected span (daily, or ISO weeks clipped to the span) and build the comparison buckets by shifting each selected bucket back by the span length; sum both through the same SQL. Applied to the 6b plan and ANALYTICS.md in the same change as this file.

## Implementation

- **`src/reporting/models.py` + migration `0004_analyticsrun_permissions`:** `permissions = [("view_analytics", "Can view sales and inventory analytics")]` on `AnalyticsRun.Meta`. No database change (`makemigrations --check` must show the migration as the only change, and it must be `AlterModelOptions` only).
- **`src/accounts/mixins.py`:** `HtmxLoginRequiredMixin` moved here; `cart/views.py` imports it.
- **`src/reporting/views.py`:** `AnalyticsAccessMixin(HtmxLoginRequiredMixin, PermissionRequiredMixin)` with `permission_required = "reporting.view_analytics"` and `raise_exception` unset (anonymous redirects, authenticated non-permitted raise 403). `AnalyticsDashboardView(AnalyticsAccessMixin, View)`, GET only (POST is 405), wrapped with `never_cache` (`Cache-Control: no-store`), because the page is operator-scoped and must not be stored by shared caches.
  1. Validate `range` and `compare` with a small Django form (`ChoiceField` from the whitelist; an invalid value falls back to `30d` and adds a visible message; `compare` is `1` or absent).
  2. `run = latest_completed_run(settings.DEMO_NAMESPACE)` once; if `None`, render the empty state (200).
  3. Derive *L* from `run.cutoff`, resolve the span and, if requested, the comparison span; decide comparison availability (whole span inside the run window and on or after the history start, else "insufficient history").
  4. Call the 6b queries once each: summary (selected, and comparison), bucketed series (selected and shifted comparison), category sales, top sellers (10), coverage. Constant query count, no per-product queries.
  5. Render `reporting/dashboard.html` (extends `base.html`), or only `reporting/_panel.html` when `HX-Request` is true. The wrapper `id="analytics-panel"` is identical in both.
- **`src/reporting/urls.py`** (`app_name = "reporting"`, `path("", ..., name="dashboard")`), mounted in `src/config/urls.py` as `path("analytics/", include("reporting.urls"))`.
- **Templates** (`src/templates/reporting/`):
  - `dashboard.html`: title, heading, `{% include "reporting/_panel.html" %}`, a `scripts` block loading the vendored Chart.js and `analytics.js` (deferred, in that order, after HTMX and `site.js`).
  - `_panel.html`, sections in order:
    1. Meta line: data as of the run cutoff (Singapore time), refreshed time, short run version, selected span dates, comparison span dates when on.
    2. Controls: range links (`7d`, `30d`, `90d`, `mtd`, `ytd`) as real `<a href>` with `hx-get`, `hx-target="#analytics-panel"`, `hx-swap="outerHTML"`, `hx-push-url="true"`, `aria-current` on the active one; a compare toggle link. Each link preserves the other parameter.
    3. Cards: sales amount and units for the span, each with the previous-period difference or "n/a" / "insufficient history"; products flagged (labelled as independent of the range).
    4. Trend chart (`<canvas>` with a label and a text summary) and category sales chart; each has an accessible data table alternative in a `<details>` element.
    5. Top sellers table (10).
    6. Replenishment table (25) with the counts above it and a note that flags always use the seven complete dates ending *L*.
    7. Assumptions footer: synthetic data, inventory is a sealed snapshot paired with the reporting cutoff; generated historical inventory is aligned to that cutoff, while a live snapshot captured after midnight is an approximation of the midnight cutoff (see KO-1 in ANALYTICS.md), seven-day rate and fixed lead time simplify reality, completed sales value is not accounting revenue.
    - Money is shown as `S$` with two decimals and thousands separators. Untrusted values (product names) are auto-escaped; chart data goes through `json_script`.
- **`src/static/js/analytics.js`:** on `htmx:load` (and initial load) find `[data-chart]` canvases, read data from the matching `json_script` element, destroy any existing `Chart.getChart(canvas)` instance, then create the chart (line with an optional dashed comparison dataset; horizontal bar for categories). Handle `htmx:responseError` for requests targeting `#analytics-panel` by showing an inline error and leaving the current panel in place (403 or 5xx are not swapped by default).
- **`src/templates/base.html`:** operator-only nav link `Analytics` guarded by `perms.reporting.view_analytics`, placed beside "Manage products".
- **`src/config/management/commands/` / `seed_demo`:** add `reporting.view_analytics` to the `store_operator` group (idempotent).
- **Docs:** [API.md](../../API.md) flips the analytics contract from reserved to implemented (route table, reserved-contracts table, HTMX section); tracker entry.

## Tests (`tests/test_analytics_dashboard.py`, PostgreSQL)

Fixtures build a tiny sealed inventory and a run through the real 6b `refresh_analytics` on explicit-date orders, so the page is tested end to end on hand-checkable numbers.

- **Access:** anonymous redirects to login; anonymous HTMX gets `HX-Redirect`; a logged-in customer gets 403; the operator gets 200; POST is 405; the response is `no-store`.
- **Empty state:** no completed run renders 200 with the message and no error.
- **Fragment vs full page:** normal request contains the full document; an HTMX request returns only the panel with `id="analytics-panel"` and no `<html>`.
- **Ranges:** each preset shows the expected span dates and totals at the fixed cutoff; invalid `range` shows the default and a message; `compare` other than `1` is ignored.
- **Compare:** correct differences; "n/a" when the previous span has no sales; "insufficient history" when the span precedes the history start (construct this with an explicit short-history fixture rather than relying on the dataset's range, which now spans January 2023 to December 2025 and generally does support year-to-date comparison); flags and coverage are identical across ranges and with compare on or off.
- **Charts:** parse the `json_script` payload: series length and values match, the comparison series aligns bucket by bucket including a weekly case; category totals equal the summary total.
- **Tables:** top sellers order and tie break; replenishment ordering, cap of 25 and the counts; states for zero sales and insufficient history are labelled, never shown as a number or infinity. In the `insufficient_history` state the page must also hide the average daily units, because `queries.coverage` still returns a numeric average with that status (raised in the [analytics-queries review](../../reviews/analytics-queries.md)); a test asserts that no average, coverage or flag appears for those rows.
- **Safety:** a product name containing markup is escaped; `assertNumQueries` bounds the query count and does not grow with the number of products.
- **Permissions plumbing:** `seed_demo` grants the permission to the operator group and is safe to re-run.

JavaScript behaviour (chart re-creation after a swap, error banner) is verified in the live walkthrough below, not by unit tests; the plan states that limit.

## Verification

`docker compose up --build -d --wait` (the image build proves `collectstatic` accepts the vendored Chart.js); `manage.py migrate`; `docker compose run --rm web pytest -q tests/test_analytics_dashboard.py` then the full suite; `manage.py check`; `makemigrations --check --dry-run` (after the migration is created, no further changes). Live walkthrough as the demo operator using data from the generator or the imported dataset (or a throwaway shell script creating orders if neither exists yet): each range link swaps the panel without a full reload and updates the URL, the back button restores the previous range, the chart is redrawn once per swap with no duplicate canvases, compare on and off, empty state, customer account gets 403, logged-out HTMX request redirects to login, a forced 500 shows the inline error. Then a Claude self-review (labelled), fix approved findings, update the tracker and API.md, and pass the independent backend review gate for the backend parts before marking complete. Commit only when asked; the user pushes.

## Out of scope

Visual design pass, CSV or other export, custom from/to range, auto-refresh, per-product drilldown, ML output (batch 6d adds a segment panel only if that batch happens), and caching.
