"""Single switch for the rate basis used to RANK regions and DISPLAY rates (ADR-0006, 2026-09-05).

RANK=crude  (default) primary analysis: incidence/mortality per adult population, LTFU as the
                       crude proportion of evaluated episodes. Output files unsuffixed.
RANK=std               age-standardized (observed/expected, indirect, State reference; LTFU age-
                       adjusted proportion) — the pre-2026-09 primary, now the sensitivity analysis.
                       Output files suffixed _std.
RANK=percap            LTFU as events per capita (historical basis) — kept only to
                       regenerate the historical figure on request. Suffix _percap.

Import:  from rank_basis import RANK, SUF, RATE, RATE_LABEL, rank_base
"""
import os, numpy as np
RANK = os.environ.get("RANK", "crude")
assert RANK in ("crude", "std", "percap"), RANK
SUF = {"crude": "", "std": "_std", "percap": "_percap"}[RANK]
# region_units.csv columns holding the rate used for ranking/display, per lens
RATE = ({"inc": "inc_crude", "mort": "drate_crude", "aband": "ltfu_crude"} if RANK == "crude" else
        {"inc": "inc_adj",   "mort": "drate_adj",   "aband": "ltfu_adj"}   if RANK == "std" else
        {"inc": "inc_crude", "mort": "drate_crude", "aband": "ltfu_percap"})
RATE_LABEL = ({"inc": "TB notification rate\n(/100,000/yr)", "mort": "TB mortality\n(/100,000/yr)",
               "aband": "LTFU\n(% of evaluated episodes)"} if RANK != "std" else
              {"inc": "TB notification rate\n(age-standardized, /100,000/yr)",
               "mort": "TB mortality\n(age-standardized, /100,000/yr)",
               "aband": "LTFU\n(age-adjusted % of evaluated episodes)"})
BASIS_TEXT = {"crude": "crude", "std": "age-standardized", "percap": "per-capita"}[RANK]

def rank_base(reg, lens, popv):
    """Denominator vector (aligned to reg rows) used to turn split-sample counts into a ranking rate.
    crude: population (inc/mort) or evaluated episodes (aband); std: expected events; percap: population."""
    if RANK == "std":
        e = reg[{"inc": "E_inc", "mort": "E_dr", "aband": "E_ab"}[lens]].values
        return np.where(e > 0, e, np.inf)
    if RANK == "crude" and lens == "aband":
        ne = reg["ne"].values.astype(float)
        return np.where(ne > 0, ne, np.inf)
    return popv
