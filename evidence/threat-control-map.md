# Threat-control map

Last updated 27 September 2026 at the `syah&hermann/ML` branch (source commit `c923958`). Threats come from recognised ecommerce sources (below), each mapped to 42Factors' control, where it is implemented and its evidence. Research and ranking of the cloud controls: [docs/plans/threat-control-map.md](../docs/plans/threat-control-map.md). Control requirements: [docs/SECURITY.md](../docs/SECURITY.md).

## Status words

- **Mitigated:** the control is implemented and its security case has a recorded `PASS` in [test-security.md](test-security.md).
- **Implemented, not yet recorded:** the control and automated tests exist, but no dated security case records them yet. Not a claim of proof.
- **Planned:** part of the AWS design; evidence only after the Terraform build (SEC-09 to SEC-11).
- **Partial:** some of the threat is controlled; the gap is stated.
- **Accepted:** a known risk, stated with the reason.
- **Not applicable:** the threat cannot occur in this design; the reason is stated.

## Map

The local security cases SEC-01 to SEC-08 passed on 2026-09-26 at `ee334cf` in local Docker ([test-security.md](test-security.md)); cloud cases SEC-09 to SEC-11 are planned.

| # | Threat (source) | How it applies to 42Factors | Control | Where implemented | Evidence | Status |
|---|---|---|---|---|---|---|
| T1 | Broken access control: reading or changing another customer's order or cart (S1 A01) | Orders hold purchase history | Every cart and order lookup is filtered by owner; foreign IDs return 404 | `src/orders/views.py`, `src/cart/views.py`, `src/cart/services.py` | SEC-01 | Mitigated |
| T2 | Privilege escalation to operator functions (S1 A01) | Operators see sales and customer segments and can deactivate sizes | `reporting.view_analytics` on the dashboard; `catalogue.toggle_product_active` on the manage list and toggle | `src/reporting/views.py`, `src/catalogue/views.py` | SEC-02 | Mitigated |
| T3 | Cross-site request forgery on cart, checkout, toggle and logout (S1 A01) | A malicious page could submit a purchase as a logged-in customer | Django CSRF middleware on every mutation, including HTMX | `src/config/settings.py` | SEC-03 | Mitigated |
| T4 | Price, owner or quantity tampering (S1 A06) | A forged field could buy at a lower price or into another cart | Owner, prices and totals derived on the server; quantity bounds 1..999 | `src/orders/services.py`, `src/cart/forms.py`, `src/cart/services.py` | SEC-04 | Mitigated |
| T5 | Duplicate or replayed checkout; overselling under concurrency (S1 A06) | Restocks bring bursts of buyers for the same shoe size | User-scoped idempotency key, row locking in a consistent order, stock constraint | `src/orders/services.py` | SEC-05 | Mitigated |
| T6 | Injection and stored XSS (S1 A05) | Product names and form input reach SQL and HTML | ORM parameterisation; template auto-escaping; chart data through `json_script` | framework defaults, `src/templates/reporting/_panel.html` | SEC-06 | Mitigated |
| T7 | Credential stuffing and account takeover (S2 OAT-008, S3, S4, S1 A07) | The most common retail breach pattern; customers reuse passwords | Framework password hashing and validators; database sessions with Secure/HttpOnly cookies in production. **No app-level throttling and no MFA.** Planned: one WAF rate-based rule on `POST /login/` | `src/config/settings.py`; WAF in [AWS_INFRASTRUCTURE.md](../docs/AWS_INFRASTRUCTURE.md) (planned) | SEC-07 (validators only) | **Partial** (app); Planned (WAF) |
| T8 | Secrets exposure in source, image, state or logs (S1 A02, A04) | A leaked database password exposes every order | Logs omit passwords, cookies and query strings; local secrets generated into the git-ignored `src/.env`; production reads secrets from Secrets Manager at startup with role credentials only and no plaintext fallback | `src/config/jsonlog.py`, `src/config/middleware.py`, `src/tools/init_env.py`, `src/config/secrets.py` | SEC-08 (logs); `tests/test_secrets.py`; SEC-11 after the build | Mitigated (logs); Implemented, not yet recorded (startup loader); Planned (AWS) |
| T9 | Unauthorised access to the database or storage (S1 A01, A02; S6) | Customer data sits in RDS; dataset and media go to S3 | Non-superuser runtime database role with a separate migration owner; private RDS subnets; security groups ALB to app to DB only; S3 Block Public Access and TLS-only policy | `src/tools/db_bootstrap.py`; Terraform (planned) | `tests/test_settings.py::test_postgresql_connection_uses_non_superuser`, `tests/test_db_bootstrap.py` (opt-in); SEC-09 after the build | Implemented, not yet recorded (DB role); Planned (AWS) |
| T10 | Data interception in transit (S1 A04) | Logins and addresses cross the internet | HTTPS redirect, Secure cookies and HSTS in production settings; `verify-full` TLS to RDS with the vendored CA bundle; HTTPS at the ALB | `src/config/settings.py`, `src/config/database.py`, `src/certs/`; Terraform (planned) | `tests/test_settings.py::test_production_configuration`; SEC-10 after the build | Implemented, not yet recorded (app); Planned (AWS) |
| T11 | Security misconfiguration (S1 A02) | Debug pages or open hosts leak internals | Debug refused outside local mode; explicit allowed hosts, with one exact internal ALB probe exception for `/health/`; IMDSv2 and Systems Manager Session Manager instead of SSH | `src/config/settings.py`, `src/config/middleware.py`; Terraform (planned) | `tests/test_settings.py::test_invalid_configuration_fails`, `tests/test_health.py::test_exact_internal_probe_exception_preserves_normal_host_validation` | Implemented, not yet recorded (app); Planned (AWS) |
| T12 | Undetected attack or failure (S1 A09) | Nobody would notice a login flood or an error spike | Structured JSON request logs with request IDs; CloudWatch 5xx alarm to SNS email; CloudTrail event history | `src/config/middleware.py`, `src/config/jsonlog.py`; Terraform (planned) | `tests/test_request_logging.py`; MON-01/MON-02 in [monitoring.md](monitoring.md) (not run) | Implemented, not yet recorded (logs); Planned (alarm) |
| T13 | Web skimming or script injection, Magecart (S3, S1 A03, A08) | A tampered script could read checkout forms | No third-party scripts: HTMX, Chart.js and model-viewer are vendored with recorded SHA-256 values; simulated payments only. Google Fonts stylesheets are still loaded from Google. **No Content-Security-Policy** (accepted as CR-012) | `src/static/vendor/`, `src/templates/base.html` | checksums in `src/static/vendor/*/README.md` | **Partial** (accepted) |
| T14 | Scalping bots on limited restocks (S2 OAT-005) | Popular shoe restocks fit the pattern | None beyond requiring login to buy | — | — | Accepted: per-account purchase limits are future work |
| T15 | Denial of inventory (S2 OAT-021) | Bots filling carts to deplete stock | Carts never reserve stock; stock is only checked as indicative and decremented at checkout | `src/cart/services.py`, `src/orders/services.py` | `tests/test_cart.py::test_add_rejects_when_exceeding_current_stock_without_mutation`; SEC-05 | Not applicable by design |
| T16 | Carding or card testing (S2 OAT-001) | Card validity checks through checkout | Payments are simulated; no card data is collected | — | — | Not applicable |
| T17 | Personal data misuse (S6) | Customer accounts and orders are personal data | Synthetic dataset only; imported customers get unusable passwords; segment rows show `CUS-<id>` references, never usernames; sanitised logs | `data/README.md`, `src/config/management/commands/import_dataset.py`, `src/reporting/queries.py` | `tests/test_import.py::test_counts_mappings_rounding_and_sealed_inventory` (unusable passwords); SEC-08 (logs) | Implemented, not yet recorded (import, segments); Mitigated (logs) |

A row moves to **Mitigated** only after its cited tests or cloud checks are re-run and recorded as a dated security case in [test-security.md](test-security.md).

## Sources

Verified 25 September 2026; full notes in [docs/plans/threat-control-map.md](../docs/plans/threat-control-map.md#sources-verified-25-september-2026).

| Ref | Source |
|---|---|
| S1 | OWASP Top 10:2025, <https://top10.owasp.org/2025/> |
| S2 | OWASP Automated Threats to Web Applications (OAT), <https://owasp.github.io/www-project-automated-threats-to-web-applications/> (CC BY-SA 3.0) |
| S3 | Verizon 2025 DBIR Retail Snapshot, <https://www.verizon.com/business/resources/infographics/2025-dbir-retail-snapshot.pdf> |
| S4 | Verizon, "Additional 2025 DBIR research on credential stuffing", <https://www.verizon.com/business/resources/articles/credential-stuffing-attacks-2025-dbir-research/> |
| S5 | OWASP Credential Stuffing Prevention Cheat Sheet, <https://cheatsheetseries.owasp.org/cheatsheets/Credential_Stuffing_Prevention_Cheat_Sheet.html> |
| S6 | Singapore PDPC, Data Protection Obligations, <https://www.pdpc.gov.sg/overview-of-pdpa/the-legislation/personal-data-protection-act/data-protection-obligations> |
