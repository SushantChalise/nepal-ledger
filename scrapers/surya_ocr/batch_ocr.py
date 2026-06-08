"""Overnight bulk Surya OCR runner — exhaustive extraction for a later AI pass.

Drains a PRIORITIZED manifest of corpus PDFs, OCR-ing each page to raw JSON on
disk. Designed to run unattended overnight on the idle GPU and survive Surya's
delicacy:

  * MODEL-WARM    — loads the Surya predictors ONCE per process (engine.py
                    singleton) and reuses them across all pages (a per-page
                    subprocess would pay ~20 s model-load each time).
  * CHECKPOINTED  — each page's output is a separate JSON; a page whose JSON
                    already exists is SKIPPED. So a kill/crash/restart resumes
                    for free, and the run is idempotent across nights.
  * ISOLATED      — every page is wrapped in try/except; one bad page writes a
                    ``.error`` marker and the run continues (never sinks). A
                    page that HARD-crashes the process (uncatchable CUDA fault)
                    leaves an ``.attempting`` marker; after a few crashes it is
                    skipped so the supervisor can never restart-loop forever.
  * SUPERVISED    — writes a heartbeat + append-only progress log the external
                    supervisor / Mother monitor reads to detect a stall/death.

This does NOT touch the database and does NOT reconcile anything — it is pure
extraction. Structuring/cleaning/reconciliation is the later AI pass's job
(ADR-0003: AI as a dev/QA assistant over already-extracted text).

Subcommands:
    python -m surya_ocr.batch_ocr manifest   # (re)build the prioritized queue
    python -m surya_ocr.batch_ocr run        # drain it (model-warm; resumable)
    python -m surya_ocr.batch_ocr status     # done/total/errors report (JSON)
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import io
import json
import os
import re
import sys
import traceback
from pathlib import Path
from typing import Any

import fitz  # pymupdf

from surya_ocr.engine import MODEL_NAME, MODEL_VERSION, ocr_image, warm_up

# ``fitz`` ships no py.typed marker → ``fitz.Document`` resolves to ``Any`` under
# mypy ``disallow_any_unimported``. Explicit alias for signatures (matches the
# pattern in parsers/intergovernmental.py).
FitzDocument = Any

# ── Paths ────────────────────────────────────────────────────────────────
# The repo root holds the (symlinked) data dirs. This module lives at
# scrapers/surya_ocr/batch_ocr.py → parents[2] == repo root.
REPO_ROOT: Path = Path(__file__).resolve().parents[2]
DATA_ROOTS: tuple[str, ...] = ("Financial Data", "NRB Current", "Stastical Information")
OUTPUT_ROOT: Path = Path(__file__).resolve().parent / "_ocr_output"
STATE_DIR: Path = OUTPUT_ROOT / "_state"
MANIFEST_PATH: Path = STATE_DIR / "manifest.json"
HEARTBEAT_PATH: Path = STATE_DIR / "heartbeat.json"
PROGRESS_LOG: Path = STATE_DIR / "progress.log"

# Render scale: fitz.Matrix(3,3) ≈ 216 DPI — the harness-validated quality for
# Devanagari recognition (task #50). Quality > speed: this is a multi-night job.
RENDER_SCALE: float = 3.0
_CUDA_CLEAR_EVERY: int = 25  # flush CUDA allocator cache every N pages (bound OOM)
_HEARTBEAT_EVERY: int = 1  # pages
# A page that HARD-crashes the process (CUDA fault / OOM that kills Python, not
# a catchable exception) leaves an ``.attempting`` marker. After this many such
# crashes we give up on that one page so the supervisor can never spin forever.
_MAX_HARDCRASH_ATTEMPTS: int = 3

# Classification thresholds (manifest builder).
_SCANNED_MAX_WORDS: float = 10.0  # avg words/page below this → no text layer
_INTERGOV_SPARSE_WORDS: float = 60.0  # intergovernmental sparse-scan cutoff
_DEV_MIN_RATIO: float = 0.25  # Devanagari char ratio above this → corrupted-NP


def _now_iso() -> str:
    return _dt.datetime.now(tz=_dt.UTC).isoformat(timespec="seconds")


def _safe_stem(path: Path) -> str:
    """A filesystem-safe, collision-resistant folder name for a source PDF."""
    ascii_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", path.stem).strip("_")[:48] or "doc"
    # DETERMINISTIC hash (NOT builtin hash() — that is per-process salted, which
    # would change out_dir every run and break resumable checkpointing).
    rel = str(path).replace("\\", "/")
    digest = hashlib.sha1(rel.encode("utf-8")).hexdigest()[:8]
    return f"{ascii_stem}_{digest}"


# ── Manifest (the prioritized queue) ─────────────────────────────────────
# Priority tiers — lower drains first. Value-ordered so a partial night still
# extracts the highest-value docs. P0 un-extractable · P1 SOE (yellowbook) · P2
# macro annex (Nepali economic survey) · P3 aid (whitebook) · P4 budget detail
# (redbook) · P5 other Devanagari-corrupted. Clean-Latin PDFs are EXCLUDED.
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
# dirname substring → (priority, tier label), checked after the P0/P2 special cases.
_DIR_TIER: tuple[tuple[str, int, str], ...] = (
    ("yellowbook", 1, "SOE financials (yellowbook)"),
    ("whitebook", 3, "foreign aid (whitebook)"),
    ("redbook", 4, "budget detail (redbook)"),
)


def _assign_tier(
    dirname: str, *, scanned: bool, avg_words: float, dev_ratio: float,
) -> tuple[int, str] | None:
    """Map a sampled PDF to (priority, tier), or None to EXCLUDE (clean Latin)."""
    if scanned or ("intergovernmental" in dirname and avg_words < _INTERGOV_SPARSE_WORDS):
        return (0, "scanned/un-extractable")
    if "economic_survey" in dirname and dev_ratio > _DEV_MIN_RATIO:
        return (2, "macro annex (Nepali economic survey)")
    for key, pri, tier in _DIR_TIER:
        if key in dirname:
            return (pri, tier)
    if dev_ratio > _DEV_MIN_RATIO:
        return (5, "other Devanagari")
    return None  # clean machine-readable Latin → AI pass reads the text layer


def _classify(path: Path) -> dict[str, Any] | None:
    """Open a PDF, sample its text layer, and assign a priority tier (or None)."""
    try:
        doc = fitz.open(str(path))
    except Exception:  # noqa: BLE001 — a corrupt file is simply skipped
        return None
    try:
        n = doc.page_count
        sample = list(range(min(2, n), min(n, 12)))
        words = sum(len(doc[i].get_text("words")) for i in sample)
        texts = [doc[i].get_text() for i in sample]
    finally:
        doc.close()
    denom = max(1, len(sample))
    avg_words = words / denom
    dev = sum(len(_DEVANAGARI.findall(t)) for t in texts)
    chars = max(1, sum(len(t) for t in texts))
    dev_ratio = dev / chars
    scanned = avg_words < _SCANNED_MAX_WORDS
    assigned = _assign_tier(str(path.parent).lower(), scanned=scanned,
                            avg_words=avg_words, dev_ratio=dev_ratio)
    if assigned is None:
        return None
    priority, tier = assigned
    return {
        "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "abs_path": str(path),
        "pages": n,
        "priority": priority,
        "tier": tier,
        "scanned": scanned,
        "avg_words": round(avg_words, 1),
        "dev_ratio": round(dev_ratio, 3),
        "out_dir": f"P{priority}__{_safe_stem(path)}",
    }


def build_manifest() -> list[dict[str, Any]]:
    pdfs: list[Path] = []
    for root in DATA_ROOTS:
        base = REPO_ROOT / root
        if base.exists():
            pdfs.extend(base.rglob("*.pdf"))
            pdfs.extend(base.rglob("*.PDF"))
    seen: set[str] = set()
    entries: list[dict[str, Any]] = []
    excluded = 0
    for p in sorted(set(pdfs)):
        key = str(p).lower()
        if key in seen:
            continue
        seen.add(key)
        entry = _classify(p)
        if entry is None:
            excluded += 1
            continue
        entries.append(entry)
    # priority asc, then fewer pages first (quick wins land sooner), then path.
    entries.sort(key=lambda e: (e["priority"], e["pages"], e["path"]))
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps({"built": _now_iso(), "excluded_clean": excluded, "entries": entries},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return entries


def _load_manifest() -> list[dict[str, Any]]:
    return list(json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["entries"])


# ── Heartbeat + progress ─────────────────────────────────────────────────

def _heartbeat(last_path: str, last_page: int, done_this_run: int, total_target: int) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    HEARTBEAT_PATH.write_text(
        json.dumps({
            "ts": _now_iso(), "pid": os.getpid(), "last_path": last_path,
            "last_page": last_page, "done_this_run": done_this_run,
            "total_target": total_target, "model": f"{MODEL_NAME} {MODEL_VERSION}",
        }, ensure_ascii=False),
        encoding="utf-8",
    )


def _log(line: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with PROGRESS_LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"{_now_iso()} {line}\n")


# ── Run (the drain loop) ─────────────────────────────────────────────────

def _page_out_path(entry: dict[str, Any], page: int) -> Path:
    return OUTPUT_ROOT / str(entry["out_dir"]) / f"page_{page:04d}.json"


def _already_done(entry: dict[str, Any], page: int) -> bool:
    p = _page_out_path(entry, page)
    if not p.exists() or p.stat().st_size == 0:
        return False
    try:
        json.loads(p.read_text(encoding="utf-8"))
        return True
    except Exception:  # noqa: BLE001 — a truncated/corrupt JSON is re-OCR'd
        return False


def _write_ocr_json(entry: dict[str, Any], doc: FitzDocument, page: int) -> int:
    """OCR a single page → write its JSON atomically. Returns the line count."""
    from PIL import Image  # noqa: PLC0415 — keep PIL out of the import-time path

    pix = doc[page].get_pixmap(matrix=fitz.Matrix(RENDER_SCALE, RENDER_SCALE))
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    lines = ocr_image(img)
    payload = {
        "path": entry["path"], "page": page, "n_pages": entry["pages"],
        "priority": entry["priority"], "tier": entry["tier"], "render_scale": RENDER_SCALE,
        "image_px": [pix.width, pix.height], "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION, "ocr_ts": _now_iso(),
        "text_lines": [
            {"text": ln.text, "confidence": round(ln.confidence, 4), "bbox": list(ln.bbox)}
            for ln in lines
        ],
    }
    out = _page_out_path(entry, page)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    tmp.replace(out)  # atomic — a crash mid-write never leaves a half JSON
    return len(lines)


def _process_one_page(entry: dict[str, Any], doc: FitzDocument, page: int) -> str:
    """Process one page with hard-crash + soft-error isolation. Returns status."""
    marker = _page_out_path(entry, page).with_suffix(".attempting")
    prior = 0
    if marker.exists():
        try:
            prior = int(marker.read_text(encoding="utf-8").strip() or "0")
        except Exception:  # noqa: BLE001
            prior = 0
    if prior >= _MAX_HARDCRASH_ATTEMPTS:
        err = _page_out_path(entry, page).with_suffix(".error")
        err.parent.mkdir(parents=True, exist_ok=True)
        err.write_text(
            f"{_now_iso()}\nSKIPPED after {prior} hard-crash attempts\n", encoding="utf-8",
        )
        marker.unlink(missing_ok=True)
        _log(f"SKIP-HARDCRASH {entry['path']}#{page} after {prior} attempts")
        return "skip"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(str(prior + 1), encoding="utf-8")  # survives a process kill
    try:
        n_lines = _write_ocr_json(entry, doc, page)
    except Exception as exc:  # noqa: BLE001 — catchable (soft) error: isolate the page
        marker.unlink(missing_ok=True)
        err = _page_out_path(entry, page).with_suffix(".error")
        err.parent.mkdir(parents=True, exist_ok=True)
        err.write_text(f"{_now_iso()}\n{exc}\n{traceback.format_exc()}", encoding="utf-8")
        _log(f"PAGE-ERROR {entry['path']}#{page}: {exc}")
        return "error"
    marker.unlink(missing_ok=True)  # success → clear
    _log(f"OK {entry['path']}#{page} lines={n_lines} P{entry['priority']}")
    return "ok"


def _maybe_clear_cuda(done: int) -> None:
    if done % _CUDA_CLEAR_EVERY != 0:
        return
    try:
        import torch  # noqa: PLC0415

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:  # noqa: BLE001
        pass


def run(max_pages: int | None = None) -> int:
    entries = _load_manifest()
    total_target = sum(e["pages"] for e in entries)
    _log(f"RUN start pid={os.getpid()} docs={len(entries)} target_pages={total_target}")
    warm_up()
    _log("models warm")
    done_this_run = 0
    for entry in entries:
        try:
            doc = fitz.open(entry["abs_path"])
        except Exception as exc:  # noqa: BLE001
            _log(f"ERROR open {entry['path']}: {exc}")
            continue
        try:
            for page in range(doc.page_count):
                if _already_done(entry, page):
                    continue
                status_ = _process_one_page(entry, doc, page)
                if status_ == "ok":
                    done_this_run += 1
                _heartbeat(entry["path"], page, done_this_run, total_target)
                _maybe_clear_cuda(done_this_run)
                if max_pages is not None and done_this_run >= max_pages:
                    _log(f"RUN hit max_pages={max_pages}; stopping")
                    return done_this_run
        finally:
            doc.close()
    _log(f"RUN complete done_this_run={done_this_run}")
    return done_this_run


# ── Status ───────────────────────────────────────────────────────────────

def status() -> dict[str, Any]:
    entries = _load_manifest()
    per_tier: dict[int, dict[str, int]] = {}
    total_pages = done_pages = err_pages = docs_done = 0
    for e in entries:
        done = sum(1 for p in range(e["pages"]) if _already_done(e, p))
        out_dir = OUTPUT_ROOT / str(e["out_dir"])
        errs = len(list(out_dir.glob("*.error"))) if out_dir.exists() else 0
        total_pages += e["pages"]
        done_pages += done
        err_pages += errs
        if done >= e["pages"]:
            docs_done += 1
        tier = per_tier.setdefault(e["priority"], {"docs": 0, "pages": 0, "done": 0})
        tier["docs"] += 1
        tier["pages"] += e["pages"]
        tier["done"] += done
    hb: dict[str, Any] = {}
    if HEARTBEAT_PATH.exists():
        try:
            hb = json.loads(HEARTBEAT_PATH.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            hb = {}
    return {
        "docs_total": len(entries), "docs_complete": docs_done,
        "pages_total": total_pages, "pages_done": done_pages, "pages_error": err_pages,
        "pct": round(100 * done_pages / max(1, total_pages), 1),
        "resolved_ge_total": (done_pages + err_pages) >= total_pages,
        "by_tier": {f"P{k}": v for k, v in sorted(per_tier.items())},
        "heartbeat": hb,
    }


def _main() -> None:
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    if isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Overnight bulk Surya OCR runner")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("manifest", help="(re)build the prioritized queue")
    runp = sub.add_parser("run", help="drain the queue (model-warm, resumable)")
    runp.add_argument("--max-pages", type=int, default=None, help="stop after N pages (smoke)")
    sub.add_parser("status", help="done/total/errors report (JSON)")
    args = ap.parse_args()

    if args.cmd == "manifest":
        entries = build_manifest()
        tiers: dict[int, list[int]] = {}
        for e in entries:
            agg = tiers.setdefault(e["priority"], [0, 0])
            agg[0] += 1
            agg[1] += e["pages"]
        print(f"manifest: {len(entries)} docs, {sum(e['pages'] for e in entries)} pages")
        for k in sorted(tiers):
            print(f"  P{k}: {tiers[k][0]} docs, {tiers[k][1]} pages")
    elif args.cmd == "run":
        try:
            print(f"done_this_run={run(max_pages=args.max_pages)}")
        except BaseException as exc:  # noqa: BLE001 — record the fatal before exit
            _log(f"FATAL run crashed: {exc!r}\n{traceback.format_exc()}")
            raise
    elif args.cmd == "status":
        print(json.dumps(status(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _main()
