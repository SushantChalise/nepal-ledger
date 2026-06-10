"""MoF Red Book (annual budget) → budget-allocation dimensional facts.

Source: Ministry of Finance, **"Estimates of Expenditure" / व्यय अनुमानको विवरण
(रातो किताब — the *Red Book*)** — Nepal's annual federal budget: the
appropriation each ministry / budget head is PLANNED to spend in the coming
fiscal year, split recurrent vs capital. This is the "what the government plans
to spend" counterpart to FCGO's audited actuals. Source id ``mof-budget-redbook``
(already registered in ``seed-source-registry.ts``, status ``paused`` — Mother
flips it to ``active`` on first live ingest; see the FOR-MOTHER notes / source
profile).

In-repo corpus: ``Financial Data/mof_documents/redbook/`` (21 editions, BS 2059
through BS 2081/82).

STEP-0 PDF-acquisition assessment (ADR-0011 / ADR-0003 — recorded so the next
maintainer does not re-discover it; page numbers are 0-based ``pdfplumber``
indices). The corpus splits FOUR ways by text-layer encoding:

  1. CLEAN DEVANAGARI-UNICODE — the parseable target. Exactly ONE edition extracts
     to clean forward Unicode AND segments into a stable budget summary table:
     **"Red Book Central 2074-75"** (``Red Book Central
     2074-75_..._00lqgwe.pdf``, BS 2074/75). Its खण्ड-१ "संघीय संचित कोषबाट
     विनियोजन हुने व्यय अनुमानको सारांश" (Summary of appropriation from the
     Federal Consolidated Fund, PDF pages 25-30) is a clean per-ministry /
     per-budget-head allocation table. THIS PARSER TARGETS THAT TABLE.
  2. BROKEN-UNICODE / glyph-substitution — the BS 2069/70-2072/73 editions
     ("RB 20xx-xx", "व्यय अनुमानको विवरण 207x-7x") extract to Devanagari but with
     a DEFECTIVE embedded-font ToUnicode map: conjuncts reorder and glyphs swap
     (header "(रू. हजारमा)" comes out "(रू. हजायभा)" — र↔य, म↔भ transposed;
     "अनुमानको"→"अनमु ानको"). Digits survive but LABELS are corrupted and the
     columns do not segment (``extract_tables`` returns whole rows in one cell).
     Not deterministically parseable without reverse-engineering the font map —
     the OCR/transliteration ADR-0003 forbids. **Deferred.**
  3. CID-BROKEN — the recent editions (BS 2073/74, 2076, 2077, 2078/79, 2079/80,
     2080/81, 2081/82) carry ``(cid:N)`` glyphs with no usable ToUnicode. The
     "what the government plans to spend NOW" editions are unfortunately all in
     this bucket. **Deferred** (no OCR; ADR-0003).
  4. LEGACY PREETI — the oldest editions (BS 2059, 2060/61, 2061/62, 2062/63,
     2065, 2066/67, 2067/68) are a Preeti font byte-map (e.g. "cfly{s" = आर्थिक),
     not Unicode. Un-mapping it is reverse-engineering a font. **Deferred.**

So coverage is intentionally ONE fiscal year (BS 2074/75 / AD 2017/18). A
documented single-edition scope is the honest result: every other edition fails
encoding, and ADR-0003 prohibits OCR/transliteration to recover them. When MoF
re-publishes a clean-Unicode Red Book, this parser's table anchors should pick it
up unchanged; if not, it emits a typed diagnostic (never a fabricated number).

Why text-line regex, not ``extract_tables`` (ADR-0003 determinism): the summary
table's ``page.extract_text()`` is clean and stably ordered — each budget-head
row is one line ``<code> <name> <8 numbers>`` — whereas ``page.extract_tables()``
mis-merges the चालु/पूँजीगत sub-rows and shifts columns. We anchor on the line
geometry (exactly like ``fcgo_consolidated`` anchors on prose), which is robust.

The 8 trailing numbers per budget-head row are, in source order:
  [0] FY-2 actual (यथार्थ खर्च) | [1] FY-1 revised (संशोधित अनुमान) |
  [2] **FY0 जम्मा रकम** (total appropriation) | [3] **चालु खर्च** (recurrent) |
  [4] **पूँजीगत तथा वित्तीय व्यवस्था** (capital+financial) |
  [5] नेपाल सरकार (GoN source) | [6] वैदेशिक अनुदान (foreign grant) |
  [7] वैदेशिक ऋण (foreign loan).
This parser emits the three FY0 budget measures [2]/[3]/[4]; the prior-year and
source-split columns are deferred. An internal consistency invariant holds on
every parsed row — total == recurrent + capital — which the parser also enforces
at RUNTIME (a violating row means the columns mis-segmented: it emits a typed
``ValueUnparseable`` and is skipped, never persisted — Rule 6) and a test asserts.

Base measures (``base_indicator_slug``):
  - ``budget-allocation-total``     — col [2] जम्मा रकम (total appropriation).
  - ``budget-allocation-recurrent`` — col [3] चालु खर्च.
  - ``budget-allocation-capital``   — col [4] पूँजीगत तथा वित्तीय व्यवस्था. NOTE:
    this is capital AND financial-provision combined (the Red Book summary fuses
    them in one column); the name reflects "capital" but consumers must read it as
    capital+financial (documented in the README + source profile).

Dimensional model (ADR-0015): the summary table is a matrix of (budget-head ×
measure), so the parser emits ``dimensional_rows`` (NOT single-series
``staging_rows``), routed into ``dne_facts``:
  - ``dimension_kind='budget-head'`` (each row is a अनुदान संख्या / appropriation
    head — most are ministries; some are constitutional bodies, provinces 701, or
    local-level transfers 801 — so "budget-head" is the accurate kind).
  - ``dimension_value`` is the kebab slug of ``<code>-<name>`` (the federal
    appropriation code prefixes the slug so two heads never collide on a
    glyph-mangled name — ADR-0011 "identity from the code, not fuzzy name").
  - ``dimension_label`` preserves the raw extracted Devanagari name verbatim.
  The grand-total row (जम्मा) is excluded as a dimension (ADR-0003: never emit a
  total as a member).

Unit (ADR-0011 — DON'T fuzzy-match; READ the annotation on the table page):
    The summary page stamps "(रू.हजारमा)" / "(रू. हजारमा)" = Rs in THOUSAND
    (हजार = thousand). We DETECT that annotation and emit ``unit='npr_thousand'``
    verbatim. Magnitude sanity (the verification protocol, ADR-0011 Decision 2):
      - Grand-total appropriation जम्मा = 1,195,378,131 thousand = NPR 1,195.4 bn;
        plus the charged-fund summary (NPR 83.6 bn) = NPR 1,279.0 bn total — the
        published FY 2074/75 budget was ~NPR 1,279 billion (≈ NPR 1.28 trillion).
      - स्थानीय तह (801, local-level transfers) = 225,054,591 thousand = NPR 225.1
        bn; अर्थ-मन्त्रालय विविध (602) = NPR 69.3 bn — correct order of magnitude
        for the largest heads. The total==recurrent+capital invariant on every row
        is a second, structural correctness anchor.

Period dating (ADR-0013): the cover / table caption labels the AD-equivalent year
implicitly via the BS fiscal year on the cover ("आर्थिक वर्ष 2074/75"). We read
the FY label and date the facts as ``annual``; ``reporting_period_bs`` /
``fiscal_year_bs`` are the BS fiscal-year label, and the AD start/end bound the
BS-fiscal-year span (mid-Shrawan..mid-Ashadh) via the canonical period helpers.
A LOCAL helper does BS-FY label parsing so ``_common/periods`` stays untouched
(same pattern as ``fcgo_consolidated`` / ``mof_yellowbook``).

Confidence: ``B`` — Red Book figures are budget ESTIMATES/appropriations (plans,
revised across the year and superseded by FCGO actuals), not audited outturn.
(The source-registry default for ``mof-budget-redbook`` is ``A``; the parser
emits ``B`` because these are plans — see the FOR-MOTHER note recommending the
registry default be reconciled to ``B``.)

Versioning: bump ``PARSER_VERSION`` on any behaviour change.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Final

import pdfplumber

from _common.periods import (
    fiscal_year_ad_label,
    fiscal_year_label,
    mid_month_ad,
)
from _common.types import ParserError, ParserStatus, ReportingPeriodType

PARSER_VERSION: Final[str] = "0.2.0"
# Registered source id (already in seed-source-registry.ts).
SOURCE_ID: Final[str] = "mof-budget-redbook"

# Only the front matter holds the appropriation summary + FY cover; the rest of a
# ~650-page redbook is per-ministry program detail this parser ignores. Capping
# the page scan keeps the full-edition parse well under the 300s parser timeout.
_MAX_SUMMARY_SCAN_PAGES: Final[int] = 80

# Confidence default for every Red Book fact (see module docstring — budget
# ESTIMATES, not audited actuals).
_CONFIDENCE: Final[str] = "B"

# Three base measures read from the FY0 columns of the appropriation summary.
_TOTAL_SLUG: Final[str] = "budget-allocation-total"
_TOTAL_NAME: Final[str] = "Budget appropriation (total)"
_RECURRENT_SLUG: Final[str] = "budget-allocation-recurrent"
_RECURRENT_NAME: Final[str] = "Budget appropriation (recurrent)"
_CAPITAL_SLUG: Final[str] = "budget-allocation-capital"
# Combined capital + financial-provision (the summary fuses them in one column).
_CAPITAL_NAME: Final[str] = "Budget appropriation (capital and financial provision)"

_KIND_BUDGET_HEAD: Final[str] = "budget-head"

# ---------------------------------------------------------------------------
# Unit detection (ADR-0011) — read the annotation stamped on the table page.
# ---------------------------------------------------------------------------

_UNIT_NPR_THOUSAND: Final[str] = "npr_thousand"

# "(रू.हजारमा)" / "(रू. हजारमा)" / "(रु. हजारमा)" — हजार = thousand. Tolerant of
# the रू/रु spelling and inner spaces.
_UNIT_THOUSAND_RE: Final = re.compile(r"\(\s*र[ूु]\.?\s*हजारमा\s*\)")


def detect_unit(page_text: str) -> str | None:
    """Return the emitted unit string for a summary-table page, or None.

    Reads the per-page Devanagari unit annotation ("(रू.हजारमा)" = Rs in
    thousand). Returning None for a page without the annotation lets the caller
    exclude the Table-of-Contents / non-summary pages deterministically.
    """
    if _UNIT_THOUSAND_RE.search(page_text):
        return _UNIT_NPR_THOUSAND
    return None


# ---------------------------------------------------------------------------
# Fiscal-year detection — from the cover / summary caption ("आर्थिक वर्ष 2074/75"
# or a bare "2074/75" on the summary header). The Red Book labels the year in
# Western digits even in the Devanagari body.
# ---------------------------------------------------------------------------

# Matches "2074/75" or "2074-75" (BS lead year + 2-digit tail). The tail is
# validated == (lead + 1) mod 100 in `_full_year_lead` so a stray pair (e.g. a
# prior-year column header "2072/73") is only accepted as a fiscal year when it
# is internally consistent; the FIRST consistent match on the cover wins.
_FY_RE: Final = re.compile(r"\b(20\d{2})\s*[/-]\s*(\d{2})\b")


def _full_year_lead(lead: int, tail: int) -> int | None:
    """Return the BS lead year if ``tail == (lead+1) mod 100``, else None."""
    if tail != (lead + 1) % 100:
        return None
    return lead


def detect_bs_fiscal_year(text: str) -> int | None:
    """Return the BS fiscal-year lead year from a 'YYYY/YY' label, or None.

    Validates the two-digit tail equals (lead + 1) mod 100 so a stray pair is not
    misread as a fiscal year. Returns None when no valid label is present.
    """
    m = _FY_RE.search(text)
    if not m:
        return None
    return _full_year_lead(int(m.group(1)), int(m.group(2)))


# ---------------------------------------------------------------------------
# Summary-page anchors. CRITICAL (ADR-0011 "read what the extractor produces"):
# the 2074-75 edition's Devanagari extracts with glyph-reordering artifacts —
# "विनियोजन" comes out "व्व नयोजन"-style with `�` replacement glyphs, and
# "सारांश" comes out "साराशं". So we anchor on the substrings that SURVIVE the
# reordering, verified against the real ``extract_text()`` output (probe):
#   - ``योजन``     — the stable tail of "विनियोजन" (appropriation). Distinguishes
#     the appropriation block from the "व्ययभार" (charged) block, which has no
#     "योजन" and is therefore excluded. It also appears in the per-FY column
#     caption "2074/75 को विनियोजन" on every continuation page.
#   - ``जम्मा रकम`` — the "total amount" column caption, present on every
#     appropriation-summary page (start + continuations) and absent from the
#     detailed शीर्षकगत section (whose total column is "जम्मा बजेट").
# Requiring BOTH (plus at least one parseable budget-head line) gates the
# appropriation summary block deterministically. The unit annotation
# "(रू.हजारमा)" sits only on the block's FIRST page, so it is detected once over
# the whole block rather than required per page.
# ---------------------------------------------------------------------------

_ANCHOR_APPROPRIATION: Final[str] = "योजन"
_ANCHOR_TOTAL_COLUMN: Final[str] = "जम्मा रकम"

# Negative anchor: the अनुसूची-१ functional-classification annex (deep in the
# book, ~page 600+) reuses the same "जम्मा रकम" / "चालु खर्च" captions AND has
# code-led ministry rows, but is a DIFFERENT cut (10 number columns incl. a
# तुलनामा वृद्धि / growth-percent block; values differ; ministries repeat under
# functional headings). Its growth-comparison caption "तुलनामा" extracts as
# "तलु नामा" under the same glyph reordering — present on EVERY annex page and on
# NONE of the summary / overview / charged pages (verified in-corpus). Excluding
# any page bearing it keeps the annex out of the block — a second guard beyond the
# exact-8-column row check (ADR-0011 "never let a look-alike table silently
# contaminate the totals").
_ANCHOR_FUNCTIONAL_ANNEX: Final[str] = "तलु नामा"

# Devanagari digit → ASCII (the appropriation code is Western, but a defensive
# normalisation keeps a Devanagari-digit edition from silently dropping rows).
_DEVA_DIGITS: Final[dict[str, str]] = {
    "०": "0", "१": "1", "२": "2", "३": "3", "४": "4",
    "५": "5", "६": "6", "७": "7", "८": "8", "९": "9",
}

# A money token: a digit run that may carry Nepali-style thousands commas. We
# strip commas before parsing (the 2-2-2-2-3 grouping is purely visual — ADR-0011
# magnitude is preserved once commas are removed).
_NUM_TOKEN: Final[str] = r"\d[\d,]*"

# A budget-head data line: a 3-4 digit appropriation code, a name, then the
# COMPLETE trailing run of money tokens to end-of-line. The name group is lazy and
# the number run is anchored to ``$``, so the number group greedily captures EVERY
# trailing numeric token (the name never absorbs a number when an all-numeric tail
# exists). The caller then requires EXACTLY 8 tokens — which is the discriminator
# that rejects the अनुसूची-१ functional-classification annex (same जम्मा-रकम /
# चालु-खर्च captions, but 10 number columns: it adds तुलनामा-वृद्धि growth-percent
# columns) and the per-head चालु/पूँजीगत sub-rows. A defensive guard also rejects a
# name that ends in a digit (so a stray wider table cannot be coerced).
_HEAD_LINE_RE: Final = re.compile(
    r"^(\d{3,4})\s+(.+?)\s+((?:" + _NUM_TOKEN + r")(?:\s+" + _NUM_TOKEN + r")*)\s*$"
)

# Column positions within the 8 trailing money tokens (see module docstring).
_TOK_TOTAL: Final[int] = 2
_TOK_RECURRENT: Final[int] = 3
_TOK_CAPITAL: Final[int] = 4
_NUM_TOKENS_PER_ROW: Final[int] = 8

# Absolute tolerance (in the source unit, npr_thousand) for the per-row invariant
# total == recurrent + capital. 0 would be ideal (the real PDF satisfies it
# exactly on all 57 heads); a tiny slack absorbs a stray rounding/OCR token
# without masking a genuine column mis-segmentation.
_INVARIANT_TOLERANCE: Final[float] = 1.0

# Sub-row / total leaders to skip (a line beginning with one of these is NOT a
# budget-head row). चालु / पूँजीगत are the per-head recurrent/capital sub-rows;
# जम्मा / कुल are totals (never a dimension member — ADR-0003).
_SKIP_LEADERS: Final[tuple[str, ...]] = (
    "चाल", "पंूज", "पँूज", "पुंज", "पूंज", "पूँज", "पुँज", "जम्मा", "कुल",
)


# ---------------------------------------------------------------------------
# Dimensional fact contract (ADR-0015) — mirrors the Yellow Book / White Book
# parsers' DimensionalRowDraft / result wrapper field-for-field so the cloned
# ingest CLI reads the same ``dimensional_rows`` JSON.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DimensionalRowDraft:
    """One dimensional fact: a base measure sliced by exactly one dimension."""

    base_indicator_slug: str
    base_indicator_name: str
    dimension_kind: str
    dimension_value: str
    dimension_label: str
    value: float
    unit: str
    reporting_period_type: ReportingPeriodType
    reporting_period_bs: str
    reporting_period_ad_start: datetime
    reporting_period_ad_end: datetime
    fiscal_year_bs: str
    fiscal_year_ad_label: str
    confidence_grade: str

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "base_indicator_slug": self.base_indicator_slug,
            "base_indicator_name": self.base_indicator_name,
            "dimension_kind": self.dimension_kind,
            "dimension_value": self.dimension_value,
            "dimension_label": self.dimension_label,
            "value": self.value,
            "unit": self.unit,
            "reporting_period_type": self.reporting_period_type,
            "reporting_period_bs": self.reporting_period_bs,
            "reporting_period_ad_start": self.reporting_period_ad_start.isoformat(),
            "reporting_period_ad_end": self.reporting_period_ad_end.isoformat(),
            "fiscal_year_bs": self.fiscal_year_bs,
            "fiscal_year_ad_label": self.fiscal_year_ad_label,
            "confidence_grade": self.confidence_grade,
        }


@dataclass(frozen=True)
class RedbookResult:
    """Red Book parser result carrying dimensional output only.

    The Red Book summary is a dimensional matrix (no single-series
    ``staging_rows``), so this wrapper mirrors the DNE/Yellow Book CLI's expected
    JSON shape: a ``dimensional_rows`` array plus ``status`` / ``errors``.
    """

    status: ParserStatus
    parser_version: str
    dimensional_rows: list[DimensionalRowDraft]
    errors: list[ParserError]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "parser_version": self.parser_version,
            "dimensional_rows": [r.to_json_dict() for r in self.dimensional_rows],
            "errors": [e.to_json_dict() for e in self.errors],
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _deva_to_ascii(text: str) -> str:
    """Map Devanagari digits to ASCII; leave other characters untouched."""
    return "".join(_DEVA_DIGITS.get(ch, ch) for ch in text)


def _parse_value(token: str) -> float | None:
    """Parse a money token to float; None for empty / dash / non-numeric.

    Strips Nepali thousands commas (the grouping is visual; ADR-0011 magnitude is
    preserved once commas are removed). A dash/blank becomes None (never
    fabricated as 0); a genuine source ``0`` is preserved as ``0.0``.
    """
    s = _deva_to_ascii(token).strip()
    if s in ("", "-", "--", "–", "—", "N/A", "n/a", "NA", "...", "."):
        return None
    try:
        v = float(s.replace(",", ""))
    except (TypeError, ValueError):
        return None
    if v != v:  # NaN  # noqa: PLR0124
        return None
    return v


def _slugify_head(code: str, label: str) -> str:
    """Kebab slug of ``<code>-<name>`` for ``dimension_value``.

    The federal appropriation code prefixes the slug so two budget heads never
    collide on a glyph-mangled Devanagari name (ADR-0011: identity from the code,
    not the fuzzy name). Devanagari is preserved (lowercasing is a no-op for it);
    only ASCII is lowercased; punctuation collapses to hyphens; whitespace runs
    fold to a single hyphen. The RAW name is kept as ``dimension_label``.
    """
    s = f"{code} {label}".lower()
    s = re.sub(r"[\s.,/()\[\]{}:;\"'`*&+]+", " ", s)
    return re.sub(r"\s+", "-", s.strip())


def _is_skip_line(line: str) -> bool:
    """True for sub-rows (चालु/पूँजीगत) and total rows (जम्मा/कुल)."""
    s = line.strip()
    return any(s.startswith(p) for p in _SKIP_LEADERS)


def _annual_span(bs_fy_start: int) -> tuple[datetime, datetime]:
    """AD start/end bounding the BS fiscal-year span (mid-Shrawan..mid-Ashadh)."""
    start = mid_month_ad("Shrawan", bs_fy_start)
    end = mid_month_ad("Ashadh", bs_fy_start)
    return start, end


def _make_row(
    base_slug: str,
    base_name: str,
    code: str,
    name_raw: str,
    value: float,
    unit: str,
    bs_fy_start: int,
    ad_start: datetime,
    ad_end: datetime,
) -> DimensionalRowDraft:
    """Build one budget-head dimensional fact for a base measure + value."""
    return DimensionalRowDraft(
        base_indicator_slug=base_slug,
        base_indicator_name=base_name,
        dimension_kind=_KIND_BUDGET_HEAD,
        dimension_value=_slugify_head(code, name_raw),
        dimension_label=name_raw,
        value=value,
        unit=unit,
        reporting_period_type="annual",
        reporting_period_bs=fiscal_year_label(bs_fy_start),
        reporting_period_ad_start=ad_start,
        reporting_period_ad_end=ad_end,
        fiscal_year_bs=fiscal_year_label(bs_fy_start),
        fiscal_year_ad_label=fiscal_year_ad_label(bs_fy_start),
        confidence_grade=_CONFIDENCE,
    )


# ---------------------------------------------------------------------------
# Deterministic core — exercised against synthesized text-line fixtures.
# ---------------------------------------------------------------------------


def extract_dimensional_rows(
    summary_text: str,
    unit: str,
    bs_fy_start: int,
) -> tuple[list[DimensionalRowDraft], list[ParserError]]:
    """Convert the appropriation-summary text → per-budget-head dimensional facts.

    ``summary_text`` is the concatenated ``extract_text()`` of the summary pages.
    A budget-head line is ``<3-4 digit code> <name> <exactly 8 money tokens>``;
    the चालु/पूँजीगत sub-rows and जम्मा/कुल totals are skipped, and a line with a
    count other than 8 numeric tokens (the 10-column functional annex) is rejected.
    For each head we emit three facts — ``budget-allocation-total`` (token 2),
    ``budget-allocation-recurrent`` (token 3), ``budget-allocation-capital``
    (token 4). A genuine source ``0`` is kept. Never raises.

    No-silent-failure guard (Rule 6): the source's own invariant is
    total == recurrent + capital. If a matched row violates it (beyond a tiny
    tolerance) the row's columns mis-segmented — the parser emits a typed
    ``ValueUnparseable`` AND skips the row so a wrong number never reaches the
    fact table. Re-emitting the same (slug, head) is de-duplicated (idempotent
    within one document).
    """
    ad_start, ad_end = _annual_span(bs_fy_start)
    rows: list[DimensionalRowDraft] = []
    errors: list[ParserError] = []
    seen: set[tuple[str, str]] = set()

    for raw_line in summary_text.splitlines():
        line = raw_line.strip()
        if not line or _is_skip_line(line):
            continue
        m = _HEAD_LINE_RE.match(line)
        if m is None:
            continue
        code = m.group(1)
        name = " ".join(m.group(2).split())
        tokens = m.group(3).split()
        # EXACTLY 8 number columns identifies the appropriation-summary row shape
        # and rejects the 10-column अनुसूची-१ functional annex (see _HEAD_LINE_RE).
        if len(tokens) != _NUM_TOKENS_PER_ROW:
            continue
        # Defensive: a genuine head name never ends in a digit; if it does, the
        # lazy name group absorbed a numeric column from a wider/odd table — skip.
        if name and _deva_to_ascii(name[-1]).isdigit():
            continue

        # Every token matched ``_NUM_TOKEN`` (digits/commas), so each measure
        # parses; ``_parse_value`` returns None only for a dash/blank, which this
        # numeric-token regex cannot produce — so a real budget-head row always
        # yields all three measures.
        parsed = [_parse_value(t) for t in tokens]
        total_v = parsed[_TOK_TOTAL]
        recurrent_v = parsed[_TOK_RECURRENT]
        capital_v = parsed[_TOK_CAPITAL]

        # No-silent-failure guard (Rule 6): the source's own invariant is
        # total == recurrent + capital. A violation means the row's columns
        # mis-segmented (a layout regression) — surface a typed error AND skip the
        # row so a wrong number never reaches the fact table. A small absolute
        # tolerance covers a stray rounding token.
        if (
            total_v is not None
            and recurrent_v is not None
            and capital_v is not None
            and abs(total_v - (recurrent_v + capital_v)) > _INVARIANT_TOLERANCE
        ):
            errors.append(
                ParserError(
                    error_class="ValueUnparseable",
                    error_detail=(
                        f"budget head {name!r} (code {code}): total "
                        f"{total_v:.0f} != recurrent {recurrent_v:.0f} + capital "
                        f"{capital_v:.0f} — columns may have mis-segmented; row skipped"
                    ),
                    source_excerpt=line[:200],
                )
            )
            continue

        head_slug = _slugify_head(code, name)
        for base_slug, base_name, value in (
            (_TOTAL_SLUG, _TOTAL_NAME, total_v),
            (_RECURRENT_SLUG, _RECURRENT_NAME, recurrent_v),
            (_CAPITAL_SLUG, _CAPITAL_NAME, capital_v),
        ):
            if value is None:
                continue
            key = (base_slug, head_slug)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                _make_row(
                    base_slug, base_name, code, name, value,
                    unit, bs_fy_start, ad_start, ad_end,
                )
            )

    return rows, errors


# ---------------------------------------------------------------------------
# PDF reading — locate the appropriation-summary pages and feed the core.
# ---------------------------------------------------------------------------


def _page_is_appropriation_summary(text: str) -> bool:
    """True if a page is part of the appropriation (विनियोजन) summary section.

    Gates on the two reordering-survivable anchors (``योजन`` + ``जम्मा रकम``;
    see the anchor-block comment) AND the absence of the functional-annex anchor
    (``तलु नामा``). This holds for every page of the summary block — its captioned
    first page AND its column-caption continuation pages — and excludes: the
    charged (व्ययभार) summary (no ``योजन``); the detailed शीर्षकगत section (total
    column is "जम्मा बजेट", not "जम्मा रकम"); and the अनुसूची-१ functional annex
    (carries ``तलु नामा``). The unit annotation is NOT required per page (it sits
    only on the block's first page); the caller detects the unit once over the
    whole collected block.
    """
    return (
        _ANCHOR_APPROPRIATION in text
        and _ANCHOR_TOTAL_COLUMN in text
        and _ANCHOR_FUNCTIONAL_ANNEX not in text
    )


def parse_redbook(source_document_path: str, source_document_id: str) -> RedbookResult:
    """Parse one Red Book PDF → budget-allocation dimensional facts (ADR-0015).

    Scans every page; collects the appropriation (विनियोजन) summary pages (the
    first carries the section caption + unit annotation; the rest are unit-bearing
    continuation pages with the per-FY caption), concatenates their text, reads
    the BS fiscal year from the cover/caption, and emits per-budget-head
    ``budget-allocation-{total,recurrent,capital}`` facts. Never raises on bad
    data: an unreadable / CID-broken / Preeti / glyph-mangled edition (every
    edition except "Red Book Central 2074-75") yields typed errors and
    ``status='failure'``.
    """
    _ = source_document_id  # threaded for orchestrator-contract symmetry

    path = Path(source_document_path)
    if not path.exists():
        return RedbookResult(
            status="failure",
            parser_version=PARSER_VERSION,
            dimensional_rows=[],
            errors=[
                ParserError(
                    error_class="Other",
                    error_detail=f"source file not found: {path}",
                )
            ],
        )

    try:
        with pdfplumber.open(str(path)) as pdf:
            # The appropriation SUMMARY (विनियोजन सारांश) + the FY cover are front
            # matter (≈ pp 1–30); the remaining hundreds of pages are per-ministry
            # program DETAIL this parser does not read. A full redbook is ~650
            # pages, and extract_text() on every page blows the 300s parser
            # timeout. Cap the scan to the front matter — generous enough for the
            # summary block + continuations on any edition. (Tests use small
            # fixtures, so the cap is a no-op there.)
            page_texts = [page.extract_text() or "" for page in pdf.pages[:_MAX_SUMMARY_SCAN_PAGES]]
    except (OSError, ValueError) as exc:
        return RedbookResult(
            status="failure",
            parser_version=PARSER_VERSION,
            dimensional_rows=[],
            errors=[
                ParserError(
                    error_class="EncodingError",
                    error_detail=f"pdfplumber could not read {path.name}: {exc}",
                )
            ],
        )

    # Fiscal year: read the cover/front matter (first consistent BS FY label).
    bs_fy_start: int | None = None
    for text in page_texts:
        detected = detect_bs_fiscal_year(text)
        if detected is not None:
            bs_fy_start = detected
            break

    # Collect every appropriation-summary page (start + continuations) and detect
    # the unit once from whichever page carries the "(रू.हजारमा)" annotation (the
    # block's first page does; the continuations repeat only the column caption).
    summary_unit: str | None = None
    summary_parts: list[str] = []
    for text in page_texts:
        if not _page_is_appropriation_summary(text):
            continue
        summary_parts.append(text)
        if summary_unit is None:
            summary_unit = detect_unit(text)

    all_errors: list[ParserError] = []

    if not summary_parts or summary_unit is None:
        all_errors.append(
            ParserError(
                error_class="PageLayoutChanged",
                error_detail=(
                    "No clean appropriation (विनियोजन) summary page with a "
                    "'(रू.हजारमा)' unit annotation found — this edition is likely "
                    "CID-broken, Preeti-encoded, or glyph-mangled (every edition "
                    "except 'Red Book Central 2074-75'). Documented infeasibility "
                    "per ADR-0003; no values fabricated. See "
                    "scrapers/mof_redbook/parser.py STEP-0 assessment."
                ),
            )
        )
        return RedbookResult(
            status="failure",
            parser_version=PARSER_VERSION,
            dimensional_rows=[],
            errors=all_errors,
        )

    if bs_fy_start is None:
        all_errors.append(
            ParserError(
                error_class="PeriodAmbiguous",
                error_detail=(
                    "appropriation summary found but no 'YYYY/YY' BS fiscal-year "
                    "label located on the cover — cannot date the facts"
                ),
            )
        )
        return RedbookResult(
            status="failure",
            parser_version=PARSER_VERSION,
            dimensional_rows=[],
            errors=all_errors,
        )

    rows, row_errors = extract_dimensional_rows(
        "\n".join(summary_parts), summary_unit, bs_fy_start
    )
    all_errors.extend(row_errors)

    if not rows:
        all_errors.append(
            ParserError(
                error_class="Other",
                error_detail=(
                    "NoDataExtracted: appropriation summary located but no "
                    "budget-head rows parsed"
                ),
            )
        )
        return RedbookResult(
            status="failure",
            parser_version=PARSER_VERSION,
            dimensional_rows=[],
            errors=all_errors,
        )

    status: ParserStatus = "partial" if all_errors else "success"
    return RedbookResult(
        status=status,
        parser_version=PARSER_VERSION,
        dimensional_rows=rows,
        errors=all_errors,
    )


def _main() -> None:
    """CLI entrypoint (orchestrator contract — mirror of mof_yellowbook.parser).

    Argv: ``parser.py <source_document_path> <source_document_id>``. Writes the
    result JSON (including the ``dimensional_rows`` key the ingest CLI reads) to
    stdout. Datetimes are ISO-8601 strings. Exit codes: 0 = ran (status may be
    failure), 2 = usage error.
    """
    expected_argv = 3  # progname + path + doc id
    if len(sys.argv) != expected_argv:
        sys.stderr.write("usage: parser.py <source_document_path> <source_document_id>\n")
        sys.exit(2)

    result = parse_redbook(sys.argv[1], sys.argv[2])
    json.dump(result.to_json_dict(), sys.stdout)


if __name__ == "__main__":
    _main()
