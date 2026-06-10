# ADR-0013: NRB DNE accepts AD fiscal-year period labels

- **Status:** Accepted
- **Date:** 2026-06-07
- **Deciders:** Mother Opus
- **Tags:** data-pipeline, parsers, calendar, dne

## Context

The `nrb_dne` parser (ADR-0010 umbrella source `nrb-dne-xlsx`) was built and tested against synthetic fixtures that used **BS** fiscal-year labels (e.g. `2079/80`). Worker J downloaded six real NRB *Database on Nepalese Economy* External Sector files (forex reserves, remittance, foreign trade, BoP BPM6, tourist arrivals, exchange rate) and found they label periods by **AD** fiscal year instead — `2022/23`, sometimes with revision suffixes (`2023/24R`).

The first parser version silently misread these: an AD label `2021/22` was treated as BS `2021/22` and mapped to ~1964/65 AD — four decades of error. Worker J's v0.2.0 added a `_BS_YEAR_MIN = 2040` guard so any year label below 2040 is rejected as `PeriodUnparseable` rather than corrupting the date. That made the parser **safe** (fail loud) but **unable to ingest** the External Sector corpus.

This is a calendar-semantics decision, so per [CALENDAR_AND_PERIODS.md](../CALENDAR_AND_PERIODS.md) it gets an ADR rather than an inline parser tweak.

## Decision

The DNE parser **accepts both BS and AD fiscal-year labels** and normalizes to the project's canonical period model.

1. **Disambiguation by magnitude (deterministic).** A `YYYY/YY` label whose lead year is ≥ 2040 is BS; ≤ 2039 is AD. The two ranges cannot overlap for any data this project ingests (BS 2040 ≈ AD 1983; AD 2039 is the future), so the heuristic is unambiguous in practice. Keep `_BS_YEAR_MIN = 2040` as the boundary constant.
2. **AD → BS via the fiscal-year offset.** Nepal's fiscal year is mid-July to mid-July, so an AD fiscal year maps 1:1 to a Nepali (BS) fiscal year: AD `2022/23` = BS `2079/80`. The conversion uses `_common/periods` (`fiscal_year_ad_label` and its inverse), not a hardcoded `+56/57`, and is verified against known pairs in tests. The row stores the BS fiscal-year label in `reporting_period_bs` and the AD label in `fiscal_year_ad_label`, identical to every other source.
3. **`reporting_period_type = 'annual'`** for these fiscal-year series; AD start/end come from the mid-July boundary via the existing period helpers. Monthly sub-columns, where present, are a separate (deferred) concern — the first ingest targets the annual series.
4. **Still fail loud on the genuinely unparseable** — transposed year-as-row layouts (tourist arrivals) and `datetime`-object period columns (one remittance sheet) remain `PeriodUnparseable` until a parser pass handles those shapes. No silent fallback, ever.

## Alternatives Considered

- **Store AD years as-is, skip BS.** Rejected — breaks the invariant that every fact carries a BS period; the Pulse/Money-Map period joins assume it.
- **Treat the ambiguity as unresolvable, require a per-file `--calendar` flag.** Rejected — the magnitude heuristic is deterministic for all real data; a flag adds operator burden and a foot-gun.
- **Leave DNE BS-only and skip External Sector.** Rejected — forex/remittance/trade/BoP are the core Money-In/Money-Out series; abandoning them defeats the source's purpose.

## Consequences

- The External Sector annual series become ingestable; forex reserves, remittance, trade, and BoP can feed Pulse + the Money Map.
- The parser carries calendar-disambiguation logic; the `_BS_YEAR_MIN`/AD-range constants are the single source of that truth and must be cited in tests.
- Transposed and datetime-period DNE sheets remain deferred and explicitly error — tracked as follow-ups, not silent gaps.
- Cross-source consistency holds: every DNE fact still carries both a BS and an AD fiscal-year label.

## References

- [ADR-0010](0010-ingest-cli-conventions.md) — ingest CLI conventions / DNE umbrella source
- [ADR-0011](0011-fiscal-data-units-and-identity.md) — the data-unit + read-the-source-not-fuzzy precedents
- [CALENDAR_AND_PERIODS.md](../CALENDAR_AND_PERIODS.md) — BS/AD + fiscal-year handling
- `scrapers/nrb_dne/parser.py` (`_BS_YEAR_MIN`, `_parse_annual_fy`), `scrapers/_common/periods.py`
