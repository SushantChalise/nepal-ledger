# Overnight bulk Surya OCR — operator + AI-pass handoff

**What it is.** An unattended, prioritized, **resumable** Surya OCR sweep over every
OCR-worthy PDF in the corpus (scanned + font-corrupted Devanagari). It writes **raw
per-page JSON** (text + bbox + confidence) to disk for a **later AI pass** to clean,
structure, and reconcile. It does **not** touch the database and does **not** reconcile
anything — extraction only (ADR-0003: AI as a dev/QA assistant over extracted text).

**Why this shape.** Surya is delicate (a CUDA fault/OOM can kill the process). The design
survives that: the runner is **model-warm** (loads once), **checkpointed** (skip-if-exists
per page — a kill/restart resumes for free), **isolated** (one bad page → `.error`, never
sinks the run; a page that hard-crashes the process 3× is skipped), and **supervised**
(a detached PowerShell loop restarts the runner on crash until the queue drains).

## Components

| File                | Role                                                        |
| ------------------- | ----------------------------------------------------------- |
| `batch_ocr.py`      | runner — `manifest` / `run` / `status` subcommands          |
| `run_overnight.ps1` | supervisor — detached loop, restarts `run` until drained    |
| `engine.py`         | the one place that loads the Surya predictors (`ocr_image`) |
| `_ocr_output/`      | output tree (gitignored — large, regenerable)               |

## Priority queue (50 docs, ~13,297 pages — value-first so a partial night still wins)

- **P0** un-extractable / scanned (450p) — incl. the 402-page Yellow Book SOE review 2081, intergovernmental FY2077/78, scanned agreements.
- **P1** SOE financials — other yellowbooks (~1,247p).
- **P2** macro annex — Nepali economic surveys (~1,064p).
- **P3** foreign aid — whitebook Preeti (~942p).
- **P4** budget detail — redbooks (~9,553p) — **last** (huge, lower marginal value/page).
- **P5** other Devanagari (~41p).

Clean machine-readable Latin PDFs (FCGO English, English Economic Survey, agriculture
stats) are **excluded** — the AI pass reads their text layer directly.

## Operate

```powershell
$py = 'C:\Users\ACER\AppData\Local\Programs\Python\Python312\python.exe'
$scr = 'C:\Users\ACER\Projects\Economy\.claude\worktrees\loving-wing-7bdcb4\scrapers'
$env:PYTHONUTF8=1; $env:PYTHONPATH=$scr; Set-Location $scr

# progress (done / total / errors / per-tier)
& $py -m surya_ocr.batch_ocr status

# (RE)LAUNCH the supervisor if it ever dies (detached; resumes from checkpoints):
Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File', `
  "$scr\surya_ocr\run_overnight.ps1"

# rebuild the manifest only if the corpus changed (out_dirs are stable hashes):
& $py -m surya_ocr.batch_ocr manifest
```

Telemetry under `_ocr_output/_state/`: `supervisor.log` (lifecycle + per-restart
progress), `progress.log` (per-page OK/ERROR + FATAL traceback), `heartbeat.json`
(`{ts, pid, last_path, done_this_run, ...}`), `DONE` (written when fully drained).

**Health check:** the run is healthy iff `heartbeat.json.ts` advances over a few minutes
_and_ a supervisor PowerShell process is alive. If `heartbeat` is stale (>~10 min) and no
runner python is alive, relaunch the supervisor (command above) — it resumes losslessly.

## Output format (for the AI pass)

```
_ocr_output/P<tier>__<stem>_<sha8>/page_0000.json
```

Each page JSON:

```json
{ "path": "Financial Data/.../<file>.pdf", "page": 0, "n_pages": 402,
  "priority": 0, "tier": "scanned/un-extractable", "render_scale": 3.0,
  "image_px": [1785, 2526], "model_name": "surya-ocr", "model_version": "0.17.1",
  "ocr_ts": "…", "text_lines": [ {"text": "…", "confidence": 0.98, "bbox": [x0,y0,x1,y1]}, … ] }
```

`text_lines` are in reading order top-to-bottom; `bbox` is pixel space at `render_scale`
(÷scale → PDF points). Confidence is 0–1. A `.error` sibling marks a page OCR could not
extract; a `.attempting` marker (if present) means a page is mid-retry after a hard crash.

**AI-pass contract:** treat this as Tier-2 OCR (ADR-0021) — recovered, **not** audited.
Anything derived must reconcile to a printed total before promotion, carry
`confidence_grade` B/C + `extraction_method=surya-ocr`, and never be presented as primary
audited data. See `docs/DATA_AUDIT.md` §7.
