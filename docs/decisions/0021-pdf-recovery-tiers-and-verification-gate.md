# ADR-0021: PDF recovery tiers + the verification gate (clarifies ADR-0003)

- **Status:** Accepted
- **Date:** 2026-06-08
- **Deciders:** user, Mother Opus
- **Tags:** data-pipeline, parsing, ocr, governance, foundational

## Context

A large, mission-essential body of data was being **deferred** ("CID-broken",
"Preeti gibberish", "RTL-mirrored — fragile") rather than recovered: the
Economic Survey macro annex (GDP / GVA-by-sector / prices / **fiscal** /
trade / BoP — the canonical national-accounts headline), the Preeti-era
foreign-aid White Books (FY2062/63–2067/68 = AD 2005–2011), historical
intergovernmental fiscal transfers (8 FYs), and the full Yellow Book per-SOE
financials. The mission is *"track whether Nepal's money becomes wealth, from
the past to the present"* — deferring the past defeats it.

Root cause: workers collapsed **three distinct techniques** under
[ADR-0003](0003-ai-assisted-parsing-policy.md) ("no production AI parsing") and
refused all three. Only the third is actually an AI technique:

1. **Font transliteration** (Preeti / legacy 8-bit Nepali fonts → Unicode) — a
   **fixed, public byte-map**. Deterministic code, not AI. *Probe confirms:* a
   FY2065/66 White Book page extracts `cid=0, ascii_alpha=514`,
   `"j}b]lzs ;xfotf"` = वैदेशिक सहायता — recoverable by a lookup table.
2. **Geometry normalization** (RTL-mirror / transposition) — a **consistent
   reversible transform**. *Probe confirms:* Economic Survey p301 extracts
   `"srotacidnI / cimonoceorcaM / P42/3202"` = `Indicators / Macroeconomic /
   2023/24P` reversed — recoverable by reversing strings + column/row order.
3. **Optical recognition** (Surya OCR) of genuinely scanned / no-usable-text-
   layer pages — *recognition with confidence*, NOT generative LLM extraction.

ADR-0003 forbids only **generative-LLM-as-primary-extractor** (an LLM "reading"
a number out of a document, which can hallucinate). It does **not** forbid
deterministic transliteration, deterministic geometry fixes, or deterministic
optical recognition. `FINANCIAL_DATA_STRATEGY.md §Phase B` already MANDATED the
Surya pipeline (the `ocr_tracking` schema + `surya-ocr-findings.md` +
`scrapers/_common/devanagari_normalization.py` are the scaffold) — it was
designed and never built.

## Decision

Adopt a **tiered recovery cascade**. For each essential-but-unparsed PDF, use
the cheapest *correct* tier; never skip data because a higher tier is needed.

- **Tier 0 — clean Unicode text layer** → `pdfplumber` (status quo).
- **Tier 1 — deterministic recovery (no OCR, no AI; ADR-0003-clean):**
  - **1a Font transliteration:** Preeti/legacy → Unicode via a fixed map in
    `scrapers/_common/preeti.py` (+ ligature reordering), then the existing
    `devanagari_normalization.py` substitution pass.
  - **1b Geometry normalization:** reverse mirrored strings + column/row order;
    de-transpose; reattach line-wrapped labels.
- **Tier 2 — Surya tile-OCR** (the mandated Phase B pipeline) for scanned /
  no-text-layer / Tier-1-infeasible pages: render → OpenCV deskew/denoise →
  tile (overlap) → Surya (`v0.17.1`, **always `--detect_boxes`**) → stitch
  (dedupe overlaps, log disagreements) → `devanagari_normalization` pass →
  persist to `ocr_tile_manifests` / `ocr_cell_extractions` /
  `ocr_stitch_disagreements`. Dual numeral systems (Devanagari ↔ Arabic) kept.
- **AI (Claude) is permitted ONLY as a dev/QA assistant** — to build the maps,
  and to run the sample verification below — **never** as the production
  extractor of a value.

### The verification gate (the trust boundary for Tiers 1b/2)

No Tier-1b or Tier-2 output enters the truth layer (`approved_indicator_values`
/ `dne_facts` / fact tables) until it passes ALL of:

1. **Reconciliation:** extracted subtotals/totals reconcile to the document's
   own **printed** grand-total rows (exact for Tier 1; within a stated
   tolerance for Tier 2). A run that doesn't reconcile has a geometry/decoding
   bug and MUST NOT ship (ADR-0011 discipline).
2. **Sample verification ("compare on sample basis with the PDF"):** a sample of
   cells — for Tier 2, biased to **low-confidence + near-tile-seam** cells via
   `ocr_cell_extractions` — is compared against the **rendered PDF page**. The
   reviewer renders the page (the **Read tool reads PDF pages natively**; or
   pymupdf) and confirms the value visually. Disagreements are fixed or the
   cell is dropped — never guessed.
3. **Provenance + confidence:** every recovered fact records its
   `extraction_method` (`pdfplumber` | `preeti-translit` | `unmirror` |
   `surya-ocr`) and a confidence grade reflecting the method (Tier 0/1a → A/B;
   Tier 1b → B; Tier 2 → B/C, flagged). Never zero-fill; absent stays absent
   (Data Continuity Protocol).

Tier 1 (deterministic) is reproducible and ships first. Tier 2 (OCR) ships after
Tier 1, gated on the same verification, with the `ocr_tracking` trio populated.

## Alternatives Considered

- **Stay deterministic-text-only, defer all hard PDFs** — rejected: it
  permanently excludes the national-accounts headline + all pre-2012 history,
  defeating the mission's "past to present" mandate.
- **LLM-vision as the primary extractor** — rejected (ADR-0003): hallucination
  risk on numbers with no reconciliation guarantee. LLM-vision is allowed only
  as the *sample verifier*, where its job is to AGREE/DISAGREE with a
  deterministically-extracted value, not to produce it.

## Consequences

- Preeti-era + mirrored + scanned data become recoverable; the platform reaches
  back to ~2005 and forward to the latest editions.
- New module `scrapers/_common/preeti.py` (Tier 1a) + a Surya harness (Tier 2,
  later). New dep set for Tier 2: `surya-ocr==0.17.1`, `pymupdf`, `opencv`
  (installed only when Tier 2 work starts — Tier 1 needs none).
- Sequencing (per user): **Tier 1 deterministic first** (Economic Survey macro
  annex un-mirror + White Book Preeti history), prove the gate, **then** Surya.
- Every recovered fact is provenance-tagged + verified; the truth layer's trust
  level is explicit per row.

## References

- [ADR-0003](0003-ai-assisted-parsing-policy.md) — the policy this clarifies (no generative-LLM extractor)
- [ADR-0011](0011-fiscal-data-units-and-identity.md) — reconcile/verify by magnitude
- `docs/FINANCIAL_DATA_STRATEGY.md` §Phase B — the mandated Surya pipeline
- `docs/research/surya-ocr-findings.md` — v0.17.1 pin, `--detect_boxes`, OpenCV preprocess, Devanagari regression
- `src/lib/db/schema/ocr-tracking.ts` — the OCR provenance/drift scaffold
- `scrapers/_common/devanagari_normalization.py` — the inherited substitution dictionary
