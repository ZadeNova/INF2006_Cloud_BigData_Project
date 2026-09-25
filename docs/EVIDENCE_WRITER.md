# Evidence writer instructions

For the evidence writer's AI assistant. Goal: write and maintain the files in `evidence/`, which markers (a professor and an AI-assisted grader) credit only for verifiable results.

**This overrides the developer workflow in CLAUDE.md/AGENTS.md:** no plan files, no review gates, no edits to `docs/IMPLEMENTATION_PLAN.md`, no reading beyond the files named here. Never commit or push unless the human says so.

## Rules (no fabrication)

1. Write only under `evidence/`. If a test fails, record FAIL and tell the human; never fix code.
2. Results come only from commands you ran this session: `<cmd> 2>&1 | tee evidence/raw/<CASE>_<YYYY-MM-DD>.txt`. If a command can't run, the status is `NOT RUN YET`, with the reason.
3. Write the expected result (from this file) before running. Never change it afterwards.
4. Raw files: only cut lines (`…`) or redact (`<REDACTED>`). Copy numbers into the `.md` exactly as they appear in the raw file.
5. Date from `date +%F`; commit from `git rev-parse --short HEAD`.
6. Status: `PASS` / `FAIL` / `NOT RUN YET` / `PLANNED`. Environment: `Local Docker` or `AWS`.
7. Re-runs add a new dated row; old rows stay.
8. Manual steps: record only what the human reports, in their words.
9. Links: relative, never into `docs/` (not submitted).
10. No `aws`/`terraform` commands, credentials or personal data. Before committing, run `grep -rEn '[0-9]{12}|amazonaws\.com|arn:aws' evidence/`.
11. Never write "Verified by". Only the human adds it.
12. Stop after each file for the human's review.

## Setup (each session)

```bash
git status                     # uncommitted changes? stop and ask
git fetch origin
git switch -c evidence/<YYYY-MM-DD>-<topic> origin/erfan/analytics
python src/tools/init_env.py   # fresh clone only
docker compose up --build -d
docker compose build web       # ALWAYS before tests: the image copies src/ at build time
docker compose run --rm web pytest -v -p no:cacheprovider <node ids>
```

If setup fails, stop and explain the error in plain words.

## Record format

Each file starts with a **Summary** table (Case | Proves | Threat/requirement | Environment | Date | Commit | Status). Then one section per case with these fields: **Objective, Threat/requirement, Setup, Command/steps, Expected result, Actual result** (a 10–20 line excerpt), **Status, Interpretation** (2–3 sentences: what it shows and what it does not), **Automated equivalent, Artefacts** (links to `raw/`), **Date/commit, Limitations/follow-up, Verified by** (left blank), then a **Run history** table (Date | Commit | Environment | Status | Raw file). Write in plain English with no internal jargon.

## Order: do the first unfinished file, then stop

**1. `evidence/README.md` + `evidence/raw/.gitkeep`**: an index (Case | Title | File | Environment | Status | Date) listing every case below, plus `Last covered commit: <hash>` and the evidence rules. `architecture.png` is marked "TODO (report lead)".

**2. `evidence/test-functional.md`**
- FUNC-01: pytest `/app/tests/test_accounts.py /app/tests/test_catalogue.py /app/tests/test_cart.py /app/tests/test_orders.py`. Expected: 0 failed, 0 errors.
- FUNC-02: a manual walkthrough. Load the data following the "Demo data" section of `src/README.md` (on a fresh database), then guide the human one step at a time:
  1. `/` redirects to the catalogue.
  2. Register at `/register/` → logged in.
  3. Add two products, change a quantity → the cart shows both lines with the right subtotal.
  4. Check out → a confirmation page with an order number and total.
  5. `/orders/` → the new order is listed first.
  6. Log in as `demo-operator`, deactivate a product at `/products/manage/` → it disappears from `/products/`; reactivate it.
  7. `/analytics/` → the dashboard renders.
  8. As the customer, `/analytics/` → access refused.

  Ask whether the human wants screenshots (`raw/FUNC-02_<date>_<n>.png`, each with a caption).

**3. `evidence/test-security.md`**: all tests are in `/app/tests/`, and all are expected to pass. Also do one combined run saved as `raw/SEC-ALL_<date>.txt`. Read each test before explaining how it demonstrates the control.

| Case | Threat | Tests |
|---|---|---|
| SEC-01 | T1 Broken access control / IDOR (OWASP A01:2025) | `test_orders.py::test_order_detail_returns_404_for_foreign_order_200_for_owner`, `test_orders.py::test_order_list_shows_only_the_owners_orders_most_recent_first`, `test_cart.py::test_update_on_foreign_item_returns_404_and_does_not_mutate`, `test_cart.py::test_delete_does_not_touch_a_foreign_cart_item` |
| SEC-02 | T2 Privilege escalation (A01) | `test_security_negative.py::test_a_customer_cannot_use_the_operator_toggle`, `test_analytics_dashboard.py::test_customer_is_forbidden_even_with_htmx` |
| SEC-03 | T3 CSRF (A01) | `test_security_negative.py::test_a_mutation_without_a_valid_csrf_token_is_rejected_and_changes_nothing`, `test_accounts.py::test_logout_without_csrf_token_is_rejected` |
| SEC-04 | T4 Price/owner/quantity tampering (A06) | `test_security_negative.py::test_checkout_ignores_forged_price_owner_total_and_status_fields`, `::test_cart_add_ignores_forged_owner_cart_and_price_fields`, `::test_cart_add_rejects_bad_quantities_without_creating_anything` |
| SEC-05 | T5 Duplicate checkout / overselling (A06) | `test_orders.py::test_concurrent_checkouts_same_idempotency_key_create_exactly_one_order`, `::test_concurrent_checkouts_different_users_racing_last_unit_of_stock` |
| SEC-06 | T6 Stored XSS (A05) | `test_analytics_dashboard.py::test_rendered_dashboard_escapes_product_names_and_shows_status_labels` |
| SEC-07 | T7 Weak passwords (A07). Limitation: no throttling, no MFA | `test_accounts.py::test_registration_enforces_the_password_validators` |
| SEC-08 | T8 Secrets in logs (A09) | `test_request_logging.py::test_a_login_post_logs_neither_the_password_nor_the_cookie`, `::test_query_strings_are_not_logged`, `::test_a_rejected_referer_is_not_echoed_into_the_security_log` |
| SEC-09–11 | T8–T10 cloud: private RDS/S3, HTTPS, Secrets Manager | PLANNED (after the AWS build) |

**4. `evidence/threat-control-map.md`**: built from the "Sources" and "Draft map" sections of `docs/plans/threat-control-map.md`. Columns: ID | Threat (source) | How it applies | Control | Where implemented | Evidence (case) | Status. A row can be "Mitigated" only if its SEC case has a PASS. Cloud rows stay "Planned". Keep Partial/Accepted/Not applicable rows with their reasons. Check every "Where implemented" path exists, and flag any that don't. Finish with a References section for S1–S6.

**5. `evidence/test-resilience.md`**
- RES-01: pytest `/app/tests/test_db_unavailable.py /app/tests/test_health.py`. Expected: all pass.
- RES-02: a live outage, all in one raw file with `date +%T` between steps. `curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/products/` → 200. Run `docker compose stop db`. `/products/` → 503, `/health/` → 200. Run `docker compose start db` and wait until `docker compose run --rm web python manage.py check_database` succeeds. `/products/` → 200. If something behaves differently, record it; don't retry until it matches.
- RES-03: a cloud mechanism. PLANNED.

**6. `evidence/monitoring.md`**
- MON-01: make a few requests with curl (200s, a 404, anonymous `/analytics/`), export with `docker compose logs web --no-log-prefix --since 15m > evidence/raw/MON-01_<date>_logs.txt`, then summarise status and path counts with a short Python command, saving the command and its output to `raw/MON-01_<date>_summary.txt`. Confirm there are no passwords, cookies or query strings in the logs. Interpretation: how an operator traces a failure by request ID, and what's missing locally (no alerting).
- MON-02: a CloudWatch query and 5xx alarm. PLANNED.

**7. `evidence/test-data-ai.md`**: restructure only. Add the Summary at the top and keep all existing content verbatim under "Run of 22 September 2026 (original dataset)". DATA-01 is PASS for that run, re-run by the data owner after the shoe remap. DATA-02 (ML evaluation) is PLANNED. Run no data commands.

## Update mode ("update evidence")

Read `Last covered commit` from `evidence/README.md`, run `git log <commit>..HEAD --name-only --oneline`, and propose re-runs from the table below. Wait for an OK, re-run, add new rows, then update the index and the commit.

| Changed | Re-run |
|---|---|
| `src/accounts/`, `catalogue/`, `cart/`, `orders/`, `templates/` | FUNC-01, FUNC-02, SEC-01–05 |
| `src/reporting/` | SEC-02, SEC-06, FUNC-02 steps 7–8 |
| `src/config/settings.py`, `middleware.py` | SEC-03, SEC-07, SEC-08, RES-01 |
| `src/config/jsonlog.py` | SEC-08, MON-01 |
| `tests/<file>` | the cases citing it |
| `docs/plans/threat-control-map.md` | threat-control-map.md |
| `analytics/`, `data/` | tell the human to notify the data owner (don't run) |
| `terraform/` or AWS | tell the human: the cloud cases need instructions added here |

## End of each file

Re-check that every number appears in a raw file and every link resolves. Run the redaction grep. Give the human a short checklist to verify before they add "Verified by". Suggest a commit message with a descriptive body. Commit and push only when told to; the PR targets `erfan/analytics`.
