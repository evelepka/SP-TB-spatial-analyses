"""Mapas focados na capital SP — vuln_score, hotspots e validação do índice.

Outputs:
  - mapa_capital_vuln_hotspots.png — 2 painéis: vuln_score vs hotspots empíricos
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

SPATIAL = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data"
IBGE_EXT = f"{SPATIAL}/IBGE_2022_extended"
OUT = f"{IBGE_EXT}/mapas_GSP"

# --- carrega setores priorizados (já tem vuln_score) ---
sp = pd.read_csv("/tmp/setores_priorizados_GSP.csv", dtype={"CD_SETOR": str})
print(f"Setores priorizados carregados: {len(sp):,}")

# --- shapefile + filtro GSP ---
sec22 = gpd.read_file(f"{SPATIAL}/SP_setores_2022/SP_setores_CD2022.shp")
sec22["CD_MUN"] = sec22["CD_MUN"].astype(str)
sec22["CD_SETOR"] = sec22["CD_SETOR"].astype(str)
gsp_munis = set(sec22[sec22["NM_CONCURB"] == "São Paulo/SP"]["CD_MUN"].unique())
sec_gsp = sec22[sec22["CD_MUN"].isin(gsp_munis)].copy()

# Merge vuln_score, rate
sec_gsp = sec_gsp.merge(
    sp[["CD_SETOR", "vuln_score", "rate_per_100k", "n_cases", "v0001",
        "is_fcu", "renda_2022", "density_km2"]],
    on="CD_SETOR", how="left"
)

# Hotspots top 5% pop
sec_an = sec_gsp[sec_gsp["n_cases"].notna()].copy()
total_pop = sec_an["v0001"].sum()
sorted_by_rate = sec_an[sec_an["n_cases"] > 0].sort_values("rate_per_100k", ascending=False)
sorted_by_rate["cum_pop"] = sorted_by_rate["v0001"].cumsum()
hotspot_setores = set(sorted_by_rate[sorted_by_rate["cum_pop"] <= total_pop * 0.05]["CD_SETOR"])

# Top 5% pop pelo índice composto
sorted_by_vuln = sec_an.sort_values("vuln_score", ascending=False).copy()
sorted_by_vuln["cum_pop"] = sorted_by_vuln["v0001"].cumsum()
vuln_target = set(sorted_by_vuln[sorted_by_vuln["cum_pop"] <= total_pop * 0.05]["CD_SETOR"])

sec_an["is_hot"] = sec_an["CD_SETOR"].isin(hotspot_setores)
sec_an["is_vuln_target"] = sec_an["CD_SETOR"].isin(vuln_target)
sec_an["both"] = sec_an["is_hot"] & sec_an["is_vuln_target"]

# Bounds capital SP (CD_MUN = 3550308)
cap = sec_an[sec_an["CD_MUN"] == "3550308"]
print(f"Setores capital SP: {len(cap):,}")
xmin, ymin, xmax, ymax = cap.total_bounds

# ========== Figura: 1x3 panel para capital ==========
print("Gerando mapa capital SP...")
fig, axs = plt.subplots(1, 3, figsize=(24, 10))
fig.suptitle("Capital de São Paulo (município) — TB e Vulnerabilidade",
             fontsize=18, fontweight="bold", y=1.02)

# Panel A: vuln_score
ax = axs[0]
sec_an.plot(ax=ax, color="lightgrey", edgecolor="none")
cap.plot(column="vuln_score", cmap="RdPu", ax=ax, edgecolor="none",
         vmin=cap["vuln_score"].quantile(0.05),
         vmax=cap["vuln_score"].quantile(0.95),
         legend=True, legend_kwds={"label": "vuln_score", "shrink": 0.5})
ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax)
ax.set_title("A) Índice composto de vulnerabilidade", fontsize=14)
ax.axis("off")

# Panel B: hotspots empíricos vs vuln target
ax = axs[1]
sec_an.plot(ax=ax, color="lightgrey", edgecolor="none")
cap_only_v = cap[cap["is_vuln_target"] & ~cap["is_hot"]]
cap_only_h = cap[cap["is_hot"] & ~cap["is_vuln_target"]]
cap_both = cap[cap["both"]]
cap_only_v.plot(ax=ax, color="#9b59b6", edgecolor="none", alpha=0.7)
cap_only_h.plot(ax=ax, color="#c0392b", edgecolor="none", alpha=0.85)
cap_both.plot(ax=ax, color="#2c3e50", edgecolor="none", alpha=0.9)
ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax)
ax.set_title("B) Hotspots empíricos × target índice", fontsize=14)
ax.axis("off")
ax.legend(handles=[
    Patch(facecolor="#9b59b6", alpha=0.7, label=f"Só target índice ({len(cap_only_v):,})"),
    Patch(facecolor="#c0392b", alpha=0.85, label=f"Só hotspot empírico ({len(cap_only_h):,})"),
    Patch(facecolor="#2c3e50", alpha=0.9, label=f"Ambos ({len(cap_both):,})"),
], loc="lower right", fontsize=10)

# Panel C: TB rate
ax = axs[2]
sec_an.plot(ax=ax, color="lightgrey", edgecolor="none")
cap_inc = cap[cap["n_cases"] > 0].copy()
cap_inc["log_rate"] = np.log10(cap_inc["rate_per_100k"].clip(lower=1))
cap_inc.plot(column="log_rate", cmap="YlOrRd", ax=ax, edgecolor="none",
             legend=True, legend_kwds={"label": "log10(taxa /100k pa)", "shrink": 0.5})
ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax)
ax.set_title("C) Taxa observada de TB", fontsize=14)
ax.axis("off")

plt.tight_layout()
png_path = f"{OUT}/mapa_capital_vuln_hotspots.png"
plt.savefig(png_path, dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print(f"  PNG salvo: {png_path}")

# Estatísticas para legenda
print(f"\nCapital SP: {len(cap):,} setores residenciais")
print(f"  Hotspots empíricos (top 5%): {cap['is_hot'].sum():,}")
print(f"  Target índice (top 5%):       {cap['is_vuln_target'].sum():,}")
print(f"  Sobreposição (ambos):         {cap['both'].sum():,} "
      f"({cap['both'].sum()/cap['is_hot'].sum()*100:.1f}% dos hotspots)")
