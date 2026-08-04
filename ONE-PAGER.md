# Zero Slop

**A linter for the AI accent.**  
Scores your draft, strips the tells, and proves the fix with numbers.

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
"Enterprise AI value has too often compounded inside individual
workflows…" and scored 45.7: suspect, despite having no emoji and no
buzzwords. The loop's catches were judgment calls: an announcement-voice
opener hiding the draft's best statistic in paragraph two, a "quiet part
out loud" cliché, and a hook promising two reports while citing one. The
rewrite opens "6x. That's how many more messages frontier users send than
the median employee, and it's OpenAI's own telemetry, not a survey," gives
each report its own number, and ends on the author's own landing:
"The playbook is already inside the building. Your super-users are writing
it daily. The work is making it everyone's." New score: 9.5, clean. Every
figure and citation intact; the author's best lines protected, not
polished away. The complete before-and-after, with its scorecard, is in
the README.

**The proof, and its limits.** Fifty AI-typical drafts, six genres,
independent blind judges on shuffled labels, every skill running its own
published prompt. The first run gave Zero Slop 32 of 50 best-picks. A full
replication with fresh judges on the identical texts gave 23 of 50. Judges
agree only slightly on which rewrite is best (kappa 0.12), so single-run
headlines in this category are noise. Pooled across 100 verdicts: Zero Slop
55, blader/humanizer 40, no-ai-slop 5, de-slop 0. Zero Slop wins the
plurality against a chance rate of 25 (p = 1.7 × 10⁻¹⁰) and is statistically
tied with blader head to head (p = 0.15). The deterministic measurements are
steadier: Zero Slop v1.2 leaves a detector score of 9.5 against 17-40 for the
alternatives, a followability penalty of zero, and — the column that matters
— the original's word count, where every other method shrinks the draft by up
to 28 percent. The most useful single result was a failure: one rewrite
invented a feeling the author never described, two independent judges caught
it, and the rule it produced now runs on every draft.

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
