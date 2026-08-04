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


def load_patterns():
    base = json.loads((DATA_DIR / "patterns.json").read_text())
    learned_path = DATA_DIR / "learned.json"
    if learned_path.exists():
        try:
            learned = json.loads(learned_path.read_text())
            base["patterns"].extend(learned.get("patterns", []))
            base["lexicon"].update(learned.get("lexicon", {}))
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
        for h in doc["hits"]:
            q = h["quote"]
            if q and q.lower() in s.lower():
                w += h["w"]
                names.append(h["name"])
        rows.append({"sentence": s, "weight": round(w, 1),
                     "tells": sorted(set(names))})
    return rows


def render_heatmap(text, data, formal=False, width=34, max_rows=14):
    """Draw the heatmap: one bar per sentence, hottest first, tells named.

    Severity bands mirror the score bands so the picture and the number agree:
    a sentence carrying weight >= 8 is the same red the composite would be.
    """
    rows = sentence_map(text, data, formal=formal)
    if not rows:
        return []
    hot = max((r["weight"] for r in rows), default=0)
    out = ["  heatmap  (each bar = one sentence, hottest first)"]
    if hot == 0:
        n = len(rows)
        out.append(f"    {'·' * min(n, width)}  {n} sentences, no tells found")
        return out
    ranked = sorted(enumerate(rows, 1), key=lambda kv: -kv[1]["weight"])
    shown = [r for r in ranked if r[1]["weight"] > 0][:max_rows]
    for idx, r in shown:
        filled = max(1, round(width * r["weight"] / hot))
        glyph = "█" if r["weight"] >= 8 else ("▇" if r["weight"] >= 4 else "▄")
        bar = glyph * filled + "·" * (width - filled)
        snippet = re.sub(r"\s+", " ", r["sentence"])[:52]
        out.append(f"    s{idx:<3} {bar} {r['weight']:5.1f}  {snippet}")
        out.append(f"         {' ' * width}         ← {', '.join(r['tells'][:4])}")
    quiet = sum(1 for r in rows if r["weight"] == 0)
    if quiet:
        out.append(f"    {quiet} of {len(rows)} sentences carry no tells")
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
        for h in doc["hits"]:
            q = h["quote"]
            if q and q.lower() in s.lower():
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


def main():
    gv, gv_tok = gate_value()
    args = [a for a in sys.argv[1:]
            if not a.startswith("--") and a != gv_tok]
    as_json = "--json" in sys.argv
    explain = "--explain" in sys.argv
    formal = "--formal" in sys.argv
    data = load_patterns()

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
        return
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
    if "--heatmap" in sys.argv and not explain:
        for line in render_heatmap(text, data, formal=formal):
            print(line)
    if gv is not None:
        ok = r["ai_likelihood"] <= gv
        print(f"  gate {gv:g}: {'PASS' if ok else 'FAIL'}")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
