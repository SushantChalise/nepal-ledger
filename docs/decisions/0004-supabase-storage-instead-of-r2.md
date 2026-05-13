# ADR-0004: Supabase Storage for Source-Document Archive (Cloudflare R2 Deferred)

- **Status:** Accepted
- **Date:** 2026-05-13
- **Deciders:** Mother Opus, user
- **Tags:** infra, storage, archival, free-tier

## Context

[ADR-0001](0001-tech-stack.md) chose Cloudflare R2 as object storage for the source-document archive (NRB CMEFs PDFs, customs Excel files, OAG audit reports, etc.). R2's killer feature is zero egress fees, which would be ideal for serving archived PDFs publicly.

**Constraint surfaced at bootstrap:** Cloudflare R2 requires a payment method on file even for the free tier. The user does not want to enter a credit card during the prototype phase.

This creates a real Day-1 blocker for the original choice. We need object storage that:
1. Requires no credit card
2. Is in our existing free-tier stack (no new accounts)
3. Survives ~6–12 months of source-document archiving at current ingestion volume
4. Has a clean migration path to R2 when a payment method is on file

## Decision

**Supabase Storage** for the Year 1 prototype. Same Supabase project as the database; same API keys; no separate account; no card required.

When the user is ready to add a payment method (or revenue starts), migrate to Cloudflare R2 per the path in [CLOUD_STACK.md §"Cloudflare R2 (Phase 2)"](../CLOUD_STACK.md).

## Alternatives Considered

### Option A: Cloudflare R2 (the v5 plan)
- **Pro:** zero egress, 10GB free, S3-compatible, native to Cloudflare Workers
- **Con:** requires credit card on file even for free tier
- Deferred to Phase 2

### Option B: GitHub LFS
- **Pro:** no card, 1GB free, lives next to the code
- **Con:** awkward content-addressing for non-code files; LFS-bandwidth costs once we exceed free quota; not designed for monthly PDF archives
- Rejected

### Option C: Backblaze B2
- **Pro:** 10GB free, S3-compatible
- **Con:** requires card (similar to R2); extra account to manage; another vendor surface
- Rejected

### Option D (chosen): Supabase Storage
- **Pro:** included in the Supabase free tier we already use; no card; same auth keys; 1GB storage; 5GB egress shared with the database; S3-compatible API for clean migration
- **Con:** 1GB is smaller than R2's 10GB; egress isn't zero (shared 5GB/month pool with DB queries)
- Chosen because the cons don't bite for at least 6–12 months and the migration path to R2 is clean

## Consequences

### Positive
- Zero Day-1 friction. No card. No new account.
- Source documents and the `source_documents` table live in the same project — operationally clean
- Same API keys (Supabase URL + service-role key) cover both database and storage
- 1GB sufficient for ~6–12 months of monthly source archiving at current volume (10–20 PDFs/month, 5–30MB each)
- S3-compatible API means the parser/Fact Ledger code paths work identically when we swap to R2 later

### Negative
- 1GB is tighter than R2's 10GB free — eventual migration to R2 is when, not if
- Supabase egress (5GB/month) is shared between DB queries and Storage downloads — high public-PDF traffic could pressure that quota faster than R2 would
- If we hit either limit before adding a payment method, we have to optimize (compress PDFs, paginate Storage to GitHub Releases) rather than upgrade

### Neutral / unknown
- Whether Supabase Storage's S3 compatibility is identical enough that the migration to R2 is genuinely a client swap (expected yes; verify when migration happens)
- Latency: Supabase Storage on Singapore region serves Nepal/diaspora roughly comparable to R2

## Implementation Notes

- Bucket name: `source-archive` inside the existing Supabase project
- Access pattern: server-side only (via service-role key from GitHub Actions scrapers); public-read URLs minted on-demand for Fact Ledger links
- Key format: `<source_id>/<yyyy-mm-dd>/<original-filename>` (same as R2 plan)
- Hash recorded in `source_documents.file_hash_sha256`
- Stored content-addressed: once a file with the same hash is uploaded, we link the new `source_documents` row to the existing object instead of reuploading
- `source_documents.storage_provider` column added — value `'supabase'` during Year 1, switches to `'r2'` per-row during migration

## Migration Trigger

Move to R2 when ANY of:
1. Supabase Storage usage exceeds 800MB
2. Supabase egress exceeds 3.5GB/month for 2 consecutive months
3. Public PDF traffic pattern emerges (linked from a viral Fact Ledger story)
4. User adds a credit card for any reason

## References

- [CLOUD_STACK.md §"Supabase Storage"](../CLOUD_STACK.md)
- [CLOUD_STACK.md §"Cloudflare R2 (Phase 2)"](../CLOUD_STACK.md)
- [DATA_PIPELINE.md](../DATA_PIPELINE.md) — `source_documents` table
- [SOURCE_REGISTRY.md](../SOURCE_REGISTRY.md) — archive policy per source
- [ADR-0001](0001-tech-stack.md) — original stack
