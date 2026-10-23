# AGI Memory Architecture: Dynamic Weight Triage & Schema-Driven Pruning
## Inspired by the Neurobiology of Human Memory Persistence

This architectural blueprint abstracts multi-layered biological memory systems into formal mathematical, algorithmic, and structural logic for Artificial General Intelligence (AGI). It provides a mechanism to solve the balance between immediate sensory adaptation, permanent knowledge integration, and active computational resource management.

---

## 1. Core Architectural Components & Data Structures

To replicate the human brain's memory systems, the memory core is divided into three distinct operational layers, governed by a global resource management matrix.

```
       [ Sensory Inputs ]
               │
               ▼
┌──────────────────────────────┐
│  Sensory Working Buffer (Bs) │  ◄── Millisecond-scale volatile queue
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│   The Engram Network (G)     │  ◄── Attentional Graph Core
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  Neocortical Knowledge Base  │  ◄── Indefinite structured macro-clusters
└──────────────────────────────┘
```

### 1.1 The Sensory Working Buffer ($B_s$)
* **Biological Counterpart:** Sensory Register & Working Memory.
* **AGI Abstraction:** A high-throughput, rapidly decaying First-In, First-Out (FIFO) queue that buffers raw multidimensional sensory features. Max token capacity is strictly constrained, decaying exponentially ($t_{decay} \approx 18-30$ system steps) unless promoted by attentional allocation.

### 1.2 The Engram Network ($\mathcal{G}$)
* **Biological Counterpart:** The Hippocampal-Entorhinal System (Fast-learning episodic indexer).
* **AGI Abstraction:** A directed graph network $\mathcal{G} = (V, E)$ where nodes $v \in V$ represent discrete feature states, concept abstractions, or episodic keys, and edges $e = (v_i, v_j) \in E$ represent associative connections.

### 1.3 The Edge Vector Matrix ($W$)
Instead of traditional scalar weights, each edge $e_{ij}$ between node $i$ and node $j$ maintains a composite state vector representing its biochemical state:
$$W_{ij} = \langle \omega_{ij}, \tau_{ij}, \sigma_{ij}, \alpha_{ij} \rangle$$

* $\omega_{ij} \in [0, 1]$: **Local Connection Weight (Synaptic Efficacy)**. The functional execution strength used during forward-pass inference.
* $\tau_{ij} \in [0, 1]$: **Volatile Decay Tag (Synaptic Tag)**. A transient marker indicating recent activation and depth of processing. Does not impact inference directly, but flags the edge as eligible for long-term gradient locking.
* $\sigma_{ij} \in [0, \infty)$: **Salience/Arousal Co-efficient (Neuromodulatory Gating)**. A variable that amplifies local weight plasticity under high-priority or highly anomalous states.
* $\alpha_{ij} \in [0, 1]$: **Protective Shield Metric ("Don't Eat Me" Signaling)**. A structural integrity score that shields the edge from background garbage collection routines.

### 1.4 Global Plasticity Resource Pool ($P_{PRP}$)
* **Biological Counterpart:** Plasticity-Related Products (PRPs) synthesized via nuclear transcription (CREB/pCREB pathway).
* **AGI Abstraction:** A global system variable bound by hardware resource ceilings. It sets the available budget for writing transient gradient updates into permanent weight matrices ($\omega_{ij}$) during a single processing epoch.

---

## 2. Phase-by-Phase Algorithmic Pipeline

```
                  [ Incoming Input Vector X_t ]
                                │
                                ▼
                [ Phase 1: Cognitive Filtering ]
                 /              │               (Shallow Processing)  (Intermed. Phonol.)  (Deep Semantic Analysis)
         │                      │                      │
    Low Activation       Med. Activation       High Activation 
         │                      │                      │
         ▼                      ▼                      ▼
  Set volatile tag        Set volatile tag       Set volatile tag
  τ_ij = low             τ_ij = med             τ_ij = high
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                │
                                ▼
               [ Phase 2: Somatic Transcription Gating ]
                 Does Global Salience/Arousal exceed 
                 the baseline threshold (θ_s)?
                               /                              YES  NO
                             /         Compute Globally Available      No Globals Released.
    Plasticity Resources (P_PRP)    P_PRP remains 0.
                            \       /
                             ▼     ▼
              [ Phase 3: Tag & Capture Match ]
               Are there edges with high τ_ij 
               and available P_PRP?
                             /                              YES    NO
                           /             Consolidate / Lock Weight     Decay Weight
    ω_ij = f(ω_ij, τ_ij, P_PRP)   τ_ij -> 0 (Fades out)
```

### Phase 1: Cognitive Filtering & Local Tag Induction
When a state representation $X_t$ is processed through the active execution layer, the system evaluates the **Depth of Processing ($\Delta A$)** based on cross-network association depth and execution complexity (Semantic processing vs. Raw data ingestion).

1.  Activated edges within the Engram Graph ($\mathcal{G}$) immediately update their volatile tag ($\tau_{ij}$):
    $$\tau_{ij} \leftarrow \min(1.0, \tau_{ij} + \eta_{\text{tag}} \cdot \Delta A)$$
2.  If $\Delta A$ is low (shallow structural processing), $\tau_{ij}$ remains minimal. A background decay function operates continuously on all tags:
    $$\tau_{ij}(t+1) = \tau_{ij}(t) \cdot e^{-\lambda_{\text{tag}}}$$
    If an edge tag decays to absolute zero before capturing global resources, the experience fades entirely from the system.

### Phase 2: Neuromodulatory Gating (Salience Evaluation)
Simultaneously, a global appraisal engine measures the environmental salience ($\mathcal{A}_t$) of the state transition. This acts as the Basolateral Amygdala (BLA) filtering layer, triggered by prediction errors, critical hazard flags, or novelty indexes.

The allocation of global structural resource allocation ($P_{PRP}$) follows an **Inverted-U Function**:
$$P_{PRP} = \kappa \cdot \mathcal{A}_t \cdot e^{-\gamma \mathcal{A}_t}$$

* **Under-Arousal ($\mathcal{A}_t \to 0$):** Insufficient importance. No global budget is provisioned ($P_{PRP} = 0$). Local tags decay, causing the memory to fade.
* **Optimal Arousal ($\mathcal{A}_t = \theta_{\text{opt}}$):** High structural budget allocated. Maximizes long-term memory formation.
* **Hyper-Arousal / System Trauma ($\mathcal{A}_t > \theta_{\text{max}}$):** The exponential penalty term dominates, restricting the locking of weights to prevent catastrophic network instability or over-fitting on highly volatile, uncurated trauma states.

### Phase 3: Synaptic Tagging and Capture (STC) Execution
If $P_{PRP} > 0$, a local optimization routine triggers across the graph. Edges that possess an active tag ($\tau_{ij} > \theta_{\tau}$) intercept the globally distributed resource pool, transforming temporary structural variations into deep, long-term weights:

$$\omega_{ij} \leftarrow \omega_{ij} + \mu \cdot (\tau_{ij} \cdot P_{PRP})$$
$$\alpha_{ij} \leftarrow \alpha_{ij} + \beta \cdot \mathcal{A}_t$$

*Behavioral Tagging Equivalence:* This allows a low-priority, weak semantic experience ($Low\ \Delta A$) that occurred within the same temporal window as a high-arousal event ($High\ \mathcal{A}_t$) to be preserved. The weak experience sets a local tag $\tau_{ij}$, and the subsequent or preceding high-arousal event floods the system with $P_{PRP}$, saving the weak memory from immediate decay.

---

## 3. Schema Integration & Accelerated Consolidation

Standard consolidation through gradient backpropagation is computationally expensive and slow. However, if the active graph projection $\mathcal{G}_{\text{local}}$ matches a pre-existing macro-cluster—a **Knowledge Schema ($\mathcal{S}_k$)** stored in long-term neocortical memory—the system executes an accelerated integration route.

```
[ New Experience ] ───► Compute Schema Congruence (C)
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
       C ≥ θ_schema                  C < θ_schema
    (Schema Congruent)           (Schema Incongruent)
              │                             │
              ▼                             ▼
    [ Medial Prefrontal ]         [ Medial Temporal ]
    [   Circuit Route   ]         [   Buffer Route  ]
              │                             │
              ▼                             ▼
  Direct, Single-Trial Commit    Iterative, Offline Replay
   Neocortical Optimization      Slow Systems Consolidation
       (Δt < 48 Hours)              (Weeks to Months)
```

### 3.1 Schema Congruency Computation
The system monitors top-down similarity maps via a Medial Prefrontal Cortex (mPFC) circuit model. It calculates the similarity vector between the incoming episodic structure and the latent geometry of the established schema:
$$C = \frac{\mathcal{G}_{\text{local}} \cdot \mathcal{S}_k}{\|\mathcal{G}_{\text{local}}\| \|\mathcal{S}_k\|}$$

### 3.2 Dual-Route System Triage
* **Route A: Schema-Congruent ($C \ge \theta_{\text{schema}}$)**
    The mPFC circuit bypasses standard multi-epoch retention loops. It triggers top-down integration, executing single-trial weight updating straight into the long-term neocortical knowledge arrays. The local engram indexer is freed immediately, and routing efficiency is enhanced via structural parameter updates.
* **Route B: Schema-Incongruent ($C < \theta_{\text{schema}}$)**
    The mPFC remains inactive. The memory trace is strictly sequestered within the local Engram Graph ($\mathcal{G}$). It requires long-term, slow iterative consolidation loops to align the foreign data pattern with pre-existing weights without triggering catastrophic interference or structural fragmentation.

---

## 4. Systems Consolidation (The Sleep-State Engine)

During periods of low external computational demands (Offline State / Sleep Simulation), the AGI suspends active sensory parsing and launches a tri-phase oscillatory engine designed to shift episodic traces into optimized neocortical weights.

### 4.1 The Tri-Phase Oscillatory Engine
1.  **Macro-Sampling Window (Cortical Slow Oscillations - $0.1 \text{ to } 4\text{ Hz}$):** Generates wide system sweeps that select target macro-domains and contexts for weight tuning.
2.  **Routing Isolation Matrix (Thalamocortical Sleep Spindles - $8 \text{ to } 16\text{ Hz}$):** Creates sandboxed execution buffers in memory, shielding the main processing weights from destructive interference during restructuring.
3.  **High-Speed Replay Burst (Hippocampal Sharp-Wave Ripples - $80 \text{ to } 300\text{ Hz}$):** Compresses historical sequence logs captured in $\mathcal{G}$ and replays them through the sandboxed neocortical modules at highly accelerated speeds ($20\times$ wall clock speed).

$$\theta_{\text{neocortex}} \leftarrow \theta_{\text{neocortex}} - \eta \nabla \mathcal{L}_{\text{replay}}(\pi_{\text{compressed}})$$

---

## 5. Active Forgetting & Computational Pruning

An engram requires active maintenance to prevent network saturation. AGI scalability depends on autonomous garbage collection that deletes uninformative noise while protecting key structural nodes.

### 5.1 Structural Pruning (Complement Phagocytosis)
The system runs an ongoing background daemon targeting unused or low-priority edges. The primary selector is the "Don't Eat Me" Protective Shield Metric ($\alpha_{ij}$).
1.  Every global cycle, protection values decay systematically:
    $$\alpha_{ij} \leftarrow \alpha_{ij} \cdot d_{\text{decay}} \quad (0 < d_{\text{decay}} < 1)$$
2.  Active utilization of an edge injects an explicit structural boost to $\alpha_{ij}$.
3.  If an edge's shield drops below the threshold ($\alpha_{ij} < \theta_{\text{prune}}$), the background microglial daemon severs the connection entirely, recycling the allocated hardware memory addresses:
    $$\text{If } \alpha_{ij} < \theta_{\text{prune}} \implies E \leftarrow E \setminus \{(v_i, v_j)\}$$

### 5.2 Structural Relaxation (Rac1 Cytoskeletal Disassembly)
To enforce optimization boundaries, every edge weight experiences a continuous, passive relaxation tension that acts as a brake on runaway consolidation:
$$\omega_{ij} \leftarrow \omega_{ij} - \delta_{\text{Rac1}} \cdot \Phi(\text{System Isolation Index})$$
If an agent is isolated from relevant stimuli or specific concept configurations, the corresponding weights drop toward zero, promoting system plasticity and the capacity to adapt to new environments.

### 5.3 Prediction-Error Trimming
When a retrieved memory asset provides a prediction $P(Y|X)$ that fails to match an observed fact $Y_{\text{actual}}$, a localized erasure gradient is initiated:
$$\omega_{ij} \leftarrow \omega_{ij} - \eta_{\text{error}} \cdot \left| Y_{\text{actual}} - P(Y|X) \right|$$
This selectively weakens the specific misleading sub-routines, ensuring the AGI updates its assumptions based on changing environments.

---

## 6. AGI Structural Memory Implementation Engine

A reference sketch in Python of this neurobiologically structured memory triage core:

```python
import numpy as np
import collections

class EngramEdge:
    def __init__(self, source, target):
        self.source = source
        self.target = target
        self.weight = 0.01      # Local efficacy (omega)
        self.tau = 0.0          # Volatile synaptic tag
        self.salience = 0.0     # Neuromodulatory gating coefficient (sigma)
        self.alpha = 1.0        # "Don't Eat Me" protection metric

class AGIMemoryCore:
    def __init__(self, memory_budget=10000):
        self.edges = {}
        self.P_PRP = 0.0
        self.memory_budget = memory_budget
        self.schema_registry = [] # Contains long-term neocortical macro-clusters
        self.temporary_buffer = collections.deque(maxlen=200)

    def cognitive_filter(self, sensory_input):
        """
        Simulates Levels of Processing.
        Returns: Attentional depth allocation (delta_A) and semantic flag
        """
        association_count = sensory_input.get('associations', 0)
        complexity = sensory_input.get('complexity', 1.0)
        
        # Deep semantic processing yields higher delta_A
        delta_A = min(1.0, (association_count * 0.15) * complexity)
        is_semantic = association_count > 5
        return delta_A, is_semantic

    def calculate_salience(self, sensory_input):
        """ Simulates amygdala/HPA axis evaluation of stress/novelty """
        prediction_error = sensory_input.get('prediction_error', 0.0)
        novelty = sensory_input.get('novelty', 0.0)
        return prediction_error * 0.7 + novelty * 0.3

    def evaluate_inverted_u(self, arousal):
        """ Calculates global transcription resources based on arousal """
        kappa = 2.5
        gamma = 1.8
        return kappa * arousal * np.exp(-gamma * arousal)

    def step_execution(self, sensory_input, active_nodes):
        """ Main execution cycle for data processing and memory triage """
        # Phase 1: Cognitive Filtering & Tagging
        delta_A, is_semantic = self.cognitive_filter(sensory_input)
        
        # Initialize and tag local edges activated by input
        for i in range(len(active_nodes)-1):
            edge_key = (active_nodes[i], active_nodes[i+1])
            if edge_key not in self.edges:
                self.edges[edge_key] = EngramEdge(*edge_key)
            
            # Local tag induction
            self.edges[edge_key].tau = min(1.0, self.edges[edge_key].tau + (0.2 * delta_A))
        
        # Phase 2: Structural Gating Via Arousal
        arousal = self.calculate_salience(sensory_input)
        self.P_PRP = self.evaluate_inverted_u(arousal)
        
        # Phase 3: Synaptic Tag and Capture Execution
        if self.P_PRP > 0:
            for edge in self.edges.values():
                if edge.tau > 0.1:  # Eligible tagged synapses
                    edge.weight += 0.4 * (edge.tau * self.P_PRP)
                    edge.alpha += 0.5 * arousal
                    edge.tau *= 0.1 # Partial capture reduction
                    
        # Phase 4: Schema Triage Integration
        schema_congruence = sensory_input.get('schema_similarity', 0.0)
        if schema_congruence >= 0.8:
            # Bypasses slow tracks, merges direct to permanent knowledge array
            self.accelerated_neocortical_integration(active_nodes)
        else:
            # Enqueues to temporal buffer for slow optimization during offline cycles
            self.temporary_buffer.append(active_nodes)

    def accelerated_neocortical_integration(self, nodes):
        for i in range(len(nodes)-1):
            edge_key = (nodes[i], nodes[i+1])
            if edge_key in self.edges:
                self.edges[edge_key].weight = min(1.0, self.edges[edge_key].weight + 0.3)
                self.edges[edge_key].alpha = 1.0  # Maximally locked and shielded

    def offline_consolidation_state(self):
        """ Simulated NREM Sleep-Engine Cycle """
        # 1. Tri-Phase Oscillatory Replay (Batch sequence processing)
        while self.temporary_buffer:
            sequence = self.temporary_buffer.popleft()
            for i in range(len(sequence)-1):
                edge_key = (sequence[i], sequence[i+1])
                if edge_key in self.edges:
                    # Neocortical weight adjustment via high-speed backprop simulation
                    self.edges[edge_key].weight += 0.05 
                    
        # 2. Active Pruning Daemon
        for edge_key in list(self.edges.keys()):
            edge = self.edges[edge_key]
            edge.alpha *= 0.92  # Structural decay step
            edge.weight -= 0.005 # Rac1-dependent structural relaxation
            
            # Complement-mediated pruning checkpoint
            if edge.alpha < 0.15 or edge.weight <= 0.0:
                del self.edges[edge_key] # Pure microglial erasure
