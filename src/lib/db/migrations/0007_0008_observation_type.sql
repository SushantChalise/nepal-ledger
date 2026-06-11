-- Migration 0008 — adds `observation_type` (ADR-0025) to the indicator-values
-- pipeline. Epistemic status orthogonal to confidence_grade: marks WEO
-- projections, PIP interpolated rows, and ILO modelled estimates as distinct
-- from directly-published actuals. Additive ADD COLUMN ... DEFAULT 'actual'
-- backfills every existing row to 'actual' and is non-locking on PG >= 11.
CREATE TYPE "public"."observation_type" AS ENUM('actual', 'projection', 'interpolated', 'estimate', 'provisional');--> statement-breakpoint
ALTER TABLE "approved_indicator_values" ADD COLUMN "observation_type" "observation_type" DEFAULT 'actual' NOT NULL;--> statement-breakpoint
ALTER TABLE "staging_indicator_values" ADD COLUMN "observation_type" "observation_type" DEFAULT 'actual' NOT NULL;