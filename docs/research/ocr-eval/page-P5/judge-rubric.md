# Judge rubric — P5_old_redbook_p007

**Source PDF:** `Financial Data/mof_documents/redbook/Budget Details - Red Book 2062 - 2063_20130717120229_cbmey2a.pdf`
**Page index (0-based):** 7
**Description:** Worst scan — old (2062 BS) Red Book; low contrast, pixelated, slight rotation.

**Source crop:** [`source-crop.png`](./source-crop.png) (192 DPI)

---

## Per-pipeline scorecard

Scores 0-5 (5 = excellent). Fill in after eyeballing source-crop.png against each pipeline's JSON.

| Metric | A (Surya 192 flat) | B (Surya 384 2x2) | C (Surya 576 3x3) | D (PaddleOCR 300) |
|---|---:|---:|---:|---:|
| Cell recall (did it find the rows/cells that exist?) | | | | |
| Cell precision (any phantom cells / duplicates?) | | | | |
| Character error rate (subjective inverse: 5=clean, 0=garbled) | | | | |
| Numeral correctness | | | | |
| Devanagari diacritic preservation | | | | |
| Table structure preservation (row/column alignment) | | | | |

## Devanagari-numeral handling

| | A | B | C | D |
|---|---|---|---|---|
| Preserved Devanagari digits (०१२...)? | | | | |
| Normalized to Arabic digits (012...)? | | | | |
| Mixed? | | | | |

## Tile-seam artefacts (B, C only)

- B: ...
- C: ...

## Notes / surprises

- ...

## Winner (per-page rank 1-4)

1.
2.
3.
4.
