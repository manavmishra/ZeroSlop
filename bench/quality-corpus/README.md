# Blind slop-quality panel

This lane asks whether a passage needs editorial correction for slop. It does not
ask who wrote the text.

The panel contains 72 variants of 12 source drafts: the original and one rewrite
from each of five anti-slop methods. Six genres are represented, with one source per
genre assigned to development and one to held-out test. Every variant from a source
stays in the same split.

Two LLM editorial raters received only `protocol.md` and `blind-packet.json`. The
packet exposes an opaque ID and text; it contains no method, source, split, score, or
other rater's label. `manifest.json` keeps the hidden mapping and source hashes.
`evaluate.py` rejects incomplete labels, stale hashes, duplicate raters, and split
leakage. Borderline calls and rater disagreements remain unresolved rather than
being forced into a binary answer.

```bash
python3 bench/quality-corpus/build_manifest.py --check
python3 bench/quality-corpus/evaluate.py \
  --manifest bench/quality-corpus/manifest.json \
  --labels bench/quality-corpus/labels-rater-a.json \
  --labels bench/quality-corpus/labels-rater-b.json \
  --out bench/quality-corpus/results.json --check
```

This is a small, clustered, blind LLM-as-a-judge study. It can compare these saved
rewrites and test whether a structured contextual review is reproducible between
the two raters. It is not independent human field accuracy and is not used to train
a neural model.
