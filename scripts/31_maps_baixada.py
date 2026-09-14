"""Maps for Baixada Santista — mirroring scripts 26 (GSP overview) and 27 (capital zoom).

Outputs:
  - mapa_Baixada_panel.png — 2×2 panel: rate per municipality, %FCU, hotspots, income
  - mapa_Baixada_top3_zoom.png — zoom on Santos+SV+Guarujá showing vuln_score, hotspots, rate
  - mapa_Baixada_interativo.html — folium interactive map
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import folium
from folium.features import GeoJsonTooltip
import os

SPATIAL = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
IBGE_EXT = f"{SPATIAL}/IBGE_2022_extended"
OUT = f"{IBGE_EXT}/mapas_Baixada"
os.makedirs(OUT, exist_ok=True)

BAIXADA_CD_MUN = {"3506359","3513504","3518701","3522109","3531100",
                  "3537602","3541000","3548500","3551009"}


def norm_setor(s):
    if pd.isna(s): return None
    s = str(s).strip()
    return s[:-1] if s.endswith("P") else s


# ===== Load data =====
print("Loading data...")
sp = pd.read_csv("/tmp/baixada_setores_priorizados_v2.csv",
                 dtype={"CD_SETOR": str}, low_memory=False)
print(f"Setores priorizados: {len(sp):,}")

# Shapefile
sec22 = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"] = sec22["CD_MUN"].astype(str)
sec22["CD_SETOR"] = sec22["CD_SETOR"].astype(str)
sec22["AREA_KM2"] = pd.to_numeric(sec22["AREA_KM2"], errors="coerce")

sec_bx = sec22[sec22["CD_MUN"].isin(BAIXADA_CD_MUN)].copy()
sec_bx = sec_bx.merge(
    sp[["CD_SETOR","vuln_score","rate_per_100k","n_cases","v0001",
        "is_fcu","renda_2022","density_km2"]],
    on="CD_SETOR", how="left"
)

# Residential filter
sec_an = sec_bx[sec_bx["n_cases"].notna()].copy()

# Hotspots
total_pop = sec_an["v0001"].sum()
sec_inc = sec_an[sec_an["n_cases"] > 0].sort_values("rate_per_100k", ascending=False)
sec_inc["cum_pop"] = sec_inc["v0001"].cumsum()
hotspot_setores = set(sec_inc[sec_inc["cum_pop"] <= total_pop * 0.05]["CD_SETOR"])
sec_an["is_hot"] = sec_an["CD_SETOR"].isin(hotspot_setores)
print(f"Setores residenciais: {len(sec_an):,}, hotspots: {sec_an['is_hot'].sum():,}")

# Aggregate by município
mun_agg = sec_an.groupby(["CD_MUN","NM_MUN"]).agg(
    pop=("v0001","sum"),
    casos=("n_cases","sum"),
    area=("AREA_KM2","sum"),
    fcu_pop=("v0001", lambda x: x[sec_an.loc[x.index,"is_fcu"]==1].sum()),
).reset_index()
mun_agg["taxa"] = mun_agg["casos"]/(mun_agg["pop"]*5)*1e5
mun_agg["pct_fcu"] = mun_agg["fcu_pop"]/mun_agg["pop"]*100

mun_geo = sec_bx.dissolve(by="CD_MUN", as_index=False)[["CD_MUN","geometry"]]
mun_geo = mun_geo.merge(mun_agg, on="CD_MUN")
print(f"Municípios: {len(mun_geo)}")

# ===== PNG panel 2x2 =====
print("\nGenerating PNG panel 2x2...")
fig, axs = plt.subplots(2, 2, figsize=(16, 14))
fig.suptitle("Análise TB Baixada Santista (2020-2024) — via CNEFE 2022",
             fontsize=18, fontweight="bold", y=0.99)

# A) TB rate per municipality
ax = axs[0,0]
mun_geo.plot(column="taxa", cmap="YlOrRd", legend=True,
             ax=ax, edgecolor="white", linewidth=0.4,
             legend_kwds={"label": "Taxa /100k pa", "shrink": 0.65})
# Add municipality labels
for r in mun_geo.itertuples():
    c = r.geometry.centroid
    ax.annotate(r.NM_MUN, xy=(c.x, c.y), ha="center", fontsize=8,
                color="#222", weight="bold",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8, edgecolor="none"))
ax.set_title("A) Taxa de TB por município", fontsize=14)
ax.axis("off")

# B) % FCU per municipality
ax = axs[0,1]
mun_geo.plot(column="pct_fcu", cmap="Blues", legend=True,
             ax=ax, edgecolor="white", linewidth=0.4,
             legend_kwds={"label": "% pop em FCU", "shrink": 0.65})
ax.set_title("B) Proporção da pop em FCU (IBGE 2022)", fontsize=14)
ax.axis("off")

# C) Hotspots over light background
ax = axs[1,0]
sec_an.plot(ax=ax, color="lightgrey", edgecolor="none")
hot = sec_an[sec_an["is_hot"]]
hot.plot(ax=ax, color="#c0392b", edgecolor="none", alpha=0.85)
mun_geo.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=0.5)
ax.set_title(f"C) Hotspots: top 5% pop por taxa ({len(hot):,} setores)", fontsize=14)
ax.axis("off")
ax.legend(handles=[
    Patch(facecolor="#c0392b", alpha=0.85, label="Hotspot (top 5%)"),
    Patch(facecolor="lightgrey", label="Resto Baixada"),
], loc="lower right", fontsize=10)

# D) Income (log)
ax = axs[1,1]
sec_an["log_renda"] = np.log10(sec_an["renda_2022"].clip(lower=100))
sec_inc2 = sec_an[sec_an["renda_2022"].notna()]
sec_inc2.plot(column="log_renda", cmap="RdYlGn", legend=True,
              ax=ax, edgecolor="none",
              legend_kwds={"label": "log10(Renda média R$)", "shrink": 0.65})
mun_geo.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=0.4)
ax.set_title("D) Renda média do responsável (IBGE 2022)", fontsize=14)
ax.axis("off")

plt.tight_layout()
png_path = f"{OUT}/mapa_Baixada_panel.png"
plt.savefig(png_path, dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print(f"  Saved: {png_path}")

# ===== Zoom Santos + SV + Guarujá + Cubatão (the 4 hot ones) =====
print("\nGenerating zoom panel for top 4 municipalities...")
top4 = {"3548500","3551009","3518701","3513504"}  # Santos, SV, Guarujá, Cubatão

# Top 5% vuln target (for comparison) — set columns BEFORE slicing top4_geo
sp_sorted = sp.sort_values("vuln_score", ascending=False)
sp_sorted["cum_pop"] = sp_sorted["v0001"].cumsum()
vuln_target = set(sp_sorted[sp_sorted["cum_pop"] <= total_pop*0.05]["CD_SETOR"])
sec_an["is_vuln_target"] = sec_an["CD_SETOR"].isin(vuln_target)
sec_an["both"] = sec_an["is_hot"] & sec_an["is_vuln_target"]

top4_geo = sec_an[sec_an["CD_MUN"].isin(top4)]
xmin, ymin, xmax, ymax = top4_geo.total_bounds

fig, axs = plt.subplots(1, 3, figsize=(22, 9))
fig.suptitle("Santos + São Vicente + Guarujá + Cubatão — TB e Vulnerabilidade",
             fontsize=17, fontweight="bold", y=1.02)

# A) Vuln score
ax = axs[0]
sec_an.plot(ax=ax, color="lightgrey", edgecolor="none")
top4_geo.plot(column="vuln_score", cmap="RdPu", ax=ax, edgecolor="none",
              vmin=top4_geo["vuln_score"].quantile(0.05),
              vmax=top4_geo["vuln_score"].quantile(0.95),
              legend=True, legend_kwds={"label":"vuln_score","shrink":0.5})
ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax)
ax.set_title("A) Índice composto de vulnerabilidade", fontsize=13)
ax.axis("off")

# B) Hotspots vs vuln target
ax = axs[1]
sec_an.plot(ax=ax, color="lightgrey", edgecolor="none")
sub_only_v = top4_geo[top4_geo["is_vuln_target"] & ~top4_geo["is_hot"]]
sub_only_h = top4_geo[top4_geo["is_hot"] & ~top4_geo["is_vuln_target"]]
sub_both = top4_geo[top4_geo["both"]]
sub_only_v.plot(ax=ax, color="#9b59b6", edgecolor="none", alpha=0.7)
sub_only_h.plot(ax=ax, color="#c0392b", edgecolor="none", alpha=0.85)
sub_both.plot(ax=ax, color="#2c3e50", edgecolor="none", alpha=0.9)
ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax)
ax.set_title("B) Hotspots empíricos × target índice", fontsize=13)
ax.axis("off")
ax.legend(handles=[
    Patch(facecolor="#9b59b6", alpha=0.7, label=f"Só target índice ({len(sub_only_v):,})"),
    Patch(facecolor="#c0392b", alpha=0.85, label=f"Só hotspot empírico ({len(sub_only_h):,})"),
    Patch(facecolor="#2c3e50", alpha=0.9, label=f"Ambos ({len(sub_both):,})"),
], loc="lower right", fontsize=10)

# C) Observed rate (log)
ax = axs[2]
sec_an.plot(ax=ax, color="lightgrey", edgecolor="none")
top4_inc = top4_geo[top4_geo["n_cases"]>0].copy()
top4_inc["log_rate"] = np.log10(top4_inc["rate_per_100k"].clip(lower=1))
top4_inc.plot(column="log_rate", cmap="YlOrRd", ax=ax, edgecolor="none",
              legend=True, legend_kwds={"label":"log10(taxa /100k pa)","shrink":0.5})
ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax)
ax.set_title("C) Taxa observada de TB", fontsize=13)
ax.axis("off")

plt.tight_layout()
png_zoom = f"{OUT}/mapa_Baixada_zoom_top4.png"
plt.savefig(png_zoom, dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print(f"  Saved: {png_zoom}")

# Stats for legend
overlap_pct = len(sub_both) / max(len(top4_geo[top4_geo['is_hot']]), 1) * 100
print(f"  Hotspot × vuln target overlap in top4 munis: {len(sub_both):,} ({overlap_pct:.1f}%)")

# ===== Folium interactive =====
print("\nGenerating Folium interactive map...")
center = [-23.95, -46.35]  # Center Baixada
m = folium.Map(location=center, zoom_start=11, tiles="cartodbpositron")

mun_geo_4326 = mun_geo.to_crs(4326)
folium.Choropleth(
    geo_data=mun_geo_4326.__geo_interface__,
    data=mun_geo,
    columns=["CD_MUN","taxa"],
    key_on="feature.properties.CD_MUN",
    fill_color="YlOrRd", fill_opacity=0.7, line_opacity=0.4,
    legend_name="TB rate / 100k py (município)",
    name="Taxa por município",
).add_to(m)

tooltip = GeoJsonTooltip(
    fields=["NM_MUN","pop","casos","taxa","pct_fcu"],
    aliases=["Município:","População:","Casos TB:","Taxa /100k:","% FCU:"],
    localize=True, sticky=False, labels=True,
)
folium.GeoJson(
    mun_geo_4326, name="Detalhes município",
    tooltip=tooltip,
    style_function=lambda x: {"fillColor":"transparent","color":"#333","weight":1,"fillOpacity":0},
).add_to(m)

# Top 220 hotspots → CircleMarkers (all of them — small set, no need to limit)
hot_4326 = sec_an[sec_an["is_hot"]].to_crs(4326).copy()
hot_4326["centroid"] = hot_4326.geometry.centroid
hot_layer = folium.FeatureGroup(name=f"Hotspots top 5% ({len(hot_4326)} setores)", show=True)
for _, r in hot_4326.iterrows():
    c = r["centroid"]
    bairro_nm = r["NM_BAIRRO"] if pd.notna(r["NM_BAIRRO"]) else "(sem nome)"
    fcu_lbl = " | FCU" if r["is_fcu"] == 1 else ""
    renda_lbl = f"<br>Renda: R$ {r['renda_2022']:.0f}" if pd.notna(r['renda_2022']) else ""
    popup_text = (f"<b>{r['NM_MUN']}</b> — {bairro_nm}{fcu_lbl}<br>"
                  f"Pop: {int(r['v0001']):,}<br>"
                  f"Casos: {int(r['n_cases'])}<br>"
                  f"Taxa: {r['rate_per_100k']:.0f}/100k pa{renda_lbl}")
    folium.CircleMarker(
        location=[c.y, c.x], radius=5,
        color="#a93226", weight=1, fill=True,
        fill_color="#c0392b", fill_opacity=0.7,
        popup=folium.Popup(popup_text, max_width=250),
    ).add_to(hot_layer)
hot_layer.add_to(m)

# FCU layer
fcu_sec = sec_an[sec_an["is_fcu"]==1].to_crs(4326)
fcu_grouped = fcu_sec.dissolve(by="NM_FCU", as_index=False)[["NM_FCU","NM_MUN","geometry"]]
print(f"  N FCUs distintas: {len(fcu_grouped):,}")
folium.GeoJson(
    fcu_grouped, name=f"FCU IBGE 2022 ({len(fcu_grouped)} favelas)",
    show=False,
    style_function=lambda x: {"fillColor":"#2980b9","color":"#1f618d","weight":0.5,"fillOpacity":0.4},
    tooltip=folium.GeoJsonTooltip(fields=["NM_FCU","NM_MUN"], aliases=["FCU:","Município:"]),
).add_to(m)

folium.LayerControl(position="topright", collapsed=False).add_to(m)

legend_html = f"""
<div style="position:fixed; bottom:20px; left:20px; z-index:1000;
            background:white; padding:12px 16px; border-radius:6px;
            box-shadow:0 2px 8px rgba(0,0,0,0.2); font-family:sans-serif; font-size:12px;">
<b style="color:#1a3d5c;">Análise Baixada Santista via CNEFE 2022</b><br>
9.447 casos TB (Comunidade, Novo+Recidiva, 2020-2024)<br>
9.207 (97,5%) com endereço CNEFE matched<br>
Hotspots = top 5% pop por taxa de TB<br>
FCU = Favelas e Comunidades Urbanas (IBGE 2022)
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

html_path = f"{OUT}/mapa_Baixada_interativo.html"
m.save(html_path)
print(f"  Saved: {html_path}")

print("\n=== Arquivos finais ===")
for f in sorted(os.listdir(OUT)):
    fpath = os.path.join(OUT, f)
    size = os.path.getsize(fpath)
    print(f"  {f} — {size/1024:.1f} KB")
