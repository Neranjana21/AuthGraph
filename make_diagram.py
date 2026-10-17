"""Architecture diagram -> figures/architecture.png"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
boxes = [("Controlled lab\nFlask app :5000\nsynthetic cookie/JWT", "#56B4E9"), ("Chromium + generated\nMV3 extensions\n(real browser APIs, Wasm)", "#0072B2"),
         ("Telemetry JSONL\nhashed credential ids\n+ server-log cross-check", "#E69F00"), ("Heterogeneous graph\n11 node / 17 relation types\n(taint edges separable)", "#009E73"),
         ("Detectors\nrules · RF · MLP\nGCN · GraphSAGE · R-GCN", "#CC79A7"), ("Explanation + dashboard\nocclusion importance\nhighlighted credential→sink path", "#D55E00")]
fig, ax = plt.subplots(figsize=(13, 2.6)); ax.axis("off"); ax.set_xlim(0, 13); ax.set_ylim(0, 2.6)
for i, (t, c) in enumerate(boxes):
    x = 0.15 + i * 2.15
    ax.add_patch(FancyBboxPatch((x, 0.5), 1.8, 1.5, boxstyle="round,pad=0.03", fc=c, ec="none", alpha=0.9))
    ax.text(x + 0.9, 1.25, t, ha="center", va="center", fontsize=7.5, color="white", fontweight="bold")
    if i < len(boxes) - 1: ax.annotate("", xy=(x + 2.12, 1.25), xytext=(x + 1.85, 1.25), arrowprops=dict(arrowstyle="->", lw=1.8))
ax.text(6.5, 0.15, "localhost only · synthetic credentials · no real users, sites or tokens", ha="center", fontsize=8, style="italic")
fig.savefig("figures/architecture.png", dpi=150, bbox_inches="tight")
