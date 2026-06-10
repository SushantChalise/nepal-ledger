#!/usr/bin/env python3
"""Deterministic SOE-yellowbook table extractor (route-smart, build of the cheap path).

The P1 SOE yellowbooks (2079 `ab0trdn`, 2080 `brzjuc2`/BIG-2080) have a usable
text layer: the table NUMERIC CELLS are clean digits (the prose/ligatures carry
PUA-font corruption, but the table values do not). So the sector×fiscal-year
summary tables (तालिका ३.x: operating income, net profit, net worth, …) are
recoverable WITHOUT LLM-OCR — fitz bbox reconstruction + digit normalization +
the Σ(6 sectors)=कुल जम्मा reconciliation gate. Cents per page vs ~1M tokens.

This is the deterministic analogue of `ocr_table_recovery.js`: it ships ONLY a
table that reconciles to its printed कुल जम्मा total; otherwise it quarantines
with a reason. **No DB writes** — stages `verified_matrix.json`; promotion is the
human's gate (extraction_method=`textlayer-deterministic`, confidence B).

Scope: the 6-sector × N-fiscal-year summary tables with a कुल जम्मा total row.
The 6 sectors are standard + fixed-order in these books:
  औद्योगिक / व्यापारिक / सेवा / सामाजिक / जनोपयोगी / वित्तीय
(industrial / commercial / service / social / utility / financial).

Run (from repo root, Python 3.12, PYTHONUTF8=1):
    python scrapers/surya_ocr/_ai_pass/deterministic_yellowbook.py \
        --pdf "<yellowbook.pdf>" --page 54 --out <out_dir> [--unit npr_lakh]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from _common.devanagari_normalization import to_arabic_numerals, normalize_devanagari_text  # noqa: E402

import fitz  # noqa: E402

# canonical fixed-order sectors (the data rows above कुल जम्मा), with EN labels
CANONICAL_SECTORS = [
    ("औद्योगिक", "industrial"),
    ("व्यापारिक", "commercial"),
    ("सेवा", "service"),
    ("सामाजिक", "social"),
    ("जनोपयोगी", "utility"),
    ("वित्तीय", "financial"),
]
_TOTAL_RE = re.compile(r"जम्मा")
_FY_RE = re.compile(r"^[०-९0-9]{4}\s*/\s*[०-९0-9]{2,4}$")  # 2073/74
ROW_TOL = 4       # px: spans within this y-distance are one row
RECON_TOL = 2     # lakh rounding tolerance for Σ(sectors)==कुल जम्मा


def _num(text: str):
    """Parse a clean numeric cell -> int/float, or None. Parens anywhere = negative
    (financial loss convention), commas/%/spaces stripped."""
    t = to_arabic_numerals(text).strip()
    neg = "(" in t or ")" in t
    t = re.sub(r"[()%,\s]", "", t)
    if not re.fullmatch(r"-?\d+(\.\d+)?", t):
        return None
    v = float(t) if "." in t else int(t)
    return -abs(v) if neg else v


def fold_parens(cells):
    """Fold parenthesized negatives that the text layer split across spans, e.g.
    "(", "3,937", ")"  ->  "(3937)" at the number's x. cells = [(x, text)] sorted by x."""
    out, i, n = [], 0, len(cells)
    while i < n:
        x, t = cells[i]
        ts = to_arabic_numerals(t).strip()
        # case: bare "(" then number then ")"  (3 spans)
        if ts == "(" and i + 2 < n and to_arabic_numerals(cells[i + 2][1]).strip() == ")":
            out.append((cells[i + 1][0], "(" + cells[i + 1][1] + ")"))
            i += 3
            continue
        # case: "(" then number")" or "(number" then ")"  (2 spans)
        if ts == "(" and i + 1 < n:
            out.append((cells[i + 1][0], "(" + cells[i + 1][1] + ")"))
            i += 2
            continue
        out.append((x, t))
        i += 1
    return out


def _spans(page):
    out = []
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            for sp in ln.get("spans", []):
                t = sp["text"].strip()
                if t:
                    out.append((round(sp["bbox"][1]), round(sp["bbox"][0]), t))
    out.sort()
    return out


def _rows(spans):
    rows, cur, ly = [], [], None
    for y, x, t in spans:
        if ly is None or abs(y - ly) <= ROW_TOL:
            cur.append((x, t))
        else:
            rows.append((ly, sorted(cur)))
            cur = [(x, t)]
        ly = y
    if cur:
        rows.append((ly, sorted(cur)))
    return rows


def extract(pdf_path, page_index, unit_hint):
    doc = fitz.open(pdf_path)
    rows = _rows(_spans(doc[page_index]))

    # 1) header row: the one whose cells are mostly FY labels (2073/74 ...)
    header, header_y = None, None
    for y, cells in rows:
        fys = [(x, to_arabic_numerals(t)) for x, t in cells if _FY_RE.match(to_arabic_numerals(t).replace(" ", ""))]
        if len(fys) >= 3:
            header, header_y = sorted(fys), y
            break
    if not header:
        return {"found": False, "reason": "no fiscal-year header row (>=3 FY labels) found"}
    col_x = [x for x, _ in header]
    col_labels = [lbl for _, lbl in header]

    def assign(cells):
        """map a row's numeric cells to the nearest header column -> {col_idx: value}."""
        vals = {}
        for x, t in fold_parens(cells):
            v = _num(t)
            if v is None:
                continue
            ci = min(range(len(col_x)), key=lambda i: abs(col_x[i] - x))
            if abs(col_x[ci] - x) <= 40:  # within a column's horizontal band
                vals[ci] = v
        return vals

    # 2) sectors = numeric rows BETWEEN the header and the कुल जम्मा total row.
    #    Stop at the total so post-total rows (growth-rate %, 5-yr average) are excluded.
    sectors, total = [], None
    for y, cells in rows:
        if y <= header_y:  # skip the header row and everything above it
            continue
        nums = assign(cells)
        if len(nums) < 2:
            continue
        label_raw = " ".join(t for x, t in cells if _num(t) is None)
        label = normalize_devanagari_text(label_raw).strip()
        rec = {"label_raw": label, "values": nums}
        if _TOTAL_RE.search(label) or _TOTAL_RE.search(label_raw):
            total = rec
            break
        sectors.append(rec)

    if total is None:
        return {"found": False, "reason": "no कुल जम्मा total row found"}
    if len(sectors) != len(CANONICAL_SECTORS):
        return {"found": False, "reason": f"expected {len(CANONICAL_SECTORS)} sector rows, got {len(sectors)} "
                f"(labels: {[s['label_raw'][:12] for s in sectors]}) — not a standard 6-sector table"}
    for i, rec in enumerate(sectors):
        rec["sector_ne"], rec["sector_en"] = CANONICAL_SECTORS[i]

    # 3) reconcile per column: Σ(sectors) == कुल जम्मा total
    recon = []
    accepted_cols, worst = [], 0
    for ci, lbl in enumerate(col_labels):
        s = sum(r["values"].get(ci, 0) for r in sectors)
        tot = total["values"].get(ci)
        if tot is None:
            recon.append({"col": lbl, "reconciles": False, "reason": "no total cell"})
            continue
        resid = round(s - tot, 2)
        ok = abs(resid) <= RECON_TOL
        worst = max(worst, abs(resid))
        recon.append({"col": lbl, "sum_sectors": s, "printed_total": tot, "residual": resid, "reconciles": ok})
        if ok:
            accepted_cols.append(ci)
    return {
        "found": True,
        "unit": unit_hint or "npr_lakh",
        "fiscal_years": col_labels,
        "sectors": sectors,
        "total": total,
        "reconciliation": recon,
        "accepted_columns": [col_labels[ci] for ci in accepted_cols],
        "worst_residual": worst,
        "all_columns_reconcile": len(accepted_cols) == len(col_labels),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--unit", default="npr_lakh")
    ap.add_argument("--table-hint", default="")
    args = ap.parse_args(argv)

    res = extract(args.pdf, args.page, args.unit)
    os.makedirs(args.out, exist_ok=True)
    artifact = {
        "source_pdf": args.pdf,
        "source_page": args.page,
        "table_hint": args.table_hint,
        "extraction_method": "textlayer-deterministic",
        "confidence_grade": "B",
        **res,
    }
    path = os.path.join(args.out, "verified_matrix.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, ensure_ascii=False, indent=2)
    if res.get("found"):
        print(f"page {args.page}: {len(res['sectors'])} sectors x {len(res['fiscal_years'])} FY; "
              f"reconciles={res['all_columns_reconcile']} worst_residual={res['worst_residual']}; "
              f"accepted cols {res['accepted_columns']} -> {os.path.relpath(path)}")
    else:
        print(f"page {args.page}: NOT a sector×FY total table ({res['reason']}) -> {os.path.relpath(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
