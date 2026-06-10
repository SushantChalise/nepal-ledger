# Assemble the verified matrix for Yellowbook 2081 page 98 (table 5.18) and apply the GATE.
#
# Table: ५.१८ - सार्वजनिक संस्थानको शेयरधनीकोष (नेटवर्थ)
#        Public Enterprises Shareholders' Fund (Net Worth)
# Source: सार्वजनिक संस्थानको वार्षिक स्थिति समीक्षा २०८१ (Yellowbook 2081),
#         file slug ksi3tbe, doc id 1d6841fe, OCR page 98 (= PyMuPDF page index 98).
# Unit: रकम (रु. लाखमा)  -> NPR in lakh.
# Extraction: surya-ocr 0.17.1 (bbox-resolved) + high-zoom visual verification of every
#             numeric cell against the rendered source page; confidence grade B.
#
# COLUMNS (the printed table has 3 numeric columns after serial+name):
#   col idx 2 = आर्थिक वर्ष २०७८/७९  (FY 2078/79 net worth)            -> SUMMABLE value column
#   col idx 3 = आर्थिक वर्ष २०७९/८०  (FY 2079/80 net worth)            -> SUMMABLE value column
#       (OCR misread the col-3 header as "२०७९/५०"; the rendered page shows २०७९/८०.)
#   col idx 4 = % Change            (year-on-year % change, derived ratio)-> NOT summable.
# Parenthesised figures are NEGATIVE (accumulated losses / negative net worth).
#
# ROW LAYOUT (task reconciliation identities, 1-based printed rows; here 0-based row_idx):
#   Six category blocks, each = component enterprise rows -> a जम्मा (subtotal) row, then
#   one कुल जम्मा (grand total). Component counts: 10 + 4 + 9 + 5 + 5 + 9 = 42.
#     औद्योगिक  (Industrial) : comps 1..10  -> जम्मा 11
#     व्यापारिक (Commercial) : comps 13..16 -> जम्मा 17
#     सेवा      (Service)    : comps 19..27 -> जम्मा 28
#     सामाजिक   (Social)     : comps 30..34 -> जम्मा 35
#     जनोपयोगी  (Utility)    : comps 37..41 -> जम्मा 42
#     वित्तीय   (Financial)  : comps 44..52 -> जम्मा 53
#   कुल जम्मा (Grand total) = row 54 = sum of the 6 जम्मा subtotals.
#
# RECONCILIATION IDENTITIES (per task; tolerance +/-9 lakh):
#   (foot)  per value column, within each category sum(components) == its जम्मा subtotal.
#   (roll)  per value column, sum(6 जम्मा subtotals) == कुल जम्मा grand total.
#   (equiv) per value column, grand total == sum of all 42 component rows.
#   Col idx 4 (% Change) is a derived ratio: NOT footing-reconcilable.
#   No row-wise cross-column identity (the two FY columns are independent values).
#
# GATE (acceptance rule from the task):
#   A numeric cell is ACCEPTED iff it passes every reconciliation axis that APPLIES:
#     * column axis (always, when a total row exists): the block the cell belongs to foots
#       within tolerance for that column (and for the grand-total cell, the subtotal roll-up
#       holds within tolerance).
#     * cross-column axis: NOT APPLICABLE here (no disaggregating->aggregate column set);
#       it is NOT required and does NOT block acceptance.
#   A derived-ratio column (% Change) is quarantined wholesale (not footing-reconcilable).
#   Cells whose applicable axis fails, or that are illegible/misread, are quarantined WITH a
#   reason. Nothing is fabricated; nothing is force-reconciled; nothing is silently dropped.

import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
TOL = 9

# ---------------------------------------------------------------------------
# VERIFIED VALUES.
# Each component row: (row_idx, serial, slug, label_ne, v2, v3, raw_ocr2, raw_ocr3, pct_raw)
#   v2 = FY2078/79 (col idx 2), v3 = FY2079/80 (col idx 3); negatives already signed.
#   raw_ocr* = the original surya-ocr token (so misreads are auditable); pct_raw = col idx 4 token.
# Values were read at 8x-20x render zoom from PyMuPDF page index 98; every cell visually checked.
# ---------------------------------------------------------------------------

# category meta: (key, label_ne, label_en, component row_idxs, subtotal row_idx)
CATS_META = [
    ("industrial", "औद्योगिक", "Industrial", list(range(1, 11)), 11),
    ("commercial", "व्यापारिक", "Commercial", list(range(13, 17)), 17),
    ("service",    "सेवा",      "Service",    list(range(19, 28)), 28),
    ("social",     "सामाजिक",   "Social",     list(range(30, 35)), 35),
    ("utility",    "जनोपयोगी",  "Utility",    list(range(37, 42)), 42),
    ("financial",  "वित्तीय",   "Financial",  list(range(44, 53)), 53),
]
GRAND_IDX = 54

# component + subtotal cells. (row_idx, kind, cat, slug, label_ne, v2, v3, raw2, raw3, pct)
ROWS = [
    # --- औद्योगिक (Industrial): comps 1..10, subtotal 11 ---
    (1,  "component","industrial","dirgha-bikas-sansthan","दीर्घ विकास संस्थान",            14986,   8640,  "98,958","5,580","(82.38)"),
    (2,  "component","industrial","gidibuti-utpadan","जिडिबुटी उत्पादन तथा प्रशोधन कम्पनी लि.", 4424,   4940,  "8.838","8,980","(8.83)"),
    (3,  "component","industrial","hetauda-cement","हिटौंडा सिमेन्ट उद्योग लि.",                 50,  -2579,  "40","(२,५७९)","(४,२२०.१२)"),
    (4,  "component","industrial","janakpur-churot","जनकपुर चुरोट कारखाना लि.",              -28144, -28139,  "(२८,9४४)","(२८,9३९)","(0.03)"),
    (5,  "component","industrial","nepal-aushadhi","नेपाल औषधि लिमिटेड",                     -18740, -20295,  "(95,680)","(२०,२९५)","5.30"),
    (6,  "component","industrial","udayapur-cement","उदयपुर सिमेन्ट उद्योग लि.",              42295,  38657,  "87,794","३८,६५७","(5.50)"),
    (7,  "component","industrial","nepal-orind-magnesite","नेपाल ओरिण्ड म्याग्नासाइट प्रा.लि.", -44217, -45876, "(४४,२१७)","(84.508)","(3.6X)"),
    (8,  "component","industrial","butwal-dhago","बुटवल धागो कारखाना लि.",                   -15903, -16281,  "(94,903)","(१६,२८१)","(२.३८)"),
    (9,  "component","industrial","nepal-metal","नेपाल मेटल कम्पनी लि.",                       1783,   1783,  "9,953","9,653",""),
    (10, "component","industrial","dhaubadi-falam","धौवादी फलाम कम्पनी लि.",                   2536,   3215,  "२,५३६","३,२१५","२६.७४"),
    (11, "subtotal", "industrial","jamma-audyogik","जम्मा (औद्योगिक)",                       -40929, -56735,  "(४०,९२९)","(१६,७३५)","(३८,६२)"),

    # --- व्यापारिक (Commercial): comps 13..16, subtotal 17 ---
    (13, "component","commercial","krishi-samagri","कृषि सामग्री कम्पनी लि.",                 116354, 116908,  "998,348","११६,९०८","0.85"),
    (14, "component","commercial","khadya-byabastha","खाद्य व्यवस्था तथा व्यापार कम्पनी लि.",  23005,  24457,  "23,00%","२४,४५७","X.39"),
    (15, "component","commercial","nepal-oil-nigam","नेपाल आयल निगम लि.",                     -68137,  61411,  "(६८,१३७)","६१,४११","990.93"),
    (16, "component","commercial","nepal-ban-nigam","नेपाल वन निगम लिमिटेड",                    4353,   3610,  "8,343","3,590","(96.05)"),
    (17, "subtotal", "commercial","jamma-byaparik","जम्मा (व्यापारिक)",                        75575, 206386,  "७४,४७४","२०६,३८६","903.09"),

    # --- सेवा (Service): comps 19..27, subtotal 28 ---
    (19, "component","service","audyogik-kshetra-byabasthapan","औद्योगिक क्षेत्र व्यवस्थापन लि.", 443485, 443841, "883,858","४४३,८४१","0.05"),
    (20, "component","service","nepal-parbahan-godam","नेपाल पारवहन तथा गोदाम व्यवस्था कं.लि.",   5187,   5599,  "४,१८७","4,499","6.93"),
    (21, "component","service","nepal-bayuseva","नेपाल वायुसेवा निगम",                        -51144, -57972,  "(49,988)","(५७,९७२)","(93.3X)"),
    (22, "component","service","rastriya-utpadakatwa","राष्ट्रिय उत्पादकत्व तथा आर्थिक विकास के.लि.", -930, -973, "(930)","(९७३)","(8.55)"),
    (23, "component","service","nepal-nagarik-uddayan","नेपाल नागरिक उड्डयन प्राधिकरण",       2059475, 3651191, "२.०५९.४७५","३,६५१,१९१","७७.२९"),
    (24, "component","service","nepal-purwadhar-nirman","नेपाल पूर्वाधार निर्माण कम्पनी लि.",     2475,   2543,  "2,86%","2,883","२.७४"),
    (25, "component","service","sajha-yatayat","साझा यातायात सहकारी संस्था लि.",               38911,  41106,  "३८,९११","४१,१०६","५.६४"),
    (26, "component","service","nepal-railway","नेपाल रेल्वे कम्पनी लि.",                       -2039,  -4035,  "(2,039)","(XEO.8)","(९७.९9)"),
    (27, "component","service","bishal-bazar","विशाल बजार कम्पनी लि.",                         50237,  51711,  "५०,२३७","५१,७११","२.९३"),
    (28, "subtotal", "service","jamma-sewa","जम्मा (सेवा)",                                  2545657, 4133010,  "२. ४४४. ६४७","8,933,090","६२.३६"),

    # --- सामाजिक (Social): comps 30..34, subtotal 35 ---
    (30, "component","social","sanskritik-sansthan","सांस्कृतिक संस्थान",                       -2553,  -2702,  "(२,४५३)","(२,७०२)","(4.57)"),
    (31, "component","social","gorkhapatra","गोरखापत्र संस्थान",                                 6491,   7126,  "4.889","७,१२६","9.05"),
    (32, "component","social","janak-shiksha","जनक शिक्षा सामग्री केन्द्र लि.",                 44366,  46303,  "४४,३६६","४६,३०३","8.38"),
    (33, "component","social","nepal-television","नेपाल टेलिभिजन",                              16909,  14910,  "98,909","98,890","(99.52)"),
    (34, "component","social","rastriya-aawas","राष्ट्रिय आवास कम्पनी लि.",                     23609,  23693,  "२३,६०९","२३,६९३","0.3X"),
    (35, "subtotal", "social","jamma-samajik","जम्मा (सामाजिक)",                               88822,  89330,  "55,522","द९,३३०","०.५७"),

    # --- जनोपयोगी (Utility): comps 37..41, subtotal 42 ---
    (37, "component","utility","nepal-khanepani","नेपाल खानेपानी संस्थान",                     -19945, -25403,  "(१९,९४५)","(24,803)","(२७.३६)"),
    (38, "component","utility","nepal-bidyut-pradhikaran","नेपाल विद्युत प्राधिकरण",          2063522, 2415106,  "२.०६३.५२२","२,४१५,१०६","90.08"),
    (39, "component","utility","nepal-dursanchar","नेपाल दूरसञ्चार कम्पनी लि.",                952680, 939450,  "947,550","९३९,४५०","(9.39)"),
    (40, "component","utility","bidyut-utpadan","बिद्युत उत्पादन कम्पनी लि.",                   48178,  49562,  "४८,१७८","89,287","२.८७"),
    (41, "component","utility","rastriya-prasaran-grid","राष्ट्रिय प्रशारण ग्रिड कम्पनी",        46434,  48326,  "४६,४३४","४८,३२६","8.00"),
    (42, "subtotal", "utility","jamma-janopayogi","जम्मा (जनोपयोगी)",                        3090869, 3427041,  "३,०९०,८६९","३,४२७,०४१","90.55"),

    # --- वित्तीय (Financial): comps 44..52, subtotal 53 ---
    (44, "component","financial","krishi-bikas-bank","कृषि विकास बैङ्क लि.",                  333570, 337937,  "333,400","३३७,९३७","9.39"),
    (45, "component","financial","rastriya-bima-sansthan-jeevan","राष्ट्रिय बिमा संस्थान (जीवन)", 3140, 3154,   "3,980","3,948","0.86"),
    (46, "component","financial","rastriya-bima-company","राष्ट्रिय बिमा कम्पनी लि.",          36519,  40382,  "३६,५१९","४०,३८२","१०.५८"),
    (47, "component","financial","rastriya-banijya-bank","राष्ट्रिय वाणिज्य बैङ्क लि.",       306142, 507383,  "३०६,१४२","५०७,३८३","६५.७३"),
    (48, "component","financial","nikshep-karja-surakshan","निक्षेप तथा कर्जा सुरक्षण कोष",   192936, 231366,  "१९२,९३६","२३१,३६६","98.88"),
    (49, "component","financial","nepal-stock-exchange","नेपाल स्टक एक्सचेन्ज लिमिटेड",        62051,  62823,  "६२,०५१","६२,८२३","9.24"),
    (50, "component","financial","nagarik-lagani-kosh","नागरिक लगानी कोष",                    353058, 222889,  "३५३,०५८","२२२,८८९","(34.50)"),
    (51, "component","financial","hidcl","हाइड्रोइलेक्ट्रिसिटी इन्भेष्टमेन्ट एण्ड डेभलपमेन्ट बैंक", 223678, 251126, "२२३,६७८","२५१,१२६","१२.२७"),
    (52, "component","financial","nepal-bank","नेपाल बैङ्क लि.",                              354636, 365227,  "३५४,६३६","३६५,२२७","2.99"),
    (53, "subtotal", "financial","jamma-bittiya","जम्मा (वित्तीय)",                         1865729, 2022286,  "१,८६५,७२९","२,०२२,२८६","5.39"),

    # --- कुल जम्मा (Grand total) row 54 ---
    (54, "grand_total","ALL","kul-jamma","कुल जम्मा",                                       7625724, 9821317,  "७,६२५,७२४","९,८२१,३१७","२८.७९"),
]

BY_IDX = {r[0]: r for r in ROWS}
COMP_IDXS = [r[0] for r in ROWS if r[1] == "component"]
assert len(COMP_IDXS) == 42, len(COMP_IDXS)

COLS = [
    {"key": "fy2078_79", "col_idx": 2, "label_ne": "आर्थिक वर्ष २०७८/७९", "fy": "2078/79", "kind": "value"},
    {"key": "fy2079_80", "col_idx": 3, "label_ne": "आर्थिक वर्ष २०७९/८०", "fy": "2079/80", "kind": "value"},
]
PCT_COL = {"key": "pct_change", "col_idx": 4, "label_ne": "% Change", "kind": "derived_ratio"}

def vget(row, col_idx):
    return row[5] if col_idx == 2 else row[6]
def rawget(row, col_idx):
    return row[7] if col_idx == 2 else row[8]

# ---- Per-column, per-category footing + grand roll-up -------------------------
def column_recon(col_idx):
    cat_results = {}
    subtotals = []
    for key, ne, en, comp_idxs, sub_idx in CATS_META:
        comp_sum = sum(vget(BY_IDX[i], col_idx) for i in comp_idxs)
        sub_val = vget(BY_IDX[sub_idx], col_idx)
        resid = comp_sum - sub_val
        foots = abs(resid) <= TOL
        cat_results[key] = {"comp_sum": comp_sum, "subtotal": sub_val,
                            "foot_residual": resid, "foots": foots,
                            "subtotal_idx": sub_idx, "component_idxs": comp_idxs}
        subtotals.append(sub_val)
    grand_val = vget(BY_IDX[GRAND_IDX], col_idx)
    roll_sum = sum(subtotals)
    roll_resid = roll_sum - grand_val
    roll_ok = abs(roll_resid) <= TOL
    all_comp_sum = sum(vget(BY_IDX[i], col_idx) for i in COMP_IDXS)
    equiv_resid = all_comp_sum - grand_val
    equiv_ok = abs(equiv_resid) <= TOL
    return {"categories": cat_results,
            "grand": {"value": grand_val, "subtotal_roll_sum": roll_sum,
                      "roll_residual": roll_resid, "roll_ok": roll_ok,
                      "all_component_sum": all_comp_sum, "equiv_residual": equiv_resid,
                      "equiv_ok": equiv_ok}}

col_recon = {c["col_idx"]: column_recon(c["col_idx"]) for c in COLS}

# ---- Apply the GATE ----------------------------------------------------------
accepted = []
quarantined = []

def cat_of(row):
    return row[2]

def base_cell(row, col):
    return {
        "row_idx": row[0], "row_kind": row[1], "category": row[2],
        "row_slug": row[3], "label_ne": row[4],
        "column": col["key"], "col_idx": col["col_idx"], "fy": col.get("fy"),
        "column_label_ne": col["label_ne"],
        "value": vget(row, col["col_idx"]), "raw_ocr": rawget(row, col["col_idx"]),
    }

ROW_CROSS_REASON = ("no disaggregating->aggregate column set exists (the two FY columns are "
                    "independent net-worth values, not parts of a row total) and no cross-source "
                    "anchor was provided -> the cross-column axis is NOT APPLICABLE and is not "
                    "required for acceptance")

for col in COLS:
    cidx = col["col_idx"]
    rec = col_recon[cidx]
    for row in ROWS:
        cell = base_cell(row, col)
        kind = row[1]
        reasons = []
        # determine the applicable column-axis result for this cell
        if kind == "component" or kind == "subtotal":
            cr = rec["categories"][cat_of(row)]
            cell["category_foot_residual"] = cr["foot_residual"]
            if not cr["foots"]:
                reasons.append(
                    f"category_foot_fail (col {cidx}: sum(components of {cat_of(row)})="
                    f"{cr['comp_sum']} vs printed जम्मा subtotal={cr['subtotal']}, "
                    f"residual={cr['foot_residual']:+d} > |{TOL}| lakh; every component and the "
                    f"subtotal of this block were visually re-verified at high zoom, so this is a "
                    f"genuine print-level footing break in the source, NOT an OCR error)")
        elif kind == "grand_total":
            g = rec["grand"]
            cell["subtotal_roll_residual"] = g["roll_residual"]
            cell["all_component_equiv_residual"] = g["equiv_residual"]
            if not g["roll_ok"]:
                reasons.append(
                    f"grand_roll_fail (col {cidx}: sum(6 subtotals)={g['subtotal_roll_sum']} vs "
                    f"printed कुल जम्मा={g['value']}, residual={g['roll_residual']:+d} > |{TOL}|)")
            # note (does not block): equiv identity may break if a category block is broken
            if not g["equiv_ok"]:
                cell["equiv_note"] = (
                    f"grand==Σ42 components breaks by {g['equiv_residual']:+d} lakh, attributable "
                    f"entirely to the quarantined industrial block; the printed subtotal roll-up "
                    f"identity (the structural identity actually shown on the page) holds within "
                    f"+/-{TOL}")
        # cross-column axis: not applicable, never blocks (per task acceptance rule)
        if reasons:
            q = dict(cell); q["quarantine_reasons"] = reasons
            quarantined.append(q)
        else:
            a = dict(cell)
            a["cross_column_axis"] = "not_applicable"
            a["cross_column_reason"] = ROW_CROSS_REASON
            accepted.append(a)

# ---- % Change column: quarantine wholesale (derived ratio, not footing-reconcilable) ----
for row in ROWS:
    pct = row[9]
    q = {
        "row_idx": row[0], "row_kind": row[1], "category": row[2],
        "row_slug": row[3], "label_ne": row[4],
        "column": PCT_COL["key"], "col_idx": PCT_COL["col_idx"],
        "column_label_ne": PCT_COL["label_ne"],
        "value": None, "raw_ocr": pct,
        "quarantine_reasons": [
            "derived_ratio_column (% Change is a year-on-year ratio between col idx 2 and idx 3; "
            "it does not participate in any summation and is not footing-reconcilable -> quarantined "
            "wholesale per the task rule; raw OCR token retained for provenance only, value not parsed)"
        ],
    }
    quarantined.append(q)

# ---- Residual summaries ------------------------------------------------------
per_column = []
for col in COLS:
    cidx = col["col_idx"]
    rec = col_recon[cidx]
    cats = []
    for key, ne, en, comp_idxs, sub_idx in CATS_META:
        cr = rec["categories"][key]
        cats.append({"category": key, "label_ne": ne, "label_en": en,
                     "component_sum": cr["comp_sum"], "printed_subtotal": cr["subtotal"],
                     "foot_residual": cr["foot_residual"], "foots": cr["foots"]})
    g = rec["grand"]
    col_reconciles = all(c["foots"] for c in cats) and g["roll_ok"]
    per_column.append({
        "column": col["key"], "col_idx": cidx, "fy": col.get("fy"),
        "label_ne": col["label_ne"], "kind": col["kind"],
        "categories": cats,
        "grand_total": {"printed": g["value"], "subtotal_roll_sum": g["subtotal_roll_sum"],
                        "roll_residual": g["roll_residual"], "roll_ok": g["roll_ok"],
                        "all_component_sum": g["all_component_sum"],
                        "equiv_residual": g["equiv_residual"], "equiv_ok": g["equiv_ok"]},
        "column_reconciles": col_reconciles,
    })

# per-row residual view (only categories carry a foot residual; grand carries roll residual)
per_row = []
for row in ROWS:
    entry = {"row_idx": row[0], "row_kind": row[1], "category": row[2],
             "row_slug": row[3], "label_ne": row[4],
             "value_fy2078_79": row[5], "value_fy2079_80": row[6],
             "cross_column_axis": "not_applicable"}
    per_row.append(entry)

# worst residual: over EVALUABLE footing/roll identities (genuine, all-clean operands)
all_resids = []
for col in COLS:
    rec = col_recon[col["col_idx"]]
    for cr in rec["categories"].values():
        all_resids.append(abs(cr["foot_residual"]))
    all_resids.append(abs(rec["grand"]["roll_residual"]))
worst_residual = max(all_resids) if all_resids else None

# worst residual over ACCEPTED cells only
acc_resids = []
for a in accepted:
    for k in ("category_foot_residual", "subtotal_roll_residual"):
        if a.get(k) is not None:
            acc_resids.append(abs(a[k]))
worst_residual_accepted = max(acc_resids) if acc_resids else None

matrix_reconciles = all(p["column_reconciles"] for p in per_column)

# ---- Diagnostics: the one genuine break + the OCR-vs-truth correction map -----
diagnostics = {
    "genuine_print_footing_break": {
        "where": "col idx 3 (FY 2079/80), औद्योगिक (Industrial) category",
        "component_sum": col_recon[3]["categories"]["industrial"]["comp_sum"],
        "printed_subtotal": col_recon[3]["categories"]["industrial"]["subtotal"],
        "residual_lakh": col_recon[3]["categories"]["industrial"]["foot_residual"],
        "explanation": (
            "All 10 industrial component cells AND the (४०,९२९)/(५६,७३५) subtotal for col idx 3 "
            "were visually re-verified at 16x-20x zoom against the rendered source page. The 10 "
            "components sum to -55,935 but the printed जम्मा subtotal is -56,735, an 800-lakh "
            "discrepancy. This is a footing error in the PUBLISHED Yellowbook table itself, not an "
            "OCR artefact. The implied 'correct' component is NOT back-solved or fabricated; the "
            "block is quarantined as printed."),
        "back_solved_value_NOT_PROMOTED": None,
    },
    "ocr_vs_verified_corrections": (
        "surya-ocr badly degraded this scanned page (per-cell confidences 0.27-1.00; many "
        "Devanagari digits flipped, e.g. ९<->१, ८<->६, script-mixed tokens, and the col-3 header "
        "OCR'd '२०७९/५०' for the true '२०७९/८०'). The naive OCR matrix reconciles on ZERO "
        "categories. After high-zoom visual verification of every numeric cell, col idx 2 foots on "
        "all 6 categories + grand (residuals -1..+1, lakh-rounding), and col idx 3 foots on 5 of 6 "
        "categories + grand; only the industrial col-3 block carries a genuine 800-lakh print "
        "break. Notable OCR->verified fixes: row1 98,958/5,580->14,986/8,640; row4 ...944/...939->"
        "...144/...139; row9 9,953/9,653->1,783/1,783 (both cols); service subtotal 8,933,090->"
        "4,133,010 (col3) and ~2,444,647->2,545,657 (col2); social subtotal 55,522->88,822; "
        "row33 98,909/98,890->16,909/14,910."),
    "note_lakh_rounding": (
        "Several foot/roll residuals are exactly +/-1 lakh (financial, grand). These are normal "
        "rounding of the underlying figures to lakh in the source and are within the +/-9 tolerance."),
}

out = {
    "source_pdf": "Financial Data/mof_documents/yellowbook/सार्वजनिक संस्थानको वार्षिक स्थिति समीक्षा २०८१_ksi3tbe.pdf",
    "source_page_ocr": 98,
    "source_page_pymupdf_index": 98,
    "page_id": "P0_1d6841fe_p0098",
    "out_dir": "P0__ksi3tbe_1d6841fe",
    "table": "५.१८ सार्वजनिक संस्थानको शेयरधनीकोष (नेटवर्थ)",
    "table_en": "Public Enterprises Shareholders' Fund (Net Worth)",
    "measure": "shareholders_fund_net_worth",
    "unit": "npr_lakh",
    "price_basis": "nominal",
    "provenance": {
        "extraction_method": "surya-ocr",
        "model_version": "0.17.1",
        "verification": ("bbox-resolved transcription from _ocr_output/P0__ksi3tbe_1d6841fe/"
                         "page_0098.json, then every numeric cell visually re-verified at 8x-20x "
                         "render zoom of the source PDF (PyMuPDF page index 98); per-category "
                         "footing + grand-total roll-up reconciliation; GATE applied"),
        "confidence_grade": "B",
        "value_columns": [{"key": c["key"], "col_idx": c["col_idx"], "label_ne": c["label_ne"],
                           "fy": c.get("fy")} for c in COLS],
        "excluded_columns": [{"key": PCT_COL["key"], "col_idx": PCT_COL["col_idx"],
                              "label_ne": PCT_COL["label_ne"],
                              "reason": "year-on-year % change (derived ratio); not a summable "
                                        "value column and not footing-reconcilable"}],
        "negative_convention": "parenthesised figures are negative (accumulated loss / negative net worth)",
        "tolerance_lakh": TOL,
        "gate": ("accept a numeric cell iff its applicable column axis reconciles: for "
                 "component/subtotal cells, its category foots (Σ components == printed जम्मा "
                 "subtotal, +/-9 lakh) for that column; for the grand-total cell, the 6 subtotals "
                 "roll up to कुल जम्मा (+/-9). The cross-column axis is NOT APPLICABLE (independent "
                 "FY columns, no cross-source anchor) and is not required. The % Change column is "
                 "quarantined wholesale (derived ratio). Quarantine on a failed applicable axis or "
                 "illegibility, with reasons; never fabricate, never force-reconcile."),
    },
    "columns": [{"key": c["key"], "col_idx": c["col_idx"], "label_ne": c["label_ne"],
                 "fy": c.get("fy"), "kind": c["kind"]} for c in COLS]
               + [{"key": PCT_COL["key"], "col_idx": PCT_COL["col_idx"],
                   "label_ne": PCT_COL["label_ne"], "kind": PCT_COL["kind"]}],
    "categories": [{"key": k, "label_ne": ne, "label_en": en,
                    "component_row_idxs": ci, "subtotal_row_idx": si}
                   for k, ne, en, ci, si in CATS_META],
    "rows": [{"idx": r[0], "kind": r[1], "category": r[2], "slug": r[3], "label_ne": r[4]}
             for r in ROWS],
    "accepted_cells": accepted,
    "quarantined_cells": quarantined,
    "reconciliation": {
        "per_column": per_column,
        "per_row": per_row,
        "worst_residual_lakh": worst_residual,
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
            "Table 5.18 public-enterprise net worth, NPR lakh, two FY value columns (2078/79, "
            "2079/80) + a % Change ratio column. Col idx 2 reconciles fully: all 6 category "
            "subtotals foot and the grand total rolls up (residuals -1..+1, lakh rounding) -> its "
            "49 numeric cells accepted. Col idx 3 reconciles on 5 of 6 categories and the grand "
            "roll-up, but the औद्योगिक (industrial) block carries a genuine 800-lakh print footing "
            "break (-55,935 components vs -56,735 printed subtotal, all cells visually verified) -> "
            "the 10 industrial components + their subtotal in col idx 3 (11 cells) are quarantined; "
            "the remaining 38 numeric col-3 cells are accepted. The % Change column (49 cells) is "
            "quarantined wholesale as a non-summable derived ratio. matrix_reconciles is FALSE "
            "because one category-column block does not foot. Nothing fabricated, nothing "
            "force-reconciled. See reconciliation.diagnostics for the OCR->verified correction map."),
    },
}

dst = os.path.join(HERE, "verified_matrix.json")
json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---- console report ----------------------------------------------------------
print("=== PER-COLUMN RECONCILIATION ===")
for p in per_column:
    print(f"\n col {p['col_idx']} ({p['fy']}): column_reconciles={p['column_reconciles']}")
    for c in p["categories"]:
        print(f"   {c['category']:11s} compΣ={c['component_sum']:>11} sub={c['printed_subtotal']:>11} "
              f"resid={c['foot_residual']:>6} foots={c['foots']}")
    g = p["grand_total"]
    print(f"   GRAND roll={g['subtotal_roll_sum']:>11} printed={g['printed']:>11} "
          f"resid={g['roll_residual']:>4} ok={g['roll_ok']} | equiv_resid={g['equiv_residual']} ok={g['equiv_ok']}")
print("\nmatrix_reconciles:", matrix_reconciles)
print("worst_residual_lakh (all evaluable identities):", worst_residual)
print("worst_residual_lakh (accepted cells):", worst_residual_accepted)
print("accepted_count:", len(accepted))
print("quarantined_count:", len(quarantined))
tot = len(accepted) + len(quarantined)
print("total cells:", tot, "(expect 49*3 = 147)")
assert tot == 147, tot
print("WROTE", dst, os.path.getsize(dst), "bytes")
