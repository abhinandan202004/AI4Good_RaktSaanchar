-- =============================================================================
-- Migration 001: Add 'validation_failed' to the requeststatus enum
-- =============================================================================
-- Run this ONCE on the live PostgreSQL database before deploying the updated
-- core-service image. It is idempotent — safe to run multiple times.
--
-- How to run (from the Oracle VM):
--   docker exec -i raktsaanchar-postgres-1 \
--     psql -U rakt -d rakt \
--     -c "$(cat infra/migrations/001_add_validation_failed_status.sql)"
-- =============================================================================

DO $$
BEGIN
    -- Only add the value if it does not already exist (idempotent)
    IF NOT EXISTS (
        SELECT 1
        FROM pg_enum e
        JOIN pg_type t ON e.enumtypid = t.oid
        WHERE t.typname = 'requeststatus'
          AND e.enumlabel = 'validation_failed'
    ) THEN
        ALTER TYPE requeststatus ADD VALUE 'validation_failed';
        RAISE NOTICE 'Added validation_failed to requeststatus enum.';
    ELSE
        RAISE NOTICE 'validation_failed already exists in requeststatus enum — skipped.';
    END IF;
END
$$;
