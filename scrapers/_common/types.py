"""Parser data contract — mirrors TypeScript enums in src/lib/db/schema/enums.ts
and the row shape in src/lib/db/schema/indicator-values.ts.

Any change here that diverges from the TS side needs a coordinated update.
Literals are spelled exactly as the Postgres enums (snake_case where applicable).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

ParserStatus = Literal["success", "partial", "failure"]
ConfidenceGrade = Literal["A", "B", "C"]
ReportingPeriodType = Literal[
    "monthly",
    "quarterly",
    "annual",
    "nine_months_cumulative",
    "year_to_date",
    "daily",
    "seasonal",
]
# Subset relevant to parser-emitted errors. Keep aligned with parserErrorClassEnum.
ParserErrorClass = Literal[
    "ColumnMissing",
    "RegexMismatch",
    "UnitAmbiguous",
    "PageLayoutChanged",
    "PeriodAmbiguous",
    "ValueUnparseable",
    "EncodingError",
    "Other",
]


@dataclass(frozen=True)
class StagingRowDraft:
    """Mirror of src/lib/db/schema/indicator-values.ts > stagingIndicatorValues
    (the fields a parser is responsible for emitting; FKs, IDs, and inserted_at
    are filled in by the orchestration layer).
    """

    indicator_slug_raw: str
    value: float
    unit: str
    reporting_period_type: ReportingPeriodType
    reporting_period_bs: str
    reporting_period_ad_start: datetime
    reporting_period_ad_end: datetime
    publication_date_ad: datetime
    publication_date_bs: str
    fiscal_year_bs: str
    fiscal_year_ad_label: str
    confidence_grade_proposed: ConfidenceGrade
    parser_notes: str | None = None


BankClass = Literal[
    "commercial",
    "development",
    "finance",
    "microfinance",
    "infrastructure",
    "system_total",
]


@dataclass(frozen=True)
class StagingBfiRowDraft:
    """Mirror of src/lib/db/schema/banking-sector-facts.ts > bankingSectorFacts
    (parser-emitted fields only; FKs, IDs, promoted_at filled in by the
    orchestration layer).

    Differs from ``StagingRowDraft`` by including ``bank_class``,
    ``bank_entity_slug`` (NULL until the entity-resolver maps it), and
    ``source_sheet`` (which C-sheet the value came from).

    ``indicator_slug`` here is the kebab-case slug; the orchestrator does NOT
    re-key by `_raw` suffix because BFI slugs are themselves the canonical
    identifier (the C-sheet -> slug map lives in scrapers/nrb_bfi/parser.py).
    """

    source_sheet: str
    indicator_slug: str
    bank_class: BankClass
    bank_entity_slug: str | None
    value: float
    unit: str
    reporting_period_type: ReportingPeriodType
    reporting_period_bs: str
    reporting_period_ad_start: datetime
    reporting_period_ad_end: datetime
    publication_date_ad: datetime
    publication_date_bs: str
    fiscal_year_bs: str
    confidence_grade_proposed: ConfidenceGrade
    parser_notes: str | None = None


@dataclass(frozen=True)
class ParserError:
    error_class: ParserErrorClass
    error_detail: str
    source_excerpt: str | None = None


@dataclass(frozen=True)
class ParserResult:
    status: ParserStatus
    parser_version: str
    staging_rows: list[StagingRowDraft] = field(default_factory=list)
    errors: list[ParserError] = field(default_factory=list)
