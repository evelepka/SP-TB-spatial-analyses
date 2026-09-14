"""Converter o README do pipeline TB para HTML estilizado."""

import markdown
import os

SRC = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data/IBGE_2022_extended/README_pipeline_TB_vulnerabilidade.md"
DST = "/Users/evelynlepkadelima/Library/CloudStorage/GoogleDrive-evelynlepka@gmail.com/My Drive/WHO modelling Project/SP-TB-spatial-analyses/Data/IBGE_2022_extended/README_pipeline_TB_vulnerabilidade.html"

with open(SRC, "r", encoding="utf-8") as f:
    md_text = f.read()

# Converte MD → HTML com extensões para tabelas, fenced code, sumário, ids automáticos
html_body = markdown.markdown(
    md_text,
    extensions=["tables", "fenced_code", "toc", "sane_lists", "attr_list"],
    extension_configs={"toc": {"permalink": False}},
)

# Template HTML com CSS embutido (estilo profissional médico/acadêmico)
template = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pipeline TB-vulnerabilidade — Grande São Paulo</title>
<style>
  /* Tipografia base */
  body {
    font-family: -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    color: #1a1a1a;
    background: #ffffff;
    max-width: 920px;
    margin: 0 auto;
    padding: 40px 30px 60px;
    line-height: 1.65;
    font-size: 15px;
  }

  /* Cabeçalhos */
  h1, h2, h3, h4 { color: #1a3d5c; font-weight: 600; }
  h1 {
    font-size: 28px;
    border-bottom: 3px solid #1a3d5c;
    padding-bottom: 10px;
    margin-bottom: 5px;
  }
  h2 {
    font-size: 22px;
    margin-top: 40px;
    border-bottom: 1px solid #c8d6e1;
    padding-bottom: 6px;
  }
  h3 { font-size: 17px; margin-top: 25px; }
  h4 { font-size: 15px; }

  /* Tabelas */
  table {
    border-collapse: collapse;
    width: 100%;
    margin: 18px 0;
    font-size: 13.5px;
  }
  th, td {
    padding: 8px 12px;
    border-bottom: 1px solid #d8e0e8;
    text-align: left;
    vertical-align: top;
  }
  th {
    background: #f3f6fa;
    color: #1a3d5c;
    font-weight: 600;
    border-bottom: 2px solid #1a3d5c;
  }
  td:nth-child(n+2):not(:has(em)):not(:has(strong)) {
    /* Alinha à direita colunas que parecem numéricas */
  }
  tr:hover { background: #fafcfe; }

  /* Código */
  code {
    background: #f3f5f7;
    color: #c7254e;
    padding: 2px 5px;
    border-radius: 3px;
    font-family: "SF Mono", Monaco, Consolas, monospace;
    font-size: 0.92em;
  }
  pre {
    background: #2c3e50;
    color: #ecf0f1;
    padding: 14px 18px;
    border-radius: 6px;
    overflow-x: auto;
    line-height: 1.45;
    font-size: 13px;
  }
  pre code {
    background: transparent;
    color: inherit;
    padding: 0;
  }

  /* Listas */
  ul, ol { padding-left: 28px; }
  li { margin: 4px 0; }

  /* Citações */
  blockquote {
    border-left: 4px solid #1a3d5c;
    background: #f0f4f8;
    margin: 16px 0;
    padding: 10px 18px;
    color: #4a5d6e;
  }

  /* Separadores */
  hr {
    border: none;
    border-top: 1px solid #d8e0e8;
    margin: 35px 0;
  }

  /* Links */
  a {
    color: #1565c0;
    text-decoration: none;
  }
  a:hover { text-decoration: underline; }

  /* Destaque emoji */
  h1 .emoji, h2 .emoji, h3 .emoji { vertical-align: middle; }

  /* Mark / strong */
  strong { color: #0d3559; }

  /* Print friendly */
  @media print {
    body { max-width: none; padding: 20mm; font-size: 11pt; }
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
Gerado automaticamente a partir do README.md • Junho 2026 • Stanford University
</footer>
</body>
</html>
"""

html = template.replace("{body}", html_body)

with open(DST, "w", encoding="utf-8") as f:
    f.write(html)

print(f"HTML gerado: {DST}")
print(f"Tamanho: {os.path.getsize(DST)/1024:.1f} KB")
