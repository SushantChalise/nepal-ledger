# Nepal Ledger — Master Plan v5 (The Integrated Vision)

> Four iterations to find the answer. v1 was too generic. v2 was too narrative. v3 was too sprawling. v4 was too minimal. v5 is the integration.

---


## The Master Thesis

> **Nepal does not lack money. Nepal lacks conversion. Nepal Ledger tracks whether money becomes wealth.**

The longer version:
> Nepal is not poor because money does not enter the country. Nepal is poor because money enters, leaks, gets captured, speculates, imports, or exits before it becomes productive capital. The state borrows future obligations to sustain present stability — debt that gets more expensive every year the currency weakens and capital spending fails to generate returns. The money that does circulate domestically funnels into a small number of family-controlled business groups that own the banks, the importers, the FMCG brands, the listed equity, and the real estate simultaneously. The capital that does get built is regularly destroyed — by floods, landslides, glacial lake outbursts, and earthquakes. And underneath all of this sits the country's primary physical asset — its land — utilized for rent-seeking rather than production. Yet there are places where money *does* compound — quietly exporting software, processing cardamom, generating hydroelectricity, formalizing into export-grade industry. Nepal Ledger tracks both: the leakage and the conversion.

The six questions Nepal Ledger asks repeatedly:
> **(1) Where does Nepal's money go — and does any of it become productive?**
> **(2) What is the future paying to keep the present stable?**
> **(3) Who captures the rupees that do circulate — and what do they do with them?**
> **(4) How much of what we build do we lose, and at what hidden cost?**
> **(5) What could Nepal's land produce — and why isn't it producing it?**
> **(6) Where is money actually compounding — and how can Nepal do more of that?**

The single answer Nepal Ledger builds toward:
> **Nepal's first money-intelligence layer: visualizing how every rupee enters, moves, leaks, gets captured, and becomes — or fails to become — productive national wealth.**

---

## The Differentiation (Why This Will Work)

**Nepal's media gap is not data — it is data-driven visual narrative.**

- NRB publishes numbers in PDFs nobody reads.
- News sites publish text with stock photos.
- Khabarhub, Setopati, OnlineKhabar do not do data viz.
- Academic economists publish papers no one cites publicly.
- World Bank / IMF publish dashboards that don't tell Nepal's story.

**No one in Nepal does what NYT Upshot, FT Visual Journalism, Bloomberg Quint, Our World in Data, The Pudding, and Reuters Graphics do for their markets.**

That is the entire opportunity. Visual narrative + rigorous data + Nepal-specific institutional knowledge = a category nobody else owns.

**The visual standard:**
- Every chart argues a point, not just shows a number
- Every flow diagram is sourced, confidence-labeled, and beautiful
- Every entity page is a multi-panel infographic, not a wiki article
- Every story is built around a hero visualization, not just text + thumbnail
- D3 + Recharts + animated transitions where they earn their cost
- Mobile-first because 70% of Nepal's web traffic is mobile

That is the moat.

---

## The Three Products + One Channel

```
                  ┌─────────────────────────────────────────────┐
                  │             ARTHIK NEPAL                    │
                  │   "Where does Nepal's money go?"            │
                  └─────────────────────────────────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
   ┌────▼─────┐                  ┌─────▼──────┐                ┌──────▼──────┐
   │  PULSE   │                  │  STORIES   │                │ KNOWLEDGE   │
   │  (live)  │◄────links into──►│ (monthly)  │◄──leaves behind┤    BASE     │
   │          │                  │            │                │ (permanent) │
   └────┬─────┘                  └─────┬──────┘                └──────┬──────┘
        │                              │                              │
        └──────────────────────────────┼──────────────────────────────┘
                                       │
                              ┌────────▼─────────┐
                              │     YOUTUBE      │
                              │ (talks about all)│
                              └──────────────────┘
```

### Product 1 — THE PULSE (live-ish data layer)

The "habit loop." Updated as fresh as the data allows.

**The Money Map** (D3 Sankey/flow visualization)
- Where money enters Nepal (remittance, exports, tourism, digital services exports (often informal channels), foreign loans, foreign grants, FDI)
- Where it circulates (banks, government — federal AND the 753 local units, cooperatives, real estate, public enterprises, private business groups, **smallholder agriculture**)
- Where it concentrates (the Money Funnel sub-view — household and bank rupees pooling into the top 15 business groups; fertile valleys consolidating into developer land banks)
- Where it leaks (imports — including **food, timber, furniture that Nepal could produce**; education abroad; Hundi; debt service; profit repatriation; tourism platform fees + imported tourist comforts; cross-border price arbitrage)
- Where it gets stuck (real estate, NPLs, unspent capital from foreign loans, frozen cooperatives, **dead-capital forest cover under regulatory limbo**)
- Where the future pays for the present (debt service flowing out vs. loans flowing in — the gap is the silent burden)
- Where capital is destroyed (monsoon damage, GLOF damage, earthquake damage, **flood-destroyed standing crops** — the climate tax)
- **Where the land could produce but isn't** (Soil Economy gap — high-value crop opportunity unrealized; spatial misallocation)
- Productive vs. rentier split (gross fixed capital formation by sector — what fraction is becoming exportable industry / energy / technology / digital services / certified agricultural exports vs. being recycled into real estate / imports / FMCG)
- Updated monthly when NRB CMEFs releases; numbers sourced; confidence-labeled
- Each flow node links to its Knowledge Base page

**Macro Pulse cards** (8–10 KPIs — including the Borrowed Time row)
- Inflation YoY (NRB CMEFs)
- Remittance inflow (NRB)
- Forex reserves (months of import cover, NRB)
- Capital expenditure execution (% of budget, FCGO)
- Trade deficit (Customs)
- **Debt-to-GDP ratio** (PDMO)
- **Debt service / revenue ratio** — the burden number (PDMO + FCGO)
- **NPR/USD** with rolling 12-month depreciation % (NRB)
- NEPSE index (live)
- Fuel price (NOC)

Each card shows: current value, vs. last period, vs. last year, and links to the indicator's permanent knowledge base entry.

**Vertical mini-pulses**
- Price Chain + Border (Kalimati prices, Day on Day; one border-arbitrage price diff this week)
- Public Enterprise Health (rotating spotlight)
- Sahakari Crisis Recovery (frozen deposits status)
- Hydropower + Climate Exposure (installed capacity, generation, export revenue, monsoon damage tally YTD)
- Borrowed Time (latest loan signing + currency-driven debt-stock growth this month)
- Private Capital Concentration (banking + NEPSE top-10 share + rotating group spotlight)
- Capital Formation vs. Consumption (productive vs. rentier vs. consumption split, net of capital destruction)
- Tourism Pulse (latest month arrivals + estimated leakage %)
- Digital Export Pulse (estimated quarterly IT services exports + freelancer FX inflow proxy)
- Local Ledger spotlight (one of the 753 units — grant disbursed vs. capex executed vs. recurrent overhead)
- **Soil Economy Pulse** (Agri-Import Tally MTD + Land Sprawl alert if any fertile-valley conversion this month + rotating Crop Opportunity)

### Product 2 — THE STORIES (narrative deep-dives)

The "authority" layer. **Monthly cadence — authority density over volume.**

**Two story types per month:**

1. **Flagship long piece** (1/month, alternating investigation ↔ explainer; quarterly the flagship is a marquee investigation taking 4–6 weeks) — original research, sources, the "Why Farmers Get Rs 25 and You Pay Rs 125" type. Builds reputation.

2. **Short explainer** (1/month) — "How does NOC set fuel prices?", "What is BOP?", "How does monetary policy actually work in Nepal?" Builds understanding.

Total: **12 flagship pieces + 12 short explainers per year.** No weekly publishing. No reaction-piece treadmill — reactions to data drops live inside the Monthly Verdict, not as separate stories.

Every flagship story = an article + a video + a visualization + 2–4 permanent Knowledge Base entries.

### Product 3 — THE KNOWLEDGE BASE (permanent encyclopedia — the moat)

Built up story by story. After 5 years, nobody can copy it without 5 years of work.

**Four collections:**

1. **Entities** — NOC, NEA, NAC, NTC, FMTCL, SalT, ADBL, RBB, NBL, Nepal Water Supply, EPF, CIT, SSF, and major private actors. Each is a multi-panel infographic page (not a wiki article): mandate, financials over time, governance, controversies, public impact, citizen relevance.

2. **Indicators** — NCPI, remittance, forex reserves, BOP, capital expenditure, public debt, NPL, etc. Each has: plain-language definition, full history chart, method note, why it matters, what would change it, related indicators.

3. **Concepts (Glossary)** — Hundi, Sahakari, NRB, monetary policy, capital expenditure, NEPSE, RERA equivalent, repatriation rules, FDI tiers. Each in 200–400 words with "see also" links.

4. **Money Flows** — every node of the Money Map has its own page: "Education outflow → where it goes, how much, why" etc.

### The Channel — YOUTUBE + The Short-Form Distribution Engine

YouTube is the **long-form layer**. The short-form engine — Shorts, Reels, TikTok, Instagram carousels, LinkedIn posts, X threads — is the **acquisition layer** that brings new audiences in. Both are distribution for the website's canonical content. No standalone short-form concepts in Year 1; every short-form piece is downstream of a long video, a flagship story, a Knowledge Base entry, or a calculator.

#### Long-form cadence: 3 long videos/month
- 1 **Monthly Pulse video** (~10 min, accompanies the Monthly Verdict release)
- 1 **Flagship video** (12–15 min, accompanies the month's flagship story)
- 1 **Short explainer** (~8 min, concept from glossary or an entity profile)

**Bilingual:** Monthly Pulse + flagship video each get a Nepali version 1 week after the English. Short explainers are produced English-only in Year 1; vernacular distribution scales in Year 2 with the Migrant Money School vertical.

#### Short-form formats (the discovery layer)

| # | Format | Length | Where it lives | Cadence |
|---|--------|--------|----------------|---------|
| 1 | **The Number** — open with a shocking number; brief reveal; CTA to full story | 15–30s | Shorts / Reels / TikTok | 2/week |
| 2 | **One Chart, One Sentence** — single chart with text overlay; argues one point | 15–30s | All vertical + X | 1/week |
| 3 | **Myth vs. Reality** — two-panel format; quick voice-over | 30–60s | All vertical | 2/month |
| 4 | **30-Second Explainer** — one glossary concept (BOP, monetary policy, related-party lending, *kittakat*) | 30s | All vertical | 1/week |
| 5 | **Compare Two Numbers** — side-by-side (debt service vs. capex, etc.) | 15–30s | All vertical | 1/week |
| 6 | **Follow the Rupee** — animated money flow following one rupee from origin to destination | 60–90s | All vertical | 1/month (high production) |
| 7 | **Household Math** — *"Rs 10,000 last year vs. Rs 10,000 today — here's what changed"* | 60s | All vertical + Instagram carousel | 2/month |
| 8 | **What Just Happened?** — reaction to a new data release or event | 30–60s | All vertical | 1–2/month (data-driven) |
| 9 | **Did You Know** — surprising fact from the Knowledge Base | 15–30s | All vertical | 2/week |
| 10 | **Carousel** — 5–10 slide explainer (Instagram + LinkedIn) | static deck | Instagram, LinkedIn | 1/week |
| 11 | **Quote / Claim Graphic** — single shareable image with a striking claim | static | All static | 2/week |
| 12 | **Map Moment** — animated time-lapse (land use, border arbitrage, etc.) | 30–60s | All vertical | 1/month (high production) |

#### Cross-platform packaging per flagship story

Every flagship story (one per month) ships not just as a video, but as a full distribution package:

```
Monthly Flagship Story (e.g., "Why Every Foreign Loan Costs More Than the Day You Signed It")
  ├── Long-form article on site (2,500–3,500 words)
  ├── YouTube long video (12–15 min)
  ├── Bilingual: Nepali version (1 week later)
  ├── 4–6 Shorts/Reels/TikTok (formats 1, 2, 5, 8, 9)
  ├── 1 Instagram + LinkedIn carousel (format 10)
  ├── 1 quote/claim graphic for each of the 3–5 key claims (format 11)
  ├── 1 X/Twitter thread (5–10 tweets, charts + key claims)
  ├── 1 LinkedIn long post + carousel (for diaspora professional reach)
  ├── 1 audio-only podcast version (for Spotify / Apple Podcasts)
  └── 1–2 newsletter sections (cross-link with full story)
```

#### Realistic Year 1 short-form output

Tied to actual production capacity (one operator, 25 hrs/week):

- **~150 short videos** (Shorts/Reels/TikTok, ~3/week)
- **~50 carousels** (Instagram + LinkedIn, ~1/week)
- **~50 X/Twitter threads** (1/week, aligned with stories + Monthly Verdict)
- **~100 quote/claim graphics** (2/week)
- **~12 audio-podcast episodes** (one per flagship story)
- **~12 Monthly Pulse threads** on X tied to the Monthly Verdict release

**Total Year 1 short-form output: ~350+ pieces, all downstream of ~36 long videos + 12 flagship articles + Knowledge Base entries.** Production cost per short: 15–45 minutes on average. Discoverability impact: 10–50× the reach of long-form alone.

#### The non-negotiable rule

**No short-form piece is created in isolation.** Every short must point back to a canonical asset on the site (story, entity, indicator, calculator, glossary, money flow). The short-form engine is acquisition + retention, never the product. If a short cannot link to something deeper, it shouldn't ship.

---

## The Public Communication Layer — 5 Master Pillars (Wrapping the 17 Internal Verticals)

**The honest operational problem:** 17 internal verticals + 12 structural forces + 6 master questions is intellectually correct but cognitively impossible for a first-time visitor. The Lenses system handles audience clutter at the UI level; this section handles narrative clutter at the language level.

**Internal architecture (operator-facing):** 17 verticals, 12 forces, 6 questions — the editorial machinery, used to assign stories, build the Knowledge Base, and structure data ingestion.

**External communication (audience-facing):** 5 pillars. Every story, video, and Pulse update is tagged with which pillar it serves. The audience learns 5 categories. The operator works with 17.

| # | Public Pillar | What it asks | Internal verticals it draws from |
|---|---------------|--------------|----------------------------------|
| 1 | **Money In** | What is Nepal earning from the world? | Money Pulse, Diaspora Capital, Digital Export Boom, Tourism Value Chain, parts of Soil Economy (export crops) |
| 2 | **Money Out** | What is leaving Nepal, and why? | Borrowed Time (debt service), parts of Tourism (leakage), Price Chain + Border (cross-border arbitrage), education outflow, Hundi, Imports, Profit Repatriation |
| 3 | **Money Captured** | Who is pocketing the rupees that do circulate? | Private Capital X-Ray, Public Enterprise X-Ray, Sahakari Tracker, Credit Allocation, parts of Soil Economy (land banking) |
| 4 | **Money Wasted or Destroyed** | Where does productive capital fail to form or get destroyed? | Budget Watch + Local Ledger (capex failure), Climate Tax lens (destruction), Public Enterprise X-Ray (operating losses), failed loan-funded projects (Borrowed Time × Budget Watch) |
| 5 | **Where Money Becomes Wealth** | Where is wealth actually being built — and how can we do more of it? | Hydropower Monitor, Digital Export Boom, Soil Economy (export-grade crops, community forestry NTFPs), well-executing municipalities, formalized SMEs, Productive Escape stories |

**Why this works:**
- A first-time visitor learns 5 categories in 30 seconds.
- Every story, video, and Knowledge Base entry has a pillar badge — visible filtering across the platform.
- Newsletter sections follow the 5 pillars; YouTube playlists follow the 5 pillars; the Monthly Verdict is structured by the 5 pillars.
- Internally, editors still work in the 17 verticals where the data and entity rigor lives.

**The narrative spine of every monthly newsletter and every Year-end Review:**
> Nepal received [Money In]. Some of it left [Money Out]. Some was captured [Money Captured]. Some was destroyed or wasted [Money Wasted]. And some — too little — became wealth [Where Money Becomes Wealth].
> Did Nepal grow this month, or did it survive another month?

---

## The Monthly Verdict (The Habit Loop)

**The honest version of the "monthly ritual" idea.** An earlier draft of this plan proposed a 0–100 *Wealth Conversion Score* combining seven subscores. After first-principles review, that idea was killed:

- Composite scores imply precision Nepal's data cannot deliver (FCGO is preliminary, NSO lags 18+ months, PDMO is quarterly — combining them into a monthly point estimate is false clarity).
- A score is the cheapest feature in the plan to copy; competing "Nepal Economic Scores" would commoditize the platform's most visible product while the deep dossiers remain uncopyable.
- A score contradicts the platform's own thesis: Nepal does not lack indicators. It lacks *understanding*. Producing another indicator solves the wrong problem.
- A score creates a permanent methodology defense burden; business groups and government economists will pressure-test the weights every month, and the platform will spend more time defending the formula than doing journalism.
- The world's best economic journalism (FT, Economist, NYT Upshot, Our World in Data) does not use composite scores. It synthesizes via prose and signature visualizations.

**What replaces it: The Monthly Verdict.**

A single sharp prose paragraph, published with each NRB CMEFs release, structured by the 5 Public Pillars. No number. No subscore stack. No methodology surface to attack. Just synthesis — the work a thinking editor does.

**Format:**
> *"Chait 2082. Remittance kept rising; trade deficit widened almost as fast. NEA's annual debt service crossed Rs X billion this month — and Pokhara Regional Airport entered its fourth year of underutilization. The Sahakari Recovery Committee restored Rs Y crore to depositors of three cooperatives, but eleven of the largest troubled institutions remain frozen. The high-value crop story this month: Ilam's large cardamom exports cleared Rs Z. Money entered Nepal. Most did not compound."*

**Why a paragraph beats a number:**
- A paragraph cannot be copied. The next platform's paragraph will be different — and worse, because they don't have our dossiers.
- A paragraph names specifics. "NEA debt crossed Rs X" is checkable; "42/100" is opaque.
- A paragraph trains readers to think structurally (5 pillars are baked into the prose).
- A paragraph is republishable: newsletter intro, video opener, social media thread, podcast lead.

**The habit loop:** readers return on the 25th of each month for The Monthly Verdict, the Monthly Pulse video, one new entry in the Loan→Project Tracker, the latest Sahakari recovery movement, and that month's flagship investigation. These are real hooks, not synthetic ones.

---

## The 17 Flagship Verticals (Internal Operating Structure)

(Externally, these collapse into the 5 Public Pillars above.)

Each vertical lives at the intersection of Pulse + Stories + Knowledge Base.

| # | Vertical | Pulse component | Knowledge Base | First story |
|---|----------|----------------|----------------|-------------|
| 1 | **Nepal Money Pulse** | Macro KPI cards + Money Map | All indicators | "How Nepal's Economy Actually Works" (Story #1) |
| 2 | **Borrowed Time (Debt Watch)** | Debt-to-GDP, debt service / revenue, currency exposure %, latest loan signings, NPR depreciation tracker | Donor entity profiles (ADB, World Bank, IMF, JICA, EXIM China, EXIM India), loan-funded project audits, debt service history | "Why Every Foreign Loan Costs More Than the Day You Signed It" |
| 3 | **Private Capital X-Ray** | Banking concentration, NEPSE concentration, FMCG category concentration, real estate developer concentration | ~15 business group profiles, ~20 commercial bank profiles, major listed company profiles, cross-ownership map | "Who Owns the Rupee You Just Spent?" |
| 4 | **Public Enterprise X-Ray** | Rotating spotlight tile | Entity profiles (NOC, NEA, NAC, NTC, FMTCL...) | "The Company Behind Every Fuel Price Hike" (NOC) |
| 5 | **Sahakari Tracker** | Frozen-deposit status tile + "Check your cooperative" search | Cooperative database (regulatory status, directors, exposure) | "How Nepal's 'People's Banks' Stole the Poor's Savings" |
| 6 | **Follow the Rupee** | Featured visual flow | "Rupee Journey" diagrams for major flows | "Why Farmers Get Rs 25 and You Pay Rs 125" |
| 7 | **Price Chain Nepal + Border Economy** | Daily Kalimati prices, markup %, cross-border price differentials (fuel, fertilizer, FMCG: NP vs. IN), peg-driven arbitrage flows | Commodity-by-commodity price-chain maps, border district price comparisons, INR-NPR peg explainer | "Who Captures the Margin Between Farmer and Plate?" |
| 8 | **Tourism Value Chain** | Arrivals + receipts + per-tourist spend + leakage % (foreign-captured share of a tourist dollar) | Trekking corridor economies (Annapurna, Everest, Langtang, Manaslu), Kathmandu hospitality sector map, NTB / TAAN / TIMS data | "Where Does a $1,500 Trek Actually Go? Mapping the Annapurna Rupee" |
| 9 | **Digital Export Boom** | IT services export estimate, formal vs. informal channels, freelancer FX inflows (Payoneer, etc.), top employers | IT services firm profiles (LeapFrog, Cotiviti, Verisk, Deerwalk, F1Soft, CloudFactory, eSewa Genese, game/animation studios), freelancer ecosystem map, regulatory environment | "Nepal's Quietest Export: How Code Crosses the Border" |
| 10 | **Budget Watch + Local Ledger (753)** | Federal capex execution + a rotating local-government spotlight (one of the 753 units) showing federal grants disbursed vs. local capex executed vs. recurrent overhead | Ministry-by-ministry federal execution; sampled municipal budgets and audit observations; NNRFC grant allocation tracking | "Nepal Has the Budget. Why Doesn't It Build?" — followed by "What Did Your Municipality Do With Your Money?" |
| 11 | **Hydropower Monitor (with Climate Exposure)** | Installed capacity, generation, export revenue, **climate exposure index** (projects in flood / GLOF risk zones), post-disaster damage tally | Project-by-project tracker, climate-risk overlays, post-disaster reconstruction debt cross-reference | "Can Electricity Replace Remittance?" — and later "When the Mountain Breaks the Plant: Hydropower's Climate Bill" |
| 12 | **Diaspora Capital Desk** | NRN investment indicators | Investment rules, sector briefs, risk matrix | "Can Diaspora Money Build Nepal?" |
| 13 | **The Soil Economy (Land & Life)** | Agri-Import Tally (rice/veg/meat imports YTD), Land Sprawl Index, Forest Wealth Proxy, Crop Opportunity Tile | District-level land-use atlas; crop suitability vs. actual cultivation maps; community forest registry; high-value crop profiles; irrigation infrastructure maps | "The Valley We Built Over" |
| 14 | **The Tax State (Follow the Tax)** | Tax revenue mix (customs/VAT/excise/income/corporate %), customs revenue share, import-dependent revenue share, tax-to-GDP, top sectors paying vs. top sectors benefiting from waivers | Revenue handle profiles (customs, VAT, excise, income tax); waiver/exemption registry; large-taxpayer concentration; customs-gate economic data | "Who Actually Pays for Nepal's Government?" |
| 15 | **The Migration Industry (Cost of Leaving Nepal) + FX Corridor Mechanics** | Recruitment-cost-to-first-year-wages ratio by destination, monthly outflows by country, manpower company concentration, recruitment-loan stress proxy, **USD/NPR interbank-vs-mid-market rate spread, top remittance-corridor pricing (Western Union / IME / Prabhu / wallet rails / informal Hundi proxy), formal-vs-informal channel share estimate** | Manpower company profiles; destination wage ladders (Qatar/UAE/Saudi/Korea/Japan/Malaysia/Romania); recruitment-cost trackers; airport-economy nodes; insurance + medical + orientation chains; **payout-partner FX exposure map**; **liquidity prefunding cycle explainer**; **"Cost of Leaving Nepal" calculator** | "Your First Nine Months Abroad Are Not Wealth. They Are Debt Recovery." |
| 16 | **The Collateral State (Credit Allocation)** | Credit by sector (real estate vs. SME vs. manufacturing vs. hydropower vs. consumer); collateral type mix (land vs. other); productive vs. consumption vs. speculative credit share; related-party lending exposure | Bank loan-book profiles (sector + collateral type); cooperative credit map; microfinance stress map; concept entries (evergreening, NPL, connected lending, base rate, refinance) | "Why Nepal's Banks Fund Land More Easily Than Businesses" |
| 17 | **The Household Ledger (Cost of Living Tracker)** | Recurring city/family dashboards: Kathmandu family-of-four, Pokhara renter, Gulf-remittance household, student-abroad household, farmer household, kirana-shopkeeper household — each tracking rice/dal/oil/LPG/rent/school/transport/medicine/interest/remittance/savings, month over month | Household basket compositions by archetype; cost-of-living methodology; **"What does this month mean for my house?" calculator** | "A Rs 45,000 Kathmandu Salary Bought 6% Less Household Security This Year." |

(Phase 2 adds: Shadow Economy Map, Migrant Money School (vernacular financial literacy), Real Estate Heat Map, Local Ledger spinning out from Budget Watch when municipal-level data quality permits.)

### Why "The Soil Economy" sits at #13 — the spatial-asset pillar in detail

If Money Pulse, Borrowed Time, and Private Capital X-Ray map Nepal's *financial* asset and *liability* sides, the Soil Economy maps Nepal's *physical* asset side. Without it, we cannot answer the fifth master question: **what could the land produce, and why isn't it producing it?**

Three structural sub-narratives:

**1. The Forest Paradox.** Nepal's community forestry program is an internationally recognized success — about 45% of the country is under forest cover, with ~22,000 community forest user groups (CFUGs) managing huge tracts of forest. Standing timber value, ecosystem services value, and non-timber forest product (NTFP) potential are enormous. Yet Nepal imports roughly Rs 30+ billion/year in timber, furniture, and wood products from Malaysia, Vietnam, Indonesia, China, and India. Regulatory limbo on timber harvest from community forests + missing processing infrastructure + lack of certification (FSC, PEFC) means the forest wealth is *dead capital* — visible, large, biologically alive, economically inert. **Story angle:** "Forest-to-Furniture Leakage."

**2. The Fragmentation Trap.** Generational land inheritance (partible inheritance practice) means agricultural plots shrink each generation. *Kittakat* — fragmentation — produces plots too small to mechanize, too small to consolidate into commercial farming, too small to take a bank loan against. The economic logic of small holding + missing irrigation + middleman-captured pricing + cheap imported alternatives means commercial farming is unviable for the next generation. They migrate to Gulf labor markets instead. **The structural link to migration:** land fragmentation is one of the underlying drivers of the remittance dependency story. Solving the migration story requires solving the soil story.

**3. The Altitude Opportunity.** Nepal spans 7 ecological zones from tropical Terai (60m) to alpine highlands (8,848m). This means almost any temperate, subtropical, or alpine crop *can* grow somewhere in Nepal. Coffee in Gulmi and Syangja. Large cardamom (*sukmel*) in eastern hills (Ilam, Panchthar, Taplejung — Nepal is among the world's top producers but most of it leaves unprocessed to India). Kiwi in the mid-hills. Hazelnuts on hillside terraces. Apples in Mustang and Jumla. Tea in Ilam. Medicinal herbs and aromatic plants (Yarsagumba, Pakhanbhed, Sugandhawal) in the high mountains. Most of this potential is **unmapped at the suitability × accessibility × irrigation level**, **uncertified for export grade**, and **uncommercialized at scale**. Smallholders grow these crops informally; the value chain captures the rent. **Story angles:** "Coffee, Cardamom, Kiwi: Nepal's Hidden Export Crops" / "The Sukmel That Leaves Nepal Unbranded and Comes Back as Indian Cardamom."

**Pulse tiles for The Soil Economy:**
- **Agri-Import Tally** — running monthly total of rice, vegetable, fruit, oilseed, dairy, and meat imports (Customs data). Annotated: "imports of crops Nepal can grow."
- **Land Sprawl Index** — rate of fertile-valley conversion to residential plots (focal areas: Kathmandu Valley, Pokhara, Chitwan, Itahari, Damak, Bharatpur). Built from satellite imagery + cadastral data.
- **Forest Wealth Proxy** — estimated value of standing timber (FAO + Nepal Forest Inventory data) vs. annual timber + furniture import bill.
- **Crop Opportunity Tile** — rotating spotlight on one high-value crop with map showing where it's suitable × where it's actually grown × where road + irrigation access enables commercialization.

**Knowledge Base entries:**
- **District profiles** — 77 districts, each with topographical/soil/altitude data, crop diversity index, current vs. potential cultivation, road and irrigation status.
- **Land Use Atlas** — multi-decade land-use change (forest / agriculture / urban / barren) using satellite-derived data (Hansen Global Forest Change, USGS Landsat, ICIMOD products).
- **High-Value Crop profiles** — coffee, large cardamom, kiwi, hazelnut, ginger, turmeric, tea, medicinal herbs. Each: where it grows, who's growing it, processing infrastructure, export markets, value-chain leakage, certification status.
- **Community Forestry encyclopedia** — CFUG count by district, forest type, NTFP potential, regulatory regime, revenue-sharing.
- **Concept entries:** kittakat (fragmentation), partible inheritance, community forestry, certification (FSC/PEFC/organic), geographical indication, contract farming.

**The Land Use Atlas — hero visualization (Q2):**
A geospatial layer on the homepage. Toggle between: forest cover (1990 → 2020), agricultural land (1990 → 2020), urban sprawl over fertile valleys (Kathmandu time-lapse, Pokhara time-lapse), crop suitability maps. Built with Mapbox or MapLibre + GeoJSON; uses public satellite-derived data (Hansen Global Forest Change, ESA WorldCover, etc.). This becomes the geospatial answer to the question: *"what could Nepal's land do?"*

**Year 1 stories under Soil Economy:**
- "The Valley We Built Over" (Kathmandu/Pokhara concrete sprawl + the food-import bill that followed)
- "The Forest Paradox: 45% Cover, Rs 30 Billion in Timber Imports"
- "Coffee, Cardamom, Kiwi: Nepal's Hidden Export Crops"
- "Why 'Kittakat' Land Fragmentation Sends Your Cousin to Qatar"
- "Why Nepal Imports Rice from a Country That Bought Our Forest"

**Data sources:**
- Department of Agriculture & Livestock (crop production, by district, by year)
- Department of Customs (food + timber + furniture import data, monthly)
- Department of Forest (community forestry data, forest inventory)
- Department of Land Management & Archive (cadastral, land-use)
- ICIMOD (geospatial, mountain ecology, climate)
- NSO Census of Agriculture (latest 2021/22)
- Hansen Global Forest Change (annual forest cover/loss, public)
- USGS Landsat / ESA Sentinel (free satellite imagery)
- Trade & Export Promotion Centre (coffee, cardamom, tea export data)
- ADB / IFAD / WFP project documents (loan-funded agricultural projects — feeds Borrowed Time cross-linking)
- FAO Nepal country profile + AGROSTAT
- NRB Agricultural Credit data

**Cross-linkages to other verticals:**
- **Borrowed Time:** ADB/IFAD/WB agricultural loans + post-disaster reconstruction loans for irrigation → feeds donor profiles
- **Concentrated Capture:** the developers and land-banking families converting fertile valleys → feeds business group profiles
- **Climate Tax:** monsoon damage to standing crops + irrigation infrastructure → feeds annual destruction tally
- **Remittance Dependency:** land fragmentation → migration → the loop closes
- **Imported Fragility:** food imports = price-anchored to Indian markets via the open border → links to Price Chain Nepal
- **Tourism Value Chain:** trekking corridors pass through agricultural districts — what trekkers eat (often imported), what they could eat (local hill produce)

### Why "Private Capital X-Ray" sits at #3 — the Money Funnel pillar in detail

If Public Enterprise X-Ray (#4) maps the state side of Nepal's economic machinery, **Private Capital X-Ray maps the private side — and the two together form the complete picture of who actually controls Nepal's money supply.**

The central observation: Nepal's domestic money funnels through a small number of family-controlled business groups that operate across the entire economic stack simultaneously:

- **The household consumption stack** — biscuits, instant noodles, cooking oil, soap, telecom, mobile internet, beer, fuel, retail, restaurants — most categories are dominated by 1–3 brands, most of those brands trace back to a handful of groups.
- **The banking stack** — most commercial banks have controlling shareholders linked to large business houses. The bank's loan book overlaps with the controlling group's other businesses (related-party lending exposure).
- **The capital market stack** — NEPSE market cap is concentrated in a small number of listed banks, hydropower SPVs, hotels, and FMCG companies — again often controlled by the same networks.
- **The real estate stack** — major developers, land banks, and high-end real estate projects are concentrated.
- **The import distribution stack** — major import licenses, exclusive dealerships (cars, electronics, white goods, machinery), and bonded warehouses are concentrated.
- **The hydropower SPV stack** — many private hydropower projects sit inside business groups.

**The structural question:** When a household spends Rs 100 on essentials, what fraction of that Rs 100 lands — directly or via the banking system — inside one of the top 15 business groups? Early estimate (to be hardened): a very large fraction. **Concentrated capture** is real.

**The other structural question:** What do these groups *do* with the capital they accumulate? Do they build exportable industry, productive employment, technology, or scale into regional markets? Or do they recycle profits into more imports, more real estate, more financial services, more domestic consumer brands — sectors that extract rent rather than build national productive capacity?

**Pulse tiles for Private Capital X-Ray:**
- **Banking concentration** — top 5 banks' share of deposits, loans, profit pool; related-party lending exposure (where disclosed)
- **NEPSE concentration** — top 10 listed companies' share of total market cap; sector concentration (banks dominate)
- **FMCG category concentration** — top 3 brands' share by category (biscuits, noodles, dairy, oil, etc.) where data exists
- **Real estate developer concentration** — major active projects by developer
- **Import license concentration** — top importers by value (where customs data permits)
- **Capital formation tracker** — gross fixed capital formation by sector (NRB / NSO national accounts) split into productive (manufacturing, energy, exports) vs. rentier (real estate, financial services, retail, hospitality)

**Knowledge Base entries — business group profiles** (template same as Public Enterprise X-Ray):
- Chaudhary Group (CG Corp Global) — Wai Wai, banking, hospitality, telecom, hydropower
- Vishal Group — FMCG, banking, hydropower, hospitality
- Shanker Group — automobiles, financial services
- Khetan Group — banking, manufacturing, FMCG distribution
- Golchha Organisation — manufacturing, FMCG, banking, energy
- Jyoti Group — banking, hydropower, hospitality, industry
- MV Dugar Group — banking, real estate, manufacturing
- Triveni Group, Goyal Group, IME Group, Saurabh Group, Vaidya Organisation — each profiled
- ~15 group profiles total, each with: businesses owned, banking relationships, listed entities, controlling family, governance, related-party exposure, controversies, public impact

**Knowledge Base entries — commercial banks** (each as an entity profile):
- NABIL, NIC Asia, NMB, Global IME, Nepal Investment Mega, Standard Chartered Nepal, Everest, Himalayan, Prabhu, Sanima, NCC, Citizens, Kumari, Laxmi Sunrise, Machhapuchchhre, Siddhartha, Prime, NBL (state-linked), RBB (state-owned), ADBL (state-owned)
- Per bank: ownership structure, controlling shareholders (and which business group they connect to), loan book composition (sector exposure), NPL ratio, related-party lending exposure, profit history

**Knowledge Base entries — major listed companies:**
- NTC, NIC Asia Bank, NABIL, Chilime Hydropower, Upper Tamakoshi, Nepal Lube Oil, Soaltee Hotel, Bishal Bazaar, Salt Trading (some state, some private)

**The Money Funnel visualization** (new D3 diagram, separate from Money Map):
- Top of funnel: household consumption (Rs 100 spent on a typical urban basket)
- Middle: split by category (food, telecom, fuel, banking, retail, etc.)
- Bottom: which company → which group → which controlling family
- A second view: bank deposits flowing into loan books, with related-party lending visualized

**Year 1 stories under Private Capital X-Ray:**
- "Who Owns the Rupee You Just Spent?" (consumption concentration — the foundational explainer)
- "The Five Families That Own Nepal's Banking System" (bank-by-bank ownership map)
- "Why Nepal's Conglomerates Don't Export" (the rentier vs. productive question)
- "Related-Party Lending: When the Bank Lends to Its Owner's Other Business"

**Data sources:**
- NRB Banking and Financial Statistics (bank-by-bank balance sheets, sector credit)
- NRB Bank Supervision Reports (related-party disclosures where present)
- NEPSE listed company filings, SEBON disclosures
- Office of Company Registrar (ownership records, where accessible)
- Annual reports of listed companies and major bank subsidiaries
- IRD large taxpayer disclosures (where available)
- Trade publications: Boss Nepal, Business 360, New Business Age
- Cross-referenced press research (Annapurna Express, Setopati, Online Khabar, The Kathmandu Post)
- Beneficial ownership: trickier in Nepal; flag confidence carefully

**This is the most editorially sensitive vertical in the platform.** Business group reporting in Nepal is thin and legally cautious. Every claim must be sourced rigorously. Right-of-reply policy must be public and honored. The Fact Ledger discipline is essential here. Confidence grading must be visible. Distinguish carefully between: (a) public-record ownership facts, (b) publicly-reported financial data, (c) corroborated reporting on practices, and (d) inference / allegation. Never present (d) as (a).

---

## The Three Signature Public Utilities (Inside the Verticals)

These are not new verticals. They are *features* inside existing verticals that elevate them from explainer-pages to indispensable public utilities — one tracker, two calculators. Each one should be among the platform's first-built artifacts because they generate disproportionate audience habit and authority.

### Signature Utility 1 — Loan → Project → Asset Tracker (inside Borrowed Time)

Every major foreign-funded project gets its own page with a citizen-readable verdict.

**Per project:**
- Loan amount (NPR + foreign currency)
- Lender (linked to donor profile)
- Interest, grace period, repayment schedule
- Project promise (what it was supposed to build)
- Original completion date → current completion status
- Cost overrun % | Time overrun (months)
- Projected benefit (per the original loan appraisal)
- Actual benefit so far
- Debt service paid to date (NPR)
- **Citizen verdict tag:** ASSET / BURDEN / ZOMBIE / UNKNOWN

**Launch projects (Year 1):**
- Pokhara Regional International Airport (China EXIM)
- Bhairahawa Gautam Buddha Airport (ADB)
- Melamchi Water Supply (ADB + JICA)
- Upper Tamakoshi Hydropower (mixed: NEA + donors)
- Kathmandu Ring Road expansion (China EXIM)
- Major sections of Postal Highway / Madhya Pahadi Highway

**Headline format:**
> "Nepal borrowed Rs X billion for this airport. Is the airport paying Nepal back?"

This format is repeatable for every loan-funded project. Over time it becomes a public ledger of national project-level accountability that does not currently exist anywhere.

### Signature Utility 2 — The Household Ledger Calculator (inside Household Ledger vertical)

Users select an archetype (or build their own):
- Kathmandu family-of-four | Pokhara renter | Gulf-remittance household | student-abroad household | farmer household | kirana-shopkeeper household

The calculator then shows:
- Monthly basket cost (NCPI-weighted, current month)
- YoY change in real purchasing power
- "What you bought for Rs 10,000 last year — and what it gets you now"
- Remittance dependency ratio (if applicable)
- Education-outflow burden (if applicable)
- A monthly "household squeeze" verdict in plain language

**The repeated headline format:**
> "A Rs 45,000 Kathmandu salary bought 6% less household security this year."

This product translates macro data into household reality every month. Sharable on WhatsApp. Sharable on Facebook. Builds direct returning-user habit.

### Signature Utility 3 — The Cost of Leaving Nepal Calculator (inside Migration Industry vertical)

User enters: destination, recruitment cost, expected salary, recruitment-loan terms, family obligations.

Calculator returns:
- Month-by-month break-even path
- "Your first 9 months abroad are debt recovery, not wealth creation"
- Net remittance after 1 / 2 / 5 years
- Comparison: same money invested in a local SME / hydropower bond / land / agriculture
- Returnee scenarios (with realistic data on returnee outcomes)

This is the platform's most emotionally powerful single product. It directly serves migrant workers, their families, and prospective migrants — the audience most underserved by Nepal's financial media. It also creates a natural Phase-2 bridge into the Migrant Money School vertical (vernacular financial literacy).

---

## The Content Format Bible

The platform knows *what* to build. This section locks down *the recurring shape* of each repeatable artifact, so the project executes without reinventing formats every month. Every entry below is a fixed template; deviating requires editorial sign-off.

### Monthly Verdict (the habit loop)

```
1. Headline (one line)
   "Money entered. Most did not compound."

2. Pillar summary (one short paragraph per pillar)
   - Money In:
   - Money Out:
   - Money Captured:
   - Money Wasted / Destroyed:
   - Where Money Became Wealth:

3. What changed this month (3–5 bullets, sourced)
4. One institution to watch  (e.g. NOC, NEA, PDMO, NRB)
5. One household impact      (e.g. food, rent, fuel, school fees)
6. One project / debt update (e.g. Pokhara Airport, Melamchi)
7. One productive escape     (e.g. IT exports, cardamom, hydropower)
8. Closing line              "Nepal did not lack money this month. It lacked conversion."
```

### Flagship Story

```
1. Human opening                       (one scene, one rupee, one household)
2. The number that matters             (one number, sourced, in context)
3. The system map                      (who, what, how — the structural picture)
4. What happened
5. Who benefits / who pays
6. Historical context
7. Data visualization                  (the hero chart that argues the point)
8. Linked entity / indicator profiles
9. Fact Ledger claims                  (clickable, sourced, confidence-graded)
10. What this means for households
11. What this reveals about conversion
12. What to watch next
13. Sources + right of reply
```

### Short Explainer

```
1. The question, in plain Nepali-English  ("What is BOP?" / "What is Hundi?")
2. Why it matters now
3. The mechanism (with one diagram or chart)
4. Two examples
5. What it does NOT mean (the common misunderstanding)
6. Where to read deeper (linked Knowledge Base entries)
```

### Entity Page (Public Enterprise, Bank, Business Group, Donor, IT Firm)

```
1. What this entity does
2. Why citizens should care        (the dramatic question)
3. Money in / money out
4. 5-year financials               (revenue, profit/loss, debt, subsidies)
5. Ownership / governance          (board, controlling shareholders, ministry)
6. Debt / liabilities
7. Public subsidy or hidden burden
8. Key controversies               (sourced, with Fact Ledger claims)
9. Related projects
10. Related people / ministries / companies
11. Timeline                       (leadership, financial events, policy events)
12. Data confidence level
13. Last updated + revision history
```

### Indicator Page

```
1. Plain-language definition
2. Current value + change vs. prior period
3. Historical chart
4. Why it matters
5. How it is calculated
6. Source institution
7. Update frequency
8. Data lag
9. Confidence grade
10. What moves this number
11. **What this number hides**     (the indicator-worship antidote)
12. Related indicators
13. Related stories
```

### Concept / Glossary Entry

```
1. Term (English + Nepali)
2. 2–3 paragraph plain explanation
3. Why it matters in Nepal specifically
4. See also (related concepts, entities, indicators)
5. Linked stories
```

### Money Flow Page (a node in the Money Map)

```
1. What this flow is              (e.g. "Education outflow," "Debt service")
2. How big it is                  (NPR + USD, latest period, source)
3. Where the money comes from
4. Where it goes
5. Why it exists at this scale
6. What would change it
7. Linked entities / indicators
8. Confidence + last updated
```

### Tracker Page (Loan→Project, Sahakari, etc.)

```
1. What this tracker monitors
2. Headline state               ("11 cooperatives frozen / 3 in recovery")
3. The list / table              (per-item: status, money, verdict tag)
4. Per-item detail page          (own template)
5. Methodology note
6. Update frequency + last updated
7. Linked stories
```

### Calculator Page (Household Ledger, Cost of Leaving Nepal)

```
1. The question this answers      ("What is this month costing your household?")
2. Input block                    (archetype selector / numeric inputs)
3. Output block                   (the headline number + 2–3 supporting numbers)
4. Plain-language interpretation  (the sentence that the number means)
5. Comparison / scenario toggle
6. Methodology note (link)
7. Linked stories + sources
8. Share-as-image button
```

### District MRI Page

```
1. District name (English + Nepali) + map locator
2. Headline economic story        (one paragraph specific to this district)
3. Remittance estimate
4. Federal grants received + capex execution
5. Top crops + crop suitability gap
6. Migration rate
7. Disaster damage YTD
8. Major public projects in district
9. Productive opportunity callout
10. Land-use change (10-year)
11. Confidence + last updated
```

### Methodology Note (for every derived/proxied product)

```
1. What this measures
2. What it does NOT measure
3. Source data
4. Formula / logic
5. Known limitations
6. Confidence level
7. Last updated
8. Revision history
```

Required for: Money Map, Money Funnel, Household Ledger, Cost of Leaving Nepal, Loan→Project Tracker, District MRI, Tourism leakage estimates, Digital export estimates, Land Use Atlas.

### Fact Ledger Claim (the visible popover schema)

```
- Claim                  (the statement, verbatim)
- Source(s)              (PDFs, filings, interviews, official reports)
- Confidence             (A = official audited / B = corroborated reporting / C = single source or disputed)
- Status                 (proven / alleged / disputed / under investigation)
- Money amount           (if applicable, NPR)
- Linked entities        (people, institutions)
- Date claim added
- Last verified
- Correction history
- Challenge link
```

### Correction / Challenge Workflow

```
1. User submits challenge        (source / objection / right-of-reply)
2. Claim enters "under review"   (visible on the claim popover)
3. Editor reviews within 7 days  (target SLA)
4. Outcome:
   - upheld           — no change; reasoning published
   - corrected        — claim text updated; correction note added
   - clarified        — context added without changing claim
   - retracted        — claim removed; retraction note remains
   - disputed         — both versions visible, sources for each
5. Public note added to claim's correction history
6. If material → story-level correction note added at top of story
7. Quarterly transparency: summary of all challenges processed
```

### Newsletter (Monthly Pulse Brief)

```
Subject line:  Same as Monthly Verdict headline
                "Money entered. Most did not compound — Chait 2082"

Sections:
1. Monthly Verdict (full paragraph)
2. The 5 numbers that moved your life
3. One chart (image embed)
4. One institution to watch
5. One project / debt update
6. One household impact
7. One productive escape
8. New Knowledge Base entries this month (3–5 links)
9. Read / Watch / Listen footer
10. Forward + share CTA
```

### Flagship Video (loose structure — flexes per story)

```
Cold open       One number or human scene
                ↓
Thesis          What this story reveals
                ↓
What happened   The events / structural picture
                ↓
The chart       Hero visualization, narrated
                ↓
Human impact    Who pays / who benefits
                ↓
The conversion  What this means for Nepal's wealth-conversion problem
                ↓
What to watch   Next month's signal
                ↓
CTA             Site link + calculator/tracker mention
```

### Short-Form Package (per flagship story)

```
- 4–6 Shorts/Reels/TikTok    (formats from the Short-Form Engine table)
- 1 Instagram + LinkedIn carousel
- 1 X/Twitter thread          (5–10 tweets)
- 1 LinkedIn long post
- 2–3 quote/claim graphics
- 1 audio-only podcast episode (re-cut from long video)
```

### Launch Package (one-time, for public beta)

```
1. Foundational article: "How Nepal's Economy Actually Works"
2. Foundational long video
3. Money Map v1 (D3 Sankey, sourced)
4. 5 Pulse KPI cards live
5. 10 Knowledge Base entries: 7 indicators (inflation, remittance, forex, BOP, capex, public debt, GDP) + 3 concepts (Hundi, Sahakari, CMEFS)
6. Fact Ledger schema live + 1 entity profile (NOC) with clickable claims
7. Newsletter issue #1
8. 10 launch shorts (Number, Did You Know, Compare Two, Map Moment formats)
9. LinkedIn launch post (for diaspora professional reach)
10. r/Nepal + r/nepaleconomy posts
11. "How to read Nepal Ledger" / Start Here guide (`/about/how-to-read`)
12. Press note: "The first money-intelligence platform for Nepal"
```

---

## District Economic MRI (The Local Identity Hook)

National macro alone doesn't make Nepalis return to a platform. **District identity** does. Every Nepali knows their district; almost no Nepali knows their district's economic profile.

**The product:** A dashboard for every district that asks "what is happening to my district's economy?"

**Per district:**
- Estimated remittance inflow (proxied from population × migration rate × destination wages)
- Federal grants received (NNRFC data)
- Capex execution rate (FCGO + sampled municipal budgets)
- Local revenue collected
- Top crops cultivated + crop suitability gap (links to Soil Economy)
- Food import dependence proxy
- Disaster damage YTD
- Road access score (Department of Roads)
- Migration rate (DoFE data + census)
- Education + health spending
- Major public projects in the district
- Land-use change over 10 years (from Land Use Atlas)
- "Productive opportunity" callout (what could this district produce that it isn't producing?)

**Year 1 launch districts (5):**
1. **Kathmandu** — urban, sprawl, real estate, banking centre
2. **Chitwan** — agricultural plain, fertile valley, transit economy
3. **Kaski (Pokhara)** — tourism, hydropower, urban sprawl, remittance
4. **Jhapa** — eastern border, tea, large cardamom, India-trade
5. **Morang (Biratnagar)** — industrial corridor, banking, agriculture

**Year 2 expands to 25 districts. Year 3 covers all 77.**

District profiles become one of the most defensible Knowledge Base assets and one of the strongest distribution hooks (every district has its own audience that will share its district's data).

---

## The Visible Fact Ledger (Trust as Product Infrastructure)

The Fact Ledger has been an editorial discipline so far. The upgrade: **make it visible product infrastructure**.

**Every major claim on the platform becomes clickable.**

When a user hovers or taps any claim in any article, video transcript, chart, or Knowledge Base entry, a small popover shows:

```
┌─ Claim ────────────────────────────────────────────────────┐
│  "NEA's debt grew 18% between FY 2078/79 and FY 2080/81."  │
├────────────────────────────────────────────────────────────┤
│  Source:       NEA Annual Reports 2078/79, 2080/81 [PDF↗] │
│  Confidence:   A (official audited statements)             │
│  Last verified: 2026-04-22                                 │
│  Dispute status: None recorded                             │
│  Correction history: No corrections                        │
│  Linked entities: NEA, Ministry of Energy [→]              │
│  [Challenge this claim →]  [Email editor →]                │
└────────────────────────────────────────────────────────────┘
```

**Why this matters:**
- In Nepal, accusations escalate into political and legal action quickly. Visible provenance is legal armor.
- Every story carries its sources in a permanent, queryable form — not just a "Sources" footer.
- "Challenge this claim" button creates a public submissions queue that becomes its own brand (we publish challenges + responses).
- Confidence grading visibly distinguishes A/B/C — readers learn that we have different confidence in different claims.
- Over time, the Fact Ledger becomes a queryable public claims database for journalists, researchers, and policymakers.

**Implementation:** every claim that warrants verification is tagged in MDX (`<Claim id="...">...</Claim>`); the build pipeline writes claim metadata to a queryable table; the popover renders client-side from a cached JSON.

---

### Why "Borrowed Time" sits at #2 — the Debt Watch pillar in detail

Nepal's debt trajectory is one of the most under-told structural stories in the country's economy. **No public outlet has built a sustained, citizen-facing intelligence layer on it.** The story has three compounding mechanisms:

1. **The currency mismatch.** Nepal borrows in USD, SDR, JPY, RMB, or INR. It earns and taxes in NPR. Every year the NPR weakens against the USD, the loan balance grows in rupee terms — without the government adding a single new project. This is silent debt inflation.

2. **The absorption mismatch.** Loans are signed for roads, hydropower, irrigation, urban infrastructure. The capital expenditure execution rate is consistently 50–70%. The other 30–50% of allocated money never converts to assets — but the loan and its interest schedule do. **Nepal borrows to build, then doesn't build, then borrows to repay.**

3. **The return mismatch.** Even projects that get built often don't generate the revenue projected in their feasibility studies. The loan was justified by expected returns; the actual returns rarely materialize at scale. The debt service comes from general revenue — i.e., from citizens.

**Pulse tiles for Borrowed Time:**
- Debt-to-GDP ratio (PDMO quarterly)
- Debt service / total revenue ratio (the real burden number)
- External vs domestic debt split
- Currency exposure breakdown (USD/SDR/JPY/CNY/INR %)
- NPR/USD depreciation tracker (NRB) with debt-stock impact calculator
- Latest loan signings (running ticker — when government signed, with whom, for what, on what terms)

**Knowledge Base entries for Borrowed Time:**
- **Donor entities** — ADB, World Bank/IDA, IMF, JICA, EXIM Bank of China, EXIM Bank of India, AIIB, Saudi Fund, OPEC Fund, KfW. Each gets the same multi-panel infographic treatment as Public Enterprises: what they fund, terms, interest rates, grace periods, currency, conditionalities, project pipeline, completed vs. failed projects.
- **Loan-funded project audits** — Melamchi Water, Pokhara Regional Airport, Bhairahawa Airport, ring road projects, hydropower loans, ADB urban transport. For each: cost overrun %, time overrun, projected vs. actual returns, current debt service status.
- **Concepts/glossary:** external debt, domestic debt, concessional loan, IDA terms, SDR basket, debt service ratio, debt distress, currency mismatch, sovereign rating, IMF Article IV, debt sustainability analysis (DSA).

**Year 1 debt-related stories:**
- "Why Every Foreign Loan Costs More Than the Day You Signed It" (currency depreciation explainer — the silent debt growth story)
- "Nepal Borrowed Rs X for [project]. Did [project] happen?" (project-level audit — likely Pokhara Airport or a hydropower loan)
- "The Donors Behind Nepal's Debt" (donor-by-donor explainer — terms, conditions, leverage)
- "What Happens If Nepal Can't Pay?" (debt distress scenarios — Sri Lanka, Pakistan, Zambia comparisons; what would IMF intervention look like)

**Data sources:** PDMO (Public Debt Management Office) bulletins + annual reports, NRB external debt statistics, MoF DFIMIS (Development Finance Information Management System), IMF Article IV reports, World Bank International Debt Statistics, ADB loan disclosures, OAG audit reports on loan-funded projects.

---

## The Master Narrative — 12 Structural Forces (11 frictions + 1 force of escape)

Every story names which force(s) it reveals:

1. **Leakage** — money enters, then exits through imports / education abroad / fuel / debt service
2. **Absorption Failure** — government has budget but cannot turn it into roads, irrigation, jobs (federally AND across the 753 local units, where grants often get spent on staff salaries, vehicles, view towers, and ribbon-cutting projects rather than productive infrastructure)
3. **Institutional Fog** — public enterprises, ministries, cooperatives, banks operate without public comprehension
4. **Imported Fragility** — Nepal imports fuel, goods, inflation pressure, and external shocks; the 1,700-km open border with India and the 1.6:1 NPR-INR peg mean Nepali border districts are price-anchored to Indian markets, with daily cross-border arbitrage on fuel, fertilizer, FMCG, and gold setting structural floors and ceilings
5. **Household Squeeze** — macro stability coexists with everyday suffering
6. **Fake Stability** — reserves look strong while productive capacity remains weak
7. **Remittance Dependency** — Nepal is stable because people leave, not because the domestic economy is strong
8. **Borrowed Time** — Nepal's present stability is increasingly bought with future obligations; foreign loans get more expensive every year the NPR depreciates against USD/SDR, and the projects they finance often fail to generate the returns that would repay them. The future is paying for the present.
9. **Concentrated Capture** — Nepal's domestic money supply funnels into a small number of family-controlled business groups that own commercial banks, importers, FMCG brands, real estate developers, listed equity, hydropower SPVs, and increasingly hospitality and telecom — simultaneously. A rupee a household spends on biscuits, deposits in a bank, or invests in NEPSE often lands inside the same network. The same dynamic plays out spatially: a small number of developers and land-banking families control the conversion of fertile agricultural valleys (Kathmandu, Pokhara, Chitwan, Itahari, Damak) into residential plots. Wealth pools instead of compounding into new productive entrants.
10. **Climate Tax (Capital Destruction)** — Nepal regularly loses the capital it has just built. Every monsoon, floods, landslides, and GLOFs (glacial lake outburst floods) wipe out roads, bridges, irrigation systems, private and public hydropower infrastructure, and standing agricultural crops. The 2015 earthquake alone destroyed an estimated Rs 706 billion of productive capital, financed by new foreign loans that the country must now service while still operating on partial reconstruction. **Net capital formation = Gross capital formation − Capital destruction.** When the destruction term is honestly accounted, Nepal's net investment in many years is far smaller than headline numbers suggest. The country builds on a leaking foundation.
11. **Spatial Misallocation (Dead Capital in the Soil)** — Nepal's primary physical asset is its land, and that asset is systematically used for the wrong things. Forty-five percent forest cover sits in regulatory limbo while the country imports billions in timber and furniture. Fertile alluvial valleys with three-crop potential are converted into residential plots while Nepal imports onions, rice, and vegetables. Land fragmentation (*kittakat*) shrinks holdings below the size needed for mechanization, pushing the next generation to Gulf labor migration rather than commercial farming. Seven altitude zones could support coffee, cardamom, kiwi, hazelnuts, medicinal herbs, and high-value horticulture — most of this potential is unmapped, uncertified, and uncommercialized. The land could produce many times what it currently produces. The economy doesn't reach for it.
12. **Productive Escape (Where Money Actually Compounds)** — The counter-force. Money in Nepal *does* compound in specific places, and refusing to name them produces doom journalism. The IT services exporters in Kathmandu and Pokhara are quietly bringing in foreign exchange and building careers without leaving. Hydropower projects that came online (Upper Tamakoshi, Chilime, Khimti) actually generate revenue and repay capital. Cardamom, tea, and coffee value chains have export-ready operators when processing and certification meet the crop. Municipalities that built strong local administration (a small minority) execute capex above 80%. Community forests in Dolakha, Chitwan, and Kavre have legal NTFP income streams. SMEs that formalize and break the kirana ceiling do exist. The platform's job is not only to expose what fails — it is to name what works, with the same rigor, so the question shifts from *"why is Nepal stuck?"* to *"why is this working here and not there?"*

Forces 1–11 are frictions on capital. Force 12 is the search for what survives them. Without it, Nepal Ledger becomes professional cynicism. With it, the platform becomes useful.

---

## The 9 Human Lenses (carried from v2)

Every story uses at least one:

| Lens | Role |
|------|------|
| Migrant worker | Sustains the household; finances stability |
| Mother managing costs | Feels inflation first |
| Kirana shopkeeper | Absorbs import cost; sets street prices |
| Student going abroad | Education outflow; aspiration drain |
| Farmer | Climate, inputs, middlemen, imports |
| Small contractor | Waits for delayed government payments |
| Banker | Sees credit risk, NPL stress |
| Taxpayer | Funds the state, rarely sees assets |
| Public enterprise employee | Inside institutional complexity |

---

## The Fact Ledger (Trust Infrastructure — From Gemini)

Every claim on the site is tagged. This is editorial discipline + a backend database.

**Per claim:**
- Statement
- Source (parliamentary report / court filing / NRB doc / interview / news / etc.)
- Confidence (A = official document, B = corroborated reporting, C = single source / disputed)
- Status (proven / alleged / disputed / under investigation)
- Money amount (if any)
- Linked entities (people, institutions)
- Linked documents (PDFs in our archive)
- Date claim was added; date last verified

**Per story, a "Sources" block:**
```
This story draws on:
- NRB CMEFS Chait 2082 (PDF, A confidence) [link]
- FCGO Daily Receipts (B confidence — preliminary) [link]
- Parliamentary Public Accounts Committee Report 2081 (A) [link]
- Interview: Bishnu Sharma, Kalimati wholesaler (C — single source)

Corrections to this story: [link to corrections log]
Right of reply: [editor@nepalledger.com]
```

This is the credibility moat for investigative stories.

---

## Site Architecture

```
/                                Verdict-first homepage (Monthly Verdict + 5 numbers + 1 story + Household calc + Lens chooser)
/pulse                           Monthly Verdict archive + extended Pulse cards + mini-pulses

/lenses/money-map                Full Money Map with drill-down on every flow node
/lenses/money-funnel             Money Funnel concentration visualization
/lenses/borrowed-time            Debt-stock × currency × project tracker
/lenses/land-use-atlas           Geospatial Soil Economy map (multi-decade, toggleable layers)
/lenses/tourism-rupee            Corridor-by-corridor leakage flow

/pillars/money-in                Pillar 1 — what is Nepal earning?
/pillars/money-out               Pillar 2 — what is leaving Nepal?
/pillars/money-captured          Pillar 3 — who pockets the rupees that circulate?
/pillars/money-wasted            Pillar 4 — where productive capital fails to form or gets destroyed?
/pillars/money-becomes-wealth    Pillar 5 — where is wealth actually being built?

/stories                         Flagship + explainer archive (filterable by pillar)
/stories/[slug]                  Individual story (long-form + embedded charts + clickable Fact Ledger claims)

/encyclopedia                    Knowledge Base index
/encyclopedia/entities/[slug]    Institution profile (multi-panel infographic)
/encyclopedia/indicators/[slug]  Indicator deep-dive
/encyclopedia/concepts/[slug]    Glossary entry

/trackers/loan-project-asset     Signature Utility 1 — Loan → Project → Asset Tracker (Borrowed Time)
/trackers/sahakari               Sahakari Tracker + "Check your cooperative" search

/calculators/household-ledger          Household Ledger calculator (archetype-driven)
/calculators/cost-of-leaving-nepal     Cost of Leaving Nepal calculator

/districts                       District MRI index
/districts/[slug]                Per-district dashboard (5 districts Year 1)

/fact-ledger                     Public claims database — sources, confidence grades, corrections, challenges
/data-room                       Source archive, methodology, downloads
/about                           Mission, masthead, editorial policy, corrections log
/newsletter                      Signup + archive

/ne/...                          Nepali versions of the Monthly Verdict, monthly flagship, and select calculators
```

---

## Information Architecture — The Lenses System (Solving the Clutter Problem)

**The honest concern:** With 17 internal verticals, 12 structural forces, 6 master questions, 4 hero visualizations (Money Map, Money Funnel, Land Use Atlas, Tourism Rupee), and 10+ Pulse tiles, the platform can collapse under its own weight on a mobile-first audience. Nepal is 70%+ mobile; small screens cannot show everything at once. (The 5 Public Pillars handle audience-facing language; the Lenses system handles audience-facing UI.)

**The solution: A Google-Maps-style Lens system.**

The homepage presents *one lens at a time*. Users switch lenses via a top toolbar (desktop) or bottom navigation (mobile). Each lens is a focused visualization that argues one point. Returning users can pin their preferred default lens.

### The 7 Lenses

| # | Lens | Hero visualization | Pulse cards shown | Primary question answered |
|---|------|-------------------|-------------------|---------------------------|
| 1 | **The Pulse** (default) | The 5 numbers that mattered this month + verdict | All headline KPIs | "What changed this month?" |
| 2 | **Money Map** | D3 Sankey of money flows (entering / circulating / leaking / destroyed) | Macro flow KPIs | "Where does Nepal's money go?" |
| 3 | **Money Funnel** | Concentration visualization (household Rs 100 → category → group) | Banking + NEPSE + FMCG concentration tiles | "Who captures the rupees that circulate?" |
| 4 | **Borrowed Time** | Debt-stock × currency-exposure × project-execution combined chart | Debt KPIs | "What is the future paying?" |
| 5 | **Land Use Atlas** | Geospatial map (forest / agri / urban over time) with toggleable layers | Soil Economy tiles | "What could the land produce?" |
| 6 | **Tourism Rupee** | Corridor-by-corridor leakage flow (Annapurna / Everest / Langtang) | Tourism KPIs | "Where does a tourist dollar actually go?" |
| 7 | **Latest Stories** | Timeline of recent investigations + their charts | Story metadata | "What is Nepal Ledger saying right now?" |

### How the lens system works

- **Default lens on first visit:** "The Pulse" — keeps mobile load light and gives a quick verdict.
- **Lens switcher:** persistent top bar (desktop) / bottom bar (mobile) with 7 icons.
- **Each lens loads independently** — no shared dashboard renders all at once. ISR cache per lens.
- **Drill-downs are always one tap away** — every Pulse tile, every flow node, every map region, every chart links to its full vertical page or Knowledge Base entry.
- **Cross-lens narrative** — the monthly verdict line at the top of every lens stays the same so users get the consistent thesis even when switching views.

### Mobile-first lens rules

- One hero visualization per screen, no more.
- KPI cards condense to a horizontal scrollable strip on phones (max 3 visible).
- Geospatial lens (Land Use Atlas) loads a low-detail tile by default; full vector layers only on tap.
- Sankey diagrams (Money Map) render as a simplified stacked-bar on phones, with a "view full diagram" link.
- Stories load reading-mode by default (large type, no sidebar).
- Newsletter signup is one persistent button, not an interstitial.

### What this solves

- **Cognitive load:** the user sees one argument per screen, not thirteen verticals competing for attention.
- **Mobile load weight:** ~1/7 of the data loads on first paint.
- **Reading vs. exploring:** Pulse is for habit users; Land Use Atlas + Money Funnel are for deep explorers. Both are first-class, neither dominates.
- **Authority + accessibility together:** the platform can be both as deep as Bloomberg Quint and as legible as the NYT Upshot. Lenses make this possible.

This is the IA decision that lets 13 verticals coexist without overwhelming a Pokhara phone user.

---

## Homepage Design (Verdict-First)

**The homepage is not the Money Map.** That was an earlier design. The audience does not return for a Sankey diagram — they return for a sharp answer. The Money Map remains a signature product (one of the 7 Lenses, and a hero visualization users explicitly choose). The front door is **The Monthly Verdict** + **the 5 numbers that moved your life** + **one story**.

```
═══════════════════════════════════════════════════════════════════
ARTHIK NEPAL          Nepal's money, mapped. Nepal's land, mapped.
═══════════════════════════════════════════════════════════════════

  THE MONTHLY VERDICT — CHAIT 2082
  Nepal received more dollars this month. Trade deficit widened
  almost as fast. NEA's debt service crossed Rs X billion. Pokhara
  Regional Airport entered its fourth year of underutilization.
  Sahakari Recovery Committee restored Rs Y crore to depositors;
  eleven of the largest troubled institutions remain frozen.
  Ilam's large cardamom exports cleared Rs Z. Money entered Nepal.
  Most did not compound.
                                      [Full Pulse article →]

  THE 5 NUMBERS THAT MOVED YOUR LIFE
  ┌──────┬──────┬──────┬──────┬──────┐
  │Infl. │Remit │Reserv│Capex │Trade │
  │ 4.47%│+12.3%│11.2mo│23%YTD│-Rs41B│
  │  ▼   │  ▲   │  ▲   │  ▼   │  ▲   │
  └──────┴──────┴──────┴──────┴──────┘

  ONE STORY THIS MONTH
  ┌────────────────────────────────────────────────────────┐
  │ [Hero image]                                            │
  │ Why Every Foreign Loan Costs More Than                  │
  │ the Day You Signed It                                   │
  │ [Read 9 min] [Watch 12 min]                             │
  └────────────────────────────────────────────────────────┘

  WHAT IS THIS MONTH COSTING YOUR HOUSEHOLD?
  [Household Ledger calculator: select archetype → basket inflation,
   purchasing-power change, remittance dependency]

  CHOOSE YOUR LENS                            (pin one as default)
  ┌─────────────────────────────────────────────────────────────┐
  │ [The Pulse ✓] [Money Map] [Money Funnel] [Borrowed Time]    │
  │ [Land Use Atlas] [Tourism Rupee] [Latest Stories]           │
  └─────────────────────────────────────────────────────────────┘

  PILLAR DRILL-DOWNS
  ┌──────────┬──────────┬──────────┬──────────┬──────────────┐
  │ Money In │Money Out │ Captured │ Wasted/  │ Where Money  │
  │          │          │          │Destroyed │Becomes Wealth│
  └──────────┴──────────┴──────────┴──────────┴──────────────┘

  NEPAL ECONOMY 101  •  ARTHIK FACT LEDGER  •  DATA ROOM
═══════════════════════════════════════════════════════════════════
```

**Why verdict-first beats chart-first:**
- A first-time mobile visitor in Pokhara reads a real answer in 10 seconds, not a Sankey to decode in 30.
- A prose verdict cannot be copied; the next platform's verdict will be different (and worse, because they don't have our dossiers).
- The Lens switcher gives power-users one tap to their preferred deep view.
- The 5 Pillar drill-downs replace the older 13-vertical grid — cleaner.
- The Household Ledger calculator above the Lens chooser turns macro data into "what does this mean for my house" — the strongest single habit hook.

This is **a financial command center for Nepal's economy** — but the command center opens with synthesis, not a model.

---

## Tech Stack (Reversed Back to Next.js — Justified)

| Layer | Choice | Why |
|-------|--------|-----|
| Framework | **Next.js 15** (App Router + TypeScript strict) | Dynamic data fetching for Pulse, ISR for stories, server actions for forms, future auth — Next.js is the right tool for a publication + dashboard hybrid. |
| Charts | Recharts (custom) + Tremor (KPI cards) | — |
| Diagrams | D3.js (Money Map, flow diagrams) | — |
| Content | MDX in `/content/stories/` + `/content/encyclopedia/` | Story content as MDX; structured fields via frontmatter |
| Database | Supabase (Postgres) + Drizzle ORM | Indicators, entity financials, fact ledger, cooperatives, hydropower projects |
| i18n | next-intl | `/en/` and `/ne/` routing |
| Search | Pagefind (built-in to Next.js export) | Static, fast, no backend cost |
| Hosting | Vercel | ISR for stories; on-demand revalidation when data refreshes |
| Email | Resend (custom newsletter) | Better than Substack — owns the audience, integrates with site auth later |
| Editorial AI | Claude Code CLI / Claude desktop | Manual workflow: extract, normalize, draft (no API subscription) |
| Scraping | Python (pdfplumber, BeautifulSoup, requests) | — |
| Automation | GitHub Actions (scheduled fetches only) | Pulls files; humans + Claude Code do parsing |
| Analytics | Plausible | Privacy-friendly, no cookie banner |

**Why Next.js wins for v5 (vs Astro for v4):**
- The Pulse requires dynamic data fetching + ISR + revalidation
- Future features need server runtime: search, newsletter signup, "Check your cooperative" tool, paid subscriptions
- Bilingual routing complexity is solved (next-intl)
- You already know it from Sagarmatha — zero learning tax
- App Router + Server Components keeps initial JS payload low; we don't pay the full Next.js cost for content pages

---

## Data Pipeline (AI-Assisted, Manual Workflow — No API)

```
┌─────────────────────────────────────────────────────────────┐
│ MONTHLY (when NRB releases CMEFs ~25th of following month)  │
├─────────────────────────────────────────────────────────────┤
│ 1. GitHub Actions fetches new CMEFs PDF + NCPI CSV          │
│    (or you drop manually if scraper fails)                  │
│ 2. Drop PDF into Economy/incoming/                          │
│ 3. Open Claude Code in that folder:                         │
│    "Extract all indicator tables. Normalize units.          │
│     Compute YoY and MoM. Output as JSON matching schema."   │
│ 4. Human review (15 min): scan for extraction errors        │
│ 5. Run import script → upsert to Supabase                   │
│ 6. Pulse cards + Money Map auto-update via ISR              │
│ 7. Claude Code drafts:                                       │
│    - "5 Numbers That Matter" newsletter section             │
│    - Monthly Pulse video script                             │
│    - Monthly Verdict draft (5-pillar prose synthesis)        │
│ 8. Human reviews / edits / records                          │
│ 9. Publish (~3–4 hours total of focused work)               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ DAILY/WEEKLY (FCGO + Customs + Kalimati + NEPSE)            │
├─────────────────────────────────────────────────────────────┤
│ - Scrapers pull data nightly; ingest scripts upsert         │
│ - Pulse tiles update via ISR                                │
│ - No AI in the loop; pure data pipeline                     │
│ - Confidence labels: "preliminary, unreconciled" for FCGO   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ STORY PRODUCTION (per story, ~1 week of focused work)       │
├─────────────────────────────────────────────────────────────┤
│ Day 1–2: Research with Claude Code (sources, data, history) │
│ Day 3:   Draft article (Claude drafts, human rewrites voice)│
│ Day 4:   Build visualizations (Recharts + D3)               │
│ Day 5:   Record + edit video                                │
│ Day 6:   Build encyclopedia entries (entity, indicator,     │
│          glossary as needed)                                │
│ Day 7:   Publish + distribute (article, video, shorts,      │
│          newsletter, social)                                │
└─────────────────────────────────────────────────────────────┘
```

---

## Production Cadence (Year 1 — Honest Reset)

**Reality check:** The earlier plan said ~5 stories/month → ~58 stories/year. That is content-factory pace, not authority-density pace. Cut by ~50%. **Authority density beats volume.**

### Realistic Year 1 monthly output

| Cadence | Output | Effort |
|---------|--------|--------|
| Monthly | Monthly Verdict release + Pulse update + Money Map refresh + Monthly Pulse video + newsletter | 2–3 days |
| Monthly | 1 flagship investigation OR explainer (alternating each month) | 2–3 weeks |
| Monthly | 1 short explainer video (8 min) | 2–3 days |
| Continuous | 2–4 encyclopedia entries built FROM each flagship story (entity profile, indicator page, glossary entry) | included in flagship |
| Quarterly | 1 marquee investigation (NOC, Sahakari, Kalimati, Pokhara Airport audit) — typically 4–6 weeks of deep research | replaces 1 monthly flagship |

### Realistic Year 1 totals

**Long-form (the authority layer):**
- **12 Monthly Verdict releases** (newsletter + video)
- **12 flagship long pieces** (article + video + Knowledge Base spinoff)
- **12 short explainer videos** (~8 min each)
- **25–40 encyclopedia entries** (entities + indicators + glossary)
- **4 hero visualizations** (Money Map + Money Funnel + Tourism Rupee + Land Use Atlas v1) — and only these four
- **3 signature utilitys built** (Loan→Project Tracker, Household Ledger Calculator, Cost of Leaving Nepal Calculator)
- **5 District MRIs** (Kathmandu, Chitwan, Kaski, Jhapa, Morang)

**Short-form (the acquisition + retention layer):**
- **~150 short videos** (Shorts/Reels/TikTok, ~3/week across 12 formats)
- **~50 carousels** (Instagram + LinkedIn, ~1/week)
- **~50 X/Twitter threads** aligned with stories + Monthly Verdicts
- **~100 quote/claim graphics** (~2/week)
- **~12 audio-podcast episodes** (audio version of each flagship)

Every short-form piece is downstream of a canonical site asset. None is created in isolation.

**This is roughly 25 hours/week of focused work.** Realistic as a serious part-time commitment or a full-time effort. **The goal is one piece of work per month that no other Nepali outlet could have produced.**

### What we explicitly do NOT do in Year 1

- We do NOT build all 17 verticals to full depth. Phase 1 is depth in 4–6 verticals; Phase 2 fills in the rest.
- We do NOT publish weekly. Monthly is the pace; weekly burns out solo operators and dilutes authority.
- We do NOT chase trending topics. We publish on the Calendar (NRB releases) and on our flagship investigations only.
- We do NOT build interactive Sankeys with live drill-down everywhere. Money Map is one D3 visualization. The rest are well-designed static charts.
- We do NOT build community features (comments, forums, user accounts) in Year 1.
- We do NOT translate every English article into Nepali. We translate the flagship monthly piece + the Monthly Pulse video. **Exception: the Cost of Leaving Nepal calculator ships bilingual from Day 1** — its highest-stakes users (prospective Gulf/Malaysia migrants making recruitment-loan decisions) are largely not English-comfortable, and gatekeeping that calculator behind English for a year wastes its primary use case.

### The Content Kill Switch (Capacity Protection Rule)

The Year 1 production math is genuinely tight. A flagship investigation can absorb 40 hours; a broken FCGO scraper can absorb 20 more. **When monthly capacity is constrained, short-form sheds first.** The Monthly Verdict, the flagship story, and the encyclopedia entries are protected. The cascade order when something has to give:

1. **First to cut:** discretionary shorts beyond the 4–6 per flagship + quote graphics
2. **Next to cut:** the 30-min-cost shorts (carousels, Twitter threads can be re-batched the following month)
3. **Next to cut:** the short explainer video for the month (defer 1 month)
4. **Last resort:** Monthly Pulse video (publish the Monthly Verdict article without the video that month, with a note)
5. **Never cut:** the Monthly Verdict itself + the flagship story + Fact Ledger updates

Authority density relentlessly protects itself from content volume. A month with a published Monthly Verdict + Flagship + zero shorts is a successful month. A month with 30 shorts and a skipped Monthly Verdict is a failed month.

---

## YouTube Channel Strategy

**Channel:** Nepal Ledger | अर्थिक नेपाल

**Format spec:**
- Long form: 10–15 min, hero D3 visualization on screen, narrator-driven, charts every 30 seconds, no stock footage
- Monthly Pulse: 10 min, "5 numbers + what they mean + what to watch"
- Shorts: 60s, one chart + one sentence, vertical aspect ratio, captioned
- Bilingual: English first, Nepali version 1 week later (separate YouTube uploads)

**Year 1 video sequence:**

| Month | Video | Type | Force |
|-------|-------|------|-------|
| 1 | How Nepal's Economy Actually Works | Master narrative explainer | All 7 |
| 1 | Why Farmers Get Rs 25 and You Pay Rs 125 | Investigation | Institutional fog |
| 2 | The Company Behind Every Fuel Price Hike (NOC) | Investigation | Institutional fog + imported fragility |
| 2 | What Inflation Really Means for Households | Explainer | Household squeeze |
| 3 | How Nepal's 'People's Banks' Stole the Poor's Savings | Investigation (Sahakari) | Money gets stolen |
| 3 | Nepal Has the Budget. Why Doesn't It Build? | Explainer | Absorption failure |
| 4 | Your Brother Sent Money from Qatar. Why Did Gold Arrive in Kathmandu? | Investigation (Hundi/gold) | Money bypasses system |
| 4 | NEA: Power Machine or Debt Machine? | Investigation | Institutional fog |
| 5 | Why Nepal Imports So Much | Explainer | Imported fragility |
| 5 | What Rs 30,000 Buys a Family in Kathmandu | Explainer | Household squeeze |
| 6 | Nepal Airlines: Why We Keep Funding It | Investigation | Institutional fog |
| 6 | **Why Every Foreign Loan Costs More Than the Day You Signed It** | Explainer (Borrowed Time #1 — currency depreciation × debt stock) | Borrowed Time |
| 7 | The Education Outflow | Investigation | Leakage |
| 7 | Can Electricity Replace Remittance? | Explainer (Hydropower) | Productive future |
| 8 | **Nepal Borrowed Rs X for [Pokhara Airport]. Did It Pay Off?** | Investigation (Borrowed Time #2 — single project audit) | Borrowed Time + absorption failure |
| 8 | Why Remittance Keeps Nepal Alive — and What It Doesn't Fix | Explainer | Remittance dependency / fake stability |
| 9 | **The Donors Behind Nepal's Debt** | Explainer (Borrowed Time #3 — ADB, WB, JICA, EXIM China, EXIM India profiles) | Borrowed Time |
| 9 | Why Nepal Imports So Much (Part 2 — the goods you didn't notice) | Explainer | Leakage / imported fragility |
| 10 | **What Happens If Nepal Can't Pay?** | Investigation (Borrowed Time #4 — debt distress scenarios vs. Sri Lanka, Pakistan, Zambia) | Borrowed Time / fake stability |
| 11 | **Who Owns the Rupee You Just Spent?** | Investigation (Private Capital X-Ray #1 — Money Funnel reveal) | Concentrated Capture |
| 11 | **The Five Families That Own Nepal's Banking System** | Investigation (Private Capital X-Ray #2 — bank-by-bank ownership map) | Concentrated Capture / Institutional fog |
| 12 | **Why Nepal's Conglomerates Don't Export** | Explainer (Private Capital X-Ray #3 — capital formation vs. rentier accumulation) | Concentrated Capture / absorption failure |
| 12 | **Where Does a $1,500 Trek Actually Go?** | Investigation (Tourism Value Chain #1 — Annapurna corridor) | Leakage / household squeeze |
| 13 | **Nepal's Quietest Export: How Code Crosses the Border** | Explainer (Digital Export Boom #1 — the productive counter-narrative) | Productive future (anti-leakage) |
| 13 | **What Did Your Municipality Do With Your Money?** | Investigation (Budget Watch / Local Ledger #1 — sampled local units) | Absorption Failure (local) / Institutional Fog |
| 14 | **Nepal Loses Rs X Billion Every Monsoon. Then We Borrow to Rebuild.** | Investigation (Climate Tax #1 — capital destruction × Borrowed Time) | Climate Tax / Borrowed Time |
| 14 | **The 1,700-km Border That Sets Nepal's Prices** | Explainer (Border Economy / Imported Fragility deep dive) | Imported Fragility |
| 15 | **The Valley We Built Over: How Kathmandu's Bread Basket Became Concrete** | Investigation (Soil Economy #1 — Land Use Atlas time-lapse + food-import bill) | Spatial Misallocation / Concentrated Capture |
| 15 | **The Forest Paradox: 45% Cover, Rs 30 Billion in Timber Imports** | Investigation (Soil Economy #2 — Forest-to-Furniture Leakage) | Spatial Misallocation / Leakage |
| 16 | **Coffee, Cardamom, Kiwi: Nepal's Hidden Export Crops** | Explainer (Soil Economy #3 — opportunity heatmap) | Spatial Misallocation / Productive future |
| 16 | **Why 'Kittakat' Land Fragmentation Sends Your Cousin to Qatar** | Investigation (Soil Economy #4 — fragmentation → migration loop) | Spatial Misallocation / Remittance Dependency |
| 17 | **Why Hundi Beats the Bank: How Money Actually Moves From Qatar to Kavre** | Investigation (FX Corridor Mechanics — interbank vs. mid-market spread, payout-partner FX exposure, liquidity prefunding, where formal channels structurally lose) | Imported Fragility / Remittance Dependency / Concentrated Capture |
| 17+ | Year in Review — All Eleven Forces in One Chart | Year-end retrospective | All forces |

**Plus 12 Monthly Pulse videos** (one per month on NRB release) and 12 short explainer videos.

**Year 1 long-form total: ~36 long videos** (12 Monthly Pulse + 12 flagship + 12 short explainer).
**Year 1 short-form total: ~350+ pieces** (~150 short videos + ~50 carousels + ~50 X threads + ~100 quote graphics + ~12 audio episodes) — see the Short-Form Distribution Engine section above.

(Note: the table lists the story slate that *informs* the YouTube schedule. Not every numbered row produces its own long video — many become explainers or feed multi-story arcs. Authority density over volume.)

---

## 90-Day Foundation Roadmap

Don't ship 12 stories in 90 days. Build the foundation. Stories accelerate after Day 90.

### Days 1–14: Bootstrap + Pulse v1

- Set up Next.js 15 + TypeScript + Supabase + Drizzle
- Build site shell: home, stories, encyclopedia, about
- Set up `next-intl` for `/en/` and `/ne/` (English first; Nepali later)
- Parse existing NCPI CSV → first 5 KPI cards on homepage
- Parse existing CMEFs PDF → remittance, forex, BOP indicators
- Build the first version of the Money Map (D3, with FY 2081/82 data)
- Set up Resend newsletter + signup

### Days 15–35: Story #1 — "How Nepal's Economy Actually Works"

The foundational explainer. Becomes the permanent #1 video on YouTube + the "Start Here" anchor on the homepage.

- Research with Claude Code: every flow in the Money Map, sourced
- Write the master narrative article (3,000 words)
- Build the full Money Map with drill-down on every node
- Record 15-min foundational video (English)
- Build encyclopedia: 7 indicator pages (inflation, remittance, forex, trade, capital exp, debt, GDP)
- Build encyclopedia: 7 concept pages (Hundi, Sahakari, CMEFS, BOP, monetary policy, fiscal deficit, NEPSE)
- Publish + launch newsletter

### Days 36–55: Story #2 — "Why Farmers Get Rs 25 and You Pay Rs 125"

- Kalimati price-chain investigation
- Builds the Price Chain vertical: daily Kalimati data scraper + first commodity map
- Records 12-min video
- Encyclopedia entries: Kalimati Market, "middleman economy" concept
- Publishes + first Reddit/LinkedIn distribution test

### Days 56–75: Story #3 — "The Company Behind Every Fuel Price Hike" (NOC)

- Full NOC investigation + dossier
- Builds the Public Enterprise X-Ray vertical: NOC as the template entity profile
- Encyclopedia entries: NOC, fuel price mechanism, Indian Oil Corporation relationship, NOC subsidy mechanism
- Records 15-min video + 3 shorts
- Establishes the multi-panel infographic template for future entities

### Days 76–90: Story #4 + Sahakari Tracker MVP + Borrowed Time + Private Capital seeding

- Sahakari investigation: "How Nepal's 'People's Banks' Stole the Poor's Savings"
- Builds Sahakari Tracker vertical: first 10 troubled cooperatives in the database
- "Check your cooperative" search v1
- Records investigation video
- **Borrowed Time vertical seeded:** ingest PDMO Q4 2081/82 debt bulletin; first donor profile (ADB); first 3 debt indicators live on Pulse (debt-to-GDP, debt service / revenue, NPR/USD with depreciation %)
- **Private Capital X-Ray seeded:** ingest NRB Banking & Financial Statistics; first banking concentration tile on Pulse (top 5 banks' share of deposits + loans); first bank profile drafted (NABIL or NIC Asia as the template); skeleton page for top-10 NEPSE concentration
- Public beta launch: r/Nepal, Nepali LinkedIn, X/Twitter, diaspora Reddit
- Press note: "The first money-intelligence platform for Nepal — mapping state, debt, and private capital in one place"

**At Day 90:**
- 4 deep stories published
- 8 videos on YouTube (4 long + 4 supporting shorts/explainers)
- Money Map live with 2 monthly updates already complete
- 5 KPI cards live and refreshing monthly
- 2 vertical hubs live (Price Chain, Public Enterprise X-Ray) + 1 in beta (Sahakari)
- 14 indicator pages, 14 concept pages, 1 entity profile (NOC) in the encyclopedia
- Newsletter list of 300+ subscribers
- ~5,000 YouTube subscribers (realistic ambition for a niche economic channel)

---

## Year 1 Vertical Build Order (After Day 90) — Honest Pace

**Existing ground-truth assets to leverage** (pull forward where possible):
- **753 fiscal-data extraction work** (if the underlying extraction architecture is already operational): a Local Ledger "Municipal Health" Pulse tile can be drafted in Q1 instead of waiting until Q4 — surfacing the extremes of local absorption failure (best and worst municipal capex execution) much earlier.
- **Annapurna ground-truth research** (topographical + on-the-ground data from the sanctuary route): the Annapurna corridor rupee-flow visualization in the Tourism Value Chain vertical can use first-party ground data rather than NTB proxy estimates, pulling Q2 work into Q1 if capacity allows.

Both are accelerators, not commitments — sequence them in only if the underlying work is genuinely production-ready. Better to ship a deep verified flow than a rushed-forward one.

| Quarter | What ships publicly | Internal work also happening |
|---------|--------------------|-----------------------------|
| Q1 (Days 1–90) | Monthly Verdict v1 + Pulse + Money Map v1 + Price Chain + Public Enterprise X-Ray (NOC) + Sahakari (beta tracker) + 3 flagship stories | Borrowed Time + Private Capital + Soil Economy data ingestion starts; Fact Ledger schema live |
| Q2 (Days 91–180) | Monthly Verdict v2 (5-pillar structure refined) + Borrowed Time vertical full launch + **Loan→Project Tracker (signature utility #1)** + Soil Economy Land Use Atlas v1 (Kathmandu + Pokhara time-lapse) + 3 more flagship stories (1 Borrowed Time, 1 Soil Economy, 1 Migration) | Private Capital X-Ray dossiers in research; Migration Industry data ingestion; **Household Ledger calculator** in development |
| Q3 (Days 181–270) | Private Capital X-Ray (Money Funnel + first 5 group profiles + 5 bank profiles) + Hydropower Monitor (with Climate Exposure) + **Household Ledger Calculator (signature utility #2)** + 3 more flagship stories (1 Private Capital, 1 Climate Tax, 1 Digital Export) | Migration Industry vertical full development; Tax State data ingestion; first 3 District MRIs (Kathmandu, Chitwan, Kaski) |
| Q4 (Days 271–365) | Migration Industry full + **Cost of Leaving Nepal Calculator (signature utility #3)** + Tax State seeded + Soil Economy district profiles (first 10 of 77) + Tourism Value Chain (Annapurna corridor full) + Digital Export Boom full + 3 more flagship stories (1 Migration Industry, 1 Soil Economy, 1 Year-in-Review) | Credit Allocation vertical seeded; remaining District MRIs queued for Year 2 |

### End-of-Year-1 deliverables (verifiable)

- **12 Monthly Verdict releases** — the ritual is established
- **12 flagship long pieces** (article + video + Knowledge Base spinoff)
- **12 short explainer videos** + ~150 short videos + ~50 carousels + ~50 X threads + ~100 quote graphics + ~12 audio episodes (see Short-Form Distribution Engine)
- **6 verticals fully live**: Pulse, Borrowed Time, Public Enterprise X-Ray, Sahakari, Private Capital, Soil Economy
- **5 verticals seeded**: Tourism, Digital Export, Migration Industry, Tax State, Household Ledger (plus Budget Watch + Local Ledger inside it)
- **3 signature utilitys shipped**: Loan→Project Tracker, Household Ledger Calculator, Cost of Leaving Nepal Calculator
- **4 hero visualizations**: Money Map, Money Funnel, Tourism Rupee, Land Use Atlas v1
- **5 District MRIs** (Kathmandu, Chitwan, Kaski, Jhapa, Morang)
- **~30 institutions profiled** (10 state enterprises, 5 donors, 5 business groups, 5 banks, 3–5 IT firms)
- **~40 indicators** with full history pages and Fact Ledger sources
- **~80 glossary entries**
- **Visible Fact Ledger** — every flagship claim clickable with source + confidence + corrections history

**Nobody in Nepal has this.** And critically, this is **producible by one serious operator** in 25 hours/week. The Year 1 plan is now honest about pace while preserving every structural pillar that makes the platform a category-definer.

---

## Editorial Policy

The Private Capital X-Ray and Sahakari Tracker verticals are legally sensitive. The Borrowed Time vertical involves political actors. Investigative credibility — and legal protection — depends on a published policy, not just internal discipline.

### Sourcing standards
- **A-grade source:** official audited document (NRB statements, OAG reports, PDMO bulletins, court filings, parliamentary committee reports, FCGO daily, customs official data)
- **B-grade source:** corroborated reporting (≥2 independent news sources, OR 1 source + corroborating documents)
- **C-grade source:** single source, on-the-record interview, leaked document with provenance, or claim under dispute
- No D-grade or rumor-based claims published. Period.

### Anonymous sources
- Allowed only when (a) the source faces real personal/professional risk, (b) the information is materially in the public interest, and (c) the editor has verified the source's identity and access. Anonymous claims always carry C-grade confidence and an explicit anonymous-source tag.

### Right of reply
- Every named individual or institution gets 7 days to respond to a material claim before publication.
- A standing email (`editor@nepalledger.com`) is published. All right-of-reply correspondence is logged.
- Responses are published in full alongside the claim, even if they dispute the claim.

### Allegation language rules
- "Alleged" ≠ "is" ≠ "appears to" ≠ "according to [source]." Use the right verb for the evidence tier.
- For C-grade claims: always attribute (`"according to..."`); never assert.
- For unproven claims naming individuals: legal review required before publication.
- For business group claims: distinguish public-record ownership facts (A) from publicly-reported financial data (B) from corroborated reporting on practices (B) from inference/allegation (C). Never present (C) as (A).

### Conflict of interest
- Editor's personal investments, family business interests, and consulting relationships are publicly disclosed.
- Any story touching an entity in the disclosure list requires a second-reader review and a published disclosure note in the story.
- No editor accepts paid speaking engagements from entities profiled on the platform.

### Sponsored content firewall
- Sponsored explainers (Phase 2+) are visually distinct, labeled "Sponsored" at the top, and never share a page with editorial coverage of the same entity.
- Sponsors never receive prior review of editorial content.
- Investment facilitation (if Diaspora Capital Desk ever monetizes) lives in a separate legal entity with a documented firewall.

### Legal review triggers
Any of these triggers mandatory legal review before publication:
- Naming a living individual in connection with alleged wrongdoing
- Claims about a publicly-traded entity that could affect share price
- Claims about a regulated financial institution (bank, cooperative, insurance)
- Claims naming a sitting government official by name
- Anonymous-source claims at C-grade confidence
- Any claim that has triggered a "Challenge this claim" submission

### Correction policy
- Material corrections published at the top of the story, dated, with the original text preserved in a strikethrough or a "previously read" block.
- The Fact Ledger correction history is permanent and queryable.
- Quarterly published "Corrections Report" summarizes all corrections made.

---

## Data Governance

### Source hierarchy
1. **Tier 1:** NRB, FCGO, PDMO, NSO, Department of Customs, MoF, MoALD, OAG, Department of Forest, NNRFC, NTB, DoFE, Land Survey Department
2. **Tier 2:** Multilateral institutions (World Bank, ADB, IMF Article IV, JICA, AIIB) and bilateral donors
3. **Tier 3:** Industry bodies (FNCCI, CNI, NRNA), trade associations, listed-company filings (NEPSE, SEBON)
4. **Tier 4:** Reputable journalism (The Kathmandu Post, Online Khabar, Setopati, Annapurna Express, Republica, Nepali Times, Centre for Investigative Journalism Nepal)
5. **Tier 5:** Interviews + on-the-record statements

When two tiers conflict, the higher tier wins unless explicitly justified.

### Visible data-status labels
Every Pulse card, chart, tracker, calculator output, and indicator page carries one of these visible labels:

| Label | Meaning |
|-------|---------|
| **Fresh** | Updated this period (within latest release cycle) |
| **Lagged** | Latest official release > 3 months old |
| **Preliminary** | Will likely be revised (e.g., FCGO daily, first-cut NSO GDP) |
| **Estimated** | Derived from a proxy or model, not official |
| **Partial** | Incomplete coverage (e.g., only some districts available) |
| **Disputed** | Two credible sources conflict; both are shown |
| **Archived** | Historical context only, not current |

### Revision policy
- When upstream data is revised (e.g., NSO revises GDP, PDMO revises debt stock), the platform updates within 5 business days.
- Old values are preserved in an `indicator_values.revision_number` chain — readers can see the history.
- A "What changed" note is added to the indicator page if the revision is material (>3% change).

### Scraping ethics
- We only scrape data that is published publicly and intended for public consumption.
- We respect `robots.txt`, rate-limit our requests, and identify our scraper with a contact email.
- We never bypass paywalls, authentication, or technical access controls.
- For government PDFs that are taken down or replaced, we keep our archived copy with the original publication date and a note explaining the takedown.

### Archival policy
- Every source document (NRB CMEFs PDF, customs Excel, OAG report, etc.) is stored in our `source_documents` archive with a hash, timestamp, and downloaded URL.
- The Data Room (`/data-room`) publishes the original archive for any cited document.
- This is critical because Nepali government PDFs are frequently replaced silently without a versioned URL.

### Metadata standards
Every chart and dataset on the platform carries:
- Source institution (with link to the original)
- Date of source data
- Date of last platform update
- Methodology link
- Confidence label
- Alt text for accessibility

### Versioning
- Charts have an internal version number; the published chart shows the version + date.
- Datasets in `/data-room` are downloadable with version metadata.
- Old chart versions remain accessible at `/charts/[slug]/v[n]` so referenced research doesn't break.

### Data Continuity Protocol (when sources break)

Government data sources in Nepal are unreliable: FCGO portals go down, customs URLs change, NRB PDF formats shift, NSO sometimes publishes inconsistent historical revisions. The platform must handle continuity gaps explicitly rather than failing silently. Five-part protocol:

1. **Continuous archival on download.** Every source document is hashed + timestamped + stored in `source_documents` *before* parsing. If the upstream URL disappears tomorrow, we still have our copy with proven provenance.
2. **Revision preservation.** When an upstream value changes retroactively (NSO revises GDP, PDMO revises debt stock, FCGO daily figures are reconciled), the prior value is kept in `indicator_values.revision_number`. The indicator page shows the revision trail with dates and an editorial note explaining material revisions.
3. **Discontinuity labeling.** When a source goes offline or changes format/methodology, affected indicators get a visible **"Data discontinuity since [date]"** tag. The Pulse card stays visible with the last known value, not silently broken or fabricated forward.
4. **Parser versioning.** `indicator_values.parser_version` records which extraction logic produced a value, so a parser bug can be traced and re-run against the archive. When we upgrade a parser, we re-extract from the archived source documents — never trust the live URL retroactively.
5. **The honest fallback.** When continuity cannot be preserved (e.g., a government portal redesign destroys historical URLs), we publish a `Data Continuity Note` explaining what broke, what we know, and what we are missing. The platform's credibility depends on naming the gaps, not hiding them with bridge estimates or interpolation.

This is why every Pulse card and chart carries a visible data-status label and a "last verified" date. If the label says "Lagged" or "Disputed," the reader knows. The platform's job is to be the most honest data layer in Nepal — not the prettiest dashboard.

---

## Chart Doctrine (Visual Argumentation)

Visual journalism is the moat. Charts are not decoration. The rules:

1. **Every chart answers a sentence.** If you cannot write the one-sentence answer the chart provides, don't make the chart.
2. **Every chart shows source + confidence + last updated.** Inline. Not a footer.
3. **Every chart has a mobile version.** Vertical-fit layout, not a desktop chart squeezed onto a phone.
4. **Every chart has alt text.** Accessibility is non-negotiable.
5. **Every chart has a static social export.** PNG, properly captioned, ready for Twitter/LinkedIn/WhatsApp share.
6. **Every chart has a "what this hides" note** when the underlying data has known limitations (e.g., FCGO preliminary, NSO lagged, geographic coverage partial).
7. **No chart exists only because data exists.** If the data doesn't argue a point in the story, leave it in the Data Room.
8. **Charts are typed and templated** (5 base types: time-series, comparison, distribution, flow, geographic). New chart types require editorial approval to avoid one-off visual debt.

---

## Audience Beachhead (Sharpened from Critique)

**Primary (Year 1) — three segments, English-first:**
1. **Urban Nepali professionals** (25–45) in Kathmandu, Pokhara, Biratnagar, Birgunj — bank accounts, NEPSE-curious, watch YouTube, on LinkedIn.
2. **Information diaspora** — educated Nepalis abroad (US, UK, Australia, Gulf, India) who want to understand the country.
3. **Investor diaspora** — NRNs considering land, hydropower, startups, SMEs, NEPSE — distinct from #2 because their job-to-be-done is "should I invest?", not "should I read?".

**Secondary (Year 1) — bridge audience for the Cost of Leaving Nepal calculator:**
Prospective migrants (still in Nepal) + families making migration decisions + diaspora researchers. **Because this calculator ships bilingual from Day 1 (not lagged a week like other Nepali content), it reaches both the English-comfortable segment AND the prospective Gulf/Malaysia migrant taking a recruitment loan — the user with the highest decision stakes.** Distribution channels for the Nepali version of this one calculator include WhatsApp + TikTok + manpower-company adjacent forums even in Year 1.

**Phase 2 (Year 2) — broader vernacular expansion:**
Active migrant workers in Gulf/Korea/Japan/Malaysia and their on-Nepal-soil families. Different tone, Nepali-first across the platform, WhatsApp + TikTok distribution for short-form. Migrant Money School vertical scales here. The Cost of Leaving Nepal calculator already shipped bilingual; in Year 2 the rest of the Migration Industry vertical also gets vernacular treatment.

**Explicitly not targeted in Year 1:** policymakers (don't pay), banks/fintechs (no need yet), academics (too narrow), general youth (too broad).

---

## Monetization Ladder (From Gemini — Phase 2+)

Year 1: free everything. Build audience and authority.

Year 2 onward:

| Stage | Product | Revenue model |
|-------|---------|---------------|
| Free | All public stories, videos, dashboards | YouTube ad rev, sponsorships (clearly labeled) |
| Registered | Watchlists, saved searches, "Check your cooperative" alerts | Email capture, lead nurture |
| Paid individual | Monthly intelligence brief, diaspora investment digests | Subscription ($5/month) |
| Paid professional | Data exports, sector reports, institutional dashboards | B2B subscription ($50/month) |
| Enterprise | Custom research for banks, DFIs, embassies | Contract revenue |
| Events | Annual Nepal Ledger Money Summit | Sponsorship + ticketing |
| Education | Financial literacy courses | Paid cohorts + grant funding |

**Editorial firewall** (non-negotiable):
- Journalism never paid. Investigative independence sacred.
- Sponsored explainers clearly labeled, never blended with editorial.
- Investment facilitation (if it happens) lives in a separate legal entity.

---

## What's Different vs. Every Previous Version

**vs. v1 (original):** Far more ambitious. 8 verticals, not just inflation. Money Map as flagship. Bilingual from launch.

**vs. v2 (narrative engine):** Adds back the data infrastructure and real-time pulse that v2 underweighted. Story Bible kept as editorial backbone.

**vs. v3 (Gemini synthesis):** Adds structural discipline. v3 was too sprawling; v5 sequences the 8 verticals across 4 quarters instead of trying to ship all at once.

**vs. v4 (radical rethink):** Brings back the dashboard, the live Pulse, the visual narrative as moat, and the data infrastructure. v4 was right that one person cannot build an institution overnight; v5 builds it across 12 months, not 90 days.

---

## The Final Statement

**Nepal Ledger is Nepal's monthly national balance-sheet ritual.**

Every month it asks one question:
> Did Nepal grow this month, or did it survive another month?

And answers it not with a number, but with **The Monthly Verdict** — a sharp prose synthesis published on each NRB release, structured by the 5 Public Pillars, anchored to specific institutions, projects, and households named in the platform's own dossiers.

Behind the Verdict sits the platform: a Lenses-based interface (Money Map / Money Funnel / Land Use Atlas / Tourism Rupee / Borrowed Time / The Pulse / Latest Stories), a flagship monthly investigation, three signature public utilities (Loan→Project→Asset Tracker, Household Ledger Calculator, Cost of Leaving Nepal Calculator), five district MRIs, a visible Fact Ledger where every claim is clickable, and a growing public encyclopedia of every institution, donor, business group, bank, IT firm, trekking corridor, crop, and local government unit that shapes Nepal's economy.

The short version:
> **Nepal does not lack money. It lacks conversion. Nepal Ledger tracks whether money becomes wealth.**

That is the category. The moat is the encyclopedia + the dossiers + the Fact Ledger — everything that compounds. The habit loop is the Verdict + the Pulse + the signature utilities — everything that synthesizes. Authority comes from doing both well, monthly, without faking precision.

---

## Verification Plan

- Money Map renders with full FY 2081/82 data, every flow node has source citation + confidence grade
- Homepage Pulse cards refresh via ISR within 5 minutes of NRB data ingestion
- "How Nepal's Economy Actually Works" foundational video has 1,000+ views in first 30 days
- 4 stories live by Day 90, each with article + video + ≥2 encyclopedia entries left behind
- Sahakari Tracker MVP can answer "is X cooperative on the troubled list?" for at least 50 cooperatives
- NOC entity profile has full financials over 5 years, governance section, controversies log, and at least 20 sourced claims with confidence grades
- Newsletter sent monthly without fail; "5 Numbers That Mattered" auto-drafted by Claude Code, human-edited
- Public beta in 90 days reaches 300 newsletter subs + 5,000 YouTube subs as a baseline KPI

---

*v5 — Integrated Vision — 2026-05-13*
*Status: Final pending Astro/Next.js confirmation*
