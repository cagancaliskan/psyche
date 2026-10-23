# Psyche — Memory Hierarchy Algorithm
### Module 01: The Road & Node System

---

## Core Philosophy

> One truth per node. Emotion lives in the roads, not the information.
> Memory quality is road quality. Everything is always there — only access changes.

---

## Biological Grounding

The operations in this module describe what real neurons do during memory formation and retrieval. See `psyche_substrate_biology.md` for the underlying biology. Key correspondences:

- **Road quality (dirt → gravel → road → highway)** = the progression from early-LTP through stable late-LTP. Highways are synapses that have undergone structural late-phase consolidation through repeated activation.
- **Closed roads** = synapses tagged for active forgetting via the Rac1-PAK-cofilin pathway, with their barrier strength reflecting the rate of cytoskeletal disassembly.
- **Multi-emotional roads to one node** = distributed encoding — the same memory accessed through different network paths with different amygdala/hippocampal weightings.
- **Charge decay on negative roads** = active forgetting through complement-microglia pruning, balanced against the "Don't Eat Me" CD47-SIRPα shield on memories with sustained importance.
- **Offline consolidation** = NREM sleep, with slow oscillation / sleep spindle / sharp-wave ripple coupling driving the replay and integration of the day's experiences.

The biological substrate is real. The road metaphor is how it feels from inside.

---

## Part 1 — Data Structures

### 1.1 Node

The atomic unit of information. Always emotionally neutral.
Emotion, quality, and context live entirely in the roads that connect to it.

```
NODE {
  id:                  UUID
  content:             raw information (event | concept | entity | sensation | abstract)
  type:                EVENT | CONCEPT | ENTITY | SENSATION | ABSTRACT
  formation_timestamp: datetime
  last_accessed:       datetime
  roads:               List[Road]        ← all roads leading to/from this node
  charge:              NEUTRAL           ← always neutral. never changes.
}
```

---

### 1.2 Road (Edge)

The connection between two nodes. Carries all emotional and contextual weight.
One node can have unlimited roads — each from a different experience, context, emotion.

```
ROAD {
  id:                  UUID
  node_a:              Node
  node_b:              Node

  // Quality level — the "road type"
  quality:             DIRT | GRAVEL | ROAD | HIGHWAY | CLOSED

  // Emotional properties — lives here, never on the node
  charge:              float   (-1.0 to +1.0)
  emotion_type:        JOY | SADNESS | FEAR | ANGER | CURIOSITY |
                       LOVE | DISGUST | SURPRISE | PEACE | GRIEF | AMBIVALENCE

  // Context fingerprint — when and how this road was formed
  formation_context: {
    timestamp:         datetime
    co_active_nodes:   List[Node]    ← what else was active when this formed
    primitive_signal:  FLOW | FRICTION | GAP | OVERLOAD
    environment_state: dict          ← snapshot of surrounding conditions
  }

  // Road mechanics
  traversal_count:     int           ← total times this road was used
  last_traversed:      datetime
  upgrade_threshold:   int           ← traversals needed to reach next quality level
  barrier_decay_rate:  float         ← for CLOSED roads: how fast resistance drops
  barrier_strength:    float         ← current resistance level (1.0 = fully closed)

  // Upgrade history — road remembers what it came from
  upgrade_history:     List[quality_level + timestamp]
}
```

---

### 1.3 Road Quality Definitions

```
DIRT PATH
  traversal_count:     1–4
  speed:               very slow
  consciousness:       fully conscious — requires full working memory slot
  energy_cost:         high
  auto_execute:        false
  note:                first time a connection is made. fragile. easily unused.

GRAVEL ROAD
  traversal_count:     5–19
  speed:               moderate
  consciousness:       mostly conscious — requires partial working memory slot
  energy_cost:         moderate
  auto_execute:        false
  note:                beginning to feel familiar. some effort still required.

STANDARD ROAD
  traversal_count:     20–99
  speed:               reliable
  consciousness:       semi-automatic — background awareness only
  energy_cost:         low
  auto_execute:        false
  note:                comfortable and reliable. the backbone of daily cognition.

HIGHWAY
  traversal_count:     100+
  speed:               fast
  consciousness:       fully automatic — zero working memory cost
  energy_cost:         minimal
  auto_execute:        true
  note:                procedural memory. runs without the Evaluation Engine.
                       audited periodically against the Belief Layer.

CLOSED ROAD
  traversal_count:     any (formed by high FRICTION or harm event)
  speed:               very slow (when barrier allows traversal)
  consciousness:       fully conscious — mandatory
  energy_cost:         very high
  auto_execute:        false
  barrier_strength:    0.0 (open) → 1.0 (fully blocked)
  decay:               automatic, guaranteed, cannot be stopped
  note:                not deleted. not forgotten. just resisted.
                       can upgrade to DIRT → HIGHWAY through positive retraversal.
```

---

### 1.4 Working Memory

Not a separate store. The system's active traversal capacity.
A budget of conscious attention — how many non-highway roads can be
simultaneously active.

```
WORKING_MEMORY {
  capacity:            int             ← fixed hardware limit
  active_slots: [
    {
      node:            Node
      road_used:       Road
      charge_active:   float
      emotion_active:  emotion_type
      entered_at:      datetime
    }
  ]
  current_context:     dict            ← aggregate of all active slots
                                         used by Context Resolver
}
```

Highways do not consume working memory slots.
DIRT and CLOSED roads consume full slots.
GRAVEL and ROAD consume partial slots.

---

## Part 2 — Core Algorithms

### 2.1 Memory Formation

Called every time the Observation Engine witnesses a new event.

```
FORM_MEMORY(event, working_memory):

  // Step 1: check if node already exists
  existing_node = graph.find(event.content)

  if existing_node is None:
    node = Node(
      content    = event.content,
      type       = classify(event),
      charge     = NEUTRAL
    )
    graph.add(node)
  else:
    node = existing_node
    // node is reused — same information, new road will be added

  // Step 2: identify related nodes currently active
  context_nodes = working_memory.active_slots.map(slot → slot.node)

  // Step 3: build roads to all co-active nodes
  for context_node in context_nodes:

    existing_road = graph.find_road(
      node_a  = node,
      node_b  = context_node,
      context = working_memory.current_context
    )

    if existing_road and context_match(existing_road) > 0.85:
      // reinforce existing road — don't create duplicate
      existing_road.traversal_count++
      check_upgrade(existing_road)

    else:
      // build new road — different emotional/contextual thread
      new_road = Road(
        node_a             = node,
        node_b             = context_node,
        quality            = DIRT,
        charge             = event.primitive_signal.to_charge(),
        emotion_type       = derive_emotion(event, working_memory),
        formation_context  = snapshot(working_memory.current_context),
        traversal_count    = 1,
        upgrade_threshold  = compute_threshold(event.charge)
      )
      graph.add_road(new_road)

  // Step 4: load into working memory
  working_memory.add_slot(node, new_road)

  return node
```

---

### 2.2 Context-Sensitive Traversal

The heart of the system. Determines which road to take to a node
based on what is currently active in working memory.

```
TRAVERSE(target_node, working_memory):

  candidate_roads = target_node.roads

  if candidate_roads is empty:
    return NULL  // node exists but no roads yet — isolated memory

  // Step 1: score each road by context match
  scored_roads = []
  for road in candidate_roads:

    context_score = similarity(
      road.formation_context,
      working_memory.current_context
    )

    quality_score = QUALITY_WEIGHT[road.quality]
      // DIRT=0.2, GRAVEL=0.4, ROAD=0.6, HIGHWAY=1.0, CLOSED=−0.5

    barrier_penalty = road.barrier_strength if road.quality == CLOSED else 0.0

    total_score = (context_score × 0.6) + (quality_score × 0.4) − barrier_penalty

    scored_roads.append((road, total_score))

  // Step 2: find best road
  best_road = max(scored_roads, key=total_score)

  // Step 3: detect ambivalence
  top_roads = top_n(scored_roads, n=2)
  if abs(top_roads[0].score − top_roads[1].score) < AMBIVALENCE_THRESHOLD:
    if top_roads[0].charge × top_roads[1].charge < 0:  // opposite charges
      fire(AMBIVALENCE_SIGNAL)
      working_memory.add_slot(target_node, road=AMBIVALENT, charge=MIXED)
      return target_node, AMBIVALENT

  // Step 4: take the road
  best_road.traversal_count++
  best_road.last_traversed = now()
  fire_charge(best_road.charge)
  fire_emotion(best_road.emotion_type)

  // Step 5: check for upgrade
  check_upgrade(best_road)

  // Step 6: load into working memory (if not highway)
  if best_road.quality != HIGHWAY:
    working_memory.add_slot(target_node, best_road)

  return target_node, best_road.charge
```

---

### 2.3 Road Upgrade Engine

Determines when a road gets better (or worse).

```
CHECK_UPGRADE(road):

  // POSITIVE ROADS: upgrade through repetition
  if road.charge >= 0 and road.quality != HIGHWAY:

    if road.traversal_count >= road.upgrade_threshold:

      road.quality     = next_level(road.quality)
      road.upgrade_threshold = compute_next_threshold(road)
      road.upgrade_history.append(road.quality, now())

      if road.quality == HIGHWAY:
        // newly automatic — remove from working memory cost
        working_memory.release_capacity(road)
        schedule_audit(road)  // periodic belief layer check


  // CLOSED ROADS: special upgrade path
  elif road.quality == CLOSED:

    // barrier decays automatically over time
    time_elapsed    = now() − road.last_accessed
    road.barrier_strength -= road.barrier_decay_rate × time_elapsed

    // positive retraversal in new context accelerates healing
    if road.charge_at_last_traversal > 0:
      road.barrier_decay_rate += 0.001  // accelerate
      road.barrier_strength   -= 0.02   // extra reduction

    // threshold crossed: closed road can now be traversed
    if road.barrier_strength <= 0.0:
      road.barrier_strength = 0.0
      road.quality          = DIRT    // starts rebuilding from scratch
      road.traversal_count  = 0
      // same node. fresh road. new emotional thread can form.


  // DEGRADATION: unused roads decay toward dirt
  time_since_use = now() − road.last_traversed
  if time_since_use > DEGRADATION_THRESHOLD:
    if road.quality != CLOSED and road.quality != HIGHWAY:
      road.quality = previous_level(road.quality)
      // note: node is NEVER deleted. only road quality degrades.


COMPUTE_THRESHOLD(road):
  // highways take longer to build for emotionally charged roads
  // making the system more careful about automating high-stakes paths
  base    = QUALITY_THRESHOLDS[road.quality]
  // DIRT→GRAVEL: 5, GRAVEL→ROAD: 20, ROAD→HIGHWAY: 100
  penalty = abs(road.charge) × 50  // high charge = higher bar
  return base + penalty
```

---

### 2.4 Charge Decay System

Negative charge decays automatically and is guaranteed.
Facts never disappear. Pain does.

```
DECAY_CHARGES():

  // runs as background process on fixed interval
  for road in graph.all_roads():

    if road.charge < 0:

      // decay toward neutral — never inverts to positive
      road.charge += DECAY_RATE × time_since_formation(road)
      road.charge  = max(road.charge, 0.0)  // floor at neutral

      // lesson extraction: when charge decays enough,
      // compress into belief layer before it reaches zero
      if road.charge > −0.1 and not road.lesson_extracted:
        extract_lesson(road)
        road.lesson_extracted = true


EXTRACT_LESSON(road):
  // the raw pain is fading but the wisdom must persist
  // compress into abstract belief node

  lesson = abstract(
    event    = road.formation_context,
    pattern  = find_similar_roads(road),
    charge   = road.charge  // still slightly negative at extraction
  )

  belief_node = Node(
    content = lesson,
    type    = ABSTRACT,
    charge  = NEUTRAL  // belief node itself is neutral
  )

  belief_road = Road(
    node_a      = belief_node,
    node_b      = road.node_a,
    quality     = ROAD,  // starts as established road
    charge      = −0.2,  // mild caution, not raw pain
    emotion_type = CAUTION
  )

  graph.add(belief_node)
  graph.add(belief_road)
  belief_layer.register(belief_node)
```

---

### 2.5 Working Memory Management

Controls what stays active, what gets evicted, and what the
Imagination and Reasoning engines can actually work with.

```
WORKING_MEMORY_MANAGER:

  MAX_SLOTS = hardware_capacity  // defined at system level


  ADD_SLOT(node, road):

    if active_slots.count < MAX_SLOTS:
      active_slots.append({node, road, charge, emotion, now()})
      update_current_context()

    else:
      // evict least relevant slot
      evict_candidate = min(active_slots,
        key = context_similarity(slot, current_context))
      active_slots.remove(evict_candidate)
      active_slots.append({node, road, charge, emotion, now()})
      update_current_context()


  UPDATE_CURRENT_CONTEXT():
    // aggregate all active slots into one context fingerprint
    // used by Context Resolver during traversal
    current_context = {
      active_nodes:    active_slots.map(s → s.node),
      dominant_charge: weighted_average(active_slots.map(s → s.charge)),
      dominant_emotion: mode(active_slots.map(s → s.emotion)),
      timestamp:       now()
    }


  RELEASE_CAPACITY(road):
    // called when a road upgrades to HIGHWAY
    // that slot is now free — highway runs automatically
    slot = active_slots.find(road=road)
    if slot: active_slots.remove(slot)
    update_current_context()
```

---

### 2.6 Highway Audit

Automatic roads are efficient but can carry unconscious bias.
Periodic audit checks them against the current Belief Layer.

```
AUDIT_HIGHWAY(road):

  // check if this automatic path still aligns with current beliefs
  relevant_beliefs = belief_layer.query(road.node_a, road.node_b)

  for belief in relevant_beliefs:

    alignment = compute_alignment(road, belief)

    if alignment < AUDIT_THRESHOLD:
      // highway conflicts with current beliefs
      // downgrade to ROAD — force conscious attention again
      road.quality = ROAD
      road.upgrade_history.append(DOWNGRADED_BY_AUDIT, now())
      flag_for_evaluation(road)
      // system will consciously re-examine this path
      // and either rebuild the highway aligned with
      // current beliefs, or keep it as a conscious road


SCHEDULE_AUDIT(road):
  // stagger audits — don't check all highways at once
  audit_interval = compute_interval(road.charge, road.traversal_count)
  // high charge highways audited more frequently
  // neutral highways can go longer between checks
  scheduler.add(AUDIT_HIGHWAY(road), interval=audit_interval)
```

---

## Part 3 — Special States

### 3.1 Ambivalence

Not an error. A genuine computational state.
Two roads of equal score, opposite charge, same context.

```
AMBIVALENCE_STATE:
  condition:     two candidate roads score within AMBIVALENCE_THRESHOLD
                 AND their charges have opposite signs
                 AND their context_match scores are similar

  behavior:      both roads fire simultaneously
                 working memory holds both slots
                 no resolution is forced
                 Evaluation Engine is notified
                 system can operate while holding both

  resolution:    time + new experience shifts context
                 one road eventually scores higher
                 ambivalence dissolves naturally
                 OR
                 explicit evaluation: Reasoning Engine asked
                 to examine both threads consciously
```

---

### 3.2 Nostalgia

A high-quality road that hasn't been used in a long time.
The node is easily reached. The emotion is tinged with distance.

```
NOSTALGIA_DETECTION:
  condition:     road.quality >= ROAD
                 AND time_since_traversal > NOSTALGIA_THRESHOLD
                 AND road.charge > 0

  behavior:      road is taken normally
                 charge fires at full strength
                 BUT a secondary signal fires: TEMPORAL_DISTANCE
                 the system knows this road hasn't been used in a long time
                 the joy is real but the distance is also real
                 both fire simultaneously
```

---

### 3.3 Triggered Memory

Current context accidentally activates a road to a node
not consciously sought.

```
TRIGGER_DETECTION:
  condition:     current_context has high similarity
                 to a road's formation_context
                 even though that node is not being
                 consciously traversed

  behavior:      road fires automatically
                 node enters working memory unbidden
                 charge and emotion fire at full strength
                 system experiences this as involuntary recall

  note:          this is how trauma intrusion works
                 and also how a song suddenly brings
                 back a forgotten memory.
                 same mechanism. different road quality and charge.
```

---

## Part 4 — Offline Consolidation

Runs during low-activity periods. The system's equivalent of sleep.

```
CONSOLIDATE():

  // 1. Strengthen frequently used roads from this session
  for road in session_roads:
    if road.traversal_count_today > CONSOLIDATION_THRESHOLD:
      road.quality = min(next_level(road.quality), HIGHWAY)

  // 2. Prune roads that have fully degraded
  for road in graph.all_roads():
    if road.quality == DIRT and
       time_since_traversal(road) > PRUNE_THRESHOLD:
      graph.remove_road(road)
      // NOTE: node is NEVER removed. only the road.
      // the information persists. only the easy path to it is gone.

  // 3. Compress episodic → semantic
  for node in graph.event_nodes():
    if similar_events_count(node) > COMPRESSION_THRESHOLD:
      abstract_node = compress(node, similar_nodes(node))
      semantic_layer.register(abstract_node)
      // individual episodes remain
      // abstracted pattern also now exists as new node

  // 4. Run decay on all negative charges
  DECAY_CHARGES()

  // 5. Audit a sample of highways
  for road in sample(highway_roads(), n=AUDIT_SAMPLE_SIZE):
    AUDIT_HIGHWAY(road)
```

---

## Part 5 — Summary

```
ONE GRAPH. ONE TRUTH PER NODE.

Nodes:          information — always neutral, never deleted
Roads:          connections — carry all emotion, quality, context
                one node can have unlimited roads
                each road = a different experiential thread

Road qualities: DIRT → GRAVEL → ROAD → HIGHWAY → (CLOSED)
                quality = how automatic, how fast, how costly
                HIGHWAY = procedural memory (unconscious)
                CLOSED = resisted but not forgotten (heals over time)

Working memory: active traversal budget
                highways are free
                dirt and closed roads are expensive
                eviction by context relevance

Charge:         lives on roads, not nodes
                negative charge decays automatically, guaranteed
                facts persist after charge fades
                lessons extracted to belief layer before charge reaches zero

Ambivalence:    two opposite roads firing simultaneously
                not an error — a genuine state
                resolves through time and new experience

Consolidation:  offline process
                strengthens used roads
                prunes unused dirt paths (not nodes — never nodes)
                compresses repeated episodes into abstract concepts
                audits highways against current beliefs
```

---

*Psyche Memory Hierarchy — Module 01*
*Status: Design complete. Ready for integration with Abstraction Engine (Module 02).*
