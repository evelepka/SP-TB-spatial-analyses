import urllib.request
import ssl
import re
import os
import sys

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base = "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2010/Aglomerados_subnormais/Aglomerados_subnormais_informacoes_territoriais/tabelas_xls/"
try:
    print(f"Fetching {base}...")
    req = urllib.request.Request(base, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ctx) as r:
        html = r.read().decode("latin1")
        links = re.findall(r'href=["\'](.*?)["\']', html)
        
        found = False
        for l in links:
            if l.endswith(".xls") or l.endswith(".zip"):
                print("Found file:", l)
                if "sp" in l.lower() or "br" in l.lower() or "aglom" in l.lower() or "sinopse" in l.lower():
                    full_url = base + l
                    print(f"Downloading data: {full_url}")
                    req2 = urllib.request.Request(full_url, headers={"User-Agent": "Mozilla/5.0"})
                    out = "Data/AGSN_2010_metadata." + l.split(".")[-1]
                    with urllib.request.urlopen(req2, context=ctx) as r2, open(out, "wb") as f:
                        f.write(r2.read())
                    print(f"Successfully downloaded to {out}")
                    found = True
                    # Let it download all relevant files instead of exiting immediately
                    
        if not found:
            print("No suitable .xls or .zip file found")
except Exception as e:
    print("Error:", e)
