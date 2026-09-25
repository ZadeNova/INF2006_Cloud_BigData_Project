"""One connection policy for Django and offline PostgreSQL tools (no Django import)."""
import os
import ssl
from psycopg import ProgrammingError
from psycopg.conninfo import conninfo_to_dict


def connection_parameters(database_url=None, *, environ=None):
    env = os.environ if environ is None else environ
    mode = env.get("DJANGO_ENV", "production")
    if mode not in {"local", "production"}:
        raise ValueError("DJANGO_ENV must be local or production")
    if database_url:
        try:
            params = conninfo_to_dict(database_url)
        except ProgrammingError:
            raise ValueError("Invalid PostgreSQL connection string") from None
        if set(params) - {"dbname", "user", "password", "host", "port", "sslmode", "sslrootcert"}:
            raise ValueError("Unsupported PostgreSQL connection string option")
    else:
        params = {key: env.get(name, "") for key, name in (
            ("dbname", "POSTGRES_DB"), ("user", "POSTGRES_USER"),
            ("password", "POSTGRES_PASSWORD"), ("host", "POSTGRES_HOST"))}
        params["port"] = env.get("POSTGRES_PORT", "5432")
    for key in ("dbname", "user", "password", "host"):
        if not params.get(key) or params[key].startswith("replace-"):
            raise ValueError("Missing PostgreSQL connection configuration")
    requested_tls = params.get("sslmode", env.get("POSTGRES_SSLMODE"))
    if mode == "production":
        if requested_tls not in (None, "verify-full"):
            raise ValueError("Production PostgreSQL requires verify-full TLS")
        if any(env.get(key) for key in ("PGSERVICE", "PGSERVICEFILE", "PGHOSTADDR")):
            raise ValueError("Implicit PostgreSQL service/address configuration is forbidden")
        host = params["host"]
        if not host or host.startswith("@") or any(char in host for char in "/, "):
            raise ValueError("Production PostgreSQL requires one explicit hostname")
        ca = params.get("sslrootcert", env.get("POSTGRES_SSLROOTCERT", ""))
        try:
            if not ca:
                raise ValueError()
            ssl.create_default_context(cafile=ca)
        except (OSError, ValueError, ssl.SSLError):
            raise ValueError("POSTGRES_SSLROOTCERT must identify a readable CA bundle") from None
        params.update(sslmode="verify-full", sslrootcert=ca, gssencmode="disable")
    else:
        params["sslmode"] = requested_tls or "disable"
        if env.get("POSTGRES_SSLROOTCERT") and "sslrootcert" not in params:
            params["sslrootcert"] = env["POSTGRES_SSLROOTCERT"]
    params["connect_timeout"] = 10
    return params
