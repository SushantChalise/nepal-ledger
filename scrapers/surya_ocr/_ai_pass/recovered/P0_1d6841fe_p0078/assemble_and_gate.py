# Assemble the verified two-column matrix for Yellowbook 2081 page 78 (table 5.4) and apply the GATE.
#
# Table: ५.४ - सार्वजनिक संस्थानको एकीकृत वासलात  (Public Enterprises Consolidated Balance Sheet)
# Source: सार्वजनिक संस्थानको वार्षिक स्थिति समीक्षा २०८१ (Yellowbook 2081), page 78 (PDF index p0078, doc id 1d6841fe)
# Unit: रु. लाखमा  (NPR in lakhs)
# Extraction: surya-ocr 0.17.1 ; confidence grade B.
#
# Value columns (the two summable columns):
#   col "2079" = आषाढ मसान्त २०७९  (Ashadh-end FY2078/79 position)
#   col "2080" = आषाढ मसान्त २०८०  (Ashadh-end FY2079/80 position)
# A third printed column (% फरक, year-on-year % change) is NOT a value column and is excluded
# from the summable matrix; it is recorded as provenance only.
#
# Row layout (per the task's reconciliation identities):
#   LIABILITIES + EQUITY side: rows 0..7 line items, row 8 = कुल जम्मा (total).
#   ASSETS side:               rows 9..14 line items, row 15 = कुल जम्मा (total).
#
# Reconciliation identities (per the task):
#   (A)  sum(rows 0..7)  == row 8   per value column      [liabilities+equity foots]
#   (B)  sum(rows 9..14) == row 15  per value column      [assets foots]
#   (C)  row 8 == row 15            per value column      [balance-sheet identity]
#   tolerance = +/- 9 (lakh).
#
# GATE: A column is "reconciled" iff it passes A AND B AND C.
#   The task wording: "Accept a cell ONLY if its column reconciled AND its row cross-reconciles
#   (Sigma across the disaggregating columns == the aggregate column, +/-9)."
#   There is NO aggregate (Nepal-style) column here: the two columns are independent reporting
#   dates, not a disaggregation that sums to a total. So the row cross-reconcile term has no
#   disaggregating-columns sum to test (no column is the arithmetic sum of the others).
#   -> Row cross-reconcile is UNEVALUABLE for every row (no cross-source anchor provided either).
#   Per the rule "Quarantine every other cell WITH a reason -- never silently drop", a cell whose
#   row cross-reconcile term cannot be satisfied cannot be ACCEPTED. We therefore record the column
#   reconciliation honestly and quarantine cells that fail it; cells in a fully-reconciling column
#   are still gated on the (unevaluable) row term and flagged accordingly.

import json, os, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
TOL = 9

# ---- Devanagari / mixed-digit conversion -------------------------------------
DEVA = "०१२३४५६७८९"
D2A = {d: str(i) for i, d in enumerate(DEVA)}

def to_int(s):
    """Convert an OCR numeric string (Devanagari and/or Latin digits, commas) to int.
    Returns (value, clean_flag). clean_flag is False when the token is OCR-suspect:
      - a stray non-digit/non-comma glyph (underscore, dash, foreign char), OR
      - SCRIPT MIXING within one number (both Devanagari and Latin digits present) --
        a genuine printed figure is single-script; mixing means the OCR garbled glyphs,
        so the parsed integer is not trustworthy."""
    if s is None:
        return None, False
    raw = s.strip()
    out = []
    suspect = False
    saw_deva = False
    saw_latin = False
    for ch in raw:
        if ch in D2A:
            out.append(D2A[ch]); saw_deva = True
        elif ch.isdigit():            # Latin digit
            out.append(ch); saw_latin = True
        elif ch in (",", "،"):   # ASCII comma or Arabic comma -> thousands sep
            continue
        else:
            suspect = True            # underscore, dash, foreign glyph, etc.
    if not out:
        return None, False
    if saw_deva and saw_latin:        # script-mixed -> garbled
        suspect = True
    return int("".join(out)), (not suspect)

# ---- Transcribed cells (bbox-resolved from page_0078.json) -------------------
# Each row: (slug, label_ne, side, raw_2079, raw_2080)
# raw strings are the OCR token text exactly as emitted; None = no token present.
ROWS = [
    # ---- LIABILITIES + EQUITY (rows 0..7), total row 8 ----
    ("paid-up-capital",                 "चुक्ता पुँजी",                       "liab_equity", "३,७२५,५४१", "४,१२१,२८१"),
    ("share-premium",                   "शेयर प्रिमियम",                     "liab_equity", "98,999",    "_"),
    ("advance-for-share-investment",    "शेयर लगानी वापत प्राप्त एडभान्स रकम","liab_equity", "४३,६६८",    "१०,५७३"),
    ("reserve-fund",                    "जगेडा कोष",                         "liab_equity", "३,३०५,९२८", "५,०७७,९६७"),
    ("accumulated-profit-loss",         "संचित नाफा/(नोक्सान)",              "liab_equity", "५२४,०७८",   "६११,४९६"),
    ("medium-long-term-loan",           "मध्यम तथा दिर्घकालीन ऋण",           "liab_equity", "६,४९२,६३४", "७,९९५,५८८"),
    ("short-term-loan-deposit",         "अल्पकालीन ऋण/निक्षेप",              "liab_equity", "६,६८१,८८०", "७,७४०,१०५"),
    ("current-other-liabilities-provisions","चालु र अन्य दायित्व तथा व्यवस्था","liab_equity","२,९५३,९०१", "२,८१४,१४१"),
    ("total",                           "कुल जम्मा",                         "liab_equity", "२३,७४१,७४०","२८,३७१,१५१"),
    # ---- ASSETS (rows 9..14), total row 15 ----
    ("net-fixed-assets",                "खुद स्थिर सम्पत्ति",                "assets",      "७,९९८,४१३", "99,३४9,5२४"),
    ("investments",                     "लगानी",                             "assets",      "४,२१०,७५३", "४,९२७,३९२"),
    ("loan-investment",                 "कर्जा लगानी",                       "assets",      "७,१६४,६९२", "७,५४९,७६५"),
    ("cash-and-bank-balance",           "नगद तथा बैङ्क मौज्दात",             "assets",      "१,१५९,२४३", "१,४२१,०२५"),
    ("current-assets",                  "चालु सम्पत्ति",                     "assets",      "२,७४९,५७४", "२,७३०,७२१"),
    ("other-assets",                    "अन्य सम्पत्ति",                     "assets",      "४५९,०६४",   "४००,४२४"),
    ("total",                           "कुल जम्मा",                         "assets",      "२३,७४१,७४०","२८,३७१,१५१"),
]
assert len(ROWS) == 16, len(ROWS)

COLS = ["2079", "2080"]
COL_LABEL_NE = {"2079": "आषाढ मसान्त २०७९", "2080": "आषाढ मसान्त २०८०"}

# Parse into a value/clean matrix.
vals = {c: [None] * 16 for c in COLS}
clean = {c: [False] * 16 for c in COLS}
raw   = {c: [None] * 16 for c in COLS}
for i, (slug, ne, side, r79, r80) in enumerate(ROWS):
    for c, rs in (("2079", r79), ("2080", r80)):
        v, ok = to_int(rs)
        vals[c][i] = v
        clean[c][i] = ok
        raw[c][i] = rs

# ---- Reconciliation per column ------------------------------------------------
LIAB = list(range(0, 8)); LIAB_TOTAL = 8
ASSET = list(range(9, 15)); ASSET_TOTAL = 15

def col_recon(c):
    v = vals[c]
    # A: liabilities+equity foots
    if any(v[i] is None for i in LIAB) or v[LIAB_TOTAL] is None:
        rA = None
    else:
        rA = sum(v[i] for i in LIAB) - v[LIAB_TOTAL]
    # B: assets foot
    if any(v[i] is None for i in ASSET) or v[ASSET_TOTAL] is None:
        rB = None
    else:
        rB = sum(v[i] for i in ASSET) - v[ASSET_TOTAL]
    # C: balance-sheet identity total==total
    if v[LIAB_TOTAL] is None or v[ASSET_TOTAL] is None:
        rC = None
    else:
        rC = v[LIAB_TOTAL] - v[ASSET_TOTAL]
    ok = (rA is not None and abs(rA) <= TOL) and \
         (rB is not None and abs(rB) <= TOL) and \
         (rC is not None and abs(rC) <= TOL)
    return {"residual_A_liabFoot": rA, "residual_B_assetFoot": rB,
            "residual_C_balanceIdentity": rC, "reconciles": ok}

col_status = {c: col_recon(c) for c in COLS}

# ---- Row cross-reconcile ------------------------------------------------------
# No disaggregating-columns -> aggregate-column relationship exists in this table
# (the two columns are independent reporting dates). No cross-source anchor was provided.
# So the row cross-reconcile term is UNEVALUABLE for every cell. Record it explicitly.
ROW_CROSS_EVALUABLE = False
ROW_CROSS_REASON = ("no disaggregating columns sum to an aggregate column in this table "
                    "(the two columns are independent balance-sheet dates), and no cross-source "
                    "anchor was provided -> row cross-reconcile is unevaluable")

# ---- Apply the GATE -----------------------------------------------------------
accepted = []
quarantined = []

def cell_base(c, i):
    slug, ne, side, _, _ = ROWS[i]
    kind = "aggregate" if i in (LIAB_TOTAL, ASSET_TOTAL) else "line_item"
    return {
        "column": c, "column_label_ne": COL_LABEL_NE[c],
        "row_idx": i, "side": side, "row_kind": kind,
        "row_slug": slug, "label_ne": ne,
        "value": vals[c][i], "raw_ocr": raw[c][i],
    }

for c in COLS:
    cs = col_status[c]
    for i in range(16):
        base = cell_base(c, i)
        reasons = []
        if vals[c][i] is None:
            reasons.append("no_parseable_value (OCR token missing or non-numeric, e.g. '_')")
        elif not clean[c][i]:
            reasons.append(f"ocr_digit_glyphs_suspect (mixed Latin/Devanagari or stray glyph in raw '{raw[c][i]}')")
        if not cs["reconciles"]:
            rA, rB, rC = cs["residual_A_liabFoot"], cs["residual_B_assetFoot"], cs["residual_C_balanceIdentity"]
            if rA is None:
                reasons.append("column_identity_A_unevaluable (a liabilities+equity cell missing/unparseable)")
            elif abs(rA) > TOL:
                reasons.append(f"column_identity_A_fail (sum(0..7)-total8={rA:+d}, >|{TOL}|)")
            if rB is None:
                reasons.append("column_identity_B_unevaluable (an assets cell missing/unparseable)")
            elif abs(rB) > TOL:
                reasons.append(f"column_identity_B_fail (sum(9..14)-total15={rB:+d}, >|{TOL}|)")
            if rC is None:
                reasons.append("column_identity_C_unevaluable (a total cell missing/unparseable)")
            elif abs(rC) > TOL:
                reasons.append(f"column_identity_C_fail (total8-total15={rC:+d}, >|{TOL}|)")
        # Row cross-reconcile gate term (always unevaluable here).
        if not ROW_CROSS_EVALUABLE:
            reasons.append("row_cross_reconcile_unevaluable (" + ROW_CROSS_REASON + ")")
        if reasons:
            q = dict(base); q["quarantine_reasons"] = reasons
            quarantined.append(q)
        else:
            a = dict(base)
            a["col_residual_A_liabFoot"] = cs["residual_A_liabFoot"]
            a["col_residual_B_assetFoot"] = cs["residual_B_assetFoot"]
            a["col_residual_C_balanceIdentity"] = cs["residual_C_balanceIdentity"]
            a["row_cross_residual"] = None
            accepted.append(a)

# ---- Residual summaries -------------------------------------------------------
per_column = []
for c in COLS:
    cs = col_status[c]
    per_column.append({"column": c, "column_label_ne": COL_LABEL_NE[c], **cs})

per_row = []
for i in range(16):
    slug, ne, side, _, _ = ROWS[i]
    per_row.append({
        "row_idx": i, "side": side, "row_slug": slug, "label_ne": ne,
        "value_2079": vals["2079"][i], "value_2080": vals["2080"][i],
        "row_cross_reconcile": "unevaluable",
        "row_cross_reason": ROW_CROSS_REASON,
    })

# worst residual over EVALUABLE column identities (the magnitude of any break we found).
# NOTE: col 2080 identity B parses to a ~88M "residual" only because the net-fixed-assets
# token is garbage OCR glyphs (not a real number). Reporting that as a reconciliation
# residual would be misleading -- it is a parse artifact, not a Rs-magnitude break. The
# headline worst_residual is therefore taken over GENUINE foot breaks (identities whose
# operands are all clean-parsed numbers); the garbage-glyph artifact is recorded separately.
all_resid = []           # all evaluable, incl. garbage-glyph artifact (audit completeness)
genuine_resid = []       # only identities whose every operand parsed clean
def identity_operands_clean(c, identity):
    if identity == "A":
        idxs = LIAB + [LIAB_TOTAL]
    elif identity == "B":
        idxs = ASSET + [ASSET_TOTAL]
    else:
        idxs = [LIAB_TOTAL, ASSET_TOTAL]
    return all(clean[c][i] for i in idxs)
for c in COLS:
    for ident, k in (("A", "residual_A_liabFoot"), ("B", "residual_B_assetFoot"),
                     ("C", "residual_C_balanceIdentity")):
        r = col_status[c][k]
        if r is not None:
            all_resid.append(abs(r))
            if identity_operands_clean(c, ident):
                genuine_resid.append(abs(r))
worst_residual = max(genuine_resid) if genuine_resid else None        # headline
worst_residual_incl_glyph_artifact = max(all_resid) if all_resid else None

# worst residual over ACCEPTED cells only
acc_resid = []
for a in accepted:
    for k in ("col_residual_A_liabFoot", "col_residual_B_assetFoot", "col_residual_C_balanceIdentity"):
        if a.get(k) is not None:
            acc_resid.append(abs(a[k]))
worst_residual_accepted = max(acc_resid) if acc_resid else None

matrix_reconciles = all(p["reconciles"] for p in per_column)

# ---- Diagnostics: sub-identity observations + back-solved implied values -------
# These are NOT promoted values. Back-solved figures are recorded so the user's
# promotion gate can see exactly which OCR cells broke each identity and by how much.
# Fabricating the implied value into the matrix is explicitly forbidden; it lives here only.
liab79_known = sum(vals["2079"][i] for i in LIAB if i != 1)  # exclude share-premium (idx 1)
asset80_known = sum(vals["2080"][i] for i in ASSET if i != 9)  # exclude net-fixed (idx 9)
liab80_known = sum(vals["2080"][i] for i in LIAB if i != 1 and vals["2080"][i] is not None)
diagnostics = {
    "col_2079": {
        "asset_side_foots": True,
        "asset_foot_residual": col_status["2079"]["residual_B_assetFoot"],
        "balance_identity_holds": True,
        "liab_side_break_lakh": col_status["2079"]["residual_A_liabFoot"],
        "break_attributed_to": "share-premium (row_idx 1): OCR token '98,999' (Latin digits) = 98999; "
                               "single defect explains the entire +84889 liab-foot break",
        "back_solved_share_premium_2079_NOT_PROMOTED": 23741740 - liab79_known,
    },
    "col_2080": {
        "balance_identity_holds": True,
        "share_premium_missing": "raw token '_' (dash); printed value is nil/blank",
        "liab_7_items_foot_to_total_exactly": (liab80_known == vals["2080"][LIAB_TOTAL]),
        "liab_7_items_minus_total": liab80_known - vals["2080"][LIAB_TOTAL],
        "asset_side_break": "net-fixed-assets (row_idx 9): OCR token '99,3४9,5२4' is a mixed "
                            "Latin/Devanagari glyph mess (naive parse 99349524) -> garbage, not a real value",
        "back_solved_net_fixed_assets_2080_NOT_PROMOTED": 28371151 - asset80_known,
    },
    "interpretation": ("Page is OCR-degraded on exactly 2 numeric cells (share-premium 2079, "
                       "net-fixed-assets 2080) plus 1 legitimately-blank cell (share-premium 2080). "
                       "All totals and all other line items are mutually consistent. The full GATE "
                       "(column-reconciles AND row-cross-reconciles) cannot be cleared: no column "
                       "passes all three column identities, and the row cross-reconcile term is "
                       "unevaluable (no aggregate column, no cross-source anchor). All 32 cells "
                       "quarantined; none fabricated."),
}

out = {
    "source_pdf": "Financial Data/mof_documents/yellowbook/सार्वजनिक संस्थानको वार्षिक स्थिति समीक्षा २०८१_ksi3tbe.pdf",
    "source_page": 78,
    "page_id": "P0_1d6841fe_p0078",
    "out_dir": "P0__ksi3tbe_1d6841fe",
    "table": "५.४ सार्वजनिक संस्थानको एकीकृत वासलात",
    "table_en": "Public Enterprises Consolidated Balance Sheet",
    "measure": "consolidated_balance_sheet",
    "unit": "npr_lakh",
    "price_basis": "nominal",
    "provenance": {
        "extraction_method": "surya-ocr",
        "model_version": "0.17.1",
        "verification": "bbox-resolved transcription from page_0078.json; dual-foot + balance-identity reconciliation; GATE applied",
        "confidence_grade": "B",
        "value_columns": [{"key": "2079", "label_ne": "आषाढ मसान्त २०७९"},
                          {"key": "2080", "label_ne": "आषाढ मसान्त २०८०"}],
        "excluded_columns": [{"key": "pct_diff", "label_ne": "तुलनामा (% फरक)",
                              "reason": "year-on-year % change column, not a summable value column"}],
        "tolerance_lakh": TOL,
        "gate": ("accept iff column reconciles (sum(0..7)==total8 AND sum(9..14)==total15 AND "
                 "total8==total15, each within +/-9 lakh) AND row cross-reconciles; row "
                 "cross-reconcile is UNEVALUABLE for every row (no disaggregating->aggregate "
                 "column relationship and no cross-source anchor) so no cell can clear the full gate"),
    },
    "columns": [{"key": c, "label_ne": COL_LABEL_NE[c]} for c in COLS],
    "rows": [{"idx": i, "slug": ROWS[i][0], "label_ne": ROWS[i][1], "side": ROWS[i][2],
              "kind": ("aggregate" if i in (8, 15) else "line_item")} for i in range(16)],
    "accepted_cells": accepted,
    "quarantined_cells": quarantined,
    "reconciliation": {
        "per_column": per_column,
        "per_row": per_row,
        "worst_residual_lakh_genuine_foot_break": worst_residual,
        "worst_residual_lakh_incl_glyph_artifact": worst_residual_incl_glyph_artifact,
        "worst_residual_lakh_accepted": worst_residual_accepted,
        "cross_source": None,
        "diagnostics": diagnostics,
    },
    "summary": {
        "matrix_reconciles": matrix_reconciles,
        "accepted_count": len(accepted),
        "quarantined_count": len(quarantined),
        "worst_residual_lakh": worst_residual,
        "note": (
            "Table 5.4 consolidated balance sheet, amounts in lakh. Two value columns "
            "(Ashadh-end 2079, Ashadh-end 2080). NO column fully reconciles, so the GATE "
            "accepts zero cells. Col 2079: assets foot (B=-1) and balance identity holds "
            "(C=0), but liabilities foot fails by +84889 lakh, entirely caused by the "
            "share-premium cell OCR'd as Latin '98,999' (=98999; back-solved correct value "
            "~14110, NOT promoted). Col 2080: balance identity holds (C=0) and the 7 non-"
            "share-premium liability items already equal the total exactly (share-premium "
            "row is a printed '_' = nil), but the assets side cannot be footed because "
            "net-fixed-assets OCR'd to mixed-glyph garbage '99,3४9,5२4' (back-solved correct "
            "value ~11341824, NOT promoted). Additionally, row cross-reconcile is unevaluable "
            "for every row: the two columns are independent reporting dates (no disaggregating-"
            "->aggregate column relationship) and no cross-source anchor was provided, so even "
            "a clean column could not clear the full gate. All 32 cells quarantined with reasons; "
            "nothing fabricated. See reconciliation.diagnostics for the per-cell breakdown."
        ),
    },
}

dst = os.path.join(HERE, "verified_matrix.json")
json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("=== PER-COLUMN RECONCILIATION ===")
for p in per_column:
    print(f"  col {p['column']}: A(liabFoot)={p['residual_A_liabFoot']}  "
          f"B(assetFoot)={p['residual_B_assetFoot']}  C(balanceId)={p['residual_C_balanceIdentity']}  "
          f"reconciles={p['reconciles']}")
print("matrix_reconciles:", matrix_reconciles)
print("worst_residual (genuine foot break, clean operands):", worst_residual)
print("worst_residual (incl garbage-glyph artifact):", worst_residual_incl_glyph_artifact)
print("accepted_count:", len(accepted))
print("quarantined_count:", len(quarantined))
print("total cells:", len(accepted) + len(quarantined), "(expect 32)")
assert len(accepted) + len(quarantined) == 32
print("WROTE", dst, os.path.getsize(dst), "bytes")
