"""Both standalone DB entrypoints use Secrets Manager before connecting in production."""
import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest
from config import secrets


@pytest.mark.parametrize("filename", ["segment_customers.py", "verify_refresh.py"])
def test_standalone_production_secret_delivery_and_dsn_refusal(monkeypatch, filename):
    spec = importlib.util.spec_from_file_location("startup_target", Path(__file__).resolve().parents[1] / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("DJANGO_ENV", "production")
    monkeypatch.setenv("AWS_SECRET_ID", "fixture-db")
    monkeypatch.setenv("AWS_REGION", "ap-southeast-1")
    payload = {"POSTGRES_DB": "app", "POSTGRES_USER": "reader", "POSTGRES_PASSWORD": "fixture-only", "POSTGRES_HOST": "db.example"}
    monkeypatch.setattr(secrets, "_retrieve", lambda *args: payload)
    monkeypatch.setenv("POSTGRES_SSLROOTCERT", str(Path(module.connection_parameters.__code__.co_filename).resolve().parents[1] / "certs/rds-global-bundle.pem"))
    connector = Mock()
    monkeypatch.setattr(module.psycopg, "connect", connector)
    module.connect()
    assert connector.call_args.kwargs["user"] == "reader"
    assert connector.call_args.kwargs["sslmode"] == "verify-full"
    connector.reset_mock()
    with pytest.raises(ValueError, match="database URLs"):
        module.connect("postgresql://ignored:ignored@localhost/ignored")
    connector.assert_not_called()
