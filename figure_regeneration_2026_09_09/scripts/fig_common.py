"""Shared palette + style for the harmonized manuscript composite figures (Fig 2, 3, 5).
Canonical outcome colours match the existing manuscript panels (scripts 102–105)."""
import matplotlib.pyplot as plt

INC  = "#1a3d5c"   # incidence  — navy
MORT = "#7a0177"   # mortality  — magenta
LTFU = "#1f6f8b"   # LTFU       — teal
VULN = "#b8860b"   # vulnerability — goldenrod
REFLINE = "#444"
GRIDCLR = "#e8e8e8"

import os
AN  = os.environ.get("SPTB_AN", "/DATA_ROOT/SP-TB-spatial-analyses/Data/analytic")
OUT = os.environ.get("SPTB_OUT", "./figures")

def set_style():
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 11, "axes.labelsize": 11,
        "axes.titlesize": 12, "xtick.labelsize": 10, "ytick.labelsize": 10,
        "axes.linewidth": 0.9, "axes.edgecolor": "#333333",
        "legend.fontsize": 9.5, "legend.frameon": False,
        "figure.dpi": 150, "savefig.dpi": 300,
    })

def panel_tag(ax, letter, x=-0.02, y=1.04):
    ax.set_title(f"({letter})", loc="left", fontsize=13, fontweight="bold", x=x, y=y)
