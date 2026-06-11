CREATE TYPE "public"."migration_destination_region" AS ENUM('india', 'saarc_other', 'asean', 'middle_east', 'other_asia', 'europe', 'africa', 'americas', 'other');--> statement-breakpoint
CREATE TYPE "public"."migration_permit_category" AS ENUM('new_individual', 'reentry', 'recruitment_agency', 'g2g');--> statement-breakpoint
CREATE TYPE "public"."migration_sex" AS ENUM('male', 'female', 'total');--> statement-breakpoint
CREATE TYPE "public"."migration_skill_class" AS ENUM('unskilled', 'semi_skilled', 'skilled', 'highly_skilled', 'professional');--> statement-breakpoint
CREATE TABLE "migration_permit_facts" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"fiscal_year_bs" text NOT NULL,
	"month_num" integer,
	"destination_country" text,
	"destination_region" "migration_destination_region",
	"origin_entity_id" uuid,
	"skill_class" "migration_skill_class",
	"permit_category" "migration_permit_category",
	"sex" "migration_sex" NOT NULL,
	"permits" numeric(20, 0) NOT NULL,
	"unit" text DEFAULT 'permits' NOT NULL,
	"source_document_id" uuid NOT NULL,
	"confidence_grade" "confidence_grade" DEFAULT 'A' NOT NULL,
	"promoted_at" timestamp with time zone DEFAULT now() NOT NULL,
	"promoted_by" text NOT NULL,
	CONSTRAINT "migration_permit_facts_unique" UNIQUE NULLS NOT DISTINCT("fiscal_year_bs","month_num","destination_country","destination_region","origin_entity_id","skill_class","permit_category","sex")
);
--> statement-breakpoint
ALTER TABLE "migration_permit_facts" ADD CONSTRAINT "migration_permit_facts_origin_entity_id_entities_id_fk" FOREIGN KEY ("origin_entity_id") REFERENCES "public"."entities"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "migration_permit_facts" ADD CONSTRAINT "migration_permit_facts_source_document_id_source_documents_id_fk" FOREIGN KEY ("source_document_id") REFERENCES "public"."source_documents"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "migration_permit_facts_fy_idx" ON "migration_permit_facts" USING btree ("fiscal_year_bs");--> statement-breakpoint
CREATE INDEX "migration_permit_facts_origin_idx" ON "migration_permit_facts" USING btree ("origin_entity_id");--> statement-breakpoint
CREATE INDEX "migration_permit_facts_region_idx" ON "migration_permit_facts" USING btree ("destination_region");--> statement-breakpoint
CREATE INDEX "migration_permit_facts_country_idx" ON "migration_permit_facts" USING btree ("destination_country");