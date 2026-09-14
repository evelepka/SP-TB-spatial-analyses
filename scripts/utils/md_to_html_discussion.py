"""Converter documento de discussão MD → HTML estilizado."""
import markdown, os

SRC = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data/IBGE_2022_extended/discussao_estrategia/GSP_TB_concentracao_e_estrategias.md"
DST = SRC.replace(".md", ".html")

with open(SRC, "r", encoding="utf-8") as f:
    md_text = f.read()

html_body = markdown.markdown(
    md_text,
    extensions=["tables", "fenced_code", "toc", "sane_lists", "attr_list"],
    extension_configs={"toc": {"permalink": False}},
)

template = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TB concentration in Greater São Paulo — active case-finding strategies</title>
<style>
  body {
    font-family: -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    color: #1a1a1a; background: #ffffff;
    max-width: 920px; margin: 0 auto;
    padding: 40px 30px 60px;
    line-height: 1.65; font-size: 15px;
  }
  h1, h2, h3, h4 { color: #1a3d5c; font-weight: 600; }
  h1 {
    font-size: 26px;
    border-bottom: 3px solid #1a3d5c;
    padding-bottom: 10px;
    margin-bottom: 5px;
  }
  h2 {
    font-size: 21px; margin-top: 38px;
    border-bottom: 1px solid #c8d6e1;
    padding-bottom: 6px;
  }
  h3 { font-size: 17px; margin-top: 24px; }
  h4 { font-size: 15px; }
  table {
    border-collapse: collapse;
    width: 100%; margin: 18px 0;
    font-size: 13px;
  }
  th, td {
    padding: 8px 12px;
    border-bottom: 1px solid #d8e0e8;
    text-align: left; vertical-align: top;
  }
  th {
    background: #f3f6fa; color: #1a3d5c;
    font-weight: 600;
    border-bottom: 2px solid #1a3d5c;
  }
  tr:hover { background: #fafcfe; }
  code {
    background: #f3f5f7; color: #c7254e;
    padding: 2px 5px; border-radius: 3px;
    font-family: "SF Mono", Monaco, Consolas, monospace;
    font-size: 0.92em;
  }
  pre {
    background: #2c3e50; color: #ecf0f1;
    padding: 14px 18px; border-radius: 6px;
    overflow-x: auto; line-height: 1.45; font-size: 13px;
  }
  ul, ol { padding-left: 28px; }
  li { margin: 4px 0; }
  blockquote {
    border-left: 4px solid #1a3d5c;
    background: #f0f4f8;
    margin: 16px 0; padding: 10px 18px;
    color: #4a5d6e;
  }
  hr {
    border: none; border-top: 1px solid #d8e0e8;
    margin: 35px 0;
  }
  a { color: #1565c0; text-decoration: none; }
  a:hover { text-decoration: underline; }
  strong { color: #0d3559; }
  /* Caixa de destaque */
  h2#8-discussion-points-for-advisor,
  h2#executive-summary,
  h2#7-proposed-methodological-pivot-a-tb-vulnerability-typology-archetypes {
    background: #fef9e7; border-left: 4px solid #f1c40f;
    padding: 10px 15px; border-bottom: none;
  }
  @media print {
    body { max-width: none; padding: 18mm; font-size: 11pt; }
    h1 { page-break-before: avoid; }
    h2, h3 { page-break-after: avoid; }
    table, pre, blockquote { page-break-inside: avoid; }
  }
</style>
</head>
<body>
{body}
<hr>
<footer style="margin-top:35px; color:#7a8b99; font-size:12px; text-align:center;">
Stanford University — WHO TB Screening Investment Case — June 2026<br>
Internal discussion document (Evelyn Lepka de Lima)
</footer>
</body>
</html>
"""

with open(DST, "w", encoding="utf-8") as f:
    f.write(template.replace("{body}", html_body))

print(f"HTML: {DST}")
print(f"Tamanho: {os.path.getsize(DST)/1024:.1f} KB")
