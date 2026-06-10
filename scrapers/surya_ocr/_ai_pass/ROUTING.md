# Corpus routing plan (operationalizes the "route smart" decision, 2026-06-11)

Most of the corpus has a usable text layer and should go to CHEAP deterministic parsers, NOT LLM-OCR.
LLM-OCR is reserved for broken-text-layer (econ surveys, clean pages) + genuinely-scanned high-value.

| Route           | docs | pages |
| --------------- | ---: | ----: |
| A-deterministic |   39 | 11742 |
| B-LLM-clean     |    2 |  1064 |
| C-scan-limited  |    1 |   402 |
| C-scan-lowvalue |    6 |     6 |
| C-scan/ADR      |    2 |    83 |

**Routes:** A-deterministic = existing Python parsers (cents/doc, exact) · B-LLM-clean = LLM-OCR on reconcilable levels tables · C-scan-limited = genuinely scanned, LLM partial yield or re-scan.

## Per-document

| Tier | Category          | Document                                                        | Pages | Scanned | ROUTE               | Rationale                                                                       |
| ---- | ----------------- | --------------------------------------------------------------- | ----: | :-----: | ------------------- | ------------------------------------------------------------------------------- |
| P0   | agreement         | P0\_\_1658043201_Progress_Report-Upto_Asar-2_cpok5mz_9d37560e   |     1 |    Y    | **C-scan-lowvalue** | 1-page scan; low structured-data value                                          |
| P0   | agreement         | P0\_\_1658642431_Progress_Report_2077.078_zaif6ul_83e591af      |     1 |    Y    | **C-scan-lowvalue** | 1-page scan; low structured-data value                                          |
| P0   | agreement         | P0\_\_1689830981_Commitment_UP_TO_Aashar_2080_cn3p3t5_2c129948  |     1 |    Y    | **C-scan-lowvalue** | 1-page scan; low structured-data value                                          |
| P0   | agreement         | P0\_\_Agreement_FY2324_8081_tk2vpt2_75b512b7                    |     1 |    Y    | **C-scan-lowvalue** | 1-page scan; low structured-data value                                          |
| P0   | agreement         | P0\_\_Agreement_FY2526_8283_ewzykwa_93adab98                    |     1 |    Y    | **C-scan-lowvalue** | 1-page scan; low structured-data value                                          |
| P0   | agreement         | P0**earthquake**20170428064449_20170502064348_5u8dzg_683d7007   |     1 |    Y    | **C-scan-lowvalue** | 1-page scan; low structured-data value                                          |
| P0   | intergovernmental | P0\_\_207778_33e35121                                           |    42 |    n    | **C-scan/ADR**      | scanned/low-text + 4-aggregate-grant ADR                                        |
| P0   | yellowbook        | P0\_\_ksi3tbe_1d6841fe                                          |   402 |    Y    | **C-scan-limited**  | SCANNED — LLM partial (sparse tables OK ~59%, dense ~3%)                        |
| P1   | yellowbook        | P1\_\_brzjuc2_cc19bfc2                                          |    97 |    n    | **A-deterministic** | TEXT-LAYER Devanagari (dev_ratio 0.76) -> deterministic SOE parser, cheap+exact |
| P1   | yellowbook        | P1\_\_wwehtk3_de6adeac                                          |   111 |    n    | **A-deterministic** | TEXT-LAYER Devanagari (dev_ratio 0.73) -> deterministic SOE parser, cheap+exact |
| P1   | yellowbook        | P1\_\_Webiste_Uploaded_Yellow_sdwyi9v_a3023ba4                  |   210 |    n    | **A-deterministic** | TEXT-LAYER Devanagari (dev_ratio 0.64) -> deterministic SOE parser, cheap+exact |
| P1   | yellowbook        | P1\_\_1685280975_Yellow_Book_BIG_2080_Final_6jh3p9r_9c4afda0    |   404 |    n    | **A-deterministic** | TEXT-LAYER Devanagari (dev_ratio 0.65) -> deterministic SOE parser, cheap+exact |
| P1   | yellowbook        | P1**1653757638\_**ab0trdn_81c127cf                              |   425 |    n    | **A-deterministic** | TEXT-LAYER Devanagari (dev_ratio 0.67) -> deterministic SOE parser, cheap+exact |
| P2   | economic_survey   | P2\_\_Economic_Survey_2081-82_309ffe7c                          |   517 |    n    | **B-LLM-clean**     | broken/RTL text layer -> LLM-OCR; pick reconcilable LEVELS tables only          |
| P2   | economic_survey   | P2\_\_Economic_Survey_2080-81_NP_a8c6ee07                       |   547 |    n    | **B-LLM-clean**     | broken/RTL text layer -> LLM-OCR; pick reconcilable LEVELS tables only          |
| P3   | whitebook         | P3\_\_Source_Book_White_Book_FY_2066-2067_rs9xxm2_c9e1ceee      |    41 |    n    | **A-deterministic** | mof_whitebook (Preeti remap) — DONE; gap FYs 2062/63,2064/65,2078/79 remain     |
| P3   | whitebook         | P3\_\_Source_Book_White_Book_FY_2067-2068_uruiozk_82e6dbee      |    41 |    n    | **A-deterministic** | mof_whitebook (Preeti remap) — DONE; gap FYs 2062/63,2064/65,2078/79 remain     |
| P3   | whitebook         | P3**-**31acuu6_cbd219c0                                         |    41 |    n    | **A-deterministic** | mof_whitebook (Preeti remap) — DONE; gap FYs 2062/63,2064/65,2078/79 remain     |
| P3   | whitebook         | P3\_\_Source_Book_White_Book_FY_2021-22_azz4yjf_999084e6        |    42 |    n    | **A-deterministic** | mof_whitebook (Preeti remap) — DONE; gap FYs 2062/63,2064/65,2078/79 remain     |
| P3   | whitebook         | P3\_\_Source_Book_White_Book_FY_2065-2066_pdhwcnt_9dd3f5b9      |    45 |    n    | **A-deterministic** | mof_whitebook (Preeti remap) — DONE; gap FYs 2062/63,2064/65,2078/79 remain     |
| P3   | whitebook         | P3**-**az1pmgw_d95dd66c                                         |    45 |    n    | **A-deterministic** | mof_whitebook (Preeti remap) — DONE; gap FYs 2062/63,2064/65,2078/79 remain     |
| P3   | whitebook         | P3**-**hlihgjf_90aeddbb                                         |    50 |    n    | **A-deterministic** | mof_whitebook (Preeti remap) — DONE; gap FYs 2062/63,2064/65,2078/79 remain     |
| P3   | whitebook         | P3\_\_Source_Book_White_Book_FY_2015-16_7jvoiky_2582461f        |    54 |    n    | **A-deterministic** | mof_whitebook (Preeti remap) — DONE; gap FYs 2062/63,2064/65,2078/79 remain     |
| P3   | whitebook         | P3\_\_source_book_20150714124835_jzitx4k_47f23be3               |    54 |    n    | **A-deterministic** | mof_whitebook (Preeti remap) — DONE; gap FYs 2062/63,2064/65,2078/79 remain     |
| P3   | whitebook         | P3**-**8xjyyod_3956617d                                         |    54 |    n    | **A-deterministic** | mof_whitebook (Preeti remap) — DONE; gap FYs 2062/63,2064/65,2078/79 remain     |
| P3   | whitebook         | P3**-**aaji14t_6c6a9288                                         |    58 |    n    | **A-deterministic** | mof_whitebook (Preeti remap) — DONE; gap FYs 2062/63,2064/65,2078/79 remain     |
| P3   | whitebook         | P3**-**rjsmftf_8cb33a1f                                         |    65 |    n    | **A-deterministic** | mof_whitebook (Preeti remap) — DONE; gap FYs 2062/63,2064/65,2078/79 remain     |
| P3   | whitebook         | P3\_\_Source_Book_White_Book_FY_2020-21_dkjqgrt_61533916        |   176 |    n    | **A-deterministic** | mof_whitebook (Preeti remap) — DONE; gap FYs 2062/63,2064/65,2078/79 remain     |
| P3   | whitebook         | P3\_\_source_book_final_20200623051728_qypntp8_eb465e80         |   176 |    n    | **A-deterministic** | mof_whitebook (Preeti remap) — DONE; gap FYs 2062/63,2064/65,2078/79 remain     |
| P4   | redbook           | P4\__Budget_Details_-_Red_Book_2062_-\_2063_2013071712_350d64d2 |   101 |    n    | **A-deterministic** | redbook parser (text-layer/Preeti); rec+cap=total gate                          |
| P4   | redbook           | P4**-**r9f2qre_a870bec6                                         |   220 |    n    | **A-deterministic** | redbook parser (text-layer/Preeti); rec+cap=total gate                          |
| P4   | redbook           | P4**-**bor7vrd_f9d3ee98                                         |   246 |    n    | **A-deterministic** | redbook parser (text-layer/Preeti); rec+cap=total gate                          |
| P4   | redbook           | P4\_\_1_20201125122043_2u9nn62_2e5c438d                         |   255 |    n    | **A-deterministic** | redbook parser (text-layer/Preeti); rec+cap=total gate                          |
| P4   | redbook           | P4\_\_LI_2066-67_20140720071156_d3kn5vp_aba7596f                |   257 |    n    | **A-deterministic** | redbook parser (text-layer/Preeti); rec+cap=total gate                          |
| P4   | redbook           | P4\_\_LI_2067-68_20140720071240_h6upkj4_e1741eea                |   269 |    n    | **A-deterministic** | redbook parser (text-layer/Preeti); rec+cap=total gate                          |
| P4   | redbook           | P4\_\_N_20201125012405_5qa561u_01a78956                         |   461 |    n    | **A-deterministic** | redbook parser (text-layer/Preeti); rec+cap=total gate                          |
| P4   | redbook           | P4\_\_1636954126_Redbook_2078_79_Revised_5pfrbev_0315aab6       |   482 |    n    | **A-deterministic** | redbook parser (text-layer/Preeti); rec+cap=total gate                          |
| P4   | redbook           | P4**Redbook_Final**2079_80_uryb8ga_06fe52c0                     |   529 |    n    | **A-deterministic** | redbook parser (text-layer/Preeti); rec+cap=total gate                          |
| P4   | redbook           | P4\_\_Redbook_2080_81_vqjjhx7_b05b9593                          |   535 |    n    | **A-deterministic** | redbook parser (text-layer/Preeti); rec+cap=total gate                          |
| P4   | redbook           | P4\_\_RB_2069-70_20140722052658_wcqrs1s_6690ba61                |   551 |    n    | **A-deterministic** | redbook parser (text-layer/Preeti); rec+cap=total gate                          |
| P4   | redbook           | P4\_\_RB_2069-70_20140722052658_wxbli5d_62b1e76c                |   551 |    n    | **A-deterministic** | redbook parser (text-layer/Preeti); rec+cap=total gate                          |
| P4   | redbook           | P4**-**k3ip15v_13ce67d1                                         |   555 |    n    | **A-deterministic** | redbook parser (text-layer/Preeti); rec+cap=total gate                          |
| P4   | redbook           | P4\_\_Redbook_2077_Website_20201129075335_onafyha_a612b19a      |   566 |    n    | **A-deterministic** | redbook parser (text-layer/Preeti); rec+cap=total gate                          |
| P4   | redbook           | P4**-**l24f95n_0d1e9134                                         |   597 |    n    | **A-deterministic** | redbook parser (text-layer/Preeti); rec+cap=total gate                          |
| P4   | redbook           | P4\_\_20190603123023_4qfchpf_577867e3                           |   629 |    n    | **A-deterministic** | redbook parser (text-layer/Preeti); rec+cap=total gate                          |
| P4   | redbook           | P4\_\_RB_2070-71_20140722052750_d5gsbhl_290b1533                |   634 |    n    | **A-deterministic** | redbook parser (text-layer/Preeti); rec+cap=total gate                          |
| P4   | redbook           | P4\_\_Red_Book_Central_2074-75_20170530083940_00lqgwe_830109ba  |   652 |    n    | **A-deterministic** | redbook parser (text-layer/Preeti); rec+cap=total gate                          |
| P4   | redbook           | P4**-**6d7mimy_6227f9c7                                         |   717 |    n    | **A-deterministic** | redbook parser (text-layer/Preeti); rec+cap=total gate                          |
| P4   | redbook           | P4**-**2qteqov_0b52daa4                                         |   746 |    n    | **A-deterministic** | redbook parser (text-layer/Preeti); rec+cap=total gate                          |
| P5   | intergovernmental | P5\_\_207576_ce72ae7e                                           |    41 |    n    | **C-scan/ADR**      | scanned/low-text + 4-aggregate-grant ADR                                        |
