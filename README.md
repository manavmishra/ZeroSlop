# Zero-Slop: the AI slop remover that proves it worked

Turn AI-sounding drafts into writing people actually finish reading. Zero-Slop
detects the tells of machine-written prose (the em-dash rhythm, the "delve"
vocabulary, the announcement voice), rewrites your draft in an expert human
register, and then shows you before/after scores from its built-in statistical
detector. No other humanizer, de-slop tool, or AI-writing cleaner does that
last part. The last part is the point.

**One command. Any agent. Fully offline.**

```bash
npx skills add manavmishra/ZeroSlop --global
```

## The 30-second demo

A real LinkedIn draft, before:

> Enterprise AI value has too often compounded inside individual workflows,
> leaving a widening gap between the employees building leverage and the
> organizations trying to scale it.

**Scored 45.7/100, "suspect."** No emoji, no obvious buzzwords, and it still
reads like a press release wrote it. The detector flagged the stock opener;
the judgment pass caught the buried lede.

After one pass through Zero-Slop:

> 6x. That's how many more messages frontier users send than the median
> employee, and it's OpenAI's own telemetry in its new State of Enterprise AI
> report, not a survey.

**Scored 9.5/100, "clean."** Same facts. Nothing invented. The number moved
to the first word, where it belongs.

(We practice what we ship. This README's prose scores 13.3/100, clean, on
its own detector. Score the raw file and you'll get 82.9 — because the
README quotes the tells it teaches, and a regex can't tell mention from
use. That gap is the whole design lesson: the meter flags, judgment
decides. Run it yourself: `python3 scripts/slopscore.py README.md`.)

## Why AI writing sounds like AI (the science)

Researchers measured it. After ChatGPT launched, "meticulous" appeared 34.7x
more often in scientific abstracts, "delve" spiked so hard it became a meme,
and detectors like GPTZero learned to spot machine text from two features:
predictable word choice and uniform sentence rhythm. The deeper finding: base
models score ~98% human on commercial detectors. It's the *post-training
polish* that gets flagged. Which means the "AI voice" lives entirely on the
surface of the text, and a disciplined rewrite can remove it without touching
your meaning. Fifteen papers behind this sit in
[references/evidence.md](references/evidence.md).

Zero-Slop turns that research into a five-step loop:

1. **Measure.** A stdlib-Python scorer computes weighted tell density,
   burstiness (sentence-length variance), LLM-lexicon hits, and formatting
   noise, then squashes them into an AI-likelihood score from 0 to 100.
2. **Diagnose.** The judgment a regex can't make: hollow paragraphs, buried
   hooks, the facts that must survive verbatim, the voice worth keeping.
3. **Rewrite.** Two passes. Strip the tells. Then build toward an expert
   voice: a practitioner writing for peers, authority earned by specifics.
4. **Verify.** A hard gate. LinkedIn posts must score ≤20 with zero
   em-dashes, zero emoji, zero hashtag clusters, burstiness at 0.45 or higher.
   Fail means iterate. Still failing after three passes, it tells you the truth instead of faking it.
5. **Learn.** Every miss becomes a new pattern in `data/learned.json`. The
   detector you install gets sharper the more the community uses it.

## Benchmarked, blind, reproducible

We tested Zero-Slop against every major alternative: 50 AI-typical drafts
across LinkedIn, blogs, newsletters, tweets, emails, and research abstracts,
scored by independent blind judges on shuffled labels:

| | **Zero-Slop** | blader/humanizer | petergyang/no-ai-slop | isatimur/de-slop |
|---|---|---|---|---|
| Judge composite (1–10) | **8.01** | 7.82 | 6.96 | 6.35 |
| Human-likeness | **7.84** | 7.60 | 6.30 | 5.00 |
| Voice / point of view | **7.54** | 6.82 | 5.42 | 4.96 |
| "Which would you publish?" wins | **32/50** | 18/50 | 0 | 0 |
| Detector score after rewrite (drafts start at 76) | **10.9** | 18.7 | 19.4 | 39.7 |

A second round against hardikpandya/stop-slop and a stacked two-skill
pipeline is in the changelog. Every scorecard ships with its methodology; if
you think the judging was wrong, rerun it. The whole pipeline is reproducible.

## What Zero-Slop refuses to do

The fastest way to "humanize" text is to invent a personal anecdote. That's
not humanizing, it's lying, and it's the trap most tools fall into. Hard
rules, enforced in the skill and checked by our judges:

- **No invented facts.** No fake numbers, names, war stories, or "by test
  day it felt familiar" interior claims. Missing a good detail? It asks you
  for a real one.
- **No hollow-span padding.** A paragraph with no point gets flagged, not
  reworded into confident emptiness.
- **No edgy-slop.** "Let's be real," forced hot takes, and staccato drama are
  AI tells in a different costume. The over-correction catalogue is a
  first-class part of the skill.
- **No detector-evasion for deception.** Zero-Slop improves writing. It
  refuses disclosure-evasion and impersonation.

## Trust the thing you're installing

Read [SECURITY.md](SECURITY.md), then read the scorer itself (~200 lines).
Standard library only. Zero network calls. Zero dependencies. Your drafts
never leave your machine. Voice profiles are git-ignored so personal data
can't ship by accident. An enterprise security review of this repo takes one
coffee.

## Install

**Skills CLI (any agent, recommended):**

```bash
npx skills add manavmishra/ZeroSlop --global
```

**Claude Code plugin:**

```
/plugin marketplace add manavmishra/ZeroSlop
/plugin install zero-slop@zero-slop
```

**Codex / OpenAI-compatible agents:** ships with `.codex-plugin/plugin.json`,
`agents/openai.yaml`, and `AGENTS.md`. **Manual:** clone into your skills
directory (name the folder `zero-slop`). **claude.ai:** upload the repo zip
under Settings → Capabilities → Skills. Built on the
[Agent Skills standard](https://agentskills.io), so one artifact runs
everywhere.

Then say, in your agent of choice: *"de-slop this"*, *"humanize this
draft"*, *"make this post not sound like AI"*, or *"score this"* for
detect-only mode.

## Use the detector standalone

```bash
pbpaste | python3 scripts/slopscore.py --explain   # score your clipboard (macOS)
python3 scripts/slopscore.py --json draft.md        # machine-readable
python3 scripts/slopscore.py --formal abstract.txt  # research register
python3 scripts/slopscore.py --predict draft.md     # + trained ML channel
```

Every hit comes back as a quote with a pattern name and weight. Calibration: raw LLM
drafts average ~76/100; strong human writing lands 9–29.

## FAQ

**Is this an AI detector bypass?** No. Detectors flag the post-training
register; Zero-Slop removes that register by making the writing better: specific, rhythmic, committed. If your context requires AI
disclosure, disclose.

**Why do LLMs overuse "delve" and em-dashes?** Preference tuning (RLHF)
rewards a polished formal register; studies trace the vocabulary spike
directly to it. Era matters: "delve" peaked in 2024, and newer models
over-use "enhance/highlight/showcase" instead, which is why the pattern
database is versioned and community-updated.

**Are em-dashes really an AI tell?** Density is. One em-dash doing real work
is fine everywhere except LinkedIn, where readers now pattern-match any
em-dash to ChatGPT. The platform modules encode exactly this kind of
context.

**Will it flatten my voice?** A writing sample outranks every rule in the
skill. If dashes and "honestly" are how you really write, they stay.

**Found a tell it missed?** Open a PR adding a regex to `data/learned.json`
with a line in `data/learned-log.md`. That's the whole contribution process.
The taxonomy is community property.

## Star this repo if…

…you've ever deleted a draft because it "sounded like ChatGPT," rewritten an
em-dash out of embarrassment, or watched a good idea die under "I'm excited
to announce." Stars are how other people find the way out.

## Credits

Zero-Slop is a synthesis, and stands on prior work it gratefully credits:
[petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop),
[blader/humanizer](https://github.com/blader/humanizer),
[isatimur/de-slop](https://github.com/isatimur/de-slop),
[hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) (all
MIT), Wikipedia's
[Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing),
Paul Graham's writing essays, and the detection literature (Kobak, Liang,
Juzek & Ward, DetectGPT, Binoculars, GPT-who, RAID, DIPPER, Reinhart,
Herbold, and others) cited in
[references/evidence.md](references/evidence.md).

## License

[MIT](LICENSE). Take it, fork it, ship it. Just keep the credits.
