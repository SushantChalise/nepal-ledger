# MoF Publications & Division Publications Catalog Audit (2026-05)

Crawled: 2026-05-20
Crawled by: Worker B (Sonnet claude-sonnet-4-6)

## Crawl Status

**BLOCKER: mof.gov.np SSL certificate fails all direct WebFetch requests** — every attempt to fetch `https://mof.gov.np/*` returned `unable to verify the first certificate`. The Wayback Machine is also blocked by the Claude Code fetch sandbox.

**Workaround used:** A prior scraping run had already captured the site and written its output to `Financial Data/mof_documents/documents_metadata.json` (42 KB, 565 JSON entries from 5 categories). All on-site file enumeration below is derived from that file. Division publications (FCGO, PDMO) were crawled directly — those domains have valid SSL.

---

## Summary

- Total publication categories discovered on mof.gov.np: **5** (agreement, whitebook, redbook, yellowbook, intergovernmental) — Economic Survey, Budget Speech, Mid-Term Review not yet in `documents_metadata.json`; see Gap Analysis
- Total downloadable files enumerated (from metadata + direct crawl): **~130** (65 in metadata.json + 41 FCGO + 15 PDMO + estimated 9+ on mof.gov.np unscraped sections)
- Already-registered sources covered: **6 of 7** (mof-budget-redbook ✓, local-fiscal-transfers-cleaned ✓, mof-dfimis ✓, mof-lmbis ✓, mof-sutra ✓, nnrfc-allocations ✓, fcgo-daily ✓)
- Newly-discovered sources NOT in our registry: **6** (FCGO Financial Statements, FCGO Debt Reports, PDMO Monthly Debt Stats, PDMO Annual Debt Report, PDMO MTDS, mof-economic-survey)
- On-disk vs. on-site delta: mof.gov.np has 1 Red Book newer than our disk copy (2082/83 edition), 1 Yellow Book newer (2082), and 1 Intergovernmental Transfer newer (2082/83); see Cross-Reference section
- Highest-priority gaps: (1) Economic Survey and Budget Speech streams are entirely absent from our source registry and from `documents_metadata.json` — these are MoF's highest-value macroeconomic publications; (2) PDMO monthly government debt statistics is an active monthly series (Chaitra 2082 = most recent) with no registry entry; (3) FCGO Consolidated Financial Statements are published in English and cover FY 2075/76 onward — structurally parseable and zero-cost to register.

---

## Per-category inventory

### Red Book (व्यय अनुमानको विवरण / रातो किताब — Budget Expenditure Details)

**Already-registered:** yes (`mof-budget-redbook`, status: paused, Tier 4)
**Already on disk:** partial — see table below

Files enumerated from `documents_metadata.json` (page 1 of Red Book section — site has multiple pages):

| # | Title (Nepali) | English equiv | FY (BS) | File URL |
|---|---------------|---------------|---------|---------|
| 1 | व्यय अनुमानको विवरण (रातो किताब) २०८१-८२ | Red Book FY 2081/82 (revised/official) | 2081/82 | `https://giwmscdnone.gov.np/media/pdf_upload/व्यय...k3ip15v.pdf` |
| 2 | Redbook_2080/81 (main) | Red Book FY 2080/81 | 2080/81 | `https://giwmscdnone.gov.np/media/pdf_upload/Redbook_2080%3A81_vqjjhx7.pdf` |
| 3 | Redbook (Final) 2079/80 | Red Book FY 2079/80 | 2079/80 | `https://giwmscdnone.gov.np/media/pdf_upload/Redbook%20(Final)_2079%3A80_uryb8ga.pdf` |
| 4 | व्यय अनुमानको विवरण (रातो किताब) २०८१-८२ (volume 2) | Red Book FY 2081/82 (vol 2) | 2081/82 | `https://giwmscdnone.gov.np/media/pdf_upload/व्यय...iynjlkz.pdf` |
| 5 | 1685431543_Redbook_2080 final | Red Book FY 2080/81 (first release) | 2080/81 | `https://giwmscdnone.gov.np/media/pdf_upload/1685431543_Redbook_2080%20final_uz6gks1.pdf` |
| 6 | 1654143439_redbook (Final) | Red Book FY 2078/79 | 2078/79 | `https://giwmscdnone.gov.np/media/pdf_upload/1654143439_redbook%20(Final)_tfzwlwf.pdf` |

Site listing header shows page 1 contains: 2081-82, 2080/81, 2079/80, 2081/82, 2080/81, 2079/80. Additional older pages likely contain 2062–2079. Our disk corpus covers:
- `Budget Details - Red Book 2062-2063` ✓
- `LI 2066-67`, `LI 2067-68` ✓
- `RB 2069-70` (two copies) ✓
- `RB 2070-71` ✓
- `Red Book Central 2074-75` ✓
- `Redbook 2077` ✓
- `Redbook_2078_79_Revised` ✓
- `Redbook (Final) 2079-80` ✓
- `Redbook_2080_81` ✓
- `व्यय अनुमानको विवरण २०७१-७२`, `२०७२-७३`, `२०७३-७४`, `२०७६`, `२०७९/८०`, `२०८०/८१` ✓
- `व्यय अनुमानको विवरण (रातो किताब) २०८१-८२` ✓ (latest)
- `रातो किताव २०५९` (FY 2059/60), `रातो किताव २०६५` ✓

**Missing on disk (on site, not on disk):** Red Book FY 2082/83 — the site listing's page 1 header references this year under "व्यय अनुमानको विवरण २०८१/८२" but a 2082/83 version was announced in FY 2082/83 budget. Likely on page 1 of the site now. Check site directly when SSL is resolved.

**OCR note:** Most pre-2079 editions are Nepali-language PDFs; requires Devanagari-capable OCR. ADR-0003 does not block table extraction with pdfplumber but image-only pages (pre-2070 editions) may need flagging as `needs-ocr`.

---

### White Book / Source Book (वैदेशिक सहायता आयोजनाहरुको स्रोत पुस्तिका — Foreign Aid Source Book)

**Already-registered:** no separate registry entry (covered implicitly under `mof-dfimis`/`mof-budget-redbook` umbrella, but no dedicated `mof-whitebook` source ID exists)
**Already on disk:** yes — 14 PDFs

Files on mof.gov.np (from `documents_metadata.json`):

Page 1 listing header lists: FY 2021-22, 2020-21 (×2), 2015-16 (×2), 2071/72

| # | Title | FY (BS) | FY (AD) | File URL | On disk |
|---|-------|---------|---------|---------|---------|
| 1 | Source Book: White Book FY 2021-22 | 2078/79 | 2021/22 | `https://giwmscdnone.gov.np/.../Source%20Book%20%20White%20Book%20FY%202021-22_azz4yjf.pdf` | yes |
| 2 | Source Book White Book FY 2020-21 (A) | 2077/78 | 2020/21 | `https://giwmscdnone.gov.np/.../source_book_final_20200623051728_qypntp8.pdf` | yes |
| 3 | Source Book White Book FY 2020-21 (B) | 2077/78 | 2020/21 | `https://giwmscdnone.gov.np/.../Source%20Book%20White%20Book%20FY%202020-21_dkjqgrt.pdf` | yes |
| 4 | Source Book White Book FY 2015-16 (A) | 2072/73 | 2015/16 | `https://giwmscdnone.gov.np/.../source_book_20150714124835_jzitx4k.pdf` | yes |
| 5 | Source Book White Book FY 2015-16 (B) | 2072/73 | 2015/16 | `https://giwmscdnone.gov.np/.../Source%20Book%20White%20Book%20FY%202015-16_7jvoiky.pdf` | yes |
| 6 | आर्थिक बर्ष २०७१/७२ को स्रोत पुस्तिका | 2071/72 | 2014/15 | `https://giwmscdnone.gov.np/.../आर्थिक...8xjyyod.pdf` | yes |

Page 2 listing header lists: 2070/71, 2065/66, 2067/68, 2067/68, 2066/67, 2065/66

| # | Title | FY (BS) | On disk |
|---|-------|---------|---------|
| 7 | आर्थिक बर्ष २०७०/७१ को स्रोत पुस्तिका | 2070/71 | yes |
| 8 | Source Book White Book FY 2065/2066 | 2065/66 | yes |
| 9 | Source Book White Book FY 2067/2068 | 2067/68 | yes |
| 10 | आर्थिक बर्ष २०६७/६८ को स्रोत पुस्तिका | 2067/68 | yes |
| 11 | Source Book White Book FY 2066/2067 | 2066/67 | yes |
| 12 | आर्थिक बर्ष २०६५/६६ को स्रोत पुस्तिका | 2065/66 | yes |

Page 3 listing header lists: 2062/63, 2064/65

| # | Title | FY (BS) | On disk |
|---|-------|---------|---------|
| 13 | आर्थिक बर्ष २०६२/६३ को स्रोत पुस्तिका | 2062/63 | yes |
| 14 | आर्थिक बर्ष २०६४/६५ को स्रोत पुस्तिका | 2064/65 | yes |

**Gap:** White Book FY 2022-23, 2023-24, 2024-25 are NOT in our disk corpus and not in the metadata JSON. The series appears to have stopped at FY 2021-22 or newer issues are hosted differently. Needs verification via direct site access when SSL is resolved.

**Also gap:** FY 2063/64 (2006/07) and FY 2068/69, 2069/70, 2072/73, 2073/74 are not present on disk or in metadata.

---

### Yellow Book (सार्वजनिक संस्थानको वार्षिक स्थिति समीक्षा — Public Enterprises Annual Review)

**Already-registered:** no dedicated source ID
**Already on disk:** 6 PDFs (FY 2079–2081 plus summary editions)

Files on mof.gov.np (from `documents_metadata.json`, page 1):

Site listing header lists: 2082, 2081, 2080 (full + summary), 2079 (full + summary)

| # | Title | FY (BS) | File URL | On disk |
|---|-------|---------|---------|---------|
| 1 | सार्वजनिक संस्थानको वार्षिक स्थिति समीक्षा २०८२ | 2082 | `https://giwmscdnone.gov.np/.../Webiste%20Uploaded%20Yellow_sdwyi9v.pdf` | **NO** (newest — not on disk) |
| 2 | सार्वजनिक संस्थानको वार्षिक स्थिति समीक्षा २०८१ | 2081 | `https://giwmscdnone.gov.np/.../सार्वजनिक...ksi3tbe.pdf` | yes |
| 3 | सार्वजनिक संस्थानको वार्षिक स्थिति समिक्षा २०८०  | 2080 | `https://giwmscdnone.gov.np/.../1685280975_Yellow%20Book%20BIG%202080%20Final_6jh3p9r.pdf` | yes |
| 4 | सार्वजनिक संस्थानको वार्षिक स्थिति समिक्षा २०८० (संक्षिप्त झलक) | 2080 summary | `https://giwmscdnone.gov.np/.../सार्वजनिक...brzjuc2.pdf` | yes |
| 5 | सार्वजनिक संस्थानको वार्षिक स्थिति समीक्षा २०७९ | 2079 | `https://giwmscdnone.gov.np/.../1653757638_सार्वजनिक...ab0trdn.pdf` | yes |
| 6 | सार्वजनिक संस्थानको वार्षिक स्थिति समीक्षा २०७९ (संक्षिप्त झलक) | 2079 summary | `https://giwmscdnone.gov.np/.../सार्वजनिक...wwehtk3.pdf` | yes |

**Gap (newest not on disk):** Yellow Book 2082 — `https://giwmscdnone.gov.np/media/pdf_upload/Webiste%20Uploaded%20Yellow_sdwyi9v.pdf`

---

### Inter-Government Financial Transfer (अन्तर सरकारी वित्तीय हस्तान्तरण)

**Already-registered:** partially — `local-fiscal-transfers-cleaned` covers FY 2082/83 XLSX only. No registry entry for the PDF series.
**Already on disk:** 9 PDFs (FY 2074/75 through 2082/83)

The `documents_metadata.json` enumerates 20 entries across 4 pages. Files include:

**Annual consolidated transfer reports (cleanly titled):**

| Original filename | FY (BS) | File URL | On disk |
|---|---------|---------|---------|
| अन्तर सरकारी वित्तीय हस्तान्तरण २०८१-८२ | 2081/82 | `https://giwmscdnone.gov.np/.../1717162262_...nbaja9d.pdf` | yes (207475→208283 range) |
| अन्तर सरकारी वित्तीय हस्तान्तरण २०७९-८० | 2079/80 | `https://giwmscdnone.gov.np/.../अन्तर...evp65cw.pdf` | yes |
| अन्तर सरकारी वित्तिय हस्तान्तरण २०७८-७९ | 2078/79 | `https://giwmscdnone.gov.np/.../अन्तर...8owxxeg.pdf` | yes |
| अन्तर सरकारी वित्तिय हस्तान्तरण २०७७-७८ | 2077/78 | `https://giwmscdnone.gov.np/.../अन्तर...ewgyiwf.pdf` | yes |
| अन्तर सरकारी वित्तिय हस्तान्तरण २०७६-७७ | 2076/77 | `https://giwmscdnone.gov.np/.../अन्तर...j8gieow.pdf` | yes |
| अन्तर सरकारी वित्तीय हस्तान्तरण २०७५-७६ | 2075/76 | `https://giwmscdnone.gov.np/.../अन्तर...jnq0iuw.pdf` | yes |
| अन्तर सरकारी वित्तीय हस्तान्तरण २०७४-७५ | 2074/75 | `https://giwmscdnone.gov.np/.../अन्तर...x4tdayx.pdf` | yes |

**Province-level guidance documents (FY 2080, 7 provinces + local govts):**

| Original filename | Coverage | File URL |
|---|---------|---------|
| Koshi Pradesh margadarsan 2080 | Koshi Province | `https://giwmscdnone.gov.np/.../1690527883_Koshi...khaxayl.pdf` |
| Madhes Pradesh margadarsan 2080 | Madhes Province | `https://giwmscdnone.gov.np/.../1690527948_Madhes...f5jpcvu.pdf` |
| Bagmati Pradesh margadarsan 2080 | Bagmati Province | `https://giwmscdnone.gov.np/.../1690528005_Bagmati...ucyihvr.pdf` |
| Gandaki margadarsan 2080/81 | Gandaki Province | `https://giwmscdnone.gov.np/.../आ.व._2080-81_Gandaki...fqdmj8l.pdf` |
| Lumbini margadarsan 2080/81 | Lumbini Province | `https://giwmscdnone.gov.np/.../आ.व._2080-81_Lumbini...ple2afi.pdf` |
| Karnali margadarsan 2080/81 | Karnali Province | `https://giwmscdnone.gov.np/.../आ.व._2080-81_Karnali...ghcg27d.pdf` |
| Sudurpaschim Pradesh margadarsan 2080 | Sudurpaschim Province | `https://giwmscdnone.gov.np/.../Sudurpaschim...a5cemku.pdf` |
| 753 Local Governments margadarsan 2080 | All local govts | `https://giwmscdnone.gov.np/.../1690364851_753...vr8b4v1.pdf` |

**Policy/legal documents also in this section:**
- Fiscal Transfer 2080 (general) — `1685431681_Fiscal%20Transfer%202080_wo3vvdq.pdf`
- Province Guidelines Budget — `1660456603_Province_Guidlines_Budget_qi4exrc.pdf`
- Nepal Sarkar Aay Byay 2077-78 — Nepal Government Revenue/Expenditure 2077/78
- Province consolidated fund operating procedures 2074 — `प्रदेश सञ्चितकोष...o1szf9j.pdf`
- Province tax policy — `प्रदेशको कर तथा गैरकर सम्बन्धी_n4muhxv.pdf`
- Revenue/expenditure estimates circular — `राजस्व र व्ययको...pqwbd92.pdf`

**Gap (newest not on disk):** The site header for intergovernmental page 1 mentions FY 2082/83 transfer document (वित्तीय हस्तान्तरण २०८२/०८३). On disk our latest is 208283.pdf but that filename suggests it covers 2082/83 already. Verify labeling.

---

### Aid Agreements (सम्झौता)

**Already-registered:** no dedicated source ID (covered as reference under `mof-dfimis`)
**Already on disk:** 6 PDFs

Files from `documents_metadata.json`:

Site listing header lists: FY 2081/82, 2080/81, 2079/80, 2078/79, 2077/078, Commitment Against Post Disaster Reconstruction

| # | Title | FY (BS) | File URL | On disk |
|---|-------|---------|---------|---------|
| 1 | Agreement FY 2081/82 (2024/25) | 2081/82 | `https://giwmscdnone.gov.np/.../Agreement_FY2526_8283_ewzykwa.pdf` | yes |
| 2 | Agreement FY 2080/81 (2023/24) | 2080/81 | `https://giwmscdnone.gov.np/.../Agreement_FY2324_8081_tk2vpt2.pdf` | yes |
| 3 | Commitment UP TO Aashar 2080 | 2079/80 | `https://giwmscdnone.gov.np/.../1689830981_Commitment...cn3p3t5.pdf` | yes |
| 4 | Progress Report Upto Asar-2 | 2079 | `https://giwmscdnone.gov.np/.../1658043201_Progress...cpok5mz.pdf` | yes |
| 5 | Progress Report 2077.078 | 2077/78 | `https://giwmscdnone.gov.np/.../1658642431_Progress...zaif6ul.pdf` | yes |
| 6 | Commitment Against Post Disaster Reconstruction | 2074 | `https://giwmscdnone.gov.np/.../earthquake...5u8dzgh.pdf` | yes |

**Gap:** Agreement FY 2082/83 (2025/26) will be published after the current FY ends (Ashadh 2083). Not yet on site at time of crawl.

---

### Economic Survey (आर्थिक सर्वेक्षण) — NOT IN METADATA.JSON

**Already-registered:** NO
**Already on disk:** NO

The `documents_metadata.json` does not include this category — it was not scraped in the prior run. Economic Survey is MoF's flagship annual macro publication, typically ~250 pages, released in Jestha/Ashadh with the budget. Historical coverage on mof.gov.np extends back to at least FY 2065/66 based on prior crawls by other researchers. Direct access to `https://mof.gov.np/en/publication/economic-survey-314` blocked (SSL error). Confirmed as an active annual series — FY 2081/82 edition would have been released in Jestha/Ashadh 2081 (May–June 2024).

**Estimated file inventory (not confirmed from direct crawl):**
- Latest available: Economic Survey FY 2081/82 (PDF, Nepali + English volumes)
- Historical: FY 2065/66 onward (~17 annual editions)
- Format: PDF, bilingual (Nepali statistical tables + English narrative summary in recent years)

**Action:** Register as `mof-economic-survey` before writing any parser.

---

### Budget Speech (बजेट वक्तव्य) — NOT IN METADATA.JSON

**Already-registered:** NO
**Already on disk:** NO

Not scraped in prior run. Budget Speech is the annual Finance Minister address delivered on Jestha 15 (first day of budget session). Contains headline revenue/expenditure targets, policy priorities, and sector-by-sector allocations. Available in Nepali and English. Coverage estimated FY 2060s onward on mof.gov.np. FY 2082/83 speech expected Jestha 15, 2082 (May 2025).

**Action:** Register as `mof-budget-speech` before writing any parser.

---

### Mid-Term Expenditure Review (मध्यावधि खर्च समीक्षा) — NOT IN METADATA.JSON

**Already-registered:** NO (referenced in `mof-budget-redbook` notes but no dedicated source)
**Already on disk:** NO

Published mid-fiscal-year (typically Poush/Magh) reviewing the first half of budget execution. A separate PDF from the Red Book. Not in the scraped metadata. Requires verification on site.

---

### Quarterly/Monthly Progress Reports (त्रैमासिक/मासिक प्रगति विवरण) — NOT IN METADATA.JSON

**Already-registered:** NO
**Already on disk:** NO

MoF publishes quarterly progress reports on capital expenditure against budget. These are distinct from FCGO daily fiscal data. Not in the scraped metadata. Requires verification.

---

## Division Publications — FCGO (Financial Comptroller General Office)

FCGO has its own website at `https://fcgo.gov.np/` — accessible directly (valid SSL). FCGO is under MoF's umbrella. Already registered as `fcgo-daily` (daily revenue/expenditure data) but the following publication streams are NOT registered:

### FCGO: Central Account Consolidated Financial Statements (केन्द्रीय लेखाको एकिकृत वित्तीय विवरण)

Enumerated from `https://fcgo.gov.np/category/cof-central-account/` (page 1 of 2):

| # | Title | FY (BS) | File URL |
|---|-------|---------|---------|
| 1 | आर्थिक वर्ष २०८०/८१ (भाग १) | 2080/81 | `https://giwmscdnone.gov.np/media/pdf_upload/fy-2080-81-01_kbdjr2r.pdf` |
| 2 | आर्थिक वर्ष २०७८/७९ (भाग १) | 2078/79 | `https://giwmscdnone.gov.np/media/pdf_upload/fy-2078-79-01_1buquf7.pdf` |
| 3 | आर्थिक वर्ष २०७७/७८ (भाग १) | 2077/78 | `https://giwmscdnone.gov.np/media/pdf_upload/fy-2077-78-01_be2ocbk.pdf` |
| 4 | आर्थिक वर्ष २०७६/७७ (भाग १) | 2076/77 | `https://giwmscdnone.gov.np/media/pdf_upload/fy-2076-77-01_7v0bxxz.pdf` |
| 5 | आर्थिक वर्ष २०७५/७६ (भाग १) | 2075/76 | `https://giwmscdnone.gov.np/media/pdf_upload/fy-2075-76-01_ybggsks.pdf` |
| 6 | आर्थिक वर्ष २०७४/७५ (भाग १) | 2074/75 | `https://giwmscdnone.gov.np/media/pdf_upload/fy-2074-75-01_cuw6sxt.pdf` |

Page 2 likely contains FY 2073/74 and earlier. Not on disk.

### FCGO: Consolidated Financial Statements — All Tiers (एकिकृत वित्तीय विवरण)

Enumerated from `https://fcgo.gov.np/category/con-fin-statements/`:

| # | Title | Period | File URL |
|---|-------|--------|---------|
| 1 | Integrated Financial Statement FY 2081/82 | 2081/82 | `https://giwmscdnone.gov.np/media/pdf_upload/2081.82_tqnktsw_kjmqech.pdf` |
| 2 | Integrated Financial Statement FY 2080/81 | 2080/81 | `https://giwmscdnone.gov.np/media/pdf_upload/ab-2080-81_bynkkcj.pdf` |
| 3 | Integrated Financial Statement FY 2079/80 | 2079/80 | `https://giwmscdnone.gov.np/media/pdf_upload/ab-2079-80_t7qdsfb.pdf` |
| 4 | Annual Income and Expenditure FY 2078/79 | 2078/79 | `https://giwmscdnone.gov.np/media/pdf_upload/ab-2078-79_dzkmiv5.pdf` |
| 5 | Annual Income and Expenditure FY 2077/78 | 2077/78 | `https://giwmscdnone.gov.np/media/pdf_upload/ab-2077-78_7ntldvt.pdf` |
| 6 | FY 2076/77 (Part 1) | 2076/77 | `https://giwmscdnone.gov.np/media/pdf_upload/ab-2076-77_jyukufi.pdf` |

### FCGO: Consolidated Financial Statements — English Version

Enumerated from `https://fcgo.gov.np/category/consolidated-us`:

| # | Title | AD Period | File URL |
|---|-------|----------|---------|
| 1 | CFS 2023-2024 | 2023/24 | `https://giwmscdnone.gov.np/media/pdf_upload/20250629144539_CFS%202023-2024_fmeywfy.pdf` |
| 2 | CFS 2022-2023 | 2022/23 | `https://giwmscdnone.gov.np/media/pdf_upload/20240725124752_cfs2022-2023_q53t9je.pdf` |
| 3 | CFS 2021-2022 | 2021/22 | `https://giwmscdnone.gov.np/media/pdf_upload/20250127145608_CFS%202021-2022_qetdf7b.pdf` |
| 4 | CFS 2020-2021 | 2020/21 | `https://giwmscdnone.gov.np/media/pdf_upload/20250127145826_2020-2021_xtybcb6.pdf` |
| 5 | CFS 2019-2020 | 2019/20 | `https://giwmscdnone.gov.np/media/pdf_upload/20210517185110_CFS_2019_2020%20final_mktdwf5.pdf` |
| 6 | CFS 2018-2019 | 2018/19 | `https://giwmscdnone.gov.np/media/pdf_upload/Book-final-2018-2019_ofqaoxz.pdf` |

### FCGO: Debt Reports (आन्तरिक तथा बैदेशिक ऋण — Internal and External Debt)

Enumerated from `https://fcgo.gov.np/category/report-on-internal-and-external-debt/`:

| # | Title | Period | File URL |
|---|-------|--------|---------|
| 1 | Second Quarterly Report 2076.09.29 | Q2 FY 2076 | `https://giwmscdnone.gov.np/media/pdf_upload/20210122212204-02_w4u1ny4.pdf` |
| 2 | First Quarterly Report 2076.06.30 | Q1 FY 2076 | `https://giwmscdnone.gov.np/media/pdf_upload/20210122212041-01_vf3cg7x.pdf` |

Only 2 entries visible — possibly incomplete series.

### FCGO: Bulletins

Enumerated from `https://fcgo.gov.np/category/bulletin`:

| # | Title | Period | Notes |
|---|-------|--------|-------|
| 1 | Bulletin 2078 Magh (mid-Feb 2022) | Magh 2078 | PDF |
| 2 | Bulletin 2078 Ashadh (mid-July 2021) | Ashadh 2078 | PDF |

Sparse — only 2 editions visible.

---

## Division Publications — PDMO (Public Debt Management Office)

PDMO is accessible at `https://pdmo.gov.np/` (valid SSL). Not yet registered in our source registry. All entries below are newly discovered.

### PDMO: Monthly Government Debt Statistics (मासिक सरकारी ऋण तथ्याङ्क)

Enumerated from `https://pdmo.gov.np/pages/monthlyrepo`:

| Month (BS) | AD equiv | File URL |
|-----------|---------|---------|
| Chaitra 2082 | Apr 2026 | `https://giwmscdnone.gov.np/media/files/2082%20chaitra_grgy9jv.pdf` |
| Falgun 2082 | Mar 2026 | `https://giwmscdnone.gov.np/media/files/Falgun%20(1)_njxxw9p.pdf` |
| Magh 2082 | Feb 2026 | `https://giwmscdnone.gov.np/media/files/GDS%20Report%202082%20Magh_bbtqw9r.pdf` |
| Poush 2082 | Jan 2026 | `https://giwmscdnone.gov.np/media/files/2082%20Poush_3uujb9p.pdf` |
| Mangsir 2082 | Dec 2025 | `https://giwmscdnone.gov.np/media/files/2082%20Mansir_ockvqyj.pdf` |
| Kartik 2082 | Nov 2025 | `https://giwmscdnone.gov.np/media/files/2082%20Kartik_mc7fluf.pdf` |
| Asoj 2082 | Oct 2025 | `https://giwmscdnone.gov.np/media/files/2082%20Ashoj_pfv1acp.pdf` |

Site notes additional editions from 2081 and 2082 in prior months. Series extends back to at least FY 2081. **Latest: Chaitra 2082 (Apr 2026).**

### PDMO: Annual Report on Public Debt and Share Investment (वार्षिक प्रतिवेदन)

| # | Title | FY (BS) | File URL |
|---|-------|---------|---------|
| 1 | Annual Report FY 2081/82 | 2081/82 | `https://giwmscdnone.gov.np/media/files/वार्षिक...ionznkw_jhywksw.pdf` |
| 2 | Annual Report FY 2080/81 | 2080/81 | (URL not resolved — see `/content/103/`) |

### PDMO: Medium-Term Debt Management Strategy (MTDS)

| # | Coverage period | File URL |
|---|----------------|---------|
| 1 | FY 2082/83–2084/85 | `https://giwmscdnone.gov.np/media/files/Approved%20MTDS%20-2082_zlcqw8w.pdf` |
| 2 | FY 2081/82–2083/84 | `https://giwmscdnone.gov.np/media/files/MTEF%20Data_MTDS%20Report_Final-1%202024_sgwmrih.pdf` |
| 3 | FY 2080/81–2082/83 | `https://giwmscdnone.gov.np/media/files/MTDS-Nepali-Translation-Rev-2081-1-11-1715498682.pdf` |
| 4 | FY 2078/79–2080/81 | `https://giwmscdnone.gov.np/media/files/PDMO_मधयम-कलन-ऋण_1670569610-1680510246.pdf` |

### PDMO: T-Bill and Bond Series Data

Active operational data (not publication-grade economic statistics — lower priority for ingestion):
- T-Bill auction results (latest: up to 2083-02-05) — Excel/CSV
- Development Bond time-series (up to 2082-12-26) — `https://giwmscdnone.gov.np/media/files/DB%20Summary...`
- Bond Holdings by BFIs — monthly
- Citizen Savings Bond (CSB) and Foreign Employment Savings Bond (FESB) series

---

## Division Publications — IRD (Inland Revenue Department)

Site: `https://www.ird.gov.np/` — accessible. Not under MoF directly (separate department under MoF umbrella).

Publications found:
- Annual reports, financial statements, RTI documents under `प्रकाशन` section
- Tax law compendiums (acts, rules, directives)

**Not yet registered.** Low priority for core macro tracking but relevant for Revenue Pillar. Recommend separate `ird-annual-report` source if/when revenue dashboard is built.

---

## Cross-reference: on-disk vs. on-site

### Files on mof.gov.np NEWER than anything on disk (need to pull)

| Category | Title | FY (BS) | URL |
|---------|-------|---------|-----|
| Yellow Book | सार्वजनिक संस्थानको वार्षिक स्थिति समीक्षा २०८२ | 2082 | `https://giwmscdnone.gov.np/media/pdf_upload/Webiste%20Uploaded%20Yellow_sdwyi9v.pdf` |
| Red Book (if 2082/83 exists) | व्यय अनुमानको विवरण २०८२/८३ | 2082/83 | Verify on site when SSL fixed |
| White Book | FY 2022-23, 2023-24, 2024-25 editions (if published) | 2079+/2080+/2081+ | Verify on site |
| Intergovernmental | FY 2082/83 consolidated transfer report | 2082/83 | Verify on site |

### Files in Financial Data/mof_documents/ that are STILL on mof.gov.np

All 6 agreement PDFs, all 6 whitebook metadata entries (pages 1–3), all 6 redbook metadata entries (pages 1–3), all 6 yellowbook metadata entries, and all 9 on-disk intergovernmental PDFs match URLs still active on giwmscdnone.gov.np. Count: ~27 file-on-site matches confirmed.

### Files on disk that no longer appear on mof.gov.np

No confirmed removals — all on-disk files have matching CDN URLs in `documents_metadata.json`. However, very old redbook editions (pre-2062) present on disk as `रातो किताव २०५९` (FY 2059/60) are not in the metadata JSON page 1 listing. These may be on deeper pages of the site or may have been delisted. Treat as **potentially archived discontinuities** — preserve on disk regardless.

---

## Gap analysis — newly-discovered sources (draft registry profiles)

### 1. mof-economic-survey

```markdown
# Source: Ministry of Finance — Economic Survey (आर्थिक सर्वेक्षण)

**source_id:** `mof-economic-survey`
**Status:** paused (pending registration)
**Tier:** Tier 2 (high strategic value — main macroeconomic narrative)

## Publication
- URL: https://mof.gov.np/en/publication/economic-survey-314 (SSL fix required)
- Frequency: annual
- Format: pdf (bilingual: Nepali tables + English narrative from ~FY 2074/75 onward)
- Reporting period type: annual
- Requires table extraction: yes (statistical annex has 100+ tables)

## What we extract
- gdp-growth-rate — Real GDP growth by sector
- inflation-rate-annual — Annual CPI headline
- fiscal-revenue-actual — Actual revenue vs. budget
- fiscal-expenditure-actual — Total expenditure vs. budget
- trade-balance — Exports, imports, trade deficit
- remittance-inflows — Annual remittance as % of GDP
- foreign-exchange-reserves — End-of-year FX reserve months of import cover
- credit-to-private-sector — Banking credit growth

## Provenance
- Confidence default: A
- License: gov_open
- Ingestion mode: manual_upload (annual)
- Historical coverage: FY 2065/66 onward (estimated ~17 editions)

## Known breakage modes
- URL structure changes each fiscal year (search-pattern fallback needed)
- PDF column layout shifts at major revision years
- Nepali numeral encoding in older editions (pre-2075)

## Revision policy
TBD — fill in on parser PR. Annual; no mid-year revisions expected.
```

### 2. mof-budget-speech

```markdown
# Source: Ministry of Finance — Budget Speech (बजेट वक्तव्य)

**source_id:** `mof-budget-speech`
**Status:** paused (pending registration)
**Tier:** Tier 2

## Publication
- URL: https://mof.gov.np/en/publication/budget-speech-315 (SSL fix required)
- Frequency: annual (Jestha 15 each year)
- Format: pdf (Nepali; English translation published ~1 week later)
- Reporting period type: annual
- Requires table extraction: yes (headline fiscal tables in appendix)

## What we extract
- budget-revenue-target — Annual revenue target (NPR bn)
- budget-expenditure-target — Total expenditure plan
- budget-capital-target — Capital expenditure allocation
- budget-deficit — Financing gap and sources

## Provenance
- Confidence default: A
- License: gov_open
- Ingestion mode: manual_upload (annual)
- Historical coverage: FY 2060 onward (estimated 23+ editions)
```

### 3. fcgo-consolidated-financial-statements

```markdown
# Source: FCGO — Consolidated Financial Statements (Nepali + English)

**source_id:** `fcgo-consolidated-financial-statements`
**Status:** paused (pending registration)
**Tier:** Tier 1 (high value — audited all-of-government outturn data)

## Publication
- URL (Nepali): https://fcgo.gov.np/category/con-fin-statements/
- URL (English): https://fcgo.gov.np/category/consolidated-us
- Frequency: annual (published Chaitra of following FY)
- Format: pdf
- Reporting period type: annual
- Requires table extraction: yes

## What we extract
- total-revenue-outturn — Final actual revenue
- total-expenditure-outturn — Final actual expenditure
- capital-expenditure-outturn — Capital spending actual
- provincial-expenditure-consolidated — Sum across 7 provinces
- local-level-expenditure-consolidated — Sum across 753 local govts

## Provenance
- Confidence default: A (audited outturn — highest confidence)
- License: gov_open
- Ingestion mode: manual_upload (annual)
- Historical coverage: FY 2074/75 onward (Nepali); FY 2018/19 onward (English)
```

### 4. pdmo-monthly-debt-statistics

```markdown
# Source: PDMO — Monthly Government Debt Statistics (मासिक सरकारी ऋण तथ्याङ्क)

**source_id:** `pdmo-monthly-debt-statistics`
**Status:** paused (pending registration)
**Tier:** Tier 2

## Publication
- URL: https://pdmo.gov.np/pages/monthlyrepo
- Frequency: monthly
- Expected window: ~15th of following month
- Format: pdf
- Reporting period type: monthly
- Requires table extraction: yes

## What we extract
- internal-debt-outstanding — Domestic debt stock (T-bills + bonds + savings certs)
- external-debt-outstanding — Foreign debt stock
- debt-to-gdp-ratio — If published in report

## Provenance
- Confidence default: A
- License: gov_open
- Ingestion mode: automated_cron (monthly)
- Historical coverage: At least FY 2081/82 onward; likely earlier on site

## Known breakage modes
- Filename pattern varies (includes BS month name in Nepali or English inconsistently)
```

### 5. pdmo-annual-debt-report

```markdown
# Source: PDMO — Annual Report on Public Debt and Share Investment

**source_id:** `pdmo-annual-debt-report`
**Status:** paused (pending registration)
**Tier:** Tier 3

## Publication
- URL: https://pdmo.gov.np/ (content pages vary by year)
- Frequency: annual
- Format: pdf (Nepali)
- Reporting period type: annual

## Provenance
- Confidence default: A
- License: gov_open
- Ingestion mode: manual_upload
- Historical coverage: FY 2080/81 and 2081/82 confirmed; earlier editions TBD
```

### 6. pdmo-mtds

```markdown
# Source: PDMO — Medium-Term Debt Management Strategy

**source_id:** `pdmo-mtds`
**Status:** paused (pending registration)
**Tier:** Tier 4 (reference-only; strategy doc, not statistical series)

## Publication
- URL: https://pdmo.gov.np/pages/debtsteategy
- Frequency: annual (updated each FY)
- Format: pdf (Nepali + English bilingual)
- Reporting period type: annual (3-year forward window)

## Provenance
- Confidence default: A
- License: gov_open
- Ingestion mode: reference_only (not a time-series feed)
- Historical coverage: FY 2078/79–2080/81 through 2082/83–2084/85 (4 editions confirmed)
```

---

## Crawl notes & blockers

1. **SSL blocker on mof.gov.np**: Every direct fetch of `https://mof.gov.np/*` returned `unable to verify the first certificate`. This affects ALL pages on the domain including Economic Survey, Budget Speech, Mid-Term Review, and any Nepali-language publication pages not previously scraped. Resolution: the prior scraping run used a Python script with `verify=False` or a system trust store that accepted the MoF cert. Future scraping should use `requests.get(url, verify=False)` with a logged warning, or configure the cert chain locally.

2. **documents_metadata.json coverage is partial**: The existing metadata captures only 5 of the ~12+ publication categories on mof.gov.np. Missing: Economic Survey, Budget Speech, Mid-Term Review, Quarterly Progress Reports, and any Division Publications hosted directly on mof.gov.np (as opposed to their own domains).

3. **CDN host**: All actual PDF files are served from `giwmscdnone.gov.np` (the Government Integrated Web Management System CDN), not from mof.gov.np directly. This domain returns 403 when accessed directly. PDF URLs embedded in the JSON are direct CDN links that DO work without authentication (they have opaque filename tokens as access control).

4. **Wayback Machine blocked**: `web.archive.org` is not reachable from the Claude Code fetch sandbox. Cannot use as SSL-bypass fallback.

5. **FCGO and PDMO are accessible**: Both `fcgo.gov.np` and `pdmo.gov.np` have valid SSL. These can be scraped directly.

6. **FCGO debt reports incomplete**: Only 2 quarterly debt reports visible in the FCGO category. The full historical series may exist under a different URL pattern or may have been migrated to PDMO.

7. **Yellow Book 2082**: Listed at the top of the site's Yellow Book page (Jestha 15, 2082 publication date per metadata header). URL: `https://giwmscdnone.gov.np/media/pdf_upload/Webiste%20Uploaded%20Yellow_sdwyi9v.pdf`. This is the highest-priority single file to add to the on-disk corpus — it was uploaded after our last disk sync.

8. **intergovernmental province-level docs**: The province margadarsan (guidance) documents in the intergovernmental section are NOT in our on-disk `intergovernmental/` folder (the 9 files there are the annual aggregate transfer PDFs). These 8 province-level documents are additional granular data.

9. **mof.gov.np page structure note**: Publication section IDs found in URLs: economic-survey-314, budget-speech-315, red-book-316 — numeric IDs suggest a CMS-based listing. The `mof-budget-redbook` source profile already notes URL changes each fiscal year as a known breakage mode.
