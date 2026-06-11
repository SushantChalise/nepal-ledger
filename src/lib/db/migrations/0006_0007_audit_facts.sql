CREATE TYPE "public"."audit_amount_basis" AS ENUM('current_year_raised', 'settled_this_year', 'cumulative_outstanding', 'opening_outstanding', 'adjustment', 'other');--> statement-breakpoint
CREATE TYPE "public"."audit_subject_class" AS ENUM('federal_government', 'provincial_government', 'local_government', 'public_corporation', 'constitutional_body', 'committee_board_authority', 'other_institution');--> statement-breakpoint
CREATE TYPE "public"."beruju_category" AS ENUM('recoverable', 'irregular', 'evidence_not_submitted', 'advance_outstanding', 'revenue_arrears', 'responsibility_not_transferred', 'other');--> statement-breakpoint
CREATE TYPE "public"."extraction_method" AS ENUM('text_layer', 'preeti_fix', 'surya_ocr', 'manual_review');--> statement-breakpoint
CREATE TYPE "public"."review_status" AS ENUM('unreviewed', 'auto_accepted', 'human_verified', 'flagged');--> statement-breakpoint
CREATE TABLE "audit_beruju_lines" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"audited_entity_id" uuid,
	"audit_subject_class" "audit_subject_class" NOT NULL,
	"aggregate_scope" text,
	"fiscal_year_bs" text NOT NULL,
	"amount_basis" "audit_amount_basis" NOT NULL,
	"beruju_category" "beruju_category" NOT NULL,
	"beruju_category_label_raw" text,
	"amount_npr" numeric(20, 2) NOT NULL,
	"amount_raw" text,
	"source_unit" text,
	"source_scale" numeric(20, 6),
	"source_page" integer,
	"source_table_ref" text,
	"source_cell_ref" text,
	"source_document_id" uuid NOT NULL,
	"source_precedence" smallint NOT NULL,
	"extraction_method" "extraction_method" NOT NULL,
	"ocr_cell_extraction_id" uuid,
	"review_status" "review_status" DEFAULT 'unreviewed' NOT NULL,
	"confidence_grade" "confidence_grade" NOT NULL,
	"promoted_at" timestamp with time zone DEFAULT now() NOT NULL,
	"promoted_by" text NOT NULL,
	"notes" text,
	CONSTRAINT "audit_beruju_lines_unique" UNIQUE NULLS NOT DISTINCT("audit_subject_class","audited_entity_id","aggregate_scope","fiscal_year_bs","amount_basis","beruju_category")
);
--> statement-breakpoint
CREATE TABLE "audit_entity_summaries" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"audited_entity_id" uuid,
	"audit_subject_class" "audit_subject_class" NOT NULL,
	"aggregate_scope" text,
	"aggregate_label_raw" text,
	"fiscal_year_bs" text NOT NULL,
	"audited_amount_npr" numeric(20, 2),
	"audited_amount_raw" text,
	"beruju_raised_npr" numeric(20, 2),
	"beruju_raised_raw" text,
	"settled_this_year_npr" numeric(20, 2),
	"settled_this_year_raw" text,
	"cumulative_outstanding_npr" numeric(20, 2),
	"cumulative_outstanding_raw" text,
	"source_unit" text,
	"source_scale" numeric(20, 6),
	"source_page" integer,
	"source_table_ref" text,
	"source_cell_ref" text,
	"source_document_id" uuid NOT NULL,
	"source_precedence" smallint NOT NULL,
	"extraction_method" "extraction_method" NOT NULL,
	"ocr_cell_extraction_id" uuid,
	"review_status" "review_status" DEFAULT 'unreviewed' NOT NULL,
	"confidence_grade" "confidence_grade" NOT NULL,
	"promoted_at" timestamp with time zone DEFAULT now() NOT NULL,
	"promoted_by" text NOT NULL,
	"notes" text,
	CONSTRAINT "audit_summaries_unique" UNIQUE NULLS NOT DISTINCT("audit_subject_class","audited_entity_id","aggregate_scope","fiscal_year_bs")
);
--> statement-breakpoint
CREATE TABLE "audit_findings" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"audited_entity_id" uuid,
	"audit_subject_class" "audit_subject_class" NOT NULL,
	"fiscal_year_bs" text NOT NULL,
	"beruju_category" "beruju_category",
	"amount_basis" "audit_amount_basis",
	"finding_ordinal" integer NOT NULL,
	"para_ref" text,
	"source_section_path" text,
	"source_page_start" integer,
	"source_page_end" integer,
	"source_locator_hash" text NOT NULL,
	"source_table_ref" text,
	"title_en" text,
	"title_ne" text,
	"narrative_en" text,
	"narrative_ne" text,
	"amount_npr" numeric(20, 2),
	"amount_raw" text,
	"source_unit" text,
	"recommendation_en" text,
	"recommendation_ne" text,
	"source_document_id" uuid NOT NULL,
	"source_precedence" smallint NOT NULL,
	"extraction_method" "extraction_method" NOT NULL,
	"ocr_cell_extraction_id" uuid,
	"review_status" "review_status" DEFAULT 'unreviewed' NOT NULL,
	"confidence_grade" "confidence_grade" NOT NULL,
	"promoted_at" timestamp with time zone DEFAULT now() NOT NULL,
	"promoted_by" text NOT NULL,
	"notes" text,
	CONSTRAINT "audit_findings_ordinal_unique" UNIQUE NULLS NOT DISTINCT("source_document_id","audited_entity_id","fiscal_year_bs","finding_ordinal")
);
--> statement-breakpoint
ALTER TABLE "audit_beruju_lines" ADD CONSTRAINT "audit_beruju_lines_audited_entity_id_entities_id_fk" FOREIGN KEY ("audited_entity_id") REFERENCES "public"."entities"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "audit_beruju_lines" ADD CONSTRAINT "audit_beruju_lines_source_document_id_source_documents_id_fk" FOREIGN KEY ("source_document_id") REFERENCES "public"."source_documents"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "audit_beruju_lines" ADD CONSTRAINT "audit_beruju_lines_ocr_cell_extraction_id_ocr_cell_extractions_id_fk" FOREIGN KEY ("ocr_cell_extraction_id") REFERENCES "public"."ocr_cell_extractions"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "audit_entity_summaries" ADD CONSTRAINT "audit_entity_summaries_audited_entity_id_entities_id_fk" FOREIGN KEY ("audited_entity_id") REFERENCES "public"."entities"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "audit_entity_summaries" ADD CONSTRAINT "audit_entity_summaries_source_document_id_source_documents_id_fk" FOREIGN KEY ("source_document_id") REFERENCES "public"."source_documents"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "audit_entity_summaries" ADD CONSTRAINT "audit_entity_summaries_ocr_cell_extraction_id_ocr_cell_extractions_id_fk" FOREIGN KEY ("ocr_cell_extraction_id") REFERENCES "public"."ocr_cell_extractions"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "audit_findings" ADD CONSTRAINT "audit_findings_audited_entity_id_entities_id_fk" FOREIGN KEY ("audited_entity_id") REFERENCES "public"."entities"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "audit_findings" ADD CONSTRAINT "audit_findings_source_document_id_source_documents_id_fk" FOREIGN KEY ("source_document_id") REFERENCES "public"."source_documents"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "audit_findings" ADD CONSTRAINT "audit_findings_ocr_cell_extraction_id_ocr_cell_extractions_id_fk" FOREIGN KEY ("ocr_cell_extraction_id") REFERENCES "public"."ocr_cell_extractions"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "audit_beruju_lines_entity_idx" ON "audit_beruju_lines" USING btree ("audited_entity_id");--> statement-breakpoint
CREATE INDEX "audit_beruju_lines_fy_idx" ON "audit_beruju_lines" USING btree ("fiscal_year_bs");--> statement-breakpoint
CREATE INDEX "audit_beruju_lines_category_idx" ON "audit_beruju_lines" USING btree ("beruju_category");--> statement-breakpoint
CREATE INDEX "audit_beruju_lines_basis_idx" ON "audit_beruju_lines" USING btree ("amount_basis");--> statement-breakpoint
CREATE INDEX "audit_summaries_entity_idx" ON "audit_entity_summaries" USING btree ("audited_entity_id");--> statement-breakpoint
CREATE INDEX "audit_summaries_fy_idx" ON "audit_entity_summaries" USING btree ("fiscal_year_bs");--> statement-breakpoint
CREATE INDEX "audit_summaries_class_idx" ON "audit_entity_summaries" USING btree ("audit_subject_class");--> statement-breakpoint
CREATE UNIQUE INDEX "audit_findings_locator_unique" ON "audit_findings" USING btree ("source_document_id","source_locator_hash");--> statement-breakpoint
CREATE INDEX "audit_findings_entity_idx" ON "audit_findings" USING btree ("audited_entity_id");--> statement-breakpoint
CREATE INDEX "audit_findings_fy_idx" ON "audit_findings" USING btree ("fiscal_year_bs");--> statement-breakpoint
CREATE INDEX "audit_findings_category_idx" ON "audit_findings" USING btree ("beruju_category");