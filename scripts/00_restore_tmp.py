"""Restore the persistent analytic artifacts into /tmp at the start of a session.

/tmp is cleared between sessions, but the expensive/authoritative intermediates are persisted in
Drive `Data/analytic/`. Run this FIRST each session so the /tmp-based scripts (100, 101-109, ...)
find their inputs without re-running the costly CNEFE matching or regionalisation.

    python3 scripts/00_restore_tmp.py
"""
import os, shutil
AN=("/DATA_ROOT/WHO modelling Project/SP-TB-spatial-analyses/Data/analytic")
FILES=["cohort_with_cnefe.csv","cohort_baixada_with_cnefe_v2.csv","cohort_sp_outros_with_cnefe.csv",
       "geocoded_cohort.csv","regions_sectors.csv","vuln_sectors.csv","vuln_final.csv",
       "region_units.csv","region_cases.csv","region_geom.gpkg","sp_muni_base.gpkg"]
for f in FILES:
    src=os.path.join(AN,f); dst=os.path.join("/tmp",f)
    if os.path.exists(src):
        shutil.copy(src,dst); print(f"  restored {f}")
    else:
        print(f"  MISSING in persistent store: {f}")
# IPVS 2022 shapefile (script 88 validation figure) — persisted zip in Data/ (87 MB, from SEADE repositório)
import zipfile
ipvs_zip=os.path.join(os.path.dirname(AN),"ipvs_2022.zip")   # AN = Data/analytic -> Data/ipvs_2022.zip
if os.path.exists(ipvs_zip) and not os.path.exists("/tmp/ipvs_2022/IPVS_2022.shp"):
    with zipfile.ZipFile(ipvs_zip) as z: z.extractall("/tmp/ipvs_2022")
    print("  restored ipvs_2022 shapefile")
elif not os.path.exists(ipvs_zip):
    print("  MISSING: Data/ipvs_2022.zip (re-download from SEADE for the IPVS validation figure, script 88)")
print("Done. /tmp repopulated from Data/analytic.")
