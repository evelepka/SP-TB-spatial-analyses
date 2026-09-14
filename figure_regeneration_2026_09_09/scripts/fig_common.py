"""Shared palette + style for the harmonized manuscript composite figures (Fig 2, 3, 5).
Outcome colours match the panels produced by scripts/102-105."""
import os
import matplotlib.pyplot as plt

INC  = "#1a3d5c"   # notifications — navy
MORT = "#7a0177"   # mortality  — magenta
LTFU = "#1f6f8b"   # LTFU       — teal
VULN = "#b8860b"   # vulnerability — goldenrod
REFLINE = "#444"
GRIDCLR = "#e8e8e8"

AN  = os.environ.get("SPTB_AN", "/DATA_ROOT/Data/analytic")
OUT = os.environ.get("SPTB_OUT", "./figures")

def set_style():
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 11, "axes.labelsize": 11,
        "axes.titlesize": 12, "xtick.labelsize": 10, "ytick.labelsize": 10,
        "axes.linewidth": 0.9, "axes.edgecolor": "#333333",
        "legend.fontsize": 9.5, "legend.frameon": False,
        "figure.dpi": 150, "savefig.dpi": 300, "pdf.fonttype": 42, "ps.fonttype": 42,
    })

def panel_tag(ax, letter, x=-0.02, y=1.04):
    ax.set_title(f"({letter})", loc="left", fontsize=13, fontweight="bold", x=x, y=y)
