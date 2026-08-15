# The Tell Taxonomy

Eighty tells in six families, merged from WP:AICATCH (Wikipedia's editor
catalog, built from thousands of caught instances), the de-slop/stop-slop
detector line, petergyang/no-ai-slop, blader/humanizer, the academic
lexicon studies (Kobak, Liang, Juzek & Ward), and community taxonomies of
reader-reported tells. The scorer
(`scripts/slopscore.py`) catches the lexically detectable ones; the rest need
judgment. **Clusters convict, singles don't** — one "robust" in technical prose
is nothing; five tells in one paragraph is a verdict. Shared idioms humans
still use ("elephant in the room") carry low weights for exactly that reason:
alone they prove nothing, five in a page is the machine's idiom autopilot.

## 1. Lexical

| Tell | Fix |
|---|---|
| AI vocabulary: delve, tapestry, testament, realm, intricate, interplay, landscape, meticulous, pivotal, garner, bolster, underscore, showcase, foster, boasts | Plain word or the specific thing. "delve into" → "look at"; "the AI landscape" → name the actual companies/tools |
| Marketing register: seamless, frictionless, cutting-edge, game-changer, state-of-the-art, supercharge, paradigm shift, empower | Delete or state the concrete capability |
| Rider buzzwords (leverage, robust, unlock, harness, streamline) | Fine in plain technical prose; slop when clustered with marketing words |
| Puffery: nestled, breathtaking, rich heritage, renowned, vibrant, groundbreaking | State the fact; let the reader judge importance |
| Legacy phrases: "a testament to", "pivotal moment", "enduring legacy", "evolving landscape", "setting the stage" | Say what happened |
| Copula avoidance: "serves as", "stands as", "functions as", "boasts", "features" | "is" / "has" |
| Stiff synonyms: utilized, authored, attempted, relocated | used, wrote, tried, moved |
| Vague quantifiers: "a wide variety of", myriad, plethora, countless, numerous | The number, or "many", or cut |
| Filler intensifiers: truly, genuinely, incredibly, undoubtedly | Cut; keep only when carrying real emphasis in the writer's voice |
| Degree intensifiers (very, really + adj) | Weak signal alone; cut in clusters |
| Business jargon: circle back, move the needle, low-hanging fruit, deep dive, double-click, boil the ocean, table stakes, north star, hit the ground running | The actual verb |
| Amplified stats: a whopping, a staggering, jaw-dropping, mind-blowing, skyrocket | State the number plainly; it carries its own weight |
| Catalog superlatives: unmatched, unrivaled, top-notch, industry-leading, must-have, hassle-free, second to none, look no further | One concrete differentiator, or nothing |
| Startup-bio vocab: visionary, trailblazing, on a mission to, passionate about, at the intersection of, thought leader | Say what you build and for whom |
| Travel-brochure vocab: picturesque, quintessential, captivating, in the heart of, perfect blend of, something for everyone | The specific detail a visitor would notice |
| Idiom autopilot: double-edged sword, tip of the iceberg, elephant in the room, perfect storm, game changer, best of both worlds, win-win, paves the way, bridge the gap, at the forefront, uncharted territory, new normal, full circle, wild west | Pre-assembled phrase → disassemble: say the actual trade-off, risk, or change |
| 2025+ era shift: emphasizing, enhance, highlight(ing), showcasing now outrank delve | Same fix; keep `data/learned.json` current |

## 2. Structural

| Tell | Fix |
|---|---|
| Listicle stems: "There are several key factors…", "Here are 5…" | Make the first point; structure follows argument |
| "Not only X but also Y" | Pick the stronger of X/Y, state it |
| Dead transitions: Moreover, Furthermore, Additionally at sentence start | "but", "so", "and", or nothing — humans cohere with connective texture, not scaffolding |
| Wrap-up scaffolding: "In conclusion", final paragraph restating the piece | End on the last concrete point or consequence |
| Rule of three: "fast, reliable, and scalable" | Two items, or one, or an actual list with content |
| "Challenges and future prospects" formula | Delete the formula; report the one real challenge |
| Rigid outline: every paragraph topic-sentence + 3 supports + mini-conclusion | Reorder; let paragraph lengths vary; put the best claim first |
| Participial analysis tails: "…, highlighting the importance of X" | Full stop, then the actual consequence ("so users can…") or nothing |
| Inline-header bullet lists (• **Header:** text) | Prose, unless it's truly a list |
| Tiny tables for prose content | Prose |
| Transformation chains: "X becomes Y. Y becomes Z." | One plain causal sentence |
| Synonym cycling (the agent/the assistant/the tool for one referent) | Repeat the clear word |
| Stacked hedges: "might possibly", "could potentially perhaps" | One hedge or none |
| Explainer stems: "in a nutshell", "simply put", "long story short", "when it comes to", "at its core", "in essence" | Cut the stem; start at the content |
| "Here's how/why/a breakdown" stems | Start with the thing itself |
| Imperative flip: "Stop X. Start Y.", "Do this instead" | Make the one claim, with the reason |
| Forecast wrap-ups: "as we move forward", "the road ahead", "as technology continues to evolve" | End on the concrete point or consequence |

## 3. Rhetorical

| Tell | Fix |
|---|---|
| Empty hedging: "It's worth noting that", "it's important to note" | Delete the stem; keep the content |
| Didactic disclaimers: "it's crucial to remember", "results may vary" | Delete unless a real caveat, then state it precisely |
| Manufactured stakes: "in today's fast-paced world", "now more than ever" | Start where the reader needs to start |
| Performed candor: "let's be honest", "here's the thing", "truth be told" | State the point |
| Rhetorical-question openers: "Ever wondered…?", "What if I told you…?" | The answer, as a statement |
| Throat-clearing: "The uncomfortable truth is", "Let me be clear" | Cut; the claim stands alone |
| Emphasis crutches: "Make no mistake", "Let that sink in", "Read that again" | Show the weight with the fact itself |
| Meta-commentary: "In this post we'll explore", "Let me walk you through" | Just do it |
| Corrective reveal: "You've been told X. Here's the truth" | Make the claim without the posture |
| Binary contrast reveal: "The answer isn't X. It's Y." | "Y matters more than X" — and at most once per piece |
| Negative parallelism family: "It's not just X, it's Y" / "No X. No Y. Just Z." / "It wasn't A. It wasn't B. It was C." | State the positive claim once |
| Contrast reveal, extended: "isn't about X — it's about Y" (any subject, any separator), "less about X, more about Y", "didn't just X. We Y", "was never about X", "That's not X. That's Y.", "AI won't replace you. Someone using AI will." | State the positive claim once; the meter now catches every separator and subject |
| Fake epiphany: "that's when it hit me", "little did I know", "changed everything", "the rest is history", "fate had other plans" | Tell the event; skip the drumroll |
| Certainty theater: "cannot be overstated", "one thing is certain", "nothing could be further from the truth", "Full stop.", "Period.", "End of story.", "would be an understatement" | Assert it once, plainly; evidence over volume |
| Non-conclusions: "only time will tell", "remains to be seen", "the jury is still out", "the possibilities are endless", "exciting times ahead" | Commit to the call the evidence supports, or cut |
| Crowd priming: "sound familiar?", "we've all been there", "you might be wondering", "believe it or not", "trust me", "hear me out" | Respect the reader; make the claim |
| Borrowed proverbs: "Rome wasn't built in a day", "the proof is in the pudding", "actions speak louder than words" | Your own words or nothing |
| Manufactured-world openers: "Gone are the days", "In a world where", "Imagine a world where", "Picture this:", "It's 2026 and", "It's no secret that" | Start at the specific situation |
| Forced profundity: "You can't have one without the other" | Earn it or cut it |
| Calls to action: "Buckle up", "Let's dive in", "Stay tuned" | Cut |
| Weasel attribution: "Experts agree", "Studies show", "Industry reports suggest" | Name the source or cut the claim; if no source exists, ask the author |
| Canned coverage claims: "featured in prominent media outlets" | Name the outlet and what it said |

## 4. Punctuation & formatting

| Tell | Fix |
|---|---|
| Em-dash overuse (density; 2+ in a sentence; spaced pairs as drama) | Commas, periods, parentheses; ≤1 per ~150 words; zero on LinkedIn |
| Title Case Headings everywhere | Sentence case |
| Bold spam mid-sentence | Unbold; if it needs emphasis, restructure |
| Emoji as bullets/headers (🚀 ✅ 👉) | Remove |
| Hashtag clusters | Zero in body; move to first comment if needed |
| Markdown artifacts in plain-text contexts | Strip |
| Chatbot markup leakage (oaicite, citeturn0…, [cite: 1], utm_source=chatgpt.com) | Strip — these are proof, not style |
| Placeholders left in ([Your Name], [Company]) | Fill or flag |
| Curly-quote inconsistency | Normalize to the document's convention |

## 5. Tone

| Tell | Fix |
|---|---|
| Assistant voice: "Great question!", "I hope this helps", "I'd be happy to" | Delete |
| Chatbot residue: "Would you like me to…", "Let me know if you'd like…", "my training data" | Delete — it is proof of paste, not style |
| Knowledge-cutoff residue: "as of my last update", "not widely documented" | Delete; verify the claim |
| Form-letter email: "wanted to reach out", "touch base", "don't hesitate to reach out" | Say the actual ask in the first sentence |
| LinkedIn ritual: "some personal news", "a new chapter", "bittersweet", "couldn't be prouder", "this is your sign", "I'll go first", "today years old" | The fact, then stop; feeling shown through detail |
| Promotional drift in neutral contexts | Neutral statement of fact |
| Uniform flawless register (every sentence equally polished) | Vary: blunt next to careful, casual next to technical |
| Excess positivity, joy-skewed affect | Allow doubt, irritation, dry humor where genuine |
| Fake humanization (edgy-slop) | See `overcorrection.md` — it's still slop |

## 6. Content-emptiness (judgment only — no regex can see these)

| Tell | Test | Action |
|---|---|---|
| Hollowness — no claim at all | Removal test: delete it; anything lost? | Flag, never pad |
| Regression to the mean — specifics smoothed into generic + inflated importance | Compare against source facts | Restore the specific |
| Smooth-but-empty specificity — "modern technologies that ensure reliability" | Can you name the referent? | Name it or cut |
| Superficial analysis — unearned significance commentary | Who says it matters? | State the mechanism or cut |
| Fabricated support — invented citations, stats, anecdotes | Verify every reference | Remove; ask author for real one |
| Speculative gap-filling — "likely supports…" | Is there a source? | Cut or mark as open question |

## What is NOT a tell (do not flag)

Perfect grammar. Formal prose where the genre demands it. A transition word in
isolation. Long sentences that earn their length. Technical vocabulary used
technically. A single em-dash doing real work. First-person hedging that
encodes real uncertainty. Unsourced-but-checkable claims. And any pattern that
is demonstrably the writer's own voice — the writing sample outranks the list.
