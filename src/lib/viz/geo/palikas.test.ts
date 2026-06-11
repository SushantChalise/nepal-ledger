import { describe, expect, it } from 'vitest';

import { PALIKA_COUNT, palikaGeometry } from './palikas';

/**
 * Guards the build-generated choropleth asset (ADR-0025). If the geometry
 * build regresses (partial match, malformed paths, code drift), these fail
 * before the asset can ship.
 */
describe('palika geometry asset', () => {
  it('contains all 753 local levels', () => {
    expect(PALIKA_COUNT).toBe(753);
    expect(palikaGeometry.features).toHaveLength(753);
  });

  it('keys every feature by a unique MoFAGA 8-digit federal code', () => {
    const codes = palikaGeometry.features.map((f) => f.code);
    for (const code of codes) {
      expect(code).toMatch(/^\d{8}$/);
    }
    expect(new Set(codes).size).toBe(753);
  });

  it('has a well-formed shared viewBox', () => {
    expect(palikaGeometry.viewBox).toMatch(/^0 0 \d+(\.\d+)? \d+(\.\d+)?$/);
  });

  it('gives every feature a renderable SVG path and a name', () => {
    for (const f of palikaGeometry.features) {
      expect(f.d.startsWith('M')).toBe(true);
      expect(f.d.length).toBeGreaterThan(8);
      expect(f.nameEn.length).toBeGreaterThan(0);
      expect(f.district.length).toBeGreaterThan(0);
    }
  });

  it('has no degenerate subpaths (every subpath has ≥3 distinct points)', () => {
    // Guards the build's round-then-dedup-then-guard order: a ring that
    // collapses to <3 distinct pixels after integer rounding must be dropped,
    // never emitted as a zero-area `M x,y L x,y x,y Z`.
    for (const f of palikaGeometry.features) {
      for (const sub of f.d.split('M').slice(1)) {
        const pts = sub
          .replace('Z', '')
          .trim()
          .split(/[ L]+/)
          .filter((t) => t.includes(','));
        expect(new Set(pts).size).toBeGreaterThanOrEqual(3);
      }
    }
  });

  it('covers all 77 districts', () => {
    const districts = new Set(palikaGeometry.features.map((f) => f.district));
    expect(districts.size).toBe(77);
  });

  it('has the constitutional local-level type split', () => {
    const byType: Record<string, number> = {};
    for (const f of palikaGeometry.features) byType[f.type] = (byType[f.type] ?? 0) + 1;
    expect(byType['metropolitan_city']).toBe(6);
    expect(byType['sub_metropolitan_city']).toBe(11);
    expect(byType['municipality']).toBe(276);
    expect(byType['rural_municipality']).toBe(460);
  });
});
