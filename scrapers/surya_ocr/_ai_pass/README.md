# `_ai_pass/` — Overnight AI-pass over the Surya-OCR corpus

This directory holds the **dev-time AI-pass** that turns raw Surya-OCR output
(`../_ocr_output/`) into clean, reconciled, provenance-tagged facts — **without
fabricating anything** (ADR-0003: AI is QA, not the source of digits). Read
[`../AI_PASS_BRIEF.md`](../AI_PASS_BRIEF.md) for the full contract and
[`docs/OVERNIGHT_AI_PASS_PLAN.md`](../../../docs/OVERNIGHT_AI_PASS_PLAN.md) for the
methodical-recovery plan.

## The Master Recovery Ledger (build step 1)

The ledger is the **methodical backbone**: every `(document → table-region)`
across the OCR'd corpus, value-ordered, deduped against the documented truth
layer, with the OCR-in-progress state recorded. The nightly loop walks it; you
promote in the morning.

- **`RECOVERY_LEDGER.json`** — source of truth. The nightly loop reads it and
  updates each table's `status` / `reconciliation_result` / `artifact_path`.
- **`RECOVERY_LEDGER.md`** — generated human dashboard (do not hand-edit).

### Build / re-build

Run from the **repo root** with Python 3.12 (a neutral cwd avoids the package's
`types.py` shadowing stdlib; `PYTHONUTF8=1` for Devanagari):

```
python scrapers/surya_ocr/_ai_pass/locate_tables.py      # scan -> RECOVERY_LEDGER.json
python scrapers/surya_ocr/_ai_pass/render_ledger.py      # JSON -> RECOVERY_LEDGER.md
```

`locate_tables.py` reads the **current** OCR state, so re-run it after the
overnight Surya OCR finishes more pages. It is **idempotent + resumable**: ids
are stable (derived from `doc + first page`), and a re-run **preserves** any
non-locator status the loop/human set (use `--no-merge` to force a clean
rebuild). Useful flags: `--calib` (per-doc summary to stderr), `--only <substr>`
(scan one doc).

### How it locates tables

Per page: numeric-density detection + title/anchor grep (`अनुसूची`/`तालिका`/
section numbers like `५.४`, English `Table`/`Statement`/`Details of`) + printed
unit header (`रु. लाखमा`, `Rs. in '00000'`). Consecutive table pages segment into
titled units; a new title or a non-table page closes a unit. Section-number
splitting is **category-aware** — annex/section docs (economic survey, yellowbook,
intergovernmental) split per section; a redbook is one dataset (budget-head ×
{total,recurrent,capital}) so only explicit title words split it.

This is a **locator, not an extractor**: it points the recovery Workflow at
regions and ranks them; precise boundaries + cell values are the Workflow's job.

### Dedup model

Baseline is [`docs/DATA_AUDIT.md`](../../../docs/DATA_AUDIT.md) (the documented,
machine-verified truth-layer inventory) + the recovered `_ai_pass` artifacts.
This worktree's `.env.local` still points at the retired online Supabase and the
local-Postgres migration (ADR-0006) is on a later branch, so a **live** DB query
here is unreliable — the nightly loop / morning promotion re-checks live via
`pnpm audit:data`. Per-table dedup classes:

| class | meaning |
|---|---|
| `new` | not in the DB → recover |
| `partly-in-db` | some FYs/measures present → cross-check before promoting |
| `owned-deterministic` | a deterministic parser owns this domain (OCR = cross-check only) |
| `needs-decision` | structural blocker (e.g. 4-aggregate-grant) → escalate, never auto-decide |
| `unknown` | triage |

### Status flow

`pending → scoped → {recovered | quarantined | needs-decision} → staged → [promoted-by-human]`

Recovery is reconciliation-gated: Σ(components) must equal the document's printed
total or the table is quarantined — never fabricated, never force-reconciled.
