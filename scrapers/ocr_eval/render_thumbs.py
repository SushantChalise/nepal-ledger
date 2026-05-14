"""Render thumbnails of candidate pages so we can pick visually."""

from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "Financial Data"
OUT = Path(__file__).parent / "thumbs"
OUT.mkdir(exist_ok=True)

PICKS = [
    ("P1_yellowbook", "mof_documents/yellowbook/1685280975_Yellow Book BIG 2080 Final_6jh3p9r.pdf", [14, 13, 39, 16, 0]),
    ("P2_redbook", "mof_documents/redbook/Redbook (Final)_2079_80_uryb8ga.pdf", [27, 25, 26, 2]),
    ("P3_intergov", "mof_documents/intergovernmental/208283.pdf", [26, 23, 12]),
    ("P4_nrb_bfi", "nrb_monthly_statistics/bfi_niyamabali.pdf", [9, 1, 5, 14]),
    ("P5_old_redbook", "mof_documents/redbook/Budget Details - Red Book 2062 - 2063_20130717120229_cbmey2a.pdf", [7, 8, 33, 11]),
    ("P5_old_intergov", "mof_documents/intergovernmental/207475.pdf", [0, 12, 7, 15]),
]


def main() -> None:
    for label, rel, pages in PICKS:
        path = CORPUS / rel
        pdf = pdfium.PdfDocument(str(path))
        for p in pages:
            if p >= len(pdf):
                continue
            page = pdf[p]
            # 120 DPI thumbnail — readable enough for eyeballing
            img = page.render(scale=120 / 72).to_pil()
            # downscale long edge to 1200 to keep files small
            w, h = img.size
            scale = 1200 / max(w, h)
            if scale < 1:
                img = img.resize((int(w * scale), int(h * scale)))
            out = OUT / f"{label}_p{p:03d}.png"
            img.save(out, "PNG", optimize=True)
            print(f"wrote {out.name}  ({img.size[0]}x{img.size[1]})")
            page.close()
        pdf.close()


if __name__ == "__main__":
    main()
