"""Mapas da análise GSP — TB hotspots, vulnerabilidade, FCU.

Output:
  - PNG estático: panel de 4 mapas (taxa por município, hotspots, FCU, renda)
  - HTML interativo: choropleth GSP por município + marcadores hotspots
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import folium
from folium.features import GeoJsonTooltip
import zipfile, io, unicodedata, re

SPATIAL = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
IBGE_EXT = f"{SPATIAL}/IBGE_2022_extended"
OUT = f"{IBGE_EXT}/mapas_GSP"
import os; os.makedirs(OUT, exist_ok=True)


def norm(s):
    if pd.isna(s):
        return None
    s = str(s).strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s)


def norm_setor(s):
    if pd.isna(s):
        return None
    s = str(s).strip()
    return s[:-1] if s.endswith("P") else s


# ========== 1) Cohort + IBGE ==========
print("Carregando dados...")
co = pd.read_csv("/tmp/cohort_with_cnefe.csv", low_memory=False)
co_m = co[co["setor_cnefe"].notna()].copy()
co_m["CD_SETOR"] = co_m["setor_cnefe"].apply(norm_setor)

# IBGE
agg = pd.read_csv(
    f"{SPATIAL}/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv",
    sep=";", encoding="latin-1", decimal=",",
    usecols=["CD_SETOR", "v0001", "v0005"],
    dtype={"CD_SETOR": str}, low_memory=False,
)
agg["v0001"] = pd.to_numeric(agg["v0001"], errors="coerce").fillna(0)
agg["v0005"] = pd.to_numeric(agg["v0005"], errors="coerce")

with zipfile.ZipFile(f"{IBGE_EXT}/renda_responsavel.zip") as z:
    fname = [n for n in z.namelist() if n.endswith(".csv")][0]
    with z.open(fname) as f:
        renda = pd.read_csv(io.TextIOWrapper(f, encoding="latin-1"),
                            sep=";", decimal=",",
                            usecols=["CD_SETOR", "V06004"],
                            dtype={"CD_SETOR": str}, low_memory=False)
renda["renda_2022"] = pd.to_numeric(renda["V06004"], errors="coerce")
agg = agg.merge(renda[["CD_SETOR", "renda_2022"]], on="CD_SETOR", how="left")

# Shapefile setores
sec22 = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"] = sec22["CD_MUN"].astype(str)
sec22["CD_SETOR"] = sec22["CD_SETOR"].astype(str)
sec22["AREA_KM2"] = pd.to_numeric(sec22["AREA_KM2"], errors="coerce")
gsp_munis = set(sec22[sec22["NM_CONCURB"] == "São Paulo/SP"]["CD_MUN"].unique())
sec_gsp = sec22[sec22["CD_MUN"].isin(gsp_munis)].copy()
sec_gsp = sec_gsp.merge(agg, on="CD_SETOR", how="left")
sec_gsp["is_fcu"] = sec_gsp["NM_FCU"].notna().astype(int)
sec_gsp["density_km2"] = sec_gsp["v0001"] / sec_gsp["AREA_KM2"]

# Casos por setor
cases_per = co_m.groupby("CD_SETOR").size().rename("n_cases").reset_index()
sec_gsp = sec_gsp.merge(cases_per, on="CD_SETOR", how="left")
sec_gsp["n_cases"] = sec_gsp["n_cases"].fillna(0)
sec_gsp["py"] = sec_gsp["v0001"] * 5
sec_gsp["rate_per_100k"] = np.where(sec_gsp["py"] > 0,
                                     sec_gsp["n_cases"] / sec_gsp["py"] * 100_000, 0)

# Filtra setores residenciais
sec_an = sec_gsp[sec_gsp["CD_TIPO"].astype(str).isin(["0", "1"]) &
                 (sec_gsp["v0001"] >= 100)].copy()

# Hotspots: top 5% pop
total_pop = sec_an["v0001"].sum()
sorted_by_rate = sec_an[sec_an["n_cases"] > 0].sort_values("rate_per_100k", ascending=False)
sorted_by_rate["cum_pop"] = sorted_by_rate["v0001"].cumsum()
hotspot_setores = set(sorted_by_rate[sorted_by_rate["cum_pop"] <= total_pop * 0.05]["CD_SETOR"])
sec_an["is_hotspot"] = sec_an["CD_SETOR"].isin(hotspot_setores).astype(int)
print(f"Setores residenciais GSP: {len(sec_an):,}")
print(f"Hotspots (top 5% pop): {sec_an['is_hotspot'].sum():,}")

# Agregação por município
mun_agg = sec_an.groupby(["CD_MUN", "NM_MUN"]).agg(
    pop=("v0001", "sum"),
    casos=("n_cases", "sum"),
    area=("AREA_KM2", "sum"),
    fcu_pop=("v0001", lambda x: x[sec_an.loc[x.index, "is_fcu"] == 1].sum()),
).reset_index()
mun_agg["taxa"] = mun_agg["casos"] / (mun_agg["pop"] * 5) * 100_000
mun_agg["pct_fcu"] = mun_agg["fcu_pop"] / mun_agg["pop"] * 100

# Junta com geometria municipal (dissolved)
mun_geo = sec_gsp.dissolve(by="CD_MUN", as_index=False)[["CD_MUN", "geometry"]]
mun_geo = mun_geo.merge(mun_agg, on="CD_MUN")

print(f"Municípios para mapa: {len(mun_geo):,}")

# ========== 2) PNG estático — panel 2x2 ==========
print("\nGerando PNG estático (panel 2x2)...")
fig, axs = plt.subplots(2, 2, figsize=(16, 16))
fig.suptitle("Análise TB Grande SP (2020-2024) — via CNEFE 2022",
             fontsize=18, fontweight="bold", y=0.98)

# Mapa 1: Taxa de TB por município
ax = axs[0, 0]
mun_geo.plot(column="taxa", cmap="YlOrRd", legend=True,
             ax=ax, edgecolor="white", linewidth=0.4,
             legend_kwds={"label": "Taxa por 100k pa", "shrink": 0.7})
ax.set_title("Taxa de incidência por município", fontsize=14, pad=10)
ax.axis("off")

# Mapa 2: % população em FCU por município
ax = axs[0, 1]
mun_geo.plot(column="pct_fcu", cmap="Blues", legend=True,
             ax=ax, edgecolor="white", linewidth=0.4,
             legend_kwds={"label": "% pop em FCU", "shrink": 0.7})
ax.set_title("Proporção da população em FCU 2022", fontsize=14, pad=10)
ax.axis("off")

# Mapa 3: Hotspots (top 5% pop) sobre fundo cinza
ax = axs[1, 0]
sec_an.plot(ax=ax, color="lightgrey", edgecolor="none")
hotspot_sec = sec_an[sec_an["is_hotspot"] == 1]
hotspot_sec.plot(ax=ax, color="#c0392b", edgecolor="none", alpha=0.85)
mun_geo.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=0.5)
ax.set_title(f"Hotspots: top 5% pop por taxa de TB ({len(hotspot_sec):,} setores)",
             fontsize=14, pad=10)
ax.axis("off")
# Legenda manual
from matplotlib.patches import Patch
ax.legend(handles=[
    Patch(facecolor="#c0392b", alpha=0.85, label="Hotspot (top 5%)"),
    Patch(facecolor="lightgrey", label="Resto GSP"),
], loc="lower right", fontsize=10)

# Mapa 4: Renda média por setor (escala log)
ax = axs[1, 1]
sec_an["log_renda"] = np.log10(sec_an["renda_2022"].clip(lower=100))
sec_an_inc = sec_an[sec_an["renda_2022"].notna()]
sec_an_inc.plot(column="log_renda", cmap="RdYlGn", legend=True,
                ax=ax, edgecolor="none",
                legend_kwds={"label": "log10(Renda média R$)", "shrink": 0.7})
mun_geo.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=0.4)
ax.set_title("Renda média do responsável (IBGE 2022)", fontsize=14, pad=10)
ax.axis("off")

plt.tight_layout()
png_path = f"{OUT}/mapa_GSP_panel.png"
plt.savefig(png_path, dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print(f"  PNG salvo: {png_path}")

# ========== 3) HTML interativo (Folium) ==========
print("\nGerando mapa interativo Folium...")

# Centro GSP: aprox SP capital
center = [-23.55, -46.65]
m = folium.Map(location=center, zoom_start=10, tiles="cartodbpositron")

# Layer 1: Taxa por município (choropleth)
mun_geo_4326 = mun_geo.to_crs(4326)
folium.Choropleth(
    geo_data=mun_geo_4326.__geo_interface__,
    data=mun_geo,
    columns=["CD_MUN", "taxa"],
    key_on="feature.properties.CD_MUN",
    fill_color="YlOrRd",
    fill_opacity=0.7,
    line_opacity=0.4,
    legend_name="Taxa TB / 100k pa (município)",
    name="Taxa por município",
).add_to(m)

# Tooltip em cada município
tooltip = GeoJsonTooltip(
    fields=["NM_MUN", "pop", "casos", "taxa", "pct_fcu"],
    aliases=["Município:", "População:", "Casos TB:", "Taxa /100k:", "% FCU:"],
    localize=True,
    sticky=False,
    labels=True,
)
folium.GeoJson(
    mun_geo_4326,
    name="Detalhes município",
    tooltip=tooltip,
    style_function=lambda x: {"fillColor": "transparent", "color": "#333", "weight": 1, "fillOpacity": 0},
).add_to(m)

# Layer 2: Hotspots (top 5%) — agrupados por bairro para reduzir tamanho
# Pega centroide de cada hotspot setor pra marcar
hot_4326 = sec_an[sec_an["is_hotspot"] == 1].to_crs(4326).copy()
print(f"  N hotspots a marcar: {len(hot_4326):,} (será limitado a 500 para performance)")

# Limita a 500 hotspots com maior taxa pra não sobrecarregar
hot_top = hot_4326.nlargest(500, "rate_per_100k").copy()
hot_top["centroid"] = hot_top.geometry.centroid

# FeatureGroup para hotspots
hot_layer = folium.FeatureGroup(name="Top 500 setores hotspot", show=True)
for _, r in hot_top.iterrows():
    c = r["centroid"]
    bairro_nm = r["NM_BAIRRO"] if pd.notna(r["NM_BAIRRO"]) else "(sem nome)"
    fcu_lbl = " | FCU" if r["is_fcu"] == 1 else ""
    popup_text = (f"<b>{r['NM_MUN']}</b> — {bairro_nm}{fcu_lbl}<br>"
                  f"Pop: {int(r['v0001']):,}<br>"
                  f"Casos: {int(r['n_cases'])}<br>"
                  f"Taxa: {r['rate_per_100k']:.0f}/100k pa<br>"
                  f"Renda: R$ {r['renda_2022']:.0f}" if pd.notna(r['renda_2022']) else "")
    folium.CircleMarker(
        location=[c.y, c.x],
        radius=4,
        color="#a93226",
        weight=1,
        fill=True,
        fill_color="#c0392b",
        fill_opacity=0.7,
        popup=folium.Popup(popup_text, max_width=250),
    ).add_to(hot_layer)
hot_layer.add_to(m)

# Layer 3: FCU polygons (favelas IBGE)
print(f"  Adicionando FCU layer...")
fcu_sec = sec_an[sec_an["is_fcu"] == 1].to_crs(4326)
# Pra reduzir tamanho, agrupa por NM_FCU
fcu_grouped = fcu_sec.dissolve(by="NM_FCU", as_index=False)[["NM_FCU", "NM_MUN", "geometry"]]
print(f"  N FCUs distintas: {len(fcu_grouped):,}")
folium.GeoJson(
    fcu_grouped,
    name="Favelas / FCU IBGE 2022",
    show=False,
    style_function=lambda x: {"fillColor": "#2980b9", "color": "#1f618d", "weight": 0.5, "fillOpacity": 0.4},
    tooltip=folium.GeoJsonTooltip(fields=["NM_FCU", "NM_MUN"], aliases=["FCU:", "Município:"]),
).add_to(m)

# Layer control + legenda
folium.LayerControl(position="topright", collapsed=False).add_to(m)

# Legenda
legend_html = """
<div style="position: fixed; bottom: 20px; left: 20px; z-index: 1000;
            background: white; padding: 12px 16px; border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2); font-family: sans-serif; font-size: 12px;">
<b style="color:#1a3d5c;">Análise GSP via CNEFE 2022</b><br>
51,016 casos TB (Comunidade, Novo+Recidiva, 2020-2024)<br>
46,303 (90,8%) com endereço CNEFE matched<br>
Hotspots = top 5% pop por taxa de TB<br>
FCU = Favelas e Comunidades Urbanas (IBGE 2022)
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

html_path = f"{OUT}/mapa_GSP_interativo.html"
m.save(html_path)
print(f"  HTML interativo salvo: {html_path}")

print("\n=== Arquivos finais ===")
for f in os.listdir(OUT):
    fpath = os.path.join(OUT, f)
    size = os.path.getsize(fpath)
    print(f"  {f} — {size/1024:.1f} KB")
