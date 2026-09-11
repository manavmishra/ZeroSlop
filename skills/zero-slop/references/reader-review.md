# Audience reader review

Use when the user asks whether someone would keep reading, what a draft makes
clear, or where its argument loses an audience. This is an opt-in diagnostic,
not a replacement for editing, fact verification, or feedback from real people.
The draft stays unchanged. Never infer AI authorship from a reader reaction.

## Choose the appropriate review

Establish the intended audience, reading situation, and intended action from the
request. State a reasonable assumption if one is missing; ask only when different
audiences would materially change the review. Avoid invented demographic traits,
personal histories, or psychological diagnoses.

- Under roughly 150 words, use one concise cold-read/skim response. Do not turn a
  short email into a multi-agent exercise.
- For narrative, essays, and launch posts, use the three responsibilities below.
- For reference documentation, inspect findability, headings, and whether a
  specified task can be completed. Readers need not read reference material in
  order. Label this a lookup review, not a sequential reading simulation; use a
  concise chat report rather than forcing a nonsequential path into the helper.
- For fiction or poetry, assess the requested literary effect. Do not demand
  numbers, explicit calls to action, or business-style specificity.

The existing eight editing responsibilities remain unchanged. When both audience
review and rewriting are requested, record the audience review first, then edit
and run the existing fidelity checks. Do not prime the readers with the slop
score, a preferred rewrite, or another reader's opinions.

## Three reader-review responsibilities

### Skim: would the opening earn attention?

Give a fresh context only the headings and opening excerpt produced by `skim`.
Ask what the draft appears to offer, whether that would merit opening it in the
stated situation, and what remains unknown. A skim is not a full-document review.
Its reaction must not refer to unseen body text.

### Passage review: two independent audience lenses

Use an interested task-focused reader and a cautious task-focused reader. These
are assumed lenses, not representative people. Both may like the draft; both may
dislike it. Never manufacture disagreement or rerun a reviewer until it criticizes
the writing. Allow "nothing missing" and uncertainty.

For every supplied passage, record a short reaction, what would help, an ordinal
attention label (`engaged`, `steady`, or `lost`), and whether to continue. Tie each
reaction to a passage ID. Ask about relevance, clarity, earned trust, and the
reader's task, not a list of prohibited words. An unsupported claim is a question
to investigate, not permission to invent evidence or change the author's facts.

**Context isolation is a real requirement, not a prompt trick.** Use sequential
mode only when the harness can supply a fresh reader context with no inherited
conversation or source access. The coordinator holds the full manifest. Give each
reader only its audience lens, current passage, and its own earlier notes. Do not
pass the full draft, source paths, the manifest, other readers' notes, or tool
access that exposes them. A helper that emits one passage does not sandbox an
agent. If those restrictions cannot be enforced, use and disclose
`retrospective` mode. Never claim that a full-context reviewer genuinely did not
see the next passage.

After a reader stops, do not send another passage. Unread passages remain unread,
not failures or zero scores. No artificial sleep or "human reading speed" claim:
model latency is not human attention. Default to a selected excerpt of at most 12
passages per reader. For a longer draft, agree a scope or state the excerpt before
running; do not silently discard the rest or launch unbounded model calls. The
helper's input size limits are safety ceilings, not a recommended model budget.

### Recall: what remains in the notes?

Use a fresh context containing only that reader's notes and the audience lens.
Ask for the main takeaway and unanswered questions, citing note IDs. Do not
provide the source or let the reader reread it. This tests reconstruction from
notes, not next-day human memory. Follow-up answers use the same notes-only
boundary and cite their grounding. Questions about unseen passages must abstain.

## Report and revision loop

Lead with the highest-impact passage-specific issues, disagreement if present,
and what the author can test or clarify. Keep reactions distinct from verified
facts. Say: **"Simulated audience review, not feedback from real readers."**
Report context mode and any incomplete coverage. Attention is qualitative, not a
probability of abandonment, engagement analytics, or a calibrated quality score.
Reader agreement never certifies accuracy, author voice, or safe publication.

The local HTML report places notes next to their passages and shows each reader's
attention labels. Every source string is text, not executable markup. An optional
previous report shows the old and new strips; passage positions are not stable
identities across revisions. Do not imply an experimental improvement from an
unaligned strip. On "again," use the same audience/lenses but fresh contexts;
withhold the old notes and strips until the new review is complete.

Do not automatically rewrite, learn from, export, or transmit reader notes. Only
a person's explicit approval can enter the existing private learning workflow.
Do not copy drafts into development tracking, telemetry, or public artifacts.

## Optional local helper

`scripts/reader_review.py` uses Python's standard library and prints outputs to
stdout. It reads only the files explicitly passed to it. It does not call a
model, open a server, or write a report automatically. The host assistant supplies
the reactions; that assistant may use a remote model. Fully offline inference
requires a local host model. These helpers alone do not make an online host
offline. Without Python, give the same bounded review in chat and disclose any
context limitations; do not fail the user's writing task.

For a user-authorized local report, the coordinator can save stdout to named
private output files using its approved file tools. These commands illustrate the
interface, not a requirement to run a shell from the reader:

```sh
python3 scripts/reader_review.py prepare draft.md --audience "Backend engineers reviewing a launch"
python3 scripts/reader_review.py skim manifest.json
python3 scripts/reader_review.py next manifest.json --reader R1 --context-mode sequential
python3 scripts/reader_review.py next manifest.json --reader R1 --notes r1.json
python3 scripts/reader_review.py recall manifest.json --reader R1 --notes r1.json
python3 scripts/reader_review.py report manifest.json --reviews reviews.json --skim skim.json
python3 scripts/reader_review.py report manifest.json --reviews reviews.json --skim skim.json --json
python3 scripts/reader_review.py report revised-manifest.json --reviews revised-reviews.json --skim revised-skim.json --previous previous-report.json
```

The first command returns the manifest; save it only if an output file is wanted.
The default mode for a new journal is `retrospective`. `sequential` is a
caller-reported assertion, not an attestation by the helper. Subsequent packets
use the journal's mode. Repeat independently for R2. A reader journal has this
shape (values below illustrate the format, not a measured result):

```json
{
  "source_sha256": "<manifest source_sha256>",
  "review_id": "<manifest review_id>",
  "reader": "R1",
  "context_mode": "retrospective",
  "entries": [{
    "note_id": "R1-p1", "passage_id": "p1", "attention": "steady",
    "reaction": "The topic is clear; the benefit is not yet stated.",
    "needed": "Explain which engineering task this helps.",
    "keep_reading": false
  }],
  "recall": {"takeaway": "A tool announcement.", "note_ids": ["R1-p1"], "questions": []}
}
```

`reviews.json` is an array containing the R1 and R2 journals. Each must finish or
explicitly stop. `skim.json` contains `source_sha256`, `review_id`, `context_mode`, `reaction`,
and the boolean `would_open`. The JSON report envelope is the input for
`--previous`; a raw HTML file is not. Source hashes reject mismatched revisions.
The `review_id` also binds the audience and lenses, preventing old reactions from
being relabelled for a new audience. Neither proves a model reaction's authenticity.

## Design provenance and evidence boundary

The passage boundary, independent lenses, notes-only recall, and revision-strip
ideas were informed by [First Reader at commit f56f4fe](https://github.com/Shubhamsaboo/awesome-llm-apps/tree/f56f4febaac4eb869c2e98859e78612889913d3e/agent_skills/first-reader).
Zero Slop's helper is independently implemented; no First Reader code is vendored
into the runtime. Source review and local contract tests do not establish which
product's feedback people prefer. See `bench/first-reader/` in the maintainer
repository for pinned comparison evidence, not a market-superiority claim.
