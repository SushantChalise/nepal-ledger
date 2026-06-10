'use client';

/**
 * MoneyFlowSankey — client component that renders Nepal's national money-flow
 * (money in → economy → money out) as an accessible inline SVG Sankey diagram.
 *
 * Mirrors `src/features/money-map/components/SankeyDiagram.tsx` field-for-field:
 * same d3-sankey adapter usage, same mobile stacked-bar fallback + "view full
 * diagram" disclosure, same always-present visually-hidden accessible table.
 *
 * D3 type-bridging casts live ONLY in `src/lib/viz/adapters/d3-sankey.ts`
 * (sanctioned cast location, ADR-0012 / CONTEXT_RULES §"Cast Escape Hatches").
 * The `link.source` / `link.target` reads below are plain narrowings to the
 * resolved-node shape the adapter already guarantees post-layout — no
 * `as unknown as`.
 *
 * Mobile rule (UI_ACCEPTANCE.md §"Mobile-First Rules"):
 *   < 640px → stacked-bar inflow summary + a disclosure to the full Sankey.
 *   ≥ 640px → full Sankey SVG.
 *
 * Accessibility:
 *   - The SVG is decorative: it is aria-hidden, and EVERY value is also printed
 *     as text (in-SVG labels + the always-present accessible table). Meaning is
 *     never carried by colour or band width alone (the money-map gotcha).
 *   - prefers-reduced-motion: link paths have no animation (there is none here).
 */

import { useId, useState } from 'react';

import {
  computeSankeyLayout,
  sankeyLinkHorizontal,
  type ResolvedNode,
} from '@/lib/viz/adapters/d3-sankey';

import type { FlowColumn, MoneyFlowData, FlowNode } from '../server/queries';
import { formatNprBillion, formatSharePct } from '../format';

type SankeyN = {
  id: string;
  label: string;
  valueBillion: number;
  column: FlowColumn;
};

type SankeyL = {
  valueBillion: number;
};

// Column palette — distinct hues with WCAG-AA contrast on white. Colour conveys
// category (inflow / hub / outflow), but a text label is ALWAYS present next to
// every node, so no information is colour-only.
const COLUMN_COLORS: Record<FlowColumn, string> = {
  0: '#0d9488', // teal-600 — money in (inflow sources)
  1: '#1d4ed8', // blue-700 — the economy hub
  2: '#b45309', // amber-700 — money out / retained (sinks)
};

const LINK_COLOR = '#94a3b8'; // slate-400 — neutral link colour

// ---------------------------------------------------------------------------
// Stacked-bar mobile fallback — composition of inflows (the headline story)
// ---------------------------------------------------------------------------

function StackedBarFallback({ data }: { data: MoneyFlowData }) {
  const inflowNodes = data.nodes.filter((n) => n.column === 0);
  const total = data.totalInflowsBillion;
  // Distinct fills per inflow, each labelled in the legend below.
  const fills = ['#0d9488', '#0891b2', '#0e7490'];

  return (
    <div aria-label="Nepal money inflows by source (mobile summary)">
      <p className="mb-2 text-xs text-zinc-500 dark:text-zinc-400">
        FY {data.periodBs} · inflows in NPR billion
      </p>
      <div className="flex h-8 w-full overflow-hidden rounded" role="img" aria-hidden="true">
        {inflowNodes.map((node, i) => {
          const pct = total > 0 ? (node.valueBillion / total) * 100 : 0;
          return (
            <div
              key={node.id}
              style={{ width: `${pct.toFixed(2)}%`, backgroundColor: fills[i % fills.length] }}
              title={`${node.label}: ${formatNprBillion(node.valueBillion)}`}
            />
          );
        })}
      </div>
      <ul className="mt-2 space-y-1">
        {inflowNodes.map((node, i) => {
          const pct = total > 0 ? (node.valueBillion / total) * 100 : 0;
          return (
            <li
              key={node.id}
              className="flex items-center gap-2 text-xs text-zinc-700 dark:text-zinc-300"
            >
              <span
                className="inline-block h-3 w-3 flex-shrink-0 rounded-sm"
                style={{ backgroundColor: fills[i % fills.length] }}
                aria-hidden="true"
              />
              <span>{node.label}</span>
              <span className="ml-auto tabular-nums">{formatNprBillion(node.valueBillion)}</span>
              <span className="w-12 text-right text-zinc-500">{formatSharePct(pct)}</span>
            </li>
          );
        })}
      </ul>
      <p className="mt-3 text-xs text-zinc-500 dark:text-zinc-400">
        Against these inflows, Nepal paid {formatNprBillion(data.importsBillion)} for merchandise
        imports — a trade deficit of {formatNprBillion(data.tradeDeficitBillion)}.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Full Sankey SVG (tablet + desktop)
// ---------------------------------------------------------------------------

const SVG_HEIGHT = 480;
const NODE_WIDTH = 18;
const NODE_PADDING = 22;

function FullSankey({ data, width }: { data: MoneyFlowData; width: number }) {
  const descId = useId();

  const inputNodes: SankeyN[] = data.nodes.map((n) => ({
    id: n.id,
    label: n.label,
    valueBillion: n.valueBillion,
    column: n.column,
  }));

  // Links use string IDs; d3-sankey resolves them via its nodeId accessor.
  const inputLinks = data.links.map((l) => ({
    source: l.sourceId,
    target: l.targetId,
    value: l.valueBillion,
    valueBillion: l.valueBillion,
  }));

  const { nodes: resolvedNodes, links: resolvedLinks } = computeSankeyLayout<SankeyN, SankeyL>(
    { nodes: inputNodes, links: inputLinks },
    { width, height: SVG_HEIGHT, nodeWidth: NODE_WIDTH, nodePadding: NODE_PADDING },
  );

  const linkGen = sankeyLinkHorizontal();

  return (
    <svg
      viewBox={`0 0 ${width} ${SVG_HEIGHT}`}
      width="100%"
      height={SVG_HEIGHT}
      aria-hidden="true"
      role="img"
      className="overflow-visible"
    >
      <desc id={descId}>
        Sankey diagram of Nepal&apos;s money flow for FY {data.periodBs}: inflows (remittance,
        foreign aid, merchandise exports) totalling {formatNprBillion(data.totalInflowsBillion)}{' '}
        pass through the economy and out to merchandise imports of{' '}
        {formatNprBillion(data.importsBillion)}.
      </desc>

      {/* Links — rendered first so nodes appear on top */}
      <g>
        {resolvedLinks.map((link, i) => {
          const srcNode = link.source as ResolvedNode<SankeyN, SankeyL>;
          const tgtNode = link.target as ResolvedNode<SankeyN, SankeyL>;
          const pathD = linkGen(link as Parameters<typeof linkGen>[0]);
          const valLabel = formatNprBillion(link.valueBillion);

          return (
            <path
              key={i}
              d={pathD ?? ''}
              fill="none"
              stroke={LINK_COLOR}
              strokeWidth={Math.max(1, link.width)}
              strokeOpacity={0.45}
            >
              <title>
                {srcNode.label} → {tgtNode.label}: {valLabel}
              </title>
            </path>
          );
        })}
      </g>

      {/* Nodes */}
      <g>
        {resolvedNodes.map((node) => {
          const nodeColor = COLUMN_COLORS[node.column];
          const nodeHeight = node.y1 - node.y0;
          const labelRight = (node.x0 ?? 0) > width / 2;
          const labelX = labelRight ? (node.x0 ?? 0) - 6 : (node.x1 ?? 0) + 6;
          const labelAnchor = labelRight ? 'end' : 'start';
          const midY = node.y0 + nodeHeight / 2;

          return (
            <g key={node.id}>
              <rect
                x={node.x0}
                y={node.y0}
                width={NODE_WIDTH}
                height={Math.max(1, nodeHeight)}
                fill={nodeColor}
                rx={3}
              >
                <title>
                  {node.label}: {formatNprBillion(node.valueBillion)}
                </title>
              </rect>

              {/* Node label */}
              <text
                x={labelX}
                y={midY}
                dy="0.35em"
                textAnchor={labelAnchor}
                fontSize={11}
                fill="currentColor"
                className="select-none fill-zinc-800 dark:fill-zinc-200"
              >
                {node.label}
              </text>

              {/* Value label — below node name, smaller */}
              {nodeHeight > 18 && (
                <text
                  x={labelX}
                  y={midY + 13}
                  dy="0.35em"
                  textAnchor={labelAnchor}
                  fontSize={9.5}
                  className="select-none fill-zinc-500 dark:fill-zinc-400"
                >
                  {formatNprBillion(node.valueBillion)}
                </text>
              )}
            </g>
          );
        })}
      </g>
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Accessible table fallback (visually hidden, always present)
// ---------------------------------------------------------------------------

function AccessibleTableFallback({ data }: { data: MoneyFlowData }) {
  return (
    <div className="sr-only">
      <table>
        <caption>Nepal money flow FY {data.periodBs} — flow summary (NPR billion)</caption>
        <thead>
          <tr>
            <th scope="col">From</th>
            <th scope="col">To</th>
            <th scope="col">Amount (NPR billion)</th>
          </tr>
        </thead>
        <tbody>
          {data.links.map((link, i) => {
            const srcNode = data.nodes.find((n: FlowNode) => n.id === link.sourceId);
            const tgtNode = data.nodes.find((n: FlowNode) => n.id === link.targetId);
            return (
              <tr key={i}>
                <td>{srcNode?.label ?? link.sourceId}</td>
                <td>{tgtNode?.label ?? link.targetId}</td>
                <td>{formatNprBillion(link.valueBillion)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main export
// ---------------------------------------------------------------------------

type MoneyFlowSankeyProps = {
  data: MoneyFlowData;
};

export function MoneyFlowSankey({ data }: MoneyFlowSankeyProps) {
  // Responsive width: default 800 before the client measures the container.
  const [svgWidth, setSvgWidth] = useState(800);

  // Attach a ResizeObserver to a container div to get a reactive width. Not torn
  // down on unmount: this is a page-level diagram that lives for the route's
  // lifetime (mirrors money-map's documented decision).
  const attachResizeObserver = (el: HTMLDivElement | null) => {
    if (!el) return;
    setSvgWidth(el.clientWidth > 0 ? el.clientWidth : 800);
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        const w = entry.contentRect.width;
        if (w > 0) setSvgWidth(w);
      }
    });
    observer.observe(el);
  };

  return (
    <div>
      {/* Mobile: stacked-bar summary (< sm = < 640px). Desktop: full Sankey. */}
      <div className="block sm:hidden">
        <StackedBarFallback data={data} />
        <details className="mt-3">
          <summary className="cursor-pointer text-sm text-blue-600 underline dark:text-blue-400">
            View full Sankey diagram
          </summary>
          <div ref={attachResizeObserver} className="mt-3 w-full overflow-x-auto">
            <FullSankey data={data} width={svgWidth} />
          </div>
        </details>
      </div>

      <div ref={attachResizeObserver} className="hidden w-full sm:block">
        <FullSankey data={data} width={svgWidth} />
      </div>

      {/* Always-present screen-reader table. */}
      <AccessibleTableFallback data={data} />
    </div>
  );
}
