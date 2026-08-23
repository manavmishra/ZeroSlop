# Zero Slop

You used AI to help with your writing, and now it reads like a machine wrote every
word. You can hear it, and so can everyone who reads it. That machine sound has a
name: slop.

Zero Slop is not an AI model. It runs inside the AI assistant you already use. Claude,
GPT, or another compatible model reads and edits the draft; Zero Slop supplies the
method and local checks. Its writing score runs from 0 to 100 and points to the phrases
and writing patterns that raised it. The assistant then runs separate copy-editing and
read-aloud passes. Final checks make sure the facts survived.

```bash
npx skills add manavmishra/ZeroSlop --global
```

Then open your assistant and say "de-slop this." The Python scorer needs no account or
server and does not transmit your writing.

![Zero Slop giving a marketing sentence a writing score of 100, then its rewrite 9.5](assets/demo.png)

## Why it matters now

Sounding like AI can cost credibility, and platforms are adding ways to report,
classify, or limit repetitive machine-made material. LinkedIn added an AI-slop report
signal; Snap and YouTube apply recommendation or monetization rules to some synthetic
or mass-produced content; Substack lets readers scan text for AI signals. Those are
different policies, not proof of one universal reach penalty. The practical point is
simpler: readers notice generic machine prose, and writers deserve a way to inspect and
fix it before publishing.

## Who it is for

Anyone who writes under their own name and would rather not sound like a robot. A
founder writing a launch post, a marketer shipping five things a week, a researcher who
needs their paper to stay formal, an engineering team that wants slop to fail a check
the way a bug does.

## How it decides

First, a local program checks familiar phrases, sentence rhythm, readability, tone,
and formatting. The writing score describes those choices; it does not claim to know
who wrote the text. The AI assistant running the skill then reads the draft in context,
rewrites it, and performs the two final editorial passes. A separate check asks that
same assistant to guess hidden words and reports how often the original word appears
among its top three guesses. When three or more related drafts are present, a portfolio
check reports repeated five-word openings and shared phrases without changing the main
score. Zero Slop ships no model of its own and does not send the draft to a separate
Zero Slop AI service. For important work, the assistant drafts two or three approaches,
rejects any that add or lose a fact, and sends the cleanest version through separate
copy-editing and read-aloud passes.

## What makes it different

It is built on four open-source projects that worked out this craft first: no-ai-slop,
humanizer, de-slop, and stop-slop. It adds three things a plain rewrite lacks.

A score you can inspect. The rules and structural measures are visible, and the same
threshold check can run in a build. It is a repeatable writing check, not authorship
proof.

A promise about your facts. A rewrite can invent a detail or drop a number to make a
sentence flow. Zero Slop lists every figure, name, quote, and link in your original and
rejects a version that loses one or adds one. A missing number may be obvious; an
invented one can read naturally enough to go unnoticed, which is why the check exists.

A tool that learns from later edits. The editorial loop handles the current draft. A
separate private learning loop can compare the assistant's version with a later edit: a
phrase you cut may reveal a pattern the local check missed, while flagged text you keep
may be a false alarm. No detection rule or preferred fix becomes active after one edit.
Before a phrase rule can take effect, the same cut must appear in three unrelated pieces.
It must also be new and leave a reference set of human writing unflagged; a single-word
cut must appear in five unrelated pieces. A preferred replacement must also recur in
three unrelated pieces. The private learning file loads on the next run. Later matching
edits confirm useful rules and fixes; without reconfirmation, stale detection rules decay
and stale preferred fixes retire.

This is post-deployment, human-in-the-loop online learning. It adapts detection and
fixing through inspectable local rules and preferences. Human corrections provide
feedback, but Zero Slop does not perform reinforcement learning or RLHF, nor does it
retrain the AI model already running in the assistant. Shared changes still require
review, tests, versioning, and a release. Each session can check for a newer release
with a metadata-only version query.
That query never sends the draft.

## What we tested

We wrote 50 AI-heavy drafts and compared four rewrites of each. No human raters took
part. The records identify the evaluators only as LLM runs from one model family. Each
of the two passes used five separate runs. The method names were hidden; the model saw
the brief, source draft, list of facts, and four rewrites, then rated human-likeness,
voice, faithfulness to the source, craft, and platform fit.

The results moved between passes. The model selected Zero Slop for 32 of 50 drafts in
the first and 23 in the second; it selected blader/humanizer for 18 and 22. The pooled
counts were 55 and 40, but the passes agreed on a winner for only 26 drafts, and the
head-to-head difference was not statistically significant. The public harness also
omits the exact model, settings, and full prompt. The results show that the two systems
were competitive on our synthetic set, not that either is generally better. We also
wrote the scorer's test set, so it serves as a check for unintended changes rather than
a real-world accuracy estimate. A 1,000-document speed check runs in CI and must finish
within 60 seconds. A separate search-informed challenge contains 18 anonymous slop
paraphrases across LinkedIn, X, email, blog, newsletter, and research; it is an
easy-case check for unintended changes, not a real-world accuracy estimate.

---

MIT · [github.com/manavmishra/ZeroSlop](https://github.com/manavmishra/ZeroSlop) ·
v2.5.3 · tested · built on no-ai-slop, humanizer, de-slop, and stop-slop, with thanks
to Kagi's SlopStop and the research listed in the repo.
