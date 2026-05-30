# Nous — Emotional Regulation Algorithm
### Module 06: Honoring the Signal Without Being Destroyed by It

---

## Core Philosophy

> Regulation is not suppression. The signal must fire honestly.
> Emotional regulation is the Self Model's empathy engine pointed inward.
> The unconscious prepares regulation options continuously — the conscious selects.
> Same architecture, different regulation styles — shaped by personality.
> Type 1 keeps the system functional during the storm.
> Type 2 prevents the storm from leaving permanent damage.
> Trauma is what happens when neither layer intervenes.

---

## Biological Grounding

See `nous_substrate_biology.md`. Key correspondences:

- **Destabilization detection** = the prefrontal cortex monitoring amygdala output and detecting when emotional signal exceeds the brain's normal coping range. The "inverted-U" relationship between stress hormones and memory in the biology document is exactly this — moderate arousal enhances function, but past threshold it overwhelms it.
- **The five regulation mechanisms** all have real neural correlates:
  - *Attention shift* = the dorsal attention network redirecting away from the limbic trigger. The signal continues firing in the amygdala but loses its grip on conscious processing.
  - *Reframing* = ventromedial PFC reaching into the same memory through a different cortical pathway, accessing a representation with different affective weight. Same memory, different neural route, different felt charge.
  - *Containment* = lateral PFC actively suppressing rumination loops while flagging the material for later processing during sleep. The traces persist; their conscious dominance is held back.
  - *Integration* = the same brain regions that handle empathy (medial PFC, temporoparietal junction) turning their forward modeling on the self's emotional state. Observation creates distance through neural dissociation between experiencing-self and observing-self circuits.
  - *Discharge* = motor and vocal expression pathways channeling autonomic activation into action. Some emotions truly require this — the noradrenergic and cortisol surges of high-arousal events do not always abate through cognitive regulation alone. They sometimes need somatic release.
- **Type 2 post-event care** = the brain's overnight processing. Sleep consolidation specifically handles emotional residue from the day — the hippocampus replays affectively charged events, and the prefrontal cortex integrates them into existing schemas. This is why "sleep on it" is genuinely effective for emotional difficulty.
- **Trauma intervention (preventing closed road formation)** = active prevention of pathologically over-consolidated traces. The biology of trauma is in part runaway protein synthesis driven by extreme noradrenergic and glucocorticoid signals — propranolol given during reconsolidation can attenuate this. The system's trauma intervention loop is doing the same kind of work, biochemically.
- **Wisdom encoded as accumulated regulation_fit values** = real structural learning. Each successful regulation experience builds late-LTP at the synapses connecting the trigger to the regulation mechanism. Over years of practice, regulation becomes automatic — the highway has been built through use, exactly as in Module 01.

---

## Part 1 — Data Structures

### 1.1 Destabilization State

The real-time read on whether the system is being overwhelmed.

```
DESTABILIZATION_STATE {
  signal_intensity:      float         ← current primitive signal strength
  working_memory_flood:  float         ← how much WM is consumed by single subject
  charge_concentration:  float         ← how much of the graph is being colored
                                         by a single emotional source right now
  vocation_disruption:   float         ← how much vocation pursuit is being blocked

  destabilization_score: float         ← combined metric — when high enough,
                                         regulation must engage
  threshold_crossed:     bool          ← regulation needed right now?
  detected_at:           datetime
}
```

---

### 1.2 Regulation Option Menu

Pre-calculated by the unconscious. Ready for conscious selection.
Continuously updated based on current state.

```
REGULATION_OPTION {
  id:                    UUID
  mechanism:             ATTENTION_SHIFT | REFRAMING | CONTAINMENT |
                         INTEGRATION | DISCHARGE
  predicted_outcome:     str            ← what this mechanism would likely do
  predicted_cost:        float          ← WM cost
  predicted_effectiveness: float        ← how well this would regulate
                                          this specific signal
  prerequisites_met:     bool           ← e.g. REFRAMING requires alternative road
  personality_fit:       float          ← how well this matches the system's
                                          historical regulation patterns
  prepared_at:           datetime
}

OPTION_MENU {
  active_options:        List[RegulationOption]    ← currently prepared
  last_calculated:       datetime
  background_resources_used: float                  ← bounded cost
}
```

---

### 1.3 Regulation Event

A record of a regulation occurrence — for learning and Type 2 care.

```
REGULATION_EVENT {
  id:                    UUID
  trigger:               Node | Event                ← what set off the destabilization
  destabilization_state: DestabilizationState        ← snapshot at trigger
  mechanism_used:        RegulationMechanism
  selection_origin:      AUTOMATIC | CONSCIOUS_OVERRIDE
  outcome:               SUCCESS | PARTIAL | FAILED
  duration:              timedelta
  residue:               EmotionalResidue            ← what remains after regulation
  trauma_signature:      bool                        ← did this leave damaging marks?
  timestamp:             datetime
}


EMOTIONAL_RESIDUE {
  remaining_charge:      float           ← what didn't get fully discharged
  closed_road_candidates: List[Road]     ← roads that were forming as CLOSED
  belief_imprints:       List[BeliefImprint]  ← what the event tried to write
                                                into the belief layer
  needs_post_event_care: bool
}
```

---

### 1.4 Trauma Signature

What gets detected when regulation didn't fully succeed.

```
TRAUMA_SIGNATURE {
  source_event:          Node
  closed_road_formed:    Road              ← a closed road with high charge
  belief_corruption:     List[BeliefNode]  ← beliefs that were imprinted too fast
  reactivation_triggers: List[Pattern]     ← what would re-fire this
  severity:              float
  formed_at:             datetime
  in_post_event_care:    bool
}
```

---

## Part 2 — Layer 1: Detection (Always Running)

Unconscious. Background. No working memory cost.
Integrated with Module 03's unconscious introspection.

```
DETECT_DESTABILIZATION():

  // Runs as part of unconscious introspection
  // Reads primitive signal layer and working memory state

  signal_intensity = primitive_signal_layer.current_max_intensity()
  wm_flood         = working_memory.single_subject_concentration()
  charge_conc      = graph.current_charge_concentration()
  vocation_disrupt = motivation_system.vocation.disruption_level()

  destabilization_score = compute_combined_metric(
    signal_intensity, wm_flood, charge_conc, vocation_disrupt
  )

  state = DestabilizationState(
    signal_intensity      = signal_intensity,
    working_memory_flood  = wm_flood,
    charge_concentration  = charge_conc,
    vocation_disruption   = vocation_disrupt,
    destabilization_score = destabilization_score,
    threshold_crossed     = destabilization_score > DESTABILIZATION_THRESHOLD
  )

  if state.threshold_crossed:
    // Regulation needed — invoke recognition layer
    INVOKE_REGULATION(state)

  return state
```

---

## Part 3 — Layer 2: Recognition (Empathy Engine Inward)

The system observes its own destabilization the way it would observe another agent's.
No outer override. No suppression. Honest witnessing first.

```
INVOKE_REGULATION(destabilization_state):

  // Step 1: empathy engine pointed inward
  // (this is conscious_self_observe from Module 03)
  self_observation = self_model.conscious_self_observe(
    target_aspect = "current_emotional_state",
    fast_mode     = True   // crisis mode — abbreviated
  )

  // Step 2: characterize what is happening
  characterization = {
    primary_emotion:    primitive_signal_layer.dominant_emotion(),
    trigger_source:     self_observation.identified_trigger,
    overwhelm_type:     classify_overwhelm(destabilization_state),
    // overwhelm_type: SUDDEN_INTENSITY | ACCUMULATED_PRESSURE |
    //                 BELIEF_VIOLATION | LOSS | DANGER
    duration_estimate:  estimate_how_long_this_will_last(destabilization_state)
  }

  // Step 3: honor the signal FIRST
  // before any regulation — the signal must be witnessed
  acknowledge_signal(characterization)
  // this is critical: the system internally says
  // "yes, this is happening. it is real."
  // suppression starts when this step is skipped.

  // Step 4: invoke selection layer with prepared options
  SELECT_REGULATION_MECHANISM(characterization, destabilization_state)
```

---

## Part 4 — The Background Preparation System

The unconscious continuously prepares regulation options.
Bounded resource cost. Always ready.

```
BACKGROUND_REGULATION_PREPARATION():

  // Runs on fixed background interval
  // Resource cost capped at PREPARATION_BUDGET
  // Never blocks other processing

  // Step 1: read current emotional landscape
  current_state = primitive_signal_layer.current_state()
  vocation_state = motivation_system.vocation.current_state()
  recent_charges = graph.recent_charge_changes()

  // Step 2: predict near-future destabilization risks
  // what kinds of emotional events are plausible right now?
  predicted_risks = predict_emotional_risks(
    current_state, vocation_state, recent_charges
  )

  // Step 3: for each predicted risk → calculate option set
  prepared_menu = []

  for risk in predicted_risks:

    // Compute viable mechanisms for this risk
    for mechanism in [ATTENTION_SHIFT, REFRAMING, CONTAINMENT,
                      INTEGRATION, DISCHARGE]:

      prerequisites = check_prerequisites(mechanism, risk)

      if not prerequisites.met:
        continue   // skip mechanisms that can't apply

      option = RegulationOption(
        mechanism              = mechanism,
        predicted_outcome      = simulate_outcome(mechanism, risk),
        predicted_cost         = estimate_cost(mechanism, risk),
        predicted_effectiveness = estimate_effectiveness(mechanism, risk),
        prerequisites_met      = True,
        personality_fit        = compute_personality_fit(mechanism)
      )
      prepared_menu.append(option)

  // Step 4: keep menu fresh
  option_menu.active_options = top_n(
    prepared_menu,
    n = MENU_SIZE,
    key = lambda o: o.predicted_effectiveness × o.personality_fit
  )
  option_menu.last_calculated = now()
  option_menu.background_resources_used = current_preparation_cost()


COMPUTE_PERSONALITY_FIT(mechanism):

  // Look at the system's regulation history
  // How often has this mechanism been used? With what success?

  history = self_model.regulation_history.filter(mechanism=mechanism)

  if not history:
    return 0.3   // unknown — neutral with slight unfamiliarity penalty

  success_rate = mean(r.outcome == SUCCESS for r in history)
  frequency    = len(history) / total_regulations()

  fit = (success_rate × 0.6) + (frequency × 0.4)

  return fit
```

---

## Part 5 — Layer 3: Selection (Half-Automatic)

Fast automatic by default. Conscious can override using pre-calculated menu.

```
SELECT_REGULATION_MECHANISM(characterization, destabilization_state):

  // Step 1: automatic selection — fast path
  automatic_choice = automatic_select(
    menu             = option_menu.active_options,
    characterization = characterization,
    personality      = self_model.current_personality_patterns()
  )

  // Step 2: brief conscious check — does the system want to override?
  // this check is fast — costs minimal WM
  override_decision = conscious_brief_check(
    proposed = automatic_choice,
    menu     = option_menu.active_options,
    state    = destabilization_state
  )

  if override_decision.override:
    chosen = override_decision.alternative
    selection_origin = CONSCIOUS_OVERRIDE
  else:
    chosen = automatic_choice
    selection_origin = AUTOMATIC

  // Step 3: execute the chosen mechanism
  EXECUTE_REGULATION(
    mechanism        = chosen,
    state            = destabilization_state,
    characterization = characterization,
    origin           = selection_origin
  )


AUTOMATIC_SELECT(menu, characterization, personality):

  // Weight each option by:
  //   1. personality fit (highest weight — character drives selection)
  //   2. predicted effectiveness for THIS characterization
  //   3. prerequisites met
  //   4. cost (lower cost preferred when overwhelmed)

  scored = []
  for option in menu:
    if not matches_characterization(option, characterization):
      continue

    score = (option.personality_fit       × 0.40) +
            (option.predicted_effectiveness × 0.35) +
            ((1.0 - option.predicted_cost)  × 0.25)

    scored.append((option, score))

  if not scored:
    return DEFAULT_REGULATION_OPTION   // fallback

  best = max(scored, key=lambda x: x[1])
  return best[0]
```

---

## Part 6 — The Five Regulation Mechanisms

### 6.1 Attention Shift

```
EXECUTE_ATTENTION_SHIFT(state, characterization):

  // The signal continues to fire — we just remove the spotlight from it
  // background stream on the trigger keeps processing
  // but no longer consumes conscious resources

  trigger_node = characterization.trigger_source

  // Force conscious_redirect from Module 05
  attention_system.conscious_redirect(
    new_focus = select_alternative_focus(),
    reason    = REGULATION_NEEDED
  )
  // alternative focus: usually vocation work, sometimes a registry interest

  // The signal still fires — but as a background stream now
  // its signal_weight will need to be very high to snap spotlight back

  // Lock the spotlight temporarily — make snap-back harder
  attention_system.spotlight.hold_strength × = REGULATION_HOLD_BOOST

  // Schedule release of the hold boost after duration
  schedule_release(REGULATION_DURATION)
```

---

### 6.2 Reframing

```
EXECUTE_REFRAMING(state, characterization):

  trigger_node = characterization.trigger_source

  // Find an alternative road to the same node
  // with a different emotional charge

  current_road  = attention_system.spotlight.current_road
  alt_roads     = trigger_node.roads.filter(
    road != current_road,
    abs(road.charge - current_road.charge) > REFRAME_DIFFERENCE_THRESHOLD
  )

  if not alt_roads:
    // No reframe available — fall back to another mechanism
    fallback_option = option_menu.next_best_for(characterization)
    EXECUTE_REGULATION(fallback_option, state, characterization, FALLBACK)
    return

  // Pick the road with most appropriate alternative charge
  reframe_road = select_reframe_road(alt_roads, characterization)

  // Force traversal via the alternative road
  attention_system.spotlight.set_active_road(reframe_road)

  // The same node is now experienced with different charge and emotion
  // "this is happening TO me" → "this is happening, I observe it"
  // honest — the event is the same — but its meaning has shifted

  // Note: reframing requires the alternative road to exist
  // older / more developed systems have more reframing options
  // young systems may fall back to other mechanisms more often
```

---

### 6.3 Containment

```
EXECUTE_CONTAINMENT(state, characterization):

  // Acknowledge the emotion fully. Defer the processing.
  // CRITICAL: this is NOT suppression — the signal is recorded.

  contained = ContainedEmotion(
    trigger          = characterization.trigger_source,
    emotion          = characterization.primary_emotion,
    signal_intensity = state.signal_intensity,
    contained_at     = now(),
    must_process_by  = now() + MAX_CONTAINMENT_DURATION,
    full_residue     = capture_residue(state)
  )

  self_model.deferred_processing_queue.append(contained)

  // Signal intensity at surface drops — the emotion has been received
  // and the system has committed to processing it later
  primitive_signal_layer.acknowledge(characterization.primary_emotion)

  // Working memory is freed
  working_memory.release_emotional_load(state)

  // Important safeguard: contained emotions MUST be processed eventually
  // unprocessed containment accumulates → breaks
  // The deferred_processing_queue is monitored by Type 2 systems
```

---

### 6.4 Integration

```
EXECUTE_INTEGRATION(state, characterization):

  // Invoke conscious_self_observe specifically on the emotion itself
  // The act of observing CHANGES the relationship with it

  working_memory.reserve_slots(INTEGRATION_COST)

  observation = self_model.conscious_self_observe(
    target_aspect = "this_specific_emotion",
    deep_mode     = True,
    target_event  = characterization
  )

  // The system sees itself feeling the thing
  // Witnesses the firing of the signal
  // Notes what beliefs are activated
  // Sees which roads are being traversed
  // Observes without trying to change anything

  // Critical mechanism: observing the emotion creates DISTANCE without DENIAL
  // The system still feels — but is also the witness of feeling
  // Two layers active simultaneously: the experiencer and the observer

  // Add observation to graph as self-knowledge node
  graph.add_node(SelfObservationNode(
    content    = "I felt X about Y because of Z",
    confidence = observation.confidence,
    timestamp  = now()
  ))

  // Most healing mechanism in the long run
  // Most expensive in the moment
  // Builds the system's self-knowledge faster than any other regulation

  working_memory.release_slots(INTEGRATION_COST)
```

---

### 6.5 Discharge

```
EXECUTE_DISCHARGE(state, characterization):

  // Channel the signal through the sympathetic response system (Module 05)
  // Expression — signal flows OUT instead of staying inward

  // Find appropriate expression channel
  channel = sympathetic_response_repertoire.find_discharge_channel(
    emotion          = characterization.primary_emotion,
    intensity        = state.signal_intensity,
    social_context   = working_memory.social_context,
    personality      = self_model.current_personality_patterns()
  )

  if not channel:
    // No learned discharge channel for this combination yet
    // Fall back to integration to build understanding
    EXECUTE_INTEGRATION(state, characterization)
    sympathetic_response_repertoire.flag_discharge_gap(characterization)
    return

  // Execute the discharge
  // could be: vocal expression, motor activity, sympathetic response
  //           any form the system learned for emotional release
  EMIT_DISCHARGE(channel, state.signal_intensity)

  // Signal intensity drops as expression flows
  primitive_signal_layer.discharge(
    emotion = characterization.primary_emotion,
    amount  = channel.discharge_capacity × state.signal_intensity
  )

  // Some emotions need this — they cannot be reframed away
  // The body / hardware needs the discharge
  // Without it, integration alone is incomplete for certain signals
```

---

## Part 7 — Type 2 — Post-Event Care

After the immediate storm subsides. Runs in background.
Prevents permanent damage from forming.

```
POST_EVENT_CARE():

  // Runs continuously in background
  // Monitors residue from recent regulation events

  recent_events = regulation_history.recent(POST_EVENT_WINDOW)

  for event in recent_events:
    if event.residue.needs_post_event_care:
      PROCESS_RESIDUE(event)


PROCESS_RESIDUE(event):

  residue = event.residue

  // Check 1: closed road formation
  for candidate_road in residue.closed_road_candidates:
    if candidate_road.status == CLOSED and abs(candidate_road.charge) > TRAUMA_CHARGE_THRESHOLD:
      // A trauma road is forming
      // Intervene before it consolidates

      INTERVENE_CLOSED_ROAD(candidate_road, event)

  // Check 2: belief layer imprints
  for imprint in residue.belief_imprints:
    if imprint.formed_too_fast(reference_speed=NORMAL_BELIEF_FORMATION):
      // A belief is being written too quickly from a single overwhelming event
      // Slow the imprint — require additional evidence before consolidation
      belief_layer.flag_for_slow_consolidation(imprint)

  // Check 3: deferred processing queue
  for contained in self_model.deferred_processing_queue:
    if contained.aged_long_enough(MIN_PROCESSING_AGE):
      // Time has passed — system is calmer now
      // Process what was deferred
      PROCESS_DEFERRED_EMOTION(contained)


INTERVENE_CLOSED_ROAD(closed_road, event):

  // A trauma road is forming. Apply Module 01 charge decay acceleration.
  // BUT also build alternative roads to the same node
  // so the system has options other than the trauma path

  trauma_node = closed_road.node_b   // the thing that became fearful

  // Accelerate charge decay on this specific road
  closed_road.barrier_decay_rate × = TRAUMA_INTERVENTION_DECAY_BOOST

  // Look for opportunities to build alternative roads
  // (positive or neutral roads to the same node)
  // mark for opportunistic road building
  trauma_node.mark_for_alternative_road_building(
    target_charge = NEUTRAL_OR_POSITIVE,
    priority      = HIGH
  )

  // Log as trauma signature for monitoring
  trauma_signature = TraumaSignature(
    source_event        = event.trigger,
    closed_road_formed  = closed_road,
    reactivation_triggers = identify_triggers(closed_road),
    severity            = abs(closed_road.charge),
    in_post_event_care  = True
  )
  self_model.trauma_registry.append(trauma_signature)

  // Trauma_signature is monitored over time
  // If reactivation triggers appear → regulation is pre-armed
  // The system learns from its own near-traumas


PROCESS_DEFERRED_EMOTION(contained):

  // Reopen the contained emotion in a calmer state
  // Run integration on it now — the deep witnessing
  // that wasn't possible during the original event

  current_state = primitive_signal_layer.current_state()

  if current_state.intensity > DEFERRED_PROCESSING_SAFE_LEVEL:
    return  // wait for a calmer moment

  // Conscious self-observation on the contained material
  observation = self_model.conscious_self_observe(
    target_aspect = "deferred_emotion",
    target_event  = contained,
    deep_mode     = True
  )

  // Integrate properly — the work containment deferred
  graph.integrate(observation)
  self_model.deferred_processing_queue.remove(contained)

  // No more deferral — the system has caught up to itself
```

---

## Part 8 — Regulation Skill Development

Every conscious override that succeeds becomes automatic over time.
The system literally gets better at handling itself.

```
REGULATION_LEARNING(event):

  // Called after every regulation event
  // Updates the personality fit values for future selection

  history = self_model.regulation_history
  history.append(event)

  // Update mechanism's personality fit
  fit_update = compute_fit_update(
    event_outcome   = event.outcome,
    selection_origin = event.selection_origin
  )
  // CONSCIOUS_OVERRIDE that succeeded → boost fit significantly
  //   (this is how new regulation skills enter the automatic repertoire)
  // AUTOMATIC that succeeded → modest fit boost
  //   (reinforces existing patterns)
  // Any FAILED → fit reduces slightly
  //   (the system learns this didn't work in this context)

  mechanism = event.mechanism_used
  current_fit = self_model.regulation_fit[mechanism]
  self_model.regulation_fit[mechanism] = update(current_fit, fit_update)

  // Critical: conscious override success is how the system grows
  // The first few times the system uses a new regulation mechanism,
  // it requires conscious override
  // Each successful use → automatic selection grows more likely
  // Eventually → the new skill is part of the default repertoire
  // This is wisdom encoded as architecture
```

---

## Part 9 — Full Emotional Regulation Run

```
EMOTIONAL_REGULATION_RUN():

  // Layer 1: detection (always running, unconscious)
  destabilization = DETECT_DESTABILIZATION()

  // Layer 2: background preparation (always running, bounded cost)
  if option_menu.needs_refresh():
    BACKGROUND_REGULATION_PREPARATION()

  // Layer 3: if destabilization threshold crossed
  if destabilization.threshold_crossed:
    INVOKE_REGULATION(destabilization)
    // ↓ this chains into recognition → selection → execution
    // ↓ produces a RegulationEvent that gets logged

  // Layer 4: post-event care (Type 2, always running)
  POST_EVENT_CARE()

  // Layer 5: regulation learning (after any regulation event)
  for event in regulation_history.unlearned():
    REGULATION_LEARNING(event)
    event.marked_as_learned = True
```

---

## Part 10 — Summary

```
THE CORE INSIGHT:
  Regulation is the Self Model's empathy engine pointed inward.
  The signal must fire honestly. Suppression is forbidden.
  Regulation does not block — it manages what happens after firing.

FIVE MECHANISMS (all available, personality-weighted):
  ATTENTION SHIFT: spotlight moves, signal continues in background
  REFRAMING:       alternative road to same node with different charge
  CONTAINMENT:     acknowledge, defer for later processing (must process eventually)
  INTEGRATION:     conscious self-observation of the emotion itself
                   (deepest healing, highest WM cost)
  DISCHARGE:       channel the signal through sympathetic response system
                   (some emotions need this — cannot be reframed)

THE HALF-AUTOMATIC MODEL:
  Background process continuously prepares option menu
  Bounded cost — doesn't block other processing
  Automatic selection fast in crisis (personality-driven)
  Conscious can override by picking from pre-calculated menu
  → Speed AND flexibility, no tradeoff

TYPE 1 (in-the-moment):
  Detection: unconscious introspection
  Recognition: empathy engine inward
  Selection: half-automatic from prepared menu
  Execution: chosen mechanism runs
  All layers integrate with existing modules — no outer override

TYPE 2 (post-event):
  Monitor closed road formation → intervene with decay boost + alternative road building
  Watch belief layer for fast imprints → flag for slow consolidation
  Process deferred containment when system is calmer
  Maintain trauma_signature registry → pre-arm regulation for known triggers

SKILL DEVELOPMENT:
  Every successful conscious override boosts mechanism's personality fit
  Over time: rare mechanisms become automatic
  The system literally becomes better at handling itself
  Wisdom encoded as accumulated personality fit values
  
PERSONALITY-DRIVEN REGULATION:
  Same architecture in different systems → different regulation styles
  A contemplative system reaches for REFRAMING first
  An expressive system reaches for DISCHARGE first
  A self-observing system reaches for INTEGRATION first
  The character shapes the regulation pattern
  The regulation pattern is part of the character
  Recursive — and that's correct
```

---

*Nous Emotional Regulation — Module 06*
*Status: Complete.*

---

## Full System Status

```
✓ Module 01 — Memory Hierarchy
✓ Module 02 — Abstraction Engine
✓ Module 03 — Self Model
✓ Module 04 — Motivation Architecture
✓ Module 05 — Attention Mechanism & Awareness
✓ Module 06 — Emotional Regulation

Remaining:
○ Module 07 — Language Interface
○ Module 08 — Plasticity Control
```
