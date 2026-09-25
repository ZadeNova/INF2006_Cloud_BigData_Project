# Evidence kit: a frictionless workflow for the evidence writer

Written 26 September 2026, branch `erfan/analytics`. Agreed with the user before writing.

**Revised the same day (supersedes the design below):** no slash command, no `docs/evidence-kit/` folder, no `AGENTS.md` edit and no evidence skeletons written by the developer. Everything is one file, [docs/EVIDENCE_WRITER.md](../EVIDENCE_WRITER.md), which overrides the developer workflow itself; the writer pastes a one-line prompt pointing to it. Everyone branches from `erfan/analytics`. The rules, case catalogue, file order and change map below carried over into that file.

## Goal

One teammate (the evidence writer) owns every file under `evidence/` and keeps it current with their own Claude Code, while development continues. They should need **one command per session** (`/evidence`) and no knowledge of the repository's development workflow. Nothing may be fabricated: every result in `evidence/` comes from a command run in that session, and every file matches what the brief requires (Section 5.2 fields, Section 8 manifest paths, Section 9 evidence rules).

## Decisions (made with the user)

- **One evidence writer**, not files split across the team. They update evidence continuously as changes land, not in one pass at the end.
- **Git flow: branch plus PR.** Each session starts from the latest integration branch on a fresh `evidence/<YYYY-MM-DD>-<topic>` branch; the user reviews and merges. Commits carry the writer's authorship (evidence for `TEAM_CONTRIBUTIONS.md`).
- **No checker script.** A done checklist in the kit replaces it.
- **`AGENTS.md` gets a short "Evidence writing" section** so the writer's Claude Code does not follow the developer workflow (plan files, review gate, tracker updates, the full required reading).
- **First version covers local cases only.** Cloud cases are listed as `PLANNED` with no commands; their commands are added after Terraform exists so they cite real resource names.
- **The kit lives in `docs/evidence-kit/`**, which is excluded from the submission ZIP. Only `evidence/` is submitted.

## Friction removed, and how

| Friction for the writer | Fix |
|---|---|
| Remembering a long prompt | Project slash command `.claude/commands/evidence.md`: `/evidence` (catch up), `/evidence setup` (first time), `/evidence <CASE-ID>` (one case) |
| Their Claude reads `CLAUDE.md` → "Discuss/Plan, write a plan to `docs/plans/`, review gates" | `AGENTS.md` evidence section: evidence tasks follow the kit only; no plan file, no review gate (documentation-only work is already outside it), no tracker edits, no required reading beyond the kit |
| Not knowing which tests prove what | `CASES.md`: every case with its ID, threat/requirement, exact pytest node IDs, command, expected result and "ready when" condition, all checked against the repository |
| Not knowing what to update after new commits | `CHANGE_MAP.md` maps changed paths to affected cases; the index in `evidence/README.md` records the last covered commit, so the AI runs `git log <last>..HEAD --name-only` |
| Stale results because the image copies `src/` at build time | Every session runs `docker compose build web` before tests (from `tests/README.md`) |
| AI guesses dates, invents output, patches failing code, marks its own work verified | Hard rules in the kit `README.md` (below) |
| Local setup on a fresh clone | `/evidence setup` walks through the existing quickstart in `src/README.md` (`.env` from `.env.example`, `docker compose up --build`), stops on the first error and explains it |
| Windows | Claude Code runs commands in bash (Git Bash on Windows), so `tee`, `date` and `git` work the same everywhere; the kit uses only those plus `docker compose` |

## Files

| File | Action | Contents |
|---|---|---|
| `.claude/commands/evidence.md` | new | The slash command: read the kit `README.md`, then run the routine named by the argument |
| `docs/evidence-kit/README.md` | new | The contract: role, scope (write only under `evidence/`), hard rules, session routines (setup, catch-up, single case), commit/PR steps, done checklist, what to tell the human at the end. Also a plain paste-in prompt for anyone not using Claude Code |
| `docs/evidence-kit/TEMPLATE.md` | new | The test-record format: summary table first, then one section per case with the Section 5.2 fields in the brief's own words, plus verdict, interpretation, automated equivalent, artefacts, limitations, "Verified by" (human only) |
| `docs/evidence-kit/CASES.md` | new | The case catalogue (below) |
| `docs/evidence-kit/CHANGE_MAP.md` | new | Path → case mapping (below) |
| `AGENTS.md` | edit | Add a short "Evidence writing" section pointing to the kit |
| `evidence/*.md` (6 files) | rewrite | Skeletons in the template format with every case listed as `NOT RUN YET` or `PLANNED`. No results. The existing `test-data-ai.md` content is kept unchanged below the new summary until the data owner re-runs it |
| `evidence/README.md` | rewrite | Index: case ID → title → file → environment → status → date, plus "Last covered commit: none yet" and the evidence rules |
| `evidence/raw/.gitkeep` | new | Folder for raw outputs, named `<CASE-ID>_<YYYY-MM-DD>.<ext>` |

Not changed: application code, tests, `docs/IMPLEMENTATION_PLAN.md` (updated once at the end with one entry), the manifest.

## Hard rules in the kit (the no-fabrication contract)

1. Write only under `evidence/`. Never edit `src/`, `tests/`, `analytics/`, `data/` or `docs/`. A failing test is recorded as FAIL and reported to the human, never fixed.
2. "Actual result" comes only from a raw file the AI created in this session with `<command> 2>&1 | tee evidence/raw/<CASE-ID>_<date>.txt`. If a command cannot run, the case stays `NOT RUN YET` and the AI says why.
3. Write the expected result from `CASES.md` before running; never change it after seeing the output.
4. Raw files are never edited except cutting lines (marked `…`) and redacting (`<REDACTED>`). Numbers in the `.md` are copied from raw files, unchanged.
5. Dates from `date +%F`; commit from `git rev-parse --short HEAD`. Never from memory.
6. Status words: `PASS`, `FAIL`, `NOT RUN YET`, `PLANNED`. Environment: `Local Docker` or `AWS`, never blurred.
7. Re-runs add a new dated row; earlier rows stay. A FAIL gets a diagnosis and a follow-up row after the fix.
8. Manual steps (browser walkthroughs) record only what the human reports, in their words; screenshots are supplements named `<CASE-ID>_<date>_<n>.png` with a caption and a text description.
9. Links are relative and point only to files that will be in the ZIP (never `docs/`).
10. No `aws` or `terraform` commands, no credentials, no personal data. Redaction check before commit: `grep -rEn '[0-9]{12}|amazonaws\.com|arn:aws' evidence/`.
11. The AI never writes "Verified by". It ends every session with a short list of what the human must check.
12. Commit only when the human says so, on the evidence branch, with a descriptive body (AGENTS.md commit rule).

## Case catalogue (first version)

pytest commands use `docker compose run --rm web pytest -v -p no:cacheprovider <node ids>` so the raw file lists every test by name. All node IDs below exist in the repository today; implementation re-checks each one.

| Case | File | What it proves | Source | Ready |
|---|---|---|---|---|
| FUNC-01 | test-functional | Automated workflow suite: accounts, catalogue, cart, checkout, history | `tests/test_accounts.py`, `test_catalogue.py`, `test_cart.py`, `test_orders.py` | Now |
| FUNC-02 | test-functional | Manual browser walkthrough: register → browse → add to cart → checkout → order in history → operator toggle and dashboard | Checklist in `CASES.md`; human reports observations | Now |
| SEC-01 | test-security | T1 broken access control (IDOR) | `test_orders.py::test_order_detail_returns_404_for_foreign_order_200_for_owner`, `::test_order_list_shows_only_the_owners_orders_most_recent_first`, `test_cart.py::test_update_on_foreign_item_returns_404_and_does_not_mutate`, `::test_delete_does_not_touch_a_foreign_cart_item` | Now |
| SEC-02 | test-security | T2 privilege escalation to operator functions | `test_security_negative.py::test_a_customer_cannot_use_the_operator_toggle`, `test_analytics_dashboard.py::test_customer_is_forbidden_even_with_htmx` | Now |
| SEC-03 | test-security | T3 CSRF | `test_security_negative.py::test_a_mutation_without_a_valid_csrf_token_is_rejected_and_changes_nothing`, `test_accounts.py::test_logout_without_csrf_token_is_rejected` | Now |
| SEC-04 | test-security | T4 price, owner and quantity tampering | `test_security_negative.py::test_checkout_ignores_forged_price_owner_total_and_status_fields`, `::test_cart_add_ignores_forged_owner_cart_and_price_fields`, `::test_cart_add_rejects_bad_quantities_without_creating_anything` | Now |
| SEC-05 | test-security | T5 duplicate checkout and overselling under concurrency | `test_orders.py::test_concurrent_checkouts_same_idempotency_key_create_exactly_one_order`, `::test_concurrent_checkouts_different_users_racing_last_unit_of_stock` | Now |
| SEC-06 | test-security | T6 stored XSS | `test_analytics_dashboard.py::test_rendered_dashboard_escapes_product_names_and_shows_status_labels` | Now |
| SEC-07 | test-security | T7 weak passwords (partial control; no throttling or MFA, stated as a limitation) | `test_accounts.py::test_registration_enforces_the_password_validators` | Now |
| SEC-08 | test-security | T8 secrets and personal data kept out of logs | `test_request_logging.py::test_a_login_post_logs_neither_the_password_nor_the_cookie`, `::test_query_strings_are_not_logged`, `::test_a_rejected_referer_is_not_echoed_into_the_security_log` | Now |
| SEC-09+ | test-security | T9–T12 cloud controls: RDS unreachable from the internet, S3 anonymous access denied, HTTPS redirect, secrets from Secrets Manager | — | `PLANNED`, after Terraform |
| THREAT | threat-control-map | T1–T17 from `docs/plans/threat-control-map.md`, restated with sources; a row is "Mitigated" only when its SEC case has a PASS row | Draft map | Now (cloud rows `PLANNED`) |
| DATA-01 | test-data-ai | Analytics refresh reconciliation against an independent pandas check | Existing 22 September record, kept verbatim | Re-run by the data owner after the shoe remap |
| DATA-02 | test-data-ai | ML segmentation evaluation | — | `PLANNED`, after the ML evaluation is committed |
| RES-01 | test-resilience | Database outage returns a clean 503 and health stays up (automated) | `tests/test_db_unavailable.py`, `tests/test_health.py` | Now |
| RES-02 | test-resilience | Live local outage: stop `db`, request a page and `/health/`, start `db`, confirm recovery | Steps in `CASES.md`, verified during implementation | Now |
| RES-03+ | test-resilience | Cloud mechanism (ALB health check replacement, backup restore or load test) | — | `PLANNED`, after Terraform |
| MON-01 | monitoring | Local structured JSON request logs: generate requests, export the log, summarise by status and path | Command verified during implementation (no `jq` assumed; Python in the container) | Now |
| MON-02+ | monitoring | CloudWatch Logs Insights query export and 5xx alarm test | — | `PLANNED`, after Terraform |

## Change map (first version)

| Changed path | Re-run |
|---|---|
| `src/accounts/`, `src/catalogue/`, `src/cart/`, `src/orders/`, `src/templates/` | FUNC-01, FUNC-02, SEC-01–05 |
| `src/reporting/`, `src/templates/reporting/` | SEC-02, SEC-06, FUNC-02 (dashboard step) |
| `src/config/settings.py`, `src/config/middleware.py` | SEC-03, SEC-07, SEC-08, RES-01 |
| `src/config/jsonlog.py` | SEC-08, MON-01 |
| `analytics/`, `data/`, import or refresh commands | DATA-01, DATA-02 (data owner) |
| `terraform/` (future) | cloud cases, once their commands exist |
| `tests/` | the cases citing the changed files |
| `docs/plans/threat-control-map.md` | THREAT |

## Open item for the user

`erfan/analytics` is 26 commits ahead of `main`, and the kit cites files that exist only on this branch (and the currently untracked `docs/plans/threat-control-map.md`). Before the writer starts, the kit and the draft map must be on the branch they start from: merge to `main`, or tell the writer to branch from `erfan/analytics`. Decided at commit time.

## Verification

- Every pytest node ID in `CASES.md` resolves: `docker compose run --rm web pytest --collect-only -q <ids>`.
- The RES-02 and MON-01 commands are dry-run once locally to confirm they work; their output is **not** saved to `evidence/` (the writer runs them for real).
- `/evidence` is checked to be picked up as a project command.
- Every relative link in `evidence/` and the kit resolves.
- No test results are written anywhere by this task.

## Out of scope

Running the evidence cases, filling any result, cloud task cards, a checker script, packaging, and changes to code or tests.
