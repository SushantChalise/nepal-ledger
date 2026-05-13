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
