# Map of content

The entry point for reading this repository as an Obsidian vault. Every link is a standard
Markdown link, so the same map also works on GitHub. The repository now serves an
undergraduate thesis. Psyche, the project it was built for, is paused under D-031 in
[DECISIONS.md](DECISIONS.md).

## Start here

- [README.md](README.md): the repository landing page.
- [Thesis overview](docs/thesis/README.md): what the thesis asks, what it plans to contribute,
  and what it does not claim.

<!-- generated:status-line:start -->
**Now:** P0 Novelty review and setup (2026-10-23 to 2026-11-15) · **Next gate:** A Novelty, 2026-11-15
<!-- generated:status-line:end -->

## Facts

A few files hold the facts, and every other document defers to them. Statuses are not copied
here; run `/psyche-orient` or read the ledger.

| File | What it holds |
|---|---|
| [tools/ledger.json](tools/ledger.json) | Every quotable Psyche fact: test totals, brick statuses, the meaning bar, and the program state that records which project is active and which is paused |
| [tools/thesis_plan.json](tools/thesis_plan.json) | The public thesis plan: phases, gates, layers and deadlines. The only source of thesis dates |
| [DECISIONS.md](DECISIONS.md) | The append-only log of what changed and why |

## Thesis

Each page is a public summary. Detail is withheld until submission under the
[disclosure policy](docs/thesis/disclosure-policy.md).

| Page | What it covers |
|---|---|
| [Overview](docs/thesis/README.md) | The research questions, planned contributions and non-claims |
| [Roadmap](docs/thesis/roadmap.md) | Phases, layers and deadlines, generated from the plan file |
| [Decision gates](docs/thesis/gates.md) | The question each gate answers, and what happens if one is not passed |
| [Test battery](docs/thesis/test-battery.md) | The classic paradigms behind the battery, the environment families and the fairness rules |
| [Claims and scope](docs/thesis/claims-and-scope.md) | What the thesis may and may not claim, what is in and out of scope, and the writing rules |
| [Engineering](docs/thesis/engineering.md) | Coding standards, reproducibility, determinism, statistics and figures |
| [Glossary](docs/thesis/glossary.md) | Terms used on these pages |
| [Reading list](docs/thesis/reading-list.md) | Classic background reading |
| [Psyche and the thesis](docs/thesis/psyche-and-the-thesis.md) | How the paused Psyche project relates to the thesis: methodology and tooling |
| [Disclosure policy](docs/thesis/disclosure-policy.md) | What is public, what is withheld, and when it is released |

## Psyche (paused)

Psyche is a dependency-free Python prototype of a memory-and-activation substrate. While it is
paused, no new brick starts and no default changes; its suites, ledger and checks stay
maintained.

| Document | Role |
|---|---|
| [docs/PSYCHE.md](docs/PSYCHE.md) | The project overview, formerly the repository README |
| [Architecture](docs/ARCHITECTURE.md) | The as-built technical reference for the code in `src/` |
| [Methodology](docs/METHODOLOGY.md) | How adversarial testing caught structural bugs |
| [Technical report](docs/REPORT.md) | The archived account of the project; the published record is the DOI release under `docs/report/` |
| [Psyche roadmap](docs/psyche_roadmap.md) | The paused roadmap. It narrates history, superseded states included, and is not a status source |
| [Specs](docs/specs/) | Brick specifications, feasibility pre-checks and the held paper's claim inventory |
| [Pre-registrations](docs/experiments/) | Frozen pre-registrations, written before any graded result. Any change made before data existed is recorded in the file with its lineage. After a result the protocol is never changed; later notes are labelled additions, not rewrites |
| [Design and vision](docs/design/README.md) | The original vision documents, written before the code and largely unbuilt: only the layer plans for the topology and the substrate store correspond to built code. Their language is vision framing, not a claim about the prototype. Start with the disclaimer |

## Obsidian

Open the repository root as a vault; this file is its entry point.
[obsidian/README.md](obsidian/README.md) explains the setup, the plugins worth having, and why
Obsidian is a reading and thinking surface, not where facts live. A fact changes in the
ledger, or for thesis dates in the plan file, never in a note.

The Specs and Pre-registrations links point at folders. They open on GitHub; in Obsidian,
browse those folders from the file explorer.
