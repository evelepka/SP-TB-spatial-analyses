"""Generate the manuscript Methods as a Word document (.docx).
Formal manuscript prose. METHODS describe who/how (criteria, definitions, process, provenance,
extraction dates) — NO counts/rates/validation numbers (those belong in Results). Method
parameters/thresholds (age >=15, period, >=30 days, ~5,000-adult floor, >=10 cases, top 20%,
age bands, geocoding tiers) are kept, as they define the procedure.
Output: Drive .../SP-TB-spatial-analyses/Reports/SP_TB_Manuscript_Methods.docx
"""
from docx import Document
from docx.shared import Pt, RGBColor
OUT=("/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/"
     "My Drive/WHO modelling Project/SP-TB-spatial-analyses/Reports/SP_TB_Manuscript_Methods.docx")

doc=Document()
st=doc.styles["Normal"]; st.font.name="Calibri"; st.font.size=Pt(11)
def H(txt,lvl=1):
    h=doc.add_heading(txt,level=lvl)
    for r in h.runs: r.font.color.rgb=RGBColor(0x0d,0x2b,0x45)
    return h
def P(txt):
    p=doc.add_paragraph(txt); p.paragraph_format.space_after=Pt(6); return p

doc.add_heading("Methods",level=0)

H("Study design and setting")
P("We conducted a population-based ecological spatial study of tuberculosis (TB) and its adverse "
  "treatment outcomes across the State of São Paulo, Brazil, the most populous Brazilian state and "
  "the one reporting the largest absolute TB burden. The study covered notifications over 2013–2024 "
  "in adults aged 15 years or older with new or relapse TB resident in the State. The unit of "
  "analysis was a statewide regionalisation of census sectors (defined below); social vulnerability "
  "was measured at the census-sector level and aggregated to the region.")

H("Data sources and extraction")
P("Individual TB notification and residential-address records were extracted from TBWeb, the São "
  "Paulo State mandatory TB notification system, in January 2025 (data lock), comprising notifications "
  "from 2013 to 2024. A TB death was ascertained jointly from two sources: the TBWeb treatment outcome "
  "of death from tuberculosis, and record linkage to the Mortality Information System (SIM), counting "
  "tuberculosis (ICD-10 A15–A19) recorded on any line of the death certificate (underlying or "
  "contributing cause). "
  "Sociodemographic variables and the census-sector cartographic mesh were obtained from the 2022 "
  "Demographic Census (IBGE). Residential addresses were geocoded using the national statistical "
  "address registry (Cadastro Nacional de Endereços para Fins Estatísticos, CNEFE 2022; IBGE). The "
  "place-based vulnerability composite was externally validated against the official São Paulo Social "
  "Vulnerability Index (Índice Paulista de Vulnerabilidade Social, IPVS 2022; SEADE Foundation).")

H("Study population and case definitions")
P("The unit of analysis was the incident tuberculosis episode: each new or relapse notification in "
  "adults (≥15 years) with a notification date in 2013–2024 was counted as one incident case, so that "
  "a person with more than one distinct episode over the period (for example, a new case and a later "
  "relapse) contributed more than one case. Notifications were excluded by design when the "
  "residence was institutional and recorded as incarceration — prison TB follows a distinct "
  "institutional epidemiology and is treated as a separate target population — and when no fixed "
  "residence was recorded, since such notifications cannot be assigned to a residential census "
  "sector. Analyses were further restricted to incident episodes: new cases and relapses. "
  "Retreatments after loss to follow-up or after failure were excluded, as they represent "
  "continuation of the same disease episode rather than a distinct incident case. A study-population "
  "flow diagram reports the number excluded at each step (Results; Figure S1).")
P("Three outcomes were examined. TB incidence used the notification rate as a proxy for incidence "
  "(new and relapse cases per adult population). TB mortality was expressed both as a rate per adult "
  "population and as a proportion of notified cases, using the integrated marker defined above and "
  "counting each death once per person. Treatment abandonment — the Brazilian programmatic category, defined as interruption of "
  "treatment for ≥30 consecutive days and equivalent to WHO loss to follow-up — was computed among "
  "cases with an evaluated treatment outcome.")

H("Geocoding to the census sector")
P("Each notification was assigned to its 2022 census sector through a hierarchical procedure, and a "
  "precision tier was retained for every case. Residential addresses were matched to CNEFE 2022, "
  "which resolves informal addresses in favelas and peripheral areas that the postal-code field does "
  "not, by an exact street-and-number match (tier T1), a street-name match (T2) or an approximate "
  "(fuzzy) street match (T3); where the street could not be matched, the address was assigned to the "
  "centroid sector of its neighbourhood (T4). Every geocoded point was then assigned to a census "
  "sector by spatial overlay on the official 2022 sector mesh, rather than by the CNEFE-reported "
  "sector code, because for a subset of records the reported code carried a preliminary (“P”) suffix "
  "absent from the final mesh; as these preliminary sectors are disproportionately favela (subnormal "
  "agglomeration) sectors, the spatial overlay both maximised recovery and avoided a differential "
  "loss of favela cases. Notifications whose street address did not match CNEFE, but which carried a "
  "valid postal code, were assigned the census sector most frequently observed — among successfully "
  "geocoded cases — for that postal code, i.e. a CNEFE-internal postal-code centroid (tier T5); an "
  "external postal-code service was deliberately avoided, as it would displace favela residents into "
  "adjacent formal areas. Only genuinely institutional sectors (barracks, encampments, indigenous "
  "villages, prisons and other collective establishments) were excluded from the residential frame. "
  "As a sensitivity analysis, all analyses were repeated excluding the coarsest, postal-code-level "
  "(T5) assignments.")

H("Territorial unit: statewide regionalisation")
P("No official sub-municipal cartographic unit is uniform enough for small-area rate estimation in "
  "São Paulo: the census sector is too small to yield stable rates, whereas municipalities and "
  "administrative districts are too coarse and highly heterogeneous in population — in the state "
  "capital, the absence of an official neighbourhood layer collapses the city into a small number of "
  "very large districts. Contiguous census sectors were therefore aggregated into approximately "
  "equal-population, socially homogeneous neighbourhoods (“regions”) by a spatially constrained, "
  "greedy region-growing algorithm to a floor of about 5,000 adults per region, minimising "
  "within-region household-income heterogeneity. Favela / subnormal-agglomeration sectors and "
  "non-favela sectors were regionalised separately, so that a favela is never merged with an "
  "adjacent affluent area. Rates were estimated for regions with at least 10 pooled cases over "
  "2013–2024.")

H("Age standardisation")
P("All rates were age-standardised by indirect standardisation against a São Paulo State internal "
  "reference, using eight adult age bands (15–19, 20–24, 25–29, 30–39, 40–49, 50–59, 60–69 and ≥70 "
  "years). Indirect standardisation was chosen because population-denominated rates in small areas "
  "are unstable under direct standardisation; the expected count in each region was derived from its "
  "age structure and the state age-specific reference rates.")

H("Place-based vulnerability index")
P("A place-based social-vulnerability index was constructed from four domains available at the "
  "census-sector level in the 2022 Census: household income (head of household), adult illiteracy, "
  "mean residents per household, and favela / subnormal-agglomeration status. Each domain was "
  "standardised (z-score) across sectors, oriented so that higher values indicate greater "
  "deprivation, and averaged; the index was anchored at the census sector and aggregated to the "
  "region by population weighting. The composite was externally validated against the official IPVS "
  "2022. Candidate domains that were tested and excluded — sanitation, precarious housing (cortiço), "
  "race, and population density — are described in the Supplement.")

H("Statistical analysis")
P("Analyses addressed four questions. First, the geographic concentration of each outcome was "
  "summarised with the Gini coefficient and Lorenz curve, ranking regions by their age-standardised "
  "rate and plotting the cumulative share of events against the cumulative share of the adult "
  "population; because rare events inflate the naïve Gini, concentration was de-noised by "
  "split-sample cross-fit, and we additionally report the share of events occurring in the 20% of "
  "the population living in the highest-rate regions. Second, hotspot regions were defined, for each "
  "lens, by accumulating regions ranked by age-standardised rate until 20% of the adult population "
  "was covered; the association with deprivation was quantified as the standardised mean difference "
  "(Cohen’s d) of each vulnerability component between hotspot and non-hotspot regions, and "
  "dose-response was characterised with population-weighted generalised additive models relating "
  "each outcome to each continuous vulnerability indicator. Third, overlap between the incidence, "
  "mortality, abandonment and vulnerability hotspots was displayed with a four-set Venn diagram of "
  "the top-20% regions and summarised by pairwise overlap. Fourth, temporal stability was assessed "
  "with the annual Gini coefficient, the year-to-year Jaccard overlap of independently re-selected "
  "hotspots, and the rank autocorrelation of region rates across time lags.")
P("Analyses were performed in Python 3 (pandas, geopandas, numpy, scipy, scikit-learn, pygam, "
  "matplotlib) and R (eulerr).")

H("Ethics")
p=P("[To be completed: secondary, anonymised routine surveillance data; ethics approval by "
    "«committee» under protocol «number»; individual informed consent waived.]")
for r in p.runs: r.italic=True

doc.save(OUT)
print("Saved:",OUT)
