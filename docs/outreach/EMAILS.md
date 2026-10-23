# Outreach email templates

Short, honest templates for sharing Psyche. Replace every `[BRACKETED]` field. The framing is
deliberately methodology-first and non-salesy: Psyche is an engineering prototype and a
software-testing-methodology case study, never a mind, a consciousness, an AGI, or a validated
cognitive model. Numbers are taken from `tools/ledger.json`, which is the single source of truth and is
generated from `docs/TEST_OUTPUT.txt` (currently **2,594 assertions across 26 suites, all
passing**). Never type a count from memory — run `python3 tools/ledger_check.py` before
sending anything. Do not add cognitive claims beyond what the technical report supports.

---

## A. To a professor: sharing the work, requesting feedback

**Subject:** A small, test-first cognitive-architecture prototype (feedback welcome)

Dear Professor [LASTNAME],

I am [YOUR NAME], a [YEAR/PROGRAM] student at [INSTITUTION]. I built Psyche, a dependency-free
Python prototype of a graph memory and spreading-activation substrate, written test-first as a
software-testing-methodology case study.

To be precise about scope: the substrate and activation layers are rigorously tested for
determinism, integrity, and purity, inside a suite of 2,594 assertions across 26 suites that
all pass; the cognitive layers above run deterministically, but their meaningfulness is not
claimed, and known limitations are asserted as explicit negative tests.

The suite runs with one command, and a short technical report documents six structural bugs that
adversarial testing caught. Would you be willing to skim the report and tell me whether the
methodology framing holds up? Even a few lines would help.

Thank you for your time,
[YOUR NAME]
[EMAIL] · https://doi.org/10.5281/zenodo.20474613

---

## B. To a professor: interest in the next step under supervision

**Subject:** Interest in validating a memory-substrate prototype against a measurable effect

Dear Professor [LASTNAME],

I am [YOUR NAME], a [YEAR/PROGRAM] student at [INSTITUTION]. I built Psyche, a dependency-free
memory-and-activation substrate that is proven for determinism, integrity, and purity at the
substrate level; the cognitive layers above are exploratory, and their meaningfulness is not yet
established.

The honest next step is to stop testing the cognitive layer on hand-built inputs and instead
measure it against an effect whose direction is known independently, for example semantic priming:
does pre-activating a related concept measurably raise a target's activation?

This connects to your work on [PROFESSOR'S AREA OR SPECIFIC PAPER]. I would value the chance to
pursue it under your supervision, as a [thesis / reading project / lab rotation]. Could we meet for
[20 minutes] to discuss whether it fits?

Thank you,
[YOUR NAME]
[EMAIL] · https://doi.org/10.5281/zenodo.20474613

---

## C. Symposium / student-conference submission (cover note + abstract)

### Cover note (email to the organizers)

**Subject:** Submission for [SYMPOSIUM NAME, YEAR]: adversarial testing of a memory substrate

Dear [COMMITTEE OR ORGANIZER NAME],

Please find my submission below. It is a methodology-first engineering project: a small
memory-and-activation substrate built test-first, in which adversarial testing caught six
structural bugs. I make no cognitive claims beyond what the tests support. The abstract is
[WORD COUNT] words; I can present as a [talk / poster], and the code and technical report are
available at https://doi.org/10.5281/zenodo.20474613.

Thank you for considering it,
[YOUR NAME], [INSTITUTION]

### Abstract (paste into the submission form, ~150 words)

Psyche is a dependency-free Python prototype of a memory-and-activation substrate for a cognitive
architecture, presented as a software-testing-methodology case study. Four layers were built
test-first: a graph substrate store, a deterministic spreading-activation engine, a multi-source
field, and an end-to-end perceive-then-think slice. The lower two layers are verified for
determinism (including across process hash seeds and across CPython versions), integrity, and
purity, inside a suite of 2,594 assertions across 26 suites that pass with zero failures. The upper
layers run deterministically, but their cognitive meaningfulness is not claimed. One failure mode recurred at every layer: a component passes on a
friendly, hand-built input and breaks only under adversarial testing, or once the loop is closed
with system-generated inputs. Six structural bugs were caught this way. Closing the loop with real
perception yields an incoherent "thought," asserted as a known-limitation test. The next step is
validation against a measurable effect with a known direction, such as semantic priming.
