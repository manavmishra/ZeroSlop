# Zero Slop

**Find AI-sounding writing. Keep the source intact.**

A prose linter that scores text 0–100 for stock phrasing, mechanical rhythm,
vague claims, and canned formatting, then tells you which phrases produced the
number. It runs offline, uses only the Python standard library, and has no
runtime dependencies.

The score describes the writing. It does not identify who wrote it. Zero Slop is
not an AI detector and must not be used as one.

## Install

```sh
pip install zero-slop
```

## Use it

```sh
slopscore draft.md                      # readable report
slopscore --json draft.md               # machine-readable
slopscore --explain draft.md            # report, reasons, line-by-line map
slopscore --batch docs/ --gate 25       # exits non-zero above the threshold
slopscore --fidelity before.md after.md # did the rewrite keep the facts?
cat draft.md | slopscore                # stdin
```

### As a library

```python
from zero_slop import load_patterns, score_text

data = load_patterns()
score_text("We are thrilled to announce a transformative solution.", data)["ai_likelihood"]
# 99.3
```

### In CI

```yaml
- uses: manavmishra/ZeroSlop@v2.11.1
  with:
    path: docs
    gate: "25"
```

### As a pre-commit hook

```yaml
repos:
  - repo: https://github.com/manavmishra/ZeroSlop
    rev: v2.11.1
    hooks:
      - id: zero-slop
        args: [--gate, "25"]
```

## What the score means

Human reference samples score 9–21. Unedited model output averages 77. Those are
reference points, not boundaries. The scoring was run over 7,627 abstracts from
the MIT-licensed RAID+ dataset and all 2,187 Beemo records; the drafts, outputs,
and hashes are in the repository so the numbers can be reproduced.

The scorer handles about 500 documents per second on a single machine, so it is
usable as a batch gate rather than only an interactive tool.

## Rewriting

This package is the scorer. The full editorial workflow — where your own AI
assistant rewrites the draft across copy-desk and read-aloud passes, and a local
fact gate rejects any revision that adds or drops a name, number, quotation, or
link — ships as an Agent Skill:

```sh
npx skills add manavmishra/ZeroSlop --global
```

- Website: <https://zero-slop.ai>
- Source: <https://github.com/manavmishra/ZeroSlop>
- MIT licensed
