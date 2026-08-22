# Search-informed slop challenge

This set contains 18 anonymous paraphrases across every prose genre with a Zero
Slop platform module: LinkedIn, X, email, blog, newsletter, and research. Public
examples were found through Google and, for LinkedIn, checked in the signed-in
site. The repository keeps no names, handles, employers, post URLs, or copied
passages.

The examples deliberately preserve the visible slop patterns while changing the
subject matter and wording. They are synthetic positive cases, not verified
human or AI originals. That makes the set safe to redistribute and useful as a
regression challenge, but unsuitable for estimating field accuracy.

Run:

```bash
python3 bench/search-corpus/evaluate.py --check
python3 bench/search-corpus/compare.py --check
```

`results.json` records the exact scores from the current detector. Every sample
must cross the 25-point surface gate or trigger the separate social-shape check.
Changing the scorer therefore requires an explicit result refresh and review.

## Same-corpus rewrite comparison

`outputs/` contains final rewrites from five pinned instruction sets: Zero Slop,
no-ai-slop, humanizer, de-slop, and stop-slop. One host Codex session produced every
rewrite with the same brief. `methods.json` records the source revision for each method,
and `comparison-results.json` records every score and pass result.

The comparison reports two narrow measurements. The first is the current Zero Slop
surface score after editing. It favors a method designed to iterate against that meter,
so it is not an independent quality ranking. The second requires the genre score gate
and automated fact check to pass. The check covers figures, names, quotations, links,
and asserted feelings; it cannot detect every semantic change. All five methods passed
that automated fact check on all 18 items, so their combined pass-rate differences are
surface-score differences.

This corpus contains only obvious positive examples. It cannot measure false positives,
specificity, field accuracy, human preference, or complete semantic fidelity. Do not
describe either chart as an accuracy benchmark.

## Public AIStoryHub checker cross-check

`aistoryhub-checker-results.json` records an item-by-item browser replay through
AIStoryHub's [public AI Slop Checker](https://aistoryhub.co/slop-checker), which uses
the public [Corpus of AI Clichés](https://aistoryhub.co/corpus). The observation file
stores canonical input hashes, the corpus version, the “Reads Clean” threshold, every
returned score, and null for a checker abstention. `compare.py` verifies those hashes
before including the external summary in `comparison-results.json`.

The checker requires at least 20 words, so eligible denominators differ by method. It
is a deterministic surface checklist and does not assess facts, meaning, writing
quality, or authorship. Its result is an external cross-meter of rewrite performance,
not an accuracy benchmark.

The cross-genre design is informed by two external projects. [The Slop
Index](https://github.com/hgaddipati1118/slop-index) contributes the idea of
measuring repeated openings across several drafts instead of treating each text
in isolation. [Measuring AI “Slop” in
Text](https://arxiv.org/abs/2509.19163) supplies the broader diagnostic taxonomy:
information density and relevance, factuality, repetition and templatedness,
coherence, fluency, verbosity, word complexity, and tone. Neither source is
treated as a calibrated weight for this corpus.
