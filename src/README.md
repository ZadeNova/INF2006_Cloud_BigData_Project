# src/

Backend foundation is being delivered in reviewed batches. The package skeleton uses config for settings/URLs/WSGI and accounts, catalogue, cart, orders and reporting for domain modules. Django's built-in User is retained; no custom authentication implementation exists yet.

Dependencies use pip with exact direct/transitive pins in requirements.txt. requirements.in is only the input for deliberate lock refreshes. Python 3.13 Linux is the container runtime. See ../evidence/foundation-batch-1.md for the actual initial resolver check. Docker application startup, environment configuration, migrations and health verification follow in separate batches; no runnable quickstart is claimed yet.

Frontend-owned paths are templates/ and static/. They are intentionally empty; Luna Max owns presentation/HTMX. Backend route and form contracts remain in ../docs/API.md. Authentication and catalogue/cart are separate follow-up tasks.
