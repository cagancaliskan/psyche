#!/usr/bin/env python3
"""
Figure: passing assertions per test suite.

Data are taken VERBATIM from docs/TEST_OUTPUT.txt:
    test_psyche_store.py        45
    test_psyche_activation.py   35
    test_psyche_coalitions.py   19
    test_psyche_field.py        13
    test_psyche_perceive.py     18
    --------------------------------
    TOTAL                    130 passed, 0 failed   (across 56 test functions)

Honesty: this counts passing assertions. It proves MECHANISM (determinism,
integrity, purity of the substrate + activation layers) and the mechanics of the
exploratory layers. It does NOT measure cognitive quality or correctness of the
"thought"; no such claim is made or implied here.

Run with a Python that has matplotlib:
    python3 test_suite_bars.py        # writes ../rendered/test_suite_bars.png
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "rendered", "test_suite_bars.png")

# --- real numbers (verbatim from docs/TEST_OUTPUT.txt) ----------------------
suites = ["store\n(substrate)", "activation", "coalitions", "field", "perceive\n(slice)"]
checks = [45, 35, 19, 13, 18]
TOTAL = sum(checks)          # 130
assert TOTAL == 130, TOTAL   # guard against accidental edits

# layer status (honest boundary)
proven = [True, True, False, False, False]   # store & activation proven; rest exploratory
colors = ["#2e7d32" if p else "#1565c0" for p in proven]

fig, ax = plt.subplots(figsize=(8.2, 4.8))
bars = ax.bar(range(len(suites)), checks, color=colors, edgecolor="black", linewidth=0.6, width=0.66)

for i, (b, v) in enumerate(zip(bars, checks)):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.7, str(v),
            ha="center", va="bottom", fontsize=12, fontweight="bold")

ax.set_xticks(range(len(suites)))
ax.set_xticklabels(suites, fontsize=10)
ax.set_ylabel("Passing assertions (checks)", fontsize=11)
ax.set_ylim(0, 52)
ax.set_title("Psyche test suite: passing assertions per suite\n"
             "130 passed, 0 failed  •  56 test functions  •  CPython 3.13.2",
             fontsize=12.5, fontweight="bold")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(axis="y", linestyle=":", alpha=0.4)

# legend for the honest boundary
from matplotlib.patches import Patch
legend = [Patch(facecolor="#2e7d32", edgecolor="black",
                label="PROVEN: determinism / integrity / purity"),
          Patch(facecolor="#1565c0", edgecolor="black",
                label="EXPLORATORY: mechanics tested; meaning NOT claimed")]
ax.legend(handles=legend, loc="upper right", fontsize=8.6, framealpha=0.95)

fig.text(0.5, -0.02,
         "Counts of passing assertions only. Proves the mechanism does exactly and only what it says, "
         "reproducibly; it does NOT measure cognitive quality.",
         ha="center", fontsize=8, style="italic", wrap=True)

fig.tight_layout()
fig.savefig(OUT, dpi=200, bbox_inches="tight")
print("wrote", os.path.normpath(OUT))
