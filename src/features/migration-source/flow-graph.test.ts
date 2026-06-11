import { describe, expect, it } from 'vitest';

import { buildMigrationFlowGraph } from './flow-graph';

describe('buildMigrationFlowGraph', () => {
  it('returns null when there is no positive flow', () => {
    expect(buildMigrationFlowGraph([])).toBeNull();
    expect(
      buildMigrationFlowGraph([{ district: 'Kaski', regionCode: 'a-india', people: 0 }]),
    ).toBeNull();
  });

  it('rolls districts up to their province', () => {
    // Kaski + Lamjung are both Gandaki.
    const graph = buildMigrationFlowGraph([
      { district: 'Kaski', regionCode: 'd-midleast', people: 100 },
      { district: 'Lamjung', regionCode: 'd-midleast', people: 50 },
    ]);
    expect(graph).not.toBeNull();
    const gandaki = graph!.nodes.find((n) => n.id === 'p-Gandaki');
    expect(gandaki?.people).toBe(150);
    expect(graph!.totalPeople).toBe(150);
    // One province node + one destination node.
    expect(graph!.nodes.filter((n) => n.column === 0)).toHaveLength(1);
    expect(graph!.nodes.filter((n) => n.column === 1)).toHaveLength(1);
  });

  it('consolidates EU + other-Europe into a single Europe destination', () => {
    const graph = buildMigrationFlowGraph([
      { district: 'Kaski', regionCode: 'f-eucntry', people: 30 },
      { district: 'Kaski', regionCode: 'g-othreuropn', people: 20 },
    ]);
    const destinations = graph!.nodes.filter((n) => n.column === 1);
    expect(destinations).toHaveLength(1);
    expect(destinations[0]!.id).toBe('d-europe');
    expect(destinations[0]!.people).toBe(50);
  });

  it('skips unknown districts, unknown regions, null districts, and non-positive people', () => {
    const graph = buildMigrationFlowGraph([
      { district: 'Kaski', regionCode: 'a-india', people: 10 },
      { district: 'Atlantis', regionCode: 'a-india', people: 999 }, // unknown district
      { district: 'Kaski', regionCode: 'z-bogus', people: 999 }, // unknown region
      { district: 'Kaski', regionCode: 'a-india', people: -5 }, // negative
      { district: null, regionCode: 'a-india', people: 5 }, // null district
    ]);
    expect(graph!.totalPeople).toBe(10);
    expect(graph!.links).toHaveLength(1);
  });

  it('builds province→destination links sorted by people descending', () => {
    const graph = buildMigrationFlowGraph([
      { district: 'Kaski', regionCode: 'a-india', people: 10 },
      { district: 'Kaski', regionCode: 'd-midleast', people: 100 },
    ]);
    expect(graph!.links.map((l) => l.people)).toEqual([100, 10]);
    expect(graph!.links[0]).toMatchObject({
      sourceId: 'p-Gandaki',
      targetId: 'd-middle-east',
      people: 100,
    });
  });
});
