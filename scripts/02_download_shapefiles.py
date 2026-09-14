import urllib.request
import zipfile
import os
import ssl

URL = "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022/setores/shp/UF/SP_setores_CD2022.zip"
ZIP_PATH = "Data/SP_setores_CD2022.zip"
EXTRACT_DIR = "Data/SP_setores_2022/"

def main():
    print(f"Downloading shapefiles from IBGE: {URL}")
    print("This is a 76MB file and may take a minute or two...")
    
    # Bypass SSL verification if needed (common on macOS Python)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    if not os.path.exists("Data"):
        os.makedirs("Data")

    # Only download if we haven't already
    if not os.path.exists(ZIP_PATH):
        try:
            req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=ctx) as response:
                with open(ZIP_PATH, 'wb') as out_file:
                    out_file.write(response.read())
            print(f"Successfully downloaded to {ZIP_PATH}")
        except Exception as e:
            print(f"Failed to download: {e}")
            return
    else:
        print(f"{ZIP_PATH} already exists. Skipping download.")

    print(f"Extracting shapefiles to {EXTRACT_DIR}...")
    
    if not os.path.exists(EXTRACT_DIR):
        os.makedirs(EXTRACT_DIR)
        
    try:
        with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
            zip_ref.extractall(EXTRACT_DIR)
        print("Extraction complete! Shapefiles are ready for spatial intersection.")
    except Exception as e:
        print(f"Error extracting zip: {e}")

if __name__ == "__main__":
    main()
