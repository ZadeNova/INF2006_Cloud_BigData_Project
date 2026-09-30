# Threat-control map: research and plan

Status (25 September 2026): research done, map drafted here. Update 27 September 2026: [evidence/threat-control-map.md](../../evidence/threat-control-map.md) is filled from this draft, updated for the WAF login rule, vendored model-viewer and the 42Factors name; the row statuses there are authoritative. Purpose: the brief requires "validation against a named threat" and a threat-control mapping (Security, 15 marks: "threats mapped to controls; least privilege; secure secrets, access and validation"). Threats are taken from recognised ecommerce sources, then each is mapped to Northstar's control, where it is implemented, and its evidence. Constraint from the user: infrastructure security work must be **high return for low effort**, because the deadline is close.

## Sources (verified 25 September 2026)

| Ref | Source | What it contributes |
|---|---|---|
| S1 | OWASP Top 10:2025, <https://top10.owasp.org/2025/> | Web application risk categories: A01 Broken Access Control, A02 Security Misconfiguration, A03 Software Supply Chain Failures, A04 Cryptographic Failures, A05 Injection, A06 Insecure Design, A07 Authentication Failures, A08 Software or Data Integrity Failures, A09 Security Logging and Alerting Failures, A10 Mishandling of Exceptional Conditions |
| S2 | OWASP Automated Threats to Web Applications (OAT), <https://owasp.github.io/www-project-automated-threats-to-web-applications/> (CC BY-SA 3.0) | Ecommerce bot abuse. OAT-008 Credential Stuffing: "Mass log in attempts used to verify the validity of stolen username/password pairs". OAT-005 Scalping: "Obtain limited-availability and/or preferred goods/services by unfair methods". OAT-021 Denial of Inventory: "Deplete goods or services stock without completing the purchase". OAT-019 Account Creation. OAT-001 Carding |
| S3 | Verizon 2025 DBIR Retail Snapshot, <https://www.verizon.com/business/resources/infographics/2025-dbir-retail-snapshot.pdf> | Retail (NAICS 44–45): 837 incidents, 419 confirmed disclosures; System Intrusion, Social Engineering and Basic Web Application Attacks are 93% of breaches; data compromised includes credentials (26%) and payment (12%). Basic web application attacks "are largely about credentials and their reuse". Magecart (web skimming) named as a frequent retail breach. Across all industries, credential abuse is the most common initial access vector (22%) |
| S4 | Verizon, "Additional 2025 DBIR research on credential stuffing", <https://www.verizon.com/business/resources/articles/credential-stuffing-attacks-2025-dbir-research/> | Median 19% of daily authentication attempts were credential stuffing (12% for small businesses) |
| S5 | OWASP Credential Stuffing Prevention Cheat Sheet, <https://cheatsheetseries.owasp.org/cheatsheets/Credential_Stuffing_Prevention_Cheat_Sheet.html> | MFA first; otherwise layered defences (CAPTCHA, IP mitigation, leaked-password checks); mitigations should be temporary, not permanent lockouts |
| S6 | Singapore PDPC, Data Protection Obligations, <https://www.pdpc.gov.sg/overview-of-pdpa/the-legislation/personal-data-protection-act/data-protection-obligations> | Protection Obligation: reasonable security arrangements against unauthorised access, collection, use or disclosure of personal data |

Every row below cites one of these; the report's references list reuses them.

## Draft map (verified against the code on 25 September 2026)

Status values: **Mitigated** (control implemented and tested), **Planned** (in the AWS design, evidence after the Terraform build), **Partial**, **Accepted** (known risk, stated), **Not applicable** (with the reason).

| # | Threat (source) | How it applies to Northstar | Control | Where | Evidence | Status |
|---|---|---|---|---|---|---|
| T1 | Broken access control: viewing or changing another customer's order or cart (S1 A01) | Orders hold names, addresses and purchase history | Every cart and order lookup filtered by owner; foreign IDs return 404 | `src/orders/views.py`, `src/cart/services.py` | `tests/test_orders.py` (foreign order 404, owner-only list), `tests/test_cart.py` (foreign item update/delete) | Mitigated |
| T2 | Privilege escalation to operator functions (S1 A01) | Operators see sales and customer segments | `store_operator` permission on the dashboard and the product toggle | `src/reporting/views.py`, `src/catalogue/` | `tests/test_analytics_dashboard.py` (customer forbidden, anonymous redirected), `tests/test_security_negative.py` (customer cannot use operator toggle) | Mitigated |
| T3 | Cross-site request forgery on cart, checkout and logout (S1 A01) | A malicious page could submit a purchase as a logged-in customer | Django CSRF middleware on every mutation, including HTMX | `src/config/settings.py` | `tests/test_security_negative.py` (mutation without token rejected), `tests/test_accounts.py` (logout without token rejected) | Mitigated |
| T4 | Price, owner or quantity tampering (S1 A06) | A forged form field could buy at a lower price or into another cart | Owner, prices and totals derived on the server; quantity bounds | `src/orders/`, `src/cart/forms.py` | `tests/test_security_negative.py` (forged price/owner/total/status ignored, bad quantities rejected) | Mitigated |
| T5 | Duplicate or replayed checkout; overselling under concurrency (S1 A06) | Restocks bring bursts of buyers for the same shoe | Idempotency key, row locking, stock constraint | `src/orders/` | `tests/test_orders.py` (concurrent same key creates one order; two users racing the last unit; insufficient stock 409) | Mitigated |
| T6 | Injection and stored XSS (S1 A05) | Product names and form input reach SQL and HTML | ORM parameterisation; template auto-escaping | framework defaults | `tests/test_analytics_dashboard.py` (product names escaped) | Mitigated |
| T7 | Credential stuffing and account takeover (S2 OAT-008, S3, S4, S1 A07) | The most common retail breach pattern; customers reuse passwords | Framework password hashing and validators, session security. **No throttling, no MFA** | `src/config/settings.py` | `tests/test_accounts.py` (password validators) | **Partial**: decide on login throttling (below) |
| T8 | Secrets exposure: keys or passwords in source, image, state or logs (S1 A02, A04) | A leaked database password exposes every order | Secrets Manager at boot; values never in Terraform state; RDS-managed master password; `.env.example` placeholders; logs omit passwords and cookies | `docs/plans/aws-terraform.md`, `src/config/jsonlog.py` | `tests/test_request_logging.py` (login POST logs neither password nor cookie); AWS config export after the build | Mitigated (logging), Planned (AWS) |
| T9 | Unauthorised access to the database or storage (S1 A01, A02; S6) | Customer data sits in RDS; the dataset and analytics exports in S3 | Private RDS subnets; security groups ALB → app → DB only; non-superuser DB role; S3 Block Public Access and TLS-only policy | Terraform (planned), `src/tools/db_bootstrap.py` | `tests/test_settings.py` (non-superuser connection); after the build: anonymous S3 GET denied, RDS unreachable from the internet | Mitigated (DB role), Planned (AWS) |
| T10 | Data interception in transit (S1 A04) | Logins and addresses cross the internet | HTTPS at the ALB with HTTP redirect, secure cookies, HSTS, TLS `verify-full` to RDS | `src/config/settings.py`, Terraform (planned) | `tests/test_settings.py` (production configuration); HTTPS check after the build | Mitigated (app), Planned (AWS) |
| T11 | Security misconfiguration (S1 A02) | Debug pages or open hosts leak internals | Debug refused outside local mode; explicit allowed hosts; IMDSv2; no SSH (Systems Manager only) | `src/config/settings.py`, Terraform (planned) | `tests/test_settings.py` (invalid configuration fails) | Mitigated (app), Planned (AWS) |
| T12 | Undetected attack or failure (S1 A09) | Nobody would notice a login flood or an error spike | Structured JSON request logs with request IDs; CloudWatch 5xx alarm to SNS email; CloudTrail event history | `src/config/middleware.py`, Terraform (planned) | `tests/test_request_logging.py`; alarm test after the build | Mitigated (logs), Planned (alarm) |
| T13 | Web skimming / script injection, Magecart (S3, S1 A03, A08) | A tampered script could read checkout forms | No third-party scripts; HTMX and Chart.js vendored with recorded SHA-256; simulated payments only. **No Content-Security-Policy** (accepted as CR-012) | `src/static/vendor/` | vendored checksums in `src/static/vendor/*/README.md` | Partial (accepted) |
| T14 | Scalping bots on limited restocks (S2 OAT-005) | Popular shoe restocks fit the pattern | None beyond login required to buy | — | — | Accepted: future per-account purchase limits |
| T15 | Denial of inventory (S2 OAT-021) | Bots filling carts to deplete stock | Carts do not reserve stock (stock is checked, "indicative", and only decremented at checkout) | `src/cart/services.py` | `tests/test_cart.py`, `tests/test_orders.py` | Not applicable by design |
| T16 | Carding / card testing (S2 OAT-001) | Card validity checks through checkout | Payments are simulated; no card data is collected | — | — | Not applicable |
| T17 | Personal data misuse (S6) | Customer accounts and orders are personal data | Synthetic dataset only; imported customers get unusable passwords; sanitised logs | `data/README.md`, importer | `tests/test_import.py`, `tests/test_request_logging.py` | Mitigated |

Before any row is marked Mitigated in `evidence/`, each cited test is re-run and the run is recorded in `evidence/test-security.md` (date, command, result), as the brief requires.

## Infrastructure controls ranked by return

High return means the control is mostly Terraform settings we are writing anyway, costs nothing extra, and yields a text export or a one-command test as evidence.

| Rank | Control | Effort | Evidence | Rows |
|---|---|---|---|---|
| 1 | Security-group chain ALB → app:8000 → RDS:5432, RDS private | Part of the network stage | SG export; connection from a laptop to RDS and to port 8000 times out | T9 |
| 2 | S3 Block Public Access, TLS-only bucket policy, encryption | A few lines | Anonymous `curl` of an object returns 403 | T9 |
| 3 | Secrets Manager, values outside state | Planned already | Redacted secret metadata; `grep` of state and image finds no secret | T8 |
| 4 | HTTPS listener with a TLS 1.2+ policy, HTTP redirect | Planned already | `curl -I http://…` shows the redirect; certificate details | T10 |
| 5 | IMDSv2 required, no SSH key, Systems Manager access | Launch-template settings | Launch-template export | T11 |
| 6 | RDS encryption and forced TLS | Two settings | RDS export; `sslmode` evidence | T9, T10 |
| 7 | CloudWatch 5xx alarm to SNS email | Small; doubles as the Operations requirement | Alarm export and the received email | T12 |
| 8 | CloudTrail event history | Zero (default) | Screenshot or `lookup-events` export of our own changes | T12 |

**Skip (low return for the deadline):** WAF (cost, lab permission unknown, interferes with load tests), GuardDuty, Security Hub, Inspector, Macie, customer-managed KMS keys (AWS-managed keys are enough), VPC flow logs.

## Decisions for the user

1. **T7 login throttling.** It is the one gap the research makes prominent (S3, S4). Options: app-level throttle (a counter of failed logins per account and IP, temporary as S5 advises; about half a day plus the review gate, testable offline) or leave it as Partial with the rationale. Recommended: the app-level throttle if it fits before the 1 October freeze.
2. **T13 CSP.** Leave accepted. `base.html` has one inline script (theme bootstrap), so a strict CSP needs a hash; not worth it before the freeze.

## Steps after approval

1. Fill `evidence/threat-control-map.md` with this table (T1 to T17) and the sources list.
2. Re-run the cited tests and record them in `evidence/test-security.md`.
3. Add the planned rows' evidence as each Terraform stage lands.
