# SEC-001 fix (round 2 repeat): stop `django.security` log messages leaking user input

## Context
Astra's round-2 review (`d092291..b282a60`) marked SEC-001 REPEATED. `config/jsonlog.py:23` emits `record.getMessage()` unchanged, and `django.security` is routed through that formatter (`config/settings.py:118`). Django's CSRF rejection message embeds the full rejected Referer (query string included), so a bad-Referer POST writes attacker-controlled text (e.g. `?token=...`) into the logs. That contradicts the sanitised-logging contract in `docs/SECURITY.md:13` and the module's own docstring. I confirmed the code path; Astra reproduced it with a real HTTPS request. Other `django.security.*` loggers (e.g. `DisallowedHost`) echo user input the same way, so the fix covers the whole family.

Per AGENTS.md a repeated finding needs manual Astra Medium escalation. The user has chosen to fix it here with Claude (learning track), then re-run the independent review. This is a self-implemented fix, not an Astra Low fix; record it as such.

## Change 1: the fix (`src/config/jsonlog.py`)
In `JsonFormatter.format`, when `record.name` starts with `django.security`:
- set `payload["message"]` to a fixed string, `"Django security rejection"`;
- add `payload["status"] = record.status_code` when Django attached one (`log_response` sets `extra={"status_code": ..., "request": ...}`; confirm in the container against Django 5.2.17);
- keep the existing safe fields: logger name (already says which check, e.g. `django.security.csrf`), `request_id` via the existing `record.request` handling, and exception class/frames.
All other loggers keep `getMessage()` unchanged (`northstar.*` messages are authored by us; the existing test at `tests/test_request_logging.py:181` stays valid). No redaction framework. Update the module docstring to say security-record messages are replaced.

## Change 2: regression tests (`tests/test_request_logging.py`)
Reuse the `logs` fixture and `Captured` helper (its `django.security` logger already gets the handler).
1. HTTPS bad-Referer POST: `Client(enforce_csrf_checks=True)`, `client.post(reverse("accounts:login"), secure=True, HTTP_REFERER="https://untrusted.example/reset?token=REVIEW_SENTINEL")`. Assert 403, a `django.security.csrf` record exists with the fixed message and `status == 403`, and `"REVIEW_SENTINEL" not in logs.raw` (whole capture, not one record).
2. Formatter unit test: a `LogRecord` named `django.security.DisallowedHost` with a sentinel in its args produces the fixed message and no sentinel; a same-shaped record on another logger name still emits its message.

## Change 3: docs
- `docs/SECURITY.md:13`: one clause saying Django security-logger messages are replaced by a fixed event message (they can echo request headers).
- `docs/IMPLEMENTATION_PLAN.md`: record round 2, SEC-001 fixed by the user with Claude and awaiting Astra re-review, the other nine findings resolved and KO-1 accepted. Also correct the stale "review pending" lines. The round-2 review log under `docs/reviews/` is written by the coordinator, not by me.

## Separate step: test trims (user selected "test trims only")
Own commit, after the fix is verified; touches only `tests/test_security_negative.py`:
- remove `"١٢"` from `BAD_QUANTITIES` (line 227; Python parses it as 12, so it tests stock, not ASCII validation);
- trim the eleven quantity strings to representative missing/non-numeric/negative/zero/decimal/boundary cases;
- reduce the CSRF matrix (`no_token`/`wrong_header`/`wrong_form_field` x normal/htmx x every route) to representative variants, keeping every mutation route and its valid-token positive control.
Ownership, price and forged-field tests are untouched. Upper-bound test: use stock above 999 so the 999 guard is what is isolated.

## Verification
Targeted only, via Docker Compose web/db, per CLAUDE.md:
- `pytest tests/test_request_logging.py`, then `tests/test_security_negative.py` after the trims;
- `manage.py check`; `makemigrations --check --dry-run` (expected no changes; no models touched);
- confirm the new bad-Referer test fails against the old formatter (temporarily revert change 1) so it proves the fix.
The full suite is not rerun unless asked; Astra's 429-test run covered `b282a60`.

## Not done
No commit or push (only on request). No Astra review is claimed; the fix needs a Round 3 independent review.
