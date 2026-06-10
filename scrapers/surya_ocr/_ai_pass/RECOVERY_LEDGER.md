# Master Recovery Ledger — Overnight AI-pass worklist

> Generated: `2026-06-10T19:06:46+00:00` · Generator: `scrapers/surya_ocr/_ai_pass/locate_tables.py`  
> Plan: `docs/OVERNIGHT_AI_PASS_PLAN.md` · Dedup baseline: docs/DATA_AUDIT.md (2026-06-08 + 2026-06-10 GVA) + \_ai_pass artifacts  
> Status flow: `pending -> scoped -> {recovered|quarantined|needs-decision} -> staged -> [promoted-by-human]`

**This file is generated** — do not hand-edit. The nightly loop updates `RECOVERY_LEDGER.json`; re-render with `render_ledger.py`.

## OCR state

- Corpus OCR: **11,443 / 13,297 pages** — ⏳ **IN PROGRESS** (re-run the locator after it finishes to pick up new pages)
- Pending OCR (0 pages yet, no candidates until done): `P4__-__2qteqov_0b52daa4`, `P4__-__6d7mimy_6227f9c7`, `P5__207576_ce72ae7e`
- Partial OCR (scanned so far): `P4__Red_Book_Central_2074-75_20170530083940_00lqgwe_830109ba`

## Summary

- Documents: **50** · Table candidates: **1350** (**1342** pending)
- By dedup class:
  - `partly-in-db`: 828
  - `new`: 491
  - `owned-deterministic`: 22
  - `unknown`: 6
  - `needs-decision`: 3

Dedup classes: `new` = not in DB → recover · `partly-in-db` = some FYs/measures present, cross-check before promote · `owned-deterministic` = a deterministic parser owns this domain (OCR is cross-check only) · `needs-decision` = structural blocker · `unknown` = triage.

## ⚠️ Structural-decision queue (do NOT auto-decide — escalate)

- **`P0__207778_33e35121`** (P0, 207778.pdf) — OCR complete 42/42, 3 candidate(s).  
  Intergovernmental fiscal transfers. The 5 recent FYs are in the DB; the corpus copies here are the _blocked_ early FYs. Gate: Σ(753 local levels) == printed स्थानीय तह total. Likely 4-aggregate-grant schema block (DATA*AUDIT §6) -> structural decision, do not force into 8 atomic types.  
  \_Recommendation:* recover + stage the matrix (reconcile to the printed total) but **queue the structural decision for the human**; never fabricate to fit the current schema.
- **`P5__207576_ce72ae7e`** (P5, 207576.pdf) — OCR pending 0/41, 0 candidate(s).  
  Intergovernmental fiscal transfers. The 5 recent FYs are in the DB; the corpus copies here are the _blocked_ early FYs. Gate: Σ(753 local levels) == printed स्थानीय तह total. Likely 4-aggregate-grant schema block (DATA*AUDIT §6) -> structural decision, do not force into 8 atomic types.  
  \_Recommendation:* recover + stage the matrix (reconcile to the printed total) but **queue the structural decision for the human**; never fabricate to fit the current schema.

## Already recovered (audit trail — excluded from the worklist)

| id                  | status       | doc                                    | page(s) | artifact                    |
| ------------------- | ------------ | -------------------------------------- | ------- | --------------------------- |
| `P0_1d6841fe_p0079` | **staged**   | `P0__ksi3tbe_1d6841fe`                 | 79–82   | `_ai_pass/soe_2081_p79_pl`  |
| `P2_309ffe7c_p0475` | **promoted** | `P2__Economic_Survey_2081-82_309ffe7c` | 475     | `_ai_pass/es2081_annex13_1` |

## Documents (completeness backbone — every OCR'd doc)

| Tier | Document                                                        | OCR      |   Pages | Tbl-pg | Cand | Dedup               | Owner / note                                                           |
| ---- | --------------------------------------------------------------- | -------- | ------: | -----: | ---: | ------------------- | ---------------------------------------------------------------------- |
| P0   | `P0__ksi3tbe_1d6841fe`                                          | complete | 402/402 |    252 |  104 | new                 | dne_facts soe-\* (only equity+loan, 1 FY 2080/81)                      |
| P0   | `P0__207778_33e35121`                                           | complete |   42/42 |     34 |    3 | needs-decision      | local_government_fiscal_transfers (5 FYs: 2078/79-2082/83)             |
| P0   | `P0__1658043201_Progress_Report-Upto_Asar-2_cpok5mz_9d37560e`   | complete |     1/1 |      1 |    1 | unknown             | —                                                                      |
| P0   | `P0__1658642431_Progress_Report_2077.078_zaif6ul_83e591af`      | complete |     1/1 |      1 |    1 | unknown             | —                                                                      |
| P0   | `P0__1689830981_Commitment_UP_TO_Aashar_2080_cn3p3t5_2c129948`  | complete |     1/1 |      1 |    1 | unknown             | —                                                                      |
| P0   | `P0__Agreement_FY2324_8081_tk2vpt2_75b512b7`                    | complete |     1/1 |      1 |    1 | unknown             | —                                                                      |
| P0   | `P0__Agreement_FY2526_8283_ewzykwa_93adab98`                    | complete |     1/1 |      1 |    1 | unknown             | —                                                                      |
| P0   | `P0__earthquake__20170428064449_20170502064348_5u8dzg_683d7007` | complete |     1/1 |      1 |    1 | unknown             | —                                                                      |
| P1   | `P1__1653757638___ab0trdn_81c127cf`                             | complete | 425/425 |    232 |  103 | new                 | dne_facts soe-\* (only equity+loan, 1 FY 2080/81)                      |
| P1   | `P1__1685280975_Yellow_Book_BIG_2080_Final_6jh3p9r_9c4afda0`    | complete | 404/404 |    245 |  107 | new                 | dne_facts soe-\* (only equity+loan, 1 FY 2080/81)                      |
| P1   | `P1__Webiste_Uploaded_Yellow_sdwyi9v_a3023ba4`                  | complete | 210/210 |    125 |   75 | new                 | dne_facts soe-\* (only equity+loan, 1 FY 2080/81)                      |
| P1   | `P1__wwehtk3_de6adeac`                                          | complete | 111/111 |     70 |   52 | new                 | dne_facts soe-\* (only equity+loan, 1 FY 2080/81)                      |
| P1   | `P1__brzjuc2_cc19bfc2`                                          | complete |   97/97 |     64 |   50 | new                 | dne_facts soe-\* (only equity+loan, 1 FY 2080/81)                      |
| P2   | `P2__Economic_Survey_2080-81_NP_a8c6ee07`                       | complete | 547/547 |    467 |  344 | partly-in-db        | dne_facts economic-survey-gva-current (FY2081/82 annex 13.1, promoted) |
| P2   | `P2__Economic_Survey_2081-82_309ffe7c`                          | complete | 517/517 |    462 |  336 | partly-in-db        | dne_facts economic-survey-gva-current (FY2081/82 annex 13.1, promoted) |
| P3   | `P3__Source_Book_White_Book_FY_2020-21_dkjqgrt_61533916`        | complete | 176/176 |    173 |    2 | owned-deterministic | mof_whitebook (Tier-1a, deterministic)                                 |
| P3   | `P3__source_book_final_20200623051728_qypntp8_eb465e80`         | complete | 176/176 |    173 |    2 | owned-deterministic | mof_whitebook (Tier-1a, deterministic)                                 |
| P3   | `P3__-__rjsmftf_8cb33a1f`                                       | complete |   65/65 |     64 |    1 | owned-deterministic | mof_whitebook (Tier-1a, deterministic)                                 |
| P3   | `P3__-__aaji14t_6c6a9288`                                       | complete |   58/58 |     57 |    1 | owned-deterministic | mof_whitebook (Tier-1a, deterministic)                                 |
| P3   | `P3__Source_Book_White_Book_FY_2015-16_7jvoiky_2582461f`        | complete |   54/54 |     53 |    2 | owned-deterministic | mof_whitebook (Tier-1a, deterministic)                                 |
| P3   | `P3__source_book_20150714124835_jzitx4k_47f23be3`               | complete |   54/54 |     53 |    2 | owned-deterministic | mof_whitebook (Tier-1a, deterministic)                                 |
| P3   | `P3__-__8xjyyod_3956617d`                                       | complete |   54/54 |     53 |    2 | owned-deterministic | mof_whitebook (Tier-1a, deterministic)                                 |
| P3   | `P3__-__hlihgjf_90aeddbb`                                       | complete |   50/50 |     50 |    2 | owned-deterministic | mof_whitebook (Tier-1a, deterministic)                                 |
| P3   | `P3__Source_Book_White_Book_FY_2065-2066_pdhwcnt_9dd3f5b9`      | complete |   45/45 |     44 |    1 | owned-deterministic | mof_whitebook (Tier-1a, deterministic)                                 |
| P3   | `P3__-__az1pmgw_d95dd66c`                                       | complete |   45/45 |     44 |    1 | owned-deterministic | mof_whitebook (Tier-1a, deterministic)                                 |
| P3   | `P3__Source_Book_White_Book_FY_2021-22_azz4yjf_999084e6`        | complete |   42/42 |     33 |    3 | owned-deterministic | mof_whitebook (Tier-1a, deterministic)                                 |
| P3   | `P3__Source_Book_White_Book_FY_2066-2067_rs9xxm2_c9e1ceee`      | complete |   41/41 |     40 |    1 | owned-deterministic | mof_whitebook (Tier-1a, deterministic)                                 |
| P3   | `P3__Source_Book_White_Book_FY_2067-2068_uruiozk_82e6dbee`      | complete |   41/41 |     41 |    1 | owned-deterministic | mof_whitebook (Tier-1a, deterministic)                                 |
| P3   | `P3__-__31acuu6_cbd219c0`                                       | complete |   41/41 |     41 |    1 | owned-deterministic | mof_whitebook (Tier-1a, deterministic)                                 |
| P4   | `P4__-__2qteqov_0b52daa4`                                       | pending  |   0/746 |      0 |    0 | partly-in-db        | dne_facts budget-allocation (1 FY: 2074/75, 57 heads)                  |
| P4   | `P4__-__6d7mimy_6227f9c7`                                       | pending  |   0/717 |      0 |    0 | partly-in-db        | dne_facts budget-allocation (1 FY: 2074/75, 57 heads)                  |
| P4   | `P4__Red_Book_Central_2074-75_20170530083940_00lqgwe_830109ba`  | partial  | 302/652 |    294 |    6 | partly-in-db        | dne_facts budget-allocation (1 FY: 2074/75, 57 heads)                  |
| P4   | `P4__RB_2070-71_20140722052750_d5gsbhl_290b1533`                | complete | 634/634 |    624 |   10 | partly-in-db        | dne_facts budget-allocation (1 FY: 2074/75, 57 heads)                  |
| P4   | `P4__20190603123023_4qfchpf_577867e3`                           | complete | 629/629 |    618 |   13 | partly-in-db        | dne_facts budget-allocation (1 FY: 2074/75, 57 heads)                  |
| P4   | `P4__-__l24f95n_0d1e9134`                                       | complete | 597/597 |    587 |   12 | partly-in-db        | dne_facts budget-allocation (1 FY: 2074/75, 57 heads)                  |
| P4   | `P4__Redbook_2077_Website_20201129075335_onafyha_a612b19a`      | complete | 566/566 |    557 |   13 | partly-in-db        | dne_facts budget-allocation (1 FY: 2074/75, 57 heads)                  |
| P4   | `P4__-__k3ip15v_13ce67d1`                                       | complete | 555/555 |    534 |   14 | partly-in-db        | dne_facts budget-allocation (1 FY: 2074/75, 57 heads)                  |
| P4   | `P4__RB_2069-70_20140722052658_wcqrs1s_6690ba61`                | complete | 551/551 |    540 |   10 | partly-in-db        | dne_facts budget-allocation (1 FY: 2074/75, 57 heads)                  |
| P4   | `P4__RB_2069-70_20140722052658_wxbli5d_62b1e76c`                | complete | 551/551 |    540 |   10 | partly-in-db        | dne_facts budget-allocation (1 FY: 2074/75, 57 heads)                  |
| P4   | `P4__Redbook_2080_81_vqjjhx7_b05b9593`                          | complete | 535/535 |    515 |   14 | partly-in-db        | dne_facts budget-allocation (1 FY: 2074/75, 57 heads)                  |
| P4   | `P4__Redbook_Final__2079_80_uryb8ga_06fe52c0`                   | complete | 529/529 |    508 |   14 | partly-in-db        | dne_facts budget-allocation (1 FY: 2074/75, 57 heads)                  |
| P4   | `P4__1636954126_Redbook_2078_79_Revised_5pfrbev_0315aab6`       | complete | 482/482 |    473 |   12 | partly-in-db        | dne_facts budget-allocation (1 FY: 2074/75, 57 heads)                  |
| P4   | `P4__N_20201125012405_5qa561u_01a78956`                         | complete | 461/461 |    458 |    7 | partly-in-db        | dne_facts budget-allocation (1 FY: 2074/75, 57 heads)                  |
| P4   | `P4__LI_2067-68_20140720071240_h6upkj4_e1741eea`                | complete | 269/269 |    266 |    3 | partly-in-db        | dne_facts budget-allocation (1 FY: 2074/75, 57 heads)                  |
| P4   | `P4__LI_2066-67_20140720071156_d3kn5vp_aba7596f`                | complete | 257/257 |    253 |    3 | partly-in-db        | dne_facts budget-allocation (1 FY: 2074/75, 57 heads)                  |
| P4   | `P4__1_20201125122043_2u9nn62_2e5c438d`                         | complete | 255/255 |    251 |    3 | partly-in-db        | dne_facts budget-allocation (1 FY: 2074/75, 57 heads)                  |
| P4   | `P4__-__bor7vrd_f9d3ee98`                                       | complete | 246/246 |    245 |    1 | partly-in-db        | dne_facts budget-allocation (1 FY: 2074/75, 57 heads)                  |
| P4   | `P4__-__r9f2qre_a870bec6`                                       | complete | 220/220 |    220 |    1 | partly-in-db        | dne_facts budget-allocation (1 FY: 2074/75, 57 heads)                  |
| P4   | `P4__Budget_Details_-_Red_Book_2062_-_2063_2013071712_350d64d2` | complete | 101/101 |    100 |    2 | partly-in-db        | dne_facts budget-allocation (1 FY: 2074/75, 57 heads)                  |
| P5   | `P5__207576_ce72ae7e`                                           | pending  |    0/41 |      0 |    0 | needs-decision      | local_government_fiscal_transfers (5 FYs: 2078/79-2082/83)             |

## Next up — top 30 of 1342 pending (value order)

|   # | id                  | tier | doc                    | page(s) | unit  | num-lines | coarse | dedup          | hint                                                         |
| --: | ------------------- | ---- | ---------------------- | ------- | ----- | --------: | :----: | -------------- | ------------------------------------------------------------ |
|   1 | `P0_33e35121_p0010` | P0   | `P0__207778_33e35121`  | 10–41   | lakh  |      4941 |        | needs-decision | p10 (untitled table)                                         |
|   2 | `P0_1d6841fe_p0071` | P0   | `P0__ksi3tbe_1d6841fe` | 71–77   | lakh  |       995 |        | new            | p71 (untitled table)                                         |
|   3 | `P0_1d6841fe_p0345` | P0   | `P0__ksi3tbe_1d6841fe` | 345–364 | lakh  |       661 |        | new            | ७.१ नेपाल सरकार वा नेपाल सरकारको स्वामित्वमा रहेका संस्थानहर |
|   4 | `P0_1d6841fe_p0256` | P0   | `P0__ksi3tbe_1d6841fe` | 256–266 | lakh  |       576 |        | new            | p256 (untitled table)                                        |
|   5 | `P0_1d6841fe_p0302` | P0   | `P0__ksi3tbe_1d6841fe` | 302–307 | lakh  |       448 |        | new            | p302 (untitled table)                                        |
|   6 | `P0_1d6841fe_p0087` | P0   | `P0__ksi3tbe_1d6841fe` | 87–88   | lakh  |       415 |        | new            | ५.११ - सार्वजनिक संस्थानको प्रशासनिक खर्च (कर्मचारी खर्चसहित |
|   7 | `P0_1d6841fe_p0337` | P0   | `P0__ksi3tbe_1d6841fe` | 337–342 | lakh  |       395 |        | new            | p337 (untitled table)                                        |
|   8 | `P0_1d6841fe_p0117` | P0   | `P0__ksi3tbe_1d6841fe` | 117–121 | lakh  |       343 |        | new            | p117 (untitled table)                                        |
|   9 | `P0_1d6841fe_p0136` | P0   | `P0__ksi3tbe_1d6841fe` | 136–144 | lakh  |       326 |        | new            | p136 (untitled table)                                        |
|  10 | `P0_1d6841fe_p0168` | P0   | `P0__ksi3tbe_1d6841fe` | 168–171 | lakh  |       316 |        | new            | p168 (untitled table)                                        |
|  11 | `P0_1d6841fe_p0250` | P0   | `P0__ksi3tbe_1d6841fe` | 250–253 | crore |       288 |        | new            | p250 (untitled table)                                        |
|  12 | `P0_1d6841fe_p0323` | P0   | `P0__ksi3tbe_1d6841fe` | 323–325 | ?     |       238 |        | new            | p323 (untitled table)                                        |
|  13 | `P0_1d6841fe_p0083` | P0   | `P0__ksi3tbe_1d6841fe` | 83–84   | lakh  |       232 |        | new            | ५.९ - सार्वजनिक संस्थानको कुल सञ्चालन/बिक्री आय              |
|  14 | `P0_1d6841fe_p0394` | P0   | `P0__ksi3tbe_1d6841fe` | 394     | ?     |       232 |        | new            | अनुसूची ४                                                    |
|  15 | `P0_1d6841fe_p0395` | P0   | `P0__ksi3tbe_1d6841fe` | 395     | lakh  |       222 |        | new            | अनुसूची ४ वाट                                                |
|  16 | `P0_1d6841fe_p0282` | P0   | `P0__ksi3tbe_1d6841fe` | 282–284 | ?     |       218 |        | new            | p282 (untitled table)                                        |
|  17 | `P0_1d6841fe_p0161` | P0   | `P0__ksi3tbe_1d6841fe` | 161–163 | lakh  |       215 |        | new            | p161 (untitled table)                                        |
|  18 | `P0_1d6841fe_p0393` | P0   | `P0__ksi3tbe_1d6841fe` | 393     | ?     |       215 |        | new            | अनुसूची ४ बाट                                                |
|  19 | `P0_1d6841fe_p0185` | P0   | `P0__ksi3tbe_1d6841fe` | 185–188 | lakh  |       209 |        | new            | p185 (untitled table)                                        |
|  20 | `P0_1d6841fe_p0367` | P0   | `P0__ksi3tbe_1d6841fe` | 367–376 | lakh  |       208 |        | new            | p367 (untitled table)                                        |
|  21 | `P0_1d6841fe_p0085` | P0   | `P0__ksi3tbe_1d6841fe` | 85–86   | lakh  |       203 |        | new            | ५.१० - सार्वजनिक संस्थानको खुद नाफा/नोक्सान                  |
|  22 | `P0_1d6841fe_p0111` | P0   | `P0__ksi3tbe_1d6841fe` | 111–113 | lakh  |       191 |        | new            | p111 (untitled table)                                        |
|  23 | `P0_1d6841fe_p0173` | P0   | `P0__ksi3tbe_1d6841fe` | 173–176 | lakh  |       189 |        | new            | p173 (untitled table)                                        |
|  24 | `P0_1d6841fe_p0203` | P0   | `P0__ksi3tbe_1d6841fe` | 203–204 | ?     |       178 |        | new            | p203 (untitled table)                                        |
|  25 | `P0_1d6841fe_p0094` | P0   | `P0__ksi3tbe_1d6841fe` | 94–95   | lakh  |       171 |        | new            | ५.१५ - सार्वजनिक संस्थानको सञ्चित नाफा तथा नोक्सान रकमको विव |
|  26 | `P0_1d6841fe_p0330` | P0   | `P0__ksi3tbe_1d6841fe` | 330–332 | ?     |       171 |        | new            | p330 (untitled table)                                        |
|  27 | `P0_1d6841fe_p0024` | P0   | `P0__ksi3tbe_1d6841fe` | 24–25   | lakh  |       166 |        | new            | तालिका १.३                                                   |
|  28 | `P0_1d6841fe_p0004` | P0   | `P0__ksi3tbe_1d6841fe` | 4–8     | ?     |       163 |        | new            | तालिका सूची                                                  |
|  29 | `P0_1d6841fe_p0180` | P0   | `P0__ksi3tbe_1d6841fe` | 180–183 | lakh  |       164 |        | new            | p180 (untitled table)                                        |
|  30 | `P0_1d6841fe_p0289` | P0   | `P0__ksi3tbe_1d6841fe` | 289–290 | ?     |       162 |        | new            | p289 (untitled table)                                        |

## Remaining pending by tier

| Tier | Pending candidates | Σ num-lines |
| ---- | -----------------: | ----------: |
| P0   |                111 |      18,337 |
| P1   |                387 |      44,706 |
| P2   |                674 |     101,168 |
| P3   |                 22 |     126,325 |
| P4   |                148 |   1,436,499 |
