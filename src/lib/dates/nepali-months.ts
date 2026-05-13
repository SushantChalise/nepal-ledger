/**
 * Canonical Nepali month vocabulary in fiscal-year order.
 *
 * FY index 1..12 = Shrawan..Ashadh per docs/CALENDAR_AND_PERIODS.md.
 * `nepali-date-converter` uses calendar order (Baisakh=0..Chaitra=11);
 * `libraryMonthFromFyMonth` / `fyMonthFromLibraryMonth` bridge the two.
 */

export const FY_MONTHS_EN = [
  'Shrawan',
  'Bhadra',
  'Ashwin',
  'Kartik',
  'Mangsir',
  'Poush',
  'Magh',
  'Falgun',
  'Chait',
  'Baisakh',
  'Jestha',
  'Ashadh',
] as const;

export type CanonicalMonthEn = (typeof FY_MONTHS_EN)[number];

export const FY_MONTHS_NE = [
  'साउन',
  'भदौ',
  'असोज',
  'कात्तिक',
  'मंसिर',
  'पुष',
  'माघ',
  'फागुन',
  'चैत',
  'बैशाख',
  'जेठ',
  'असार',
] as const;

const ALIASES: Record<string, CanonicalMonthEn> = {
  shrawan: 'Shrawan',
  saun: 'Shrawan',
  sawan: 'Shrawan',
  bhadra: 'Bhadra',
  bhadau: 'Bhadra',
  ashwin: 'Ashwin',
  asoj: 'Ashwin',
  aswin: 'Ashwin',
  kartik: 'Kartik',
  kartika: 'Kartik',
  mangsir: 'Mangsir',
  marg: 'Mangsir',
  poush: 'Poush',
  push: 'Poush',
  magh: 'Magh',
  falgun: 'Falgun',
  phagun: 'Falgun',
  fagun: 'Falgun',
  chait: 'Chait',
  chaitra: 'Chait',
  baisakh: 'Baisakh',
  vaishakha: 'Baisakh',
  baishakh: 'Baisakh',
  jestha: 'Jestha',
  jeth: 'Jestha',
  ashadh: 'Ashadh',
  asar: 'Ashadh',
  asadh: 'Ashadh',
};

export function normalizeMonthName(raw: string): CanonicalMonthEn | null {
  return (
    ALIASES[
      raw
        .trim()
        .toLowerCase()
        .replace(/[.\s-]/g, '')
    ] ?? null
  );
}

// FY index 1..12 (Shrawan..Ashadh) ↔ library calendar index 0..11 (Baisakh..Chaitra).
export const libraryMonthFromFyMonth = (fyMonth: number): number => (fyMonth + 2) % 12;
export const fyMonthFromLibraryMonth = (libMonth: number): number => ((libMonth + 9) % 12) + 1;
