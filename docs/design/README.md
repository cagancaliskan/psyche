# Original design & vision documents: read this first

The 13 Markdown files in this folder are the project's **original, aspirational design and
vision documents**, written **before** the code in `src/` existed. They are kept here
**byte-unchanged** as a historical record of the intent that motivated the prototype.

**They describe intent and ambition, not what the built code does or proves:**

These documents use deliberately grand language: "AGI," "a real brain," "mind," "felt
experience," "not artificial, not simulated." **That is vision framing. It is not a claim about
the prototype.** None of it is implemented or validated by the code in this repository. Read it as
a statement of where the author wanted to go, written in the author's own register, not as a
description of a working system.

## What actually corresponds to the built code

Of the 13 files here, only two correspond to what was actually built:

- [`nous_plan_layer0_topology.md`](nous_plan_layer0_topology.md): the topology/graph layer plan.
- [`nous_plan_layer1_substrate_store.md`](nous_plan_layer1_substrate_store.md): the substrate
  store plan, realized in `src/nous_store.py`.

The other **eleven** documents (substrate biology, memory hierarchy, abstraction engine, self
model, motivation architecture, attention & awareness, emotional regulation, the sleeping brain,
the body's voice, how this brain comes to speak, and the project evaluation) describe a large,
**mostly-unbuilt** architecture. They are design exploration, not specifications of shipped code.
Treating any of them as a description of implemented behavior would be a mistake.

## Where the honest account lives

For the verified, hype-free account of the **real** system: what is proven, what is exploratory,
and what is explicitly a known limitation: see, at the repository root and in `docs/`:

- [`../../README.md`](../../README.md): scope, real test results, what this is (and is not).
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md): the as-built technical reference.
- [`../METHODOLOGY.md`](../METHODOLOGY.md): how adversarial testing caught a sequence of real
  structural bugs; the most checkable, transferable part of the project.

## On the gap between these documents and the code

The distance between the vision in this folder and the small, honestly-scoped slice that was
actually built is **intentional and instructive, not a contradiction to be hidden:** The
discipline of narrowing an ambitious vision down to a substrate that can be *proven correct*, and
of refusing to let aspiration stand in for evidence, is exactly the subject of
[`../METHODOLOGY.md`](../METHODOLOGY.md). These vision documents are the "before"; the proven
substrate and the documented known-limitations are the "after." Keeping both, side by side and
clearly labeled, is the honest way to show the work.
