"""UNDP HDR Composite Indices (Nepal) parser — deterministic Python.

Source id: ``hdr-composite``

Input format:
    The UNDP Human Development Report "Composite indices — complete time series"
    CSV, read **directly** (the ingest CLI downloads it and passes the path).
    It is a WIDE table: one row per country, ~1,112 columns of the form
    ``<metric>_<year>`` (e.g. ``hdi_2023``, ``le_1990``). Column 0 is ``iso3``.

    .. important::
        The file is **Latin-1 (cp1252)** encoded, not UTF-8 (country names like
        "Côte d'Ivoire"). Reading it as UTF-8 raises a decode error.

    The parser selects the ``iso3 == 'NPL'`` row and, for each configured metric
    prefix, emits one staging row per ``<prefix>_<year>`` column that holds a
    numeric value. Prefix matching is exact (``^<prefix>_(\\d{4})$``) so ``hdi``
    never captures ``hdi_f`` / ``hdi_rank`` / ``hdi_male`` columns.

Period dating:
    HDR years are calendar years. To keep ``hdr-*`` aligned with ``wdi-*`` /
    ``pip-*`` for the same year, the parser reuses the WDI convention: year "Y"
    → Nepal FY beginning Shrawan of BS year (Y + 57); AD Jul 15 Y – Jul 15 Y+1.

Publication date:
    The CSV carries no release timestamp, so the vintage is pinned here
    (``_PUBLICATION_DATE_AD`` = the HDR 2025 launch). Bump it when the source
    CSV vintage changes (the structure is version-pinned to HDR 2025).

Indicators (18):
    Slug prefix ``hdr-``. HDI-family composites are unitless indices in [0,1]
    (``index_0_1``); schooling/longevity are ``years``; GNI per capita is
    2021-PPP ``intl_dollar``; inequality losses and participation rates are
    ``percent`` (already 0–100 in the source). Confidence A.

ADR-0003: no LLM / AI calls. Deterministic file-in → dataclass-out.
"""

from __future__ import annotations

import csv
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from _common.periods import fiscal_year_ad_label, fiscal_year_label
from _common.types import (
    ParserError,
    ParserErrorClass,
    ParserResult,
    ParserStatus,
    StagingRowDraft,
)

PARSER_VERSION: Final[str] = "0.1.0"
SOURCE_ID: Final[str] = "hdr-composite"

# HDR year Y → Nepal FY starting Shrawan of BS year (Y + 57), matching wb_wdi.
_BS_AD_OFFSET: Final[int] = 57

# HDR 2025 report launch (data through 2023). Bump with the CSV vintage.
_PUBLICATION_DATE_AD: Final[datetime] = datetime(2025, 5, 6, tzinfo=UTC)

_ISO3_COLUMN: Final[str] = "iso3"
_NEPAL_ISO3: Final[str] = "NPL"
_MIN_YEAR: Final[int] = 1960
_MAX_YEAR: Final[int] = 2100

# metric prefix → (slug, unit). Emitted for every `<prefix>_<year>` numeric cell.
_INDICATOR_CONFIG: Final[dict[str, tuple[str, str]]] = {
    "hdi":       ("hdr-hdi",                                "index_0_1"),
    "hdi_f":     ("hdr-hdi-female",                         "index_0_1"),
    "hdi_m":     ("hdr-hdi-male",                           "index_0_1"),
    "ihdi":      ("hdr-ihdi",                               "index_0_1"),
    "gii":       ("hdr-gii",                                "index_0_1"),
    "gdi":       ("hdr-gdi",                                "index_0_1"),
    "phdi":      ("hdr-phdi",                               "index_0_1"),
    "le":        ("hdr-life-expectancy",                    "years"),
    "eys":       ("hdr-expected-years-schooling",           "years"),
    "mys":       ("hdr-mean-years-schooling",               "years"),
    "gnipc":     ("hdr-gni-per-capita-ppp",                 "intl_dollar"),
    "coef_ineq": ("hdr-coefficient-human-inequality",       "percent"),
    "loss":      ("hdr-ihdi-overall-loss",                  "percent"),
    "ineq_edu":  ("hdr-inequality-education",               "percent"),
    "ineq_inc":  ("hdr-inequality-income",                  "percent"),
    "ineq_le":   ("hdr-inequality-life-expectancy",         "percent"),
    "lfpr_f":    ("hdr-labour-force-participation-female",   "percent"),
    "lfpr_m":    ("hdr-labour-force-participation-male",     "percent"),
}


def _fail(error_class: ParserErrorClass, detail: str) -> ParserResult:
    return ParserResult(
        status="failure",
        parser_version=PARSER_VERSION,
        errors=[ParserError(error_class=error_class, error_detail=detail)],
    )


def _column_index(headers: list[str]) -> dict[str, tuple[str, int]]:
    """Map each `<prefix>_<year>` header to (prefix, year) for configured prefixes."""
    out: dict[str, tuple[str, int]] = {}
    for col in headers:
        m = re.match(r"^([a-z_]+)_(\d{4})$", col)
        if m is None:
            continue
        prefix, year_s = m.group(1), m.group(2)
        if prefix in _INDICATOR_CONFIG:
            out[col] = (prefix, int(year_s))
    return out


def _make_row(slug: str, unit: str, value: float, year: int) -> StagingRowDraft:
    bs_start = year + _BS_AD_OFFSET
    fy_bs = fiscal_year_label(bs_start)
    return StagingRowDraft(
        indicator_slug_raw=slug,
        value=value,
        unit=unit,
        reporting_period_type="annual",
        reporting_period_bs=fy_bs,
        reporting_period_ad_start=datetime(year, 7, 15, tzinfo=UTC),
        reporting_period_ad_end=datetime(year + 1, 7, 15, tzinfo=UTC),
        publication_date_ad=_PUBLICATION_DATE_AD,
        publication_date_bs=fy_bs,
        fiscal_year_bs=fy_bs,
        fiscal_year_ad_label=fiscal_year_ad_label(bs_start),
        confidence_grade_proposed="A",
        observation_type="actual",
        parser_notes=f"HDR composite CSV; column {slug.replace('hdr-', '')}_{year}",
    )


def parse(source_document_path: str, source_document_id: str) -> ParserResult:
    """Parse the HDR composite-indices CSV for Nepal; see module docstring."""
    _ = source_document_id  # contract parameter — unused by this parser

    path = Path(source_document_path)
    if not path.exists():
        return _fail("Other", f"source file not found: {path}")

    try:
        # HDR CSV is Latin-1; reading as UTF-8 raises on accented country names.
        text = path.read_text(encoding="latin-1")
    except OSError as exc:
        return _fail("EncodingError", f"csv read failed: {exc}")

    reader = csv.DictReader(text.splitlines())
    if reader.fieldnames is None or _ISO3_COLUMN not in reader.fieldnames:
        return _fail("ColumnMissing", f"missing '{_ISO3_COLUMN}' header column")

    col_map = _column_index(list(reader.fieldnames))
    if not col_map:
        return _fail("ColumnMissing", "no recognised <metric>_<year> columns for configured prefixes")

    nepal_row: dict[str, str] | None = None
    for record in reader:
        if (record.get(_ISO3_COLUMN) or "").strip().upper() == _NEPAL_ISO3:
            nepal_row = record
            break

    if nepal_row is None:
        return _fail("Other", f"no row with {_ISO3_COLUMN} == {_NEPAL_ISO3}")

    rows: list[StagingRowDraft] = []
    errors: list[ParserError] = []

    for col, (prefix, year) in col_map.items():
        if not (_MIN_YEAR <= year <= _MAX_YEAR):
            continue
        raw = (nepal_row.get(col) or "").strip()
        if raw == "" or raw.lower() in {"na", "n/a", ".."}:
            continue
        try:
            value = float(raw)
        except ValueError:
            errors.append(
                ParserError(
                    error_class="ValueUnparseable",
                    error_detail=f"{col}: value {raw!r} is not numeric",
                    source_excerpt=raw,
                )
            )
            continue
        slug, unit = _INDICATOR_CONFIG[prefix]
        rows.append(_make_row(slug, unit, value, year))

    if not rows:
        return _fail("Other", "no data rows produced for Nepal")

    rows.sort(key=lambda r: (r.indicator_slug_raw, r.fiscal_year_bs))
    status: ParserStatus = "partial" if errors else "success"
    return ParserResult(
        status=status,
        parser_version=PARSER_VERSION,
        staging_rows=rows,
        errors=errors,
    )


def _serialize_result(result: ParserResult) -> dict[str, Any]:
    """Serialize ``ParserResult`` to the JSON shape expected by ParserOutputSchema."""
    from dataclasses import asdict

    out_rows: list[dict[str, Any]] = []
    for row in result.staging_rows:
        d = asdict(row)
        for k in ("reporting_period_ad_start", "reporting_period_ad_end", "publication_date_ad"):
            v = d.get(k)
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        out_rows.append(d)
    return {
        "status": result.status,
        "parser_version": result.parser_version,
        "staging_rows": out_rows,
        "errors": [asdict(e) for e in result.errors],
    }


def _main() -> None:
    """CLI entry-point: ``parser.py <source_document_path> <source_document_id>``."""
    import json
    import sys

    if len(sys.argv) != 3:
        sys.stderr.write("usage: parser.py <source_document_path> <source_document_id>\n")
        sys.exit(2)

    result = parse(sys.argv[1], sys.argv[2])
    json.dump(_serialize_result(result), sys.stdout)


if __name__ == "__main__":
    _main()
