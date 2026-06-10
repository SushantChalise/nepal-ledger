# Build + verify the render-confirmed FY2081/82 GVA matrix (annex 13.1). Mother-authored.
# Values render-verified from high-zoom column strips (Matrix 8). idx0-17 sectors, 18=GVA-basic, 19=net-tax, 20=GDP.
import json, os

PROV = ["koshi","madhes","bagamati","gandaki","lumbini","karnali","sudur-pashchim"]
PROV_NE = ["कोशी","मधेस","वागमती","गण्डकी","लुम्बिनी","कर्णाली","सुदूरपश्चिम"]
SECTORS = [
 ("agriculture-forestry-fishing","कृषि, वन र मत्स्यपालन"),
 ("mining-quarrying","खानी तथा उत्खनन्"),
 ("manufacturing","उत्पादनमूलक उद्योग"),
 ("electricity-gas-steam-ac","विद्युत, ग्यास, वाष्प तथा वातानुकलित आपूर्ति"),
 ("water-supply-sewerage-waste","पानी आपूर्ति, ढल, फोहोर व्यवस्थापन"),
 ("construction","निर्माण"),
 ("wholesale-retail-trade-vehicle-repair","थोक तथा खुद्रा व्यापार"),
 ("transport-storage","यातायात तथा भण्डारण"),
 ("accommodation-food-service","आवास तथा भोजन सेवा"),
 ("information-communication","सुचना तथा सञ्चार"),
 ("financial-insurance","वित्तीय तथा बीमा"),
 ("real-estate","घरजग्गा कारोवार"),
 ("professional-scientific-technical","पेशागत, वैज्ञानिक तथा प्राविधिक"),
 ("administrative-support-service","प्रशासनिक तथा सहयोगी सेवा"),
 ("public-administration-defence","सार्वजनिक प्रशासन, रक्षा"),
 ("education","शिक्षा"),
 ("human-health-social-work","मानव स्वास्थ्य तथा सामाजिक कार्य"),
 ("other-service","अन्य सेवा"),
]
# idx0..20 per column (2081/82), render-verified
NATIONAL = [135373,2478,26780,9324,2279,28164,78296,38758,13255,10425,35766,44610,5208,3877,46916,42351,10264,3836,537959,72763,610722]
COLS = {
 "koshi":[29119,312,5813,2051,385,5200,8095,4929,1968,1743,3254,5627,492,275,7090,6712,1765,677,85507,11566,97074],
 "madhes":[26013,104,3791,437,432,2782,9704,4998,635,1768,2495,1922,282,266,6655,6888,1279,368,70818,9579,80397],
 "bagamati":[23179,1224,9651,3257,531,7203,44303,18310,5269,3256,22025,29814,3469,2829,8658,9063,2673,1737,196452,26572,223023],
 "gandaki":[13085,322,1544,2465,188,3753,3853,2767,2324,1136,2910,2429,319,154,5558,4005,1160,315,48285,6531,54816],
 "lumbini":[23744,391,4305,637,418,4929,7864,5785,1573,1637,3742,3403,410,266,7869,7408,1723,436,76537,10352,86890],
 "karnali":[7093,37,230,147,128,1617,1330,614,744,297,407,425,76,39,5242,3277,687,127,22514,3045,25559],
 "sudur-pashchim":[13140,88,1446,330,198,2679,3148,1356,742,589,932,990,161,48,5845,4998,977,178,37844,5119,42963],
}
DNE_GDP_NOMINAL_2081_82_CRORE = 610722  # = 6107.221 npr_billion (live DB)

def recon():
    per_prov=[]; worst_col=0
    for p in PROV:
        v=COLS[p]; ssum=sum(v[0:18]); r=ssum-v[18]; r2=(v[18]+v[19])-v[20]
        worst_col=max(worst_col,abs(r),abs(r2)); per_prov.append((p,ssum,v[18],r,v[18]+v[19],v[20],r2))
    per_sec=[]; worst_row=0
    for i in range(21):
        psum=sum(COLS[p][i] for p in PROV); r=psum-NATIONAL[i]
        worst_row=max(worst_row,abs(r)); per_sec.append((i,psum,NATIONAL[i],r))
    return per_prov,per_sec,worst_col,worst_row

per_prov,per_sec,worst_col,worst_row=recon()
print("=== per-province (Σsectors vs GVA | GVA+tax vs GDP) ===")
for p,ss,gva,r,gt,gdp,r2 in per_prov: print(f"  {p:16} Σ={ss} GVA={gva} r={r:+d} | {gt} vs GDP {gdp} r={r2:+d}")
print("=== per-sector/agg (Σ7prov vs national) ===")
for i,ps,nat,r in per_sec: print(f"  idx{i:2} Σ={ps} nat={nat} r={r:+d}")
print(f"WORST residual: column={worst_col}  row={worst_row}  (rounding tolerance ~±9 for 18 summed crore values)")
print(f"CROSS-SOURCE: national GDP {NATIONAL[20]} vs dne-gdp-nominal {DNE_GDP_NOMINAL_2081_82_CRORE} -> {'EXACT' if NATIONAL[20]==DNE_GDP_NOMINAL_2081_82_CRORE else 'DIFF'}")

# Build artifact
allcols=dict(COLS); allcols["nepal"]=NATIONAL
cells=[]; aggs=[]
for p in PROV+["nepal"]:
    v=allcols[p]
    for i,(slug,ne) in enumerate(SECTORS):
        cells.append({"province":p,"sector_idx":i,"sector_slug":slug,"value":v[i]})
    aggs.append({"province":p,"gva_basic":v[18],"net_product_tax":v[19],"gdp_producer":v[20]})
out={
 "source_pdf":"Financial Data/mof_documents/economic_survey/Economic_Survey_2081-82.pdf","source_page":475,
 "table":"अनुसूची १३.१ प्रदेशगत कुल मूल्य अभिवृद्धि (औद्योगिक वर्गीकरण अनुसार)",
 "measure":"gross_value_added_basic_prices","unit":"npr_crore","price_basis":"current",
 "fiscal_year_bs":"2081/82","fiscal_year_ad":"2024/25",
 "extraction_method":"surya-ocr","verification":"Mother render-verified (Matrix-8 column strips), dual-reconciled","confidence_grade":"B",
 "provinces":PROV+["nepal"],"sectors":[{"idx":i,"slug":s,"label_ne":n} for i,(s,n) in enumerate(SECTORS)],
 "cells":cells,"aggregates":aggs,
 "reconciliation":{
   "per_province":[{"province":p,"sum_sectors":ss,"gva_printed":gva,"residual":r,"gva_plus_tax":gt,"gdp_printed":gdp,"residual":r2} for p,ss,gva,r,gt,gdp,r2 in per_prov],
   "per_sector":[{"sector_idx":i,"sum_provinces":ps,"national":nat,"residual":r} for i,ps,nat,r in per_sec],
   "worst_residual_crore":{"column":worst_col,"row":worst_row},
   "cross_source":{"national_gdp":NATIONAL[20],"dne_gdp_nominal_2081_82_crore":DNE_GDP_NOMINAL_2081_82_CRORE,"match":NATIONAL[20]==DNE_GDP_NOMINAL_2081_82_CRORE},
 },
}
dst=os.path.join(os.path.dirname(os.path.abspath(__file__)),"verified_matrix_2081_82.json")
json.dump(out,open(dst,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("WROTE",dst,os.path.getsize(dst),"bytes")
