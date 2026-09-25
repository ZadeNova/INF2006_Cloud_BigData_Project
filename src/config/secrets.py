"""Startup-only Secrets Manager delivery; local execution never imports the AWS SDK."""
from functools import lru_cache
import json
import os

DB_FIELDS = frozenset({"POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST"})
APP_FIELDS = DB_FIELDS | {"DJANGO_SECRET_KEY"}
BOOTSTRAP_FIELDS = DB_FIELDS | {"MIGRATION_USER", "MIGRATION_PASSWORD", "BOOTSTRAP_USER", "BOOTSTRAP_PASSWORD"}


@lru_cache(maxsize=1)
def _retrieve(secret_id, region):
    try:
        import boto3
        from botocore.config import Config
        session = boto3.Session(region_name=region)
        credentials = session.get_credentials()
        if credentials is None or credentials.method not in {
                "iam-role", "container-role", "assume-role", "assume-role-with-web-identity"}:
            raise ValueError("Role credentials required")
        client = session.client("secretsmanager", config=Config(
            connect_timeout=3, read_timeout=5, retries={"mode": "standard", "total_max_attempts": 2},
            ignore_configured_endpoint_urls=True))
        try:
            response = client.get_secret_value(SecretId=secret_id)
        finally:
            client.close()
        value = json.loads(response["SecretString"])
        if not isinstance(value, dict):
            raise ValueError("Object required")
        return value
    except Exception:
        # SDK and parser exceptions can contain endpoints, credentials and secret payload fragments.
        raise ValueError("Production secret retrieval failed") from None


def load_environment(required_fields, *, environ=None):
    env = dict(os.environ if environ is None else environ)
    mode = env.get("DJANGO_ENV", "production")
    if mode == "local":
        return env
    if mode != "production":
        raise ValueError("DJANGO_ENV must be local or production")
    secret_id, region = env.get("AWS_SECRET_ID", ""), env.get("AWS_REGION", "")
    if not secret_id or not region or secret_id.startswith("replace-"):
        raise ValueError("AWS_SECRET_ID and AWS_REGION are required in production")
    secret = _retrieve(secret_id, region)
    if not required_fields <= secret.keys() or secret.keys() - (required_fields | {"POSTGRES_PORT"}):
        raise ValueError("Production secret fields do not match this entrypoint")
    if any(not isinstance(value, str) or not value or value.startswith("replace-") for value in secret.values()):
        raise ValueError("Production secret fields must be non-placeholder strings")
    return {**env, **secret}
