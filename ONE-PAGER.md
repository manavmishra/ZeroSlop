# Zero-Slop, on one page

**What it is.** An agent skill that turns AI-sounding drafts into writing an
expert would publish, then proves the change with numbers. It ships its own
statistical detector, a research-ranked rewrite method, a hard pass/fail
gate, and a learning loop that gets sharper with use. MIT-licensed, offline,
zero dependencies. Built on the Agent Skills standard, so the same artifact
runs in Claude Code, Codex, claude.ai, and any compatible harness.

**The problem it solves.** Readers now recognize machine prose on sight: the
em-dash rhythm, "I'm excited to announce," the tidy rule-of-three, the
uplifting wrap-up. Research explains why. Preference-tuned models converge on
one register, and its fingerprints are measurable: "meticulous" spiked 34.7x
in post-ChatGPT abstracts, sentence rhythm flattens, word choice sits at the
probability maximum. The register lives on the text's surface. A disciplined
rewrite removes it without touching meaning.

**How it works.** Five steps. Measure the draft with a ~200-line stdlib
scorer (weighted tell density across 60+ patterns, burstiness, LLM lexicon,
formatting noise → AI-likelihood, 0–100). Diagnose what regexes can't see:
hollow paragraphs, buried hooks, the facts that must survive. Rewrite in two
passes: strip the tells, then build toward an expert voice, authority earned
by specifics. Verify against a gate (LinkedIn: ≤20/100, zero em-dashes, zero
emoji, zero hashtag clusters) and iterate until it passes or say so plainly.
Learn: every miss becomes a new pattern in the shared database.

**A real run.** A LinkedIn draft opening with "Enterprise AI value has too
often compounded inside individual workflows…" measured 45.7/100. The rewrite
opens "6x. That's how many more messages frontier users send than the median
employee," and measured 9.5/100. Same facts. Nothing invented. The number
moved to the first word.

**The proof.** Benchmarked blind against the best-known alternatives: 50
AI-typical drafts, six genres, independent judges, shuffled labels. Zero-Slop
took 32 of 50 "which would you publish" picks; the three rivals combined took
18. Judge composite 8.01/10 against 7.82, 6.96, and 6.35. Detector residue
after rewriting: 10.9/100 versus 18.7, 19.4, and 39.7 (drafts start at 76).
The harness ships in the repo. Rerun it if you doubt it.

**What it refuses.** No invented numbers, anecdotes, or "it felt familiar"
interior claims; missing details get asked for, never manufactured. No
padding hollow paragraphs into confident emptiness. No edgy-slop ("let's be
real," forced hot takes): that's the same disease in a louder costume. No
detector-evasion for deception; where disclosure is required, disclose.

**Trust.** The scorer makes no network calls, spawns nothing, writes nothing.
Your drafts never leave your machine. Voice profiles are git-ignored by
design. Security review is one coffee: SECURITY.md plus 200 lines of Python.

**Install.**
`npx skills add manavmishra/ZeroSlop --global` (any agent), or
`/plugin marketplace add manavmishra/ZeroSlop` then
`/plugin install zero-slop@zero-slop` (Claude Code), or clone into your
skills directory. Then say "de-slop this."

github.com/manavmishra/ZeroSlop · MIT · built on petergyang/no-ai-slop,
blader/humanizer, isatimur/de-slop, hardikpandya/stop-slop, Wikipedia's
Signs of AI writing, and 15 detection papers cited in the repo.
