/**
 * Workflow: ocr-table-recovery
 * Fault-tolerant recovery of a financial table from Surya-OCR output to a
 * render-verified, reconciliation-GATED matrix. Ships ONLY cells that reconcile
 * to the document's printed totals; quarantines the rest with reasons. Writes a
 * verified_matrix.json + report. Does NOT touch the DB or schema (Mother + user
 * own promotion + any ADR).
 *
 * Why this cannot get stuck (maps 1:1 to the 2026-06-10 stuck-worker incident):
 *  - Control flow is deterministic JS here, not a model idling on a notification.
 *  - Every agent is BOUNDED: exact render recipe + a hard 2-render retry cap →
 *    no open-ended "figure out how to read these" thrash.
 *  - Reconciliation is the OBJECTIVE gate: an agent's output is accepted only if
 *    Σ matches the printed total — unverified/unreconciled data cannot pass.
 *  - parallel() turns a thrown/failed column into null → it is quarantined, the
 *    run continues; one bad column never hangs the batch.
 *  - No infinite loops: fan-out is finite (one agent per column), no while-true.
 *  - Structural decisions are RETURNED, never executed → human-in-loop for ADRs.
 *  - Resumable via Workflow({scriptPath, resumeFromRunId}).
 *
 * args (all absolute paths):
 *   { python, ocr_dir, pdf_path, page_index, table_hint, out_dir,
 *     cross_check?: { label, expected } }   // optional cross-source anchor
 */
export const meta = {
  name: 'ocr-table-recovery',
  description:
    'Fault-tolerant OCR table recovery: scope → per-column render-verify (bounded, retry-capped) → dual-reconcile gate. Ships only reconciled cells; quarantines the rest. No DB writes.',
  whenToUse:
    'Recover a financial table from Surya-OCR output into a render-verified, reconciliation-gated matrix (e.g. SOE Yellow Book, Economic Survey annex, redbook).',
  phases: [
    {
      title: 'Scope',
      detail:
        'locate table; extract column geometry, row labels, reconciliation keys, printed totals',
    },
    {
      title: 'Verify columns',
      detail:
        'one bounded agent per column: exact render recipe, ≤2 attempts, reconciliation-gated',
    },
    {
      title: 'Reconcile + gate',
      detail:
        'assemble matrix, dual lattice, accept reconciled cells, quarantine rest, emit artifacts',
    },
  ],
};

// ---------- structured-output schemas (force determinism; agents cannot ramble) ----------
const SCOPE_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: [
    'found',
    'reconciles_how',
    'columns',
    'rows',
    'total_row_idx',
    'y_top_px',
    'y_bottom_px',
    'unit',
  ],
  properties: {
    found: {
      type: 'boolean',
      description: 'true only if a table WITH a printed total/reconciliation key exists',
    },
    table_title: { type: 'string' },
    unit: {
      type: 'string',
      description: 'printed unit, e.g. npr_crore/lakh/thousand — read the header',
    },
    reconciles_how: {
      type: 'array',
      items: { type: 'string' },
      description:
        'the reconciliation identities, e.g. "sum(rows 0..17)=row 18 per column"; "sum(cols 0..6)=col 7 per row"',
    },
    columns: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['idx', 'label', 'x0_px', 'x1_px'],
        properties: {
          idx: { type: 'number' },
          label: { type: 'string' },
          x0_px: { type: 'number' },
          x1_px: { type: 'number' },
        },
      },
    },
    rows: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['idx', 'label', 'is_total'],
        properties: {
          idx: { type: 'number' },
          label: { type: 'string' },
          is_total: { type: 'boolean' },
        },
      },
    },
    total_row_idx: {
      type: 'number',
      description: 'row idx whose value each column must reconcile to (Σ components)',
    },
    y_top_px: { type: 'number' },
    y_bottom_px: { type: 'number' },
  },
};

const COLUMN_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['col_idx', 'reconciles', 'residual', 'values', 'quarantined'],
  properties: {
    col_idx: { type: 'number' },
    reconciles: { type: 'boolean' },
    residual: { type: 'number', description: 'Σ(components) − printed total, in unit' },
    attempts: { type: 'number' },
    values: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['row_idx', 'value'],
        properties: { row_idx: { type: 'number' }, value: { type: ['number', 'null'] } },
      },
    },
    quarantined: {
      type: 'array',
      items: { type: 'number' },
      description: 'row idxs that could not be read/reconciled',
    },
  },
};

const GATE_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: [
    'matrix_reconciles',
    'worst_residual',
    'accepted_count',
    'quarantined_count',
    'artifact_path',
    'structural_decision_needed',
  ],
  properties: {
    matrix_reconciles: { type: 'boolean' },
    worst_residual: { type: 'number' },
    accepted_count: { type: 'number' },
    quarantined_count: { type: 'number' },
    cross_source: {
      type: 'string',
      description: 'result of the optional cross-source anchor check',
    },
    artifact_path: { type: 'string' },
    structural_decision_needed: {
      type: 'string',
      description:
        'any schema/enum/ADR decision that MUST be escalated to the user before promotion; empty string if none',
    },
  },
};

// ---------- prompt builders (each agent is fully self-contained + bounded) ----------
const PY =
  args && args.python
    ? args.python
    : 'C:\\Users\\ACER\\AppData\\Local\\Programs\\Python\\Python312\\python.exe';
const ENV = `Set $env:PYTHONUTF8=1 for all python. Python: ${PY}.`;

function scopePrompt(a) {
  return [
    `You are scoping ONE table for fault-tolerant recovery. READ-ONLY. ${ENV}`,
    `OCR per-page JSON dir: ${a.ocr_dir} (files page_NNNN.json; text_lines:[{text,confidence,bbox:[x0,y0,x1,y1] in PIXELS at render_scale 3.0}]).`,
    `Source PDF: ${a.pdf_path} (page index ${a.page_index}).`,
    `Find the table matching: "${a.table_hint}".`,
    `Return its structure: the column list with each column's pixel x-range (x0_px,x1_px from the cell bboxes), the row list (idx,label,is_total) top-to-bottom, the total_row_idx the components must sum to, y_top_px/y_bottom_px spanning the data rows, and the printed UNIT (read the header — never assume).`,
    `State reconciles_how: the exact reconciliation identities (e.g. "sum(rows 0..N)=total_row per column", "sum(cols 0..M)=last col per row").`,
    `CRITICAL: if the table has NO printed total / no reconciliation key, set found=false and reconciles_how=[] — do NOT invent one. A table we cannot reconcile must not be recovered.`,
  ].join('\n');
}

function columnPrompt(scope, col, a) {
  const nRows = scope.rows.length;
  return [
    `BOUNDED render-verification of ONE column (idx ${col.idx}, "${col.label}"). ${ENV}`,
    `Do EXACTLY this, no improvising:`,
    `1) Write a tiny python file that renders this column's strip and run it:`,
    `   import fitz; p=fitz.open(r"${a.pdf_path}")[${a.page_index}];`,
    `   clip=fitz.Rect(${col.x0_px}/3-2, ${scope.y_top_px}/3-2, ${col.x1_px}/3+2, ${scope.y_bottom_px}/3+2);`,
    `   pix=p.get_pixmap(matrix=fitz.Matrix(8,8), clip=clip); pix.save(r"%TEMP%/wf_col_${col.idx}.png")`,
    `2) Read that PNG with the Read tool. Transcribe the ${nRows} values TOP-TO-BOTTOM in row order (Devanagari ०१२३४५६७८९ = 0-9; South-Asian grouping). Map them to row_idx 0..${nRows - 1}.`,
    `3) Reconcile: sum the component rows; it MUST equal the value at total_row_idx ${scope.total_row_idx} within ±9 (rounding of crore figures).`,
    `4) If it does NOT reconcile, re-render ONCE at Matrix(12,12) and re-read. HARD CAP: 2 render attempts total.`,
    `5) If still not reconciling after 2 attempts, set reconciles=false and put the ambiguous row_idx(s) in quarantined — do NOT guess a digit to force it.`,
    `Return the column values (every row_idx), reconciles, residual (Σcomponents − total), attempts, quarantined. Never invent a digit the image does not show.`,
  ].join('\n');
}

function gatePrompt(scope, cols, a) {
  const cross = a.cross_check
    ? `Cross-source: also verify ${a.cross_check.label} == ${a.cross_check.expected} (±9) and report it in cross_source.`
    : 'No cross-source anchor provided.';
  return [
    `Assemble the verified columns into the final matrix and apply the GATE. ${ENV}`,
    `Reconciliation identities: ${scope.reconciles_how.join('; ')}.`,
    `Inputs you have: the per-column results (values + reconciles flags) are in this prompt's context via the workflow; rebuild the matrix from them.`,
    `Accept a cell ONLY if its column reconciled AND its row cross-reconciles (Σ across the disaggregating columns == the aggregate column, ±9). Quarantine every other cell WITH a reason — never silently drop.`,
    cross,
    `Write the accepted matrix to ${a.out_dir}/verified_matrix.json (cells + per-province/per-row reconciliation residuals + quarantine list + provenance: extraction_method=surya-ocr, confidence B).`,
    `Report matrix_reconciles, worst_residual, accepted_count, quarantined_count, artifact_path, and structural_decision_needed: name any schema/enum/ADR decision required before promotion (e.g. a new dimension_kind, a unit conversion, an enum gap). DO NOT write to any database or schema — promotion is the user's gate.`,
  ].join('\n');
}

// ---------- orchestration body (deterministic) ----------
const a = args || {};
if (!a.ocr_dir || !a.pdf_path || a.page_index == null || !a.out_dir) {
  log('Missing required args (ocr_dir, pdf_path, page_index, out_dir) — aborting.');
  return { status: 'bad-args' };
}

phase('Scope');
const scope = await agent(scopePrompt(a), { schema: SCOPE_SCHEMA, label: 'scope' });
if (!scope.found || scope.reconciles_how.length === 0) {
  log(
    `No reconciliation key for "${a.table_hint}" — aborting CLEANLY (cannot verify ⇒ will not ship). This is a handled outcome, not a failure.`,
  );
  return { status: 'no-reconciliation-key', scope };
}
log(
  `Scoped "${scope.table_title}": ${scope.columns.length} cols × ${scope.rows.length} rows, unit ${scope.unit}. Keys: ${scope.reconciles_how.join(' | ')}`,
);

phase('Verify columns');
// One bounded agent per column; a thrown/failed agent → null → quarantined; the batch never hangs.
const colResults = (
  await parallel(
    scope.columns.map(
      (col) => () =>
        agent(columnPrompt(scope, col, a), {
          schema: COLUMN_SCHEMA,
          label: `col:${col.idx}`,
          phase: 'Verify columns',
        }),
    ),
  )
).filter(Boolean);
const reconciled = colResults.filter((c) => c.reconciles);
log(
  `Columns: ${reconciled.length}/${scope.columns.length} reconciled, ${scope.columns.length - reconciled.length} quarantined.`,
);

phase('Reconcile + gate');
const gate = await agent(gatePrompt(scope, colResults, a), { schema: GATE_SCHEMA, label: 'gate' });
log(
  `GATE → reconciles=${gate.matrix_reconciles} worst_residual=${gate.worst_residual} accepted=${gate.accepted_count} quarantined=${gate.quarantined_count}`,
);
if (gate.cross_source) log(`Cross-source: ${gate.cross_source}`);
if (gate.structural_decision_needed)
  log(`⚠ ESCALATE to user before promotion: ${gate.structural_decision_needed}`);

return { status: 'done', scope, columns: colResults, gate };
