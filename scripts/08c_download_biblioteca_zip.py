import urllib.request
import ssl
import re
import os
import zipfile

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://biblioteca.ibge.gov.br/index.php/biblioteca-catalogo?view=detalhes&id=792"
try:
    print(f"Fetching IBGE Biblioteca page: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ctx) as r:
        html = r.read().decode("utf-8", errors="ignore")
        
        # Searching for zip links
        # IBGE library downloads use a javascript pattern or direct hrefs
        links = re.findall(r'href=["\'](.*?)["\']', html)
        zip_link = None
        for L in links:
            if "cd_2010_aglomerados_subnormais_cd.zip" in L.lower():
                zip_link = L
                break
                
        if not zip_link:
            # Fallback: maybe it's just attached raw
            for L in links:
                if L.endswith(".zip") and "aglomerados" in L.lower():
                    zip_link = L
                    break

        if zip_link:
            if zip_link.startswith('/'):
                zip_link = "https://biblioteca.ibge.gov.br" + zip_link
            elif not zip_link.startswith('http'):
                zip_link = "https://biblioteca.ibge.gov.br/" + zip_link
                
            print("Found Zip Link:", zip_link)
            
            # Download it!
            zip_path = "Data/AGSN_2010_Library.zip"
            if not os.path.exists(zip_path):
                print(f"Downloading {zip_path}...")
                req2 = urllib.request.Request(zip_link, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req2, context=ctx) as r2, open(zip_path, "wb") as f:
                    f.write(r2.read())
            
            extract_dir = "Data/SP_AGSN_2010_Library"
            os.makedirs(extract_dir, exist_ok=True)
            print(f"Extracting to {extract_dir}...")
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(extract_dir)
            print("Successfully extracted AGSN 2010 Shapefiles!")
        else:
            print("Could not find the zip link on the page.")
            print("Available zip links:", [l for l in links if ".zip" in l.lower()])
except Exception as e:
    print(f"Error: {e}")
