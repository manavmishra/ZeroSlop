# Antithesis-pair detector: labelled precision and recall

`references/eval.md` A1 budgets antithesis pairs by frequency — one per piece,
two is a finding — so the count has to be right before the budget means
anything. Until this corpus existed the detector had two kinds of evidence: it
fired on four hand-picked anchors, and it stayed silent on the certified-human
corpus. Neither of those is a recall measurement, and the recall was 37.5%.

## Running it

```sh
python3 bench/antithesis/evaluate.py           # print the current numbers
python3 bench/antithesis/evaluate.py --check   # fail if results.json is stale
python3 bench/antithesis/evaluate.py --write   # re-record
```

## What is in the corpus

58 adjacent-sentence pairs: 30 labelled `antithesis`, 28 labelled `ordinary`.
The positive shapes come from `references/tells.md` and `SKILL.md` step 2.1.
The negatives are deliberately adversarial for this detector — negation that is
not a figure, anaphora, repeated subjects, shared vocabulary, imperatives, and
technical prose that happens to be parallel.

## The recall ceiling, which is a property of the figure

Two positive shapes are labelled `antithesis` that the detector is not expected
to reach. They count against recall rather than being excused, and
`in_reach_recall` reports the rest separately.

- **subject-swap** — "Llama is open-weights. Dolma releases the data."
  `references/tells.md` calls this a judgment call outright.
- **weak-isocolon** — "A meter reports a number. A reader reports a feeling."
  is identical to the ordinary "The report lists every vendor. The appendix
  lists every contract." on every lexical statistic available: same lengths,
  one shared word, 0.33 overlap. Only semantic opposition separates them, and
  no word count can see that. A detector that caught the first would catch the
  second, and the second is not the figure.

## Limits

The pairs are hand-authored and hand-labelled by the maintainer. They are not
sampled from a population, and no second reader adjudicated them. These numbers
are a regression floor for the detector against one reader's labels on
constructed examples. They are not field accuracy, and they say nothing about
how often the figure occurs in real drafts.
