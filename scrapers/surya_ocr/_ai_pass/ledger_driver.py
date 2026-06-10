#!/usr/bin/env python3
"""Ledger driver — the nightly-loop substrate (Overnight AI-pass, build step 3).

The Master Recovery Ledger (`RECOVERY_LEDGER.json`) is the source of truth; this
CLI walks it in value order, emits dispatch-ready args for the
`ocr-table-recovery` Workflow, applies recovery results back, and writes the
morning report. The orchestrator (Mother, live, or `run_ai_pass_overnight.ps1`
unattended) calls these subcommands between Workflow runs.

**Recover + stage only — this never writes to the DB or the schema** (the five
hard rules; promotion is the human's, in the morning).

Run (stdlib only, Python 3.12, from repo root):

    # next batch of pending tables (value order), dispatch-ready:
    python scrapers/surya_ocr/_ai_pass/ledger_driver.py next --n 5 [--single-only] [--tier P0] [--max-pages 8]

    # apply a Workflow result to the ledger (status flow advances):
    python .../ledger_driver.py update --id P0_1d6841fe_p0079 --status recovered \
        --residual 0 --artifact _ai_pass/recovered/P0_1d6841fe_p0079 --note "..."

    # write the morning report:
    python .../ledger_driver.py report
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LEDGER = os.path.join(HERE, "RECOVERY_LEDGER.json")
OCR_ROOT = os.path.join(REPO_ROOT, "scrapers", "surya_ocr", "_ocr_output")
RECOVERED = os.path.join(HERE, "recovered")
REPORTS = os.path.join(HERE, "REPORTS")
PY = r"C:\Users\ACER\AppData\Local\Programs\Python\Python312\python.exe"

# status flow: pending -> scoped -> {recovered|quarantined|needs-decision} -> staged -> [promoted-by-human]
VALID_STATUSES = {"pending", "scoped", "recovered", "quarantined",
                  "needs-decision", "staged", "promoted"}
DONE_STATUSES = {"recovered", "quarantined", "staged", "promoted"}  # not re-dispatched


def load():
    with open(LEDGER, encoding="utf-8") as fh:
        return json.load(fh)


def save(ledger):
    with open(LEDGER, "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, ensure_ascii=False, indent=2)


def dispatch_args(t):
    """Build the ocr-table-recovery Workflow args for one ledger table."""
    out = os.path.join(RECOVERED, t["id"])
    return {
        "python": PY,
        "ocr_dir": os.path.join(OCR_ROOT, t["out_dir"]),
        "pdf_path": os.path.join(REPO_ROOT, t["source_path"].replace("/", os.sep)),
        "page_index": t["page_start"],          # back-compat single-page entry point
        "page_start": t["page_start"],
        "page_end": t["page_end"],
        "n_pages": t["n_pages"],
        "table_hint": t["table_hint"],
        "unit_hint": t["unit_hint"],
        "out_dir": out,
        "column_model": "opus",
    }


def cmd_next(args):
    ledger = load()
    rows = [t for t in ledger["tables"] if t["status"] == "pending"]
    if args.tier:
        rows = [t for t in rows if t["tier_code"] == args.tier]
    if args.single_only:
        rows = [t for t in rows if t["n_pages"] == 1]
    if args.max_pages:
        rows = [t for t in rows if t["n_pages"] <= args.max_pages]
    if not args.include_coarse:
        rows = [t for t in rows if not t["signals"]["coarse_run"]]
    rows = rows[: args.n]  # ledger is already value-ordered
    batch = [{
        "id": t["id"],
        "tier": t["tier_code"],
        "dedup": t["dedup"]["class"],
        "n_pages": t["n_pages"],
        "multipage": t["n_pages"] > 1,
        "numeric_lines": t["signals"]["numeric_lines"],
        "table_hint": t["table_hint"],
        "args": dispatch_args(t),
    } for t in rows]
    print(json.dumps(batch, ensure_ascii=False, indent=2))


def cmd_update(args):
    ledger = load()
    t = next((t for t in ledger["tables"] if t["id"] == args.id), None)
    if t is None:
        raise SystemExit(f"id not found: {args.id}")
    if args.status not in VALID_STATUSES:
        raise SystemExit(f"bad status: {args.status} (valid: {sorted(VALID_STATUSES)})")
    t["status"] = args.status
    if args.residual is not None:
        t["reconciliation_result"] = (
            f"reconciled (worst residual {args.residual})" if args.status in ("recovered", "staged")
            else f"NOT reconciled (residual {args.residual})")
    if args.recon is not None:
        t["reconciliation_result"] = args.recon
    if args.artifact is not None:
        t["artifact_path"] = args.artifact
    if args.note is not None:
        t["notes"] = args.note
    t["updated_utc"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    save(ledger)
    print(f"updated {args.id} -> {args.status}"
          + (f" | {t['reconciliation_result']}" if t.get("reconciliation_result") else ""))


def cmd_report(args):
    ledger = load()
    date = args.date or _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")
    os.makedirs(REPORTS, exist_ok=True)
    by = {}
    for t in ledger["tables"]:
        by.setdefault(t["status"], []).append(t)
    o = ledger["ocr_state"]

    def section(title, items, cols):
        out = [f"\n## {title} ({len(items)})\n"]
        if not items:
            out.append("\n_none_\n")
            return out
        out.append("\n| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n")
        for t in items:
            pg = t["page_start"] if t["page_start"] == t["page_end"] else f"{t['page_start']}–{t['page_end']}"
            row = {
                "id": f"`{t['id']}`", "doc": f"`{t['out_dir'][:30]}`", "page(s)": str(pg),
                "hint": t["table_hint"][:48], "recon": str(t.get("reconciliation_result") or ""),
                "artifact": f"`{t['artifact_path']}`" if t.get("artifact_path") else "",
                "dedup": t["dedup"]["class"], "note": t.get("notes", ""),
            }
            out.append("| " + " | ".join(row.get(c, "") for c in cols) + " |\n")
        return out

    md = [f"# Overnight AI-pass — morning report {date}\n",
          f"\n> Ledger: `RECOVERY_LEDGER.json` · Generated: "
          f"`{_dt.datetime.now(_dt.timezone.utc).isoformat(timespec='seconds')}`\n",
          f"\n**Recover + stage only — nothing was promoted. Promotion is yours.**\n",
          f"\n- OCR: {o['pages_present']:,}/{o['pages_target']:,} pages"
          f"{' (still in progress)' if o['in_progress'] else ''}\n",
          f"- Ledger progress: "
          + " · ".join(f"{k} {len(by.get(k, []))}" for k in
                       ["pending", "scoped", "recovered", "staged", "quarantined",
                        "needs-decision", "promoted"] if by.get(k))
          + "\n"]
    md += section("✅ READY TO PROMOTE (reconciled + staged)",
                  by.get("recovered", []) + by.get("staged", []),
                  ["id", "doc", "page(s)", "recon", "artifact", "hint"])
    # structural queue = items flagged needs-decision at scan time (dedup class)
    # OR surfaced during recovery (status); dedup by id, value order preserved.
    nd_seen, needs_decision = set(), []
    for t in ledger["tables"]:
        if (t["status"] == "needs-decision" or t["dedup"]["class"] == "needs-decision") \
                and t["id"] not in nd_seen and t["status"] not in ("staged", "promoted"):
            nd_seen.add(t["id"])
            needs_decision.append(t)
    md += section("⚠️ NEEDS DECISION (structural — escalated)", needs_decision,
                  ["id", "doc", "page(s)", "dedup", "note", "hint"])
    md += section("🟥 QUARANTINED (did not reconcile — never promote)", by.get("quarantined", []),
                  ["id", "doc", "page(s)", "recon", "hint"])
    path = os.path.join(REPORTS, f"{date}.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("".join(md))
    print(f"report -> {os.path.relpath(path, REPO_ROOT)}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Master Recovery Ledger driver.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("next", help="emit next pending tables (value order), dispatch-ready")
    p.add_argument("--n", type=int, default=5)
    p.add_argument("--tier", default=None)
    p.add_argument("--single-only", action="store_true", help="only n_pages==1 tables")
    p.add_argument("--max-pages", type=int, default=None)
    p.add_argument("--include-coarse", action="store_true")
    p.set_defaults(func=cmd_next)

    p = sub.add_parser("update", help="apply a recovery result to the ledger")
    p.add_argument("--id", required=True)
    p.add_argument("--status", required=True)
    p.add_argument("--residual", default=None)
    p.add_argument("--recon", default=None, help="free-text reconciliation_result override")
    p.add_argument("--artifact", default=None)
    p.add_argument("--note", default=None)
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("report", help="write the morning report")
    p.add_argument("--date", default=None)
    p.set_defaults(func=cmd_report)

    args = ap.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
