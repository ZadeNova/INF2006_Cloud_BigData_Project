# Latest Opus 5.5 review: whole codebase

Date: 25 September 2026. Reviewer: Claude Opus 5.5, read-only (no files changed, staged or committed).
Snapshot: branch `erfan/analytics` at `91eba60`, plus the uncommitted `src/tools/aws_capability_check.py`,
`tests/test_aws_capability_check.py` and an edit to `docs/archive/plans/cloud-independent-prep.md`.

**Independence.** One session ran four passes: `f5c6557..HEAD`, the storefront redesign and core, the ML component, and a final sweep. It never saw an implementing conversation. However, it is not a fresh-session review in the [DEVELOPMENT.md](../DEVELOPMENT.md#backend-review-gate) sense, because later passes had the earlier ones in context. Log it as a **same-session** review if it is used for the backend gate.

This file lists every problem those passes raised, merged into one priority order. Finding IDs are kept from the passes so earlier references still match: `F-` for the analytics branch diff, `S-` for storefront and core, `M-` for ML, `W-` for new items from the final sweep. Status is **CONFIRMED** when the problem was reproduced, **PLAUSIBLE** when the code path was traced but not run.

## Checks run

| Check | Result |
|---|---|
| `docker compose build web` | passed |
| `docker compose run --rm web pytest -q -p no:cacheprovider` | **447 passed** |
| `manage.py check` / `makemigrations --check --dry-run` | no issues / no changes |
| `analytics/tests/test_segment_customers.py` (venv) | 3 passed |
| `python -m pytest analytics/tests` as documented | **fails at collection**: `test_verify_refresh.py` needs Django (F-06) |
| `tests/test_aws_capability_check.py` (with `PYTHONPATH=src`) | 12 passed |
| Full demo import → refresh → `segment_customers.py` → `load_customer_segments` in a throwaway Compose project (deleted afterwards) | 0 rejects, 65,589 daily rows, 19,766 customers segmented, k=2, silhouette 0.387, ARI 0.979; `/analytics/` rendered in about 0.15 s; anonymous → 302, anonymous HTMX → `HX-Redirect`, customer → 403 |
| Probe tests (scratch files, never added to the repo) | segment-loader edge cases, `/register/` ARIA wiring, AWS probe redaction and timeout |

## Priority 0: fix before submission

These affect marks directly, correctness, or the brief's no-personal-data rule.

| ID | Where | Problem | Fix | Status |
|---|---|---|---|---|
| M-01 (= F-01) | [analytics/segment_customers.py:127](../../analytics/segment_customers.py#L127), [:88-91](../../analytics/segment_customers.py#L88-L91) | Choosing k by silhouette always gives **k=2** on this data (k=2…6 score 0.387, 0.332, 0.310, 0.313, 0.311). The names only include `at_risk` from k=3 upward. The result: lapsed customers (mean 387 days since the last order) are labelled `core`, 62.5% of customers are `high_value`, and `at_risk` never appears. | Fix k=3 as a stated business choice (resampling stability 0.96). Report silhouette and stability for k=2…4 as the justification. Or keep k=2 and name the tiers honestly (`engaged` / `lapsing`). Add a naming test for k=2 and k=3. | CONFIRMED |
| M-02 | ML feature as a whole | Nothing shows the segments predict behaviour. Silhouette and seed stability only describe the geometry. The rubric asks for "credible evaluation". | Time-split check: segment at an earlier cutoff (T−90 days), then report each segment's repurchase rate and spend in [T−90, T). Record it in `evidence/test-data-ai.md`. | CONFIRMED (absent) |
| M-06 | [load_customer_segments.py](../../src/reporting/management/commands/load_customer_segments.py), [.gitignore](../../.gitignore) | The loader drops `stability_ari_*` and `segment_profiles`, and `analytics/segments.json` is gitignored, so none of the ML evaluation survives into the submission. | Commit a small evaluation summary (metrics and cluster profiles, no customer rows) and point `project_manifest.yaml` `data_ai.evaluation` at it. | CONFIRMED |
| F-05 | [README.md:36](../../README.md#L36), [SCHEMA.md](../SCHEMA.md), [tests/README.md:24](../../tests/README.md#L24), [analytics/README.md:157](../../analytics/README.md#L157), [project_manifest.yaml:30](../../project_manifest.yaml#L30) | The docs contradict the code: the README says segmentation is "Not implemented"; SCHEMA.md has no `CustomerSegment` row (AGENTS.md requires it with any model change); two READMEs say four analytics tests (there are seven); the manifest cites 410 tests and no ML. | Update all five. The SCHEMA row needs the FKs (run CASCADE, customer PROTECT), the unique constraint and the check constraints. | CONFIRMED |
| S-005 | [foundation/statistics.html:9-11](../../src/templates/foundation/statistics.html#L9-L11) | The banner says the real dashboard "is a later batch … it will live on its own protected operator route". It exists at `/analytics/`, so a marker is told analytics is not built. | Point to `/analytics/` (operator only) and keep "Every number on this page is invented." | CONFIRMED |
| W-01 | [src/tools/aws_capability_check.py:43-44](../../src/tools/aws_capability_check.py#L43-L44) (uncommitted) | `redact()` only masks 12-digit account numbers. Error messages from denied calls include the full caller ARN, whose assumed-role **session name** is often the student's ID and name in AWS Academy labs. Tested: `…assumed-role/voclabs/user2345678=Jane_Doe is not authorized…` passes through unchanged into the Markdown meant for `evidence/`, which the brief forbids. | Also redact the session segment, for example `re.sub(r"(assumed-role/[^/\s]+/)[^\s:\"']+", r"\1<session>", text)`, and add a test with such an ARN. | CONFIRMED (redaction gap); PLAUSIBLE (that the lab's session names contain names) |

## Priority 1: fix soon

| ID | Where | Problem | Fix | Status |
|---|---|---|---|---|
| S-001 | [accounts/_form_fields.html:6-9](../../src/templates/accounts/_form_fields.html#L6-L9) | Django 5.2 sets `aria-describedby="id_x_helptext id_x_error"`, but the template gives those elements the ids `id_x-help` and `id_x-error`. Every reference points at nothing, so screen readers never announce help text or errors on login or register. | Use `id="{{ field.auto_id }}_helptext"`. Wrap each field's errors in one `<div id="{{ field.auto_id }}_error">`, which also removes duplicate ids when a field has several errors. Add one test that the referenced ids exist. | CONFIRMED (rendered HTML) |
| M-03 | [segment_customers.py:112-115](../../analytics/segment_customers.py#L112-L115) | Feature handling works against the data. The log transform pushes monetary skew from 0.85 to **−1.45**. Recency (skew 1.41) is left raw. Frequency and log(monetary) correlate at r=0.74, so the volume signal outweighs recency roughly 2:1. | Log-transform frequency and recency, or use rank/quantile features. Consider average order value instead of total spend. Record the comparison (log frequency alone: k=2 silhouette 0.437). | CONFIRMED |
| M-04 | [segment_customers.py:52-63](../../analytics/segment_customers.py#L52-L63) (`fetch_rfm`) | Frequency and monetary cover each customer's whole history, so recently joined customers look weak (tenure bias). The dashboard shows a lifetime "Segment sales value S$55.8M" next to 30-day sales cards. | Use a lookback that matches the run window (366 days), or divide by tenure. Label the card "lifetime to cutoff". | CONFIRMED (window); PLAUSIBLE (tenure effect not measured) |
| M-05 | [segment_customers.py:100-109](../../analytics/segment_customers.py#L100-L109) | "Stability" only reruns with a different seed on the same data. Refitting on 80% samples shows k=4 is unstable (mean ARI 0.66, worst 0.37), which the seed-only check hides. ANALYTICS.md asks for seeds **or resamples**. | Use repeated 80% subsamples and report the mean and minimum ARI. | CONFIRMED |
| F-02 / M-09 | [load_customer_segments.py:41](../../src/reporting/management/commands/load_customer_segments.py#L41), [:64-85](../../src/reporting/management/commands/load_customer_segments.py#L64-L85) | `cluster_id: 40000` and `recency_days: 3e9` escape as raw `DataError` tracebacks; `"NaN"` and `"Infinity"` as `ValidationError`. The transaction rolls back, so no data is corrupted. | Catch `DataError` and `ValidationError` alongside `IntegrityError`, or reject non-finite decimals and out-of-range integers in `_assignment`. | CONFIRMED |
| F-03 | [load_customer_segments.py:68](../../src/reporting/management/commands/load_customer_segments.py#L68) | Any user id is accepted, including a superuser, with no check against the run's namespace. The dashboard then shows that account's login username to operators. | Check ids against `CustomerProfile.objects.filter(namespace=run.inventory.namespace)` before `bulk_create`. | CONFIRMED |
| M-10 | [_panel.html:196-197](../../src/templates/reporting/_panel.html#L196-L197), `fetch_rfm` | The segment customer table shows **login usernames**, which targeting does not need (fails data minimisation). Storefront orders by staff or demo accounts in the demo namespace feed the model. | Remove the username column (the customer reference is enough). Exclude `is_staff`/`is_superuser` owners in `fetch_rfm`. | CONFIRMED |
| S-006 | [reporting/services.py](../../src/reporting/services.py) `_prune` with `CustomerSegment` `on_delete=CASCADE` | Each `refresh_analytics` publishes a new run with no segments, so the ML panel disappears until segmentation is re-run. After `keep` refreshes the old assignments are deleted. None of this is documented. | Document the order (refresh → segment → load) in analytics/README, or have the dashboard fall back to the latest run that has segments and label it. | CONFIRMED (code path) |
| F-06 / M-12 | [.github/workflows/ci.yml:39](../../.github/workflows/ci.yml#L39), `analytics/tests/`, [test_analytics_dashboard.py:365](../../tests/test_analytics_dashboard.py#L365) | CI runs no analytics or ML test. `fetch_run`/`fetch_rfm` SQL, the choice of k and recency across timezones are untested. The documented `pytest analytics/tests` command cannot collect. `"demo-operator" not in body` can never fail, because the fixture user is `operator` and is itself shown as a segment row. | Add a CI step for `test_segment_customers.py` (needs no database). Document the two separate analytics test commands, or skip Django-dependent files when Django is missing. Replace the vacuous assertion. Add tests for choosing k and for naming. | CONFIRMED |
| W-02 | [aws_capability_check.py:180-182](../../src/tools/aws_capability_check.py#L180-L182) (uncommitted) | `subprocess.run(..., timeout=45)` raises `TimeoutExpired`, which nothing catches. One slow API call aborts the run with a traceback and loses every result collected so far. Separately, a `|` in an error detail breaks the Markdown table. | Catch `subprocess.TimeoutExpired` in `runner` and return an `error` outcome. Escape `|` in `render`. | CONFIRMED (timeout) |
| W-03 | [accounts/urls.py](../../src/accounts/urls.py) (`LoginView`) | No throttling or lockout on login. The brief asks for "validation against a named threat", and credential stuffing/brute force is the obvious threat for this app, but there is nothing to cite as its control. | Add a control (for example an AWS WAF rate-based rule on the ALB, or a small per-username/IP throttle), map it in `evidence/threat-control-map.md` and record a test. At minimum, record it as a known limitation. | CONFIRMED (absent) |

## Priority 2: polish and cleanup

| ID | Where | Problem | Fix | Status |
|---|---|---|---|---|
| F-04 | [static/js/analytics.js:244-249](../../src/static/js/analytics.js#L244-L249) | HTMX fires `htmx:load` on `body` at startup, so `announcePanel` moves focus to the panel `<h2>` on a normal page load, past the header navigation. | Call `announcePanel` only when `event.detail.elt.id === "analytics-panel"`. | PLAUSIBLE (checked in the vendored HTMX source, not in a browser) |
| S-002 | [cart/_content.html](../../src/templates/cart/_content.html) stepper | `#cart-content` is swapped with outerHTML. HTMX restores focus only to an element with the same id, and the −/+ buttons have none, so each step drops keyboard focus to `<body>`. "Remove" does the same. | Give the stepper buttons stable ids (`qty-{{ item.pk }}-inc`/`-dec`). After a remove, move focus to a sensible element. | PLAUSIBLE |
| S-003 | [base.html:66-70](../../src/templates/base.html#L66-L70) | The header cart badge is not in the HTMX fragment, so it keeps the old count after an update, removal or emptied cart until a full page load. | Add an out-of-band (`hx-swap-oob`) badge to HTMX responses, or refresh it on `htmx:afterSwap`. | CONFIRMED |
| S-004 | [503.html:24](../../src/templates/503.html#L24) | The 503 page loads Inter and Manrope, while `site.css` uses Work Sans, Archivo Black and Space Mono. The outage page renders off-brand and downloads unused fonts. Both pages still use the Google Fonts CDN even after CR-009 vendored scripts. | Use the `base.html` font link, or self-host the three families. | CONFIRMED |
| S-007 | [reporting/ranges.py:57-61](../../src/reporting/ranges.py#L57-L61) | `coerce_range` is dead code (the view uses `DashboardRangeForm`), and `tests/test_analytics_ranges.py:87` still tests it. | Delete the function and its test. | CONFIRMED |
| S-008 | [base.html](../../src/templates/base.html) theme toggle | A static `aria-label` and no state, so assistive technology cannot tell which theme is active. | Add `aria-pressed` and update it in the `site.js` click handler. | CONFIRMED |
| M-07 | [segment_customers.py:128](../../analytics/segment_customers.py#L128) | A negative silhouette becomes `None` ("unavailable"), mixed up with the `-1.0` "not computable" placeholder. | Keep negative values; use `None` only when the score cannot be computed. | CONFIRMED |
| M-08 | `--model-version` default `rfm-kmeans-v1` | The version stays the same across k range, seed, features or code, and the loader replaces same-version rows. Different models can share one label. | Build the version from the parameters (for example `rfm-kmeans-k3-s42`), or store the parameters in the JSON and check them on load. | CONFIRMED |
| M-11 | [analytics/README.md:32](../../analytics/README.md#L32) | The documented run uses `--user 0` with the repo mounted read-write, which leaves a root-owned `segments.json` on Linux (observed). `--database-url` exposes the password in shell history and the process list. | Mount a separate output directory without `--user 0`. Recommend the environment variables. | CONFIRMED |
| W-04 | [catalogue/views.py](../../src/catalogue/views.py) `ProductToggleActiveView` | After activating or deactivating a product, the operator is redirected to page 1 of the list, losing their place. | Redirect back to the page the operator was on (a `page` hidden field). | CONFIRMED (code) |

## Checked and sound

- **Security:**
  - Settings refuse to start when misconfigured (required secrets, `DEBUG` forbidden outside local, explicit hosts, `verify-full` DB TLS).
  - Secure cookies, HSTS and SSL redirect outside local.
  - Logs record the path only and never exception messages.
  - All reporting SQL is parameterised.
  - Templates auto-escape; chart data goes through `json_script`; JS uses `textContent`.
  - `/analytics/` permission gate verified, including HTMX.
- **Checkout:**
  - Ordered row locking; `Decimal` money.
  - The session idempotency key survives until success, and a replay compares the review fingerprint, so the "Safe to retry" copy is true.
  - `external_id` is non-null and unique, so fingerprints cannot collide.
- **Analytics core:**
  - The refresh publishes in one SQL statement under an advisory lock with a transaction-local timeout.
  - Orphaned runs are marked failed; retention keeps at least two runs.
  - Snapshots only record today's stock.
  - Import and pandas figures reproduce exactly.
- **Containers and CI:**
  - Non-root image, digest-pinned images, exact dependency pins with `pip check`.
  - The bootstrap password never reaches `web`; no DB port is published; web binds to 127.0.0.1.
  - CI has least permissions and a SHA-pinned checkout.
- **Theme:**
  - The two dark-mode blocks are identical.
  - Text contrast is at least 4.6:1 in both themes (red `#ef4444` is used only for fills and rules).
  - All CSS custom properties used are defined.
- **ML engineering:**
  - Deterministic: re-running reproduced the published file exactly.
  - Kept out of the web image; loads atomically; re-runs replace cleanly.

## Rubric position (brief §10)

"Rough today" is a reviewer estimate from the evidence present on the snapshot date, not a prediction. The §4 minimum requirements are **compulsory**, so the cloud items are required, not optional extras.

| Criterion | Marks | Evidence now | Gaps | What would raise the score | Rough today |
|---|---|---|---|---|---|
| Problem framing & architecture | 15 | `docs/PROBLEM_FRAMING_AND_ARCHITECTURE.md`, `docs/ARCHITECTURE.md`, `DESIGN.md` | No `evidence/architecture.png` (the manifest points to it). Manifest `project`/`architecture` fields and README team table empty. No `report.pdf` | Diagram with trust boundaries and data flows, labelled to match the repo; filled manifest; two rejected alternatives in the report (§5.1) | 4–6 |
| Cloud implementation & functionality | 20 | Complete storefront → checkout → history → operator flow; 447 tests; CI; `src/README.md` | Not deployed. `evidence/test-functional.md` is TODO | Record a functional run now from the existing tests; deploy with redacted provider evidence | 7–9 |
| Cloud data & analytics/AI | 20 | Dataset provenance and checksums, `data/DATA_DICTIONARY.md`, pandas cross-check in `evidence/test-data-ai.md`, dashboard, optional ML | No cloud database or storage yet. M-01…M-06 | RDS plus S3 import evidence; fix M-01/M-03; add the M-02 time-split check and the M-06 evaluation record | 12–15 |
| Security & responsible practice | 15 | Settings, permission gates, CSRF, non-superuser DB role, `tests/test_security_negative.py` | `evidence/threat-control-map.md` and `evidence/test-security.md` are TODO. No IAM evidence. W-03. CSP accepted as absent (CR-012) | Threat map built from the existing tests; one named threat with a recorded test; least-privilege IAM | 5–7 |
| Scalability, resilience & ops | 15 | Local DB-outage recovery (`docs/reviews/foundation-batch-4.md`), `/health/`, JSON logs with request IDs | `evidence/test-resilience.md` and `evidence/monitoring.md` are TODO. No mechanism deployed | ALB health check or RDS backup/restore test; CloudWatch Logs Insights query export with interpretation; cost notes | 3–5 |
| Engineering quality & reproducibility | 10 | Clean app layout, pinned dependencies, CI, migration check, review logs | Manifest paths missing. Broken ML test command (F-06). Doc drift (F-05, S-005) | Script a manifest path check; fix the drift | 5–7 |
| Team contribution & communication | 5 | Review logs show work by role | `TEAM_CONTRIBUTIONS.md` and the `AI_USE_DECLARATION.md` table are TODO. No Claude or ML-author entry; no Phosphor (MIT), Google Fonts, Chart.js or HTMX attribution in the declaration | Fill both files | 0–2 |

## Suggested order

1. **P0 docs and copy:** F-05 and S-005. An hour of edits; removes contradictions a marker would see first.
2. **W-01** before anyone runs the AWS probe for evidence.
3. **ML: M-01 with M-03, then M-02 and M-06.** Turns "a clustering ran" into evaluated evidence.
4. **Evidence templates that need no AWS:** functional and security test records and the threat-control map from the existing tests, then `TEAM_CONTRIBUTIONS.md` and `AI_USE_DECLARATION.md`.
5. **The AWS track** (compulsory §4 items), including a control for W-03.
6. **P1 code fixes** (S-001, F-02/F-03, M-10, S-006, F-06/M-12, W-02), then P2.

## Limitations

- No browser was used. Focus behaviour (F-04, S-002), visual layout and dark-mode rendering were judged from code and computed contrast.
- The tenure effect in M-04 was not measured (signup dates were not in the segmentation output), and the M-02 check has not been run.
- AWS, Terraform and monitoring are not built, so they were assessed only against the rubric. Previously cleared findings (CR-003…007 parked, CR-012 accepted, items in `docs/reviews/`) were not reopened unless the code had regressed them.
- The uncommitted AWS probe was reviewed as in-progress work and was not run against a real account.
