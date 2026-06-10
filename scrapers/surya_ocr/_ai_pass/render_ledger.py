#!/usr/bin/env python3
"""Render RECOVERY_LEDGER.json -> RECOVERY_LEDGER.md (a human dashboard).

The JSON is the source of truth (the nightly loop reads/updates it); this renders
a bounded, readable view for morning review: OCR state, the structural-decision
queue, a per-document completeness table, and the value-ordered "next up"
worklist. The full worklist lives in the JSON.

Run (stdlib only, any Python 3):
    python scrapers/surya_ocr/_ai_pass/render_ledger.py
"""
from __future__ import annotations

import argparse
import json
import os

TOP_WORKLIST = 30   # how many value-ranked pending candidates to spell out


def _unit(t):
    return t["unit_hint"] or "?"


def _hint(t):
    h = t["table_hint"]
    return ("p" + str(t["page_start"]) + " " + h) if h == "(untitled table)" else h


def render(L) -> str:
    o, s = L["ocr_state"], L["stats"]
    out = []
    w = out.append

    w("# Master Recovery Ledger — Overnight AI-pass worklist\n\n")
    w(f"> Generated: `{L['generated_utc']}` · Generator: `{L['generator']}`  \n")
    w(f"> Plan: `{L['plan']}` · Dedup baseline: {L['dedup_baseline']}  \n")
    w(f"> Status flow: `{L['status_flow']}`\n\n")
    w("**This file is generated** — do not hand-edit. The nightly loop updates "
      "`RECOVERY_LEDGER.json`; re-render with `render_ledger.py`.\n")

    # OCR state ---------------------------------------------------------------
    w("\n## OCR state\n\n")
    prog = f"{o['pages_present']:,} / {o['pages_target']:,} pages"
    w(f"- Corpus OCR: **{prog}**"
      + (" — ⏳ **IN PROGRESS** (re-run the locator after it finishes to pick up new pages)"
         if o["in_progress"] else " — ✅ complete") + "\n")
    if o["docs_pending_ocr"]:
        w(f"- Pending OCR (0 pages yet, no candidates until done): "
          + ", ".join(f"`{d}`" for d in o["docs_pending_ocr"]) + "\n")
    if o["docs_partial_ocr"]:
        w(f"- Partial OCR (scanned so far): "
          + ", ".join(f"`{d}`" for d in o["docs_partial_ocr"]) + "\n")

    # Summary -----------------------------------------------------------------
    w("\n## Summary\n\n")
    w(f"- Documents: **{s['docs']}** · Table candidates: **{s['table_candidates']}** "
      f"(**{s['pending_candidates']}** pending)\n")
    w("- By dedup class:\n")
    for k, v in sorted(s["table_candidates_by_dedup_class"].items(), key=lambda kv: -kv[1]):
        w(f"  - `{k}`: {v}\n")
    w("\nDedup classes: `new` = not in DB → recover · `partly-in-db` = some FYs/measures "
      "present, cross-check before promote · `owned-deterministic` = a deterministic parser "
      "owns this domain (OCR is cross-check only) · `needs-decision` = structural blocker · "
      "`unknown` = triage.\n")

    # Needs-decision queue ----------------------------------------------------
    nd = [d for d in L["docs"] if d["dedup"]["class"] == "needs-decision"]
    if nd:
        w("\n## ⚠️ Structural-decision queue (do NOT auto-decide — escalate)\n\n")
        for d in nd:
            w(f"- **`{d['out_dir']}`** ({d['tier_code']}, {d['source_pdf']}) — "
              f"OCR {d['ocr_status']} {d['pages_ocrd']}/{d['pages_total']}, "
              f"{d['table_candidate_count']} candidate(s).  \n")
            w(f"  {d['dedup']['note']}  \n")
            w("  _Recommendation:_ recover + stage the matrix (reconcile to the printed "
              "total) but **queue the structural decision for the human**; never fabricate "
              "to fit the current schema.\n")

    # Already recovered -------------------------------------------------------
    done = [t for t in L["tables"] if t["status"] in ("promoted", "staged")]
    if done:
        w("\n## Already recovered (audit trail — excluded from the worklist)\n\n")
        w("| id | status | doc | page(s) | artifact |\n|---|---|---|---|---|\n")
        for t in done:
            pg = t["page_start"] if t["page_start"] == t["page_end"] else f"{t['page_start']}–{t['page_end']}"
            w(f"| `{t['id']}` | **{t['status']}** | `{t['out_dir']}` | {pg} | `{t['artifact_path']}` |\n")

    # Per-document completeness ----------------------------------------------
    w("\n## Documents (completeness backbone — every OCR'd doc)\n\n")
    w("| Tier | Document | OCR | Pages | Tbl-pg | Cand | Dedup | Owner / note |\n")
    w("|---|---|---|--:|--:|--:|---|---|\n")
    for d in sorted(L["docs"], key=lambda d: (d["tier_code"], -d["pages_total"])):
        owner = d["dedup"]["owner"] or "—"
        w(f"| {d['tier_code']} | `{d['out_dir']}` | {d['ocr_status']} | "
          f"{d['pages_ocrd']}/{d['pages_total']} | {d['table_page_count']} | "
          f"{d['table_candidate_count']} | {d['dedup']['class']} | {owner} |\n")

    # Worklist next-up --------------------------------------------------------
    pend = [t for t in L["tables"] if t["status"] == "pending"]
    w(f"\n## Next up — top {min(TOP_WORKLIST, len(pend))} of {len(pend)} pending (value order)\n\n")
    w("| # | id | tier | doc | page(s) | unit | num-lines | coarse | dedup | hint |\n")
    w("|--:|---|---|---|---|---|--:|:-:|---|---|\n")
    for i, t in enumerate(pend[:TOP_WORKLIST], 1):
        pg = t["page_start"] if t["page_start"] == t["page_end"] else f"{t['page_start']}–{t['page_end']}"
        coarse = "⚠️" if t["signals"]["coarse_run"] else ""
        w(f"| {i} | `{t['id']}` | {t['tier_code']} | `{t['out_dir'][:30]}` | {pg} | "
          f"{_unit(t)} | {t['signals']['numeric_lines']} | {coarse} | {t['dedup']['class']} | "
          f"{_hint(t)[:60]} |\n")

    # Remaining pending by tier ----------------------------------------------
    w("\n## Remaining pending by tier\n\n")
    by_tier = {}
    for t in pend:
        by_tier.setdefault(t["tier_code"], [0, 0])
        by_tier[t["tier_code"]][0] += 1
        by_tier[t["tier_code"]][1] += t["signals"]["numeric_lines"]
    w("| Tier | Pending candidates | Σ num-lines |\n|---|--:|--:|\n")
    for tier in sorted(by_tier):
        c, nl = by_tier[tier]
        w(f"| {tier} | {c} | {nl:,} |\n")

    return "".join(out)


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(here, "RECOVERY_LEDGER.json"))
    ap.add_argument("--out", default=os.path.join(here, "RECOVERY_LEDGER.md"))
    args = ap.parse_args(argv)
    with open(args.json, encoding="utf-8") as fh:
        ledger = json.load(fh)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(render(ledger))
    print(f"rendered -> {os.path.relpath(args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
