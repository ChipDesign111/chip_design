"""Stacked bar for the slide "效果": where the CPU self-check cycles went.

Palette slots 1 (blue) and 2 (orange) from the validated reference palette,
checked with validate_palette.js (light, surface #fcfcfb): CVD dE 24.7,
normal-vision dE 33.6, both >= 3:1 contrast against the surface.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
BLUE = "#2a78d6"
ORANGE = "#eb6834"

plt.rcParams["font.family"] = "Microsoft YaHei"
plt.rcParams["axes.unicode_minus"] = False

rows = [
    ("改动后", 2107, 230),
    ("改动前", 2107, 1543),
]
GAP = 16.0          # surface-colored gap between stacked segments
GOOD = "#006300"    # success text, used for the delta cue only

fig, ax = plt.subplots(figsize=(9.8, 3.2), dpi=220)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)

h = 0.40
for i, (name, work, fetch) in enumerate(rows):
    yc = i
    ax.barh(yc, work, height=h, left=0, color=BLUE, linewidth=0, zorder=3)
    ax.barh(yc, fetch - GAP, height=h, left=work + GAP, color=ORANGE,
            linewidth=0, zorder=3)
    ax.text(work / 2, yc, "有效工作  2,107 拍", ha="center", va="center",
            color="#ffffff", fontsize=13, fontweight="bold", zorder=4)
    if fetch > 600:
        ax.text(work + fetch / 2, yc, f"取指开销  {fetch:,} 拍",
                ha="center", va="center", color="#ffffff", fontsize=13,
                fontweight="bold", zorder=4)
    else:
        ax.annotate(f"取指开销 {fetch:,} 拍", xy=(work + 40, yc + h / 2),
                    xytext=(work + 210, yc + 0.42), fontsize=12, color=INK2,
                    ha="left", va="center",
                    arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=1,
                                    shrinkA=0, shrinkB=2))
    total = work + fetch
    ax.text(total + 70, yc, f"{total:,} 拍", ha="left", va="center",
            color=INK, fontsize=16, fontweight="bold")

before = sum(rows[1][1:])
after = sum(rows[0][1:])
ax.text(4300, 0.5, f"−{before - after:,} 拍\n−{(before-after)*100.0/before:.1f}%",
        ha="left", va="center", color=GOOD, fontsize=13, fontweight="bold",
        linespacing=1.5)

ax.set_yticks(range(len(rows)))
ax.set_yticklabels([r[0] for r in rows], fontsize=14, color=INK)
ax.set_xlim(0, 4560)
ax.set_ylim(-0.62, len(rows) - 0.30)
ax.set_xticks([])
for s in ("top", "right", "bottom", "left"):
    ax.spines[s].set_visible(False)
ax.tick_params(axis="y", length=0, pad=14)
ax.set_xlabel("CPU 自检段周期数（RTL 行为级，10 ns 时钟）", fontsize=11,
              color=MUTED, labelpad=12, loc="left")

fig.tight_layout(pad=0.5)
fig.savefig("chart_breakdown.png", facecolor=SURFACE)
print("wrote chart_breakdown.png")
