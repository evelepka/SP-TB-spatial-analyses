"""Table 1 (manuscript) — descriptive characteristics of the REGIONS on the episode-level base.
Groups:
metropolitan (Greater SP + Baixada) vs interior, each split into incidence-hotspot (top-20% pop) vs
non-hotspot; plus favela regions (subset) and the State total. Per group: size, burden share, crude
rates, and the population-weighted vulnerability profile. Output: /tmp/table1.csv (+ prints).
"""
import pandas as pd, geopandas as gpd, numpy as np, zipfile
SP="/DATA_ROOT/Data"
BAIXADA={"3506359","3513504","3518701","3522109","3531100","3537602","3541000","3548500","3551009"}
BANDS=["V01034","V01035","V01036","V01037","V01038","V01039","V01040","V01041"]
T=12
# sectors -> CD_MUN, adult pop, region_id, metro flag
sec=gpd.read_file(f"{SP}/SP_setores_2022/SP_setores_CD2022.shp")[["CD_SETOR","CD_MUN","CD_DIST","CD_TIPO","NM_CONCURB"]]
sec["CD_SETOR"]=sec["CD_SETOR"].astype(str); sec["CD_MUN"]=sec["CD_MUN"].astype(str)
with zipfile.ZipFile(f"{SP}/IBGE_2022_extended/demografia.zip") as z:
    dem=pd.read_csv(z.open("Agregados_por_setores_demografia_BR.csv"),sep=";",encoding="latin-1",decimal=",",usecols=["CD_setor"]+BANDS,dtype={"CD_setor":str},low_memory=False)
dem["pop_adult"]=dem[BANDS].apply(pd.to_numeric,errors="coerce").fillna(0).sum(axis=1)
sec=sec.merge(dem.rename(columns={"CD_setor":"CD_SETOR"})[["CD_SETOR","pop_adult"]],on="CD_SETOR",how="left")
sec["pop_adult"]=sec["pop_adult"].fillna(0)
sec=sec[sec["CD_TIPO"].astype(str).isin(["0","1"])&(sec["pop_adult"]>0)].copy()
GSP=set(sec.loc[sec["NM_CONCURB"]=="São Paulo/SP","CD_MUN"].unique()); METRO=GSP|BAIXADA
sec["metro"]=sec["CD_MUN"].isin(METRO)
rg=pd.read_csv("/tmp/regions_sectors.csv",dtype={"CD_SETOR":str})[["CD_SETOR","region_id"]]
sec=sec.merge(rg,on="CD_SETOR",how="left"); sec["region_id"]=sec["region_id"].fillna("DIST_"+sec["CD_DIST"].astype(str))
# region -> metro (pop-weighted majority of its sectors)
rm=sec.groupby("region_id").apply(lambda x:np.average(x["metro"],weights=x["pop_adult"])>0.5).rename("metro")

d=pd.read_csv("/tmp/region_units.csv",dtype={"region_id":str}).merge(rm,on="region_id",how="left")
d["metro"]=d["metro"].fillna(False)
d=d[d["pop"]>0].copy()

def prof(g):
    def pw(c):
        t=g.dropna(subset=[c]); return np.average(t[c],weights=t["pop"]) if len(t) else np.nan
    return pd.Series({
        "n_reg":len(g),
        "pop":int(g["pop"].sum()),
        "cases":int(g["n"].sum()),
        "inc":g["n"].sum()/g["pop"].sum()/T*1e5,
        "mort":g["nd"].sum()/g["pop"].sum()/T*1e5,
        "aband_pct":g["na"].sum()/g["ne"].sum()*100 if g["ne"].sum()>0 else np.nan,
        "income":pw("income"),"illit":pw("illit"),"residents":pw("residents"),
        "favela_pct":pw("favela"),"vuln":pw("vuln"),
    })
TOTpop=d["pop"].sum(); TOTcase=d["n"].sum(); TOTdeath=d["nd"].sum(); TOTltfu=d["na"].sum()
rows=[]
for lab,mask in [("Metropolitan — hotspot",d["metro"]&d["hs_inc"]),
                 ("Metropolitan — non-hotspot",d["metro"]&~d["hs_inc"]),
                 ("Interior — hotspot",~d["metro"]&d["hs_inc"]),
                 ("Interior — non-hotspot",~d["metro"]&~d["hs_inc"]),
                 ("Favela regions (subset)",d["favela"]>50),
                 ("State total",d["region_id"].notna())]:
    s=prof(d[mask]); s["group"]=lab; s["pop_pct"]=s["pop"]/TOTpop*100; s["cases_pct"]=s["cases"]/TOTcase*100
    s["deaths_pct"]=d.loc[mask,"nd"].sum()/TOTdeath*100; s["ltfu_pct"]=d.loc[mask,"na"].sum()/TOTltfu*100  # share of state deaths / LTFU
    rows.append(s)
tab=pd.DataFrame(rows).set_index("group")

# ── clinical / programmatic block (episode-level, joined to each region's group) ──
gmap=d[["region_id","metro","hs_inc","favela"]]
rc=pd.read_csv("/tmp/region_cases.csv",dtype={"sinan_clean":str,"region_id":str})[["sinan_clean","region_id","year"]]
Mc=pd.read_csv(f"{SP}/cohort_with_spatial.csv",low_memory=False,dtype={"sinan_clean":str},
    usecols=["sinan_clean","notification_date","age_tb","case_type","address_type",
             "case_outcome","hiv","clinical_form_1","disease_discovery","hosp_admission",
             "tx_administration_type","alcoholism","drug_use","tobacco_use","diabetes"])
Mc["year"]=pd.to_datetime(Mc["notification_date"],errors="coerce").dt.year
cl=Mc[(Mc["age_tb"]>=15)&Mc["year"].between(2013,2024)&(Mc["address_type"]=="ENDERECO PADRAO")
      &Mc["case_type"].isin(["Novo","Recidiva"])].drop_duplicates(["sinan_clean","year"])[
      ["sinan_clean","year","case_outcome","hiv","clinical_form_1","disease_discovery","hosp_admission",
       "tx_administration_type","alcoholism","drug_use","tobacco_use","diabetes"]]
epi=rc.merge(cl,on=["sinan_clean","year"],how="left").merge(gmap,on="region_id",how="left")
epi["metro"]=epi["metro"].fillna(False).astype(bool); epi["hs_inc"]=epi["hs_inc"].fillna(0).astype(bool)
def clin(df):
    dd=df["disease_discovery"].dropna(); n_dd=len(dd)
    oc=df["case_outcome"].dropna(); oc=oc[~oc.isin(["Transf Outro Estado/Pais","Mud Diag","S/inf"])]; n_oc=len(oc)
    ht=df["hiv"].isin(["Pos","Neg"])
    return {"pulm":df["clinical_form_1"].eq("Pul").sum()/max(df["clinical_form_1"].notna().sum(),1)*100,
            "hiv_pos":df.loc[ht,"hiv"].eq("Pos").mean()*100 if ht.sum() else np.nan,
            "outpt":dd.eq("Demanda Ambulatorial").sum()/n_dd*100 if n_dd else np.nan,
            "er":dd.eq("Urgencia / Emergencia").sum()/n_dd*100 if n_dd else np.nan,
            "hospdx":dd.eq("Elucidacao Diagn. em Internacao").sum()/n_dd*100 if n_dd else np.nan,
            "acf":dd.isin(["Busca Ativa em Instituicao","Busca Ativa na Comunidade"]).sum()/n_dd*100 if n_dd else np.nan,
            "contact":dd.eq("Investigacao de Contatos").sum()/n_dd*100 if n_dd else np.nan,
            # DOT among EVALUATED episodes with recorded administration (matches the GLMM basis, ADR-0005)
            "dot":(lambda ev:(lambda dt:ev.loc[dt,"tx_administration_type"].eq("Supervisionado").mean()*100 if dt.sum() else np.nan)(
                   ev["tx_administration_type"].isin(["Supervisionado","Auto-Administrado"])))(
                   df[df["case_outcome"].isin(["Cura","Abandono","Abandono Primario","Obito TB","Obito NTB","Falencia/Resistencia"])]),
            "cure":oc.eq("Cura").sum()/n_oc*100 if n_oc else np.nan,
            "tbdeath":oc.eq("Obito TB").sum()/n_oc*100 if n_oc else np.nan,
            "hosptx":df["hosp_admission"].eq("S").sum()/max(df["hosp_admission"].isin(["S","N"]).sum(),1)*100,
            **{v:df[v].eq("S").sum()/max(df[v].isin(["S","N"]).sum(),1)*100
               for v in ("alcoholism","drug_use","tobacco_use","diabetes")}}
CG=[("Metropolitan — hotspot",epi.metro&epi.hs_inc),("Metropolitan — non-hotspot",epi.metro&~epi.hs_inc),
    ("Interior — hotspot",~epi.metro&epi.hs_inc),("Interior — non-hotspot",~epi.metro&~epi.hs_inc),
    ("Favela regions (subset)",epi["favela"].fillna(0)>50),("State total",pd.Series(True,index=epi.index))]
tab=tab.join(pd.DataFrame({lab:clin(epi[m]) for lab,m in CG}).T)

tab=tab[["n_reg","pop","pop_pct","cases","cases_pct","deaths_pct","ltfu_pct","inc","mort","aband_pct",
         "pulm","hiv_pos","alcoholism","drug_use","tobacco_use","diabetes",
         "outpt","er","hospdx","acf","contact","dot","cure","tbdeath","hosptx",
         "income","illit","residents","favela_pct","vuln"]]
pd.set_option("display.width",240,"display.max_columns",30)
print(tab.round(1).to_string())
tab.to_csv("/tmp/table1.csv")
print("\nSaved /tmp/table1.csv")
