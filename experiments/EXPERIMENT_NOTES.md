# Experiment Notes — Phase 2 (empirical validation)

Running log of mechanism findings that shape the experiments. Plain language; numbers
captured literally from `results/`.

---

## STEP 0 — Does spreading activation normalize by out-degree? (decides the fan study)

**Question.** When activation radiates from a source node, does the engine *divide* /
normalize the source's energy among its out-roads — so that each individual target
receives less as the source acquires more out-edges — or does each out-road *independently*
transmit `energy × strength × decay`, with no regard to how many siblings it has?

**Answer (from reading the frozen engine).** No normalization. In
`src/psyche_activation.py`, inside `spread_activation`, each out-road is fed the source
node's **full** activation:

```python
outgoing = node_act                                   # the source's FULL activation
...
transmitted = outgoing * road.strength * decay_per_hop # per-edge, independent of fan
...
activation[target] = activation.get(target, 0.0) + transmitted
```

There is no `/ len(out_roads)`, no division of `node_act` across the source's out-edges,
and no per-source energy budget. Each edge carries the source's whole activation, attenuated
only by that edge's own `strength` (conductance) and the global `decay_per_hop` (distance
penalty). Two distinct attenuators — neither of them out-degree.

**Empirical confirmation.** `step0_probe.py` builds one source `S` with **equal-strength**
out-edges (identical traverse count) and reads the activation arriving at a target `T1`,
for source out-degree **1 vs 8**. Verbatim (`results/step0_probe_output.txt`):

```
  out-degree 1  ->  T1 activation = 0.2433743975
  out-degree 8  ->  T1 activation = 0.2433743975
```

Byte-identical. Adding seven more equal out-edges to the source did **not** reduce (or
change at all) the activation reaching `T1`. Energy is not shared; it is replicated down
every road.

**Consequence for the fan experiment (stated in advance).** Because activation is **not**
normalized by out-degree, a fan manipulation that varies *only connectivity* while holding
edge strength equal will produce a **FLAT** curve: a target's activation depends on its own
incoming edge strength and distance, not on how many siblings its source has. So under the
human-fan-effect direction ("more associations on a cue ⇒ weaker/slower retrieval of any
one of them"), Psyche is **expected to show NO fan effect**.

Per the project's discipline this flat/null outcome is the **honest, informative result** —
not a defect to engineer around. The engine is correct and will not be modified to
manufacture an effect it does not have. What the fan study delivers is (a) a reusable,
pre-registered, reproducible measurement harness and (b) a characterized null with a clear
mechanistic explanation, which in turn tells the priming study (2B) what kind of contrast
*can* register (see `FAN_EFFECT.md` → "Implication for the priming study").

**Determinism note.** The probe (and all experiments) build against `Clock(simulated=True)`
so that elapsed-time decay is a no-op (dt = 0). That makes "all edges equal strength" exact
rather than approximate and keeps the build deterministic; the only remaining randomness
(uuid4 IDs, hash-seeded set iteration) is what the library is already verified invariant to.
