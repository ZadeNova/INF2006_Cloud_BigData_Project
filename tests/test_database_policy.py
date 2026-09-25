"""Production connection policy is shared with Django and standalone tools."""
from pathlib import Path
import pytest
from config import database as database_config
from config.database import connection_parameters

CA = str(Path(database_config.__file__).resolve().parents[1] / "certs/rds-global-bundle.pem")
BASE = {"POSTGRES_DB": "app", "POSTGRES_USER": "runtime", "POSTGRES_PASSWORD": "test-only",
        "POSTGRES_HOST": "db.example", "POSTGRES_SSLROOTCERT": CA}


def test_default_production_policy_and_explicit_local_mode():
    result = connection_parameters(environ=BASE)
    assert result["sslmode"] == "verify-full" and result["gssencmode"] == "disable"
    assert connection_parameters(environ={**BASE, "DJANGO_ENV": "local"})["sslmode"] == "disable"


@pytest.mark.parametrize("change", [
    {"POSTGRES_SSLMODE": "require"}, {"POSTGRES_SSLROOTCERT": "missing.pem"},
    {"POSTGRES_HOST": "/tmp"}, {"PGSERVICE": "unsafe"}, {"DJANGO_ENV": "invalid"},
])
def test_invalid_production_config_is_refused(change):
    with pytest.raises(ValueError):
        connection_parameters(environ={**BASE, **change})


def test_dsn_cannot_bypass_policy_or_inject_unreviewed_options():
    dsn = "postgresql://runtime:test-only@db.example/app"
    assert connection_parameters(dsn, environ=BASE)["sslmode"] == "verify-full"
    for suffix in ("?sslmode=disable", "?hostaddr=127.0.0.1", "?service=other"):
        with pytest.raises(ValueError):
            connection_parameters(dsn + suffix, environ=BASE)
    with pytest.raises(ValueError) as error:
        connection_parameters("password=private invalid", environ=BASE)
    assert "private" not in str(error.value)


def test_production_refuses_abstract_socket_from_environment_and_dsn():
    for dsn in (None, "dbname=app user=runtime password=test-only host=@socket"):
        with pytest.raises(ValueError, match="explicit hostname"):
            connection_parameters(dsn, environ={**BASE, "POSTGRES_HOST": "@socket"})
