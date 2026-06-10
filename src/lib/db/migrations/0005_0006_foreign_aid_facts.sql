CREATE TABLE "foreign_aid_facts" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"source_document_id" uuid NOT NULL,
	"base_indicator_slug" text NOT NULL,
	"base_indicator_name" text NOT NULL,
	"dimension_kind" text NOT NULL,
	"dimension_value" text NOT NULL,
	"dimension_label" text NOT NULL,
	"value" numeric(20, 4) NOT NULL,
	"unit" text NOT NULL,
	"reporting_period_type" "reporting_period_type" NOT NULL,
	"reporting_period_bs" text NOT NULL,
	"reporting_period_ad_start" timestamp with time zone,
	"reporting_period_ad_end" timestamp with time zone,
	"fiscal_year_bs" text,
	"fiscal_year_ad_label" text,
	"confidence_grade" "confidence_grade" DEFAULT 'B' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "foreign_aid_facts" ADD CONSTRAINT "foreign_aid_facts_source_document_id_source_documents_id_fk" FOREIGN KEY ("source_document_id") REFERENCES "public"."source_documents"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
CREATE UNIQUE INDEX "foreign_aid_facts_unique_idx" ON "foreign_aid_facts" USING btree ("base_indicator_slug","dimension_kind","dimension_value","reporting_period_bs","reporting_period_type","source_document_id");--> statement-breakpoint
CREATE INDEX "foreign_aid_facts_base_indicator_idx" ON "foreign_aid_facts" USING btree ("base_indicator_slug");--> statement-breakpoint
CREATE INDEX "foreign_aid_facts_dimension_idx" ON "foreign_aid_facts" USING btree ("dimension_kind","dimension_value");--> statement-breakpoint
CREATE INDEX "foreign_aid_facts_period_idx" ON "foreign_aid_facts" USING btree ("reporting_period_bs");