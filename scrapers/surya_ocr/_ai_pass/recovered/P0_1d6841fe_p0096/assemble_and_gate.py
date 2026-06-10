# Assemble the verified contingent-liability matrix for Yellowbook 2081 page 96 (table 5.16)
# and apply the GATE.
#
# Table: ५.१६ - कोषमा व्यवस्था नभएको सम्भावित दायित्वको विवरण (आ.व.२०७९/८०)
#        Statement of contingent liabilities not provisioned (FY 2079/80)
# Source: सार्वजनिक संस्थानको वार्षिक स्थिति समीक्षा २०८१ (Yellowbook 2081),
#         PDF page 96 (page_0096.json), doc id 1d6841fe, out_dir P0__ksi3tbe_1d6841fe.
# Unit: रु. लाखमा (NPR in lakhs). Extraction: surya-ocr 0.17.1; confidence grade B.
#
# THREE numeric value columns:
#   col2 = कोषमा व्यवस्था नभएको दायित्व रकम  (provision-not-made liability amount)   x-band ~819-876
#   col3 = सम्भावित दायित्व रकम              (contingent liability amount)            x-band ~929-1012
#   col4 = कुल जम्मा रकम                     (grand total amount)                     x-band ~1070-1158
#
# RECONCILIATION IDENTITIES (per the task brief):
#   (X) CROSS-COLUMN, per row:  col2 + col3 == col4   (+/-9)
#       verified clean on grand total: 528702 + 18001259 == 18529961.
#   (V) VERTICAL, per group:    sum(enterprise rows in a category) == that category's
#       जम्मा subtotal row, INDEPENDENTLY per numeric column (col2, col3, col4).  (+/-9)
#       verified clean on सामाजिक group col4: 218+6087+9459+13681 == 29445.
#   (G) GRAND VERTICAL:         sum(the 6 category जम्मा subtotal rows) == कुल जम्मा row,
#       per numeric column.  (+/-9)
#
# GATE (a cell is ACCEPTED iff every axis that APPLIES to it passes):
#   line-item cell  -> its row cross-reconciles (X) AND its group-column vertical foot (V) reconciles.
#   जम्मा cell      -> its row cross-reconciles (X) AND its group-column foot (V) reconciles
#                      (it is the foot target) AND the grand foot (G) for its column reconciles.
#   कुल जम्मा cell  -> its row cross-reconciles (X) AND the grand foot (G) for its column reconciles.
#   A cell whose own OCR token is dirty (script-mixed / stray glyph) is quarantined regardless.
#   A foot that contains a dirty/garbled component is UNEVALUABLE for that column (the residual is
#   a parse artifact, not a Rs break) -> cells gated on it cannot be accepted; recorded honestly.

import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
TOL = 9
DEVA = "०१२३४५६७८९"
D2A = {d: str(i) for i, d in enumerate(DEVA)}

def to_cell(s):
    """Return (value, status) where status in {'clean','dirty','blank','empty'}.
       clean : pure-Devanagari digits (the source script), trustworthy integer.
       dirty : OCR-suspect -> integer NOT trustworthy. This source is an all-Devanagari
               yellow-book table, so ANY Latin digit in a figure is an OCR glyph
               substitution (e.g. '9'<->'९', '5'<->'५'); script-mixing and stray glyphs
               are likewise garbled. All are flagged dirty.
       blank : printed nil marker '-'/'_' -> known-empty (value None, a real nil).
       empty : no token at all in this column for this row (value None)."""
    if s is None:
        return None, "empty"
    raw = s.strip()
    if raw in ("-", "_", "–", "—"):
        return None, "blank"
    out, suspect, saw_d, saw_l = [], False, False, False
    for ch in raw:
        if ch in D2A:
            out.append(D2A[ch]); saw_d = True
        elif ch.isdigit():
            out.append(ch); saw_l = True
        elif ch in (",", "،", " "):
            continue
        else:
            suspect = True
    if not out:
        return None, "dirty"        # token present but no digits (pure glyph junk)
    if saw_l:
        suspect = True              # any Latin digit in a Devanagari source -> garbled OCR
    # Western 3-digit comma grouping sanity (this table uses 1,234,567 style): every group
    # after the first must be exactly 3 digits. A stray/misplaced comma (e.g. '४७७,६') is a
    # garbled OCR token even when single-script. (Skip if a space was present -> already junk.)
    if "," in raw and " " not in raw and not saw_l:
        groups = [g for g in raw.replace("،", ",").split(",")]
        groups = ["".join(c for c in g if c in D2A) for g in groups]
        if len(groups) > 1:
            if any(len(g) != 3 for g in groups[1:]) or not (1 <= len(groups[0]) <= 3) or groups[0] == "":
                suspect = True
    return int("".join(out)), ("dirty" if suspect else "clean")

# (rownum_raw, slug, label_ne, raw_col2, raw_col3, raw_col4)
GROUPS = [
    ("audyogik", "औद्योगिक", [
        (1,  "dugdha-bikas",            "दुग्ध विकास संस्थान",                  "१८,१२५", None,   "१८,१२५"),
        (2,  "jadibuti",                "जडिबुटी उत्पादन तथा प्रशोधन कम्पनी लि.","७१३",   None,    "७१३"),
        (3,  "hetauda-cement",          "हेटौंडा सिमेन्ट उद्योग लि.",            "६,१६८",  "२४",    "६,१९३"),
        (4,  "janakpur-cigarette",      "जनकपुर चुरोट कारखाना लि.",             None,     "_",     None),
        (5,  "nepal-aushadhi",          "नेपाल औषधि लिमिटेड",                   "9,528",  "9,289", "३,०६६"),
        (6,  "udayapur-cement",         "उदयपुर सिमेन्ट उद्योग लि.",            "5,525",  None,    "5,545"),
        (7,  "nepal-orind-magnesite",   "नेपाल ओरिण्ड म्याग्नासाइट प्रा.लि.",     None,    None,    None),
        (8,  "butwal-dhago",            "बुटबल धागो कारखाना लि.",               None,     None,    None),
        (9,  "nepal-metal",             "नेपाल मेटल कम्पनी लि.",                None,     None,    None),
        (10, "dhaubadi-falam",          "धौवादी फलाम कम्पनी लि.",               None,     None,    None),
    ], (35688, "३५,६८८", 1266, "१,२६६", 34948, "34,948")),
    ("byaparik", "व्यापारिक", [
        (11, "krishi-samagri",          "कृषि सामग्री कम्पनी लि.",              None,     "५२,२८९","५२,२८९"),
        (12, "khadya-byabastha",        "खाद्य व्यवस्था तथा व्यापार कम्पनी लि.",  None,    None,    None),
        (13, "nepal-oil-nigam",         "नेपाल आयल निगम लि.",                   None,     "१,३७०", "9,३७०"),
        (14, "nepal-ban-nigam",         "नेपाल वन निगम लिमिटेड",                "823",    "२१६",   "६३९"),
    ], (823, "823", 53875, "५३,८७५", 54299, "५४,२९९")),
    ("sewa", "सेवा", [
        (15, "audyogik-chhetra-mgmt",   "औद्योगिक क्षेत्र व्यवस्थापन लि.",        "995",   None,    "995"),
        (16, "nepal-parbahan-godam",    "नेपाल पारवहन तथा गोदाम व्यवस्था कं.लि.", "900",   None,    "900"),
        (17, "nepal-bayusewa-nigam",    "नेपाल वायुसेवा निगम",                  None,     None,    None),
        (18, "rastriya-utpadakatwa",    "राष्ट्रिय उत्पादकत्व तथा आर्थिक विकास केन्द्र लि.","२७९",None,"२७९"),
        (19, "caan",                    "नेपाल नागरिक उड्डयन प्राधिकरण",         "३४,८१२", "४७७,६", "३९,५८६"),
        (20, "nepal-purbadhar",         "नेपाल पूर्वाधार निर्माण कम्पनी लि.",     None,    None,    None),
        (21, "sajha-yatayat",           "साझा यातायात सहकारी संस्था लि.",        None,     None,    None),
        (22, "nepal-railway",           "नेपाल रेल्वे कम्पनी लि.",              None,     None,    None),
        (23, "bishal-bajar",            "विशाल बजार कम्पनी लि.",                None,     None,    None),
    ], (36396, "३६,३९६", 4776, "४७७,६", 40170, "४०,१७०")),
    ("samajik", "सामाजिक सांस्कृतिक संस्थान", [
        (24, "gorkhapatra",             "गोरखापत्र संस्थान",                    "२१८",    None,    "२१८"),
        (25, "social-enterprise-2",     "सामाजिक सांस्कृतिक संस्थान (पंक्ति २)","६,०८७",  None,    "६,०८७"),
        (26, "janak-shiksha-samagri",   "जनक शिक्षा सामग्री केन्द्र लि.",        "९,४५९",  None,    "९,४५९"),
        (27, "nepal-television",        "नेपाल टेलिभिजन",                       "१३,६८१", None,    "१३,६८१"),
        (28, "rastriya-aawas",          "राष्ट्रिय आवास कम्पनी लि.",            "-",      "-",     None),
    ], (None, None, None, None, 29445, "२९,४४५")),
    ("janopayogi", "जनोपयोगी", [
        (29, "nepal-khanepani",         "नेपाल खानेपानी संस्थान",               "६,३७४",  None,    "६,३७४"),
        (30, "nea",                     "नेपाल विद्युत प्राधिकरण",               "३७८,६७१","७३५,११३","१,११३,७८४"),
        (31, "nepal-telecom",           "नेपाल दूरसञ्चार कम्पनी लि.",            None,     "४४,२१४","४४,२१४"),
        (32, "bidyut-utpadan",          "बिद्युत उत्पादन कम्पनी लि.",            "39",     None,    "39"),
        (33, "rastriya-prasaran-grid",  "राष्ट्रिय प्रशारण ग्रिड कम्पनी",        "39",     None,    "39"),
    ], (384122, "३८४,१२२", 780327, "७८०,३२७", None, "9,9 ६५,४४९")),
    ("bittiya", "वित्तीय", [
        (34, "adbl",                    "कृषि विकास बैङ्क लि.",                 None,     "9,२२०,५२९","9,२२०,५२९"),
        (35, "rbi-jeevan",              "राष्ट्रिय बिमा संस्थान (जीवन)",         None,    None,    None),
        (36, "rbi-company",             "राष्ट्रिय बिमा कम्पनी लि.",            None,     None,    None),
        (37, "rbb",                     "राष्ट्रिय वाणिज्य बैङ्क लि.",          "२०,९११", "५८८,१९६","६०९,१०७"),
        (38, "nikshep-karja-surakshan", "निक्षेप तथा कर्जा सुरक्षण कोष",         "9,480",  "१५,०६६,४२३","१५,०६७,९७०"),
        (39, "nepse",                   "नेपाल स्टक एक्सचेन्ज लिमिटेड",          "989",    "६२४",   "७७३"),
        (40, "nagarik-lagani-kosh",     "नागरिक लगानी कोष",                    None,     None,    None),
        (41, "hidcl",                   "हाइड्रोइलेक्ट्रिसिटी इन्भेष्टमेन्ट एण्ड डेभलपमेन्ट बैंक","ХЗ",None,"X3"),
        (42, "nepal-bank",              "नेपाल बैङ्क लि.",                      "१८,९६७", "२८६,२४४","३०५,२१२"),
    ], (41627, "४१,६२७", 17162017, "१७,१६२,०१७", 17203644, "१७,२०३,६४४")),
]
GRAND = (528702, "५२८,७०२", 18001259, "१८,००१,२५९", 18529961, "१८,५२९,९६१")
COLS = ["col2", "col3", "col4"]
COL_LABEL = {
    "col2": "कोषमा व्यवस्था नभएको दायित्व रकम",
    "col3": "सम्भावित दायित्व रकम",
    "col4": "कुल जम्मा रकम",
}

# ---- Parse every cell -------------------------------------------------------
def parse_row(c2, c3, c4):
    v2, s2 = to_cell(c2); v3, s3 = to_cell(c3); v4, s4 = to_cell(c4)
    return {"col2": (v2, s2, c2), "col3": (v3, s3, c3), "col4": (v4, s4, c4)}

# ---- Cross-column residual per row -----------------------------------------
def cross_resid(cells):
    v2 = cells["col2"][0]; v3 = cells["col3"][0]; v4 = cells["col4"][0]
    s2 = cells["col2"][1]; s3 = cells["col3"][1]; s4 = cells["col4"][1]
    if v4 is None:
        return None, "unevaluable (no col4 total token)"
    # any dirty operand contaminates the test
    dirty = any(cells[c][1] == "dirty" for c in ("col2", "col3", "col4"))
    # If BOTH disaggregating components are entirely absent ('empty'), we cannot test
    # col2+col3==col4 (this happens on subtotal rows where the col2/col3 subtotal tokens
    # were not captured by OCR; treating them as 0 would fabricate a -col4 break).
    if s2 == "empty" and s3 == "empty":
        return None, "unevaluable (both disaggregating components absent)"
    resid = (v2 or 0) + (v3 or 0) - v4
    if dirty:
        return resid, "dirty_operand"
    return resid, "clean"

# ---- Vertical foot per group per column ------------------------------------
def foot(group_rows, sub_val, col):
    comps = []
    any_dirty = False
    any_missing_expected = False  # we treat empty as 0 (blank line), not missing
    for (_, _, _, c2, c3, c4) in group_rows:
        v, st = to_cell({"col2": c2, "col3": c3, "col4": c4}[col])
        if st == "dirty":
            any_dirty = True
        if v is not None:
            comps.append(v)
    ssum = sum(comps)
    if sub_val is None:
        return ssum, None, None, "subtotal_missing", any_dirty
    resid = ssum - sub_val
    if any_dirty:
        return ssum, sub_val, resid, "unevaluable_dirty_component", True
    status = "reconciles" if abs(resid) <= TOL else "fail"
    return ssum, sub_val, resid, status, False

# Build parsed structure
parsed_groups = []
for gkey, gname, rows, sub in GROUPS:
    sv2, r_sv2, sv3, r_sv3, sv4, r_sv4 = sub
    grows = []
    for (rn, slug, ne, c2, c3, c4) in rows:
        grows.append({"rownum": rn, "slug": slug, "label_ne": ne,
                      "cells": parse_row(c2, c3, c4)})
    sub_parsed = {"col2": (sv2, r_sv2), "col3": (sv3, r_sv3), "col4": (sv4, r_sv4)}
    parsed_groups.append({"key": gkey, "name": gname, "rows": grows,
                          "subtotal": sub_parsed,
                          "subtotal_cross": parse_row(r_sv2, r_sv3, r_sv4)})

# Per-group per-column foot status
foot_status = {}
for (gkey, gname, rows, sub) in GROUPS:
    sv = {"col2": sub[0], "col3": sub[2], "col4": sub[4]}
    fs = {}
    for col in COLS:
        ssum, subv, resid, status, dirty = foot(rows, sv[col], col)
        fs[col] = {"sum": ssum, "subtotal": subv, "resid": resid, "status": status, "dirty_component": dirty}
    foot_status[gkey] = fs

# Grand foot per column (sum of 6 subtotals == grand)
grand_vals = {"col2": GRAND[0], "col3": GRAND[2], "col4": GRAND[4]}
grand_raw = {"col2": GRAND[1], "col3": GRAND[3], "col4": GRAND[5]}
grand_foot = {}
for col in COLS:
    comps = []
    any_missing = False
    any_dirty_sub = False
    for (gkey, gname, rows, sub) in GROUPS:
        sv = {"col2": sub[0], "col3": sub[2], "col4": sub[4]}[col]
        raw = {"col2": sub[1], "col3": sub[3], "col4": sub[5]}[col]
        _, st = to_cell(raw)
        if sv is None:
            any_missing = True
        else:
            comps.append(sv)
        if st == "dirty":
            any_dirty_sub = True
    ssum = sum(comps)
    gv = grand_vals[col]
    resid = (ssum - gv) if gv is not None else None
    if any_missing or any_dirty_sub:
        status = "unevaluable_dirty_or_missing_subtotal"
    elif resid is not None and abs(resid) <= TOL:
        status = "reconciles"
    else:
        status = "fail"
    grand_foot[col] = {"sum": ssum, "grand": gv, "resid": resid, "status": status,
                       "missing_subtotal": any_missing, "dirty_subtotal": any_dirty_sub}

# Grand row cross
grand_cross_cells = parse_row(GRAND[1], GRAND[3], GRAND[5])
grand_cross_resid, grand_cross_state = cross_resid(grand_cross_cells)

# ---- Apply the GATE ---------------------------------------------------------
accepted = []
quarantined = []

def emit(cell_dict):
    if cell_dict.get("_accept"):
        cell_dict.pop("_accept")
        accepted.append(cell_dict)
    else:
        cell_dict.pop("_accept", None)
        quarantined.append(cell_dict)

# line items + group subtotals
for pg in parsed_groups:
    gkey = pg["key"]; gname = pg["name"]
    # cross residual per data row
    for r in pg["rows"]:
        xresid, xstate = cross_resid(r["cells"])
        for col in COLS:
            v, st, raw = r["cells"][col]
            base = {
                "group": gkey, "group_label_ne": gname,
                "row_kind": "line_item", "rownum": r["rownum"],
                "row_slug": r["slug"], "label_ne": r["label_ne"],
                "column": col, "column_label_ne": COL_LABEL[col],
                "value": v, "raw_ocr": raw, "ocr_status": st,
            }
            reasons = []
            # own-cell OCR sanity
            if st == "dirty":
                reasons.append(f"ocr_digit_glyphs_suspect (script-mixed or stray glyph in raw '{raw}')")
            if st in ("empty", "blank"):
                reasons.append(f"no_value_in_cell ({'printed nil marker' if st=='blank' else 'no OCR token in this column'})")
            # cross-column axis (applies to every data row that has a col4 total)
            if xstate == "unevaluable (no col4 total token)":
                reasons.append("row_cross_unevaluable (row has no col4 total token to test col2+col3==col4)")
            elif xstate == "dirty_operand":
                reasons.append(f"row_cross_unevaluable_dirty (col2+col3-col4={xresid:+d} but a row operand is garbled OCR)")
            elif abs(xresid) > TOL:
                reasons.append(f"row_cross_fail (col2+col3-col4={xresid:+d}, >|{TOL}|)")
            # vertical group-column foot axis
            fst = foot_status[gkey][col]
            if fst["status"] == "subtotal_missing":
                reasons.append(f"group_foot_unevaluable ({gname}/{col} subtotal token missing/illegible)")
            elif fst["status"] == "unevaluable_dirty_component":
                reasons.append(f"group_foot_unevaluable ({gname}/{col} foot contains a garbled-glyph component; residual {fst['resid']:+d} is a parse artifact)")
            elif fst["status"] == "fail":
                reasons.append(f"group_foot_fail ({gname}/{col}: sum(rows)-subtotal={fst['resid']:+d}, >|{TOL}|)")
            if reasons:
                base["quarantine_reasons"] = reasons
                base["_accept"] = False
            else:
                base["row_cross_residual"] = xresid
                base["group_foot_residual"] = fst["resid"]
                base["_accept"] = True
            emit(base)
    # group subtotal cells
    sxresid, sxstate = cross_resid(pg["subtotal_cross"])
    for col in COLS:
        sv, rawsub = pg["subtotal"][col]
        _, sst = to_cell(rawsub)
        base = {
            "group": gkey, "group_label_ne": gname,
            "row_kind": "subtotal", "rownum": None,
            "row_slug": "jamma", "label_ne": "जम्मा",
            "column": col, "column_label_ne": COL_LABEL[col],
            "value": sv, "raw_ocr": rawsub, "ocr_status": sst,
        }
        reasons = []
        if sst == "dirty":
            reasons.append(f"ocr_digit_glyphs_suspect (script-mixed or stray glyph in raw '{rawsub}')")
        if sv is None:
            reasons.append("no_value_in_cell (subtotal token missing/illegible)")
        # subtotal row cross
        if sxstate.startswith("unevaluable"):
            reasons.append("subtotal_cross_unevaluable (no col4 subtotal token)")
        elif sxstate == "dirty_operand":
            reasons.append(f"subtotal_cross_unevaluable_dirty (col2+col3-col4={sxresid:+d}, garbled operand)")
        elif abs(sxresid) > TOL:
            reasons.append(f"subtotal_cross_fail (col2+col3-col4={sxresid:+d}, >|{TOL}|)")
        # this column's group foot must reconcile (the subtotal is its target)
        fst = foot_status[gkey][col]
        if fst["status"] == "subtotal_missing":
            reasons.append(f"group_foot_unevaluable ({gname}/{col} subtotal missing)")
        elif fst["status"] == "unevaluable_dirty_component":
            reasons.append(f"group_foot_unevaluable ({gname}/{col} foot has garbled component; residual {fst['resid']:+d} parse artifact)")
        elif fst["status"] == "fail":
            reasons.append(f"group_foot_fail ({gname}/{col}: sum(rows)-subtotal={fst['resid']:+d}, >|{TOL}|)")
        # grand foot for this column (subtotal participates as a component)
        gf = grand_foot[col]
        if gf["status"] != "reconciles":
            reasons.append(f"grand_foot_{gf['status']} ({col}: sum(6 subtotals)-grand={gf['resid']}, status={gf['status']})")
        if reasons:
            base["quarantine_reasons"] = reasons
            base["_accept"] = False
        else:
            base["row_cross_residual"] = sxresid
            base["group_foot_residual"] = fst["resid"]
            base["grand_foot_residual"] = gf["resid"]
            base["_accept"] = True
        emit(base)

# grand total row cells
for col in COLS:
    gv = grand_vals[col]; rawg = grand_raw[col]
    _, gst = to_cell(rawg)
    base = {
        "group": None, "group_label_ne": None,
        "row_kind": "grand_total", "rownum": None,
        "row_slug": "kul-jamma", "label_ne": "कुल जम्मा",
        "column": col, "column_label_ne": COL_LABEL[col],
        "value": gv, "raw_ocr": rawg, "ocr_status": gst,
    }
    reasons = []
    if gst == "dirty":
        reasons.append(f"ocr_digit_glyphs_suspect (raw '{rawg}')")
    if gv is None:
        reasons.append("no_value_in_cell")
    if grand_cross_state.startswith("unevaluable"):
        reasons.append("grand_cross_unevaluable")
    elif grand_cross_state == "dirty_operand":
        reasons.append(f"grand_cross_unevaluable_dirty ({grand_cross_resid:+d})")
    elif abs(grand_cross_resid) > TOL:
        reasons.append(f"grand_cross_fail (col2+col3-col4={grand_cross_resid:+d}, >|{TOL}|)")
    gf = grand_foot[col]
    if gf["status"] != "reconciles":
        reasons.append(f"grand_foot_{gf['status']} ({col}: sum(6 subtotals)-grand={gf['resid']}, status={gf['status']})")
    if reasons:
        base["quarantine_reasons"] = reasons
        base["_accept"] = False
    else:
        base["grand_cross_residual"] = grand_cross_resid
        base["grand_foot_residual"] = gf["resid"]
        base["_accept"] = True
    emit(base)

# ---- Residual rollups -------------------------------------------------------
per_row = []
for pg in parsed_groups:
    for r in pg["rows"]:
        xr, xs = cross_resid(r["cells"])
        per_row.append({
            "group": pg["key"], "rownum": r["rownum"], "row_slug": r["slug"],
            "label_ne": r["label_ne"],
            "col2": r["cells"]["col2"][0], "col3": r["cells"]["col3"][0], "col4": r["cells"]["col4"][0],
            "cross_residual": xr, "cross_state": xs,
        })
    sxr, sxs = cross_resid(pg["subtotal_cross"])
    per_row.append({
        "group": pg["key"], "rownum": None, "row_slug": "jamma", "label_ne": "जम्मा",
        "col2": pg["subtotal"]["col2"][0], "col3": pg["subtotal"]["col3"][0], "col4": pg["subtotal"]["col4"][0],
        "cross_residual": sxr, "cross_state": sxs,
    })
per_row.append({
    "group": None, "rownum": None, "row_slug": "kul-jamma", "label_ne": "कुल जम्मा",
    "col2": GRAND[0], "col3": GRAND[2], "col4": GRAND[4],
    "cross_residual": grand_cross_resid, "cross_state": grand_cross_state,
})

per_group_foot = []
for pg in parsed_groups:
    entry = {"group": pg["key"], "group_label_ne": pg["name"]}
    for col in COLS:
        entry[col] = foot_status[pg["key"]][col]
    per_group_foot.append(entry)

# worst residual over EVALUABLE identities whose operands are all clean (genuine breaks only)
genuine = []
# clean cross rows
for pr in per_row:
    if pr["cross_state"] == "clean" and pr["cross_residual"] is not None:
        genuine.append(abs(pr["cross_residual"]))
# clean group foots
for pg in parsed_groups:
    for col in COLS:
        fs = foot_status[pg["key"]][col]
        if fs["status"] in ("reconciles", "fail") and fs["resid"] is not None:
            genuine.append(abs(fs["resid"]))
# clean grand foots
for col in COLS:
    gf = grand_foot[col]
    if gf["status"] in ("reconciles", "fail") and gf["resid"] is not None:
        genuine.append(abs(gf["resid"]))
worst_residual = max(genuine) if genuine else 0

worst_accepted = 0
for a in accepted:
    for k in ("row_cross_residual", "group_foot_residual", "grand_foot_residual", "grand_cross_residual"):
        if a.get(k) is not None:
            worst_accepted = max(worst_accepted, abs(a[k]))

matrix_reconciles = (
    grand_cross_state == "clean" and abs(grand_cross_resid) <= TOL and
    all(grand_foot[c]["status"] == "reconciles" for c in COLS) and
    all(foot_status[pg["key"]][c]["status"] == "reconciles" for pg in parsed_groups for c in COLS)
)

out = {
    "source_pdf": "Financial Data/mof_documents/yellowbook/सार्वजनिक संस्थानको वार्षिक स्थिति समीक्षा २०८१_ksi3tbe.pdf",
    "source_page": 96,
    "page_id": "P0_1d6841fe_p0096",
    "out_dir": "P0__ksi3tbe_1d6841fe",
    "table": "५.१६ कोषमा व्यवस्था नभएको सम्भावित दायित्वको विवरण (आ.व.२०७९/८०)",
    "table_en": "Statement of contingent liabilities not provisioned in fund (FY 2079/80)",
    "measure": "contingent_liabilities_unprovisioned",
    "unit": "npr_lakh",
    "price_basis": "nominal",
    "fiscal_year_bs": "2079/80",
    "provenance": {
        "extraction_method": "surya-ocr",
        "model_version": "0.17.1",
        "verification": "bbox-resolved transcription from page_0096.json; cross-column (col2+col3==col4) + per-group vertical foot + grand-foot reconciliation; GATE applied",
        "confidence_grade": "B",
        "value_columns": [{"key": c, "label_ne": COL_LABEL[c]} for c in COLS],
        "tolerance_lakh": TOL,
        "identities": {
            "cross_column_per_row": "col2 + col3 == col4 (+/-9)",
            "vertical_per_group": "sum(enterprise rows in category) == category jamma subtotal, per column (+/-9)",
            "grand_vertical": "sum(6 category jamma subtotals) == kul-jamma row, per column (+/-9)",
        },
        "gate": ("line-item accepted iff its row cross-reconciles AND its group-column vertical foot "
                 "reconciles; jamma accepted iff its row cross-reconciles AND its group foot reconciles "
                 "AND the grand foot for its column reconciles; kul-jamma accepted iff grand cross AND "
                 "grand foot reconcile; any cell with a dirty OCR token is quarantined; a foot with a "
                 "garbled component is unevaluable."),
    },
    "columns": [{"key": c, "label_ne": COL_LABEL[c]} for c in COLS],
    "groups": [{"key": pg["key"], "label_ne": pg["name"],
                "rownums": [r["rownum"] for r in pg["rows"]]} for pg in parsed_groups],
    "accepted_cells": accepted,
    "quarantined_cells": quarantined,
    "reconciliation": {
        "per_row_cross": per_row,
        "per_group_vertical_foot": per_group_foot,
        "grand_vertical_foot": grand_foot,
        "grand_cross": {"residual": grand_cross_resid, "state": grand_cross_state,
                        "col2": GRAND[0], "col3": GRAND[2], "col4": GRAND[4]},
        "worst_residual_lakh_genuine": worst_residual,
        "worst_residual_lakh_accepted": worst_accepted,
        "cross_source": None,
        "diagnostics": {
            "clean_anchors_confirmed": [
                "grand cross: 528702 + 18001259 == 18529961 (residual 0)",
                "samajik group col4 foot: 218+6087+9459+13681 == 29445 (residual 0)",
            ],
            "ocr_defect_cells": [
                "audyogik row5 (nepal-aushadhi): col2 '9,528'/col3 '9,289'/col4 '३,०६६' - Latin-digit col2/col3, cross fails +15751; whole row untrustworthy",
                "audyogik row6 (udayapur-cement): col2 '5,525' col4 '5,545' Latin digits; cross -20",
                "byaparik row13 (nepal-oil): col4 '9,३७०' = Latin-9 + Deva => script-mixed (true ~1,370); cross -8000",
                "byaparik row14 (nepal-ban-nigam): col2 '823' Latin; cross 823+216-639=+400 fail",
                "sewa row19 / sewa subtotal: col3 '४७७,६' is a malformed/garbled token (comma misplaced); group col3 foot contaminated",
                "janopayogi subtotal col4 '9,9 ६५,४४९' = mixed Latin/Deva with spaces (true ~1,164,449); grand col4 foot contaminated",
                "janopayogi rows 32,33: col2/col4 '39' Latin digits",
                "bittiya row34 (adbl): col3/col4 '9,२२०,५२९' Latin-9 prefix (script-mixed)",
                "bittiya row38 (nikshep): col2 '9,480' Latin; cross +7933 fail",
                "bittiya row39 (nepse): col2 '989' Latin; cross +840 fail",
                "bittiya row41 (hidcl): col2 'ХЗ' / col4 'X3' = Cyrillic/Latin glyph junk, no real value",
            ],
            "interpretation": (
                "Table 5.16, contingent liabilities by enterprise, FY2079/80, in lakh. The arithmetic "
                "backbone is sound: the GRAND cross-column identity is exact (528702+18001259=18529961) "
                "and the samajik group col4 foot is exact (29445). Acceptance is driven by the AND of "
                "(row cross-column) and (group vertical foot). Many rows have only a single populated "
                "value column (col2 OR col3) repeated into col4, so their cross-column trivially holds; "
                "those are accepted when their group's column also foots. Cells are quarantined where "
                "(a) the OCR token is script-mixed/garbled (Latin digits, Cyrillic glyphs, misplaced "
                "commas), or (b) the applicable group/grand foot is contaminated by such a garbled "
                "component and is therefore unevaluable, or (c) the row cross-column genuinely fails. "
                "No values were corrected/back-solved into the matrix; defects are recorded only."
            ),
        },
    },
    "summary": {
        "matrix_reconciles": matrix_reconciles,
        "accepted_count": len(accepted),
        "quarantined_count": len(quarantined),
        "worst_residual_lakh": worst_residual,
        "note": (
            "Yellowbook 2081 table 5.16 (contingent liabilities not provisioned, FY2079/80, lakh). "
            "Three value columns col2(provision-not-made)+col3(contingent)=col4(total). Grand cross "
            "identity is exact and samajik col4 foots exactly. The matrix does NOT fully reconcile "
            "because two subtotal/grand cells are OCR-garbled (sewa col3 '४७७,६' and janopayogi col4 "
            "'9,9 ६५,४४९'), so the sewa col3 group-foot and the col4 grand-foot are unevaluable. Cells "
            "that pass BOTH their applicable axes (row cross + group foot) are accepted; everything "
            "else is quarantined with a reason. Nothing fabricated or back-solved into values."
        ),
    },
}

dst = os.path.join(HERE, "verified_matrix.json")
json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("=== GROUP VERTICAL FOOTS ===")
for pg in parsed_groups:
    for col in COLS:
        fs = foot_status[pg["key"]][col]
        print(f"  {pg['key']:11} {col}: sum={fs['sum']} sub={fs['subtotal']} resid={fs['resid']} -> {fs['status']}")
print("=== GRAND FOOT ===")
for col in COLS:
    print(f"  {col}: {grand_foot[col]}")
print("grand cross:", grand_cross_resid, grand_cross_state)
print("matrix_reconciles:", matrix_reconciles)
print("worst_residual (genuine, clean operands):", worst_residual)
print("accepted_count:", len(accepted))
print("quarantined_count:", len(quarantined))
print("total cells:", len(accepted) + len(quarantined))
print("WROTE", dst, os.path.getsize(dst), "bytes")
