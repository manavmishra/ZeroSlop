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

## Negative results: what we tested and did not ship

Three classic approaches were evaluated for a trained detection channel and
all three were rejected on evidence, not preference.

**Support-vector machines.** Head-to-head comparisons on text classification
show no measurable gain over logistic regression, and an SVM would add a
dependency to a package whose entire value proposition includes having none.

**Hidden Markov models.** No published result shows HMMs adding value for
AI-text detection. The sequence signal they would model is already captured
by the burstiness and followability statistics, which are cheaper and
interpretable.

**Logistic regression (MaxEnt) over a Bayesian log-odds lexicon.** This one
worked in-domain: 0.985 AUC, 94% accuracy on held-out HC3 data, Platt
calibrated with an abstain band. It was built, trained, integrated, and then
cut. The reason is the transfer test. Trained on ChatGPT-3.5-era text, it
rated 2026-era AI drafts as human at a mean probability of 0.038, and in a
live check returned 0.33 on a passage the pattern meter scored 100/100.
Detector decay across model generations is well documented (RAID,
arXiv:2405.07940); this is that decay measured directly. A channel that is
confidently wrong on current text is worse than no channel, even when it is
reported separately and labelled a second opinion.

The lesson generalises: interpretable surface features degrade gracefully as
models change, because the tells are updated in a data file. A trained
classifier degrades silently, and silence is the failure mode you cannot
audit.
