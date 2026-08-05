# Zero Slop

You used AI to help you write, and now the writing sounds like AI. You can hear it,
and so can everyone who reads it. There is a word for that sound now: slop.

Zero Slop finds it in your draft and takes it out, without changing what you actually
said. It scores the writing from 0 to 100, points at the exact words dragging it down,
rewrites them, and then double-checks that it kept every fact you had and invented
nothing.

```bash
npx skills add manavmishra/ZeroSlop --global
```

Then say "de-slop this" in any agent. No account, no server, and your writing never
leaves your machine.

![Zero Slop scoring a marketing sentence at 100, then its rewrite at 9.5](assets/demo.png)

## Why it matters now

Sounding like AI used to just cost you a little credibility. Now it costs you reach.
Over two weeks in mid-2026, LinkedIn, Snapchat, YouTube, and Substack all started acting
on slop. On LinkedIn, a flagged post now stops reaching anyone outside your own network.
One study the platforms keep citing estimates that up to 40% of social-media writing is
already machine-made. When a feed is that full of slop, the systems ranking it bury
anything that smells the same, and human-sounding writing is what gets through.

## Who it is for

Anyone who writes under their own name and would rather not sound like a robot. A
founder writing a launch post, a marketer shipping five things a week, a researcher who
needs their paper to stay formal, an engineering team that wants slop to fail a check
the way a bug does.

## How it decides

Slop is not one thing, so Zero Slop looks at four signals, and only the first pays
attention to the actual words. That is the point: you cannot dodge it with a thesaurus, because most
of what it measures is the shape of the writing, not the vocabulary. It weighs the words you chose, but also the rhythm of your sentences, how hard they
are to read, and how heavily the page is formatted. Then it leans toward mercy. One
em-dash is not slop; plenty of great writing leans on them. A tell only counts once the word
choice backs it up, so a cluster convicts and a lone one does not. It adds a check no
rulebook can: it asks the model running it to guess your words, and counts how often it
can — machine writing is easy to predict, and yours should not be. Zero Slop ships no
model of its own; it borrows whichever one you are already in. When it rewrites, it
writes several versions and keeps the cleanest one that changes no fact.

## What makes it different

It is built on four open-source projects that worked out this craft first: no-ai-slop,
humanizer, de-slop, and stop-slop. It adds three things a plain rewriter cannot.

A score you can trust and check. It comes from rules you can read, not a black box, so
every point traces to a phrase you can see, and it can go straight into a build.

A promise about your facts. Most "humanizer" tools will invent a detail or drop a number
to make a sentence flow. Zero Slop lists every figure, name, quote, and link in your
original and fails a rewrite that loses one or adds one. A missing number you would
catch; an invented one reads perfectly and slips right past, which is exactly why the
check exists.

A tool that learns you. What you delete after it hands your draft back was a tell it
missed, so it watches for that next time. And a sample of your own writing teaches it
which words are just how you talk. It also keeps itself current: each session it checks
for a newer release and points you at the one-line update, sending a version query and
nothing of what you wrote.

## Does it actually work

We ran it head to head against the four tools it builds on: 50 AI-heavy drafts, six kinds
of writing, judged blind. Across 100 picks, judges chose the Zero Slop version most often,
55 to humanizer's 40, with the other two far back. It clearly beat two of them, and tied
the strongest. It also cleanly separates obvious slop from genuine human writing, with no
overlap, at about 1,100 documents a second.

The honest caveat, which the full README does not bury: our accuracy numbers all come
from test writing we created ourselves, so they show the tool agreeing with an obvious
call, not that it will nail every draft in the wild. A number you could really trust needs
about a thousand hand-labeled samples, and building that set is the next thing on the
list.

---

MIT · [github.com/manavmishra/ZeroSlop](https://github.com/manavmishra/ZeroSlop) ·
v2.2.0 · 72 tests · built on no-ai-slop, humanizer, de-slop, and stop-slop, with thanks
to Kagi's SlopStop and the research listed in the repo.
