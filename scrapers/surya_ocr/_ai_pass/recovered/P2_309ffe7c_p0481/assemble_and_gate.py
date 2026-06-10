# Assemble the verified 25-row x 16-column matrix for Economic Survey 2081-82, page 481
# (Annex 13.7: Provincial Consolidated Fund annual financial statement) and apply the GATE.
#
# Table title : अनुसूची १३.७: प्रदेश सञ्चित कोषको वार्षिक आर्थिक विवरण
#               (Annex 13.7: Provincial Consolidated Fund Annual Financial Statement)
# Source      : Financial Data/mof_documents/economic_survey/Economic_Survey_2081-82.pdf, page 481
# Source doc  : P2__Economic_Survey_2081-82_309ffe7c
# Unit        : रु. करोडमा  (NPR in crore)
# Source cite : स्रोतः महालेखा नियन्त्रक कार्यालय  (Office of the Auditor General / FCGO)
# Extraction  : surya-ocr 0.17.1 ; confidence grade B.
#
# COLUMN LAYOUT (rebuilt from bbox x-bands; verified against the prompt's cross-column anchor):
#   FY2079/80: c0 कोशी, c1 मधेश, c2 बागमती, c3 गण्डकी, c4 लुम्बिनी, c5 कर्णाली, c6 सुदूरपश्चिम, c7 जम्मा(total)
#   FY2080/81: c8 कोशी, c9 मधेश, c10 बागमती, c11 गण्डकी, c12 लुम्बिनी, c13 कर्णाली, c14 सुदूरपश्चिम, c15 जम्मा(total)
#
# RECONCILIATION AXES (per task):
#  (1) WITHIN-COLUMN formula chain (applies to every one of the 16 columns):
#        r0  = r1 + r4 + r8
#        r1  = r2 + r3
#        r4  = r5 + r6 + r7
#        r9  = r10
#        r11 = r0 + r9
#        r13 = r14 + r15
#        r16 = r17 + r18 + r19
#        r12 = r13 + r16
#        r21 = r12 + r20
#        r22 = r11 - r21
#        r24 = r22 + r23
#      Terminal: column must close at r24.
#  (2) CROSS-COLUMN (this table HAS cross_groups), per row r:
#        c7  (जम्मा FY2079/80) = sum(c0..c6)
#        c15 (जम्मा FY2080/81) = sum(c8..c14)
#      tolerance +/- 9 (rounding; the source itself rounds, e.g. r0 sum 18981 vs printed 18980).
#
# GATE (per task, per-identity granularity matching the established P2_309ffe7c_p0314 precedent
# in this same recovered/ tree): a cell is ACCEPTED iff it passes EVERY axis that APPLIES to it
# AT CELL GRANULARITY:
#   * within-column axis: EVERY chain identity that this cell PARTICIPATES IN (as the LHS total
#                  OR as a component term) foots within +/-9. A cell that is a member of no chain
#                  identity has no within-column constraint (rare here).
#   * cross-column axis (this table HAS cross_groups, so it always applies): the FY-group row
#                  identity at the cell's row foots within +/-9 (sum of the 7 disaggregating
#                  province cols == the jamma aggregate col). A province cell uses its FY group's
#                  identity at its row; a jamma cell (c7/c15) is the aggregate term of that same
#                  identity, so it passes exactly when that identity foots.
# (Precedent p0314 line: "with no column-foot total row the column axis collapses onto the same
#  per-row cross-group identity". Here BOTH axes genuinely exist, so BOTH are enforced per cell.)
# Quarantine ONLY cells whose applicable axis failed, or that are themselves misread/illegible,
# WITH a reason. Never silently drop; never fabricate; never force-reconcile.

import json, os, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = r'C:\Users\ACER\Projects\Economy\.claude\worktrees\loving-wing-7bdcb4\scrapers\surya_ocr\_ocr_output\P2__Economic_Survey_2081-82_309ffe7c\page_0481.json'
TOL_COL = 9      # crore; same rounding tolerance as the cross axis (source rounds to whole crore)
TOL_CROSS = 9    # crore (per task: +/- 9)

# ---- grid reconstruction (bbox -> 25x16) -------------------------------------
d = json.load(open(SRC, encoding='utf-8'))
tl = d['text_lines']
BAND_MID = [555,640,727,815,901,988,1076,1157,1247,1333,1420,1505,1593,1679,1764,1844]
ROW_Y = [322,352,382,412,442,474,508,539,569,602,641,677,707,751,795,826,858,888,917,948,995,1054,1114,1175,1235]

def band(xc):
    return min(range(16), key=lambda i: abs(xc - BAND_MID[i]))

def nearest_row(yc):
    return min(range(25), key=lambda i: abs(yc - ROW_Y[i]))

grid = [[None]*16 for _ in range(25)]
for t in tl:
    b = t['bbox']; yc = (b[1]+b[3])/2; xc = (b[0]+b[2])/2
    if xc > 460 and 300 < yc < 1260:
        r = nearest_row(yc); c = band(xc)
        if grid[r][c] is None or t['confidence'] > grid[r][c][1]:
            grid[r][c] = (t['text'], float(t['confidence']))

# ---- numeric parser ----------------------------------------------------------
DEVA = "०१२३४५६७८९"
D2A = {ch: str(i) for i, ch in enumerate(DEVA)}

def parse_num(s):
    """(value, clean, reason). Devanagari/Latin digits, decimal point, leading minus,
    thousands separators. Script-mix or stray glyph -> clean=False (OCR-suspect)."""
    if s is None:
        return None, False, "no_token (cell blank in OCR)"
    raw = s.replace('<b>', '').replace('</b>', '').strip()
    neg = False
    body = raw
    for m in ('-', '–', '−', '_'):
        if body.startswith(m):
            neg = True; body = body[1:].strip(); break
    out = []
    saw_deva = saw_latin = suspect = False
    dotcount = 0
    for ch in body:
        if ch in D2A:
            out.append(D2A[ch]); saw_deva = True
        elif ch.isdigit():
            out.append(ch); saw_latin = True
        elif ch == '.':
            out.append('.'); dotcount += 1
        elif ch in (',', '،', ' '):
            continue
        else:
            suspect = True
    if not out or all(ch == '.' for ch in out):
        return None, False, "no_parseable_digits (raw=%r)" % raw
    if saw_deva and saw_latin:
        suspect = True
    if dotcount > 1:
        suspect = True
    try:
        v = float(''.join(out))
    except ValueError:
        return None, False, "unparseable (raw=%r)" % raw
    if neg:
        v = -v
    reason = None if not suspect else (
        "ocr_glyphs_suspect (script-mixed Latin/Devanagari or stray glyph, raw=%r)" % raw)
    return v, (not suspect), reason

val = [[None]*16 for _ in range(25)]
clean = [[False]*16 for _ in range(25)]
raw = [[None]*16 for _ in range(25)]
parse_reason = [[None]*16 for _ in range(25)]
conf = [[None]*16 for _ in range(25)]
for r in range(25):
    for c in range(16):
        cell = grid[r][c]
        rs = cell[0] if cell else None
        v, ok, why = parse_num(rs)
        val[r][c] = v; clean[r][c] = ok; raw[r][c] = rs
        parse_reason[r][c] = why
        conf[r][c] = round(cell[1], 4) if cell else None

# ---- row metadata ------------------------------------------------------------
ROW_LABELS = [
    "१ राजस्व, अनुदान र अन्य प्राप्ति",            # 0
    "१.१ राजस्व",                                  # 1
    "क. कर",                                        # 2
    "ख. अन्य राजस्व",                               # 3
    "१.२ अनुदान",                                   # 4
    "क. द्विपक्षिय वैदेशिक अनुदान",                  # 5
    "ख. बहुपक्षिय वैदेशिक अनुदान",                  # 6
    "ग. अन्तरसरकारी वित्तीय हस्तान्तरण",            # 7
    "१.३ बेरूजु तथा अन्य प्राप्ति",                  # 8
    "२ वित्तीय व्यवस्थाबाट प्राप्ति",               # 9
    "२.१ ऋण लगानी फिर्ता",                          # 10
    "३ यस वर्षको खुद प्राप्ति (१+२)",               # 11
    "४ भुक्तानी",                                    # 12
    "४.१ सञ्चित कोष माथि व्ययभार हुने रकमबाट खर्च", # 13
    "क. चालु खर्च",                                  # 14
    "ख. वित्तीय खर्च",                               # 15
    "४.२ विनियोजन ऐनद्वारा भएको खर्च",              # 16
    "क. चालु खर्च",                                  # 17
    "ख. पुँजीगत खर्च",                               # 18
    "ग. वित्तीय खर्च",                               # 19
    "५ विनिमय दर वा अन्य समायोजन",                  # 20
    "६ यस वर्षको जम्मा भुक्तानी (४+५)",             # 21
    "७ यस अवधिको कोषमा भएको थप घट (+/-) (३-६)",     # 22
    "८ आर्थिक वर्षको सुरूवातको मौज्दात",            # 23
    "९ आर्थिक वर्षको अन्त्यको मौज्दात (७+८)",        # 24
]
assert len(ROW_LABELS) == 25

PROV = ["कोशी","मधेश","बागमती","गण्डकी","लुम्बिनी","कर्णाली","सुदूरपश्चिम","जम्मा"]
COLS = []
for c in range(16):
    fy = "2079/80" if c < 8 else "2080/81"
    prov = PROV[c % 8]
    is_total = (c in (7, 15))
    COLS.append({"col_id": "C%d" % c, "fy": fy, "province": prov, "is_total": is_total})

# ---- within-column formula chain ---------------------------------------------
# Each identity: (lhs_row, [component_rows], sign_for_each) ; default all +, r22 uses -.
# Represent as (lhs, terms) where terms is list of (row, +1/-1).
CHAIN = [
    (0,  [(1, +1), (4, +1), (8, +1)]),
    (1,  [(2, +1), (3, +1)]),
    (4,  [(5, +1), (6, +1), (7, +1)]),
    (9,  [(10, +1)]),
    (11, [(0, +1), (9, +1)]),
    (13, [(14, +1), (15, +1)]),
    (16, [(17, +1), (18, +1), (19, +1)]),
    (12, [(13, +1), (16, +1)]),
    (21, [(12, +1), (20, +1)]),
    (22, [(11, +1), (21, -1)]),
    (24, [(22, +1), (23, +1)]),
]
TERMINAL_ROW = 24  # column must close here

def col_chain(c):
    """Evaluate every chain identity for column c. Returns dict with per-identity residuals,
    list of failing identities, and overall reconciles flag (all evaluable identities pass
    AND terminal r24 evaluable+closes)."""
    results = []
    all_ok = True
    terminal_ok = False
    for lhs, terms in CHAIN:
        lv = val[lhs][c]
        operands = [val[r][c] for r, _ in terms]
        if lv is None or any(o is None for o in operands):
            results.append({"lhs_row": lhs, "rhs_rows": [r for r, _ in terms],
                            "residual": None, "status": "unevaluable",
                            "reason": "missing/unparseable operand"})
            all_ok = False
            continue
        rhs = sum(s * val[r][c] for r, s in terms)
        resid = round(lv - rhs, 4)
        ok = abs(resid) <= TOL_COL
        results.append({"lhs_row": lhs, "rhs_rows": [r for r, _ in terms],
                        "residual": resid, "status": "ok" if ok else "fail",
                        "reason": None if ok else "identity break |%.4g| > %d" % (resid, TOL_COL)})
        if not ok:
            all_ok = False
        if lhs == TERMINAL_ROW:
            terminal_ok = ok
    reconciles = all_ok and terminal_ok
    return {"identities": results, "reconciles": reconciles, "terminal_closes": terminal_ok}

col_chain_status = {c: col_chain(c) for c in range(16)}

# membership: for each row, which chain identities does it participate in (as lhs or component)?
ROW_IN_IDENTITIES = {r: [] for r in range(25)}
for idx, (lhs, terms) in enumerate(CHAIN):
    ROW_IN_IDENTITIES[lhs].append(idx)
    for rr, _ in terms:
        ROW_IN_IDENTITIES[rr].append(idx)

def cell_within_col_status(r, c):
    """Per-cell within-column axis: every chain identity row r participates in (for column c)
    must foot. Returns (ok, evaluable, detail_list)."""
    idents = col_chain_status[c]["identities"]
    mine = [idents[i] for i in ROW_IN_IDENTITIES[r]]
    if not mine:
        return None, False, []   # no within-column constraint on this cell
    detail = []
    ok = True
    any_eval = False
    for it in mine:
        detail.append({"lhs_row": it["lhs_row"], "rhs_rows": it["rhs_rows"],
                       "residual": it["residual"], "status": it["status"]})
        if it["status"] == "ok":
            any_eval = True
        elif it["status"] == "fail":
            any_eval = True; ok = False
        else:  # unevaluable
            ok = False
    return ok, any_eval, detail

# ---- cross-column axis --------------------------------------------------------
# group A: c0..c6 -> c7 ; group B: c8..c14 -> c15. Per row.
CROSS = [(list(range(0, 7)), 7), (list(range(8, 15)), 15)]

def row_cross(r):
    out = {}
    for parts, total in CROSS:
        tv = val[r][total]
        pv = [val[r][c] for c in parts]
        if tv is None or any(p is None for p in pv):
            out[total] = {"parts": parts, "total_col": total, "sum_parts": None,
                          "total_val": tv, "residual": None, "status": "unevaluable",
                          "reason": "missing/unparseable cell in row %d for group ->c%d" % (r, total)}
        else:
            sp = round(sum(pv), 4)
            resid = round(sp - tv, 4)
            ok = abs(resid) <= TOL_CROSS
            out[total] = {"parts": parts, "total_col": total, "sum_parts": sp,
                          "total_val": tv, "residual": resid, "status": "ok" if ok else "fail",
                          "reason": None if ok else "cross break |%.4g| > %d" % (resid, TOL_CROSS)}
    return out

row_cross_status = {r: row_cross(r) for r in range(25)}

def cross_for_cell(r, c):
    """Return the cross-axis result that APPLIES to cell (r,c): the FY-group cross identity."""
    total = 7 if c < 8 else 15
    return row_cross_status[r][total]

# ---- apply the GATE ----------------------------------------------------------
accepted = []
quarantined = []

def cell_record(r, c):
    return {
        "row_idx": r, "row_label": ROW_LABELS[r],
        "col_id": "C%d" % c, "fy": COLS[c]["fy"], "province": COLS[c]["province"],
        "is_total_col": COLS[c]["is_total"],
        "value": val[r][c], "raw_ocr": raw[r][c], "ocr_confidence": conf[r][c],
    }

for r in range(25):
    for c in range(16):
        base = cell_record(r, c)
        reasons = []
        # cell-level parse problems
        if val[r][c] is None:
            reasons.append("cell_unparseable: " + (parse_reason[r][c] or "no value"))
        elif not clean[r][c]:
            reasons.append("cell_" + (parse_reason[r][c] or "ocr_suspect"))
        # within-column axis (per-cell, per-identity membership)
        wcol_ok, wcol_eval, wcol_detail = cell_within_col_status(r, c)
        # cross-column axis (applies: table has cross_groups)
        cx = cross_for_cell(r, c)
        cross_ok = (cx["status"] == "ok")
        # within-column gate term
        if wcol_ok is None:
            # cell participates in no chain identity -> within-column axis does not apply to it
            pass
        elif not wcol_eval:
            reasons.append("within_column_axis_unevaluable (every chain identity this cell is in "
                           "has a missing/unparseable operand): " + "; ".join(
                               "r%d=%s res=%s [%s]" % (it["lhs_row"],
                                   "+".join("r%d" % x for x in it["rhs_rows"]), it["residual"], it["status"])
                               for it in wcol_detail))
        elif not wcol_ok:
            reasons.append("within_column_axis_failed: " + "; ".join(
                "r%d(=%s) res=%s [%s]" % (it["lhs_row"], "+".join("r%d" % x for x in it["rhs_rows"]),
                                          it["residual"], it["status"])
                for it in wcol_detail))
        # cross-column gate term
        if cx["status"] == "unevaluable":
            reasons.append("cross_axis_unevaluable (row %d, FY-group ->c%d): %s" % (
                r, cx["total_col"], cx["reason"]))
        elif not cross_ok:
            reasons.append("cross_axis_failed (row %d, FY-group ->c%d): sum(parts)=%s vs total=%s, "
                           "residual %+.4g > +-%d" % (r, cx["total_col"], cx["sum_parts"],
                                                      cx["total_val"], cx["residual"], TOL_CROSS))
        # build cell out
        rec = dict(base)
        rec["within_column_identities"] = wcol_detail
        rec["cross_residual"] = cx["residual"]
        rec["cross_group_total_col"] = cx["total_col"]
        rec["cross_status"] = cx["status"]
        if reasons:
            rec["status"] = "quarantined"
            rec["quarantine_reasons"] = reasons
            quarantined.append(rec)
        else:
            rec["status"] = "accepted"
            accepted.append(rec)

# ---- residual summaries ------------------------------------------------------
per_column = []
for c in range(16):
    cc = col_chain_status[c]
    worst = None
    for it in cc["identities"]:
        if it["residual"] is not None:
            worst = it["residual"] if worst is None else (worst if abs(worst) >= abs(it["residual"]) else it["residual"])
    per_column.append({
        "col_id": "C%d" % c, "fy": COLS[c]["fy"], "province": COLS[c]["province"],
        "is_total": COLS[c]["is_total"],
        "reconciles": cc["reconciles"], "terminal_closes": cc["terminal_closes"],
        "worst_identity_residual": worst,
        "identities": cc["identities"],
    })

per_row = []
for r in range(25):
    rc = row_cross_status[r]
    per_row.append({
        "row_idx": r, "row_label": ROW_LABELS[r],
        "cross_FY2079_80_to_c7": rc[7],
        "cross_FY2080_81_to_c15": rc[15],
    })

# worst residual across ALL evaluable identities (both axes) -- audit completeness.
# Many large magnitudes here are OCR-glyph parse artifacts (a digit misread as Latin 9/5 inflates
# a sum by thousands), NOT genuine reconciliation breaks in the printed figures; recorded for audit.
all_resid = []
for c in range(16):
    for it in col_chain_status[c]["identities"]:
        if it["residual"] is not None:
            all_resid.append(abs(it["residual"]))
for r in range(25):
    for tot in (7, 15):
        rr = row_cross_status[r][tot]
        if rr["residual"] is not None:
            all_resid.append(abs(rr["residual"]))
worst_residual_all_evaluable = max(all_resid) if all_resid else None

# worst residual over ACCEPTED cells -- the headline: worst error in the matrix actually kept.
# An accepted cell satisfies BOTH a within-column identity and its cross-column identity, each
# within +/-9; we take the max abs residual seen across either axis on accepted cells.
acc_resid = []
for a in accepted:
    if a["cross_residual"] is not None:
        acc_resid.append(abs(a["cross_residual"]))
    for it in a["within_column_identities"]:
        if it["residual"] is not None:
            acc_resid.append(abs(it["residual"]))
worst_residual_accepted = max(acc_resid) if acc_resid else None
# headline worst_residual = worst residual among accepted (promotable) cells
worst_residual = worst_residual_accepted

# matrix_reconciles: does the WHOLE matrix tie out? (every column chain closes AND every
# evaluable cross-group row foots). It does not here -- the page is OCR-degraded.
matrix_reconciles = all(p["reconciles"] for p in per_column) and all(
    (row_cross_status[r][t]["status"] == "ok") for r in range(25) for t in (7, 15)
    if row_cross_status[r][t]["status"] != "unevaluable")

# ---- structural decision scan ------------------------------------------------
structural = (
    "PERIOD/DIMENSION: table is two full fiscal years (2079/80, 2080/81) x 7 provinces + a "
    "jamma(total) column per year; rows are a fixed receipts->payments->closing-balance flow "
    "with an explicit subtotal chain. dimension_kind needed = province (7 Nepal provinces) as a "
    "geographic dimension and fiscal_year as the period dimension. CHECK before promotion: "
    "(a) does the entity/dimension registry already have a 'province' geographic dimension with "
    "all 7 provinces (कोशी/मधेश/बागमती/गण्डकी/लुम्बिनी/कर्णाली/सुदूरपश्चिम)? if not, that is a new "
    "dimension_kind decision; (b) unit 'npr_crore' (रु. करोडमा) must exist in the unit enum "
    "(it is used elsewhere e.g. es2081 nrb annex, so likely present -- confirm, no conversion is "
    "applied here); (c) several rows mix whole-crore and one-decimal-crore precision in the same "
    "column (e.g. row5/row6 vaideshik anudan, row9/row10 vittiya vyavastha are 0.0/decimal while "
    "flow rows are whole crore) -- this is source-native, NOT a unit change, but the schema must "
    "store crore as numeric/decimal, not integer. No new measure enum is needed (this is a "
    "consolidated-fund cash-flow statement). NOTE the source-citation year prints as '२०६१' on "
    "the page which is almost certainly an OCR misread of २०८१; recorded in provenance verbatim, "
    "not corrected."
)

out = {
    "table_id": "P2_309ffe7c_p0481",
    "out_dir": "P2__Economic_Survey_2081-82_309ffe7c",
    "source_path": "Financial Data/mof_documents/economic_survey/Economic_Survey_2081-82.pdf",
    "page": 481,
    "table_title": "अनुसूची १३.७: प्रदेश सञ्चित कोषको वार्षिक आर्थिक विवरण (Annex 13.7: Provincial Consolidated Fund Annual Financial Statement)",
    "unit": "npr_crore",
    "unit_source_label": "रु. करोडमा",
    "price_basis": "nominal",
    "provenance": {
        "extraction_method": "surya-ocr",
        "ocr_model": "surya-ocr 0.17.1",
        "confidence": "B",
        "assembled_by": "ai_pass matrix-assembly + GATE (deterministic post-OCR reconciliation; grid rebuilt from bbox x-bands)",
        "assembled_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_citation_verbatim": "स्रोतः महालेखा नियन्त्रक कार्यालय, २०६१ ।",
        "source_citation_note": "printed year '२०६१' is an OCR misread of २०८१ (FCGO / Office of the Auditor General); recorded verbatim, not corrected",
        "grid_reconstruction": "16 column x-bands and 25 row y-bands clustered from text-line bboxes; cross-column anchor row0 reproduced (sum c0..c6=18981 vs printed c7=18980; sum c8..c14=17342 vs printed c15=17341; 1-unit source rounding).",
        "render_confirmation": ("PDF page index 481 rendered at Matrix(4,4) (=2052x1512, matching OCR "
            "image_px) and zoomed bands inspected: header (8 provinces + jamma per FY) confirmed in "
            "the exact column order C0..C15; row0 (राजस्व...) and row24 (अन्त्यको मौज्दात) read off the "
            "image match the accepted values exactly. NO cell value was corrected from the render "
            "(no render-repair applied) -- accepted cells stand on dual-axis arithmetic alone."),
        "gate": ("accept iff (within-column axis: every formula-chain identity the cell is a member "
            "of foots within +-9) AND (cross-column axis: the cell's FY-group row identity "
            "sum(7 provinces)==jamma foots within +-9). Per-identity granularity matches the sibling "
            "P2_309ffe7c_p0314 precedent. % / ratio columns: none in this table."),
        "ocr_degradation_note": ("page is heavily OCR-degraded: Surya systematically substitutes "
            "Latin glyphs for Devanagari digits on many cells (e.g. row1 बागमती '2468' is the print "
            "२५९४=2594; row1 गण्डकी '9020' is १०२७=1027; row2 मधेश '9229' is १२२९=1229), which breaks "
            "the bulk of identities. These misreads are QUARANTINED, never silently corrected. "
            "Recommend full-page Opus render-verify / re-OCR before bulk promotion (same disposition "
            "as p0314)."),
    },
    "matrix_shape": {
        "rows": 25, "cols": 16,
        "row_labels": {str(i): ROW_LABELS[i] for i in range(25)},
        "columns": COLS,
        "cross_groups": [
            {"aggregate_col": "C7", "fy": "2079/80", "disaggregating_cols": ["C%d" % i for i in range(0, 7)]},
            {"aggregate_col": "C15", "fy": "2080/81", "disaggregating_cols": ["C%d" % i for i in range(8, 15)]},
        ],
        "note": "Each FY group = 7 provinces (disaggregating) + 1 jamma(total) aggregate column.",
    },
    "reconciliation": {
        "within_column_chain": [
            {"lhs_row": lhs, "rhs": ["%sr%d" % ("-" if s < 0 else "+", r) for r, s in terms]}
            for lhs, terms in CHAIN
        ],
        "terminal_row": TERMINAL_ROW,
        "col_tolerance": TOL_COL,
        "cross_tolerance": TOL_CROSS,
        "per_column": per_column,
        "per_row_cross": per_row,
        "worst_residual": worst_residual,
        "worst_residual_accepted": worst_residual_accepted,
        "worst_residual_all_evaluable_incl_glyph_artifacts": worst_residual_all_evaluable,
        "worst_residual_note": ("headline worst_residual is over ACCEPTED (promotable) cells only "
            "(max abs residual across either axis); the all-evaluable figure is dominated by OCR-glyph "
            "parse artifacts in quarantined cells, not genuine print breaks."),
        "cross_source": None,
    },
    "accepted_cells": accepted,
    "quarantine": quarantined,
    "structural_decision_needed": structural,
    "summary": {
        "matrix_reconciles": matrix_reconciles,
        "worst_residual": worst_residual,
        "worst_residual_all_evaluable_incl_glyph_artifacts": worst_residual_all_evaluable,
        "accepted_count": len(accepted),
        "quarantined_count": len(quarantined),
        "total_cells": len(accepted) + len(quarantined),
        "note": ("Annex 13.7 provincial consolidated-fund flow, 25-row subtotal chain x 16 cols "
            "(7 provinces + jamma per FY2079/80 & FY2080/81), unit रु. करोडमा (npr_crore). Page is "
            "OCR-degraded; only the cross-verified aggregate spine (rows 0/11/12/21/24 and the all-zero "
            "वैदेशिक-अनुदान / वित्तीय-व्यवस्था / व्ययभार rows) clears BOTH axes. %d cells ACCEPTED (each "
            "passes a within-column chain identity AND its FY-group cross identity, both within +-9; "
            "worst accepted residual %s crore), %d QUARANTINED with per-cell reasons (mostly Latin-for-"
            "Devanagari digit misreads that break the identities). Nothing fabricated; no cross-source "
            "anchor provided; render-confirmed header + row0/row24, no value corrected from the image.")
            % (len(accepted), worst_residual, len(quarantined)),
    },
}

dst = os.path.join(HERE, "verified_matrix.json")
json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---- console report ----------------------------------------------------------
print("=== PER-COLUMN within-chain reconciliation ===")
for p in per_column:
    print("  %s %-7s %-12s reconciles=%s terminal_closes=%s worst_id_resid=%s" % (
        p["col_id"], p["fy"], p["province"], p["reconciles"], p["terminal_closes"], p["worst_identity_residual"]))
print()
print("=== CROSS-COLUMN per-row (residual sum(parts)-total) ===")
for pr in per_row:
    a = pr["cross_FY2079_80_to_c7"]; b = pr["cross_FY2080_81_to_c15"]
    print("  row%2d  FY79/80->c7 resid=%-8s(%s)  FY80/81->c15 resid=%-8s(%s)" % (
        pr["row_idx"], a["residual"], a["status"], b["residual"], b["status"]))
print()
print("matrix_reconciles:", matrix_reconciles)
print("worst_residual (HEADLINE; over accepted cells, either axis):", worst_residual)
print("worst_residual_all_evaluable (incl glyph artifacts):", worst_residual_all_evaluable)
print("accepted_count:", len(accepted))
print("quarantined_count:", len(quarantined))
print("total cells:", len(accepted) + len(quarantined), "(expect 400)")
assert len(accepted) + len(quarantined) == 400
print("WROTE", dst, os.path.getsize(dst), "bytes")
