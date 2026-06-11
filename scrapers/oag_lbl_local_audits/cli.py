"""CLI for the OAG local-body report acquisition scraper. See README.md.

Default mode is DISCOVER-ONLY (harvest the ~6,000-report URL catalog into the
manifest, no downloads). Pass --archive to actually download, narrowed by
--province / --fiscal-year / --max-docs. Exit 0 clean, 1 errors, 2 args.
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path
from typing import Final

import httpx

from oag_lbl_local_audits.archive import ArchiveError, archive_report
from oag_lbl_local_audits.discover import DiscoveryError, LocalReportRef, discover_reports
from oag_lbl_local_audits.manifest import append_event

USER_AGENT: Final[str] = "nepal-ledger/0.1 (+https://github.com/SushantChalise/nepal-ledger)"
DEFAULT_MAX_DOCS: Final[int] = 50


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m scrapers.oag_lbl_local_audits.cli",
        description=(
            "Discover (and optionally archive) OAG local-body audit reports from "
            "the backend JSON API."
        ),
    )
    p.add_argument("--output-dir", required=True, type=Path, help="Dir for PDFs/sidecars/manifest.")
    p.add_argument("--province", default=None, help="Case-insensitive province-name filter.")
    p.add_argument("--fiscal-year", default=None, help="Substring filter on the FY label.")
    p.add_argument("--lang", default=None, help="Filter by file language tag (e.g. en, ne).")
    p.add_argument("--page-from", type=int, default=1, help="First API page (default 1).")
    p.add_argument("--page-to", type=int, default=None, help="Last API page (default: all).")
    p.add_argument(
        "--archive",
        action="store_true",
        help="Download matching reports (default is discover-only — no downloads).",
    )
    p.add_argument(
        "--max-docs",
        type=int,
        default=DEFAULT_MAX_DOCS,
        help=f"Cap on PDFs archived per run when --archive (default {DEFAULT_MAX_DOCS}).",
    )
    p.add_argument("--download-timeout-s", type=int, default=180)
    return p


def _matches(ref: LocalReportRef, args: argparse.Namespace) -> bool:
    if args.province and args.province.lower() not in ref.province_name.lower():
        return False
    if args.fiscal_year and args.fiscal_year not in ref.fiscal_year_label:
        return False
    return not (args.lang and ref.lang != args.lang)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    out_dir: Path = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {"discovered": 0, "archived": 0, "skipped": 0, "errors": 0}

    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        try:
            refs = discover_reports(client, page_from=args.page_from, page_to=args.page_to)
            for ref in refs:
                if not _matches(ref, args):
                    continue
                counts["discovered"] += 1
                append_event(
                    out_dir,
                    event_type="discovered",
                    url=ref.url,
                    ref_key=ref.ref_key,
                    payload={
                        "municipality": ref.municipality_name,
                        "province": ref.province_name,
                        "district": ref.district_name,
                        "fiscal_year": ref.fiscal_year_label,
                        "audited_fy": ref.audited_fiscal_year_bs,
                        "lang": ref.lang,
                    },
                )
                if not args.archive:
                    continue
                if counts["archived"] >= args.max_docs:
                    continue
                try:
                    result = archive_report(
                        ref, out_dir, timeout_s=args.download_timeout_s, client=client
                    )
                except ArchiveError as exc:
                    counts["errors"] += 1
                    append_event(
                        out_dir,
                        event_type="error",
                        url=ref.url,
                        ref_key=ref.ref_key,
                        payload={"error": repr(exc), "trace": traceback.format_exc(limit=2)},
                    )
                    continue
                if result is None:
                    counts["skipped"] += 1
                else:
                    counts["archived"] += 1
        except DiscoveryError as exc:
            counts["errors"] += 1
            append_event(
                out_dir, event_type="error", url="<discovery>", ref_key="<discovery>",
                payload={"error": repr(exc)},
            )

    sys.stdout.write(
        f"discovered: {counts['discovered']}, archived: {counts['archived']}, "
        f"skipped: {counts['skipped']}, errors: {counts['errors']}\n"
    )
    return 0 if counts["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
