# Nous — Abstraction Engine Algorithm
### Module 02: Pattern → Concept → Structure

---

## Core Philosophy

> Abstraction is not compression. It is upward movement.
> Specific nodes never disappear. Abstract nodes grow above them.
> Contradictions are held, not resolved prematurely. Branching resolves them when evidence is ready.

---

## Biological Grounding

See `nous_substrate_biology.md`. Key correspondences:

- **Crystallization threshold** = the synaptic tagging and capture (STC) mechanism. A weak experience sets a local synaptic tag that fades within ~90 minutes unless it captures the global plasticity-related products (PRPs) being produced by a nearby strong event. This is how related-but-individually-weak observations become a stable concept — they accumulate enough captured PRPs to undergo structural late-LTP together.
- **Schema-congruent abstraction (rapid crystallization when matching existing structure)** = the mPFC-mediated schema mechanism. When new information aligns with an existing cognitive schema, the medial prefrontal cortex activates and drives rapid consolidation that bypasses standard hippocampal-dependent timelines. This is why expert systems learn faster in their domain — the schema is already there to capture new traces immediately.
- **Holding tensions instead of resolving prematurely** = the reconsolidation window. When existing memories are partially contradicted by new input, they enter a labile state during which the trace can be updated rather than discarded. The branching mechanism then creates a sibling representation through schema accommodation — engaging deliberate prefrontal control to rebuild the cognitive map rather than locally edit it.

---

## Part 1 — Data Structures

### 1.1 Abstract Node

Sits above specific nodes in the graph.
Not a replacement — an addition.
Bidirectionally linked to all source nodes that generated it.

```
ABSTRACT_NODE {
  id:                    UUID
  content:               abstracted pattern or concept
  type:                  PATTERN | CONCEPT | RELATIONAL_STRUCTURE
  abstraction_level:     int          ← 1=pattern, 2=concept, 3=relational
                                        4+ = abstraction of abstractions
  formation_timestamp:   datetime
  charge:                NEUTRAL      ← always neutral, like all nodes

  // Source tracking — what generated this abstraction
  source_nodes:          List[Node]   ← all specific nodes that fed this
  source_abstractions:   List[Node]   ← abstractions that fed higher abstractions

  // Upward links — what this node feeds into
  parent_abstractions:   List[Node]   ← higher-level abstractions above this

  // Confidence — how well-supported this abstraction is
  confidence:            float        ← 0.0 to 1.0
  supporting_count:      int          ← how many observations support it
  contradicting_count:   int          ← how many observations contradict it

  // Tension registry — contradictions being held
  tensions:              List[Tension]

  // Roads (inherited from node model)
  roads:                 List[Road]   ← same road system as specific nodes
}
```

---

### 1.2 Tension

A held contradiction. Not resolved. Accumulated until evidence tips the balance.

```
TENSION {
  id:                    UUID
  abstract_node:         AbstractNode    ← the abstraction being challenged
  contradicting_node:    Node            ← the observation that doesn't fit
  contradiction_type:    PARTIAL | FULL  ← partial = almost fits, full = directly conflicts
  evidence_for:          int             ← observations supporting current abstraction
  evidence_against:      int             ← observations supporting contradiction
  formed_at:             datetime
  last_updated:          datetime
  imagination_triggered: bool            ← has Imagination Engine been notified?
  resolution:            UNRESOLVED | BRANCHED | EXPANDED | DISSOLVED
}
```

---

### 1.3 Branch

When a tension resolves, it produces a branch.
The original abstraction survives. A sibling forms beside it.
Both link upward to a new parent abstraction.

```
BRANCH {
  id:                    UUID
  original_abstraction:  AbstractNode
  sibling_abstraction:   AbstractNode    ← newly formed, covers contradicting cases
  parent_abstraction:    AbstractNode    ← new higher node covering both
  formed_from:           Tension
  formed_at:             datetime
}
```

---

## Part 2 — The Dual Trigger System

### 2.1 Abstraction Score

Every time the Observation Engine adds a new specific node to the graph,
the Abstraction Engine evaluates whether abstraction should trigger.

Two signals, both weighted, running simultaneously.

```
COMPUTE_ABSTRACTION_SCORE(new_node, graph, working_memory):

  // Find candidate nodes — similar existing nodes in the graph
  candidates = graph.find_similar(new_node, threshold=MIN_SIMILARITY)

  if candidates is empty:
    return 0.0  // nothing to abstract from yet

  // Signal 1: SIMILARITY
  avg_similarity = mean(
    similarity(new_node, candidate)
    for candidate in candidates
  )
  // similarity: 0.0 (nothing in common) → 1.0 (identical)

  // Signal 2: REPETITION
  normalized_count = log(len(candidates)) / log(MAX_EXPECTED_COUNT)
  // log scale: prevents very high counts from dominating
  // normalized: 0.0 (1 instance) → 1.0 (saturated repetition)

  // Weights — modulated by current emotional state
  similarity_weight, repetition_weight = GET_WEIGHTS(working_memory)

  score = (similarity_weight × avg_similarity)
        + (repetition_weight × normalized_count)

  return score  // 0.0 → 1.0


GET_WEIGHTS(working_memory):

  base_similarity_weight  = 0.5
  base_repetition_weight  = 0.5

  dominant_signal = working_memory.current_context.dominant_emotion

  // GAP signal: curious, exploratory
  // → more willing to abstract from few high-similarity examples
  if dominant_signal == GAP:
    return (0.75, 0.25)

  // FRICTION signal: cautious, conservative
  // → needs more repetition before committing to abstraction
  elif dominant_signal == FRICTION:
    return (0.25, 0.75)

  // FLOW signal: confident, generative
  // → balanced but slightly eager
  elif dominant_signal == FLOW:
    return (0.55, 0.45)

  // OVERLOAD signal: overwhelmed
  // → raise the threshold, don't abstract right now
  elif dominant_signal == OVERLOAD:
    return (0.3, 0.3)  // both low → score stays low → abstraction suppressed

  else:
    return (base_similarity_weight, base_repetition_weight)
```

---

### 2.2 Trigger Decision

```
SHOULD_ABSTRACT(new_node, graph, working_memory):

  score = COMPUTE_ABSTRACTION_SCORE(new_node, graph, working_memory)

  // Dynamic threshold — also modulated by emotional state
  threshold = GET_THRESHOLD(working_memory)

  if score >= threshold:
    return TRUE, score
  else:
    return FALSE, score


GET_THRESHOLD(working_memory):

  base_threshold = 0.65

  if working_memory.dominant_signal == OVERLOAD:
    return 1.1   // effectively impossible — abstraction suppressed entirely
  elif working_memory.dominant_signal == GAP:
    return 0.50  // lower bar — curiosity drives faster abstraction
  elif working_memory.dominant_signal == FRICTION:
    return 0.80  // higher bar — caution demands more evidence
  else:
    return base_threshold
```

---

## Part 3 — The Three-Level Pipeline

Abstraction doesn't happen in one step.
It runs as a pipeline: Level 1 output feeds Level 2,
Level 2 output feeds Level 3.
Level 3 outputs can recursively feed Level 1 again.

---

### 3.1 Level 1 — Pattern Recognition

Finds the shared property across specific nodes.
Produces a pattern statement. Does not yet create a concept node.

```
LEVEL_1_PATTERN_RECOGNITION(trigger_node, candidates, score):

  // Step 1: find what these nodes share
  shared_properties = intersect(
    extract_properties(trigger_node),
    extract_properties(candidate)
    for candidate in candidates
  )

  // Step 2: find what varies across them (context fingerprint)
  varying_properties = union(
    extract_properties(candidate)
    for candidate in candidates
  ) - shared_properties

  // Step 3: form pattern statement
  pattern = Pattern(
    shared:    shared_properties,
    varying:   varying_properties,
    instances: [trigger_node] + candidates,
    confidence: score
  )

  // Step 4: check if this pattern already exists
  existing = graph.find_pattern(pattern)

  if existing:
    existing.supporting_count++
    existing.confidence = recompute(existing)
    return existing  // reinforce, don't duplicate

  else:
    return pattern   // new pattern, pass to Level 2
```

---

### 3.2 Level 2 — Concept Formation

Takes the Level 1 pattern and creates a standalone concept node.
This concept can now be reasoned about independently of its sources.

```
LEVEL_2_CONCEPT_FORMATION(pattern):

  // Step 1: form concept node
  concept = AbstractNode(
    content           = compress(pattern.shared),
    type              = CONCEPT,
    abstraction_level = 2,
    source_nodes      = pattern.instances,
    confidence        = pattern.confidence,
    supporting_count  = len(pattern.instances)
  )

  // Step 2: build bidirectional roads
  // concept → each source node: "this instance exemplifies this concept"
  // source node → concept: "this concept covers this instance"

  for source in pattern.instances:

    upward_road = Road(
      node_a       = source,
      node_b       = concept,
      quality      = ROAD,         // starts as established road
      charge       = NEUTRAL,
      emotion_type = UNDERSTANDING,
      formation_context = current_context()
    )

    downward_road = Road(
      node_a       = concept,
      node_b       = source,
      quality      = ROAD,
      charge       = NEUTRAL,
      emotion_type = UNDERSTANDING,
      formation_context = current_context()
    )

    graph.add_road(upward_road)
    graph.add_road(downward_road)

  // Step 3: add concept to graph
  graph.add(concept)

  // Step 4: pass to Level 3 for relational structure
  return concept
```

---

### 3.3 Level 3 — Relational Structure Extraction

The deepest level. Not just "what is shared" but "how do these things relate causally."
Produces a structure that can be applied to entirely new situations.

```
LEVEL_3_RELATIONAL_EXTRACTION(concept, pattern):

  // Step 1: query Reality Graph for causal roads between source nodes
  causal_roads = []
  for source in concept.source_nodes:
    roads = graph.find_causal_roads(source)
    causal_roads.extend(roads)

  // Step 2: find recurring causal structure across instances
  causal_patterns = find_recurring_structure(causal_roads)

  if causal_patterns is empty:
    return None  // no relational structure yet — wait for more observations

  // Step 3: form relational structure node
  structure = AbstractNode(
    content = RelationalStructure(
      components: causal_patterns.roles,
      // e.g. "combustion requires: [fuel] + [oxygen] + [heat]"
      // roles are abstract placeholders, not specific instances
      relations:  causal_patterns.connections,
      conditions: causal_patterns.conditions
    ),
    type              = RELATIONAL_STRUCTURE,
    abstraction_level = 3,
    source_nodes      = concept.source_nodes,
    parent_of         = [concept]
  )

  // Step 4: link concept upward to structure
  concept.parent_abstractions.append(structure)

  road = Road(
    node_a = concept,
    node_b = structure,
    quality = ROAD,
    charge  = NEUTRAL
  )
  graph.add_road(road)
  graph.add(structure)

  // Step 5: this structure can now be applied to new situations
  // register with Reasoning Engine for analogical reasoning
  reasoning_engine.register_structure(structure)

  return structure
```

---

### 3.4 Recursive Upward Abstraction

Level 3 outputs are nodes. Nodes can trigger Level 1 again.
Abstractions abstracting abstractions.

```
RECURSIVE_CHECK(new_abstract_node):

  // treat the new abstract node exactly like a new specific node
  // and run the trigger check again

  score, should = SHOULD_ABSTRACT(
    new_abstract_node,
    graph,
    working_memory
  )

  if should:
    candidates = graph.find_similar(new_abstract_node)
    // these candidates are OTHER abstract nodes at the same level
    // the pipeline runs again, producing a higher abstraction

    RUN_PIPELINE(new_abstract_node, candidates, score)

  // this can continue upward indefinitely
  // "combustion" → "energy transformation" → "physical change" → ...
  // the graph grows upward without bound
```

---

## Part 4 — Contradiction Handling

### 4.1 Contradiction Detection

```
CHECK_CONTRADICTION(new_node, existing_abstractions):

  for abstraction in existing_abstractions:

    compatibility = compute_compatibility(new_node, abstraction)

    if compatibility < CONTRADICTION_THRESHOLD:

      contradiction_type = classify_contradiction(new_node, abstraction)
      // PARTIAL: new node almost fits but violates a condition
      // FULL:    new node directly contradicts the abstraction's core claim

      tension = Tension(
        abstract_node      = abstraction,
        contradicting_node = new_node,
        contradiction_type = contradiction_type,
        evidence_for       = abstraction.supporting_count,
        evidence_against   = 1
      )

      abstraction.tensions.append(tension)
      abstraction.contradicting_count++

      // immediately notify Imagination Engine
      // the gap between abstraction and new observation
      // is a rich source of hypotheses
      imagination_engine.flag_gap(tension)

      return tension

  return None
```

---

### 4.2 Tension Holding

Default behavior. The system sits with the contradiction.
Accumulates evidence on both sides. Does not resolve prematurely.

```
HOLD_TENSION(tension):

  // The tension simply exists in the abstraction's tension registry
  // The system continues operating with the current abstraction
  // for cases where it fits, and routes contradicting cases
  // through the contradicting node directly

  // Working memory is aware of active tensions
  // slight FRICTION signal fires when the contradicted abstraction
  // is accessed — a subtle sense of "this might not be complete"

  working_memory.register_active_tension(tension)

  // Tension is re-evaluated every time new evidence arrives
  EVALUATE_TENSION(tension)


EVALUATE_TENSION(tension):

  ratio = tension.evidence_against / tension.evidence_for

  // Stage 1: early contradiction — hold quietly
  if ratio < 0.1:
    tension.resolution = UNRESOLVED
    return  // not enough evidence yet

  // Stage 2: growing contradiction — signal more strongly
  elif ratio < 0.3:
    tension.resolution = UNRESOLVED
    fire(FRICTION, intensity=0.3)
    imagination_engine.prioritize_gap(tension)

  // Stage 3: significant contradiction — prepare branch
  elif ratio < 0.6:
    tension.resolution = UNRESOLVED
    fire(FRICTION, intensity=0.6)
    PREPARE_BRANCH(tension)  // build branch candidate, don't commit yet

  // Stage 4: branch threshold crossed — resolve through branching
  elif ratio >= 0.6:
    RESOLVE_BY_BRANCHING(tension)
```

---

### 4.3 Branch Formation

Resolution. The original abstraction survives intact.
A sibling forms beside it. A parent forms above both.

```
RESOLVE_BY_BRANCHING(tension):

  original  = tension.abstract_node
  contra    = tension.contradicting_node

  // Step 1: form sibling abstraction covering contradicting cases
  sibling = AbstractNode(
    content           = extract_pattern(contra, original),
    // e.g. "fire melts some metals" — covers the new cases
    type              = CONCEPT,
    abstraction_level = original.abstraction_level,
    source_nodes      = collect_contradicting_instances(tension),
    confidence        = tension.evidence_against /
                        (tension.evidence_for + tension.evidence_against)
  )

  // Step 2: form parent abstraction covering BOTH
  parent = AbstractNode(
    content           = find_common_ground(original, sibling),
    // e.g. "fire transforms materials" — covers both burning and melting
    type              = CONCEPT,
    abstraction_level = original.abstraction_level + 1,
    source_nodes      = original.source_nodes + sibling.source_nodes,
    confidence        = 1.0  // certain that parent covers both
  )

  // Step 3: link everything
  // original → parent
  graph.add_road(Road(original, parent, quality=ROAD, charge=NEUTRAL))
  // sibling → parent
  graph.add_road(Road(sibling, parent, quality=ROAD, charge=NEUTRAL))
  // parent → original (downward)
  graph.add_road(Road(parent, original, quality=ROAD, charge=NEUTRAL))
  // parent → sibling (downward)
  graph.add_road(Road(parent, sibling, quality=ROAD, charge=NEUTRAL))

  // Step 4: add to graph
  graph.add(sibling)
  graph.add(parent)

  // Step 5: resolve tension
  tension.resolution = BRANCHED
  original.tensions.remove(tension)
  working_memory.resolve_tension(tension)

  // Step 6: fire FLOW signal — resolution feels satisfying
  fire(FLOW, intensity=0.6)

  // Step 7: check if parent can trigger further abstraction
  RECURSIVE_CHECK(parent)

  return Branch(original, sibling, parent, tension)
```

---

## Part 5 — Abstraction Applied

### 5.1 Using Abstractions for Transfer

The entire point. Applying an abstraction to a situation never before seen.

```
APPLY_ABSTRACTION(structure, new_situation):

  // Step 1: find matching relational structure
  candidate_structures = reasoning_engine.query_structures(new_situation)

  best_match = max(candidate_structures,
    key = structural_similarity(structure, new_situation))

  if structural_similarity(best_match, new_situation) < APPLY_THRESHOLD:
    return NULL  // no abstraction fits — flag as genuinely new

  // Step 2: map abstract roles to new situation's elements
  role_mapping = map_roles(best_match.components, new_situation)
  // e.g. "combustion" structure:
  //   [fuel] → new material X
  //   [oxygen] → available oxygen in environment
  //   [heat] → ignition source present

  // Step 3: generate prediction
  prediction = apply_structure(best_match, role_mapping)
  // e.g. "material X should burn if ignition source is applied"

  // Step 4: add to Hypothesis Pool as testable prediction
  hypothesis = Hypothesis(
    claim              = prediction,
    source             = 'abstraction_transfer',
    confidence         = best_match.confidence × structural_similarity,
    falsification_cond = derive_test(prediction),
    test_plan          = build_test(prediction, new_situation)
  )

  hypothesis_pool.add(hypothesis)

  return hypothesis
```

---

### 5.2 Grounding Check — Traveling Downward

When an abstraction is used in reasoning,
the system can always travel downward to verify it
against the specific instances that generated it.

```
GROUND_CHECK(abstraction, claim):

  // travel down to source nodes
  source_nodes = abstraction.source_nodes

  supporting  = 0
  contradicting = 0

  for source in source_nodes:
    if supports(source, claim):
      supporting++
    elif contradicts(source, claim):
      contradicting++

  confidence = supporting / (supporting + contradicting)

  if confidence < GROUNDING_THRESHOLD:
    // abstraction is being used beyond its evidential base
    fire(FRICTION, intensity=0.4)
    flag_overextension(abstraction, claim)
    // hypothesis gets lower confidence rating

  return confidence
```

---

## Part 6 — Full Pipeline

```
ABSTRACTION_ENGINE_RUN(new_node, graph, working_memory):

  // 1. Check trigger
  should_abstract, score = SHOULD_ABSTRACT(new_node, graph, working_memory)

  // 2. Check contradiction against existing abstractions
  existing_abstractions = graph.find_covering_abstractions(new_node)
  tension = CHECK_CONTRADICTION(new_node, existing_abstractions)

  if tension:
    HOLD_TENSION(tension)

  // 3. Run abstraction pipeline if triggered
  if should_abstract:

    candidates = graph.find_similar(new_node)

    // Level 1
    pattern = LEVEL_1_PATTERN_RECOGNITION(new_node, candidates, score)

    // Level 2
    concept = LEVEL_2_CONCEPT_FORMATION(pattern)

    // Level 3
    structure = LEVEL_3_RELATIONAL_EXTRACTION(concept, pattern)

    // Recursive upward check
    RECURSIVE_CHECK(concept)
    if structure: RECURSIVE_CHECK(structure)

  // 4. Periodically re-evaluate held tensions
  for tension in graph.all_active_tensions():
    EVALUATE_TENSION(tension)
```

---

## Part 7 — Summary

```
TRIGGER:
  score = (similarity_weight × avg_similarity)
        + (repetition_weight × normalized_count)
  weights shift with emotional state:
    GAP      → eager to abstract (similarity weighted higher)
    FRICTION → cautious (repetition weighted higher)
    OVERLOAD → abstraction suppressed entirely

THREE LEVELS:
  Level 1 → Pattern Recognition   (find shared properties)
  Level 2 → Concept Formation     (create standalone concept node)
  Level 3 → Relational Structure  (extract causal skeleton)
  Recursive → abstractions abstract abstractions

NODE MODEL:
  specific nodes never deleted
  abstract nodes form above them
  bidirectional roads connect up and down
  system can always travel down to ground-check a claim

CONTRADICTIONS:
  default → HOLD THE TENSION
  accumulate evidence on both sides
  imagination engine notified immediately
  when evidence ratio crosses threshold → BRANCH

BRANCHING:
  original abstraction survives intact
  sibling abstraction forms covering contradicting cases
  parent abstraction forms above both
  graph grows upward and sideways simultaneously

TRANSFER:
  Level 3 structures register with Reasoning Engine
  applied to new situations via role mapping
  produces testable hypotheses, not certain claims
  always ground-checkable against source nodes
```

---

*Nous Abstraction Engine — Module 02*
*Status: Design complete. Ready for Module 03 — Self Model.*
