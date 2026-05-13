CREATE TYPE "public"."bank_class" AS ENUM('commercial', 'development', 'finance', 'microfinance', 'infrastructure', 'system_total');--> statement-breakpoint
CREATE TYPE "public"."census_indicator_family" AS ENUM('household_housing', 'household_facility', 'household_economic', 'household_demographic', 'individual_demographic', 'individual_education', 'individual_economic', 'individual_migration', 'individual_fertility');--> statement-breakpoint
CREATE TYPE "public"."entity_kind" AS ENUM('bank', 'public_enterprise', 'local_level', 'district', 'province', 'cooperative', 'business_group', 'ministry', 'department', 'donor', 'constituency', 'ward', 'polling_station');--> statement-breakpoint
CREATE TYPE "public"."grant_type" AS ENUM('equalization_minimum', 'equalization_formula', 'equalization_performance', 'conditional_current', 'conditional_capital', 'special_current', 'special_capital', 'complementary_capital');--> statement-breakpoint
CREATE TYPE "public"."ingestion_mode" AS ENUM('automated_cron', 'manual_upload', 'reference_only');--> statement-breakpoint
CREATE TYPE "public"."local_level_type" AS ENUM('metropolitan_city', 'sub_metropolitan_city', 'municipality', 'rural_municipality');--> statement-breakpoint
CREATE TYPE "public"."stitch_resolution" AS ENUM('kept_higher_confidence', 'kept_left_tile', 'kept_right_tile', 'flagged_for_review');--> statement-breakpoint
CREATE TABLE "entities" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"kind" "entity_kind" NOT NULL,
	"slug" text NOT NULL,
	"name_en" text NOT NULL,
	"name_ne" text,
	"parent_entity_id" uuid,
	"metadata" jsonb,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "administrative_units" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"entity_id" uuid NOT NULL,
	"federal_code" text,
	"local_level_type" "local_level_type",
	"constituency_no" text,
	"ward_no" integer,
	"rural_urban" text,
	"voter_count" integer,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "local_government_fiscal_transfers" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"local_level_entity_id" uuid NOT NULL,
	"fiscal_year_bs" text NOT NULL,
	"grant_type" "grant_type" NOT NULL,
	"amount_npr" numeric(20, 2) NOT NULL,
	"unit" text DEFAULT 'NPR_thousand' NOT NULL,
	"source_document_id" uuid NOT NULL,
	"confidence_grade" "confidence_grade" NOT NULL,
	"promoted_at" timestamp with time zone DEFAULT now() NOT NULL,
	"promoted_by" text NOT NULL,
	"notes" text
);
--> statement-breakpoint
CREATE TABLE "census_facts" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"entity_id" uuid NOT NULL,
	"indicator_family" "census_indicator_family" NOT NULL,
	"source_table_id" text NOT NULL,
	"indicator_slug" text NOT NULL,
	"value" numeric(24, 6) NOT NULL,
	"unit" text NOT NULL,
	"census_year_ad" text DEFAULT '2021' NOT NULL,
	"census_year_bs" text DEFAULT '2078' NOT NULL,
	"source_document_id" uuid NOT NULL,
	"confidence_grade" "confidence_grade" DEFAULT 'A' NOT NULL,
	"promoted_at" timestamp with time zone DEFAULT now() NOT NULL,
	"promoted_by" text NOT NULL
);
--> statement-breakpoint
CREATE TABLE "banking_sector_facts" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"bank_class" "bank_class" NOT NULL,
	"bank_entity_id" uuid,
	"source_sheet" text NOT NULL,
	"indicator_slug" text NOT NULL,
	"value" numeric(24, 6) NOT NULL,
	"unit" text NOT NULL,
	"reporting_period_type" "reporting_period_type" NOT NULL,
	"reporting_period_bs" text NOT NULL,
	"reporting_period_ad_start" timestamp with time zone NOT NULL,
	"reporting_period_ad_end" timestamp with time zone NOT NULL,
	"publication_date_ad" timestamp with time zone NOT NULL,
	"publication_date_bs" text NOT NULL,
	"fiscal_year_bs" text NOT NULL,
	"source_document_id" uuid NOT NULL,
	"confidence_grade" "confidence_grade" DEFAULT 'A' NOT NULL,
	"promoted_at" timestamp with time zone DEFAULT now() NOT NULL,
	"promoted_by" text NOT NULL
);
--> statement-breakpoint
CREATE TABLE "ocr_cell_extractions" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"tile_id" uuid NOT NULL,
	"table_region_id" text,
	"tile_bbox_x" integer NOT NULL,
	"tile_bbox_y" integer NOT NULL,
	"tile_bbox_w" integer NOT NULL,
	"tile_bbox_h" integer NOT NULL,
	"page_bbox_x" integer NOT NULL,
	"page_bbox_y" integer NOT NULL,
	"page_bbox_w" integer NOT NULL,
	"page_bbox_h" integer NOT NULL,
	"near_tile_seam_px" integer,
	"text_raw" text NOT NULL,
	"text_normalized" text,
	"numeral_arabic" text,
	"numeral_devanagari" text,
	"confidence" numeric(6, 4),
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "ocr_stitch_disagreements" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"cell_a_extraction_id" uuid NOT NULL,
	"cell_b_extraction_id" uuid NOT NULL,
	"iou" numeric(6, 4) NOT NULL,
	"resolution" "stitch_resolution" NOT NULL,
	"resolution_reason" text NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "ocr_tile_manifests" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"parser_run_id" uuid NOT NULL,
	"source_document_id" uuid NOT NULL,
	"page_number" integer NOT NULL,
	"tile_index" integer NOT NULL,
	"offset_x_px" integer NOT NULL,
	"offset_y_px" integer NOT NULL,
	"width_px" integer NOT NULL,
	"height_px" integer NOT NULL,
	"dpi" integer NOT NULL,
	"model_name" text NOT NULL,
	"model_version" text NOT NULL,
	"rendered_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "source_registry" ADD COLUMN "ingestion_mode" "ingestion_mode" DEFAULT 'automated_cron' NOT NULL;--> statement-breakpoint
ALTER TABLE "entities" ADD CONSTRAINT "entities_parent_fk" FOREIGN KEY ("parent_entity_id") REFERENCES "public"."entities"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "administrative_units" ADD CONSTRAINT "administrative_units_entity_id_entities_id_fk" FOREIGN KEY ("entity_id") REFERENCES "public"."entities"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "local_government_fiscal_transfers" ADD CONSTRAINT "local_government_fiscal_transfers_local_level_entity_id_entities_id_fk" FOREIGN KEY ("local_level_entity_id") REFERENCES "public"."entities"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "local_government_fiscal_transfers" ADD CONSTRAINT "local_government_fiscal_transfers_source_document_id_source_documents_id_fk" FOREIGN KEY ("source_document_id") REFERENCES "public"."source_documents"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "census_facts" ADD CONSTRAINT "census_facts_entity_id_entities_id_fk" FOREIGN KEY ("entity_id") REFERENCES "public"."entities"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "census_facts" ADD CONSTRAINT "census_facts_source_document_id_source_documents_id_fk" FOREIGN KEY ("source_document_id") REFERENCES "public"."source_documents"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "banking_sector_facts" ADD CONSTRAINT "banking_sector_facts_bank_entity_id_entities_id_fk" FOREIGN KEY ("bank_entity_id") REFERENCES "public"."entities"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "banking_sector_facts" ADD CONSTRAINT "banking_sector_facts_source_document_id_source_documents_id_fk" FOREIGN KEY ("source_document_id") REFERENCES "public"."source_documents"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "ocr_cell_extractions" ADD CONSTRAINT "ocr_cell_extractions_tile_id_ocr_tile_manifests_id_fk" FOREIGN KEY ("tile_id") REFERENCES "public"."ocr_tile_manifests"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "ocr_stitch_disagreements" ADD CONSTRAINT "ocr_stitch_disagreements_cell_a_extraction_id_ocr_cell_extractions_id_fk" FOREIGN KEY ("cell_a_extraction_id") REFERENCES "public"."ocr_cell_extractions"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "ocr_stitch_disagreements" ADD CONSTRAINT "ocr_stitch_disagreements_cell_b_extraction_id_ocr_cell_extractions_id_fk" FOREIGN KEY ("cell_b_extraction_id") REFERENCES "public"."ocr_cell_extractions"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "ocr_tile_manifests" ADD CONSTRAINT "ocr_tile_manifests_parser_run_id_parser_runs_id_fk" FOREIGN KEY ("parser_run_id") REFERENCES "public"."parser_runs"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "ocr_tile_manifests" ADD CONSTRAINT "ocr_tile_manifests_source_document_id_source_documents_id_fk" FOREIGN KEY ("source_document_id") REFERENCES "public"."source_documents"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
CREATE UNIQUE INDEX "entities_kind_slug_idx" ON "entities" USING btree ("kind","slug");--> statement-breakpoint
CREATE INDEX "entities_parent_idx" ON "entities" USING btree ("parent_entity_id");--> statement-breakpoint
CREATE INDEX "entities_kind_idx" ON "entities" USING btree ("kind");--> statement-breakpoint
CREATE UNIQUE INDEX "admin_units_entity_idx" ON "administrative_units" USING btree ("entity_id");--> statement-breakpoint
CREATE INDEX "admin_units_federal_code_idx" ON "administrative_units" USING btree ("federal_code");--> statement-breakpoint
CREATE INDEX "admin_units_constituency_idx" ON "administrative_units" USING btree ("constituency_no");--> statement-breakpoint
CREATE UNIQUE INDEX "fiscal_transfers_unique_idx" ON "local_government_fiscal_transfers" USING btree ("local_level_entity_id","fiscal_year_bs","grant_type");--> statement-breakpoint
CREATE INDEX "fiscal_transfers_local_idx" ON "local_government_fiscal_transfers" USING btree ("local_level_entity_id");--> statement-breakpoint
CREATE INDEX "fiscal_transfers_fy_idx" ON "local_government_fiscal_transfers" USING btree ("fiscal_year_bs");--> statement-breakpoint
CREATE UNIQUE INDEX "census_facts_unique_idx" ON "census_facts" USING btree ("entity_id","indicator_slug","census_year_ad");--> statement-breakpoint
CREATE INDEX "census_facts_entity_idx" ON "census_facts" USING btree ("entity_id");--> statement-breakpoint
CREATE INDEX "census_facts_family_idx" ON "census_facts" USING btree ("indicator_family");--> statement-breakpoint
CREATE INDEX "census_facts_slug_idx" ON "census_facts" USING btree ("indicator_slug");--> statement-breakpoint
CREATE UNIQUE INDEX "banking_facts_unique_idx" ON "banking_sector_facts" USING btree ("bank_class","bank_entity_id","indicator_slug","reporting_period_bs","reporting_period_type");--> statement-breakpoint
CREATE INDEX "banking_facts_class_idx" ON "banking_sector_facts" USING btree ("bank_class");--> statement-breakpoint
CREATE INDEX "banking_facts_indicator_idx" ON "banking_sector_facts" USING btree ("indicator_slug");--> statement-breakpoint
CREATE INDEX "banking_facts_period_idx" ON "banking_sector_facts" USING btree ("reporting_period_ad_end");--> statement-breakpoint
CREATE INDEX "ocr_cells_tile_idx" ON "ocr_cell_extractions" USING btree ("tile_id");--> statement-breakpoint
CREATE INDEX "ocr_cells_region_idx" ON "ocr_cell_extractions" USING btree ("table_region_id");--> statement-breakpoint
CREATE INDEX "ocr_cells_seam_idx" ON "ocr_cell_extractions" USING btree ("near_tile_seam_px");--> statement-breakpoint
CREATE INDEX "ocr_disagreements_a_idx" ON "ocr_stitch_disagreements" USING btree ("cell_a_extraction_id");--> statement-breakpoint
CREATE INDEX "ocr_disagreements_b_idx" ON "ocr_stitch_disagreements" USING btree ("cell_b_extraction_id");--> statement-breakpoint
CREATE INDEX "ocr_tiles_run_idx" ON "ocr_tile_manifests" USING btree ("parser_run_id");--> statement-breakpoint
CREATE INDEX "ocr_tiles_page_idx" ON "ocr_tile_manifests" USING btree ("source_document_id","page_number");