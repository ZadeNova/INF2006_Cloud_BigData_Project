# Review: shoe-baseline backend gate (quarantine merge onward)

- Reviewer: **Independent (fresh session), Claude Opus 5.5**. The session had never seen the implementing conversations. Read-only apart from this log; no sub-agents; medium effort.
- Date: 27 September 2026. Round 1.
- Snapshot: branch `syah&hermann/ML` at `fcd45f5`, clean working tree, tracking `origin/syah&hermann/ML`.
- Range: `0442665^1..HEAD` (`09600a7..fcd45f5`): the quarantine merge `0442665` (shoe catalogue schema, migration `catalogue/0003`, importer shoe columns, derived dataset builder, analytics size/top-seller SQL and pagination), `2698b05` and `ee334cf` (evidence/docs), `b481f1f` (ML hold-out evaluation and `log_rfm_aov`), `3d8719c` (manage filters, product detail page, stay-on-page cart), `c1ed7c6` (vendored model-viewer, CI), `c923958` and `fcd45f5` (doc sync).
- Owned paths reviewed: `src/catalogue/` (models, migration 0003, `shoes.py`, views, urls, `seed_demo`), `src/config/dataset.py`, `src/config/management/commands/import_dataset.py`, `src/config/settings.py`, `src/cart/`, `src/orders/`, `src/reporting/` (queries, views, `segment_contract.py`), `analytics/build_shoe_dataset.py`, `analytics/evaluate_holdout.py`, `analytics/segment_customers.py`, `.github/workflows/ci.yml` and the matching tests. Templates were read only where they consume backend context (`catalogue/_product_card.html`, `catalogue/product_detail.html`, `reporting/_panel.html`). Evidence files, CSS, JS and binary models were not reviewed.
- Specs checked: [SCHEMA](../SCHEMA.md), [API](../API.md), [ANALYTICS](../ANALYTICS.md), [SECURITY](../SECURITY.md), [DATA_PIPELINE](../DATA_PIPELINE.md), [data/README.md](../../data/README.md), [shoe-sizes plan](../plans/shoe-sizes-catalogue.md).

## Checks run

| Check | Result |
|---|---|
| `git status -sb`, `git log --oneline 0442665^1..HEAD`, `git diff 0442665^1..HEAD` | Branch and clean tree confirmed; 14 commits, 154 files |
| Static inspection of the backend diff against the specs above | 4 findings below |
| Recorded (not rerun): full web suite in local Docker at `c1ed7c6` | 503 passed, 8 opt-in skips ([tests/README.md](../../tests/README.md)) |
| Test suite, Docker, `makemigrations --check` | **Not run in this review** (read-only gate, per instructions). Migration/model agreement was checked by reading `0003` against `models.py` only |

## Findings

| ID | Severity | File/line | Required spec / evidence | Issue and expected correction | Low fix / verification | Re-review outcome |
|---|---|---|---|---|---|---|
| G-001 | Medium | [src/config/dataset.py:130-151](../../src/config/dataset.py#L130-L151); crash at [import_dataset.py:175](../../src/config/management/commands/import_dataset.py#L175) | [data/README.md:101-103](../../data/README.md#L101-L103): "`--allow-rejects` imports complete valid orders only. Rejected parents reject children" | The new shoe checks (name/category differs, duplicate size) reject a product **after** it is already in `parsed["products"]`. The order-item check at line 150 tests only `product_id not in parsed["products"]`, so lines that point at that rejected product stay valid, and so do their orders. `valid` then holds order items whose product is missing. Failure: an inconsistent sized product that has order lines, run with `--allow-rejects` → `persist` does `products[row["product_id"]]` → uncaught `KeyError` traceback (not a `CommandError`; the transaction rolls back). Fix: at line 150 also reject when the product's row is in `rejects`, e.g. `product = parsed["products"].get(row["product_id"]); if product is None or ("products", product["_row"]) in rejects: ...`. Add one regression: `tests/test_import.py::test_inconsistent_shoe_sizes_rejected` (or a single new case) with `allow_rejects=True`, asserting the dependent lines and orders are rejected and the import completes. That test would settle this finding; it was not run here | Fixed by Claude Opus 5.5 at the user's direction (not Astra Low). `validate` now also rejects a line whose product row is in `rejects`. New test `test_allow_rejects_drops_orders_that_use_a_rejected_shoe_size`: passes, and fails with `KeyError: 'P2'` against the pre-fix `dataset.py` | Resolved (round 2, same-session) |
| G-002 | Low | [seed_demo.py:18, 64-72](../../src/catalogue/management/commands/seed_demo.py#L18) and docstring line 1; [tests/test_catalogue.py:418](../../tests/test_catalogue.py#L418) | AGENTS.md "Simplicity": remove dead code; README/evidence describe the delivered system | The retirement loop deactivates `demo-`/`sneaker-` rows only in `settings.DEMO_NAMESPACE`, which this range changed to `synthetic/shoes/revision-a/demo/v1`. The `demo-` and `sneaker-` rows were created under the old `synthetic/revision-a/demo/v1` (`DEMO_NAMESPACE` at `2ad7b82`), and nothing creates them in the new namespace, so the loop never matches a real row. The namespace switch alone already hides the old rows from the shop and checkout rejects them (`InvalidProductError`). The test only passes because it creates retired rows directly in the new namespace, which is a state that cannot happen. Fix: remove `RETIRED_EXTERNAL_ID_PREFIXES`, the loop and the "apart from deactivating" docstring clause, and drop the retired-row assertions from the test. Alternatively, if retiring old-namespace rows is really wanted, target that namespace explicitly and record the decision | Fixed by Claude Opus 5.5 at the user's direction: loop, constant and docstring clause removed; test renamed `test_seed_demo_creates_every_shoe_in_every_size` with the retired-row set-up and assertions removed | Resolved (round 2, same-session) |
| G-003 | Low | [src/catalogue/views.py:26-45](../../src/catalogue/views.py#L26-L45) | AGENTS.md "Simplicity": no duplicated business rules | `ProductListView.get_queryset` and `ProductDetailView.get_queryset` repeat the same visibility rule: demo namespace, at least one active SKU, and prefetched active `sizes` ordered by size. The only difference is `order_by`. If the "what the shop shows" rule changes in one place and not the other, list and detail pages would disagree. Fix: one module-level helper, e.g. `def shop_shoes(): ...`, used by both (the list adds `.order_by("name", "pk")`) | Not fixed: owner decision, 27 September 2026 | Accepted by owner |
| G-004 | Low | [tests/test_cart.py:272](../../tests/test_cart.py#L272); [tests/test_catalogue.py:307](../../tests/test_catalogue.py#L307) | AGENTS.md test rule: "Parametrise only across inputs that reach different code paths" | Both `next` rejection tests use 4 and 3 targets, but every target except `/products/manage/` fails the same first `startswith(...)` prefix check, so the `https://…`, `//evil…` and `/orders/` or `/cart/` cases each detect the same defect. The `url_has_allowed_host_and_scheme` branch is never the deciding check. Fix: keep one off-prefix target (e.g. `//evil.example/…`) per view, plus the cart's `/products/manage/` exclusion case | Trimmed in round 3 (cart 4 → 2 cases, toggle 3 → 1); 57 passed | Resolved (round 3, same-session) |

### Checked and clear

- **Migration `catalogue/0003`**: fields, `PROTECT` FK, `product_size_pair`, `product_size_range` and `product_model_size_unique` match `models.py`. Existing size-less rows satisfy the new constraints because both new columns are null for them. The nullable-column rationale in the plan holds.
- **Importer**: `shoe_size` rejects a shoe ID without a size, a size without a shoe ID, non-finite values, and sizes outside 1..20 or not in half steps. On replay it verifies shoe models, and verifies `size`/`shoe_model_id` on products. A namespace with shoe models outside the accepted source is a conflict. Apart from G-001, the reject cascade is unchanged.
- **Analytics SQL**: `TOP_SELLERS_SQL` groups by `m.id, CASE WHEN m.id IS NULL THEN p.id END`, which gives one group per model and keeps each size-less product separate. The tie break `MIN(p.id)` matches ANALYTICS.md. `SIZE_SQL` is run-scoped and excludes null sizes. `COVERAGE_SQL` column order matches the new `CoverageRow` unpacking. The query budget of 19 is asserted in `test_analytics_dashboard.py:216`.
- **Pagination**: `coverage_page` and `customers_page` go through `Paginator.get_page`, so invalid or out-of-range values clamp. Pager URLs are built with `reverse` + `urlencode` from validated state. The segment sample is still selected by `queries` under the run lock; pagination is display-only, as API.md states.
- **Producer/consumer contract**: `segment_customers.py` (`log_rfm_aov` default, choices) and `segment_contract.validate_batch` accept the same three preprocessing values. `evaluate_holdout.fetch_outcomes` uses the same eligibility filter as `fetch_rfm`.
- **Authorisation, CSRF and redirects**: the manage list and toggle keep `OperatorPermissionRequiredMixin`. The detail page is public and filtered to the demo namespace with an active size. Cart add still requires login, demo namespace and an active product. Both `next` targets are limited to a same-host path prefix, and the cart add excludes `/products/manage/`. Forms carry `{% csrf_token %}`.
- **Doc claims**: API.md rows for `/products/`, `/products/<id>/`, manage filters, toggle `next`, cart `next` and the dashboard context keys match the code. SCHEMA.md ShoeModel/Product rows match the model; the rule that name and category repeat the model's is enforced by the importer and `seed_demo`, not by a database constraint, which SCHEMA does not claim. The only contradicted doc claim is the data/README `--allow-rejects` statement (G-001).

## Verdict

**Findings to fix.** G-001 (Medium) is a correctness defect on the documented `--allow-rejects` path. G-002–G-004 are Low dead-code, duplication and test-budget findings under AGENTS.md. No authorisation, CSRF, open-redirect or migration defect was found. Nothing was fixed in this review. After Astra Low remediation, the same tier re-reviews the updated diff under these IDs.

## Round 2: re-review of the G-001 and G-002 fixes

- Reviewer: **Same-session, Claude Opus 5.5.** This is a logged exception, not an independent review. The session that ran round 1 also wrote these fixes, at the user's direction instead of Astra Low. The user authorised Opus 5.5 to take the gate. Because the author reviewed its own fix, a shared blind spot is possible. The gate is cleared by the owner's acceptance of this same-session review, not by independent review. A fresh-session Astra Medium or Opus 5.5 pass remains the default if independence is wanted.
- Date: 27 September 2026. Base `86e1d95` (a user docs-only commit after round 1, unrelated to these paths), with uncommitted changes to `src/config/dataset.py`, `src/catalogue/management/commands/seed_demo.py`, `tests/test_import.py` and `tests/test_catalogue.py`. Plan: [shoe-baseline-gate-fixes.md](../archive/plans/shoe-baseline-gate-fixes.md).

| Check | Result |
|---|---|
| `docker compose build web`, then `pytest /app/tests/test_import.py /app/tests/test_catalogue.py` | **63 passed** |
| New G-001 test against the pre-fix `dataset.py`, bind-mounted over the image copy (working tree untouched) | 1 failed, `KeyError: 'P2'` at `import_dataset.py:175`, so the test detects the original defect |
| Search `src/`, `tests/` and the contract docs for `RETIRED_EXTERNAL`, `retired demo`, `sneaker-` | No references left (only binary `.glb` byte matches) |
| Full suite, hosted CI | Not run; the change is limited to these two modules |

Review of the fix diff:

- **G-001:** `validate` rejects customers only while parsing, so products are the only table rejected after parsing. The new check therefore covers every such case. The existing cascade then rejects the order and its sibling lines; the test asserts O2..O5 are dropped and O1 is imported. The data/README `--allow-rejects` claim now matches the code.
- **G-002:** the removal leaves `settings` and `Product` still in use in `seed_demo`, and `HISTORICAL_NAMESPACE` still used at `tests/test_catalogue.py:140`. The retirement line in [shoe-sizes-catalogue.md](../plans/shoe-sizes-catalogue.md) is a historical plan; the new plan records that it is superseded.
- No new findings.

**Round 2 verdict: CLEAR** (same-session, owner-accepted). G-001 and G-002 are resolved; G-003 and G-004 were accepted by the owner without a fix. Nothing committed or pushed.

## Round 3: test redundancy audit and trim

- Reviewer: **Same-session, Claude Opus 5.5.** The same session also wrote the G-001 and G-002 fixes and this trim, so this is **not** an independent review. The user asked for it to be logged as independent; it is logged as same-session because DEVELOPMENT.md requires that label whenever the author reviews its own change. As with round 2, the gate is cleared by the owner's acceptance of a same-session review.
- Date: 27 September 2026. Plan: [test-trim-shoe-baseline.md](../archive/plans/test-trim-shoe-baseline.md).
- Method: the 25 September trim ([test-trim.md](test-trim.md), 466 → 392) already removed cases that mutants showed to be equivalent. This round looked mainly at tests added since `0f7e9d4`, and at duplication across modules (`test_security_negative.py` against the feature modules). A case counts as redundant only if a kept case fails for every defect it would catch. Evidence citations (SEC-02, SEC-04) were checked before any removal.

| Change | Kept coverage |
|---|---|
| Removed `test_catalogue.py::test_toggle_forbidden_for_non_operators` | `test_security_negative.py::test_a_customer_cannot_use_the_operator_toggle` (same assertions; cited by SEC-02) |
| Removed `test_catalogue.py::test_chosen_size_is_added_to_the_cart` | `test_cart.py::test_add_creates_a_new_cart_item` (same `cart:add` path) |
| `test_toggle_is_idempotent_under_double_submit`: 2 → 1 | The view has no per-direction branch; one direction still catches a flip toggle |
| `test_add_ignores_a_next_outside_the_shop`: 4 → 2; `test_toggle_ignores_a_next_outside_the_manage_list`: 3 → 1 | G-004: the dropped targets fail the same prefix check |

Kept after inspection: the anonymous cart matrix (one base class, but a per-route override would otherwise go uncaught); `BAD_QUANTITIES` (SEC-04 evidence cites its parameter IDs); the 18-case segment-loader matrix (each case hits a different bound, type or coherence check in `segment_contract.py`); and the three leap-day query tests (low value, since they mostly re-check date arithmetic, but not worth the churn).

| Check | Result |
|---|---|
| `pytest /app/tests/test_catalogue.py /app/tests/test_cart.py` (web image) | **57 passed** |
| `pytest --collect-only /app/tests` | **505 collected** (511 at `c1ed7c6`, +1 G-001 regression, −7 trimmed): 497 runnable plus the 8 opt-in bootstrap skips |
| Full web suite after these changes | **Not run**; recommended once before merging. `tests/README.md` keeps the last full-run count until then |

**Round 3 verdict: CLEAR** (same-session, owner-accepted). No new backend findings. Historical raw evidence that lists removed test names (`FUNC-01_2026-09-26.txt`) records a past run and is unchanged.
