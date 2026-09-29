-- Part 1 of 2: create the trainer's read-only login. Run as the RDS master (BOOTSTRAP_USER), because
-- db_bootstrap makes the migration owner NOCREATEROLE on purpose. Idempotent: a rerun only resets the
-- password to match the trainer secret. The login gets no rights here; part 2 grants read access.
--
-- Values come from the environment, never from this file or the command line:
--   TRAINER_USER, TRAINER_PASSWORD  (from the inf2006-grp21/trainer secret)
\set ON_ERROR_STOP on
\getenv trainer_user TRAINER_USER
\getenv trainer_password TRAINER_PASSWORD

SELECT NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'trainer_user') AS create_needed \gset

\if :create_needed
  CREATE ROLE :"trainer_user" LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS
    PASSWORD :'trainer_password';
\else
  ALTER ROLE :"trainer_user" LOGIN PASSWORD :'trainer_password';
\endif

-- Show the result without any password: every flag should be false except rolcanlogin.
SELECT rolname, rolcanlogin, rolsuper, rolcreaterole, rolcreatedb, rolreplication, rolbypassrls
FROM pg_roles WHERE rolname = :'trainer_user';
