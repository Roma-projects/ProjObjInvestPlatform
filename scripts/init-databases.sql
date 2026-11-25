-- Idempotently provision isolated databases and non-superuser application roles.
-- This script runs from both the fresh-volume initializer and postgres-bootstrap.
\getenv auth_password AUTH_DB_PASSWORD
\getenv listing_password LISTING_DB_PASSWORD
\getenv moderation_password MODERATION_DB_PASSWORD
\getenv analytic_ai_password ANALYTIC_AI_DB_PASSWORD

SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', 'auth_app', :'auth_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'auth_app') \gexec
SELECT format('ALTER ROLE %I WITH LOGIN PASSWORD %L', 'auth_app', :'auth_password') \gexec
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', 'listing_app', :'listing_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'listing_app') \gexec
SELECT format('ALTER ROLE %I WITH LOGIN PASSWORD %L', 'listing_app', :'listing_password') \gexec
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', 'moderation_app', :'moderation_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'moderation_app') \gexec
SELECT format('ALTER ROLE %I WITH LOGIN PASSWORD %L', 'moderation_app', :'moderation_password') \gexec
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', 'analytic_ai_app', :'analytic_ai_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'analytic_ai_app') \gexec
SELECT format('ALTER ROLE %I WITH LOGIN PASSWORD %L', 'analytic_ai_app', :'analytic_ai_password') \gexec

SELECT 'CREATE DATABASE auth_db OWNER auth_app'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'auth_db') \gexec
SELECT 'ALTER DATABASE auth_db OWNER TO auth_app' \gexec
SELECT 'CREATE DATABASE listing_db OWNER listing_app'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'listing_db') \gexec
SELECT 'ALTER DATABASE listing_db OWNER TO listing_app' \gexec
SELECT 'CREATE DATABASE moderation_db OWNER moderation_app'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'moderation_db') \gexec
SELECT 'ALTER DATABASE moderation_db OWNER TO moderation_app' \gexec
SELECT 'CREATE DATABASE analytic_ai_db OWNER analytic_ai_app'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'analytic_ai_db') \gexec
SELECT 'ALTER DATABASE analytic_ai_db OWNER TO analytic_ai_app' \gexec

REVOKE ALL ON DATABASE auth_db FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE auth_db TO auth_app;
REVOKE ALL ON DATABASE listing_db FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE listing_db TO listing_app;
REVOKE ALL ON DATABASE moderation_db FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE moderation_db TO moderation_app;
REVOKE ALL ON DATABASE analytic_ai_db FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE analytic_ai_db TO analytic_ai_app;

\connect auth_db
SELECT format(
    'ALTER %s %I.%I OWNER TO auth_app',
    CASE c.relkind WHEN 'v' THEN 'VIEW' WHEN 'm' THEN 'MATERIALIZED VIEW' WHEN 'f' THEN 'FOREIGN TABLE' ELSE 'TABLE' END,
    n.nspname,
    c.relname
)
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relowner = (SELECT oid FROM pg_roles WHERE rolname = current_user)
  AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
\gexec
ALTER SCHEMA public OWNER TO auth_app;
GRANT ALL ON SCHEMA public TO auth_app;

\connect listing_db
SELECT format(
    'ALTER %s %I.%I OWNER TO listing_app',
    CASE c.relkind WHEN 'v' THEN 'VIEW' WHEN 'm' THEN 'MATERIALIZED VIEW' WHEN 'f' THEN 'FOREIGN TABLE' ELSE 'TABLE' END,
    n.nspname,
    c.relname
)
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relowner = (SELECT oid FROM pg_roles WHERE rolname = current_user)
  AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
\gexec
ALTER SCHEMA public OWNER TO listing_app;
GRANT ALL ON SCHEMA public TO listing_app;

\connect moderation_db
SELECT format(
    'ALTER %s %I.%I OWNER TO moderation_app',
    CASE c.relkind WHEN 'v' THEN 'VIEW' WHEN 'm' THEN 'MATERIALIZED VIEW' WHEN 'f' THEN 'FOREIGN TABLE' ELSE 'TABLE' END,
    n.nspname,
    c.relname
)
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relowner = (SELECT oid FROM pg_roles WHERE rolname = current_user)
  AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
\gexec
ALTER SCHEMA public OWNER TO moderation_app;
GRANT ALL ON SCHEMA public TO moderation_app;

\connect analytic_ai_db
SELECT format(
    'ALTER %s %I.%I OWNER TO analytic_ai_app',
    CASE c.relkind WHEN 'v' THEN 'VIEW' WHEN 'm' THEN 'MATERIALIZED VIEW' WHEN 'f' THEN 'FOREIGN TABLE' ELSE 'TABLE' END,
    n.nspname,
    c.relname
)
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relowner = (SELECT oid FROM pg_roles WHERE rolname = current_user)
  AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
\gexec
ALTER SCHEMA public OWNER TO analytic_ai_app;
GRANT ALL ON SCHEMA public TO analytic_ai_app;
