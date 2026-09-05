# Zero Slop launch playbook

The repository is the conversion surface. The launch supplies concentrated,
audience-specific traffic to it.

## Positioning

**Promise:** Find AI-sounding writing. Keep the source intact.

**Category:** An open-source Agent Skill and local writing meter, not an
authorship detector.

**Primary CTA:** Try a draft at `https://zero-slop.ai/try/`.

**Developer CTA:** `npx skills add manavmishra/ZeroSlop --global`.

**Hosted CTA:** Connect the MCP at `https://zero-slop.ai/#mcp` when a user wants
one managed endpoint instead of a local installation.

## One launch, several demonstrations

Record each idea vertically and horizontally. Keep the final cut between 20 and
40 seconds. Start on the bad sentence, not the logo.

| Demo | Hook | Visible proof | Best channels |
|---|---|---|---|
| Launch post | “Four phrases made this announcement sound interchangeable.” | Score falls from 99.3 to 9.5; 40% held | LinkedIn, X, Product Hunt |
| Product update | “Can an AI editor remove the pitch and keep 10,000 rows in 8 seconds?” | Exact figures survive | Hacker News, Reddit, YouTube |
| Team email | “This 31-word email only needed 14 words.” | Priya, 12 dashboards, and the date survive | LinkedIn, Shorts |
| Research summary | “Tighten this without losing the held-out-set qualifier.” | Both 0.42 and 0.31 survive | research and ML communities |
| CI gate | “Fail a docs build when generated copy crosses 25.” | Batch command exits above the threshold | developer newsletters, HN |
| Hosted MCP | “Add the same writing checks to Codex or Claude with one endpoint.” | Connection command, then one tool call | MCP and coding communities |

The repository's signature animation is the reusable visual system: rust flags,
the diagonal **Zero Cut**, then a green source check. Use the same sequence in
video thumbnails and short clips so the motion becomes recognizable.

## Seven-day launch spike

### T−7 to T−5: prepare

- Verify the README, latest-release downloads, npm installer, browser trial, and
  hosted MCP from clean sessions.
- Export the six demonstrations in 16:9, 1:1, and 9:16.
- Build a list of 20–50 creators and newsletters whose audience already uses
  Claude, Codex, Cursor, AI writing tools, or open-source developer tools.
- Give each contact one relevant demo and one sentence explaining why their
  audience would care.

### T−4 to T−2: seed

- Send personal previews to the first ten creators. Ask for criticism or a
  demonstration request, not a generic share.
- Submit the human-only awesome-claude-code recommendation.
- Pitch console.dev with the CI gate and reproducible benchmark.
- Prepare responses for privacy, authorship detection, benchmark limits, and
  why the project ships no model.

### T−1: dry run

- Test every tracked link in an incognito window.
- Confirm the GitHub social preview renders clearly at small sizes.
- Put the best 20-second clip, two screenshots, benchmark summary, and founder
  bio in one shareable folder.
- Capture the baseline: stars, forks, npm downloads, release downloads, unique
  visitors, referrers, and MCP guide visits.

### Launch day

1. Publish Product Hunt shortly after its daily reset.
2. Publish Show HN when Manav can answer technical questions for the next two
   hours.
3. Post the launch example on LinkedIn and X. Upload the clip natively. Where a
   platform suppresses links, add the repository URL in a reply.
4. Send the prepared creator notes after the public pages are live.
5. Reply with concrete evidence, commands, or limitations. Do not argue with
   taste.

### T+1 to T+3: widen

- Post the product-update and CI-gate demonstrations to the relevant developer
  communities.
- Post the research-summary demo to ML and writing audiences.
- Share useful technical answers from launch discussions as standalone posts.
- Thank creators who covered it and give them a follow-up demo tailored to
  questions their audience asked.

### T+4 to T+7: compound

- Publish the results: what people tried, what failed, and what changed.
- Turn repeated questions into README fixes or discussions.
- Contact the next 10–15 creators using the strongest real launch result.
- Keep one distribution channel only if it produces activated users, not merely
  impressions.

## Ready-to-adapt launch copy

### Product Hunt

**Tagline**

> Find AI slop. Keep the source intact.

**Opening**

> Zero Slop scores stock phrasing, mechanical rhythm, and canned formatting,
> then gives your existing AI assistant a source-preserving editing workflow.
> Local checks guard names, numbers, links, quotations, code, tables, and paths.
> Use the local skill, try it in the browser, or connect the hosted MCP.

### Show HN

**Title**

> Show HN: Zero Slop – score AI-sounding writing, edit it, check the source

**Opening**

> I built Zero Slop after “make this sound human” prompts kept flattening drafts
> and occasionally changing concrete details. It is an Agent Skill, not a
> model. A standard-library Python meter points to exact phrases and structural
> problems; your existing assistant edits; local tools check protected strings.
>
> In a saved 18-draft replay using the same model and pinned instructions, the
> mean writing score moved from 76.3 to 12.8 and all 18 source checks passed.
> The drafts, outputs, hashes, and limitations are in the repository.

### Creator note

> You cover [specific audience/problem], so I thought this example might be
> useful: Zero Slop cut a launch post from 99.3 to 9.5 while keeping its 40%
> result. It is free, open source, and works inside the assistant people already
> use. If you want to test it, I can send the 20-second clip and the exact draft.
> No obligation to post.

### MCP note

> Prefer a hosted connection? Add `https://mcp.zero-slop.ai/mcp` to a supported
> client. It exposes Zero Slop's scoring and source-checking tools without a
> local clone. The local skill remains the right choice when drafts must stay on
> the machine.

## Tracking without invasive telemetry

Use a consistent campaign convention on links to the website:

```text
utm_source=producthunt|hackernews|reddit|linkedin|x|youtube|creator_name
utm_medium=launch|social|community|creator
utm_campaign=zero_slop_launch
utm_content=launch_post|product_update|team_email|research|ci_gate|mcp
```

GitHub repository links do not need tracking parameters. Use GitHub's aggregate
traffic and clone reports, npm's public download totals, release download
counts, and privacy-preserving site analytics. Never add draft text, filenames,
paths, or user identifiers to analytics.

## Weekly decision rule

For each channel, record:

- qualified visits
- install or trial starts
- successful first uses
- stars and discussions
- time spent producing and replying

Double down when a channel creates successful first uses at a reasonable cost
in time. Change the demonstration before abandoning an audience: the wrong
example often fails before the channel does.
