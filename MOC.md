# Map of content

The entry point for reading this repository as an Obsidian vault. Every link is a standard
Markdown link, so the same map also works on GitHub. Psyche is one open research project that
builds brain-inspired components in stages, with artificial general intelligence (AGI) as its
long-term aim, named only as an aim. Stage 1, the substrate, is the foundation and is paused;
stage 2, spiking cognitive maps, is the active line. Both are recorded under D-031 in
[DECISIONS.md](DECISIONS.md), and the aim under D-033.

## Start here

- [README.md](README.md): the repository landing page, with the stages and the current status.
- [Reader's guide](docs/guide.md): where to begin, what the project is and why, and where to go
  next.
- [Questions and answers](docs/faq.md): short answers to what newcomers ask first.
- [Progress](docs/progress.md): the public record of the research plan as it moves.
- [How Psyche is run](docs/governance.md): who leads the project, the four roles, and how the work
  is kept honest.
- [Research overview](docs/research/README.md): what the cognitive-map line asks, what it plans
  to contribute, and what it does not claim.
- [Origins](docs/research/origins.md): how the substrate led to the cognitive-map line.

<!-- generated:status-line:start -->
**Now:** P0 Novelty review and setup (2026-10-23 to 2026-11-15) · **Next gate:** A Novelty, 2026-11-15
<!-- generated:status-line:end -->

## Facts

A few files hold the facts, and every other document defers to them. Statuses are not copied
here; read them from the ledger.

| File | What it holds |
|---|---|
| [tools/ledger.json](tools/ledger.json) | Every quotable substrate fact: test totals, brick statuses, the meaning bar, and the program state that records which stage is active and which is paused |
| [tools/research_plan.json](tools/research_plan.json) | The public plan of the cognitive-map line: phases, gates, layers and deadlines. The only source of the line's dates |
| [DECISIONS.md](DECISIONS.md) | The append-only log of what changed and why |

## Stage 2: spiking cognitive maps (active)

Each page is a public summary. Detail is withheld until submission under the
[disclosure policy](docs/research/disclosure-policy.md).

| Page | What it covers |
|---|---|
| [Overview](docs/research/README.md) | The research questions, planned contributions and non-claims |
| [Origins](docs/research/origins.md) | How the substrate led to this line: what carries over, what does not, and where it points |
| [Roadmap](docs/research/roadmap.md) | Phases, layers and deadlines, generated from the plan file |
| [Decision gates](docs/research/gates.md) | The question each gate answers, and what happens if one is not passed |
| [Test battery](docs/research/test-battery.md) | The classic paradigms behind the battery, the environment families and the fairness rules |
| [Claims and scope](docs/research/claims-and-scope.md) | What the line may and may not claim, what is in and out of scope, and the writing rules |
| [Engineering](docs/research/engineering.md) | Coding standards, reproducibility, determinism, statistics and figures |
| [Glossary](docs/research/glossary.md) | Terms used on these pages |
| [Reading list](docs/research/reading-list.md) | Classic background reading |
| [Disclosure policy](docs/research/disclosure-policy.md) | What is public, what is withheld, and when it is released |
| [cogmap/](cogmap/README.md) | The export-only package for released versions of the spiking model; nothing released yet |

## Stage 1: the substrate (foundation, paused)

The substrate is a dependency-free Python prototype of a memory-and-activation substrate, the
project's foundation. While its development is paused, no new brick starts and no default
changes; its suites, ledger and checks stay maintained.

| Document | Role |
|---|---|
| [docs/PSYCHE.md](docs/PSYCHE.md) | The substrate's overview and record, formerly the repository README |
| [Architecture](docs/ARCHITECTURE.md) | The as-built technical reference for the code in `src/` |
| [Methodology](docs/METHODOLOGY.md) | How adversarial testing caught structural bugs |
| [Technical report](docs/REPORT.md) | The archived account of the substrate; the published record is the DOI release under `docs/report/` |
| [Substrate roadmap](docs/psyche_roadmap.md) | The substrate's paused roadmap. It narrates history, superseded states included, and is not a status source |
| [Specs](docs/specs/) | Brick specifications and feasibility pre-checks |
| [Pre-registrations](docs/experiments/) | Frozen pre-registrations, written before any graded result. Any change made before data existed is recorded in the file with its lineage. After a result the protocol is never changed; later notes are labelled additions, not rewrites |
| [The three walls](docs/three-walls.md) | The substrate's three negative results, each stopped before a graded run, and the pattern they show |
| [Design and vision](docs/design/README.md) | The original vision documents, written before the code and largely unbuilt: only the layer plans for the topology and the substrate store correspond to built code. Their language is vision framing, not a claim about the prototype. Start with the disclaimer |

## Obsidian

Open the repository root as a vault; this file is its entry point. Obsidian is a reading and
thinking surface, not where facts live. A fact changes in the ledger, or for the research
line's dates in the plan file, never in a note.

The Specs and Pre-registrations links point at folders. They open on GitHub; in Obsidian,
browse those folders from the file explorer.
