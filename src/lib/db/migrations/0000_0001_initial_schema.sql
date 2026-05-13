CREATE TYPE "public"."confidence_grade" AS ENUM('A', 'B', 'C');--> statement-breakpoint
CREATE TYPE "public"."data_quality_flag_type" AS ENUM('SchemaInvalid', 'PeriodAmbiguous', 'UnitUnrecognized', 'DuplicateOfApproved', 'RevisionMismatch', 'ValueOutOfPlausibleRange', 'IndicatorUnknown', 'SourceHashCollision');--> statement-breakpoint
CREATE TYPE "public"."file_format" AS ENUM('pdf', 'csv', 'xlsx', 'xls', 'html', 'json', 'xml');--> statement-breakpoint
CREATE TYPE "public"."flag_severity" AS ENUM('blocking', 'warning');--> statement-breakpoint
CREATE TYPE "public"."indicator_category" AS ENUM('price', 'monetary', 'fiscal', 'external_sector', 'real_sector', 'banking', 'capital_markets', 'labour', 'tourism', 'agriculture', 'energy', 'land', 'demographic', 'composite');--> statement-breakpoint
CREATE TYPE "public"."license_status" AS ENUM('public_domain', 'gov_open', 'cc_by', 'cc_by_nc_sa', 'proprietary', 'unclear');--> statement-breakpoint
CREATE TYPE "public"."parser_error_class" AS ENUM('ColumnMissing', 'RegexMismatch', 'UnitAmbiguous', 'PageLayoutChanged', 'PeriodAmbiguous', 'ValueUnparseable', 'EncodingError', 'Other');--> statement-breakpoint
CREATE TYPE "public"."parser_status" AS ENUM('success', 'partial', 'failure');--> statement-breakpoint
CREATE TYPE "public"."publication_frequency" AS ENUM('monthly', 'quarterly', 'annual', 'daily', 'seasonal', 'ad_hoc');--> statement-breakpoint
CREATE TYPE "public"."reporting_period_type" AS ENUM('monthly', 'quarterly', 'annual', 'nine_months_cumulative', 'year_to_date', 'daily', 'seasonal');--> statement-breakpoint
CREATE TYPE "public"."source_status" AS ENUM('active', 'paused', 'deprecated');--> statement-breakpoint
CREATE TYPE "public"."storage_provider" AS ENUM('supabase', 'r2');--> statement-breakpoint
CREATE TABLE "source_registry" (
	"source_id" text PRIMARY KEY NOT NULL,
	"agency" text NOT NULL,
	"agency_short" text NOT NULL,
	"dataset_name" text NOT NULL,
	"source_url" text NOT NULL,
	"publication_frequency" "publication_frequency" NOT NULL,
	"expected_release_window" text,
	"reporting_period_type" "reporting_period_type" NOT NULL,
	"file_format" "file_format" NOT NULL,
	"requires_table_extraction" boolean DEFAULT false NOT NULL,
	"historical_coverage" text,
	"license_status" "license_status" DEFAULT 'gov_open' NOT NULL,
	"parser_owner" text,
	"parser_version" text,
	"revision_policy" text,
	"known_breakage_modes" text[] DEFAULT ARRAY[]::text[] NOT NULL,
	"confidence_default" "confidence_grade" DEFAULT 'A' NOT NULL,
	"status" "source_status" DEFAULT 'active' NOT NULL,
	"notes" text,
	"registered_at" timestamp with time zone DEFAULT now() NOT NULL,
	"last_verified_at" timestamp with time zone
);
--> statement-breakpoint
CREATE TABLE "source_documents" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"source_id" text NOT NULL,
	"original_url" text NOT NULL,
	"storage_provider" "storage_provider" DEFAULT 'supabase' NOT NULL,
	"storage_key" text NOT NULL,
	"file_hash_sha256" text NOT NULL,
	"file_size_bytes" bigint NOT NULL,
	"content_type" text NOT NULL,
	"downloaded_at" timestamp with time zone DEFAULT now() NOT NULL,
	"reporting_period_label" text,
	"notes" text
);
--> statement-breakpoint
CREATE TABLE "parser_errors" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"parser_run_id" uuid NOT NULL,
	"error_class" "parser_error_class" NOT NULL,
	"error_detail" text NOT NULL,
	"source_excerpt" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "parser_runs" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"source_document_id" uuid NOT NULL,
	"parser_path" text NOT NULL,
	"parser_version" text NOT NULL,
	"started_at" timestamp with time zone DEFAULT now() NOT NULL,
	"ended_at" timestamp with time zone,
	"status" "parser_status" NOT NULL,
	"staging_rows_written" integer DEFAULT 0 NOT NULL,
	"error_summary" text,
	"stdout_tail" text
);
--> statement-breakpoint
CREATE TABLE "indicator_source_map" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"indicator_id" uuid NOT NULL,
	"source_id" text NOT NULL,
	"notes" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "indicator_units" (
	"unit" text PRIMARY KEY NOT NULL,
	"display_en" text NOT NULL,
	"display_ne" text,
	"dimension" text NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "indicators" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"slug" text NOT NULL,
	"name_en" text NOT NULL,
	"name_ne" text,
	"category" "indicator_category" NOT NULL,
	"unit" text NOT NULL,
	"native_frequency" text NOT NULL,
	"source_agency" text NOT NULL,
	"parent_indicator_id" uuid,
	"description_en" text,
	"description_ne" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "indicators_slug_unique" UNIQUE("slug")
);
--> statement-breakpoint
CREATE TABLE "approved_indicator_values" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"source_document_id" uuid NOT NULL,
	"indicator_id" uuid NOT NULL,
	"value" numeric(24, 6) NOT NULL,
	"unit" text NOT NULL,
	"reporting_period_type" "reporting_period_type" NOT NULL,
	"reporting_period_bs" text NOT NULL,
	"reporting_period_ad_start" timestamp with time zone NOT NULL,
	"reporting_period_ad_end" timestamp with time zone NOT NULL,
	"publication_date_ad" timestamp with time zone NOT NULL,
	"publication_date_bs" text NOT NULL,
	"fiscal_year_bs" text NOT NULL,
	"fiscal_year_ad_label" text NOT NULL,
	"confidence_grade" "confidence_grade" NOT NULL,
	"revision_number" integer DEFAULT 0 NOT NULL,
	"promoted_at" timestamp with time zone DEFAULT now() NOT NULL,
	"promoted_by" text NOT NULL,
	"notes" text
);
--> statement-breakpoint
CREATE TABLE "data_quality_flags" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"staging_row_id" uuid NOT NULL,
	"flag_type" "data_quality_flag_type" NOT NULL,
	"severity" "flag_severity" NOT NULL,
	"detail" text NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"resolved_at" timestamp with time zone,
	"resolution_note" text
);
--> statement-breakpoint
CREATE TABLE "staging_indicator_values" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"parser_run_id" uuid NOT NULL,
	"source_document_id" uuid NOT NULL,
	"indicator_id" uuid,
	"indicator_slug_raw" text NOT NULL,
	"value" numeric(24, 6) NOT NULL,
	"unit" text NOT NULL,
	"reporting_period_type" "reporting_period_type" NOT NULL,
	"reporting_period_bs" text NOT NULL,
	"reporting_period_ad_start" timestamp with time zone NOT NULL,
	"reporting_period_ad_end" timestamp with time zone NOT NULL,
	"publication_date_ad" timestamp with time zone NOT NULL,
	"publication_date_bs" text NOT NULL,
	"fiscal_year_bs" text NOT NULL,
	"fiscal_year_ad_label" text NOT NULL,
	"confidence_grade_proposed" "confidence_grade" NOT NULL,
	"parser_notes" text,
	"inserted_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "fact_ledger_challenges" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"claim_id" uuid NOT NULL,
	"email" text NOT NULL,
	"source_url" text,
	"message" text NOT NULL,
	"status" text DEFAULT 'pending' NOT NULL,
	"resolution_note" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"resolved_at" timestamp with time zone
);
--> statement-breakpoint
CREATE TABLE "fact_ledger_claims" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"slug" text NOT NULL,
	"text_en" text NOT NULL,
	"text_ne" text,
	"indicator_value_id" uuid,
	"indicator_id" uuid,
	"source_document_id" uuid NOT NULL,
	"confidence_grade" "confidence_grade" NOT NULL,
	"last_verified_at" timestamp with time zone DEFAULT now() NOT NULL,
	"verified_by" text NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_reason" text
);
--> statement-breakpoint
CREATE TABLE "leads" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"email" text NOT NULL,
	"source" text,
	"referrer" text,
	"status" text DEFAULT 'subscribed' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"confirmed_at" timestamp with time zone,
	"unsubscribed_at" timestamp with time zone
);
--> statement-breakpoint
ALTER TABLE "source_documents" ADD CONSTRAINT "source_documents_source_id_source_registry_source_id_fk" FOREIGN KEY ("source_id") REFERENCES "public"."source_registry"("source_id") ON DELETE restrict ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "parser_errors" ADD CONSTRAINT "parser_errors_parser_run_id_parser_runs_id_fk" FOREIGN KEY ("parser_run_id") REFERENCES "public"."parser_runs"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "parser_runs" ADD CONSTRAINT "parser_runs_source_document_id_source_documents_id_fk" FOREIGN KEY ("source_document_id") REFERENCES "public"."source_documents"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "indicator_source_map" ADD CONSTRAINT "indicator_source_map_indicator_id_indicators_id_fk" FOREIGN KEY ("indicator_id") REFERENCES "public"."indicators"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "indicator_source_map" ADD CONSTRAINT "indicator_source_map_source_id_source_registry_source_id_fk" FOREIGN KEY ("source_id") REFERENCES "public"."source_registry"("source_id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "indicators" ADD CONSTRAINT "indicators_parent_fk" FOREIGN KEY ("parent_indicator_id") REFERENCES "public"."indicators"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "approved_indicator_values" ADD CONSTRAINT "approved_indicator_values_source_document_id_source_documents_id_fk" FOREIGN KEY ("source_document_id") REFERENCES "public"."source_documents"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "approved_indicator_values" ADD CONSTRAINT "approved_indicator_values_indicator_id_indicators_id_fk" FOREIGN KEY ("indicator_id") REFERENCES "public"."indicators"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "data_quality_flags" ADD CONSTRAINT "data_quality_flags_staging_row_id_staging_indicator_values_id_fk" FOREIGN KEY ("staging_row_id") REFERENCES "public"."staging_indicator_values"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "staging_indicator_values" ADD CONSTRAINT "staging_indicator_values_parser_run_id_parser_runs_id_fk" FOREIGN KEY ("parser_run_id") REFERENCES "public"."parser_runs"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "staging_indicator_values" ADD CONSTRAINT "staging_indicator_values_source_document_id_source_documents_id_fk" FOREIGN KEY ("source_document_id") REFERENCES "public"."source_documents"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "staging_indicator_values" ADD CONSTRAINT "staging_indicator_values_indicator_id_indicators_id_fk" FOREIGN KEY ("indicator_id") REFERENCES "public"."indicators"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "fact_ledger_challenges" ADD CONSTRAINT "fact_ledger_challenges_claim_id_fact_ledger_claims_id_fk" FOREIGN KEY ("claim_id") REFERENCES "public"."fact_ledger_claims"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "fact_ledger_claims" ADD CONSTRAINT "fact_ledger_claims_indicator_value_id_approved_indicator_values_id_fk" FOREIGN KEY ("indicator_value_id") REFERENCES "public"."approved_indicator_values"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "fact_ledger_claims" ADD CONSTRAINT "fact_ledger_claims_indicator_id_indicators_id_fk" FOREIGN KEY ("indicator_id") REFERENCES "public"."indicators"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "fact_ledger_claims" ADD CONSTRAINT "fact_ledger_claims_source_document_id_source_documents_id_fk" FOREIGN KEY ("source_document_id") REFERENCES "public"."source_documents"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "source_documents_source_id_idx" ON "source_documents" USING btree ("source_id");--> statement-breakpoint
CREATE INDEX "source_documents_hash_idx" ON "source_documents" USING btree ("file_hash_sha256");--> statement-breakpoint
CREATE INDEX "parser_errors_run_idx" ON "parser_errors" USING btree ("parser_run_id");--> statement-breakpoint
CREATE INDEX "parser_runs_source_doc_idx" ON "parser_runs" USING btree ("source_document_id");--> statement-breakpoint
CREATE INDEX "parser_runs_status_idx" ON "parser_runs" USING btree ("status");--> statement-breakpoint
CREATE INDEX "indicator_source_map_indicator_idx" ON "indicator_source_map" USING btree ("indicator_id");--> statement-breakpoint
CREATE INDEX "indicator_source_map_source_idx" ON "indicator_source_map" USING btree ("source_id");--> statement-breakpoint
CREATE INDEX "indicators_category_idx" ON "indicators" USING btree ("category");--> statement-breakpoint
CREATE UNIQUE INDEX "approved_unique_period_revision" ON "approved_indicator_values" USING btree ("indicator_id","reporting_period_type","reporting_period_bs","revision_number");--> statement-breakpoint
CREATE INDEX "approved_indicator_idx" ON "approved_indicator_values" USING btree ("indicator_id");--> statement-breakpoint
CREATE INDEX "approved_period_idx" ON "approved_indicator_values" USING btree ("reporting_period_ad_end");--> statement-breakpoint
CREATE INDEX "approved_fy_idx" ON "approved_indicator_values" USING btree ("fiscal_year_bs");--> statement-breakpoint
CREATE INDEX "flags_staging_row_idx" ON "data_quality_flags" USING btree ("staging_row_id");--> statement-breakpoint
CREATE INDEX "flags_unresolved_idx" ON "data_quality_flags" USING btree ("severity","created_at") WHERE resolved_at IS NULL;--> statement-breakpoint
CREATE INDEX "staging_run_idx" ON "staging_indicator_values" USING btree ("parser_run_id");--> statement-breakpoint
CREATE INDEX "staging_indicator_idx" ON "staging_indicator_values" USING btree ("indicator_id");--> statement-breakpoint
CREATE INDEX "staging_period_idx" ON "staging_indicator_values" USING btree ("reporting_period_bs","reporting_period_type");--> statement-breakpoint
CREATE INDEX "fact_ledger_challenges_claim_idx" ON "fact_ledger_challenges" USING btree ("claim_id");--> statement-breakpoint
CREATE UNIQUE INDEX "fact_ledger_slug_idx" ON "fact_ledger_claims" USING btree ("slug");--> statement-breakpoint
CREATE INDEX "fact_ledger_indicator_idx" ON "fact_ledger_claims" USING btree ("indicator_id");--> statement-breakpoint
CREATE INDEX "fact_ledger_source_doc_idx" ON "fact_ledger_claims" USING btree ("source_document_id");--> statement-breakpoint
CREATE INDEX "leads_email_idx" ON "leads" USING btree ("email");--> statement-breakpoint
CREATE INDEX "leads_status_idx" ON "leads" USING btree ("status");