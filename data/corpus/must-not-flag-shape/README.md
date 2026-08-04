# Shape regression corpus

Genres that are structurally indistinguishable from broetry: every sentence on
its own line, high fragment counts, no connective tissue. The shape channel
must stay silent on these, and `calibrate.py --selftest` runs them under
`--genre social` — the hostile setting, where the channel actually engages.

The guards that keep them silent (structural markers, dialogue openings, and
an eight-paragraph floor) run before the metric, not after.

## Known boundary

`lyrics.txt` flags. Song verse and broetry are the same shape, and no
structural signal separates them; telling them apart needs semantics the
channel does not have. It is listed as a known boundary rather than suppressed
with a special case, because a metric that quietly excuses its failures is
worse than one that names them.

This costs little in practice. Shape is reported as its own axis and never
folded into the AI-likelihood score, so a false positive costs the author one
advisory line rather than a wrong verdict — and lyrics declared as a social
post is a mis-declared genre to begin with.
