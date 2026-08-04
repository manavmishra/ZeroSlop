import json, os

out = {}

out["L01"] = """FlagShip has raised a $4.2M seed round, led by Basis Ventures.

We started 18 months ago with one belief: shipping software shouldn't be scary. Feature flags should be the foundation of how modern teams deliver, not an afterthought.

The funding lets our team of 6 grow into a real engineering org, ship faster for our early customers, and keep making feature management easier for every developer.

To our customers: thank you for betting on us early. To the team: none of this happens without you.

We're hiring. If you want to build developer tools with us, my DMs are open."""

out["L02"] = """After 9 months and 3 teams, we finished our migration from a monolith to microservices at our fintech this week.

p99 latency is down 40%. Deployments that used to take hours now take minutes. Three teams ship independently without stepping on each other.

The technical work was the easy part. The hard part was alignment: getting 3 teams to agree on service boundaries, ownership, and standards took more energy than any line of code.

What I'd tell anyone starting a migration like this:

1. Start with the domain, not the technology.
2. Migrate incrementally. Big bangs fail.
3. Celebrate small wins along the way.

People call microservices overhyped. For this job, they were the right tool.

If you've been through a big migration, I'd like to hear how it went."""

out["L03"] = """We're hiring a founding designer at our AI startup in Austin.

You'd be our first design hire, reporting directly to the CEO, with 0.5-1% equity. You'd define our visual identity and design culture from scratch and shape how people interact with AI.

We want someone who works well in ambiguity, sweats the details, and treats design as a competitive advantage.

Austin-based preferred, but we're flexible for the right person.

If this sounds like you, or someone you know, send me a DM. Referrals appreciated."""

out["L04"] = """In January, I was laid off from a big tech company.

Six months later, I've joined a 30-person startup to lead product.

The months in between were the hardest of my career. 200+ applications. Countless rejections. Interviews that went nowhere. Days where I questioned everything I thought I knew about my own value.

What I took from it: my job is not my identity, and the right opportunity was worth the wait.

To anyone navigating a layoff right now: the process is brutal, and the silence is the worst part. To the hiring managers who took the time to send thoughtful rejections: thank you. It mattered more than you know.

If you're job searching and need support, my DMs are open."""

out["L05"] = """Most AI agent startups are thin wrappers around the same 3 foundation models.

Every week another "revolutionary AI agent" launches, and the pattern is the same: a clever prompt, a polished UI, and a foundation model doing all the heavy lifting underneath.

Prompts are not a moat. Anyone can copy them in an afternoon.

Defensibility comes from workflow depth and data: embedding so deeply into how a team works that switching becomes painful, and building feedback loops that make your product smarter with use.

The winners will be the companies that understand their customers' workflows best, not the ones with the best demo.

If you're building an AI agent startup, ask yourself: if the model providers shipped your feature tomorrow, what would be left?"""

out["L06"] = """Just back from SaaStr Annual, where I met 40+ founders and sat in on dozens of sessions. Three takeaways:

1. PLG is maturing. Companies are getting genuinely sophisticated about layering sales on top of self-serve motions.

2. AI pricing is unsettled. Seat-based, usage-based, outcome-based: every founder I spoke with is experimenting, and not one sounded confident.

3. Community-led growth is back, this time with real ROI expectations attached.

If you were there, what stood out to you?"""

out["L07"] = """Roughly 70% of enterprise AI pilots never reach production, and the models aren't the reason. The models are ready.

Two things kill pilots.

Data readiness. Most enterprises are sitting on fragmented, inconsistent, poorly governed data. You can't build production AI on spreadsheets and silos.

Process redesign, or the lack of it. Too many companies bolt AI onto existing workflows. AI doesn't just automate a process; it forces you to rethink it. Skip that step and the pilot dies in the demo phase.

The companies that get AI into production do the unglamorous work first: cleaning their data, redesigning their processes, and preparing their people for change."""

out["L08"] = """Clearlens v2 is live.

Over the past year we ran 300+ customer interviews, and the two most requested features are in this release:

Session replay: watch exactly how users move through your product.
Funnel comparison: put two conversion funnels side by side and compare them.

Thank you to the 14 beta customers who tested, broke, and refined these features over the past few months.

Building this release taught us that customers already know what your roadmap should be. You just have to ask.

If you want to see what your users are actually doing inside your product, the link is in the comments."""

out["L09"] = """Ten years in B2B sales, and the #1 skill I've learned is listening.

A few years ago I was on a call with a deal that was falling apart. The prospect had concerns, and every instinct told me to jump in with answers. Instead I shut up. For 90 seconds.

The silence was excruciating. But in it, the prospect talked themselves through their own objection and revealed the real blocker, one I never would have guessed. We closed the deal two weeks later.

Prospects will tell you exactly how to sell to them if you let them. Sometimes the best discovery question is no question at all."""

out["L10"] = """After 3 years, I'm shutting down Cartful.

We raised $1.1M. We grew to 4,000 users. We poured everything we had into this company, and we never found repeatable revenue.

Writing this is painful, but I owe it to everyone who believed in us to share what I learned.

1. Users are not customers. We celebrated signups while avoiding the harder question: who will actually pay, and why?

2. Repeatable revenue beats everything. One-off deals feel like traction. They're not. If you can't describe your sales motion in one sentence, you don't have one.

3. Runway is for learning, not surviving. We stretched our runway to stay alive instead of spending it to find the truth faster.

To our investors, our team, and our users: thank you. I'm sorry we couldn't get there."""

out["L11"] = """I stopped daily standups for my team of 14.

A few months ago we replaced them with async written updates. Every morning, each person posts three things: what they did, what they're doing, and what's blocking them.

Meetings dropped by 6 hours a week. Shipping speed didn't change. Engineers report fewer interruptions and more deep work.

Most standups are for the manager, not the team. A status ritual dressed up as collaboration.

Written updates turned out better in almost every way. People think before they write. Updates are searchable and permanent. Time zones stop mattering.

Standups aren't always wrong. But if yours feels like a status meeting, it probably is one, and your team already knows it."""

out["L12"] = """I passed the AWS Solutions Architect Professional exam.

11 weeks of studying around a full-time job, 5 practice exams, and a lot of early mornings. One of the hardest certifications I've done.

What worked for me:

- Consistency over intensity. One hour every day beats eight hours on Saturday.
- Practice exams. Each of the 5 I took exposed gaps I didn't know I had.
- Build, don't just read. Hands-on labs made concepts stick in a way videos never did.
- Protect your study time like a meeting, because it is one.

If you're balancing a certification with a full-time job: it's hard, but it's possible."""

out["L13"] = """One year ago, I became an engineering manager. It's been the most humbling year of my career.

The hardest change wasn't the meetings or the difficult conversations. It was learning to measure my output by my team's work instead of my personal commits.

For years, my sense of accomplishment came from shipping code. Green squares. Merged PRs. Tangible progress I could point to at the end of every day.

Then my output became invisible. A good week meant my 7 direct reports were unblocked, growing, and shipping, while my own contributions showed up nowhere. It took me months to stop feeling like an impostor.

What year one taught me: your team's success is your success, most problems are communication problems in disguise, and the job is giving clarity, not jumping in to fix things yourself.

To every new EM struggling with the identity shift: you're not alone."""

out["L14"] = """Our team of 9 SREs committed to writing runbooks, and on-call pages dropped 30% in one quarter.

The systems didn't get better. Our knowledge stopped living only in people's heads.

What we did:

- Every incident got a runbook entry, no exceptions.
- Every repeated page triggered a documentation review.
- We deleted outdated docs as aggressively as we wrote new ones.
- Runbook quality became part of our definition of done.

The payoff: fewer 2 AM wake-ups, faster onboarding, less bus factor, calmer rotations.

If your team is drowning in pages, don't buy another tool. Write a runbook."""

out["L15"] = """After 3 years fully remote, our company went hybrid: 2 days in the office.

The good: retention is better than it's been in two years, onboarding got noticeably faster, and cross-team collaboration feels easier.

The hard: 2 senior people quit over the change, trust took a hit during the transition, and some days the office is half empty and people wonder why they commuted.

There's no perfect answer here. Every model has tradeoffs, and every policy disappoints someone. What matters is honesty. We told the team exactly why we made the change and accepted that some people would make a different choice for their lives. I respect that.

Anyone who claims remote vs hybrid is a solved problem is selling something."""

out["L16"] = """AI won't replace junior developers, but it changes what "junior" means.

We recently hired 2 junior engineers on my team. Both use AI pair-programming tools daily, and they ship production code faster than juniors did five years ago.

The skills that make them valuable have shifted: less memorizing syntax and writing boilerplate, more reviewing code critically, asking the right questions, and understanding systems. Today's junior orchestrates AI tools, verifies the output, and learns architecture from day one.

Three implications:

1. Hiring rubrics built around syntax trivia are obsolete.
2. Mentorship matters more, not less. Judgment can't be autocompleted.
3. The ladder from junior to senior is compressing.

Companies that stop hiring juniors "because AI" are cutting their future senior pipeline, not a cost."""

out["L17"] = """Last week a churned customer came back.

When they left, they told us why: our seat-based pricing punished them for growing their team. They were paying for licenses nobody used.

So we moved from seat-based to usage-based pricing. We modeled the downside a dozen times, and some advisors told us not to do it.

Since the switch, expansion revenue is up 22%, sales conversations start with value instead of license counts, and churned customers are coming back on their own.

Seat-based pricing rewarded us when customers overbought. Usage-based pricing rewards us only when our customers succeed."""

out["L18"] = """Six months ago, a bootcamp grad asked me to mentor them. This week, they signed an offer as a frontend developer at an insurance company.

The hard work was entirely theirs. I'm sharing this because the process taught me as much as it taught them.

Over 6 months we did weekly check-ins even when progress felt slow, code reviews on real projects instead of toy exercises, 4 mock interviews that got harder each time, and honest conversations about rejection.

Mentorship, it turns out, is mostly showing up consistently when someone's confidence is wavering.

The industry loves to debate whether bootcamp grads can make it. With the right support and a lot of grit, they can.

If you're an experienced developer, mentor someone. One hour a week is enough.

To my mentee: congratulations. You earned this."""

out["L19"] = """We changed one email subject line and open rates jumped 31%.

For months, our emails to 18k subscribers led with features: "New: Advanced Reporting Dashboard." Solid open rates, nothing special.

Then we described the outcome instead of the feature. Same email, same list, same send time.

Feature-focused: "New: Advanced Reporting Dashboard"
Outcome-focused: "Find out where your pipeline is leaking"

Open rate up 31%. Customers don't care about your features; they care about what the features do for them. Old lesson, but we clearly needed the reminder.

We've since rewritten every subject line in our lifecycle emails the same way.

If you write marketing emails, audit your last 10 subject lines and count how many talk about you instead of your reader."""

out["L20"] = """People ask how our 12-person team stays productive without a big ops function. We run the whole company on 5 tools:

1. Linear: every task, bug, and project. If it's not in Linear, it doesn't exist.
2. Notion: docs, wikis, meeting notes, onboarding.
3. Slack: communication, with strict channel hygiene to keep the noise down.
4. Figma: where product ideas become real before any code is written.
5. Otto: our homegrown deploy bot. One command takes code from PR to production. Everyone's favorite teammate.

No sprawling stack, no overlapping subscriptions, no "wait, which doc is the source of truth?"

Every new tool adds a tax: context switching, licenses, onboarding, integrations. We only add one when the pain of not having it beats that tax."""

out["L21"] = """I just took my first real break in 4 years. Two weeks. No Slack, no email, no "quick calls."

The first few days were deeply uncomfortable. I checked my phone out of habit. I felt guilty. I convinced myself things would fall apart without me. They didn't.

The real insight came when I got back. With fresh eyes, I could see how much of my busyness was self-inflicted. In my first week back I killed 3 recurring meetings that, it turns out, nobody missed.

Two things the break taught me: rest isn't a reward for finishing the work, because the work is never finished. And if your business can't survive 2 weeks without you, that's a design flaw, not a badge of honor.

If you're a founder or leader grinding without a break: take the two weeks."""

out["L22"] = """3 years ago, we were 4 people in a garage in Denver. This week, we hired employee #50.

I keep scrolling through old photos of that garage: the folding tables, the space heater, the whiteboard we bought off Craigslist.

Today we serve 900 customers. What I'm proudest of, though, is that the values we scribbled on that Craigslist whiteboard still guide how we operate: customers first, default to transparency, hire people better than yourself.

To our first 4: thank you for believing when there was nothing to believe in.
To our newest 46: thank you for choosing us.
To our 900 customers: everything we do is for you.

Back to work."""

out["L23"] = """Networking events are mostly useless.

I used to attend every conference, every mixer, every "founder happy hour." I collected hundreds of business cards. Total clients from all of it: zero.

My last 3 clients all came from writing online.

Writing beats networking for three reasons:

- Scale: a conversation reaches one person; a post reaches thousands.
- Selection: the right people come to you, already sold on how you think.
- Compounding: a good post keeps working for months; a handshake is forgotten by Monday.

Relationships still matter. But the best ones start when someone reads your ideas and thinks, "this person gets it."

Stop collecting business cards. Start publishing your thinking."""

out["L24"] = """I joined Supply Chain Weekly for episode 142 to talk about AI demand forecasting.

We covered why traditional forecasting breaks down in volatile markets, what AI-driven forecasting looks like in practice, and one result I keep coming back to: at one of our pilot customers, forecast error is down 18%. That means less overstock, fewer stockouts, and working capital freed up.

We also talked about the hard parts: data quality, change management, and why the forecasting team's expertise matters more with AI, not less.

Thanks to the hosts for the thoughtful questions. If you work in supply chain, operations, or planning, the episode link is in the comments."""

out["L25"] = """Our year in review.

ARR: $1.2M to $3.4M
Team: 9 to 21
NPS: 61

By almost every measure, the best year in our company's history. The number I'm proudest of is the NPS, because growth means little if customers don't love what you build.

My biggest mistake: hiring sales too early. We brought on reps before we, the founders, had nailed the sales motion ourselves. The result was months of missed targets, frustrated reps, and expensive lessons. It wasn't their fault; it was mine. You can't hand off a playbook you haven't written.

We rebuilt the process from first principles and things finally clicked, but I'd take those months back if I could.

I'm sharing the mistake because year-in-review posts usually show only the highlight reel, and growth is messier than that."""

path = "/private/tmp/claude-501/-Users-manav-Coding-Legal-Agent/db22184e-14cc-4774-85a9-20c701b2d692/scratchpad/eval/outputs/petergyang_h1.json"
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)

# verify
with open(path) as f:
    data = json.load(f)
assert len(data) == 25, len(data)
expected = ["L%02d" % i for i in range(1, 26)]
assert sorted(data) == expected, sorted(data)
for k, v in data.items():
    assert isinstance(v, str) and v.strip(), k
print("OK", len(data), "ids")
