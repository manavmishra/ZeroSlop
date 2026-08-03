# Zero-Slop

A portable agent skill that turns AI-sounding drafts — LinkedIn posts, blogs,
newsletters, tweets, emails, research abstracts — into prose that reads as
written by a sharp human, **with measurable proof**. It is the only de-slop
skill with a statistical scorer and a quantitative pass/fail gate: every
rewrite ships with before/after metrics.

Plain Markdown + one dependency-free Python script, so it runs in any harness
that supports skill-style instructions (Claude Code, claude.ai, Codex-style
agents, or copy-paste).

## Why another de-slop skill

The research says detectors (and readers) key on the *post-training register*:
the most-probable phrasing, uniform sentence rhythm, a few hundred
over-represented style words, template structure, relentless even polish. All
of it lives in the surface realization of the text — which means all of it is
removable while preserving meaning exactly. Zero-slop operationalizes that as
a loop: **Measure → Diagnose → Rewrite → Verify → Learn**, with an
evidence-ranked rewrite ladder ordered by measured detection-signal strength
(15 papers, cited in [references/evidence.md](references/evidence.md)).

Benchmarked blind against the three best-known alternatives on 50 AI-typical
drafts (5 independent blind judges, shuffled labels, 5 dimensions):

| | **zero-slop** | blader/humanizer | petergyang/no-ai-slop | isatimur/de-slop |
|---|---|---|---|---|
| Judge composite (1–10) | **8.01** | 7.82 | 6.96 | 6.35 |
| Human-likeness | **7.84** | 7.60 | 6.30 | 5.00 |
| "Which would you publish" wins | **32/50** | 18/50 | 0 | 0 |
| Objective AI-likelihood (drafts start at 76) | **10.9** | 18.7 | 19.4 | 39.7 |

## Installation

### Skills CLI

```bash
npx skills add manavmishra/ZeroSlop --global
```

Omit `--global` for a project-local install. Update later with
`npx skills update zero-slop --global`.

### Claude Code plugin

```
/plugin marketplace add manavmishra/ZeroSlop
/plugin install zero-slop@zero-slop
```

### Codex / OpenAI-compatible agents

The repo ships `.codex-plugin/plugin.json`, `agents/openai.yaml`, and
`AGENTS.md`, so Codex-style harnesses can load it directly. The skill is
harness-neutral: the runtime artifact is `SKILL.md`, and when `python3`
isn't available the skill degrades gracefully to its reference lists and
self-rubric instead of the metered gate.

### Manual (any harness)

```bash
git clone https://github.com/manavmishra/ZeroSlop.git ~/.claude/skills/zero-slop
```

Or copy the repo into wherever your harness looks for skills. The runtime
artifact is `SKILL.md`; `scripts/`, `data/`, and `references/` travel with it.

### claude.ai

Zip the repo (or download the GitHub zip) and upload it under
Settings → Capabilities → Skills.

## Usage

Once installed, the skill triggers on natural phrasing:

- "Humanize this draft" / "de-slop this" / "this reads like ChatGPT — fix it"
- "Make this LinkedIn post not sound like AI"
- "Run a slop check on this post" (detect-only: metrics + named tells, no rewrite)

What you get back: the rewritten text, before → after metrics (AI-likelihood,
burstiness, tell count), a change log naming the patterns fixed, and flags for
spans that need a real fact from you — the skill never invents one.

### Standalone scorer

The statistical scorer works without any AI, as a plain CLI:

```bash
# score a file
python3 scripts/slopscore.py --explain draft.md

# score whatever is on the clipboard (macOS)
pbpaste | python3 scripts/slopscore.py --explain

# machine-readable
python3 scripts/slopscore.py --json draft.md

# research/professional prose (formal register is native there)
python3 scripts/slopscore.py --formal abstract.txt
```

Output: AI-likelihood 0–100 with a band (clean / suspect / slop-likely /
slop), burstiness, tell density, and every hit quoted with its pattern name
and weight. Calibration: raw LLM drafts average ~76; strong human writing
lands 9–29.

## How it works

1. **Measure** — the scorer computes weighted tell density (~60 patterns),
   LLM-lexicon hits, burstiness (sentence-length variance), and formatting
   densities. Clusters convict; singles don't.
2. **Diagnose** — judgment the regex can't make: the removal test for hollow
   spans, a facts inventory that must survive verbatim, and 3–5 voice signals
   to preserve.
3. **Rewrite** — the evidence ladder, strongest detection signal first:
   substance → order → rhythm → register → lexicon → formatting, with
   platform modules (LinkedIn, X, email, blog, newsletter, research).
4. **Verify** — quantitative gate (≤25 general, ≤20 LinkedIn, ≤35 email;
   burstiness ≥0.45) plus fidelity and hostile-editor checks. Fail → iterate,
   max 3 passes, then flag honestly.
5. **Learn** — new tells append to `data/learned.json` (merged at runtime, no
   code change); false positives get weight adjustments; per-user voice
   profiles accumulate in `data/voices/` (git-ignored — personal).

Hard rules: never invent facts (experiential claims included), flag hollow
spans instead of padding them, no over-correction (edgy-slop is still slop),
and honest use only — this skill improves writing; it refuses
disclosure-evasion and impersonation.

## Repo structure

```
SKILL.md                     the skill (runtime artifact)
scripts/slopscore.py         statistical scorer (stdlib-only Python)
data/patterns.json           weighted tell patterns + lexicon
data/learned.json            continuous-learning overlay
data/learned-log.md          dated log of taxonomy changes
references/tells.md          67-tell taxonomy with fixes
references/rewrite-moves.md  the positive program (the ladder, expanded)
references/platforms.md      LinkedIn / X / email / blog / newsletter / research
references/overcorrection.md edgy-slop catalogue + what NOT to flag
references/evidence.md       the research basis (papers + detector mechanics)
```

## Credits

Zero-slop conforms to the [Agent Skills standard](https://agentskills.io) — the same SKILL.md format runs in Claude Code, Codex, OpenCode, and any spec-compatible harness.

Zero-slop is a synthesis, and stands on prior work it gratefully credits:
[petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop) (MIT),
[blader/humanizer](https://github.com/blader/humanizer) (MIT),
[isatimur/de-slop](https://github.com/isatimur/de-slop) (MIT),
[hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) (MIT),
Wikipedia's [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)
(WikiProject AI Cleanup), Paul Graham's writing essays, and the academic
detection literature cited in
[references/evidence.md](references/evidence.md) (Kobak et al., Liang et al.,
Juzek & Ward, DetectGPT, Binoculars, GPT-who, RAID, DIPPER, Reinhart et al.,
Herbold et al., and others).

## License

[MIT](LICENSE)
