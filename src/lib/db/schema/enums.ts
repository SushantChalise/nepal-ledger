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
