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


def load_patterns():
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
    return base


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
        for m in re.finditer(r"\b" + re.escape(term) + r"\w*", lower):
            hits.append({"cat": "lexicon", "name": term, "w": w, "quote": m.group(0)})
    riders, triggers = data.get("riders", {}), data.get("rider_triggers", [])
    if riders:
        for sent in sents:
            sl = sent.lower()
            if not any(t in sl for t in triggers):
                continue
            for term, w in riders.items():
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
    corroboration = min(1.0, 0.45 + tell_density / 3.0)
    stylistic = ((emdash_penalty + formality_penalty) * corroboration
                 + uniformity_penalty + followability_penalty)
    # No lexical evidence at all means no cluster, and the rule is that
    # clusters convict. Style alone (dashes, long sentences, formal register,
    # even rhythm) describes plenty of excellent human prose — 19th-century
    # oratory, dense technical writing — so with zero tells and zero emoji or
    # hashtag spam, style can raise suspicion but must never convict.
    if not hits and emoji == 0 and hashtags == 0:
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
    args = [a for a in sys.argv[1:]
            if not a.startswith("--") and a != gv_tok and a != gen_tok]
    as_json = "--json" in sys.argv
    explain = "--explain" in sys.argv
    formal = "--formal" in sys.argv
    genre = "general"
    if "--genre" in sys.argv:
        try: genre = sys.argv[sys.argv.index("--genre") + 1]
        except IndexError: pass
    if formal: genre = "formal"
    data = load_patterns()

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
