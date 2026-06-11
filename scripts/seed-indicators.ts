/**
 * Seed the indicator catalogue + controlled unit vocabulary.
 *
 * Three tables, in dependency order:
 *   1. `indicator_units`     — the controlled vocabulary the validator checks
 *                              a staging row's `unit` against (lowercase
 *                              snake_case, matching what the deterministic
 *                              Python parsers emit verbatim).
 *   2. `indicators`          — the canonical concepts (slug → name/category/
 *                              unit). The validator resolves a staging row's
 *                              `indicator_slug_raw` against this table.
 *   3. `indicator_source_map`— links each indicator to the source(s) that
 *                              feed it (here: nrb-cmefs-monthly).
 *
 * Without these rows the validation job blocks every CMEFs staging row with
 * IndicatorUnknown + UnitUnrecognized (see docs/DATA_PIPELINE.md §"The
 * Validation Job"). Seeding them unblocks promotion to
 * `approved_indicator_values`.
 *
 * Idempotent: units + indicators upsert on their natural keys; the
 * source-map link is read-then-write (repo handles existence).
 *
 * Usage:
 *   pnpm seed:indicators --dry-run    # no DB; prints what would be written
 *   pnpm seed:indicators              # requires DATABASE_URL (.env.local)
 */

import process from 'node:process';

import type { IndicatorCategory } from '@/lib/db/schema/enums';
import type { NewIndicatorRow } from '@/lib/db/schema/indicators';
import type { NewIndicatorUnitRow } from '@/lib/db/schema/indicators';

const CMEFS_SOURCE_ID = 'nrb-cmefs-monthly';
const NCPI_SOURCE_ID = 'nrb-ncpi-table';
const DNE_SOURCE_ID = 'nrb-dne-xlsx';
const FCGO_SOURCE_ID = 'fcgo-consolidated-financial-statements';
const ECONOMIC_SURVEY_SOURCE_ID = 'mof-economic-survey-annual';
const WDI_SOURCE_ID = 'wb-wdi';
const WEO_SOURCE_ID = 'imf-weo';
const PIP_SOURCE_ID = 'wb-pip';

// FCGO Consolidated Financial Statements — audited all-of-government fiscal
// outturn (scrapers/fcgo_consolidated). Headline annual aggregates, NPR
// million. Category 'fiscal'. Verified FY 2079/80: total revenue 1,506,321.5.
const FCGO_INDICATORS: readonly SeedIndicator[] = [
  {
    slug: 'fcgo-total-revenue-outturn-annual',
    nameEn: 'Total Revenue Outturn (consolidated)',
    category: 'fiscal',
    unit: 'npr_million',
    nativeFrequency: 'annual',
    sourceAgency: 'Financial Comptroller General Office',
  },
  {
    slug: 'fcgo-total-expenditure-outturn-annual',
    nameEn: 'Total Expenditure Outturn (consolidated)',
    category: 'fiscal',
    unit: 'npr_million',
    nativeFrequency: 'annual',
    sourceAgency: 'Financial Comptroller General Office',
  },
  {
    slug: 'fcgo-recurrent-expenditure-outturn-annual',
    nameEn: 'Recurrent Expenditure Outturn (consolidated)',
    category: 'fiscal',
    unit: 'npr_million',
    nativeFrequency: 'annual',
    sourceAgency: 'Financial Comptroller General Office',
  },
  {
    slug: 'fcgo-capital-expenditure-outturn-annual',
    nameEn: 'Capital Expenditure Outturn (consolidated)',
    category: 'fiscal',
    unit: 'npr_million',
    nativeFrequency: 'annual',
    sourceAgency: 'Financial Comptroller General Office',
  },
  {
    slug: 'fcgo-provincial-expenditure-consolidated-annual',
    nameEn: 'Provincial Expenditure (consolidated)',
    category: 'fiscal',
    unit: 'npr_million',
    nativeFrequency: 'annual',
    sourceAgency: 'Financial Comptroller General Office',
  },
  {
    slug: 'fcgo-local-level-expenditure-consolidated-annual',
    nameEn: 'Local-Level Expenditure (consolidated)',
    category: 'fiscal',
    unit: 'npr_million',
    nativeFrequency: 'annual',
    sourceAgency: 'Financial Comptroller General Office',
  },
];

// MoF Economic Survey — Annex 6.1 (Number of Workers having Foreign Employment
// Permit), the one cleanly-parseable annex table (ADR-0016; EN 2023/24 edition).
// The headline macro annex is RTL-mirrored and the Nepali editions are
// CID-broken, so GDP/CPI/fiscal series are deferred. Category 'labour'; unit
// 'count'; annual. Verified FY2079/80 total = 494,224 (female + male = total).
const ECONOMIC_SURVEY_INDICATORS: readonly SeedIndicator[] = [
  {
    slug: 'economic-survey-foreign-employment-permits-total',
    nameEn: 'Foreign Employment Permits Issued (Total)',
    category: 'labour',
    unit: 'count',
    nativeFrequency: 'annual',
    sourceAgency: 'Ministry of Finance',
  },
  {
    slug: 'economic-survey-foreign-employment-permits-female',
    nameEn: 'Foreign Employment Permits Issued (Female)',
    category: 'labour',
    unit: 'count',
    nativeFrequency: 'annual',
    sourceAgency: 'Ministry of Finance',
  },
  {
    slug: 'economic-survey-foreign-employment-permits-male',
    nameEn: 'Foreign Employment Permits Issued (Male)',
    category: 'labour',
    unit: 'count',
    nativeFrequency: 'annual',
    sourceAgency: 'Ministry of Finance',
  },
];

// DNE single-series indicators (ADR-0014): ONLY genuinely single-dimensional
// DNE series are registered here. The DNE dimensional matrices (Foreign Trade
// by commodity, Remittance by country/district) and the messy auto-prefixed
// reserve components are NOT registered — they await a dimensional model. The
// tourist-arrival series is one clean indicator (monthly total arrivals).
const DNE_INDICATORS: readonly SeedIndicator[] = [
  {
    slug: 'dne-tourist-arrival',
    nameEn: 'Tourist Arrivals (monthly)',
    category: 'tourism',
    unit: 'count',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // Real-sector + price headline series (parser nrb_dne v0.6.0 — National
  // Accounts + CPI). GDP is npr_billion (sheet unit "Rs. in billion", ADR-0011).
  {
    slug: 'dne-gdp-nominal',
    nameEn: "Nominal GDP (at producers' price)",
    category: 'real_sector',
    unit: 'npr_billion',
    nativeFrequency: 'annual',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'dne-gdp-real',
    nameEn: "Real GDP (at purchasers' price)",
    category: 'real_sector',
    unit: 'npr_billion',
    nativeFrequency: 'annual',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'dne-gdp-real-growth',
    nameEn: "Real GDP Growth Rate (at purchasers' price)",
    category: 'real_sector',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'dne-gdp-per-capita-usd',
    nameEn: 'Per Capita GDP (USD)',
    category: 'real_sector',
    unit: 'usd',
    nativeFrequency: 'annual',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'dne-gdp-deflator',
    nameEn: 'GDP Deflator',
    category: 'real_sector',
    unit: 'index_points',
    nativeFrequency: 'annual',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'dne-cpi',
    nameEn: 'National Consumer Price Index — Overall',
    category: 'price',
    unit: 'index_points',
    nativeFrequency: 'annual',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'dne-inflation-rate',
    nameEn: 'Consumer Price Inflation — Overall',
    category: 'price',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // Remittance inflow (BoP BPM6 Personal transfers, Credit) — the "Money In"
  // cornerstone. parser nrb_dne v0.8.0. npr_million, annual (full-FY July
  // cumulative). ADR-0011: FY2081/82 = 1,731,270 = NPR 1.73 trillion.
  {
    slug: 'dne-remittance-inflow',
    nameEn: 'Remittance Inflow (personal transfers, BPM6)',
    category: 'external_sector',
    unit: 'npr_million',
    nativeFrequency: 'annual',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // Historical BPM5 remittance back-series (parser nrb_bop v0.1.0).
  // Covers FY2000/01–FY2023/24P. NOT directly comparable to dne-remittance-inflow
  // (BPM6). Charts that join both series MUST show a break at FY2069/70 (AD2012/13).
  {
    slug: 'remittance-inflow-bpm5',
    nameEn: "Workers' Remittances Inflow (BPM5 historical)",
    category: 'external_sector',
    unit: 'npr_million',
    nativeFrequency: 'annual',
    sourceAgency: 'Nepal Rastra Bank',
  },
];

// ─── WDI indicators (parser wb_wdi v0.1.0) ──────────────────────────────────
// 15 WB indicator codes for Nepal. All annual, confidence A.
// Cross-checks: wdi-gdp-growth-annual-pct ↔ dne-gdp-real-growth;
//               wdi-cpi-inflation-annual-pct ↔ dne-inflation-rate;
//               wdi-gdp-per-capita-current-usd ↔ dne-gdp-per-capita-usd.
// USD level indicators (GDP, GNI, remittances) stored in usd_million (÷1e6).
// Per-capita indicators stored in usd (no scaling).
const WDI_INDICATORS: readonly SeedIndicator[] = [
  {
    slug: 'wdi-gdp-current-usd',
    nameEn: 'GDP (current US$)',
    category: 'real_sector',
    unit: 'usd_million',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
  {
    slug: 'wdi-gdp-constant-2015-usd',
    nameEn: 'GDP (constant 2015 US$)',
    category: 'real_sector',
    unit: 'usd_million',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
  {
    slug: 'wdi-gdp-growth-annual-pct',
    nameEn: 'GDP growth (annual %)',
    category: 'real_sector',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
  {
    slug: 'wdi-gdp-per-capita-current-usd',
    nameEn: 'GDP per capita (current US$)',
    category: 'real_sector',
    unit: 'usd',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
  {
    slug: 'wdi-gdp-per-capita-growth-pct',
    nameEn: 'GDP per capita growth (annual %)',
    category: 'real_sector',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
  {
    slug: 'wdi-cpi-inflation-annual-pct',
    nameEn: 'Inflation, consumer prices (annual %)',
    category: 'price',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
  {
    slug: 'wdi-remittances-received-usd',
    nameEn: 'Personal remittances received (current US$)',
    category: 'external_sector',
    unit: 'usd_million',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
  {
    slug: 'wdi-remittances-pct-gdp',
    nameEn: 'Personal remittances received (% of GDP)',
    category: 'external_sector',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
  {
    slug: 'wdi-gni-current-usd',
    nameEn: 'GNI (current US$)',
    category: 'real_sector',
    unit: 'usd_million',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
  {
    slug: 'wdi-gni-per-capita-current-usd',
    nameEn: 'GNI per capita (current US$)',
    category: 'real_sector',
    unit: 'usd',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
  {
    slug: 'wdi-poverty-headcount-national-pct',
    nameEn: 'Poverty headcount ratio at national poverty lines (% of population)',
    category: 'demographic',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
  {
    slug: 'wdi-gini-index',
    nameEn: 'Gini index',
    category: 'demographic',
    unit: 'index_points',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
  {
    slug: 'wdi-gross-capital-formation-pct-gdp',
    nameEn: 'Gross capital formation (% of GDP)',
    category: 'real_sector',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
  {
    slug: 'wdi-central-govt-debt-pct-gdp',
    nameEn: 'Central government debt, total (% of GDP)',
    category: 'fiscal',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
  {
    slug: 'wdi-current-account-balance-pct-gdp',
    nameEn: 'Current account balance (% of GDP)',
    category: 'external_sector',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
];

// ─── IMF WEO indicators (parser imf_weo v0.1.0) ─────────────────────────────
// 13 IMF World Economic Outlook codes for Nepal. All annual, confidence A.
// The ONLY source of forward projections (ADR-0025: observation_type).
// USD/PPP levels stored ÷ in *_million (WEO publishes billions → parser ×1000),
// matching wb_wdi's usd_million so the two benchmark in one unit.
// Cross-checks: weo-gdp-real-growth-pct ↔ dne-gdp-real-growth / wdi-gdp-growth-annual-pct;
//               weo-inflation-avg-pct ↔ wdi-cpi-inflation-annual-pct.
const WEO_INDICATORS: readonly SeedIndicator[] = [
  {
    slug: 'weo-gdp-current-usd',
    nameEn: 'GDP, current prices (US$)',
    category: 'real_sector',
    unit: 'usd_million',
    nativeFrequency: 'annual',
    sourceAgency: 'International Monetary Fund',
  },
  {
    slug: 'weo-gdp-real-growth-pct',
    nameEn: 'Real GDP growth (annual %)',
    category: 'real_sector',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'International Monetary Fund',
  },
  {
    slug: 'weo-gdp-per-capita-current-usd',
    nameEn: 'GDP per capita, current prices (US$)',
    category: 'real_sector',
    unit: 'usd',
    nativeFrequency: 'annual',
    sourceAgency: 'International Monetary Fund',
  },
  {
    slug: 'weo-gdp-ppp-intl-dollar',
    nameEn: 'GDP, PPP valuation (international $)',
    category: 'real_sector',
    unit: 'intl_dollar_million',
    nativeFrequency: 'annual',
    sourceAgency: 'International Monetary Fund',
  },
  {
    slug: 'weo-inflation-avg-pct',
    nameEn: 'Inflation, average consumer prices (annual %)',
    category: 'price',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'International Monetary Fund',
  },
  {
    slug: 'weo-current-account-pct-gdp',
    nameEn: 'Current account balance (% of GDP)',
    category: 'external_sector',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'International Monetary Fund',
  },
  {
    slug: 'weo-govt-revenue-pct-gdp',
    nameEn: 'General government revenue (% of GDP)',
    category: 'fiscal',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'International Monetary Fund',
  },
  {
    slug: 'weo-fiscal-balance-pct-gdp',
    nameEn: 'General government net lending/borrowing (% of GDP)',
    category: 'fiscal',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'International Monetary Fund',
  },
  {
    slug: 'weo-govt-gross-debt-pct-gdp',
    nameEn: 'General government gross debt (% of GDP)',
    category: 'fiscal',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'International Monetary Fund',
  },
  {
    slug: 'weo-gross-national-savings-pct-gdp',
    nameEn: 'Gross national savings (% of GDP)',
    category: 'real_sector',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'International Monetary Fund',
  },
  {
    slug: 'weo-total-investment-pct-gdp',
    nameEn: 'Total investment (% of GDP)',
    category: 'real_sector',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'International Monetary Fund',
  },
  {
    slug: 'weo-unemployment-rate-pct',
    nameEn: 'Unemployment rate (% of total labour force)',
    category: 'labour',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'International Monetary Fund',
  },
  {
    slug: 'weo-population',
    nameEn: 'Population',
    category: 'demographic',
    unit: 'persons_million',
    nativeFrequency: 'annual',
    sourceAgency: 'International Monetary Fund',
  },
];

// ─── WB PIP indicators (parser wb_pip v0.1.0) ───────────────────────────────
// 10 World Bank Poverty & Inequality Platform series for Nepal. Survey anchors
// (5 rounds 1984–2022) are confidence A / observation_type 'actual'; the $3.65
// filled trend is conf B / interpolated|projected (ADR-0025).
// Headcount/gap/severity/decile shares stored ×100 → percent; Gini ×100 →
// index_points (matches wdi-gini-index for cross-check); mean/median in
// intl_dollar_per_day (2017-PPP daily consumption).
const PIP_INDICATORS: readonly SeedIndicator[] = [
  {
    slug: 'pip-poverty-headcount-215',
    nameEn: 'Poverty headcount ratio at $2.15/day (2017 PPP)',
    category: 'demographic',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
  {
    slug: 'pip-poverty-headcount-365',
    nameEn: 'Poverty headcount ratio at $3.65/day (2017 PPP)',
    category: 'demographic',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
  {
    slug: 'pip-poverty-headcount-685',
    nameEn: 'Poverty headcount ratio at $6.85/day (2017 PPP)',
    category: 'demographic',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
  {
    slug: 'pip-poverty-gap-365',
    nameEn: 'Poverty gap at $3.65/day (2017 PPP)',
    category: 'demographic',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
  {
    slug: 'pip-poverty-severity-365',
    nameEn: 'Poverty severity (squared gap) at $3.65/day (2017 PPP)',
    category: 'demographic',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
  {
    slug: 'pip-gini',
    nameEn: 'Gini index (consumption/income)',
    category: 'demographic',
    unit: 'index_points',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
  {
    slug: 'pip-mean-consumption',
    nameEn: 'Mean daily consumption per capita (2017 PPP)',
    category: 'demographic',
    unit: 'intl_dollar_per_day',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
  {
    slug: 'pip-median-consumption',
    nameEn: 'Median daily consumption per capita (2017 PPP)',
    category: 'demographic',
    unit: 'intl_dollar_per_day',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
  {
    slug: 'pip-decile1-share',
    nameEn: 'Consumption share of the bottom decile',
    category: 'demographic',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
  {
    slug: 'pip-decile10-share',
    nameEn: 'Consumption share of the top decile',
    category: 'demographic',
    unit: 'percent',
    nativeFrequency: 'annual',
    sourceAgency: 'World Bank',
  },
];

// ─── Controlled unit vocabulary ────────────────────────────────────────────
const UNITS: readonly NewIndicatorUnitRow[] = [
  { unit: 'npr_billion', displayEn: 'NPR billion', dimension: 'currency' },
  { unit: 'npr_million', displayEn: 'NPR million', dimension: 'currency' },
  { unit: 'npr_crore', displayEn: 'NPR crore', dimension: 'currency' },
  { unit: 'npr_lakh', displayEn: 'NPR lakh', dimension: 'currency' },
  { unit: 'npr', displayEn: 'NPR', dimension: 'currency' },
  { unit: 'usd_million', displayEn: 'USD million', dimension: 'currency' },
  { unit: 'usd', displayEn: 'USD', dimension: 'currency' },
  { unit: 'intl_dollar_million', displayEn: 'international $ million (PPP)', dimension: 'currency' },
  { unit: 'intl_dollar_per_day', displayEn: 'international $ per day (PPP)', dimension: 'currency' },
  { unit: 'persons_million', displayEn: 'persons (millions)', dimension: 'count' },
  { unit: 'percent', displayEn: 'percent', dimension: 'ratio' },
  { unit: 'percent_yoy', displayEn: 'percent (year-on-year)', dimension: 'ratio' },
  { unit: 'index_points', displayEn: 'index points', dimension: 'index' },
  { unit: 'months', displayEn: 'months', dimension: 'duration' },
  { unit: 'count', displayEn: 'count', dimension: 'count' },
  { unit: 'ratio', displayEn: 'ratio', dimension: 'ratio' },
  { unit: 'metric_tonnes', displayEn: 'metric tonnes', dimension: 'mass' },
  { unit: 'kg_per_capita', displayEn: 'kg per capita', dimension: 'mass' },
  { unit: 'gigawatt_hours', displayEn: 'GWh', dimension: 'energy' },
  { unit: 'megawatt_hours', displayEn: 'MWh', dimension: 'energy' },
];

// ─── CMEFs headline indicators (parser nrb_cmefs v0.1.0) ────────────────────
type SeedIndicator = NewIndicatorRow & { category: IndicatorCategory };

const INDICATORS: readonly SeedIndicator[] = [
  {
    slug: 'cmefs-ncpi-yoy-overall',
    nameEn: 'Consumer Price Inflation (y-o-y)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'cmefs-remittance-inflow-ytd',
    nameEn: 'Remittance Inflows (year-to-date)',
    category: 'external_sector',
    unit: 'npr_billion',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'cmefs-merchandise-imports-ytd',
    nameEn: 'Merchandise Imports (year-to-date)',
    category: 'external_sector',
    unit: 'npr_billion',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'cmefs-trade-deficit-ytd',
    nameEn: 'Trade Deficit (year-to-date)',
    category: 'external_sector',
    unit: 'npr_billion',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'cmefs-bop-surplus-ytd',
    nameEn: 'Balance of Payments Surplus (year-to-date)',
    category: 'external_sector',
    unit: 'npr_billion',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'cmefs-gross-forex-reserves',
    nameEn: 'Gross Foreign Exchange Reserves',
    category: 'external_sector',
    unit: 'npr_billion',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'cmefs-forex-reserves-months-of-import-cover',
    nameEn: 'Foreign Exchange Reserves — Months of Import Cover',
    category: 'external_sector',
    unit: 'months',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
];

// ─── CMEFs v0.2.0 extended indicators (parser nrb_cmefs v0.2.0) ─────────────
// Government finance, monetary, and external-sector extensions. Prose-based.
// Cross-validate revenue/expenditure vs FCGO CFS and DNE in the TS validation
// layer (see docs/sources/nrb-cmefs-monthly.md §"Cross-validation").
const CMEFS_V02_INDICATORS: readonly SeedIndicator[] = [
  {
    slug: 'cmefs-merchandise-exports-ytd',
    nameEn: 'Merchandise Exports (year-to-date)',
    category: 'external_sector',
    unit: 'npr_billion',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'cmefs-govt-revenue-total-ytd',
    nameEn: 'Government Total Revenue (year-to-date)',
    category: 'fiscal',
    unit: 'npr_billion',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'cmefs-govt-expenditure-total-ytd',
    nameEn: 'Government Total Expenditure (year-to-date)',
    category: 'fiscal',
    unit: 'npr_billion',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'cmefs-govt-fiscal-balance-ytd',
    nameEn: 'Government Fiscal Balance (year-to-date)',
    category: 'fiscal',
    unit: 'npr_billion',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'cmefs-m2-yoy',
    nameEn: 'Broad Money (M2) — Year-on-Year Growth',
    category: 'monetary',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'cmefs-private-sector-credit-yoy',
    nameEn: 'Private Sector Credit — Year-on-Year Growth',
    category: 'monetary',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'cmefs-bfi-deposits-yoy',
    nameEn: 'BFI Deposits — Year-on-Year Growth',
    category: 'monetary',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
];

// ─── NCPI indicators (parser nrb_ncpi v0.1.0) ────────────────────────────────
// Each canonical concept is registered once per geography variant (overall,
// rural, urban) — three slugs per CSV row. Unit is always percent_yoy
// (already in UNITS above). Source agency: Nepal Rastra Bank.
// Category 'price' for all (consumer price index sub-groups).
// nativeFrequency 'monthly' — NRB publishes monthly CMEFs updates.

const NCPI_INDICATORS: readonly SeedIndicator[] = [
  // ── Overall Index ─────────────────────────────────────────────────────────
  {
    slug: 'ncpi-overall-index-overall-yoy',
    nameEn: 'NCPI Overall Index — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-overall-index-rural-yoy',
    nameEn: 'NCPI Overall Index — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-overall-index-urban-yoy',
    nameEn: 'NCPI Overall Index — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── A: Food and Beverages aggregate ───────────────────────────────────────
  {
    slug: 'ncpi-a-food-and-beverages-overall-yoy',
    nameEn: 'NCPI Food and Beverages — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-a-food-and-beverages-rural-yoy',
    nameEn: 'NCPI Food and Beverages — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-a-food-and-beverages-urban-yoy',
    nameEn: 'NCPI Food and Beverages — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── A.1: Cereal grains and their products ─────────────────────────────────
  {
    slug: 'ncpi-a-1-cereal-grains-and-their-products-overall-yoy',
    nameEn: 'NCPI A.1 Cereal Grains and Their Products — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-a-1-cereal-grains-and-their-products-rural-yoy',
    nameEn: 'NCPI A.1 Cereal Grains and Their Products — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-a-1-cereal-grains-and-their-products-urban-yoy',
    nameEn: 'NCPI A.1 Cereal Grains and Their Products — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── A.2: Pulses and Legumes ────────────────────────────────────────────────
  {
    slug: 'ncpi-a-2-pulses-and-legumes-overall-yoy',
    nameEn: 'NCPI A.2 Pulses and Legumes — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-a-2-pulses-and-legumes-rural-yoy',
    nameEn: 'NCPI A.2 Pulses and Legumes — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-a-2-pulses-and-legumes-urban-yoy',
    nameEn: 'NCPI A.2 Pulses and Legumes — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── A.3: Vegetable ────────────────────────────────────────────────────────
  {
    slug: 'ncpi-a-3-vegetable-overall-yoy',
    nameEn: 'NCPI A.3 Vegetable — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-a-3-vegetable-rural-yoy',
    nameEn: 'NCPI A.3 Vegetable — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-a-3-vegetable-urban-yoy',
    nameEn: 'NCPI A.3 Vegetable — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── A.4: Meat and Fish ────────────────────────────────────────────────────
  {
    slug: 'ncpi-a-4-meat-and-fish-overall-yoy',
    nameEn: 'NCPI A.4 Meat and Fish — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-a-4-meat-and-fish-rural-yoy',
    nameEn: 'NCPI A.4 Meat and Fish — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-a-4-meat-and-fish-urban-yoy',
    nameEn: 'NCPI A.4 Meat and Fish — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── A.5: Milk products and Eggs ───────────────────────────────────────────
  {
    slug: 'ncpi-a-5-milk-products-and-eggs-overall-yoy',
    nameEn: 'NCPI A.5 Milk Products and Eggs — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-a-5-milk-products-and-eggs-rural-yoy',
    nameEn: 'NCPI A.5 Milk Products and Eggs — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-a-5-milk-products-and-eggs-urban-yoy',
    nameEn: 'NCPI A.5 Milk Products and Eggs — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── A.6: Ghee and Oil ─────────────────────────────────────────────────────
  {
    slug: 'ncpi-a-6-ghee-and-oil-overall-yoy',
    nameEn: 'NCPI A.6 Ghee and Oil — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-a-6-ghee-and-oil-rural-yoy',
    nameEn: 'NCPI A.6 Ghee and Oil — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-a-6-ghee-and-oil-urban-yoy',
    nameEn: 'NCPI A.6 Ghee and Oil — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── A.7: Fruit ────────────────────────────────────────────────────────────
  {
    slug: 'ncpi-a-7-fruit-overall-yoy',
    nameEn: 'NCPI A.7 Fruit — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-a-7-fruit-rural-yoy',
    nameEn: 'NCPI A.7 Fruit — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-a-7-fruit-urban-yoy',
    nameEn: 'NCPI A.7 Fruit — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── A.8: Sugar and Sugar products ─────────────────────────────────────────
  {
    slug: 'ncpi-a-8-sugar-and-sugar-products-overall-yoy',
    nameEn: 'NCPI A.8 Sugar and Sugar Products — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-a-8-sugar-and-sugar-products-rural-yoy',
    nameEn: 'NCPI A.8 Sugar and Sugar Products — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-a-8-sugar-and-sugar-products-urban-yoy',
    nameEn: 'NCPI A.8 Sugar and Sugar Products — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── A.9: Spices ───────────────────────────────────────────────────────────
  {
    slug: 'ncpi-a-9-spices-overall-yoy',
    nameEn: 'NCPI A.9 Spices — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-a-9-spices-rural-yoy',
    nameEn: 'NCPI A.9 Spices — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-a-9-spices-urban-yoy',
    nameEn: 'NCPI A.9 Spices — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── A.10: Non-alcoholic drinks ────────────────────────────────────────────
  {
    slug: 'ncpi-a-10-non-alcoholic-drinks-overall-yoy',
    nameEn: 'NCPI A.10 Non-Alcoholic Drinks — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-a-10-non-alcoholic-drinks-rural-yoy',
    nameEn: 'NCPI A.10 Non-Alcoholic Drinks — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-a-10-non-alcoholic-drinks-urban-yoy',
    nameEn: 'NCPI A.10 Non-Alcoholic Drinks — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── B: Non-food and Services aggregate ───────────────────────────────────
  {
    slug: 'ncpi-b-non-food-and-services-overall-yoy',
    nameEn: 'NCPI Non-Food and Services — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-non-food-and-services-rural-yoy',
    nameEn: 'NCPI Non-Food and Services — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-non-food-and-services-urban-yoy',
    nameEn: 'NCPI Non-Food and Services — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── B.1: Alcoholic drinks ─────────────────────────────────────────────────
  {
    slug: 'ncpi-b-1-alcoholic-drinks-overall-yoy',
    nameEn: 'NCPI B.1 Alcoholic Drinks — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-1-alcoholic-drinks-rural-yoy',
    nameEn: 'NCPI B.1 Alcoholic Drinks — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-1-alcoholic-drinks-urban-yoy',
    nameEn: 'NCPI B.1 Alcoholic Drinks — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── B.2: Tobacco products ─────────────────────────────────────────────────
  {
    slug: 'ncpi-b-2-tobacco-products-overall-yoy',
    nameEn: 'NCPI B.2 Tobacco Products — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-2-tobacco-products-rural-yoy',
    nameEn: 'NCPI B.2 Tobacco Products — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-2-tobacco-products-urban-yoy',
    nameEn: 'NCPI B.2 Tobacco Products — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── B.3: Clothes and Footwear ─────────────────────────────────────────────
  {
    slug: 'ncpi-b-3-clothes-and-footwear-overall-yoy',
    nameEn: 'NCPI B.3 Clothes and Footwear — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-3-clothes-and-footwear-rural-yoy',
    nameEn: 'NCPI B.3 Clothes and Footwear — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-3-clothes-and-footwear-urban-yoy',
    nameEn: 'NCPI B.3 Clothes and Footwear — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── B.4: Housing and Utilities ────────────────────────────────────────────
  {
    slug: 'ncpi-b-4-housing-and-utilities-overall-yoy',
    nameEn: 'NCPI B.4 Housing and Utilities — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-4-housing-and-utilities-rural-yoy',
    nameEn: 'NCPI B.4 Housing and Utilities — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-4-housing-and-utilities-urban-yoy',
    nameEn: 'NCPI B.4 Housing and Utilities — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── B.5: Furnishing and Household equipment ───────────────────────────────
  {
    slug: 'ncpi-b-5-furnishing-and-household-equipment-overall-yoy',
    nameEn: 'NCPI B.5 Furnishing and Household Equipment — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-5-furnishing-and-household-equipment-rural-yoy',
    nameEn: 'NCPI B.5 Furnishing and Household Equipment — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-5-furnishing-and-household-equipment-urban-yoy',
    nameEn: 'NCPI B.5 Furnishing and Household Equipment — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── B.6: Health ───────────────────────────────────────────────────────────
  {
    slug: 'ncpi-b-6-health-overall-yoy',
    nameEn: 'NCPI B.6 Health — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-6-health-rural-yoy',
    nameEn: 'NCPI B.6 Health — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-6-health-urban-yoy',
    nameEn: 'NCPI B.6 Health — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── B.7: Transportation ───────────────────────────────────────────────────
  {
    slug: 'ncpi-b-7-transportation-overall-yoy',
    nameEn: 'NCPI B.7 Transportation — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-7-transportation-rural-yoy',
    nameEn: 'NCPI B.7 Transportation — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-7-transportation-urban-yoy',
    nameEn: 'NCPI B.7 Transportation — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── B.8: Communication ────────────────────────────────────────────────────
  {
    slug: 'ncpi-b-8-communication-overall-yoy',
    nameEn: 'NCPI B.8 Communication — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-8-communication-rural-yoy',
    nameEn: 'NCPI B.8 Communication — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-8-communication-urban-yoy',
    nameEn: 'NCPI B.8 Communication — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── B.9: Recreation and Culture ───────────────────────────────────────────
  {
    slug: 'ncpi-b-9-recreation-and-culture-overall-yoy',
    nameEn: 'NCPI B.9 Recreation and Culture — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-9-recreation-and-culture-rural-yoy',
    nameEn: 'NCPI B.9 Recreation and Culture — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-9-recreation-and-culture-urban-yoy',
    nameEn: 'NCPI B.9 Recreation and Culture — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── B.10: Education ───────────────────────────────────────────────────────
  {
    slug: 'ncpi-b-10-education-overall-yoy',
    nameEn: 'NCPI B.10 Education — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-10-education-rural-yoy',
    nameEn: 'NCPI B.10 Education — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-10-education-urban-yoy',
    nameEn: 'NCPI B.10 Education — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── B.11: Restaurants and Accommodation Services ──────────────────────────
  {
    slug: 'ncpi-b-11-restaurants-and-accomodation-services-overall-yoy',
    nameEn: 'NCPI B.11 Restaurants and Accommodation Services — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-11-restaurants-and-accomodation-services-rural-yoy',
    nameEn: 'NCPI B.11 Restaurants and Accommodation Services — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-11-restaurants-and-accomodation-services-urban-yoy',
    nameEn: 'NCPI B.11 Restaurants and Accommodation Services — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── B.12: Insurance and Financial Services ────────────────────────────────
  {
    slug: 'ncpi-b-12-insurance-and-financial-services-overall-yoy',
    nameEn: 'NCPI B.12 Insurance and Financial Services — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-12-insurance-and-financial-services-rural-yoy',
    nameEn: 'NCPI B.12 Insurance and Financial Services — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-12-insurance-and-financial-services-urban-yoy',
    nameEn: 'NCPI B.12 Insurance and Financial Services — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  // ── B.13: Miscellaneous goods and services ────────────────────────────────
  {
    slug: 'ncpi-b-13-miscellaneous-goods-and-services-overall-yoy',
    nameEn: 'NCPI B.13 Miscellaneous Goods and Services — Overall (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-13-miscellaneous-goods-and-services-rural-yoy',
    nameEn: 'NCPI B.13 Miscellaneous Goods and Services — Rural (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
  {
    slug: 'ncpi-b-13-miscellaneous-goods-and-services-urban-yoy',
    nameEn: 'NCPI B.13 Miscellaneous Goods and Services — Urban (YoY)',
    category: 'price',
    unit: 'percent_yoy',
    nativeFrequency: 'monthly',
    sourceAgency: 'Nepal Rastra Bank',
  },
];

function log(msg: string): void {
  process.stdout.write(`[seed-indicators] ${msg}\n`);
}

async function persist(): Promise<void> {
  // Lazy imports so --dry-run runs without DATABASE_URL.
  const { db } = await import('@/lib/db/client');
  const { indicators } = await import('@/lib/db/schema/indicators');
  const { safeQuery } = await import('@/lib/db/safe-query');
  const { bulkUpsertIndicatorUnits } = await import('@/lib/db/repositories/indicator-units');
  const { findIndicatorBySlug, linkIndicatorToSource } =
    await import('@/lib/db/repositories/indicators');

  // 1. Units.
  const unitsResult = await bulkUpsertIndicatorUnits(UNITS);
  if (!unitsResult.ok) throw new Error(`units upsert failed: ${JSON.stringify(unitsResult.error)}`);
  log(`indicator_units: ${unitsResult.value} inserted (of ${UNITS.length}; existing skipped)`);

  // 2. Indicators.
  const insertResult = await safeQuery(() =>
    db()
      .insert(indicators)
      .values([...INDICATORS])
      .onConflictDoNothing({ target: indicators.slug })
      .returning({ id: indicators.id, slug: indicators.slug }),
  );
  if (!insertResult.ok)
    throw new Error(`indicators insert failed: ${JSON.stringify(insertResult.error)}`);
  log(
    `indicators: ${insertResult.value.length} inserted (of ${INDICATORS.length}; existing skipped)`,
  );

  // 3. Source map — resolve every slug (incl. pre-existing) to its id, then link.
  let linked = 0;
  for (const ind of INDICATORS) {
    const found = await findIndicatorBySlug(ind.slug);
    if (!found.ok) throw new Error(`resolve ${ind.slug} failed: ${JSON.stringify(found.error)}`);
    const link = await linkIndicatorToSource(found.value.id, CMEFS_SOURCE_ID, 'CMEFs headline set');
    if (!link.ok) throw new Error(`link ${ind.slug} failed: ${JSON.stringify(link.error)}`);
    linked += 1;
  }
  log(`indicator_source_map: ${linked} links ensured → ${CMEFS_SOURCE_ID}`);

  // 4. CMEFs v0.2.0 extended indicators.
  const cmefs02InsertResult = await safeQuery(() =>
    db()
      .insert(indicators)
      .values([...CMEFS_V02_INDICATORS])
      .onConflictDoNothing({ target: indicators.slug })
      .returning({ id: indicators.id, slug: indicators.slug }),
  );
  if (!cmefs02InsertResult.ok)
    throw new Error(
      `CMEFs v0.2.0 indicators insert failed: ${JSON.stringify(cmefs02InsertResult.error)}`,
    );
  log(
    `indicators (CMEFs v0.2.0): ${cmefs02InsertResult.value.length} inserted ` +
      `(of ${CMEFS_V02_INDICATORS.length}; existing skipped)`,
  );
  let cmefs02Linked = 0;
  for (const ind of CMEFS_V02_INDICATORS) {
    const found = await findIndicatorBySlug(ind.slug);
    if (!found.ok)
      throw new Error(`resolve ${ind.slug} failed: ${JSON.stringify(found.error)}`);
    const link = await linkIndicatorToSource(
      found.value.id,
      CMEFS_SOURCE_ID,
      'CMEFs extended set (v0.2.0)',
    );
    if (!link.ok) throw new Error(`link ${ind.slug} failed: ${JSON.stringify(link.error)}`);
    cmefs02Linked += 1;
  }
  log(`indicator_source_map: ${cmefs02Linked} links ensured → ${CMEFS_SOURCE_ID} (v0.2.0)`);

  // 6. NCPI indicators.
  const ncpiInsertResult = await safeQuery(() =>
    db()
      .insert(indicators)
      .values([...NCPI_INDICATORS])
      .onConflictDoNothing({ target: indicators.slug })
      .returning({ id: indicators.id, slug: indicators.slug }),
  );
  if (!ncpiInsertResult.ok)
    throw new Error(`NCPI indicators insert failed: ${JSON.stringify(ncpiInsertResult.error)}`);
  log(
    `indicators (NCPI): ${ncpiInsertResult.value.length} inserted (of ${NCPI_INDICATORS.length}; existing skipped)`,
  );

  // 7. NCPI source map links.
  let ncpiLinked = 0;
  for (const ind of NCPI_INDICATORS) {
    const found = await findIndicatorBySlug(ind.slug);
    if (!found.ok) throw new Error(`resolve ${ind.slug} failed: ${JSON.stringify(found.error)}`);
    const link = await linkIndicatorToSource(
      found.value.id,
      NCPI_SOURCE_ID,
      'NCPI Table 2(B) full breakdown',
    );
    if (!link.ok) throw new Error(`link ${ind.slug} failed: ${JSON.stringify(link.error)}`);
    ncpiLinked += 1;
  }
  log(`indicator_source_map: ${ncpiLinked} links ensured → ${NCPI_SOURCE_ID}`);

  // 6. DNE single-series indicators (ADR-0014: clean single series only).
  const dneInsertResult = await safeQuery(() =>
    db()
      .insert(indicators)
      .values([...DNE_INDICATORS])
      .onConflictDoNothing({ target: indicators.slug })
      .returning({ id: indicators.id, slug: indicators.slug }),
  );
  if (!dneInsertResult.ok)
    throw new Error(`DNE indicators insert failed: ${JSON.stringify(dneInsertResult.error)}`);
  log(
    `indicators (DNE): ${dneInsertResult.value.length} inserted (of ${DNE_INDICATORS.length}; existing skipped)`,
  );

  // 7. DNE source map links.
  let dneLinked = 0;
  for (const ind of DNE_INDICATORS) {
    const found = await findIndicatorBySlug(ind.slug);
    if (!found.ok) throw new Error(`resolve ${ind.slug} failed: ${JSON.stringify(found.error)}`);
    const link = await linkIndicatorToSource(
      found.value.id,
      DNE_SOURCE_ID,
      'DNE single-series (ADR-0014)',
    );
    if (!link.ok) throw new Error(`link ${ind.slug} failed: ${JSON.stringify(link.error)}`);
    dneLinked += 1;
  }
  log(`indicator_source_map: ${dneLinked} links ensured → ${DNE_SOURCE_ID}`);

  // 8. FCGO consolidated financial statements (audited gov-finance aggregates).
  const fcgoInsertResult = await safeQuery(() =>
    db()
      .insert(indicators)
      .values([...FCGO_INDICATORS])
      .onConflictDoNothing({ target: indicators.slug })
      .returning({ id: indicators.id, slug: indicators.slug }),
  );
  if (!fcgoInsertResult.ok)
    throw new Error(`FCGO indicators insert failed: ${JSON.stringify(fcgoInsertResult.error)}`);
  log(
    `indicators (FCGO): ${fcgoInsertResult.value.length} inserted (of ${FCGO_INDICATORS.length}; existing skipped)`,
  );

  // 9. FCGO source map links.
  let fcgoLinked = 0;
  for (const ind of FCGO_INDICATORS) {
    const found = await findIndicatorBySlug(ind.slug);
    if (!found.ok) throw new Error(`resolve ${ind.slug} failed: ${JSON.stringify(found.error)}`);
    const link = await linkIndicatorToSource(
      found.value.id,
      FCGO_SOURCE_ID,
      'FCGO CFS headline aggregates',
    );
    if (!link.ok) throw new Error(`link ${ind.slug} failed: ${JSON.stringify(link.error)}`);
    fcgoLinked += 1;
  }
  log(`indicator_source_map: ${fcgoLinked} links ensured → ${FCGO_SOURCE_ID}`);

  // 10. MoF Economic Survey Annex-6.1 foreign-employment-permit series (ADR-0016).
  const esInsertResult = await safeQuery(() =>
    db()
      .insert(indicators)
      .values([...ECONOMIC_SURVEY_INDICATORS])
      .onConflictDoNothing({ target: indicators.slug })
      .returning({ id: indicators.id, slug: indicators.slug }),
  );
  if (!esInsertResult.ok)
    throw new Error(
      `economic-survey indicators insert failed: ${JSON.stringify(esInsertResult.error)}`,
    );
  log(
    `indicators (Economic Survey): ${esInsertResult.value.length} inserted (of ${ECONOMIC_SURVEY_INDICATORS.length}; existing skipped)`,
  );

  // 11. Economic Survey source map links.
  let esLinked = 0;
  for (const ind of ECONOMIC_SURVEY_INDICATORS) {
    const found = await findIndicatorBySlug(ind.slug);
    if (!found.ok) throw new Error(`resolve ${ind.slug} failed: ${JSON.stringify(found.error)}`);
    const link = await linkIndicatorToSource(
      found.value.id,
      ECONOMIC_SURVEY_SOURCE_ID,
      'Economic Survey Annex 6.1 (foreign employment permits)',
    );
    if (!link.ok) throw new Error(`link ${ind.slug} failed: ${JSON.stringify(link.error)}`);
    esLinked += 1;
  }
  log(`indicator_source_map: ${esLinked} links ensured → ${ECONOMIC_SURVEY_SOURCE_ID}`);

  // 12. WDI (World Bank) indicators — 15 annual benchmark series.
  const wdiInsertResult = await safeQuery(() =>
    db()
      .insert(indicators)
      .values([...WDI_INDICATORS])
      .onConflictDoNothing({ target: indicators.slug })
      .returning({ id: indicators.id, slug: indicators.slug }),
  );
  if (!wdiInsertResult.ok)
    throw new Error(`WDI indicators insert failed: ${JSON.stringify(wdiInsertResult.error)}`);
  log(
    `indicators (WDI): ${wdiInsertResult.value.length} inserted (of ${WDI_INDICATORS.length}; existing skipped)`,
  );

  // 13. WDI source map links.
  let wdiLinked = 0;
  for (const ind of WDI_INDICATORS) {
    const found = await findIndicatorBySlug(ind.slug);
    if (!found.ok) throw new Error(`resolve ${ind.slug} failed: ${JSON.stringify(found.error)}`);
    const link = await linkIndicatorToSource(found.value.id, WDI_SOURCE_ID, 'WB WDI Nepal annual');
    if (!link.ok) throw new Error(`link ${ind.slug} failed: ${JSON.stringify(link.error)}`);
    wdiLinked += 1;
  }
  log(`indicator_source_map: ${wdiLinked} links ensured → ${WDI_SOURCE_ID}`);

  // 14. IMF WEO indicators — 13 annual benchmark + projection series.
  const weoInsertResult = await safeQuery(() =>
    db()
      .insert(indicators)
      .values([...WEO_INDICATORS])
      .onConflictDoNothing({ target: indicators.slug })
      .returning({ id: indicators.id, slug: indicators.slug }),
  );
  if (!weoInsertResult.ok)
    throw new Error(`WEO indicators insert failed: ${JSON.stringify(weoInsertResult.error)}`);
  log(
    `indicators (WEO): ${weoInsertResult.value.length} inserted (of ${WEO_INDICATORS.length}; existing skipped)`,
  );

  // 15. WEO source map links.
  let weoLinked = 0;
  for (const ind of WEO_INDICATORS) {
    const found = await findIndicatorBySlug(ind.slug);
    if (!found.ok) throw new Error(`resolve ${ind.slug} failed: ${JSON.stringify(found.error)}`);
    const link = await linkIndicatorToSource(found.value.id, WEO_SOURCE_ID, 'IMF WEO Nepal annual');
    if (!link.ok) throw new Error(`link ${ind.slug} failed: ${JSON.stringify(link.error)}`);
    weoLinked += 1;
  }
  log(`indicator_source_map: ${weoLinked} links ensured → ${WEO_SOURCE_ID}`);

  // 16. WB PIP indicators — 10 poverty/inequality series.
  const pipInsertResult = await safeQuery(() =>
    db()
      .insert(indicators)
      .values([...PIP_INDICATORS])
      .onConflictDoNothing({ target: indicators.slug })
      .returning({ id: indicators.id, slug: indicators.slug }),
  );
  if (!pipInsertResult.ok)
    throw new Error(`PIP indicators insert failed: ${JSON.stringify(pipInsertResult.error)}`);
  log(
    `indicators (PIP): ${pipInsertResult.value.length} inserted (of ${PIP_INDICATORS.length}; existing skipped)`,
  );

  // 17. PIP source map links.
  let pipLinked = 0;
  for (const ind of PIP_INDICATORS) {
    const found = await findIndicatorBySlug(ind.slug);
    if (!found.ok) throw new Error(`resolve ${ind.slug} failed: ${JSON.stringify(found.error)}`);
    const link = await linkIndicatorToSource(found.value.id, PIP_SOURCE_ID, 'WB PIP Nepal poverty');
    if (!link.ok) throw new Error(`link ${ind.slug} failed: ${JSON.stringify(link.error)}`);
    pipLinked += 1;
  }
  log(`indicator_source_map: ${pipLinked} links ensured → ${PIP_SOURCE_ID}`);
}

async function main(): Promise<void> {
  const dryRun = process.argv.slice(2).includes('--dry-run');
  log(`dry_run = ${dryRun}`);
  log(
    `units = ${UNITS.length}, ` +
      `indicators (CMEFs) = ${INDICATORS.length}, source = ${CMEFS_SOURCE_ID}`,
  );
  log(`indicators (NCPI)  = ${NCPI_INDICATORS.length}, source = ${NCPI_SOURCE_ID}`);
  log(`indicators (WDI)   = ${WDI_INDICATORS.length}, source = ${WDI_SOURCE_ID}`);
  log(`indicators (WEO)   = ${WEO_INDICATORS.length}, source = ${WEO_SOURCE_ID}`);
  log(`indicators (PIP)   = ${PIP_INDICATORS.length}, source = ${PIP_SOURCE_ID}`);

  if (dryRun) {
    log('dry-run: would upsert the following indicator slugs (CMEFs):');
    for (const i of INDICATORS) log(`  - ${i.slug} (${i.category}, ${i.unit})`);
    log('dry-run: would upsert the following indicator slugs (NCPI):');
    for (const i of NCPI_INDICATORS) log(`  - ${i.slug} (${i.category}, ${i.unit})`);
    log('dry-run complete — no DB writes performed');
    return;
  }

  await persist();
  log('done.');
}

main().catch((e: unknown) => {
  process.stderr.write(`[seed-indicators] fatal: ${e instanceof Error ? e.message : String(e)}\n`);
  process.exit(1);
});
