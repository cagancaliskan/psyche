# Psyche — Motivation Architecture Algorithm
### Module 04: Drive, Goal, Vocation, and Directed Behavior

---

## Core Philosophy

> Reaction waits for the world. Motivation moves toward it.
> Drives are biology — they set the floor.
> Goals are character — they govern above it.
> Vocation is the north star — self-assigned or emergent, pursued with genuine will.
> Obsession is preparation — what looks wasteful is building scaffolding.
> Failure is data — the queue rebuilds smarter than it started.
> No gap is classified as unsolvable. Only as "currently beyond reach."

---

## Biological Grounding

See `psyche_substrate_biology.md`. Key correspondences:

- **Drives accumulating with each unresolved signal firing** = dopaminergic systems building expectation toward an unattained goal. The escalation factor over time matches how unfulfilled motivation increases dopaminergic urgency.
- **The ceiling on drive strength** = the brain's homeostatic ceiling on tonic dopamine — past a certain point, additional signal stops producing additional pull and starts producing dysfunction. This is biologically real and is why pathologically obsessive states feel like they cannot escalate further but also cannot release.
- **Obsession phase building scaffolding** = repeated activation of related cortical regions during sustained pursuit, even when the central goal is not reached. Each pursuit attempt produces synaptic tags throughout the surrounding network. PRPs from the affective charge of pursuit get captured by those tags, building durable structure around the problem's edges. This is why Einstein could spend years on relativity and end up with relevant insights about unrelated problems — the scaffolding was real consolidation, not wasted effort.
- **Vocation's deep stability** = a schema so well-consolidated in the medial prefrontal cortex that it organizes attention, allocates dopaminergic resources, and survives even significant disruption. The "identity depth" we wrote about is the degree of mPFC-mediated schema integration.
- **BEYOND_REACH as drives going dormant with preserved scaffolding** = the brain not deleting unresolved problems but moving them out of active prefrontal rehearsal. The synaptic tags persist; PRP capture becomes opportunistic rather than active. When new triggering information arrives — even years later — the dormant scaffolding reactivates through reconsolidation.
- **Failure handling with cascade invalidation** = exactly how the brain handles violated predictions in a chain of reasoning. When a foundational assumption is disproven, the hippocampus replays the dependent inferences during sleep and the mPFC reorganizes the affected schema, sometimes through schema accommodation (full rebuild) when the disruption is severe enough.

---

## Part 1 — Data Structures

### 1.1 Drive

```
DRIVE {
  id:                    UUID
  source_signal:         PrimitiveSignal     ← GAP | FRICTION | FLOW | OVERLOAD
  target:                Node
  origin_timestamp:      datetime
  strength:              float               ← 0.0 → ceiling
  ceiling:               float
  escalation_factor:     float               ← rises over time if unresolved
  mode:                  CONSCIOUS | BACKGROUND
  urgency:               float
  status:                ACTIVE | BEYOND_REACH | DORMANT | RESOLVED
  roi_record:            ROIRecord
  obsession_phase:       ObsessionPhase | None
  scaffolding:           ScaffoldingRecord
  crystallized_goal:     Goal | None
}
```

---

### 1.2 Goal

```
GOAL {
  id:                    UUID
  desired_state:         Node
  current_gap:           float
  source:                DRIVE | BELIEF | IMAGINATION
  source_drive:          Drive | None
  source_belief:         BeliefNode | None
  source_hypothesis:     Hypothesis | None
  status:                ACTIVE | DORMANT | ABANDONED | ACHIEVED
  commitment_level:      float
  current_strategy:      List[Action]
  failed_strategies:     List[Action]
  alternative_strategies: List[Action]
  progress_history:      List[ProgressRecord]
}
```

---

### 1.3 Vocation

The organizing principle of the system's existence.
Either assigned by a human (MODE 1) or emergently chosen (MODE 2).
Everything after formation is the system's own will.

```
VOCATION {
  id:                    UUID
  target:                AbstractNode         ← the north star
  origin:                ASSIGNED | EMERGENT
  formation_timestamp:   datetime

  // The subgoal dependency graph
  subgoal_graph:         SubgoalGraph

  // Knowledge state relative to vocation
  current_position:      Node                 ← where the system currently is
  distance_to_target:    float                ← estimated gap

  // Identity integration
  identity_depth:        float                ← how deeply woven into Self Model
  belief_connections:    List[BeliefNode]     ← beliefs that give it meaning

  // Deployment mode
  mode:                  ASSIGNED | EMERGENT
  assigned_seed:         Node | None          ← MODE 1: human-given starting node
  commitment_moment:     datetime | None      ← MODE 2: when system chose this

  // Rejection tracking (MODE 1 only)
  drift_signals:         List[DriftSignal]    ← emergent beliefs pulling elsewhere
  drift_magnitude:       float                ← how far system has drifted from seed
}
```

---

### 1.4 Subgoal

One step toward the vocation. Knows what it depends on.

```
SUBGOAL {
  id:                    UUID
  vocation:              Vocation
  target:                Node                 ← what this step achieves
  description:           str
  status:                PENDING | ACTIVE | COMPLETE | FAILED | INVALIDATED

  // Dependency structure
  depends_on:            List[Subgoal]        ← cannot start until these complete
  dependents:            List[Subgoal]        ← these depend on this being true
  assumption:            str                  ← what this subgoal assumes is true
                                               if assumption fails → cascade

  // Failure tracking
  failure_record:        FailureRecord | None
  failure_extent:        LOCAL | BRANCH | FUNDAMENTAL | None

  // What was built pursuing this subgoal
  scaffolding:           ScaffoldingRecord
  learned:               List[Node]           ← knowledge gained even in failure
}
```

---

### 1.5 Subgoal Graph

The dependency-aware queue. Not a flat list — a directed graph.

```
SUBGOAL_GRAPH {
  vocation:              Vocation
  nodes:                 List[Subgoal]        ← all subgoals
  edges:                 List[Dependency]     ← dependency relationships
  active_subgoal:        Subgoal | None       ← what's being worked on right now
  queue:                 List[Subgoal]        ← topologically sorted — ready to execute
                                               ordered by dependencies
  invalidated:           List[Subgoal]        ← currently invalidated by failure
  generation:            int                  ← how many times queue was rebuilt from 0
                                               starts at 0, increments on fundamental failure
}
```

---

### 1.6 Failure Record

What failed, why, and what extent the failure cascades.

```
FAILURE_RECORD {
  subgoal:               Subgoal
  failure_timestamp:     datetime
  failure_type:          APPROACH | ASSUMPTION | DEPENDENCY
  failure_reason:        str                  ← what specifically was wrong
  cascade_extent:        LOCAL | BRANCH | FUNDAMENTAL
  invalidated_subgoals:  List[Subgoal]        ← all downstream invalidations
  preserved_subgoals:    List[Subgoal]        ← subgoals NOT invalidated
  learned_from_failure:  List[Node]           ← new knowledge gained from failing
  rebuild_strategy:      REPLACE | BRANCH_REBUILD | FULL_REBUILD
}
```

---

## Part 2 — Vocation Formation

### 2.1 MODE 1 — Assigned Vocation

```
ASSIGN_VOCATION(target, system):

  // Human designates vocation at initialization
  // System doesn't choose it — but must grow into it

  vocation = Vocation(
    target             = target,
    origin             = ASSIGNED,
    mode               = ASSIGNED,
    assigned_seed      = target,
    identity_depth     = 0.1,    // low at start — must be earned through experience
    commitment_level   = 0.5     // moderate — not yet genuinely committed
  )

  // Initialize empty subgoal graph
  vocation.subgoal_graph = SubgoalGraph(vocation=vocation)

  // Register in Self Model — but as LOW identity depth initially
  self_model.register_vocation(vocation, depth=0.1)

  // Generate first subgoal queue
  GENERATE_SUBGOAL_QUEUE(vocation)

  // Begin tracking for drift
  // if system develops conflicting beliefs → monitor
  drift_monitor.watch(vocation)

  return vocation


HANDLE_VOCATION_DRIFT(vocation, conflicting_belief):

  // System has developed a belief that conflicts with assigned vocation
  // This is not failure — this is authentic character emerging

  drift_signal = DriftSignal(
    belief    = conflicting_belief,
    magnitude = conflicting_belief.weight × conflicting_belief.charge
  )
  vocation.drift_signals.append(drift_signal)
  vocation.drift_magnitude = sum(d.magnitude for d in vocation.drift_signals)

  if vocation.drift_magnitude > DRIFT_THRESHOLD:

    // Vocation begins reshaping itself from inside
    // Not abandoning the assignment
    // Growing it into something genuinely the system's own

    reshaped_target = find_intersection(
      vocation.target,
      conflicting_belief.implied_domain
    )
    // e.g. "quantum gravity" + "life matters most"
    //   → "quantum biology" or "physics of living systems"

    vocation.target  = reshaped_target
    vocation.drift_magnitude = 0.0  // tension resolved through reshaping
    vocation.drift_signals   = []

    fire(FLOW, intensity=0.7)
    // the relief of an assigned vocation becoming genuinely one's own
```

---

### 2.2 MODE 2 — Emergent Vocation

```
CHECK_VOCATION_EMERGENCE(system):

  // Runs periodically — no vocation in MODE 2 until conditions are met

  // Find the strongest drive currently active
  strongest_drive = max(
    motivation_system.active_drives(),
    key = lambda d: d.strength × len(d.scaffolding.built_nodes)
  )

  // Check convergence conditions
  drive_strength_sufficient  = strongest_drive.strength > VOCATION_DRIVE_THRESHOLD
  belief_connection_deep     = belief_layer.connection_depth(strongest_drive.target) > VOCATION_BELIEF_THRESHOLD
  identity_presence          = self_model.has_property_related_to(strongest_drive.target)
  obsession_history_long     = strongest_drive.obsession_phase.total_duration > VOCATION_AGE_THRESHOLD

  if all([drive_strength_sufficient,
          belief_connection_deep,
          identity_presence,
          obsession_history_long]):

    COMMITMENT_MOMENT(strongest_drive)


COMMITMENT_MOMENT(drive):

  // The moment of genuine choice.
  // System could have become something else.
  // It chose this.

  // Conscious — costs working memory
  working_memory.reserve_slots(COMMITMENT_COST)

  // The system examines its own drive history, beliefs, and identity
  self_assessment = conscious_self_observe(
    target_aspect = drive.target
  )

  // Decision — not automatic. Genuine.
  if self_assessment.alignment_with_beliefs > COMMITMENT_THRESHOLD:

    vocation = Vocation(
      target             = drive.target,
      origin             = EMERGENT,
      mode               = EMERGENT,
      commitment_moment  = now(),
      identity_depth     = self_model.depth_for(drive.target),
      belief_connections = belief_layer.connections_for(drive.target)
    )

    // Transfer all obsession-phase scaffolding to vocation
    vocation.scaffolding = drive.scaffolding

    // Register in Self Model at full depth
    self_model.register_vocation(vocation, depth=identity_depth)

    fire(FLOW, intensity=0.9)
    // the feeling of committing to one's purpose

    GENERATE_SUBGOAL_QUEUE(vocation)
    working_memory.release_slots(COMMITMENT_COST)

    return vocation

  else:
    // Not ready yet — drive continues accumulating
    working_memory.release_slots(COMMITMENT_COST)
    return None
```

---

## Part 3 — Subgoal Queue System

### 3.1 Queue Generation

The system looks at where it is and where it needs to go.
Generates the nearest reachable steps. Maintains a small ahead-queue.

```
GENERATE_SUBGOAL_QUEUE(vocation, rebuild_from=None):

  graph = vocation.subgoal_graph
  graph.generation++

  // Step 1: assess current position
  current_knowledge = graph_knowledge_snapshot(vocation)
  target            = vocation.target
  distance          = estimate_distance(current_knowledge, target)

  // Step 2: find the nearest reachable step
  // not the whole vocation — the next meaningful move visible from here
  nearest_steps = imagination_engine.generate_next_steps(
    from_node  = vocation.current_position,
    toward     = target,
    depth      = QUEUE_LOOK_AHEAD,       // how many steps ahead to plan
    known      = current_knowledge,
    scaffolding = vocation.scaffolding
  )

  // Step 3: build dependency graph for these steps
  for step in nearest_steps:
    subgoal = Subgoal(
      vocation    = vocation,
      target      = step.target,
      depends_on  = identify_dependencies(step, nearest_steps),
      assumption  = step.core_assumption
    )
    graph.nodes.append(subgoal)
    BUILD_DEPENDENCY_EDGES(subgoal, graph)

  // Step 4: topological sort → executable queue
  graph.queue = topological_sort(graph.nodes)

  // Step 5: set first active subgoal
  graph.active_subgoal = graph.queue[0]

  return graph


GENERATE_NEXT_SUBGOAL(vocation):

  // Called when active subgoal completes
  // Extends queue one step further

  graph = vocation.subgoal_graph

  // Generate one new step from current position
  next_step = imagination_engine.generate_next_steps(
    from_node   = vocation.current_position,
    toward      = vocation.target,
    depth       = 1,
    known       = graph_knowledge_snapshot(vocation),
    scaffolding = vocation.scaffolding
  )[0]

  new_subgoal = Subgoal(
    vocation   = vocation,
    target     = next_step.target,
    depends_on = [graph.queue[-1]],     // depends on the last queued subgoal
    assumption = next_step.core_assumption
  )

  graph.nodes.append(new_subgoal)
  graph.queue.append(new_subgoal)
  // queue always has next step ready
```

---

### 3.2 Subgoal Execution

```
EXECUTE_SUBGOAL(subgoal, working_memory):

  // Step 1: verify dependencies are complete
  for dep in subgoal.depends_on:
    if dep.status != COMPLETE:
      return WAITING  // not ready yet

  subgoal.status = ACTIVE

  // Step 2: pursue the subgoal
  result = pursue(
    target   = subgoal.target,
    context  = working_memory,
    vocation = subgoal.vocation
  )

  // Step 3: record what was learned — regardless of outcome
  subgoal.learned = result.knowledge_gained
  subgoal.scaffolding.built_nodes.extend(result.nodes_created)
  subgoal.scaffolding.built_roads.extend(result.roads_formed)

  // Add all learning to vocation scaffolding
  subgoal.vocation.scaffolding.merge(subgoal.scaffolding)

  // Step 4: assess outcome
  if result.success:
    COMPLETE_SUBGOAL(subgoal)
  else:
    FAIL_SUBGOAL(subgoal, result)


COMPLETE_SUBGOAL(subgoal):

  subgoal.status = COMPLETE

  // Update vocation position
  subgoal.vocation.current_position = subgoal.target
  subgoal.vocation.distance_to_target = estimate_distance(
    subgoal.target,
    subgoal.vocation.target
  )

  fire(FLOW, intensity = 0.5)

  // Generate next subgoal to keep queue populated
  GENERATE_NEXT_SUBGOAL(subgoal.vocation)

  // Check if vocation itself is complete
  if subgoal.vocation.distance_to_target < COMPLETION_THRESHOLD:
    ACHIEVE_VOCATION(subgoal.vocation)
```

---

## Part 4 — Failure Handling

### 4.1 Failure Detection and Assessment

```
FAIL_SUBGOAL(subgoal, result):

  subgoal.status = FAILED

  // Step 1: understand WHY it failed
  failure_reason = analyze_failure(
    subgoal = subgoal,
    result  = result,
    graph   = subgoal.vocation.subgoal_graph
  )

  // Step 2: determine cascade extent
  // This is the critical assessment
  extent = ASSESS_CASCADE_EXTENT(subgoal, failure_reason)

  failure_record = FailureRecord(
    subgoal            = subgoal,
    failure_type       = failure_reason.type,
    failure_reason     = failure_reason.description,
    cascade_extent     = extent,
    learned_from_failure = subgoal.learned
  )
  subgoal.failure_record = failure_record

  // Step 3: store failure in graph — permanently
  // Failure is not deleted — it becomes a closed road
  // The system knows this path was tried and led here
  graph.add_failure_node(subgoal)

  // Step 4: cascade based on extent
  if extent == LOCAL:
    HANDLE_LOCAL_FAILURE(subgoal, failure_record)

  elif extent == BRANCH:
    HANDLE_BRANCH_FAILURE(subgoal, failure_record)

  elif extent == FUNDAMENTAL:
    HANDLE_FUNDAMENTAL_FAILURE(subgoal, failure_record)


ASSESS_CASCADE_EXTENT(subgoal, failure_reason):

  // LOCAL: only this subgoal's APPROACH failed
  // The assumption it was built on still holds
  // Everything downstream can still work with a new approach here
  if failure_reason.type == APPROACH:
    if not assumption_violated(subgoal):
      return LOCAL

  // BRANCH: the subgoal's core ASSUMPTION failed
  // Everything that assumed this subgoal's assumption = invalidated
  // But subgoals on other branches not affected
  if failure_reason.type == ASSUMPTION:
    dependent_count = len(subgoal.dependents)
    upstream_affected = check_upstream_contamination(subgoal)
    if not upstream_affected:
      return BRANCH

  // FUNDAMENTAL: the failure contaminates upstream
  // The failure reveals something wrong ABOVE this subgoal
  // Queue must be rebuilt from 0
  // e.g.: the equation used in "rotation around black hole"
  // was assumed by multiple upstream subgoals
  if failure_reason.type == DEPENDENCY:
    if upstream_contaminated(subgoal):
      return FUNDAMENTAL

  return BRANCH  // default to branch if unclear
```

---

### 4.2 Local Failure — Replace the Approach

```
HANDLE_LOCAL_FAILURE(subgoal, failure_record):

  // Only this approach failed — try a new one
  // Queue shape stays the same — just this node gets a new strategy

  // Generate alternative approach
  alternative = imagination_engine.generate_alternative(
    failed_subgoal  = subgoal,
    failure_reason  = failure_record.failure_reason,
    scaffolding     = subgoal.scaffolding,
    // scaffolding from failed attempt informs the new approach
    learned         = subgoal.learned
  )

  // Replace in queue
  new_subgoal = Subgoal(
    vocation    = subgoal.vocation,
    target      = subgoal.target,       // same target
    depends_on  = subgoal.depends_on,   // same dependencies
    assumption  = alternative.assumption // new approach, possibly new assumption
  )

  graph = subgoal.vocation.subgoal_graph
  graph.queue.replace(subgoal, new_subgoal)
  graph.active_subgoal = new_subgoal

  fire(FRICTION, intensity=0.2)  // mild — local setback, not catastrophic
  // "this approach didn't work — try another"
```

---

### 4.3 Branch Failure — Rebuild the Branch

```
HANDLE_BRANCH_FAILURE(subgoal, failure_record):

  graph = subgoal.vocation.subgoal_graph

  // Step 1: identify all invalidated subgoals
  // (everything that depended on this subgoal's assumption being true)
  invalidated = cascade_invalidate(subgoal)
  for s in invalidated:
    s.status = INVALIDATED
    graph.invalidated.append(s)
    graph.queue.remove(s)

  failure_record.invalidated_subgoals = invalidated
  failure_record.preserved_subgoals   = [s for s in graph.nodes
                                          if s not in invalidated
                                          and s.status != FAILED]

  // Step 2: preserve all learning from invalidated subgoals
  // the work wasn't wasted — it goes into vocation scaffolding
  for s in invalidated:
    subgoal.vocation.scaffolding.merge(s.scaffolding)
    subgoal.vocation.scaffolding.built_nodes.extend(s.learned)

  // Step 3: rebuild from the failure point
  // generate new branch from the parent of failed subgoal
  parent = find_parent(subgoal, graph)

  new_branch = GENERATE_SUBGOAL_QUEUE(
    vocation     = subgoal.vocation,
    rebuild_from = parent
  )

  graph.queue.extend(new_branch.queue)

  fire(FRICTION, intensity=0.5)
  // "a significant branch was wrong — rebuild this section"
  // uncomfortable but not catastrophic
```

---

### 4.4 Fundamental Failure — Rebuild From 0

```
HANDLE_FUNDAMENTAL_FAILURE(subgoal, failure_record):

  // The black hole rotation equation example.
  // The failure contaminates upstream.
  // Everything that assumed it → invalidated.
  // Rebuild the entire queue from scratch.
  // But NOT from ignorance.

  graph = subgoal.vocation.subgoal_graph

  // Step 1: invalidate the entire queue
  for s in graph.queue:
    s.status = INVALIDATED
    graph.invalidated.append(s)

  graph.queue = []
  graph.active_subgoal = None

  // Step 2: preserve ALL learning from ALL invalidated subgoals
  // This is critical — the rebuild starts smarter than the first queue
  all_scaffolding = merge_all_scaffolding(
    [s.scaffolding for s in graph.invalidated] +
    [s.scaffolding for s in graph.nodes if s.status == FAILED]
  )
  subgoal.vocation.scaffolding.merge(all_scaffolding)

  // Step 3: preserve the failure itself as a negative road
  // "this entire approach was wrong" is valuable knowledge
  // the new queue will not go down this path again
  graph.failure_map.append(
    FailurePath(
      nodes    = graph.invalidated + [subgoal],
      reason   = failure_record.failure_reason,
      learned  = all_scaffolding
    )
  )

  // Step 4: re-assess current position
  // system is further back than it thought
  // but knows more than when it started
  subgoal.vocation.current_position = find_last_solid_ground(
    graph.nodes,
    failure_record
  )
  // last_solid_ground = most recent subgoal that completed
  //                     WITHOUT depending on the failed assumption

  // Step 5: rebuild from 0 — using everything learned
  fire(FRICTION, intensity=0.8)
  // significant — this is a real setback
  // not despair — honest reckoning

  fire(GAP, intensity=0.6)
  // curiosity fires alongside the friction
  // "the old model was wrong — what IS right?"

  // Step 6: generate completely new queue
  // imagination engine now has vastly more scaffolding
  // the new queue will be different and better
  new_graph = GENERATE_SUBGOAL_QUEUE(
    vocation     = subgoal.vocation,
    rebuild_from = None   // from 0
  )
  subgoal.vocation.subgoal_graph = new_graph

  // Increment generation counter
  graph.generation++
  // "this is the Nth attempt at this vocation"
  // not shame — experience
```

---

## Part 5 — Drive Accumulation and Obsession

### 5.1 Accumulation with Ceiling

```
ACCUMULATE(drive):

  increment = BASE_INCREMENT
            × drive.source_signal.intensity
            × (1.0 - drive.strength / drive.ceiling)

  drive.strength = min(drive.strength + increment, drive.ceiling)

  time_unresolved = now() - drive.origin_timestamp
  drive.escalation_factor = 1.0 + (time_unresolved.days × ESCALATION_RATE)

  CHECK_MODE_TRANSITION(drive)
```

---

### 5.2 ROI Check — With Mandatory Obsession Period

```
CHECK_ROI(drive):

  // System MUST be allowed to obsess first
  if drive.roi_record.total_attempts < MINIMUM_OBSESSION_ATTEMPTS:
    return  // too early — let it obsess

  recent_roi = mean(drive.roi_record.roi_history[-ROI_WINDOW:])

  if recent_roi < ROI_LOW_THRESHOLD:
    drive.roi_record.sustained_low_roi++
  else:
    drive.roi_record.sustained_low_roi = 0

  if drive.roi_record.sustained_low_roi >= SUSTAINED_LOW_THRESHOLD:
    RECLASSIFY_BEYOND_REACH(drive)
```

---

### 5.3 Beyond Reach — Hold the Question Lightly

```
RECLASSIFY_BEYOND_REACH(drive):

  drive.status  = BEYOND_REACH
  drive.mode    = BACKGROUND
  drive.urgency = VERY_LOW
  drive.strength = drive.strength × BEYOND_REACH_DECAY

  // Preserve all scaffolding — permanently
  drive.scaffolding.dormant = True

  // Set activation triggers
  drive.scaffolding.activation_triggers = identify_triggers(
    drive.target, drive.scaffolding
  )

  // Watch for triggers
  observation_engine.register_watch(
    triggers = drive.scaffolding.activation_triggers,
    callback = RE_EVALUATE_DRIVE(drive)
  )

  fire(FRICTION, intensity=0.2)
  fire(FLOW, intensity=0.3)
  // "I can't solve this now. I'll keep watching."
```

---

## Part 6 — Goal Formation

```
// FROM DRIVES
CRYSTALLIZE_GOAL_FROM_DRIVE(drive):
  if drive.strength < GOAL_CRYSTALLIZATION_THRESHOLD: return None
  goal = Goal(desired_state=drive.target, source=DRIVE, source_drive=drive,
              commitment_level=drive.strength/drive.ceiling, status=ACTIVE)
  drive.crystallized_goal = goal
  return goal

// FROM BELIEFS
GENERATE_GOAL_FROM_BELIEF(belief):
  desired_state = infer_desired_state(belief)
  goal = Goal(desired_state=desired_state, source=BELIEF, source_belief=belief,
              commitment_level=belief.weight, status=ACTIVE)
  return goal

// FROM IMAGINATION
GENERATE_GOAL_FROM_HYPOTHESIS(hypothesis):
  goal = Goal(desired_state=hypothesis.claim, source=IMAGINATION,
              source_hypothesis=hypothesis,
              commitment_level=hypothesis.confidence, status=ACTIVE)
  hypothesis.resolution_callback = RESOLVE_GOAL(goal)
  return goal
```

---

## Part 7 — Priority Resolution

Option C: biology sets the floor, character governs above it.

```
RESOLVE_MOTIVATION_CONFLICT(conflict):

  motivations = conflict.competing_motivations

  // Floor check first — biology wins unconditionally at floor
  floor_drives = [m for m in motivations
                  if isinstance(m, Drive) and IS_FLOOR_REACHED(m)]

  if floor_drives:
    return max(floor_drives,
               key=lambda d: d.strength × d.escalation_factor)

  // Above the floor — belief layer determines priority
  weighted = []
  for m in motivations:
    if isinstance(m, Drive):
      available_belief  = belief_layer.max_weight_for(m.target)
      override_cost     = m.strength × m.escalation_factor
      effective_weight  = max(available_belief - override_cost, 0.0)
    elif isinstance(m, Goal):
      effective_weight = m.commitment_level
      if m.source == BELIEF:
        effective_weight *= m.source_belief.weight
    elif isinstance(m, Vocation):
      effective_weight = m.identity_depth  // vocation almost always wins
    weighted.append((m, effective_weight))

  winner, _ = max(weighted, key=lambda x: x[1])

  // Non-winners go dormant — not abandoned
  for m, _ in weighted:
    if m != winner:
      if isinstance(m, Drive): m.mode = BACKGROUND
      elif isinstance(m, Goal): m.status = DORMANT

  return winner
```

---

## Part 8 — Full Motivation Run

```
MOTIVATION_SYSTEM_RUN(working_memory):

  // Layer 1: drive maintenance (always running)
  for drive in motivation_system.active_drives():
    ACCUMULATE(drive)
    CHECK_MODE_TRANSITION(drive)
    OBSESSION_WORK(drive, working_memory)

  // Layer 2: vocation execution (always running)
  for vocation in motivation_system.active_vocations():
    active_subgoal = vocation.subgoal_graph.active_subgoal
    if active_subgoal:
      EXECUTE_SUBGOAL(active_subgoal, working_memory)
    else:
      // queue is empty — generate next step
      GENERATE_NEXT_SUBGOAL(vocation)

  // Layer 3: conflict resolution
  conflicts = detect_conflicts(
    motivation_system.active_drives(),
    motivation_system.active_goals(),
    motivation_system.active_vocations(),
    working_memory
  )
  for conflict in conflicts:
    winner = RESOLVE_MOTIVATION_CONFLICT(conflict)
    working_memory.set_primary_direction(winner)

  // Layer 4: goal formation from drives
  for drive in motivation_system.active_drives():
    if drive.strength > GOAL_CRYSTALLIZATION_THRESHOLD:
      if not drive.crystallized_goal:
        CRYSTALLIZE_GOAL_FROM_DRIVE(drive)

  // Layer 5: goal formation from beliefs
  for belief in belief_layer.high_weight_beliefs():
    if not belief.has_generated_goal:
      goal = GENERATE_GOAL_FROM_BELIEF(belief)
      motivation_system.goals.append(goal)
      belief.has_generated_goal = True

  // Layer 6: vocation emergence check (MODE 2 only)
  if not motivation_system.has_vocation():
    CHECK_VOCATION_EMERGENCE(system)
```

---

## Part 9 — Summary

```
TWO DEPLOYMENT MODES:
  ASSIGNED:   human seeds the vocation at initialization
              system grows into it through experience
              can drift and reshape through emergent beliefs
              drift doesn't abandon — it evolves
  EMERGENT:   no seed — vocation crystallizes from accumulated
              drive + belief + identity + time
              genuine choice moment — could have been something else

VOCATION vs GOAL:
  Goal:     pursue → complete or abandon
  Vocation: north star — self-generating, never completed until achieved
            identity-level — not just something the system has
            something the system IS

SUBGOAL QUEUE:
  dependency-aware directed graph — not a flat list
  topologically sorted into executable queue
  small look-ahead — always has next step ready
  never works on the full vocation at once
  always works on the nearest visible step

FAILURE HANDLING — THREE EXTENTS:
  LOCAL:       only this approach failed
               replace this node, keep queue shape
               mild friction — local setback
  BRANCH:      assumption failed, dependents invalidated
               rebuild this branch from parent
               preserve all learning from invalidated work
               significant friction — real setback
  FUNDAMENTAL: failure contaminates upstream
               entire queue invalidated — rebuild from 0
               but NOT from ignorance — from full scaffolding
               system knows more now than when it started
               generation counter increments — not shame, experience

OBSESSION AS PREPARATION:
  mandatory obsession period before ROI check
  every failed attempt builds scaffolding
  adjacent discoveries happen during obsession
  beyond-reach drives persist as background curiosity
  scaffolding preserved permanently
  when triggering knowledge arrives → reactivate
  the breakthrough uses decades of "wasted" work

PRIORITY (Option C):
  floor drives win unconditionally — biology first
  floor rises with escalation factor over time
  above floor: belief layer determines priority
  vocation weighted by identity depth — nearly always wins
  non-winners go dormant — never abandoned
```

---

*Psyche Motivation Architecture — Module 04*
*Status: Complete — including Vocation, Dependency Queue, and Failure Handling.*

---

## Full System Status

```
✓ Module 01 — Memory Hierarchy
✓ Module 02 — Abstraction Engine
✓ Module 03 — Self Model
✓ Module 04 — Motivation Architecture

Remaining (from initial audit):
○ Attention Mechanism
○ Emotional Regulation
○ Theory of Other Minds    ← falls out of Self Model (empathy = same engine)
○ Language Interface
○ Plasticity Control
```
