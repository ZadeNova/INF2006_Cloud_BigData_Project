-- Part 2 of 2: give the trainer read access to exactly what the ML trainer and refresh verifier read
-- (analytics/segment_customers.py, analytics/verify_refresh.py), and nothing else. Run as the migration
-- owner (MIGRATION_USER), connected to the application database, after `migrate` has created the
-- tables. The migration owner owns every table, so it is the one that can grant on them.
--
-- Deliberately NOT granted: django_session (its session keys would let a reader take over logged-in
-- sessions), the rest of auth_user (password hashes, emails), carts and anything else. No default
-- privileges: a table added by a later migration stays unreadable until it is added here on purpose.
-- Idempotent: repeating a GRANT is harmless.
--
--   TRAINER_USER (from the inf2006-grp21/trainer secret), APP_DB (POSTGRES_DB)
\set ON_ERROR_STOP on
\getenv trainer_user TRAINER_USER
\getenv app_db APP_DB

GRANT CONNECT ON DATABASE :"app_db" TO :"trainer_user";
GRANT USAGE ON SCHEMA public TO :"trainer_user";

GRANT SELECT ON
  public.orders_order,
  public.orders_orderitem,
  public.catalogue_product,
  public.auth_group,
  public.auth_user_groups,
  public.reporting_analyticsrun,
  public.reporting_inventoryversion,
  public.reporting_inventorysnapshot,
  public.reporting_dailyproductsales
TO :"trainer_user";

-- Only the columns used to exclude staff and operators from customer segments.
GRANT SELECT (id, is_staff, is_superuser) ON public.auth_user TO :"trainer_user";

-- Evidence: which tables the trainer can read and write. Expected: 9 readable tables, auth_user
-- readable only through its 3 columns (not listed as a readable table), nothing writable.
SELECT c.relname AS table_name,
       has_table_privilege(:'trainer_user', c.oid, 'SELECT') AS can_select_all_columns,
       has_any_column_privilege(:'trainer_user', c.oid, 'SELECT') AS can_select_some_columns,
       has_table_privilege(:'trainer_user', c.oid, 'INSERT,UPDATE,DELETE,TRUNCATE') AS can_write
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
  AND has_any_column_privilege(:'trainer_user', c.oid, 'SELECT')
ORDER BY 1;
