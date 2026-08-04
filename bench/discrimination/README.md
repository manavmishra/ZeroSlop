# Discrimination test

The 50-draft benchmark compares *rewriters*. This asks the prior question about
the *detector*: given text a reader would confidently label either way, does the
score agree? A gate is only worth having if it does.

```bash
python3 bench/discrimination/evaluate.py
```

## Result

| | n | mean | range |
|---|--:|--:|---|
| slop | 6 | 87.1 | 38.6 – 100.0 |
| human | 6 | 10.5 | 9.5 – 13.4 |

Separation 76.6 points, AUC 1.000, 12/12 correct at the ≤25 gate, no overlap
between the classes.

## Read this before quoting that number

**Both classes were written for this corpus.** They are authored exemplars, not
scraped posts, so a perfect AUC shows the meter agrees with an obvious human
judgment — not that it generalizes to text in the wild. Treat it as a sanity
check and a regression guard, not evidence of field accuracy. It is the same
train/test limitation the must-not-flag corpus has, and it is why the numbers
here are reported next to their caveat rather than in the README headline.

Scraped posts would be better evidence and are not used deliberately: committing
other people's LinkedIn, Medium and Reddit content into a public MIT repository
is a copyright and privacy problem, and a corpus nobody can redistribute is a
benchmark nobody can reproduce.

## The interesting row

`social-slop-06` scores **38.6 with zero charged spans**. No banned vocabulary,
no emoji, no hashtag cluster — it fails on rhythm and format alone. That is the
case a lexicon-only tool misses entirely, and the reason the meter has channels
that never look at words.

## Adding samples

Keep the classes balanced and the genre spread wide. A sample earns its place by
being one a reader would label without hesitating; anything arguable belongs in
`data/corpus/must-not-flag/` instead, where the bar is "must never fire".
