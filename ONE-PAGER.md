# Zero-Slop, on one page

In 2024, researchers measured the word "meticulous" appearing in
AI-conference peer reviews at nearly 35 times its expected rate, and the
same style words surging across fifteen million biomedical abstracts. The
cause was not a sudden outbreak of care. Scientists had started writing with
ChatGPT, and ChatGPT has favorite words. Readers everywhere learned the accent: the em-dash
rhythm, the tidy triplets, "I'm excited to announce," the polish that never
varies. On LinkedIn, sounding like a machine is now a reputation problem.

The research underneath is stranger and more hopeful. Take one model in two
versions, raw and assistant-trained, and detectors call the raw one human 98
percent of the time. The AI voice is a style, taught in the last step of
training, living entirely in wording. Remove the wording, keep the facts,
and the voice is gone.

**Zero-Slop is that removal, packaged as an agent skill that proves its
work.** It measures a draft with a built-in statistical detector, rewrites
it toward an expert human register, verifies the result against a hard gate,
and shows you the before-and-after numbers. It is MIT-licensed, fully
offline, dependency-free, and built on the Agent Skills standard, so the
same artifact runs in Claude Code, Codex, claude.ai, and any compatible
harness.

**A real run.** This August, a founder's LinkedIn draft opened with
"Enterprise AI value has too often compounded inside individual workflows…"
The scorer read 45.7 out of 100. The draft's best material, a startling
statistic, sat buried in paragraph two. The rewrite opens: "6x. That's how
many more messages frontier users send than the median employee, and it's
OpenAI's own telemetry, not a survey." New score: 9.5, clean. Same facts.
Nothing invented.

**The proof.** Fifty AI-typical drafts, six genres, independent blind
judges, every rival running its own published prompt. Zero-Slop took 32 of
50 "which would you publish" verdicts; the three best-known alternatives
combined took 18. Its rewrites left a third of the detector residue of the
weakest rival. The most useful result was a failure: one rewrite invented a
feeling the author never described, a blind judge caught it, and the
fabrication became a hard rule the same day. The full harness ships in the
repo, reproducible, with close results labeled as close.

**What it refuses.** No invented anecdotes, numbers, or feelings; missing
details get asked for. No padding empty paragraphs into confident mush. No
swapping the AI voice for forced hot takes and performed candor, which is
the same disease at higher volume. No detector-evasion for deception.

**Trust.** The scorer is two hundred lines of standard-library Python. No
network calls, no dependencies, nothing leaves your machine. Personal voice
profiles are git-ignored by design. The security review is one coffee.

**Install.** `npx skills add manavmishra/ZeroSlop --global` for any agent,
or `/plugin marketplace add manavmishra/ZeroSlop` then
`/plugin install zero-slop@zero-slop` in Claude Code. Then say "de-slop
this."

github.com/manavmishra/ZeroSlop · MIT · built on petergyang/no-ai-slop,
blader/humanizer, isatimur/de-slop, hardikpandya/stop-slop, Wikipedia's
Signs of AI writing, and fifteen detection papers cited in the repo.
