#!/usr/bin/env python3
"""
Generate the three matplotlib figures for the Psyche paper as vector PDFs.

Every plotted value is transcribed from a committed real source and matches
Appendix B of the paper:

  F-3b  fan_flat.pdf      target activation 0.2433743975, spread 0.0, across
                          fan in {1,2,4,8,16}.
                          source: experiments/results/fan_effect_output.txt
  F-3a  s0_collapse.pdf   N_S0 = 7 weight-blind in-degree-matched pairs against
                          the pre-registered floor of 30; N_S+ = 296 weight-
                          informative pairs.
                          source: experiments/results/priming_1e_selection_output.txt
  F-3c  friction_band.pdf realistic CPU-bound friction ~ 0 (scale-invariant)
                          vs the yield-dominated band [0.79, 0.93], mean 0.86,
                          produced only by an injected 0.5 ms wait.
                          source: docs/experiments/EXP-2c-interoception.md, sec 6.1

Run with the arm64 conda interpreter:
    /opt/anaconda3/bin/python make_figures.py
"""

import os
import matplotlib
matplotlib.use("pdf")  # non-interactive, vector PDF output
import matplotlib.pyplot as plt

# ----------------------------------------------------------------------------
# Restrained, publication-style defaults. Vector output, embedded TrueType
# fonts (Type 42), serif family, no top/right spines, no chartjunk.
# ----------------------------------------------------------------------------
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.titlesize": 11,
    "axes.labelsize": 11,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.8,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "lines.linewidth": 1.6,
    "pdf.fonttype": 42,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
})

INK = "#2b2b2b"
PRIMARY = "#39516b"     # muted steel blue
ACCENT = "#8f3b3b"      # muted brick (used sparingly: thresholds / means)
BAND = "#c9d2dc"        # light gray-blue fill

HERE = os.path.dirname(os.path.abspath(__file__))


def save(fig, name):
    path = os.path.join(HERE, name)
    fig.savefig(path)
    plt.close(fig)
    print("wrote", path)


# ============================================================================
# F-3b : the flat fan sweep
# ============================================================================
def fig_fan_flat():
    fan = [1, 2, 4, 8, 16]
    value_str = "0.2433743975"        # verbatim from fan_effect_output.txt
    value = float(value_str)
    x = list(range(len(fan)))         # evenly spaced categorical positions

    fig, ax = plt.subplots(figsize=(5.4, 3.2))
    ax.plot(x, [value] * len(fan), marker="o", color=PRIMARY,
            markerfacecolor=PRIMARY, markeredgecolor=PRIMARY, markersize=6,
            zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels([str(f) for f in fan])
    ax.set_xlabel("Source fan (out-degree)")
    ax.set_ylabel("Activation at target")
    ax.set_ylim(0.0, 0.30)
    ax.set_xlim(-0.4, len(fan) - 0.6)
    ax.annotate(value_str + "  (identical across fan; spread 0)",
                xy=(x[0], value), xytext=(-0.3, value - 0.055),
                fontsize=9.5, color=INK, va="top", ha="left")
    save(fig, "fan_flat.pdf")


# ============================================================================
# F-3a : the weight-blind stratum collapse
# ============================================================================
def fig_s0_collapse():
    n_s0 = 7      # weight-blind, in-degree-matched pairs
    n_sp = 296    # weight-informative pairs
    floor = 30    # pre-registered floor on N_S0

    fig, ax = plt.subplots(figsize=(5.4, 3.4))
    ax.bar([0, 1], [n_s0, n_sp], width=0.5, color=PRIMARY, zorder=3)

    # the pre-registered floor, drawn only over the N_S0 bar it governs
    ax.hlines(floor, -0.42, 0.42, color=ACCENT, lw=1.4, ls="--", zorder=4)
    ax.annotate("floor on $N_{S0}$: " + str(floor), xy=(0.42, floor),
                xytext=(0.55, floor + 4), fontsize=9.5, color=ACCENT,
                va="bottom", ha="left")

    for xi, c in zip([0, 1], [n_s0, n_sp]):
        ax.text(xi, c + 6, str(c), ha="center", va="bottom", fontsize=11,
                color=INK)

    ax.set_xticks([0, 1])
    ax.set_xticklabels(["$N_{S0}$\nweight-blind,\nin-degree-matched",
                        "$N_{S+}$\nweight-informative"])
    ax.set_ylabel("Prime pairs")
    ax.set_ylim(0, 320)
    ax.set_xlim(-0.6, 1.6)
    save(fig, "s0_collapse.pdf")


# ============================================================================
# F-3c : friction near zero on realistic work vs the manufactured band
# ============================================================================
def fig_friction_band():
    band_lo, band_hi, band_mean = 0.79, 0.93, 0.86  # measured w/ injected wait
    LIGHTBAND = "#e6ebf1"   # lightened so the manufactured band recedes

    fig, ax = plt.subplots(figsize=(5.4, 3.3))

    # manufactured band: present only with the injected wait. Drawn first and
    # lightened so it does not dominate; tagged so it reads as the artifact.
    ax.fill_between([0.80, 1.20], band_lo, band_hi, color=LIGHTBAND, zorder=1)
    ax.hlines(band_mean, 0.80, 1.20, color=ACCENT, lw=1.3, alpha=0.85, zorder=2)
    ax.annotate("[%.2f, %.2f], mean %.2f\n(manufactured)"
                % (band_lo, band_hi, band_mean),
                xy=(1.0, band_lo), xytext=(1.0, 0.585),
                fontsize=9.0, color="#5a5a5a", ha="center")

    # realistic CPU-bound work: friction ~ 0 (analytic; scale-invariant). This
    # is the finding, so it carries the strongest visual weight: a bold segment
    # and a prominent marker, labelled directly above it.
    ax.hlines(0.0, -0.22, 0.22, color=PRIMARY, lw=5, zorder=5)
    ax.plot([0.0], [0.0], marker="o", color=PRIMARY, markersize=11,
            markeredgecolor="white", markeredgewidth=1.0, zorder=6)
    ax.annotate("$\\approx 0$  (scale-invariant)", xy=(0.0, 0.0),
                xytext=(0.0, 0.06), fontsize=9.5, color=INK, ha="center")

    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Realistic\nCPU-bound work",
                        "With injected\n0.5 ms wait"])
    ax.set_ylabel("Friction")
    ax.set_ylim(-0.03, 1.0)
    ax.set_xlim(-0.6, 1.6)
    save(fig, "friction_band.pdf")


if __name__ == "__main__":
    fig_fan_flat()
    fig_s0_collapse()
    fig_friction_band()
    print("done")
