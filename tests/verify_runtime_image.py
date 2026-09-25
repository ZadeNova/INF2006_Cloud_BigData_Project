"""Manual local image/TLS verification. No AWS calls; use only disposable fixtures."""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import ssl
import subprocess

SENTINELS = (
    ".env", ".env.production", "nested/.env.private", "infrastructure/marker.txt",
    "infra/marker.txt", "terraform/marker.txt", "nested/.terraform/marker.txt",
    "state.tfstate", "nested/state.tfstate.backup", "saved.tfplan", "nested/saved.plan",
    "secret.tfvars", "nested/secret.auto.tfvars.json", "nested/private.key",
    "nested/private.pem", "nested/.aws/credentials",
)
MARKER = b"HARMLESS_RUNTIME_C_SENTINEL"
CA_SHA256 = "e5bb2084ccf45087bda1c9bffdea0eb15ee67f0b91646106e466714f9de3c7e3"


def make_context(destination):
    """Copy tracked source only, then add harmless markers; never copy a real local .env."""
    root = Path(__file__).resolve().parents[1]
    destination.mkdir(parents=True, exist_ok=False)
    names = subprocess.check_output(["git", "ls-files", "-z", "--", "src"], cwd=root).decode().split("\0")
    for name in filter(None, names):
        source = root / name
        target = destination / Path(name).relative_to("src")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for name in SENTINELS:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(MARKER)
    print("Created tracked-source-only context with 16 harmless exclusion markers")


def audit_image():
    root = Path("/app")
    assert os.getuid() == 10001
    assert all(not (root / name).exists() for name in SENTINELS)
    assert all(MARKER not in path.read_bytes() for path in root.rglob("*") if path.is_file())
    assert (root / ".env.example").is_file()
    assert hashlib.sha256((root / "certs/rds-global-bundle.pem").read_bytes()).hexdigest() == CA_SHA256
    ssl.create_default_context(cafile=os.environ["POSTGRES_SSLROOTCERT"])
    assert all(importlib.util.find_spec(name) is None for name in ("numpy", "pandas", "sklearn", "scipy"))
    print("PASS: excluded markers absent; safe example/CA retained; UID10001; no ML dependencies")


def verify_tls(ca_path):
    """Connect only to the disposable localhost server with its one-day test certificate."""
    import psycopg
    from config.database import connection_parameters
    from config import secrets
    payload = {"POSTGRES_DB": "postgres", "POSTGRES_USER": "postgres",
               "POSTGRES_PASSWORD": "disposable-tls-only", "POSTGRES_HOST": "localhost"}
    # Intentionally fake secret retrieval; this tests TLS, never AWS access or deployed credentials.
    secrets._retrieve = lambda *args: payload
    env = {"DJANGO_ENV": "production", "AWS_SECRET_ID": "fake-only", "AWS_REGION": "ap-southeast-1",
           "POSTGRES_SSLROOTCERT": str(ca_path)}
    with psycopg.connect(**connection_parameters(environ=secrets.load_environment(secrets.DB_FIELDS, environ=env))) as conn:
        assert conn.execute("SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()").fetchone() == (True,)
    print("PASS: production policy completed certificate-verified TLS handshake")
    for case in ("wrong-host", "wrong-ca"):
        payload["POSTGRES_HOST"] = "127.0.0.1" if case == "wrong-host" else "localhost"
        config = {**env, "POSTGRES_SSLROOTCERT": "/app/certs/rds-global-bundle.pem"} if case == "wrong-ca" else env
        try:
            with psycopg.connect(**connection_parameters(environ=secrets.load_environment(secrets.DB_FIELDS, environ=config))):
                pass
        except psycopg.OperationalError as error:
            expected = "does not match host name" if case == "wrong-host" else "certificate verify failed"
            if expected not in str(error).lower():
                raise AssertionError(case + " failed for an unexpected reason") from None
            print("PASS: " + case + " rejected for expected certificate validation reason")
        else:
            raise AssertionError(case + " was accepted")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("make-context", "audit-image", "tls"))
    parser.add_argument("path", nargs="?", type=Path)
    args = parser.parse_args()
    if args.action in {"make-context", "tls"} and args.path is None:
        parser.error("this action requires a path")
    if args.action == "make-context":
        make_context(args.path)
    elif args.action == "audit-image":
        audit_image()
    else:
        verify_tls(args.path)
