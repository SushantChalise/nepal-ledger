/**
 * District → province mapping for Nepal's 77 districts (7 provinces).
 *
 * Generated from the authoritative "province" field of the source admin-boundary
 * GeoJSON (nepal-admin-boundaries, ADR-0025), keyed by the canonical district_en
 * spelling used in entities.metadata.district_en / scripts/geo/crosswalk.csv.
 * Used by the migration origin→destination Sankey to roll palika-grain census
 * absentee data up to origin province. Static reference data — not guessed.
 */

export type ProvinceName =
  | 'Koshi'
  | 'Madhesh'
  | 'Bagmati'
  | 'Gandaki'
  | 'Lumbini'
  | 'Karnali'
  | 'Sudurpashchim';

/** Canonical district_en (matching entities.metadata.district_en) → province. */
export const DISTRICT_TO_PROVINCE: Record<string, ProvinceName> = {
  Achham: 'Sudurpashchim',
  Arghakhanchi: 'Lumbini',
  Baglung: 'Gandaki',
  Baitadi: 'Sudurpashchim',
  Bajhang: 'Sudurpashchim',
  Bajura: 'Sudurpashchim',
  Banke: 'Lumbini',
  Bara: 'Madhesh',
  Bardiya: 'Lumbini',
  Bhaktapur: 'Bagmati',
  Bhojpur: 'Koshi',
  Chitwan: 'Bagmati',
  Dadeldhura: 'Sudurpashchim',
  Dailekh: 'Karnali',
  Dang: 'Lumbini',
  Darchula: 'Sudurpashchim',
  Dhading: 'Bagmati',
  Dhankuta: 'Koshi',
  Dhanusha: 'Madhesh',
  Dolakha: 'Bagmati',
  Dolpa: 'Karnali',
  Doti: 'Sudurpashchim',
  Gorkha: 'Gandaki',
  Gulmi: 'Lumbini',
  Humla: 'Karnali',
  Ilam: 'Koshi',
  Jajarkot: 'Karnali',
  Jhapa: 'Koshi',
  Jumla: 'Karnali',
  Kailali: 'Sudurpashchim',
  Kalikot: 'Karnali',
  Kanchanpur: 'Sudurpashchim',
  Kapilvastu: 'Lumbini',
  Kaski: 'Gandaki',
  Kathmandu: 'Bagmati',
  Kavrepalanchok: 'Bagmati',
  Khotang: 'Koshi',
  Lalitpur: 'Bagmati',
  Lamjung: 'Gandaki',
  Mahottari: 'Madhesh',
  Makwanpur: 'Bagmati',
  Manang: 'Gandaki',
  Morang: 'Koshi',
  Mugu: 'Karnali',
  Mustang: 'Gandaki',
  Myagdi: 'Gandaki',
  'Nawalparasi (Bardaghat Susta East)': 'Gandaki',
  'Nawalparasi (Bardaghat Susta West)': 'Lumbini',
  Nuwakot: 'Bagmati',
  Okhaldhunga: 'Koshi',
  Palpa: 'Lumbini',
  Panchthar: 'Koshi',
  Parbat: 'Gandaki',
  Parsa: 'Madhesh',
  Pyuthan: 'Lumbini',
  Ramechhap: 'Bagmati',
  Rasuwa: 'Bagmati',
  Rautahat: 'Madhesh',
  Rolpa: 'Lumbini',
  'Rukum (East)': 'Lumbini',
  'Rukum (West)': 'Karnali',
  Rupandehi: 'Lumbini',
  Salyan: 'Karnali',
  Sankhuwasabha: 'Koshi',
  Saptari: 'Madhesh',
  Sarlahi: 'Madhesh',
  Sindhuli: 'Bagmati',
  Sindhupalchok: 'Bagmati',
  Siraha: 'Madhesh',
  Solukhumbu: 'Koshi',
  Sunsari: 'Koshi',
  Surkhet: 'Karnali',
  Syangja: 'Gandaki',
  Tanahu: 'Gandaki',
  Taplejung: 'Koshi',
  Tehrathum: 'Koshi',
  Udayapur: 'Koshi',
};

/** The 7 provinces in fixed display order (national layout). */
export const PROVINCE_ORDER: readonly ProvinceName[] = [
  'Koshi',
  'Madhesh',
  'Bagmati',
  'Gandaki',
  'Lumbini',
  'Karnali',
  'Sudurpashchim',
] as const;
