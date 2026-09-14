import pandas as pd
import geopandas as gpd

print("1. Loading 2022 SP Census Tracts & Population...")
df_pop = pd.read_csv("Data/SP_Agregados_2022/Agregados_por_setores_basico_BR_20250417.csv", sep=";", encoding="latin1", dtype={"CD_SETOR": str})

df_pop_sp = df_pop[(df_pop["CD_UF"] == "35") | (df_pop["CD_UF"] == 35)].copy()

if df_pop_sp["v0001"].dtype == object:
    df_pop_sp["v0001"] = df_pop_sp["v0001"].str.replace(",", ".").astype(float)
else:
    df_pop_sp["v0001"] = df_pop_sp["v0001"].astype(float)

gdf_2022 = gpd.read_file("Data/SP_setores_2022/SP_setores_CD2022.shp").to_crs("EPSG:4674")
gdf_2022["CD_SETOR"] = gdf_2022["CD_SETOR"].astype(str)

print("Merging shapes with population...")
gdf_2022 = gdf_2022.merge(df_pop_sp[["CD_SETOR", "v0001"]], on="CD_SETOR", how="left")

print("2. Loading 2010 Favela Boundaries...")
gdf_2010 = gpd.read_file("Data/SP_AGSN_2010/AglomeradosSubnormais2010_Limites.shp")
gdf_2010["uf"] = gdf_2010["uf"].astype(str)
favelas_2010_sp = gdf_2010[gdf_2010["uf"] == "35"].to_crs("EPSG:4674")

print("3. Classifying 2022 Census Tract Favelas...")
favelas_2022_sp = gdf_2022[gdf_2022["NM_FCU"].notna()].copy()
non_favelas_2022_sp = gdf_2022[gdf_2022["NM_FCU"].isna()].copy()

joined = gpd.sjoin(favelas_2022_sp, favelas_2010_sp, how="left", predicate="intersects")
# Must drop duplicates caused by intersection cardinality
joined = joined.drop_duplicates(subset=["CD_SETOR"])
favelas_2022_sp = favelas_2022_sp.drop_duplicates(subset=["CD_SETOR"])

favelas_2022_sp["lives_in_favela_2010"] = favelas_2022_sp["CD_SETOR"].isin(joined[joined["index_right"].notna()]["CD_SETOR"]).astype(int)

def get_tier(row):
    if row["lives_in_favela_2010"] == 1: return "Established (Pre-2010)"
    return "Newly Formed (Post-2010)"

favelas_2022_sp["favela_tier"] = favelas_2022_sp.apply(get_tier, axis=1)

print("\n--- POPULATION DENOMINATORS (IBGE 2022) ---")
pop_established_favela = favelas_2022_sp[favelas_2022_sp["favela_tier"] == "Established (Pre-2010)"]["v0001"].sum()
pop_newly_formed_favela = favelas_2022_sp[favelas_2022_sp["favela_tier"] == "Newly Formed (Post-2010)"]["v0001"].sum()
pop_non_favela = non_favelas_2022_sp["v0001"].sum()

print(f"Non-Favela Pop: {pop_non_favela:,.0f}")
print(f"Established Favela Pop: {pop_established_favela:,.0f}")
print(f"Newly Formed Favela Pop: {pop_newly_formed_favela:,.0f}")

print("\n--- INCIDENCE CALCULATION ---")
# 64,275 geocoded out of 220,049 (Scale Factor: 3.42355)
cases_established = 2482
cases_newly_formed = 881
cases_non_favela = 60912

scaled_established = cases_established * 3.42355
scaled_newly_formed = cases_newly_formed * 3.42355
scaled_non = cases_non_favela * 3.42355

def calc_inc(annual_cases, pop):
    if pop == 0 or pd.isna(pop): return 0
    return (annual_cases / pop) * 100000

print(f"Non-Favela Annual TB Incidence: {calc_inc(scaled_non/12, pop_non_favela):.1f} per 100k")
print(f"Established Favela Annual TB Incidence: {calc_inc(scaled_established/12, pop_established_favela):.1f} per 100k")
print(f"Newly Formed Favela Annual TB Incidence: {calc_inc(scaled_newly_formed/12, pop_newly_formed_favela):.1f} per 100k")
print("Done!")
