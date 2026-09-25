"""Provision separate schema-owner and runtime roles; never run on an ASG boot."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from config.database import connection_parameters
from config.secrets import BOOTSTRAP_FIELDS, load_environment


def required(env, name):
    value = env.get(name, "")
    if not value or value.startswith("replace-"):
        raise ValueError(f"{name} must be set to a non-placeholder value")
    return value


def check_role(conn, name):
    row = conn.execute("""SELECT oid, rolsuper OR rolcreaterole OR rolcreatedb
        OR rolreplication OR rolbypassrls FROM pg_roles WHERE rolname = %s""", (name,)).fetchone()
    if row and (row[1] or conn.execute(
            "SELECT 1 FROM pg_auth_members WHERE member = %s LIMIT 1", (row[0],)).fetchone()):
        raise ValueError("Application roles must have no administrative attributes or memberships")
    return row


def check_database(conn, runtime, migration):
    if conn.execute("""SELECT 1 FROM pg_database d, aclexplode(d.datacl) acl
            WHERE d.datname = current_database()
            AND acl.grantee = (SELECT oid FROM pg_roles WHERE rolname = %s)
            AND acl.privilege_type = 'TEMPORARY' LIMIT 1""", (runtime,)).fetchone():
        raise ValueError("Runtime role has an explicit temporary-object grant")
    # Global defaults and public-schema defaults are additive; inspect both before changing credentials.
    if conn.execute("""SELECT 1 FROM pg_default_acl d, aclexplode(d.defaclacl) acl
            WHERE d.defaclrole = (SELECT oid FROM pg_roles WHERE rolname = %s)
            AND (d.defaclnamespace = 0 OR d.defaclnamespace = 'public'::regnamespace)
            AND (acl.grantee = 0 OR acl.grantee = (SELECT oid FROM pg_roles WHERE rolname = %s))
            AND ((d.defaclobjtype = 'r' AND (acl.is_grantable OR acl.privilege_type NOT IN ('SELECT','INSERT','UPDATE','DELETE')))
              OR (d.defaclobjtype = 'S' AND (acl.is_grantable OR acl.privilege_type NOT IN ('USAGE','SELECT')))
              OR (d.defaclobjtype = 'n' AND (acl.is_grantable OR acl.privilege_type <> 'USAGE')))
            LIMIT 1""", (migration, runtime)).fetchone():
        raise ValueError("Migration owner has excessive runtime/public default privileges")
    if conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (runtime,)).fetchone():
        if conn.execute("""SELECT 1 FROM pg_namespace
                WHERE nspname !~ '^pg_' AND nspname <> 'information_schema'
                AND has_schema_privilege(%s, oid, 'CREATE') LIMIT 1""", (runtime,)).fetchone():
            raise ValueError("Runtime role has existing schema creation privileges")
        if conn.execute("""SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relkind IN ('r','p','v','m','f')
                AND has_table_privilege(%s, c.oid, 'TRUNCATE,REFERENCES,TRIGGER') LIMIT 1""", (runtime,)).fetchone():
            raise ValueError("Runtime role has excessive table privileges")
        if conn.execute("""SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relkind = 'S'
                AND CASE WHEN c.relkind = 'S' THEN has_sequence_privilege(%s, c.oid, 'UPDATE') ELSE false END LIMIT 1""", (runtime,)).fetchone():
            raise ValueError("Runtime role has excessive sequence privileges")
    if conn.execute("""SELECT 1 FROM pg_namespace WHERE nspname = 'public'
            AND nspowner NOT IN (SELECT oid FROM pg_roles WHERE rolname IN (%s, 'pg_database_owner'))""",
            (migration,)).fetchone():
        raise ValueError("Public schema must belong to the migration database owner")
    # This bootstrap owns one dedicated public-schema database, never an unrelated shared schema.
    if conn.execute("""SELECT 1 FROM pg_namespace
            WHERE nspname !~ '^pg_' AND nspname NOT IN ('public', 'information_schema')
            LIMIT 1""").fetchone():
        raise ValueError("Bootstrap requires a dedicated public-schema application database")
    if conn.execute("""SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relowner <> (SELECT oid FROM pg_roles WHERE rolname = %s)
            UNION ALL SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = 'public' AND p.proowner <> (SELECT oid FROM pg_roles WHERE rolname = %s)
            LIMIT 1""", (migration, migration)).fetchone():
        raise ValueError("Existing public-schema objects must belong to the migration role")


def bootstrap(env=None):
    env = load_environment(BOOTSTRAP_FIELDS, environ=env)
    app = connection_parameters(environ=env)
    if env.get("BOOTSTRAP_SSLMODE") not in (None, app["sslmode"]):
        raise ValueError("BOOTSTRAP_SSLMODE must match the shared PostgreSQL TLS policy")
    runtime, runtime_password, database = app["user"], app["password"], app["dbname"]
    migration, migration_password = required(env, "MIGRATION_USER"), required(env, "MIGRATION_PASSWORD")
    master, master_password = required(env, "BOOTSTRAP_USER"), required(env, "BOOTSTRAP_PASSWORD")
    if len({runtime, migration, master}) != 3:
        raise ValueError("Runtime, migration and bootstrap users must be distinct")
    master_options = {**app, "user": master, "password": master_password, "dbname": "postgres"}
    with psycopg.connect(**master_options, autocommit=True) as conn:
        existing = {name: check_role(conn, name) for name in (runtime, migration)}
        is_superuser = conn.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user").fetchone()[0]
        for name, row in existing.items():
            if row and not is_superuser and not conn.execute("""SELECT 1 FROM pg_auth_members
                    WHERE roleid = %s AND member = (SELECT oid FROM pg_roles WHERE rolname = current_user)
                    AND admin_option""", (row[0],)).fetchone():
                raise ValueError("Bootstrap user must already administer both existing application roles")
        if conn.execute("""SELECT 1 FROM pg_auth_members m JOIN pg_roles r ON r.oid = m.roleid
                WHERE r.rolname IN (%s, %s) AND m.member = (SELECT oid FROM pg_roles WHERE rolname = current_user)
                AND (m.inherit_option OR m.set_option) LIMIT 1""", (runtime, migration)).fetchone():
            raise ValueError("Bootstrap membership must be ADMIN-only without INHERIT or SET")
        if existing[runtime]:
            if conn.execute("""SELECT 1 FROM pg_shdepend
                    WHERE refclassid = 'pg_authid'::regclass AND refobjid = %s AND deptype = 'o'
                    UNION ALL SELECT 1 FROM pg_database WHERE has_database_privilege(%s, oid, 'CREATE')
                    LIMIT 1""", (existing[runtime][0], runtime)).fetchone():
                raise ValueError("Runtime role must not own objects or hold database creation privileges")
        owner = conn.execute("SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = %s",
                             (database,)).fetchone()
        if owner and owner[0] != migration:
            raise ValueError("Existing application database must be owned by the migration role")
        if owner:
            with psycopg.connect(**{**master_options, "dbname": database}) as target:
                check_database(target, runtime, migration)
        # Complete preflight before changing either password.
        for name, password in ((migration, migration_password), (runtime, runtime_password)):
            if existing[name]:
                statement = "ALTER ROLE {} LOGIN PASSWORD {}"
            else:
                statement = "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS PASSWORD {}"
            conn.execute(sql.SQL(statement).format(sql.Identifier(name), sql.Literal(password)))
        if not owner:
            prior_membership = conn.execute("""SELECT m.set_option FROM pg_auth_members m
                JOIN pg_roles r ON r.oid = m.roleid
                WHERE r.rolname = %s AND m.member = (SELECT oid FROM pg_roles WHERE rolname = current_user)""",
                (migration,)).fetchone()
            try:
                conn.execute(sql.SQL("GRANT {} TO CURRENT_USER WITH SET TRUE, INHERIT FALSE").format(sql.Identifier(migration)))
                conn.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(
                    sql.Identifier(database), sql.Identifier(migration)))
            finally:
                if prior_membership is None:
                    conn.execute(sql.SQL("REVOKE {} FROM CURRENT_USER").format(sql.Identifier(migration)))
                elif not prior_membership[0]:
                    conn.execute(sql.SQL("GRANT {} TO CURRENT_USER WITH SET FALSE").format(sql.Identifier(migration)))
    with psycopg.connect(**{**app, "user": migration, "password": migration_password}) as conn:
        role = sql.Identifier(runtime)
        conn.execute(sql.SQL("REVOKE TEMPORARY ON DATABASE {} FROM PUBLIC").format(sql.Identifier(database)))
        conn.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        conn.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(database), role))
        conn.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
        conn.execute(sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {}").format(role))
        conn.execute(sql.SQL("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {}").format(role))
        conn.execute(sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}").format(role))
        conn.execute(sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {}").format(role))


def main():
    try:
        bootstrap()
    except (ValueError, OSError, psycopg.Error):
        print("FAIL: unsafe bootstrap configuration, existing privileges/ownership, or database operation", file=sys.stderr)
        return 1
    print("Application database roles and grants configured.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
