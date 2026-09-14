"""Map and characteristic profile of top hotspot bairros (20% pop window).

Generates:
  1. /tmp/bairro_hotspot_map.png        — static overview map (GSP + Baixada)
  2. /tmp/bairro_hotspot_zoom.png       — zoom on SP capital + Santos/SV/Guarujá
  3. /tmp/bairro_hotspot_interativo.html — folium interactive map
  4. /tmp/bairro_profile_table.csv      — selected vs. non-selected characteristics

Unit: NM_DIST for SP capital · NM_BAIRRO for other municipalities
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
import folium
from folium.features import GeoJsonTooltip
import zipfile, io, os

SPATIAL = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
IBGE_EXT = f"{SPATIAL}/IBGE_2022_extended"
CAPITAL   = "3550308"
TARGET_WINDOW = 0.20   # top bairros covering 20% of total pop

def norm_setor(s):
    if pd.isna(s): return None
    s = str(s).strip()
    return s[:-1] if s.endswith("P") else s

# ============================================================
# 1) Shapefile + census
# ============================================================
print("Loading shapefile + census variables...")
sec22 = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"]   = sec22["CD_MUN"].astype(str)
sec22["CD_SETOR"] = sec22["CD_SETOR"].astype(str)
sec22["AREA_KM2"] = pd.to_numeric(sec22["AREA_KM2"], errors="coerce")

agg = pd.read_csv(
    f"{SPATIAL}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",
    sep=";", encoding="latin-1", decimal=",",
    usecols=["CD_SETOR","v0001","v0005"],
    dtype={"CD_SETOR": str}, low_memory=False,
)
agg["v0001"] = pd.to_numeric(agg["v0001"], errors="coerce").fillna(0)
agg["v0005"] = pd.to_numeric(agg["v0005"], errors="coerce")   # avg residents per household

with zipfile.ZipFile(f"{IBGE_EXT}/renda_responsavel.zip") as z:
    fname = [n for n in z.namelist() if n.endswith(".csv")][0]
    with z.open(fname) as f:
        renda = pd.read_csv(io.TextIOWrapper(f, encoding="latin-1"),
                            sep=";", decimal=",",
                            usecols=["CD_SETOR","V06004"],
                            dtype={"CD_SETOR": str}, low_memory=False)
renda["renda_2022"] = pd.to_numeric(renda["V06004"], errors="coerce")
agg = agg.merge(renda[["CD_SETOR","renda_2022"]], on="CD_SETOR", how="left")

GSP_MUNIS = set(sec22[sec22["NM_CONCURB"] == "São Paulo/SP"]["CD_MUN"].unique())
BX_MUNIS  = {"3506359","3513504","3518701","3522109","3531100","3537602","3541000","3548500","3551009"}
ALL_MUNIS = GSP_MUNIS | BX_MUNIS

sec = sec22[sec22["CD_MUN"].isin(ALL_MUNIS)].copy()
sec = sec.merge(agg, on="CD_SETOR", how="left")
sec_res = sec[
    sec["CD_TIPO"].astype(str).isin(["0","1"]) &
    (sec["v0001"] >= 100)
].copy()
sec_res["is_fcu"] = sec_res["NM_FCU"].notna().astype(int)

# ============================================================
# 2) Geo unit assignment (same as script 35)
# ============================================================
sec_res["geo_unit"] = sec_res.apply(
    lambda r: f"dist_{r['CD_DIST']}" if str(r["CD_MUN"]) == CAPITAL
              else (f"bairro_{r['CD_MUN']}_{r['NM_BAIRRO']}" if pd.notna(r["NM_BAIRRO"])
                    else f"dist_{r['CD_DIST']}"),
    axis=1
)
sec_res["geo_label"] = sec_res.apply(
    lambda r: f"SP/{r['NM_DIST']}" if str(r["CD_MUN"]) == CAPITAL
              else (f"{r['NM_MUN']}/{r['NM_BAIRRO']}" if pd.notna(r["NM_BAIRRO"])
                    else f"{r['NM_MUN']}/{r['NM_DIST']}"),
    axis=1
)
sec_res["region"] = sec_res["CD_MUN"].map(
    lambda x: "Baixada" if x in BX_MUNIS else "GSP"
)

sec2unit = sec_res.set_index("CD_SETOR")["geo_unit"].to_dict()
print(f"  Geo units: {sec_res['geo_unit'].nunique():,}")

# ============================================================
# 3) Cases with year
# ============================================================
print("Loading cases...")
gsp_co = pd.read_csv("/tmp/cohort_with_cnefe.csv", low_memory=False, dtype={"sinan_clean": str})
gsp_co["key"]      = gsp_co["sinan_clean"].str.zfill(7)
gsp_co["CD_SETOR"] = gsp_co["setor_cnefe"].apply(norm_setor)

bx_co = pd.read_csv("/tmp/cohort_baixada_with_cnefe_v2.csv", low_memory=False, dtype={"sinan_clean": str})
bx_co["match_tier"] = bx_co["cnefe_match"].astype(str).str.extract(r"^(T\d)")
bx_co = bx_co[bx_co["match_tier"].isin(["T1","T2","T3"])]
bx_co["key"]      = bx_co["sinan_clean"].str.zfill(7)
bx_co["CD_SETOR"] = bx_co["setor_cnefe"].apply(norm_setor)

spatial_yr = pd.read_csv(
    f"{SPATIAL}/cohort_with_spatial.csv",
    usecols=["sinan_clean","notification_date"], dtype={"sinan_clean": str}, low_memory=False
)
spatial_yr["key"]  = spatial_yr["sinan_clean"].str.strip()
spatial_yr["year"] = pd.to_datetime(spatial_yr["notification_date"], errors="coerce").dt.year
spatial_yr = (spatial_yr[spatial_yr["year"].between(2020,2024)]
              .drop_duplicates("key")[["key","year"]])

all_co = pd.concat([gsp_co[["key","CD_SETOR"]], bx_co[["key","CD_SETOR"]]], ignore_index=True)
all_co = all_co.merge(spatial_yr, on="key", how="left")
all_co["year"]     = all_co["year"].fillna(2022).astype(int)
all_co             = all_co.dropna(subset=["CD_SETOR"])
all_co["geo_unit"] = all_co["CD_SETOR"].map(sec2unit)
all_co             = all_co.dropna(subset=["geo_unit"])

# ============================================================
# 4) Bairro-level aggregation
# ============================================================
print("Aggregating to bairro level...")

def wavg(vals, weights):
    mask = vals.notna() & weights.notna() & (weights > 0)
    if mask.sum() == 0: return np.nan
    return (vals[mask] * weights[mask]).sum() / weights[mask].sum()

bairro_stats = sec_res.groupby("geo_unit").apply(lambda g: pd.Series({
    "pop":          g["v0001"].sum(),
    "area_km2":     g["AREA_KM2"].sum(),
    "n_setores":    len(g),
    "fcu_pop":      g.loc[g["is_fcu"]==1, "v0001"].sum(),
    "renda_w":      wavg(g["renda_2022"], g["v0001"]),
    "v0005_w":      wavg(g["v0005"],      g["v0001"]),  # avg residents/household
    "NM_MUN":       g["NM_MUN"].iloc[0],
    "region":       g["region"].iloc[0],
    "geo_label":    g["geo_label"].iloc[0],
})).reset_index()

bairro_stats["density_km2"] = bairro_stats["pop"] / bairro_stats["area_km2"]
bairro_stats["pct_fcu"]     = bairro_stats["fcu_pop"] / bairro_stats["pop"] * 100

# Cases
cases_total = all_co.groupby("geo_unit").size().rename("n_cases").reset_index()
bairro_stats = bairro_stats.merge(cases_total, on="geo_unit", how="left")
bairro_stats["n_cases"]   = bairro_stats["n_cases"].fillna(0)
bairro_stats["rate_100k"] = bairro_stats["n_cases"] / (bairro_stats["pop"] * 5) * 1e5

# Year-by-year cases for variability
for yr in [2020,2021,2022,2023,2024]:
    yc = all_co[all_co["year"]==yr].groupby("geo_unit").size().rename(f"n_{yr}")
    bairro_stats = bairro_stats.merge(yc, on="geo_unit", how="left")
    bairro_stats[f"n_{yr}"] = bairro_stats[f"n_{yr}"].fillna(0).astype(int)

bairro_stats["cases_yr_avg"] = bairro_stats["n_cases"] / 5
bairro_stats["cases_yr_std"] = bairro_stats[["n_2020","n_2021","n_2022","n_2023","n_2024"]].std(axis=1)
bairro_stats["cases_cv"]     = bairro_stats["cases_yr_std"] / (bairro_stats["cases_yr_avg"] + 0.1)

# ============================================================
# 5) Identify top bairros (TARGET_WINDOW)
# ============================================================
total_pop    = bairro_stats["pop"].sum()
total_cases  = bairro_stats["n_cases"].sum()
ranked       = bairro_stats.sort_values("rate_100k", ascending=False).copy()
ranked["cum_pop"]    = ranked["pop"].cumsum()
ranked["cum_cases"]  = ranked["n_cases"].cumsum()
hot_mask     = ranked["cum_pop"] <= total_pop * TARGET_WINDOW
ranked["is_hotspot"] = hot_mask
n_hot        = hot_mask.sum()
pct_cases    = ranked[hot_mask]["n_cases"].sum() / total_cases * 100
print(f"\nTop {TARGET_WINDOW*100:.0f}% pop window → {n_hot} bairros → {pct_cases:.1f}% of cases")

# ============================================================
# 6) Comparison table: selected vs. non-selected
# ============================================================
print("\nBuilding comparison table...")

def pop_size_pct(grp, lo, hi):
    mask = (grp["pop"] >= lo) & (grp["pop"] < hi)
    return mask.mean() * 100

def fmt_med_iqr(series):
    return f"{series.median():,.0f} ({series.quantile(0.25):,.0f}–{series.quantile(0.75):,.0f})"

hot   = ranked[ranked["is_hotspot"]]
nohot = ranked[~ranked["is_hotspot"]]

rows = []
metrics = [
    ("N bairros",         lambda g: f"{len(g):,}", None),
    ("Total population",  lambda g: f"{g['pop'].sum():,.0f}", None),
    ("% of all TB cases", lambda g: f"{g['n_cases'].sum()/total_cases*100:.1f}%", None),
    ("─── Size ───",      None, None),
    ("Pop median (IQR)",  lambda g: fmt_med_iqr(g["pop"]),          None),
    ("% pop < 2,000",     lambda g: f"{pop_size_pct(g,0,2000):.0f}%",        None),
    ("% pop 2,000–5,000", lambda g: f"{pop_size_pct(g,2000,5000):.0f}%",     None),
    ("% pop 5,000–10,000",lambda g: f"{pop_size_pct(g,5000,10000):.0f}%",    None),
    ("% pop 10,000–50,000",lambda g: f"{pop_size_pct(g,10000,50000):.0f}%",  None),
    ("% pop ≥ 50,000",    lambda g: f"{pop_size_pct(g,50000,1e9):.0f}%",     None),
    ("─── Density ───",   None, None),
    ("Density /km² median (IQR)", lambda g: fmt_med_iqr(g["density_km2"]),   None),
    ("─── Income ───",    None, None),
    ("Mean income R$ median (IQR)", lambda g: fmt_med_iqr(g["renda_w"].dropna()), None),
    ("─── Crowding ───",  None, None),
    ("Residents/household median (IQR)", lambda g: fmt_med_iqr(g["v0005_w"].dropna()), None),
    ("─── FCU (favela/slum) ───", None, None),
    ("% bairros with any FCU",  lambda g: f"{(g['fcu_pop']>0).mean()*100:.0f}%", None),
    ("% population in FCU",     lambda g: f"{g['fcu_pop'].sum()/g['pop'].sum()*100:.1f}%", None),
    ("─── TB burden ───",  None, None),
    ("TB rate /100k/yr median (IQR)", lambda g: fmt_med_iqr(g["rate_100k"]),  None),
    ("Cases/yr per bairro median (IQR)", lambda g: fmt_med_iqr(g["cases_yr_avg"]), None),
    ("Year-to-year CV median (IQR)", lambda g: fmt_med_iqr(g["cases_cv"]),    None),
]

print(f"\n{'Characteristic':<42} {'SELECTED (top 20% pop)':>26} {'NOT selected':>26}")
print("-"*96)
for label, fn, _ in metrics:
    if fn is None:
        print(f"\n{label}")
        continue
    v_hot   = fn(hot)
    v_nohot = fn(nohot)
    print(f"  {label:<40} {v_hot:>26} {v_nohot:>26}")

# Save to CSV
profile_rows = []
for label, fn, _ in metrics:
    if fn is None: continue
    profile_rows.append({
        "characteristic": label,
        "selected_top20pct": fn(hot),
        "not_selected": fn(nohot)
    })
pd.DataFrame(profile_rows).to_csv("/tmp/bairro_profile_table.csv", index=False)

# ============================================================
# 7) Dissolve geometries to bairro level
# ============================================================
print("\nDissolving geometries to bairro level (may take ~1 min)...")
sec_proj = sec_res[["CD_SETOR","geo_unit","v0001","geometry"]].copy()
bairro_geo = sec_proj.dissolve(by="geo_unit", as_index=False)[["geo_unit","geometry"]]
bairro_geo = bairro_geo.merge(
    ranked[["geo_unit","geo_label","NM_MUN","region","pop","n_cases","rate_100k",
            "cases_yr_avg","renda_w","pct_fcu","density_km2","is_hotspot"]],
    on="geo_unit", how="left"
)
print(f"  Bairro geometries: {len(bairro_geo):,}")

# Municipality outlines
mun_outline = sec_res.dissolve(by="CD_MUN", as_index=False)[["CD_MUN","geometry"]]
mun_outline = mun_outline.merge(
    sec_res.groupby("CD_MUN")["NM_MUN"].first().reset_index(), on="CD_MUN"
)

# ============================================================
# 8) Static map — full GSP + Baixada overview
# ============================================================
print("Generating overview map...")
fig, ax = plt.subplots(1, 1, figsize=(18, 15))

bg   = bairro_geo[~bairro_geo["is_hotspot"]]
hot_geo = bairro_geo[bairro_geo["is_hotspot"]].copy()

bg.plot(ax=ax, color="#e8e8e8", edgecolor="none")
hot_geo.plot(ax=ax, column="rate_100k", cmap="YlOrRd", edgecolor="none",
             vmin=hot_geo["rate_100k"].quantile(0.05),
             vmax=hot_geo["rate_100k"].quantile(0.95),
             legend=True,
             legend_kwds={"label":"TB rate /100k·yr (pooled 2020–2024)", "shrink":0.5})
mun_outline.boundary.plot(ax=ax, color="#333333", linewidth=0.5)

# Labels for large hotspot municipalities
major_munis = ["Santos","São Vicente","Guarujá","Osasco","Diadema","São Bernardo do Campo",
               "Guarulhos","Cubatão","São Paulo"]
for _, r in mun_outline.iterrows():
    if r["NM_MUN"] in major_munis:
        c = r["geometry"].centroid
        ax.annotate(r["NM_MUN"], (c.x, c.y), ha="center", fontsize=8, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.75, edgecolor="none"))

ax.set_title(
    f"Top hotspot bairros — GSP + Baixada Santista\n"
    f"Top 20% of population by TB rate · {n_hot} bairros · {pct_cases:.0f}% of all TB cases (2020–2024)",
    fontsize=15, fontweight="bold"
)
ax.axis("off")
handles = [
    mpatches.Patch(facecolor="#e8e8e8", label=f"Non-hotspot ({len(bg):,} bairros)"),
    mpatches.Patch(facecolor="#c0392b", label=f"Hotspot ({n_hot} bairros — shaded by rate)"),
]
ax.legend(handles=handles, loc="lower left", fontsize=11)

plt.tight_layout()
plt.savefig("/tmp/bairro_hotspot_map.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print("  Saved: /tmp/bairro_hotspot_map.png")

# ============================================================
# 9) Zoom panel: SP capital + Baixada top-4
# ============================================================
print("Generating zoom panel...")
fig, axes = plt.subplots(1, 2, figsize=(20, 10))
fig.suptitle("Hotspot bairros — zoom: SP capital (left) · Santos/Guarujá/São Vicente (right)",
             fontsize=14, fontweight="bold")

sp_geo = bairro_geo[bairro_geo["NM_MUN"] == "São Paulo"]
bx_geo = bairro_geo[bairro_geo["region"] == "Baixada"]

for ax, gdf, title in [
    (axes[0], sp_geo, "São Paulo capital — hotspot distritos"),
    (axes[1], bx_geo, "Baixada Santista — hotspot bairros"),
]:
    bg_sub = gdf[~gdf["is_hotspot"]]
    hot_sub = gdf[gdf["is_hotspot"]]
    bg_sub.plot(ax=ax, color="#e8e8e8", edgecolor="#cccccc", linewidth=0.3)
    if len(hot_sub) > 0:
        hot_sub.plot(ax=ax, column="rate_100k", cmap="YlOrRd", edgecolor="none",
                     vmin=0, vmax=hot_sub["rate_100k"].quantile(0.95),
                     legend=True,
                     legend_kwds={"label":"TB rate /100k·yr", "shrink":0.5})
    # Label top 8 hotspots
    top8 = hot_sub.nlargest(8, "rate_100k")
    for _, r in top8.iterrows():
        c = r["geometry"].centroid
        short = str(r["geo_label"]).split("/")[-1][:18]
        ax.annotate(short, (c.x, c.y), ha="center", fontsize=7,
                    bbox=dict(boxstyle="round,pad=0.15", facecolor="white", alpha=0.8, edgecolor="none"))
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.axis("off")

plt.tight_layout()
plt.savefig("/tmp/bairro_hotspot_zoom.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print("  Saved: /tmp/bairro_hotspot_zoom.png")

# ============================================================
# 10) Folium interactive map
# ============================================================
print("Generating interactive map...")
bg_4326   = bairro_geo[~bairro_geo["is_hotspot"]].to_crs(4326)
hot_4326  = bairro_geo[bairro_geo["is_hotspot"]].to_crs(4326)

center = [-23.7, -46.5]
m = folium.Map(location=center, zoom_start=9, tiles="cartodbpositron")

# Non-hotspot layer (thin, grey)
folium.GeoJson(
    bg_4326,
    name="Non-hotspot bairros",
    show=True,
    style_function=lambda x: {"fillColor":"#dddddd","color":"#aaaaaa","weight":0.3,"fillOpacity":0.4},
    tooltip=GeoJsonTooltip(
        fields=["geo_label","pop","rate_100k","cases_yr_avg"],
        aliases=["Bairro:","Pop:","TB rate /100k:","Cases/yr avg:"],
        localize=True
    )
).add_to(m)

# Hotspot layer — coloured by rate
import branca.colormap as cm
rate_min = float(hot_4326["rate_100k"].quantile(0.05))
rate_max = float(hot_4326["rate_100k"].quantile(0.95))
colormap = cm.LinearColormap(["#ffffb2","#fd8d3c","#bd0026"], vmin=rate_min, vmax=rate_max,
                               caption="TB rate /100k·yr (pooled 2020–2024)")
colormap.add_to(m)

def hot_style(feature):
    rate = feature["properties"].get("rate_100k") or 0
    return {"fillColor": colormap(min(max(rate, rate_min), rate_max)),
            "color":"#333","weight":0.5,"fillOpacity":0.8}

folium.GeoJson(
    hot_4326,
    name=f"Hotspot bairros — top 20% pop ({n_hot} units)",
    show=True,
    style_function=hot_style,
    tooltip=GeoJsonTooltip(
        fields=["geo_label","pop","rate_100k","cases_yr_avg","pct_fcu","renda_w"],
        aliases=["Bairro:","Pop:","TB rate /100k·yr:","Cases/yr avg:","% em FCU:","Renda média R$:"],
        localize=True
    )
).add_to(m)

# Municipality outlines
mun_4326 = mun_outline.to_crs(4326)
folium.GeoJson(
    mun_4326,
    name="Municípios",
    show=True,
    style_function=lambda x: {"fillColor":"none","color":"#222","weight":1.2,"fillOpacity":0},
    tooltip=GeoJsonTooltip(fields=["NM_MUN"], aliases=["Município:"])
).add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

legend_html = f"""
<div style="position:fixed;bottom:20px;left:20px;z-index:1000;background:white;
            padding:12px 16px;border-radius:6px;box-shadow:0 2px 8px rgba(0,0,0,0.2);
            font-family:sans-serif;font-size:12px;max-width:280px;">
<b style="color:#1a3d5c;">Hotspot bairros — GSP + Baixada</b><br>
<b>Geocodificação:</b> CNEFE 2022 (90–97% cobertura)<br>
<b>Período:</b> 2020–2024 (NOVO + RECIDIVA)<br>
<b>Seleção:</b> top bairros = 20% da população total<br>
<b>{n_hot} bairros</b> · <b>{pct_cases:.0f}%</b> de todos os casos<br>
Cor: taxa TB /100k·ano (pooled 5 anos)
</div>"""
m.get_root().html.add_child(folium.Element(legend_html))

m.save("/tmp/bairro_hotspot_interativo.html")
print("  Saved: /tmp/bairro_hotspot_interativo.html")
print("\nDone.")
