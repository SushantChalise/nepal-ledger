# Inspect the OCR grid for Economic Survey 2081-82 page 0477
# (अनुसूची १३.३ : provincial GDP structure by broad industry, IN PERCENT).
# Goal: discover the 16 data-column x-band centers and the 19 row y-centers,
# snap every numeric token into grid[row][col], and print raw cells for eyeballing.
import json, os

SRC = r'C:\Users\ACER\Projects\Economy\.claude\worktrees\loving-wing-7bdcb4\scrapers\surya_ocr\_ocr_output\P2__Economic_Survey_2081-82_309ffe7c\page_0477.json'
d = json.load(open(SRC, encoding='utf-8'))
tl = d['text_lines']

# Numeric tokens live to the right of the row-label column (x > ~560).
# Collect their x-centers to discover column bands.
num_tokens = []
for t in tl:
    b = t['bbox']
    xc = (b[0] + b[2]) / 2
    yc = (b[1] + b[3]) / 2
    if xc > 560 and 410 < yc < 1050:
        num_tokens.append((round(xc), round(yc), t['text'], round(t['confidence'], 2)))

# Distribution of x-centers -> cluster into columns
xs = sorted(t[0] for t in num_tokens)
print("=== x-center histogram (numeric tokens) ===")
clusters = []
cur = [xs[0]]
for x in xs[1:]:
    if x - cur[-1] <= 25:
        cur.append(x)
    else:
        clusters.append(cur); cur = [x]
clusters.append(cur)
print("n x-clusters:", len(clusters))
for c in clusters:
    print(f"  band x~{round(sum(c)/len(c))}  n={len(c)}  range[{c[0]}..{c[-1]}]")

# y-centers -> rows
ys = sorted(set(t[1] for t in num_tokens))
print("\n=== y-center clusters (rows) ===")
yclusters = []
cur = [ys[0]]
for y in ys[1:]:
    if y - cur[-1] <= 18:
        cur.append(y)
    else:
        yclusters.append(cur); cur = [y]
yclusters.append(cur)
print("n y-clusters:", len(yclusters))
for c in yclusters:
    print(f"  row y~{round(sum(c)/len(c))}  n={len(c)}")
