/**
 * Workflow: ocr-table-recovery-multipage
 * Multi-page extension of ocr-table-recovery for ROW-IDENTITY tables that span a
 * page range with a single printed GRAND TOTAL — the intergovernmental fiscal
 * transfers (Σ grant columns = जम्मा per local level; Σ753 local levels = the
 * printed स्थानीय तह total) and redbook budget detail (recurrent+capital=total
 * per head; heads sum to the appropriation total).
 *
 * Same trust model as the single-page workflow: bounded agents, exact render
 * recipe, retry-capped, reconciliation is the OBJECTIVE gate, only reconciled
 * cells ship, structural decisions are RETURNED not executed, NO DB writes.
 *
 * Two reconciliation axes (both must hold for a cell to ship):
 *   (R) ROW identity  : Σ(part_cols) = aggregate_col, per data row   [local, strong]
 *   (G) GRAND total   : Σ(all data rows) = the printed grand-total row, per col [global]
 * Subtotal rows (province/group) are carried + used as bonus cross-checks.
 *
 * args (absolute paths):
 *   { python, ocr_dir, pdf_path, page_start, page_end, table_hint, out_dir,
 *     unit_hint?, column_model?, grand_total_cross_check?: { label, expected } }
 */
export const meta = {
  name: 'ocr-table-recovery-multipage',
  description:
    'Multi-page OCR table recovery for row-identity tables (intergovernmental transfers, redbook budget): per-page scope → per-(page,column) render-verify → row-identity repair → grand-total gate across pages. Ships only reconciled rows; no DB writes.',
  whenToUse:
    'Recover a financial table that spans MANY pages with a per-row identity (Σ components = row total) and ONE printed grand total (e.g. intergovernmental fiscal transfers, redbook budget detail).',
  phases: [
    {
      title: 'Scope pages',
      detail:
        'scope each page: columns, rows (data/subtotal/grandtotal), geometry, the row identity',
    },
    {
      title: 'Verify columns',
      detail:
        'one bounded agent per (page,column): exact render recipe, retry-capped, read every row',
    },
    {
      title: 'Row-identity repair',
      detail: 'localize cells that break Σ(parts)=aggregate per row; render-confirm',
    },
    {
      title: 'Grand-total gate',
      detail:
        'Σ rows = printed grand total per column; accept reconciled rows, quarantine rest; emit matrix',
    },
  ],
};

// ---------- schemas ----------
const PAGE_SCOPE_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: [
    'found',
    'page',
    'unit',
    'columns',
    'rows',
    'y_top_px',
    'y_bottom_px',
    'row_identity',
    'grand_total_row_idx',
  ],
  properties: {
    found: { type: 'boolean', description: 'true if this page carries rows of the target table' },
    page: { type: 'number' },
    unit: {
      type: 'string',
      description: 'printed unit — read the header; "" if not printed on this page',
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
        required: ['idx', 'label', 'kind'],
        properties: {
          idx: { type: 'number', description: 'row index on THIS page, top-to-bottom from 0' },
          label: { type: 'string', description: 'row label (entity / head / subtotal name)' },
          kind: {
            type: 'string',
            enum: ['data', 'subtotal', 'grandtotal', 'header'],
            description:
              'data=leaf; subtotal=group sum; grandtotal=the document total; header=skip',
          },
          group: {
            type: 'string',
            description: 'subtotal-group label this row belongs to (e.g. province), "" if none',
          },
        },
      },
    },
    y_top_px: { type: 'number' },
    y_bottom_px: { type: 'number' },
    row_identity: {
      type: 'object',
      additionalProperties: false,
      required: ['aggregate_col', 'part_cols'],
      description:
        'the per-row identity Σ(part_cols)=aggregate_col (e.g. aggregate=जम्मा col, parts=the grant cols). aggregate_col=-1 if the table has no per-row total.',
      properties: {
        aggregate_col: { type: 'number' },
        part_cols: { type: 'array', items: { type: 'number' } },
      },
    },
    grand_total_row_idx: {
      type: 'number',
      description: 'idx of the printed grand-total row on THIS page, or -1',
    },
  },
};

const COLUMN_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['page', 'col_idx', 'values', 'low_conf_rows'],
  properties: {
    page: { type: 'number' },
    col_idx: { type: 'number' },
    values: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['row_idx', 'value'],
        properties: { row_idx: { type: 'number' }, value: { type: ['number', 'null'] } },
      },
    },
    low_conf_rows: {
      type: 'array',
      items: { type: 'number' },
      description: 'row idxs that stayed low-confidence after retry',
    },
  },
};

const GATE_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: [
    'grand_total_reconciles',
    'worst_residual',
    'accepted_rows',
    'quarantined_rows',
    'artifact_path',
    'structural_decision_needed',
  ],
  properties: {
    grand_total_reconciles: { type: 'boolean' },
    worst_residual: { type: 'number' },
    accepted_rows: { type: 'number' },
    quarantined_rows: { type: 'number' },
    grand_total_cross_check: { type: 'string' },
    artifact_path: { type: 'string' },
    structural_decision_needed: {
      type: 'string',
      description: 'schema/enum/ADR decision to escalate before promotion; "" if none',
    },
  },
};

// ---------- env + prompts ----------
let a = args || {};
if (typeof a === 'string') {
  try {
    a = JSON.parse(a);
  } catch (e) {
    return { status: 'bad-args', received: String(a).slice(0, 200) };
  }
}
const PY = a.python || 'C:\\Users\\ACER\\AppData\\Local\\Programs\\Python\\Python312\\python.exe';
const ENV = `Set $env:PYTHONUTF8=1 for all python. Python: ${PY}.`;

function pageScopePrompt(pageIdx) {
  return [
    `You are scoping ONE page of a MULTI-PAGE financial table for fault-tolerant recovery. READ-ONLY. ${ENV}`,
    `OCR per-page JSON dir: ${a.ocr_dir} (page_${String(pageIdx).padStart(4, '0')}.json; text_lines:[{text,confidence,bbox:[x0,y0,x1,y1] in PIXELS at render_scale 3.0}]).`,
    `Source PDF: ${a.pdf_path}, page index ${pageIdx}.`,
    `The overall table is: "${a.table_hint}".`,
    `Return THIS page's structure: columns (idx left-to-right, label, pixel x0_px/x1_px from cell bboxes), rows (idx top-to-bottom from 0, label, kind: data|subtotal|grandtotal|header, and group = the subtotal-group label a data/subtotal row belongs to e.g. the province name), y_top_px/y_bottom_px spanning the data rows, the printed unit (read the header; "" if not on this page).`,
    `row_identity: the per-row identity Σ(part_cols)=aggregate_col — e.g. aggregate_col = the जम्मा/Total column idx, part_cols = the component (grant / recurrent+capital) column idxs. Set aggregate_col=-1 if this table has no per-row total column.`,
    `grand_total_row_idx: the idx of the printed DOCUMENT grand-total row if it appears on THIS page (e.g. स्थानीय तह / कुल जम्मा), else -1.`,
    `Set found=false if this page carries no rows of the target table (divider/notes/blank). Never invent structure.`,
  ].join('\n');
}

function columnPrompt(pageScope, col) {
  const nRows = pageScope.rows.length;
  return [
    `BOUNDED render-verification of ONE column on ONE page. page=${pageScope.page}, column idx ${col.idx} ("${col.label}"). Return page=${pageScope.page}, col_idx=${col.idx}. ${ENV}`,
    `Do EXACTLY this, no improvising:`,
    `1) Write+run a tiny python file rendering this column's strip:`,
    `   import fitz; p=fitz.open(r"${a.pdf_path}")[${pageScope.page}];`,
    `   clip=fitz.Rect(${col.x0_px}/3-2, ${pageScope.y_top_px}/3-2, ${col.x1_px}/3+2, ${pageScope.y_bottom_px}/3+2);`,
    `   pix=p.get_pixmap(matrix=fitz.Matrix(8,8), clip=clip); pix.save(r"%TEMP%/wf_mp_${pageScope.page}_${col.idx}.png")`,
    `2) Read that PNG. Transcribe the ${nRows} values TOP-TO-BOTTOM mapping to row_idx 0..${nRows - 1} (Devanagari ०१२३४५६७८९=0-9; South-Asian lakh/crore grouping; a blank/dash cell = null).`,
    `3) For any cell you are <0.9 sure of, re-render JUST that row at higher zoom (Matrix(14,14) then (18,18) on a tight crop) and re-read. Common confusions: ५/8↔८/5, ९/9↔१/1, ०/0↔६/6.`,
    `4) Return values for EVERY row_idx, and low_conf_rows = any row still uncertain. Never invent a digit the image does not show; leave genuinely-illegible cells as null and list them in low_conf_rows.`,
  ].join('\n');
}

function repairPrompt(pageScope, col, suspects) {
  return [
    `CROSS-COLUMN REPAIR of column idx ${col.idx} ("${col.label}") on page ${pageScope.page}. Return page=${pageScope.page}, col_idx=${col.idx}. ${ENV}`,
    `The row identity Σ(parts)=aggregate localized these suspect cells in this column:`,
    ...suspects.map(
      (s) =>
        `  row ${s.row_idx} ("${s.label}"): OCR read=${s.read}; identity implies ≈ ${s.implied != null ? s.implied : '(ambiguous)'}`,
    ),
    `For EACH suspect row, render JUST that cell at high zoom and READ the printed Devanagari digits — the printed page is the sole truth; "implies" is only a hint for where to look.`,
    `Recipe per suspect row: rowY = ${pageScope.y_top_px} + row_idx*(${pageScope.y_bottom_px}-${pageScope.y_top_px})/${pageScope.rows.length}; import fitz; p=fitz.open(r"${a.pdf_path}")[${pageScope.page}]; pix=p.get_pixmap(matrix=fitz.Matrix(18,18), clip=fitz.Rect(${col.x0_px}/3-3, rowY/3-2, ${col.x1_px}/3+3, rowY/3+7)); save; Read it.`,
    `Return the FULL column values for page ${pageScope.page} (your confirmed corrections + unchanged others) and low_conf_rows (any still illegible — never guess).`,
  ].join('\n');
}

function gatePrompt(unit) {
  return [
    `Assemble the verified multi-page columns into ONE matrix and apply the GRAND-TOTAL gate. ${ENV}`,
    `The workflow has reconciled the per-row identity already; you finalize the global gate + artifact.`,
    `Accept a data row ONLY if its row-identity held (Σ parts = aggregate, ±tolerance). The matrix of accepted values, the printed grand-total row, and per-row residuals are provided in context — rebuild from them.`,
    `Check the GRAND total: Σ(accepted data-row values) per column == the printed grand-total row value (±9 for crore rounding, ±0 if unit is lakh/thousand integers). Report worst_residual.`,
    a.grand_total_cross_check
      ? `Cross-check: also verify ${a.grand_total_cross_check.label} == ${a.grand_total_cross_check.expected} and report in grand_total_cross_check.`
      : 'No external grand-total cross-check provided.',
    `Write the accepted matrix to ${a.out_dir}/verified_matrix.json (rows with label+group+per-column values; the grand-total row; per-row + grand-total residuals; quarantine list with reasons; provenance: source_pdf, page_start=${a.page_start}, page_end=${a.page_end}, unit="${unit}", extraction_method="surya-ocr", confidence_grade "B"). Quarantine — never silently drop — any row whose identity failed or whose cells stayed illegible.`,
    `Report grand_total_reconciles, worst_residual, accepted_rows, quarantined_rows, artifact_path, and structural_decision_needed (e.g. "intergovernmental uses 4 AGGREGATE grant types not the schema's 8 atomic — needs an enum ADR"; "" if none). DO NOT write to any database or schema.`,
  ].join('\n');
}

// ---------- orchestration ----------
if (!a.ocr_dir || !a.pdf_path || a.page_start == null || a.page_end == null || !a.out_dir) {
  return { status: 'bad-args', got: JSON.stringify(a).slice(0, 300) };
}
const pages = [];
for (let p = a.page_start; p <= a.page_end; p++) pages.push(p);
log(
  `Multi-page recovery: pages ${a.page_start}..${a.page_end} (${pages.length}), out ${a.out_dir}`,
);

phase('Scope pages');
const scopes = (
  await parallel(
    pages.map(
      (p) => () =>
        agent(pageScopePrompt(p), {
          schema: PAGE_SCOPE_SCHEMA,
          label: `scope:${p}`,
          phase: 'Scope pages',
          model: a.column_model || 'opus',
        }),
    ),
  )
)
  .filter(Boolean)
  .filter((s) => s.found);
if (!scopes.length) {
  log('No page carried the target table — aborting cleanly.');
  return { status: 'no-table', pages: a.page_start + '..' + a.page_end };
}
const canonicalIdentity =
  (scopes.find((s) => s.row_identity && s.row_identity.aggregate_col >= 0) || {}).row_identity ||
  null;
const unit = a.unit_hint || (scopes.find((s) => s.unit) || {}).unit || '';
const grandPage = scopes.find((s) => s.grand_total_row_idx >= 0) || null;
log(
  `Scoped ${scopes.length} pages; unit=${unit}; row_identity=${canonicalIdentity ? `Σ[${canonicalIdentity.part_cols}]=col${canonicalIdentity.aggregate_col}` : 'none'}; grand total on page ${grandPage ? grandPage.page : 'NOT FOUND'}.`,
);
if (!canonicalIdentity && !grandPage) {
  log(
    'No row identity AND no grand total → cannot reconcile; aborting (will not ship unverifiable data).',
  );
  return { status: 'no-reconciliation-key', scopes: scopes.map((s) => s.page) };
}

phase('Verify columns');
// fan out one bounded agent per (page, column)
const colTasks = [];
for (const s of scopes) for (const col of s.columns) colTasks.push({ s, col });
let colResults = (
  await parallel(
    colTasks.map(
      ({ s, col }) =>
        () =>
          agent(columnPrompt(s, col), {
            schema: COLUMN_SCHEMA,
            label: `col:${s.page}.${col.idx}`,
            phase: 'Verify columns',
            model: a.column_model || 'opus',
          }),
    ),
  )
).filter(Boolean);
log(`Read ${colResults.length}/${colTasks.length} (page,column) cells.`);

// index: byPage[page][col_idx] = {row_idx: value}
const byPage = {};
for (const cr of colResults) {
  (byPage[cr.page] = byPage[cr.page] || {})[cr.col_idx] = Object.fromEntries(
    cr.values.map((v) => [v.row_idx, v.value]),
  );
}
const cellAt = (page, ci, r) => (byPage[page] && byPage[page][ci] ? byPage[page][ci][r] : null);

phase('Row-identity repair');
let suspectTotal = 0;
if (canonicalIdentity) {
  const { aggregate_col, part_cols } = canonicalIdentity;
  const repairTasks = [];
  for (const s of scopes) {
    const suspectsByCol = {};
    for (const row of s.rows) {
      if (row.kind === 'header') continue;
      const agg = cellAt(s.page, aggregate_col, row.idx);
      if (agg == null) continue;
      const sum = part_cols.reduce((acc, pc) => acc + (cellAt(s.page, pc, row.idx) || 0), 0);
      const resid = sum - agg;
      if (Math.abs(resid) <= 1) continue; // integer lakh rows should be exact
      const badParts = part_cols.filter((pc) => cellAt(s.page, pc, row.idx) == null);
      const targets = badParts.length ? badParts : part_cols; // if none null, all parts are suspect
      for (const pc of targets) {
        const implied =
          targets.length === 1 ? agg - (sum - (cellAt(s.page, pc, row.idx) || 0)) : null;
        (suspectsByCol[pc] = suspectsByCol[pc] || []).push({
          row_idx: row.idx,
          label: row.label,
          read: cellAt(s.page, pc, row.idx),
          implied,
        });
      }
    }
    for (const pc of Object.keys(suspectsByCol).map(Number)) {
      suspectTotal += suspectsByCol[pc].length;
      const col = s.columns.find((c) => c.idx === pc);
      if (col) repairTasks.push({ s, col, suspects: suspectsByCol[pc] });
    }
  }
  log(
    `Row-identity repair: ${repairTasks.length} (page,column) targets, ${suspectTotal} suspect cells.`,
  );
  if (repairTasks.length) {
    const repaired = (
      await parallel(
        repairTasks.map(
          ({ s, col, suspects }) =>
            () =>
              agent(repairPrompt(s, col, suspects), {
                schema: COLUMN_SCHEMA,
                label: `repair:${s.page}.${col.idx}`,
                phase: 'Row-identity repair',
                model: 'opus',
              }),
        ),
      )
    ).filter(Boolean);
    for (const rc of repaired)
      (byPage[rc.page] = byPage[rc.page] || {})[rc.col_idx] = Object.fromEntries(
        rc.values.map((v) => [v.row_idx, v.value]),
      );
  }
}

phase('Grand-total gate');
// hand the assembled matrix + identity + grand-total context to the gate agent (deterministic checks already localized errors)
const gate = await agent(
  [
    gatePrompt(unit),
    `Pages scoped: ${scopes.map((s) => s.page).join(', ')}. Row identity: ${canonicalIdentity ? `Σ cols [${canonicalIdentity.part_cols}] = col ${canonicalIdentity.aggregate_col}` : 'none'}.`,
    `Grand-total row: ${grandPage ? `page ${grandPage.page} row ${grandPage.grand_total_row_idx}` : 'NONE — gate on row identity coverage only and SAY SO'}.`,
    `Assembled values by page are available to you via the column agents' outputs in this run; reconstruct the matrix and write the artifact.`,
  ].join('\n'),
  { schema: GATE_SCHEMA, label: 'gate', phase: 'Grand-total gate' },
);
log(
  `GATE → grand_total_reconciles=${gate.grand_total_reconciles} worst_residual=${gate.worst_residual} accepted=${gate.accepted_rows} quarantined=${gate.quarantined_rows}`,
);
if (gate.grand_total_cross_check) log(`Cross-check: ${gate.grand_total_cross_check}`);
if (gate.structural_decision_needed)
  log(`⚠ ESCALATE before promotion: ${gate.structural_decision_needed}`);

return {
  status: 'done',
  pages: a.page_start + '..' + a.page_end,
  scoped: scopes.length,
  suspects: suspectTotal,
  gate,
};
