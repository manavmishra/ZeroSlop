# Evidence Base — why the ladder is ordered the way it is

Every rule in this skill traces to measured findings. This file is the chain
of custody. Full dossier with per-paper notes lives in the research archive;
citations here are the load-bearing ones.

## The central finding

Commercial detectors (GPTZero, Pangram) rate *base-model* text as ~97–99%
human while flagging *instruction-tuned* output from the same model
(arXiv:2605.19516). Detectors are classifiers of the **post-training (RLHF)
register** — the polished, uniform, preference-optimized voice — not of
machine generation itself. That register lives entirely in surface
realization, which is why rewriting can remove it without touching meaning.
It is also why "humanizing" is legitimate editing: the target is a register,
not a deception.

## Detection features, ranked by evidence strength

1. **Token-level predictability.** AI text sits at local maxima of model
   log-probability (DetectGPT, arXiv:2301.11305; Binoculars, 2401.12070).
   Human text doesn't. → Ladder L1: specific, slightly surprising phrasing
   and concrete facts are the direct counter.
2. **The LLM lexicon.** A few hundred style words carry huge evidential
   weight: "meticulous" +34.7x, "commendable" +9.8x, "intricate" +11.2x in
   post-ChatGPT scientific text (Liang, 2403.07183); ~900 excess words
   catalogued across 15M PubMed abstracts (Kobak, 2406.07016 —
   github.com/berenslab/llm-excess-vocab); 21 focal words traced to RLHF
   (Juzek & Ward, 2412.11385). Era-dependent: delve peaked 2023–24;
   enhance/highlight/showcase dominate 2025+. → Ladder L5 + the scorer's
   weighted lexicon + the learning loop's era updates.
3. **Surprisal uniformity.** Humans spike information density unevenly; LLMs
   smooth it (GPT-who/UID, 2310.06202 — beats commercial detectors by >20%).
   → L3's "don't pad every claim to equal weight".
4. **Low burstiness.** Uniform sentence length/structure: GPTZero's founding
   feature, corroborated independently (Muñoz-Ortiz, 2308.09067; Reinhart,
   PNAS 2410.16107). Human sentence-length CV is simply higher. → the
   scorer's burstiness metric and the ≥0.45 gate.
5. **Register rigidity.** LLMs hold one polished expository voice regardless
   of situation; humans shift register (Reinhart). → L4.
6. **Stance asymmetry.** Humans: first-person stance, modals, selective
   epistemic hedging, discourse-marker cohesion. LLMs: nominalizations,
   formal connectives, paragraph-architecture cohesion (Herbold, 2304.14276).
   → L4's hedging rules and "connective texture over scaffolding".
7. **Syntax signature.** Nominalization density, present-participial
   clauses, longer constituents (Reinhart; Muñoz-Ortiz). → de-nominalize;
   kill participial openers.
8. **Affect skew.** LLM text is joy-skewed and uniformly positive
   (Muñoz-Ortiz). → widen affect.

## Why the scorer measures features, not detector verdicts

Detectors are brittle: RAID (2405.07940) shows trivial perturbations fool
them, and DIPPER (2303.13408) shows one paraphrase pass drops DetectGPT from
70% to 4.6% detection. Verdicts are therefore neither necessary nor
sufficient. The features they key on, however, are exactly what human readers
report as "sounds like AI" — so the scorer tracks the features directly:
weighted tell density, lexicon hits, burstiness, formatting densities,
register signals. Passing the gate means "the measurable tells are gone",
which is the honest, robust target.

## What rewriting cannot do (the honesty boundary)

- Retrieval/watermarking by providers survives any rewrite (DIPPER's
  conclusion). Fine — this skill's goal is reader-experienced quality, not
  evasion.
- Character-level tricks and fake typos fool detectors (RAID) but degrade
  writing. Banned.
- Hollow content scores clean on every surface metric. Only the removal test
  catches it, which is why the judgment pass can never be skipped and why
  hollow spans are flagged, not padded.

## Practitioner corroboration

Paul Graham's "Write Like You Talk" and "How to Write Usefully" predate LLMs
and independently prescribe the same counters: spoken register (high
perplexity relative to formal boilerplate), maximal-strength claims without
overclaiming, qualification as precision. Wikipedia's WP:AICATCH — the
largest human-curated corpus of caught-in-the-wild AI text — converges on the
same tell families and adds the cluster rule this skill inherits: one tell is
coincidence; many tells, repeatedly, convict.

## Negative results: trained classifiers

Several trained-classifier approaches were evaluated for an additional
detection channel. None shipped, and the reasoning generalises beyond the
specific methods.

**The ones that added nothing.** Two well-established classifier families were
ruled out on published evidence: one shows no measurable gain over a simpler
model on text classification while adding a dependency to a package whose value
includes having none, and the other models a sequence signal that the burstiness
and followability statistics already capture more cheaply and more legibly.

**The one that worked, and was cut anyway.** A trained channel built on lexical
frequency and stylometric features performed well in-domain: 0.985 AUC and 94%
accuracy on held-out data, properly calibrated with an abstain band. It was
built, integrated, and then removed. The transfer test is why. Trained on
2022-era text, it rated 2026-era AI drafts as human at a mean probability of
0.038, and in a live check returned 0.33 on a passage the pattern meter scored
100 out of 100. Detector decay across model generations is well documented
(RAID, arXiv:2405.07940); this was that decay measured directly. A channel that
is confidently wrong on current text is worse than no channel, even reported
separately and labelled a second opinion.

The lesson generalises. Interpretable surface features degrade gracefully as
models change, because updating them means editing a data file and the drift is
visible in the diff. A trained classifier degrades silently, and silence is the
failure mode you cannot audit.

## Fairness: who a false positive lands on

Liang et al. ran seven commercial GPT detectors over two human-written corpora,
US eighth-grade essays and TOEFL essays by non-native English speakers. Native
samples scored near-perfectly. **More than half of the non-native samples were
misclassified as AI-generated** (arXiv:2304.02819; *Patterns* 4:100779, 2023).

The mechanism matters more than the headline. The same study found that
enriching word choice in the non-native samples reduced misclassification,
while simplifying the native samples increased it. The detectors were keying on
linguistic complexity, so anything measuring "does this read as polished" will
penalize the writers with the least room to perform polish.

That is a direct hazard for this skill, which measures surface features by
design. Two consequences are load-bearing rather than decorative. Burstiness
and followability are scored as *bands*, not as "more is better", so plain
sentences are never evidence on their own. And
`data/corpus/must-not-flag/esl-engineer-email.txt` is in the corpus every new
pattern must clear, so the reflect loop cannot learn a rule that convicts
competent non-native writing however many people cut the phrase.

## The reflect loop: why recurrence is the gate

The learning path (`scripts/learn.py`) takes its labels from the difference
between what the skill returned and what the author published. Two design
choices come from the failure modes above rather than from preference.

*Learning must be two-directional.* A loop that only adds patterns can only
grow, and a detector that only grows converges on flagging everything —
which, per Liang, lands hardest on the writers already over-flagged. So a
pattern the author overrules repeatedly loses weight.

*A single edit is not evidence.* Authors cut for length, fix facts, and change
their minds, and none of that is a style signal. Requiring the same span across
three independent documents is a crude significance test: it separates a
construction that recurs across unrelated writing from one person's sentence.
The same property is what makes an upstream contribution shareable without
carrying private text.

The honest limit: this measures what *writers who use the skill* strike, not
what readers detect. It tracks the register those authors are editing away
from, which is the target, but it is a convenience sample and no substitute for
the frequency work in `calibrate.py` against a real corpus.

## Practitioner corroboration: Kagi SlopStop

Kagi ships a production system for the same problem at web scale, and it
converged on three of the design decisions here independently, which is the
closest thing to external validation this architecture has.

**Corroboration before conviction.** A domain is downranked when it is *mostly*
AI-generated, typically above 80% of its pages, rather than on a single hit.
That is the same principle as "clusters convict, singles don't", arrived at from
ranking rather than from linting.

**Multiple reports accelerate review.** Kagi's community reporting treats
repeated independent flags on one domain as stronger evidence than one flag.
The reflect loop's three-document threshold is the same idea at document scale,
and for the same reason: one reporter's judgment is taste, several unrelated
reporters agreeing is signal.

**An appeals path is a first-class feature, not an afterthought.** Users can
report content as *not* slop, which triggers re-review and restores ranking.
A system that can only add suspicion converges on suspecting everything. This
is what `learn.py --demote` exists for, and Kagi treating it as core rather
than optional is the argument for building it before you think you need it.

**Downrank, never remove.** Flagged results stay visible and simply rank lower.
The analogue here is hard rule 2 — flag hollow spans, do not fill them — and
the reason both hold is that a false positive under a removal policy is
unrecoverable, while a false positive under a flagging policy is an annoyance.

Source: <https://help.kagi.com/kagi/features/slopstop.html>

## Platform enforcement (August 2026)

The target moved from reader disapproval to ranking. LinkedIn added a "Seems
like AI slop" report control; reporting hides the post for that reader and
trains LinkedIn's classifiers, flagged posts lose algorithmic reach beyond the
author's own network, and repeat authors are notified privately in analytics.
LinkedIn retired its "enhance your post" generator for a proofreader. Snapchat
made wholly AI-generated video ineligible for Spotlight recommendation, ranking
human-made above synthetic even with a disclosure label
(Forbes, 1 August 2026).

Two consequences for this skill's design.

**The adversary is a reader-report classifier, not a word list.** LinkedIn's
system is trained on what readers flag. That is a moving target defined by
perception, which is an argument for the reflect loop — learning from what
writers actually strike tracks the same perception — and against betting the
detector on any fixed lexicon.

**Reach is the cost of a false negative.** Before this, shipping a sloppy draft
cost credibility with the people who noticed. Now it costs distribution to
everyone. That raises the value of catching the structural tells, which is where
a lexicon-only tool fails: the discrimination corpus contains a post scoring
38.6 with zero charged spans, caught on rhythm and shape alone.

It also raises the cost of *over*-correction, since a rewrite that strips a
writer's voice to pass a meter is a worse outcome than the tell it removed.
That trade is why `references/overcorrection.md` exists and why the gate reports
what it did not measure.

## The roadmap channels, and why they are not shipped yet

Current work on interpretable detection converges on a small set of
content-independent stylometric features, which is the direction this scorer
should grow rather than adding more regex patterns.

- **Function-word bigram frequency and average sentence length** are the two
  highest-importance features in a lightweight interpretable detector, and the
  paper reports 95–97% accuracy from them alone (NEULIF, arXiv:2511.21744).
- A systematic cross-domain analysis finds the same family — function words,
  punctuation, linguistic diversity — carries most of the interpretable signal
  (arXiv:2606.04177).
- These are attractive here because they are blind to specific wording, so
  unlike the pattern meter they cannot be defeated by swapping synonyms, and
  they degrade gracefully as models change.

They are **not shipped**, and the reason is a measured negative result rather
than a plan. Computing normalised sentence-opener entropy and function-word
bigram entropy over the labelled discrimination corpus separates human from
slop by essentially nothing (0.976 vs 0.986 opener entropy on twelve samples),
with slop scoring marginally *higher*. That is not evidence the features fail;
it is evidence the corpus is far too small to calibrate them — the cited work
derives its thresholds from tens of thousands of documents. Adding an
uncalibrated channel that shows no signal on the only data available would be
exactly the hand-tuned rule this project tries to avoid.

So the dependency is explicit: the labelled corpus (RAID arXiv:2405.07940, HC3,
M4, AuTextification) comes first, the stylometric channels are calibrated
against it second, and only then do they join the meter. Until then the honest
statement is that the scorer is a lexical-and-structural linter with a
research-backed roadmap, not a stylometric classifier.

## Why register repair beats detection (2025-26)

Two current results reframe what a slop tool should even try to do.

**Detection is losing an arms race.** Adversarial paraphrasing — an LLM
rewriting AI text under the guidance of a detector — cuts detector true-positive
rates by 87-99% and transfers across neural, watermark and zero-shot detectors
(Adversarial Paraphrasing, arXiv:2506.07001; StealthRL, arXiv:2602.08934).
Anything that competes on catching a machine is chasing a target the literature
is actively defeating. Zero Slop does not compete there: it repairs the register
rather than classifying authorship, which is the half that stays useful when
detection fails.

**Slop is a training-supply pollutant, not just an aesthetic one.** Model
collapse work shows machine text re-entering training corpora degrades the next
model, with as little as 1% synthetic data measurably harming quality
(arXiv:2603.11784, arXiv:2510.16657). That makes de-slopping a contribution to
the commons, not only to one post's reach — the cleaner the human writing that
survives, the less the collapse.

Together these are the argument for the product's shape: measure and rewrite the
author's own draft, personalise to the author's own voice, and never optimise
against a detector, because the detector is both defeatable and beside the point.
