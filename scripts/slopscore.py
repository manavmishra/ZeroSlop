#!/usr/bin/env python3
"""slopscore — statistical AI-slop scorer for the zero-slop skill.

Computes an AI-likelihood score (0-100) for a piece of prose from measurable
features: pattern-tell density, lexical over-representation, rhythm uniformity
(anti-burstiness), punctuation/formatting densities, and register signals.

The score is a *surface-tell meter*, not a truth oracle: a low score means "no
measurable tells", not "good writing". Hollowness (no claim present) is
invisible to any regex — the skill's judgment pass covers that.

Usage (runnable from any cwd; data resolves relative to this script):
    python3 slopscore.py <file>            # pretty report
    python3 slopscore.py --json <file>     # machine-readable
    python3 slopscore.py --dna a.md b.md   # channel anatomy, before vs after
    python3 slopscore.py --fidelity a.md b.md  # facts kept? anything invented?
    cat text | python3 slopscore.py        # stdin
    python3 slopscore.py --explain <file>  # report + hits + heatmap
    python3 slopscore.py --heatmap <file>  # per-sentence heatmap only
    python3 slopscore.py --formal <file>   # research/professional genres:
                                           # zeroes rhythm-uniformity and
                                           # formality penalties (formal
                                           # register is native there; gate on
                                           # tell density instead)

Pattern/lexicon data lives beside this script in ../data/patterns.json and
../data/learned.json (same schema; learned merges over base — this is the
continuous-learning hook). Editing data files requires no code change.
"""
import json
import math
import re
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SHAPE_SOLO_THRESHOLD = 0.62  # calibrated, see calibrate.py --shape


# Where personal voice profiles live — outside the repo, since they are the
# user's own writing. One file per author, git-ignored by construction.
import os
HOME = Path(os.environ.get("ZERO_SLOP_HOME", Path.home() / ".zero-slop")).expanduser()


def load_patterns(voice=None):
    base = json.loads((DATA_DIR / "patterns.json").read_text())
    learned_path = DATA_DIR / "learned.json"
    if learned_path.exists():
        try:
            learned = json.loads(learned_path.read_text())
            # Last-wins by name. Appending made --demote do the opposite of
            # its name: a softened copy joined the original instead of
            # replacing it, so halving a weight of 4 produced an effective 6.
            _by = {q["name"]: q for q in base["patterns"]}
            _order = [q["name"] for q in base["patterns"]]
            for q in learned.get("patterns", []):
                if q["name"] not in _by:
                    _order.append(q["name"])
                _by[q["name"]] = q
            base["patterns"] = [_by[n] for n in _order]
            base["lexicon"].update(learned.get("lexicon", {}))
            # riders too: the reflect loop promotes single words as riders, and
            # for a while it wrote them somewhere nothing ever read.
            base.setdefault("riders", {}).update(learned.get("riders", {}))
            # Drop entries whose regex will not compile. SECURITY.md promises a
            # malformed learned file degrades to base patterns; that was only
            # true for JSON errors — one bad `rx` raised re.error at scan time
            # and took the scorer down with it.
            good = []
            for q in base["patterns"]:
                try:
                    re.compile(q["rx"])
                    good.append(q)
                except (re.error, KeyError, TypeError):
                    pass
            base["patterns"] = good
        except Exception:
            pass  # a malformed learned file must never break scoring
    if voice:
        _apply_voice(base, voice)
    return base


def _apply_voice(base, name):
    """Personalise the meter to one author. Their profile lists words and
    patterns they genuinely use; each gets its weight cut or zeroed, so the
    author's own voice stops reading as slop while every other user's meter is
    unchanged. A writing sample outranks a global rule — that is the whole point
    of a linter you can teach rather than one you fight."""
    prof_path = HOME / "voices" / f"{name}.json"
    if not prof_path.exists():
        return
    try:
        prof = json.loads(prof_path.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return
    keep = {k.lower() for k in prof.get("keep", [])}   # words this author owns
    for term in list(base.get("lexicon", {})):
        if term.lower() in keep:
            base["lexicon"][term] = 0
    for term in list(base.get("riders", {})):
        if term.lower() in keep:
            base["riders"][term] = 0
    for pat in base["patterns"]:
        if pat["name"] in prof.get("mute", []):
            pat["w"] = 0


SENT_SPLIT = re.compile(r"(?<=[.!?])[\")”’]?\s+(?=[A-Z“\"(0-9])")
WORD = re.compile(r"[A-Za-z’']+")


def strip_noise(text):
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    # Inline `code` spans still render as visible prose, so their words are
    # scored; only the backticks go. Fenced blocks are genuinely code.
    text = re.sub(r"`([^`\n]*)`", r"\1", text)
    text = re.sub(r"https?://\S+", " ", text)
    return text


def sentences(text):
    parts = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        for s in SENT_SPLIT.split(para.replace("\n", " ")):
            s = s.strip()
            if len(WORD.findall(s)) >= 2:
                parts.append(s)
    return parts


def cv(values):
    if len(values) < 2:
        return 1.0
    m = sum(values) / len(values)
    if m == 0:
        return 1.0
    var = sum((v - m) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(var) / m


def score_text(text, data, formal=False):
    raw = text
    text = strip_noise(text)
    words = WORD.findall(text)
    n_words = max(len(words), 1)
    sents = sentences(text)
    hits = []

    # 1. Pattern tells (regex, weighted)
    for p in data["patterns"]:
        if not p.get("w"):
            continue
        for m in re.finditer(p["rx"], text, re.I | (re.M if p.get("m") else 0)):
            hits.append({
                "cat": p["cat"], "name": p["name"], "w": p["w"],
                "quote": m.group(0)[:90].strip(),
            })

    # 2. Lexicon. Two tiers, because context decides. Always-on terms
    # ("delve", "tapestry") almost never appear in honest prose. Rider terms
    # ("robust", "landscape", "elevated") are ordinary technical vocabulary
    # and only count when a marketing-register trigger shares their sentence —
    # so "elevated write volume" in a runbook is silent while "elevate your
    # brand with our seamless platform" fires. Sentence-scoped, not global.
    lower = text.lower()
    for term, w in data["lexicon"].items():
        if not w:
            continue
        for m in re.finditer(r"\b" + re.escape(term) + r"\w*", lower):
            hits.append({"cat": "lexicon", "name": term, "w": w, "quote": m.group(0)})
    riders, triggers = data.get("riders", {}), data.get("rider_triggers", [])
    if riders:
        for sent in sents:
            sl = sent.lower()
            if not any(t in sl for t in triggers):
                continue
            for term, w in riders.items():
                if not w:
                    continue
                for m in re.finditer(r"\b" + re.escape(term) + r"\w*", sl):
                    hits.append({"cat": "rider", "name": term, "w": w,
                                 "quote": m.group(0)})

    pattern_weight = sum(h["w"] for h in hits)
    # Density window is floored at 60 words (a single tell in a 7-word tweet
    # must not read as 100/100) and the long-text dilution is bounded by also
    # tracking absolute weight: a 2000-word piece cannot hide 20 tells.
    tell_density = 100.0 * pattern_weight / max(n_words, 60)
    tell_density = max(tell_density, min(pattern_weight / 3.0, 14.0))

    # 3. Rhythm: burstiness = coefficient of variation of sentence lengths.
    # Human prose ~0.55-0.75; machine prose clusters ~0.25-0.45.
    slens = [len(WORD.findall(s)) for s in sents]
    burstiness = cv(slens)
    # Short texts give unstable CV estimates — scale the penalty in by length.
    length_conf = min(1.0, len(sents) / 8.0)
    uniformity_penalty = 0.0 if formal else (
        max(0.0, (0.42 - burstiness)) * 35 * length_conf)

    # 4. Punctuation / formatting densities (per 100 words)
    emdash = 100.0 * len(re.findall(r"—|--", raw)) / max(n_words, 120)
    # Capped: dash-heavy but otherwise excellent prose (Lincoln, Dickinson)
    # must not be convicted on punctuation alone.
    emdash_penalty = min(max(0.0, emdash - 0.6) * 6, 8.0)
    emoji = len(re.findall(r"[\U0001F300-\U0001FAFF✅✨⚡\U0001F449\U0001F447\U0001F680\U0001F525]", raw))
    emoji_penalty = min(emoji * 2.0, 12)
    # Bold as mid-sentence emphasis is the tell (WP:AICATCH); bold used as a
    # label at the start of a line/list item is ordinary document formatting.
    bold = sum(1 for m in re.finditer(r"\*\*[^*\n]{2,60}\*\*", raw)
               if not re.match(r"[\s>*#-]*(?:\d+\.\s*)?$",
                               raw[raw.rfind("\n", 0, m.start()) + 1:m.start()]))
    bold_penalty = min(max(0, bold - 1) * 1.5, 9)
    hashtags = len(re.findall(r"(?<!\S)#\w+", raw))
    hashtag_penalty = min(hashtags * 1.2, 8)

    # 5. Register: contraction scarcity in casual genres reads machine-formal.
    contractions = len(re.findall(r"\b\w+[’'](?:t|s|re|ve|ll|d|m)\b", text))
    contraction_rate = 100.0 * contractions / n_words
    formality_penalty = 0.0 if formal else (
        3.0 if contraction_rate < 0.4 and n_words > 80 else 0.0)

    # 6. Followability: density without accessibility reads machine-compressed,
    # not expert. Signals: noun-phrase chains (many commas, no verbs between),
    # heavy polysyllabic ratio, and overlong sentences. Formal genres exempt
    # (their register legitimately runs denser).
    poly_ratio = sum(1 for w in words if len(w) >= 9) / n_words
    chain_frac = sum(1 for s in sents if s.count(",") >= 4) / max(len(sents), 1)
    overlong_frac = sum(1 for L in slens if L > 38) / max(len(slens), 1)
    followability_penalty = 0.0 if formal else min(
        max(0.0, poly_ratio - 0.14) * 40 + chain_frac * 9 + overlong_frac * 7,
        12.0)

    # Clusters convict, singles don't. Em-dash density and missing contractions
    # are stylistic habits, not evidence on their own — 19th-century oratory and
    # plenty of excellent formal prose trip both. So corroborate them against
    # lexical evidence: with no tells present they contribute little. Emoji,
    # hashtags and bold spam stay at full strength (they convict alone), and
    # burstiness is an independent statistical signal, so neither is scaled.
    # The floor was 0.45, which handed style 45% weight on text with no lexical
    # evidence whatsoever. Measured against genuine human technical prose that
    # convicted 5 of 8 documents: AGENTS.md scored 59.2 on one weight-2.5 hit in
    # 392 words. Corroboration has to be earned, so the floor is now low enough
    # that dashes and formal register alone cannot carry a verdict.
    corroboration = min(1.0, 0.10 + tell_density / 2.5)
    stylistic = ((emdash_penalty + formality_penalty) * corroboration
                 + uniformity_penalty + followability_penalty)
    # No lexical evidence at all means no cluster, and the rule is that
    # clusters convict. Style alone (dashes, long sentences, formal register,
    # even rhythm) describes plenty of excellent human prose — 19th-century
    # oratory, dense technical writing — so with zero tells and zero emoji or
    # hashtag spam, style can raise suspicion but must never convict.
    # Weighted evidence, not hit count. Keying on `not hits` meant a single
    # light tell — one arrow in a spec, one borderline word — escaped the clamp
    # entirely and unlocked the full stylistic penalty. A lone weak hit is not
    # a cluster, and clusters are what convict.
    if tell_density < 1.5 and emoji == 0 and hashtags == 0:
        stylistic = min(stylistic, 3.5)
    evidence = (
        tell_density * 1.15
        + stylistic
        + emoji_penalty
        + bold_penalty
        + hashtag_penalty
    )
    ai_likelihood = round(100 / (1 + math.exp(-(evidence - 9.0) / 4.0)), 1)

    cats = {}
    for h in hits:
        cats[h["cat"]] = round(cats.get(h["cat"], 0) + h["w"], 1)

    return {
        "ai_likelihood": ai_likelihood,
        "evidence": round(evidence, 2),
        "tell_density_per_100w": round(tell_density, 2),
        "n_words": n_words,
        "n_sentences": len(sents),
        "burstiness": round(burstiness, 3),
        "emdash_per_100w": round(emdash, 2),
        "emoji_count": emoji,
        "bold_spans": bold,
        "hashtags": hashtags,
        "contraction_per_100w": round(contraction_rate, 2),
        "followability_penalty": round(followability_penalty, 2),
        "poly_ratio": round(poly_ratio, 3),
        "comma_chain_frac": round(chain_frac, 3),
        "overlong_frac": round(overlong_frac, 3),
        "categories": cats,
        "hits": hits,
    }



# ── shape channel ─────────────────────────────────────────────────────────────
# Broetry (every sentence its own paragraph) is invisible to every other
# channel: paragraph structure is flattened before scoring, so identical words
# in 26 paragraphs or 1 score the same to the decimal. Worse, broetry's
# fragment/long-sentence mix INFLATES burstiness, so the rhythm channel that
# exists to catch machine cadence is satisfied by the tell itself.
#
# This is reported as its own axis and never folded into ai_likelihood, for
# two reasons. Mechanically, anything added to `stylistic` dies at the
# corroboration clamp exactly when broetry is the only tell. Conceptually,
# broetry is a slop tell, not a machine tell: LinkedIn writers invented it
# years before GPT-3, and it demonstrably performs on the platform. Whether to
# trade reach for a human voice is the author's call, not the meter's.
STRUCT_MARK = re.compile(r"^\s*(?:[-*+•>#]|\d+[.)]|\|)")
DIALOGUE_OPEN = re.compile("^[\"“‘']")


def shape_metrics(text, genre="general"):
    """Paragraph-shape signals. Gated by genre; abstains when unreliable."""
    out = {"genre": genre, "measured": False, "solo_frac": None,
           "prose_paras": 0, "max_fragment_run": 0, "broetry": None,
           "reason": ""}
    if genre != "social":
        out["reason"] = f"not measured (genre={genre}; shape signals apply to social posts)"
        return out
    raw = [p.strip() for p in re.split(r"\n\s*\n", strip_noise(text)) if p.strip()]
    # Guards BEFORE the metric — these genres are structurally identical to
    # broetry and score harder than the real thing.
    prose = [p for p in raw
             if not STRUCT_MARK.match(p)                       # lists, headings, tables
             and not DIALOGUE_OPEN.match(p)                    # dialogue
             and len(WORD.findall(p)) >= 3]                    # stubs
    out["prose_paras"] = len(prose)
    if len(prose) < 8:                                         # mirrors length_conf
        out["reason"] = f"abstains ({len(prose)} prose paragraphs; needs 8+)"
        return out
    solo = sum(1 for p in prose if len(sentences(p)) <= 1)
    frag, run, best = [len(WORD.findall(s)) for s in sentences(strip_noise(text))], 0, 0
    for L in frag:
        run = run + 1 if L < 7 else 0
        best = max(best, run)
    out.update(measured=True, solo_frac=round(solo / len(prose), 2),
               max_fragment_run=best, reason="")
    out["broetry"] = out["solo_frac"] >= SHAPE_SOLO_THRESHOLD and best >= 3
    return out


def band(score):
    if score < 25:
        return "clean"
    if score < 50:
        return "suspect"
    if score < 75:
        return "slop-likely"
    return "slop"


def sentence_map(text, data, formal=False):
    """Every sentence with its attributed weight — the heatmap's data layer."""
    clean = strip_noise(text)
    doc = score_text(text, data, formal=formal)
    rows = []
    for s in sentences(clean):
        w, names = 0.0, []
        _sl = s.lower()   # hoisted out of the hit loop: this was
                          # recomputed once per hit, giving O(sentences x hits)
        for h in doc["hits"]:
            q = h["quote"].lower()
            if q and q in _sl:
                w += h["w"]
                names.append(h["name"])
        rows.append({"sentence": s, "weight": round(w, 1),
                     "tells": sorted(set(names))})
    return rows


# Plain-English names and fixes, keyed by pattern category. The internal
# category is a maintenance label; a writer needs to know what it is and what
# to do instead.
CAT_MEANING = {
    "linkedin":      ("LinkedIn tell", "readers pattern-match this to AI instantly"),
    "marketing":     ("marketing register", "name what it does; cut the adjectives"),
    "scaffolding":   ("structural filler", "delete the stem, keep the point"),
    "hedging":       ("empty hedge", "commit, or cut the sentence"),
    "lexicon":       ("AI vocabulary", "use the plain word"),
    "rider":         ("buzzword in marketing context", "plain word, or drop the hype around it"),
    "performed":     ("performed candor", "say the thing instead of announcing it"),
    "contrast":      ("not-X-but-Y construction", "state Y directly; one per piece maximum"),
    "puffery":       ("unearned significance", "state the fact, let the reader judge"),
    "drama":         ("manufactured drama", "the fact should carry the weight"),
    "triads":        ("rule of three", "two items, or one, or a real list"),
    "filler":        ("filler word", "cut it; the sentence survives"),
    "stakes":        ("manufactured stakes", "start where the reader needs to start"),
    "verbs":         ("weak verb", "use the direct verb"),
    "assistant":     ("assistant voice", "delete; you are not a chatbot"),
    "artifact":      ("template artifact", "fill it in or remove it"),
    "overcorrection":("over-corrected, still slop", "edgy-slop is slop in a costume"),
    "spec-notation": ("spec notation in prose", "write it as a sentence"),
    "misc":          ("machine phrasing", "rewrite plainly"),
}


def _severity(w):
    """Absolute bands, so bars mean the same thing in every document."""
    if w >= 10: return "heavy", 8
    if w >= 5:  return "moderate", 5
    if w >= 2:  return "mild", 3
    return "trace", 2


def render_heatmap(text, data, formal=False, max_rows=8, width=8):
    """A map a writer can act on: where the slop is, how bad, and what to do."""
    clean = strip_noise(text)
    doc = score_text(text, data, formal=formal)
    paras = [p for p in re.split(r"\n\s*\n", clean) if p.strip()]
    rows = []
    for pi, para in enumerate(paras, 1):
        for s in sentences(para):
            w, cats, quotes = 0.0, [], []
            _sl = s.lower()   # hoisted out of the hit loop: this was
                              # recomputed once per hit, giving O(sentences x hits)
            for h in doc["hits"]:
                q = h["quote"].lower()
                if q and q in _sl:
                    w += h["w"]
                    cats.append(h["cat"])
                    quotes.append(q)
            rows.append({"para": pi, "sent": s, "w": round(w, 1),
                         "cats": cats, "quotes": quotes})
    total = len(rows)
    dirty = [r for r in rows if r["w"] > 0]
    out = []
    if not total:
        return out
    if not dirty:
        out.append(f"  SLOP MAP · {total} sentences · none carry tells")
        out.append("  " + "·" * min(total, 40) + "   all clean")
        return out

    out.append(f"  SLOP MAP · {total} sentences · {len(dirty)} carry tells "
               f"· hottest first")
    out.append("")
    for r in sorted(dirty, key=lambda r: -r["w"])[:max_rows]:
        label, fill = _severity(r["w"])
        bar = "█" * fill + "░" * (width - fill)
        # quote the trigger, not the whole sentence — that is what to change
        trig = max(r["quotes"], key=len)[:46]
        out.append(f'  {bar}  {label:<8} ¶{r["para"]}  “{trig}”')
        seen, notes = set(), []
        for c in r["cats"]:
            if c in seen:
                continue
            seen.add(c)
            name, fix = CAT_MEANING.get(c, (c, "rewrite plainly"))
            notes.append(f"{name} — {fix}")
        for n in notes[:2]:
            out.append(f'  {" " * width}            {n}')
    if len(dirty) > max_rows:
        out.append(f'  {" " * width}            …and {len(dirty)-max_rows} more')
    out.append("")
    # document shape: one block per paragraph, so clustering is visible
    shape = []
    for pi in range(1, len(paras) + 1):
        pw = sum(r["w"] for r in rows if r["para"] == pi)
        shape.append("█" if pw >= 10 else "▓" if pw >= 5 else "▒" if pw > 0 else "·")
    out.append(f'  by paragraph  {" ".join(shape)}   █ heavy  ▓ moderate  '
               f'▒ mild  · clean')
    return out


def worst_sentences(text, data, formal=False, k=3):
    """Per-sentence heatmap, worst first.

    Attributes the *document's* hits to the sentence containing them rather
    than re-scoring each sentence alone. Scoring in isolation makes every
    sentence look like the start of a document, so start-anchored patterns
    fire on all of them — a heatmap that reports tells the document scan
    never found is worse than no heatmap.
    """
    clean = strip_noise(text)
    doc = score_text(text, data, formal=formal)
    sents = sentences(clean)
    spans, cursor = [], 0
    for s in sents:
        i = clean.find(s[:40], cursor)
        if i < 0:
            i = cursor
        spans.append((i, i + len(s), s))
        cursor = i + len(s)
    rows = []
    for start, end, s in spans:
        w, names = 0.0, []
        _sl = s.lower()   # hoisted out of the hit loop: this was
                          # recomputed once per hit, giving O(sentences x hits)
        for h in doc["hits"]:
            q = h["quote"].lower()
            if q and q in _sl:
                w += h["w"]
                names.append(h["name"])
        if w > 0:
            rows.append((w, s, names))
    return sorted(rows, key=lambda x: -x[0])[:k]


def gate_value():
    """Return (threshold, raw_token) for --gate, consuming its argument."""
    if "--gate" not in sys.argv:
        return None, None
    i = sys.argv.index("--gate")
    try:
        tok = sys.argv[i + 1]
        return float(tok), tok
    except (IndexError, ValueError):
        return 25.0, None


CHANNELS = [
    # label, how to pull the number, which direction is better, how to show it
    ("vocabulary",    lambda r: sum(h["w"] for h in r["hits"]
                                    if h["cat"] in ("lexicon", "rider")), "low"),
    ("register",      lambda r: sum(h["w"] for h in r["hits"]
                                    if h["cat"] not in ("lexicon", "rider")), "low"),
    ("rhythm",        lambda r: r["burstiness"], "high"),
    ("followability", lambda r: r["followability_penalty"], "low"),
    ("format",        lambda r: r["emdash_per_100w"] + r["emoji_count"]
                                + r["hashtags"], "low"),
]


# What counts as a fact worth preserving. Deliberately narrow: things a reader
# could check, and things whose invention is the failure the skill forbids.
FACT_RX = [
    ("figure",  r"(?<![\w.])\$?\d[\d,]*(?:\.\d+)?\s*(?:%|percent|x|bn|m|k|million|billion)?(?![\w])"),
    ("name",    r"\b(?:[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]+)*)\b"),
    ("quote",   r"[\u201c\"]([^\u201d\"]{6,120})[\u201d\"]"),
    ("url",     r"https?://\S+"),
]
# Sentence-initial capitals are not names. Neither are these.
NOT_NAMES = set("""The This That These Those We They It He She You I A An And But Or
So Then Now Here There When While If After Before Our Their His Her Its My Your
Most Many Some Every Each Both All No Not One Two Three Four Five Six Seven
Eight Nine Ten First Second Third Last Next Why How What Which Who Where
See Read Use Run Add Set Get Let Note Also Just Only Even Still Yet Once
More Less Best Worst Same Other Another Such Very Much Well Then Than
Shipped Built Made Added Fixed Moved Cut Kept Found Gave Took Went Came
Said Did Had Was Were Been Being Done Going Getting Started Stopped
Because Since Though Although Unless Until Whether Given Once Yet""".split())

# Spelled-out numbers, mapped to digits. A rewrite that turns "18 months" into
# "Eighteen months" is faithful, but the raw extractor read "18" as a dropped
# figure and "Eighteen" as an invented name — two false alarms from one honest
# edit. Normalising both texts to digits before extracting cancels that, and
# because the same transform runs on the original and the rewrite, it can never
# manufacture a mismatch that was not already there.
NUM_WORDS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
    "eleven": "11", "twelve": "12", "thirteen": "13", "fourteen": "14",
    "fifteen": "15", "sixteen": "16", "seventeen": "17", "eighteen": "18",
    "nineteen": "19", "twenty": "20", "thirty": "30", "forty": "40",
    "fifty": "50", "sixty": "60", "seventy": "70", "eighty": "80",
    "ninety": "90", "hundred": "100", "thousand": "1000",
    "million": "1000000", "billion": "1000000000",
}
# Only normalise numbers of eleven or more. "one".."ten" double as articles and
# pronouns ("one of them", "two ways"), so digitising them invents figures that
# were never quantities; from eleven up, a spelled number is almost always a real
# count ("eighteen months", "forty percent", "a hundred users").
_NUM_RX = re.compile(
    r"\b(" + "|".join(w for w, d in NUM_WORDS.items() if int(d) >= 11) + r")\b", re.I)


def _spell_to_digits(text):
    return _NUM_RX.sub(lambda m: NUM_WORDS[m.group(0).lower()], text)


# Common English words that legitimately start sentences and so get capitalised,
# but are not names — "Draw the diagram", "Usually it works", "Start here". The
# entity regex cannot tell these from "Priya" or "Acme" (which are never ordinary
# words), so an explicit frequency list carries the difference. This is a
# precision aid only: a word here is skipped as a name in BOTH texts, so it can
# widen a miss but never invent a false fabrication flag.
COMMON_WORDS = set("""
about above across again against along already also although always among another
any anyone around away back become been before behind below better between beyond
build building built call called celebrate change changed come coming could deploy
deployment deployments double doing down draw during each either enough every
everyone everything except finally find found from give given going gone great grow
growing hard help here however instead into keep kept later least leave less look
looking made make making many maybe might migrate more most move moving much must
never next nobody nothing often once only other over people perhaps ready really
right run running same say saying send sent set ship shipping should show shown
since some someone something soon start started still stop such take taken talk
tell than that their them then there these they thing things think this those
though through today together too took toward tried true trying turn under until
upon usually using very want was way well went were what when where which while
whole will with within without work working would writing agree agreeing
monday tuesday wednesday thursday friday saturday sunday none plenty seats reps
fix sit mid ambiguity team teams user users product feature features day days week
weeks month months year years time thing done anyway besides meanwhile therefore
worse worst harder easier simpler faster slower bigger smaller lots plus minus
""".split())


def facts(text, _other=""):
    """Checkable claims in a draft: figures, named entities, quotes, links."""
    # URLs contain lowercase forms of the names they point at ("acme.io" made
    # "Acme" look like a sentence opener in the source and an invention in the
    # rewrite), so entity detection runs on the text with links removed.
    urls = text  # links keep their spelled forms; numbers in a slug are not facts
    prose = _spell_to_digits(re.sub(r"https?://\S+", " ", text))
    other = _spell_to_digits(_other)
    out = {}
    for kind, rx in FACT_RX:
        found = set()
        for m in re.finditer(rx, urls if kind == "url" else prose):
            v = (m.group(1) if m.lastindex else m.group(0)).strip()
            if kind == "name":
                if v in NOT_NAMES or len(v) < 3:
                    continue
                low = v.lower()
                # A capitalised common word ("Draw", "Usually", "Start"), an
                # adverb ("Finally"), or a sentence-opening gerund ("Watching",
                # "Calling") is not an entity; a real name never is.
                if " " not in v and (low in COMMON_WORDS
                                     or low.endswith("ly") or low.endswith("ing")):
                    continue
                # A word is only a name if it is never used as an ordinary
                # lowercase word — not here, and not in the text we compare
                # against. "Under"/"Shipped" appear lowercased somewhere in
                # normal prose; "Priya"/"Acme" do not. Multi-word entities keep
                # their head token for this test.
                head = v.split()[0]
                # Is this token ever used as an ordinary lowercase word, here or
                # in the compared text? Sentence openers are ("under load",
                # "shipped tuesday"); real names never are. Strip the capitalized
                # forms first so the entity cannot vouch for itself.
                blob = re.sub(r"\b" + re.escape(head) + r"\b", " ", prose + " " + other)
                if re.search(r"\b" + re.escape(head.lower()) + r"\b", blob):
                    continue
            if kind == "figure":
                v = v.replace(",", "").lstrip("$").rstrip()
                v = re.sub(r"\s*percent$", "%", v)
                v = re.sub(r"\s*(million|bn|billion|m|k)$",
                           lambda x: {"million":"m","billion":"bn"}.get(x.group(1), x.group(1)), v)
            if kind == "url":
                # a link at the end of a sentence carries the full stop
                v = v.rstrip(".,;:)]}\u201d\"'")
            if v:
                found.add(v)
        out[kind] = found
    return out


# Interior states the author has to have supplied. The benchmark's one
# fabrication was exactly this shape — "by test day the real thing felt
# familiar" — and an entity check cannot see it, because no name or figure moved.
# First-person emotional state and the body-as-feeling idiom. Kept deliberately
# tight: "I felt/was <emotion>", "my heart/stomach ...", not every clause with
# a feeling verb, because the goal is catching an INVENTED inner state, and the
# comparison below cancels any that were already in the source.
INTERIOR_RX = re.compile(
    r"\b(?:I|we)\s+(?:was|were|am|felt|feel|got)\s+\w+"
    r"|\b(?:I|we)\s+(?:remember|realrandom|realise|realize|knew|feared|hoped|"
    r"worried|panicked|struggled|doubted)\w*"
    r"|\b(?:my|our)\s+(?:heart|stomach|gut|chest|hands|mind)\b"
    r"|\bit\s+felt\s+(?:surreal|unreal|impossible|inevitable|like\b)"
    r"|\bfelt\s+(?:familiar|natural|surreal|foreign|inevitable|effortless)\b", re.I)


def interior_claims(text):
    """Inner-state assertions, reduced to a comparable core so paraphrase of an
    existing one does not read as a new invention."""
    out = set()
    for m in INTERIOR_RX.finditer(text):
        # keep the emotion/state word, drop the pronoun and tense
        words = re.findall(r"[a-z]+", m.group(0).lower())
        out.add(words[-1] if words else m.group(0).lower())
    return out


def fidelity(before, after):
    """Did the rewrite keep every fact, and did it add any?

    The benchmark's worst result was a rewrite that invented a feeling the
    author never described — the exact thing hard rule 1 forbids — and nothing
    in the gate measured it. Preservation is checkable; invention is the half
    that matters, because a dropped figure is visible to the author and an
    added one is not.
    """
    a, b = facts(before, after), facts(after, before)
    rows, kept_all, invented_any = [], True, False
    # Names compare by shared token, so "Shipped Tuesday" and "Tuesday" cancel
    # (both contain the token) while a genuinely new name shares nothing.
    def toks(s): return {w for e in s for w in re.findall(r"[a-z]+", e.lower())}
    a_nt, b_nt = toks(a["name"]), toks(b["name"])
    # Interior experience is the fabrication the judges actually caught, and the
    # one no entity check sees: nothing was renamed, a feeling was added.
    ia, ib = interior_claims(before), interior_claims(after)
    new_interior = ib - ia
    for kind, _ in FACT_RX:
        if kind == "name":
            dropped = {e for e in a[kind]
                       if not (toks({e}) & b_nt)}
            added = {e for e in b[kind] if not (toks({e}) & a_nt)}
            kept = a[kind] - dropped
        else:
            kept = a[kind] & b[kind]
            dropped = a[kind] - b[kind]
            added = b[kind] - a[kind]
        if not (a[kind] or b[kind]):
            continue
        rows.append((kind, kept, dropped, added))
        if dropped:
            kept_all = False
        if added:
            invented_any = True
    if new_interior:
        rows.append(("feeling", set(), set(), new_interior))
        invented_any = True
    return {"rows": rows, "preserved": kept_all, "invented": invented_any,
            "interior": new_interior}


# The shared rewrite-quality objective. One definition of "a better rewrite",
# used in two places: scripts/rerank.py picks the best of N candidates by it, and
# bench/skillopt/reward.py tunes SKILL.md against it — so selecting a draft and
# improving the instructions optimise the same thing. Fidelity is reported
# alongside, never folded in, so a candidate can never win by dropping or
# inventing a fact however clean it reads.
RW_GATE = {"email": 35, "research": 40, "professional": 40}
RW_GATE_DEFAULT = 25
RW_FORMAL = {"research", "professional"}
RW_WEIGHTS = {"deslop": 0.45, "gate": 0.25, "rhythm": 0.15, "length": 0.15}


def rewrite_score(before_text, after_text, genre=None, data=None):
    """Score one rewrite: a soft quality in [0,1] plus its fidelity flags."""
    if data is None:
        data = load_patterns()
    formal = genre in RW_FORMAL
    b = score_text(before_text, data, formal=formal)
    a = score_text(after_text, data, formal=formal)
    b_ai = b["ai_likelihood"] or 1e-9
    clamp = lambda x: max(0.0, min(1.0, x))
    deslop = clamp((b_ai - a["ai_likelihood"]) / b_ai)
    gate = 1.0 if a["ai_likelihood"] <= RW_GATE.get(genre, RW_GATE_DEFAULT) else 0.0
    rhythm = clamp(a.get("burstiness", 0.0) / 0.45)
    bw, aw = len(before_text.split()), len(after_text.split())
    length = 1.0 if not bw or aw / bw >= 0.6 else clamp((aw / bw) / 0.6)
    soft = sum(RW_WEIGHTS[k] * v for k, v in
               {"deslop": deslop, "gate": gate, "rhythm": rhythm, "length": length}.items())
    fid = fidelity(before_text, after_text)
    return {"soft": round(soft, 4), "deslop": round(deslop, 3), "gate": gate,
            "rhythm": round(rhythm, 3), "length": round(length, 3),
            "after_ai": a["ai_likelihood"], "before_ai": b["ai_likelihood"],
            "burstiness": round(a.get("burstiness", 0.0), 3),
            "high_tells": sum(1 for h in a.get("hits", []) if h.get("w", 0) >= 4),
            "preserved": fid["preserved"], "invented": fid["invented"]}


def render_fidelity(before, after):
    r = fidelity(before, after)
    out = ["", "  FIDELITY · facts in the draft vs the rewrite", ""]
    for kind, kept, dropped, added in r["rows"]:
        out.append(f"  {kind:<8} {len(kept)} kept"
                   + (f" · {len(dropped)} DROPPED" if dropped else "")
                   + (f" · {len(added)} ADDED" if added else ""))
        for v in sorted(dropped)[:4]:
            out.append(f"           dropped  {v[:56]!r}")
        for v in sorted(added)[:4]:
            out.append(f"           ADDED    {v[:56]!r}   <-- not in the source")
    if not r["rows"]:
        out.append("  no checkable facts in either text")
    if r.get("interior"):
        out.append("  the author never said these; an added feeling is still a "
                   "fabrication")
    out += ["",
            "  verdict: " + ("facts preserved, nothing invented"
                             if r["preserved"] and not r["invented"] else
                             ("FACTS DROPPED" if not r["preserved"] else "")
                             + (" · CONTENT INVENTED" if r["invented"] else "")),
            "  note   : checks figures, names, quotes, links and asserted",
            "           feelings. It cannot see a reframed claim or a shifted",
            "           emphasis, so the judgment pass still applies.", ""]
    return out


def dna(before, after, data, formal=False, width=22):
    """Side-by-side channel anatomy of a draft and its rewrite.

    The composite says a draft got better; it never says what *kind* of better.
    A writer who sees that the whole score was vocabulary learns to stop
    reaching for those words, which outlasts the edit. Bars are scaled per
    channel against the worse of the two texts, so each row reads as its own
    before-and-after rather than against an arbitrary ceiling.
    """
    a, b = score_text(before, data, formal), score_text(after, data, formal)
    out = ["", "  DNA · before → after", ""]
    for label, get, better in CHANNELS:
        x, y = get(a), get(b)
        top = max(x, y) or 1.0
        fx, fy = x / top, y / top
        bar = "".join("█" if i < round(fx * width) else
                      ("▁" if i < round(max(fx, fy) * width) else " ")
                      for i in range(width))
        gone = (x - y) if better == "low" else (y - x)
        mark = "improved" if gone > 1e-9 else ("unchanged" if abs(gone) < 1e-9 else "WORSE")
        fmt = (lambda v: f"{v:.2f}") if max(x, y) < 10 else (lambda v: f"{v:g}")
        out.append(f"  {label:<14}{bar}  {fmt(x):>6} → {fmt(y):<6} {mark}")
    out += ["",
            f"  composite     {a['ai_likelihood']:.1f} → {b['ai_likelihood']:.1f}"
            f"   ({band(a['ai_likelihood'])} → {band(b['ai_likelihood'])})",
            f"  length        {a['n_words']} → {b['n_words']} words "
            f"({(b['n_words']-a['n_words'])/max(a['n_words'],1)*100:+.0f}%)",
            f"  tells         {len(a['hits'])} → {len(b['hits'])}"]
    kept = {h["name"] for h in b["hits"]}
    fixed = [h["name"] for h in a["hits"] if h["name"] not in kept]
    if fixed:
        out.append("  fixed         " + ", ".join(sorted(set(fixed))[:6]))
    if kept:
        out.append("  still present " + ", ".join(sorted(kept)[:6]))
    # A shorter text with the same tells is not a better text.
    if b["n_words"] < a["n_words"] * 0.75 and len(b["hits"]) >= len(a["hits"]):
        out.append("  note          got shorter without removing tells — "
                   "check this is an edit, not a deletion")
    return out + [""]


def main():
    gv, gv_tok = gate_value()
    gen_tok = sys.argv[sys.argv.index("--genre") + 1] if "--genre" in sys.argv and len(sys.argv) > sys.argv.index("--genre") + 1 else None
    # Values that belong to a flag (--gate 25, --genre social, --voice manav)
    # are not positional file arguments. Drop each flag and the token after it.
    VALUE_FLAGS = {"--gate", "--genre", "--voice"}
    args, skip = [], False
    for i, a in enumerate(sys.argv[1:]):
        if skip:
            skip = False
            continue
        if a in VALUE_FLAGS:
            skip = True
            continue
        if not a.startswith("--"):
            args.append(a)
    as_json = "--json" in sys.argv
    explain = "--explain" in sys.argv
    formal = "--formal" in sys.argv
    genre = "general"
    if "--genre" in sys.argv:
        try: genre = sys.argv[sys.argv.index("--genre") + 1]
        except IndexError: pass
    if formal: genre = "formal"
    voice = None
    if "--voice" in sys.argv:
        try: voice = sys.argv[sys.argv.index("--voice") + 1]
        except IndexError: pass
    data = load_patterns(voice=voice)

    if "--fidelity" in sys.argv:
        if len(args) < 2:
            sys.exit("--fidelity needs two files: before and after")
        before, after = Path(args[0]).read_text(), Path(args[1]).read_text()
        for line in render_fidelity(before, after):
            print(line)
        r = fidelity(before, after)
        sys.exit(0 if (r["preserved"] and not r["invented"]) else 1)

    if "--dna" in sys.argv:
        if len(args) < 2:
            sys.exit("--dna needs two files: before and after")
        for line in dna(Path(args[0]).read_text(), Path(args[1]).read_text(),
                        data, formal=formal):
            print(line)
        return

    if "--batch" in sys.argv:
        root = Path(args[0]) if args else Path(".")
        files = sorted(p for p in root.rglob("*") if p.suffix in
                       (".md", ".txt", ".markdown") and p.is_file())
        rows = []
        for p in files:
            try:
                r = score_text(p.read_text(), data, formal=formal)
                rows.append((r["ai_likelihood"], p, band(r["ai_likelihood"])))
            except Exception as e:
                rows.append((float("nan"), p, f"error: {e}"))
        rows.sort(key=lambda x: -(x[0] if x[0] == x[0] else -1))
        for sc, p, b in rows:
            print(f"{sc:6.1f}  {b:12s} {p}")
        worst = max((sc for sc, _, _ in rows if sc == sc), default=0)
        sys.exit(1 if gv is not None and worst > gv else 0)

    text = Path(args[0]).read_text() if args else sys.stdin.read()
    r = score_text(text, data, formal=formal)
    if as_json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        if gv is None:
            return
        # --json --gate is documented CI usage; returning here exited 0 on a
        # failing document, so a broken gate silently passed every build.
        sh_j = shape_metrics(text, genre=genre)
        sys.exit(0 if (r["ai_likelihood"] <= gv and not sh_j.get("broetry")) else 1)
    print(f"AI-likelihood: {r['ai_likelihood']}/100  [{band(r['ai_likelihood'])}]")
    print(f"  tell density : {r['tell_density_per_100w']:.2f} weighted hits /100w "
          f"({r['n_words']} words)")
    print(f"  burstiness   : {r['burstiness']:.3f}  (human prose usually > 0.45)")
    print(f"  em-dash /100w: {r['emdash_per_100w']:.2f}   emoji: {r['emoji_count']}  "
          f"bold: {r['bold_spans']}  hashtags: {r['hashtags']}")
    if r["followability_penalty"] > 2:
        print(f"  followability : penalty {r['followability_penalty']} — "
              f"comma-chains {r['comma_chain_frac']:.0%} of sentences, "
              f"long-word ratio {r['poly_ratio']:.0%}, "
              f"overlong {r['overlong_frac']:.0%} (dense ≠ expert; unpack)")
    if r["categories"]:
        top = sorted(r["categories"].items(), key=lambda kv: -kv[1])[:8]
        print("  top categories: " + ", ".join(f"{k}({v})" for k, v in top))
    sh = shape_metrics(text, genre=genre)
    r["shape"] = sh
    print("  shape         : " + (
        f"broetry — {sh['solo_frac']:.0%} of paragraphs are single sentences, "
        f"longest fragment run {sh['max_fragment_run']}" if sh.get("broetry")
        else (f"ok ({sh['solo_frac']:.0%} solo paragraphs)" if sh["measured"]
              else sh["reason"])))
    print("  checked       : vocabulary, formatting, rhythm, followability, register"
          + (", shape" if sh["measured"] else "")
          + "\n  not measured  : substance (is there a claim?), voice, factual accuracy"
          + ("" if sh["measured"] else ", shape"))
    if explain:
        if r["hits"]:
            print(f"\n  charged spans ({len(r['hits'])}), heaviest first:")
            for h in sorted(r["hits"], key=lambda h: -h["w"]):
                print(f"    {h['w']:>4}  {h['cat']:<14} {h['name']:<22} {h['quote']!r}")
            print(f"    {'':>4}  {'':14} {'':22} "
                  f"= {sum(h['w'] for h in r['hits']):g} weighted, "
                  f"{r['tell_density_per_100w']:.2f} per 100 words")
        else:
            print("\n  charged spans: none — the score is rhythm and format only")
    if "--heatmap" in sys.argv or explain:
        for line in render_heatmap(text, data, formal=formal):
            print(line)
    if gv is not None:
        ok = r["ai_likelihood"] <= gv and not sh.get("broetry")
        why = "" if ok else (" (shape: broetry)" if sh.get("broetry") and r["ai_likelihood"] <= gv else "")
        verdict = "PASS" if ok else "FAIL"
        print(f"  gate {gv:g}: {verdict}{why} — measured channels only; "
              f"substance and voice still need the judgment pass")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
