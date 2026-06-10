# Overnight AI-Pass — methodical recovery of the ENTIRE OCR'd corpus

**Status:** Plan (approved 2026-06-10). **Owner:** Mother + the `ocr-table-recovery` Workflow.
**Mandate (user, verbatim intent):** work *methodically on **all** the documents that have been OCR'd* —
every reconcilable table recovered, reconciled, and staged; nothing skipped; auditable progress;
**you promote in the morning** (no unattended DB writes). Budget: **run it down (~60M+ tokens/night)**.

This mirrors the proven overnight **OCR runner** (`scrapers/surya_ocr/`): prioritized · checkpointed ·
resumable · supervised. The work-unit is now the recovery Workflow instead of Surya OCR.

---

## The five hard rules (each is a scar from the 2026-06-10 session)

1. **No unattended DB writes or schema changes.** The night only *recovers + stages* artifacts
   (`verified_matrix.json` + reconciliation report per table) and writes a **morning report**. The
   human promotes + makes structural decisions in the AM. (A workflow gate-agent overstepped this
   boundary and silently ran an ingest — never again.)
2. **Reconciliation is the only trust.** Σ(components) = the document's printed total, or the table is
   **quarantined**. Never fabricated, never zero-filled, never force-reconciled.
3. **Magnitude sanity on every table (ADR-0011).** Catches unit bugs (a real 10× lakh/crore error was
   caught this way). Cross-check against the live DB where an anchor exists (e.g. national GDP).
4. **Structural decisions queue — never auto-decided.** New enum/ADR/migration needs (e.g. FY2077/78's
   4-aggregate-grant block) go to the morning report with a recommendation, not into the schema.
5. **Bounded · checkpointed · resumable · cost-capped.** A per-night token budget stops the run; a
   supervisor restarts on crash and resumes from the last ledger checkpoint.

---

## Architecture

```
[Master Recovery Ledger]──▶[Supervised nightly loop]──per table──▶[Workflow: scope→verify→repair→GATE]
 every doc × every table        ↓ checkpoint each entry            reconciles? ─yes─▶ stage artifact
 value-ordered, deduped         ↓                                            └─no──▶ quarantine + reason
                         [Morning report] ◀──────── [Human review (AM): promote / decide / triage]
```

### 1. Master Recovery Ledger (the methodical backbone)
A tracked manifest of **every (document → table)** across `_ocr_output`. One row per table:
`doc · page(s) · table-hint · status · reconciliation_result · artifact_path · notes`.
Status flow: `pending → scoped → {recovered | quarantined | needs-decision} → staged → [promoted-by-human]`.
Built once by a **table-locator scan** (annex/title grep + dense-page detection) over all OCR'd docs,
**deduped against the live DB** (skip measures already promoted). This guarantees completeness +
auditability + resumability. Lives at `scrapers/surya_ocr/_ai_pass/RECOVERY_LEDGER.json` (+ a readable .md).

### 2. The nightly loop (supervised)
A supervisor (`run_ai_pass_overnight.ps1`, modeled on `run_overnight.ps1`) keeps a Mother session
walking the ledger in value-order. Per `pending` table: run the Workflow → read the gate → update the
ledger (stage / quarantine / queue-decision) → checkpoint → next. Runs until the token budget or the
ledger is exhausted. Crash → supervisor relaunches → resumes at the next `pending` (skip-if-done).

### 3. Recover + stage only (your decision)
Reconciled tables produce a staged `verified_matrix.json` + a ready-to-run ingest command in the
report. The **morning report** (`_ai_pass/REPORTS/<date>.md`) sections: **READY TO PROMOTE** (headline
numbers + ingest cmd), **QUARANTINED** (+ reason), **NEEDS DECISION** (+ recommendation), token spend,
ledger progress (N done / M total).

### 4. Gates (all four, every table)
reconciliation (hard) · magnitude sanity · DB dedup · no-fabrication. A table failing any gate is
quarantined with the reason — it is never promoted and never guessed.

---

## The corpus = "all documents that have been OCR'd" (`_ocr_output/`)
Value-first order (P0→P5); the ledger scan reads the **current** OCR state at build time.

- **P0** — intergovernmental FY2077/78 (scanned; *4-aggregate-grant → needs-decision*), **SOE review 2081**
  (`ksi3tbe`, 402pp), scanned agreements/commitments/progress reports.
- **P1** — Yellow Books (समीक्षा २०७९/२०८०, BIG 2080, संक्षिप्त झलक editions; ~1,247pp). *Nested per-SOE
  financial statements → need the workflow extension.*
- **P2** — Economic Survey 2080-81 + 2081-82 (Nepali; ~1,064pp). *Annex 13.1 GVA already done; the rest
  of the statistical annex (provincial fiscal 13.6–13.8, social-sector, prices, trade) remain.*
- **P3** — White Book foreign aid (Preeti; ~942pp). donor==sector reconciliation gate.
- **P4** — Red Books, federal budget detail (~9,553pp — the bulk → **many nights**). recurrent+capital==total.
- **P5** — misc Devanagari (~41pp).

The ledger turns this into a methodical, resumable, multi-night march — nothing is cherry-picked or lost.

---

## Build sequence (to enable the first night) — ~3–4 focused sessions
1. **Table-locator scan → Master Recovery Ledger** (covers every OCR'd doc; dedup vs live DB).
2. **Extend `ocr-table-recovery`** for **nested-subtotal + multi-page** tables (the SOE/redbook detail;
   the current model is flat single-page). Also: validate the cross-column **repair** phase live (it's
   implemented but never executed end-to-end).
3. **Driver loop + supervisor + morning report** (`run_ai_pass_overnight.ps1` + the ledger updater).
4. **Implement local-FS storage (ADR-0006)** so morning-promotion isn't blocked — `@/lib/storage` still
   routes to Supabase; the oversized Yellow Book PDF can't archive. (Or keep promotion fully manual.)
5. **Dry-run** on one P0 doc end-to-end (ledger → loop → stage → report), tune, then launch full nights.

## First night (once built)
Start the ledger at **P0** (SOE review 2081 + the intergovernmental scanned FY) and let value-order +
the budget run it down. Each morning: review the report, promote the READY pile, decide the queued
structural items, and re-launch — the ledger marches forward until the corpus is exhausted.
