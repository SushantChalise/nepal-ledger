# ADR-0003: AI-Assisted Parsing Policy (Claude CLI as Dev Assistant, Not Production API)

- **Status:** Accepted
- **Date:** 2026-05-13
- **Deciders:** Mother Opus, user
- **Tags:** ai, parsing, ingestion, security, cost

## Context

The Nepal Ledger data pipeline ingests Nepal government PDFs, CSVs, and Excel sheets (NRB CMEFs, customs trade data, PDMO bulletins, etc.). The temptation, in 2026, is to throw every parsing problem at Claude or another LLM via an API and let the model extract structured data from messy government documents.

Constraints making this not the right Year 1 path:

1. **No Anthropic API key in scope.** The user has Claude.ai subscription access (Claude CLI + Code) but not API access.
2. **Production cost.** Even with an API key, calling Claude on every monthly ingestion has a non-zero cost the prototype shouldn't carry.
3. **Reproducibility.** LLM outputs vary by prompt, by model version, by retry. A Fact Ledger built on non-reproducible parses is structurally weak.
4. **Audit trail.** Every ingested value needs to be re-derivable from the source document. "Claude said so" is not a citation a Fact Ledger should rest on.
5. **The senior-data-engineer pattern works.** Claude CLI sitting beside a human developer is highly effective for parser design, debugging, edge-case discovery, and review — without taking on the cost or reproducibility burden of API calls in production.

## Decision

**Year 1 production ingestion is deterministic Python only.** No Claude or LLM API calls at request time, at scrape time, or at validation time.

**Claude CLI / Claude Code (Sonnet 4.6, via the user's Claude.ai subscription) is used as a local development assistant**, in roles a senior data engineer would play sitting beside the developer:

- Designing parsers (table structure, regex patterns, edge cases)
- Inspecting parser failures and proposing fixes
- Generating extraction rules from observed PDF layouts
- Reviewing parser output before promotion to approved tables
- Generating test fixtures from real source documents
- Writing boilerplate (Drizzle schemas, Zod types, repository functions)
- Explaining weird document layouts the parser missed

The human keystroke is what promotes data from staging to approved. Not an LLM confidence score.

## Alternatives Considered

### Option A: Claude API for production parsing
- **Pro:** Handles ambiguous PDFs that deterministic parsers fail on; faster initial iteration.
- **Con:** Requires API key (not in scope); cost per ingestion; non-reproducible without strict prompt/version logging; audit trail is weak.
- Rejected for Year 1. Re-evaluated when an API key is in scope, with the gating requirements in [CLOUD_STACK.md](../CLOUD_STACK.md) §"AI-Assisted Parsing Policy".

### Option B: No LLM at all
- **Pro:** Maximally reproducible; cheapest.
- **Con:** Slower developer iteration; harder to debug PDF layout edge cases.
- Rejected — Claude CLI as a dev assistant captures most of the productivity benefit at zero production cost.

### Option C (chosen): Claude CLI as dev assistant, deterministic Python as parser of record
- **Pro:** Zero production cost. Full reproducibility. Strong audit trail. Claude CLI productivity for the developer.
- **Con:** Some PDFs may take longer to crack initially. Mitigated by Claude CLI helping design the parser.

## Consequences

### Positive
- Every approved indicator value is reproducible from source document + parser version
- Zero ongoing AI cost in production
- Fact Ledger claims rest on a deterministic chain
- Human-in-the-loop for ambiguous parses (the right pattern for a Fact Ledger)
- Claude CLI provides ~80% of the productivity benefit of API parsing at 0% of the cost

### Negative
- Parsers take longer to write initially (deterministic Python vs. "ask Claude to extract this")
- PDFs with non-tabular text (prose explanations interleaved with numbers) are harder
- Mitigation: lean on Claude CLI heavily during parser *design*; production parser is just Python

### Neutral / unknown
- If a sufficiently-funded later phase decides to add API parsing, the gating in [CLOUD_STACK.md](../CLOUD_STACK.md) covers the prerequisites (budget cap, ADR, reproducibility logging)

## Implementation Notes

- Every parser lives at `scrapers/<source-id>/parser.py`
- Parser version is tracked in `parser_runs.parser_version` and `approved_indicator_values.parser_version`
- Test fixtures live at `scrapers/<source-id>/fixtures/`
- See [PARSING_WORKFLOW.md](../PARSING_WORKFLOW.md) for the day-to-day workflow

## References

- [CLOUD_STACK.md §"AI-Assisted Parsing Policy"](../CLOUD_STACK.md)
- [PARSING_WORKFLOW.md](../PARSING_WORKFLOW.md)
- [DATA_PIPELINE.md](../DATA_PIPELINE.md)
- [SOURCE_REGISTRY.md](../SOURCE_REGISTRY.md)
