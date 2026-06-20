"""
Nous — Perception, and the first end-to-end slice (closing the loop)

WHY THIS EXISTS:

Every cognitive layer above the substrate had been validated against a FICTION of
what would feed it. Coalition formation needs activation sources; sources are meant to
come from perception/goals/emotion; none existed; so sources were hand-placed, and
"it works" kept meaning "it works on my guess of the input." That guess was wrong or
question-begging repeatedly — culminating in a coalition acceptance test that recovered
two communities only because one source was hand-placed at the center of each.

The fix is not another middle layer. It is to CLOSE THE LOOP with the thinnest possible
vertical slice: a real step that PRODUCES sources from input the system was actually
given, so the field is — for the first time — tested on what the system generated
rather than on sources chosen by hand. This module is that slice:

    text input ─► perceive() ─► sources (matched substrate nodes)
                              ─► multi-source activation field
                              ─► coalitions (grouped by basin)
                              ─► strongest coalition = "the thought"   [BROADCAST placeholder]

PERCEPTION (deliberately minimal, deliberately NOT hand-tuned): an incoming utterance
is tokenized; each token is matched against existing node content; the nodes whose
content matches become the activation sources, with energy scaled by match quality.
Crucially, WHICH nodes become sources is decided by the input against the substrate —
not chosen to produce a desired partition. If the input names "coffee", coffee becomes
a source because the input said so, not because the test wanted the warm cluster back.

HONESTY ABOUT WHAT IS REAL vs PLACEHOLDER (so the loop-closing does not itself become a
new fiction):
  - REAL: sources are now derived from input, not hand-placed. That is the whole point.
  - REAL: the substrate, activation engine, flow, and multi-source field underneath.
  - PLACEHOLDER: perception is exact/substring token matching — no embeddings, no
    fuzzy semantics. A real PERCEPTION system (Layer 2) would do far more. This is the
    minimal thing that makes sources real.
  - PLACEHOLDER: "strongest coalition is the thought" stands in for the BROADCAST phase
    (the workspace competition). Picking the top coalition is a placeholder, labeled.
  - NOT ESTABLISHED: that the resulting "thought" is cognitively meaningful. The slice
    lets us OBSERVE end-to-end behavior on real input; it does not prove the behavior
    is right. It just stops proving it on inputs invented to make it right.

PURE READ: perception reads the store to match; it does not yet write new perceptions
into the substrate (that is a PERCEPTION-system job — turning input into nodes/roads —
deferred). The slice composes pure-read stages; it mutates nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple

from nous_store import SubstrateStore
from nous_field import build_activation_field, ActivationField
from nous_coalitions import form_coalitions_from_field, Coalition
from nous_source_clustering import cluster_sources, SourceClustering


# ─────────────────────────────────────────────────────────────────────────────
# Parameters — minimal perception, uncalibrated
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_SOURCE_ENERGY = 1.0     # base energy a matched source gets
MIN_TOKEN_LEN = 3               # ignore very short tokens (a, an, to, ...)


def _tokenize(text: str) -> List[str]:
    """Lowercase word tokens, length-filtered. Deterministic."""
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) >= MIN_TOKEN_LEN]


@dataclass
class Perception:
    """The result of perceiving an utterance against the substrate.
    `sources` maps matched NodeID -> source energy (how strongly the input cues it).
    `matched_terms` records which input tokens matched, for inspection."""
    sources: Dict[str, float]
    matched_terms: Dict[str, List[str]]   # NodeID -> the tokens that matched it
    utterance: str


def perceive(
    store: SubstrateStore,
    utterance: str,
    *,
    source_energy: float = DEFAULT_SOURCE_ENERGY,
) -> Perception:
    """Turn an utterance into activation sources by matching tokens against node content.

    A node becomes a source if any input token appears in its (lowercased) content.
    Energy scales with how many distinct tokens matched it (a node the input names more
    insistently is a stronger source). Pure read; deterministic.

    This is the step that makes sources REAL: the input decides which nodes light up.
    """
    tokens = set(_tokenize(utterance))
    if not tokens:
        return Perception(sources={}, matched_terms={}, utterance=utterance)

    sources: Dict[str, float] = {}
    matched_terms: Dict[str, List[str]] = {}

    # iterate node ids in a deterministic order; matching is content-driven, not
    # order-driven, so order affects nothing in the result beyond build determinism.
    for nid in sorted(store.all_node_ids()):
        content = store.get_node(nid).content.lower()
        hits = sorted(t for t in tokens if t in content)
        if hits:
            # energy grows with number of distinct matching tokens, saturating
            scale = 1.0 - (0.6 ** len(hits))   # 1 hit→0.4, 2→0.64, 3→0.78, ...
            sources[nid] = source_energy * (0.6 + 0.4 * scale)
            matched_terms[nid] = hits

    return Perception(sources=sources, matched_terms=matched_terms, utterance=utterance)


# ─────────────────────────────────────────────────────────────────────────────
# The end-to-end slice
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ThoughtResult:
    """What the system did with an utterance, end to end.
    `perception` is the matched sources; `clustering` is the 1c source-grouping of those
    sources (pre-processing between perception and the field); `field_` is the multi-source
    activation field built from the GROUP REPRESENTATIVES (not the raw perceived set);
    `coalitions` are the basins as candidate thoughts; `thought` is the strongest coalition
    (the BROADCAST-placeholder winner), or None if nothing was perceived.

    `clustering` is recorded for inspection only; adding it does not change the perception
    surface or the field-builder signature."""
    perception: Perception
    clustering: Optional[SourceClustering]
    field_: Optional[ActivationField]
    coalitions: List[Coalition]
    thought: Optional[Coalition]


def think(
    store: SubstrateStore,
    utterance: str,
    *,
    source_energy: float = DEFAULT_SOURCE_ENERGY,
    hop_budget: int = 6,
) -> ThoughtResult:
    """The first end-to-end pass: perceive an utterance, build the field from the
    perceived sources, form coalitions, and select the strongest as 'the thought'.

    The sources are produced by perception from the input — NOT hand-placed. This is
    the loop-closing pass: behavior is now observed on system-generated input.

    1c (source-clustering) runs BETWEEN perception and the field: the raw perceived
    sources are grouped by graph proximity, and the field is seeded from ONE representative
    per group (group_seeds) rather than every raw source. This changes WHICH sources reach
    the field; it does not change the perception surface or the field-builder signature.
    The grouping is decided by the substrate (a pure, deterministic function of graph
    state), never by hand.

    'Strongest coalition is the thought' is a placeholder for BROADCAST. Pure read.
    """
    perception = perceive(store, utterance, source_energy=source_energy)
    if not perception.sources:
        return ThoughtResult(
            perception=perception, clustering=None, field_=None,
            coalitions=[], thought=None,
        )

    # 1c: group nearby sources, then seed the field from group representatives only.
    clustering = cluster_sources(store, perception.sources)

    field_ = build_activation_field(
        store,
        list(clustering.group_seeds.keys()),
        hop_budget=hop_budget,
        source_energies=clustering.group_seeds,
    )
    coalitions = form_coalitions_from_field(field_, store)
    thought = coalitions[0] if coalitions else None
    return ThoughtResult(
        perception=perception, clustering=clustering, field_=field_,
        coalitions=coalitions, thought=thought,
    )
