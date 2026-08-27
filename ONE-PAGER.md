# Zero Slop

You used AI to help with a draft, but the result sounds generic. You can hear it,
and so can everyone who reads it. That machine sound has a name: slop.

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

## Seven roles, one workflow

The local scorer finds exact phrases and problems with rhythm, readability, and
formatting. The AI assistant acts as interpreter, then rewriter. The local fact gate
rejects versions that change names, numbers, quotations, links, code, tables, or
document structure. Fresh AI passes
act as the copy desk, then the read-aloud editor. Finally, local tools and the assistant
share the verifier role, comparing the exact finished text with the source. These are seven
roles, not seven models. Separating them stops the rewriter from certifying its own work
and keeps late edits from bypassing the final checks.

## What makes it different

It builds on open-source projects that worked out this craft first: no-ai-slop,
humanizer, de-slop, stop-slop, and
[unslop-text](https://github.com/JCarterJohnson/vibecoded-design-tells/tree/main/unslop-ai-text),
along with the published work in avoid-ai-writing.
It adds three things a plain rewrite lacks.

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
with a metadata-only version query. That query never sends the draft.

## What we tested

Version 2.5.10 closes a structural blind spot: the balanced two-part contrast used as
a formula. The meter read wording, rhythm, and formatting, so a draft could land the
same rhetorical snap in every paragraph and still come back clear. Four new checks
catch the forms that carry no "not this, but that" marker — a repeated give-you frame
across a sentence break, "This is what X looks like", "No X had to decide; Y decided",
and a wider set of "Here's the …" openers. On the draft that prompted the change the
score moved from 13.0 to 59.0. All 18 known-human controls stayed clear, the Gettysburg
Address and the Federalist among them, and one span the project had recorded as
unreachable by any safe rule is now caught by one.

Version 2.5.9 adds hidden-character and mixed-script normalization, broader AI-tool
tracking residue, chat role-play actions, a cautious long-document check, and
protection for structured material. Compared with v2.5.8, it changed none of 114
frozen scores, kept all 18 known-human controls clean, and matched the 84.2 percent
result on the 38-item LLM editorial panel. It caught all five new edge cases and
blocked four tested classes of structured-document damage. A 12-run interleaved check
measured 0.41 percent higher median throughput.

We also regenerated four sets of rewrites on the same 18 drafts with GPT-5.4 and the
same reasoning level and batch size. Zero Slop passed all of its checks on 18 of 18;
avoid-ai-writing passed 15, no-ai-slop 12, and humanizer 9. Because those checks belong
to Zero Slop, this is a regression comparison, not independent human field accuracy.
The incumbent's own meter preferred its own outputs.

The external distribution checks remain current. RAID+ contributed 7,627 usable
generations from four model families; their mean writing scores ranged from 14.5 to
25.5. In Beemo, raw model responses averaged 30.2, expert edits 25.3, and independent
human answers 20.0. Neither dataset labels editorial quality. On one Apple silicon
Mac, the local checker processed 1,000 documents in 2.0566 seconds, or 486.2 per
second. These are reproducible checks with stated limits, not universal claims.

---

Open source under the [MIT License](LICENSE) ·
[github.com/manavmishra/ZeroSlop](https://github.com/manavmishra/ZeroSlop) · v2.5.10 ·
tested · built on no-ai-slop, humanizer, de-slop, stop-slop, unslop-text, and
avoid-ai-writing, with thanks
to Kagi's SlopStop and the research listed in the repo.
