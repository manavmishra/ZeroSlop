# Newsletters: cost, distribution, impact

What a sponsored slot actually buys for a free MIT tool, and the ranked list of
where to place. Written 30 August 2026, against 13 stars and ~16 all-time skill
downloads.

Score this file before changing it:

```bash
python3 scripts/slopscore.py --explain growth/newsletter-analysis.md
```

---

## The short answer

Do not buy a slot yet. Buy one after roughly 500 stars.

A sponsored click lands on a GitHub repository, and on GitHub the star count
*is* the trust signal. A developer who clicks a paid ad, arrives at 13 stars,
and sees no corroborating list entries leaves. The same click against a
500-star repository with three directory listings converts several times
better. Paying now spends the budget at the worst point on that curve.

Everything below is a model, not a measurement. The conversion rates are
industry ranges, and the only way to replace them with facts is the daily
snapshot in `growth/growth-snapshot.mjs`, which now records npm downloads,
release assets per file, clones and per-star timestamps.

---

## The cost model

Published rates, and the assumptions applied to them:

- Sponsor slot CTR, developer newsletters: 0.5 to 1.5%. Take 1%.
- Click reaches GitHub: a landing page leaks. Take 35%.
- GitHub visit converts to a star: 1 to 2% with no social proof, 5 to 8%
  once the repository looks established. Both are shown.
- GitHub visit converts to an install: roughly half the star rate.

### TLDR — 275,000 subscribers, $3,500 per issue, $12 CPM

| Stage | Count |
|---|---:|
| Delivered | 275,000 |
| Clicks at 1% | 2,750 |
| Reach the repository at 35% | 960 |
| Stars at 2% (today's credibility) | ~19 → $184 per star |
| Stars at 6% (post-traction) | ~58 → $60 per star |

### A niche list — 20,000 subscribers at $100 CPM = $2,000

| Stage | Count |
|---|---:|
| Delivered | 20,000 |
| Clicks at 1.5% (higher relevance) | 300 |
| Reach the repository at 35% | 105 |
| Stars at 2% | ~2 → $950 per star |
| Stars at 6% | ~6 → $317 per star |

Mass-market volume wins on cost per star; niche wins on the quality of the
person who installs. Neither is good at 13 stars.

### What the free work costs

For contrast, reallocating five dead GitHub topics took ten minutes and put the
repository on the front page of four topics — rank 5 in `ai-slop-detection`,
4 in `slop-detector`, 5 in `prose-linter`, 1 in `writing-score`. Cost per star:
zero. The free channels are not exhausted, so paid spend is premature by
definition.

---

## Impact, honestly

A single newsletter placement is a spike rather than a slope. It produces two or
three days of traffic and then stops. It compounds only through what it leaves
behind: stars that raise topic rank, and a backlink that helps the domain get
indexed at all — zero-slop.ai currently has no pages in Google's index, and
links are what fixes that.

That argues for placements that leave a permanent URL — an editorial review, a
directory entry — over a slot in an email nobody can link to later.

---

## Ranked placements

Sorted by expected return for this product at this stage. Cost is real money;
effort is yours.

### Tier 0 — free, do this week

| # | Placement | Reach | Cost | Why it ranks here |
|---|---|---|---|---|
| 1 | GitHub topics | — | Free | Done. Four front-page topic placements in ten minutes. |
| 2 | [blader/humanizer](https://github.com/blader/humanizer) reciprocal link | 38,893★ | Free | You already credit it. Highest-relevance backlink available. |
| 3 | [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) | 16,581★ | Free | Same. |
| 4 | [petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop) | 6,458★ | Free | Same, and the closest peer. |
| 5 | [shannhk/avoid-slop](https://github.com/shannhk/avoid-slop) | 177★ | Free | A directory of exactly this. One PR. |
| 6 | [console.dev](https://console.dev/) | 22,000 subs | Free | Editorial review, no sponsored option. Best-fit list in the whole table. |
| 7 | Show HN | Large | Free | Highest ceiling of anything here. Lead with the benchmark. |
| 8 | r/ClaudeAI, r/LocalLLaMA | Large | Free | Where agent-skill users actually are. |
| 9 | [hwajongpark/awesome-slop](https://github.com/hwajongpark/awesome-slop) | 5★ | Free | Tiny, but exact-match and one PR. |

### Tier 1 — free, after ~100 stars

| # | Placement | Reach | Cost | Gate |
|---|---|---|---|---|
| 10 | [awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) | 53,214★ | Free | Their stated bar is 100 stars. Web form only. |
| 11 | Product Hunt | Large | Free | Needs the launch-day audience Tier 0 builds. |
| 12 | [awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) | 93,088★ | Free | Only if an MCP surface ships; not today. |

### Tier 2 — paid, after ~500 stars

Ordered by fit, not by size.

| # | Newsletter | Subscribers | Published rate | Fit |
|---|---|---:|---|---|
| 13 | console.dev ads | 22,000 | Contact | Devtools-only audience. Start here. |
| 14 | TLDR AI | ~1.1M | Contact | Largest AI-developer reach; TLDR's main list is $3,500 at $12 CPM. |
| 15 | Bytes | 105,311 | $3,650 premier | JS-heavy, strong engagement, writing-adjacent. |
| 16 | TLDR (main) | 275,000 | $3,500 / $12 CPM | Cheapest cost per impression in the table. |
| 17 | Quastor | 40,000 | Contact | Engineering depth, good for a benchmark story. |
| 18 | Hacker Newsletter | 60,000 | Contact | Curated HN digest; pairs with a Show HN. |
| 19 | Unzip.dev | 3,700 | Contact | Small, deep, trend-explainer format suits the slop thesis. |
| 20 | A Byte of Coding | 2,800 | Contact | Cheapest real test of the channel before a big spend. |
| 21 | Ben's Bites | 160,000 | Contact | AI-builder audience, less developer-tool intent. |
| 22 | The Rundown AI | 2,000,000+ | Contact | Huge and consumer-leaning. Worst fit-per-dollar here. |

### How to test the channel cheaply

Buy #20 or #19 first, for a few hundred dollars, with a tagged URL. The
snapshot records referrers daily, so one small placement produces a real CTR and
a real star conversion for this specific product. Every number in the model
above is then replaced by a measurement, before any $3,500 decision.

---

## What would change this advice

- Clearing 500 stars — moves every conversion rate to the upper band.
- A revenue surface. Cost per star only matters because nothing here monetises;
  a paid tier would make cost per install the number, and change the ranking.
- Google indexing the site. Until then a paid click cannot be recovered through
  search later, which makes each placement worth less than it looks.
