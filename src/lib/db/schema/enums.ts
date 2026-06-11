/**
 * Postgres enum definitions used across schemas.
 *
 * Centralizing them prevents drift — every place that talks about a
 * period type, a confidence grade, or a parser status refers to the same
 * literal union and the same Postgres enum.
 *
 * Reference: docs/CALENDAR_AND_PERIODS.md, docs/DATA_PIPELINE.md.
 */

import { pgEnum } from 'drizzle-orm/pg-core';

export const reportingPeriodTypeEnum = pgEnum('reporting_period_type', [
  'monthly',
  'quarterly',
  'annual',
  'nine_months_cumulative',
  'year_to_date',
  'daily',
  'seasonal',
]);

export type ReportingPeriodType = (typeof reportingPeriodTypeEnum.enumValues)[number];

export const confidenceGradeEnum = pgEnum('confidence_grade', ['A', 'B', 'C']);
export type ConfidenceGrade = (typeof confidenceGradeEnum.enumValues)[number];

/**
 * Epistemic status of an indicator value — orthogonal to confidence_grade
 * (which is about source authority). A WEO debt forecast is confidence A AND
 * observation_type 'projection'. Default 'actual' for every directly published
 * value. See ADR-0025.
 *   - actual        — directly published / measured
 *   - projection    — forward-looking forecast (IMF WEO out-years)
 *   - interpolated  — filled between observed anchors (WB PIP fill_gaps)
 *   - estimate      — model-derived where no direct observation (ILO modelled)
 *   - provisional   — published but flagged by source as subject to revision
 */
export const observationTypeEnum = pgEnum('observation_type', [
  'actual',
  'projection',
  'interpolated',
  'estimate',
  'provisional',
]);
export type ObservationType = (typeof observationTypeEnum.enumValues)[number];

export const storageProviderEnum = pgEnum('storage_provider', ['supabase', 'r2']);
export type StorageProvider = (typeof storageProviderEnum.enumValues)[number];

export const publicationFrequencyEnum = pgEnum('publication_frequency', [
  'monthly',
  'quarterly',
  'annual',
  'daily',
  'seasonal',
  'ad_hoc',
]);
export type PublicationFrequency = (typeof publicationFrequencyEnum.enumValues)[number];

export const fileFormatEnum = pgEnum('file_format', [
  'pdf',
  'csv',
  'xlsx',
  'xls',
  'html',
  'json',
  'xml',
]);
export type FileFormat = (typeof fileFormatEnum.enumValues)[number];

export const licenseStatusEnum = pgEnum('license_status', [
  'public_domain',
  'gov_open',
  'cc_by',
  'cc_by_nc_sa',
  'proprietary',
  'unclear',
]);
export type LicenseStatus = (typeof licenseStatusEnum.enumValues)[number];

export const sourceStatusEnum = pgEnum('source_status', ['active', 'paused', 'deprecated']);
export type SourceStatus = (typeof sourceStatusEnum.enumValues)[number];

export const parserStatusEnum = pgEnum('parser_status', ['success', 'partial', 'failure']);
export type ParserStatus = (typeof parserStatusEnum.enumValues)[number];

export const parserErrorClassEnum = pgEnum('parser_error_class', [
  'ColumnMissing',
  'RegexMismatch',
  'UnitAmbiguous',
  'PageLayoutChanged',
  'PeriodAmbiguous',
  'ValueUnparseable',
  'EncodingError',
  'Other',
]);
export type ParserErrorClass = (typeof parserErrorClassEnum.enumValues)[number];

export const dataQualityFlagTypeEnum = pgEnum('data_quality_flag_type', [
  'SchemaInvalid',
  'PeriodAmbiguous',
  'UnitUnrecognized',
  'DuplicateOfApproved',
  'RevisionMismatch',
  'ValueOutOfPlausibleRange',
  'IndicatorUnknown',
  'SourceHashCollision',
]);
export type DataQualityFlagType = (typeof dataQualityFlagTypeEnum.enumValues)[number];

export const flagSeverityEnum = pgEnum('flag_severity', ['blocking', 'warning']);
export type FlagSeverity = (typeof flagSeverityEnum.enumValues)[number];

export const indicatorCategoryEnum = pgEnum('indicator_category', [
  'price',
  'monetary',
  'fiscal',
  'external_sector',
  'real_sector',
  'banking',
  'capital_markets',
  'labour',
  'tourism',
  'agriculture',
  'energy',
  'land',
  'demographic',
  'composite',
]);
export type IndicatorCategory = (typeof indicatorCategoryEnum.enumValues)[number];

// ─── Added in migration 0002 ──────────────────────────────────────

/**
 * How a source is ingested. Distinguishes automated scrapers from manual
 * uploads (typical for PDFs needing OCR) and from reference-only assets
 * we cite but don't parse into approved_indicator_values.
 */
export const ingestionModeEnum = pgEnum('ingestion_mode', [
  'automated_cron',
  'manual_upload',
  'reference_only',
]);
export type IngestionMode = (typeof ingestionModeEnum.enumValues)[number];

/**
 * Kinds of entity tracked. Banks, public enterprises, local levels,
 * cooperatives, business groups, ministries, donors all live in the
 * single `entities` dimension.
 */
export const entityKindEnum = pgEnum('entity_kind', [
  'bank',
  'public_enterprise',
  'local_level',
  'district',
  'province',
  'cooperative',
  'business_group',
  'ministry',
  'department',
  'donor',
  'constituency',
  'ward',
  'polling_station',
]);
export type EntityKind = (typeof entityKindEnum.enumValues)[number];

/**
 * Federal fiscal transfer types (per intergovernmental fiscal transfer
 * standard chart of accounts). The bracketed budget head codes are the
 * canonical Nepal Govt budget heads — kept inline for traceability.
 */
export const grantTypeEnum = pgEnum('grant_type', [
  'equalization_minimum',
  'equalization_formula',
  'equalization_performance',
  'conditional_current',
  'conditional_capital',
  'special_current',
  'special_capital',
  'complementary_capital',
]);
export type GrantType = (typeof grantTypeEnum.enumValues)[number];

/**
 * Local-level type per Nepal's federal structure. Numbers in parens are
 * the constitutional counts (753 = 6 metro + 11 sub-metro + 276 muni + 460 rural).
 */
export const localLevelTypeEnum = pgEnum('local_level_type', [
  'metropolitan_city',
  'sub_metropolitan_city',
  'municipality',
  'rural_municipality',
]);
export type LocalLevelType = (typeof localLevelTypeEnum.enumValues)[number];

/**
 * Bank class per NRB BFI structure. Matches the C-series sheets in the
 * monthly Banking & Financial Statistics XLSX.
 */
export const bankClassEnum = pgEnum('bank_class', [
  'commercial',
  'development',
  'finance',
  'microfinance',
  'infrastructure',
  'system_total',
]);
export type BankClass = (typeof bankClassEnum.enumValues)[number];

/**
 * Census 2021 indicator family. Mirrors the NPHC 2021 CSV file groupings
 * (Hhld* household, Indv* individual).
 */
export const censusIndicatorFamilyEnum = pgEnum('census_indicator_family', [
  'household_housing',
  'household_facility',
  'household_economic',
  'household_demographic',
  'individual_demographic',
  'individual_education',
  'individual_economic',
  'individual_migration',
  'individual_fertility',
]);
export type CensusIndicatorFamily = (typeof censusIndicatorFamilyEnum.enumValues)[number];

/**
 * Resolution rule applied when overlapping OCR tiles produce different
 * text for the same spatial cell. Tracked in ocr_stitch_disagreements.
 */
export const stitchResolutionEnum = pgEnum('stitch_resolution', [
  'kept_higher_confidence',
  'kept_left_tile',
  'kept_right_tile',
  'flagged_for_review',
]);
export type StitchResolution = (typeof stitchResolutionEnum.enumValues)[number];

// ─── Added in migration 0006 — government audit fact domain (ADR-0024) ──

/**
 * The class of audited subject the OAG report covers. Despite the "tier"
 * intuition, these are subject CLASSES, not only government tiers —
 * corporations, constitutional bodies, and committees/boards are audited
 * alongside the three government tiers. Extending this set = future ADR.
 */
export const auditSubjectClassEnum = pgEnum('audit_subject_class', [
  'federal_government',
  'provincial_government',
  'local_government',
  'public_corporation',
  'constitutional_body',
  'committee_board_authority',
  'other_institution',
]);
export type AuditSubjectClass = (typeof auditSubjectClassEnum.enumValues)[number];

/**
 * OAG's classification of an irregularity (beruju). Canonical Nepali audit
 * taxonomy; `other` is the escape hatch for labels not yet mapped (the exact
 * source label is preserved in `beruju_category_label_raw`). Extending = ADR.
 */
export const berujuCategoryEnum = pgEnum('beruju_category', [
  'recoverable', // असुल उपर गर्नुपर्ने (incl. embezzlement, loss/damage)
  'irregular', // अनियमित (to-regularize: irregular)
  'evidence_not_submitted', // प्रमाण कागजात पेश नभएको
  'advance_outstanding', // पेश्की बाँकी (peski)
  'revenue_arrears', // राजस्व / धरौटी बक्यौता
  'responsibility_not_transferred', // जिम्मेवारी नसारिएको
  'other',
]);
export type BerujuCategory = (typeof berujuCategoryEnum.enumValues)[number];

/**
 * WHICH amount a beruju line/finding describes. A single category can recur
 * across bases — e.g. an entity's `recoverable` beruju has a current-year
 * raised amount, a settled amount, and a cumulative-outstanding amount.
 */
export const auditAmountBasisEnum = pgEnum('audit_amount_basis', [
  'current_year_raised', // यो वर्ष कायम
  'settled_this_year', // फर्स्यौट / सम्परीक्षण
  'cumulative_outstanding', // अद्यावधिक बाँकी
  'opening_outstanding', // गत वर्षसम्मको बाँकी
  'adjustment', // समायोजन / पुनर्वर्गीकरण
  'other',
]);
export type AuditAmountBasis = (typeof auditAmountBasisEnum.enumValues)[number];

/**
 * How a fact row's values were extracted from the source PDF. Drives the
 * confidence grade and post-hoc auditability (text_layer → A; surya_ocr → B
 * until human-verified). Mirrors the tiered-recovery doctrine (ADR-0021).
 */
export const extractionMethodEnum = pgEnum('extraction_method', [
  'text_layer', // Tier 0 — born-digital pdfplumber text
  'preeti_fix', // Tier 1 — legacy-encoding / geometry repair
  'surya_ocr', // Tier 2 — Surya OCR on scanned pages
  'manual_review', // hand-entered / corrected by a reviewer
]);
export type ExtractionMethod = (typeof extractionMethodEnum.enumValues)[number];

/**
 * Human-review state of a fact row. Defaults to `unreviewed` so OCR-derived
 * rows never imply false confidence; promotion gates check this column.
 */
export const reviewStatusEnum = pgEnum('review_status', [
  'unreviewed',
  'auto_accepted',
  'human_verified',
  'flagged',
]);
export type ReviewStatus = (typeof reviewStatusEnum.enumValues)[number];
