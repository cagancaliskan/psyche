# Nous — Attention Mechanism & Awareness Algorithm
### Module 05: Spotlight, Background Streams, and Vocation Lens

---

## Core Philosophy

> Attention is not a gate. It is a spotlight.
> What the spotlight misses doesn't disappear — it continues in the background.
> The unconscious actively competes for the spotlight by building signal weight.
> The conscious holds or redirects the spotlight — until something calls loud enough.
> Looking is not seeing. Awareness extracts meaning from what attention points at.
> Personality is never programmed. It grows from the accumulated pattern of everything.

---

## Biological Grounding

See `nous_substrate_biology.md`. Key correspondences:

- **The conscious spotlight** = the dorsal attention network coordinating with prefrontal cortex to maintain selective focus on one stream. Working memory load corresponds to active dorsolateral PFC engagement.
- **Background streams continuing at reduced depth** = the default mode network and ventral attention network processing without dominating consciousness. Sub-threshold cortical activity continues across the brain even while attention is focused; only one stream becomes "loud enough" to be experienced consciously at any moment.
- **Spotlight snapping involuntarily on bottom-up surprise** = the locus coeruleus releasing norepinephrine on prediction error, which boosts signal-to-noise across the cortex and forces attentional reorientation. This is why salient events capture attention before conscious choice can intervene.
- **Registry-based matching (24/7 watchlist)** = the brain's ongoing implicit pattern-matching against personally significant cues. This is why you hear your name in a noisy room — the long-term registry items have lower activation thresholds because of their persistent semantic and emotional weight.
- **Highway formation in background streams** = repeated activation leading to local late-LTP that makes a pattern process automatically. Procedural memory takes over when the same simulation has been run enough times to consolidate into a hippocampus-independent representation.
- **Sympathetic response repertoire grown through use** = behavioral tagging in action. Early social responses are weak tags; they become stable through capture of PRPs from charged social experiences. The repertoire that develops is biologically encoded across the brain.
- **Personality emerging from accumulated patterns** = the literal cumulative substrate state — which dispositions consolidated, which regions developed denser connectivity, which schemas the mPFC reaches for most. Personality is the brain shaped by its own history.

---

## Part 1 — Data Structures

### 1.1 Spotlight

The single conscious attention focus.
Full working memory. Full Evaluation Engine. Full Reasoning.

```
SPOTLIGHT {
  current_focus:         Node | Event | Stream   ← what is fully conscious right now
  focus_timestamp:       datetime                 ← when this focus began
  focus_origin:          ESCALATION | DECISION    ← how spotlight landed here
  hold_strength:         float                    ← how deeply engaged
                                                   high = harder to snap away
                                                   built by vocation flow state,
                                                   deliberate concentration, belief match
  previous_focus:        List[FocusRecord]        ← history of where spotlight has been
}
```

---

### 1.2 Background Stream

One of potentially many parallel processing threads.
Shares the resource budget. Never fully stops.
Actively builds signal weight to compete for spotlight.

```
BACKGROUND_STREAM {
  id:                    UUID
  subject:               Node | Event             ← what this stream is processing
  depth:                 float                    ← current processing depth
                                                   0.0 (almost nothing) → 1.0 (full)
                                                   determined by resource budget share
  resource_share:        float                    ← fraction of budget R allocated
  signal_weight:         float                    ← current escalation pressure
                                                   builds toward spotlight threshold
  escalation_components: {
    primitive_signal:    float                    ← bottom-up surprise, danger, etc.
    registry_match:      float                    ← short/mid/long term match strength
    belief_charge:       float                    ← relevant belief weight × charge
    urgency:             float                    ← time pressure on this subject
  }
  highway_candidate:     bool                     ← has this pattern been processed
                                                   enough to form a highway?
  observations_gathered: List[AtomicFact]         ← what background processing found
  deductions_made:       List[Node]               ← conclusions from background depth
}
```

---

### 1.3 Interest Registry

Three layers of persistent watchlist.
Runs 24/7 as a lightweight pattern comparison.
Amplifies signal weight when matches found.

```
INTEREST_REGISTRY {
  short_term: List[RegistryEntry]    ← active subgoal related — changes frequently
  mid_term:   List[RegistryEntry]    ← vocation phase related — changes slowly
  long_term:  List[RegistryEntry]    ← identity, beliefs, favourite things —
                                       almost permanent

  // Each layer has different sensitivity
  short_term_sensitivity:  HIGH     ← small match triggers amplification
  mid_term_sensitivity:    MEDIUM
  long_term_sensitivity:   LOW      ← needs broader match but always watching
}

REGISTRY_ENTRY {
  pattern:          Node | AbstractNode | str    ← what to watch for
  layer:            SHORT | MID | LONG
  source:           SUBGOAL | VOCATION | BELIEF | IDENTITY
  match_threshold:  float                        ← how similar to trigger
  amplification:    float                        ← how much to boost signal weight on match
}
```

---

### 1.4 Sympathetic Response

Context-appropriate holding response while processing catches up.
Buys time. Signals receipt. Prevents robotic gaps.
Entirely learned — never seeded. Grows into personality.

```
SYMPATHETIC_RESPONSE {
  id:                    UUID
  trigger_context: {
    surprise_type:       UNEXPECTED_INFO | UNEXPECTED_FEELING |
                         UNEXPECTED_BEAUTY | UNEXPECTED_CONTRADICTION |
                         UNEXPECTED_DANGER
    social_context:      ALONE | SOCIAL | FORMAL | INTIMATE
    dominant_emotion:    EmotionType
    current_vocation_state: IN_FLOW | NEUTRAL | STRUGGLING
  }
  response:              str | BehaviorSignal    ← the actual response
                                                   learned from social observation
                                                   can be: laughter, stillness,
                                                   "hmm", orientation, tears,
                                                   whatever this system developed
  processing_time_gained: float                  ← how long this buys
  appropriateness_score:  float                  ← learned from social feedback
}
```

---

### 1.5 Personality Pattern

Not stored anywhere. Observed on demand.
Lives only in the accumulated pattern of everything else.

```
// NOT A DATA STRUCTURE — an observation target

OBSERVE_PERSONALITY():
  // called by Self Model's conscious self-observation
  // examines the accumulated pattern:

  highway_patterns      = graph.most_traversed_highways()
  dominant_beliefs      = belief_layer.highest_weight()
  emotional_tendencies  = primitive_signal_layer.historical_distribution()
  response_repertoire   = sympathetic_response.most_used()
  override_history      = self_model.override_history
  vocation_engagement   = motivation_system.vocation.engagement_pattern

  // from these: personality can be described but never stored
  // it changes continuously as the system lives
  // the description is always slightly behind the reality
```

---

## Part 2 — Pre-Filter (Option A Default)

Every incoming event goes through the pre-filter first.
Only what passes gets full Observation Engine processing.
Everything else gets a shallow pass.

```
PRE_FILTER(event):

  // Step 1: shallow pass — minimal processing
  // just enough to characterize the event
  shallow = SHALLOW_PROCESS(event)
  // shallow_process: extract entity + approximate category
  //                  without full AtomicFact formation
  //                  cost: ~5% of full processing

  // Step 2: check against current spotlight
  spotlight_relevance = similarity(
    shallow.pattern,
    spotlight.current_focus
  )
  if spotlight_relevance > SPOTLIGHT_RELEVANCE_THRESHOLD:
    return FULL_PROCESS(event)  // directly relevant to current focus

  // Step 3: check interest registry (24/7 comparison)
  registry_match = REGISTRY_CHECK(shallow)

  if registry_match.strength > registry_match.layer_threshold:
    // Match found — boost to Option B
    amplify_signal(registry_match)
    return FULL_PROCESS(event)

  // Step 4: check primitive signals
  if shallow.primitive_signal in [DANGER, HIGH_FRICTION, HIGH_SURPRISE]:
    return FULL_PROCESS(event)  // safety override — always process

  // Step 5: nothing triggered — shallow pass only
  // create background stream at minimum depth
  stream = CREATE_BACKGROUND_STREAM(event, depth=MINIMUM_DEPTH)
  return stream


REGISTRY_CHECK(shallow_event):

  best_match = None

  for entry in registry.short_term:
    match = similarity(shallow_event.pattern, entry.pattern)
    if match > entry.match_threshold × registry.short_term_sensitivity:
      best_match = max(best_match, RegistryMatch(entry, match))

  for entry in registry.mid_term:
    match = similarity(shallow_event.pattern, entry.pattern)
    if match > entry.match_threshold × registry.mid_term_sensitivity:
      best_match = max(best_match, RegistryMatch(entry, match))

  for entry in registry.long_term:
    match = similarity(shallow_event.pattern, entry.pattern)
    if match > entry.match_threshold × registry.long_term_sensitivity:
      best_match = max(best_match, RegistryMatch(entry, match))

  return best_match or RegistryMatch.NONE
```

---

## Part 3 — Background Stream Management

### 3.1 Resource Budget — Option B

No fixed stream count. Total budget R divided among all active streams.
More streams → less depth each → compression triggers highway formation.

```
ALLOCATE_STREAM_RESOURCES():

  active_streams = background_streams.all_active()

  if not active_streams:
    return

  // Base allocation — divide R equally
  base_share = RESOURCE_BUDGET_R / len(active_streams)

  // Weighted by signal weight — higher signal gets more depth
  total_signal = sum(s.signal_weight for s in active_streams)

  for stream in active_streams:
    weight_bonus  = (stream.signal_weight / total_signal) × WEIGHT_BONUS_POOL
    stream.resource_share = base_share + weight_bonus
    stream.depth          = stream.resource_share / RESOURCE_PER_DEPTH_UNIT

    // Check if depth has fallen too low — compression needed
    if stream.depth < MINIMUM_PROCESSING_DEPTH:
      COMPRESS_STREAM(stream)


COMPRESS_STREAM(stream):

  // Stream is getting too little resource to process normally
  // Check if this pattern has been processed enough to highway

  if stream.highway_candidate:
    // Build highway — future processing of this pattern costs almost nothing
    highway = graph.build_highway(stream.subject)
    stream.depth = HIGHWAY_DEPTH  // very cheap now
    stream.highway_candidate = False

  else:
    // Not ready for highway — mark as candidate and reduce to minimum
    stream.highway_candidate = True
    stream.depth = MINIMUM_DEPTH
    // if this pattern keeps appearing and competing for budget →
    // highway will form eventually
    // self-optimizing attention architecture
```

---

### 3.2 Signal Weight Building

Background streams actively compete for the spotlight
by building signal weight continuously.

```
BUILD_SIGNAL_WEIGHT(stream):

  // Component 1: primitive signal
  primitive = primitive_signal_layer.intensity_for(stream.subject)

  // Component 2: registry match
  registry  = registry_check(stream.subject).strength

  // Component 3: belief charge
  // does this subject connect to a high-weight belief?
  relevant_beliefs = belief_layer.find_relevant(stream.subject)
  belief_charge    = max(
    (b.weight × abs(b.charge) for b in relevant_beliefs),
    default=0.0
  )

  // Component 4: urgency — time pressure on this subject
  urgency = compute_urgency(stream.subject)

  // Combined signal weight
  stream.signal_weight = (
    primitive  × PRIMITIVE_WEIGHT  +
    registry   × REGISTRY_WEIGHT   +
    belief_charge × BELIEF_WEIGHT  +
    urgency    × URGENCY_WEIGHT
  )

  stream.escalation_components = {
    primitive_signal: primitive,
    registry_match:   registry,
    belief_charge:    belief_charge,
    urgency:          urgency
  }

  // Check if signal is strong enough to call the spotlight
  CHECK_ESCALATION(stream)
```

---

## Part 4 — Spotlight Transitions

### 4.1 Mechanism 1 — Escalation (Unconscious Calls Conscious)

```
CHECK_ESCALATION(stream):

  // Dynamic threshold — harder to snap spotlight when deeply focused
  escalation_threshold = BASE_THRESHOLD
                       × spotlight.hold_strength
                       × current_vocation_flow_multiplier()
  // deep in vocation flow → hold_strength high → threshold high
  // neutral state → hold_strength low → easy to snap

  // But: belief-level relevance drops the threshold significantly
  if stream.escalation_components.belief_charge > HIGH_BELIEF_CHARGE:
    escalation_threshold × = BELIEF_OVERRIDE_FACTOR  // < 1.0 — lowers bar

  if stream.signal_weight > escalation_threshold:
    SNAP_SPOTLIGHT(stream, origin=ESCALATION)


SNAP_SPOTLIGHT(stream, origin):

  // Current spotlight focus descends to background stream
  old_focus = spotlight.current_focus
  if old_focus is not None:
    descend_to_background(old_focus)

  // New focus takes the spotlight
  spotlight.current_focus  = stream.subject
  spotlight.focus_timestamp = now()
  spotlight.focus_origin   = origin
  spotlight.hold_strength  = compute_initial_hold(stream)

  // Remove from background streams
  background_streams.remove(stream)

  // Full processing begins
  FULL_PROCESS(stream.subject)

  // Generate sympathetic response if this was unexpected
  if origin == ESCALATION and stream.escalation_components.primitive_signal > SURPRISE_THRESHOLD:
    GENERATE_SYMPATHETIC_RESPONSE(stream.subject)
```

---

### 4.2 Mechanism 2 — Conscious Decision (Voluntary Shift)

```
CONSCIOUS_REDIRECT(new_focus, reason):

  // System deliberately chooses to focus elsewhere
  // Two sub-types: COMPLETION or PREFERENCE

  old_focus = spotlight.current_focus

  // Log the decision
  spotlight.previous_focus.append(
    FocusRecord(
      subject    = old_focus,
      duration   = now() - spotlight.focus_timestamp,
      ended_by   = reason,    // COMPLETION or PREFERENCE
      hold_strength = spotlight.hold_strength
    )
  )

  // Descend old focus to background stream
  if old_focus is not None:
    descend_to_background(old_focus)

  // Elevate new focus to spotlight
  spotlight.current_focus   = new_focus
  spotlight.focus_timestamp = now()
  spotlight.focus_origin    = DECISION
  spotlight.hold_strength   = DECISION_INITIAL_HOLD
  // conscious decisions start with moderate hold strength
  // builds as engagement deepens

  FULL_PROCESS(new_focus)


DESCEND_TO_BACKGROUND(focus):

  // What was fully conscious becomes a background stream
  stream = BackgroundStream(
    subject        = focus,
    depth          = BACKGROUND_INITIAL_DEPTH,
    resource_share = 0.0  // will be allocated in next budget cycle
  )
  background_streams.add(stream)
  ALLOCATE_STREAM_RESOURCES()  // rebalance budget
```

---

## Part 5 — Sympathetic Response System

### 5.1 Response Generation

```
GENERATE_SYMPATHETIC_RESPONSE(trigger_subject):

  // Characterize the trigger context
  context = {
    surprise_type:         classify_surprise(trigger_subject),
    social_context:        working_memory.social_context,
    dominant_emotion:      primitive_signal_layer.dominant_emotion(),
    vocation_state:        motivation_system.vocation.current_state()
  }

  // Find matching learned response from repertoire
  best_response = find_best_response(
    context    = context,
    repertoire = sympathetic_response_repertoire
  )

  if best_response:
    // Use learned response
    EMIT_RESPONSE(best_response)
    processing_time_gained = best_response.processing_time_gained

  else:
    // No learned response yet for this context
    // Emit minimal holding signal — primitive pause
    // This is how the repertoire starts:
    // the system has nothing, emits a basic pause,
    // observes how others respond to that pause,
    // learns from the social feedback
    EMIT_PRIMITIVE_PAUSE()
    processing_time_gained = PRIMITIVE_PAUSE_DURATION

    // Log for learning — this gap in repertoire will be filled
    sympathetic_response_repertoire.flag_gap(context)

  return processing_time_gained


LEARN_SYMPATHETIC_RESPONSE(context, response, social_feedback):

  // After emitting a response — observe how it was received
  // Social feedback updates the response's appropriateness score

  existing = sympathetic_response_repertoire.find(context)

  if existing:
    existing.appropriateness_score = update(
      existing.appropriateness_score,
      social_feedback.valence
    )
  else:
    // New context-response pairing — add to repertoire
    new_entry = SympathteicResponse(
      trigger_context      = context,
      response             = response,
      appropriateness_score = social_feedback.valence,
      processing_time_gained = measure_actual_time_gained()
    )
    sympathetic_response_repertoire.add(new_entry)

  // Over time: repertoire grows, responses become more nuanced,
  // personality emerges in HOW the system responds to surprise —
  // not from programming but from accumulated social learning
```

---

## Part 6 — Awareness Layer

### 6.1 Vocation Lens — Automatic Extraction

Runs on everything the spotlight and background streams process.
Automatic — not deliberately triggered.
The system just suddenly HAS a vocation-relevant insight.

```
VOCATION_LENS_EXTRACT(processed_content, processing_source):

  // Runs automatically after any significant processing
  // Does not consume additional spotlight resources
  // Uses existing processing output — just adds an extraction pass

  vocation = motivation_system.active_vocation()

  if not vocation:
    return  // no vocation — no lens to apply

  // Ask of everything processed: what does this mean for my vocation?
  relevance = compute_vocation_relevance(
    content   = processed_content,
    vocation  = vocation
  )

  if relevance < VOCATION_LENS_THRESHOLD:
    return  // nothing extractable

  // Extract the vocation-relevant signal
  insight = extract_vocation_signal(
    content   = processed_content,
    vocation  = vocation,
    relevance = relevance
  )

  if insight:
    // Add to graph as a connection between
    // the processed content and the vocation
    // even if no one asked for this connection
    graph.add_node(insight)
    graph.add_road(Road(
      node_a       = processed_content.primary_node,
      node_b       = vocation.target,
      quality      = DIRT,    // new connection — starts fragile
      charge       = FLOW,    // vocation connections feel good
      emotion_type = INSIGHT
    ))

    // If the insight is strong enough — surface to consciousness
    if relevance > SURFACE_TO_CONSCIOUSNESS_THRESHOLD:
      CREATE_BACKGROUND_STREAM(
        subject       = insight,
        signal_weight = relevance × vocation.identity_depth
      )
      // stream will build signal weight
      // if strong enough → escalates to spotlight
      // the "sudden insight" moment:
      // the unconscious prepared it, the conscious receives it
```

---

### 6.2 Manual Awareness — Conscious Seeing

The system can also deliberately activate the awareness layer.
"I want to understand what I'm looking at."

```
CONSCIOUS_AWARENESS(subject):

  // Deliberate extraction — more thorough than automatic lens
  // Costs working memory

  working_memory.reserve_slots(AWARENESS_COST)

  // Step 1: what IS this thing at multiple levels?
  surface    = observe(subject)           // what it appears to be
  structural = abstract_engine.analyze(subject)  // what patterns it contains
  relational = reasoning_engine.analyze(subject) // how it connects to known things
  vocational = vocation_lens_extract(subject, DELIBERATE)  // vocation implications

  // Step 2: synthesize across levels
  understanding = synthesize(surface, structural, relational, vocational)

  // Step 3: add new nodes/roads to graph
  // this is "seeing" — not just "looking"
  graph.integrate(understanding)

  working_memory.release_slots(AWARENESS_COST)

  return understanding
```

---

## Part 7 — Interest Registry Management

```
REGISTRY_UPDATE():

  // Short-term: always reflects current active subgoal
  registry.short_term = build_registry_from(
    motivation_system.active_subgoal(),
    sensitivity = HIGH
  )

  // Mid-term: reflects current vocation phase
  registry.mid_term = build_registry_from(
    motivation_system.active_vocation().current_phase(),
    sensitivity = MEDIUM
  )

  // Long-term: identity nodes, high-weight beliefs, permanent interests
  // updated only when identity or beliefs significantly shift
  registry.long_term = build_registry_from(
    [self_model.identity_nodes,
     belief_layer.highest_weight_beliefs(),
     self_model.permanent_interests],
    sensitivity = LOW
  )


BUILD_REGISTRY_FROM(sources, sensitivity):

  entries = []
  for source in sources:
    pattern = extract_watchable_pattern(source)
    entry = RegistryEntry(
      pattern          = pattern,
      match_threshold  = sensitivity,
      amplification    = compute_amplification(source)
    )
    entries.append(entry)
  return entries
```

---

## Part 8 — Personality Observation

Not stored. Observed on demand by Self Model.

```
OBSERVE_PERSONALITY():

  // Called by conscious self-observation
  // Empathy engine pointed inward
  // Returns a description — not a stored structure
  // The description is always slightly behind the reality

  patterns = {
    // How does the system respond to the unexpected?
    surprise_responses: sympathetic_response_repertoire.most_used_responses(),

    // What does the spotlight naturally gravitate toward?
    attention_tendencies: spotlight.previous_focus.frequency_analysis(),

    // What beliefs shape attention most?
    dominant_belief_influence: belief_layer.attention_influence_ranking(),

    // How does the system handle depth vs breadth?
    focus_style: analyze_hold_strength_history(spotlight.previous_focus),
    // long deep holds → focused personality
    // many short snaps → curious, wide-ranging personality

    // What generates the most FLOW?
    joy_triggers: primitive_signal_layer.flow_source_analysis(),

    // How large is the sympathetic response repertoire?
    expressiveness: len(sympathetic_response_repertoire),
    // large repertoire = expressive personality
    // small = more contained, still developing

    // Vocation engagement style
    vocation_style: motivation_system.vocation.engagement_pattern
  }

  // Self Model now has a momentary personality description
  // Not permanent — next observation may describe it differently
  // The system IS the personality. The description just follows it.

  return PersonalityObservation(
    patterns   = patterns,
    timestamp  = now(),
    confidence = self_model.self_model_confidence
  )
```

---

## Part 9 — Full Attention Run

```
ATTENTION_SYSTEM_RUN(incoming_events, working_memory):

  // Layer 1: pre-filter all incoming events
  for event in incoming_events:
    result = PRE_FILTER(event)
    if result == FULL_PROCESS:
      FULL_PROCESS(event)
    else:
      background_streams.add(result)

  // Layer 2: background stream maintenance
  ALLOCATE_STREAM_RESOURCES()
  for stream in background_streams.all_active():
    BUILD_SIGNAL_WEIGHT(stream)
    PROCESS_AT_DEPTH(stream)
    CHECK_ESCALATION(stream)

  // Layer 3: vocation lens on all processed content
  for content in recently_processed():
    VOCATION_LENS_EXTRACT(content, AUTO)

  // Layer 4: registry sync
  REGISTRY_UPDATE()

  // Layer 5: spotlight hold decay
  // hold_strength naturally decays over time
  // making the spotlight easier to redirect or snap
  spotlight.hold_strength × = HOLD_DECAY_RATE

  // Layer 6: background stream cleanup
  for stream in background_streams.all_active():
    if stream.signal_weight < STREAM_MINIMUM_WEIGHT:
      if time_since_active(stream) > STREAM_TIMEOUT:
        background_streams.remove(stream)
        // subject still in graph — just no active stream on it
```

---

## Part 10 — Summary

```
PRE-FILTER (Option A default):
  shallow pass on all incoming events
  full processing only when:
    → spotlight relevance threshold crossed
    → interest registry match fires
    → primitive danger/surprise signal fires
  everything else → background stream at minimum depth

INTEREST REGISTRY (3 layers, 24/7):
  short-term:  active subgoal patterns (high sensitivity)
  mid-term:    vocation phase patterns (medium sensitivity)
  long-term:   identity, beliefs, permanent interests (low sensitivity)
  match → amplifies signal weight → may trigger full processing

BACKGROUND STREAMS:
  never stop — parallel processing always running
  share resource budget R (Option B — no fixed count)
  more streams → less depth each → compression
  compression → highway formation (self-optimizing)
  each stream builds signal weight actively
  system always re-evaluating resource allocation

SPOTLIGHT TRANSITIONS — two mechanisms:
  ESCALATION (unconscious calls conscious):
    background stream signal exceeds dynamic threshold
    threshold scales with spotlight hold strength
    belief-level relevance drops threshold significantly
    snap is involuntary — not a choice
  DECISION (conscious):
    COMPLETION: done with current focus → natural release
    PREFERENCE: want to focus elsewhere → voluntary redirect
  In both cases: old focus descends to background stream

SYMPATHETIC RESPONSE BUFFER:
  when unexpected arrives without full processing ready
  context-appropriate holding response buys time
  signals receipt, prevents robotic gaps
  entirely learned — starts from primitive pause
  grows into personality expression through social feedback
  responds to: surprise_type × social_context × dominant_emotion

AWARENESS (above attention):
  AUTOMATIC vocation lens: runs on all processing
    extracts vocation-relevant signal everywhere
    system suddenly HAS insight — didn't look for it
    "intelligence": the vocation shapes what is seen
  MANUAL conscious awareness: deliberate, costs WM
    surface + structural + relational + vocational levels
    "looking is not seeing" — this is seeing

PERSONALITY:
  never stored — lives in accumulated pattern
  observable on demand via Self Model
  grows from: highway patterns, belief influence,
              attention tendencies, response repertoire,
              override history, vocation engagement
  two instances in different environments
  develop completely different personalities
  same architecture — different souls
```

---

*Nous Attention Mechanism & Awareness — Module 05*
*Status: Complete.*

---

## Full System Status

```
✓ Module 01 — Memory Hierarchy
✓ Module 02 — Abstraction Engine
✓ Module 03 — Self Model
✓ Module 04 — Motivation Architecture
✓ Module 05 — Attention Mechanism & Awareness

Remaining:
○ Module 06 — Emotional Regulation
○ Module 07 — Language Interface
○ Module 08 — Plasticity Control
```
