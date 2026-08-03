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
    python3 slopscore.py --explain <file>  # report + every hit quoted
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
    text = re.sub(r"`[^`]*`", " ", text)
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

    # 2. Lexicon (over-represented LLM vocabulary, weighted per occurrence)
    lex_hits = 0.0
    lower = text.lower()
    for term, w in data["lexicon"].items():
        for m in re.finditer(r"\b" + re.escape(term) + r"\w*", lower):
            hits.append({"cat": "lexicon", "name": term, "w": w, "quote": m.group(0)})
            lex_hits += w

    pattern_weight = sum(h["w"] for h in hits)
    tell_density = 100.0 * pattern_weight / n_words  # weighted tells per 100 words

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
    emdash_penalty = max(0.0, emdash - 0.6) * 6
    emoji = len(re.findall(r"[\U0001F300-\U0001FAFF✅✨⚡\U0001F449\U0001F447\U0001F680\U0001F525]", raw))
    emoji_penalty = min(emoji * 2.0, 12)
    bold = len(re.findall(r"\*\*[^*\n]{2,60}\*\*", raw))
    bold_penalty = min(max(0, bold - 1) * 1.5, 9)
    hashtags = len(re.findall(r"(?<!\S)#\w+", raw))
    hashtag_penalty = min(hashtags * 1.2, 8)

    # 5. Register: contraction scarcity in casual genres reads machine-formal.
    contractions = len(re.findall(r"\b\w+[’'](?:t|s|re|ve|ll|d|m)\b", text))
    contraction_rate = 100.0 * contractions / n_words
    formality_penalty = 0.0 if formal else (
        3.0 if contraction_rate < 0.4 and n_words > 80 else 0.0)

    # Composite: logistic squash of the summed evidence.
    evidence = (
        tell_density * 1.15
        + uniformity_penalty
        + emdash_penalty
        + emoji_penalty
        + bold_penalty
        + hashtag_penalty
        + formality_penalty
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
        "categories": cats,
        "hits": hits,
    }


def predict_channel(text):
    """Optional trained channel (--predict): p(post-training register).

    Reported SEPARATELY, never blended into the composite: the shipped model
    is trained on HC3 (ChatGPT-3.5-era QA text) and measured era-fragile —
    it scores 2026-era marketing/social slop as human. Trust it in-domain or
    after retraining on your own corpus (scripts/train_model.py); otherwise
    treat the pattern meter as primary. Abstains below 60 words and inside
    its calibrated uncertainty band.
    """
    mpath = DATA_DIR / "model.json"
    if not mpath.exists():
        return {"status": "no-model"}
    try:
        import train_model as T
        m = json.loads(mpath.read_text())
        f = T.scalar_features(text)
        f.update(T.logodds_features(text, m["tables"]))
        if len(WORD.findall(text)) < m["meta"].get("min_tokens", 60):
            return {"status": "abstain-short"}
        z = [(f[k] - mu) / s for k, mu, s in zip(m["names"], m["means"], m["stds"])]
        raw = m["b"] + sum(w * x for w, x in zip(m["w"], z))
        p = 1 / (1 + math.exp(-(m["platt_a"] * raw + m["platt_b"])))
        lo, hi = m["meta"].get("abstain", [0.35, 0.65])
        return {"status": "abstain-uncertain" if lo < p < hi else "ok",
                "p_ai_register": round(p, 3),
                "trained_on": "HC3 (ChatGPT-3.5 era) — era-fragile; retrain for current models"}
    except Exception as e:
        return {"status": f"error: {e}"}


def band(score):
    if score < 25:
        return "clean"
    if score < 50:
        return "suspect"
    if score < 75:
        return "slop-likely"
    return "slop"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    as_json = "--json" in sys.argv
    explain = "--explain" in sys.argv
    formal = "--formal" in sys.argv
    text = Path(args[0]).read_text() if args else sys.stdin.read()
    data = load_patterns()
    r = score_text(text, data, formal=formal)
    if "--predict" in sys.argv:
        r["predictive_channel"] = predict_channel(text)
    if as_json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return
    print(f"AI-likelihood: {r['ai_likelihood']}/100  [{band(r['ai_likelihood'])}]")
    print(f"  tell density : {r['tell_density_per_100w']:.2f} weighted hits /100w "
          f"({r['n_words']} words)")
    print(f"  burstiness   : {r['burstiness']:.3f}  (human prose usually > 0.45)")
    print(f"  em-dash /100w: {r['emdash_per_100w']:.2f}   emoji: {r['emoji_count']}  "
          f"bold: {r['bold_spans']}  hashtags: {r['hashtags']}")
    if r["categories"]:
        top = sorted(r["categories"].items(), key=lambda kv: -kv[1])[:8]
        print("  top categories: " + ", ".join(f"{k}({v})" for k, v in top))
    if "predictive_channel" in r:
        pc = r["predictive_channel"]
        if pc.get("status") == "ok":
            print(f"  predictive    : p(ai-register)={pc['p_ai_register']}  "
                  f"[separate channel — {pc['trained_on']}]")
        else:
            print(f"  predictive    : {pc['status']}")
    if explain:
        for h in sorted(r["hits"], key=lambda h: -h["w"]):
            print(f"   [{h['w']:>4}] {h['cat']}/{h['name']}: “{h['quote']}”")


if __name__ == "__main__":
    main()
