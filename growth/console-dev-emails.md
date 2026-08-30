# console.dev submissions

Two emails, both to **hello@console.dev** — their stated channel is "Email
hello@console.dev with the details and we'll happily take a look."

Send them **separately, about two weeks apart**. Console reviews 2-3 tools a
week. Two submissions from one sender on one day reads as a marketing push and
invites a single "no" for both.

Send Zero Slop first: it is free, MIT, self-hosted and offline, which clears
every one of their criteria without qualification. Prompeteer is the harder
sell because it is a hosted product, so it benefits from going second.

---

## Email 1 — Zero Slop

**To:** hello@console.dev
**Subject:** Tool submission: Zero Slop, a prose linter with a fact gate

Hi,

Zero Slop is an open-source prose linter for teams whose docs are drifting into
AI boilerplate. I think it fits what Console covers, and it is free, so there is
nothing to sell.

The developer-facing shape of it:

```
slopscore.py --batch drafts/ --gate 25
```

That scores every document in a directory 0-100 and exits non-zero above the
threshold, so a docs build fails on the writing the way it already fails on a
type error. It is one standard-library Python file with zero third-party
dependencies, runs entirely offline, and needs no account or API key — nothing
leaves the machine.

The part I would want reviewed is the fact gate. When it rewrites, any version
that adds or drops a name, number, quotation, link, code block or table is
rejected and redone. The model is never trusted to have preserved the facts; a
local check decides and fails the pass. That is the difference between this and
the "humanizer" prompts floating around, which happily rewrite your numbers.

It is deliberately not an AI detector. The score measures the writing, not the
author, and the docs say so repeatedly — human writing in its own corpus scores
9 to 21 while unedited AI drafts average 77, and neither number identifies who
wrote anything.

- Repo: https://github.com/manavmishra/ZeroSlop (MIT)
- Docs and benchmark: https://zero-slop.ai/benchmark/
- Install: `npx skills add manavmishra/ZeroSlop --global`, or run the scorer
  standalone with Python 3

It is a small project and I will not pretend otherwise. Happy to answer anything
or send a walkthrough.

Thanks for reading,
Manav Mishra

---

## Email 2 — Prompeteer

**To:** hello@console.dev
**Subject:** Tool submission: Prompeteer, prompt scoring and agent skills with an MCP server

Hi,

Prompeteer turns a plain-language goal into a prompt tuned for whichever model
you are targeting, and scores prompts across 16 quality dimensions so the
result is a number you can act on rather than a vibe.

The reason I think it belongs in Console rather than in a general AI roundup is
the developer surface. It is not only a web app:

- An MCP server, so it works from inside Claude Code, Cursor or any MCP client
  without leaving the editor
- A REST API with OpenAPI docs and self-serve API keys
- Agent skills that install into Claude Code, Cursor, Copilot and Windsurf
- A community n8n node for people wiring it into pipelines

Where it earns its place in a normal workflow: prompts in a codebase are
untracked, unversioned and unreviewed, so they rot the way config used to before
anyone checked it in. PromptDrive gives them a home, and the score gives a
review a reference point, which turns "this prompt feels worse" into a
diff you can argue about.

Signup is self-service with a free tier, no call with anyone, and the free tier
is enough to evaluate every claim above.

- Product: https://www.prompeteer.ai/
- Pricing: https://prompeteer.ai/pricing

Glad to set up an account with limits lifted if that helps a reviewer, or to
answer anything.

Thanks,
Manav Mishra

---

## Before you send

Check these, because I could not verify them from outside and Console tests
what it is told:

- **Free tier scope.** The email says the free tier is enough to evaluate
  everything. Make sure MCP access and API keys are actually available on Free,
  not gated to Pro. If they are gated, cut that sentence.
- **The n8n node.** It is a community node; confirm it is current before citing
  it.
- **Console's power-user checklist** rewards dark mode, keyboard shortcuts, an
  API, a CLI and accessibility. I only claimed the API because that is all I
  could confirm. If Prompeteer has the others, add one line listing them — it
  maps directly onto their criteria.
- **Zero Slop's install line** uses `npx skills add`, which works today.
  `npx zero-slop install` will also work, but only once the pending release is
  published; do not put it in the email before then.
