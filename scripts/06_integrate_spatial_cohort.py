"""
06_integrate_spatial_cohort.py
-------------------------------
Merges the spatial linkage results (favela indicator) back into the main
analysis cohort, and generates descriptive statistics + model-ready dataset.

Run locally:
    cd "Abandonment Paper"
    python3 code/06_integrate_spatial_cohort.py

Inputs:
    - Data/cep_spatial_linkage.csv   (from 05_spatial_intersection.py)
    - Data/analysis_ready_cohort.csv (main cohort with treatment outcomes)

Outputs:
    - Data/cohort_with_spatial.csv   (analysis cohort with lives_in_favela)
    - Data/spatial_descriptive_stats.csv (Table 1 by favela status)
"""

import pandas as pd
import os
import sys

LINKAGE_PATH = "Data/cep_spatial_linkage.csv"
COHORT_PATH  = "Data/analysis_ready_cohort.csv"
OUTPUT_PATH  = "Data/cohort_with_spatial.csv"
STATS_PATH   = "Data/spatial_descriptive_stats.csv"

def main():
    # ── 1. Load spatial linkage ────────────────────────────────────────────
    print("1. Loading spatial linkage data...")
    if not os.path.exists(LINKAGE_PATH):
        print(f"   ✗ {LINKAGE_PATH} not found. Run 05_spatial_intersection.py first.")
        sys.exit(1)
    
    df_spatial = pd.read_csv(LINKAGE_PATH)
    print(f"   ✓ {len(df_spatial)} CEPs with spatial data")
    print(f"     - In favela: {df_spatial['lives_in_favela'].sum()}")
    
    # Keep only what we need for the merge
    spatial_cols = ["cep", "lives_in_favela", "NM_FCU", "NM_MUN", "CD_SETOR"]
    spatial_cols = [c for c in spatial_cols if c in df_spatial.columns]
    df_link = df_spatial[spatial_cols].copy()
    
    # Ensure CEP is string and zero-padded
    df_link["cep"] = df_link["cep"].astype(str).str.zfill(8)
    
    # ── 2. Load analysis cohort ────────────────────────────────────────────
    print("2. Loading analysis cohort...")
    df_cohort = pd.read_csv(COHORT_PATH)
    print(f"   ✓ {len(df_cohort)} patients in cohort")
    
    # Find CEP column (case-insensitive)
    cep_col = None
    for c in df_cohort.columns:
        if c.lower() == 'cep':
            cep_col = c
            break
    
    if cep_col is None:
        print("   ✗ No 'cep' column found in cohort!")
        print(f"     Available columns: {list(df_cohort.columns)}")
        sys.exit(1)
    
    # Standardize CEP format for matching
    df_cohort[cep_col] = df_cohort[cep_col].astype(str).str.strip().str.zfill(8)
    
    # ── 3. Merge ───────────────────────────────────────────────────────────
    print("3. Merging spatial data into cohort...")
    df_merged = df_cohort.merge(
        df_link,
        left_on=cep_col,
        right_on="cep",
        how="left"
    )
    
    # Fill unmatched patients as "not in favela" (conservative assumption)
    matched = df_merged["lives_in_favela"].notna().sum()
    unmatched = df_merged["lives_in_favela"].isna().sum()
    df_merged["lives_in_favela"] = df_merged["lives_in_favela"].fillna(0).astype(int)
    
    print(f"   ✓ Merge complete:")
    print(f"     - Matched to spatial data: {matched} ({matched/len(df_merged)*100:.1f}%)")
    print(f"     - Unmatched (set to 0):    {unmatched} ({unmatched/len(df_merged)*100:.1f}%)")
    print(f"     - Lives in favela:         {df_merged['lives_in_favela'].sum()}")
    print(f"     - Does not:                {(df_merged['lives_in_favela'] == 0).sum()}")
    
    # ── 4. Save enriched cohort ────────────────────────────────────────────
    print(f"4. Saving enriched cohort to {OUTPUT_PATH}...")
    df_merged.to_csv(OUTPUT_PATH, index=False)
    print(f"   ✓ {len(df_merged)} rows saved")
    
    # ── 5. Descriptive statistics by favela status ─────────────────────────
    print("5. Generating descriptive statistics...")
    
    stats_rows = []
    
    # Overall
    stats_rows.append({
        "Variable": "Total patients",
        "Favela (n)": df_merged[df_merged["lives_in_favela"] == 1].shape[0],
        "Non-Favela (n)": df_merged[df_merged["lives_in_favela"] == 0].shape[0],
    })
    
    # Treatment outcomes - check common outcome column names
    outcome_cols = ['outcome', 'desfecho', 'sit_encerr', 'SITENCERRA']
    outcome_col = None
    for c in outcome_cols:
        if c in df_merged.columns:
            outcome_col = c
            break
    
    if outcome_col:
        print(f"   Using outcome column: {outcome_col}")
        for group_name, group_df in df_merged.groupby("lives_in_favela"):
            label = "Favela" if group_name == 1 else "Non-Favela"
            outcomes = group_df[outcome_col].value_counts()
            for outcome, count in outcomes.items():
                pct = count / len(group_df) * 100
                stats_rows.append({
                    "Variable": f"Outcome: {outcome}",
                    f"{label} (n)": count,
                    f"{label} (%)": f"{pct:.1f}",
                })
    
    # Demographic variables
    demo_vars = ['sex', 'sexo', 'Age_group', 'age_group', 'hiv_aids',
                 'incarceration', 'homelessness', 'alcohol', 'drug_use_stat',
                 'race', 'education', 'diabetes']
    
    for var in demo_vars:
        if var in df_merged.columns:
            for val in df_merged[var].dropna().unique():
                favela_n = ((df_merged["lives_in_favela"] == 1) & (df_merged[var] == val)).sum()
                nonfav_n = ((df_merged["lives_in_favela"] == 0) & (df_merged[var] == val)).sum()
                fav_total = (df_merged["lives_in_favela"] == 1).sum()
                nonfav_total = (df_merged["lives_in_favela"] == 0).sum()
                stats_rows.append({
                    "Variable": f"{var}: {val}",
                    "Favela (n)": favela_n,
                    "Favela (%)": f"{favela_n/max(fav_total,1)*100:.1f}",
                    "Non-Favela (n)": nonfav_n,
                    "Non-Favela (%)": f"{nonfav_total and nonfav_n/nonfav_total*100:.1f}",
                })
    
    df_stats = pd.DataFrame(stats_rows)
    df_stats.to_csv(STATS_PATH, index=False)
    print(f"   ✓ Descriptive stats saved to {STATS_PATH}")
    
    # ── 6. Print summary ──────────────────────────────────────────────────
    print("\n" + "="*60)
    print("PIPELINE COMPLETE")
    print("="*60)
    print(f"Enriched cohort:    {OUTPUT_PATH}")
    print(f"Descriptive stats:  {STATS_PATH}")
    print(f"\nNext step: Run multivariable models with 'lives_in_favela' as a covariate")

if __name__ == "__main__":
    main()
