# Surya OCR — Research Findings

**Date:** 2026-05-14
**Upstream version surveyed:** `surya-ocr` v0.17.1 (released 2026-01-30 / -31 on PyPI)
**Canonical repo:** `github.com/datalab-to/surya` (master branch). The historical `github.com/VikParuchuri/surya` URL still appears in the BibTeX and PyPI metadata but redirects to the `datalab-to` org; the README is identical.
**License posture:** Code GPL-3.0-or-later; model weights under a modified OpenRAIL-M ("free for research, personal use, and startups under USD 2M funding/revenue"). For NRB/FCGO data work as a public-good project this is fine; commercial self-hosting would need a paid license from datalab.to.

**Three-sentence summary.** Surya is a PyTorch toolkit that composes six independent document-AI tasks — text detection, OCR/recognition, layout analysis, reading order, table recognition, and LaTeX OCR — each exposed as a CLI command and a Python `Predictor` class with pydantic schemas. Devanagari (Nepali `ne`, Hindi `hi`, plus Marathi/Sanskrit/etc.) is in the recognition model's official language set, although the v0.16.0 (Aug 2025) OCR-model rewrite removed user-facing per-call language hints — language is now inferred and there are open issues (#388, #475) where Hindi/Devanagari pages return null or wrong-script text. Table recognition is a separate decoder-only model that emits cells, rows, columns, colspan/rowspan and header flags — but cell **text** is sourced from the underlying PDF text layer, not re-OCRed, which is the #1 reason scanned (image-only) NRB PDFs need a layout + crop + OCR pipeline rather than the single-shot `surya_table` command.

---

## 1. What Surya does

Six capabilities, each independently invokable from the CLI or Python. From the README:

> Surya is a document OCR toolkit that does:
> - OCR in 90+ languages that benchmarks favorably vs cloud services
> - Line-level text detection in any language
> - Layout analysis (table, image, header, etc detection)
> - Reading order detection
> - Table recognition (detecting rows/columns)
> - LaTeX OCR

**Module layout** (`surya/` package):

| Module | Purpose | CLI entry point |
|---|---|---|
| `surya.detection` | Line-level text bbox detection (modified EfficientViT, semantic segmentation) | `surya_detect` |
| `surya.foundation` | Shared vision-text foundation transformer (Donut-derived) used by recognition & layout | (used internally) |
| `surya.recognition` | Text recognition / OCR | `surya_ocr` |
| `surya.layout` | Layout element classification + reading order in one model | `surya_layout` |
| `surya.table_rec` | Table cell / row / column / colspan / merge prediction | `surya_table` |
| `surya.texify` | LaTeX OCR (math equations) | `surya_latex_ocr` |
| `surya.ocr_error` | OCR-error detection classifier (post-hoc) | (programmatic) |
| `surya.input` | PDF→image, image loading utilities | — |
| `surya.scripts` | CLI dispatchers + finetune script | — |

A Streamlit playground `surya_gui` is also installed.

**Composable vs independent.**
- `detection`, `layout`, `table_rec`, `texify`, `ocr_error` are independently callable.
- `recognition` requires a `FoundationPredictor` instance and optionally takes a `DetectionPredictor` (when omitted, recognition assumes the input image is already cropped to a single line).
- `layout` also takes a `FoundationPredictor` constructed with the layout checkpoint (`settings.LAYOUT_MODEL_CHECKPOINT`).
- `table_rec` does NOT need detection or recognition — it predicts cell geometry only; **text inside cells must be filled in separately** (either from the PDF text layer or by cropping each cell and running `surya_ocr`).

**GPU vs CPU.** Everything runs on CPU; nothing is GPU-required. `torch_device` is auto-detected with priority `cuda → mps → xla → cpu` (`settings.py` lines 33-52). CPU defaults are tuned conservatively (e.g. `DETECTOR_BATCH_SIZE=2`, `RECOGNITION_BATCH_SIZE=8`, `TABLE_REC_BATCH_SIZE=8` per `TableRecPredictor.default_batch_sizes`). README claims A10 GPU per-page times: detection 0.108s, layout 0.27s, table-rec 0.022s, reading order 0.4s, OCR ~0.62s.

---

## 2. Language coverage

The authoritative list lives in `surya/recognition/languages.py` — a single dict `CODE_TO_LANGUAGE` (97 keys including `_math`). Devanagari-relevant entries:

```python
"hi": "Hindi",
"mr": "Marathi",
"ne": "Nepali",
"sa": "Sanskrit",
```

Plus other Indic neighbours:
```python
"as": "Assamese",  "bn": "Bengali",  "gu": "Gujarati",
"kn": "Kannada",   "ml": "Malayalam", "or": "Oriya",
"pa": "Punjabi",   "sd": "Sindhi",    "si": "Sinhala",
"ta": "Tamil",     "te": "Telugu",    "ur": "Urdu",
```

The file has **no script classification, no per-language confidence, no script→language map** — it's a flat ISO-639-1 dict. Hindi/Nepali/Marathi/Sanskrit all share Devanagari but Surya doesn't expose that grouping. (Bengali, Gujarati, Tamil etc. each have their own scripts, but again no script tag.)

**[GAP — important for us]** README §"Limitations" says: "You can find language support for OCR in `surya/recognition/languages.py`. **Text detection, layout analysis, and reading order will work with any language.**" — so detection/layout/order are script-agnostic; only recognition is language-bound.

**Benchmark on Devanagari.** README §"OCR" reports a single aggregate score (avg similarity 0.97 across languages on common-crawl PDFs + synthetic data), with a separate Google-Cloud comparison. There's a "Full language results" PNG (`static/images/rec_acc_table.png` and `static/images/gcloud_full_langs.png`) — **the per-Devanagari score is not in the README text**, only in those images, which I cannot read here. **[GAP]** We will need to render those images locally and check the Hindi/Nepali rows, or run our own micro-benchmark on NRB-extracted pages.

**Caveats for mixed-script PDFs (Nepali tables with English column headers and Devanagari numerals).** Since v0.16.0 the OCR model no longer accepts a `langs=` argument (README + open issue #388: "From Surya 3, how can i config the ocr's language?" — unresolved, assigned but no maintainer reply). The model auto-detects script per line. Open issue **#475 (Dec 2025)**: Hindi word images return null text while bounding boxes are produced — a Devanagari-specific regression that is **open and unfixed at v0.17.1**. This is almost certainly part of why "extraction quality was poor" in the prior chat.

**Concrete recommendation for Nepal Ledger.** For NRB Devanagari tables, do not rely on the bare `surya_ocr` command. Instead:
1. Use `surya_layout` to find table regions (script-agnostic — works fine for Devanagari).
2. Use `surya_detect` to find line bboxes inside the cell region (also script-agnostic).
3. Crop each line and pass through `RecognitionPredictor` with `det_predictor=None` (the line-level OCR path that historically had better Devanagari behaviour).
4. Run the OCR-error detection model (`ocr_error/2025_02_18`) on each line and flag low-confidence rows for human review.
5. Treat any null/empty `text` field as a regression bug, not a "no text" signal.

---

## 3. Output schema

All predictors return pydantic `BaseModel` instances (not dicts) when called from Python; the CLI serializes them to JSON. Schemas are stable since v0.16; v0.15→v0.16 changed `chars`/`words` fields significantly.

### 3.1 OCR / Recognition — `surya.recognition.schema`

```python
class BaseChar(PolygonBox):              # polygon + bbox inherited from PolygonBox
    text: str
    confidence: Optional[float] = 0      # NaN-coerced to 0

class TextChar(BaseChar):
    bbox_valid: bool = True              # False for special tokens, math

class TextWord(BaseChar):
    bbox_valid: bool = True

class TextLine(BaseChar):
    chars: List[TextChar]
    original_text_good: bool = False     # NEW since v0.16 — when text came from PDF layer not re-OCR
    words: List[TextWord] | None = None

class OCRResult(BaseModel):
    text_lines: List[TextLine]
    image_bbox: List[float]              # [x1, y1, x2, y2]
```

`PolygonBox` (in `surya.common.polygon`) adds:
- `polygon: List[List[float]]` — 4 points, clockwise from top-left
- `bbox: List[float]` — axis-aligned (x1, y1, x2, y2), top-left origin
- `confidence: Optional[float]`

The README documents the JSON form (lines 126-146): each page has `text_lines[]`, `page` (int), `image_bbox`. Each `text_line` has `text`, `confidence`, `polygon`, `bbox`, `chars[]`, `words[]`.

### 3.2 Detection — `surya.detection`

JSON-only documentation (README lines 182-191):
- `bboxes[]`: `bbox`, `polygon`, `confidence`
- `vertical_lines[]`: `bbox` only
- `page`, `image_bbox`

### 3.3 Layout — `surya.layout`

(README lines 223-232) Each `bbox` carries:
- `bbox`, `polygon`, `position` (reading-order int), `top_k` (dict label→confidence)
- `label`: one of **15 classes** — `Caption`, `Footnote`, `Formula`, `List-item`, `Page-footer`, `Page-header`, `Picture`, `Figure`, `Section-header`, `Table`, `Form`, `Table-of-contents`, `Handwriting`, `Text`, `Text-inline-math`.

These 15 labels are what we'd map into our `surya_layout_block` schema on the Node side.

### 3.4 Table recognition — `surya.table_rec.schema`

```python
class TableCell(PolygonBox):
    row_id: int
    colspan: int
    within_row_id: int
    cell_id: int
    is_header: bool
    rowspan: int | None = None
    merge_up: bool = False
    merge_down: bool = False
    col_id: int | None = None
    text_lines: List[dict] | None = None   # only populated if you fill it

class TableRow(PolygonBox):
    row_id: int
    is_header: bool

class TableCol(PolygonBox):
    col_id: int
    is_header: bool

class TableResult(BaseModel):
    cells: List[TableCell]
    unmerged_cells: List[TableCell]    # IMPORTANT: pre-merge cells, useful for debugging merges
    rows: List[TableRow]
    cols: List[TableCol]
    image_bbox: List[float]
```

The README JSON description (lines 270-288) is slightly less detailed than the source: it omits `unmerged_cells`, `merge_up`, `merge_down`, `within_row_id`. **The source is canonical — use it for our Zod schemas.**

### 3.5 Reading order

Folded into the layout output (`position` integer on each layout box) since the v0.17.0 layout rewrite (Sep 2025). No separate predictor or schema.

---

## 4. Table recognition (priority section)

NRB CMEFs and FCGO budget tables are the hard targets. Here is everything we have on Surya's table path.

### 4.1 How detection vs recognition split

There are TWO ways tables enter Surya:

1. **End-to-end via `surya_table`**: Surya first runs an internal table detector (a layout sub-task) to find table bounding boxes on the page, then runs the table-rec decoder on each crop.
2. **Skip detection via `--skip_table_detection`**: pass an already-cropped table image directly. Useful when you know table coordinates from another source (e.g. our own `surya_layout` pass).

CLI flags (README lines 261-266):
- `--detect_boxes` — by default cell text is **pulled from the PDF text layer**, not OCRed. Set this flag to detect cell bboxes via the model instead. Critical for image-only / scanned PDFs.
- `--skip_table_detection` — for pre-cropped table images.

### 4.2 Cell-level output

The decoder is autoregressive and predicts a *sequence* of cells, each cell encoded as a bag of "box properties": `bbox` (regression), `category` (classification — cell vs header vs etc.), `colspan` (regression, clamped ≥1), `rowspan`, plus merge directions. See `surya/table_rec/__init__.py` lines 80-110 (`BOX_PROPERTIES` loop). Cells stop generating when the model emits EOS or pad — capped at `TABLE_REC_MAX_BOXES=150` per table.

**Implication for NRB:** any single table with >150 cells will be truncated silently. The NRB CMEFs nine-months table 9.B has rows × columns easily in the hundreds. We need to either (a) raise `TABLE_REC_MAX_BOXES` env var, (b) chunk the table by manually splitting the input image into vertical strips, or (c) detect this overflow by checking that the last cell's `row_id`/`col_id` equals the last row/col we expect. **[GAP — not in docs]** — needs empirical test.

### 4.3 Header detection

Each `TableCell`, `TableRow`, `TableCol` has an `is_header: bool` field. The README shows it (lines 274, 278, 285). No multi-level header support is documented — a cell is header xor not. **For NRB tables with multi-row headers (e.g. "Particulars / Mid-July / Year-on-year change / % change" two-row), expect Surya to mark the first row as header and miss the second header row.** **[GAP — verify empirically]**

### 4.4 Merged cells

`TableCell.colspan: int` and `rowspan: int | None`. Plus `merge_up: bool`, `merge_down: bool` — these are the raw decoder predictions; the public field is `colspan`/`rowspan` after `unmerged_cells` → `cells` post-processing. `TableResult.unmerged_cells` preserves the pre-merge view, so you can debug merge mistakes.

**Open issue #372** (closed without fix, May 2025): cells were merged vertically when they shouldn't have been; user asked "Is there a minimum row height that would cause all that?" — no maintainer answer. **This is a real footgun** — Devanagari documents tend to have tighter line spacing than English, which may amplify the false-merge rate. **Recommendation: always log `unmerged_cells` alongside `cells` during ingestion so we can diff and detect over-merging.**

### 4.5 Footer / row-total handling

No explicit "footer" cell class. Row totals appear as ordinary cells. The layout model has a `Page-footer` label but that is page footer, not table footer. **[GAP]** — for NRB tables where "Total" rows are visually distinguished (bold, separator line), we will need our own postprocess heuristic.

### 4.6 Multi-page table continuation

**Not handled by Surya.** Each page is processed independently. NRB nine-months tables span 5-8 pages each — we will need our own continuation logic: same column-count + same header → glue.

### 4.7 Image-only vs hybrid PDFs

This is the bear trap. README line 264 (paraphrasing): "`--detect_boxes` specifies if cells should be detected. **By default, they're pulled out of the PDF, but this is not always possible.**" If the PDF is image-only (a scan, like many NRB and almost all FCGO PDFs), the PDF text layer is empty, so cells get null `text`. Without `--detect_boxes` you may get bbox-only output with no text at all.

**Recommendation:** ALWAYS run `surya_table` on Nepal financial PDFs with `--detect_boxes`. Then run `surya_ocr` over each cell bbox to fill `text_lines`. Do not trust the default extract-from-PDF path.

### 4.8 Performance

- Per-image: 0.302s on A10 GPU (README benchmark vs Table Transformer's 0.081s — Surya is 3-4x slower but more accurate).
- Memory: `TABLE_REC_BATCH_SIZE` defaults to 64 on GPU (~10 GB VRAM @ 150 MB/item), 8 on CPU.
- Compile speedup: enabling `COMPILE_TABLE_REC=true` gives ~11.5% gain on A10.

### 4.9 Known failure modes (the likely "prior chat got this wrong")

1. **Default does not OCR cell text** — born-digital path assumes a usable PDF text layer. Scanned NRB pages get empty `text`.
2. **`TABLE_REC_MAX_BOXES=150` ceiling** — silent truncation on large tables.
3. **`TABLE_REC_IMAGE_SIZE` is 768×768** — Surya resizes every table crop to 768×768 for the decoder. Very wide tables (NRB pages are landscape A4-ish; CMEFs Table 9 has ~10 numeric columns) get squashed horizontally; very tall tables lose detail. Pre-cropping per-page and feeding via `--skip_table_detection` lets you control aspect ratio.
4. **No multi-level header support.**
5. **Vertical false-merge bug (#372) for small-row-height tables.**
6. **No multi-page join.**
7. **Per-cell text alignment is not in output** — there's no "cell text reading order"; if a cell contains multiple lines, you get `text_lines: List[dict]` but you must order them yourself.

---

## 5. Scanned pages vs born-digital PDFs (priority section)

### 5.1 How Surya handles image-only PDFs

`surya/input/load.py` uses `surya.input.processing.get_page_images(doc, page_range, dpi=...)` to rasterize PDF pages via **pypdfium2 (`pypdfium2==4.30.0` pinned)**. Every page — born-digital OR scanned — is rasterized at `settings.IMAGE_DPI` (default 96) for detection/layout and `settings.IMAGE_DPI_HIGHRES` (default 192) for OCR and table-rec. This means **Surya does not branch on "is this page image-only?"** — both flow through the same rasterization step.

The implication is two-faceted:
- For scanned PDFs, this is fine — the page is already an image and you get an image.
- For born-digital PDFs with embedded text, the **text layer is still extracted and used by `surya_table` (default cell-text path) and by `surya_ocr`'s `original_text_good=True` flag**. The `FLATTEN_PDF: bool = True` setting (default on) merges PDF form fields into the page rendering.

### 5.2 DPI / resolution

| Setting | Default | Used for |
|---|---|---|
| `IMAGE_DPI` | 96 | Detection, layout, reading-order |
| `IMAGE_DPI_HIGHRES` | 192 | OCR, table-rec |

README troubleshooting (line 370): "Try increasing resolution of the image so the text is bigger. If the resolution is already very high, try decreasing it to no more than a `2048px` width."

So the practical ceiling is **2048px on the long edge**. Going higher does NOT help — open issue **#389** documents segfaults when feeding 600-DPI scans into `surya_ocr` on Apple Silicon (unresolved). The combination of `IMAGE_DPI_HIGHRES=192` and a 2048px cap means the effective rasterization is **safe up to ~10.6 inches at 192 DPI** = an A4 page (8.27 × 11.7 in) is comfortable; anything bigger needs downscaling.

**Recommendation for NRB scanned PDFs:**
- Rasterize at 192 DPI (Surya default). Do NOT push to 300 or 600 DPI — that triggers crashes and offers no quality gain.
- Pre-check page dimensions; if the rasterized image > 2048 px on the long edge, downscale to 2048 first.

### 5.3 Image preprocessing — does Surya do it or do we?

**Surya does almost none.** No deskew, no denoise, no binarization, no contrast normalization is documented or visible in `surya/input/`. The README explicitly delegates this to the user (line 371): "Preprocessing the image (binarizing, deskewing, etc) can help with very old/blurry images."

**Recommendation for NRB legacy scans:**
- Use OpenCV (already a Surya dep: `opencv-python-headless==4.11.0.86`) for deskew + adaptive threshold + denoise BEFORE handing to Surya.
- Specifically: `cv2.adaptiveThreshold` with `cv2.ADAPTIVE_THRESH_GAUSSIAN_C` works well on Devanagari scans where the diacritic strokes are faint.

### 5.4 Detection vs recognition separation

Surya keeps these as separate models for a reason: detection is script-agnostic (works on any language including Devanagari, per README §Limitations) but recognition is language-locked. You can therefore use Surya's detector for line bboxes on any document and route recognition through either Surya (for supported languages), Tesseract with `script=Devanagari`, or a different OCR model entirely. This is the cleanest fall-back pattern if Surya OCR has a Devanagari regression.

### 5.5 Confidence thresholds

Three tunable thresholds, all in 0-1 range (settings.py lines 61-65):

| Setting | Default | Effect |
|---|---|---|
| `DETECTOR_TEXT_THRESHOLD` | 0.6 | Above this is text |
| `DETECTOR_BLANK_THRESHOLD` | 0.35 | Below this is blank space (line breaks) |
| `DETECTOR_BOX_Y_EXPAND_MARGIN` | 0.05 | Vertical expansion of detected boxes |

Rule: `DETECTOR_TEXT_THRESHOLD > DETECTOR_BLANK_THRESHOLD`, both in [0, 1].

Per-character/word/line confidence is in the output as `confidence: float` (0-1). NaN is coerced to 0 (see `BaseChar.validate_confidence`). **Our "we didn't read this well" gate should be: any line with mean `chars.confidence < 0.75` → mark for human review.** **[GAP — Surya does not publish a calibrated threshold]** — needs to be empirically tuned on a labelled NRB sample.

A separate `ocr_error` model (`s3://ocr_error_detection/2025_02_18`, ~0.1B params) classifies whole-line OCR errors after recognition. We should wire this in as a confidence layer.

---

## 6. Devanagari numerals

The docs are **silent on Devanagari (०१२३४५६७८९) vs Arabic (0123456789) numerals**.

What we know:
- `recognition/languages.py` lists `hi`, `mr`, `ne`, `sa` — all Devanagari users.
- The recognition model uses UTF-8 / UTF-16 decoding (README line 574: "modified donut model (... UTF-16 decoding ...)") — so it can in principle output both digit ranges.
- Issue **#475** (Hindi OCR returns null) is open at v0.17.1, suggesting Devanagari pipelines have regressions.

**[GAP — must be tested]**:
- Confusable pairs `१` (1) vs `१९` (19), `०` (0) vs `०.` (0 with period).
- Whether the model normalizes Devanagari digits to Arabic digits or preserves the original script.
- Behaviour on mixed numerals within one row (NRB tables routinely write column headers in English/Arabic numerals and body values in Devanagari).

**Recommendation:**
- Treat Devanagari numerals as a postprocessing problem on our side.
- Build a normalizer in `src/lib/text/devanagari-digits.ts` that maps `०१२३४५६७८९` → `0123456789` and validates that every cell in a numeric column matches `/^[-\d.,]+$/` after normalization.
- Flag any cell that fails this regex as low-confidence and route to human review.

---

## 7. CLI tools shipped

From `pyproject.toml` `[tool.poetry.scripts]`:

```
surya_detect       → surya.scripts.run_detect:detect
surya_ocr          → surya.scripts.run_ocr:ocr
surya_layout       → surya.scripts.run_layout:layout
surya_gui          → surya.scripts.run_gui:main      (Streamlit playground)
surya_table        → surya.scripts.run_table:table
surya_latex_ocr    → surya.scripts.run_latex_ocr:latex_ocr
texify_gui         → surya.scripts.run_texify_gui:main
```

Common args across all commands:
- `DATA_PATH` — image, PDF, or folder
- `--output_dir DIR`
- `--page_range "0,5-10,20"` (mixed singletons, ranges, comma lists)
- `--images` — also dump rendered debug images of the detected geometry

OCR-specific (`surya_ocr`):
- `--task_name {ocr_with_boxes, ocr_without_boxes, block_without_boxes}`
  - `ocr_with_boxes` (default): text + bboxes; recommended.
  - `ocr_without_boxes`: trade bboxes for accuracy; **try this if `ocr_with_boxes` gives bad results.**
  - `block_without_boxes`: for paragraph/equation blocks; better at preserving structure inside a block.
- `--disable_math` — suppress math detection (recommended for pure-prose Devanagari to avoid spurious `<math>` tags; README mentions math-tag false positives v0.16.0 release-noted as fixed but issue #410 shows lingering hallucinated content).

Table-specific (`surya_table`):
- `--detect_boxes` — OCR cell text via the model (REQUIRED for scanned/image-only PDFs).
- `--skip_table_detection` — input is already cropped to a table.

**Environment-variable knobs** (override any setting):

| Env var | Default | Purpose |
|---|---|---|
| `TORCH_DEVICE` | auto | Override device (`cpu`, `cuda`, `mps`, `xla`) |
| `IMAGE_DPI` | 96 | Detection/layout rasterization |
| `IMAGE_DPI_HIGHRES` | 192 | OCR/table-rec rasterization |
| `DETECTOR_BATCH_SIZE` | 2 CPU / 32 GPU | Detector batching |
| `RECOGNITION_BATCH_SIZE` | 8 CPU / 256 GPU | Recognition batching |
| `LAYOUT_BATCH_SIZE` | 4 CPU / 32 GPU | Layout batching |
| `TABLE_REC_BATCH_SIZE` | 8 CPU / 64 GPU | Table-rec batching |
| `TABLE_REC_MAX_BOXES` | 150 | Cell-count ceiling per table |
| `DETECTOR_TEXT_THRESHOLD` | 0.6 | Text-vs-blank threshold |
| `DETECTOR_BLANK_THRESHOLD` | 0.35 | Blank-space threshold |
| `DETECTOR_IMAGE_CHUNK_HEIGHT` | 1400 | Slicing tall images vertically |
| `COMPILE_DETECTOR` / `COMPILE_LAYOUT` / `COMPILE_TABLE_REC` / `COMPILE_FOUNDATION` / `COMPILE_OCR_ERROR` / `COMPILE_ALL` | False | `torch.compile()` (3-11% speedup on A10) |
| `FOUNDATION_MODEL_QUANTIZE` | False | Quantize foundation model |
| `MODEL_CACHE_DIR` | `<platformdir>/datalab/models` | Where to cache weights |
| `S3_BASE_URL` | `https://models.datalab.to` | Origin for weight downloads |
| `PARALLEL_DOWNLOAD_WORKERS` | 10 | Concurrent weight-shard downloads |
| `TESSDATA_PREFIX` | unset | Only for benchmarks |
| `DISABLE_TQDM` | False | Quiet progress bars |

Settings file: `surya/settings.py`. Local override file: `local.env` (auto-loaded via `python-dotenv.find_dotenv`).

---

## 8. Python API

The shape is consistent across all predictors: instantiate once, call as a function with a `List[PIL.Image]`.

### 8.1 OCR

```python
from PIL import Image
from surya.foundation import FoundationPredictor
from surya.recognition import RecognitionPredictor
from surya.detection import DetectionPredictor

image = Image.open(IMAGE_PATH)
foundation_predictor = FoundationPredictor()
recognition_predictor = RecognitionPredictor(foundation_predictor)
detection_predictor = DetectionPredictor()

predictions = recognition_predictor([image], det_predictor=detection_predictor)
# predictions: List[OCRResult]  -- one per input image
```

If you skip `det_predictor`, recognition assumes the input is already cropped to a single line.

### 8.2 Detection

```python
from PIL import Image
from surya.detection import DetectionPredictor

det_predictor = DetectionPredictor()
predictions = det_predictor([image])
# predictions: list of dicts -- see schema in §3.2
```

### 8.3 Layout

```python
from surya.foundation import FoundationPredictor
from surya.layout import LayoutPredictor
from surya.settings import settings

layout_predictor = LayoutPredictor(
    FoundationPredictor(checkpoint=settings.LAYOUT_MODEL_CHECKPOINT)
)
layout_predictions = layout_predictor([image])
```

Note: layout uses the *same* foundation architecture as recognition but a different checkpoint.

### 8.4 Table recognition

```python
from surya.table_rec import TableRecPredictor

table_rec_predictor = TableRecPredictor()
table_predictions = table_rec_predictor([image])
# table_predictions: List[TableResult]  -- see §3.4
```

`TableRecPredictor.__call__` accepts `(images, batch_size=None)`.

### 8.5 LaTeX OCR (Texify)

```python
from surya.texify import TexifyPredictor
predictor = TexifyPredictor()
predictor([image])
```

Expects pre-cropped equation images.

### 8.6 Inputs

- Always `List[PIL.Image.Image]` (RGB). Not bytes, not file paths, not numpy arrays.
- For PDFs use `surya.input.load.load_pdf(path, page_range=..., dpi=settings.IMAGE_DPI)` which returns a list of `PIL.Image`s via pypdfium2.
- The README is silent on max image size; combined with the 2048px-width troubleshooting tip (§5.2), treat 2048px on the long edge as the operational ceiling.

---

## 9. Models, weights, footprint

Surya pulls model checkpoints from `https://models.datalab.to/` on first run; they cache to `MODEL_CACHE_DIR` (platform default: `~/Library/Caches/datalab/models` on macOS, `%LOCALAPPDATA%\datalab\models` on Windows, `~/.cache/datalab/models` on Linux).

Per `settings.py` and the HuggingFace mirror at `huggingface.co/datalab-to`:

| Component | Checkpoint (S3) | HF mirror | Size |
|---|---|---|---|
| Foundation (used by recognition + layout) | `s3://text_recognition/2025_09_23` | (in `surya-alpha` 0.7B) | ~0.6-0.7B params |
| Recognition (same checkpoint as foundation since v0.16) | `s3://text_recognition/2025_09_23` | — | shared |
| Detection | `s3://text_detection/2025_05_07` | `datalab-to/line_detector0` (38M params) | ~150 MB |
| Layout | `s3://layout/2025_09_23` | `datalab-to/surya_layout` (0.1B) | ~400 MB |
| Table recognition | `s3://table_recognition/2025_02_18` | `datalab-to/surya_tablerec` (0.1B) | ~400 MB |
| Texify | (loaded by `TexifyPredictor`) | `datalab-to/texify` (0.2B) | ~800 MB |
| OCR error detection | `s3://ocr_error_detection/2025_02_18` | `datalab-to/ocr_error_detection` (0.1B) | ~400 MB |

**Memory per batch item** (README "Performance tips" blocks):
- Detector: 440 MB VRAM/item; default GPU batch 36 (~16 GB)
- Recognition: 40 MB VRAM/item; default GPU batch 512 (~20 GB)
- Layout: 220 MB VRAM/item; default GPU batch 32 (~7 GB)
- Table-rec: 150 MB VRAM/item; default GPU batch 64 (~10 GB)

Total VRAM if you run everything in sequence with defaults: ~50 GB → realistically a single A6000 (48GB) is the README's reference machine. On a 12 GB GPU you must downsize batches.

**CPU footprint:** the README does not state RAM, but with default CPU batches (2-8) and float32, expect 6-12 GB RAM for OCR+detection+layout sequentially.

**Pre-caching for CI:** set `MODEL_CACHE_DIR` to a CI-mounted volume, run a single `surya_detect` + `surya_ocr` + `surya_layout` + `surya_table` against a 1-page sample on cache miss, then snapshot the cache directory. Approx 2 GB on disk for the full set. The downloader is parallelized at `PARALLEL_DOWNLOAD_WORKERS=10`.

The foundation model uses `bfloat16` on XLA, `float16` on CUDA/MPS, and `float32` on CPU (`MODEL_DTYPE` computed field). FP16 is fine on most GPUs; on a card without FP16 acceleration you'll see CPU-like speeds.

---

## 10. Dependencies

From `pyproject.toml`:

**Core (production):**
```
python    >=3.10, <4
transformers   >=4.56.1
torch          ^2.7.0
pydantic       ^2.5.3
pydantic-settings ^2.1.0
python-dotenv  ^1.0.0
pillow         ^10.2.0
pypdfium2      ==4.30.0   (pinned exactly)
filetype       ^1.2.0
click          ^8.1.8
platformdirs   ^4.3.6
opencv-python-headless ==4.11.0.86   (pinned exactly)
einops         ^0.8.1
pre-commit     ^4.2.0
```

**Dev (only for benchmarking + finetuning):**
`jupyter, pytesseract, pymupdf, datasets, rapidfuzz, streamlit, pytest, pdftext, tabulate`

**Optional XLA group:**
`torch-xla ^2.4.1` for TPU.

**Conflicts with our planned Python stack** (`pandas`, `pdfplumber`, `httpx`, `python-dateutil`, `pytest`, `ruff`, `mypy`):
- No outright conflicts. All co-installable.
- **`pypdfium2==4.30.0` is hard-pinned.** If we want a newer pypdfium2 elsewhere we cannot. (Currently we have no other pypdfium2 dependency, so fine.)
- **`opencv-python-headless==4.11.0.86` hard-pinned.** Same caveat.
- **`pillow ^10.2.0`** — open issue **#459** requests Pillow 11 support; not yet merged. If something else in our stack needs Pillow 11, we have a conflict.
- **`transformers >=4.56.1`** — open issue **#492** flags incompatibility with transformers 5.x (`find_pruneable_heads_and_indices` removed); transformers 4.x is fine.
- Surya inherits PyTorch 2.7+, so we will pull ~2 GB of torch/CUDA wheels into our Python venv. Worth considering whether the Surya step should run in a **separate venv** (or a separate worker container) so the rest of our pipeline stays lightweight.

**Recommendation:** put Surya into its own venv at `python/.venv-surya` and invoke via subprocess from the main pipeline. Mirrors what our PARSING_WORKFLOW.md already implies for heavyweight extractors.

---

## 11. Determinism

Surya is neural; the docs **never claim reproducibility**.

What we can infer from the code:
- No explicit `torch.manual_seed(...)` call in the predictors I read (`table_rec/__init__.py`, `recognition/schema.py`, `settings.py`).
- Decoding is argmax over logits (`torch.argmax`, see `table_rec/__init__.py` line 85), so absent floating-point non-determinism, the same input on the same hardware in the same dtype should produce identical output.
- However, GPU kernels (especially attention on CUDA) are non-deterministic by default unless `torch.use_deterministic_algorithms(True)` is set; Surya does not set this.
- Mixed-precision (`float16` on CUDA, `bfloat16` on XLA, `float32` on CPU) means cross-device output is NOT bit-identical.

**Practical determinism guarantees:**
- Same machine + same Python + same torch + same Surya version + same input + CPU device → identical output across runs (high confidence, untested).
- Same machine + GPU → near-identical but rare flapping is possible.
- Cross-machine → not guaranteed.

**For ADR-0003 compliance ("reproducibility required for production parsers"):**
- The ADR's binding constraint is that *parsing* be deterministic. Surya here is a *line-extraction step*, with deterministic Python parsers downstream.
- Mitigation: pin `surya-ocr==0.17.1`, pin `torch`, pin `transformers`, pin the model cache directory (and cache file hashes), record the device used and the seed in our `extraction_runs` table. If a re-run produces different output, mark it as a model-drift event and re-validate.
- **[GAP]** No `--seed` CLI flag exists. We'd need a small `surya_ocr_pinned.py` wrapper that calls `torch.use_deterministic_algorithms(True)` and `torch.manual_seed(0)` before each predictor call.

---

## 12. Versioning / pinning

| Version | Date | Notable change |
|---|---|---|
| v0.17.1 | 2026-01-30 | LaTeX control-character escaping fix |
| v0.17.0 | 2025-09-23 | **NEW LAYOUT MODEL trained from scratch; unified tokenizer.** Reading order folded into layout. |
| v0.16.7 | 2025-09-08 | Flash-attention import reorg |
| v0.16.6 | 2025-09-08 | Configurable attention method |
| v0.16.5 | 2025-09-08 | Foundation predictor init tweaks |
| v0.16.4 | 2025-09-08 | **20-30% perf gain; SDPA attention masking fix.** |
| v0.16.3 | 2025-09-05 | Checkpoint reversion |
| v0.16.2 | 2025-09-05 | **Multi-token decoding** (faster, better math + table handling) |
| v0.16.1 | 2025-09-02 | Hotfix for transformers 4.56.0 |
| v0.16.0 | 2025-08-29 | **NEW OCR MODEL — better, smaller vocab, improved vision encoder.** Removed user-facing `langs=` argument. |

Recent breaking changes (last 12 months):
- **v0.15.0 → v0.16.0**: changed character-/word-level bbox output format (issue #450 — bboxes scaled incorrectly in v0.16.x compared to v0.14.7). Not yet fully resolved at v0.17.1.
- **v0.16.0**: dropped per-call language hint (issue #388 — no replacement documented).
- **v0.17.0**: layout output schema changed (15 labels, `top_k` field added).

**Known-good versions for Devanagari work:**
- The pre-v0.16 model (v0.14.7) reportedly had more accurate Devanagari behaviour but worse general performance. **[GAP]** — no published per-language regression test; this is anecdotal from issues #475 and #388.
- **Pin v0.17.1 as our baseline** (the latest stable), and have a documented fallback to `surya-ocr==0.14.7` for any Devanagari-heavy ingestion that fails post-validation.

---

## 13. Known limitations / gotchas

Explicit from README §Limitations (line 360):

> - This is specialized for document OCR. It will likely not work on photos or other images.
> - It is for printed text, not handwriting (though it may work on some handwriting).
> - The text detection model has trained itself to ignore advertisements.
> - You can find language support for OCR in `surya/recognition/languages.py`. Text detection, layout analysis, and reading order will work with any language.

From open issues (April–December 2025/2026):

| # | Title | Why it matters for us |
|---|---|---|
| **#475** | OCR on Hindi word images returns null text (open, unassigned, no fix) | **Direct blocker.** Confirmed Devanagari regression in v0.17.1. |
| **#388** | "How do I set the language of the OCR from version 0.14.1?" (open) | No way to bias toward Devanagari since v0.16. We have to live with auto-detect. |
| **#450** | Incorrect word-level bboxes in ≥v0.15.0 (open, "bug: output") | Affects our cell-text alignment. Use line-level bboxes, not word-level, when accuracy matters. |
| **#389** | `surya_ocr` segfaults on 600 DPI image/PDF (closed without fix) | Cap rasterization at 192 DPI / 2048 px width. |
| **#410** | Hallucinated text + repeated output in large vertical gaps (closed without fix) | Wide whitespace gaps in NRB tables can trigger spurious text. Use layout-first cropping. |
| **#372** | Vertically merged cells shouldn't be merged (closed without fix) | Always also log `unmerged_cells` for diff. |
| **#496** | Multi-dot filenames merge into same result key | Don't put dots in NRB filenames passed to Surya. |
| **#492** | Incompatible with transformers 5.x | Pin transformers <5.0. |
| **#467** | HTML tags appearing in OCR output (closed) | Recognition model can emit `<math>`, possibly other tags. Strip in postproc. Use `--disable_math` when no math is expected. |
| **#459** | Pillow 11 not supported | Stay on Pillow 10.x. |

**Likely root cause of "prior chat got extraction quality bad":**
1. They ran the default `surya_table` on scanned NRB PDFs without `--detect_boxes`, so cell text was pulled from an empty PDF text layer and came back blank.
2. They expected OCR to take a language hint (pre-v0.16 API), didn't provide one, hit the Devanagari regression in #475.
3. They hit the 150-cell ceiling on a long CMEFs table and got silent truncation.
4. They did not preprocess scans (no deskew/denoise), and Devanagari diacritics suffered.

---

## 14. Citations

Every URL I read for this document:

- **`https://github.com/datalab-to/surya`** — canonical repository, current master branch. Confirms the repo migrated from `VikParuchuri/surya` to `datalab-to/surya`.
- **`https://raw.githubusercontent.com/datalab-to/surya/master/README.md`** — full README (619 lines); primary source for capabilities, CLI flags, JSON output schemas, performance numbers, benchmarks, troubleshooting, limitations.
- **`https://raw.githubusercontent.com/datalab-to/surya/master/surya/settings.py`** — all env-var-overridable defaults (210 lines).
- **`https://raw.githubusercontent.com/datalab-to/surya/master/surya/recognition/languages.py`** — full supported-language dict (97 entries; `ne`, `hi`, `mr`, `sa` confirmed).
- **`https://raw.githubusercontent.com/datalab-to/surya/master/surya/recognition/schema.py`** — pydantic OCR output dataclasses (`OCRResult`, `TextLine`, `TextChar`, `TextWord`).
- **`https://raw.githubusercontent.com/datalab-to/surya/master/surya/table_rec/schema.py`** — pydantic table output dataclasses (`TableResult`, `TableCell`, `TableRow`, `TableCol` including `unmerged_cells`, `merge_up`, `merge_down`, `colspan`, `rowspan`, `within_row_id`).
- **`https://raw.githubusercontent.com/datalab-to/surya/master/surya/table_rec/__init__.py`** — `TableRecPredictor` source (387 lines); confirms `TABLE_REC_MAX_BOXES=150` ceiling and decoder structure.
- **`https://github.com/datalab-to/surya/blob/master/surya/input/load.py`** — PDF loading via pypdfium2 at `IMAGE_DPI`.
- **`https://github.com/datalab-to/surya/tree/master/surya`** — package directory listing.
- **`https://github.com/datalab-to/surya/tree/master/surya/table_rec`** — table_rec directory listing.
- **`https://github.com/datalab-to/surya/releases`** — release history; last 10 releases with dates and notes.
- **`https://raw.githubusercontent.com/datalab-to/surya/master/pyproject.toml`** (via WebFetch) — dependency pins, console-entrypoint definitions, Python version pin.
- **`https://pypi.org/project/surya-ocr/`** — v0.17.1 latest, Python 3.10–3.14, GPLv3+.
- **`https://documentation.datalab.to/`** — the *commercial* datalab docs; primarily API endpoints (`/convert`, `/extract-structured-data`, etc.) — not OSS documentation. OSS users read the GitHub README.
- **`https://documentation.datalab.to/llms.txt`** — LLM-oriented commercial-API index; still no OSS-specific content.
- **`https://huggingface.co/datalab-to`** — model org index; 10+ models including `surya-alpha`, `surya_tablerec`, `surya_layout`, `ocr_error_detection`, `texify`, `line_detector0`, `chandra`, `chandra-ocr-2`.
- **`https://huggingface.co/datalab-to/text_recognition`** — returned HTTP 401 (model is gated or private). Could not read the model card directly.
- **GitHub issues read:**
  - **#475** Hindi OCR returns null (open) — `https://github.com/datalab-to/surya/issues/475`
  - **#388** How to set OCR language post-0.14.1 (open) — `https://github.com/datalab-to/surya/issues/388`
  - **#450** Word-bbox regression in ≥0.15.0 (open) — `https://github.com/datalab-to/surya/issues/450`
  - **#389** Segfault on 600 DPI (closed without fix) — `https://github.com/datalab-to/surya/issues/389`
  - **#410** Hallucinated/repeated text (closed) — `https://github.com/datalab-to/surya/issues/410`
  - **#372** False vertical cell merging (closed without fix) — `https://github.com/datalab-to/surya/issues/372`
  - **#492, #486, #459, #496, #443, #347, #332, #331, #241** — table-rec / dependency / output bugs, summarized in §13.
- **`https://github.com/datalab-to/surya/issues?q=is%3Aissue+devanagari+OR+nepali+OR+hindi`** — search index for Devanagari-script issues.
- **`https://github.com/datalab-to/surya/issues?q=is%3Aissue+scanned+OR+dpi+OR+resolution`** — search index for scan/DPI issues.

**Things I could NOT verify and we must test ourselves:**
- Per-language OCR accuracy on Devanagari (README's full-language results are embedded in images: `static/images/rec_acc_table.png`, `gcloud_full_langs.png`).
- The exact behaviour of the v0.17.1 OCR model on Devanagari (issue #475 unresolved).
- Whether the model normalizes Devanagari digits to Arabic or preserves the original script.
- The HF model card for `datalab-to/text_recognition` (401 response — likely gated).
- Multi-page table continuation behaviour.
- Whether `TABLE_REC_MAX_BOXES` can safely be raised to 500+ without OOM or quality loss.
- True bit-level determinism guarantees across runs on the same hardware (no explicit `manual_seed` in code path).

---

## Appendix A — Recommended invocation for Nepal Ledger NRB CMEFs ingestion

```bash
# Env (write to .env or set inline)
export TORCH_DEVICE=cpu                       # CI; bump to cuda when we have a GPU runner
export IMAGE_DPI=96                           # detection/layout
export IMAGE_DPI_HIGHRES=192                  # OCR/table — DO NOT raise to 300+
export DETECTOR_TEXT_THRESHOLD=0.6
export DETECTOR_BLANK_THRESHOLD=0.35
export TABLE_REC_MAX_BOXES=400                # raise from 150 for large NRB tables; verify empirically
export DISABLE_TQDM=true                      # CI cleanliness
export MODEL_CACHE_DIR=./.cache/surya-models  # cache to repo-local dir; commit hash, not weights

# Pipeline
surya_layout  data/raw/nrb/cmef.pdf --output_dir data/staging/layout
# (Python step) crop table regions from layout output

surya_table   data/staging/cropped/*.png \
              --detect_boxes \
              --skip_table_detection \
              --output_dir data/staging/tables

surya_ocr     data/staging/cropped_cells/*.png \
              --task_name ocr_with_boxes \
              --disable_math \
              --output_dir data/staging/ocr
```

Followed by deterministic Python postprocessing (Devanagari digit normalization → cell text alignment → row stitching → schema validation → write to `approved/`).

## Appendix B — Surya version + dep pinning for our pyproject

```toml
# pyproject.toml (Surya extraction venv only — not the main app)
[project]
requires-python = ">=3.11, <4"

dependencies = [
  "surya-ocr==0.17.1",
  "pillow>=10.2,<11",                 # locked by Surya
  "opencv-python-headless==4.11.0.86",# locked by Surya
  "pypdfium2==4.30.0",                # locked by Surya
  "transformers>=4.56.1,<5.0",        # locked by Surya
  "torch>=2.7,<3.0",                  # locked by Surya
]
```
