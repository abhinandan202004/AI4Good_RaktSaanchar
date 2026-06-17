-- =============================================================================
-- RaktSaanchar — PostgreSQL Schema Initialisation
-- =============================================================================
-- Creates one schema per microservice so all services share ONE PostgreSQL
-- instance but each has logically isolated tables.
-- This file is mounted into the Postgres container via:
--   ./infra/init.sql:/docker-entrypoint-initdb.d/init.sql
-- =============================================================================

-- Create schemas
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS notifications;
CREATE SCHEMA IF NOT EXISTS chat;
CREATE SCHEMA IF NOT EXISTS ml;

-- Grant the rakt user full access to each schema
GRANT ALL PRIVILEGES ON SCHEMA auth          TO rakt;
GRANT ALL PRIVILEGES ON SCHEMA core          TO rakt;
GRANT ALL PRIVILEGES ON SCHEMA notifications TO rakt;
GRANT ALL PRIVILEGES ON SCHEMA chat          TO rakt;
GRANT ALL PRIVILEGES ON SCHEMA ml            TO rakt;

-- Allow each schema to create tables (needed for SQLAlchemy create_all)
ALTER USER rakt SET search_path TO auth, core, notifications, chat, ml, public;

-- Cross-schema read grants (so notification-service can read core.users etc.)
-- These are applied after SQLAlchemy creates the tables.
-- The notification-service runs with CORE_DB_URL pointing to core schema.

-- =============================================================================
-- NOTE: SQLAlchemy services will call Base.metadata.create_all() at startup
-- using their own schema-scoped DATABASE_URL, so explicit CREATE TABLE
-- statements are NOT needed here.  This file only sets up schemas + grants.
-- =============================================================================
