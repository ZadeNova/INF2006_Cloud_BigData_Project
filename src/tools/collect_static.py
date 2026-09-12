"""Build static files without application secrets or database access."""
from pathlib import Path
import django
from django.conf import settings
from django.core.management import call_command

base = Path(__file__).resolve().parents[1]
settings.configure(
    INSTALLED_APPS=["django.contrib.staticfiles"],
    STATIC_URL="/static/", STATIC_ROOT=base / "staticfiles",
    STATICFILES_DIRS=[base / "static"],
    STORAGES={"staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}},
)
django.setup()
call_command("collectstatic", interactive=False, verbosity=0)
