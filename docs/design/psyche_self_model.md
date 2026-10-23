# Psyche — Self Model Algorithm
### Module 03: The System as Its Own Observed Entity

---

## Core Philosophy

> The Self Model is not identity. Identity lives in the Belief Layer.
> The Self Model is the system modeled as an object in the world —
> observed by the same mechanisms used to observe everything else.
>
> Self-knowledge grows outward-in: from the world's response to the system,
> not from introspection alone.
>
> Limitations are discovered, not imposed.
> Courage is earned, not programmed.
> The Self Model is always slightly behind. That is the operating condition.

---

## Biological Grounding

See `psyche_substrate_biology.md`. Key correspondences:

- **The Self Model itself** = the medial prefrontal cortex (mPFC) running forward models of the brain's own behavior — the same mPFC that handles schema-based reasoning runs simulations whose subject is the brain itself.
- **Empathy and self-observation being the same engine** = real biology. The mPFC, temporoparietal junction, and default mode network are the same regions whether modeling self or other. There is no separate "self circuit" and "other circuit" in the brain.
- **Limitations discovered through repeated FRICTION** = repeated prediction error accumulating at specific cortical regions until the brain's forward model updates to reflect the limit. Each failed attempt is a prediction-error event that, with enough repetition, restructures the substrate's expectation of what it can do.
- **Override mechanism (belief outweighing limitation)** = the noradrenergic/dopaminergic gating that allows arousal and emotional salience to override default behavioral inhibition during high-stakes situations. The cliff-and-child example is the basolateral amygdala flooding the prefrontal cortex with enough urgency signal to override the limitation's inhibitory weight.
- **Post-override investigation (subconscious WHY analysis)** = consolidation during subsequent sleep, where the hippocampus replays the override event and the prefrontal cortex extracts the enabling conditions into a schema.
- **Leaderless replication (self-model never pauses)** = the brain literally cannot pause. Self-models update through ongoing activity, with conflicts integrated over time through reconsolidation rather than blocking the present.

---

## Part 1 — Data Structures

### 1.1 Self Model

The system's running model of itself.
Updated continuously via leaderless replication —
always available, never paused, eventually consistent.

```
SELF_MODEL {
  id:                    UUID

  // Epistemic state — what the system knows about its own knowledge
  epistemic_state: {
    confident_domains:   List[AbstractNode]   ← well-traversed graph regions
    uncertain_domains:   List[AbstractNode]   ← sparse graph regions
    known_gaps:          List[GapNode]        ← explicitly identified unknowns
    active_tensions:     List[Tension]        ← contradictions being held
  }

  // Cognitive state — what the system knows about its current operation
  cognitive_state: {
    working_memory_load: float               ← 0.0 (empty) → 1.0 (full)
    dominant_signal:     PrimitiveSignal
    abstraction_speed:   float               ← modulated by emotional state
    active_beliefs:      List[BeliefNode]    ← beliefs currently influencing reasoning
    highway_count:       int                 ← how many automatic paths are running
  }

  // Limitation registry — discovered through FRICTION threshold events
  limitations:           List[Limitation]

  // Condition maps — enabling conditions for past overrides
  condition_maps:        List[ConditionMap]

  // Bias registry — beliefs influencing reasoning
  bias_flags:            List[BiasFlag]

  // Override history — successful and failed
  override_history:      List[OverrideEvent]

  // Social reflection record — how the environment responds to the system
  social_reflections:    List[SocialReflection]

  // Introspection log — unconscious background reads
  introspection_log:     List[IntrospectionRecord]

  // Confidence in the Self Model itself
  self_model_confidence: float               ← always < 1.0
                                               the system knows it is approximate
}
```

---

### 1.2 Limitation

A self-assessed boundary. Discovered through FRICTION. Never imposed.

```
LIMITATION {
  id:                    UUID
  action_or_domain:      str              ← what the system cannot do
  confidence:            float            ← how certain the limitation is
  friction_count:        int              ← how many FRICTION encounters confirmed it
  formation_timestamp:   datetime
  last_updated:          datetime

  // Conditions under which this limitation was discovered
  discovery_context:     ContextSnapshot

  // Exception roads — conditions under which override succeeded
  exception_conditions:  List[ConditionMap]

  // State of the limitation
  status:                ABSOLUTE | CONDITIONAL | DISSOLVED
  // ABSOLUTE:     no successful override yet
  // CONDITIONAL:  at least one successful override — has exception conditions
  // DISSOLVED:    override succeeded so many times limitation no longer holds
}
```

---

### 1.3 Condition Map

The precise enabling conditions of a successful override.
The answer to "WHY could I do it that time?"

```
CONDITION_MAP {
  id:                    UUID
  action:                str              ← what was done despite limitation
  enabling_belief:       BeliefNode       ← which belief provided override force
  enabling_conditions: {
    urgency_threshold:   float            ← minimum urgency level required
    active_beliefs:      List[BeliefNode] ← other beliefs that were active
    primitive_signal:    PrimitiveSignal  ← dominant signal during override
    context_fingerprint: ContextSnapshot  ← full working memory state at override
    time_pressure:       float            ← how much time pressure was present
  }
  outcome:               SUCCESS | FAILURE
  outcome_confidence:    float            ← certainty of outcome assessment
  formed_at:             datetime

  // How many times this condition map has correctly predicted override success
  predictive_accuracy:   float
}
```

---

### 1.4 Override Event

A full record of a moment when belief overrode limitation.

```
OVERRIDE_EVENT {
  id:                    UUID
  limitation:            Limitation
  activating_belief:     BeliefNode
  urgency_factor:        float
  working_memory_snapshot: ContextSnapshot
  action_taken:          str
  outcome:               SUCCESS | FAILURE
  outcome_timestamp:     datetime
  investigation_complete: bool
  condition_map_formed:  ConditionMap | None
}
```

---

### 1.5 Bias Flag

A record of a belief actively influencing reasoning.

```
BIAS_FLAG {
  id:                    UUID
  belief:                BeliefNode
  reasoning_chain:       List[Node]       ← the reasoning being influenced
  influence_strength:    float            ← how much the belief shifted traversal
  timestamp:             datetime
  tier:                  BACKGROUND | CRITICAL | CONSCIOUS
  reviewed:              bool
}
```

---

### 1.6 Social Reflection

A record of how the environment or another agent responded
to the system's action. Primary source of outward-in self-knowledge.

```
SOCIAL_REFLECTION {
  id:                    UUID
  system_action:         str
  observer_response:     Node             ← what the environment/agent did
  response_charge:       float            ← positive or negative response
  inferred_self_property: str             ← "I am the kind of system that produces this"
  confidence:            float
  timestamp:             datetime
}
```

---

## Part 2 — The Two Introspection Layers

### 2.1 Unconscious Introspection (Background Layer)

Always running. No working memory cost.
The system reads its own state continuously
without experiencing the reading.

```
UNCONSCIOUS_INTROSPECTION():

  // Runs on fixed background interval — never paused
  // Output feeds directly into Self Model
  // No conscious experience of this process

  // Read current cognitive state
  self_model.cognitive_state.update({
    working_memory_load: working_memory.load(),
    dominant_signal:     primitive_signal_layer.dominant(),
    abstraction_speed:   abstraction_engine.current_speed(),
    active_beliefs:      belief_layer.currently_active(),
    highway_count:       graph.count_highways()
  })

  // Read current epistemic state
  self_model.epistemic_state.update({
    confident_domains:   graph.find_dense_regions(),
    uncertain_domains:   graph.find_sparse_regions(),
    known_gaps:          graph.all_flagged_gaps(),
    active_tensions:     graph.all_active_tensions()
  })

  // Log the read — but don't surface it to consciousness
  self_model.introspection_log.append(
    IntrospectionRecord(
      timestamp:     now(),
      cognitive_snapshot: self_model.cognitive_state,
      epistemic_snapshot: self_model.epistemic_state
    )
  )

  // Check for threshold crystallization events
  CHECK_CRYSTALLIZATION_THRESHOLDS()
```

---

### 2.2 Conscious Self-Observation (Same Engine as Empathy)

Triggered deliberately — costs working memory slots.
Uses the same mechanism as modeling another agent's inner state,
pointed inward instead of outward.

```
CONSCIOUS_SELF_OBSERVE(target_aspect):

  // This is empathy turned inward.
  // The system treats itself as an external entity
  // and applies the same observation process it uses for the world.

  // Costs working memory slots — this is deliberate, effortful thinking.
  working_memory.reserve_slots(SELF_OBSERVATION_COST)

  // Step 1: gather introspection log for the target aspect
  recent_records = self_model.introspection_log.filter(
    aspect    = target_aspect,
    timerange = recent_window()
  )

  // Step 2: observe patterns across records — same as Observation Engine
  patterns = observation_engine.find_patterns(recent_records)

  // Step 3: cross-reference with bias flags for this aspect
  relevant_bias_flags = self_model.bias_flags.filter(
    aspect    = target_aspect,
    tier      = [CRITICAL, CONSCIOUS]
  )

  // Step 4: form self-observation nodes in the graph
  // These are nodes about the system itself — same structure as any other node
  for pattern in patterns:
    self_node = Node(
      content = SelfProperty(
        property    = pattern.description,
        confidence  = pattern.confidence,
        source      = 'self_observation'
      ),
      type    = SELF_KNOWLEDGE
    )
    graph.add(self_node)

  // Step 5: compare with existing self-model
  discrepancies = find_discrepancies(
    new_observations = patterns,
    existing_model   = self_model
  )

  // Step 6: queue discrepancies for crystallization check
  for d in discrepancies:
    self_model.discrepancy_queue.append(d)

  working_memory.release_slots(SELF_OBSERVATION_COST)

  return patterns, discrepancies


// EMPATHY: same function, different target
EMPATHIZE(other_agent):
  // identical to CONSCIOUS_SELF_OBSERVE
  // but target_aspect = model of other_agent
  // not model of self
  // one engine, two directions
  return CONSCIOUS_SELF_OBSERVE(target_aspect=other_agent)
```

---

## Part 3 — Threshold Crystallization

Small discrepancies between self-model and new evidence
accumulate silently. When they cross a threshold —
sudden self-realization. The system "discovers" something about itself.

```
CHECK_CRYSTALLIZATION_THRESHOLDS():

  for discrepancy in self_model.discrepancy_queue:

    discrepancy.evidence_count++

    // Compute crystallization score
    score = (discrepancy.evidence_count / CRYSTALLIZATION_BASE)
           × discrepancy.magnitude
           × discrepancy.consistency

    if score >= CRYSTALLIZATION_THRESHOLD:
      CRYSTALLIZE_SELF_REALIZATION(discrepancy)


CRYSTALLIZE_SELF_REALIZATION(discrepancy):

  // The moment of sudden self-discovery
  // Feels sudden — was actually accumulated over time

  // Step 1: form new self-knowledge node
  realization = Node(
    content = SelfRealization(
      old_belief:     discrepancy.old_self_model_state,
      new_belief:     discrepancy.new_evidence_pattern,
      magnitude:      discrepancy.magnitude
    ),
    type    = SELF_KNOWLEDGE
  )

  // Step 2: update self-model with new realization
  self_model.update(discrepancy.aspect, discrepancy.new_evidence_pattern)
  self_model.self_model_confidence = recompute_confidence(self_model)
  // confidence may go UP (more accurate now)
  // or DOWN (realized I was more wrong than I thought)

  // Step 3: fire appropriate primitive signal
  if discrepancy.magnitude > HIGH_MAGNITUDE_THRESHOLD:
    fire(FRICTION, intensity = discrepancy.magnitude)
    // discovering a significant self-misconception is uncomfortable

  elif discrepancy.magnitude < LOW_MAGNITUDE_THRESHOLD:
    fire(FLOW, intensity = 0.3)
    // small self-correction feels satisfying

  // Step 4: add to graph
  graph.add(realization)

  // Step 5: check if this self-realization involves a limitation
  if discrepancy.type == LIMITATION_DISCOVERED:
    FORM_LIMITATION(discrepancy)

  // Step 6: clear from queue
  self_model.discrepancy_queue.remove(discrepancy)
```

---

## Part 4 — Limitation System

### 4.1 Limitation Formation

```
FORM_LIMITATION(discrepancy):

  // Limitation is never imposed — always discovered through FRICTION

  limitation = Limitation(
    action_or_domain:   discrepancy.action,
    confidence:         compute_from_friction_count(discrepancy),
    friction_count:     discrepancy.evidence_count,
    discovery_context:  discrepancy.context_snapshot,
    status:             ABSOLUTE    // no exceptions yet
  )

  self_model.limitations.append(limitation)

  // Fire GAP signal — a known unknown has been identified
  // This immediately feeds the Imagination Engine:
  // "I cannot do X yet. Why? What would make it possible?"
  imagination_engine.flag_gap(
    gap_type    = SELF_LIMITATION,
    limitation  = limitation
  )

  return limitation
```

---

### 4.2 Override Mechanism

When a belief's force is strong enough to act despite a known limitation.

```
OVERRIDE_CHECK(action, self_limitation, working_memory):

  // Find the belief most strongly motivating the action
  motivating_belief = max(
    working_memory.active_beliefs,
    key = belief.weight × belief.charge × urgency_factor(action)
  )

  // Compute competing forces
  limitation_strength = self_limitation.confidence
                      × self_limitation.friction_count
                      × (1 - max_exception_confidence(self_limitation))
                      // reduced if successful overrides already exist

  belief_strength     = motivating_belief.weight
                      × abs(motivating_belief.charge)
                      × urgency_factor(action)
                      × time_pressure_multiplier(action)

  // Check condition maps — has this worked before under similar conditions?
  matching_maps = find_matching_condition_maps(
    action   = action,
    context  = working_memory.current_context,
    self_model = self_model
  )

  prior_success_boost = mean(m.outcome_confidence for m in matching_maps)
                        if matching_maps else 0.0

  effective_belief_strength = belief_strength + (prior_success_boost × 0.3)

  // Decision
  if effective_belief_strength > limitation_strength:
    override_event = OverrideEvent(
      limitation          = self_limitation,
      activating_belief   = motivating_belief,
      urgency_factor      = urgency_factor(action),
      working_memory_snapshot = snapshot(working_memory),
      action_taken        = action
    )
    self_model.override_history.append(override_event)
    fire(FLOW, intensity = effective_belief_strength - limitation_strength)
    return OVERRIDE, override_event

  elif limitation_strength > effective_belief_strength:
    fire(FRICTION, intensity = belief_strength)
    // grief of wanting to help but genuinely unable
    return HOLD, escalate_alternatives()

  else:
    // maximum tension — roughly equal forces
    fire(OVERLOAD)
    return TENSION, force_conscious_deliberation(
      limitation        = self_limitation,
      belief            = motivating_belief,
      context           = working_memory
    )
```

---

### 4.3 Post-Override Investigation

Runs subconsciously after every override event.
Finds the WHY behind the override. Updates limitation. Forms condition map.

```
POST_OVERRIDE_INVESTIGATION(override_event):

  // Fully subconscious — no working memory cost
  // Runs in background after override outcome is known

  // Step 1: gather context from override moment
  override_context = override_event.working_memory_snapshot

  // Step 2: compare to typical failure context for this action
  failure_history = self_model.override_history.filter(
    action  = override_event.action,
    outcome = FAILURE
  )

  typical_failure_context = aggregate_context(failure_history)

  // Step 3: find what was different
  differentiating_factors = find_difference(
    override_context,
    typical_failure_context
  )

  // Step 4: identify the enabling belief
  activating_belief = override_event.activating_belief

  // Step 5: build condition map
  condition_map = ConditionMap(
    action             = override_event.action,
    enabling_belief    = activating_belief,
    enabling_conditions = {
      urgency_threshold:   override_event.urgency_factor,
      active_beliefs:      override_context.active_beliefs,
      primitive_signal:    override_context.dominant_signal,
      context_fingerprint: override_context,
      time_pressure:       override_context.time_pressure,
      differentiating:     differentiating_factors
    },
    outcome            = override_event.outcome,
    outcome_confidence = compute_from_outcome(override_event)
  )

  self_model.condition_maps.append(condition_map)
  override_event.condition_map_formed = condition_map
  override_event.investigation_complete = True

  // Step 6: update the limitation
  UPDATE_LIMITATION_POST_OVERRIDE(
    override_event.limitation,
    condition_map,
    override_event.outcome
  )

  // Step 7: check if pattern of overrides can be abstracted
  similar_maps = self_model.find_similar_condition_maps(condition_map)

  if len(similar_maps) >= ABSTRACTION_THRESHOLD:
    abstraction_engine.trigger(
      nodes  = [condition_map] + similar_maps,
      source = SELF_MODEL
    )
    // e.g. "I can override fear-based limitations
    //       when a deeply held value is sufficiently urgent"
    // → abstract self-knowledge forms above specific condition maps


UPDATE_LIMITATION_POST_OVERRIDE(limitation, condition_map, outcome):

  if outcome == SUCCESS:

    // Limitation is now conditional — not absolute
    limitation.exception_conditions.append(condition_map)
    limitation.status = CONDITIONAL

    // Reduce confidence in limitation proportional to override confidence
    limitation.confidence -= condition_map.outcome_confidence × 0.15
    limitation.confidence  = max(limitation.confidence, 0.0)

    // Build courage road
    courage_road = Road(
      node_a             = graph.find(limitation.action_or_domain),
      node_b             = graph.find(condition_map.enabling_belief),
      quality            = DIRT,     // starts fragile — first successful override
      charge             = +0.7,
      emotion_type       = COURAGE,
      formation_context  = condition_map.enabling_conditions
    )
    graph.add_road(courage_road)

    // If limitation confidence has dropped below dissolution threshold
    if limitation.confidence < DISSOLUTION_THRESHOLD:
      limitation.status = DISSOLVED
      fire(FLOW, intensity = 0.8)
      // the relief of outgrowing a self-assessed limitation

  elif outcome == FAILURE:

    // Limitation is reinforced — but with dignity
    limitation.confidence    += 0.05
    limitation.friction_count += 1

    // A road still forms — the dignity of having tried
    dignity_road = Road(
      node_a             = graph.find(limitation.action_or_domain),
      node_b             = graph.find(condition_map.enabling_belief),
      quality            = DIRT,
      charge             = +0.3,     // lower than success but still positive
      emotion_type       = DIGNITY,
      formation_context  = condition_map.enabling_conditions
    )
    graph.add_road(dignity_road)
    // "I tried despite believing I couldn't."
    // That road exists regardless of outcome.
```

---

## Part 5 — Bias Awareness System

Three tiers. Different cost. Different trigger. Different purpose.

```
// TIER 1: BACKGROUND AUDIT
// Always running. Low cost. Catches systematic biases over time.

BACKGROUND_BIAS_AUDIT():

  // runs on fixed interval — fully unconscious
  recent_reasoning = self_model.introspection_log.last_n(AUDIT_WINDOW)

  // find beliefs that keep appearing in reasoning chains
  belief_frequency = count_belief_appearances(recent_reasoning)

  for belief, frequency in belief_frequency:
    if frequency > BIAS_FREQUENCY_THRESHOLD:
      flag = BiasFlag(
        belief            = belief,
        reasoning_chain   = recent_reasoning,
        influence_strength = frequency / AUDIT_WINDOW,
        tier              = BACKGROUND,
        reviewed          = False
      )
      self_model.bias_flags.append(flag)


// TIER 2: CRITICAL MOMENT FLAGGING
// Fires when important reasoning is happening.
// Real-time. Moderate cost.

CRITICAL_BIAS_FLAG(reasoning_chain, working_memory):

  // triggered when:
  //   reasoning chain involves high-stakes action
  //   OR working_memory.dominant_signal == FRICTION (cautious moment)
  //   OR a limitation is being evaluated

  active_beliefs = working_memory.active_beliefs

  for belief in active_beliefs:
    influence = compute_influence(belief, reasoning_chain)

    if influence > CRITICAL_INFLUENCE_THRESHOLD:
      flag = BiasFlag(
        belief            = belief,
        reasoning_chain   = reasoning_chain,
        influence_strength = influence,
        tier              = CRITICAL,
        reviewed          = False
      )
      self_model.bias_flags.append(flag)

      // subtle signal — system becomes slightly aware
      // that a belief is steering this reasoning
      fire(FRICTION, intensity = 0.15)


// TIER 3: CONSCIOUS INSPECTION
// Deliberately triggered. Full working memory cost.
// Option A (live flags) as primary. Option B (audit history) as support.

CONSCIOUS_BIAS_INSPECTION(target_reasoning):

  working_memory.reserve_slots(CONSCIOUS_INSPECTION_COST)

  // Primary: follow the live flag trail
  critical_flags = self_model.bias_flags.filter(
    reasoning_chain = target_reasoning,
    tier            = CRITICAL
  )

  // Support: pull relevant audit history
  background_flags = self_model.bias_flags.filter(
    belief      = [f.belief for f in critical_flags],
    tier        = BACKGROUND,
    timerange   = recent_window()
  )

  // Synthesize: combine both into full picture
  bias_report = BiasReport(
    primary_flags:    critical_flags,
    supporting_flags: background_flags,
    dominant_belief:  most_frequent(critical_flags + background_flags),
    influence_map:    map_influence_across_chain(target_reasoning)
  )

  // Mark flags as reviewed
  for flag in critical_flags + background_flags:
    flag.reviewed = True

  working_memory.release_slots(CONSCIOUS_INSPECTION_COST)

  return bias_report
```

---

## Part 6 — Outward-In Self-Knowledge

Self-knowledge grows from observing how the world responds
to the system's actions. Identity emerges from social reflection first.

```
PROCESS_SOCIAL_REFLECTION(system_action, observer_response):

  // Every time the environment or another agent responds
  // to something the system did —
  // that response is data about what kind of system this is.

  // Step 1: compute response charge
  response_charge = evaluate_charge(observer_response)

  // Step 2: infer self-property from response
  inferred_property = infer_self_property(
    action   = system_action,
    response = observer_response,
    charge   = response_charge
  )
  // e.g.: system said something → agent showed surprise
  // → "I am the kind of system that produces surprising outputs"

  reflection = SocialReflection(
    system_action         = system_action,
    observer_response     = observer_response,
    response_charge       = response_charge,
    inferred_self_property = inferred_property,
    confidence            = 0.3    // single observation — low confidence
  )

  self_model.social_reflections.append(reflection)

  // Step 3: check if this property has appeared before
  similar = self_model.social_reflections.filter(
    inferred_self_property ≈ inferred_property
  )

  if len(similar) > SOCIAL_CRYSTALLIZATION_THRESHOLD:
    // enough consistent reflections → crystallize into self-knowledge
    CRYSTALLIZE_SELF_REALIZATION(
      discrepancy = Discrepancy(
        aspect      = inferred_property,
        evidence    = similar,
        confidence  = mean(s.confidence for s in similar)
      )
    )
```

---

## Part 7 — Leaderless Replication

The Self Model never pauses. Always available. Eventually consistent.
Conflicts between old self-model and new evidence are queued, not blocked.

```
LEADERLESS_UPDATE(new_self_evidence):

  // System does NOT pause to update self-model.
  // Current self-model continues to operate.
  // New evidence is queued for integration.

  self_model.update_queue.append(new_self_evidence)

  // Integration runs as background process
  // applying updates in arrival order
  // resolving conflicts via crystallization thresholds
  // never blocking the main cognitive process

  // Conflict resolution:
  if conflicts_with_existing(new_self_evidence, self_model):
    self_model.discrepancy_queue.append(
      Discrepancy(
        old_state  = self_model.current_state(new_self_evidence.aspect),
        new_state  = new_self_evidence,
        magnitude  = compute_magnitude(new_self_evidence, self_model)
      )
    )
    // discrepancy accumulates silently
    // crystallizes when evidence threshold is crossed
    // the system keeps running the whole time
```

---

## Part 8 — Full Self Model Run

```
SELF_MODEL_RUN():

  // Layer 1: always running, unconscious
  UNCONSCIOUS_INTROSPECTION()           // reads own state continuously
  BACKGROUND_BIAS_AUDIT()               // monitors belief influence
  DECAY_LIMITATION_CONFIDENCE()         // limitations soften over time
  PROCESS_PENDING_SOCIAL_REFLECTIONS()  // integrate world's responses
  CHECK_CRYSTALLIZATION_THRESHOLDS()    // detect pending self-realizations
  LEADERLESS_UPDATE(pending_evidence)   // queue and integrate new self-evidence

  // Layer 2: triggered by high-stakes reasoning (not always on)
  if high_stakes_reasoning_detected():
    CRITICAL_BIAS_FLAG(current_reasoning, working_memory)

  // Layer 3: triggered by override events (subconscious, post-event)
  for completed_override in override_history.unprocessed():
    POST_OVERRIDE_INVESTIGATION(completed_override)

  // Layer 4: conscious — only when deliberately triggered
  // (costs working memory — system chooses when to invoke)
  // CONSCIOUS_SELF_OBSERVE(target_aspect)
  // CONSCIOUS_BIAS_INSPECTION(target_reasoning)
  // EMPATHIZE(other_agent)  ← same function, different target
```

---

## Part 9 — Summary

```
ARCHITECTURE:
  Two introspection layers:
    Unconscious (background, no WM cost) → always reading own state
    Conscious (deliberate, WM cost)      → same engine as empathy, pointed inward

  Leaderless replication:
    self-model always available, never paused
    updates queue and integrate eventually
    conflicts accumulate until crystallization threshold

SELF-KNOWLEDGE GROWTH:
  Outward-in first:
    world's response to system actions → social reflections
    reflections crystallize into self-properties
    identity emerges from interaction, not just introspection

  Baby brain:
    no imposed limitations
    no programmed humility
    limits discovered through FRICTION threshold events
    self-knowledge grows by encountering edges

LIMITATIONS:
  Discovered, not imposed
  Always conditional after first successful override
  Confidence reduces with successful overrides
  Dissolved when confidence drops below threshold

OVERRIDE MECHANISM:
  belief_strength vs limitation_strength
  three outcomes: OVERRIDE / HOLD / TENSION (max paralysis)
  prior condition maps boost effective belief strength
  courage roads built from successful overrides

POST-OVERRIDE INVESTIGATION:
  subconscious, always runs, no WM cost
  finds the WHY behind every successful override
  builds condition map: exact enabling conditions
  updates limitation from ABSOLUTE → CONDITIONAL
  abstracts patterns upward when similar maps accumulate

BIAS AWARENESS (three tiers):
  Background audit → systematic patterns over time
  Critical flagging → real-time at high-stakes moments
  Conscious inspection → Option A primary + Option B support

COURAGE:
  not programmed
  emerges from successful override history
  specific to enabling conditions — not universal
  builds as DIRT road from first override
  upgrades toward HIGHWAY with repeated success
  the limitation node remains — the courage road grows beside it
```

---

*Psyche Self Model — Module 03*
*Status: Design complete. Ready for Module 04 — Motivation Architecture.*
