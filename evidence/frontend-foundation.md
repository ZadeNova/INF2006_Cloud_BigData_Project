# Frontend foundation verification

12 September 2026. Frontend task starting commit: `d081007` (the first frontend foundation checkpoint). Local implementation checkpoints: `d081007` (shared shell and representative page), `e3800c3` (responsive components and HTMX preview), and `ffbe975` (message and branded 404 states). This task remains local-only; no AWS resources were provisioned and no push was performed.

## Scope and changed paths

The complete frontend task diff from `d081007` through `ffbe975` covers the shared editor/runtime setup and frontend presentation paths: `.vscode/settings.json`, `docs/API.md`, `docs/IMPLEMENTATION_PLAN.md`, `src/README.md`, `src/config/urls.py`, `src/config/views.py`, `src/static/css/site.css`, `src/static/js/site.js`, `src/templates/404.html`, `src/templates/base.html`, `src/templates/foundation/_design-notes.html`, `src/templates/foundation/home.html`, and `tests/test_frontend.py`.

Business routes remain reserved. The live presentation routes are `/`, `/foundation/design-notes/` and the branded Django 404 handler. `/health/` remains the existing backend liveness contract.

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

Actual results: Compose validation and image builds passed; Django system check reported no issues; focused frontend tests passed `4 passed in 0.20s`; the full suite passed `52 passed in 2.79s`. The full result includes the 48-test backend foundation baseline plus four frontend tests. The host editor environment also passed:

```powershell
.venv\Scripts\python.exe -c "import django; from django.http import JsonResponse; from django.shortcuts import render; from django.views.decorators.http import require_safe; print(django.get_version())"
```

Actual result: `5.2.17`.

## HTTP verification

Against the running Gunicorn service at `http://127.0.0.1:8000/`:

- `GET /` returned `200 text/html`, with the shared template and hashed WhiteNoise CSS.
- `GET /foundation/design-notes/` returned `200 text/html` and the expected presentation fragment.
- `GET /not-a-live-route/` returned `404 text/html` and rendered `404.html` with the shared shell and error message.
- `GET /health/` returned the unchanged `200 application/json` body `{"status": "ok"}` with `Cache-Control: no-store`.

## Browser verification

Browser verification used the Codex in-app browser against the running Django application, after the final image rebuild:

- Desktop viewport `1440x900`: navigation visible, menu toggle hidden, 99px header, two-column hero, three-column state grid, and corrected dark-outline hero action.
- Mobile viewport `390x844`: navigation hidden until the Menu button is activated, hero/state content collapses to one column, actions meet the mobile touch size, and the mobile screenshot shows the corrected green-outline action.
- Keyboard: activating Menu with Enter exposed the navigation and focused Overview; Escape closed it and restored focus to the menu button.
- HTMX: activating “Load design notes” kept the URL at `/`, replaced `#design-note` with the Django fragment, moved focus to the new heading, and produced no browser console errors.
- Error state: the live missing route displayed the branded 404 page with a valid return link to `/`.

Desktop and mobile captures were emitted inline from the browser verification in this task at the stated viewports. The in-app browser capture API does not return a local filesystem path for its screenshot bytes; the verification record is preserved here and the live preview tab is left available for review.

## Review gate

Independent Astra Medium review: pending. The final reviewer must inspect the complete diff from `d081007` through `ffbe975` read-only against `DESIGN.md`, `docs/FRONTEND.md`, `docs/API.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY.md`, and the actual verification above. Findings and re-review outcome belong in `docs/reviews/frontend-foundation.md` before the frontend foundation is marked complete.
