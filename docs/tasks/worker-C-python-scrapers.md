# Worker C — Python Scraper Scaffolding + NRB-NCPI parser shell

**Spawn type:** `general-purpose`
**Plan mode:** required (touches >3 files)
**Diff cap:** 300 lines

---

## Goal

Stand up the Python side of the data pipeline. Per ADR-0003, production parsing is **deterministic Python only**, never API calls. This worker scaffolds the `scrapers/` workspace and writes the first parser shell against the real NCPI CSV that's already in the repo.

Done = `scrapers/` has a working `pyproject.toml` (uv or pip), shared `_common/` helpers, and a `scrapers/nrb-ncpi/parser.py` that reads the existing CSV at `NRB Current/CMEFs_Table_Nine-Months_2082.83(2(B).csv` and emits structured rows matching the `staging_indicator_values` shape. Python tests pass via `pytest`.

## Why

Day 11–28 milestone — the data-provenance core. Schema and the staging table contract are in (PR #3). What's missing is the parser that puts rows there. ADR-0003 mandates deterministic Python, so this lives in `scrapers/`, separate from the TypeScript runtime, called from the future ingestion CLI / GitHub Action cron.

## Scope Fence (files this worker MAY touch)

Create:
- `scrapers/pyproject.toml` — Python 3.12, deps: `pandas`, `pdfplumber`, `httpx`, `python-dateutil`, plus dev deps `pytest`, `pytest-asyncio` if needed, `ruff`, `mypy`
- `scrapers/README.md` — short ops doc (how to install, how to run a parser, the contract)
- `scrapers/_common/__init__.py`
- `scrapers/_common/types.py` — `StagingRowDraft`, `ParserResult`, `ParserError`, `ParserStatus` enums matching the TS schemas (mirror exactly)
- `scrapers/_common/hashing.py` — `sha256_of_file(path) -> str`
- `scrapers/_common/periods.py` — Python mirror of the canonical period vocabulary (Shrawan…Ashadh, FY label parsing). DO NOT re-invent BS↔AD math — for Year 1 the parser receives AD dates from the orchestrator OR uses naive "mid-month" approximations that the validator will refine. State this clearly in a comment.
- `scrapers/_common/parser_contract.py` — abstract base / protocol for the `parse()` function, mirroring `docs/DATA_PIPELINE.md` §"Parser Contract"
- `scrapers/nrb-ncpi/__init__.py`
- `scrapers/nrb-ncpi/parser.py` — implements `parse(source_document_path, source_document_id) -> ParserResult` against the existing CSV
- `scrapers/nrb-ncpi/tests/__init__.py`
- `scrapers/nrb-ncpi/tests/test_parser.py` — pytest against the real CSV file as a fixture (path: `NRB Current/CMEFs_Table_Nine-Months_2082.83(2(B).csv` — read-only)
- `scrapers/nrb-ncpi/fixtures/.gitkeep` — placeholder for sample/parametric fixtures
- `scrapers/.python-version` — `3.12`

Optional but encouraged:
- `scrapers/_common/registry.py` — tiny dataclass mirror of a `source_registry` row so the parser can declare its `source_id` self-referentially

**Out of scope (must NOT touch):**
- Any TypeScript file (`src/**`, `.github/**`, root configs)
- `package.json` / `pnpm-lock.yaml`
- `.gitignore` (Mother updates this if needed — but the existing `source-data/` ignore covers the parser's runtime outputs)
- Real network calls (parsers never call the network — they operate on already-downloaded files)
- Drizzle migrations or schema

## Context to Read First (in order)

1. `docs/decisions/0003-ai-assisted-parsing-policy.md` — the policy in one page.
2. `docs/PARSING_WORKFLOW.md` — Claude CLI as dev assistant, deterministic Python production.
3. `docs/DATA_PIPELINE.md` §"Parser Contract" + §"Confidence Grade Assignment" — the exact `parse()` shape.
4. `docs/SOURCE_REGISTRY.md` §"Tier 1" — `nrb-ncpi-table` is one of two starter sources.
5. `docs/CALENDAR_AND_PERIODS.md` — what reporting-period fields each row must carry.
6. `NRB Current/CMEFs_Table_Nine-Months_2082.83(2(B).csv` — the actual data file. Open it. Understand its shape. Header rows, geographies (rural/urban/overall), 23 NCPI subcategories.
7. `src/lib/db/schema/indicator-values.ts` (in repo, PR #3) — the TS shape your `StagingRowDraft` mirrors.

## Parser Contract (target shape)

```python
# scrapers/_common/types.py
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

ParserStatus = Literal['success', 'partial', 'failure']
ConfidenceGrade = Literal['A', 'B', 'C']
ReportingPeriodType = Literal['monthly', 'quarterly', 'annual', 'nine_months_cumulative', 'year_to_date', 'daily', 'seasonal']

@dataclass(frozen=True)
class StagingRowDraft:
    indicator_slug_raw: str
    value: float
    unit: str
    reporting_period_type: ReportingPeriodType
    reporting_period_bs: str         # e.g. "FY 2082/83 9M"
    reporting_period_ad_start: datetime  # tz-aware UTC
    reporting_period_ad_end: datetime    # inclusive of last day, tz-aware UTC
    publication_date_ad: datetime
    publication_date_bs: str
    fiscal_year_bs: str              # "2082/83"
    fiscal_year_ad_label: str        # "2025/26"
    confidence_grade_proposed: ConfidenceGrade
    parser_notes: str | None = None

@dataclass(frozen=True)
class ParserError:
    error_class: str                 # match enum from src/lib/db/schema/enums.ts
    error_detail: str
    source_excerpt: str | None = None

@dataclass(frozen=True)
class ParserResult:
    status: ParserStatus
    parser_version: str              # semver
    staging_rows: list[StagingRowDraft]
    errors: list[ParserError]
```

```python
# scrapers/nrb-ncpi/parser.py
PARSER_VERSION = "0.1.0"
SOURCE_ID = "nrb-ncpi-table"

def parse(source_document_path: str, source_document_id: str) -> ParserResult:
    """Read the NCPI CSV and emit one StagingRowDraft per (subcategory × geography)."""
    ...
```

## Required Test Cases

In `scrapers/nrb-ncpi/tests/test_parser.py`, against the real CSV:

- `parse()` returns `status == 'success'`
- Exactly 23 NCPI subcategories × 3 geographies (urban / rural / overall) = 69 rows (adjust if the CSV actually has different geographies — read it first)
- Every row has all required fields populated (no Nones except `parser_notes`)
- `reporting_period_type == 'nine_months_cumulative'` and `fiscal_year_bs == '2082/83'`
- AD start/end span ≈ Shrawan 2082 → Chait 2082 (mid-July 2025 → mid-April 2026); allow ±2 days slack because the parser uses naive mid-month approximation, refinement happens at the validation step
- `confidence_grade_proposed == 'A'` (NCPI from NRB is A-tier per SOURCE_REGISTRY.md)
- Unit string is one of the canonical ones (`index_points`, `percent_yoy`, etc. — see what the CSV actually reports)
- `parser_version == '0.1.0'`

If the CSV has a row the parser doesn't recognize, it must return `status == 'partial'` with `errors[].error_class == 'ColumnMissing'` (or appropriate), NOT raise.

## Acceptance Criteria

- [ ] Files in scope only (`git diff --name-only main`)
- [ ] `cd scrapers && uv pip install -e .` (or `python -m pip install -e .`) succeeds
- [ ] `cd scrapers && pytest -q` — all tests pass
- [ ] `ruff check scrapers/` — clean (you write the ruff config inline in `pyproject.toml`)
- [ ] `mypy scrapers/` — clean (strict mode in pyproject)
- [ ] No real network calls in any test
- [ ] Diff under 300 lines
- [ ] Parser is idempotent — running it twice on the same input produces identical output
- [ ] `parser.py` declares `PARSER_VERSION` as a module constant; version bump = behavior change
- [ ] Type names match the TS enums exactly (case + spelling — `nine_months_cumulative` not `nine-months-cumulative`)

## What to Return

1. Summary of changes (≤10 bullets)
2. Acceptance-criteria checklist with checkmarks
3. `git diff --stat main` output
4. Any deviations from this brief and why (including any divergence between the CSV's actual shape and this brief's assumptions — flag this clearly)
5. Open questions
6. Conventional-commit suggestion (`feat(scrapers): nrb-ncpi parser shell + python toolchain`)
