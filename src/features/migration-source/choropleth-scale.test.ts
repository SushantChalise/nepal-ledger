import { describe, expect, it } from 'vitest';

import { CHOROPLETH_CLASSES, classOf, quantileBreaks } from './choropleth-scale';

describe('quantileBreaks', () => {
  it('returns no breaks when there are no positive values', () => {
    expect(quantileBreaks([])).toEqual([]);
    expect(quantileBreaks([0, 0, 0])).toEqual([]);
    expect(quantileBreaks([-5, -1])).toEqual([]);
  });

  it('returns CHOROPLETH_CLASSES - 1 internal breaks', () => {
    const values = Array.from({ length: 100 }, (_, i) => i + 1);
    expect(quantileBreaks(values)).toHaveLength(CHOROPLETH_CLASSES - 1);
  });

  it('produces non-decreasing breaks', () => {
    const values = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8, 9, 7, 9];
    const breaks = quantileBreaks(values);
    for (let i = 1; i < breaks.length; i += 1) {
      expect(breaks[i]).toBeGreaterThanOrEqual(breaks[i - 1]!);
    }
  });

  it('ignores zero and negative values when computing quantiles', () => {
    const withNoise = quantileBreaks([0, -1, 10, 20, 30, 40, 50, 60]);
    const clean = quantileBreaks([10, 20, 30, 40, 50, 60]);
    expect(withNoise).toEqual(clean);
  });
});

describe('classOf', () => {
  const breaks = [10, 20, 30, 40, 50];

  it('puts the smallest values in class 0', () => {
    expect(classOf(1, breaks)).toBe(0);
    expect(classOf(10, breaks)).toBe(0); // equal to a break → lower class
  });

  it('puts values above the last break in the top class', () => {
    expect(classOf(51, breaks)).toBe(5);
    expect(classOf(1_000_000, breaks)).toBe(5);
  });

  it('assigns interior values to the expected band', () => {
    expect(classOf(15, breaks)).toBe(1);
    expect(classOf(25, breaks)).toBe(2);
    expect(classOf(45, breaks)).toBe(4);
  });

  it('never exceeds the number of classes', () => {
    for (const v of [0, 5, 10, 25, 50, 99]) {
      expect(classOf(v, breaks)).toBeLessThan(CHOROPLETH_CLASSES);
      expect(classOf(v, breaks)).toBeGreaterThanOrEqual(0);
    }
  });

  it('returns class 0 when there are no breaks (all one colour)', () => {
    expect(classOf(123, [])).toBe(0);
  });
});
