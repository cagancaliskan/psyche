#!/usr/bin/env python3
"""
Build docs/outreach/slides/nous_slides.pptx (~12 slides) for the Nous prototype.

Hard rules honored here (same as the report):
  - Numbers are verbatim from docs/TEST_OUTPUT.txt: 130 passed across 56 test
    functions; per-suite 45 / 35 / 19 / 13 / 18.
  - Methodology-first framing. Nous is an engineering prototype AND a
    testing-methodology case study; never a mind, consciousness, AGI, or a
    validated cognitive model. Cognitive meaningfulness is not claimed.
  - Neuroscience is conceptual inspiration only.
  - REUSES existing rendered figures in docs/diagrams/rendered/. Invents no new
    charts and introduces no claim beyond docs/REPORT.md.
On-slide text is terse; the detail lives in python-pptx speaker notes.

Run with the venv that has python-pptx + Pillow:
    /tmp/nous_venv/bin/python build_slides.py
"""
import os
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.normpath(os.path.join(HERE, "..", "..", "diagrams", "rendered"))
OUT = os.path.join(HERE, "nous_slides.pptx")

# palette
INK = RGBColor(0x1A, 0x1A, 0x1A)
ACCENT = RGBColor(0x1F, 0x4E, 0x79)      # deep blue
PROVEN = RGBColor(0x2E, 0x7D, 0x32)      # green
WARN = RGBColor(0xC0, 0x39, 0x2B)        # red
GREY = RGBColor(0x55, 0x55, 0x55)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
SW, SH = 13.333, 7.5
BLANK = prs.slide_layouts[6]


def slide():
    return prs.slides.add_slide(BLANK)


def textbox(s, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    return tf


def setrun(p, text, size, bold=False, color=INK, italic=False, font="Calibri"):
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = color
    r.font.name = font
    return r


def title(s, text, color=INK):
    tf = textbox(s, 0.6, 0.35, SW - 1.2, 1.0)
    p = tf.paragraphs[0]
    setrun(p, text, 30, bold=True, color=color)
    # thin accent rule under title
    line = s.shapes.add_shape(1, Inches(0.62), Inches(1.28), Inches(SW - 1.24), Pt(2.2))
    line.fill.solid(); line.fill.fore_color.rgb = ACCENT
    line.line.fill.background()
    return tf


def takeaway(s, text, color=ACCENT, y=1.45):
    tf = textbox(s, 0.62, y, SW - 1.24, 0.85)
    p = tf.paragraphs[0]
    setrun(p, text, 16, bold=True, color=color, italic=True)
    return tf


def bullets(s, items, x=0.7, y=1.7, w=SW - 1.4, h=5.2, size=18, gap=10):
    tf = textbox(s, x, y, w, h)
    first = True
    for it in items:
        # it may be (text, color, bold) or plain str
        if isinstance(it, tuple):
            text, color, bold = it
        else:
            text, color, bold = it, INK, False
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_after = Pt(gap)
        p.line_spacing = 1.05
        setrun(p, "•  ", size, bold=True, color=ACCENT)
        setrun(p, text, size, bold=bold, color=color)
    return tf


def figure(s, name, area=(0.6, 2.35, SW - 1.2, 4.55)):
    """Place a rendered figure, fit-to-area preserving aspect, centered."""
    path = os.path.join(FIG, name)
    iw, ih = Image.open(path).size
    ar = iw / ih
    x, y, w, h = area
    width = w; height = w / ar
    if height > h:
        height = h; width = h * ar
    left = x + (w - width) / 2
    top = y + (h - height) / 2
    s.shapes.add_picture(path, Inches(left), Inches(top), Inches(width), Inches(height))


def footer(s, label):
    tf = textbox(s, 0.6, SH - 0.45, SW - 1.2, 0.4)
    p = tf.paragraphs[0]
    setrun(p, label, 9, color=GREY)


def notes(s, text):
    s.notes_slide.notes_text_frame.text = text


# ----------------------------------------------------------------------------
# Slide 1 - Title
# ----------------------------------------------------------------------------
s = slide()
band = s.shapes.add_shape(1, 0, Inches(2.55), prs.slide_width, Inches(2.4))
band.fill.solid(); band.fill.fore_color.rgb = ACCENT; band.line.fill.background()
tf = textbox(s, 0.8, 2.7, SW - 1.6, 1.0)
setrun(tf.paragraphs[0], "Nous", 54, bold=True, color=WHITE)
tf = textbox(s, 0.8, 3.75, SW - 1.6, 1.1)
setrun(tf.paragraphs[0],
       "A dependency-free memory-and-activation substrate, and a software-testing-methodology case study",
       20, color=WHITE)
tf = textbox(s, 0.8, 5.2, SW - 1.6, 0.6)
setrun(tf.paragraphs[0], "Cagan Caliskan", 18, bold=True, color=INK)
tf = textbox(s, 0.8, 5.8, SW - 1.6, 0.8)
setrun(tf.paragraphs[0],
       "An engineering prototype. Not a mind, a consciousness, an AGI, or a validated cognitive model.",
       13, italic=True, color=GREY)
notes(s,
      "One honest sentence: Nous is a small, dependency-free Python prototype of a graph memory and "
      "spreading-activation substrate, and equally a case study in how adversarial, property-based testing "
      "caught a sequence of real structural bugs. The talk is methodology-first. Everything cognitive on top "
      "of the substrate is exploratory and is labeled as such. Nothing here claims a mind, consciousness, AGI, "
      "or a validated cognitive model.")

# ----------------------------------------------------------------------------
# Slide 2 - What this is / is NOT
# ----------------------------------------------------------------------------
s = slide()
title(s, "What this is, and what it is not")
bullets(s, [
    ("IS: a small Python prototype of a graph memory and spreading-activation substrate, built test-first", PROVEN, True),
    ("IS: a case study in adversarial, property-based testing and loop-closure", PROVEN, True),
    ("IS NOT: a mind, a consciousness, or an AGI", WARN, True),
    ("IS NOT: a validated cognitive model; cognitive meaningfulness above the substrate is not claimed", WARN, True),
    ("Neuroscience here is conceptual inspiration only, never implemented or reproduced", GREY, False),
], y=1.75, size=19, gap=14)
footer(s, "Binding non-claims for the rest of the talk.")
notes(s,
      "These non-claims bind everything that follows. The proven part is mechanism: the substrate does exactly "
      "and only what it says, reproducibly. The exploratory part runs and is deterministic, but whether its "
      "output is cognitively meaningful is an open question, not a result. The neuroscience vocabulary "
      "(complementary learning systems, synaptic tagging, global workspace, LIDA) is framing inspiration; "
      "no biological result is implemented, reproduced, or validated.")

# ----------------------------------------------------------------------------
# Slide 3 - Four-layer architecture
# ----------------------------------------------------------------------------
s = slide()
title(s, "Four layers: two proven, two exploratory")
takeaway(s, "Two rigorously tested substrate layers, with two exploratory cognitive layers built on top.")
figure(s, "architecture_stack.png", area=(0.6, 2.35, SW - 1.2, 4.55))
footer(s, "Figure: architecture_stack.png")
notes(s,
      "Bottom up: (1) Substrate store, a graph of concept nodes and weighted roads with consolidation-inspired "
      "dynamics, lazy decay, and sticky closure. (2) Spreading activation, a deterministic engine recording "
      "per-edge flow, treating closed roads as leaky rather than inert. Layers 1 and 2 are PROVEN for "
      "determinism, integrity, and purity. (3) Multi-source field, assigning each node to its dominant source. "
      "(4) The perceive-then-think slice. Layers 3 and 4 are EXPLORATORY: they run and are deterministic, but "
      "their cognitive meaningfulness is not claimed.")

# ----------------------------------------------------------------------------
# Slide 4 - Pipeline
# ----------------------------------------------------------------------------
s = slide()
title(s, "The end-to-end slice")
takeaway(s, "perceive  ->  activate  ->  field  ->  coalitions  ->  one selected 'thought' (last step is a placeholder).")
figure(s, "pipeline.png", area=(0.6, 2.35, SW - 1.2, 4.55))
footer(s, "Figure: pipeline.png")
notes(s,
      "Input text is matched to nodes (exact/substring tokens, no embeddings), producing activation sources. "
      "The field runs the proven single-source spread once per source and assembles basins. Coalitions group "
      "co-activated nodes. The final step picks the single strongest coalition and calls it the 'thought'. "
      "That selection is an explicit PLACEHOLDER for a workspace-competition (broadcast) phase that does not "
      "yet exist. The pipeline is deterministic end-to-end; that is a mechanism property, not evidence of "
      "meaning.")

# ----------------------------------------------------------------------------
# Slide 5 - The thesis
# ----------------------------------------------------------------------------
s = slide()
title(s, "The thesis: adversarial and property-based testing, plus loop-closure")
bullets(s, [
    ("Build each layer test-first; write adversarial tests designed to break the claim, not confirm it", INK, False),
    ("Property-based checks: determinism across process hash seeds, read-purity, full-graph integrity", INK, False),
    ("Close the loop: feed each layer system-generated inputs instead of hand-chosen ones", INK, False),
    ("A 'structural bug' lives in the design's logic, not in a typo: it passes the happy path and fails adversarially", WARN, True),
], y=1.75, size=19, gap=16)
footer(s, "What 'structural bug' means.")
notes(s,
      "Happy-path tests confirm what you already believe. Adversarial tests are written to falsify the claim: "
      "re-run the same construction in fresh interpreters under different PYTHONHASHSEED values and demand "
      "byte-identical output; assert that reads never mutate state; scan the whole graph for index/adjacency "
      "drift after every mutation. Loop-closure means stop hand-feeding friendly inputs and let an earlier "
      "stage generate them. A structural bug is one in the logic of the design: it survives friendly inputs and "
      "only shows up under these pressures.")

# ----------------------------------------------------------------------------
# Slide 6 - Six findings
# ----------------------------------------------------------------------------
s = slide()
title(s, "Six structural findings")
takeaway(s, "One failure mode recurred: 'passes on a friendly input.' Each bug was caught adversarially or by loop-closure.")
figure(s, "six_findings.png", area=(0.6, 2.35, SW - 1.2, 4.55))
footer(s, "Figure: six_findings.png")
notes(s,
      "(a) Read-as-write: a lazy decay path that mutated on read. (b) Convergence double-counting: Dijkstra's "
      "'first pop is final' imported into an engine that SUMS flow. (c) Order-dependence and nondeterminism: a "
      "priority frontier over hash-randomized sets. (d) Identity/order leak: uuid4 tie-breaks regenerated per "
      "process. (e) Binding degeneracy: connected-components always yields exactly one coalition. (f) Circular "
      "validation: sources hand-placed one per community, so the test could not fail. The common thread is the "
      "'friendly input' failure mode.")

# ----------------------------------------------------------------------------
# Slide 7 - Deep example: convergence double-counting
# ----------------------------------------------------------------------------
s = slide()
title(s, "Deep example: convergence double-counting")
takeaway(s, "Dijkstra's 'first pop is final' is wrong for an engine that SUMS flow at convergence points.")
figure(s, "convergence_before_after.png", area=(0.6, 2.35, SW - 1.2, 4.55))
footer(s, "Figure: convergence_before_after.png")
notes(s,
      "Shortest-path intuition says the first time you pop a node you are done. But spreading activation adds "
      "contributions from every incoming path, so reusing that intuition counts converging flow more than once. "
      "The fix is a bounded, hop-layered single-expansion with per-layer frozen values, which is both correct "
      "and deterministic. This is a mechanism correction, asserted by a no-double-count test.")

# ----------------------------------------------------------------------------
# Slide 8 - Deep example: determinism
# ----------------------------------------------------------------------------
s = slide()
title(s, "Deep example: determinism across process hash seeds")
takeaway(s, "Same construction, fresh interpreters, several hash seeds: byte-identical output. Mechanism, not cognition.", color=PROVEN)
figure(s, "determinism_seeds.png", area=(0.6, 2.35, SW - 1.2, 4.55))
footer(s, "Figure: determinism_seeds.png")
notes(s,
      "Natural implementations leak set-iteration order over uuid4 keys into results, so output varies across "
      "process runs. Four determinism tests re-run the same construction in fresh interpreters under several "
      "PYTHONHASHSEED values and assert byte-identical output (activation {0,1,3,7,42}; coalitions and field "
      "{0,1,2,3,7,42,123,999}; slice {0,1,2,7,42,999}). The 'before' row is the documented prior behavior shown "
      "qualitatively, not re-measured. This establishes reproducibility of MECHANISM only. It says nothing "
      "about cognition.")

# ----------------------------------------------------------------------------
# Slide 9 - The reframe: single-seed -> multi-source
# ----------------------------------------------------------------------------
s = slide()
title(s, "The reframe: single-seed degeneracy to multi-source")
takeaway(s, "One seed always collapses to one blob; multiple sources give structure. Caveat: here the sources were hand-placed (finding f).")
figure(s, "single_seed_vs_multisource.png", area=(0.6, 2.35, SW - 1.2, 4.55))
footer(s, "Figure: single_seed_vs_multisource.png")
notes(s,
      "A single seed over connectivity (or flow-cut) is degenerate: it tends to return one undifferentiated "
      "group, anti-correlated with real community structure. Running activation from several sources and "
      "assigning each node to its dominant source recovers structure and is deterministic. Spoken caveat: in "
      "this figure the sources are still hand-placed, one per community. That is exactly finding (f), the "
      "circular-validation trap, and it is what motivated closing the loop with real perception on the next "
      "slide.")

# ----------------------------------------------------------------------------
# Slide 10 - The honest negative result
# ----------------------------------------------------------------------------
s = slide()
title(s, "The honest negative result", color=WARN)
takeaway(s, "Close the loop with real same-domain perception and the 'thought' is incoherent. Asserted as a known-limitation test.", color=WARN)
figure(s, "closed_loop_known_limitation.png", area=(0.6, 2.35, SW - 1.2, 4.55))
footer(s, "Figure: closed_loop_known_limitation.png")
notes(s,
      "When real perception lights up several nodes in the SAME domain, the field's basins collapse: one source "
      "over-swallows across domains while same-domain siblings strand as singletons, so the selected 'thought' "
      "is incoherent. This is not hidden. It is asserted as test_KNOWN_LIMITATION_clustered_sources_give_poor_"
      "basins, which is currently red-by-design and flips to green only if the underlying problem is solved. A "
      "negative result, documented as one.")

# ----------------------------------------------------------------------------
# Slide 11 - Proven vs not
# ----------------------------------------------------------------------------
s = slide()
title(s, "Proven vs. not: the test suite")
takeaway(s, "130 assertions across 56 functions, all passing (45, 35, 19, 13, 18). Green = proven mechanism.", color=PROVEN)
figure(s, "test_suite_bars.png", area=(0.6, 2.35, SW - 1.2, 4.55))
footer(s, "Figure: test_suite_bars.png  -  numbers verbatim from docs/TEST_OUTPUT.txt")
notes(s,
      "Per suite: substrate store 45, spreading activation 35, coalition formation 19, multi-source field 13, "
      "perception + slice 18. Total 130 passed, 0 failed, across 56 test functions, including the adversarial "
      "cross-process determinism checks and the one asserted known-limitation. 'Passing' means the mechanism is "
      "correct and deterministic, not that the cognitive layer is meaningful. Green marks the proven substrate; "
      "the rest is exploratory mechanics that merely runs reproducibly.")

# ----------------------------------------------------------------------------
# Slide 12 - Future work + conclusion
# ----------------------------------------------------------------------------
s = slide()
title(s, "Future work, and the ethos")
bullets(s, [
    ("Validate against a measurable effect with a known direction: semantic priming [10, 11]", INK, False),
    ("Fix source-grouping so same-domain perception does not collapse basins", INK, False),
    ("Build the broadcast/competition phase that 'strongest coalition = thought' currently stands in for", INK, False),
], y=1.75, size=19, gap=14)
eth = textbox(s, 0.7, 4.6, SW - 1.4, 1.6, anchor=MSO_ANCHOR.MIDDLE)
p = eth.paragraphs[0]
setrun(p, "“This part is proven; that part is not, and here is the failing test that says so.”",
       22, bold=True, color=ACCENT, italic=True)
footer(s, "Conclusion.")
notes(s,
      "The honest next step is to stop validating the cognitive layer against hand-built inputs and instead "
      "test it against a measurable cognitive effect whose direction is known independently of Nous, for "
      "example semantic priming [10, 11]: does pre-activating a related concept measurably raise a target's "
      "activation? Then fix the source-grouping that collapses same-domain basins, and build the broadcast "
      "phase that the 'thought' selection currently stands in for. The ethos is the whole point: claim only "
      "what a test proves, and keep the failing test visible.")

prs.save(OUT)
print("wrote", OUT, "with", len(prs.slides._sldIdLst), "slides")
