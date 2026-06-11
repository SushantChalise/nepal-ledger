import { describe, expect, it } from 'vitest';

import { DISTRICT_TO_PROVINCE, PROVINCE_ORDER, type ProvinceName } from './district-province';

describe('DISTRICT_TO_PROVINCE', () => {
  it('maps exactly Nepal’s 77 districts', () => {
    expect(Object.keys(DISTRICT_TO_PROVINCE)).toHaveLength(77);
  });

  it('assigns every district to one of the 7 provinces', () => {
    const provinces = new Set<ProvinceName>(PROVINCE_ORDER);
    for (const province of Object.values(DISTRICT_TO_PROVINCE)) {
      expect(provinces.has(province)).toBe(true);
    }
  });

  it('has the constitutional district-per-province counts (sum 77)', () => {
    const counts: Record<ProvinceName, number> = {
      Koshi: 0,
      Madhesh: 0,
      Bagmati: 0,
      Gandaki: 0,
      Lumbini: 0,
      Karnali: 0,
      Sudurpashchim: 0,
    };
    for (const province of Object.values(DISTRICT_TO_PROVINCE)) counts[province] += 1;
    expect(counts).toEqual({
      Koshi: 14,
      Madhesh: 8,
      Bagmati: 13,
      Gandaki: 11,
      Lumbini: 12,
      Karnali: 10,
      Sudurpashchim: 9,
    });
    const total = Object.values(counts).reduce((a, b) => a + b, 0);
    expect(total).toBe(77);
  });

  it('PROVINCE_ORDER lists all 7 provinces once, west-to-east by number', () => {
    expect(PROVINCE_ORDER).toEqual([
      'Koshi',
      'Madhesh',
      'Bagmati',
      'Gandaki',
      'Lumbini',
      'Karnali',
      'Sudurpashchim',
    ]);
    expect(new Set(PROVINCE_ORDER).size).toBe(7);
  });
});
