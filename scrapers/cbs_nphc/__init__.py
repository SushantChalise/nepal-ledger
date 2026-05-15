"""Parser for CBS National Population & Housing Census 2021 (NPHC 2021).

Source ID: ``cbs-nphc-2021`` (see docs/sources/cbs-nphc-2021.md).

The corpus is the 89 palika-grain CSVs under
``Financial Data/Census/census_2021_data/census-dataset/``. The header layout
of those CSVs is NOT uniform: ``Hhld01..Hhld04`` carry a 5-line title
preamble while the remaining 85 files have a clean row-0 header. This package
ships a two-mode reader (``two_mode_reader``) that detects layout and the
parser (``parser``) that emits :class:`CensusFactDraft` rows keyed on
``(entity_slug, indicator_slug, census_year_ad)``.

See ``docs/research/cbs-nphc-2021-audit.md`` for the canonical audit.
"""

from .parser import (
    PARSER_VERSION,
    SOURCE_ID,
    CensusFactDraft,
    CensusParserError,
    CensusParserResult,
    parse,
)

__all__ = [
    "PARSER_VERSION",
    "SOURCE_ID",
    "CensusFactDraft",
    "CensusParserError",
    "CensusParserResult",
    "parse",
]
