"""All secret retrieval is fake; these checks never contact AWS."""
import builtins
import json
import traceback
from types import SimpleNamespace

import pytest
from config import secrets

DB = {"POSTGRES_DB": "app", "POSTGRES_USER": "runtime", "POSTGRES_PASSWORD": "fixture-password", "POSTGRES_HOST": "db.example"}
ENV = {"DJANGO_ENV": "production", "AWS_SECRET_ID": "fixture-secret", "AWS_REGION": "ap-southeast-1"}


@pytest.fixture(autouse=True)
def reset_cache():
    secrets._retrieve.cache_clear()
    yield
    secrets._retrieve.cache_clear()


def fake_sdk(monkeypatch, payload, method="iam-role"):
    import boto3
    calls = []
    class Client:
        def get_secret_value(self, **kwargs):
            calls.append(kwargs)
            if isinstance(payload, Exception):
                raise payload
            return {"SecretString": json.dumps(payload)}
        def close(self):
            pass
    class Session:
        def __init__(self, **kwargs):
            assert kwargs == {"region_name": ENV["AWS_REGION"]}
        def get_credentials(self):
            return SimpleNamespace(method=method)
        def client(self, service, config):
            assert service == "secretsmanager"
            assert config.ignore_configured_endpoint_urls and config.read_timeout == 5
            return Client()
    monkeypatch.setattr(boto3, "Session", Session)
    return calls


def test_production_retrieves_once_and_overrides_plaintext_credentials(monkeypatch):
    calls = fake_sdk(monkeypatch, DB)
    env = {**ENV, "POSTGRES_PASSWORD": "ignored-plaintext"}
    assert secrets.load_environment(secrets.DB_FIELDS, environ=env)["POSTGRES_PASSWORD"] == DB["POSTGRES_PASSWORD"]
    assert secrets.load_environment(secrets.DB_FIELDS, environ=env)["POSTGRES_USER"] == "runtime"
    assert calls == [{"SecretId": "fixture-secret"}]


def test_local_never_imports_or_calls_aws(monkeypatch):
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        assert not name.startswith(("boto3", "botocore"))
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)
    env = {"DJANGO_ENV": "local", **DB}
    assert secrets.load_environment(secrets.DB_FIELDS, environ=env) == env


def test_missing_production_selection_cannot_fall_back_to_plaintext():
    with pytest.raises(ValueError, match="AWS_SECRET_ID"):
        secrets.load_environment(secrets.DB_FIELDS, environ=DB)


@pytest.mark.parametrize("payload", [
    {**DB, "BOOTSTRAP_PASSWORD": "forbidden"}, {**DB, "POSTGRES_PASSWORD": ""},
    {key: value for key, value in DB.items() if key != "POSTGRES_USER"},
])
def test_incomplete_or_wrong_secret_schema_is_refused(monkeypatch, payload):
    fake_sdk(monkeypatch, payload)
    with pytest.raises(ValueError, match="Production secret fields"):
        secrets.load_environment(secrets.DB_FIELDS, environ=ENV)


def test_sdk_error_is_redacted_with_cause_suppressed(monkeypatch):
    fake_sdk(monkeypatch, RuntimeError("private-secret-content"))
    with pytest.raises(ValueError) as caught:
        secrets.load_environment(secrets.DB_FIELDS, environ=ENV)
    assert "private-secret-content" not in "".join(traceback.format_exception(caught.value))


def test_static_sdk_credentials_are_rejected(monkeypatch):
    calls = fake_sdk(monkeypatch, DB, method="env")
    with pytest.raises(ValueError, match="retrieval failed"):
        secrets.load_environment(secrets.DB_FIELDS, environ=ENV)
    assert calls == []


def test_bootstrap_loads_its_privileged_schema_before_connection(monkeypatch):
    from tools import db_bootstrap
    payload = {**DB, "MIGRATION_USER": "owner", "MIGRATION_PASSWORD": "owner-fixture",
               "BOOTSTRAP_USER": "master", "BOOTSTRAP_PASSWORD": "master-fixture"}
    fake_sdk(monkeypatch, payload)
    class ReachedPolicy(Exception):
        pass
    def policy(*, environ):
        assert all(environ[key] == value for key, value in payload.items())
        raise ReachedPolicy
    monkeypatch.setattr(db_bootstrap, "connection_parameters", policy)
    with pytest.raises(ReachedPolicy):
        db_bootstrap.bootstrap(ENV)
