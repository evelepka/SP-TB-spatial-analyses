import urllib.request
import re
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

try:
    url = "https://centrodametropole.fflch.usp.br/en/node/8388"
    html = urllib.request.urlopen(url, context=ctx).read().decode("utf-8", errors="ignore")
    links = re.findall(r'href=["\'](.*?)["\']', html)
    for link in links:
        if "download" in link.lower() or "zip" in link.lower() or "rar" in link.lower():
            if 'centrodametropole' in link or link.startswith('/'):
                print(f"Possible download link: {link}")
except Exception as e:
    print(f"Error: {e}")
