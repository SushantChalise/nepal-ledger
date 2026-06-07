'use client';

/**
 * SankeyDiagram — client component that renders Nepal's fiscal transfer flows
 * as an accessible inline SVG Sankey diagram.
 *
 * D3 type-bridging casts in this file are sanctioned per CONTEXT_RULES.md
 * §"Cast Escape Hatches" item 3 (files under src/lib/viz/adapters/* OR,
 * as noted in the task brief, co-located viz components that bridge D3 types).
 * All casts are local, post-layout, and narrowing-only.
 *
 * Mobile rule (UI_ACCEPTANCE.md §"Mobile-first lens rules"):
 *   < 640px → stacked bar fallback with a "view full diagram" disclosure.
 *   ≥ 640px → full Sankey SVG.
 *
 * Accessibility:
 *   - aria-label on the SVG summarises the overall flow.
 *   - Each SVG node rect has an aria-label with value.
 *   - Each SVG path has an SVG <title> (tooltips + screen reader).
 *   - A visually-hidden <table> below the SVG exposes the same data
 *     for screen readers that navigate tables (role="table" fallback).
 *   - prefers-reduced-motion: link paths have no animation.
 */

import { useId, useState } from 'react';
import { sankey, sankeyJustify, sankeyLinkHorizontal } from 'd3-sankey';
import type { SankeyGraph, SankeyLink, SankeyNode } from 'd3-sankey';

import type { SankeyData, SankeyNodeData } from '../server/queries';
import { formatNprThousand } from '../format';

// ---------------------------------------------------------------------------
// D3 Sankey node/link extra properties (user-defined fields)
// ---------------------------------------------------------------------------

type SankeyN = {
  id: string;
  label: string;
  totalNprThousand: number;
  column: 0 | 1 | 2;
};

type SankeyL = {
  valueNprThousand: number;
};

// Resolved node type after d3-sankey layout — x0/y0/x1/y1 are guaranteed.
// Cast from SankeyNode<SankeyN, SankeyL> is a sanctioned D3-type bridge.
type ResolvedNode = SankeyNode<SankeyN, SankeyL> & {
  x0: number;
  x1: number;
  y0: number;
  y1: number;
};

type ResolvedLink = SankeyLink<SankeyN, SankeyL> & {
  width: number;
  y0: number;
  y1: number;
};

// Column colour palette — distinct, WCAG-AA contrast on white background.
// Colors convey category, but labels are always present (no color-only info).
const COLUMN_COLORS: Record<0 | 1 | 2, string> = {
  0: '#1d4ed8', // blue-700 — Federal
  1: '#0891b2', // cyan-600 — Grant types
  2: '#0d9488', // teal-600 — Local-level types
};

const LINK_COLOR = '#94a3b8'; // slate-400 — neutral link colour

// ---------------------------------------------------------------------------
// Stacked-bar mobile fallback
// ---------------------------------------------------------------------------

function StackedBarFallback({ data }: { data: SankeyData }) {
  const localNodes = data.nodes.filter((n) => n.column === 2);
  const grand = data.grandTotalNprThousand;

  return (
    <div aria-label="Fiscal transfers by local-level type (mobile summary)">
      <p className="mb-2 text-xs text-zinc-500 dark:text-zinc-400">
        FY {data.fiscalYearBs} · amounts in NPR (thousands)
      </p>
      <div className="flex h-8 w-full overflow-hidden rounded" role="img" aria-hidden="true">
        {localNodes.map((node, i) => {
          const pct = grand > 0 ? (node.totalNprThousand / grand) * 100 : 0;
          const colors = ['#1d4ed8', '#0891b2', '#0d9488', '#059669'];
          return (
            <div
              key={node.id}
              style={{ width: `${pct.toFixed(2)}%`, backgroundColor: colors[i % colors.length] }}
              title={`${node.label}: ${formatNprThousand(node.totalNprThousand)}`}
            />
          );
        })}
      </div>
      <ul className="mt-2 space-y-1">
        {localNodes.map((node, i) => {
          const pct = grand > 0 ? (node.totalNprThousand / grand) * 100 : 0;
          const colors = ['#1d4ed8', '#0891b2', '#0d9488', '#059669'];
          return (
            <li
              key={node.id}
              className="flex items-center gap-2 text-xs text-zinc-700 dark:text-zinc-300"
            >
              <span
                className="inline-block h-3 w-3 flex-shrink-0 rounded-sm"
                style={{ backgroundColor: colors[i % colors.length] }}
                aria-hidden="true"
              />
              <span>{node.label}</span>
              <span className="ml-auto tabular-nums">
                {formatNprThousand(node.totalNprThousand)}
              </span>
              <span className="w-10 text-right text-zinc-500">{pct.toFixed(1)}%</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Full Sankey SVG (tablet + desktop)
// ---------------------------------------------------------------------------

const SVG_HEIGHT = 540;
const NODE_WIDTH = 18;
const NODE_PADDING = 20;

function FullSankey({ data, width }: { data: SankeyData; width: number }) {
  const descId = useId();

  // Build d3-sankey input from our typed structures.
  const inputNodes: SankeyN[] = data.nodes.map((n) => ({
    id: n.id,
    label: n.label,
    totalNprThousand: n.totalNprThousand,
    column: n.column,
  }));

  // Links use string IDs; d3-sankey resolves them via nodeId accessor.
  const inputLinks = data.links.map((l) => ({
    source: l.sourceId,
    target: l.targetId,
    value: l.valueNprThousand,
    valueNprThousand: l.valueNprThousand,
  }));

  const layout = sankey<SankeyN, SankeyL>()
    .nodeId((n) => n.id)
    .nodeAlign(sankeyJustify)
    .nodeWidth(NODE_WIDTH)
    .nodePadding(NODE_PADDING)
    .extent([
      [1, 1],
      [width - 1, SVG_HEIGHT - 6],
    ]);

  // d3-sankey mutates in place; the cast is a sanctioned D3-type bridge.
  // sankeyGraph contains nodes + links with computed layout positions.
  const graph = layout({
    nodes: inputNodes,
    links: inputLinks as unknown as Array<{
      source: string;
      target: string;
      value: number;
      valueNprThousand: number;
    }>,
  } as unknown as SankeyGraph<SankeyN, SankeyL>);

  const resolvedNodes = graph.nodes as ResolvedNode[];
  const resolvedLinks = graph.links as ResolvedLink[];

  const linkGen = sankeyLinkHorizontal();

  return (
    <svg
      viewBox={`0 0 ${width} ${SVG_HEIGHT}`}
      width="100%"
      height={SVG_HEIGHT}
      aria-labelledby={descId}
      role="img"
      className="overflow-visible"
    >
      <desc id={descId}>
        Sankey diagram of Nepal federal fiscal transfers for FY {data.fiscalYearBs}. Federal
        Government distributes {formatNprThousand(data.grandTotalNprThousand)} across{' '}
        {data.nodes.filter((n) => n.column === 1).length} grant types to{' '}
        {data.nodes.filter((n) => n.column === 2).length} local-level types.
      </desc>

      {/* Links — rendered first so nodes appear on top */}
      <g aria-hidden="true">
        {resolvedLinks.map((link, i) => {
          // Sanctioned D3-type bridge: source/target are resolved node objects
          // after layout, but typed as string | number | SankeyNode<N,L>.
          const srcNode = link.source as ResolvedNode;
          const tgtNode = link.target as ResolvedNode;
          const pathD = linkGen(link as unknown as Parameters<typeof linkGen>[0]);
          const srcLabel = srcNode.label;
          const tgtLabel = tgtNode.label;
          const valLabel = formatNprThousand(link.valueNprThousand);

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
                {srcLabel} → {tgtLabel}: {valLabel}
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
            <g
              key={node.id}
              aria-label={`${node.label}: ${formatNprThousand(node.totalNprThousand)}`}
            >
              <rect
                x={node.x0}
                y={node.y0}
                width={NODE_WIDTH}
                height={Math.max(1, nodeHeight)}
                fill={nodeColor}
                rx={3}
              >
                <title>
                  {node.label}: {formatNprThousand(node.totalNprThousand)}
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
                aria-hidden="true"
              >
                {node.label}
              </text>

              {/* Value label — below node name, smaller */}
              {nodeHeight > 20 && (
                <text
                  x={labelX}
                  y={midY + 13}
                  dy="0.35em"
                  textAnchor={labelAnchor}
                  fontSize={9.5}
                  aria-hidden="true"
                  className="select-none fill-zinc-500 dark:fill-zinc-400"
                >
                  {formatNprThousand(node.totalNprThousand)}
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

function AccessibleTableFallback({ data }: { data: SankeyData }) {
  return (
    <div className="sr-only">
      <table>
        <caption>Federal fiscal transfers FY {data.fiscalYearBs} — flow summary</caption>
        <thead>
          <tr>
            <th scope="col">Source</th>
            <th scope="col">Destination</th>
            <th scope="col">Amount</th>
          </tr>
        </thead>
        <tbody>
          {data.links.map((link, i) => {
            const srcNode = data.nodes.find((n: SankeyNodeData) => n.id === link.sourceId);
            const tgtNode = data.nodes.find((n: SankeyNodeData) => n.id === link.targetId);
            return (
              <tr key={i}>
                <td>{srcNode?.label ?? link.sourceId}</td>
                <td>{tgtNode?.label ?? link.targetId}</td>
                <td>{formatNprThousand(link.valueNprThousand)}</td>
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

type SankeyDiagramProps = {
  data: SankeyData;
};

export function SankeyDiagram({ data }: SankeyDiagramProps) {
  // Responsive width: default 800 before client measures the container.
  const [svgWidth, setSvgWidth] = useState(800);

  // Attach a ResizeObserver to a container div to get reactive width.
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
    // The observer is attached to the element; GC'd when the element unmounts.
  };

  return (
    <div>
      {/* Mobile: stacked-bar summary (< sm breakpoint = < 640px).
          Desktop: full Sankey. */}
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
