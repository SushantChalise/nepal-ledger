/**
 * Comprehensive live-DB data audit (pnpm audit:data).
 *
 * Produces an authoritative inventory of what data EXISTS, its temporal
 * coverage, its provenance/confidence, and machine-checkable reconciliation
 * results — the anti-hallucination reference for agents and the accuracy
 * baseline for verifying OCR-recovered data. Read-only.
 *
 * Output is sectioned plain text; pipe to docs/DATA_AUDIT.md generation or read
 * directly. Every section is independently guarded so a single failing query
 * never aborts the audit.
 */
import { db as getDb } from '@/lib/db/client';
import { sql } from 'drizzle-orm';

type Row = Record<string, unknown>;

async function section(
  db: ReturnType<typeof getDb>,
  title: string,
  query: ReturnType<typeof sql>,
): Promise<void> {
  console.log(`\n${'='.repeat(78)}\n## ${title}\n${'='.repeat(78)}`);
  try {
    const rows = (await db.execute(query)) as unknown as Row[];
    if (rows.length === 0) {
      console.log('  (no rows)');
      return;
    }
    for (const r of rows) {
      console.log(
        '  ' +
          Object.entries(r)
            .map(([k, v]) => `${k}=${v === null ? '∅' : v}`)
            .join('  '),
      );
    }
  } catch (e: unknown) {
    console.log(`  [SECTION ERROR] ${e instanceof Error ? e.message.slice(0, 200) : String(e)}`);
  }
}

async function main(): Promise<void> {
  const db = getDb();
  console.log(`NEPAL LEDGER — DATA AUDIT`);

  // ── A. Table row counts ────────────────────────────────────────────────
  await section(
    db,
    'A. TABLE ROW COUNTS',
    sql`
    SELECT relname AS table, n_live_tup AS approx_rows
    FROM pg_stat_user_tables
    WHERE schemaname='public'
    ORDER BY n_live_tup DESC`,
  );

  // ── B. Source registry: status + which sources actually have documents ──
  await section(
    db,
    'B. SOURCE REGISTRY STATUS',
    sql`
    SELECT status, count(*)::int AS sources FROM source_registry GROUP BY status ORDER BY status`,
  );
  await section(
    db,
    'B2. SOURCES WITH vs WITHOUT ingested documents (distinct sources)',
    sql`
    SELECT sr.status,
           count(DISTINCT sr.source_id)::int AS registered,
           count(DISTINCT sd.source_id)::int AS with_data,
           count(DISTINCT sr.source_id)::int - count(DISTINCT sd.source_id)::int AS no_data
    FROM source_registry sr
    LEFT JOIN source_documents sd ON sd.source_id = sr.source_id
    GROUP BY sr.status ORDER BY sr.status`,
  );
  await section(
    db,
    'B3. ACTIVE sources with NO ingested data (gap)',
    sql`
    SELECT sr.source_id, sr.agency_short, sr.tier
    FROM source_registry sr
    LEFT JOIN source_documents sd ON sd.source_id = sr.source_id
    WHERE sr.status='active' AND sd.source_id IS NULL
    ORDER BY sr.tier, sr.source_id`,
  );

  // ── C. approved_indicator_values: per-indicator coverage ────────────────
  await section(
    db,
    'C. APPROVED INDICATOR COVERAGE (per indicator)',
    sql`
    SELECT i.slug, i.category, min(a.unit) AS unit,
           count(*)::int AS rows,
           count(DISTINCT a.reporting_period_bs)::int AS periods,
           min(a.reporting_period_bs) AS first_period,
           max(a.reporting_period_bs) AS last_period,
           min(a.confidence_grade) AS conf
    FROM approved_indicator_values a JOIN indicators i ON i.id=a.indicator_id
    GROUP BY i.slug, i.category ORDER BY i.category, i.slug`,
  );

  // ── D. dne_facts: per base measure × dimension coverage ─────────────────
  await section(
    db,
    'D. DNE_FACTS COVERAGE (base measure × dimension)',
    sql`
    SELECT base_indicator_slug, dimension_kind,
           count(*)::int AS rows,
           count(DISTINCT dimension_value)::int AS dims,
           count(DISTINCT reporting_period_bs)::int AS periods,
           min(reporting_period_bs) AS first_p, max(reporting_period_bs) AS last_p,
           min(unit) AS unit, min(confidence_grade) AS conf
    FROM dne_facts GROUP BY base_indicator_slug, dimension_kind
    ORDER BY base_indicator_slug, dimension_kind`,
  );

  // ── E. foreign_aid_facts: per fiscal year ───────────────────────────────
  await section(
    db,
    'E. FOREIGN_AID_FACTS COVERAGE (per fiscal year)',
    sql`
    SELECT reporting_period_bs AS bs_fy, max(fiscal_year_ad_label) AS ad_fy,
           count(*)::int AS rows,
           count(DISTINCT dimension_value) FILTER (WHERE dimension_kind='donor')::int AS donors,
           count(DISTINCT dimension_value) FILTER (WHERE dimension_kind='sector')::int AS sectors,
           min(unit) AS unit, min(confidence_grade) AS conf
    FROM foreign_aid_facts GROUP BY reporting_period_bs ORDER BY reporting_period_bs`,
  );

  // ── F. Other fact tables ────────────────────────────────────────────────
  await section(
    db,
    'F1. CENSUS_FACTS coverage',
    sql`
    SELECT count(*)::int AS rows, count(DISTINCT entity_id)::int AS entities
    FROM census_facts`,
  );
  await section(
    db,
    'F2. BANKING_SECTOR_FACTS coverage',
    sql`
    SELECT count(*)::int AS rows,
           count(DISTINCT reporting_period_bs)::int AS months,
           min(reporting_period_bs) AS first_p, max(reporting_period_bs) AS last_p
    FROM banking_sector_facts`,
  );
  await section(
    db,
    'F3. LOCAL_GOVERNMENT_FISCAL_TRANSFERS coverage',
    sql`
    SELECT count(*)::int AS rows,
           count(DISTINCT fiscal_year_bs)::int AS fiscal_years,
           min(fiscal_year_bs) AS first_fy, max(fiscal_year_bs) AS last_fy
    FROM local_government_fiscal_transfers`,
  );

  // ── G. RECONCILIATION CHECKS (accuracy) ─────────────────────────────────
  await section(
    db,
    'G1. Provincial GDP sum vs national nominal GDP (latest)',
    sql`
    WITH prov AS (
      SELECT reporting_period_bs, sum(value) AS prov_sum
      FROM dne_facts WHERE base_indicator_slug='dne-provincial-gdp' GROUP BY reporting_period_bs)
    SELECT prov.reporting_period_bs, prov.prov_sum::numeric(20,1) AS provincial_sum_npr_million
    FROM prov ORDER BY prov.reporting_period_bs DESC LIMIT 3`,
  );
  await section(
    db,
    'G2. Customs cross-tab reconciliation (composite vs single-dim, imports 2081/82)',
    sql`
    SELECT
      (SELECT sum(value) FROM dne_facts WHERE base_indicator_slug='customs-merchandise-imports'
        AND dimension_kind='commodity' AND reporting_period_bs='2081/82')::numeric(24,1) AS single_dim_total,
      (SELECT sum(value) FROM dne_facts WHERE base_indicator_slug='customs-merchandise-imports'
        AND dimension_kind='customs-import-source' AND reporting_period_bs='2081/82')::numeric(24,1) AS composite_total`,
  );
  await section(
    db,
    'G3. Foreign-aid donor-total vs sector-total per FY (must match)',
    sql`
    SELECT reporting_period_bs AS bs_fy,
      sum(value) FILTER (WHERE dimension_kind='donor')::numeric(20,1) AS donor_total,
      sum(value) FILTER (WHERE dimension_kind='sector')::numeric(20,1) AS sector_total
    FROM foreign_aid_facts GROUP BY reporting_period_bs ORDER BY reporting_period_bs`,
  );
  await section(
    db,
    'G4. Redbook recurrent+capital vs total (FY2074/75, sample 5 heads)',
    sql`
    SELECT dimension_value AS budget_head,
      sum(value) FILTER (WHERE base_indicator_slug='budget-allocation-recurrent')::numeric(20,0)
        + sum(value) FILTER (WHERE base_indicator_slug='budget-allocation-capital')::numeric(20,0) AS rec_plus_cap,
      sum(value) FILTER (WHERE base_indicator_slug='budget-allocation-total')::numeric(20,0) AS stated_total
    FROM dne_facts WHERE base_indicator_slug LIKE 'budget-allocation-%'
    GROUP BY dimension_value ORDER BY stated_total DESC NULLS LAST LIMIT 5`,
  );

  // ── H. Provenance / confidence distribution ─────────────────────────────
  await section(
    db,
    'H1. dne_facts confidence + period-type distribution',
    sql`
    SELECT confidence_grade AS conf, reporting_period_type AS ptype, count(*)::int AS rows
    FROM dne_facts GROUP BY confidence_grade, reporting_period_type ORDER BY rows DESC`,
  );
  await section(
    db,
    'H2. approved_indicator_values by source agency',
    sql`
    SELECT i.source_agency AS agency, count(*)::int AS rows, count(DISTINCT i.slug)::int AS indicators
    FROM approved_indicator_values a JOIN indicators i ON i.id=a.indicator_id
    GROUP BY i.source_agency ORDER BY rows DESC`,
  );

  console.log('\n\nAUDIT COMPLETE.');
  process.exit(0);
}

main().catch((e: unknown) => {
  console.error('[audit] fatal:', e instanceof Error ? e.stack : String(e));
  process.exit(1);
});
