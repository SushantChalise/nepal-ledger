"""BFI 49-month analytical pass. Reads staging-data/nrb-bfi/*.json and emits
summary CSVs to docs/research/_bfi_workspace/ for the Worker kappa narrative."""
from __future__ import annotations
import json
import glob
import os
import re
import csv
from collections import defaultdict
from pathlib import Path

BS_MONTHS = {
    'baisakh': 'Baisakh', 'baishakh': 'Baisakh',
    'jestha': 'Jestha', 'jeshtha': 'Jestha',
    'asar': 'Ashadh', 'ashar': 'Ashadh', 'ashadh': 'Ashadh',
    'shrawan': 'Shrawan', 'saun': 'Shrawan', 'shravan': 'Shrawan',
    'bhadau': 'Bhadra', 'bhadra': 'Bhadra',
    'ashwin': 'Ashwin', 'asoj': 'Ashwin',
    'kartik': 'Kartik',
    'manghir': 'Mangsir', 'mangshir': 'Mangsir', 'mangsir': 'Mangsir',
    'poush': 'Poush', 'magh': 'Magh', 'falgun': 'Falgun', 'chaitra': 'Chaitra',
}

BS_MONTH_ORDER = ['Shrawan', 'Bhadra', 'Ashwin', 'Kartik', 'Mangsir', 'Poush',
                  'Magh', 'Falgun', 'Chaitra', 'Baisakh', 'Jestha', 'Ashadh']


def parse_stem(stem: str):
    s = stem.lower()
    m_year = re.search(r'(207[89]|208[0-3])', s)
    if not m_year:
        return None
    year = int(m_year.group(1))
    for k, v in BS_MONTHS.items():
        if re.search(rf'(^|[_\- ]){re.escape(k)}([_\- 0-9]|$)', s):
            return (v, year)
    return None


def ad_key(period_bs_tuple):
    m, y = period_bs_tuple
    idx = BS_MONTH_ORDER.index(m)
    return (y, idx)


def main():
    files = sorted(glob.glob('staging-data/nrb-bfi/*.json'))
    mapping = []
    for f in files:
        stem = os.path.basename(f).replace('.json', '')
        p = parse_stem(stem)
        if p:
            mapping.append((stem, p, f))
        else:
            print(f'NO PARSE: {stem}')
    mapping.sort(key=lambda x: ad_key(x[1]))

    print(f'Mapped {len(mapping)} files. Range: {mapping[0][1]} -> {mapping[-1][1]}')

    workspace = Path('docs/research/_bfi_workspace')
    workspace.mkdir(parents=True, exist_ok=True)

    series = defaultdict(dict)
    all_observed = defaultdict(list)

    for stem, (m, y), f in mapping:
        d = json.load(open(f, encoding='utf-8'))
        headline_prefix = f'{m} {y}'
        for row in d['rows']:
            rp = row['reporting_period_bs']
            key = (row['source_sheet'], row['indicator_slug'], row['bank_class'])
            value = row['value']
            if value is None:
                continue
            all_observed[(row['source_sheet'], row['indicator_slug'], row['bank_class'], rp)].append((stem, value))
            if rp == headline_prefix or rp.startswith(headline_prefix + ' '):
                series[key][(m, y)] = value

    # monthly series CSV
    months = sorted({mo for v in series.values() for mo in v.keys()}, key=ad_key)
    month_labels = [f'{m} {y}' for m, y in months]
    with (workspace / 'monthly_series.csv').open('w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['sheet', 'slug', 'bank_class'] + month_labels)
        for (sheet, slug, bc), vals in sorted(series.items()):
            row = [sheet, slug, bc]
            for m in months:
                v = vals.get(m)
                row.append(f'{v:.4f}' if v is not None else '')
            w.writerow(row)
    print(f'Wrote monthly_series.csv')

    # revisions
    revisions = []
    for k, obs in all_observed.items():
        if len(obs) < 2:
            continue
        vals = [v for _, v in obs]
        vmax, vmin = max(vals), min(vals)
        if vmin == 0:
            continue
        rel = abs(vmax - vmin) / max(abs(vmin), 1e-6)
        if rel > 0.001:
            revisions.append((k, obs, rel))
    revisions.sort(key=lambda x: -x[2])
    with (workspace / 'revisions.csv').open('w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['sheet', 'slug', 'bank_class', 'period_bs', 'n_obs', 'min', 'max', 'rel_diff', 'files'])
        for k, obs, rel in revisions[:300]:
            sheet, slug, bc, p = k
            vals = [v for _, v in obs]
            files_str = '; '.join(f'{s}={v:.2f}' for s, v in obs)
            w.writerow([sheet, slug, bc, p, len(obs), min(vals), max(vals), rel, files_str])
    print(f'Wrote revisions.csv ({len(revisions)} revisions >0.1%)')

    first = months[0]
    last = months[-1]
    print(f'\nMONTH SPAN: {first} -> {last} ({len(months)} months)')

    targets = [
        ('C4', 'credit-deposit-ratios--cd-ratio', 'system_total'),
        ('C4', 'credit-deposit-ratios--cd-ratio', 'commercial'),
        ('C4', 'credit-deposit-ratios--cd-ratio', 'development'),
        ('C4', 'credit-deposit-ratios--cd-ratio', 'finance'),
        ('C4', 'credit-deposit-ratios--npl-total-loan', 'commercial'),
        ('C4', 'credit-deposit-ratios--npl-total-loan', 'development'),
        ('C4', 'credit-deposit-ratios--npl-total-loan', 'finance'),
        ('C4', 'credit-deposit-ratios--npl-total-loan', 'system_total'),
        ('C4', 'capital-adequacy-ratios--total-capital-rwa', 'commercial'),
        ('C4', 'capital-adequacy-ratios--total-capital-rwa', 'development'),
        ('C4', 'capital-adequacy-ratios--total-capital-rwa', 'finance'),
        ('C4', 'capital-adequacy-ratios--total-capital-rwa', 'system_total'),
        ('C4', 'capital-adequacy-ratios--core-capital-rwa', 'system_total'),
        ('C4', 'credit-deposit-ratios--saving-deposit-total-deposit', 'system_total'),
        ('C4', 'credit-deposit-ratios--fixed-deposit-total-deposit', 'system_total'),
        ('C4', 'credit-deposit-ratios--current-deposit-total-deposit', 'system_total'),
        ('C4', 'credit-deposit-ratios--call-deposit-total-deposit', 'system_total'),
        ('C4', 'credit-deposit-ratios--total-credit-gdp', 'system_total'),
        ('C4', 'credit-deposit-ratios--total-deposit-gdp', 'system_total'),
        ('C4', 'credit-deposit-ratios--total-llp-total-loan', 'system_total'),
        ('C4', 'credit-deposit-ratios--deprived-sector-loan-total-loan', 'system_total'),
        ('C4', 'interest-rate--wt-avg-interest-rate-on-credit', 'commercial'),
        ('C4', 'interest-rate--wt-avg-interest-rate-on-deposit', 'commercial'),
        ('C4', 'financial-access--no-of-branches', 'commercial'),
        ('C4', 'financial-access--no-of-branches', 'system_total'),
        ('C4', 'financial-access--no-of-atms', 'system_total'),
        ('C4', 'financial-access--no-of-deposit-accounts', 'system_total'),
        ('C4', 'financial-access--no-of-loan-accounts', 'system_total'),
        ('C4', 'financial-access--no-of-mobile-banking-customers', 'system_total'),
        ('C5', 'deposits', 'system_total'),
        ('C5', 'deposits--savings', 'system_total'),
        ('C5', 'deposits--fixed', 'system_total'),
        ('C5', 'deposits--current', 'system_total'),
        ('C5', 'deposits--call-deposits', 'system_total'),
        ('C5', 'capital-fund', 'system_total'),
        ('C5', 'capital-fund--paid-up-capital', 'system_total'),
        ('C5', 'capital-fund--retained-earning', 'system_total'),
        ('C5', 'borrowings', 'system_total'),
        ('C5', 'investments', 'system_total'),
        ('C5', 'investments--govt-securities', 'system_total'),
        ('C5', 'deposits', 'commercial'),
        ('C5', 'deposits', 'development'),
        ('C5', 'deposits', 'finance'),
        ('C5', 'capital-fund', 'commercial'),
        ('C5', 'capital-fund', 'development'),
        ('C5', 'capital-fund', 'finance'),
        ('C7', 'productwise--total', 'system_total'),
        ('C7', 'productwise--total', 'commercial'),
        ('C7', 'productwise--total', 'development'),
        ('C7', 'productwise--total', 'finance'),
        ('C7', 'productwise--real-estate-loan', 'system_total'),
        ('C7', 'productwise--residential-personal-home-loan-up-to-rs-30-million', 'system_total'),
        ('C7', 'productwise--margin-nature-loan', 'system_total'),
        ('C7', 'productwise--hire-purchase-loan', 'system_total'),
        ('C7', 'productwise--deprived-sector-loan', 'system_total'),
        ('C7', 'productwise--cash-credit-loan', 'system_total'),
        ('C7', 'productwise--overdraft', 'system_total'),
        ('C7', 'productwise--term-loan', 'system_total'),
        ('C7', 'productwise--trust-receipt-loan-import-loan', 'system_total'),
        ('C7', 'agricultural-and-forest-related', 'system_total'),
        ('C7', 'construction', 'system_total'),
        ('C7', 'wholesaler-retailer', 'system_total'),
        ('C7', 'consumption-loans', 'system_total'),
        ('C7', 'electricity-gas-and-water', 'system_total'),
        ('C7', 'finance-insurance-and-real-estate', 'system_total'),
        ('C7', 'tourism-service', 'system_total'),
        ('C7', 'transport-communication-and-public-utilities', 'system_total'),
        ('C7', 'mining-related', 'system_total'),
        ('C7', 'others', 'system_total'),
        ('C7', 'other-services', 'system_total'),
        ('C7', 'metal-products-machinary-electronic-equipment-assemblage', 'system_total'),
    ]
    print('\n=== Key indicator first->last ===')
    headline_tbl = []
    for sheet, slug, bc in targets:
        s = series.get((sheet, slug, bc), {})
        if not s:
            print(f'  MISS {sheet}/{slug}/{bc}')
            continue
        ms = sorted(s.keys(), key=ad_key)
        v0 = s[ms[0]]
        vN = s[ms[-1]]
        delta = vN - v0
        rel = (delta / v0 * 100) if v0 not in (0, None) else float('nan')
        print(f'  {sheet}/{slug[:55]:55s} {bc[:11]:11s} {ms[0][0]:8s}{ms[0][1]}={v0:14.2f}  {ms[-1][0]:8s}{ms[-1][1]}={vN:14.2f}  d={delta:+12.2f} ({rel:+6.1f}%)')
        headline_tbl.append({'sheet': sheet, 'slug': slug, 'bank_class': bc,
                             'first_period': f'{ms[0][0]} {ms[0][1]}', 'first_value': v0,
                             'last_period': f'{ms[-1][0]} {ms[-1][1]}', 'last_value': vN,
                             'delta_abs': delta, 'delta_rel_pct': rel, 'n_months': len(ms)})
    with (workspace / 'headline_table.json').open('w', encoding='utf-8') as fh:
        json.dump(headline_tbl, fh, indent=2)

    # Sector shares
    total_series = series.get(('C7', 'productwise--total', 'system_total'), {})
    print('\n=== Sector shares (% of productwise--total system_total) ===')
    print(f'{"slug":58s} {first[0]} {first[1]}   {last[0]} {last[1]}   dPP')
    share_rows = []
    sector_slugs = ['agricultural-and-forest-related', 'construction', 'wholesaler-retailer',
                    'consumption-loans', 'electricity-gas-and-water', 'finance-insurance-and-real-estate',
                    'tourism-service', 'transport-communication-and-public-utilities', 'mining-related',
                    'others', 'other-services',
                    'metal-products-machinary-electronic-equipment-assemblage',
                    'productwise--real-estate-loan',
                    'productwise--residential-personal-home-loan-up-to-rs-30-million',
                    'productwise--margin-nature-loan', 'productwise--hire-purchase-loan',
                    'productwise--deprived-sector-loan', 'productwise--term-loan',
                    'productwise--overdraft', 'productwise--cash-credit-loan',
                    'productwise--trust-receipt-loan-import-loan']
    for slug in sector_slugs:
        s = series.get(('C7', slug, 'system_total'), {})
        if not s:
            continue
        v_first = s.get(first)
        v_last = s.get(last)
        t_first = total_series.get(first)
        t_last = total_series.get(last)
        if None in (v_first, v_last, t_first, t_last):
            continue
        sf = v_first / t_first * 100
        sl = v_last / t_last * 100
        dpp = sl - sf
        print(f'  {slug:58s} {sf:7.3f}%   {sl:7.3f}%   {dpp:+6.2f}')
        share_rows.append({'slug': slug, 'share_first_pct': sf, 'share_last_pct': sl,
                           'delta_pp': dpp, 'value_first_npr_million': v_first,
                           'value_last_npr_million': v_last,
                           'first_period': f'{first[0]} {first[1]}',
                           'last_period': f'{last[0]} {last[1]}'})
    with (workspace / 'sector_shares.json').open('w', encoding='utf-8') as fh:
        json.dump(share_rows, fh, indent=2)

    # Concentration
    print('\n=== Bank-class concentration ===')
    classes = ['commercial', 'development', 'finance']
    conc = []
    for slug, sheet, label in [('deposits', 'C5', 'deposits'),
                                ('productwise--total', 'C7', 'loans'),
                                ('capital-fund', 'C5', 'capital_fund')]:
        for m in [first, last]:
            cls_vals = {c: series.get((sheet, slug, c), {}).get(m) for c in classes}
            if any(v is None for v in cls_vals.values()):
                print(f'  SKIP {label} {m} (missing class)')
                continue
            tot = sum(cls_vals.values())
            shares = {c: v / tot * 100 for c, v in cls_vals.items()}
            hhi = sum(s * s for s in shares.values())
            print(f'  {label:12s} {m[0]:8s}{m[1]}  shares={shares}  HHI(class)={hhi:.0f}  total_npr_mn={tot:.0f}')
            conc.append({'metric': label, 'period': f'{m[0]} {m[1]}',
                         'shares_pct': shares, 'hhi_class': hhi, 'total_npr_million': tot})
    with (workspace / 'concentration.json').open('w', encoding='utf-8') as fh:
        json.dump(conc, fh, indent=2)

    # Real estate / productive ratio over time
    print('\n=== Real-estate-cluster vs productive-sector share trend ===')
    re_cluster = ['productwise--real-estate-loan',
                  'productwise--residential-personal-home-loan-up-to-rs-30-million',
                  'finance-insurance-and-real-estate']
    productive = ['agricultural-and-forest-related', 'electricity-gas-and-water',
                  'metal-products-machinary-electronic-equipment-assemblage',
                  'transport-communication-and-public-utilities', 'mining-related',
                  'tourism-service']
    re_prod_trend = []
    for m in months:
        tot = total_series.get(m)
        if not tot:
            continue
        re_sum = sum(series.get(('C7', s, 'system_total'), {}).get(m, 0) for s in re_cluster)
        prod_sum = sum(series.get(('C7', s, 'system_total'), {}).get(m, 0) for s in productive)
        cons = series.get(('C7', 'consumption-loans', 'system_total'), {}).get(m, 0)
        wr = series.get(('C7', 'wholesaler-retailer', 'system_total'), {}).get(m, 0)
        re_share = re_sum / tot * 100
        prod_share = prod_sum / tot * 100
        cons_share = cons / tot * 100
        wr_share = wr / tot * 100
        print(f'  {m[0]:8s}{m[1]}  RE_cluster={re_share:5.2f}%  productive={prod_share:5.2f}%  consumption={cons_share:5.2f}%  wholesale={wr_share:5.2f}%  total_npr_mn={tot:.0f}')
        re_prod_trend.append({'period': f'{m[0]} {m[1]}',
                              're_cluster_pct': re_share, 'productive_pct': prod_share,
                              'consumption_pct': cons_share, 'wholesale_retail_pct': wr_share,
                              'total_npr_million': tot})
    with (workspace / 're_vs_productive.json').open('w', encoding='utf-8') as fh:
        json.dump(re_prod_trend, fh, indent=2)

    # NPL trend across the 4 NPL periods we have
    print('\n=== NPL trend (system_total %) ===')
    npl = series.get(('C4', 'credit-deposit-ratios--npl-total-loan', 'system_total'), {})
    npl_trend = []
    for m in sorted(npl.keys(), key=ad_key):
        print(f'  {m[0]:8s}{m[1]}  {npl[m]:.3f}%')
        npl_trend.append({'period': f'{m[0]} {m[1]}', 'npl_pct_system': npl[m]})
    with (workspace / 'npl_trend.json').open('w', encoding='utf-8') as fh:
        json.dump(npl_trend, fh, indent=2)


if __name__ == '__main__':
    main()
