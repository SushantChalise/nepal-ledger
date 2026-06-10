# Mother verification — अनुसूची १३.१ (Economic Survey 2081-82, p475)

**Source:** `Financial Data/mof_documents/economic_survey/Economic_Survey_2081-82.pdf` page index 475 (0-based).
**Table:** प्रदेशगत कुल मूल्य अभिवृद्धि (औद्योगिक वर्गीकरण अनुसार) — Provincial GVA by industrial classification.
**Unit:** रू. करोडमा (NPR crore), प्रचलित मूल्य (current prices). **Method:** surya-ocr (Tier-2), Mother render-verified.
**Verification tool:** pymupdf `get_pixmap(Matrix(7–18), clip=…)` high-zoom crops of the नेपाल column, read visually (AI-as-QA agree/disagree; no digit invented).

## Scope of this verification

Only the **नेपाल (national) column** was render-verified cell-by-cell (the highest-value, least-degraded column). The 7 province columns remain OCR-degraded and are **QUARANTINED** (see below).

## Verified national GVA-by-sector (render-confirmed digits)

| idx | sector (ne)                                  |    2080/81 |    2081/82 |
| --: | -------------------------------------------- | ---------: | ---------: |
|   0 | कृषि, वन र मत्स्यपालन                        |     124869 |     135373 |
|   1 | खानी तथा उत्खनन्                             |       2402 |       2478 |
|   2 | उत्पादनमूलक उद्योग                           |      24925 |      26780 |
|   3 | विद्युत, ग्यास, वाष्प                        |       9143 |       9324 |
|   4 | पानी आपूर्ति, ढल                             |       2205 |       2279 |
|   5 | निर्माण                                      |      27272 |      28164 |
|   6 | थोक तथा खुद्रा व्यापार                       |      70752 |      78296 |
|   7 | यातायात तथा भण्डारण                          |      34287 |      38758 |
|   8 | आवास तथा भोजन सेवा                           |      12142 |      13255 |
|   9 | सुचना तथा सञ्चार                             |       9783 |      10425 |
|  10 | वित्तीय तथा बीमा                             |      33903 |      35766 |
|  11 | घरजग्गा कारोवार                              |      42438 |      44610 |
|  12 | पेशागत/प्राविधिक                             |       4998 |       5208 |
|  13 | प्रशासनिक/सहयोगी                             |       3604 |       3877 |
|  14 | सार्वजनिक प्रशासन, रक्षा                     |      48110 |      46916 |
|  15 | शिक्षा                                       |      43164 |      42351 |
|  16 | मानव स्वास्थ्य                               |       9488 |      10264 |
|  17 | अन्य सेवा                                    |       3379 |       3836 |
|   — | **Σ(0–17)**                                  | **506864** | **537960** |
|  18 | कुल मूल्य अभिवृद्धि (आधारभूत मूल्य, printed) |     506065 |     537959 |
|  19 | उत्पादित वस्तुमा खुद कर                      |      65569 |      72763 |
|  20 | कुल गार्हस्थ्य उत्पादन (printed)             |     571634 |     610722 |

## Corrections applied to the worker's raw OCR (national column)

- **2080/81:** idx1 `2803`→**2402**; idx13 `3608`→**3604**; idx16 `9855`→**9488**. (Worker flagged idx6=70752 & idx10=33903 suspect; render confirms they were already correct.)
- **2081/82:** idx8 `93244`→**13255**; idx12 `4208`→**5208**; idx13 `3500`→**3877**; idx16 `90788`→**10264**. (The spurious leading `9` on आवास/स्वास्थ्य was the entire +159,137 Gate-1 break.)

## Reconciliation verdict (national column)

- **2081/82 — RECONCILES.** Σ(18 sectors)=537,960 vs printed GVA 537,959 (**±1, rounding**). GVA+tax=GDP exactly (537,959+72,763=610,722). GDP **= DNE `dne-gdp-nominal` 2081/82 (610,722 crore / 6107.221 bn) to the rupee.** → **shippable, confidence B.**
- **2080/81 — SOURCE-INTERNAL DISCREPANCY.** All 18 sector cells + the three aggregate cells are render-verified correct-as-printed, yet Σ(sectors)=506,864 vs printed GVA-basic 506,065 = **+799 (0.158%)**. The printed total line is itself self-consistent (GVA+tax=GDP: 506,065+65,569=571,634). ES GDP 571,634 vs DNE 570,910 = +724 (0.127%, a revision difference). → The +799 is **in the printed source**, not OCR. Disposition pending (ship with logged discrepancy at confidence C, or quarantine the year).

## Provincial columns (कोशी…सुदूरपश्चिम) FY2081/82 — RECOVERED + RECONCILED

Initial pure-OCR had ~27% province-cell damage (`X03X`, `ሂሂ३`, `प्र२६९`). Resolved by a dedicated
Mother render-verification pass: rendered each province as a `Matrix(8)` full-column strip and read
every FY2081/82 cell from the printed page. The full **8-column × 18-sector matrix now reconciles on
the dual lattice** (`build_matrix.py` → `verified_matrix_2081_82.json`):

- **Per province** Σ(18 sectors) = printed GVA-basic, residual **0…+3 crore**; GVA+tax = GDP, **±1**.
- **Per sector** Σ(7 provinces) = verified national, residual **−1…+2 crore**.
- **Worst residual = 3 crore** (rounding; tolerance ~±9 for 18 crore-rounded values).
- **Cross-source:** Σ(7 provinces) GDP = national GDP = **610,722** = `dne-gdp-nominal` FY2081/82 **exact**.

Every cell render-confirmed; nothing computed-and-left-unread. **FY2081/82 is promotable in full**
(national `industry` + provincial `province-industry`, ADR-0023).

## FY2080/81 — EXCLUDED (source defect)

National Σ(sectors)=506,864 vs printed GVA 506,065 = **+799**, all cells render-verified
correct-as-printed → a printed-source inconsistency that cannot be reconciled clean. Not promoted;
documented gap. (Provinces for 2080/81 not processed — the year is excluded regardless.)

## Bottom line

The OCR AI pass recovered a **complete, render-verified, dual-reconciled, cross-source-validated
FY2081/82 GVA-by-sector matrix** — national + all 7 provinces × 18 industries, printed-total-clean
to ±3 crore rounding. This is the "absolutely clean, nothing unverified/unreconciled/missing"
deliverable. FY2080/81 + constant-price + the 2080-81 edition remain documented follow-ups.
