import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns
import contextily as cx
import os

# Create output directory for figures
os.makedirs("figures", exist_ok=True)

# Load data
print("Loading spatial linkage data...")
df = pd.read_csv("Data/cep_spatial_linkage.csv")
print(f"Loaded {len(df)} geocoded records.")

# 1. Bar Chart: Top Favelas
print("Generating Top Favelas Bar Chart...")
favela_counts = df[df["lives_in_favela"] == 1]["NM_FCU"].value_counts().head(15)

plt.figure(figsize=(12, 8))
sns.barplot(x=favela_counts.values, y=favela_counts.index, palette="viridis")
plt.title("Top 15 Favelas / Comunidades Urbanas by TB Case Load", fontsize=16)
plt.xlabel("Number of Unique Addresses (CEPs)", fontsize=12)
plt.ylabel("Favela Name (IBGE 2022)", fontsize=12)
plt.tight_layout()
plt.savefig("figures/Chart_Top_Favelas.png", dpi=300)
plt.close()
print("Saved figures/Chart_Top_Favelas.png")

# 2. Maps setup
print("Converting to GeoDataFrame for mapping...")
# Drop invalid coordinates
df_valid = df.dropna(subset=["lon", "lat"]).copy()
gdf = gpd.GeoDataFrame(
    df_valid, 
    geometry=gpd.points_from_xy(df_valid.lon, df_valid.lat),
    crs="EPSG:4326"
)

# Project to Web Mercator (EPSG:3857) for plotting with Contextily basemaps
gdf_web = gdf.to_crs(epsg=3857)

# Separate into favela and non-favela
gdf_favela = gdf_web[gdf_web["lives_in_favela"] == 1]
gdf_non = gdf_web[gdf_web["lives_in_favela"] == 0]

# Filter out extreme outliers (e.g., incorrect coords outside of SP state)
# Rough bounding box for SP state in Web Mercator: Note: Web Mercator uses large meters.
# It's safer to bound by lat/lon first. SP bounds are roughly -53 to -44 lon, -25 to -19 lat
valid_bounds = df_valid[
    (df_valid["lon"] > -54) & (df_valid["lon"] < -44) & 
    (df_valid["lat"] > -26) & (df_valid["lat"] < -19)
]
gdf_bounded = gpd.GeoDataFrame(
    valid_bounds, 
    geometry=gpd.points_from_xy(valid_bounds.lon, valid_bounds.lat),
    crs="EPSG:4326"
).to_crs(epsg=3857)

# 3. Density / Hexbin Map
print("Generating Statewide Density Map...")
fig, ax = plt.subplots(figsize=(12, 12))
# We use hexbin on the coordinate arrays
hb = ax.hexbin(
    gdf_bounded.geometry.x, 
    gdf_bounded.geometry.y, 
    gridsize=50, 
    cmap='inferno', 
    bins='log',
    alpha=0.8
)
cx.add_basemap(ax, source=cx.providers.CartoDB.Positron)
cb = fig.colorbar(hb, ax=ax)
cb.set_label('log10(Case Density)')
ax.set_axis_off()
ax.set_title("TB Case Density Distribution (State of São Paulo)", fontsize=16)
plt.tight_layout()
plt.savefig("figures/Map_Density_Statewide.png", dpi=300, bbox_inches="tight")
plt.close()
print("Saved figures/Map_Density_Statewide.png")

# 4. Zoomed-in Map: São Paulo Metropolitan Area Scatter
print("Generating SP Metro Scatter Map...")
# SP Metro rough bounds in EPSG:4326
sp_lon = (-47.0, -45.5)
sp_lat = (-24.0, -23.0)

gdf_sp_metro = df_valid[
    (df_valid["lon"] >= sp_lon[0]) & (df_valid["lon"] <= sp_lon[1]) &
    (df_valid["lat"] >= sp_lat[0]) & (df_valid["lat"] <= sp_lat[1])
]

gdf_sp = gpd.GeoDataFrame(
    gdf_sp_metro, 
    geometry=gpd.points_from_xy(gdf_sp_metro.lon, gdf_sp_metro.lat),
    crs="EPSG:4326"
).to_crs(epsg=3857)

gdf_sp_favela = gdf_sp[gdf_sp["lives_in_favela"] == 1]
gdf_sp_non = gdf_sp[gdf_sp["lives_in_favela"] == 0]

fig, ax = plt.subplots(figsize=(14, 12))

# Plot non-favela first (background)
gdf_sp_non.plot(ax=ax, markersize=10, color="blue", alpha=0.1, label="Outside Favela")
# Plot favela cases on top
gdf_sp_favela.plot(ax=ax, markersize=15, color="red", alpha=0.8, edgecolor="white", linewidth=0.3, label="In Favela")

cx.add_basemap(ax, source=cx.providers.CartoDB.Positron)

ax.set_axis_off()
ax.set_title("TB Cases in São Paulo Metropolitan Area", fontsize=18)
# Add legend with custom markers to fix alpha transparency issues in legend
leg = ax.legend(fontsize=14, loc="lower right", frameon=True, framealpha=0.9)
for lh in leg.legend_handles: 
    lh.set_alpha(1)
    
plt.tight_layout()
plt.savefig("figures/Map_Favela_Hotspots.png", dpi=300, bbox_inches="tight")
plt.close()
print("Saved figures/Map_Favela_Hotspots.png")

print("All visualizations completed successfully!")
