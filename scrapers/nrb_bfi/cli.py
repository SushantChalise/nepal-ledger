"""CLI driver for the NRB BFI parser.

Walks a directory of XLSX snapshots and emits one staging JSON per file at
``staging-data/nrb-bfi/<stem>.json``. Idempotent: re-running overwrites
existing outputs.

Usage::

    python -m scrapers.nrb_bfi.cli \
        --inputs "Financial Data/nrb_monthly_statistics" \
        --outputs staging-data/nrb-bfi
"""

from __future__ import annotations

import argparse
import dataclasses
import json
from datetime import datetime
from pathlib import Path

from _common.hashing import sha256_of_file

from .parser import PARSER_VERSION, parse


def _serialise_row(row: object) -> dict[str, object]:
    """Convert a frozen dataclass row to JSON-friendly primitives.

    Accepts ``StagingBfiRowDraft`` (BFI parser) or any other staging row
    dataclass; we don't import the type to keep this CLI loosely coupled.
    """
    if not dataclasses.is_dataclass(row):
        raise TypeError(f"expected a dataclass instance, got {type(row).__name__}")
    out: dict[str, object] = {}
    for f in dataclasses.fields(row):
        value = getattr(row, f.name)
        if isinstance(value, datetime):
            out[f.name] = value.isoformat()
        else:
            out[f.name] = value
    return out


def emit_for_file(source_path: Path, output_dir: Path) -> dict[str, object]:
    """Parse one XLSX and write its staging JSON. Returns a summary dict."""
    result = parse(str(source_path), source_document_id=source_path.name)
    output_dir.mkdir(parents=True, exist_ok=True)

    sha = sha256_of_file(source_path)
    payload: dict[str, object] = {
        "source_file": str(source_path).replace("\\", "/"),
        "source_hash_sha256": sha,
        "source_bytes": source_path.stat().st_size,
        "parser_version": PARSER_VERSION,
        "parser_status": result.status,
        "row_count": len(result.staging_rows),
        "error_count": len(result.errors),
        "rows": [_serialise_row(r) for r in result.staging_rows],
        "errors": [
            {
                "error_class": e.error_class,
                "error_detail": e.error_detail,
                "source_excerpt": e.source_excerpt,
            }
            for e in result.errors
        ],
    }

    out_path = output_dir / f"{source_path.stem}.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {
        "stem": source_path.stem,
        "status": result.status,
        "rows": len(result.staging_rows),
        "errors": len(result.errors),
        "output": str(out_path).replace("\\", "/"),
    }


def main() -> None:
    """CLI entry."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--inputs",
        required=True,
        help="directory containing NRB BFI XLSX snapshots",
    )
    ap.add_argument(
        "--outputs",
        required=True,
        help="directory to write staging JSON files into",
    )
    ap.add_argument(
        "--glob",
        default="*.xlsx",
        help="glob pattern within --inputs (default: *.xlsx)",
    )
    args = ap.parse_args()

    inputs = Path(args.inputs)
    outputs = Path(args.outputs)

    files = sorted(inputs.glob(args.glob))
    if not files:
        print(f"[nrb_bfi.cli] no files matched {inputs}/{args.glob}")
        return

    totals: dict[str, int] = {"success": 0, "partial": 0, "failure": 0}
    total_rows = 0
    total_errors = 0
    for source in files:
        summary = emit_for_file(source, outputs)
        status = str(summary["status"])
        totals[status] = totals.get(status, 0) + 1
        rows_obj = summary["rows"]
        errors_obj = summary["errors"]
        assert isinstance(rows_obj, int)
        assert isinstance(errors_obj, int)
        total_rows += rows_obj
        total_errors += errors_obj
        row_count = rows_obj
        error_count = errors_obj
        print(
            f"  [{status:8s}] {summary['stem']:40s} "
            f"rows={row_count:>5}  errors={error_count:>3}"
        )

    print()
    print(f"files={len(files)}  rows={total_rows}  errors={total_errors}")
    print(f"status totals: {totals}")


if __name__ == "__main__":
    main()
