"""Configuration failures must be visible before serving requests."""
import os
import ssl
import subprocess
import sys

import pytest
from django.conf import settings

@pytest.mark.parametrize("changes, message", [
    ({"DJANGO_SECRET_KEY": ""}, "DJANGO_SECRET_KEY"),
    ({"DJANGO_SECRET_KEY": "short"}, "at least 50"),
    ({"DJANGO_ALLOWED_HOSTS": "*"}, "Explicit allowed hosts"),
    ({"DJANGO_ENV": "staging"}, "DJANGO_ENV"),
    ({"DJANGO_DEBUG": "yes"}, "true or false"),
    ({"DJANGO_ENV": "production", "DJANGO_DEBUG": "true"}, "DEBUG is forbidden"),
    ({"DJANGO_HSTS_SECONDS": "-1"}, "DJANGO_HSTS_SECONDS"),
])
def test_invalid_configuration_fails(changes, message):
    result = subprocess.run([sys.executable, "-c", "import config.settings"],
        env={**os.environ, **changes}, capture_output=True, text=True)
    assert result.returncode != 0
    assert message in result.stderr

def test_production_configuration():
    code = """from config import settings as s
assert not s.DEBUG
assert s.SESSION_COOKIE_SECURE and s.CSRF_COOKIE_SECURE
assert s.SECURE_SSL_REDIRECT
assert s.SECURE_HSTS_SECONDS == 3600
assert s.DATABASES['default']['OPTIONS']['sslmode'] == 'verify-full'
assert not hasattr(s, 'SECURE_PROXY_SSL_HEADER')
"""
    result = subprocess.run([sys.executable, "-c", code], env={**os.environ,
        "DJANGO_ENV": "production", "DJANGO_DEBUG": "false",
        "DJANGO_TRUST_PROXY": "false", "POSTGRES_SSLROOTCERT": os.environ["POSTGRES_SSLROOTCERT"]},
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

def test_image_carries_a_loadable_rds_certificate_bundle():
    # The Dockerfile's default path, which production verify-full TLS reads.
    ssl.create_default_context(cafile=os.environ["POSTGRES_SSLROOTCERT"])

def test_shared_session_configuration():
    assert settings.SESSION_ENGINE == "django.contrib.sessions.backends.db"
    assert settings.SESSION_COOKIE_HTTPONLY
    assert settings.SESSION_COOKIE_SAMESITE == "Lax"

@pytest.mark.django_db
def test_postgresql_connection_uses_non_superuser():
    from django.db import connection
    assert connection.vendor == "postgresql"
    with connection.cursor() as cursor:
        cursor.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
        assert cursor.fetchone() == (False,)
