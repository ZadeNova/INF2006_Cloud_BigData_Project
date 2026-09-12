# Security contract

Read [scope](../PROJECT_SCOPE_INF2006.md) and [API](API.md). This defines controls; evidence/threat-control-map.md records their actual implementation and proof.

- Use framework password hashing and database sessions; no custom cryptography or frontend token store.
- Share signing configuration. Use Secure/HttpOnly cookies and SameSite=Lax under HTTPS. Verify logout/expiry across instances and plan expired-session cleanup.
- Enforce ownership on every cart/order lookup and operator permission on every analytics request. Imported identities are not active logins by default.
- Enforce CSRF on browser mutations including HTMX. Validate bounds, use parameterised ORM queries and escape untrusted values.
- Derive owner/prices/totals on server. Transactions, stock constraints and idempotency protect concurrent/retried checkout. Simulated payments only.
- Disable production debug; restrict allowed hosts; configure trusted proxy handling and safe redirects correctly.
- Private RDS/S3, restricted security groups/IAM and non-superuser runtime DB role. Separate migration privileges where practical; document lab limits honestly.
- Inject secrets through permitted runtime mechanisms. Examples contain placeholders. Never commit tokens, private keys, passwords, Terraform state or real personal data.
- Log request IDs, durations and sanitised errors, not credentials/cookies/raw personal payloads. Follow brief redaction rules for cloud evidence.
- Optional caching must not bypass authorisation or share personalised content. Restrict cache access and tolerate its loss for disposable reads.

Negative tests: unauthenticated checkout, foreign cart/order access, non-operator analytics, missing/invalid CSRF, quantity/price manipulation, duplicate checkout and anonymous S3 access. Record expected/actual results; a generic security claim is insufficient.
