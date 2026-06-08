# Source: Ministry of Finance — Historical intergovernmental fiscal transfer books

**source_id:** `mof-intergovernmental`
**Status:** active
**Tier:** Tier 4 (Phase B1)
**Registered at:** 2026-06-08
**Last verified:** 2026-06-08 (FY2078/79 + FY2079/80, text-layer reconciled)

> The historical federal→local-level fiscal transfer schedules (FY2074/75–
> 2082/83), in-repo as FY-coded PDFs. Powers the per-local-level transfer
> time-series that, with the FY2082/83 cleaned XLSX, becomes the spine of
> Vertical 10 (Local Ledger) + District MRI. Recovered under ADR-0021 (PDF
> recovery tiers) + ADR-0022 (the Surya harness + dual-channel design).

## Publication

- URL: https://mof.gov.np/  (also republished via NNRFC, https://nnrfc.gov.np/)
- Title: `अन्तरसरकारी वित्तीय हस्तान्तरण` (Intergovernmental Fiscal Transfer)
- Frequency: annual (one fiscal year per book)
- Format: pdf
- Reporting period type: annual
- Requires table extraction: yes

## Provenance

- Confidence default: B (recovered historical data; dual-validated — text-layer
  values + Surya cross-check, triple reconciliation)
- License: gov_open
- Ingestion mode: manual_upload
- Consumer: `scrapers/surya_ocr/parsers/intergovernmental.py` → `local_government_fiscal_transfers`
- Files in repo: `Financial Data/mof_documents/intergovernmental/207475.pdf … 208283.pdf`

## Data shape

Each book lists, per local level, the federal grant allocation broken into the
8 atomic components of Nepal's fiscal-federalism chart of accounts (the same
`grant_type` enum the FY2082/83 XLSX uses):

- Equalization (26331): minimum / formula-based / performance-based
- Conditional: current (26332) / capital (26336)
- Special: current (26333) / capital (26337)
- Complementary (26334): capital

Subtotal and grand-total columns are present but excluded on ingest (they are
derived, and shipping them would double-count). Printed unit is **NPR lakh**;
converted to **npr_crore** on ingest (÷10) so historical rows share the unit
with the FY2082/83 XLSX rows.

## Coverage + recovery status (per FY)

| FY (BS) | File | Text layer | Status |
|---|---|---|---|
| 2074/75 | 207475 | numbers not extractable | **deferred** — Surya-OCR-only |
| 2075/76 | 207576 | numbers not extractable | **deferred** — Surya-OCR-only |
| 2076/77 | 207677 | codes present, columns don't reconcile | **deferred** — needs layout work |
| 2077/78 | 207778 | numbers not extractable | **deferred** — Surya-OCR-only |
| 2078/79 | 207879 | **clean (753/753 reconcile)** | **shippable** |
| 2079/80 | 207980 | **clean (753/753 reconcile)** | **shippable** |
| 2080/81 | 208081 | numbers not extractable | **deferred** — Surya-OCR-only |
| 2081/82 | 208182 | fully scanned (1 image/page) | **deferred** — Surya-OCR-only |
| 2082/83 | 208283 | fully scanned (1 image/page) | already in DB via XLSX; PDF deferred |

The two shippable FYs reconcile at three levels: per-row (8 atomic components =
printed row grand total), document (sum of 753 grand totals = printed
`स्थानीय तह` total, to the rupee), and magnitude (FY2079/80 = NPR 300.4bn,
FY2078/79 = NPR 283.0bn — consistent with the FY2082/83 ~NPR 321bn baseline).

## Code crosswalk

The PDF uses a **9-digit** local-level code = the canonical **8-digit** federal
code + a trailing `3`. Verified 753/753 onto the seeded `entities` rows
(`kind='local_level'`); the parser strips the trailing digit. The code is the
entity join key — the text-layer Devanagari names are font-corrupted and
unneeded.

## Known breakage modes

- **Mixed page types within the corpus.** Only FY2078/79 + FY2079/80 have a
  usable numeric text layer; the rest are scanned or have a non-reconciling
  layout. A new FY must be probed before assuming the text-layer path applies.
- **Font-corrupted text-layer labels.** Devanagari labels drop matras in the
  embedded text layer; Surya OCR recovers them correctly. Never trust the
  text-layer label text — use the code (and Surya for display names).
- **Surya digit errors.** ~5–10% of numeric cells; this is why values come from
  the reconciling text layer, with Surya as cross-check (ADR-0022).
- **Column x-anchor jitter.** The detail-page numeric columns sit at stable x
  positions with small per-page jitter; the parser uses tolerant nearest-anchor
  matching. A book with a materially different layout (e.g. FY2076/77) won't
  reconcile and is refused.

## Revision policy

One-shot per fiscal year. Re-running is idempotent (ON CONFLICT DO NOTHING on
`(local_level_entity_id, fiscal_year_bs, grant_type)`). If MoF republishes a
book with corrections, a new `source_documents` row is created; conflicting
values open a ticket — never auto-overwrite. Scanned FYs are revisited when the
Surya OCR output for that FY reconciles end-to-end (ADR-0021 gate).
