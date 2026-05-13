# Parsing Workflow — Claude CLI as Senior Data Engineer

This is the day-to-day workflow for writing parsers when a new source document arrives. Doctrine context: [ADR-0003](decisions/0003-ai-assisted-parsing-policy.md) — production stays deterministic; Claude CLI accelerates development.

---

## The Model

> Claude CLI sits beside you like a senior data engineer. It does not parse documents in production. It helps you write the Python parser that does.

Hard rules:
- **Production parsers are pure Python** (pdfplumber, pandas, openpyxl, csv, regex). No LLM calls at scrape time.
- **Claude CLI helps with parser design, debugging, review, and test generation.** Not with the parse-of-record.
- **Every approved row** is reproducible by running the deterministic parser against the archived source document.

---

## End-to-End Workflow (per new source document)

### 1. Acquire and archive the source

```powershell
# From the repo root
python scrapers/fetch.py --source nrb-cmefs-monthly --period 2082-83-9m
# Downloads to source-data/nrb/<filename>.pdf
# Computes sha256, writes to source_documents row, uploads to Supabase Storage
```

(For the first sources, `source-data/` already has the existing CSV + PDFs — the fetch step is a no-op for those.)

### 2. Inspect with Claude CLI

Open Claude CLI in the repo. Paste the source document path. Ask:

```
I have a new source document at source-data/nrb/CMEFs_Eng_Nine-Months_2082.83.pdf.
Read pages 3–8 (the table sections). Describe:
1. What tables are present and what each one reports.
2. Column structure and any merged/nested headers.
3. Footnotes that change interpretation.
4. Anything that looks like it changed from prior years' format.
Don't write code yet — just the inventory.
```

Claude reads the PDF text and returns a structured inventory. You use this to scope what the parser needs to extract.

### 3. Generate parser scaffold

Continue in Claude CLI:

```
Based on that inventory, scaffold scrapers/nrb/cmefs/parser.py.

Constraints:
- Use pdfplumber for table extraction.
- Match the schema in src/lib/db/schema/data-pipeline.ts (paste relevant fields).
- All output goes to staging_indicator_values via a ParserResult dataclass.
- Read calendar/period rules from docs/CALENDAR_AND_PERIODS.md.
- Confidence grade default: A (NRB published values).
- Parser version: 1.0.0.
- Idempotent: same input → same output.
- No network calls.
```

Claude returns a parser draft. **You read it carefully** before committing — not because Claude is wrong, but because the parser is the parser of record.

### 4. Build a fixture

Take 1–3 representative pages from the source PDF and save:

```
scrapers/nrb/cmefs/fixtures/
├── 2082-83-9m.pdf              # the actual source page
└── 2082-83-9m.expected.json    # what the parser should produce
```

Use Claude CLI to generate the `.expected.json` by reading the PDF and writing the expected structured output. **You manually verify** a sample of rows against the source. This is the "human keystroke" gate.

### 5. Write tests

```
Write Vitest cases in scrapers/nrb/cmefs/tests/parser.test.ts
that run parse_cmefs.py against fixtures/2082-83-9m.pdf
and assert equality with fixtures/2082-83-9m.expected.json.
Include cases for:
- All 23 NCPI subcategories present
- Rural/urban/overall splits present
- Period parsing (BS + AD) correct
- YoY and MoM deltas match expected
- Confidence grade = A for all rows
```

Claude writes the test scaffold. You run `pnpm test scrapers/nrb/cmefs/` and verify.

### 6. Run the parser, review staging output

```powershell
python scrapers/nrb/cmefs/parser.py source-data/nrb/CMEFs_Eng_Nine-Months_2082.83.pdf
# Writes to staging_indicator_values
```

Then in Claude CLI:

```
Read the staging rows for source_document_id <id>.
Spot-check 5 random rows against the source PDF table.
Flag any that look wrong.
```

Claude does the cross-reference for you (PDF page + staging row) and lists discrepancies. You inspect each one manually. This is the second human gate.

### 7. Promote to approved

```powershell
python scrapers/promote.py --source-document <id>
# Runs validation (DATA_PIPELINE.md), promotes passing rows to approved_indicator_values
# Anything failing validation lands in data_quality_flags
```

Review any blocked rows in the `data_quality_flags` table. For each: fix and re-promote, or write an override with a reason.

### 8. Commit

```powershell
git add scrapers/nrb/cmefs/
git commit -m "feat(scrapers/nrb-cmefs): initial parser v1.0.0 for nine-month report"
```

The parser, fixtures, tests, and (if newly registered) the source registry row all land in the same commit.

---

## When Claude CLI Disagrees With What You See

The parser is the source of truth for what gets ingested. Claude CLI might:

- Misread a merged column header
- Hallucinate a row that isn't in the PDF
- Misclassify a footnote as a data point

When this happens:
1. Trust the source PDF. Open it and look.
2. Fix the parser (deterministic Python) to handle the case correctly.
3. Add a fixture case that pins the correct behavior.
4. Do NOT add "Claude said this" as a justification anywhere.

Claude CLI is the assistant, not the authority. The source PDF + the parser code + the fixture are the authority.

---

## Anti-Patterns (What This Workflow Prevents)

| Pattern | Why it's bad | The workflow's response |
|---------|--------------|------------------------|
| "Let Claude API parse the PDF at ingestion time" | Cost, reproducibility, audit-trail failure | Production parser is Python only (ADR-0003) |
| "Trust Claude's extraction without checking the fixture" | LLM hallucination silently lands in approved data | Fixture + manual sample check is mandatory |
| "Update the parser without bumping version" | Old-and-new rows in the same indicator with different extraction logic | `parser_version` is required; revision flow handles bumps |
| "Edit fixture .expected.json to match new parser output" | Breaks the test as a regression check | Bump parser version + add a NEW fixture for the new format; keep the old one |
| "Skip the staging table, write straight to approved" | Bypasses validation; bad data lands publicly | Pipeline enforces staging → validation → approved (DATA_PIPELINE.md) |

---

## Per-Source Workflow Files

For each registered source, the workflow expects:

```
scrapers/<source-id>/
├── README.md              # how to fetch + parse this source manually
├── parser.py              # the parser of record
├── fetch.py               # downloads + archives to Supabase Storage
├── fixtures/              # sample inputs + expected outputs
│   ├── <period>.pdf
│   └── <period>.expected.json
├── tests/
│   └── parser.test.ts     # Vitest / pytest cases
└── notes.md               # observed edge cases, format changes per fiscal year, etc.
```

`notes.md` is where you (with Claude CLI's help) record "the FY 2081/82 PDF added a new column we ignored; FY 2082/83 reorganized totals; the parser handles both via version 1.0 (FY ≤ 2081) and 1.1 (FY ≥ 2082)."

---

## Cross-Reference

- [ADR-0003](decisions/0003-ai-assisted-parsing-policy.md) — the policy this workflow implements
- [DATA_PIPELINE.md](DATA_PIPELINE.md) — staging → validation → approved details
- [SOURCE_REGISTRY.md](SOURCE_REGISTRY.md) — registry workflow per source
- [CALENDAR_AND_PERIODS.md](CALENDAR_AND_PERIODS.md) — how the parser populates date/period fields
- [CONVENTIONS.md §"Testing"](CONVENTIONS.md) — Vitest patterns
