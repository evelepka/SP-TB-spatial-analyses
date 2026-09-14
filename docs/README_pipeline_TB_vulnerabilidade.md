# Pipeline TB-vulnerabilidade — Grande São Paulo

**Versão:** 1.0 (junho 2026)
**Equipe:** Stanford University (Evelyn Lepka)
**Período do cohort:** 2020–2024
**Universo:** Grande São Paulo (37 municípios — IBGE Concentração Urbana "São Paulo/SP")

---

## 1. Objetivo

Identificar áreas (setores censitários) de alta concentração de tuberculose na Grande São Paulo, para servir como **target de busca ativa**, usando dados oficiais e abordagem replicável a outras regiões.

---

## 2. O problema metodológico que precisamos resolver

A primeira versão da análise usou o **CEP** declarado no TBweb como chave de localização. Isso falhou sistematicamente porque:

| Achado do diagnóstico | Magnitude |
|---|---|
| Bairro do CEP (API Correios) **não bate** com bairro declarado no TBweb | **91,5% mismatch** |
| Município do CEP **não bate** com município declarado | 47,2% mismatch |
| CEPs "genéricos" terminados em "-000" (cobrem distrito inteiro) | 11,3% dos casos |
| CEP 01001000 (Sé, SP capital) — usado como "guarda-chuva" | **3.361 casos** num único CEP |
| Coordenadas vinham via fallback Olist 5-dígitos (centroide de bairro) | **75% dos casos** |

**Consequência:** pacientes de favela tinham coordenada caindo no centro formal do bairro adjacente. Isso **sistematicamente puxava casos para fora das favelas**, gerando o resultado contraintuitivo de "favela tem MENOS TB que não-favela" — claramente um artefato metodológico.

---

## 3. Solução: CNEFE 2022 (IBGE)

**Cadastro Nacional de Endereços para Fins Estatísticos** — banco oficial IBGE com **todos os endereços recenseados no Censo 2022**, atualizado em **setembro de 2024**.

Cada endereço tem:
- `LOGRAD_NUM` — rua + número
- `DSC_LOCALIDADE` — **bairro oficial IBGE** ← chave da solução
- `COD_SETOR` — setor censitário 2022 (linka direto com shapefile IBGE)
- `geometry` — coordenadas precisas coletadas pelo recenseador
- `COD_ESPECIE` — tipo de endereço (1 = Domicílio particular)

**Por que CNEFE resolve:**
- Independe do CEP (que é o ponto fraco no TBweb)
- Cobre favelas/comunidades urbanas (IBGE recenseou todos)
- Setor + bairro vêm da mesma fonte, sem necessidade de spatial join
- Contemporaneous com nosso cohort (Censo 2022 ↔ casos 2020-2024)
- **Gratuito** via FTP IBGE

**Download URL:**
```
https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos/
Censo_Demografico_2022/Arquivos_CNEFE/GeoJSON/Municipio_20240910/
qg_810_endereco_Munic{CD_MUN}.json.zip
```

Tamanho: SP estado inteiro = 1,2 GB; Grande SP (37 municípios) = 324 MB.

---

## 4. Pipeline end-to-end

```
┌─ INPUT ──────────────────────────────────────────┐
│ TBweb cohort 2013-2024 (cohort_with_spatial.csv) │
│ TBWeb_20250328_endereco.xlsx (raw addresses)     │
│ CNEFE 2022 GeoJSON (37 munis GSP)                │
│ IBGE 2022 setores shapefile + agregados básicos  │
│ IBGE 2022 V06004 (renda do responsável)          │
└──────────────────┬───────────────────────────────┘
                   │
        ┌──────────▼──────────┐
        │ FILTRO COHORT        │
        │ - GSP (37 munis)     │
        │ - 2020-2024          │
        │ - Comunidade         │
        │ - Novo + Recidiva    │
        │ → 51.016 casos       │
        └──────────┬───────────┘
                   │
        ┌──────────▼──────────────────────────┐
        │ MATCH CNEFE                          │
        │ Normalize rua TBweb                  │
        │ Lookup (cd_mun, rua, num) → CNEFE    │
        │ Fallback (cd_mun, rua) se sem número │
        │ → 90,8% cobertura                    │
        │   66,6% rua+num exato                │
        │   24,2% só rua                       │
        │    9,2% sem match                    │
        └──────────┬───────────────────────────┘
                   │
        ┌──────────▼──────────────────────────┐
        │ NOVAS COLUNAS NO COHORT              │
        │ - bairro_cnefe (DSC_LOCALIDADE)      │
        │ - setor_cnefe (COD_SETOR)            │
        │ - lat_cnefe, lon_cnefe               │
        │ - cnefe_match (qualidade)            │
        └──────────┬───────────────────────────┘
                   │
        ┌──────────▼──────────────────────────────────────┐
        │ AGREGAÇÃO POR SETOR + IBGE 2022                  │
        │ Para cada setor: pop (v0001), renda (V06004),    │
        │ FCU (NM_FCU), densidade demográfica (hab/km²),   │
        │ casos atribuídos via setor_cnefe                 │
        └──────────┬───────────────────────────────────────┘
                   │
              ┌────┴────┐
              │         │
      ┌───────▼───┐ ┌───▼───────────────┐
      │ HOTSPOTS  │ │ ÍNDICE COMPOSTO   │
      │ EMPÍRICOS │ │ z(-renda) +       │
      │ Top X%    │ │ z(densidade) +    │
      │ por taxa  │ │ z(is_fcu)         │
      └───────────┘ └───────────────────┘
              │         │
              └────┬────┘
                   │
        ┌──────────▼──────────────────┐
        │ SETORES PRIORITÁRIOS         │
        │ /tmp/setores_priorizados...  │
        └──────────────────────────────┘
```

---

## 5. Variáveis e fontes

### Numerador (casos de TB)
- **Fonte:** TBweb (SES-SP, Sistema de Informações TB)
- **Filtros:** `address_type = ENDERECO PADRAO`; `case_type ∈ {Caso novo, Recidiva}`; janela 2020-2024
- **N casos GSP:** 51.016 (após filtros)
- **N casos com endereço matched no CNEFE:** 46.303 (90,8%)
- **N casos atribuídos a setor IBGE 2022 residencial:** 43.791

### Denominador (população)
- **Fonte:** IBGE Censo 2022 — `v0001` (pop residente em domicílios particulares ocupados)
- **Filtros:** Setor `CD_TIPO ∈ {0 = comum, 1 = aglomerado subnormal/FCU}`; pop ≥ 100
- **Pop total GSP:** 20.535.941
- **Pessoas-ano (5 anos):** 102.679.705

### Variáveis de vulnerabilidade
| Variável | Fonte IBGE 2022 | Significado |
|---|---|---|
| `renda_2022` | V06004 (rendimento médio do responsável) | Renda formal — proxy SES |
| `density_km2` | v0001 / AREA_KM2 | Densidade demográfica urbana |
| `v0005` | v0005 (média mor/dom) | Densidade habitacional (overcrowding) |
| `is_fcu` | NM_FCU not null | Favela ou Comunidade Urbana (IBGE) |
| `bairro_cnefe` | CNEFE DSC_LOCALIDADE | Bairro oficial derivado do endereço |
| `setor_cnefe` | CNEFE COD_SETOR | Setor censitário 2022 |

---

## 6. Resultados principais

### 6.1 Diagnóstico de qualidade de endereço

CNEFE vs TBweb declarado:
- **Concordância de bairro:** 34,2% (entre os 45.437 com ambos preenchidos)
- **Inconsistência:** 65,8% — confirma que o bairro TBweb é frequentemente incorreto/genérico
- **Cobertura CNEFE:** 90,8% dos casos GSP têm endereço matched

### 6.2 Perfil dos hotspots (top 5% pop por taxa observada)

| Métrica | Hotspots | Resto GSP | Razão |
|---|---:|---:|---:|
| Pop | 1.026.649 (5%) | 19.509.292 (95%) | — |
| **Casos** | **12.689 (29%)** | 31.102 (71%) | — |
| Taxa por 100k pa | **247** | 32 | **7,7×** |
| **Renda média (R$)** | **2.823** | 4.074 | **0,69×** ⬇️ |
| Densidade demográfica | 29.815 | 25.119 | 1,19× |
| **% pop em FCU** | **25,3%** | 13,7% | **1,84×** ⬆️ |
| Densidade habitacional | 2,77 | 2,76 | 1,01 (não discrimina) |

### 6.3 Top bairros (via CNEFE oficial)

1. **Itaim Paulista** — 705 casos (extremo leste SP, periferia)
2. **Brasilândia** — 667 (zona norte, favelas)
3. **Jabaquara** — 606
4. **Jardim Helena** — 503
5. **Vila Curuçá** — 493
6. **Cidade Ademar** — 455
7. **Lajeado** — 447
8. **Jaraguá** — 401
9. **Cidade Tiradentes** — 390 (extremo leste, alta vulnerabilidade)
10. **Guaianazes** — 381
11. **Paraisópolis** — 323 (favela canônica)
12. **Santa Cecília** — 316 (centro, próximo Cracolândia)

### 6.4 Performance do índice composto vs hotspots empíricos

| Top X% pop | Índice composto | Hotspots empíricos |
|---:|---:|---:|
| 1% | 1,3× | — |
| 5% | **1,5× (7,3% casos)** | **5,8× (29% casos)** |
| 10% | 1,4× (14% casos) | 4,5× (45% casos est.) |
| 20% | 1,4× (27% casos) | — |

**Sobreposição entre os dois rankings: 11,4%.**

### 6.5 Implicação metodológica

O índice composto (renda + densidade + FCU) é **menos eficiente** que esperado porque:
- Não captura **pop em situação de rua** (Sé, Bom Retiro têm renda média "alta" mas TB extrema)
- Não captura **comorbidades** (HIV, drogas) que cluster localmente
- Não captura **mobilidade urbana** intra-cidade

**Para target operacional, recomenda-se abordagem HÍBRIDA:**
1. **Índice composto** → captura periferias estruturalmente vulneráveis (Itaim Paulista, Brasilândia, Cidade Tiradentes)
2. **+ Hotspots empíricos** → adiciona áreas centrais com pop vulnerável específica (Sé, Bom Retiro, Santa Cecília)

---

## 7. Limitações

1. **9,2% dos casos sem match CNEFE** — endereços incompletos ou pós-Censo 2022
2. **Densidade habitacional v0005 não discrimina** em GSP — provavelmente porque toda área urbana tem mor/dom similares (~2,7-2,9)
3. **Renda V06004 é formal** — pode subestimar vulnerabilidade em comunidades com economia informal extensa
4. **Setores institucionais (CD_TIPO 2-7)** excluídos do denominador — pequena perda (~30k pop, <0,15% da GSP)
5. **NM_BAIRRO esparso no shapefile IBGE** — usamos CNEFE para bairro derivado, mais robusto

---

## 8. Replicabilidade para outras regiões

Pipeline reutiliza-se para qualquer região metropolitana brasileira:

1. Identificar municípios da região via `NM_CONCURB` no shapefile IBGE 2022
2. Baixar CNEFE GeoJSON desses municípios
3. Rodar `cnefe_efficient.py` com lista de municípios atualizada
4. Rodar `analise_hotspots_cnefe.py` e `indice_vulnerabilidade_target.py`

Próximas regiões críticas para o projeto:
- **Baixada Santista** (SP) — São Vicente tem 577/100k, a mais alta do estado
- **Campinas** (SP)
- Outras a definir

---

## 9. Arquivos de saída

| Arquivo | Descrição |
|---|---|
| `cohort_with_cnefe.csv` | Cohort com colunas CNEFE (bairro, setor, lat/lon) |
| `setores_priorizados_GSP.csv` | 43.972 setores ordenados por índice de vulnerabilidade |
| `hotspots_top5pct_setores.csv` | 2.501 setores hotspot empírico |
| `bairros_cnefe_ranking.csv` | Bairros ordenados por casos (via bairro CNEFE) |

---

## 10. Scripts de execução

| Script | Função |
|---|---|
| `download_cnefe_gsp.py` | Baixa CNEFE para 37 municípios GSP |
| `cnefe_efficient.py` | Parseia CNEFE → constrói índice → faz matching com cohort |
| `analise_hotspots_cnefe.py` | Identifica e perfila hotspots |
| `indice_vulnerabilidade_target.py` | Constrói índice composto + ranking |

---

## Histórico de versões

- **v1.0 (2026-06):** Versão inicial. Pipeline CEP → CNEFE estabelecido. Análise GSP 2020-2024.
