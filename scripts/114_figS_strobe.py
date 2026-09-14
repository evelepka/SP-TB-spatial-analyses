"""Supplementary Figure S1 — STROBE participant-flow diagram (episode-level cohort).
Output: /tmp/figS_strobe.png
"""
import matplotlib, matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
matplotlib.rcParams.update({"font.family":"sans-serif"})
fig,ax=plt.subplots(figsize=(9.5,13.2)); ax.set_xlim(0,10); ax.set_ylim(0,15.6); ax.axis("off")
def box(x,y,w,h,text,fc,ec,fs=10,bold=False):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.08",fc=fc,ec=ec,lw=1.4))
    ax.text(x+w/2,y+h/2,text,ha="center",va="center",fontsize=fs,fontweight="bold" if bold else "normal",color="#1a202c")
MAIN=["All tuberculosis notifications,\nSão Paulo State, 2013–2024\nn = 270,492",
      "Adult notifications (≥15 years)\nn = 263,052",
      "Incident notifications (new + recurrence)\nn = 238,568",
      "With a standard residential address\nn = 200,292",
      "Unique incident episodes\nn = 200,107",
      "Analytic set — episodes geocoded to a\nresidential region\nn = 192,161"]
EXCL=["Excluded: 7,132 children (<15 years)\nand 308 with missing age",
      "Excluded: 24,484 re-treatment\nnotifications (not incident)",
      "Excluded: 28,565 incarcerated and\n9,711 with no fixed residence",
      "Excluded: 185 duplicate\nnotification records",
      "Excluded: 7,946 not geocodable to a\nresidential region"]
mx,mw,mh=0.5,5.2,1.3; ex_x,ex_w,ex_h=6.2,3.5,1.0
ys=[12.9,10.44,7.98,5.52,3.06,0.6]
for i,m in enumerate(MAIN):
    last=(i==len(MAIN)-1)
    box(mx,ys[i],mw,mh,m,fc="#cfe3f7" if last else "#eef4fa",ec="#0d2b45",fs=10,bold=last)
for i in range(len(MAIN)-1):
    y0=ys[i]; y1=ys[i+1]+mh
    ax.annotate("",xy=(mx+mw/2,y1),xytext=(mx+mw/2,y0),arrowprops=dict(arrowstyle="-|>",lw=1.6,color="#0d2b45"))
    ymid=(y0+y1)/2-ex_h/2
    box(ex_x,ymid,ex_w,ex_h,EXCL[i],fc="#fdecea",ec="#b03a2e",fs=8.6)
    ax.annotate("",xy=(ex_x,ymid+ex_h/2),xytext=(mx+mw/2,ymid+ex_h/2),arrowprops=dict(arrowstyle="-|>",lw=1.2,color="#b03a2e"))
plt.savefig("/tmp/figS_strobe.png",dpi=300,bbox_inches="tight"); plt.close()
print("Saved /tmp/figS_strobe.png")
