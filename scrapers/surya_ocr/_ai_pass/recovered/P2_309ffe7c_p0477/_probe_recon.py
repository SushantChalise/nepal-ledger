# Probe: parse the 16x19 grid for p0477 (percent structure) and test the
# column-foot identity sum(rows 0..17) == row 18 (कुल जम्मा) == 100.0 per column.
import json, os

SRC = r'C:\Users\ACER\Projects\Economy\.claude\worktrees\loving-wing-7bdcb4\scrapers\surya_ocr\_ocr_output\P2__Economic_Survey_2081-82_309ffe7c\page_0477.json'
d = json.load(open(SRC, encoding='utf-8'))
tl = d['text_lines']

BAND_MID = [629, 708, 785, 865, 943, 1023, 1104, 1182, 1260, 1338, 1418, 1496, 1575, 1653, 1733, 1811]
# 19 row y-centers from inspection
ROW_Y = [434, 462, 492, 521, 580, 610, 668, 698, 727, 756, 788, 818, 848, 878, 910, 941, 970, 1002, 1033]

def band(xc):
    return min(range(16), key=lambda i: abs(xc - BAND_MID[i]))

def nearest_row(yc):
    return min(range(19), key=lambda i: abs(yc - ROW_Y[i]))

# Build grid[row][col] = (text, conf). Numeric area only.
grid = [[None]*16 for _ in range(19)]
for t in tl:
    b = t['bbox']; yc = (b[1]+b[3])/2; xc = (b[0]+b[2])/2
    if xc > 560 and 410 < yc < 1050:
        r = nearest_row(yc); c = band(xc)
        if grid[r][c] is None or t['confidence'] > grid[r][c][1]:
            grid[r][c] = (t['text'], t['confidence'])

DEVA = "०१२३४५६७८९"
D2A = {ch: str(i) for i, ch in enumerate(DEVA)}
# common OCR confusions for Devanagari digits seen in this page
EXTRA = {
    '९': '9', '५': '5', '०': '0', '१': '1', '२': '2', '३': '3', '४': '4', '६': '6', '७': '7', '८': '8',
}

def parse_num(s):
    """Return (value_float, clean_bool, reason). Percent values; one decimal place expected."""
    if s is None:
        return None, False, "missing"
    raw = s.strip().replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '')
    raw = raw.replace('<u>', '').replace('</u>', '').replace('<br>', ' ')
    body = raw
    out = []
    saw_deva = saw_latin = suspect = False
    dotcount = 0
    for ch in body:
        if ch in D2A:
            out.append(D2A[ch]); saw_deva = True
        elif ch.isdigit():
            out.append(ch); saw_latin = True
        elif ch in ('.', ',', '۔', '٬'):
            out.append('.'); dotcount += 1
        elif ch in (' ', '‍', '‌'):
            continue
        else:
            suspect = True
    if not out or all(c == '.' for c in out):
        return None, False, "no_digits(raw=%r)" % raw
    if saw_deva and saw_latin:
        suspect = True
    # collapse multiple dots: keep last as decimal
    joined = ''.join(out)
    if dotcount > 1:
        suspect = True
        parts = joined.split('.')
        joined = ''.join(parts[:-1]) + '.' + parts[-1]
    try:
        v = float(joined)
    except ValueError:
        return None, False, "unparseable(raw=%r)" % raw
    return v, (not suspect), (None if not suspect else "suspect(raw=%r)" % raw)

val = [[None]*16 for _ in range(19)]
clean = [[False]*16 for _ in range(19)]
rawg = [[None]*16 for _ in range(19)]
conf = [[None]*16 for _ in range(19)]
for r in range(19):
    for c in range(16):
        cell = grid[r][c]
        rawg[r][c] = cell[0] if cell else None
        conf[r][c] = cell[1] if cell else None
        v, ok, why = parse_num(cell[0] if cell else None)
        val[r][c] = v; clean[r][c] = ok

PROV = ["koshi","koshi","madhes","madhes","bagamati","bagamati","gandaki","gandaki",
        "lumbini","lumbini","karnali","karnali","sudur-pashchim","sudur-pashchim","nepal","nepal"]

print("=== RAW GRID (text) ===")
for r in range(19):
    cells = " | ".join((rawg[r][c] or "·").ljust(7) for c in range(16))
    print(f"r{r:2d}: {cells}")

print("\n=== PARSED VALUES ===")
for r in range(19):
    cells = " | ".join(("%5.1f"%val[r][c] if val[r][c] is not None else "  ?  ") for c in range(16))
    print(f"r{r:2d}: {cells}")

print("\n=== COLUMN FOOT (sum rows0..17) vs row18 (printed total) vs 100.0 ===")
for c in range(16):
    comps = [val[r][c] for r in range(18)]
    miss = [r for r in range(18) if val[r][c] is None]
    tot = val[18][c]
    s = sum(x for x in comps if x is not None)
    print(f"col {c:2d} {PROV[c]:14s} sum0..17={s:6.1f}  printed_tot={tot!s:>6}  resid_vs_100={s-100.0:+.1f}  missing_rows={miss}")
