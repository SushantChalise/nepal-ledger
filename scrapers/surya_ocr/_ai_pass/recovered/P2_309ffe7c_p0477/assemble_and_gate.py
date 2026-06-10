# Assemble the FINAL verified matrix for Economic Survey 2081-82 p0477
# (अनुसूची १३.३ : वृहत औद्योगिक वर्गीकरण अनुसारको प्रदेशगत कुल गार्हस्थ्य उत्पादनको संरचना)
# "Structure of provincial GDP by broad industrial classification" -- IN PERCENT.
# Apply the GATE.
#
# =============================================================================
# STRUCTURAL FINDING (must be surfaced -- the task's stated identity does NOT hold):
#
#   The task prompt stated the reconciliation identity as:
#       "sum(rows 0..17) == row 18 (कुल जम्मा) == 100.0 PER COLUMN, for all 16 columns."
#   That is INCORRECT for this table. It was inferred from a catastrophic OCR misread:
#   the bottom data row OCR-read as "900.0" in every column (which the prompt-author
#   read as a per-column 100.0 total). Ground-truth PDF vector text + a high-res render
#   show the bottom row is labelled "औसत योगदान" (average/overall contribution) and its
#   values are 15.9, 13.2, 36.2, 9.1, 14.3, 4.3, 7.1 (FY2080/81) -- NOT 100.0, and it is
#   NOT a column total (sum of rows 0..17 in col 0 is 271.7, not 15.9).
#
#   The table actually has 14 data columns (7 provinces x 2 fiscal years), NOT 16, and
#   the TRUE reconciliation identity is PER-ROW ACROSS PROVINCES:
#       sum over the 7 province cells in a row == 100.0 (+/- rounding), per fiscal year.
#   This holds for ALL 19 rows (18 sectors + औसत योगदान), both FYs. Each cell is a
#   province's % share of the national total for that sector/aggregate.
#
#   This is the "प्रदेशगत संरचना" (provincial-composition) dual of the p475 GVA-in-crore
#   table. We reconcile on the axis that ACTUALLY applies and holds, document the
#   discrepancy, and DO NOT force the false per-column identity.
#
# =============================================================================
# DATA SOURCE: the digit cells in this PDF are embedded as proper Latin-Unicode vector
# text (the Nepali LABELS use a glyph-encoded font, which is why OCR was needed; but the
# NUMBERS extract cleanly). We extract the numbers from the vector layer and cross-confirm
# against (a) the high-confidence Surya-OCR Devanagari reading and (b) a high-res render.
# Provenance recorded as surya-ocr (the registered pipeline) + vector cross-confirmation;
# confidence grade B per task instruction.
# =============================================================================
import fitz, re, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
PDF = r'C:\Users\ACER\Projects\Economy\Financial Data\mof_documents\economic_survey\Economic_Survey_2081-82.pdf'
PAGE0 = 476          # 0-based; OCR json 'page' is 477 (1-based)
SRC_PAGE_INDEX = 477

# rounding tolerance for 1-decimal percentage shares summing across 7 provinces.
# 7 values each rounded to 1 dp => worst-case rounding band ~ +/- 0.35; use 0.5.
TOL = 0.5

# ---- 7 provinces, interleaved (even col = FY2080/81, odd col = FY2081/82) ----
PROV7 = ["koshi", "madhes", "bagamati", "gandaki", "lumbini", "karnali", "sudur-pashchim"]
PROV7_NE = ["कोशी", "मधेस", "वागमती", "गण्डकी", "लुम्बिनी", "कर्णाली", "सुदूरपश्चिम"]
NCOLS = 14
EVEN = [2 * k for k in range(7)]      # FY2080/81 province cols
ODD = [2 * k + 1 for k in range(7)]   # FY2081/82 province cols
COL_META = {}
for k, p in enumerate(PROV7):
    COL_META[2 * k] = {"province": p, "province_ne": PROV7_NE[k], "year": "2080/81", "role": "province_share"}
    COL_META[2 * k + 1] = {"province": p, "province_ne": PROV7_NE[k], "year": "2081/82", "role": "province_share"}

# ---- 19 rows: 18 sectors + 1 aggregate (औसत योगदान) ----
SECTORS = [
    ("agriculture-forestry-fishing", "कृषि, वन र मत्स्यपालन"),
    ("mining-quarrying", "खानी तथा उत्खनन्"),
    ("manufacturing", "उत्पादनमूलक उद्योग"),
    ("electricity-gas-steam-ac", "विद्युत, ग्यास, वाष्प तथा वातानुकलित आपूर्ति सेवा"),
    ("water-supply-sewerage-waste", "पानी आपूर्ति, ढल फोहोर व्यवस्थापन तथा पुनःउत्पादनका क्रियाकलापहरू"),
    ("construction", "निर्माण"),
    ("wholesale-retail-trade-vehicle-repair", "थोक तथा खुद्रा व्यापार, गाडि तथा मोटरसाइकल मर्मत सेवा"),
    ("transport-storage", "यातायात तथा भण्डारण"),
    ("accommodation-food-service", "आवास तथा भोजन सेवा"),
    ("information-communication", "सूचना तथा सञ्चार"),
    ("financial-insurance", "वित्तीय तथा बीमा क्रियाकलापहरू"),
    ("real-estate", "घरजग्गा कारोवारको सेवा"),
    ("professional-scientific-technical", "पेशागत वैज्ञानीक तथा प्राविधिक क्रियाकलापहरू"),
    ("administrative-support-service", "प्रशासनिक तथा सहयोगी सेवाका क्रियाकलापहरू"),
    ("public-administration-defence", "सार्वजनिक प्रशासन, रक्षा र अत्यावश्यक सामाजिक सुरक्षा"),
    ("education", "शिक्षा"),
    ("human-health-social-work", "मानव स्वास्थ्य तथा सामाजिक कार्य"),
    ("other-service", "अन्य सेवाका क्रियाकलापहरू"),
]
ROW18 = ("average-contribution-total-gva", "औसत योगदान (कुल मूल्य अभिवृद्धिको प्रदेशगत हिस्सा)")
NROWS = 19

# ---- column x-band centers in DISPLAYED (derotated) PDF points, from inspection ----
COLX = [223, 253, 283, 312, 341, 371, 402, 432, 460, 490, 521, 551, 580, 611]
def which_col(x):
    return min(range(NCOLS), key=lambda i: abs(x - COLX[i]))

# ---- extract numeric vector tokens in displayed coords ----
doc = fitz.open(PDF)
pg = doc[PAGE0]
m = pg.rotation_matrix
toks = []
for w in pg.get_text("words"):
    if re.fullmatch(r"\d{1,3}\.\d", w[4]):
        r = fitz.Rect(w[:4]) * m
        toks.append(((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2, float(w[4])))

# cluster rows by y
toks.sort(key=lambda t: t[1])
rows = []
cur = [toks[0]]
for t in toks[1:]:
    if t[1] - cur[-1][1] <= 8:
        cur.append(t)
    else:
        rows.append(cur); cur = [t]
rows.append(cur)
assert len(rows) == NROWS, f"expected {NROWS} rows, got {len(rows)}"

# build value grid
M = [[None] * NCOLS for _ in range(NROWS)]
for ri, rw in enumerate(rows):
    for x, y, v in rw:
        c = which_col(x)
        # keep first; collisions would indicate a column-snap error
        if M[ri][c] is None:
            M[ri][c] = v
        else:
            raise RuntimeError(f"col collision row {ri} col {c}: {M[ri][c]} vs {v}")

# completeness check
missing = [(r, c) for r in range(NROWS) for c in range(NCOLS) if M[r][c] is None]

# ---------------------------------------------------------------------------
# RECONCILIATION (the axis that APPLIES): per row, per fiscal year, sum of the 7
# province shares == 100.0 (+/- TOL).  There is NO per-column total row in this table.
def row_share_resid(prov_cols, row):
    if any(M[row][c] is None for c in prov_cols):
        return None
    return round(sum(M[row][c] for c in prov_cols) - 100.0, 4)

resid80 = {r: row_share_resid(EVEN, r) for r in range(NROWS)}   # FY2080/81
resid81 = {r: row_share_resid(ODD, r) for r in range(NROWS)}    # FY2081/82
ok80 = {r: (resid80[r] is not None and abs(resid80[r]) <= TOL) for r in range(NROWS)}
ok81 = {r: (resid81[r] is not None and abs(resid81[r]) <= TOL) for r in range(NROWS)}

def cell_axis(col, row):
    """Return (residual, ok, group_label) for the row-share identity this cell participates in."""
    if COL_META[col]["year"] == "2080/81":
        return resid80[row], ok80[row], "FY2080/81 row-share (Σ 7 provinces == 100)"
    return resid81[row], ok81[row], "FY2081/82 row-share (Σ 7 provinces == 100)"

# ---------------------------------------------------------------------------
# Apply the GATE: accept a cell iff the reconciliation axis that applies to it passes.
def cell_base(row, col):
    cm = COL_META[col]
    if row < 18:
        slug, ne = SECTORS[row]; kind = "sector"
    else:
        slug, ne = ROW18; kind = "aggregate_row"
    return {
        "row_idx": row, "col_idx": col,
        "province": cm["province"], "province_ne": cm["province_ne"],
        "year": cm["year"], "col_role": cm["role"],
        "row_kind": kind, "row_slug": slug, "row_label_ne": ne,
        "value": M[row][col], "unit": "percent_province_share",
    }

accepted, quarantined = [], []
for col in range(NCOLS):
    for row in range(NROWS):
        base = cell_base(row, col)
        resid, axis_ok, group = cell_axis(col, row)
        reasons = []
        if M[row][col] is None:
            reasons.append("cell_missing (no numeric token snapped to this row/col)")
        if resid is None:
            reasons.append(f"row_share_unevaluable ({group}: >=1 province cell missing in this row/FY)")
        elif not axis_ok:
            reasons.append(f"row_share_fail ({group}: Σ-100={resid:+.1f}, >|{TOL}|)")
        if reasons:
            q = dict(base); q["quarantine_reasons"] = reasons
            quarantined.append(q)
        else:
            a = dict(base)
            a["row_share_residual"] = resid
            a["row_share_group"] = group
            a["reconciled_axis"] = "row_across_provinces"
            accepted.append(a)

# ---------------------------------------------------------------------------
# Summaries.
per_row = []
for row in range(NROWS):
    if row < 18:
        slug, ne = SECTORS[row]; kind = "sector"
    else:
        slug, ne = ROW18; kind = "aggregate_row"
    per_row.append({
        "row_idx": row, "row_kind": kind, "row_slug": slug, "row_label_ne": ne,
        "FY2080_81_sum7prov_minus_100": resid80[row], "FY2080_81_reconciles": ok80[row],
        "FY2081_82_sum7prov_minus_100": resid81[row], "FY2081_82_reconciles": ok81[row],
    })

# per "province-FY column" residual summary is NOT meaningful (no column total); we still
# report each column's role and that the column axis is not-applicable for this table.
per_column = []
for col in range(NCOLS):
    cm = COL_META[col]
    per_column.append({
        "col_idx": col, "province": cm["province"], "year": cm["year"], "role": cm["role"],
        "column_total_axis": "NOT_APPLICABLE (no column-foot total row; the bottom row 'औसत योगदान' is itself a province-share row, not a column sum)",
    })

acc_resid = [abs(a["row_share_residual"]) for a in accepted if a.get("row_share_residual") is not None]
worst_residual_accepted = max(acc_resid) if acc_resid else None
all_resid = [abs(r) for r in list(resid80.values()) + list(resid81.values()) if r is not None]
worst_residual_all = max(all_resid) if all_resid else None

matrix_reconciles = all(ok80[r] for r in range(NROWS)) and all(ok81[r] for r in range(NROWS)) and not missing

out = {
    "source_pdf": "Financial Data/mof_documents/economic_survey/Economic_Survey_2081-82.pdf",
    "source_page_index": SRC_PAGE_INDEX,
    "source_page_printed": "अनुसूची १३.३",
    "page_id": "P2_309ffe7c_p0477",
    "out_dir": "P2__Economic_Survey_2081-82_309ffe7c",
    "table": "अनुसूची १३.३ : वृहत औद्योगिक वर्गीकरण अनुसारको प्रदेशगत कुल गार्हस्थ्य उत्पादनको संरचना",
    "table_en": "Annex 13.3: Structure of provincial GDP by broad industrial classification (province shares of national sector GVA)",
    "measure": "provincial_share_of_national_sector_gva",
    "unit": "percent",
    "unit_ne": "प्रतिशतमा",
    "price_basis": "current",
    "price_basis_ne": "प्रचलित मूल्यमा",
    "matrix_layout": {
        "n_rows": NROWS,
        "n_cols": NCOLS,
        "rows": "0..17 = sectors (broad industrial classification); 18 = औसत योगदान (province share of TOTAL national GVA) -- an independent aggregate, NOT a column sum",
        "columns": "14 data cols = 7 provinces x 2 fiscal years interleaved; even col=FY2080/81, odd col=FY2081/82; NO national/total column",
        "even_cols_FY2080_81": EVEN,
        "odd_cols_FY2081_82": ODD,
        "province_order": PROV7,
    },
    "provenance": {
        "extraction_method": "surya-ocr",
        "model_version": "0.17.1",
        "verification": (
            "Surya-OCR Devanagari reading was heavily degraded for this percent table (scale/digit errors, "
            "e.g. 100.0 read as 900.0). Numeric cells were recovered from the PDF's embedded Latin-Unicode vector "
            "text layer (labels are glyph-encoded -> OCR-only; numbers extract cleanly) and cross-confirmed against "
            "a high-res PyMuPDF render and the OCR reading. Reconciled on the per-row across-provinces identity "
            "(Σ 7 province shares == 100, per fiscal year); GATE applied."
        ),
        "confidence_grade": "B",
        "tolerance_percent": TOL,
        "reconciles_how": [
            "per row, per fiscal year: sum of the 7 province shares == 100.0 (+/- 0.5, 1-dp rounding band)",
            "NO per-column total row exists; the bottom row 'औसत योगदान' is itself a province-share row that ALSO reconciles row-wise to 100",
        ],
        "gate": "accept iff the cell's applicable axis (per-row across-provinces sum==100 for the cell's FY) reconciles within +/-0.5; quarantine WITH reason otherwise; never force the (false) per-column identity",
        "cross_source": None,
    },
    "column_index": [
        {"col_idx": c, "province": COL_META[c]["province"], "province_ne": COL_META[c]["province_ne"],
         "year": COL_META[c]["year"], "role": COL_META[c]["role"]}
        for c in range(NCOLS)
    ],
    "row_index": (
        [{"row_idx": i, "slug": SECTORS[i][0], "label_ne": SECTORS[i][1], "kind": "sector"} for i in range(18)]
        + [{"row_idx": 18, "slug": ROW18[0], "label_ne": ROW18[1], "kind": "aggregate_row"}]
    ),
    "accepted_cells": accepted,
    "quarantined_cells": quarantined,
    "reconciliation": {
        "axis_applied": "per_row_across_provinces (Σ 7 province shares == 100, per FY)",
        "column_axis": "NOT_APPLICABLE_for_this_table (no column-foot total row; the task's stated per-column 100.0 identity was based on an OCR misread of the 'औसत योगदान' row as '900.0' and does NOT hold)",
        "cross_column_axis": "NOT_APPLICABLE (no disaggregating->aggregate column groups; no national column on the page)",
        "per_row": per_row,
        "per_column": per_column,
        "worst_residual_percent_accepted": worst_residual_accepted,
        "worst_residual_percent_all_evaluable": worst_residual_all,
        "cross_source": None,
    },
    "summary": {
        "matrix_reconciles": matrix_reconciles,
        "accepted_count": len(accepted),
        "quarantined_count": len(quarantined),
        "worst_residual_percent": worst_residual_accepted,
        "structural_decision_needed": (
            "TWO structural items must be resolved by the user BEFORE promotion. "
            "(1) IDENTITY/LAYOUT CORRECTION: the task brief's reconciliation identity ('sum rows0..17 == row18 == 100 "
            "per column, 16 columns') is WRONG for this table -- it came from an OCR misread of the bottom row "
            "(औसत योगदान) as '900.0'. Ground truth: 14 columns (7 provinces x 2 FYs, NO national column), and the "
            "real identity is per-ROW across the 7 provinces == 100 per fiscal year. Confirm this corrected layout. "
            "(2) NEW DIMENSION: promotion needs a 'province-share-of-national-sector' dimension_kind (a share/ratio "
            "measure, unit=percent, price_basis=current). This differs from the absolute province-industry GVA kind "
            "needed by sibling p475 (npr_crore). Either add a new dimension_kind 'provincial-gva-share' (recommended; "
            "needs an ADR) OR derive these shares from the absolute table and DON'T store them (store-vs-derive "
            "decision). No unit gap beyond registering 'percent' as a share unit if not already present."
        ),
        "note": (
            "14-col x 19-row matrix recovered from embedded vector text (OCR-degraded for this percent page). All 19 "
            "rows reconcile per-FY across the 7 provinces to 100.0 (worst +/-0.2, within the 1-dp rounding band). "
            "Both fiscal years (FY2080/81 even cols, FY2081/82 odd cols) fully accepted. The task's per-column 100.0 "
            "identity is a misread and is reported as NOT-APPLICABLE, not forced. Nothing fabricated; nothing dropped."
        ),
    },
}

dst = os.path.join(HERE, "verified_matrix.json")
json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------------------
print("=== GRID (vector ground truth) ===")
for r in range(NROWS):
    print(f" r{r:2d}: " + " ".join(f"{M[r][c]:5.1f}" if M[r][c] is not None else "  .  " for c in range(NCOLS)))
print("\n=== PER-ROW row-share residual (Σ7 provinces - 100) ===")
for pr in per_row:
    print(f"  r{pr['row_idx']:2d} {pr['row_slug']:38s} "
          f"FY80/81={pr['FY2080_81_sum7prov_minus_100']:+.1f}({pr['FY2080_81_reconciles']}) "
          f"FY81/82={pr['FY2081_82_sum7prov_minus_100']:+.1f}({pr['FY2081_82_reconciles']})")
print()
print("missing cells:", missing)
print("matrix_reconciles:", matrix_reconciles)
print("worst_residual_percent (accepted):", worst_residual_accepted)
print("worst_residual_percent (all evaluable):", worst_residual_all)
print("accepted_count:", len(accepted))
print("quarantined_count:", len(quarantined))
print("WROTE", dst, os.path.getsize(dst), "bytes")

total = len(accepted) + len(quarantined)
assert total == NCOLS * NROWS, f"cell total {total} != {NCOLS*NROWS}"
print(f"SANITY OK: total {total} == {NCOLS}x{NROWS}")
