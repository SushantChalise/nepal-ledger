-- =====================================================
-- Nepal Ledger — post-`apply-all` verification queries
-- =====================================================
--
-- Run these in the Supabase SQL editor (or any psql client
-- pointed at DATABASE_URL from .env.local) after running
-- `pnpm exec tsx scripts/apply-all.ts`.
--
-- Each section prints what we expect + what we got. Numbers
-- diverging by more than a few percent indicate the ingest
-- didn't land cleanly.

\echo '=== 1. Schema sanity (21 user tables expected) ==='
SELECT count(*) AS total_user_tables
FROM pg_tables
WHERE schemaname = 'public';

SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

\echo ''
\echo '=== 2. source_registry seeded ==='
SELECT source_id, agency_short, publication_frequency, ingestion_mode, status
FROM source_registry
ORDER BY source_id;
-- Expect: nrb-cmefs-monthly, nrb-ncpi-table, nrb-bfi-monthly,
--         mof-intergovernmental-fiscal-transfer, admin-hierarchy-voters

\echo ''
\echo '=== 3. entities aggregate (expect: 7 provinces + 77 districts + 753 local levels + ~6,176 wards + ~10,203 polling stations) ==='
SELECT kind, count(*) AS row_count
FROM entities
GROUP BY kind
ORDER BY kind;

\echo ''
\echo '=== 4. administrative_units coverage (expect: 753 with local_level_type set) ==='
SELECT local_level_type, count(*) AS row_count
FROM administrative_units
WHERE local_level_type IS NOT NULL
GROUP BY local_level_type
ORDER BY local_level_type;
-- Expect: metropolitan_city ≈ 6, sub_metropolitan_city ≈ 11,
--         municipality ≈ 276, rural_municipality ≈ 460

\echo ''
\echo '=== 5. local_government_fiscal_transfers totals (FY 2082/83) ==='
SELECT grant_type,
       count(*) AS row_count,
       to_char(SUM(amount_npr::numeric), '999G999G999G990D00') AS total_npr_lakh
FROM local_government_fiscal_transfers
WHERE fiscal_year_bs = '2082/83'
GROUP BY grant_type
ORDER BY grant_type;

\echo ''
\echo '=== 6. banking_sector_facts counts (expect ~105K rows across 49+ snapshots) ==='
SELECT count(*) AS total_rows FROM banking_sector_facts;

SELECT bank_class, count(*) AS row_count
FROM banking_sector_facts
GROUP BY bank_class
ORDER BY bank_class;
-- Expect: commercial ≈ 26K, development ≈ 26K, finance ≈ 26K, system_total ≈ 26K

SELECT source_sheet, count(*) AS row_count
FROM banking_sector_facts
GROUP BY source_sheet
ORDER BY source_sheet;
-- Expect C4, C5, C6, C7 each with ~25K rows

\echo ''
\echo '=== 7. banking_sector_facts time range ==='
SELECT min(reporting_period_ad_start) AS earliest,
       max(reporting_period_ad_end) AS latest,
       count(DISTINCT reporting_period_bs) AS distinct_periods
FROM banking_sector_facts;
-- Expect earliest ≈ 2018 (historical columns); latest ≈ Sept 2025;
-- distinct periods 50+

\echo ''
\echo '=== 8. Top 10 banking indicators by row count ==='
SELECT indicator_slug, count(*) AS row_count
FROM banking_sector_facts
GROUP BY indicator_slug
ORDER BY count(*) DESC
LIMIT 10;

\echo ''
\echo '=== 9. Provincewise summary of fiscal transfers ==='
SELECT
  prov.name_en AS province,
  count(DISTINCT ft.local_level_entity_id) AS local_levels_with_transfers,
  to_char(SUM(ft.amount_npr::numeric), '999G999G999G990D00') AS total_npr_lakh
FROM local_government_fiscal_transfers ft
JOIN entities ll ON ll.id = ft.local_level_entity_id
JOIN entities dist ON dist.id = ll.parent_entity_id
JOIN entities prov ON prov.id = dist.parent_entity_id
WHERE ft.fiscal_year_bs = '2082/83'
GROUP BY prov.name_en
ORDER BY prov.name_en;

\echo ''
\echo '=== 10. Top 10 local levels by total grant received (FY 2082/83) ==='
SELECT
  ll.name_en AS local_level,
  dist.name_en AS district,
  ll.metadata ->> 'local_level_type' AS local_level_type,
  to_char(SUM(ft.amount_npr::numeric), '999G999G990D00') AS total_npr_lakh
FROM local_government_fiscal_transfers ft
JOIN entities ll ON ll.id = ft.local_level_entity_id
JOIN entities dist ON dist.id = ll.parent_entity_id
WHERE ft.fiscal_year_bs = '2082/83'
GROUP BY ll.name_en, dist.name_en, ll.metadata
ORDER BY SUM(ft.amount_npr::numeric) DESC
LIMIT 10;

\echo ''
\echo '=== 11. Sanity: any orphaned entity references? ==='
SELECT 'fiscal_transfers' AS source, count(*) AS orphan_count
FROM local_government_fiscal_transfers ft
LEFT JOIN entities e ON e.id = ft.local_level_entity_id
WHERE e.id IS NULL
UNION ALL
SELECT 'admin_units' AS source, count(*) AS orphan_count
FROM administrative_units au
LEFT JOIN entities e ON e.id = au.entity_id
WHERE e.id IS NULL;
-- Both should be 0.

\echo ''
\echo '=== 12. Wards + polling stations ingested? (depends on admin-hierarchy ingest step running) ==='
SELECT
  (SELECT count(*) FROM entities WHERE kind = 'ward') AS ward_count,
  (SELECT count(*) FROM entities WHERE kind = 'polling_station') AS polling_station_count;
-- Expect: ward ≈ 6,176, polling_station ≈ 10,203

\echo ''
\echo '=== END OF VERIFICATION ==='
