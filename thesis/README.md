# Thesis package

> Nothing has been released here yet. This folder fills only through releases made under the
> [disclosure policy](../docs/thesis/disclosure-policy.md).

This folder is the home of the thesis code in this repository. The thesis itself is described
in the [thesis overview](../docs/thesis/README.md). Its phases, gates and dates are on the
[roadmap](../docs/thesis/roadmap.md), generated from
[`tools/thesis_plan.json`](../tools/thesis_plan.json).

## How code arrives here

Thesis code is developed in a private companion and reaches this folder only as a release: a
complete, working, older tagged version, never the current state. The conditions a release must
meet, and the checks it passes before it leaves, are in the
[release rule](../docs/thesis/disclosure-policy.md#the-release-rule).

This folder is export-only (D-031 in [DECISIONS.md](../DECISIONS.md)). No agent and no
contributor edits its files directly. A change here arrives as a new release.

## What will arrive, and when

Code is released in groups. Each group has an earliest-release condition, and the lag in the
release rule applies on top of it.

| Group | Contents | Earliest release |
|---|---|---|
| Battery | The environments, the test battery, the agent interface, the random and shortest-path reference agents, the behaviour and statistics metrics, and their public tests | After paper submission |
| Operation counter | The counter behind the analytic estimate of synaptic operations, and its tests | After paper submission |
| Model | The spiking model: only the version that was submitted, never a later one | After the review decision or the thesis defence, whichever comes earlier |

The submission deadline and the other dates are in the [roadmap](../docs/thesis/roadmap.md).
Some material is never released through this process; the
[release groups](../docs/thesis/disclosure-policy.md#release-groups) section of the policy lists
it.

## Installing

Installation will be separate from Psyche. When the earliest group is released, it will bring
its own project file with pinned dependencies and its own test command, documented here. The
root [`requirements.txt`](../requirements.txt) covers only the Psyche core, which needs nothing
beyond the Python standard library, and does not install this package.

## Relation to the Psyche core

The Psyche core under [`src/`](../src) never imports this package, and nothing in this folder is
registered in [`run_tests.py`](../run_tests.py). The core's suites and its governance checks
stay standard-library only and unaffected by anything released here. How the paused Psyche
project relates to the thesis is described in
[psyche-and-the-thesis.md](../docs/thesis/psyche-and-the-thesis.md).
