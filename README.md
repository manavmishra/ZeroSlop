# Zero Slop

<p align="center">
  <img alt="MIT" src="https://img.shields.io/badge/license-MIT-1B1D22">
  <img alt="tests" src="https://img.shields.io/badge/tests-CI%20gated-1E7A4C">
  <img alt="dependencies" src="https://img.shields.io/badge/dependencies-0-1E7A4C">
  <img alt="privacy" src="https://img.shields.io/badge/scorer-offline-1E7A4C">
  <img alt="version" src="https://img.shields.io/badge/version-2.4.0-2a78d6">
</p>

You used AI to help with your writing, and now it reads like a machine wrote every
word. You can hear it, and so can everyone who reads it. That machine sound has a name:
slop. On LinkedIn, it can get you accused of not thinking for yourself.

Zero Slop finds the slop in your draft and removes it without changing what you
actually said. It gives the draft a transparent surface score from 0 to 100, calculated
with explicit heuristics. It points to the words and structural signals that contribute
to the score, then rewrites the draft. The number is not the probability that AI wrote
the text. A copy desk fixes grammar, spelling, punctuation, and awkward phrasing. A
second editor then reads the copy aloud and fixes its flow and cohesion before Zero
Slop double-checks that every fact survived and nothing new slipped in.

![Zero Slop scoring a marketing sentence at 100, then its rewrite at 9.5](assets/demo.png)

That is a real before and after. The first sentence scores 100, which is as sloppy
as it gets. Six phrases account for the score, and the tool names each one. Remove
them, and the fact is clear: setup time dropped 40%. That is what slop usually is,
once you look: a real point buried under decoration.

Lower is better. In our test set, known-human writing lands between 9 and 21, while raw
AI drafts averaged 77. Read the list of flagged phrases first; the number is only a
summary.

## Who Zero Slop is for

Anyone who creates content and would rather not sound like a robot. A founder shipping
a launch post. A marketer with five posts due this week. A researcher whose paper
needs to stay formal, not get "humanized" into mush. An engineering team that wants
slop to fail a check the way a bug does. If AI helps you write and you want the result
to still sound like you, this is for you.

## Why Zero Slop matters now

For a while, sounding like AI mainly cost you credibility with the readers who
noticed. Platforms have started attaching product and policy consequences to it. In
July 2026, [LinkedIn added a “Seems like AI slop” reporting
signal](https://techcrunch.com/2026/07/30/linkedin-adds-a-button-to-report-ai-generated-slop/),
[Snap made wholly AI-generated Spotlight videos ineligible for
recommendation](https://newsroom.snap.com/rewarding-authentic-creativity-on-spotlight),
and [Substack gave readers a “Scan for AI text”
tool](https://support.substack.com/hc/en-us/articles/50891130623508-How-can-I-detect-AI-on-Substack).
[YouTube's monetization policy](https://support.google.com/youtube/answer/1311392?hl=en)
had already clarified in July 2025 that repetitive or mass-produced content was
ineligible under its existing rules.

Those changes have different effects: Snap and YouTube govern recommendations or
monetization, while LinkedIn and Substack give users new ways to report or assess
content. They do not create one universal reach penalty. Pangram Labs, an AI-detection
vendor, reported that 25.72% of long-form items in its
[opt-in data set of 1,002,627 social posts](https://www.pangram.com/blog/ai-in-your-feed)
were flagged as fully AI-generated; for long-form LinkedIn posts, the figure was over
40%. This was not a platform census. The data came from browser-extension users who
opted to share their scans. Still, the result helps explain why readers and platforms
are reacting.

## Try it

### Paste this into your agent

Give this prompt to Claude Code, Codex, Cursor, OpenCode, Warp, Zed, or any other
Agent Skills-compatible coding agent:

```text
Install or update Zero Slop from https://github.com/manavmishra/ZeroSlop for
this agent.

1. Identify the current agent and any active Zero Slop installations. Record the
   path, version, and install method of each one. Do not mix installation methods.
   If more than one active copy exists, report every path and ask which one to keep;
   do not delete any copy.
2. Use the native user-level installer when one exists. In Codex, invoke
   $skill-installer and install only the repository path `skills/zero-slop`. The
   repository also has a root source copy; installing both creates duplicate
   discovery. In Claude Code or Cowork, use the plugin marketplace's install or
   update flow. For a first install in any other supported agent, run:
   npx skills add manavmishra/ZeroSlop --global
3. For an update, use the existing install method. If the existing copy was installed
   with the third-party `skills` CLI, run:
   npx skills update zero-slop --global
   Preserve `ZERO_SLOP_HOME` (default: `~/.zero-slop`). Reflection evidence, the
   private detector-and-fix overlay, learning logs, and voice profiles live there.
   Never delete, replace, or copy that directory into the installation.
4. Install the complete runtime: `SKILL.md`, `references/`, `scripts/`, and `data/`.
   Do not substitute the README or single-file bundle unless this agent requires that
   format. Do not create a second copy inside the discovered skill directory; a
   plugin-owned `skills/zero-slop` directory is valid.
5. Verify that the installed `SKILL.md` version matches the repository and that every
   required runtime file and directory named in `SKILL.md` exists. User-created or
   optional paths, such as voice profiles, may remain absent until needed. Confirm
   that the agent can discover a skill named `zero-slop`. If Python is available,
   run `python3 scripts/calibrate.py --selftest` from the installed skill directory.
6. Report the install method, exact path, installed version, validation result, and
   whether I need to restart the agent or open a new session.

Do not claim success until verification passes. Do not modify the current project
or unrelated configuration. If a user-level install is impossible and you need to
fall back to a project-local install, ask me first.
```

### Install from the terminal

```bash
npx skills add manavmishra/ZeroSlop --global   # then open the agent and say "de-slop this"
```

The command detects supported agents on your machine and installs Zero Slop globally.
To target one agent, add `--agent` and name it (`claude-code`, `codex`, `cursor`,
`opencode`, `warp`, or `zed`). Drop `--global` for a project-local installation.

<details>
<summary>Claude Code plugin · ChatGPT · Codex · Claude.ai · manual clone</summary>

For Claude Code and Cowork, install the plugin:

```
/plugin marketplace add manavmishra/ZeroSlop
/plugin install zero-slop@zero-slop
```

ChatGPT and ChatGPT at Work: paste the single-file version into a Project's
instructions, or upload it as Custom GPT knowledge.

```bash
curl -sLO https://raw.githubusercontent.com/manavmishra/ZeroSlop/main/dist/zero-slop-single-file.md
```

Codex has a built-in installer for skills from other repositories. Invoke it, then
give it the repository and the user-level scope:

```text
$skill-installer
Install zero-slop from https://github.com/manavmishra/ZeroSlop as a user-level skill.
```

Codex discovers skill changes automatically. If the skill does not appear, restart
Codex. See OpenAI's [skill installation
guide](https://developers.openai.com/codex/skills/#install-curated-skills-for-local-use).

Claude.ai and Claude Desktop need a zip that contains only this skill. GitHub's green
"Download ZIP" button packages the whole repository, so Claude rejects it. Build the
right zip with these commands:

```bash
git clone https://github.com/manavmishra/ZeroSlop.git
python3 ZeroSlop/scripts/build_skill_zip.py     # writes ZeroSlop/dist/zero-slop.zip
```

Then upload `dist/zero-slop.zip` under Settings, Capabilities, Skills. The same file is
attached to the [latest release](https://github.com/manavmishra/ZeroSlop/releases/latest)
if you would rather download it.

For a manual Claude-compatible install:

```bash
git clone https://github.com/manavmishra/ZeroSlop.git ~/.claude/skills/zero-slop
```

The folder has to be named `zero-slop`. On Windows, clone into
`$env:USERPROFILE\.claude\skills\zero-slop`.

</details>

You can also run the scorer straight from the command line:

```bash
python3 scripts/slopscore.py --explain draft.md          # score it, and see every flagged phrase
python3 scripts/slopscore.py --gate 25 draft.md          # fail a build if the draft is too sloppy
python3 scripts/slopscore.py --fidelity draft.md new.md  # check the rewrite kept your facts
python3 scripts/slopscore.py --voice you draft.md        # score against your own writing style
```

The scorer needs no third-party packages, account, or server. A single
standard-library Python file does the scoring, and your writing never leaves your
machine. If Python is unavailable, the skill still runs from its written rules — you
only lose the number.

## How it works

Zero Slop measures the draft before it changes a word.

Four surface channels produce a score from 0 to 100. The pattern meter identifies
specific words and phrases. The other three use structural counts and rates to measure
rhythm, followability, and a combined formatting-and-register signal. Every result
points back to a quoted phrase or a document-level statistic you can inspect.

| Channel | What it measures |
|---|---|
| Pattern meter | 266 weighted patterns, a 96-word watchlist, and 25 words that count only in a salesy sentence |
| Rhythm | low variation in sentence length |
| Followability | comma pile-ups, clusters of long words, and sentences longer than 38 words |
| Formatting and register | em dash density, emoji, hashtags, heavy use of bold, and machine-formal language |

For social posts, Zero Slop reports paragraph shape separately; it does not change the
0-to-100 score. Changing a word to a synonym can remove a weighted phrase, but it
cannot fix the structural signals and may leave much of the score unchanged.

No single signal determines the result. Em dashes are common in good writing, so one
carries little weight on its own. A dash matters only when several independent signals
cluster in the same draft.

Word choice is also judged in context. *Leverage* and *robust* are ordinary in a
runbook but can become useful signals in promotional copy. "Elevated write volume" is
normal engineering language. The phrase "elevate
your brand with our seamless platform" is not.

Predictability sits outside the main score. Zero Slop hides a handful of words and asks
your assistant — whether Claude, GPT, or another supported model — to guess each one
from the words that come before it. When the original word keeps appearing among the
top three guesses, the prose may be too easy for a model to anticipate. This can expose
polished, generic writing that slipped past the pattern meter. It does not require
another model or service.

Editing starts with subtraction. The first pass removes stock phrases and fussy
formatting while leaving the substance alone. The second works on the argument and the
voice: what should lead, where a sentence needs room to breathe, and whether the result
sounds like an expert speaking to peers. Separating those jobs keeps a wording cleanup
from turning into a needless rewrite.

For important pieces, Zero Slop tries two or three different edits. One may cut harder,
another may keep more warmth, and a third may change the opening or order. Any version
that drops or adds a fact is out. Zero Slop chooses the cleanest of the rest and runs
the full verification.

Before Zero Slop returns anything, it compares the names, numbers, quotations, links,
and claims with the original. A copy editor fixes grammar, spelling, punctuation,
consistency, and awkward phrasing. A second editor then reads the copy aloud and fixes
anything that still sounds stiff, repetitive, or poorly joined. The finished piece is
scored and compared with the original once more. If a late fix changes the wording,
both editors see it again and all the checks run again. This repair loop stops after
three rounds. If a check still cannot pass without guessing, Zero Slop returns the best
version that completed both editorial passes while preserving the source's meaning. It
names the failed check and unresolved passage instead of calling the result fully
verified.

## It will not touch your facts

This is a common failure in rewriting tools: a smoother draft may invent a detail you
never wrote or quietly drop a number. Zero Slop treats that as the one thing it must
never do.

Before it calls a rewrite finished, the scripted fact-preservation check confirms that
every figure, name, quote, and link in the original survived and that none was added. A
separate judgment pass compares the claims and qualifiers, including statements about
the writer's feelings or experience, because software cannot reliably catch an
invented feeling. Both checks matter: a dropped number is conspicuous, but an invented
detail can read naturally enough to slip by. The safeguards exist because an early
version of the tool did exactly that, handing a writer a feeling they never expressed.

## Post-deployment online learning

Zero Slop can **reflect** on edits you make after it returns a draft. The technical
name is *post-deployment, human-in-the-loop online learning*. It is also a form of
continual learning: the detector gathers evidence from real edits after the skill has
been installed, then uses that evidence on later drafts.

Here is exactly what that means. When Zero Slop hands a draft back and you edit it
before publishing, it compares the two versions. A phrase you *cut* may be a tell it
missed; a flagged phrase you *kept* may be a false positive. Both become evidence, but
no detection rule or preferred fix becomes active on the strength of one edit pair.
A phrase becomes eligible only after the same cut appears across three content-distinct
edit pairs. The potential rule must also be new and pass a safety check against the
reference set of human writing. Single words need five edit pairs and enter as
context-dependent signals rather than universal tells.

Once it meets those requirements, Zero Slop can activate the change in a private local
learning file at
`$ZERO_SLOP_HOME/learned.json` (default: `~/.zero-slop/learned.json`). The scorer
reloads that file on every run, so the new evidence affects the next draft without
changing the installed skill or anyone else's detector. This is next-run adaptation,
not a remote service changing a draft while it is open. If the writer repeatedly
replaces the same tell in the same way, the file also remembers the fix as a private
preference after the same replacement appears in three content-distinct edit pairs.
The next rewrite can consult it with `learn.py --guide`, but uses it only when it
preserves the current meaning and facts.

Repeated false-positive evidence can lower a local weight. Reconfirmation keeps
detection rules and preferred fixes current. Without it, detection rules lose weight
after 18 months, while stale preferred fixes are retired. An author-specific voice
profile separately suppresses terms found in that writer's own work. The loop
therefore adapts both detection and fixing while keeping every learned change
inspectable and local.

```bash
python3 scripts/learn.py --reflect --produced out.md --shipped final.md --auto-apply
python3 scripts/learn.py --promote --apply     # activate eligible evidence locally
python3 scripts/learn.py --demote --apply      # lower repeatedly overruled patterns locally
python3 scripts/learn.py --confirm known-slop/ # keep local patterns current
python3 scripts/learn.py --decay               # reduce stale local patterns
python3 scripts/learn.py --guide               # show recurring local fix preferences
python3 scripts/learn.py --voice you --from ~/my-writing/   # teach it your style
python3 scripts/learn.py --stats               # see what it has learned
```

Human corrections provide feedback, but Zero Slop does not perform reinforcement
learning or RLHF. It does not retrain the host language model or alter its weights. It
updates an external, interpretable detector and a private rewrite memory. You can
inspect their patterns, evidence counts, weights, preferred fixes, provenance, and
decay dates. Shared changes still go through ordinary code review, regression tests,
versioning, and a release.

Separately, Zero Slop checks for a newer release once per session. It shows you the
one-line update if one exists. The check is a version query and nothing else; it never
sends the draft.

Online learning changes only private detection evidence, preferred fixes, and personal
voice profiles. It does not rewrite `SKILL.md` or silently alter the shared skill.

## What the benchmark can and cannot show

This is a small, synthetic comparison, not proof that one tool is best. We wrote 50
AI-heavy drafts across six kinds of writing and produced four rewrites of each: Zero
Slop, blader/humanizer, petergyang/no-ai-slop, and isatimur/de-slop. We recreated the
other projects' outputs from their published prompts instead of running their live
products. Only the Zero Slop rewrites were tuned against this benchmark's scorecard.
[hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) appears in the
detector chart below but was not part of the blinded comparison.

### Who did the judging

No human raters took part. The benchmark records identify the evaluators only as LLM
runs from one model family. Each of the two passes used five separate runs, one for each
ten-draft packet. The model received the writing brief, source draft, factual inventory,
and four rewrites labeled A through D. The method names were shuffled and hidden. It
scored each rewrite from 1 to 10 for human-likeness, voice, fidelity, writing craft, and
platform fit. It also flagged fabrication and selected the best and worst version. The
second pass used the same text and label mapping but fresh model runs.

The repository includes the packets, shuffle key, and resulting scores. It does not
preserve the exact judge model and version, inference settings, or full evaluation
prompt. That omission prevents an exact reproduction of the judging and limits what
the result can support.

The model selected Zero Slop as best for 32 of 50 drafts in the first pass and 23 in
the second. It selected blader/humanizer for 18 and 22. Across both passes, the counts
were 55 and 40, but the passes chose the same winner on only 26 of 50 drafts. Cohen's
kappa was 0.12, the confidence intervals overlapped, and the head-to-head difference
was not statistically significant (p = 0.15). These data show that the two systems were
competitive in this setup. They do not establish a general winner.

![Versions selected as best across two blinded LLM passes: Zero Slop 55, blader 40, no-ai-slop 5, de-slop 0](assets/bench-bestpicks.png)

The second chart measures how much of the AI register each rewrite leaves behind. Zero
Slop's own detector produces these numbers, so they are useful for checking the meter's
target, not for independently grading Zero Slop against other tools.

![AI register remaining after de-slop, lower is cleaner: Zero Slop 9.8 versus 15.7 to 23.4 for others, from 69.0 for the raw drafts](assets/bench-detector.png)

In a separate discrimination test across LinkedIn, blogs, Reddit, newsletters, and
short social posts, the scorer separated the obvious-slop samples from the known-human
samples without overlap. We wrote that test set ourselves. It is a regression check for
easy cases, not an accuracy estimate for writing in the wild. A separate 1,000-document
test guards speed; CI fails if the batch takes longer than 60 seconds. The full inputs,
rewrites, anonymized packets, raw ratings, and analysis scripts are in the
[benchmark harness](bench/).

## Built on good work

Zero Slop did not invent any of this. It builds on four open-source projects that
worked out the craft first: [petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop),
[blader/humanizer](https://github.com/blader/humanizer),
[isatimur/de-slop](https://github.com/isatimur/de-slop), and
[hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop). They proved that the
sound can be removed, and their lists of tells seeded ours. We added the score, the
fact-check, the copy desk, the read-aloud editor, and the learning loop — the parts
that let you measure a rewrite and trust the finished copy.

One distinction matters: detectors like Pangram and GPTZero answer a different question.
They estimate whether a machine wrote something; Zero Slop measures the AI register
left in the text. We do not tune rewrites to fool those detectors.

## What's next

- **A big, labeled test set.** It is what the remaining accuracy claims need.
  RAID, HC3, M4, and AuTextification are free and cover email, social, and blogs.
- **New signals that ignore vocabulary entirely.** The research
  ([NEULIF](https://arxiv.org/abs/2511.21744)) points to how often certain small words
  pair up and how sentence lengths vary. Neither can be removed simply with a
  thesaurus, and both need the test set above to tune.
- **Running the competitors live.** This will make the comparison a true head-to-head.

## Under the hood

Zero Slop has two operational loops. Editorial delivery turns the current draft into
finished copy. Online learning observes later published edits, checks the evidence
against its thresholds, and updates a private learning layer. Later evidence reconfirms
detection patterns and preferred fixes; without it, stale patterns decay and stale
fixes retire. The learning layer feeds both the pattern meter and the rewrite guide,
so it adapts slop detection and fixing.

![Zero Slop has two operational loops. Editorial delivery measures, diagnoses, rewrites, copy-edits, reads aloud, and verifies the final text. Online learning observes later published edits, checks the evidence against its thresholds, and updates a private learning layer. Later evidence reconfirms detection patterns and preferred fixes; stale patterns decay, and stale fixes retire. The private layer feeds both the pattern meter and the rewrite pass.](assets/engine.svg)

```
SKILL.md                    the instructions the AI agent follows
scripts/slopscore.py        the scorer, plain Python, no libraries
scripts/predictability.py   host-model predictability probe, reported separately
scripts/rerank.py           best of N — choose the cleanest version that keeps the source intact
scripts/learn.py            the learning loop and your style profile
scripts/calibrate.py        retune from a corpus; retire stale tells
scripts/version_check.py    the once-a-session update check
data/patterns.json          the 266 tells, the watchlist, the context words
data/corpus/must-not-flag/  human writing the tool must never flag
references/readalong.md     the final pass for spoken flow and cohesion
references/copy-desk.md     the grammar, spelling, and style pass before read-aloud finalization
tests/test_all.py           correctness, safety, concurrency, packaging, and speed tests
```

Run `python3 tests/test_all.py` and `python3 scripts/calibrate.py --selftest`. The tests
cover the scorer, the learning safeguards, the retirement of old tells, and speed.
Each requirement slipped once, so a set of tripwires now checks that the numbers here
match the data, the charts match the benchmark, the packaged copies stay current, and
none of your writing ever enters a tracked file.

## Thanks

Zero Slop builds on the four MIT-licensed projects above,
Wikipedia's [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing),
and Kagi's [SlopStop](https://help.kagi.com/kagi/features/slopstop.html), which landed on
two of the same ideas: require several signals before judging, and let people appeal.
The thirteen research papers behind the design are listed in
[references/evidence.md](references/evidence.md). Three carry the most weight. One
study finds that detectors read a model's training style rather than the machine itself
(arXiv:2605.19516). Kobak et al. describe a method for spotting overused words
(arXiv:2406.07016). A third study shows that detectors wrongly flag more than half of
non-native English writers (arXiv:2304.02819). That last finding is why a non-native
sample sits in our safety set.

MIT.
