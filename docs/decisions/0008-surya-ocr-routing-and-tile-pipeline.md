# ADR-0008: Surya OCR Routing + Tile-Based Pipeline for Devanagari PDFs

- **Status:** Proposed (concrete routing thresholds finalize after Worker δ's empirical evaluation returns)
- **Date:** 2026-05-14
- **Deciders:** Mother Opus, user (delegated via overnight authorization)
- **Tags:** ocr, parsing, devanagari, surya, infrastructure

## Context

ADR-0003 mandates deterministic Python for production parsing. The MoF PDF corpus (Red Book, White Book, Yellow Book, Agreement, Intergovernmental Fiscal Transfer reports) requires OCR because Nepali text in these PDFs commonly has non-Unicode font embedding that defeats pure text-layer extractors like `pdfplumber`.

The user mandated:
1. Read 100% of Surya OCR documentation before integrating — done (`docs/research/surya-ocr-findings.md`).
2. Surya OCR is the primary OCR engine.
3. Claude CLI provides spot-check / review during dev workflow (per ADR-0003 — Claude is a dev assistant, not a production runtime).
4. Build with proactive failure-mode foresight for tile-based processing.
5. PaddleOCR is an acceptable fallback if Surya falls below threshold; require empirical evidence before committing to a routing rule.

The Surya findings doc revealed three critical architecture-shaping facts:

1. **`surya_table` defaults to PDF text-layer extraction, not OCR.** For scanned NRB/MoF PDFs this returns blank cells unless `--detect_boxes` is passed. This is almost certainly the failure mode of the user's prior chat.
2. **`TABLE_REC_MAX_BOXES=150` silently truncates large tables.** Red Book and intergovernmental tables routinely exceed 150 cells per page.
3. **DPI is hard-capped at 192** (`IMAGE_DPI_HIGHRES=192`, segfaults at 300/600 DPI per issue #389 unresolved at v0.17.1). 192 DPI is below the OCR-industry standard 300 DPI for dense Devanagari — and the **Devanagari regression open at issue #475** makes this worse.

## Decision

### 1. Surya v0.17.1 pinned. PaddleOCR as fallback per Worker δ's evidence.

- Production parsers depend on `surya-ocr==0.17.1` exactly (per the findings doc's recommendation).
- PaddleOCR pinned to the version Worker δ benchmarks; install only on parser machines that need fallback.
- Both run locally; no API calls (ADR-0003 compliance).

### 2. Tile-based processing as the default Surya invocation.

Effective higher resolution is achieved by tiling, not by raising DPI:

- **Default**: render PDF page at 384 DPI (~ 2× the 192 cap). Split into a **2×2 grid with 80 px overlap**. Each tile fits Surya's 2048 px width cap.
- **Stress tier** for dense Devanagari pages: 576 DPI, 3×3 grid, 100 px overlap.
- **Layout detection** runs on the full-page 192 DPI image FIRST (Surya's layout is script-agnostic and not the OCR-quality bottleneck). Recognition runs on the higher-DPI tiles aligned to the detected table cells, so tiles don't bisect cells.

### 3. Mandatory Surya invocation flags

- `--detect_boxes` **always** for scanned/Nepali PDFs (otherwise cells return blank).
- `TABLE_REC_MAX_BOXES=500` env var per parser run (raised from 150 default; per-page bound).
- `IMAGE_DPI_HIGHRES=192` — never raised; cap.
- Surya `langs=` parameter is NOT used (removed in v0.16.0; script auto-detected).

### 4. Pre-Surya OpenCV pipeline (Surya does no preprocessing)

For Devanagari-dominant pages:
- Deskew via `cv2.minAreaRect` over text contours
- Adaptive binarization (`cv2.adaptiveThreshold` with `THRESH_BINARY` + Gaussian)
- Denoise (`cv2.fastNlMeansDenoising`)
- All before tile splitting

For Latin-dominant pages: pre-processing usually unnecessary; let Surya run on the raw render.

### 5. Twelve foreseen tile-stitch failure modes — codified mitigations

| # | Failure | Mitigation |
|---|---|---|
| 1 | Devanagari diacritic clipped at tile edge | 80–120 px overlap (≥2 line heights at 384 DPI) |
| 2 | Numeral split across vertical seam | Tile per detected table region (layout-aware), not on fixed grid |
| 3 | Same cell OCR'd twice with different text | Log every disagreement to `ocr_stitch_disagreements`; resolution rule keeps higher-confidence (or flag for human review) |
| 4 | Bbox coordinate-transform bug | Tile offset persisted in `ocr_tile_manifests` (`offset_x_px`, `offset_y_px`); page-global coords computed deterministically; unit-tested |
| 5 | Reading order broken at seam | Run `surya_ordering` on full-page low-res; bind tile output by bbox spatial match |
| 6 | Whitespace-collapse ambiguity in Devanagari joins | Apply `_common/devanagari_normalization.py` substitution dict post-OCR |
| 7 | DPI inconsistency between tiles | Render entire page → split. Assert `dpi_consistent` per page in manifest |
| 8 | Confidence aggregation: false-confident wrong answer | Cross-tile consistency check: same text + high confidence both sides = `cross_validated`; same conf + different text = escalate |
| 9 | Devanagari ↔ Arabic numeral mixed cell | Post-OCR canonicalization preserves both representations losslessly (`numeral_arabic` + `numeral_devanagari` columns) |
| 10 | Tile boundary mid merged cell | Layout-aware tiling: never cut through a detected cell. Cells wider than one tile escalate to PaddleOCR or human review |
| 11 | Cell partial-overlap dedup error | Spatial IoU > 0.5 = same cell; keep one |
| 12 | Page-level metadata loss across tiles | `cell_extraction.table_region_id` ties cells back to layout pass; full provenance to `source_document_id` + `parser_run_id` |

The OCR tracking tables shipped in migration 0002 (`ocr_tile_manifests`, `ocr_cell_extractions`, `ocr_stitch_disagreements`) persist exactly the data these mitigations require for post-hoc operator review.

### 6. Routing rule (finalized by Worker δ evidence)

> **Default**: Surya 384 DPI 2×2 tiled with 80 px overlap.
>
> **Fall through to PaddleOCR** when:
> - Page is detected as Devanagari-dominant AND mean Surya confidence < **TBD** (set by Worker δ)
> - OR tile-seam disagreement rate exceeds **TBD per 100 cells** (set by Worker δ)
> - OR Surya returns null text for ≥ 5% of detected cells (issue #475 regression signal)
>
> **Pure-English pages**: Surya flat 192 DPI is sufficient.
>
> **Above-the-stress-tier pages** (Red Book budget pages, etc.): jump straight to 576 DPI 3×3 tiled.

The TBD thresholds are filled in when Worker δ's evaluation completes. Until then, parsers default to the 384 DPI tiled config with confidence-aware logging — they don't yet fall through to PaddleOCR.

### 7. Devanagari numeral handling — lossless dual representation

The Surya doc didn't tell us whether Devanagari numerals (०१२३४५६७८९) are preserved or normalized to Arabic (0123456789). Worker δ's empirical test answers this. Either way, our parsers handle it the same:

- **Always preserve both representations** in `ocr_cell_extractions.numeral_arabic` + `.numeral_devanagari`
- Compute the missing representation via deterministic substitution (lossless 1:1 map)
- Downstream queries (Fact Ledger, Pulse) use whichever script the consuming surface requires

### 8. Claude CLI spot-check workflow (dev-only; not production)

Per ADR-0003, Claude CLI is a dev assistant. The spot-check loop:

1. Parser run completes → all rows in `staging_indicator_values` + cell-extractions in `ocr_cell_extractions`
2. Dev (or Claude CLI assisting) loads N sampled rows by `near_tile_seam_px` (highest seam-proximity first — most likely to have artifacts)
3. Compare against source PDF; correct via the validator's manual-review workflow (per DATA_PIPELINE.md)
4. Substitution-dictionary additions go to `scrapers/_common/devanagari_normalization.py` with the source-PDF citation
5. Parser version bumps if extraction logic changed

A future tool (`scripts/spot-check-staging.ts`) automates loading the N most-suspicious cells alongside their PDF excerpts. Not in scope for this ADR.

## Alternatives Considered

### A. Surya flat at 192 DPI (the obvious default)
- Pro: simplest invocation; one inference pass per page
- Con: 192 DPI insufficient for Devanagari numerals in dense tables (user's instinct, validated by industry guidance)
- Rejected as the default; kept as the pure-English-page tier

### B. Different OCR for Devanagari (PaddleOCR primary, Surya secondary)
- Pro: PaddleOCR is reported to have better Devanagari support
- Con: Surya's layout + table-rec + reading-order are best-in-class and script-agnostic; replacing them costs visualization quality
- Rejected as the default; kept as Devanagari fallback per Worker δ evidence

### C. Cloud OCR (Google Document AI, Azure Form Recognizer)
- Pro: zero ops; reportedly better quality
- Con: ADR-0003 mandates no API calls in production parsers (cost, reproducibility, audit trail)
- Rejected

### D (chosen). Tile-based Surya default + PaddleOCR fallback + lossless numeral handling
- Stays compliant with ADR-0003 (deterministic, local, no API)
- Addresses every concrete failure mode raised by the user and the findings doc
- Empirically validated via Worker δ before the routing thresholds harden

## Consequences

### Positive
- Effective recognition DPI rises from 192 to 384 (or 576 in the stress tier) without Surya's segfault risk
- Devanagari diacritic clipping mitigated by overlap
- Confidence scores + stitch disagreements persisted = post-hoc debuggability via SQL
- Lossless numeral representation means downstream surfaces choose script freely

### Negative
- 4× to 9× more Surya inference per page (4 tiles for 2×2; 9 for 3×3)
- More disk/memory churn during parser runs
- Stitch logic adds ~200 lines of Python infrastructure per parser (one-time cost)

### Neutral / unknown (filled by Worker δ)
- The exact confidence threshold for falling through to PaddleOCR
- Whether tile-overlap of 80 px catches all diacritic-clip cases or we need 120 px
- Whether PaddleOCR's Devanagari quality justifies the dual-stack maintenance cost

## Implementation handles

- `scrapers/_common/surya_pipeline.py` (Phase B1 work; not yet shipped) — the orchestrator that takes a page image, runs layout, splits tiles, runs recognition, stitches, persists to `ocr_tile_manifests` + `ocr_cell_extractions`
- `scrapers/_common/devanagari_normalization.py` (shipped by Worker ε on `feat/scrapers-common-utils`) — the post-OCR substitution + numeral-script utilities
- `scrapers/_common/paddleocr_fallback.py` (Phase B1 work) — the fallback invocation, gated by the routing rule
- `docs/research/surya-ocr-findings.md` (shipped in PR #15)
- `docs/research/ocr-eval/EVALUATION_REPORT.md` (Worker δ output; pending) — the empirical basis for the threshold settings

## References

- [`docs/research/surya-ocr-findings.md`](../research/surya-ocr-findings.md)
- ADR-0003 (parsing policy — Claude CLI is dev-only, deterministic Python in production)
- `src/lib/db/schema/ocr-tracking.ts` (the tile/stitch tracking tables shipped in migration 0002)
- Issue [#475](https://github.com/datalab-to/surya/issues/475) — Devanagari regression
- Issue [#389](https://github.com/datalab-to/surya/issues/389) — DPI segfault cap
