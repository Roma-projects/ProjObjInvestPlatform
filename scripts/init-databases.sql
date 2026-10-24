-- Create the isolated PostgreSQL databases required by the independently deployed services.
SELECT 'CREATE DATABASE auth_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'auth_db') \gexec
SELECT 'CREATE DATABASE listing_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'listing_db') \gexec
SELECT 'CREATE DATABASE analytic_ai_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'analytic_ai_db') \gexec
