import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from safeio import atomic_write_text  # noqa: E402

out = {}

out["B01"] = """RAG versus fine-tuning is one of the most common debates in applied AI. Both approaches make a large language model more useful for your specific needs, but they solve different problems, and choosing the wrong one can cost you time, money, and accuracy.

The distinction is straightforward. Retrieval-Augmented Generation (RAG) is built for freshness and citations. Because it pulls answers from a live knowledge base at query time, your model can reference up-to-date documents and point users to exact sources. Fine-tuning is built for style and latency. It bakes knowledge and tone into the model's weights, so responses are faster and more consistent, with no retrieval step.

Take a concrete case: a customer-support knowledge base with 100,000 documents. Should you retrieve from it, fine-tune on it, or both? The answer depends on how often your content changes, how much citations matter, and what latency your users will tolerate.

This post breaks down those trade-offs so you can make the right call for your use case."""

out["B02"] = """Postgres indexes get treated as a silver bullet: slow query, add an index. But every index comes with a hidden cost, and over time those costs quietly erode your database's write performance.

Unused indexes are one of the most common and most overlooked pitfalls. Every INSERT, UPDATE, and DELETE has to maintain every index on the table, which means indexes that never serve a single query are still bloating your writes, inflating your storage, and slowing down your vacuum cycles.

We saw this firsthand with a recent client. One of their core tables had accumulated 23 indexes over the years. After an audit, we dropped 14 of them, and write throughput doubled. No hardware changes, no query rewrites, just less unnecessary work on every write.

This post walks through the pitfalls we see most, shows how to find unused indexes in your own database, and ends with a practical checklist for keeping your indexes lean."""

out["B03"] = """Remote onboarding is one of those things every company claims to have figured out, until a new hire spends their first week waiting for access, hunting for documentation, and wondering who to ask for help. In a distributed team, those small frictions compound.

Over the past year, we onboarded 27 remote hires. We made plenty of mistakes and ran plenty of experiments, and we cut our time-to-first-PR from 12 days to 5. New engineers now ship meaningful code in their first week instead of their third.

This guide shares the playbook that got us there: how we structure the first day, the role of onboarding buddies, the documentation that matters (and the documentation that doesn't), and the metrics we track to keep improving."""

out["B04"] = """Design systems are now a standard part of product development, but how are they actually faring inside organizations? To find out, we surveyed 412 designers across industries, company sizes, and levels of design maturity for The State of Design Systems 2026.

The headline finding is sobering: 61% of respondents say their design system is partially adopted at best. For the majority of teams, the design system exists but isn't the single source of truth it was meant to be.

Adoption stalls for varied reasons: unclear ownership, competing priorities, gaps between design and code, and the challenge of keeping documentation up to date. The data also points to what's working, and the teams that get adoption right share some surprisingly consistent habits.

This report unpacks the numbers, highlights the trends shaping design systems in 2026, and shares practical takeaways you can bring back to your own team."""

out["B05"] = """Building an emergency fund isn't glamorous. There's no dopamine hit, no compounding chart to admire, no one bragging about their savings account at parties. And yet, if there's one financial move that consistently pays off, it's this one.

The standard advice is to set aside 3–6 months of expenses: enough of a cushion to absorb a job loss, a medical bill, or a surprise car repair without reaching for a credit card. It sounds simple. It's also, for most people, genuinely hard.

I know because I've done it. It took me 14 months to build my emergency fund on a $52k salary, and along the way I learned that the challenge is less about math and more about habits, trade-offs, and staying motivated when progress feels painfully slow.

I'll share exactly how I did it: the budget changes that mattered most, the automation that kept me consistent, and the mindset shifts that made the difference. If you've been putting off starting, or you've started and stalled, I hope this gives you a realistic roadmap."""

out["B06"] = """The ancient temples, the quiet lanes, the sense that every corner holds a thousand years of history — Kyoto rewards slowing down, even when you only have four days.

Four days is exactly what we had. We based ourselves in Gion, the city's famous geisha district, where wooden machiya houses and lantern-lit streets make even a simple evening stroll feel like stepping back in time.

Two moments stood out. Walking beneath the vermilion gates of Fushimi Inari at 6am, before the crowds arrived, with the mountain path almost entirely to ourselves. And on our final night, a kaiseki dinner that cost ¥18,000. Not cheap, but an unforgettable procession of seasonal dishes that felt more like art than food.

Below is our full four-day itinerary: where we stayed, what we ate, what we'd happily skip next time, and the small tips that made the trip smoother."""

out["B07"] = """Procurement is often the last place companies look for efficiency gains, and the first place inefficiency hides. The average mid-market company uses 7 different tools just for purchasing, from spreadsheets and email threads to ERP modules and standalone approval apps.

The result is a process nobody loves. Requests get lost between systems. Approvers don't know what's waiting for them. Finance loses visibility into committed spend. A simple purchase turns into a multi-week ordeal that frustrates everyone involved.

Modern procurement software consolidates requests, approvals, and vendor management into a single workflow, and the impact shows up fast: companies that make the switch see 14-day approval cycles drop to 3.

This post covers why procurement tooling became so fragmented, what a consolidated approach looks like in practice, and how to tell whether your organization is ready for the change."""

out["B08"] = """On Tuesday, our platform experienced a 4-hour outage that affected a significant portion of our users. The root cause was an expired TLS certificate on an internal service that sat squarely in our request path. We know how disruptive this was, and we're sharing this postmortem to explain what happened and what we're changing.

The short version is humbling. A certificate we didn't realize was close to expiry, on a service most of us rarely thought about, expired quietly and took a surprising amount of our stack down with it. Alerts fired, but the failure mode was confusing, and it took longer than it should have to trace the cascading errors back to their source.

Below, we walk through the full timeline, the contributing factors, and the 3 action items we're committing to: automated certificate-expiry monitoring across all services, documented rotation runbooks for every internal certificate, and regular game-day testing of certificate failure modes.

We hope sharing the details helps other teams avoid the same trap."""

out["N01"] = """Welcome back to your weekly AI roundup. Here's what caught our eye this week.

First up, open weights keep getting stronger. A new open-weights 30B model dropped this week, and early benchmarks suggest it's competitive with much larger closed models on reasoning and code tasks. For teams that want to self-host without frontier-lab price tags, the gap keeps narrowing.

Meanwhile, in Brussels, the next EU AI Act enforcement deadline is fast approaching. Companies deploying AI systems in the EU should be reviewing their compliance posture now rather than later. Expect a last-minute scramble, and a wave of legal-tech vendors happy to help.

Finally, a new study on AI code review found that 28% of surveyed teams have adopted AI tools in their review workflows. That's a lot for a practice that barely existed two years ago.

That's it for this week. Thanks for reading, and see you next week!"""

out["N02"] = """Here's what's new this cycle.

Dark mode has shipped. It was our most-requested feature, with 340 users asking for it, and it's now live for everyone. Head to Settings → Appearance to try it out.

CSV export is now in beta. If you've been waiting to get your data out of the app and into your spreadsheets, you can enable it today under Labs. It's still early, so we'd love your feedback as we polish it up.

We also shipped 2 bug fixes from your reports, in notifications and scheduled reports.

Keep the feedback coming — it genuinely shapes what we build next. More soon!"""

out["N03"] = """This week, let's talk about vertical SaaS, and why the math that used to kill these deals is changing.

The old objection to vertical software was always market size. A niche industry might desperately need better tools, but if the TAM couldn't support a venture-scale outcome, investors passed. AI changes that math. When a small team can build, sell, and support software that previously required fifty people, small vertical markets become viable, even attractive.

Take software for marinas: a $400M TAM that most funds would have ignored a decade ago. Today, an AI-native team can serve that market profitably at a fraction of the historical cost structure, own the core workflow end to end, and expand into payments, insurance, and adjacent services over time.

Our thesis: the next generation of great vertical SaaS companies will be smaller teams attacking smaller markets, and capturing far more of them. If you're building in this space, we'd love to hear from you."""

out["N04"] = """Happy Friday, runners! A few quick updates from the club this week.

First, a schedule change: starting this weekend, the Saturday long run moves to 7am. With the summer heat rolling in, an earlier start means cooler miles and more of your Saturday back. Same meeting spot as always. Just set that alarm a little earlier and bring your water bottle.

Second, a warm welcome to the 8 new members who joined us this month! If you spot a new face at a group run, say hello and introduce yourself. We were all the new person once.

Finally, huge congratulations to our half-marathon team, who crossed the finish line with 4 PRs between them! Months of consistent training paid off, and we couldn't be prouder of everyone who raced.

That's all for this week. See you on the roads — 7am sharp!"""

out["N05"] = """Hi everyone,

Starting in March, the Pro plan will go from $29 to $39 per month. I want to explain why.

Over the past two years, we've expanded what Pro includes, and the new price reflects the product Pro has become — including SSO, which we're adding to the Pro plan as part of this change. It's been one of your most frequent requests.

If you're an existing user, you're grandfathered at your current price for 12 months. Nothing changes for you until then, and we'll remind you well before it does.

Thank you for building alongside us. This change lets us keep investing in the product you rely on.

— [Founder Name]"""

out["T01"] = """Last year I sent thousands of cold emails and hit an 8% reply rate.

Most cold email fails for fixable reasons. Here are the 5 lessons that mattered: \U0001f9f5

1/ Keep it to 4 lines. Seriously. Your prospect is scanning on their phone between meetings. Four lines is enough to say who you are, why you're relevant, and what you want. Anything longer gets archived.

2/ One CTA per email. Every additional ask cuts your response rate. "Worth a 15-min chat?" beats a menu of options every time.

3/ Personalize the first line, but make it real. "Loved your post on X" only works if you actually read it. One genuine sentence beats five templated ones.

4/ Follow up. Most replies come from the 2nd or 3rd email, not the 1st. A polite bump is how deals happen. Silence is not a no.

5/ Track everything: subject lines, send times, CTAs. I only hit 8% after treating cold email like a system, not a lottery. Iterate weekly. If this helped, a repost on the first tweet goes a long way."""

out["T02"] = """Hot take: most meetings should be memos.

Writing forces clarity, respects everyone's time, and leaves a record you can actually search. If an idea can't survive being written down, it won't survive a 60-minute meeting either."""

out["T03"] = """19 months ago, I launched a $49 one-time product.

This week, we crossed $10k MRR. No funding, no team, no audience.

Here's the playbook, in 4 tweets: \U0001f9f5

1/ Start ugly. The first version was a $49 one-time purchase: no subscriptions, no dashboard, barely a landing page. It made a handful of sales, but it proved people would pay. Validation first, polish later.

2/ Listen for the pivot. Customers kept coming back with the same recurring problem, and a one-time product couldn't serve it. In month 7, we pivoted to subscriptions. Revenue dipped for a few weeks. Then it compounded.

3/ Do things that don't scale. I onboarded every early customer personally, answered every support email, and asked every churned user why they left. Those conversations became our roadmap.

4/ Patience is the moat. 19 months to $10k MRR isn't a rocket ship, and that's the point. Slow, compounding, profitable growth beats hype. If you're bootstrapping right now, keep going."""

out["T04"] = """We're open-sourcing gatekeepr, the Rust rate-limiter library we've run in production for the last 2 years.

MIT licensed. Stars, issues, and PRs all welcome. Link below."""

out["T05"] = """A new paper puts LLM-as-judge to the test, and the results matter for anyone using AI to evaluate AI.

The key findings, in 4 tweets: \U0001f9f5

1/ LLM judges agree with human evaluators 81% of the time overall. For many routine evaluation tasks, an LLM judge is a reasonable stand-in for a human rater.

2/ On creative tasks, agreement drops to 64%. When there's no objectively correct answer (style, originality, taste), LLM judges and humans part ways.

3/ One likely culprit: judges reward surface features like structure, fluency, and length over genuine creativity. They favor writing that looks good over writing that is good.

4/ Takeaway: use LLM judges for scale on objective tasks, and keep humans in the loop for creative work. 81% is not 100%, and 64% is uncomfortably close to a coin flip."""

out["E01"] = """Subject: Your trial ends in 3 days

Hi [First Name],

Your free trial ends in 3 days. After that, you'll lose access to the projects, dashboards, and workflows you've set up.

If you'd like to stay, upgrade now and get 20% off your first year with code SAVE20.

Here's what you'll keep:
- All your existing projects and data
- Full access to every feature you've been using
- Priority support whenever you need it

[Claim 20% Off →]

Questions? Just hit reply and we'll help.

Best,
The [Product] Team"""

out["E02"] = """Subject: You're invited: Scaling Postgres to 1B rows

Hi [First Name],

What happens when your Postgres database grows from millions of rows to a billion? Most teams find out the hard way. We'd like to help you skip that part.

Join us on March 14 at 2pm ET for "Scaling Postgres to 1B rows," a live 45-minute webinar (plus Q&A) led by our principal engineer. We'll cover:

- Partitioning strategies that hold up at scale
- Indexing and query patterns for billion-row tables
- The mistakes we made so you don't have to

Whether you're at 10 million rows or 900 million, you'll leave with techniques you can apply right away.

[Save My Seat →]

Can't make it live? Register anyway and we'll send you the recording.

See you there,
The [Company] Team"""

out["E03"] = """Subject: Meet Pulse: know how your team is really doing

Hi [First Name],

Today we're launching Pulse: weekly team-health surveys that live inside Slack.

Every week, Pulse asks your team a few quick questions and turns the answers into trends you can act on. No new tools to learn, no logins to remember. It all happens in Slack, where your team already works.

Setup takes 2 minutes: connect your workspace, pick your channels, and Pulse handles the rest.

What Pulse helps you do:
- Spot burnout and blockers before they become problems
- Give everyone a voice, not just the loudest in the room
- Track team health over time with zero admin work

Try Pulse free for 14 days, no credit card required.

[Start My Free Trial →]

We can't wait to hear what you think.

The Pulse Team"""

out["E04"] = """Subject: We've missed you, and we've been busy

Hi [First Name],

It's been over 60 days since we last saw you, and you picked an eventful time to step away. Here's what's new:

- A new dashboard that puts everything you care about on one screen
- Search that's now 3x faster
- Dozens of polish and performance improvements across the app

Getting back in takes exactly one click. No password reset, no setup. Your account is right where you left it.

[Reactivate My Account →]

If there's a reason you stepped away, hit reply and tell us. We read every message.

Hope to see you soon,
The [Product] Team"""

out["R01"] = """Automated code review can reduce defect rates and reviewer workload, yet existing tools remain limited in scope and precision. We present ReviewBot, an automated code-review system that combines static analysis with learned models to surface defects directly within the pull-request workflow. We evaluate ReviewBot on 1,200 pull requests drawn from 8 repositories spanning multiple languages and project sizes. ReviewBot caught 34% more defects than baseline linters, with a 12% false-positive rate that developers in our study characterized as acceptable for day-to-day use. We analyze the categories of defects where ReviewBot provides the greatest lift, finding particular strength in cross-file inconsistencies and API-misuse patterns that traditional linters routinely miss. We also discuss practical considerations for deploying automated review at scale, including reviewer trust, alert fatigue, and integration with existing continuous-integration pipelines. Our findings suggest that automated code review can meaningfully augment human reviewers, though not replace them. We outline directions for future work, including adaptive precision thresholds and repository-specific tuning, and release our evaluation framework to support reproducibility."""

out["R02"] = """Data is every enterprise's most valuable asset and, increasingly, a significant liability. To understand how organizations are managing this tension, we surveyed 156 enterprises across industries and regions about their data-governance practices, challenges, and priorities.

The findings reveal a substantial maturity gap. Most notably, 44% of surveyed enterprises have no data-classification policy, leaving them unable to consistently identify which data is sensitive, regulated, or business-critical. Without classification as a foundation, downstream controls such as access management, retention, encryption, and incident response rest on guesswork rather than policy.

The consequences show up in practice. Organizations lacking foundational governance report longer audit cycles, higher breach-response costs, and mounting friction as AI initiatives demand well-understood, well-labeled data.

To close the gap, this whitepaper recommends a 5-step maturity model that takes organizations from initial data discovery through classification, ownership, policy enforcement, and continuous monitoring. Each step includes concrete milestones and self-assessment criteria so teams can benchmark progress."""

out["R03"] = """At pilot firms deploying AI-assisted contract review, review time is down 60%. Work that once consumed days of associate attention now takes hours, freeing legal teams to focus on negotiation strategy and higher-value counsel. For legal ops leaders under pressure to do more with less, that efficiency is hard to ignore.

The caveat is hallucinated citations. AI tools can generate authorities that look entirely plausible and simply do not exist, and courts have shown little patience with filings that include them. Every AI-assisted output still needs qualified human review. No exceptions.

The profession's guardrails are taking shape, too. The ABA has issued guidance on lawyers' use of generative AI, emphasizing competence, confidentiality, and supervision. Adopt the technology, but own the output.

For legal teams, that means starting with high-volume, lower-risk workflows like contract review, measuring everything, and keeping humans firmly in the loop.

What's your team's experience with AI in legal ops? I'd love to hear it in the comments."""

path = Path(__file__).resolve().parent / "petergyang_h2.json"
atomic_write_text(path, json.dumps(out, ensure_ascii=False, indent=1) + "\n")

# Verify
with open(path, encoding="utf-8") as f:
    data = json.load(f)
expected = ["B01","B02","B03","B04","B05","B06","B07","B08","N01","N02","N03","N04","N05","T01","T02","T03","T04","T05","E01","E02","E03","E04","R01","R02","R03"]
assert sorted(data.keys()) == sorted(expected), sorted(data.keys())
assert len(data) == 25

# Tweet length check (per tweet segment, split on blank lines)
for tid in ["T01","T02","T03","T04","T05"]:
    for seg in data[tid].split("\n\n"):
        assert len(seg) <= 280, (tid, len(seg), seg[:60])

# Em dash count per item
for k, v in data.items():
    print(k, "emdash:", v.count("—"), "len:", len(v))
print("OK: 25 ids, JSON parses, tweets under 280")
