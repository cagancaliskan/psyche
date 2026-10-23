#!/usr/bin/env python3
"""
Figure: adversarial determinism across process hash seeds (before/after).

What is REAL here (traceable to the test sources in tests/):
  - Four determinism tests re-run the same construction in FRESH interpreters under
    several PYTHONHASHSEED values and assert the output is BYTE-IDENTICAL:
        test_psyche_activation : test_determinism_with_same_hop_edge_adversarial   seeds {0,1,3,7,42}
        test_psyche_coalitions : test_determinism_adversarial_across_hash_seeds     seeds {0,1,2,3,7,42,123,999}
        test_psyche_field      : test_field_determinism_adversarial_across_hash_seeds seeds {0,1,2,3,7,42,123,999}
        test_psyche_perceive   : test_slice_determinism_across_hash_seeds           seeds {0,1,2,7,42,999}
    All of these pass (see docs/TEST_OUTPUT.txt), i.e. output is identical across each
    test's seed set.

Honesty:
  - The "AFTER (fixed)" row shows the FACT OF IDENTITY only (a check mark), not any
    invented activation values.
  - The "BEFORE (the bug)" row depicts the DOCUMENTED prior behavior (findings (c)/(d):
    a priority frontier over hash-randomized uuid sets, and uuid tie-breaks, varied
    across process runs). It is shown qualitatively and is NOT a re-measurement; the
    magnitude reported at the time is intentionally omitted (the artifact cannot
    reproduce it).

This figure proves reproducibility of MECHANISM. It says nothing about cognition.

Run with matplotlib:
    python3 determinism_seeds.py      # writes ../rendered/determinism_seeds.png
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "rendered", "determinism_seeds.png")

seeds = [0, 1, 2, 3, 7, 42, 123, 999]          # union shown as columns

fig, ax = plt.subplots(figsize=(9.6, 4.2))
ax.set_xlim(-0.7, len(seeds) + 0.9)
ax.set_ylim(-0.2, 3.25)
ax.axis("off")

# column headers (seeds)
ax.text(-0.6, 3.0, "PYTHONHASHSEED $\\rightarrow$", ha="left", va="center",
        fontsize=9.5, fontweight="bold")
for j, s in enumerate(seeds):
    ax.text(j, 2.62, f"{s}", ha="center", va="center", fontsize=10, fontweight="bold")

def strip(y, label, label_color, mark, face, edge, tcol, right):
    # descriptive label ABOVE the strip (so it never overlaps the cells)
    ax.text(-0.6, y + 0.62, label, ha="left", va="center",
            fontsize=10, fontweight="bold", color=label_color)
    for j in range(len(seeds)):
        ax.add_patch(Rectangle((j - 0.42, y - 0.40), 0.84, 0.80,
                               facecolor=face, edgecolor=edge, linewidth=1.1))
        ax.text(j, y, mark, ha="center", va="center", fontsize=15, color=tcol, fontweight="bold")
    ax.text(len(seeds) - 0.5 + 0.55, y, right, ha="left", va="center",
            fontsize=8.6, color=tcol, fontweight="bold")

# BEFORE: documented bug, varied across seeds (qualitative, not re-measured)
strip(1.55, "BEFORE: priority frontier + uuid tie-break  (the bug)", "#c0392b",
      "$\\neq$", "#fdecea", "#c0392b", "#c0392b", "output\nVARIED")
# AFTER: fixed, byte-identical across seeds (the asserted test result)
strip(0.30, "AFTER: hop-layered expansion + creation_seq tie-break  (current)", "#2e7d32",
      "$\\checkmark$", "#e8f5e9", "#2e7d32", "#2e7d32", "output\nIDENTICAL")

ax.set_title("Adversarial determinism across process hash seeds (before / after)\n"
             "same construction re-run in fresh interpreters; output compared byte-for-byte",
             fontsize=12, fontweight="bold")

fig.text(0.5, -0.06,
         "AFTER = the asserted result of the four determinism tests (identical across each test's seed set: "
         "activation {0,1,3,7,42}; coalitions & field {0,1,2,3,7,42,123,999}; slice {0,1,2,7,42,999}).\n"
         "BEFORE = documented prior behavior (findings c, d), shown qualitatively, not re-measured. "
         "Establishes reproducibility of mechanism only, not cognition.",
         ha="center", fontsize=7.8, style="italic")

fig.tight_layout()
fig.savefig(OUT, dpi=200, bbox_inches="tight")
print("wrote", os.path.normpath(OUT))
