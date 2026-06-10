/**
 * d3-sankey type adapters.
 *
 * d3-sankey's TypeScript types require `source`/`target` as
 * `string | number | SankeyNode<N,L>`, but its `nodeId` accessor makes
 * plain string IDs work at runtime. The `as unknown as` casts here are the
 * standard workaround — sanctioned per CONTEXT_RULES.md §"Cast Escape
 * Hatches" item (c): `src/lib/viz/adapters/*`.
 */

import {
  sankey,
  sankeyJustify,
  sankeyLinkHorizontal,
  type SankeyGraph,
  type SankeyLink,
  type SankeyNode,
} from 'd3-sankey';

export type { SankeyGraph, SankeyLink, SankeyNode };
export { sankeyLinkHorizontal };

type StringIdLink<L> = {
  source: string;
  target: string;
  value: number;
} & L;

export type LayoutInput<N, L> = {
  nodes: N[];
  links: StringIdLink<L>[];
};

type ExtraProps = Record<string, unknown>;

export type ResolvedNode<N extends ExtraProps, L extends ExtraProps> = SankeyNode<N, L> & {
  x0: number;
  x1: number;
  y0: number;
  y1: number;
};

export type ResolvedLink<N extends ExtraProps, L extends ExtraProps> = SankeyLink<N, L> & {
  width: number;
  y0: number;
  y1: number;
};

export function computeSankeyLayout<N extends { id: string } & ExtraProps, L extends ExtraProps>(
  input: LayoutInput<N, L>,
  opts: { width: number; height: number; nodeWidth?: number; nodePadding?: number },
): { nodes: ResolvedNode<N, L>[]; links: ResolvedLink<N, L>[] } {
  const { width, height, nodeWidth = 18, nodePadding = 20 } = opts;

  const layoutFn = sankey<N, L>()
    .nodeId((n: SankeyNode<N, L>) => (n as unknown as { id: string }).id)
    .nodeAlign(sankeyJustify)
    .nodeWidth(nodeWidth)
    .nodePadding(nodePadding)
    .extent([
      [1, 1],
      [width - 1, height - 6],
    ]);

  const graph = layoutFn(input as unknown as SankeyGraph<N, L>);

  return {
    nodes: graph.nodes as ResolvedNode<N, L>[],
    links: graph.links as ResolvedLink<N, L>[],
  };
}
