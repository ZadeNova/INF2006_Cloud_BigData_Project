"""Opt-in destructive fixtures only on a dedicated disposable PostgreSQL server."""
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest
from tools.db_bootstrap import bootstrap
from config import database as database_config


@pytest.fixture
def roles():
    dsn = os.environ.get("BOOTSTRAP_TEST_DSN")
    if not dsn:
        pytest.skip("requires explicit disposable BOOTSTRAP_TEST_DSN")
    suffix = uuid4().hex[:10]
    names = ["test_" + item + suffix for item in ("master_", "owner_", "runtime_", "db_")]
    master, owner, runtime, database = names
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE ROLE {} LOGIN CREATEROLE CREATEDB PASSWORD 'fixture-only'").format(sql.Identifier(master)))
        info = admin.info
        env = {"DJANGO_ENV": "local", "POSTGRES_HOST": info.host, "POSTGRES_PORT": str(info.port),
               "POSTGRES_DB": database, "POSTGRES_USER": runtime, "POSTGRES_PASSWORD": "runtime-only",
               "MIGRATION_USER": owner, "MIGRATION_PASSWORD": "migration-only",
               "BOOTSTRAP_USER": master, "BOOTSTRAP_PASSWORD": "fixture-only"}
        try:
            yield admin, env
        finally:
            admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(database)))
            for name in (runtime, owner, master):
                admin.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(name)))


def test_non_superuser_bootstrap_migrations_runtime_and_rerun(roles):
    admin, env = roles
    bootstrap(env)
    bootstrap(env)
    app_root = Path(database_config.__file__).resolve().parents[1]
    process_env = {**os.environ, **env, "PYTHONPATH": str(app_root),
                   "DJANGO_SECRET_KEY": "test-only-" * 8, "DJANGO_ALLOWED_HOSTS": "localhost",
                   "POSTGRES_USER": env["MIGRATION_USER"], "POSTGRES_PASSWORD": env["MIGRATION_PASSWORD"]}
    result = subprocess.run([sys.executable, str(app_root / "manage.py"), "migrate", "--noinput"],
                            env=process_env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    # Grants configured before migration must apply to its tables/sequences and trigger-bearing tables.
    runtime_env = {**process_env, "POSTGRES_USER": env["POSTGRES_USER"], "POSTGRES_PASSWORD": env["POSTGRES_PASSWORD"]}
    code = """import django; django.setup()
from django.core.management import call_command
from django.contrib.auth import get_user_model
from catalogue.models import Product
from django.db import connection
u = get_user_model().objects.create_user(username='runtime-check')
u.first_name='Updated'; u.save(); u.delete()
p = Product.objects.create(namespace='fixture', external_id='1', name='Test', category='Test',
                           price='2.00', cost='1.00', stock=2, lead_time_days=1)
p.stock=1; p.save(); p.delete()
call_command('check_database')
with connection.cursor() as c:
 c.execute('SELECT count(*) FROM orders_order')
 c.execute('SELECT count(*) FROM reporting_analyticsrun')
"""
    result = subprocess.run([sys.executable, "-c", code], env={**runtime_env, "DJANGO_SETTINGS_MODULE": "config.settings"}, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    with psycopg.connect(host=env["POSTGRES_HOST"], port=env["POSTGRES_PORT"], dbname=env["POSTGRES_DB"],
                         user=env["POSTGRES_USER"], password=env["POSTGRES_PASSWORD"], autocommit=True) as runtime:
        for statement in ("CREATE TABLE public.forbidden (id integer)", "CREATE TEMP TABLE forbidden (id integer)",
                          sql.SQL("SET ROLE {}").format(sql.Identifier(env["MIGRATION_USER"])),
                          "ALTER TABLE auth_user ADD COLUMN forbidden integer"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                runtime.execute(statement)
    row = admin.execute("SELECT pg_has_role(%s, %s, 'SET'), pg_has_role(%s, %s, 'USAGE')",
        (env["BOOTSTRAP_USER"], env["MIGRATION_USER"], env["BOOTSTRAP_USER"], env["MIGRATION_USER"])).fetchone()
    assert row == (False, False)
    bootstrap(env)


@pytest.mark.parametrize("unsafe", ["membership", "ownership", "schema_create", "admin", "explicit_temp"])
def test_preflight_rejects_unsafe_state_before_password_change(roles, unsafe):
    admin, env = roles
    bootstrap(env)
    role = sql.Identifier(env["POSTGRES_USER"])
    if unsafe == "membership":
        admin.execute(sql.SQL("GRANT pg_read_all_data TO {}").format(role))
    elif unsafe == "ownership":
        admin.execute(sql.SQL("ALTER DATABASE {} OWNER TO {}").format(sql.Identifier(env["POSTGRES_DB"]), role))
    elif unsafe == "explicit_temp":
        admin.execute(sql.SQL("GRANT TEMPORARY ON DATABASE {} TO {}").format(sql.Identifier(env["POSTGRES_DB"]), role))
    elif unsafe == "admin":
        admin.execute(sql.SQL("ALTER ROLE {} CREATEDB").format(role))
    else:
        with psycopg.connect(os.environ["BOOTSTRAP_TEST_DSN"], dbname=env["POSTGRES_DB"], autocommit=True) as target:
            target.execute(sql.SQL("GRANT CREATE ON SCHEMA public TO {}").format(role))
    before = admin.execute("SELECT rolpassword FROM pg_authid WHERE rolname IN (%s,%s) ORDER BY rolname",
                           (env["POSTGRES_USER"], env["MIGRATION_USER"])).fetchall()
    with pytest.raises(ValueError):
        bootstrap({**env, "POSTGRES_PASSWORD": "changed", "MIGRATION_PASSWORD": "changed"})
    assert admin.execute("SELECT rolpassword FROM pg_authid WHERE rolname IN (%s,%s) ORDER BY rolname",
                        (env["POSTGRES_USER"], env["MIGRATION_USER"])).fetchall() == before


def test_bootstrap_error_is_redacted(monkeypatch, capsys):
    from tools import db_bootstrap
    def fail():
        raise psycopg.OperationalError("private-password connection details")
    monkeypatch.setattr(db_bootstrap, "bootstrap", fail)
    assert db_bootstrap.main() == 1
    output = capsys.readouterr()
    assert "private-password" not in output.err and not output.out


def test_excessive_defaults_are_refused_before_passwords_and_future_table(roles):
    admin, env = roles
    bootstrap(env)
    before = admin.execute("SELECT rolpassword FROM pg_authid WHERE rolname IN (%s,%s) ORDER BY rolname",
                           (env["POSTGRES_USER"], env["MIGRATION_USER"])).fetchall()
    with psycopg.connect(host=env["POSTGRES_HOST"], port=env["POSTGRES_PORT"], dbname=env["POSTGRES_DB"],
                         user=env["MIGRATION_USER"], password=env["MIGRATION_PASSWORD"], autocommit=True) as owner:
        # Global role and per-schema PUBLIC defaults are independently additive sources.
        for scope, recipient in ((sql.SQL(""), sql.Identifier(env["POSTGRES_USER"])),
                                 (sql.SQL("IN SCHEMA public"), sql.SQL("PUBLIC"))):
            owner.execute(sql.SQL("ALTER DEFAULT PRIVILEGES {} GRANT TRUNCATE ON TABLES TO {}").format(scope, recipient))
            with pytest.raises(ValueError, match="default privileges"):
                bootstrap({**env, "POSTGRES_PASSWORD": "changed", "MIGRATION_PASSWORD": "changed"})
            assert admin.execute("SELECT rolpassword FROM pg_authid WHERE rolname IN (%s,%s) ORDER BY rolname",
                                 (env["POSTGRES_USER"], env["MIGRATION_USER"])).fetchall() == before
            owner.execute("CREATE TABLE public.future_table (id integer)")
            assert owner.execute("SELECT has_table_privilege(%s, 'public.future_table', 'TRUNCATE')",
                                 (env["POSTGRES_USER"],)).fetchone() == (True,)
            owner.execute("DROP TABLE public.future_table")
            owner.execute(sql.SQL("ALTER DEFAULT PRIVILEGES {} REVOKE TRUNCATE ON TABLES FROM {}").format(scope, recipient))
        bootstrap(env)
        owner.execute("CREATE TABLE public.future_table (id integer)")
        assert owner.execute("SELECT has_table_privilege(%s, 'public.future_table', 'TRUNCATE')",
                             (env["POSTGRES_USER"],)).fetchone() == (False,)


def test_existing_sequence_update_is_refused_before_password_changes(roles):
    admin, env = roles
    bootstrap(env)
    before = admin.execute("SELECT rolpassword FROM pg_authid WHERE rolname IN (%s,%s) ORDER BY rolname",
                           (env["POSTGRES_USER"], env["MIGRATION_USER"])).fetchall()
    with psycopg.connect(host=env["POSTGRES_HOST"], port=env["POSTGRES_PORT"], dbname=env["POSTGRES_DB"],
                         user=env["MIGRATION_USER"], password=env["MIGRATION_PASSWORD"], autocommit=True) as owner:
        owner.execute("CREATE SEQUENCE public.existing_sequence")
        # PUBLIC exercises effective privilege lookup rather than just inspecting the runtime ACL entry.
        owner.execute("GRANT UPDATE ON SEQUENCE public.existing_sequence TO PUBLIC")
        with pytest.raises(ValueError, match="sequence privileges"):
            bootstrap({**env, "POSTGRES_PASSWORD": "changed", "MIGRATION_PASSWORD": "changed"})
        assert admin.execute("SELECT rolpassword FROM pg_authid WHERE rolname IN (%s,%s) ORDER BY rolname",
                             (env["POSTGRES_USER"], env["MIGRATION_USER"])).fetchall() == before
