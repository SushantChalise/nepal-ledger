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

// ─── Controlled unit vocabulary ────────────────────────────────────────────
const UNITS: readonly NewIndicatorUnitRow[] = [
  { unit: 'npr_billion', displayEn: 'NPR billion', dimension: 'currency' },
  { unit: 'npr_million', displayEn: 'NPR million', dimension: 'currency' },
  { unit: 'npr_crore', displayEn: 'NPR crore', dimension: 'currency' },
  { unit: 'npr_lakh', displayEn: 'NPR lakh', dimension: 'currency' },
  { unit: 'npr', displayEn: 'NPR', dimension: 'currency' },
  { unit: 'usd_million', displayEn: 'USD million', dimension: 'currency' },
  { unit: 'usd', displayEn: 'USD', dimension: 'currency' },
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

  // 4. NCPI indicators.
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

  // 5. NCPI source map links.
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
}

async function main(): Promise<void> {
  const dryRun = process.argv.slice(2).includes('--dry-run');
  log(`dry_run = ${dryRun}`);
  log(
    `units = ${UNITS.length}, ` +
      `indicators (CMEFs) = ${INDICATORS.length}, source = ${CMEFS_SOURCE_ID}`,
  );
  log(`indicators (NCPI)  = ${NCPI_INDICATORS.length}, source = ${NCPI_SOURCE_ID}`);

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
