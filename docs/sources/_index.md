<!-- GENERATED — do not edit. Run: pnpm gen:source-index -->

# Source Registry — Index

Generated from `scripts/seed-source-registry.ts` (the canonical seed).
For schema + workflow, see [`../SOURCE_REGISTRY.md`](../SOURCE_REGISTRY.md).
For the lifetime contract, see [ADR-0009](../decisions/0009-source-registry-single-source-of-truth.md).

Total registered sources: 50

| Tier | Source ID | Agency | Dataset | Frequency | Mode | Status |
|---|---|---|---|---|---|---|
| Tier 0 | [nrb-cmefs-monthly](nrb-cmefs-monthly.md) | NRB | Current Macroeconomic and Financial Situation | monthly | manual_upload | active |
| Tier 0 | [nrb-ncpi-table](nrb-ncpi-table.md) | NRB | NCPI Table 2(B) | monthly | manual_upload | active |
| Tier 1 | [customs-monthly-trade](customs-monthly-trade.md) | Customs | Monthly trade statistics (imports + exports) | monthly | automated_cron | paused |
| Tier 1 | [fcgo-daily](fcgo-daily.md) | FCGO | Daily revenue + expenditure (preliminary) | daily | automated_cron | paused |
| Tier 1 | [kalimati-daily-prices](kalimati-daily-prices.md) | Kalimati | Daily wholesale fruit & vegetable prices | daily | automated_cron | paused |
| Tier 1 | [local-fiscal-transfers-cleaned](local-fiscal-transfers-cleaned.md) | MoF | Federal fiscal transfers to 753 local levels, FY 2082/83 (pre-cleaned XLSX) | annual | manual_upload | active |
| Tier 1 | [nepse-eod](nepse-eod.md) | NEPSE | End-of-day quotes + market cap by stock | daily | automated_cron | paused |
| Tier 1 | [noc-petroleum-monthly](noc-petroleum-monthly.md) | NOC | Petroleum imports + price-revision notices | monthly | manual_upload | paused |
| Tier 1 | [nrb-reserves-daily](nrb-reserves-daily.md) | NRB | Daily foreign exchange reserve disclosure | daily | automated_cron | paused |
| Tier 2 | [dofe-labour-migration](dofe-labour-migration.md) | DoFE | Monthly labour permits + airport-records | monthly | manual_upload | paused |
| Tier 2 | [nrb-banking-stats](nrb-banking-stats.md) | NRB | Banking and Financial Statistics (quarterly bulletin) | quarterly | manual_upload | paused |
| Tier 2 | [nrb-fdi-bulletin](nrb-fdi-bulletin.md) | NRB | Status of FDI in Nepal (annual bulletin) | annual | manual_upload | paused |
| Tier 2 | [nrb-loans-by-sector](nrb-loans-by-sector.md) | NRB | Loans & advances by economic sector | quarterly | manual_upload | paused |
| Tier 2 | [nso-gdp](nso-gdp.md) | NSO | Quarterly GDP estimates | quarterly | manual_upload | paused |
| Tier 2 | [ntb-tourism-monthly](ntb-tourism-monthly.md) | NTB | Monthly arrivals + receipts | monthly | automated_cron | paused |
| Tier 2 | [pdmo-debt-bulletin](pdmo-debt-bulletin.md) | PDMO | Quarterly public debt bulletin | quarterly | manual_upload | paused |
| Tier 3 | [coops-regulatory-status](coops-regulatory-status.md) | DoC | Cooperative regulatory status + Sahakari Bibhag directory | ad_hoc | manual_upload | paused |
| Tier 3 | [doed-project-pipeline](doed-project-pipeline.md) | DoED | Hydropower licence + project pipeline registry | ad_hoc | manual_upload | paused |
| Tier 3 | [dpm-public-enterprises-annual](dpm-public-enterprises-annual.md) | DPM | Annual Performance Review of Public Enterprises (Yellow Book) | annual | manual_upload | paused |
| Tier 3 | [ird-revenue-monthly](ird-revenue-monthly.md) | IRD | Monthly revenue dashboard | monthly | automated_cron | paused |
| Tier 3 | [moald-crop-production](moald-crop-production.md) | MoALD | Seasonal crop production statistics | seasonal | manual_upload | paused |
| Tier 3 | [mof-lmbis](mof-lmbis.md) | MoF | Line Ministry Budget Information System (federal budget execution) | monthly | automated_cron | paused |
| Tier 3 | [mof-sutra](mof-sutra.md) | MoF | Sub-national Treasury Regulatory Application (SuTRA) | monthly | automated_cron | paused |
| Tier 3 | [nea-generation-monthly](nea-generation-monthly.md) | NEA | Monthly hydropower generation snapshots | monthly | manual_upload | paused |
| Tier 3 | [nea-power-export](nea-power-export.md) | NEA | Power export revenue (to India) | annual | manual_upload | paused |
| Tier 3 | [nnrfc-allocations](nnrfc-allocations.md) | NNRFC | Fiscal transfer allocations to provincial + local levels | annual | manual_upload | paused |
| Tier 3 | [npc-project-bank](npc-project-bank.md) | NPC | Project Bank + line-ministry monitoring | ad_hoc | manual_upload | paused |
| Tier 3 | [oag-audit-reports](oag-audit-reports.md) | OAG | Annual audit reports (federal + sectoral) | annual | manual_upload | paused |
| Tier 4 | [cehrd-emis](cehrd-emis.md) | CEHRD | Education Management Information System (EMIS) | annual | manual_upload | paused |
| Tier 4 | [census-2078-district](census-2078-district.md) | NSO | Census 2078 district-level disaggregated data | ad_hoc | manual_upload | paused |
| Tier 4 | [customs-exemptions](customs-exemptions.md) | Customs | Customs duty exemption list (budget annex) | annual | manual_upload | paused |
| Tier 4 | [dhm-hydro-met](dhm-hydro-met.md) | DHM | Flood / discharge / precipitation records | daily | automated_cron | paused |
| Tier 4 | [dohs-hmis](dohs-hmis.md) | DoHS | Health Management Information System (HMIS) | annual | manual_upload | paused |
| Tier 4 | [dolm-malpot-stats](dolm-malpot-stats.md) | DoLM | Malpot land-transaction statistics | monthly | manual_upload | paused |
| Tier 4 | [fepb-manpower-companies](fepb-manpower-companies.md) | FEPB | Recruitment-cost ceilings + manpower licenses | ad_hoc | manual_upload | paused |
| Tier 4 | [ird-top-taxpayers](ird-top-taxpayers.md) | IRD | Top Taxpayers annual disclosure + LTO data | annual | manual_upload | paused |
| Tier 4 | [moe-noc-student-outflow](moe-noc-student-outflow.md) | MoE | No Objection Letter (NOC) data — student outflow | monthly | manual_upload | paused |
| Tier 4 | [mof-budget-redbook](mof-budget-redbook.md) | MoF | Federal Budget Red Book + Mid-Term Review | annual | manual_upload | paused |
| Tier 4 | [mof-dfimis](mof-dfimis.md) | MoF | Aid Management Platform / DFIMIS — foreign aid disbursement | quarterly | automated_cron | paused |
| Tier 4 | [ndrrma-damage-tally](ndrrma-damage-tally.md) | NDRRMA | Disaster damage tally | ad_hoc | automated_cron | paused |
| Tier 4 | [nrn-investment-tracker](nrn-investment-tracker.md) | NRN | Diaspora / NRN investment + IBN disclosures | ad_hoc | manual_upload | paused |
| Tier 4 | [oag-lbl-local-audits](oag-lbl-local-audits.md) | OAG | Local-body audit reports (OAG-LBL) | annual | manual_upload | paused |
| Tier 4 | [un-comtrade](un-comtrade.md) | UNSD | UN Comtrade — trade partner perspective on Nepal | annual | automated_cron | paused |
| Reference | adb-ado-nepal | ADB | Asian Development Outlook — Nepal section | annual | reference_only | active |
| Reference | imf-article-iv | IMF | Article IV consultation reports — Nepal | annual | reference_only | active |
| Reference | mof-economic-survey-annual | MoF | Economic Survey (annual) | annual | reference_only | active |
| Reference | ndhs-survey | MoHP | Nepal Demographic & Health Survey (NDHS) | ad_hoc | reference_only | active |
| Reference | nlss-survey | NSO | Nepal Living Standards Survey (NLSS) | ad_hoc | reference_only | active |
| Reference | npc-16th-plan | NPC | 16th Five-Year Plan (FY 2081/82–2085/86) | ad_hoc | reference_only | active |
| Reference | wb-wdi | WB | World Development Indicators (WDI) — Nepal | annual | reference_only | active |
