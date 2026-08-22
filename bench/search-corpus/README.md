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
```

`results.json` records the exact scores from the current detector. Every sample
must cross the 25-point surface gate or trigger the separate social-shape check.
Changing the scorer therefore requires an explicit result refresh and review.

The cross-genre design is informed by two external projects. [The Slop
Index](https://github.com/hgaddipati1118/slop-index) contributes the idea of
measuring repeated openings across several drafts instead of treating each text
in isolation. [Measuring AI “Slop” in
Text](https://arxiv.org/abs/2509.19163) supplies the broader diagnostic taxonomy:
information density and relevance, factuality, repetition and templatedness,
coherence, fluency, verbosity, word complexity, and tone. Neither source is
treated as a calibrated weight for this corpus.
