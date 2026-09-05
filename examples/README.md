# Before-and-after examples

These four small examples show the core promise: remove stock writing without
changing the draft's concrete details. They are demonstrations, not a quality
benchmark.

| Draft | Before | After | Protected detail |
|---|---:|---:|---|
| [Launch post](launch-post.before.md) → [edit](launch-post.after.md) | 99.3 | 9.5 | 40% |
| [Product update](product-update.before.md) → [edit](product-update.after.md) | 100.0 | 9.5 | 10,000 rows; 8 seconds |
| [Team email](team-email.before.md) → [edit](team-email.after.md) | 45.7 | 20.2 | Priya; 12 dashboards; Friday, September 11 |
| [Research summary](research-summary.before.md) → [edit](research-summary.after.md) | 20.2 | 9.5 | held-out set; 0.42; 0.31 |

Reproduce a score:

```sh
python3 scripts/slopscore.py --explain examples/launch-post.before.md
python3 scripts/slopscore.py --explain examples/launch-post.after.md
```

Check the protected strings:

```sh
python3 scripts/slopscore.py --fidelity \
  examples/launch-post.before.md \
  examples/launch-post.after.md
```

The fidelity command protects exact strings. The editorial workflow also
compares meaning, qualifications, voice, structure, and format.
