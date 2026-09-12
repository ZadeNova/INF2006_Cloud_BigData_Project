# Frontend foundation verification

12 September 2026. Frontend task starting commit: `51e4ec1` (the backend foundation handover immediately before frontend work). Local implementation checkpoints: `d081007` (shared shell and representative page), `e3800c3` (responsive components and HTMX preview), `ffbe975` (message and branded 404 states), and `c59b162` (review remediation). The complete frontend task diff is `51e4ec1..c59b162`. This task remains local-only; no AWS resources were provisioned and no push was performed.

## Scope and changed paths

The complete frontend task diff from `51e4ec1` through `c59b162` covers the shared editor/runtime setup and frontend presentation paths: `.vscode/settings.json`, `docs/API.md`, `docs/IMPLEMENTATION_PLAN.md`, `src/README.md`, `src/config/urls.py`, `src/config/views.py`, `src/static/css/site.css`, `src/static/js/site.js`, `src/templates/404.html`, `src/templates/base.html`, `src/templates/foundation/_design-notes.html`, `src/templates/foundation/_design-notes-unavailable.html`, `src/templates/foundation/home.html`, `tests/test_frontend.py`, this evidence record and the review record in `docs/reviews/frontend-foundation.md`.

Business routes remain reserved. The live presentation routes are `/`, `/foundation/design-notes/`, the presentation-only 503 preview at `/foundation/design-notes-unavailable/` and the branded Django 404 handler. `/health/` remains the existing backend liveness contract.

## Automated checks

Commands were run from the repository root using Docker Desktop Linux containers:

```powershell
docker compose -f src/compose.yaml config --quiet
docker compose -f src/compose.yaml build
docker compose -f src/compose.yaml up -d --wait --wait-timeout 60 web
docker compose -f src/compose.yaml run --rm web python manage.py check
docker compose -f src/compose.yaml run --rm web pytest -q -p no:cacheprovider /app/tests/test_frontend.py
docker compose -f src/compose.yaml run --rm web pytest -q -p no:cacheprovider /app/tests
```

Actual results after the review remediation: Compose validation and image builds passed; Django system check reported no issues; focused frontend tests passed `5 passed in 0.23s`; the full suite passed `53 passed in 2.76s`. The full result includes the 48-test backend foundation baseline plus five frontend tests. The host editor environment also passed:

```powershell
.venv\Scripts\python.exe -c "import django; from django.http import JsonResponse; from django.shortcuts import render; from django.views.decorators.http import require_safe; print(django.get_version())"
```

Actual result: `5.2.17`.

## HTTP verification

Against the running Gunicorn service at `http://127.0.0.1:8000/`:

- `GET /` returned `200 text/html`, with the shared template and hashed WhiteNoise CSS.
- `GET /foundation/design-notes/` returned `200 text/html` and the expected presentation fragment.
- `GET /foundation/design-notes-unavailable/` returned the intentional `503 text/html` presentation failure fragment.
- `GET /not-a-live-route/` returned `404 text/html` and rendered `404.html` with the shared shell and error message.
- `GET /health/` returned the unchanged `200 application/json` body `{"status": "ok"}` with `Cache-Control: no-store`.

## Browser verification

Browser verification used the Codex in-app browser against the running Django application, after the remediation image rebuild:

- Desktop viewport `1440x900`: navigation visible, menu toggle hidden, 99px header, two-column hero, three-column state grid, and corrected dark-outline hero action.
- Mobile viewport `390x844`: navigation hidden until the Menu button is activated, hero/state content collapses to one column, and measured Menu/System status controls are `44px` high; the mobile screenshot shows the corrected green-outline action.
- Keyboard: activating Menu with Enter exposed the navigation and focused Overview; Escape closed it and restored focus to the menu button.
- Validation: the live page exposed the invalid email sample with `aria-invalid="true"`, an associated error element and presentation-only wording.
- HTMX success: activating “Load design notes” kept the URL on the preview page, replaced `#design-note` with the Django fragment, moved focus to the new heading and applied a computed `solid` `2.4px` focus outline.
- HTMX failure/retry: activating “Preview failure state” made the actual 503 request, produced `role="alert"`/assertive live feedback, focused the error heading and changed the action to “Retry design notes”; retry restored the success fragment, `role="status"`/polite live feedback and focus. The browser recorded the expected HTMX response-status console entry for the deliberate 503; no JavaScript exception was observed.
- Error state: the live missing route displayed the branded 404 page with a valid return link to `/`.

Desktop and mobile captures were emitted inline from the browser verification in this task at the stated viewports. The in-app browser capture API does not return a local filesystem path for its screenshot bytes; the verification record is preserved here and the live preview tab is left available for review.

## Review gate

Round 1 independent Astra Medium review identified F-001 through F-005. The remediation is implemented in `c59b162` and verified above; the same reviewer must re-review the complete corrected diff from `51e4ec1` through `c59b162` read-only against `DESIGN.md`, `docs/FRONTEND.md`, `docs/API.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY.md`, and the actual verification above. The review log and Round 2 outcome belong in `docs/reviews/frontend-foundation.md` before the frontend foundation is marked complete.
