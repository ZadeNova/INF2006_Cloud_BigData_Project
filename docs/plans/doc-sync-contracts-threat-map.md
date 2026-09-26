# Doc sync: API context, review gate, tracker, naming and threat map

Written 27 September 2026, branch `syah&hermann/ML`. Approved by the user from the docs sync audit
(items 3, 6, 8, 11 and 13). Documentation only; no code changes.

## 6. docs/API.md

- Dashboard context table: `coverage` is the current page of every product in the run's sealed
  inventory, 10 per page (the "first 25" wording predates pagination); add `coverage_page`,
  `coverage_pager`, `segment_customers_page`, `customers_pager`, the size keys (`sizes`,
  `comparison_sizes`, `size_rows`, `size_chart`), `sales_cards`, `trend_chart`, `trend_rows` and
  the run labels (`run_short_id`, `cutoff_label`, `refreshed_label`), taken from
  `src/reporting/views.py`. Top sellers are shoe models.
- Foundation handover: model-viewer is vendored beside HTMX and Chart.js.
- Integration table: add `catalogue:product_detail`.

## 8. Review-gate wording and tracker

- `docs/TESTING.md` and `README.md`: the independent reviewer is Astra Medium or Claude Opus 5.5
  per the tier rules in DEVELOPMENT.md; CI's analytics job now also runs the shoe-dataset tests.
- `docs/IMPLEMENTATION_PLAN.md`: a current-state entry for `2698b05`, `b481f1f`, `3d8719c`,
  `c1ed7c6`, `c923958` and this pass, with the backend review gate for `0442665..HEAD` open.

## 13. Tracker phase table

Dates and statuses as of 27 September: Phase 2 complete locally with AWS/S3 open; Phase 3's window
(25 Sep–1 Oct) is running with no Terraform committed and no scaling, recovery or monitoring
evidence. Work continues on `syah&hermann/ML`.

## 11. Brand name

`docs/PROBLEM_FRAMING_AND_ARCHITECTURE.md` uses "Northstar"; the delivered site is 42Factors.
Rename the business there. The internal `northstar.*` logger names and historical plans and
review logs are left unchanged.

## 3. evidence/threat-control-map.md

Fill it from the drafted map in [threat-control-map.md](threat-control-map.md) with its sources,
updated for later decisions: the WAF rate rule on `POST /login/` (T7, planned), model-viewer
vendored (T13; Google Fonts stylesheets remain external), Session Manager (T11). Status follows
the evidence-kit rule: a row is **Mitigated** only when its SEC case has a PASS record (T1–T8);
other implemented controls say "Implemented; not yet recorded in evidence", cloud controls
**Planned**.
