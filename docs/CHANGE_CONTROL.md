# Change Control — ADRs + Scope Change Log

How architectural decisions and scope shifts are documented. Without this, the project drifts and nobody remembers why.

---

## Two Different Things, Two Different Files

| Thing | Where it lives | Frequency | Format |
|-------|----------------|-----------|--------|
| **Architectural Decision Record (ADR)** | `docs/decisions/NNNN-<title>.md` | When a structural choice is made | Long-form, immutable once accepted |
| **Scope Change Log entry** | `docs/changes/CHANGELOG.md` | When project scope shifts vs. the strategy plan | Short, dated, links to ADR if applicable |

The ADR captures *what was decided and why*. The change log captures *that the project shifted from the original plan*.

---

## ADRs — Architecture Decision Records

### What gets an ADR

- A new tool, library, or service is adopted
- A schema decision is made (new entity, new constraint)
- A pattern is established that future code must follow
- A trade-off was made that future readers will question ("why didn't we just...")
- A free-tier service is replaced with a paid one
- An external API is depended on for a critical path

### What does NOT get an ADR

- Choosing variable names
- Picking a tailwind color
- Adding a small utility function
- Routine bug fixes
- One-off scripts

Rule of thumb: **if a future contributor 6 months from now would say "huh, why is it like this?" → ADR.**

### ADR Template

`docs/decisions/NNNN-<title>.md`:

```markdown
# ADR-NNNN: <Title in Title Case>

- **Status:** Proposed | Accepted | Superseded by ADR-NNNN | Deprecated
- **Date:** YYYY-MM-DD
- **Deciders:** Mother Opus, (user if escalated)
- **Tags:** db, security, ui, infra, etc.

## Context

What is the problem we are solving? What forces are at play? What constraints?

## Decision

What did we decide? One paragraph.

## Alternatives Considered

- **Option A:** description. Why rejected.
- **Option B:** description. Why rejected.
- **Option C (chosen):** description.

## Consequences

### Positive
- Bullet
- Bullet

### Negative
- Bullet
- Bullet

### Neutral / unknown
- Bullet

## References

- Strategy plan section: ...
- Related ADRs: ADR-NNNN
- External docs: ...
- Discussion: GitHub issue #N (if any)
```

### ADR Numbering

- Start at `0001`. Zero-padded to 4 digits.
- Numbers never reused. If an ADR is rejected at proposed stage, the number is still consumed (mark as `Rejected`).
- Filename: `0001-tech-stack.md`, `0002-drizzle-vs-prisma.md`, `0003-cloudflare-r2-archival-policy.md`.

### ADR Workflow

1. Mother (or user) recognizes the decision needs recording
2. `pnpm new-adr "<title>"` (script scaffolds the file with the next number)
3. Fill in Context + Alternatives Considered
4. Discuss with user if escalation criterion met
5. Decide
6. Mark as **Accepted**, fill in Decision + Consequences
7. Commit the ADR
8. Reference the ADR number in:
   - The PR that implements the decision
   - The CHANGELOG entry (if scope shifted)
   - Code comments where the decision is enforced (e.g., `// per ADR-0007`)

### ADR Immutability

Once **Accepted**, an ADR is **never edited** (except typos). If circumstances change:

- Write a new ADR
- The new ADR's status: `Accepted`, with header `Supersedes: ADR-NNNN`
- The old ADR's status changes to `Superseded by ADR-NNNN`
- That edit is the only edit allowed on a superseded ADR

This preserves the historical reasoning. Future readers see *what we thought then* and *why we changed our minds*.

---

## Scope Change Log

The strategy plan (`../.claude/plans/ok-i-want-to-mossy-dragonfly.md`) is the canonical specification of *what we are building*. The scope change log captures *where reality diverged from that spec and why*.

### When to add a change log entry

- A vertical is added, removed, deferred, or merged
- A killer product / signature utility is repositioned
- A 90-day roadmap milestone slips materially or is reordered
- A force / pillar / lens is added, renamed, or removed
- A vertical's first story changes
- A cadence target changes (Year 1 output, etc.)
- An audience priority shifts

### Format

`docs/changes/CHANGELOG.md` — append-only, reverse-chronological at the top:

```markdown
## 2026-06-05 — Soil Economy seeding pulled from Q4 → Q2

**What changed:** Soil Economy vertical (#13) seed phase moved from Q4 to Q2 based on existing Annapurna ground-truth data being production-ready.

**Why:** User has working topographical + GIS extraction already done; not using it wastes accumulated context.

**Plan section affected:** Strategy plan §"Year 1 Vertical Build Order" (Q2 column).

**Related:** ADR-0014 (geospatial library choice). Reverts no prior decision.

**Backward compatibility:** None — no code yet for this vertical.
```

Each entry is one short paragraph. Detail lives in the linked ADR.

### Audit Discipline

Mother audits the change log monthly:

- Are all entries consistent with the latest plan?
- Are there changes that should have been documented but weren't? (Cross-check git log; conventional commits with `BREAKING CHANGE` should have an entry.)
- Are any entries contradicted by later entries?

The change log is a living document. It should be readable as a narrative of how the project evolved.

---

## Pattern: Decision → ADR → Code → Reference

When a decision is implemented, the implementing code references the ADR:

```typescript
// per ADR-0007: source documents are immutable; new versions create new rows.
export async function archiveDocument(doc: SourceDocument) {
  // ...
}
```

Or at the file/folder level (in CLAUDE.md or a header comment):

```markdown
<!-- docs/CONVENTIONS.md §error-handling — per ADR-0003: typed errors only. -->
```

This makes the codebase self-documenting backwards into its decisions.

---

## ADRs to Write at Bootstrap (Day 1)

These decisions are already made — we just need to capture them formally:

| ADR | Title | Status at write time |
|-----|-------|---------------------|
| 0001 | Tech stack: Next.js 15 + TypeScript + Supabase + Drizzle + Cloudflare | Accepted |
| 0002 | Repository structure: single-repo with feature-domain folders | Accepted |
| 0003 | Typed errors only — neverthrow or tagged unions | Accepted |
| 0004 | Cloudflare R2 for source-document archival; immutable rows | Accepted |
| 0005 | Mother Opus + Sonnet workers orchestration model | Accepted |
| 0006 | Bilingual i18n: next-intl, `/en/` + `/ne/`; Cost of Leaving Nepal is bilingual Day 1 | Accepted |
| 0007 | Free-tier-first cloud stack; upgrade only on quota hit + ADR | Accepted |
| 0008 | Pagefind for static search | Accepted |
| 0009 | Conventional commits + squash merge to `main` | Accepted |
| 0010 | Fact Ledger schema: claims have A/B/C confidence; corrections immutable | Accepted |

These ADRs get written during the Day 1–3 bootstrap. They are short — most of the reasoning lives in the relevant `docs/` file; the ADR is the formal record.

---

## Anti-Pattern: Silent Decisions

The biggest project-killing pattern: **a decision was made implicitly by code without an ADR.**

Example: a Sonnet worker added `lodash` to the dependencies because it needed `debounce`. No ADR. Six months later we have lodash + ramda + native polyfills competing.

**Mother's job:** every PR review asks "is there an implicit decision in this diff?" If yes → ADR before merge.

---

## Naming Examples

Good ADR titles (concrete, decision-shaped):
- `0011-cloudflare-pages-vs-vercel.md`
- `0023-money-map-flow-confidence-thresholds.md`
- `0034-newsletter-double-opt-in-policy.md`

Bad ADR titles:
- `frontend.md` (too vague)
- `important-decision.md` (says nothing)
- `notes.md` (not a decision)

A good title alone tells you what the ADR is about.
