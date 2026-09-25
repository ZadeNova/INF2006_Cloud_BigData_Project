# Review: triage of latest-opus5.5-review.md and test-suite audit

- Reviewer: **Independent (fresh session), Claude Opus 5.5**. The session had never seen the implementing conversations. It was read-only until the user approved the test trim; this log also records that implementation.
- Date: 25 September 2026. Snapshot: branch `erfan/analytics` at `f72a872`, clean working tree.
- Scope: (A) every finding ID in [latest-opus5.5-review.md](../latest-opus5.5-review.md) checked against the code; (B) the pytest suite judged by the test-budget rule in [AGENTS.md](../../AGENTS.md#simplicity-and-maintainability).
- AWS was not contacted and no sub-agents were used. A disposable Compose project (`inf2006-review`) held a full import for the ML checks and was deleted with its volume. Probe tests and mutant copies stayed in the session scratchpad; none were added to the repository.

## Checks run

| Check | Result |
|---|---|
| `docker compose build web`; collect | 466 collected (186 parametrised IDs) |
| Full suite (before) | **466 passed in 26.8 s**; slowest test 1.04 s |
| Scratch loader probe | `cluster_id` 40000 and `recency_days` 3e9 raise raw `DataError`; `NaN` and `Infinity` raise raw `ValidationError`; a superuser id is accepted |
| Scratch ARIA probe (`/register/`, `/login/`) | `/register/`: 5 of 5 `aria-describedby` targets missing; `/login/`: none referenced |
| Full import + `refresh_analytics --as-of 2026-01-02`, then scratch analysis with `analytics/requirements.txt` | 19,766 customers; silhouette k=2…6: 0.389, 0.333, 0.318, 0.313, 0.313 (k=2 always chosen); at k=2 `high_value` is 63.3% and `core` mean recency is 391 days; skew log(monetary) −1.45; corr(frequency, log monetary) 0.743; resampled (80%) ARI mean/min: k=2 0.98/0.96, k=3 0.96/0.91, k=4 0.73/0.44; 0 staff-owned orders |

## Task A: finding triage

| ID | Verdict | Severity | Recommendation |
|---|---|---|---|
| M-01 / F-01 | CONFIRMED (reproduced) | High if the panel is shown | Fix: fixed k=3 as a stated choice, naming test |
| M-02 | CONFIRMED (absent) | Medium | Document as descriptive only; time-split check optional |
| M-03 | CONFIRMED | Low–Medium | Document |
| M-04 | CONFIRMED (window); tenure not measured | Low | Relabel card, document |
| M-05 | CONFIRMED | Low–Medium | Fix with M-01 (subsample stability) |
| M-06 | CONFIRMED | Medium | Fix: commit metrics and profiles without customer rows |
| F-05, S-005, W-01, W-02 | ALREADY FIXED | none | none |
| S-001 | CONFIRMED on `/register/`; OVERSTATED for `/login/` | Medium (accessibility) | Fix plus one test |
| M-10 | CONFIRMED (username column); risk rises if a refresh cutoff includes live orders | Medium (privacy) | Fix: drop column, exclude staff in `fetch_rfm` |
| F-02 / M-09 | CONFIRMED (probe) | Low | Fix: map to `CommandError` |
| F-03 | CONFIRMED (probe) | Low–Medium | Fix with M-10 |
| S-006 | CONFIRMED (code path); partly documented in SCHEMA.md | Medium for the AWS demo | Document run order |
| F-06 / M-12 | CONFIRMED (vacuous assertion, no ML tests in CI); OVERSTATED (CI runs loader and panel tests; no `pytest analytics/tests` command is documented) | Low–Medium | Fix assertion, add CI step, document commands |
| W-03 | CONFIRMED; previously accepted | none | Document in threat map |
| F-04 | CONFIRMED in vendored HTMX source; no browser check | Low | Fix |
| S-002 | PLAUSIBLE | Low | Skip |
| S-003 | CONFIRMED | Low–Medium | Fix |
| S-004, S-007, S-008, M-07, M-08 | CONFIRMED | Low | Fix cheaply (S-007 done here) |
| M-11 | CONFIRMED (root-owned file); OVERSTATED (`--database-url` is not in the documented command) | Low | Doc fix |
| W-04 | CONFIRMED | Low | Skip |

Missed by the earlier review: the outage tests never reached a view body (a mutant that swallows errors in `CartDetailView.get` passed all 12 tests); `require_GET` and `http_method_names` duplicate each other on the dashboard view; the M-10 fix will need `test_analytics_dashboard.py` edited. Also, the tracker says W-01/W-02 are "not yet committed", but they were committed in `f72a872`.

## Task B: test trim

Rule: a case was removed only when a mutant showed that a kept test fails for every defect it detects, or (three cases, marked) when it hits the same constraint or framework branch as a kept value. Plan: [test-trim.md](../plans/test-trim.md).

| File | Before → after | Evidence |
|---|---|---|
| `test_security_negative.py` | 47 → 28 | Making cart add exempt from CSRF failed all 3 token variants alike; the app's HTMX posts the form field, not the header; `min_value=0` fails only `[0]` |
| `test_cart.py` | 29 → 25 | Login and bounds mutants were caught by the `test_security_negative.py` tests too |
| `test_orders.py` | 37 → 33 | Removing the review check failed all 5 values alike; removing the checkout login mixin fails the anonymous POST test |
| `test_analytics_ranges.py` | 59 → 27 | Comparison, week-end, daily-length, granularity and preset mutants are all caught by the kept explicit tests; the tiling matrix missed the week-end mutant entirely; 23:59:59 kept because a UTC+9 mutant fails it and not 10:00 |
| `test_analytics_dashboard.py` | 31 → 25 | Wrong-L mutant failed all 5 keys alike; removing both GET guards failed all 3 methods alike |
| `test_db_unavailable.py` | 12 → 8 | Logged-in cases fail while loading the session; the kept anonymous catalogue case fails when the view swallows the error, which none of the old 6 did |
| `test_request_logging.py` | 20 → 18 | `match` instead of `fullmatch` caught by the newline and 65-character cases; only a harmless widening of allowed characters was caught by the removed two |
| `test_schema.py`, `test_analytics_snapshot.py`, `test_accounts.py` | −1 each (reasoned) | Same constraint, same branch, or Django's own LogoutView behaviour |
| Source | `coerce_range` deleted | Dead code (S-007) |

Tests not changed here: the vacuous `demo-operator` assertion and the new F-02, F-03, S-001 and M-01 tests belong with those fixes. Defensible range for this project: about 370–410. Below that, the remaining tests catch distinct defects.

### Implementation verification (after approval)

| Check | Result |
|---|---|
| `docker compose build web`; collect | 392 collected |
| `docker compose run --rm web pytest -q -p no:cacheprovider /app/tests` | **392 passed in 26.5 s** |
| `manage.py check` / `makemigrations --check --dry-run` | no issues / no changes |
| 22 mutants re-run against the trimmed suite | every defect the old suite caught is still caught; the new anonymous outage case adds one it did not catch |

Limitations: the same session proposed and implemented the trim, so this is not an independent review of the implementation; the backend gate for this change is still open. No browser was used.
