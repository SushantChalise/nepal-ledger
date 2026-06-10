#!/usr/bin/env python3
"""Table-locator scan -> Master Recovery Ledger (Overnight AI-pass, build step 1).

Deterministic, stdlib-only, re-runnable scan over the *current* Surya-OCR output
(`_ocr_output/`). It does NOT touch the DB and does NOT extract any values -- it
builds the methodical worklist the nightly recovery loop walks:

  every (document -> table-region) across the OCR'd corpus,
  value-ordered, deduped against the documented truth layer + already-recovered
  `_ai_pass` artifacts, with the OCR-in-progress state recorded.

How it finds tables (per docs/OVERNIGHT_AI_PASS_PLAN.md): "annex/title grep +
dense-page detection". Per page it computes a numeric-density signal and greps
for table anchors (Devanagari `अनुसूची`/`तालिका`/section numbers like `५.४`,
English `Table`/`Annex`/`Statement`/`Details of`) and the printed unit header
(`रु. लाखमा`, `Rs. in '00000'`, ...). Consecutive table pages are segmented into
titled table units; a new title or a non-table page closes the current unit.

This is a *locator*, not an extractor: it points the recovery Workflow at regions
and ranks them. Precise table boundaries + cell values are the Workflow's job.

Run (from repo root, neutral cwd so the package's `types.py` does not shadow
stdlib; use Python 3.12):

    python scrapers/surya_ocr/_ai_pass/locate_tables.py

Outputs (idempotent overwrite): `_ai_pass/RECOVERY_LEDGER.json`. The readable
`RECOVERY_LEDGER.md` is rendered by `render_ledger.py` from the same JSON.

CLI:
    --ocr-dir   path to _ocr_output (default: alongside this file)
    --out       path to RECOVERY_LEDGER.json (default: _ai_pass/RECOVERY_LEDGER.json)
    --only      substring filter on out_dir (debug; scan a subset)
    --calib     print a per-doc calibration summary to stderr
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import json
import os
import re
import sys

# --- tuning constants (a page is a "table page" if it clears these) -----------
MIN_LINES = 12            # ignore near-blank / divider pages
NUMERIC_MIN = 10          # min pure-numeric lines to count as a table page
RATIO_MIN = 0.18          # min numeric / total line ratio
UNIT_NUMERIC_MIN = 5      # a printed unit header + this many numbers also counts
LARGE_UNIT_PAGES = 40     # flag oversized untitled runs for sub-scoping
HINT_MAXLEN = 90          # truncate the stored table-hint string

# --- digit / markup helpers ---------------------------------------------------
_DEV_DIGITS = "०१२३४५६७८९"
_DEV2LAT = {ord(d): str(i) for i, d in enumerate(_DEV_DIGITS)}
_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")          # strip OCR <b>..</b> markup
_NUM_HAS_DIGIT = re.compile(r"[0-9]")
# after folding Devanagari->Latin, a "numeric cell" is digits + grouping/sep only
_NUM_STRIP = re.compile(r"[0-9\s,.\-–%()\[\]/:]+")


def fold_digits(s: str) -> str:
    return s.translate(_DEV2LAT)


def clean(s: str) -> str:
    return _TAG_RE.sub("", s).strip()


def is_numeric_line(text: str) -> bool:
    """True if the (cleaned) line is just a number/percent/range/date-ish cell."""
    s = clean(text)
    if not s:
        return False
    folded = fold_digits(s)
    if not _NUM_HAS_DIGIT.search(folded):
        return False
    return _NUM_STRIP.sub("", folded) == ""


# --- anchor (title) + unit detection ------------------------------------------
_DEV_TITLE = re.compile(r"(अनुसूची|अनुसुची|तालिका|परिशिष्ट|महलेख|विवरणपत्र)")
_EN_TITLE = re.compile(r"\b(Table|Annex(?:ure)?|Schedule|Appendix|Statement|Details\s+of)\b", re.I)
# a section-number heading token, e.g. ५.४ / 13.1 / २.१४ (1-2 digit groups)
_SEC_NUM = re.compile(r"(?<![0-9])([0-9]{1,2}\.[0-9]{1,3}(?:\.[0-9]{1,3})?)(?![0-9])")
_TOTAL_KW = re.compile(r"(जम्मा|कुल|कूल|योग|समग्र|Grand\s*Total|Total)", re.I)
_LETTERS = re.compile(r"[^\W\d_]", re.UNICODE)  # any-script letter (incl. Devanagari)

# unit header patterns, most-specific first; value = canonical unit token
_UNIT_PATTERNS = [
    (re.compile(r"Rs\.?\s*in\s*'?0{7,}'?", re.I), "crore(0000000)"),
    (re.compile(r"Rs\.?\s*in\s*'?0{5}'?", re.I), "lakh(00000)"),
    (re.compile(r"Rs\.?\s*in\s*'?0{3}'?", re.I), "thousand(000)"),
    (re.compile(r"Rs\.?\s*in\s*crore", re.I), "crore"),
    (re.compile(r"Rs\.?\s*in\s*million", re.I), "million"),
    (re.compile(r"Rs\.?\s*in\s*lakh", re.I), "lakh"),
    (re.compile(r"Rs\.?\s*in\s*thousand", re.I), "thousand"),
    (re.compile(r"करोड"), "crore"),
    (re.compile(r"अरब"), "arba_billion"),
    (re.compile(r"लाख"), "lakh"),
    (re.compile(r"हजार"), "thousand"),
]


def detect_unit(text: str):
    for pat, tok in _UNIT_PATTERNS:
        if pat.search(text):
            return tok
    return None


TOP_BAND_FRAC = 0.30      # section-number headings only count in the top of a page


def title_anchor(text: str):
    """Classify a line as a table-title anchor.

    Returns ``(kind, heading)`` where kind is:
      - ``"word"``  : an explicit title word (अनुसूची/तालिका/Table/Statement/...) —
        unambiguous, qualifies as a heading anywhere on the page.
      - ``"secnum"``: a bare section-number heading (e.g. `५.४ <title text>`) — only
        a real heading when near the top of the page (mid-page `X.Y` tokens are row
        codes in budget books and must NOT split a table). The caller gates these
        by y-position.
    A section-number heading must carry non-numeric text after the number, so a
    data row that merely starts with `5.4` is never an anchor. Returns None
    otherwise."""
    s = clean(text)
    if not s:
        return None
    if _DEV_TITLE.search(s) or _EN_TITLE.search(s):
        return ("word", s[:HINT_MAXLEN])
    folded = fold_digits(s)
    m = _SEC_NUM.match(folded)
    if m and len(s) <= HINT_MAXLEN:
        # require real title text after the number (>=3 letters) so a garbled
        # numeric row like "3.5.5.0$" or "0.98 | 1316319.17" is not a heading
        if len(_LETTERS.findall(folded[m.end():])) >= 3:
            return ("secnum", s[:HINT_MAXLEN])
    return None


# --- per-page feature extraction ---------------------------------------------
class PageFeat:
    __slots__ = ("page", "n_lines", "n_numeric", "ratio", "unit", "has_total",
                 "anchors", "top_word", "top_secnum", "is_table")

    def __init__(self, page, n_lines, n_numeric, unit, has_total, anchors,
                 top_word, top_secnum):
        self.page = page
        self.n_lines = n_lines
        self.n_numeric = n_numeric
        self.ratio = (n_numeric / n_lines) if n_lines else 0.0
        self.unit = unit
        self.has_total = has_total
        self.anchors = anchors          # display list of heading strings (y-sorted)
        self.top_word = top_word        # topmost explicit-title-word heading, or None
        self.top_secnum = top_secnum    # topmost top-band section-number heading, or None
        self.is_table = (
            n_lines >= MIN_LINES
            and (
                (n_numeric >= NUMERIC_MIN and self.ratio >= RATIO_MIN)
                or (unit is not None and n_numeric >= UNIT_NUMERIC_MIN)
            )
        )


def scan_page(path: str):
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None  # mid-write or unreadable -> skip (re-run picks it up)
    lines = doc.get("text_lines") or []
    page = doc.get("page", 0)
    img = doc.get("image_px") or [0, 0]
    height = img[1] if len(img) > 1 else 0
    top_band = TOP_BAND_FRAC * height if height else None
    n_numeric = 0
    unit = None
    has_total = False
    words = []    # (y, heading) explicit-title-word anchors
    secnums = []  # (y, heading) top-band section-number anchors
    for ln in lines:
        txt = ln.get("text", "")
        if is_numeric_line(txt):
            n_numeric += 1
            continue
        if unit is None:
            unit = detect_unit(txt)
        if not has_total and _TOTAL_KW.search(clean(txt)):
            has_total = True
        a = title_anchor(txt)
        if a:
            kind, heading = a
            y = (ln.get("bbox") or [0, 0, 0, 0])[1]
            if kind == "word":
                words.append((y, heading))
            elif top_band is None or y <= top_band:  # bare section number near top
                secnums.append((y, heading))
    words.sort(key=lambda t: t[0])
    secnums.sort(key=lambda t: t[0])
    top_word = words[0][1] if words else None
    top_secnum = secnums[0][1] if secnums else None
    anchors = [h for _, h in sorted(words + secnums, key=lambda t: t[0])]
    return PageFeat(page, len(lines), n_numeric, unit, has_total,
                    anchors, top_word, top_secnum)


# --- segmentation: table pages -> titled table units --------------------------
# Section numbers split units only for annex/section-structured docs. A redbook
# is ONE dataset (budget-head x {total,recurrent,capital}); its per-page
# budget-head statements are repetitions of one schema, not separate tables, so
# only an explicit title-word starts a new unit there.
_SECNUM_SPLIT_CATEGORIES = {"economic_survey", "yellowbook", "intergovernmental"}


def segment(feats, allow_secnum_split: bool):
    units = []
    cur = None

    def close():
        nonlocal cur
        if cur is not None:
            units.append(cur)
            cur = None

    for f in feats:
        if not f.is_table:
            close()
            continue
        new_anchor = f.top_word or (f.top_secnum if allow_secnum_split else None)
        start_new = (
            cur is None
            or (new_anchor is not None and new_anchor != cur["hint"])
        )
        if start_new:
            close()
            cur = {
                "hint": new_anchor or "(untitled table)",
                "titled": new_anchor is not None,
                "page_start": f.page,
                "page_end": f.page,
                "anchors": list(dict.fromkeys(f.anchors)),
                "unit_hint": f.unit,
                "numeric_lines": f.n_numeric,
                "max_numeric_on_page": f.n_numeric,
                "has_total": f.has_total,
                "n_pages": 1,
            }
        else:
            cur["page_end"] = f.page
            cur["n_pages"] += 1
            cur["numeric_lines"] += f.n_numeric
            cur["max_numeric_on_page"] = max(cur["max_numeric_on_page"], f.n_numeric)
            cur["has_total"] = cur["has_total"] or f.has_total
            if cur["unit_hint"] is None:
                cur["unit_hint"] = f.unit
            for a in f.anchors:
                if a not in cur["anchors"]:
                    cur["anchors"].append(a)
    close()
    return units


# --- dedup classification (DATA_AUDIT.md + _ai_pass artifacts) -----------------
# Documented truth-layer coverage as of DATA_AUDIT.md (2026-06-08, +06-10 GVA).
# This is the *documented* proxy for the live DB: this worktree's .env.local
# still points at the retired online Supabase, and the local-Postgres migration
# (ADR-0006) is on a later branch -- so a live query here is unreliable. The
# nightly loop / morning promotion re-checks live via `pnpm audit:data`.
_DEDUP_BY_CATEGORY = {
    "whitebook": dict(
        cls="owned-deterministic",
        owner="mof_whitebook (Tier-1a, deterministic)",
        bias=-5000,
        note=("Foreign aid is recovered deterministically from the (Preeti/text-layer) "
              "source; DATA_AUDIT §5/§8: all 14 White Book editions reconcile "
              "(donor==sector per FY). OCR here is a cross-check only. The 3 gap FYs "
              "(2062/63, 2064/65, 2078/79) are still deterministic targets, not OCR."),
    ),
    "redbook": dict(
        cls="partly-in-db",
        owner="dne_facts budget-allocation (1 FY: 2074/75, 57 heads)",
        bias=0,
        note=("Federal budget detail. DB has only FY2074/75 (DATA_AUDIT §2). Every "
              "other edition is NEW. Gate: recurrent+capital==total per head; heads "
              "sum to the appropriation total. Bulk -> many nights."),
    ),
    "economic_survey": dict(
        cls="partly-in-db",
        owner="dne_facts economic-survey-gva-current (FY2081/82 annex 13.1, promoted)",
        bias=+40,
        note=("Macro statistical annex. GVA annex 13.1 / FY2081/82 already promoted "
              "(ADR-0023). Remaining annexes (provincial fiscal, prices, trade, "
              "constant-price GVA, FY2080/81) are NEW. Headline GDP/CPI already in DB."),
    ),
    "yellowbook": dict(
        cls="new",
        owner="dne_facts soe-* (only equity+loan, 1 FY 2080/81)",
        bias=+60,
        note=("SOE financials. DB has only government-share + loan-principal for 1 FY. "
              "Revenue / profit-loss / paid-up capital are all deferred (DATA_AUDIT §6) "
              "-> high value. Reconcile sub-components to per-enterprise + जम्मा totals."),
    ),
    "intergovernmental": dict(
        cls="needs-decision",
        owner="local_government_fiscal_transfers (5 FYs: 2078/79-2082/83)",
        bias=+50,
        note=("Intergovernmental fiscal transfers. The 5 recent FYs are in the DB; the "
              "corpus copies here are the *blocked* early FYs. Gate: Σ(753 local levels) "
              "== printed स्थानीय तह total. Likely 4-aggregate-grant schema block "
              "(DATA_AUDIT §6) -> structural decision, do not force into 8 atomic types."),
    ),
    "agreement": dict(
        cls="unknown",
        owner=None,
        bias=-200,
        note=("Scanned MoF agreement / commitment / progress / earthquake docs (mostly "
              "1 page). Structured-fact value unknown; let density decide, low priority."),
    ),
}
_DEFAULT_DEDUP = dict(cls="unknown", owner=None, bias=-100,
                      note="Uncategorised document; review manually.")

_TIER_WEIGHT = {0: 600, 1: 500, 2: 400, 3: 300, 4: 200, 5: 100}


def category_of(source_path: str) -> str:
    marker = "mof_documents/"
    if marker in source_path.replace("\\", "/"):
        return source_path.replace("\\", "/").split(marker, 1)[1].split("/", 1)[0]
    return "?"


def load_artifacts(ai_pass_dir: str):
    """Map already-recovered artifacts -> (source_pdf_basename, source_page, status, dir)."""
    out = []
    status_by_dir = {  # status is a human/decision fact, not derivable from the JSON
        "es2081_annex13_1": "promoted",   # GVA 13.1 -> dne_facts (ADR-0023)
        "es2081_annex13_1_wf": "promoted",
        "soe_2081_p79_pl": "staged",      # verified, ingest-ready, storage-blocked
    }
    for sub in sorted(os.listdir(ai_pass_dir)):
        d = os.path.join(ai_pass_dir, sub)
        if not os.path.isdir(d):
            continue
        for jf in glob.glob(os.path.join(d, "*.json")):
            try:
                with open(jf, encoding="utf-8") as fh:
                    j = json.load(fh)
            except (OSError, json.JSONDecodeError):
                continue
            sp = j.get("source_pdf")
            pg = j.get("source_page")
            if sp is None or pg is None:
                continue
            out.append({
                "basename": os.path.basename(str(sp)),
                "page": int(pg),
                "status": status_by_dir.get(sub, "staged"),
                "artifact": os.path.relpath(d, os.path.dirname(ai_pass_dir)).replace("\\", "/"),
            })
    return out


# --- main scan ----------------------------------------------------------------
# Statuses the locator may assign from ground truth; anything else on an existing
# entry was set by the nightly loop / a human and must be preserved on re-run.
_LOCATOR_STATUSES = {"pending", "promoted", "staged"}


def stable_id(out_dir: str, page_start: int) -> str:
    """Deterministic id from (doc, first page) so re-runs (OCR still growing) keep
    ids stable -- no churn, and the merge can carry forward loop/human progress."""
    sha8 = out_dir.rsplit("_", 1)[-1]
    return f"{out_dir.split('__', 1)[0]}_{sha8}_p{page_start:04d}"


def build_ledger(ocr_dir, ai_pass_dir, only, calib, prev_tables_by_id):
    man = json.load(open(os.path.join(ocr_dir, "_state", "manifest.json"), encoding="utf-8"))
    artifacts = load_artifacts(ai_pass_dir)
    docs, tables = [], []
    for e in sorted(man["entries"], key=lambda e: (e["priority"], -e["pages"])):
        out_dir = e["out_dir"]
        if only and only not in out_dir:
            continue
        src = e["path"]
        src_base = os.path.basename(src)
        cat = category_of(src)
        dd = dict(_DEDUP_BY_CATEGORY.get(cat, _DEFAULT_DEDUP))
        ddir = os.path.join(ocr_dir, out_dir)
        page_files = sorted(glob.glob(os.path.join(ddir, "page_*.json"))) if os.path.isdir(ddir) else []
        n_present = len(page_files)
        ocr_status = ("pending" if n_present == 0
                      else "complete" if n_present >= e["pages"] else "partial")
        # which already-recovered artifacts belong to this doc (keep the first
        # match per page -- load order is sorted, so a committed dir wins over a
        # later `*_wf` scratch variant of the same recovered table)
        art_pages = {}
        for a in artifacts:
            if a["basename"] == src_base:
                art_pages.setdefault(a["page"], a)

        feats = []
        for pf in page_files:
            f = scan_page(pf)
            if f is not None:
                feats.append(f)
        feats.sort(key=lambda f: f.page)
        units = segment(feats, allow_secnum_split=cat in _SECNUM_SPLIT_CATEGORIES)
        table_page_count = sum(1 for f in feats if f.is_table)

        for u in units:
            tid = stable_id(out_dir, u["page_start"])
            # is a recovered artifact inside this unit's page span?
            art = next((art_pages[p] for p in art_pages
                        if u["page_start"] <= p <= u["page_end"]), None)
            prev = prev_tables_by_id.get(tid)
            # status precedence: artifact (ground truth) > preserved loop/human
            # progress (a non-locator status) > pending.
            if art:
                status, recon, artifact_path = art["status"], None, art["artifact"]
            elif prev and prev.get("status") not in _LOCATOR_STATUSES:
                status = prev["status"]
                recon = prev.get("reconciliation_result")
                artifact_path = prev.get("artifact_path")
            else:
                status, recon, artifact_path = "pending", None, None
            size_bonus = min(u["numeric_lines"] / 200.0, 60.0)
            value_rank = _TIER_WEIGHT.get(e["priority"], 0) + dd["bias"] + size_bonus
            if status in ("promoted", "staged"):
                value_rank -= 10000  # already done -> sink, but keep for audit
            tables.append({
                "id": tid,
                "out_dir": out_dir,
                "source_path": src,
                "category": cat,
                "tier_code": f"P{e['priority']}",
                "page_start": u["page_start"],
                "page_end": u["page_end"],
                "n_pages": u["n_pages"],
                "table_hint": u["hint"],
                "titled": u["titled"],
                "anchors": u["anchors"][:8],
                "unit_hint": u["unit_hint"],
                "signals": {
                    "numeric_lines": u["numeric_lines"],
                    "max_numeric_on_page": u["max_numeric_on_page"],
                    "has_total_keyword": u["has_total"],
                    "coarse_run": u["n_pages"] >= LARGE_UNIT_PAGES,
                },
                "status": status,
                "reconciliation_result": recon,
                "artifact_path": artifact_path,
                "dedup": {"class": dd["cls"], "owner": dd["owner"]},
                "value_rank": round(value_rank, 2),
                "notes": ("recovered artifact present" if art else
                          "OCR incomplete for this doc" if ocr_status != "complete" else ""),
            })

        docs.append({
            "out_dir": out_dir,
            "source_path": src,
            "source_pdf": src_base,
            "category": cat,
            "tier_code": f"P{e['priority']}",
            "tier_label": e["tier"],
            "scanned": e["scanned"],
            "avg_words": e["avg_words"],
            "dev_ratio": e["dev_ratio"],
            "pages_total": e["pages"],
            "pages_ocrd": n_present,
            "ocr_status": ocr_status,
            "table_page_count": table_page_count,
            "table_candidate_count": len(units),
            "recovered_artifacts": sorted(
                {a["artifact"] for a in art_pages.values()}),
            "dedup": {"class": dd["cls"], "owner": dd["owner"],
                      "note": dd["note"], "baseline": "docs/DATA_AUDIT.md (2026-06-08/06-10)"},
        })
        if calib:
            print(f"P{e['priority']} {out_dir[:44]:44} ocr={ocr_status:8} "
                  f"pages={n_present}/{e['pages']:<4} tablepg={table_page_count:<4} "
                  f"units={len(units):<4} dedup={dd['cls']}", file=sys.stderr)

    tables.sort(key=lambda t: -t["value_rank"])
    pages_present = sum(d["pages_ocrd"] for d in docs)
    pages_target = sum(d["pages_total"] for d in docs)
    by_class = {}
    for t in tables:
        by_class[t["dedup"]["class"]] = by_class.get(t["dedup"]["class"], 0) + 1
    return {
        "schema_version": 1,
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "generator": "scrapers/surya_ocr/_ai_pass/locate_tables.py",
        "plan": "docs/OVERNIGHT_AI_PASS_PLAN.md",
        "dedup_baseline": "docs/DATA_AUDIT.md (2026-06-08 + 2026-06-10 GVA) + _ai_pass artifacts",
        "ocr_state": {
            "pages_present": pages_present,
            "pages_target": pages_target,
            "in_progress": pages_present < pages_target,
            "docs_pending_ocr": [d["out_dir"] for d in docs if d["ocr_status"] == "pending"],
            "docs_partial_ocr": [d["out_dir"] for d in docs if d["ocr_status"] == "partial"],
        },
        "status_flow": "pending -> scoped -> {recovered|quarantined|needs-decision} -> staged -> [promoted-by-human]",
        "stats": {
            "docs": len(docs),
            "table_candidates": len(tables),
            "table_candidates_by_dedup_class": by_class,
            "pending_candidates": sum(1 for t in tables if t["status"] == "pending"),
        },
        "docs": docs,
        "tables": tables,
    }


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="Build the Master Recovery Ledger.")
    ap.add_argument("--ocr-dir", default=os.path.join(os.path.dirname(here), "_ocr_output"))
    ap.add_argument("--out", default=os.path.join(here, "RECOVERY_LEDGER.json"))
    ap.add_argument("--ai-pass-dir", default=here)
    ap.add_argument("--only", default=None)
    ap.add_argument("--calib", action="store_true")
    ap.add_argument("--no-merge", action="store_true",
                    help="rebuild from scratch; do not preserve loop/human statuses")
    args = ap.parse_args(argv)

    prev_by_id = {}
    if not args.no_merge and os.path.exists(args.out):
        try:
            with open(args.out, encoding="utf-8") as fh:
                prev_by_id = {t["id"]: t for t in json.load(fh).get("tables", [])}
        except (OSError, json.JSONDecodeError, KeyError):
            prev_by_id = {}  # corrupt/old ledger -> fresh build

    ledger = build_ledger(args.ocr_dir, args.ai_pass_dir, args.only, args.calib, prev_by_id)
    ledger["merged_from_prev"] = len(prev_by_id) > 0
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, ensure_ascii=False, indent=2)
    s = ledger["stats"]
    o = ledger["ocr_state"]
    print(f"ledger: {s['docs']} docs, {s['table_candidates']} table candidates "
          f"({s['pending_candidates']} pending) -> {os.path.relpath(args.out)}")
    print(f"  OCR {o['pages_present']}/{o['pages_target']} pages"
          f"{' (IN PROGRESS)' if o['in_progress'] else ''}; "
          f"by dedup class: {s['table_candidates_by_dedup_class']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
