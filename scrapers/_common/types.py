"""Parser data contract — mirrors TypeScript enums in src/lib/db/schema/enums.ts
and the row shape in src/lib/db/schema/indicator-values.ts.

Any change here that diverges from the TS side needs a coordinated update.
Literals are spelled exactly as the Postgres enums (snake_case where applicable).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal

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

    def to_json_dict(self) -> dict[str, Any]:
        """Serializable dict with ISO 8601 strings for all datetime fields.

        The TS-side Zod schema (`src/lib/ingestion/types.ts`) accepts ISO
        strings and coerces them to Date via ``z.coerce.date()``.
        """
        return {
            "indicator_slug_raw": self.indicator_slug_raw,
            "value": self.value,
            "unit": self.unit,
            "reporting_period_type": self.reporting_period_type,
            "reporting_period_bs": self.reporting_period_bs,
            "reporting_period_ad_start": self.reporting_period_ad_start.isoformat(),
            "reporting_period_ad_end": self.reporting_period_ad_end.isoformat(),
            "publication_date_ad": self.publication_date_ad.isoformat(),
            "publication_date_bs": self.publication_date_bs,
            "fiscal_year_bs": self.fiscal_year_bs,
            "fiscal_year_ad_label": self.fiscal_year_ad_label,
            "confidence_grade_proposed": self.confidence_grade_proposed,
            "parser_notes": self.parser_notes,
        }


@dataclass(frozen=True)
class ParserError:
    error_class: ParserErrorClass
    error_detail: str
    source_excerpt: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ParserResult:
    status: ParserStatus
    parser_version: str
    staging_rows: list[StagingRowDraft] = field(default_factory=list)
    errors: list[ParserError] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        """Top-level serializer used by parser ``__main__`` entrypoints.

        Returns the shape expected by ``ParserOutputSchema`` on the TS side
        (`src/lib/ingestion/types.ts`). Datetimes are ISO 8601 strings.
        """
        return {
            "status": self.status,
            "parser_version": self.parser_version,
            "staging_rows": [row.to_json_dict() for row in self.staging_rows],
            "errors": [e.to_json_dict() for e in self.errors],
        }
