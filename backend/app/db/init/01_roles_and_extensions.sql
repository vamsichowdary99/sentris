-- Runs once, automatically, on first Postgres container init (docker-entrypoint-initdb.d).
-- Sets up the least-privilege app role vs. the migrator role described in
-- ENGINEERING_PLAN.md §4 "DB permissions", plus extensions used for search.

CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- pgvector is optional (semantic search / embeddings). Uncomment once the
-- postgres image includes the extension (e.g. pgvector/pgvector:pg16), or
-- install it manually in prod.
-- CREATE EXTENSION IF NOT EXISTS vector;

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'sentris_migrator') THEN
    CREATE ROLE sentris_migrator LOGIN PASSWORD 'sentris_dev_migrator_password';
  END IF;
END
$$;

GRANT ALL PRIVILEGES ON SCHEMA public TO sentris_migrator;
GRANT CONNECT ON DATABASE sentris TO sentris_migrator;

-- The app role (POSTGRES_USER) is created by the base postgres image already.
-- Ensure it can use, but not alter, the schema; Alembic (run as
-- sentris_migrator) will grant table-level CRUD after each migration via
-- `ALTER DEFAULT PRIVILEGES`.
GRANT USAGE ON SCHEMA public TO PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE sentris_migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE sentris_migrator IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO PUBLIC;
