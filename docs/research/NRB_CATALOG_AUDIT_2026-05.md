# NRB Publications & Statistics Catalog Audit (2026-05)

Crawled: 2026-05-20
Crawled by: Worker A (Sonnet 4.6)

---

## Summary

- Total publication categories discovered: 21
- Total downloadable files enumerated: ~350+ (exact count by category below)
- Already-registered sources covered: 6 of 7 (see notes on `nrb-fdi-bulletin` and `nrb-reserves-daily`)
- Newly-discovered sources NOT in our registry: 11 (listed in Gap Analysis)
- Highest-priority gaps: (1) The **Database on Nepalese Economy** is a structured XLSX time-series gold mine covering ~70 named datasets across 5 sectors — none of these are registered and many directly feed our Pulse/Money-Map pillars. (2) The **Economic Bulletin & Indicators** (quarterly, ~35 issues back to 2003) is the richest single-PDF compilation of headline macro indicators outside CMEFs. (3) The **Concessional / Subsidized Loan** monthly XLSX series (FY 2078 onward) captures directed credit flows that are central to the Money Captured pillar and are not in any existing registry entry.

---

## Per-Category Inventory

### Annual Reports

- Latest issue on site: Annual Report 2024-25 English (May 19, 2026, PDF, 10.61 MB) — https://www.nrb.org.np/red/annual-report-2024-25-english/
- Historical coverage: FY 2003/04 → FY 2024/25 (English + Nepali editions)
- Total issues listed: ~22 English + matching Nepali editions; also FIU-Nepal annual reports, Bank Supervision reports, Non-Bank Financial Institution Supervision reports, Money Laundering Prevention Supervision reports — 11 pages of results
- Already-registered in source_registry: NO — no `nrb-annual-report` entry exists
- Crawl note: `/category/annual-report/` 404s; correct URL is `/category/annual-reports` (no trailing slash) — 11 pages, ~100 total items including supervision sub-reports

**Sample file listing (most recent 10):**

| Title | Date | Format | Size | URL |
|-------|------|--------|------|-----|
| Annual Report 2024-25 (English) | 2026-05-19 | PDF | 10.61 MB | https://www.nrb.org.np/red/annual-report-2024-25-english/ |
| FIU-Nepal Annual Report 2081/82 (2024/25) | 2026 | PDF | 15.63 MB | https://www.nrb.org.np/fiu/fiu-nepal-annual-report-2081-82-2024-25/ |
| Annual Report 2081-82 (Nepali) | 2026 | PDF | 13.07 MB | https://www.nrb.org.np/red/annual-report-2081-82-nepali/ |
| Money Laundering Prevention Supervision AR 2081-82 | 2026 | PDF | 4.43 MB | https://www.nrb.org.np/mlpsd/annual-report-2081-82/ |
| Annual Report 2023-24 (English) | 2025 | PDF | 10.13 MB | https://www.nrb.org.np/red/annual-report-2023-24-english/ |
| FIU-Nepal Annual Report 2080/81 (2023/24) | 2025 | PDF | 33.34 MB | https://www.nrb.org.np/fiu/fiu-nepal-annual-report-2080-81-2023-24/ |
| Annual Bank Supervision Report 2024 | 2025 | PDF | 2.82 MB | https://www.nrb.org.np/bsd/annual-bank-supervision-report-2024/ |
| Non-Bank FI Supervision Report 2023/24 | 2025 | PDF | 2.55 MB | https://www.nrb.org.np/nbfisd/non-bank-financial-institutions-supervision-report-2023-24/ |
| Annual Report 2080-81 (Nepali) | 2025 | PDF | 8.98 MB | https://www.nrb.org.np/red/annual-report-2080-81-nepali/ |
| Annual Report 2003-04 (English) | oldest | PDF | 665 KB | https://www.nrb.org.np/red/annual-report-2003-04-english/ |

---

### Current Macro-Economic and Financial Situation (CMEFs)

- Latest issue: CMEFs English Nine-Months 2082/83 (May 11, 2026, PDF, 812.73 KB) — https://www.nrb.org.np/red/current-macroeconomic-and-financial-situation-english-based-on-nine-months-data-of-2025-26/
- Nepali edition: CMEFs Nepali Nine-Months 2082/83 (May 11, 2026, PDF, 778.13 KB) — https://www.nrb.org.np/red/current-macroeconomic-and-financial-situation-nepali-based-on-nine-months-data-of-2082-83/
- Historical coverage: FY 2059/60 (2002/03) → FY 2082/83 (2025/26); FY-based archive URLs at `/category/current-macroeconomic-situation/?department=&fy=<fy-slug>`
- Total issues listed: 23 fiscal years, typically 12 monthly releases per year = ~276 PDFs total (individual year filter pages returned "No posts" — the category index uses JS-filtered display; direct URL by post slug is the reliable path)
- Already-registered in source_registry: YES — `nrb-cmefs-monthly` (parser v0.1.0 active)
- Crawl note: The FY-filtered pages (`?fy=2082-83`, `?fy=2081-82`) return "No posts" — individual report post URLs appear only via the un-filtered category index rendered page. The direct post slug approach (as used by the current downloader) is the correct workaround.

**NCPI Table 2(B) companion CSV** is bundled with each CMEFs release at the same category URL.
- Already-registered: YES — `nrb-ncpi-table`

---

### Economic Bulletin & Indicators (Quarterly)

- Latest: Economic Bulletin-2026 (Mid-Jan) — April 10, 2026, PDF, 8.18 MB — https://www.nrb.org.np/red/economic-bulletin-2026-mid-jan/
- Historical coverage: Mid-April 2003 → Mid-January 2026 (9 pages of pagination)
- Total issues: ~35 (9 pages × ~4 per page, minus duplicates) — quarterly cadence (Jan/Apr/Jul/Oct)
- Already-registered in source_registry: NO

**Recent file listing (10 most recent):**

| Title | Pub Date | Format | Size | Period | URL |
|-------|----------|--------|------|--------|-----|
| Economic Bulletin-2026 (Mid-Jan) | 2026-04-10 | PDF | 8.18 MB | Mid-Jan 2026 | https://www.nrb.org.np/red/economic-bulletin-2026-mid-jan/ |
| Economic Bulletin-2025 (Mid-Oct) | 2026-01-14 | PDF | 8.12 MB | Mid-Oct 2025 | https://www.nrb.org.np/red/economic-bulletin-2025-mid-oct/ |
| Economic Bulletin-2025-07 (Mid July) | 2025-11-06 | PDF | 8.04 MB | Mid-Jul 2025 | https://www.nrb.org.np/red/economic-bulletin-2025-07-mid-july/ |
| Economic Bulletin-2025-04 (Mid April) | 2025-07-16 | PDF | 7.93 MB | Mid-Apr 2025 | https://www.nrb.org.np/red/economic-bulletin-2025-04-mid-april/ |
| Economic Bulletin-2025-01 (Mid January) | 2025-05-16 | PDF | 7.88 MB | Mid-Jan 2025 | https://www.nrb.org.np/red/economic-bulletin-2025-01-mid-january/ |
| Economic Bulletin-2024-10 (Mid Oct) | 2025-03-09 | PDF | 7.83 MB | Mid-Oct 2024 | https://www.nrb.org.np/red/economic-bulletin-2024-10-mid-oct/ |
| Economic Bulletin-2024-07 (Mid July) | 2024-12-24 | PDF | 7.81 MB | Mid-Jul 2024 | https://www.nrb.org.np/red/economic-bulletin-2024-07-mid-july/ |
| Economic Bulletin-2024-04 (Mid April) | 2024-09-20 | PDF | 7.79 MB | Mid-Apr 2024 | https://www.nrb.org.np/red/economic-bulletin-2024-04-mid-april/ |
| Economic Bulletin-2003-07 (Mid July) | oldest | PDF | 564 KB | Mid-Jul 2003 | https://www.nrb.org.np/red/2003-07-mid-july_2003/ |
| Economic Bulletin-2003-04 (Mid April) | oldest | PDF | 517 KB | Mid-Apr 2003 | https://www.nrb.org.np/red/2003-04-mid-april_2003/ |

---

### Monthly Statistics (BFI Monthly XLSX + PDF)

- Latest: 2082-12 (Mid-April 2026) — May 14, 2026, PDF 3.78 MB + XLSX 856.80 KB
  - XLSX: https://www.nrb.org.np/contents/uploads/2026/05/Chaitra_2082_Publish.xlsx
- Historical coverage: Mid-July 2011 (BS 2068-03) → Mid-April 2026 (BS 2082-12)
- Total issues: 18 pages × ~10 per page = ~180 monthly releases; each has both PDF and XLSX
- Already-registered: YES — `nrb-bfi-monthly-xlsx` (active, parser v0.1.0; covers Shrawan 2078 → Bhadau 2082 in on-disk corpus; online archive extends back further to 2068/2011 as PDF-only, XLSX from ~2078)
- Crawl note: Older issues (pre-2078) are PDF-only; XLSX availability begins approximately BS 2078. Older PDFs are scan-embedded and need OCR for table extraction.

**Recent file listing (most recent 10 — each has both PDF and XLSX):**

| Title/Period | Pub Date | XLSX URL | PDF Size | XLSX Size |
|--------------|----------|----------|----------|-----------|
| 2082-12 (Mid-Apr 2026) | 2026-05-14 | https://www.nrb.org.np/contents/uploads/2026/05/Chaitra_2082_Publish.xlsx | 3.78 MB | 857 KB |
| 2082-11 (Mid-Mar 2026) | 2026-04-06 | https://www.nrb.org.np/contents/uploads/2026/04/Falgun_2082_Publish.xlsx | 3.77 MB | 854 KB |
| 2082-10 (Mid-Feb 2026) | 2026-03-13 | https://www.nrb.org.np/contents/uploads/2026/03/Magh_2082_Publish-2.xlsx | 3.76 MB | 863 KB |
| 2082-09 (Mid-Jan 2026) | 2026-02-12 | https://www.nrb.org.np/contents/uploads/2026/02/Poush_2082_Publish.xlsx | 3.75 MB | 861 KB |
| 2082-08 (Mid-Dec 2025) | 2026-01-13 | https://www.nrb.org.np/contents/uploads/2026/01/Mangshir_2082_Publish.xlsx | 3.74 MB | 859 KB |
| 2082-07 (Mid-Nov 2025) | 2025-12-10 | https://www.nrb.org.np/contents/uploads/2025/12/Kartik_2082_Publish.xlsx | 3.72 MB | 856 KB |
| 2082-06 (Mid-Oct 2025) | 2025-11-18 | https://www.nrb.org.np/contents/uploads/2025/11/Asoj_2082_Publish.xlsx | 3.71 MB | 854 KB |
| 2082-05 (Mid-Sep 2025) | 2025-10-17 | https://www.nrb.org.np/contents/uploads/2025/10/Bhadau_2082_Publish.xlsx | 3.70 MB | 850 KB |
| 2082-04 (Mid-Aug 2025) | 2025-09-16 | https://www.nrb.org.np/contents/uploads/2025/09/Saun-2082-Publish.xlsx | 3.69 MB | 848 KB |
| 2082-03 (Mid-Jul 2025) | 2025-08-22 | https://www.nrb.org.np/contents/uploads/2025/08/Asar_2082_Publish.xlsx | 3.69 MB | 850 KB |
| 2068-03 (Mid-Jul 2011) | oldest | PDF only | 740 KB | — |

---

### Banking and Financial Statistics (Quarterly Bulletin)

- Latest: No 61 July 2015 (last on-site issue)
- Historical coverage: Mid-April 2001 (No. 37) → July 2015 (No. 61); 3 pages of results, ~30 issues total
- Already-registered: YES — `nrb-banking-stats` (paused stub)
- Crawl note: The last issue is No. 61 (July 2015). The quarterly bulletin appears to have been superseded by the monthly XLSX corpus. Breakage mode: issues 39, 44, 46 appear absent (numbering gaps suggesting some were never digitized).

**Sample file listing:**

| Issue | Period | Pub Listed | Format | Size | URL |
|-------|--------|------------|--------|------|-----|
| No 61 | July 2015 | 2019-12-30 | PDF | 2.67 MB | https://www.nrb.org.np/bfr/no_61-july-2015/ |
| No 59 | July 2013 | 2019-12-30 | PDF | 2.14 MB | https://www.nrb.org.np/bfr/no_59-july-2013/ |
| No 57 | July 2011 | 2019-12-30 | PDF | 2.03 MB | https://www.nrb.org.np/bfr/no_57-july-2011/ |
| No 37 | Mid-Apr 2001 | oldest | PDF | 315 KB | https://www.nrb.org.np/bfr/no_37-mid_april_2001/ |

---

### Financial Stability Report (FSR)

- Latest: FSR FY 2023/24 (Issue No. 16) — April 23, 2025, PDF, 3.26 MB — https://www.nrb.org.np/bfr/financial-stability-report-fy-2023-24-issue-no-16/
- Historical coverage: Issue No. 1 (July 2012) → Issue No. 16 (FY 2023/24); annual cadence
- Total issues: 16 (2 pages)
- Already-registered: NO

**Full file listing:**

| Issue | Period | Pub Date | Format | Size | URL |
|-------|--------|----------|--------|------|-----|
| No. 16 | FY 2023/24 | 2025-04-23 | PDF | 3.26 MB | https://www.nrb.org.np/bfr/financial-stability-report-fy-2023-24-issue-no-16/ |
| No. 15 | FY 2022/23 | 2024-06-18 | PDF | 2.93 MB | https://www.nrb.org.np/bfr/financial-stability-report-fy-2022-23-issue-no-15-july-2023/ |
| No. 14 | FY 2021/22 | 2023-06-23 | PDF | 2.52 MB | https://www.nrb.org.np/bfr/financial-stability-report-fy-2021-22-issue-no-14-july-2022/ |
| No. 13 | FY 2020/21 | 2022-05-19 | PDF | 1.84 MB | https://www.nrb.org.np/bfr/financial-stability-report-fy-2020-21-issue-no-13-july-2021/ |
| No. 12 | FY 2019/20 | 2021-04-26 | PDF | 3.89 MB | https://www.nrb.org.np/bfr/financial-stability-report-fy-2019-20-issue-no-12-july-2020/ |
| No. 11 | FY 2018/19 | 2020-07-15 | PDF | 1.54 MB | https://www.nrb.org.np/bfr/financial-stability-report-fy-2018-19/ |
| No. 10 | July 2018 | 2020-02-07 | PDF | 3.19 MB | https://www.nrb.org.np/bfr/issue-no-10-july-2018/ |
| No. 9 | July 2017 | 2020-02-07 | PDF | 3.28 MB | https://www.nrb.org.np/bfr/issue-no-9-july-2017/ |
| No. 8 | July 2016 | 2020-02-07 | PDF | 2.56 MB | https://www.nrb.org.np/bfr/issue-no-8-july-2016/ |
| No. 7 | July 2015 | 2020-02-07 | PDF | 1.68 MB | https://www.nrb.org.np/bfr/issue-no-7-july-2015/ |
| No. 6 | Jan 2015 | 2020-02-07 | PDF | 1.62 MB | https://www.nrb.org.np/bfr/issue-no-6-january-2015/ |
| No. 5 | July 2014 | 2020-02-07 | PDF | 176 KB | https://www.nrb.org.np/bfr/issue-no-5-july-2014/ |
| No. 4 | Jan 2014 | 2020-02-07 | PDF | 2.73 MB | https://www.nrb.org.np/bfr/issue-no-4-january-2014/ |
| No. 3 | July 2013 | 2020-02-07 | PDF | 3.03 MB | https://www.nrb.org.np/bfr/issue-no-3-july-2013/ |
| No. 2 | Jan 2013 | 2020-02-07 | PDF | 5.60 MB | https://www.nrb.org.np/bfr/issue-no-2-january-2013/ |
| No. 1 | July 2012 | 2020-02-07 | PDF | 3.50 MB | https://www.nrb.org.np/bfr/issue-no-1-july-2012/ |

---

### Concessional / Subsidized Loan (monthly XLSX)

- Latest: Subsidized loan Chaitra end 2082 — May 14, 2026, PDF 432 KB + XLSX 384 KB
  - XLSX: https://www.nrb.org.np/contents/uploads/2026/05/Interest-subsidized-loan-Chaitra-2082-Publish.xlsx
- Historical coverage: Jeth end 2078 (July 2021) → Chaitra 2082 (May 2026); 8 pages
- Total issues: ~75 monthly releases; also "Refinance FY 2077/78" and "Business Continuity Asar 2078" companion reports
- Already-registered: NO

**Sample file listing (most recent 6):**

| Period | Pub Date | XLSX URL | XLSX Size |
|--------|----------|----------|-----------|
| Chaitra end 2082 | 2026-05-14 | https://www.nrb.org.np/contents/uploads/2026/05/Interest-subsidized-loan-Chaitra-2082-Publish.xlsx | 384 KB |
| Falgun end 2082 | 2026-04-06 | https://www.nrb.org.np/contents/uploads/2026/04/Interest-subsidized-loan-Falgun-2082-Publish.xlsx | 384 KB |
| Magh end 2082 | 2026-03-13 | https://www.nrb.org.np/contents/uploads/2026/03/Interest-subsidized-loan-Magh-2082-Publish-1.xlsx | 384 KB |
| Poush end 2082 | 2026-02-12 | https://www.nrb.org.np/contents/uploads/2026/02/Interest-subsidized-loan-Poush-2082-Publish.xlsx | 385 KB |
| Mangshir end 2082 | 2026-01-13 | https://www.nrb.org.np/contents/uploads/2026/01/Interest-subsidized-loan-excluding-settle-accounts-to-be-published-Mangshir-2082.xlsx | 385 KB |
| Jeth end 2078 | 2021-07-15 | oldest (PDF): https://www.nrb.org.np/bfr/subsidized-loan/ | 388 KB |

---

### Economic Review (Academic Journal)

- Latest: "Time-Varying Efficiency and Volatility Regimes in Nepal Stock Exchange" — April 9, 2026, PDF, 2.80 MB
- Historical coverage: Vol. 24 (pre-2013) → 2026; 8 pages of individual papers
- Total issues: 8 pages × ~10 = ~80 papers; individual-article PDF releases
- Already-registered: NO
- Relevance: academic research papers; low-priority for Pulse ingestion; useful for Fact Ledger citations on structural claims

---

### Study Reports

- Latest: "A Report on the Status of Real Estate Market in Nepal" — April 13, 2026, PDF, 1.93 MB — https://www.nrb.org.np/red/a-report-on-the-status-of-real-estate-market-in-nepal/
- Coverage: ad-hoc, spanning many years; 11 pages, ~100+ reports
- Already-registered: YES (partially) — the FDI Survey Report is the FDI bulletin (`nrb-fdi-bulletin`); other sub-topics unregistered
- Notable sub-series visible:
  - FDI Survey Report (annual): `nrb-fdi-bulletin` covers this — see gap analysis note
  - CPI Compilation Report: "Report on Compilation of Consumer Price Index in Nepal" (2025-11-23) and "A brief Technical Note On CPI (Base Year 2023/24)" (2024-10-09) — methodology docs, not ingested data
  - Real Estate Market Report (2026-04-13) — unregistered; useful for housing price context
  - Salary and Wage Index Survey Report (2025-01-22)

---

### Financial Corporations Survey (FCS)

- Coverage: FY 2076/77–2079/80 (2019/20–2022/23) + FY 2080/81 + FY 2081/82 + FY 2082/83 (current, no posts yet)
- Crawl note: All fiscal-year-filtered pages returned "No posts" — likely JS-filtered or content not yet published for recent years. FCS data for FY 2076/77–2079/80 likely exists but is not surfacing via the filter URL.
- Already-registered: NO — not in registry despite being a major monetary statistics series (IMF-aligned)
- Category URL: https://www.nrb.org.np/category/financial-corporations-survey/

---

### Interest Rate Structure Archives

- Latest: Interest Rate Structure as of MFIs Poush 2079 (Mid-Jan 2023) — https://www.nrb.org.np/mfd/interest-rate-structure-as-of-mfis-poush-2079-mid-jan-2023/
- Historical coverage: Mid-May 2010 (BS 2067-01) → Mid-Jan 2023; 3 pages, ~25 issues
- Format: PDF (~40-115 KB each)
- Already-registered: NO
- Crawl note: The category `/category/interest-rate-structure/` works; the alias `/category/interest-rates/` and `/category/interest-rate-archives/` return 404. The series appears discontinued (last entry 2023); the Database on Nepalese Economy has a live "Structure of Interest Rate" monthly XLSX replacing it.

---

### Quarterly Financial Highlights of Commercial Banks

- Historical coverage: Q1 FY 2007/08 → Q1 FY 2010/11; 3 pages, ~15 issues
- Format: PDF (~35–152 KB each)
- Already-registered: NO
- Crawl note: Appears discontinued — the last entry is Q1 FY 2010/11. Content superseded by Monthly Statistics XLSX corpus.

---

### Central Bank Survey and Liquidity Position (NRB Summarized Balance Sheet)

- Cadence: Daily (published every working day of each BS month)
- Latest: 2083.02.05-NRB Summarized Balance Sheet (May 20, 2026, PDF, 38.53 KB)
- Historical coverage: Srawan 2082 (FY 2082/83) visible; older FY available via month filter
- URL pattern: `/category/central-bank-survey-and-liquidity-position/?department=red&fy=<fy>&month=<month>`
- Format: PDF (~38–41 KB per day)
- Already-registered: NO — partly maps to `nrb-reserves-daily` stub but that entry is vague ("may be weekly")

---

### Economic Activities Study Reports (Provincial)

- Latest visible: "अर्ध वार्षिक आर्थिक गतिविधि अध्ययन प्रतिवेदन २०८२-८३ (बागमती प्रदेश)" — May 14, 2026, PDF, 598 KB — https://www.nrb.org.np/red/[url-encoded-slug]/
- Pattern: Semi-annual provincial economic activity study reports; each of NRB's provincial offices publishes for its province
- Already-registered: NO
- Category URL: The correct path is under `red` or `skt` department slugs; `/category/economic-activities-study-report/` and `/category/economic-activity-study-report/` both return 404 — use `/category/study-reports/` as the parent

---

### Database on Nepalese Economy (TIME-SERIES GOLD MINE)

The database is structured into 5 sectors. All files are XLSX, hosted at `https://www.nrb.org.np/contents/uploads/<year>/<month>/<filename>.xlsx`. Already-registered: NO (none of these 70+ datasets are registered).

**Real Sector (22 datasets):**

| Dataset | Freq | URL |
|---------|------|-----|
| Hydroelectricity Consumption | Monthly | https://www.nrb.org.np/contents/uploads/2026/01/Hydroelectricity-consumption.xlsx |
| Petroleum Import and Sales | Monthly | https://www.nrb.org.np/contents/uploads/2026/01/Tourist-arrivals-1.xlsx |
| Price (Monthly CPI) | Monthly | https://www.nrb.org.np/contents/uploads/2026/01/Price-Monthly.xlsx |
| Quarterly GDP (Old) | Quarterly | https://www.nrb.org.np/contents/uploads/2025/06/Quarterly-GDP.xlsx |
| Manufacturing Production Index (MPI) | Quarterly | https://www.nrb.org.np/contents/uploads/2025/11/Manufacturing-production-index-1.xlsx |
| Quarterly GDP (New) | Quarterly | https://www.nrb.org.np/contents/uploads/2025/08/Quarterly-GDP-2081-82Q2.xlsx |
| Agriculture Inputs | Yearly | https://www.nrb.org.np/contents/uploads/2025/06/Agriculture-inputs.xlsx |
| Agriculture Production | Yearly | https://www.nrb.org.np/contents/uploads/2025/06/Agriculture-production.xlsx |
| Consumer Price Index | Yearly | https://www.nrb.org.np/contents/uploads/2025/06/Consumer-Price-Index.xlsx |
| Education | Yearly | https://www.nrb.org.np/contents/uploads/2025/06/Education.xlsx |
| Energy | Yearly | https://www.nrb.org.np/contents/uploads/2025/06/Energy.xlsx |
| Health | Yearly | https://www.nrb.org.np/contents/uploads/2025/06/Health.xlsx |
| Industry | Yearly | https://www.nrb.org.np/contents/uploads/2025/06/Industry.xlsx |
| National Accounts | Yearly | https://www.nrb.org.np/contents/uploads/2025/07/National-Accounts.xlsx |
| Petroleum Products | Yearly | https://www.nrb.org.np/contents/uploads/2025/06/Petroleum-products.xlsx |
| Provincial GDP | Yearly | https://www.nrb.org.np/contents/uploads/2025/07/Provincial-_GDP_2024_25.xlsx |
| Tourism | Yearly | https://www.nrb.org.np/contents/uploads/2025/06/Tourism.xlsx |
| Transportation and Communication | Yearly | https://www.nrb.org.np/contents/uploads/2025/06/Transportation-and-communication.xlsx |
| WPI and SWRI | Yearly | https://www.nrb.org.np/contents/uploads/2025/06/WPI-and-SWRI.xlsx |

**Financial Sector (40 datasets, selection of key ones):**

| Dataset | Freq | URL |
|---------|------|-----|
| Liquidity and Interbank Rate | Daily | https://www.nrb.org.np/contents/uploads/2026/01/Liquidity-and-interbank-rate.xlsx |
| NEPSE Index and Market Cap | Daily | https://www.nrb.org.np/contents/uploads/2026/01/NEPSE-index-and-market-capitalization.xlsx |
| Asset and Liability of BFIs | Monthly | (upload pattern) |
| Deposits of the BFIs | Monthly | (upload pattern) |
| Electronic Payment Transactions | Monthly | (upload pattern) |
| Loans of the BFIs (Sector-wise) | Monthly | (upload pattern) |
| Loans of the BFIs (Security-wise) | Monthly | (upload pattern) |
| Monetary Survey | Monthly | (upload pattern) |
| Structure of Interest Rate | Monthly | (upload pattern) |
| Number of BFIs | Quarterly | (upload pattern) |
| Balance Sheet of the BFIs | Yearly | (upload pattern) |
| Monetary Survey | Yearly | (upload pattern) |
| Stock Market | Yearly | (upload pattern) |

**External Sector (17 datasets):**

| Dataset | Freq | URL |
|---------|------|-----|
| Balance of Payments (BPM 5) | Monthly | https://www.nrb.org.np/contents/uploads/2026/01/Balance-of-Payments-BPM5.xlsx |
| Balance of Payments (BPM 6) | Monthly | https://www.nrb.org.np/contents/uploads/2026/01/Balance-of-Payments-BPM6.xlsx |
| Exchange Rate | Monthly | https://www.nrb.org.np/contents/uploads/2026/01/Exchange-rate.xlsx |
| Foreign Exchange Reserves | Monthly | https://www.nrb.org.np/contents/uploads/2026/01/Foreign-exchange-reserves.xlsx |
| Foreign Trade | Monthly | https://www.nrb.org.np/contents/uploads/2026/01/Foreign-Trade.xlsx |
| Migrant Workers (Remittance) | Monthly | https://www.nrb.org.np/contents/uploads/2026/01/MIgrant-Workers_.xlsx |
| Tourist Arrivals | Monthly | https://www.nrb.org.np/contents/uploads/2026/01/Tourist-arrivals.xlsx |
| Exports | Yearly | https://www.nrb.org.np/contents/uploads/2025/10/Exports.xlsx |
| Imports | Yearly | https://www.nrb.org.np/contents/uploads/2025/10/Imports-1.xlsx |
| Direction of Foreign Trade | Yearly | https://www.nrb.org.np/contents/uploads/2025/10/Direction-of-foreign-trade.xlsx |

**Fiscal Sector (16 datasets):**

| Dataset | Freq | URL |
|---------|------|-----|
| Government Revenue and Expenditure | Daily | https://www.nrb.org.np/contents/uploads/2025/05/Government-Revenue-and-Expenditure.xlsx |
| Government Budgetary Operation | Monthly | https://www.nrb.org.np/contents/uploads/2025/07/Government-budgetary-operation.xlsx |
| Government Revenue | Monthly | https://www.nrb.org.np/contents/uploads/2025/07/Government-revenue-1.xlsx |
| Outstanding Government Debt | Monthly | https://www.nrb.org.np/contents/uploads/2025/07/Outstanding-government-debt-1.xlsx |

**Survey Data (1 dataset):**

| Dataset | Format | URL |
|---------|--------|-----|
| Financial Literacy Survey | Stata (.zip) | https://www.nrb.org.np/contents/uploads/2022/12/Financial-Literacy-Data-Stata-Format.zip |

---

### NRB Working Papers

- Category `/category/nrb-working-papers/` and `/category/working-papers/` return 404. Working papers appear to be published through the Economic Review category or via ad-hoc Study Reports. No clean archive found.
- Workaround: Search `site:nrb.org.np "working paper"` or use the RED department filter.

---

### Macroeconomic Reports

- Category `/category/macroeconomic-report/` returns 404. The NRB navigation menu lists "Macroeconomic Reports" under Economic Research Department but no valid category slug was confirmed. Reports likely live under `/red/` with various tags.

---

### e-GDDS

- Category `/category/e-gdds/` and `/category/e-gdds` both return 404. NRB participates in the IMF's e-GDDS (Enhanced General Data Dissemination System) but the dedicated category page is not accessible. The underlying datasets are published through the Database on Nepalese Economy sections.

---

## Gap Analysis — Newly-Discovered Sources

The following NRB publication streams are NOT in our `docs/sources/nrb-*.md` registry. Listed in priority order.

---

### 1. nrb-db-external-sector

**Proposed source_id:** `nrb-db-external-sector`
**agency_short:** NRB
**dataset_name:** Database on Nepalese Economy — External Sector (BoP, Forex, Trade, Remittance, Tourism)
**source_url:** https://www.nrb.org.np/database-on-nepalese-economy/external-sector/
**publication_frequency:** monthly (key files); also yearly editions
**reporting_period_type:** monthly
**file_format:** xlsx
**requires_table_extraction:** false (structured XLSX, not PDF)
**estimated_historical_coverage:** likely FY 2065/66 onward (~2008) based on NRB data series depth
**confidence_default:** A
**known_breakage_modes:** URL embeds upload date (`/contents/uploads/<year>/<month>/`), so file path changes each update cycle — parser must fetch the sector page and parse the download link dynamically, not hardcode the URL
**rationale:** Seven monthly XLSX series (BoP BPM5/BPM6, exchange rate, forex reserves, foreign trade, migrant workers/remittance, tourist arrivals) directly power the Money In and Money Out pillars of Pulse v1 without any PDF extraction. These are the most parse-friendly files in the entire NRB catalog.

---

### 2. nrb-db-fiscal-sector

**Proposed source_id:** `nrb-db-fiscal-sector`
**agency_short:** NRB
**dataset_name:** Database on Nepalese Economy — Fiscal Sector (Government Revenue, Expenditure, Debt)
**source_url:** https://www.nrb.org.np/database-on-nepalese-economy/fiscal-sector/
**publication_frequency:** monthly
**reporting_period_type:** monthly
**file_format:** xlsx
**requires_table_extraction:** false
**estimated_historical_coverage:** likely FY 2065/66 onward
**confidence_default:** B (NRB compiles from MoF; preliminary figures revised)
**known_breakage_modes:** Same upload-URL pattern issue as external sector; dynamic link parsing required
**rationale:** Government Revenue and Expenditure (daily), Government Budgetary Operation (monthly), Outstanding Government Debt (monthly) directly populate the Money Out and Money Wasted pillars.

---

### 3. nrb-db-financial-sector

**Proposed source_id:** `nrb-db-financial-sector`
**agency_short:** NRB
**dataset_name:** Database on Nepalese Economy — Financial Sector (BFI Assets, Deposits, Loans, Monetary Survey, Interest Rates, NEPSE)
**source_url:** https://www.nrb.org.np/database-on-nepalese-economy/financial-sector/
**publication_frequency:** monthly (core); daily (liquidity/NEPSE)
**reporting_period_type:** monthly
**file_format:** xlsx
**requires_table_extraction:** false
**estimated_historical_coverage:** likely FY 2065/66 onward
**confidence_default:** A
**known_breakage_modes:** Dynamic upload URL; ~40 datasets in this sector — parser must enumerate all, not hardcode; some datasets (e.g., "Electronic Payment Transactions") may have structural breaks when new payment rails were introduced
**rationale:** Loans by sector, monetary survey, and interest rate structure datasets feed the Money Captured pillar and validate against the `nrb-bfi-monthly-xlsx` corpus. The sector-wise loan data here is a clean XLSX alternative to the complex multi-block BFI monthly XLSX.

---

### 4. nrb-db-real-sector

**Proposed source_id:** `nrb-db-real-sector`
**agency_short:** NRB
**dataset_name:** Database on Nepalese Economy — Real Sector (GDP, CPI, Agriculture, Industry, Tourism, Energy)
**source_url:** https://www.nrb.org.np/database-on-nepalese-economy/real-sector/
**publication_frequency:** quarterly (GDP); monthly (price, energy); yearly (agriculture, national accounts)
**reporting_period_type:** quarterly
**file_format:** xlsx
**requires_table_extraction:** false
**estimated_historical_coverage:** National Accounts likely back to FY 2060/61; GDP quarterly from ~2072
**confidence_default:** B (NRB compiles from CBS/MoALD; preliminary)
**known_breakage_modes:** "Quarterly GDP (Old)" and "Quarterly GDP (New)" reflect a base-year revision — parsers must handle two incompatible series; Provincial GDP is a separate file
**rationale:** National Accounts (GDP) and the quarterly GDP series are foundational context for the "Where Money Becomes Wealth" pillar and every per-capita comparison in the Household Ledger Calculator.

---

### 5. nrb-financial-stability-report

**Proposed source_id:** `nrb-financial-stability-report`
**agency_short:** NRB
**dataset_name:** Financial Stability Report
**source_url:** https://www.nrb.org.np/category/financial-stability-report/
**publication_frequency:** annual (July–October of each year)
**reporting_period_type:** annual
**file_format:** pdf
**requires_table_extraction:** true
**estimated_historical_coverage:** Issue No. 1 (July 2012) → Issue No. 16 (FY 2023/24); 16 issues
**confidence_default:** A
**known_breakage_modes:** URL slug format changed between older issues (at `/red/`) and newer ones (at `/bfr/`); no issue yet for FY 2024/25
**rationale:** The FSR synthesizes systemic risk, NPL ratios, capital adequacy, and financial system stress — the definitive Money Captured quality signal for the Fact Ledger. High editorial value for the Monthly Verdict.

---

### 6. nrb-concessional-loan

**Proposed source_id:** `nrb-concessional-loan`
**agency_short:** NRB
**dataset_name:** Interest-Subsidized / Concessional Loan Monthly Statistics
**source_url:** https://www.nrb.org.np/category/concessional-loan/
**publication_frequency:** monthly
**reporting_period_type:** monthly
**file_format:** xlsx (also PDF companion)
**requires_table_extraction:** false
**estimated_historical_coverage:** Jeth 2078 (May/June 2021) → present; ~75 months, 8 pages
**confidence_default:** A
**known_breakage_modes:** Filename uses Nepali month names with inconsistent transliteration (e.g., "Badau" vs "Bhadau"); some older entries are PDF-only (pre-XLSX transition)
**rationale:** Directed credit subsidies are the mechanism by which the government shapes where private capital flows. This series is essential for the Money Captured pillar and the "Cost of Credit" narrative in Borrowed Time lens.

---

### 7. nrb-economic-bulletin

**Proposed source_id:** `nrb-economic-bulletin`
**agency_short:** NRB
**dataset_name:** Economic Bulletin & Indicators (Quarterly)
**source_url:** https://www.nrb.org.np/category/quarterly-economic-bulletin/
**publication_frequency:** quarterly (January/April/July/October)
**reporting_period_type:** quarterly
**file_format:** pdf
**requires_table_extraction:** true
**estimated_historical_coverage:** Mid-April 2003 → Mid-January 2026 (9 pages, ~35 issues)
**confidence_default:** A
**known_breakage_modes:** PDF size ~8 MB each (dense tables); URL slug uses date format `<year>-<month>-mid-<month-name>`; no XLSX companion
**rationale:** The quarterly Economic Bulletin is the richest single-PDF compilation of ~200 time-series tables covering all economic sectors. It partially overlaps CMEFs but has deeper historical tables and is released quarterly. Useful for filling monthly-statistics gaps between CMEFs releases.

---

### 8. nrb-annual-report

**Proposed source_id:** `nrb-annual-report`
**agency_short:** NRB
**dataset_name:** NRB Annual Report (English + Nepali)
**source_url:** https://www.nrb.org.np/category/annual-reports
**publication_frequency:** annual
**reporting_period_type:** annual
**file_format:** pdf
**requires_table_extraction:** true
**estimated_historical_coverage:** FY 2003/04 → FY 2024/25 (22 years); 11 pages of results
**confidence_default:** A
**known_breakage_modes:** The category slug is `annual-reports` (plural, no trailing slash); also note FIU and supervision sub-reports are mixed into the same archive category under different department slugs (`fiu/`, `bsd/`, `nbfisd/`, `mlpsd/`)
**rationale:** The Annual Report carries the official audited macro-economic tables for each FY — the gold standard for any historical baseline. Required for back-filling Pulse indicators before monthly XLSX coverage begins (pre-2078).

---

### 9. nrb-fdi-survey (extends nrb-fdi-bulletin)

**Proposed source_id:** (update existing `nrb-fdi-bulletin` source URL)
**agency_short:** NRB
**dataset_name:** Survey Report on Foreign Direct Investment in Nepal
**source_url:** https://www.nrb.org.np/red/survey-report-on-foreign-direct-investment-2023-24/ (per-year slug)
**publication_frequency:** annual
**reporting_period_type:** annual
**file_format:** pdf
**requires_table_extraction:** true
**estimated_historical_coverage:** FY 2022/23 and FY 2023/24 visible; likely back to ~2076/77
**confidence_default:** A
**known_breakage_modes:** Slug includes year (e.g., `-2023-24`); no consistent category URL — lives under `/red/` or `/category/study-reports/`. The existing `nrb-fdi-bulletin` stub has source_url as `https://www.nrb.org.np/` which is too vague — update to per-report search on the study-reports category.
**rationale:** FDI by country and sector is the core Money In foreign capital signal.

---

### 10. nrb-central-bank-balance-sheet-daily

**Proposed source_id:** `nrb-central-bank-balance-sheet-daily`
**agency_short:** NRB
**dataset_name:** NRB Summarized Balance Sheet (Daily)
**source_url:** https://www.nrb.org.np/category/central-bank-survey-and-liquidity-position/?department=red
**publication_frequency:** daily (each working day)
**reporting_period_type:** daily
**file_format:** pdf
**requires_table_extraction:** true (small, ~38 KB; simple table)
**estimated_historical_coverage:** FY 2080/81 onward (confirmed); possibly older via month filter
**confidence_default:** A
**known_breakage_modes:** Page uses month+FY filter navigation; no direct archive list; URL pattern is consistent (`/red/YYYY-MM-DD-nrb-summarized-balance-sheet/`). This replaces and corrects the vague `nrb-reserves-daily` stub (which speculated "may be weekly" — confirmed daily).
**rationale:** Daily central bank balance sheet captures NRB's own monetary operations (OMO, sterilization, reserve money). The liquidity position from these sheets feeds the Pulse "interbank rate" tile and validates the Database on Nepalese Economy daily liquidity XLSX.

---

### 11. nrb-financial-corporations-survey

**Proposed source_id:** `nrb-financial-corporations-survey`
**agency_short:** NRB
**dataset_name:** Financial Corporations Survey (FCS)
**source_url:** https://www.nrb.org.np/category/financial-corporations-survey/
**publication_frequency:** annual (by FY groupings)
**reporting_period_type:** annual
**file_format:** pdf
**requires_table_extraction:** true
**estimated_historical_coverage:** FY 2076/77–2079/80 confirmed; likely FY 2080/81+ when published
**confidence_default:** A
**known_breakage_modes:** FY-filtered category pages return "No posts" even when data exists — must use the un-filtered category page or search by post slug. Groupings of multiple FYs in one release (e.g., "2076/77-2079/80").
**rationale:** The FCS follows IMF MFSM (Monetary and Financial Statistics Manual) methodology — the standard-compliant view of the Nepali financial system used by IMF Article IV reviews. Complements the BFI monthly XLSX which is NRB's own format.

---

## "Latest Data We Should Pull" List

Priority ordered for the money-flow narrative:

| Priority | Source | Latest File | URL |
|----------|--------|-------------|-----|
| 1 | CMEFs English (nrb-cmefs-monthly) | Nine-Months 2082/83 | https://www.nrb.org.np/red/current-macroeconomic-and-financial-situation-english-based-on-nine-months-data-of-2025-26/ |
| 2 | Monthly Statistics XLSX (nrb-bfi-monthly-xlsx) | Chaitra 2082 | https://www.nrb.org.np/contents/uploads/2026/05/Chaitra_2082_Publish.xlsx |
| 3 | DB External: Migrant Workers/Remittance | Jan 2026 update | https://www.nrb.org.np/contents/uploads/2026/01/MIgrant-Workers_.xlsx |
| 4 | DB External: Foreign Exchange Reserves | Jan 2026 update | https://www.nrb.org.np/contents/uploads/2026/01/Foreign-exchange-reserves.xlsx |
| 5 | DB External: Balance of Payments BPM6 | Jan 2026 update | https://www.nrb.org.np/contents/uploads/2026/01/Balance-of-Payments-BPM6.xlsx |
| 6 | DB External: Foreign Trade | Jan 2026 update | https://www.nrb.org.np/contents/uploads/2026/01/Foreign-Trade.xlsx |
| 7 | Financial Stability Report | Issue No. 16 (FY 2023/24) | https://www.nrb.org.np/bfr/financial-stability-report-fy-2023-24-issue-no-16/ |
| 8 | DB Fiscal: Government Budgetary Operation | Jul 2025 update | https://www.nrb.org.np/contents/uploads/2025/07/Government-budgetary-operation.xlsx |
| 9 | Concessional Loan XLSX | Chaitra 2082 | https://www.nrb.org.np/contents/uploads/2026/05/Interest-subsidized-loan-Chaitra-2082-Publish.xlsx |
| 10 | DB Real: National Accounts | Jul 2025 update | https://www.nrb.org.np/contents/uploads/2025/07/National-Accounts.xlsx |
| 11 | Economic Bulletin | Mid-Jan 2026 | https://www.nrb.org.np/red/economic-bulletin-2026-mid-jan/ |
| 12 | Annual Report 2024-25 (English) | May 2026 | https://www.nrb.org.np/red/annual-report-2024-25-english/ |
| 13 | DB Real: Quarterly GDP (New) | Aug 2025 update | https://www.nrb.org.np/contents/uploads/2025/08/Quarterly-GDP-2081-82Q2.xlsx |
| 14 | DB Financial: Loans BFI Sector-wise | Jan 2026 update | (fetch dynamically from /database-on-nepalese-economy/financial-sector/) |
| 15 | NCPI Table 2(B) CSV (nrb-ncpi-table) | Nine-Months 2082/83 | bundled at same category URL as CMEFs |

---

## Crawl Notes & Blockers

### 404 Patterns (category slug issues)
The following category slugs return 404 — use the working alternatives:

| Broken slug | Working alternative |
|-------------|---------------------|
| `/category/annual-report/` | `/category/annual-reports` (no trailing slash, plural) |
| `/category/macroeconomic-report/` | No clean URL found; content lives at `/red/` with tags |
| `/category/working-papers/` | No clean URL found; see Study Reports |
| `/category/nrb-working-papers/` | Same — 404 |
| `/category/e-gdds/` | 404 — content served via Database on Nepalese Economy sub-pages |
| `/category/interest-rates/` | Use `/category/interest-rate-structure/` |
| `/category/interest-rate-archives/` | Use `/category/interest-rate-structure/` |
| `/category/quarterly-financial-highlights/` | Use `/category/quarterly-financial-highlights-of-commercial-banks/` |
| `/category/economic-activities-study-report/` | Use `/category/study-reports/` |
| `/category/database-on-nepalese-economy/` | Use `/database-on-nepalese-economy/` (no `category/` prefix) |
| `/publications/` | 404 — navigate via the homepage menu structure |

### JS-Filtered Category Pages
The CMEFs category (`/category/current-macroeconomic-situation/`) and FCS category (`/category/financial-corporations-survey/`) use JS-rendered FY filters. The un-filtered index and the individual post slug (`/red/<slug>/`) are the reliable extraction targets. Parameterized URLs (`?fy=2082-83`) return "No posts" even when content exists.

### Requires OCR (Scan-Only PDFs)
Monthly Statistics issues pre-BS 2078 (pre-approximately 2021) are PDF-only with no XLSX companion. Spot-checks suggest these are typeset PDFs (not scan-only), but structure verification is needed before parser work. The Banking and Financial Statistics quarterly bulletins (No. 37–61, 2001–2015) are typeset PDFs; table extraction with pdfplumber should work.

### Database on Nepalese Economy — URL Stability Risk
All XLSX download URLs embed the upload date (`/contents/uploads/<year>/<month>/`). File paths change with each update cycle. A downloader must scrape the sector page to extract the current link rather than hardcoding a static URL. This is a critical breakage mode for all 70+ Database datasets.

### Financial Corporations Survey — Content Availability
FCS category pages return "No posts" for all FY filters. The actual FCS PDFs may live under the un-filtered category index or require a direct search. This needs a follow-up manual check.

### CMEFs Nepali Edition — Out of Scope (ADR-0003 / Path B1)
The Nepali (Devanagari) CMEFs edition is published at the same cadence but is out of scope for the current parser per the `nrb-cmefs-monthly` source profile. The Devanagari numerals require verified OCR (see `docs/research/surya-ocr-findings.md`).

### NRB Working Papers
No dedicated archive category found. Working papers appear to be scattered across `/red/` posts and the Economic Review journal. A site-search approach is needed for systematic enumeration.

### Estimated File Counts by Category

| Category | Approx Files | Format |
|----------|-------------|--------|
| Monthly Statistics (BFI XLSX) | ~180 | PDF + XLSX |
| Annual Reports (all sub-types) | ~100 | PDF |
| Economic Review (journal) | ~80 | PDF |
| Study Reports | ~100 | PDF |
| Concessional Loan | ~75 | PDF + XLSX |
| Economic Bulletin (quarterly) | ~35 | PDF |
| Financial Stability Report | 16 | PDF |
| Banking & Financial Statistics | ~30 | PDF |
| Interest Rate Structure | ~25 | PDF |
| Quarterly Financial Highlights | ~15 | PDF |
| Database on Nepalese Economy | ~70 datasets (single files, updated in-place) | XLSX |
| Central Bank Daily Balance Sheet | ~250/year × n years | PDF |
| CMEFs (all years) | ~276 | PDF + companion CSV |
| **Total enumerated** | **~1,300+** | |
