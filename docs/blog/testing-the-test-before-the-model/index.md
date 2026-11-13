---
title: "Testing the test before the model: a random player at 22%"
date: "2026-11-13"
description: "Psyche's second stage tested its test equipment before any model: a random player solved 22% of cases, so the check did not pass and the test is redesigned."
tags:
  - "cognitive-maps"
  - "methods"
  - "project"
---

Psyche's second stage began by testing its own test equipment, before any model is judged by it.
Two reference players went through the new evaluation harness: one that always knows the best
move, and one that acts at random. The all-knowing reference succeeded in every case. The random
player succeeded in 22% of cases on average, where close to zero had been assumed, and in 2 of the
50 test environments it crossed the limit written down before the run. By the criterion fixed in
advance the check did not pass. The criterion was left as written, the result is recorded as a
failure, and the test is redesigned before any model is evaluated.

Stage 2 studies spiking cognitive maps. A cognitive map is an internal picture of an environment
that lets its owner find new routes, not only repeat learned ones; the model under study is a
spiking neural network, a brain-inspired network whose units communicate with brief pulses instead
of passing continuous numbers at every step. No model has been evaluated yet. Everything in this
post is about the equipment that will one day evaluate one.

## The assumption behind "close to zero"

A test meant to need real competence invites an intuition about a player with none: it will do
badly. If a task is hard for a careful player, the reasoning goes, a player that ignores
everything it sees must almost never get there. The random baseline then turns into a formality,
something run last, with its number expected instead of measured.

The expectation here was the same: close to zero. It rests on a gap. How hard a task is for a
competent player and how often a guesser gets through it are two separate properties of a test.
The first is what a designer has in mind. The second is known only once it has been measured, and
this was the measurement.

### How luck adds up

The arithmetic behind that gap is general, and it is the familiar multiple-comparisons sum. Suppose
a check asks a chance player to stay under some limit in each of <var>m</var> independent places,
and that in any one of them luck takes it over the limit with probability <var>p</var>. The
probability that it stays under everywhere is (1 − <var>p</var>)<sup><var>m</var></sup>, so the
probability that luck breaks the check somewhere is

<var>P</var> = 1 − (1 − <var>p</var>)<sup><var>m</var></sup>

The numbers that follow are illustrative and are not this project's. With <var>p</var> = 0.05 and
<var>m</var> = 20, <var>P</var> is about 0.64. With <var>m</var> = 100 it is about 0.994. A chance
that looks negligible in one place becomes near certainty once there are enough places. Read the
other way, the same sum sets the budget: to keep <var>P</var> below a target <var>α</var>, each
place needs <var>p</var> below about <var>α</var> / <var>m</var>. An intuition of "close to zero"
for one place says little about the whole.

## Equipment before the model

A sanity check, in the sense used here, is a test of the test equipment itself, run before any
real candidate is evaluated. The evaluation harness is the software that runs a test on a player
and scores the outcome. A first runnable version of it now exists, with an automated test suite of
its own: 8 tests at the end of the day it first ran, and 13 at the end of the next day, the day the
sanity check ran.

The order is deliberate. As a general matter, a score on any test is read against two reference
points, a floor and a ceiling, and both have to be measured on the same equipment before the
score means anything. Reference players are stand-ins whose answer is known in advance, which is
what makes them useful here:

- **The all-knowing reference** is given the right answer. It should always succeed. If it does
  not, the equipment is broken.
- **The random player** acts by chance. It marks the floor. If it scores well, the test is too
  easy, and a high score from anything else says less than it appears to.

The pass criterion for the check was fixed before the run: written down in advance, so that it
could not be bent to fit the outcome. The check ran over 5 random seeds, each seed being a number
that fixes the random choices of a run so that the run can be repeated exactly, and over 50 test
environments.

## What the check returned

| Reference player | Expected | Observed |
|---|---|---|
| All-knowing reference | always succeeds | succeeded in 100% of cases |
| Random player | almost never succeeds, assumed close to zero | succeeded in 22% of cases on average |
| Random player, against the limit set in advance | below the limit | crossed it in 2 of the 50 test environments |

![Share of cases each reference player succeeded in, over 5 seeds and 50 test environments. The all-knowing reference reached 100%, as expected. The random player had been assumed to score close to zero and reached 22% on average. A note below the chart states that in 2 of the 50 test environments the random player crossed the limit written down before the run, so the check failed its pre-set criterion, and the failure stays on record.](first-check.svg)

The top end behaved. The all-knowing reference succeeded in every case, which is what working
equipment should report for a player that is handed the right answer.

The bottom end did not. The random player's 22% was far from the assumption, and in 2 of the 50
environments it went past the limit fixed before the run. A pre-registered criterion is either met
or not met, and this one was not met.

The cause was not a programming error. The test as designed was too easy to pass by luck.

## Why the criterion stayed where it was

The obvious way out of a failed check is to move the limit. After a run, a limit can always be
placed above whatever the random player happened to score. A limit chosen that way carries no
information: a check that passes whenever its threshold is set after the result can never fail,
so its passing says nothing. This is general practice in experimental work, and it is the reason
criteria are written down in advance at all.

That did not happen here. The criterion stayed as it was written, the experiment is recorded as
failed under it, and what changes next is the test. This is the check doing its job: it exists to
find a test that luck can pass while finding it is still cheap.

The record now says that the floor was measured and came out at 22%, where it had been assumed
to be close to zero. Every later number from this equipment can be read with that history
visible.

## What else is open

The sanity check was not the only finding about the test. An internal review of this first
experiment listed further weaknesses in the test design, to be fixed before any model is
evaluated. What they are is not described here. They are open, and the evaluation of a model waits
on them as it waits on the redesign.

Alongside the equipment, a structured review of prior work has started. About 1,800 records were
collected from scholarly indexes for screening. The review is in progress: collecting records is
the start of it, and nothing about what they contain is reported here.

## What this does not show

- **Nothing about any model.** No model has been evaluated. The check says nothing about how a
  spiking neural network, or any other kind of model, would do on this test or any other.
- **The 100% is a statement about the equipment.** It shows that the harness registers success for
  a player given the right answer. It does not show that the test is sound in every other respect;
  the internal review found weaknesses in the test design that are still to be fixed.
- **The 22% describes this version of the test.** It is a property of the test as first designed,
  measured with these reference players. It says nothing about how the redesigned version will
  behave.
- **Understood in kind, not yet fixed.** The cause is known to be a test that luck can pass. The
  redesign that removes it is still to be done.
- **The prior-work review is not finished.** Records have been collected for screening. No
  conclusion is drawn from them yet.

## The general lesson

A random baseline is a measurement. It is among the cheapest numbers in an evaluation, and it
sets how the scores near it can be read: if luck alone scores 22%, a score close to that floor
says little, because a model that seems to do well may be doing little more than a lucky guesser.
Running the random player before anything else is how that is found out while it is still cheap.

A pass criterion earns its value in the cases where it says no. One that is adjusted whenever it
would fail has never been tested, and the results it waves through inherit that weakness. Keeping
a failed check on the record, under the criterion it was given, is what lets the passes that come
later be believed.

Starting with the measuring equipment is also cheaper. Here the failure leads to the redesign of
a test before any model has touched it. Found later, the same problem could have meant discarding
results that had looked real. An [earlier post](../three-questions-before-a-number-counts/index.md)
told a similar story from the project's first stage: checks written before a run, each of which
stopped an experiment before a graded number existed.

## What comes next

Two pieces of work follow from this: redesigning the test so that luck cannot pass it, and
finishing the review of prior work. The weaknesses the internal review listed are to be fixed
before any model is evaluated.

## Further reading

- [Spiking cognitive maps: overview](../../research/README.md), the public overview of stage 2.
- [Claims and scope](../../research/claims-and-scope.md), what the project does and does not claim.
- [Glossary](../../research/glossary.md), the terms used on the pages of the cognitive-map line.
- [Three questions a test answers before its number counts](../three-questions-before-a-number-counts/index.md),
  the earlier post on pre-registered checks in stage 1.
