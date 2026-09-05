# One-call editor checks — 2.8.11

The [saved replay](results.json) records real Cloudflare Workers AI responses,
the earlier six-case baseline, and local fact-checking and selection results.
Each of the 12 final requests used one Llama 3.3 70B call. All returned text;
that is a completion result, not a claim that every edit was good.

The reported failure had two causes: the editing instructions allowed empty
sentences to survive as synonyms, and the fact checker treated ordinary subjects
such as “Efficiency” as names it had to preserve. Regression tests now permit
deleting those narrowly defined openings while protecting actual names and quotes.
An unchanged, valid response is no longer reported as a provider outage.

The main example now becomes “Setup time fell from 11 hours to 3.” Some other
responses still repeat benefits. The record also identifies a contextual inference
that a name-and-number check cannot detect. These development cases helped shape
the prompt, so they cannot establish independent accuracy or competitor rankings.

Timings exclude browser startup and rendering. Local selection was replayed with
the general genre; it is separate from browser compatibility testing. The release
keeps the existing model and the one-call limit.
