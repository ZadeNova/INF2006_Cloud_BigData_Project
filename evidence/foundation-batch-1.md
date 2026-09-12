# Foundation batch 1: package skeleton and dependencies

12 September 2026. Scope: manage.py, config package/WSGI entry point, logical app package markers, empty template/static directories, .gitignore and requirements.in/requirements.txt. Configuration, models and routes drafted before batching are excluded and remain unverified until their batches.

Dependency workflow: pip installs src/requirements.txt, which locks direct and transitive versions. requirements.in records the intentional release ranges used to refresh the lock; ordinary builds do not resolve those ranges. Runtime: Python 3.13.15, Linux amd64, from python:3.13-slim-bookworm@sha256:ed86c82274b3c69b52fb5820f358f0bd7df0b603332063cb5c6e32bd220c3e6e. Django 5.2 is the selected LTS series (https://docs.djangoproject.com/en/5.2/releases/5.2/).

Actual resolver check: an ephemeral Docker container mounted src at /work and ran:

```sh
python -m pip install -r requirements.in
python -m pip freeze > requirements.txt
python -m pip check
python -m django --version
python --version
```

Exit 0; no broken requirements; Django 5.2.17; Python 3.13.15. No application/database startup claimed in this batch. The Docker engine used was Desktop 4.78.0 / Engine 29.5.3. Authentication, catalogue/cart execution, import, frontend and AWS remain unimplemented.

Fresh exact-lock replay also passed in a new container: python -m pip install -q -r requirements.txt; python -m pip check; python -m django --version. Entry-point AST parsing passed for manage.py/config/wsgi.py. git diff --cached --check passed after normalizing endings.
