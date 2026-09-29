-- Part 2 of 2: give the trainer read-only access to the application tables. Run as the migration
-- owner (MIGRATION_USER), connected to the application database, after `migrate` has created the
-- tables. The migration owner owns every table, so it is the one that can grant on them.
-- Idempotent: GRANT and ALTER DEFAULT PRIVILEGES can be repeated safely.
--
--   TRAINER_USER (from the inf2006-grp21/trainer secret), APP_DB (POSTGRES_DB)
\set ON_ERROR_STOP on
\getenv trainer_user TRAINER_USER
\getenv app_db APP_DB

GRANT CONNECT ON DATABASE :"app_db" TO :"trainer_user";
GRANT USAGE ON SCHEMA public TO :"trainer_user";
GRANT SELECT ON ALL TABLES IN SCHEMA public TO :"trainer_user";
-- Tables created by later migrations (owned by this same login) are readable too.
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO :"trainer_user";

-- Evidence: the trainer can SELECT, and nothing else, on every table.
SELECT count(*) AS tables_in_public,
       count(*) FILTER (WHERE has_table_privilege(:'trainer_user', c.oid, 'SELECT')) AS trainer_can_select,
       count(*) FILTER (WHERE has_table_privilege(:'trainer_user', c.oid, 'INSERT,UPDATE,DELETE,TRUNCATE')) AS trainer_can_write
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p');
