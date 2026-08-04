# must-not-flag — the false-positive floor

Every sample here is writing a human would recognise as human. No pattern in
`data/patterns.json` or `data/learned.json` may fire on any of them, and
`calibrate.py --selftest` fails the build if one does. `learn.py` consults the
same directory before minting anything from the reflect loop, so a pattern
learned from one writer's edit can never start convicting the writing below.

The corpus is the meter's conscience. Adding to it is the single most useful
contribution to this repo: when you find honest writing the scorer got wrong,
the fix is not to lower a weight, it is to add the sample here so the mistake
can never recur.

## What each sample guards against

| Sample | The false positive it prevents |
|---|---|
| `gettysburg.txt` | Dash-heavy 19th-century oratory. An early build convicted it at 88.9 on em-dash density alone. |
| `federalist.txt` | Long periodic sentences and formal abstraction that predate the machines by 240 years. |
| `ml-methods.txt` | Academic methods prose. Passive voice and nominalisation are correct register here, not tells. |
| `grant-abstract.txt` | Research proposal register — hypothesis framing and hedged claims that the general ladder would wrongly strip. |
| `sre-runbook.txt` | Terms of art. "Elevated write volume" is literal; it drove the rider-gating design. |
| `technical-postmortem.txt` | Structured incident writing, where headers and sequence are the correct form. |
| `terse-engineer-note.txt` | Very short, low-burstiness writing that has no room to vary rhythm. |
| `personal-essay.txt` | First-person reflection, which shares surface features with performed candor but is not it. |
| `exec-memo.txt` | Business register. Formal, declarative, and legitimately using the vocabulary marketing copy abuses. |
| `press-release.txt` | Human promotional writing. PR is *supposed* to sound like PR; the meter must not treat genre as guilt. |
| `recipe.txt` | Imperative instructional prose with deliberate second person and short commands. |
| `esl-engineer-email.txt` | **Non-native English.** Published work has found AI detectors misclassify non-native writing at sharply higher rates. A tool that inherits that bias penalizes the writers who can least afford it, so this sample is a fairness guard, not just a coverage one. |

## Provenance

`gettysburg.txt` and `federalist.txt` are public-domain historical texts,
excerpted. The rest are authored exemplars written to be representative of
their genre rather than harvested from real correspondence, which keeps
personal and proprietary text out of a public repository. They are held to the
same bar: if any of them ever fires a pattern, the pattern is wrong.

## Adding a sample

1. Drop a `.txt` file here with prose that is unambiguously human.
2. Run `python3 scripts/calibrate.py --selftest`. If your sample fails, that is
   a finding — fix the pattern, not the sample.
3. Add a row to the table above naming the false positive it prevents. A sample
   with no stated purpose gets deleted in the next cleanup.

See `../must-not-flag-shape/` for the parallel corpus that protects
legitimately fragmented forms (poems, lyrics, changelogs, transcripts) from the
shape channel.
