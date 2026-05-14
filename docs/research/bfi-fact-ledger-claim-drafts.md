# Fact Ledger claim drafts — NRB BFI 49-month analytical pass

**Source:** Worker κ analytical pass; all values from `staging-data/nrb-bfi/*.json` produced by `scrapers.nrb_bfi` v0.1.0.
**Confidence:** all A (NRB is Tier-1 per `docs/SOURCE_REGISTRY.md`).
**Slug convention:** `nrb-bfi--<indicator-slug>--<bank_class>--<period-bs-slug>--<delta-or-level>`. Periods slugged as `<month-lower>-<bs-year>`. Deterministic: same input → same slug.

> The `text_ne` field is populated where translation is unambiguous; the rest are flagged for editorial translation. Indicator slugs in this draft assume `<sheet>--<indicator_slug>` keys; the materialized Indicator entity name should be set by Worker Ε's source-registry seed when these claims land.

---

## 1. Banking system aggregates

### Claim 1
- **slug:** `nrb-bfi--cd-ratio--system-total--bhadra-2082--level`
- **text_en:** "Nepal's system-wide credit-deposit ratio stood at 75.90% in Bhadra 2082 (Mid-Sept 2025), down from 86.98% in Shrawan 2078."
- **text_ne:** `[needs editorial translation]`
- **indicator_slug:** `nrb-bfi--c4--credit-deposit-ratios--cd-ratio`
- **bank_class:** `system_total`
- **period_label:** `Bhadra 2082`
- **value:** 75.903209
- **source_file:** `staging-data/nrb-bfi/Bhadau_2082_Publish.json`
- **confidence_grade:** A

### Claim 2
- **slug:** `nrb-bfi--cd-ratio--system-total--shrawan-2078-to-bhadra-2082--delta`
- **text_en:** "Nepal's system credit-deposit ratio fell 11.08 percentage points between Shrawan 2078 and Bhadra 2082 — from 86.98% to 75.90%."
- **indicator_slug:** `nrb-bfi--c4--credit-deposit-ratios--cd-ratio`
- **bank_class:** `system_total`
- **period_label:** `Shrawan 2078 → Bhadra 2082`
- **value:** -11.08
- **unit:** percentage_points
- **source_file:** `staging-data/nrb-bfi/Shrawan-2078-2.json` + `staging-data/nrb-bfi/Bhadau_2082_Publish.json`
- **confidence_grade:** A

### Claim 3
- **slug:** `nrb-bfi--total-credit-gdp--system-total--ashadh-2082--level`
- **text_en:** "Bank credit to the private sector equalled 91.60% of GDP in Ashadh 2082 (FY-end 2081/82), down 7.40 pp from 99.00% in Shrawan 2078."
- **indicator_slug:** `nrb-bfi--c4--credit-deposit-ratios--total-credit-gdp`
- **bank_class:** `system_total`
- **period_label:** `Ashadh 2082`
- **value:** 91.60
- **unit:** percent
- **source_file:** `staging-data/nrb-bfi/Asar_2082_Publish.json`
- **confidence_grade:** A

### Claim 4
- **slug:** `nrb-bfi--total-deposit-gdp--system-total--ashadh-2082--level`
- **text_en:** "Bank deposits stood at 119.59% of GDP in Ashadh 2082, up 10.21 pp from 109.38% in Shrawan 2078 — deposits grew faster than the economy while credit shrank as a share of GDP."
- **indicator_slug:** `nrb-bfi--c4--credit-deposit-ratios--total-deposit-gdp`
- **bank_class:** `system_total`
- **period_label:** `Ashadh 2082`
- **value:** 119.59
- **unit:** percent
- **source_file:** `staging-data/nrb-bfi/Asar_2082_Publish.json`
- **confidence_grade:** A

---

## 2. Asset-quality (NPL)

### Claim 5
- **slug:** `nrb-bfi--npl-total-loan--system-total--bhadra-2082--level`
- **text_en:** "System non-performing loans were 4.62% of total loans in Bhadra 2082 — more than triple the 1.48% recorded in Shrawan 2078."
- **indicator_slug:** `nrb-bfi--c4--credit-deposit-ratios--npl-total-loan`
- **bank_class:** `system_total`
- **period_label:** `Bhadra 2082`
- **value:** 4.62
- **unit:** percent
- **source_file:** `staging-data/nrb-bfi/Bhadau_2082_Publish.json`
- **confidence_grade:** A

### Claim 6
- **slug:** `nrb-bfi--npl-total-loan--finance--bhadra-2082--level`
- **text_en:** "Finance-company-class NPL stood at 11.05% in Bhadra 2082 — 2.5× the commercial-bank ratio (4.44%) and 2.2× the development-bank ratio (5.03%)."
- **indicator_slug:** `nrb-bfi--c4--credit-deposit-ratios--npl-total-loan`
- **bank_class:** `finance`
- **period_label:** `Bhadra 2082`
- **value:** 11.05
- **unit:** percent
- **source_file:** `staging-data/nrb-bfi/Bhadau_2082_Publish.json`
- **confidence_grade:** A

### Claim 7
- **slug:** `nrb-bfi--npl-total-loan--system-total--poush-2081--peak`
- **text_en:** "System NPL peaked at 4.92% in Poush 2081 (Mid-Jan 2025) and has eased to 4.62% by Bhadra 2082 — the first quarter-on-quarter improvement in the 47-month series."
- **indicator_slug:** `nrb-bfi--c4--credit-deposit-ratios--npl-total-loan`
- **bank_class:** `system_total`
- **period_label:** `Poush 2081`
- **value:** 4.92
- **unit:** percent
- **source_file:** `staging-data/nrb-bfi/Poush_2081_Publish_2.json`
- **confidence_grade:** A

### Claim 8
- **slug:** `nrb-bfi--total-llp-total-loan--system-total--ashadh-2082--level`
- **text_en:** "Total loan-loss provisions reached 5.09% of total loans in Ashadh 2082, up from 2.45% in Shrawan 2078 — provisioning rose roughly in line with the NPL ratio."
- **indicator_slug:** `nrb-bfi--c4--credit-deposit-ratios--total-llp-total-loan`
- **bank_class:** `system_total`
- **period_label:** `Ashadh 2082`
- **value:** 5.09
- **unit:** percent
- **source_file:** `staging-data/nrb-bfi/Asar_2082_Publish.json`
- **confidence_grade:** A

---

## 3. Capital adequacy and profitability proxy

### Claim 9
- **slug:** `nrb-bfi--capital-adequacy-total-rwa--system-total--ashadh-2082--level`
- **text_en:** "System total capital adequacy ratio was 12.95% in Ashadh 2082, down from 14.19% in Shrawan 2078 — the system has moved 1.24 pp closer to the 11% regulatory floor."
- **indicator_slug:** `nrb-bfi--c4--capital-adequacy-ratios--total-capital-rwa`
- **bank_class:** `system_total`
- **period_label:** `Ashadh 2082`
- **value:** 12.95
- **unit:** percent
- **source_file:** `staging-data/nrb-bfi/Asar_2082_Publish.json`
- **confidence_grade:** A

### Claim 10
- **slug:** `nrb-bfi--capital-adequacy-total-rwa--finance--ashadh-2082--level`
- **text_en:** "Finance-company capital adequacy dropped from 22.04% in Shrawan 2078 to 13.93% in Ashadh 2082 — a 8.10 pp erosion of the segment's Tier 1+2 cushion."
- **indicator_slug:** `nrb-bfi--c4--capital-adequacy-ratios--total-capital-rwa`
- **bank_class:** `finance`
- **period_label:** `Ashadh 2082`
- **value:** 13.93
- **unit:** percent
- **source_file:** `staging-data/nrb-bfi/Asar_2082_Publish.json`
- **confidence_grade:** A

### Claim 11
- **slug:** `nrb-bfi--capital-fund-retained-earning--system-total--ashadh-2082--level`
- **text_en:** "Banking-system retained earnings turned negative in the 47-month window — from +NPR 75,135 million in Shrawan 2078 to –NPR 31,473 million by Ashadh 2082, even as paid-up capital rose NPR 77,745 million."
- **indicator_slug:** `nrb-bfi--c5--capital-fund--retained-earning`
- **bank_class:** `system_total`
- **period_label:** `Ashadh 2082`
- **value:** -31472.59
- **unit:** NPR_million
- **source_file:** `staging-data/nrb-bfi/Asar_2082_Publish.json`
- **confidence_grade:** A

### Claim 12
- **slug:** `nrb-bfi--wt-avg-credit-rate--commercial--ashadh-2082--level`
- **text_en:** "Commercial-bank weighted-average lending rate fell to 7.85% by Ashadh 2082 from 8.48% in Shrawan 2078; deposit rate fell 4.76% → 4.19%; the implied gross spread compressed slightly from 3.72 pp to 3.66 pp."
- **indicator_slug:** `nrb-bfi--c4--interest-rate--wt-avg-interest-rate-on-credit`
- **bank_class:** `commercial`
- **period_label:** `Ashadh 2082`
- **value:** 7.85
- **unit:** percent
- **source_file:** `staging-data/nrb-bfi/Asar_2082_Publish.json`
- **confidence_grade:** A

---

## 4. Sector credit allocation (the Vertical 16 spine)

### Claim 13
- **slug:** `nrb-bfi--construction--system-total--ashadh-2082-vs-shrawan-2078--delta-absolute`
- **text_en:** "Outstanding bank credit to the construction sector fell from NPR 416,865 million in Shrawan 2078 to NPR 231,369 million in Ashadh 2082 — a 44.5% absolute contraction over 47 months."
- **indicator_slug:** `nrb-bfi--c7--construction`
- **bank_class:** `system_total`
- **period_label:** `Shrawan 2078 → Ashadh 2082`
- **value:** -185495.34
- **unit:** NPR_million
- **source_file:** `staging-data/nrb-bfi/Shrawan-2078-2.json` + `staging-data/nrb-bfi/Asar_2082_Publish.json`
- **confidence_grade:** A

### Claim 14
- **slug:** `nrb-bfi--construction--system-total--ashadh-2082--share-of-loan-book`
- **text_en:** "Construction's share of total system bank credit fell from 9.88% in Shrawan 2078 to 4.14% in Ashadh 2082 — a 5.74 pp retreat over 47 months."
- **indicator_slug:** `nrb-bfi--c7--construction-share-of-total`
- **bank_class:** `system_total`
- **period_label:** `Ashadh 2082`
- **value:** 4.14
- **unit:** percent
- **source_file:** `staging-data/nrb-bfi/Asar_2082_Publish.json`
- **confidence_grade:** A

### Claim 15
- **slug:** `nrb-bfi--consumption-loans--system-total--ashadh-2082--share-of-loan-book`
- **text_en:** "Consumption loans rose from 5.57% to 20.60% of system bank credit between Shrawan 2078 and Ashadh 2082 — the single largest compositional shift in the 47-month window, partly reflecting reclassification but more than tripling in absolute NPR terms."
- **indicator_slug:** `nrb-bfi--c7--consumption-loans-share-of-total`
- **bank_class:** `system_total`
- **period_label:** `Ashadh 2082`
- **value:** 20.60
- **unit:** percent
- **source_file:** `staging-data/nrb-bfi/Asar_2082_Publish.json`
- **confidence_grade:** A

### Claim 16
- **slug:** `nrb-bfi--electricity-gas-water--system-total--ashadh-2082--share-of-loan-book`
- **text_en:** "Bank credit to electricity, gas and water sector grew from 4.99% to 7.97% of total system credit over 47 months — driven by the FY 2080/81 hydropower IPO cycle."
- **indicator_slug:** `nrb-bfi--c7--electricity-gas-and-water-share-of-total`
- **bank_class:** `system_total`
- **period_label:** `Ashadh 2082`
- **value:** 7.97
- **unit:** percent
- **source_file:** `staging-data/nrb-bfi/Asar_2082_Publish.json`
- **confidence_grade:** A

### Claim 17
- **slug:** `nrb-bfi--agricultural-and-forest-related--system-total--ashadh-2082--share-of-loan-book`
- **text_en:** "Agricultural credit's share of the total loan book was 6.37% in Ashadh 2082, essentially unchanged from 6.60% in Shrawan 2078 — agriculture has not gained ground in the system's loan composition over the 47-month window."
- **indicator_slug:** `nrb-bfi--c7--agricultural-and-forest-related-share-of-total`
- **bank_class:** `system_total`
- **period_label:** `Ashadh 2082`
- **value:** 6.37
- **unit:** percent
- **source_file:** `staging-data/nrb-bfi/Asar_2082_Publish.json`
- **confidence_grade:** A

### Claim 18
- **slug:** `nrb-bfi--deprived-sector-loan-total-loan--system-total--ashadh-2082--level`
- **text_en:** "Deprived-sector lending was 5.52% of total bank loans in Ashadh 2082, down 2.73 pp from 8.25% in Shrawan 2078 — the inclusion-mandate compliance ratio has declined materially."
- **indicator_slug:** `nrb-bfi--c4--credit-deposit-ratios--deprived-sector-loan-total-loan`
- **bank_class:** `system_total`
- **period_label:** `Ashadh 2082`
- **value:** 5.52
- **unit:** percent
- **source_file:** `staging-data/nrb-bfi/Asar_2082_Publish.json`
- **confidence_grade:** A

### Claim 19
- **slug:** `nrb-bfi--productwise-term-loan--system-total--ashadh-2082--share-of-loan-book`
- **text_en:** "Term loans rose from 22.52% to 36.98% of total system credit (productwise) over 47 months — a 14.45 pp jump that mirrors the 13.26 pp fall in overdraft share, reflecting NRB's working-capital reclassification directive."
- **indicator_slug:** `nrb-bfi--c7--productwise--term-loan-share-of-total`
- **bank_class:** `system_total`
- **period_label:** `Ashadh 2082`
- **value:** 36.98
- **unit:** percent
- **source_file:** `staging-data/nrb-bfi/Asar_2082_Publish.json`
- **confidence_grade:** A

---

## 5. Bank-class concentration

### Claim 20
- **slug:** `nrb-bfi--deposit-share--commercial--ashadh-2082--level`
- **text_en:** "Commercial banks held 89.57% of system deposits in Ashadh 2082, up 1.16 pp from 88.41% in Shrawan 2078; development banks (8.63%) and finance companies (1.80%) lost share."
- **indicator_slug:** `nrb-bfi--c5--deposits-share-by-class`
- **bank_class:** `commercial`
- **period_label:** `Ashadh 2082`
- **value:** 89.57
- **unit:** percent
- **source_file:** `staging-data/nrb-bfi/Asar_2082_Publish.json`
- **confidence_grade:** A

### Claim 21
- **slug:** `nrb-bfi--hhi-deposits-bank-class--system-total--ashadh-2082--level`
- **text_en:** "Bank-class deposit HHI rose from 7,914 to 8,100 between Shrawan 2078 and Ashadh 2082 — a modest concentration drift of +186 points at the class level (per-bank HHI not yet computable; awaits parser v0.2.0)."
- **indicator_slug:** `nrb-bfi--derived--hhi-deposits-by-class`
- **bank_class:** `system_total`
- **period_label:** `Ashadh 2082`
- **value:** 8100
- **unit:** index_0_to_10000
- **source_file:** `docs/research/_bfi_workspace/concentration.json`
- **confidence_grade:** A

---

## 6. Deposits + access

### Claim 22
- **slug:** `nrb-bfi--deposits--system-total--ashadh-2082--level-npr-million`
- **text_en:** "Total bank deposits reached NPR 7,303,531 million in Ashadh 2082, up 56.5% from NPR 4,666,314 million in Shrawan 2078."
- **indicator_slug:** `nrb-bfi--c5--deposits`
- **bank_class:** `system_total`
- **period_label:** `Ashadh 2082`
- **value:** 7303531.19
- **unit:** NPR_million
- **source_file:** `staging-data/nrb-bfi/Asar_2082_Publish.json`
- **confidence_grade:** A

### Claim 23
- **slug:** `nrb-bfi--deposits-savings-share--system-total--ashadh-2082--level`
- **text_en:** "Savings deposits rose to 36.60% of total system deposits in Ashadh 2082 from 33.76% in Shrawan 2078; fixed deposits' share fell from 49.34% to 48.02%."
- **indicator_slug:** `nrb-bfi--c4--credit-deposit-ratios--saving-deposit-total-deposit`
- **bank_class:** `system_total`
- **period_label:** `Ashadh 2082`
- **value:** 36.60
- **unit:** percent
- **source_file:** `staging-data/nrb-bfi/Asar_2082_Publish.json`
- **confidence_grade:** A

### Claim 24
- **slug:** `nrb-bfi--no-of-deposit-accounts--system-total--ashadh-2082--level`
- **text_en:** "System deposit-account count reached 59.88 million in Ashadh 2082, up 58.5% from 37.77 million in Shrawan 2078; mobile-banking customers nearly doubled to 27.74 million."
- **indicator_slug:** `nrb-bfi--c4--financial-access--no-of-deposit-accounts`
- **bank_class:** `system_total`
- **period_label:** `Ashadh 2082`
- **value:** 59881353
- **unit:** count
- **source_file:** `staging-data/nrb-bfi/Asar_2082_Publish.json`
- **confidence_grade:** A

### Claim 25
- **slug:** `nrb-bfi--no-of-branches--system-total--ashadh-2082--level`
- **text_en:** "Bank branch network reached 6,522 in Ashadh 2082, up 8.4% from 6,015 in Shrawan 2078 — branch growth lagged deposit-account growth (+58.5%) by roughly seven-to-one."
- **indicator_slug:** `nrb-bfi--c4--financial-access--no-of-branches`
- **bank_class:** `system_total`
- **period_label:** `Ashadh 2082`
- **value:** 6522
- **unit:** count
- **source_file:** `staging-data/nrb-bfi/Asar_2082_Publish.json`
- **confidence_grade:** A

---

## 7. Investments — the government-securities channel

### Claim 26
- **slug:** `nrb-bfi--investments--system-total--ashadh-2082--level-npr-million`
- **text_en:** "Bank investments reached NPR 1,743,212 million in Ashadh 2082, up 137.4% from NPR 734,383 million in Shrawan 2078 — banks redirected the deposit growth they did not lend to government securities and other instruments."
- **indicator_slug:** `nrb-bfi--c5--investments`
- **bank_class:** `system_total`
- **period_label:** `Ashadh 2082`
- **value:** 1743211.67
- **unit:** NPR_million
- **source_file:** `staging-data/nrb-bfi/Asar_2082_Publish.json`
- **confidence_grade:** A

### Claim 27
- **slug:** `nrb-bfi--investments-govt-securities--system-total--ashadh-2082--level-npr-million`
- **text_en:** "Government-securities holdings on bank balance sheets reached NPR 1,172,419 million in Ashadh 2082, up 62.1% from NPR 723,233 million in Shrawan 2078."
- **indicator_slug:** `nrb-bfi--c5--investments--govt-securities`
- **bank_class:** `system_total`
- **period_label:** `Ashadh 2082`
- **value:** 1172419.07
- **unit:** NPR_million
- **source_file:** `staging-data/nrb-bfi/Asar_2082_Publish.json`
- **confidence_grade:** A

---

## 8. Productive vs. real-estate ratio (the Vertical 16 headline)

### Claim 28
- **slug:** `nrb-bfi--re-vs-productive-share-ratio--system-total--ashadh-2082--level`
- **text_en:** "The ratio of system bank credit to the real-estate cluster vs. productive sectors (agriculture + hydropower + manufacturing + transport + mining + tourism) was 0.58 in Ashadh 2082, down from 0.79 in Shrawan 2078 — productive sectors gained 6.3 pp of share while the real-estate cluster's share was flat."
- **indicator_slug:** `nrb-bfi--derived--re-vs-productive-share-ratio`
- **bank_class:** `system_total`
- **period_label:** `Ashadh 2082`
- **value:** 0.58
- **unit:** ratio
- **source_file:** `docs/research/_bfi_workspace/re_vs_productive.json`
- **confidence_grade:** A

### Claim 29
- **slug:** `nrb-bfi--re-cluster-share--system-total--ashadh-2082--level`
- **text_en:** "The real-estate cluster (productwise--real-estate-loan + finance-insurance-and-real-estate) accounted for 12.82% of total system bank credit in Ashadh 2082 — essentially flat from 12.42% in Shrawan 2078, contradicting the popular framing that Nepal's banks have moved into real estate."
- **indicator_slug:** `nrb-bfi--derived--re-cluster-share-of-total`
- **bank_class:** `system_total`
- **period_label:** `Ashadh 2082`
- **value:** 12.82
- **unit:** percent
- **source_file:** `docs/research/_bfi_workspace/re_vs_productive.json`
- **confidence_grade:** A

---

## 9. Revision detection (data-quality finding)

### Claim 30
- **slug:** `nrb-bfi--revisions-detected--c4-c7--shrawan-2078-to-bhadra-2082--level`
- **text_en:** "Across 51 monthly NRB BFI snapshots, no material revisions to C4 (Major Financial Indicators) or C7 (Sector-wise Lending) cells were detected. The single classification event was the introduction of a separate residential-personal-home-loan line item in the Saun-2082 snapshot."
- **indicator_slug:** `nrb-bfi--meta--revisions-count`
- **bank_class:** `system_total`
- **period_label:** `Shrawan 2078 → Bhadra 2082`
- **value:** 0
- **unit:** count
- **source_file:** `docs/research/_bfi_workspace/revisions.csv`
- **confidence_grade:** A

---

**Total claim drafts: 30.** All A-grade. All source-cited to a specific staging JSON file or the analytical workspace. When the production schema for `banking_sector_facts` + `claims` is live, these slugs are deterministic — re-running this analysis on the same staging data will produce the same slugs.
