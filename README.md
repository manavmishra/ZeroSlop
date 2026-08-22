# Zero Slop

<p align="center">
  <img alt="MIT" src="https://img.shields.io/badge/license-MIT-1B1D22">
  <img alt="tests" src="https://img.shields.io/badge/tests-75%20passing-1E7A4C">
  <img alt="dependencies" src="https://img.shields.io/badge/dependencies-0-1E7A4C">
  <img alt="offline" src="https://img.shields.io/badge/network-none-1E7A4C">
  <img alt="version" src="https://img.shields.io/badge/version-2.3.4-2a78d6">
</p>

You used AI to help with your writing, and now it reads like a machine wrote every
word. You can hear it, and so can everyone who reads it. There is even a word for that
machine sound: slop. On LinkedIn, that sound can get you accused of not thinking for
yourself.

Zero Slop finds the slop in your draft and removes it without changing what you
actually said. It scores the writing from 0 to 100, points to the exact words
dragging it down, and rewrites them. A copy desk fixes grammar, spelling,
punctuation, and awkward phrasing. A second editor then reads the copy aloud and
fixes its flow and cohesion before Zero Slop double-checks that every fact survived
and nothing new slipped in.

![Zero Slop scoring a marketing sentence at 100, then its rewrite at 9.5](assets/demo.png)

That is a real before and after. The first sentence scores 100, which is as sloppy
as it gets. Six phrases are doing the damage, and the tool names each one. Take them
out, and one thing is left standing: setup time dropped 40%. That is what slop usually
is, once you look: a single real fact buried under decoration.

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

1. Identify the current harness and any active Zero Slop installation, including
   its path, version, and install method. Do not mix installation methods. If more
   than one active copy exists, report every path and ask which one to keep; do not
   delete any copy.
2. Use the native user-level installer when one exists: invoke $skill-installer in
   Codex; use the plugin marketplace's install or update flow in Claude Code or
   Cowork. For a first install in any other supported Agent Skills harness, run:
   npx skills add manavmishra/ZeroSlop --global
3. For an update, use the existing install method. If the existing copy was installed
   with the third-party `skills` CLI, run:
   npx skills update zero-slop --global
   Preserve ZERO_SLOP_HOME (default: ~/.zero-slop) and inspect the installed runtime
   for locally modified data/learned.json or data/learned-log.md. Do not overwrite or
   delete local learning. If those files cannot be merged safely, make a recoverable
   backup and ask before continuing.
4. Install the complete runtime: SKILL.md, references/, scripts/, and data/. Do not
   substitute the README or single-file bundle unless this harness requires that
   format. Do not create a second copy inside the discovered skill directory; a
   plugin-owned skills/zero-slop directory is valid.
5. Verify that the installed SKILL.md version matches the repository and that every
   required runtime file and directory named by SKILL.md exists. User-created or
   optional paths, such as voice profiles, may remain absent until needed. Confirm
   that the harness can discover a skill named zero-slop. If Python is available,
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
the assistant already in use, whether Claude, GPT, or another supported model, to guess
each one from the words that come before it. When the original word keeps appearing
among the top three guesses, the prose may be too easy for a model to anticipate. This
can expose polished, generic writing that slipped past the pattern meter. It does not
require another model or service.

Editing starts with subtraction. The first pass removes stock phrases and fussy
formatting while leaving the substance alone. The second works on the argument and the
voice: what should lead, where a sentence needs room to breathe, and whether the result
sounds like an expert speaking to peers. Giving those jobs separate passes keeps a
wording cleanup from turning into a needless rewrite.

For important pieces, Zero Slop tries two or three different edits. One may cut harder,
another may keep more warmth, and a third may change the opening or order. Any version
that drops or adds a fact is out. Zero Slop chooses the cleanest of the rest and runs
the full verification.

Before Zero Slop returns anything, it checks that the names, numbers, quotations, links,
and claims still match the original. A copy editor fixes grammar, spelling, punctuation,
consistency, and awkward phrasing. A second editor then reads the copy aloud and fixes
anything that still sounds stiff, repetitive, or poorly joined. The finished piece is
scored and compared with the original once more. If a late fix changes the wording,
both editors see it again and all the checks run again. This repair loop stops after
three rounds. If a check still cannot pass without guessing, Zero Slop returns the
strongest version that keeps the original meaning and tells you exactly what remains
unresolved.

## It will not touch your facts

This is where most humanizers fail. To sound more human, they will invent a detail you
never wrote, or quietly drop a number to smooth a sentence. Zero Slop treats that as the
one thing it must never do.

Before it calls a rewrite finished, the scripted fidelity check confirms that every
figure, name, quote, and link in the original survived and that none was added. A
separate judgment pass compares the claims, qualifiers, and interior states because
software cannot reliably catch an invented feeling. Both checks matter: a dropped
number is conspicuous, but an invented detail can read naturally enough to slip by.
The safeguards exist because an early version of the tool did exactly that, handing a
writer a feeling they never expressed.

## It gets sharper the more you use it

After the rewrite comes the part most tools skip: it **reflects** on what you did next.
Most tools are frozen the day they ship. This one learns from you.

Here is exactly what that means. When Zero Slop hands a draft back and you edit it
before publishing, it compares the two versions. A phrase you *cut* may be a tell it
missed; a flagged phrase you *kept* may be a false positive. Both become evidence, but
nothing changes on the strength of one document. A phrase becomes a candidate rule only
after independent cuts from three distinct documents, and promotion still requires
review. Repeated false-positive evidence can lower a pattern's weight. Global patterns
that go unconfirmed for more than 18 months can decay, while an author-specific voice
profile suppresses terms found in that writer's own work. The loop learns in both
directions instead of treating every edit as a universal rule.

```bash
python3 scripts/learn.py --reflect --produced out.md --shipped final.md
python3 scripts/learn.py --promote --apply     # turn agreed-on phrases into rules
python3 scripts/learn.py --demote --apply      # lower repeatedly overruled patterns
python3 scripts/learn.py --voice you --from ~/my-writing/   # teach it your style
python3 scripts/learn.py --stats               # see what it has learned
```

It keeps itself current, too. Each session, it checks for a newer release and shows you
the one-line update if one exists — a version query and nothing else, so your writing
still never leaves your machine.

Better rewrite instructions improve every future rewrite. That tuning runs on a score,
not on taste. It uses Microsoft's
[SkillOpt](https://github.com/microsoft/SkillOpt), which treats `SKILL.md` — the rewrite
instructions — as text it may edit. SkillOpt runs the skill on a batch of drafts,
scores each rewrite with a reward shipped in this repo (`bench/skillopt/`), makes a
small edit to the instructions, and runs the skill again. It keeps the edit only when it
*strictly improves* the score on a held-out set of drafts that the edit never saw. The
reward keeps it honest: fidelity is a separate pass/fail signal, so an edit that
de-slops harder by dropping or inventing a fact scores zero, however clean it reads.
The output is `best_skill.md`, a better instruction set rather than a one-draft patch.
SkillOpt tuning is a maintainer workflow because running the rewrites requires a model;
it does not run during local, offline use. The learning loop sharpens the meter, while
SkillOpt sharpens the rewrite instructions.

## Does it actually work

We ran it head to head against three of the four tools it builds on: fifty AI-heavy
drafts across six kinds of writing, each rewritten by every tool, then scored by judges
who could not see which tool produced which version. The fourth, stop-slop, appears in
the detector comparison below but was not included in the blind judging packets. Treat
this as a careful study rather than a verdict. We reproduced the competitors' outputs
from their published prompts instead of running their live products, and only our
rewrites were tuned against a scorecard, so the field is not perfectly level.

Across 100 blind picks, judges preferred the Zero Slop version more often than any
other.

![Best-picks, pooled over 100 blind verdicts: Zero Slop 55, blader 40, no-ai-slop 5, de-slop 0](assets/bench-bestpicks.png)

The result is narrower than the bar looks. In the pooled count, Zero Slop led blader's
humanizer 55 picks to 40 and clearly beat the other two. The two rounds told different
stories, however: Zero Slop received 32 picks in the first and 23 in the second, while
blader received 18 and 22. Winner agreement across rounds was 52% (Cohen's kappa 0.12),
and the confidence intervals overlapped. Treat the pooled lead as suggestive, not
decisive.

A steadier measure is how much of the AI register each tool removes. This is scored by
Zero Slop's own detector, so read it as register stripped, not an independent grade.

![AI register remaining after de-slop, lower is cleaner: Zero Slop 9.8 versus 15.7 to 23.4 for others, from 69.0 for the raw drafts](assets/bench-detector.png)

The last test is the one a writer should care about most: can the tool tell obvious
slop from obvious human writing? Across LinkedIn, blogs, Reddit, newsletters, and short
social posts it separated the two every time, with no overlap. We wrote both piles,
though, so it shows the tool agreeing with an obvious call, not that it will judge every
draft in the wild. A separate 1,000-document performance test guards speed; CI fails if
the batch takes longer than 60 seconds.


## Built on good work

Zero Slop did not invent any of this. It builds on four open-source projects that
worked out the craft first: [petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop),
[blader/humanizer](https://github.com/blader/humanizer),
[isatimur/de-slop](https://github.com/isatimur/de-slop), and
[hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop). They proved that the
sound can be removed, and their lists of tells seeded ours. We added the score, the
fact-check, the copy desk, the read-aloud editor, and the learning loop — the parts
that let you measure a rewrite and trust the finished copy.

Worth heading off one confusion: detectors like Pangram and GPTZero answer a different
question. They estimate whether a machine wrote something; Zero Slop measures the AI
register left in the text. We do not tune rewrites to fool those detectors.

## What's next

- **A big, labeled test set.** It is what the remaining accuracy claims need.
  RAID, HC3, M4, and AuTextification are free and cover email, social, and blogs.
- **New signals that ignore vocabulary entirely.** The research
  ([NEULIF](https://arxiv.org/abs/2511.21744)) points to how often certain small words
  pair up and how sentence lengths vary. Neither can be removed simply with a
  thesaurus, and both need the test set above to tune.
- **Running the competitors live.** This will make the comparison a true head-to-head.

## Under the hood

![Zero Slop workflow: four surface channels produce a traceable score, while a fifth tests predictability. The draft is diagnosed, rewritten, reranked, checked for score and fidelity, copy-edited, finalized by a read-aloud editor, then rechecked. Feedback and SkillOpt loops improve the meter and instructions.](assets/engine.svg)

```
SKILL.md                    the instructions the AI agent follows
scripts/slopscore.py        the scorer, plain Python, no libraries
scripts/predictability.py   the model channel — cloze probe, answered by the host model
scripts/rerank.py           best of N — pick the cleanest faithful rewrite
scripts/learn.py            the learning loop and your style profile
scripts/calibrate.py        retune from a corpus; retire stale tells
scripts/version_check.py    the once-a-session update check
data/patterns.json          the 266 tells, the watchlist, the context words
data/corpus/must-not-flag/  human writing the tool must never flag
references/readalong.md     the final pass for spoken flow and cohesion
references/copy-desk.md     the grammar, spelling, and style pass before read-aloud finalization
bench/skillopt/             the reward and harness for tuning SKILL.md
tests/test_all.py           75 tests
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
two of the same ideas: wait for a few tells before convicting, and let people appeal.
The thirteen research papers behind the design are listed in
[references/evidence.md](references/evidence.md). Three carry the most weight: the
finding that detectors read a model's training style rather than the machine itself
(arXiv:2605.19516), the method for spotting overused words (Kobak et al.,
arXiv:2406.07016), and the study showing that detectors wrongly flag more than half of
non-native English writers (arXiv:2304.02819). That last finding is why a non-native
sample sits in our safety set.

MIT.
