# Canonical submission copy

One source for every directory form, so the listing text stops being improvised
per site. Copy from here; do not rewrite in the form field.

Every claim below is checkable in the repository. Keep it that way: a directory
listing is the first thing a sceptical reader checks against the README.

Score this file before changing it:

```bash
python3 scripts/slopscore.py --explain growth/submission-copy.md
```

---

## Name

Zero Slop

## Tagline, under 40 characters

The anti-slop editor for AI writing.

## One-liner, under 60 characters

Score AI-sounding writing 0-100. Fix it. Keep every fact.

## One-liner, under 100 characters

An open-source skill that scores AI-sounding prose 0-100 and rewrites it without losing a fact.

## Short description, about 50 words

Zero Slop is a free Agent Skill that scores your writing 0-100 for AI-sounding
language, names the exact phrases behind the score, and rewrites them. A local
fact gate rejects any version that adds or drops a name, number, quotation, or
link. It runs inside Claude Code, Codex, Cursor, Warp, Zed, and OpenCode.

## Description, about 150 words

You used AI to help with a draft and it came back sounding generic. Zero Slop
finds that and strips it out without changing what you said.

It is a skill, not a model. The AI assistant you already use does the editing;
Zero Slop supplies the method and the local checks. A standard-library Python
scorer gives the draft a 0-100 writing score and lists the phrases, rhythm
problems, and formatting that raised it. Separate copy-desk and read-aloud
passes follow, and a fact gate rejects any rewrite that loses a number or
invents one.

Nothing is uploaded. The scorer runs offline, needs no account, and has zero
runtime dependencies. On a public 18-draft benchmark it moved a mean score of
76.3 to 16.4 with every fact check passing.

Free and MIT-licensed. Install with one command.

## Description, about 300 words

You used AI to help with a draft, and the result sounds like a machine wrote it.
Readers notice. That machine sound has a name: slop.

Zero Slop is an Agent Skill rather than an AI model. Claude, GPT, or another
compatible model in your assistant does the editing; Zero Slop supplies the
method and the local checks. Seven roles make up one workflow. A local scorer
finds exact phrases, mechanical rhythm, and distracting formatting, then
explains the 0-100 writing score it produced. Your assistant interprets the
draft and rewrites it. A local fact gate rejects any version that adds or drops
a name, number, quotation, or link. Fresh passes handle copy editing and a
read-aloud check. Local tools and your assistant then compare the finished text
against the source.

The score describes the writing, not the author. In the test sets, human samples
scored 9 to 21 and unedited AI drafts averaged 77, which are reference points
rather than boundaries.

The evidence is public and reproducible. Zero Slop scored 7,627 abstracts from
the MIT-licensed RAID+ dataset, re-scored all 2,187 Beemo records, and published
an 18-draft comparison against four other open-source editors: a mean of 76.3
before, 16.4 after, with 18 of 18 fact checks passing. The scorer handles 1,000
documents in 2.0 seconds on one Apple silicon Mac.

Privacy is structural, not a policy. The scorer uses only Python's standard
library, runs offline, and never transmits a draft. Zero Slop can also learn
privately from edits you make afterwards, but a phrase must be cut from three
unrelated pieces before it becomes a rule, and those rules stay on your machine.

Free, MIT-licensed, and installed with one command in Claude Code, Codex,
Cursor, Warp, Zed, OpenCode, or any assistant that reads SKILL.md.

## Install command

```
npx skills add manavmishra/ZeroSlop --global
```

## Links

- Website: https://zero-slop.ai
- Source: https://github.com/manavmishra/ZeroSlop
- Latest release: https://github.com/manavmishra/ZeroSlop/releases/latest
- Free checker page: https://zero-slop.ai/ai-slop-checker/
- Benchmark detail: https://github.com/manavmishra/ZeroSlop/tree/main/bench
- Press assets: https://zero-slop.ai/press/

## Pricing

Free. Open source under the MIT License. No account, no server, no paid tier.

## Categories and tags

Primary category: Developer Tools. Secondary: Writing, Productivity.

Tags: ai-writing, writing-assistant, editing, proofreading, humanizer,
developer-tools, open-source, cli, agent-skill, claude-code, privacy, offline.

Never select an "AI detector" or "AI checker" category, even where a directory
offers one and it would win traffic. See "What not to claim" below.

## Author

Manav Mishra. Machine learning in production, from Microsoft's first ML spam
filtering and SmartScreen anti-phishing to agentic AI.
https://zero-slop.ai/about/

## Facts a reviewer may check

- 7,627 RAID+ abstracts scored; overall mean 19.6.
- 2,187 Beemo records: 30.2 raw model output, 25.3 expert edit, 20.0
  independent human answer.
- 18-draft workflow comparison: 76.3 original, 16.4 after Zero Slop, 18/18
  passing all checks.
- 1,000 documents in 2.0147 seconds (496.4 per second) on one Apple silicon Mac.
- Zero runtime dependencies; Python standard library only.
- MIT licence; every benchmark reproducible from the commands in the README.

## What not to claim

Zero Slop does not detect authorship and must never be filed under AI detection.
The score describes writing, not who wrote it. Do not describe the private
learning as retraining, reinforcement learning, or RLHF; it updates local rules
and nothing else. Do not quote a productivity number the repository does not
support.
