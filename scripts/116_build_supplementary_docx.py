"""Build the standalone SUPPLEMENTARY MATERIAL Word document: the supplementary figures (embedded)
and tables, separated from the main Results. Numbering: Figures S1-S9, Tables S1-S8.
S4/S5 figures + Table S5 added 2026-08-11 (ADR-0005: LTFU as proportion; crude-ranking
robustness; GLMM place effects). Requires /tmp figures from scripts 121/122 (RANK=crude too).
Output: Drive .../SP-TB-spatial-analyses/Supplementary_material/SP_TB_Manuscript_Supplementary.docx
"""
import pandas as pd, os, json, shutil
from docx import Document
from docx.shared import Pt, RGBColor, Inches
SUP=("/DATA_ROOT/WHO modelling Project/SP-TB-spatial-analyses/Supplementary_material")
FIG=f"{SUP}/figures"; OUT=f"{SUP}/SP_TB_Manuscript_Supplementary.docx"
os.makedirs(FIG,exist_ok=True)
# stage the S-figures from their generating scripts' /tmp outputs (114, 111, 88, 122-crude)
_SRC={"figS1_strobe_flow.png":"/tmp/figS_strobe.png",
      "figS2_denoising.png":"/tmp/figS1_denoising.png",
      "figS3_ipvs_validation.png":"/tmp/fig_ipvs_validation.png"}
import shutil as _sh
for dst,src in _SRC.items():
    if os.path.exists(src): _sh.copy(src,f"{FIG}/{dst}")
    elif not os.path.exists(f"{FIG}/{dst}"):
        raise SystemExit(f"faltando {src} (rode o script gerador) e sem cópia prévia de {dst}")

doc=Document()
st=doc.styles["Normal"]; st.font.name="Calibri"; st.font.size=Pt(11)
def H(t,l=1):
    h=doc.add_heading(t,level=l)
    for r in h.runs: r.font.color.rgb=RGBColor(0x0d,0x2b,0x45)
    return h
def figcap(label,text,img,w=6.0):
    doc.add_picture(f"{FIG}/{img}",width=Inches(w))
    doc.paragraphs[-1].alignment=1
    p=doc.add_paragraph(); r=p.add_run(label+" "); r.bold=True; r.font.size=Pt(9.5)
    rr=p.add_run(text); rr.font.size=Pt(9.5); p.paragraph_format.space_after=Pt(14)
def tblcap(label,text):
    p=doc.add_paragraph(); r=p.add_run(label+" "); r.bold=True; r.font.size=Pt(10)
    p.add_run(text); p.paragraph_format.space_after=Pt(4)
def mktable(cols,data,fs=9,note=None):
    t=doc.add_table(rows=len(data)+1,cols=len(cols)); t.style="Light Grid Accent 1"
    for j,c in enumerate(cols):
        t.rows[0].cells[j].text=c
        for rr in t.rows[0].cells[j].paragraphs[0].runs: rr.font.bold=True; rr.font.size=Pt(fs)
    for i,row in enumerate(data):
        for j,v in enumerate(row):
            t.rows[i+1].cells[j].text=str(v)
            for rr in t.rows[i+1].cells[j].paragraphs[0].runs: rr.font.size=Pt(fs)
    if note:
        p=doc.add_paragraph(); rn=p.add_run(note); rn.font.size=Pt(8); rn.font.color.rgb=RGBColor(0x5b,0x6b,0x7a)
    doc.add_paragraph()

doc.add_heading("Supplementary Material",level=0)
doc.add_paragraph("Geographic concentration, adverse-outcome hotspots, and place vulnerability of "
                  "tuberculosis in São Paulo State, 2013–2024.").runs[0].italic=True

H("Supplementary methods — rate basis and age-standardized sensitivity analysis")
for _p in [
 "All primary results use crude rates: notifications and deaths per adult resident per year, and loss to "
 "follow-up (LTFU) as the proportion of evaluated episodes. Because the aim of the analysis is to locate "
 "cases, deaths and treatment losses rather than to compare risk net of age structure, crude rates are the "
 "quantity a programme would act on. As a sensitivity analysis every result was recomputed with "
 "age-standardized rates: indirect standardization against the São Paulo state population as internal "
 "reference in eight adult age bands (15–19, 20–24, 25–29, 30–39, 40–49, 50–59, 60–69, ≥70 years), with "
 "LTFU as the age-adjusted proportion of evaluated episodes (observed/expected under the state-wide "
 "age-specific proportions).",
 "The two bases give the same answer for every headline result. The hotspot sets coincide almost entirely "
 "(Jaccard 0.97 for notifications, 0.93 for mortality and 0.83 for LTFU); the de-noised shares of events in "
 "the top 20% of the population are identical for notifications (45%) and mortality (39%) and 22% versus 24% "
 "for LTFU (Gini 0.21 versus 0.23); the excess fraction relative to the least-deprived quintile is 33% "
 "versus 34% for notifications; and the geographic-inequality excess fraction is 65% under both. The one "
 "material difference is the deprivation gradient of mortality, which is steeper under standardization "
 "(excess fraction 35% versus 28%) because deprived regions have younger populations and tuberculosis "
 "mortality rises steeply with age, so crude rates understate the mortality excess in deprived areas "
 "(Supplementary Figure S9).",
]:
    _para=doc.add_paragraph(_p); _para.paragraph_format.space_after=Pt(8)

H("Supplementary methods — construction of the statewide regionalization")
for _p in [
 "The units of analysis were built from the 2022 census sectors by a greedy, spatially constrained "
 "region-growing algorithm developed for this study. Inputs are the sector polygons, the adult (15+) "
 "population, the mean household income of the responsible person (2022 Census variable V06004), and "
 "favela (subnormal agglomerate) status.",
 "Within each IBGE district, and separately for favela and non-favela sectors, the algorithm seeds a "
 "region and repeatedly adds the contiguous unassigned sector closest in household income until the "
 "region reaches the target of approximately 5,000 adults; residual sectors too small to form a region "
 "are merged into the most income-similar neighbouring region. Contiguity islands are reconnected to "
 "their nearest sector, so that growth never strands single sectors. Because favela and non-favela "
 "sectors are regionalized separately, a favela is never merged with an adjacent affluent area; sectors "
 "not covered by the regionalization fall back to district-level units.",
 "The population target is a parameter of the algorithm. Rebuilding the entire regionalization at "
 "targets of approximately 3,000 and 8,000 adults leaves the main findings unchanged (Supplementary "
 "Table S2). The implementation is available in the analysis code repository "
 "(scripts/83_regionalize_state.py).",
]:
    _para=doc.add_paragraph(_p); _para.paragraph_format.space_after=Pt(8)

H("Supplementary figures")
figcap("Supplementary Figure S1.","Study-population flow (STROBE).","figS1_strobe_flow.png",w=5.3)
figcap("Supplementary Figure S2.","De-noising the concentration estimate. For each outcome the naïve "
       "estimate (dashed) overstates clustering — most for the rarer outcomes — because sampling "
       "variability inflates the naïve index when events are rare; the split-sample cross-fit (solid) "
       "removes this bias.","figS2_denoising.png",w=5.6)
figcap("Supplementary Figure S3.","External validation of the place-based vulnerability composite "
       "against the official São Paulo Social Vulnerability Index (IPVS 2022, SEADE); Spearman ρ = 0.76. "
       "An index constructed on the domains of the Brazilian Deprivation Index (IBP, CIDACS/Fiocruz; "
       "income, education, sanitation) applied to the 2022 Census showed comparable agreement with the "
       "IPVS (ρ = 0.72) and correlated strongly with our composite (ρ = 0.89), indicating consistency "
       "with an established, independently developed index (see Supplementary Table S8).",
       "figS3_ipvs_validation.png",w=6.2)
# S4 — legacy figure carried from the V1 supplement (generator pending); S5–S7 from scripts/129 (ADR-0006)
LEG=json.load(open(f"{FIG}/legacy_captions.json"))
if os.path.exists("/tmp/figS4_spatial_structure.png"): shutil.copy("/tmp/figS4_spatial_structure.png",f"{FIG}/figS4_spatial_structure.png")   # scripts/131
figcap("Supplementary Figure S4.","Spatial structure of tuberculosis outcomes. (a) Global Moran's I (queen contiguity, "
       "row-standardized weights, 999 permutations) on log region-level rates for tuberculosis notifications, mortality "
       "and loss to follow-up (LTFU), unadjusted and on the residuals after regression on the place-vulnerability index. "
       "(b) Percentage of the variance in each log rate explained by the place-vulnerability index. (c) Spatial "
       "autoregressive parameter (ρ) from maximum-likelihood spatial-lag models, fitted on the largest connected component "
       "of the contiguity graph. Notifications are strongly clustered (I = 0.60; 0.58 after adjustment), mortality and LTFU "
       "only weakly (I = 0.21 and 0.18); the vulnerability index explains 16% of the variance in notification rates but "
       "about 1% for mortality and LTFU.","figS4_spatial_structure.png",w=6.4)
for src,dst in [("/tmp/figS5_ltfu_deprivation.png","figS5_ltfu_deprivation.png"),
                ("/tmp/figS6_attributable_deprivation.png","figS6_attributable_deprivation.png"),
                ("/tmp/figS7_attributable_metro.png","figS7_attributable_metro.png"),
                ("/tmp/fig2_composite_percap.png","figS8_ltfu_percapita.png"),
                ("/tmp/fig3_composite_std.png","figS9_vulnerability_age_standardized.png")]:
    if os.path.exists(src): shutil.copy(src,f"{FIG}/{dst}")
figcap("Supplementary Figure S5.","Loss to follow-up across deprivation. LTFU (% of evaluated episodes) by "
       "quintile of (a) household-income deprivation and (b) the composite vulnerability index (1 = least, "
       "5 = most deprived), with 95% confidence intervals from a region-cluster bootstrap. The dashed line "
       "marks the least-deprived (reference) quintile. LTFU varies little across quintiles (household income: "
       "12.3% to 13.8%).","figS5_ltfu_deprivation.png",w=6.0)
figcap("Supplementary Figure S6.","Excess burden associated with deprivation, by household income and by the "
       "composite index (all São Paulo). Tuberculosis notification rate (a, c) and mortality (b, d) by quintile of "
       "household-income deprivation (a, b) and of the composite vulnerability index (c, d), from 1 (least) to "
       "5 (most deprived). The dashed line marks the least-deprived (reference) quintile; numbers above bars are "
       "excess cases or deaths relative to that quintile, and insets report the excess fraction (region-cluster "
       "bootstrap 95% CI). Panels (a) and (b) reproduce the household-income analysis of Figure 3.",
       "figS6_attributable_deprivation.png",w=6.0)
figcap("Supplementary Figure S7.","Excess burden associated with deprivation within metropolitan regions "
       "(Greater São Paulo and Baixada Santista). Layout as in Supplementary Figure S6, restricted to "
       "metropolitan regions.","figS7_attributable_metro.png",w=6.0)
# S8 — LTFU as events per capita (scripts/122 RANK=percap); S9 — age-standardized sensitivity (scripts/124 RANK=std)
figcap("Supplementary Figure S8.","Concentration analysis with LTFU counted as events per capita rather than "
       "as a proportion of evaluated episodes. Notifications and mortality are unchanged. Under the per-capita "
       "definition LTFU appears the most concentrated outcome (de-noised Gini 0.42) because loss-to-follow-up "
       "events track the concentration of notifications themselves; as a proportion of evaluated episodes "
       "(primary analysis) it is the least concentrated (Gini 0.23).","figS8_ltfu_percapita.png",w=6.2)
figcap("Supplementary Figure S9.","Sensitivity analysis: place vulnerability of hotspots and the excess burden "
       "associated with deprivation using age-standardized rates (indirect standardization, State reference, "
       "eight age bands; LTFU as the age-adjusted proportion of evaluated episodes) in place of the crude rates "
       "of the primary analysis (main Figure 3). Hotspot sets under the two rate bases coincide almost entirely "
       "(Jaccard 0.97, 0.93 and 0.83 for notifications, mortality and LTFU), and the notification gradient is unchanged "
       "(excess fraction 33% vs 34%); the mortality gradient is steeper under standardization (35% vs 28%) "
       "because deprived regions have younger populations and tuberculosis mortality rises steeply with age.",
       "figS9_vulnerability_age_standardized.png",w=6.2)

H("Supplementary tables")
# S1 — geocoding precision
rc=pd.read_csv("/tmp/region_cases.csv"); N=len(rc); tc=rc["tier"].value_counts()
tblcap("Supplementary Table S1.","Geocoding precision of the analytic set (192,161 notified episodes "
       "assigned to a residential region; 96.0% of the 200,107 eligible episodes with a standard "
       "residential address).")
mktable(["Precision tier","Assignment","Episodes, n","%"],
        [["T1","Exact street and number",f"{int(tc.get('T1',0)):,}",f"{tc.get('T1',0)/N*100:.1f}"],
         ["T2","Street name",f"{int(tc.get('T2',0)):,}",f"{tc.get('T2',0)/N*100:.1f}"],
         ["T3","Approximate (fuzzy) street match",f"{int(tc.get('T3',0)):,}",f"{tc.get('T3',0)/N*100:.1f}"],
         ["T4","Neighbourhood centroid",f"{int(tc.get('T4',0)):,}",f"{tc.get('T4',0)/N*100:.1f}"],
         ["T5","Postal-code centroid",f"{int(tc.get('T5',0)):,}",f"{tc.get('T5',0)/N*100:.1f}"],
         ["Total geocoded","",f"{N:,}","100.0"]])
# S2 — region-size sensitivity
tblcap("Supplementary Table S2.","Sensitivity of the main findings to the region-size target "
       "(modifiable areal unit problem). The regionalization was rebuilt at three population targets.")
mktable(["Target region size","Regions, n","Regions ≥10 cases","Median adults","Notifications /100 000",
         "Top-20% concentration, % (notifications / mortality / LTFU)","Hotspot deprivation, Cohen's d (income / vulnerability)"],
        [["≈3,000","11,151","6,699","3,307","44.6","46 / 37 / 48","−0.49 / +0.54"],
         ["≈5,000 (main)","7,314","5,248","5,329","44.6","45 / 39 / 49","−0.62 / +0.71"],
         ["≈8,000","5,131","3,790","8,208","44.6","45 / 41 / 50","−0.70 / +0.81"]],fs=8.5,
        note="Concentration = de-noised share of events in the top 20% of the population by rate. "
             "Cohen's d = standardized difference (notification-hotspot vs non-hotspot), income oriented so "
             "negative = poorer hotspots. Findings are stable across region sizes." "This table was computed when the analysis ranked LTFU per capita (Supplementary Figure S8) and is retained on that basis; on the primary basis the main-analysis values are 45 / 39 / 24 and d = 0.64 for income. Incidence and mortality are unaffected by the ranking basis.")
# S3 — excluded domains
tblcap("Supplementary Table S3.","Candidate domains tested and excluded from the place-based vulnerability index.")
mktable(["Candidate domain","Observation"],
        [["Sanitation","Near-universal in urban São Paulo (~87% of the adult population with adequate sanitation); its inclusion lowered agreement with the IPVS."],
         ["Precarious housing (cortiço)","Recorded in only 0.3% of census sectors — too sparse to characterise areas."],
         ["Race (Black and mixed-race)","Strongly correlated with the income-based composite (Spearman ρ ≈ 0.98)."],
         ["Population density","Negatively correlated with the composite (ρ ≈ −0.20); the densest sectors are predominantly high-income vertical housing."]])
# S4 — no-CEP (T5) sensitivity
tblcap("Supplementary Table S4.","Sensitivity of the geographic concentration to excluding the coarsest "
       "(postal-code-level, tier T5) geocoded episodes.")
mktable(["Geocoded set","Episodes, n","Notifications","TB mortality","Loss to follow-up"],
        [["All tiers (T1–T5), main","192,161","45","39","24"],
         ["Excluding CEP (T1–T4)","176,932","43","37","26"]],
        note="Values are the de-noised share (%) of events in the top 20% of the population living in the "
             "highest-rate regions (LTFU as the proportion of evaluated episodes, as in the main analysis). "
             "Concentration is essentially unchanged when postal-code-level cases are excluded.")
# S5/S6 — recovered verbatim from the 2026-08-04 dated supplement (generator scripts lived in a
# lost session /tmp; re-scripting is a registered task with these values as validation targets)
tblcap("Supplementary Table S5.","Out-of-sample capture of notified cases at matched 20% population coverage.")
mktable(["Training window","Test window","Region-level hotspots","Whole municipalities","No targeting"],
        [["2013–2018","2019–2024","44%","16%","20%"],
         ["2013–2018","2022–2024","43%","16%","20%"],
         ["2013–2015","2022–2024","42%","15%","20%"]],
        note="Region-level hotspots and whole municipalities were selected by ranking units on 2013–2018 "
             "(or 2013–2015) notification rate and taking the highest-rate units up to 20% of the adult population, "
             "then measuring the share of test-period cases captured. Municipality targeting is constrained "
             "to whole municipalities; São Paulo city (26% of the state population and 38% of cases) alone "
             "exceeds the 20% budget and cannot be subdivided. \u201cNo targeting\u201d is the 20% of cases expected "
             "under random selection of the population.")
tblcap("Supplementary Table S6.","Sensitivity of the income-deprivation excess fraction (notifications) to the "
       "spatial unit definition (age-standardized rates).")
mktable(["Spatial unit","Units, n","Notification rate, least→most deprived quintile (/100,000/yr)","Excess fraction, %"],
        [["Income-homogeneous regionalization (main)","5,248","34 → 67","33"],
         ["Income-neutral regionalization (same resolution)","5,818","36 → 66","29"],
         ["Operational (administrative) unit","1,494","41 → 81","11"]],
        note="The regions used in the main analysis were constructed to minimise within-region heterogeneity "
             "in household income, which could in principle sharpen the observed income gradient. The excess "
             "fraction was recomputed on age-standardized rates under two alternative unit definitions, holding "
             "the estimation identical (the primary crude-rate analysis gives 34% for the main regionalization): an income-neutral regionalization of the same resolution (contiguous "
             "units of approximately 5,000 adults grown by spatial proximity rather than by income), and a "
             "coarser administrative unit (favela, neighbourhood, or district). The fraction was 29% under "
             "the income-neutral regionalization, versus 33% in the main analysis, indicating that the "
             "gradient is not primarily an artefact of income-based unit construction. The lower value under "
             "the coarser administrative unit (11%) reflects greater within-unit income heterogeneity, which "
             "attenuates area-level exposures — a general feature of aggregated analyses (the modifiable "
             "areal unit problem).")
# S5 — GLMM place effects on LTFU (script 121; ADR-0005)
if os.path.exists("/tmp/ltfu_glmm_ors.csv") and os.path.exists("/tmp/ltfu_glmm_summary.json"):
    g=json.load(open("/tmp/ltfu_glmm_summary.json")); ors=pd.read_csv("/tmp/ltfu_glmm_ors.csv")
    LBL={"ageband[15, 20)":"Age 15–19 (vs 30–39)","ageband[20, 25)":"Age 20–24","ageband[25, 30)":"Age 25–29",
         "ageband[40, 50)":"Age 40–49","ageband[50, 60)":"Age 50–59","ageband[60, 70)":"Age 60–69",
         "ageband[70, 200)":"Age ≥70","sex_stdM":"Male sex","alcoholism":"Alcohol use","drug_use":"Drug use",
         "tobacco_use":"Tobacco use","diabetes":"Diabetes","hivcpos":"HIV positive (vs negative)",
         "hivcunknown":"HIV unknown","period16-18":"2016–18 (vs 2013–15)","period19-21":"2019–21",
         "period22-24":"2022–24","dotself":"Self-administered (vs supervised)","dotmissing":"Treatment administration missing"}
    rows=[[LBL.get(r["term"],r["term"]),f"{r['OR']:.2f}",f"{r['lo']:.2f}–{r['hi']:.2f}"] for _,r in ors.iterrows()]
    tblcap("Supplementary Table S7.",
           f"Individual predictors of loss to follow-up and the independent place effect: logistic mixed "
           f"model with random region intercepts ({g['n_episodes']:,} evaluated episodes, "
           f"{g['n_regions']:,} regions). Between-region variance (σ²) was {g['m0']['sigma2']:.3f} with age only, "
           f"{g['m1']['sigma2']:.3f} after adding patient characteristics (proportional change 0%) and "
           f"{g['m2']['sigma2']:.3f} after adding treatment administration (proportional change 4%); median odds "
           f"ratio {g['m0']['MOR']:.2f} / {g['m1']['MOR']:.2f} / {g['m2']['MOR']:.2f}; latent-scale intraclass "
           f"correlation {g['m1']['ICC']*100:.0f}%. On the probability scale, predicted LTFU for an otherwise "
           f"identical patient is approximately 8% and 19% in regions at the 10th and 90th percentiles of the "
           f"estimated region-effect distribution (baseline 12.6%). Region effects were uncorrelated with the "
           f"place-vulnerability index (Spearman ρ = 0.01). Odds ratios below are from the model including "
           f"treatment administration.")
    mktable(["Predictor","Odds ratio","95% CI"],rows,fs=9,
            note="Treatment administration is assigned during treatment and is therefore adjusted for "
                 "separately (indication/mediation, not pure confounding). Age adjustment uses the "
                 "individual-level age of evaluated episodes; no population denominators are involved.")
else:
    print("AVISO: /tmp/ltfu_glmm_* ausentes — rode scripts/121 antes; Tabela S5 omitida.")

# S8 — IBP sensitivity (script 125; JC comments)
if os.path.exists("/tmp/ibp_sensitivity.json"):
    ib=json.load(open("/tmp/ibp_sensitivity.json"))
    tblcap("Supplementary Table S8.",
           f"Robustness of the hotspot–deprivation divergence to the deprivation index. Cohen's d "
           f"(hotspot vs non-hotspot regions) for the study composite and for an index built on the "
           f"domains of the Brazilian Deprivation Index (IBP; income, education, sanitation) from the "
           f"2022 Census.")
    mktable(["Hotspot type","Study composite, d","IBP-domain index, d"],
            [[{"incidence":"Notifications","ltfu":"LTFU"}.get(k.lower(), k.capitalize()), f"{v['composite']:+.2f}", f"{v['ibp']:+.2f}"] for k,v in ib["cohend"].items()],
            note=f"The divergence is preserved under both indices: notification and mortality hotspots are more "
                 f"deprived while LTFU hotspots are not. The weaker discrimination of the IBP-domain index "
                 f"reflects its inclusion of sanitation — adequate for {ib['sanit_adequate_pct']}% of the "
                 f"population, with {ib['pop_le5_pct']:.0f}% living in sectors with ≤5% inadequate sanitation — "
                 f"and its omission of informal-settlement residence, a salient axis of tuberculosis risk in "
                 f"this setting, motivating the setting-specific composite.")
else:
    print("AVISO: /tmp/ibp_sensitivity.json ausente — rode scripts/125; Tabela S8 omitida.")

doc.save(OUT); print("Saved:",OUT)
