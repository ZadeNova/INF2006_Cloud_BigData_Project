# Authentication review

Task ID `auth-registration`. Round 1 of the independent backend review gate ([DEVELOPMENT.md](../DEVELOPMENT.md#backend-review-gate)); brief: [astra-review.md](../plans/astra-review.md). Report received 20 September 2026 from the project's teammate running Astra as the independent reviewer (model and reasoning level are not stated in the report). Log written by the coordinator (the user with Claude Code) from that report.

- **Base and snapshot:** `4795f9f..cafe528`. Reviewed PR head `d0922916e12c9df6c582c369032b70c975c967b4`.
- **Owned paths:** `src/accounts/` (urls, views), the related settings (`LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL`), `tests/test_accounts.py`.
- **Specs:** [API.md](../API.md) auth rows, [SECURITY.md](../SECURITY.md), [SCHEMA.md](../SCHEMA.md).
- **Status:** Round 1 complete; **no actionable findings**.

## Result

No actionable findings in the reviewed diff.

## Checks and limitations

Environment: built from Git into a separate Docker image with pinned dependencies and PostgreSQL, disposable database, non-superuser role; fresh migrations, `manage.py check` and `makemigrations --check --dry-run` passed; full suite 301 passed. The literal root Compose commands were not run; the host checkout was not edited.

Task-specific: registration, login and logout tests passed, including duplicate usernames, password validation, safe and unsafe `next` URLs, authenticated-user redirects and logout CSRF. Registration creates no `CustomerProfile`; seed account collisions do not grant privileges.

Limitations: imported-user provisioning is not implemented in this task, and deployed cross-instance session behaviour was not exercised. Session rotation remains delegated to Django's login implementation; the suite does not directly assert key rotation. No new owner decision identified.

## Findings

| ID | Severity | File/line | Required spec / evidence | Issue and expected correction | Low fix / verification | Re-review outcome |
|---|---|---|---|---|---|---|
| none | n/a | n/a | n/a | No actionable findings. | n/a | n/a |
