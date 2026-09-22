# Backend and dataset completion roadmap

Written 22 September 2026 as a shared reference for the team and for coding agents picking up this
work. Target: finish the dataset and remaining backend features as working, self-tested code by
24-25 September, then move to AWS deployment (not started, and the bigger risk to the final grade
— see the strategic note at the end). This file sequences the work; it does not replace the
detailed batch plans it links to. Where this file and a linked plan disagree, the linked plan wins.

## Where things stand

Done and independently review-gate cleared (see [analytics-status.md](analytics-status.md) and
[IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)): auth, catalogue, cart, checkout, order
history, and the analytics refresh backend (view, ranges, `refresh_analytics`,
`snapshot_inventory`, `queries.py`). All of it has only run on fixture/`seed_demo` data so far.

The dataset is resolved: [PROJECT_SCOPE_INF2006.md](../PROJECT_SCOPE_INF2006.md) §5 records the
switch to the Analytics Engineering Ecommerce Sales Dataset (CC BY 4.0, not gated) after the
original LaelaZ selection was never granted access. The CSV source tables are downloaded,
checksummed and sitting in `data/raw/` (20,000 customers, 1,200 products, 100,000 orders, 237,537
order items, row counts confirmed exact against the download). Nothing has been profiled or
imported yet.

Not started at all: AWS deployment, Terraform, the architecture diagram, the report, and the
submission package (`analytics/`, `evidence/` and `project_manifest.yaml` exist only as empty
scaffolding).

## Phase 0 — Clear the decks (15 minutes)

1. Commit the four docs already updated for the dataset switch (`PROJECT_SCOPE_INF2006.md`,
   `docs/DATA_PIPELINE.md`, `docs/plans/analytics-status.md`,
   `docs/plans/batch-06a-data-import.md`). Do not start implementation on top of uncommitted
   planning changes.
2. Commit the raw CSVs in `data/raw/`, per the decision recorded in
   [batch-06a-data-import.md](batch-06a-data-import.md) decision 7 (no PII, CC BY 4.0 permits
   redistribution with attribution, ~27 MB total, removes an external-download dependency from the
   reproducibility story).

## Phase 1 — Dataset acceptance (about half a day)

3. Write `analytics/profile_dataset.py` and `analytics/requirements.txt` (pandas; kept out of the
   web image). It reads `data/raw/` and writes `data/PROFILE.md`: verified counts and date range,
   integrity checks (unique IDs, orphan foreign keys, status mapping, nonnegative money, positive
   quantities, per-order sum-of-lines reconciliation), and the analytics/K-means signal checks
   listed in [batch-06a-data-import.md](batch-06a-data-import.md) step 1.
4. **Run it. This is the acceptance gate, not a formality.** If integrity fails or the sales signal
   is flat noise, the documented fallback is the deterministic generator
   ([batch-06a-dataset-generator.md](batch-06a-dataset-generator.md)) — record the substitution
   rather than silently swapping.
5. Write `data/README.md` and `data/DATA_DICTIONARY.md`: provenance, the CC BY 4.0 attribution
   string (already in `data/raw/LICENSE.txt`), checksums, the column mapping and every
   transformation (the `partially_refunded` collapse, the discarded tax/shipping/discount columns —
   see `PROJECT_SCOPE_INF2006.md` §5). Write this while the profiling facts are fresh, not as an
   afterthought.

### A specific thing profiling must answer

237,537 order lines across 1,200 products over a 1,095-day range is roughly 0.18 lines per product
per day. Over the 7-day window the coverage calculation uses, that is about 1.3 lines per
product — so a meaningful share of the catalogue (a rough Poisson estimate puts it around 25-30%)
will show "No recent sales; coverage unavailable" at any given cutoff. The stock generator already
compensates for this (stock is derived from the 7-day average times a seeded 2-20 day factor, so
replenishment flags still fire for products that did sell recently), but the team needs the real
percentage before demoing the dashboard or writing the report's limitations section. If profiling
shows ~30%, that is an honest, documentable limitation. If it shows ~80%, the cutoff date or the
demoed product subset needs to change.

## Phase 2 — Import (about one day, the largest single piece)

6. `src/config/dataset.py`: `load_source(path)` using the standard-library `csv.DictReader` (no new
   dependency — the original plan assumed Parquet and `pyarrow`; both are dropped now that the
   actual download is CSV), `validate(source)`, and the field mapping.
7. `src/config/management/commands/import_dataset.py`, beside the existing `check_database.py`.
8. Add the read-only `../data:/app/data:ro` Compose mount so the command can read `/app/data/raw`
   inside the container.
9. `tests/test_import.py` per [batch-06a-data-import.md](batch-06a-data-import.md): idempotent
   re-import, conflict rollback, validation rejects, the date-shift fixture, namespace isolation,
   generator determinism.
10. Run the real import, reconcile row counts and decimal totals, spot-check the storefront and an
    imported order on a customer's history page.
11. Fold in **A9** here: `seed_demo --no-products` (create the demo operator without the 14
    hand-written products) — trivial, easy to forget if left for later.

## Phase 3 — Analytics meets real data (about half a day)

12. Run `snapshot_inventory` then `refresh_analytics` against the imported data. This is the first
    time the already-reviewed 6b code touches anything real — expect to find something. Finding a
    bad status mapping or a timezone bug here is far cheaper than finding it through a dashboard
    chart that quietly renders wrong numbers.
13. Write `analytics/verify_refresh.py` (**A6**): an independent pandas recomputation compared
    against the database, per the plan in
    [batch-06b-analytics-refresh.md](batch-06b-analytics-refresh.md). **This is not optional** — see
    "the thing worth knowing for the grade" below.

## Phase 4 — Dashboard (about one day)

14. Move `HtmxLoginRequiredMixin` to `accounts/mixins.py`; add the `reporting.view_analytics`
    permission (an options-only migration) and grant it in `seed_demo`.
15. Build the view, the `#analytics-panel` HTMX fragment, templates, and vendor Chart.js (confirm
    `collectstatic` accepts it). Full plan: [batch-06c-dashboard.md](batch-06c-dashboard.md).
16. Tests, then a real walkthrough against the imported data.

## Phase 5 — Evidence (about half a day, largely delegable to non-developer teammates)

17. `analytics/README.md`, `evidence/data-validation.md`, `evidence/test-data-ai.md` — written from
    actual command output, not from what the plan expected to happen.
18. `project_manifest.yaml`'s `data_ai` fields, flip `docs/API.md`'s analytics route to
    implemented, document the view in `docs/SCHEMA.md`, update tracker entries in
    [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md).
19. Queue 6a (import) then the 6c backend part for the independent Astra review, per
    [astra-review.md](astra-review.md).

## Why this order

**The import is the spine.** Phases 3, 4 and 5 all consume its output; nothing after Phase 2 can
start in earnest without it.

**Analytics-against-real-data (Phase 3) deliberately sits before the dashboard (Phase 4).** The
dashboard is the only remaining piece with zero unknowns — it reads query functions that are
already written and independently reviewed. Building it before the dataset's real behaviour is
understood risks rework once real numbers surface a mapping problem.

## The thing worth knowing for an A grade

`profile_dataset.py` and `verify_refresh.py` are **submission deliverables, not development
scaffolding.** The project brief requires `analytics/` to contain "notebook(s) or script(s),
requirements and a short README explaining how results are reproduced," and the 20-mark cloud
data/analytics rubric criterion explicitly grades "credible evaluation and limitations." Right now
`analytics/` contains only a README and nothing else. Phase 1 step 3 and Phase 3 step 13 are
simultaneously the team's risk-reduction work *and* a meaningful share of that 20 marks. This is
the best value-per-hour work in the whole roadmap, and it should not be the thing that gets cut
under time pressure.

## Honest timeline calibration

This is roughly 3.5 days of focused work against 2.5-3 available days before 24-25 September.
Achievable only if profiling in Phase 1 turns up nothing unexpected. Two things to calibrate
expectations against:

- **Independent review will not finish inside this window.** Astra's review rounds have each taken
  multiple days and depend on a teammate's availability to run them. "Backend code done and
  self-tested by the 25th" is realistic; "reviewed and gate-cleared" is a separate, later
  milestone — do not conflate the two when reporting status.
- **If the team falls behind, cut in this order:** batch 6d (K-means) first — it is already gated
  and optional, and the brief's analytics requirement is fully satisfied without it; then the A8
  generator's remaining job (the load-test fixture, which naturally belongs with the later
  Locust/cloud work anyway); then dashboard visual polish. **Do not cut A6 or the evidence files**
  (step 13 and Phase 5) — they are comparatively cheap and are the artifacts actually graded.

## Strategic note: why the date matters

AWS deployment is worth 20 more rubric marks on its own (cloud implementation and functionality)
and contributes to two more (scalability/resilience, and part of security) — and it has not
started. Unlike the backend work above, cloud has genuine unknowns outside the team's control: lab
account permissions, an HTTPS certificate arrangement, actual Terraform behaviour against a real
lab environment (see [cloud-independent-prep.md](cloud-independent-prep.md) B4 onward). Every extra
day spent polishing backend features already working on fixture data is a day not spent surfacing
those cloud unknowns while there is still time to react to them. That is the real argument for
holding the 24-25 September date and being willing to cut from the list above rather than let it
slip.
