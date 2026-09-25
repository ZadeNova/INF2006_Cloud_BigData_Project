"""Create the application role and database once, with the RDS master credentials. Safe to rerun.

The AWS counterpart of docker/10-local-role.sh. Run it from a one-off container of the app image; the web
containers never receive BOOTSTRAP_USER/BOOTSTRAP_PASSWORD. Nothing secret is printed.
"""
import os
import sys

import psycopg
from psycopg import sql


def env(name, default=None):
    value = os.environ.get(name, default or "")
    if not value or value.startswith("replace-"):
        sys.exit(f"{name} must be set to a non-placeholder value")
    return value


def main():
    app_user, app_password, app_db = env("POSTGRES_USER"), env("POSTGRES_PASSWORD"), env("POSTGRES_DB")
    master = env("BOOTSTRAP_USER")
    if app_user == master:
        sys.exit("POSTGRES_USER must differ from BOOTSTRAP_USER; the app must not run as the master user")
    tls = {"sslmode": env("BOOTSTRAP_SSLMODE", "verify-full")}
    if tls["sslmode"] == "verify-full":
        tls["sslrootcert"] = env("POSTGRES_SSLROOTCERT")
    # CREATE DATABASE cannot run inside a transaction block.
    with psycopg.connect(host=env("POSTGRES_HOST"), port=env("POSTGRES_PORT", "5432"), dbname="postgres",
            user=master, password=env("BOOTSTRAP_PASSWORD"), connect_timeout=10, autocommit=True, **tls) as conn:
        role, database, password = sql.Identifier(app_user), sql.Identifier(app_db), sql.Literal(app_password)
        existing = conn.execute("SELECT rolsuper OR rolcreaterole OR rolcreatedb OR rolreplication OR rolbypassrls"
            " FROM pg_roles WHERE rolname = %s", (app_user,)).fetchone()
        if existing and existing[0]:
            sys.exit(f"Role {app_user} already exists with administrative rights; refusing to use it for the application")
        if existing:
            # Only the password: RDS's master is not a superuser, so it may not restate SUPERUSER attributes.
            conn.execute(sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {}").format(role, password))
            print(f"Role {app_user} exists; password updated.")
        else:
            conn.execute(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB PASSWORD {}")
                .format(role, password))
            print(f"Role {app_user} created.")
        # PostgreSQL 16+: a non-superuser may give a database to another role only if it can SET ROLE to it.
        conn.execute(sql.SQL("GRANT {} TO CURRENT_USER").format(role))
        owner = conn.execute("SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = %s", (app_db,)).fetchone()
        if owner is None:
            conn.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(database, role))
            print(f"Database {app_db} created, owned by {app_user}.")
        elif owner[0] != app_user:
            # e.g. created by the RDS console's "Initial database name", owned by the master. The public schema
            # follows the database owner on PostgreSQL 15+, so without this the app cannot migrate.
            conn.execute(sql.SQL("ALTER DATABASE {} OWNER TO {}").format(database, role))
            print(f"Database {app_db} existed, owned by {owner[0]}; ownership moved to {app_user}.")
        else:
            print(f"Database {app_db} exists, owned by {app_user}.")


if __name__ == "__main__":
    main()
