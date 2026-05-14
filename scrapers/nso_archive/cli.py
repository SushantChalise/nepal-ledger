"""CLI entry point for the NSO archive scraper. See README.md. Exit 0 clean, 1 errors, 2 args."""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path
from typing import Final

import httpx

from nso_archive.archive import ArchiveError, archive_document
from nso_archive.discover import DiscoveryError, discover_documents
from nso_archive.manifest import append_event

DEFAULT_CATEGORY_BASE: Final[str] = "https://nsonepal.gov.np/category/"
DEFAULT_MAX_DOCS: Final[int] = 100
USER_AGENT: Final[str] = "nepal-ledger/0.1 (+https://github.com/SushantChalise/nepal-ledger)"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m scrapers.nso_archive.cli",
        description="Acquire NSO Nepal PDFs and append a provenance manifest.",
    )
    p.add_argument("--category-ids", nargs="+", required=True,
                   help="One or more NSO category ids (e.g. 1058 1059).")
    p.add_argument("--output-dir", required=True, type=Path,
                   help="Directory for downloaded PDFs, sidecars, and manifest.jsonl.")
    p.add_argument("--category-base-url", default=DEFAULT_CATEGORY_BASE,
                   help=f"Base URL for category pages (default: {DEFAULT_CATEGORY_BASE}).")
    p.add_argument("--max-docs", type=int, default=DEFAULT_MAX_DOCS,
                   help=f"Hard cap on PDFs archived per run (default: {DEFAULT_MAX_DOCS}).")
    p.add_argument("--discovery-timeout-s", type=int, default=30,
                   help="Timeout (s) for each category page fetch.")
    p.add_argument("--download-timeout-s", type=int, default=120,
                   help="Timeout (s) for each PDF download.")
    p.add_argument("--dry-run", action="store_true",
                   help="Discover only; log discovery_only events without downloading.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    out_dir: Path = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {"discovered": 0, "archived": 0, "skipped": 0, "errors": 0}

    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        for category_id in args.category_ids:
            category_url = f"{args.category_base_url.rstrip('/')}/{category_id}/"
            try:
                docs = discover_documents(
                    category_url, timeout_s=args.discovery_timeout_s, client=client
                )
            except DiscoveryError as exc:
                counts["errors"] += 1
                append_event(out_dir, event_type="error", url=category_url,
                             category_id=str(category_id),
                             payload={"phase": "discovery", "error": repr(exc)})
                continue
            counts["discovered"] += len(docs)
            for doc in docs:
                if counts["archived"] >= args.max_docs:
                    sys.stderr.write(f"Reached --max-docs cap ({args.max_docs}); stopping.\n")
                    break
                if args.dry_run:
                    append_event(out_dir, event_type="discovery_only", url=doc.url,
                                 category_id=doc.category_id, payload={"title": doc.title})
                    continue
                try:
                    result = archive_document(
                        doc, out_dir, timeout_s=args.download_timeout_s, client=client
                    )
                except ArchiveError as exc:
                    counts["errors"] += 1
                    append_event(out_dir, event_type="error", url=doc.url,
                                 category_id=doc.category_id,
                                 payload={"phase": "archive", "error": repr(exc),
                                          "trace": traceback.format_exc(limit=3)})
                    continue
                if result is None:
                    counts["skipped"] += 1
                    append_event(out_dir, event_type="skipped_duplicate", url=doc.url,
                                 category_id=doc.category_id, payload={"title": doc.title})
                else:
                    counts["archived"] += 1
                    append_event(out_dir, event_type="archived", url=doc.url,
                                 category_id=doc.category_id,
                                 payload={"sha256": result.sha256, "bytes": result.bytes,
                                          "title": doc.title})

    sys.stdout.write(
        f"discovered: {counts['discovered']}, archived: {counts['archived']}, "
        f"skipped: {counts['skipped']}, errors: {counts['errors']}\n"
    )
    return 0 if counts["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
