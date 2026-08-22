import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from safeio import atomic_write_text  # noqa: E402

posts = {}

posts["L01"] = """FlagShip raised a $4.2M seed round led by Basis Ventures.

We started building 18 months ago with one belief: shipping software shouldn't be scary. Feature flags belong at the foundation of how teams deliver, and we've spent those 18 months building the platform that treats them that way.

The round funds two things: growing our team of 6 into a real engineering org, and shipping faster for the customers who signed on early.

To those customers, thank you for trusting an unfinished product. To Basis Ventures, thank you for leading the round.

We're hiring. If you want to build developer tools with us, send me a message."""

posts["L02"] = """Nine months and 3 teams later, our fintech runs on microservices instead of the monolith. We finished the cutover this week.

p99 latency dropped 40%. Deployments that took hours now take minutes, and the 3 teams ship without stepping on each other.

The code was the easy part. Getting 3 teams to agree on service boundaries and ownership took more energy than any refactor.

Two lessons I'd hand anyone starting a similar migration: model services around the business domain before you touch the technology, and migrate one slice at a time. A big-bang rewrite would have buried us by month two.

If you've lived through a migration like this, tell me your war story."""

posts["L03"] = """We're hiring a founding designer at our AI startup in Austin.

You'd be our first design hire, reporting to the CEO, with 0.5–1% equity. You'd define the visual identity and the design culture, and you'd shape how people experience AI inside our product.

We want someone who sweats the details and treats design as a competitive advantage.

Austin preferred. We'll flex for the right person.

If that's you, or someone you know who fits, send me a message or share this post. Referrals welcome."""

posts["L04"] = """A big tech company laid me off in January.

Six months later, I'm leading product at a 30-person startup.

The months in between were the hardest of my career. I sent 200+ applications and stopped counting the rejections. Some weeks I questioned what my work was worth.

Two things carried me through: separating who I am from what my badge said, and holding out for a role I wanted rather than the first exit from the search.

To the hiring managers who sent real rejection notes instead of silence: thank you. Those notes mattered.

If you're in the middle of a search, message me. I'll answer."""

posts["L05"] = """Most AI agent startups are thin wrappers around the same 3 foundation models.

Watch the next "revolutionary agent" that crosses your feed: a clever prompt and a polished UI, with a foundation model doing the work underneath. A competitor can copy that prompt in an afternoon.

You earn a moat two ways. Workflow depth: embed into how a team works until switching hurts. Proprietary data: build feedback loops that sharpen the product with use.

The winners will understand their customers' workflows better than the model providers do.

If the providers shipped your feature tomorrow, what would you have left?"""

posts["L06"] = """Back from SaaStr Annual, where I met 40+ founders across sessions and hallway conversations. I'm carrying home 3 takeaways.

1. PLG is maturing. Companies have moved past the buzzword and are getting disciplined about layering sales on top of self-serve motions.

2. AI pricing is unsettled. The founders I asked are experimenting across seat-based, usage-based, and outcome-based models, and none of them sounded confident.

3. Community-led growth is back, and this time it comes with ROI expectations attached.

The energy in SaaS feels higher than it has in years. If you were there, tell me your biggest takeaway; I want to compare notes."""

posts["L07"] = """About 70% of enterprise AI pilots never reach production.

The models are ready and have been for a while. The blockers sit in data readiness and process redesign.

Data first: most enterprises run on fragmented, ungoverned data scattered across spreadsheets and silos. No model compensates for that.

Process second: companies bolt AI onto existing workflows and expect magic. AI pays off when you redesign the process around it, and teams that skip the redesign retire their pilots at the demo stage.

The companies that reach production did the unglamorous work first. They cleaned their data and rebuilt their workflows before scaling anything.

If your pilots sit stuck in the demo phase, audit your data and your process map before you blame the model."""

posts["L08"] = """Clearlens v2 is live.

Over the past year we ran 300+ customer interviews and heard two requests more than any others: session replay and funnel comparison. Both ship today.

Session replay shows you how users move through your product, moment by moment. Funnel comparison puts two funnels side by side so you can see which version converts.

Our 14 beta customers spent the last few months breaking these features and telling us where they fell short. Thank you; you set this roadmap.

Come see what your users do inside your product. Link in the comments."""

posts["L09"] = """Ten years in B2B sales, and the skill I rank first is listening.

A few years ago I was on a call watching a deal fall apart. The prospect had concerns, and I wanted to jump in with answers. Instead I shut up for 90 seconds.

Those seconds felt endless. In the silence, the prospect talked through their own objection and named the real blocker, one I would not have guessed. We closed the deal two weeks later.

A decade of calls left me with two habits. Give prospects room; they'll tell you how to sell to them. Treat silence as a discovery question.

Tell me the sales lesson you learned the hard way."""

posts["L10"] = """After 3 years, I'm shutting down Cartful.

We raised $1.1M and grew to 4,000 users, but we never found repeatable revenue.

I owe the people who believed in us an honest account. I'm leaving with three lessons.

1. Users are not customers. We celebrated signups and dodged the harder question: who pays, and why?

2. We mistook one-off deals for traction. We couldn't describe our sales motion in one sentence, and that was the tell.

3. We treated runway as time to survive. It should have been budget for learning the truth faster.

To the people who built Cartful and the people who bet on it, with money or with their time: thank you. I'm sorry we couldn't get there."""

posts["L11"] = """I stopped daily standups for my team of 14.

A few months ago we replaced the meeting with async written updates. Each morning, each person posts what they're working on and what's blocking them.

We cut 6 hours of meetings a week, and shipping speed held steady. Engineers report fewer interruptions and longer stretches of deep work.

Our standup had served me, the manager, more than it served the team. I wanted a live status feed; the team wanted their mornings back.

Writing raised the quality of the updates too. People think before they type, and the record stays searchable months later.

If your standup exists to collect status, collect it in writing for a month and see what breaks."""

posts["L12"] = """I passed the AWS Solutions Architect Professional exam.

It took 11 weeks of studying around a full-time job, plus 5 practice exams and a long run of early mornings.

Two things made the difference. The practice exams, each of which exposed gaps I didn't know I had. And hands-on labs, because building the architectures made them stick where videos didn't.

The schedule mattered as much as the material. I studied one hour a day and defended that hour like a meeting.

If you're working toward a certification around a full-time job, it's a grind and it's doable. Tell me which one you're chasing; I'll cheer you on."""

posts["L13"] = """One year ago I became an engineering manager. It has humbled me more than any other year of my career.

The hardest change was learning to measure my output by my team's work instead of my personal commits.

For years my sense of progress came from shipping code: green squares and merged PRs, something concrete to point at by the end of the day. Then my output turned invisible. A good week now means my 7 direct reports are unblocked and shipping while my own contributions show up nowhere. I spent months feeling like an impostor.

Year one left me with two lessons. Most of the fires I chased started as communication gaps. And grabbing the keyboard to fix things myself, the move that felt most helpful, stalled my team fastest.

If you moved into management this year and miss the green squares, the feeling fades. Tell me the hardest lesson from your first year."""

posts["L14"] = """Our team of 9 SREs committed to writing runbooks. One quarter later, on-call pages dropped 30%.

Our systems didn't get better. We moved the knowledge out of individual heads and onto pages the whole rotation can follow at 2 AM.

The practice stayed simple. We wrote a runbook entry for each incident and treated a repeated page as a documentation bug. We deleted stale docs as fast as we wrote new ones.

The 30% shows up as fewer 2 AM wake-ups and a calmer rotation, and new engineers now onboard from the same pages.

If your team is drowning in pages, write a runbook before you buy another tool."""

posts["L15"] = """After 3 years as a remote-only company, we went hybrid: 2 days a week in the office.

Retention improved to its best level in two years, and onboarding got faster.

The change also cost us. 2 senior people quit over it, and trust dipped during the transition. On quiet days the office sits half empty while people question the commute.

We told the team the reasoning behind the move and accepted that some would make a different call for their lives. The two who left made that call, and I respect them for it.

I can't score this as a clean win or a clean loss: better retention on one side, two empty desks on the other.

If your company has settled on a model, tell me how it's holding up."""

posts["L16"] = """AI won't replace junior developers, but it is rewriting the job description.

We hired 2 junior engineers on my team this year. Both ship production code with AI pair-tools, and they ship faster than the juniors I worked with five years ago.

Syntax recall and boilerplate count for less than they did. The juniors who stand out review generated code with a critical eye and absorb architecture from day one, because boilerplate no longer fills their weeks.

Two consequences for hiring. Interview rubrics built on syntax trivia now test for the wrong job. And mentorship matters more, because no tool autocompletes judgment.

A company that stops hiring juniors "because AI" is cancelling its senior pipeline five years out.

Tell me whether your team still hires juniors, and why."""

posts["L17"] = """A churned customer came back last week.

They told us why on the way out: our seat-based pricing punished them for growing their team, and they were paying for licenses that sat unused.

We switched to usage-based pricing. We modeled the downside a dozen times first, and a few advisors told us to keep the seats.

Since the switch, expansion revenue is up 22%. Sales conversations now start with what a customer uses, and churned customers have begun coming back on their own.

The old model paid us when customers overbought. The new one pays us when customers get value.

If your company has rewritten its pricing, tell me how it went."""

posts["L18"] = """Six months ago, a bootcamp grad asked me to mentor them. This week they signed an offer as a frontend developer at an insurance company.

The hard work was theirs. I supplied structure: weekly check-ins even when progress felt slow, and code reviews on real projects instead of toy exercises. We ran 4 mock interviews, each harder than the last, and talked through the rejections in between.

The mentoring taught me something too: consistency carried more weight than expertise. On the weeks their confidence dipped, showing up on schedule mattered more than any advice I gave.

Debates about whether bootcamp grads can make it keep circulating. Mine made it, with grit and six months of steady support.

If you have a few years of experience, take on a mentee. It cost me an hour a week.

To my mentee: congratulations. You earned this."""

posts["L19"] = """We changed one email subject line and open rates jumped 31%.

For months our emails to 18k subscribers led with features: "New: Advanced Reporting Dashboard." Solid open rates, nothing special.

Then we rewrote a single subject line to name the outcome instead of the feature. Same email, same list, same send time.

Feature version: "New: Advanced Reporting Dashboard"
Outcome version: "Find out where your pipeline is leaking"

The outcome version lifted opens 31%. The first line talks about us; the second talks about the reader's pipeline.

We've since rewritten the subject line of our lifecycle emails on the same principle, and the gains have continued.

Audit your last 10 subject lines. Count how many talk about you and how many talk about your reader."""

posts["L20"] = """Our 12-person team runs the whole company on 5 tools.

Linear holds the work. We track it there down to the smallest bug and treat anything outside Linear as nonexistent.

Notion stores the docs, from meeting notes to onboarding guides.

Slack carries the day-to-day conversation, with strict channel hygiene to keep the noise down.

Figma is where we shape product ideas before anyone writes code.

Otto, our homegrown deploy bot, takes code from PR to production on one command. Ask the team to pick a favorite and they'll name Otto.

Each new tool adds a tax in context-switching and onboarding, so we only add one when the pain of going without it exceeds that tax.

Tell me which tools your team refuses to give up."""

posts["L21"] = """I took my first real break in 4 years: two weeks with no Slack and no email.

The first days felt wrong. I checked my phone out of habit and braced for things to fall apart without me. Nothing did.

I got the real value after I returned. With two weeks of distance, most of my busyness looked self-inflicted, and in my first week back I killed 3 recurring meetings. No one asked where they went.

I brought two lessons home. The work doesn't finish, so I stopped waiting for a finished stretch to rest. And a business that can't survive two weeks without its founder has a design flaw.

If you lead a team and haven't taken a real break in years, book the two weeks. Then reread your calendar when you get back."""

posts["L22"] = """Three years ago, we were 4 people in a garage in Denver. This week we hired employee #50.

I keep going back to the photos from that garage, the folding tables and the whiteboard we bought off Craigslist.

We serve 900 customers today, and the growth is worth celebrating. The part I'm proudest of sits elsewhere: the values we scribbled on that Craigslist whiteboard still guide how we operate. Customers come first, and we hire people better than ourselves.

To the first 4: thank you for believing when there was nothing to believe in. To the 46 who joined since: thank you for choosing us.

Now back to work."""

posts["L23"] = """Networking events are close to useless for winning clients.

For years I attended the conferences and the founder happy hours, and I collected hundreds of business cards. I won zero clients from all of it. My last 3 clients came from one channel: writing online.

Writing beats the conference circuit on two counts. A post reaches thousands of readers while a conversation reaches one, and the people who reach out after reading arrive pre-sold on how I think.

Relationships still close deals. Mine now start when someone reads a piece of mine and decides I understand their problem.

If your pipeline runs on conferences, publish your thinking for a quarter and compare the results."""

posts["L24"] = """I joined Supply Chain Weekly for episode 142 to talk about AI demand forecasting.

I keep coming back to one number from the conversation: at one of our pilot customers, forecast error is down 18%. In practice that means less overstock and fewer stockouts, which frees working capital.

We dug into why traditional methods break down in volatile markets and what AI-driven forecasting looks like past the buzzwords. We stayed honest about the hard parts too, data quality and change management above all, and about why a forecasting team's expertise counts for more once AI enters the loop.

Thanks to the hosts for questions that went past the talking points.

If you work in supply chain or planning, give episode 142 a listen. Link in the comments."""

posts["L25"] = """Our year in review: the numbers and the mistake I'd take back.

ARR grew from $1.2M to $3.4M. The team grew from 9 to 21. NPS came in at 61, and of the three numbers, the 61 makes me proudest, because it means the growth came with customers who'd recommend us.

The mistake: I hired salespeople too early. We brought reps on before we, the founders, had nailed the motion ourselves, which meant we handed them a playbook we hadn't written. They spent months missing targets through no failure of theirs. The fault was mine.

We rebuilt the sales process from first principles, and the reps started hitting their numbers. I'd still take those months back if I could.

I'm including the mistake because the highlight reel alone would flatter us.

Tell me your biggest lesson from the year."""

out = Path(__file__).resolve().parent / "stopslop_h1.json"
atomic_write_text(out, json.dumps(posts, indent=1, ensure_ascii=False) + "\n")

# verify
with open(out) as f:
    data = json.load(f)
expected = ["L%02d" % i for i in range(1, 26)]
assert sorted(data.keys()) == expected, sorted(data.keys())
assert all(isinstance(v, str) and v.strip() for v in data.values())
# guard: no em dashes anywhere
bad = [k for k, v in data.items() if "—" in v]
assert not bad, bad
print("OK", len(data), "posts written")
