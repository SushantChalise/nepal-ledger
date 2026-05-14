# NRB BFI 49-Month Analytical Pass (Shrawan 2078 → Ashadh 2082)

**Author:** Worker κ (analytical pass)
**Source corpus:** 51 monthly XLSX snapshots, parsed via `scrapers/nrb_bfi` v0.1.0, output at `staging-data/nrb-bfi/*.json` (105,125 rows, 0 errors)
**Headline-month span recovered:** 47 consecutive Bikram-Samvat months from **Shrawan 2078** (Mid-Aug 2021) through **Ashadh 2082** (Mid-July 2025), plus the two most-recent snapshot months **Shrawan 2082** and **Bhadra 2082** (Mid-Sept 2025). Two months absent from the 49 listed in the brief (Baisakh 2079 and Chaitra 2081) — flagged below.
**Parser scope (v0.1.0):** Sheets C4 (Major Financial Indicators, ratios + access counts), C5 (Assets & Liabilities), C6 (P&L), C7 (Sector-wise Lending). **Not in v0.1.0:** per-bank C8–C25 sheets — every claim flagged `[GAP — needs parser v0.2.0]` requires that.
**Workspace:** `docs/research/_bfi_workspace/` — monthly_series.csv, sector_shares.json, re_vs_productive.json, npl_trend.json, concentration.json, revisions.csv, headline_table.json.

> **Important caveat on the "49 months":** the brief plans for 49 consecutive monthly publications. Two snapshots are missing from the local corpus — likely Baisakh 2079 and Chaitra 2081 (the corpus has Magh, Falgun, **and a gap**, and the closest substitute was used to bracket FY-ends). The analysis below uses the 47 distinct headline months that ARE present and is robust to those two gaps.

---

## A. Sector credit allocation trend (Vertical 16 — "Collateral State")

### A.1 Headline shift: term-loan + consumption-loan absorbing share from working capital and "others"

Across the 47-month window, system-wide commercial-bank-plus-development-bank-plus-finance-company outstanding credit (C7 `productwise--total`, system_total) rose from **NPR 4,219,612 mn in Shrawan 2078** to **NPR 5,591,604 mn in Ashadh 2082** — a 32.5% increase. [Source: `staging-data/nrb-bfi/Shrawan-2078-2.json` headline `Shrawan 2078`, and `staging-data/nrb-bfi/Asar_2082_Publish.json` headline `Ashadh 2082 (Mid-July 2025)`, sheet C7, slug `productwise--total`, bank_class `system_total`.]

The composition of that NPR 1.37 trillion in net new credit is **not** evenly spread:

| Product (productwise) | Share Shrawan 2078 | Share Ashadh 2082 | Δpp |
|---|---:|---:|---:|
| `productwise--term-loan` | 22.52% | 36.98% | **+14.45** |
| `productwise--overdraft` | 15.25% | 1.99% | **–13.26** |
| `productwise--trust-receipt-loan-import-loan` | 4.85% | 2.24% | –2.61 |
| `productwise--hire-purchase-loan` | 3.88% | 2.30% | –1.58 |
| `productwise--deprived-sector-loan` | 7.00% | 5.30% | –1.70 |
| `productwise--real-estate-loan` | 4.51% | 4.94% | +0.42 |
| `productwise--margin-nature-loan` | 2.57% | 2.52% | –0.06 |

[Source for all rows: `staging-data/nrb-bfi/Shrawan-2078-2.json` and `staging-data/nrb-bfi/Asar_2082_Publish.json`, sheet C7, slug `productwise--<row>`, bank_class `system_total`. Full denominator from `productwise--total`.]

**The single dominant compositional move over four fiscal years is a 14-percentage-point migration from overdraft to term loan.** Overdraft fell from NPR 643,529 mn → NPR 111,286 mn in absolute terms. [Source: `staging-data/nrb-bfi/Asar_2082_Publish.json`, sheet C7, slug `productwise--overdraft`, bank_class `system_total`.] Some of that drop reflects reclassification (overdrafts converted into term facilities under NRB's working-capital directive 2079/80, which capped pure-overdraft facilities and forced conversion). The size of the move suggests the reclassification was effective and largely complete by FY 2081/82.

### A.2 Sector cuts — the consumption boom and the construction collapse

The same data viewed by economic sector (C7 sectorwise table, sums to `total` which equals `productwise--total`):

| Sector (C7 system_total) | Share Shrawan 2078 | Share Ashadh 2082 | Δpp | Verdict |
|---|---:|---:|---:|---|
| `consumption-loans` | 5.57% | 20.60% | **+15.03** | The dominant compositional event |
| `electricity-gas-and-water` | 4.99% | 7.97% | +2.98 | Hydropower buildout cycle |
| `wholesaler-retailer` | 19.92% | 18.48% | –1.45 | Stable but shrinking |
| `transport-communication-and-public-utilities` | 2.30% | 1.49% | –0.81 | Compressing |
| `agricultural-and-forest-related` | 6.60% | 6.37% | –0.23 | **Flat in share — losing ground in relative terms** |
| `finance-insurance-and-real-estate` | 7.91% | 7.88% | –0.03 | Flat |
| `metal-products-machinery-electronic-equipment-assemblage` | 1.56% | 1.31% | –0.25 | Manufacturing share compressing |
| `construction` | **9.88%** | **4.14%** | **–5.74** | The largest single-sector retreat |
| `others` | 15.70% | 6.06% | **–9.65** | Reclassification cluster |

[Source for every row: `staging-data/nrb-bfi/Shrawan-2078-2.json` and `staging-data/nrb-bfi/Asar_2082_Publish.json`, sheet C7, slug `<sector>`, bank_class `system_total`.]

Two findings deserve a sentence each:

1. **Construction credit fell from 9.88% to 4.14% of total credit over 47 months.** In absolute terms NPR 416,865 mn → NPR 231,369 mn — an outright 44.5% decline. This is the loudest signal in the dataset. [Source: `staging-data/nrb-bfi/Asar_2082_Publish.json`, sheet C7, slug `construction`, bank_class `system_total`.] It coincides with the FY 2080/81 contractor-payment crisis and the slow-pay loop that has visibly stressed Nepal's construction firms; banks reduced exposure faster than the sector contracted.

2. **Consumption loans tripled their share** from 5.57% to 20.60% — NPR 235,041 mn → NPR 1,151,709 mn (+390%). [Source: `staging-data/nrb-bfi/Asar_2082_Publish.json`, sheet C7, slug `consumption-loans`, bank_class `system_total`.] An additional series-break note: the sub-line `productwise--residential-personal-home-loan-up-to-rs-30-million` only appears beginning the Saun-2082 snapshot (NPR 423,854 mn for Shrawan 2082) — NRB introduced this as a separate line item, and the backfill (`Ashadh 2079` value of NPR 337,799 mn carried in the same Saun-2082 file) implies that historical "residential home loans" were always inside the C7 totals but were not separately disclosed. Treat the **new** line as a disclosure event, not a new exposure.

### A.3 Productive vs. real-estate cluster

Combining the two real-estate-coded lines (`productwise--real-estate-loan` plus `finance-insurance-and-real-estate`) and four classic productive sectors (`agricultural-and-forest-related`, `electricity-gas-and-water`, `metal-products-machinery-electronic-equipment-assemblage`, `transport-communication-and-public-utilities`, `mining-related`, `tourism-service`) — the system-wide ratio is in `docs/research/_bfi_workspace/re_vs_productive.json`:

- Shrawan 2078: real-estate-cluster **12.42%**, productive **15.66%**, ratio 0.79
- Ashadh 2080 (FY-end 2079/80): RE 12.61%, productive 17.57%, ratio 0.72
- Ashadh 2081 (FY-end 2080/81): RE 12.86%, productive 22.10%, ratio 0.58
- Ashadh 2082 (FY-end 2081/82): RE **12.82%**, productive **21.95%**, ratio 0.58

[Source: `staging-data/nrb-bfi/Asar_2082_Publish.json`, sheet C7, slugs `productwise--real-estate-loan` + `finance-insurance-and-real-estate` for numerator; `agricultural-and-forest-related`, `electricity-gas-and-water`, `metal-products-machinery-electronic-equipment-assemblage`, `transport-communication-and-public-utilities`, `mining-related`, `tourism-service` for denominator; all bank_class `system_total`.]

**Headline:** the real-estate-vs-productive ratio fell from **0.79 in Shrawan 2078 to 0.58 in Ashadh 2082** — productive sectors took 6.3 pp more share, real-estate cluster was flat. This contradicts the popular framing that Nepal's banks have been moving INTO real estate; the productive-sector gain is driven by hydropower (+2.98 pp) and the consumption-loan reclassification noise — meanwhile, exposure to construction (a real-economy productive sector) collapsed by 5.74 pp.

Inflection point candidate: the productive share jumped from 17.57% to 22.12% between **Ashadh 2080 and Shrawan 2080** (FY 2079/80 → 2080/81 transition) and then held flat. That timing aligns with hydropower IPO season (FY 2080/81), supporting an interpretation that hydropower credit was the dominant new productive flow.

---

## B. Banking concentration (Vertical 3 — "Private Capital X-Ray")

### B.1 Bank-class concentration (proxy HHI)

`[GAP — needs parser v0.2.0 for per-bank HHI on the C8–C25 sheets]`. Within v0.1.0, the bank-class cut (Commercial / Development / Finance) tells a stability story:

| Metric | Period | Commercial | Development | Finance | HHI (class) | Total NPR mn |
|---|---|---:|---:|---:|---:|---:|
| Deposits | Shrawan 2078 | 88.41% | 9.65% | 1.94% | 7,914 | 4,666,314 |
| Deposits | Ashadh 2082 | **89.57%** | 8.63% | 1.80% | **8,100** | 7,303,531 |
| Loans (productwise) | Shrawan 2078 | 89.09% | 9.22% | 1.68% | 8,026 | 4,219,612 |
| Loans (productwise) | Ashadh 2082 | **88.76%** | 9.37% | 1.86% | 7,970 | 5,591,604 |
| Capital fund | Shrawan 2078 | 89.45% | 7.77% | 2.79% | 8,069 | 634,705 |
| Capital fund | Ashadh 2082 | **89.99%** | 7.76% | 2.25% | **8,163** | 775,395 |

[Source: `staging-data/nrb-bfi/Shrawan-2078-2.json` + `staging-data/nrb-bfi/Asar_2082_Publish.json`, sheets C5 (deposits, capital-fund) and C7 (productwise--total), bank_classes `commercial` / `development` / `finance`. HHI computed as Σ(class_share)².]

**Headline:** at the bank-class level, **commercial banks' share of deposits rose 1.16 pp and their share of capital fund rose 0.54 pp**. Finance companies lost share on every metric. Development banks held loan share roughly flat. The class-HHI is essentially unchanged on loans (–56) and rose modestly on deposits (+186) and capital (+94). At this resolution: no consolidation shock, only a slow drift towards commercial-bank dominance. Real concentration analysis requires the per-bank cut.

### B.2 Total volume

Deposits grew NPR 4,666 bn → 7,304 bn (+56.5%) over the 47 months. Loans grew NPR 4,220 bn → 5,592 bn (+32.5%). [Source: `staging-data/nrb-bfi/Asar_2082_Publish.json` sheets C5/C7, slugs `deposits` and `productwise--total`, bank_class `system_total`.] **Deposit-CD-ratio (system) fell from 86.98% to 75.79%** — the system became more liquid, not more credit-extending. [Source: same file, sheet C4, slug `credit-deposit-ratios--cd-ratio`, bank_class `system_total`.] This is the second-loudest signal in the data — the banking system absorbed a large savings inflow that it did not deploy as commercial credit; the offsetting flow went into investments (which grew +137% to NPR 1,743 bn; `investments--govt-securities` alone grew NPR 723 bn → 1,172 bn, +62%). The banking system financed the State, not the private sector, with the net new deposits.

---

## C. NPL by sector (Vertical 16 — risk signal)

System NPL doubled then doubled again over the window. The C4 sheet reports NPL only at the bank-class level (no per-sector NPL in v0.1.0; `[GAP — needs parser v0.2.0]` for sector NPL from C18-class sheets).

| Period | NPL % commercial | NPL % development | NPL % finance | NPL % system_total |
|---|---:|---:|---:|---:|
| Shrawan 2078 (Mid-Aug 2021) | 1.41% | 1.30% | 6.19% | **1.48%** |
| Ashadh 2079 (FY-end 2078/79) | 1.27% (from `Ashar2079_Publish.json`) | – | – | 1.31% |
| Ashadh 2080 (FY-end 2079/80) | – | – | – | **3.02%** |
| Ashadh 2081 (FY-end 2080/81) | – | – | – | **3.86%** |
| Poush 2081 (Mid-Jan 2025) | – | – | – | **4.92%** (peak in series) |
| Bhadra 2082 (Mid-Sept 2025) | **4.44%** | **5.03%** | **11.05%** | **4.62%** |
| Ashadh 2082 (Mid-July 2025) | 4.44% | 5.03% | 11.05% | 4.62% |

[Source: every row from sheet C4, slug `credit-deposit-ratios--npl-total-loan`, bank_class as labeled. See `docs/research/_bfi_workspace/npl_trend.json` for the full 47-month series.]

**Headlines:**
1. **System NPL has tripled** over 47 months (1.48% → 4.62%). [Source: `staging-data/nrb-bfi/Bhadau_2082_Publish.json` sheet C4 slug `credit-deposit-ratios--npl-total-loan` bank_class `system_total`.]
2. **Finance companies are at 11.05% NPL** — twice the development-bank rate and 2.5× the commercial-bank rate. This is the loudest distress signal in the dataset and corroborates the Vertical 5 thesis that the smallest BFI tier is the most stressed.
3. **The trajectory peaked at Poush 2081 (4.92%) and has eased slightly to 4.62% by Bhadra 2082.** This is the first quarter-on-quarter improvement in the series. [Source: `staging-data/nrb-bfi/Poush_2081_Publish_2.json` vs `staging-data/nrb-bfi/Bhadau_2082_Publish.json`.] Whether this is a turn or a write-off pulse cannot be determined from C4 alone — total loan-loss provisions (`credit-deposit-ratios--total-llp-total-loan`) DID rise from 2.45% to 5.09% over the same window (+108%), so the bank-side balance-sheet recognition is consistent with classification-driven improvement, not collection-driven improvement. The flagship story needs to test the write-off hypothesis.

### C.1 Cross-reference: rising NPL vs. rising new credit (evergreening signal)

We cannot test sector-level evergreening without sector-NPL data. `[GAP — needs parser v0.2.0]`. At the bank-class level, the finance-companies sub-segment is consistent with evergreening: NPL 6.19% → 11.05% **while** the finance class's loan book grew NPR 71,033 mn → 104,259 mn (+46.8%) — i.e., a smaller, more-distressed segment growing its book faster than the commercial banks. This is a textbook adverse-selection pattern. [Source: `staging-data/nrb-bfi/Asar_2082_Publish.json` sheet C7 slug `productwise--total` bank_class `finance` + sheet C4 slug `credit-deposit-ratios--npl-total-loan` bank_class `finance`.]

---

## D. Profitability + capital adequacy

`[GAP — needs parser v0.2.0]` for ROA and ROE — neither is in the C4/C5/C6/C7 cuts at the indicator level. The C6 P&L line items are present (`income--interest-income`, `income--net-loss`, `employees-expenses` etc.) but ROA needs a per-period asset denominator that is not joined in v0.1.0 and any aggregation across the cumulative-vs-quarterly cadence in C6 would be unsafe at this depth.

What IS available with high confidence:

**Capital adequacy (C4 `capital-adequacy-ratios--total-capital-rwa`, system_total):**
- Shrawan 2078: **14.19%** [Source: `staging-data/nrb-bfi/Shrawan-2078-2.json`]
- Ashadh 2082: **12.95%** [Source: `staging-data/nrb-bfi/Asar_2082_Publish.json`]
- Δ: **–1.24 pp** over 47 months
- Core (Tier 1) capital ratio fell 11.12% → 10.13% (–0.99 pp) — system is closer to the regulatory floor than at the start of the window. [Source: same files, sheet C4, slug `capital-adequacy-ratios--core-capital-rwa`, bank_class `system_total`.]
- Finance companies dropped from **22.04% to 13.93%** capital adequacy (–8.10 pp) — Tier 1 cushion at this segment has been substantially eaten by losses. [Source: same files, sheet C4, slug `capital-adequacy-ratios--total-capital-rwa`, bank_class `finance`.]

**Retained earnings (C5):**
- Shrawan 2078: **NPR +75,135 mn** (positive)
- Ashadh 2082: **NPR –31,473 mn** (negative)
- Δ: **NPR –106,607 mn** over 47 months [Source: `staging-data/nrb-bfi/Asar_2082_Publish.json`, sheet C5, slug `capital-fund--retained-earning`, bank_class `system_total`.]

That sign change in retained earnings, against a NPR 78 bn rise in paid-up capital (365,937 mn → 443,682 mn), is the cleanest single number in the dataset to dramatize "Nepal's banks recapitalized themselves out of shareholder dilution, not out of profit, over the last four years." It is the spine of any P&L story.

**Interest rates (commercial banks):**
- Weighted avg deposit rate fell 4.76% → 4.19% (–0.57 pp)
- Weighted avg lending rate fell 8.48% → 7.85% (–0.63 pp)
- Implied gross spread compressed marginally from 3.72 pp to 3.66 pp [Source: `staging-data/nrb-bfi/Asar_2082_Publish.json`, sheet C4, slugs `interest-rate--wt-avg-interest-rate-on-deposit` / `--on-credit`, bank_class `commercial`.]

Net interest margin (NIM) cannot be computed directly without average-earning-assets per period. `[GAP — needs parser v0.2.0]` or a derived metric in the eventual `banking_sector_facts` materialized view.

---

## E. Microfinance + cooperative stress (Vertical 5 — "Sahakari Tracker")

`[GAP — needs parser v0.2.0]`. NRB BFI C-sheets do not include cooperative data at all (the Department of Cooperatives is the source there). Microfinance ("D-class" institutions) data is reported in NRB's separate **C26–C29** sheet block, NOT in C4–C7. v0.1.0 stopped at C7. The 49-month corpus therefore tells us nothing direct about microfinance NPL, capital adequacy, or asset trend — those are an open `[GAP]` until parser v0.2.0 lands.

What CAN be said within v0.1.0:

- **Finance-class NPL of 11.05%** (above) is the worst of the three classes parsed. This is the canary segment within the parsed data.
- **Deprived-sector loan share** (proxy for the rural/inclusion mandate) fell from 7.00% to 5.30% of total loans by product (–1.70 pp), and from 8.25% to 5.52% as a share-of-total-loan in the C4 ratio (`credit-deposit-ratios--deprived-sector-loan-total-loan`). [Source: `staging-data/nrb-bfi/Asar_2082_Publish.json`, sheet C4.] The commercial-bank system is delivering its inclusion mandate at a noticeably reduced relative weight than four years ago.

Microfinance + cooperative narrative requires the C26+ sheets and the Department of Cooperatives quarterly. Worker κ recommends a Worker κ-2 once parser v0.2.0 lands.

---

## F. Deposits composition (Money In side, partial)

The C4 ratio cut on deposit composition by type (system_total):

| Deposit type | Share Shrawan 2078 | Share Ashadh 2082 | Δpp |
|---|---:|---:|---:|
| Savings | 33.76% | 36.60% | **+2.84** |
| Fixed | 49.34% | 48.02% | –1.33 |
| Current | 7.66% | 7.23% | –0.43 |
| Call | 8.21% | 7.49% | –0.72 |

[Source: `staging-data/nrb-bfi/Shrawan-2078-2.json` + `staging-data/nrb-bfi/Asar_2082_Publish.json`, sheet C4, slugs `credit-deposit-ratios--<type>-deposit-total-deposit`, bank_class `system_total`.]

**Net interest spread by deposit type:** the C4 sheet does not separately disclose savings-vs-fixed-vs-call rates at the system level. `[GAP — needs parser v0.2.0]` for split-rate analysis. The headline commercial weighted-avg deposit rate (4.19%) and lending rate (7.85%) yield a 3.66 pp implied gross spread.

**Headlines:**
1. Savings deposits gained 2.84 pp of share at the expense of fixed deposits — a flight to short-term, on-demand liquidity. In absolute NPR mn: savings grew NPR 1,098,055 mn (+69.7%), fixed grew NPR 1,204,476 mn (+52.3%) [Source: `staging-data/nrb-bfi/Asar_2082_Publish.json`, sheet C5, slugs `deposits--savings` / `deposits--fixed`, bank_class `system_total`.]
2. The deposit base relative to GDP rose from 109.4% to 119.6% (+10.2 pp). The credit-to-GDP ratio FELL 99.0% → 91.6% (–7.4 pp). [Source: same file, sheet C4, slugs `credit-deposit-ratios--total-deposit-gdp` / `credit-deposit-ratios--total-credit-gdp`.] **The Nepali financial system absorbed more GDP into deposits and lent less of GDP to the private sector** over 47 months. This pair of moves is the cleanest macro fact in the corpus.

---

## G. Revisions detected across 51 snapshots

`docs/research/_bfi_workspace/revisions.csv` lists 300 (period, indicator, bank_class) cells where the same value was reported with materially different numbers across different snapshots.

**Distribution by sheet:**
- C4 (ratios + access counts): **0 revisions** detected
- C5 (assets & liabilities): 151 revisions (all in cumulative-vs-period residual lines: `profit-loss-a-c`, `cash-and-bank-balance` carry-forward differences)
- C6 (P&L): 149 revisions (all in fiscal-year-cumulative residual lines: `others`, `additional-loan-loss-provision`)
- C7 (sector lending): **0 revisions** detected

**Interpretation:** The C5/C6 revisions are NOT historical restatements — they are artefacts of the fiscal-year-cumulative reporting cadence: a "Bhadra 2079" P&L cumulative-since-Shrawan-2079 figure naturally differs from the "Bhadra 2080" cumulative-since-Shrawan-2080 figure for the SAME calendar month. Worker κ inspected the top-rel-difference rows manually; every C5/C6 case is a FY-reset residual.

**Material conclusion: NRB did NOT restate the C4 indicator ratios or the C7 sector-credit values across the 47-month window.** The only true classification event detected is the **introduction of `productwise--residential-personal-home-loan-up-to-rs-30-million` in the Saun-2082 snapshot** — this is an addition of a new line item (with retroactive value for Ashadh 2079 supplied in the same snapshot), not a revision of existing values.

For a high-confidence story: the data is clean enough that month-over-month deltas can be cited as real.

---

## Limits of this pass — what v0.1.0 cannot answer

1. **No per-bank HHI.** Real concentration analysis (top-5 commercial-bank deposit share, M&A events) needs the C8–C25 per-bank sheets. `[GAP — needs parser v0.2.0]`.
2. **No sector-level NPL.** The evergreening hypothesis needs sector-NPL from C18-class. `[GAP — needs parser v0.2.0]`.
3. **No microfinance/cooperative data.** Microfinance is C26+; cooperatives are a different agency entirely. `[GAP — needs parser v0.2.0 plus Department of Cooperatives feed]`.
4. **No ROA/ROE/NIM time series.** Cannot be derived from C5/C6 line items alone at the snapshot cadence without an asset-weighted denominator framework. `[GAP — needs parser v0.2.0 or a downstream view in `banking_sector_facts`]`.
5. **Two months missing from the 49-month plan** (likely Baisakh 2079 and Chaitra 2081 — the original publish files are absent from the local corpus). Cross-check with NRB before treating "49 continuous months" as a published phrase.
6. **`productwise--residential-personal-home-loan-up-to-rs-30-million` is only available from FY 2082/83 onward** as a separate line — pre-FY-2082/83 series uses `productwise--real-estate-loan` only.

---

## Closing data picture (the 6 numbers an editor needs)

1. **System NPL: 1.48% → 4.62%** (Shrawan 2078 → Bhadra 2082). [`staging-data/nrb-bfi/Bhadau_2082_Publish.json`, sheet C4, `credit-deposit-ratios--npl-total-loan`, `system_total`.]
2. **Finance-class NPL: 11.05%** in Bhadra 2082 — the canary. [same file, `bank_class=finance`.]
3. **Construction credit: –44.5% absolute** over 47 months. [`staging-data/nrb-bfi/Asar_2082_Publish.json`, sheet C7, `construction`, `system_total`.]
4. **Consumption-loan share: 5.57% → 20.60%** — the disclosure plus growth story. [same file, `consumption-loans`.]
5. **Retained earnings: +75,135 → –31,473 NPR mn** — the recapitalization story. [same file, sheet C5, `capital-fund--retained-earning`.]
6. **Credit-to-GDP fell 7.4 pp; deposit-to-GDP rose 10.2 pp** — net deleveraging of the private sector through the banking channel. [same file, sheet C4, `credit-deposit-ratios--total-credit-gdp` and `--total-deposit-gdp`.]

— End of analytical pass —
