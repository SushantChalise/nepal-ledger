"""CLI for the OAG audit-report archive. See README.md. Exit 0 clean, 1 errors, 2 args."""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path
from typing import Final

import httpx

from oag_audit_reports.archive import ArchiveError, archive_report
from oag_audit_reports.manifest import append_event
from oag_audit_reports.sources import KNOWN_REPORTS, Language, select_reports

USER_AGENT: Final[str] = "nepal-ledger/0.1 (+https://github.com/SushantChalise/nepal-ledger)"
DEFAULT_MAX_DOCS: Final[int] = 50


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m scrapers.oag_audit_reports.cli",
        description=(
            "Acquire OAG audit-report PDFs from the curated catalog and append a "
            "provenance manifest."
        ),
    )
    p.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory for downloaded PDFs, sidecars, and manifest.jsonl.",
    )
    p.add_argument(
        "--edition",
        nargs="+",
        type=int,
        default=None,
        help="Restrict to these report editions (e.g. 58 61).",
    )
    p.add_argument(
        "--language",
        choices=["en", "ne"],
        default=None,
        help="Restrict to one language edition.",
    )
    p.add_argument(
        "--max-docs",
        type=int,
        default=DEFAULT_MAX_DOCS,
        help=f"Hard cap on PDFs archived per run (default: {DEFAULT_MAX_DOCS}).",
    )
    p.add_argument(
        "--download-timeout-s",
        type=int,
        default=120,
        help="Timeout (s) for each PDF download.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="List the catalog selection without downloading.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    out_dir: Path = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    editions = frozenset(args.edition) if args.edition else None
    language: Language | None = args.language
    selected = select_reports(KNOWN_REPORTS, editions=editions, language=language)
    counts = {"selected": len(selected), "archived": 0, "skipped": 0, "errors": 0}

    if args.dry_run:
        for ref in selected:
            append_event(
                out_dir,
                event_type="discovery_only",
                url=ref.url,
                ref_key=ref.ref_key,
                payload={"title": ref.title, "verified": ref.verified},
            )
            sys.stdout.write(f"[dry-run] {ref.ref_key:>22}  verified={ref.verified}  {ref.url}\n")
        sys.stdout.write(f"selected: {counts['selected']} (dry-run, no downloads)\n")
        return 0

    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        for ref in selected:
            if counts["archived"] >= args.max_docs:
                sys.stderr.write(f"Reached --max-docs cap ({args.max_docs}); stopping.\n")
                break
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
                    payload={
                        "phase": "archive",
                        "error": repr(exc),
                        "trace": traceback.format_exc(limit=3),
                    },
                )
                continue
            if result is None:
                counts["skipped"] += 1
                append_event(
                    out_dir,
                    event_type="skipped_duplicate",
                    url=ref.url,
                    ref_key=ref.ref_key,
                    payload={"title": ref.title},
                )
            else:
                counts["archived"] += 1
                append_event(
                    out_dir,
                    event_type="archived",
                    url=ref.url,
                    ref_key=ref.ref_key,
                    payload={"sha256": result.sha256, "bytes": result.bytes, "title": ref.title},
                )

    sys.stdout.write(
        f"selected: {counts['selected']}, archived: {counts['archived']}, "
        f"skipped: {counts['skipped']}, errors: {counts['errors']}\n"
    )
    return 0 if counts["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
