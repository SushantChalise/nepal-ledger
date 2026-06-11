'use client';

/**
 * MigrationFlowSankey — origin province → destination region flow of Nepal's
 * absent population (the NDRI Atlas's Figure 6), as an accessible inline-SVG
 * Sankey. Built from the 2021 census; the unit is PEOPLE (headcount), never
 * rupees.
 *
 * Mirrors `src/features/money-flow/components/MoneyFlowSankey.tsx` field-for-
 * field: same d3-sankey adapter usage, same <640px stacked-bar fallback +
 * "view full diagram" disclosure, same always-present visually-hidden table.
 * D3 type-bridging casts live ONLY in `src/lib/viz/adapters/d3-sankey.ts`
 * (ADR-0012); the `link.source`/`link.target` reads here are plain post-layout
 * narrowings the adapter already guarantees — no `as unknown as`.
 *
 * Accessibility: the SVG is decorative (aria-hidden); every value is also text
 * (in-SVG labels + the always-present accessible table). Meaning is never
 * carried by colour or band width alone.
 */

import { useId, useState } from 'react';

import {
  computeSankeyLayout,
  sankeyLinkHorizontal,
  type ResolvedNode,
} from '@/lib/viz/adapters/d3-sankey';

import { formatPeople, formatPeopleFull, formatSharePct } from '../format';
import type { FlowNode, MigrationFlowGraph } from '../flow-graph';

type SankeyN = {
  id: string;
  label: string;
  column: 0 | 1;
  people: number;
};

type SankeyL = {
  people: number;
};

// Column palette — teal = origin province (left), amber = destination (right).
// Colour conveys side, but a text label is ALWAYS present on every node.
const COLUMN_COLORS: Record<0 | 1, string> = {
  0: '#0d9488', // teal-600 — origin provinces
  1: '#b45309', // amber-700 — destination regions
};

const LINK_COLOR = '#94a3b8'; // slate-400

// ---------------------------------------------------------------------------
// Mobile fallback — where the absent population goes (destination breakdown)
// ---------------------------------------------------------------------------

function StackedBarFallback({ graph }: { graph: MigrationFlowGraph }) {
  const destinations = graph.nodes
    .filter((n) => n.column === 1)
    .sort((a, b) => b.people - a.people);
  const total = graph.totalPeople;
  const fills = ['#b45309', '#c2410c', '#9a3412', '#d97706', '#92400e', '#78350f'];

  return (
    <div aria-label="Nepal absent population by destination region (mobile summary)">
      <p className="mb-2 text-xs text-zinc-500 dark:text-zinc-400">
        Census {graph.censusYearAd} · absent population by destination
      </p>
      <div className="flex h-8 w-full overflow-hidden rounded" role="img" aria-hidden="true">
        {destinations.map((node, i) => {
          const pct = total > 0 ? (node.people / total) * 100 : 0;
          return (
            <div
              key={node.id}
              style={{ width: `${pct.toFixed(2)}%`, backgroundColor: fills[i % fills.length] }}
              title={`${node.label}: ${formatPeople(node.people)}`}
            />
          );
        })}
      </div>
      <ul className="mt-2 space-y-1">
        {destinations.map((node, i) => {
          const pct = total > 0 ? (node.people / total) * 100 : 0;
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
              <span className="ml-auto tabular-nums">{formatPeople(node.people)}</span>
              <span className="w-12 text-right text-zinc-500">{formatSharePct(pct)}</span>
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

const SVG_HEIGHT = 520;
const NODE_WIDTH = 18;
const NODE_PADDING = 14;

function FullSankey({ graph, width }: { graph: MigrationFlowGraph; width: number }) {
  const descId = useId();

  const inputNodes: SankeyN[] = graph.nodes.map((n) => ({
    id: n.id,
    label: n.label,
    column: n.column,
    people: n.people,
  }));

  const inputLinks = graph.links.map((l) => ({
    source: l.sourceId,
    target: l.targetId,
    value: l.people,
    people: l.people,
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
        Sankey diagram of Nepal&apos;s absent population in the {graph.censusYearAd} census, flowing
        from origin province (left) to destination region (right); total{' '}
        {formatPeopleFull(graph.totalPeople)} people.
      </desc>

      <g>
        {resolvedLinks.map((link, i) => {
          const srcNode = link.source as ResolvedNode<SankeyN, SankeyL>;
          const tgtNode = link.target as ResolvedNode<SankeyN, SankeyL>;
          const pathD = linkGen(link as Parameters<typeof linkGen>[0]);
          return (
            <path
              key={i}
              d={pathD ?? ''}
              fill="none"
              stroke={LINK_COLOR}
              strokeWidth={Math.max(1, link.width)}
              strokeOpacity={0.4}
            >
              <title>
                {srcNode.label} → {tgtNode.label}: {formatPeopleFull(link.people)}
              </title>
            </path>
          );
        })}
      </g>

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
                  {node.label}: {formatPeopleFull(node.people)}
                </title>
              </rect>
              <text
                x={labelX}
                y={midY}
                dy="0.35em"
                textAnchor={labelAnchor}
                fontSize={11}
                className="select-none fill-zinc-800 dark:fill-zinc-200"
              >
                {node.label}
              </text>
              {nodeHeight > 16 && (
                <text
                  x={labelX}
                  y={midY + 13}
                  dy="0.35em"
                  textAnchor={labelAnchor}
                  fontSize={9.5}
                  className="select-none fill-zinc-500 dark:fill-zinc-400"
                >
                  {formatPeople(node.people)}
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

function AccessibleTableFallback({ graph }: { graph: MigrationFlowGraph }) {
  const nodeLabel = (id: string): string =>
    graph.nodes.find((n: FlowNode) => n.id === id)?.label ?? id;
  return (
    <div className="sr-only">
      <table>
        <caption>
          Nepal absent population by origin province and destination region, {graph.censusYearAd}{' '}
          census (people)
        </caption>
        <thead>
          <tr>
            <th scope="col">Origin province</th>
            <th scope="col">Destination region</th>
            <th scope="col">People</th>
          </tr>
        </thead>
        <tbody>
          {graph.links.map((link, i) => (
            <tr key={i}>
              <td>{nodeLabel(link.sourceId)}</td>
              <td>{nodeLabel(link.targetId)}</td>
              <td>{formatPeopleFull(link.people)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main export
// ---------------------------------------------------------------------------

type MigrationFlowSankeyProps = {
  graph: MigrationFlowGraph;
};

export function MigrationFlowSankey({ graph }: MigrationFlowSankeyProps) {
  const [svgWidth, setSvgWidth] = useState(800);

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
      <div className="block sm:hidden">
        <StackedBarFallback graph={graph} />
        <details className="mt-3">
          <summary className="cursor-pointer text-sm text-blue-600 underline dark:text-blue-400">
            View full flow diagram
          </summary>
          <div ref={attachResizeObserver} className="mt-3 w-full overflow-x-auto">
            <FullSankey graph={graph} width={svgWidth} />
          </div>
        </details>
      </div>

      <div ref={attachResizeObserver} className="hidden w-full sm:block">
        <FullSankey graph={graph} width={svgWidth} />
      </div>

      <AccessibleTableFallback graph={graph} />
    </div>
  );
}
