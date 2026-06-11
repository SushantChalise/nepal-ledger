CREATE TYPE "public"."aggregation_role" AS ENUM('detail', 'subtotal', 'grand_total');--> statement-breakpoint
CREATE TYPE "public"."audit_paragraph_status" AS ENUM('issued', 'settled_on_response', 'carried_forward', 'remaining');--> statement-breakpoint
CREATE TYPE "public"."audit_stock_type" AS ENUM('audit_backlog', 'revenue_arrears', 'foreign_grant_reimbursable', 'foreign_loan_reimbursable', 'overdue_principal', 'overdue_interest', 'other');--> statement-breakpoint
CREATE TYPE "public"."value_origin" AS ENUM('printed', 'computed');--> statement-breakpoint
CREATE TABLE "audit_financial_stocks" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"audited_entity_id" uuid,
	"audit_subject_class" "audit_subject_class" NOT NULL,
	"aggregate_scope" text,
	"fiscal_year_bs" text NOT NULL,
	"stock_type" "audit_stock_type" NOT NULL,
	"opening_npr" numeric(20, 2),
	"opening_raw" text,
	"addition_npr" numeric(20, 2),
	"addition_raw" text,
	"settlement_npr" numeric(20, 2),
	"settlement_raw" text,
	"adjustment_npr" numeric(20, 2),
	"adjustment_raw" text,
	"closing_npr" numeric(20, 2),
	"closing_raw" text,
	"source_unit" text,
	"source_scale" numeric(20, 6),
	"source_table_code" text NOT NULL,
	"source_row_label" text,
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
	CONSTRAINT "audit_financial_stocks_unique" UNIQUE NULLS NOT DISTINCT("source_document_id","audit_subject_class","audited_entity_id","aggregate_scope","fiscal_year_bs","stock_type")
);
--> statement-breakpoint
CREATE TABLE "audit_paragraph_metrics" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"audited_entity_id" uuid,
	"audit_subject_class" "audit_subject_class" NOT NULL,
	"aggregate_scope" text,
	"fiscal_year_bs" text NOT NULL,
	"paragraph_status" "audit_paragraph_status" NOT NULL,
	"paragraph_count" integer,
	"amount_npr" numeric(20, 2),
	"amount_raw" text,
	"source_unit" text,
	"source_scale" numeric(20, 6),
	"source_table_code" text NOT NULL,
	"source_row_label" text,
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
	CONSTRAINT "audit_paragraph_metrics_unique" UNIQUE NULLS NOT DISTINCT("source_document_id","audit_subject_class","audited_entity_id","aggregate_scope","fiscal_year_bs","paragraph_status")
);
--> statement-breakpoint
CREATE TABLE "beruju_categories" (
	"code" text PRIMARY KEY NOT NULL,
	"main_category" text NOT NULL,
	"name_en" text NOT NULL,
	"name_ne" text,
	"act_reference" text,
	"display_order" integer NOT NULL
);
--> statement-breakpoint
ALTER TABLE "audit_beruju_lines" DROP CONSTRAINT "audit_beruju_lines_unique";--> statement-breakpoint
ALTER TABLE "audit_beruju_lines" ALTER COLUMN "beruju_category" SET DATA TYPE text;--> statement-breakpoint
ALTER TABLE "audit_findings" ALTER COLUMN "beruju_category" SET DATA TYPE text;--> statement-breakpoint
ALTER TABLE "audit_beruju_lines" ADD COLUMN "source_row_label" text;--> statement-breakpoint
ALTER TABLE "audit_beruju_lines" ADD COLUMN "aggregation_role" "aggregation_role" DEFAULT 'detail' NOT NULL;--> statement-breakpoint
ALTER TABLE "audit_beruju_lines" ADD COLUMN "value_origin" "value_origin" DEFAULT 'printed' NOT NULL;--> statement-breakpoint
ALTER TABLE "audit_beruju_lines" ADD COLUMN "source_table_code" text NOT NULL;--> statement-breakpoint
ALTER TABLE "audit_financial_stocks" ADD CONSTRAINT "audit_financial_stocks_audited_entity_id_entities_id_fk" FOREIGN KEY ("audited_entity_id") REFERENCES "public"."entities"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "audit_financial_stocks" ADD CONSTRAINT "audit_financial_stocks_source_document_id_source_documents_id_fk" FOREIGN KEY ("source_document_id") REFERENCES "public"."source_documents"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "audit_financial_stocks" ADD CONSTRAINT "audit_financial_stocks_ocr_cell_extraction_id_ocr_cell_extractions_id_fk" FOREIGN KEY ("ocr_cell_extraction_id") REFERENCES "public"."ocr_cell_extractions"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "audit_paragraph_metrics" ADD CONSTRAINT "audit_paragraph_metrics_audited_entity_id_entities_id_fk" FOREIGN KEY ("audited_entity_id") REFERENCES "public"."entities"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "audit_paragraph_metrics" ADD CONSTRAINT "audit_paragraph_metrics_source_document_id_source_documents_id_fk" FOREIGN KEY ("source_document_id") REFERENCES "public"."source_documents"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "audit_paragraph_metrics" ADD CONSTRAINT "audit_paragraph_metrics_ocr_cell_extraction_id_ocr_cell_extractions_id_fk" FOREIGN KEY ("ocr_cell_extraction_id") REFERENCES "public"."ocr_cell_extractions"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "audit_financial_stocks_fy_idx" ON "audit_financial_stocks" USING btree ("fiscal_year_bs");--> statement-breakpoint
CREATE INDEX "audit_financial_stocks_type_idx" ON "audit_financial_stocks" USING btree ("stock_type");--> statement-breakpoint
CREATE INDEX "audit_financial_stocks_entity_idx" ON "audit_financial_stocks" USING btree ("audited_entity_id");--> statement-breakpoint
CREATE INDEX "audit_paragraph_metrics_fy_idx" ON "audit_paragraph_metrics" USING btree ("fiscal_year_bs");--> statement-breakpoint
CREATE INDEX "audit_paragraph_metrics_entity_idx" ON "audit_paragraph_metrics" USING btree ("audited_entity_id");--> statement-breakpoint
ALTER TABLE "audit_beruju_lines" ADD CONSTRAINT "audit_beruju_lines_beruju_category_beruju_categories_code_fk" FOREIGN KEY ("beruju_category") REFERENCES "public"."beruju_categories"("code") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "audit_findings" ADD CONSTRAINT "audit_findings_beruju_category_beruju_categories_code_fk" FOREIGN KEY ("beruju_category") REFERENCES "public"."beruju_categories"("code") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "audit_beruju_lines" ADD CONSTRAINT "audit_beruju_lines_unique" UNIQUE NULLS NOT DISTINCT("source_document_id","audit_subject_class","audited_entity_id","aggregate_scope","fiscal_year_bs","amount_basis","beruju_category","aggregation_role","source_table_code");--> statement-breakpoint
-- Seed the OAG beruju taxonomy (ADR-0027). English labels are verbatim from the
-- report's classification (58th, p33); Nepali labels are deferred to the Nepali
-- edition (left NULL rather than fabricate). The three bare main-category codes
-- (recoverable / to_be_regularized / advance) tag ungrouped + subtotal rows.
INSERT INTO "beruju_categories" ("code","main_category","name_en","display_order") VALUES
	('recoverable','recoverable','Recoverable',10),
	('rec_embezzled_falsified','recoverable','Embezzled and falsified',11),
	('rec_loss_damage','recoverable','Loss and damage',12),
	('rec_other','recoverable','Other recoverable',13),
	('to_be_regularized','to_be_regularized','To be regularized',20),
	('tbr_irregular','to_be_regularized','Irregular (non-compliance)',21),
	('tbr_evidence_not_submitted','to_be_regularized','Evidences/documents not submitted (unsubstantiated)',22),
	('tbr_balance_not_brought_forward','to_be_regularized','Balance not brought forward',23),
	('tbr_reimbursement_not_received','to_be_regularized','Reimbursement not received',24),
	('advance','advance','Advance',30),
	('adv_staff','advance','Staff advance',31),
	('adv_mobilization','advance','Mobilization advance',32),
	('adv_other_institutional','advance','Other institutional advance',33),
	('other','other','Other',99);