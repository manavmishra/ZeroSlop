# Zero Slop

<p align="center">
  <img alt="MIT" src="https://img.shields.io/badge/license-MIT-1B1D22">
  <img alt="tests" src="https://img.shields.io/badge/tests-63%20passing-1E7A4C">
  <img alt="dependencies" src="https://img.shields.io/badge/dependencies-0-1E7A4C">
  <img alt="offline" src="https://img.shields.io/badge/network-none-1E7A4C">
  <img alt="version" src="https://img.shields.io/badge/version-1.6.0-2a78d6">
</p>

You used AI to help you write, and now the writing sounds like AI. You can hear it,
and so can everyone who reads it. There is even a word for that sound: slop. On
LinkedIn it gets you accused of not thinking for yourself.

Zero Slop finds that sound in your draft and takes it out, without changing what you
actually said. It gives the writing a score from 0 to 100, points at the exact words
dragging it down, and rewrites them. Then it double-checks that it kept every fact
you had and invented nothing.

![Zero Slop scoring a marketing sentence at 100, then its rewrite at 9.5](assets/demo.png)

That is a real before and after. The first sentence scores 100, which is as sloppy
as it gets. Six phrases are doing the damage, and the tool names each one. Take them
out and the only thing worth keeping is left standing: setup time dropped 40%. That
is what slop usually is once you look, a single real fact buried under decoration.

## Who it is for

Anyone who writes under their own name and would rather not sound like a robot. A
founder shipping a launch post. A marketer writing five things a week. A researcher
whose paper needs to stay formal, not get "humanized" into mush. An engineering team
that wants slop to fail a check the way a bug does. If AI helps you write and you
want the result to still sound like you, this is for you.

## Why it matters now

For a while, sounding like AI just cost you a little credibility with the people who
noticed. That changed fast. In two weeks across late July and August 2026, four
platforms started acting on it. LinkedIn added a button that lets any reader flag a
post as AI slop, and flagged posts stop reaching people outside your own network.
Snapchat pulled fully AI-made videos out of its recommendations. YouTube stopped
paying out on generic, mass-produced clips. Substack shipped a detector its readers
can run on a post.

So the cost moved. It used to be about looking lazy; now it is about who sees your
work at all. One study the platforms keep citing puts as much as 40% of social-media
writing at machine-made already. When that much of a feed is slop, the systems ranking
it learn to bury anything that smells the same, and the writing that reads as human is
what gets through.

## Try it

```bash
npx skills add manavmishra/ZeroSlop --global   # then say "de-slop this" in any agent
```

`--agent '*'` installs it everywhere; name one (`claude-code`, `codex`, `cursor`,
`opencode`, `warp`, `zed`) to install just there; drop `--global` to keep it to one
project.

<details>
<summary>Claude Code plugin · ChatGPT · Codex · claude.ai · manual clone</summary>

Claude Code and Cowork, as a plugin:

```
/plugin marketplace add manavmishra/ZeroSlop
/plugin install zero-slop@zero-slop
```

ChatGPT and ChatGPT at Work: paste the single-file version into a Project's
instructions, or upload it as Custom GPT knowledge.

```bash
curl -sLO https://raw.githubusercontent.com/manavmishra/ZeroSlop/main/dist/zero-slop-single-file.md
```

Codex: run this in your own project, not in a copy of this repo, because it writes
`AGENTS.md`.

```bash
curl -sL https://raw.githubusercontent.com/manavmishra/ZeroSlop/main/dist/zero-slop-single-file.md -o AGENTS.md
```

claude.ai and Desktop: download the repo as a zip and upload it under Settings,
Capabilities, Skills.

By hand, in any tool:

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

There is nothing to install and nothing to sign up for. One small Python file does
the scoring, it never sends your writing anywhere, and if Python is not around, the
skill still works from its written rules, you just lose the score.

## How it decides

Slop is not one thing, so Zero Slop looks at four, and only the first pays any
attention to the actual words. That is the trick: you cannot dodge it by swapping in
a thesaurus, because most of what it measures is the shape of the writing, not the
vocabulary.

| what it looks at | what gives you away |
|---|---|
| word choice | 74 known tell-phrases, a 55-word watchlist, and 13 words that only count in a salesy sentence |
| rhythm | sentences that are all the same length, paragraphs that march in step |
| readability | comma pile-ups, long-word traffic jams, sentences that run past 38 words |
| formatting | too many em-dashes, emoji, hashtags, bold everywhere |

It is deliberately hard to convict. One em-dash is not slop; plenty of wonderful
human writing leans on them. So a habit like that only counts once the word choice
backs it up. The rule is simple: a cluster of tells convicts, a lone one does not.

That last row of the word list matters more than it looks. A word like *leverage* or
*robust* is perfectly normal in a runbook. It only becomes a tell when a salesy word
is sitting in the same sentence. "Elevated write volume" in an engineering note is
fine. "Elevate your brand with our seamless platform" is not.

Once it has scored your draft, the rewrite happens in two passes, because that beat
doing it all at once in testing. The first pass only removes the tells and touches
nothing else. The second rewrites what is left into the voice of someone who knows
the subject, now that the clutter is gone and cannot hide a weak point.

## It will not touch your facts

This is the part most "humanizer" tools get wrong. To sound more human, they will
happily add a detail you never wrote, or drop a number to make a sentence flow. Zero
Slop treats that as the one unforgivable move.

Before it calls a rewrite done, it lists every figure, name, quote, and link in your
original and checks they are all still there, and that nothing new snuck in. The
second half is the part that saves you: a missing number is easy to catch yourself,
but an invented one reads perfectly and slips right past. We built this check because
an early version of the tool did exactly that in testing. More on that below, because
we would rather show you the miss than hide it.

## It gets sharper the more you use it

Most tools are frozen the day they ship. This one learns from you.

The best signal a slop-catcher can get is what you delete after it hands your draft
back. If you cut a phrase before posting, that phrase was a tell it missed. So it
watches for that, but carefully: a phrase only becomes a new rule after three
different documents have cut it, so one person's quirk never turns into everyone's
rule. It runs the other way too. A rule you keep overriding gets quieter, and rules
that stop catching anything fade out on their own.

```bash
python3 scripts/learn.py --reflect --produced out.md --shipped final.md
python3 scripts/learn.py --promote --apply     # turn agreed-on phrases into rules
python3 scripts/learn.py --voice you --from ~/my-writing/   # teach it your style
python3 scripts/learn.py --stats               # see what it has learned
```

There is a second way it can improve, and it is on the way rather than done. The
rewrite instructions live in one file, and the repo already ships the scorecard that
would grade a change to them. Microsoft's [SkillOpt](https://github.com/microsoft/SkillOpt)
is built to tune exactly that kind of file against exactly that kind of scorecard, so
wiring the two together is on the roadmap.

## Does it actually work

We tested it against the tools it is built on: 50 AI-heavy drafts across six kinds of
writing, rewritten by each tool, then handed to judges who did not know which tool
produced which version. Read this as a careful study, not a courtroom verdict. We
wrote the competitors' outputs from their published instructions rather than running
their live products, and only our rewrites were tuned against a scorecard, so the deck
is not perfectly even.

Across 100 blind picks, judges chose the Zero Slop version most often.

![Best-picks, pooled over 100 blind verdicts: Zero Slop 55, blader 40, no-ai-slop 5, de-slop 0](assets/bench-bestpicks.png)

The honest read: it clearly beat two of the four, and it was a statistical tie with
the strongest one, blader/humanizer. We ran the judging twice with fresh judges and
the two runs barely agreed on a winner, which is worth knowing before anyone leans too
hard on a single number.

The steadier measure is how much of the AI sound each tool strips out. Fair warning:
this one is scored by Zero Slop's own detector, so read it as "how much register got
removed," not as an independent grade.

![AI register remaining after de-slop, lower is cleaner: Zero Slop 9.8 versus 15.7 to 23.4 for others, from 69.0 for the raw drafts](assets/bench-detector.png)

There is one more test, and it is the one that matters most to a writer. Can the tool
tell obvious slop from obvious human writing, across LinkedIn, blogs, social, Reddit,
and newsletters? It separated the two cleanly, every time, with no overlap. The catch:
we wrote both piles ourselves, so it proves the tool agrees with an obvious call, not
that it will nail every draft in the wild. And it is fast, about 1,100 documents a
second, fast enough to sit in a build without anyone noticing.

## Where it falls short

We would rather you hear this from us.

The most useful thing the test turned up was a loss. An early build ranked last of the
four on keeping facts straight, and it was the only tool that invented something, a
feeling the writer never mentioned. That is what the fact-check above exists to catch.
It catches invented numbers and names now, but a claim that gets quietly twisted can
still slip through.

About that score. A 9.5 is the floor, not an A. Anything with nothing wrong lands at
9.5, and so does the word "Hello," so read the list of flagged phrases first and treat
the number as a summary. For a sense of scale, raw AI drafts tend to sit around 70,
and good human writing lands between 9 and 21.

And the honest limit under all of it: our accuracy numbers come from writing we wrote
to test with. An early bug had the tool flagging five of the eight human samples in
this very repo as slop; it is fixed and guarded against now, and it flags none of them,
but eight samples is a hint, not proof. A number you could really trust needs about a
thousand hand-labeled human samples, and that set does not exist yet. It is the first
thing on the list below.

## Built on good work

Zero Slop did not invent any of this. It stands on four open-source projects that
worked out the craft first: [petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop),
[blader/humanizer](https://github.com/blader/humanizer),
[isatimur/de-slop](https://github.com/isatimur/de-slop), and
[hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop). They proved the
sound can be removed, and their lists of tells seeded ours. What we added is the score,
the fact-check, and the learning, so a good idea becomes something you can measure,
trust, and improve.

Detectors like Pangram and GPTZero are a different tool for a different job, telling a
teacher or an editor whether a machine wrote something. They do that well. We are not
trying to beat them, and we deliberately do not tune our rewrites to fool them.

## What is next

- **A big, labeled test set.** It is what every accuracy claim here is waiting on.
  RAID, HC3, M4, and AuTextification are free and cover email, social, and blogs.
- **New signals that ignore vocabulary entirely.** The research
  ([NEULIF](https://arxiv.org/abs/2511.21744)) points at how often certain small words
  pair up, and how sentence lengths vary. Both are impossible to dodge with a thesaurus,
  and both need the test set above to tune.
- **Running the competitors live**, so the comparison is a true head-to-head.
- **A fact-check that reads meaning, not just names.** It catches an invented person
  today; it can still miss a twisted argument.
- **Tuning the rewrite instructions with [SkillOpt](https://github.com/microsoft/SkillOpt)**
  against the scorecard the repo already ships.

## Under the hood

```
SKILL.md                    the instructions the AI agent follows
scripts/slopscore.py        the scorer, plain Python, no libraries
scripts/learn.py            the learning loop and your style profile
scripts/calibrate.py        retune from a corpus; retire stale tells
data/patterns.json          the 74 tells, the watchlist, the context words
data/corpus/must-not-flag/  human writing the tool must never flag
references/                 the full tell list, rewrite guide, and research
bench/                      the test harness, the sorting test, the charts
tests/test_all.py           63 tests
```

Run `python3 tests/test_all.py` and `python3 scripts/calibrate.py --selftest`. The
tests cover the scorer, the learning safeguards, the retirement of old tells, and speed,
plus a set of tripwires that exist because each of these slipped once: the numbers in
this README have to match the data, the charts have to match the benchmark, the packaged
copies have to be current, and none of your writing is ever allowed into a tracked file.

## Thanks

Builds on [petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop),
[blader/humanizer](https://github.com/blader/humanizer),
[isatimur/de-slop](https://github.com/isatimur/de-slop), and
[hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop), all MIT;
Wikipedia's [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing);
and Kagi's [SlopStop](https://help.kagi.com/kagi/features/slopstop.html), which landed on
two of the same ideas we did, wait for a few tells before convicting, and let people
appeal. The thirteen research papers behind the design are listed in
[references/evidence.md](references/evidence.md). The three that carry the most weight:
the finding that detectors read a model's training style rather than the machine itself
(arXiv:2605.19516), the method for spotting over-used words (Kobak et al.,
arXiv:2406.07016), and the study showing detectors wrongly flag more than half of
non-native English writers (arXiv:2304.02819), which is why a non-native sample sits in
our safety set.

MIT.
