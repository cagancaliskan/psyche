# Phase 2B data — Small World of Words (SWOW-EN)

This directory holds the **input data** for the Phase 2B semantic-priming study. The raw
data file is **NOT committed** to this repository (it is ~53 MB and the SWOW license does
not permit redistribution). You must obtain it yourself and place it here; the code reads it
by an explicit path and fails with a clear message if it is absent.

## File this study expects

```
experiments/data/strength.SWOW-EN.R123.20180827.csv
```

- **Despite the `.csv` extension it is TAB-separated.**
- Header: `cue<TAB>response<TAB>R123<TAB>N<TAB>R123.Strength`
- One row per (cue, response) association.
  - `cue` → `response` is a directed association (we use this as a directed edge).
  - `R123.Strength` ∈ [0, 1] is the association strength (we map it to edge weight).
  - `R123` is the response count; `N` is the total responses for that cue.
- Size as used here: **1,389,711 data rows**, **12,217 distinct cues**, **133,763 distinct
  words** (nodes = union of all cues and responses).

### Parsing note (important)

A small number of rows contain a stray double-quote character. Python's `csv` module treats
`"` as a quote and then reads past the end of line, raising
`_csv.Error: field larger than field limit (131072)`. **Parse this file as plain TSV**
(`line.split("\t")`), which is what `experiments/swow.py` does. Every data row has exactly 5
tab-separated fields.

## How to obtain it

1. Go to the Small World of Words project site: <https://smallworldofwords.org/>
   (Research → Data, English / SWOW-EN).
2. Download the **R123 strength** file (the 2018-08-27 release used here is
   `strength.SWOW-EN.R123.20180827.csv`). Registration/agreement to the data-use terms may
   be required.
3. Place the downloaded file at the exact path above.

If you use a different SWOW release, update the path constant `DEFAULT_DATA_PATH` in
`experiments/swow.py` and re-record the version here; the edge-mapping and selection rules
are version-independent but the captured numbers in `results/` are specific to this release.

## License & citation

The SWOW data are © the Small World of Words project and are provided under their own
data-use terms — see the project website. They are used here for non-commercial research and
are **not redistributed** in this repository. The full arm (c) pair list that
`experiments/priming_1e.py` writes (`priming_1e_pairs_arm_c.txt`) is not kept here either,
because it carries SWOW strengths in bulk: its SHA-256 stays frozen in
`docs/experiments/EXP-1e-priming.md`, and the script regenerates it from the SWOW file.

If you use SWOW, cite:

> De Deyne, S., Navarro, D. J., Perfors, A., Brysbaert, M., & Storms, G. (2019).
> *The "Small World of Words" English word association norms for over 12,000 cue words.*
> Behavior Research Methods, 51(3), 987–1006. https://doi.org/10.3758/s13428-018-1115-7

## How this data is used (summary; full detail in `../PRIMING.md`)

- **Graph:** one node per word; a directed road `cue → response` for every row with
  `R123.Strength > 0` (self-loops dropped). Built once on a simulated clock so edge strengths
  are exact and the build is deterministic.
- **Edge-strength mapping (fixed, identical for every edge):**
  `traverse_count = min(10, 1 + floor(R123.Strength * 100))`.
- **Pair selection** (DIRECT / MEDIATED / UNRELATED) is done from graph topology and SWOW
  strength **only**, before any activation is computed.
