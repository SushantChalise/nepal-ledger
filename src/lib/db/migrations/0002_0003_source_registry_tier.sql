-- Migration 0003 — adds the `tier` column to `source_registry`.
-- Locked semantics per ADR-0009: 0 = pre-ADR-0009 baseline (the two
-- starter rows registered in migration 0001), 1–4 = phased rollout per
-- BACKEND_PLAN, NULL = reference-only assets or rows registered before
-- the column landed. Tier semantics changes require a new ADR.
ALTER TABLE "source_registry" ADD COLUMN "tier" smallint;
