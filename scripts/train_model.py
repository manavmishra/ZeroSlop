#!/usr/bin/env python3
"""Train zero-slop's predictive channel — pure stdlib, no dependencies.

Trains an L2-regularized logistic regression (the MaxEnt family) over three
evidence-backed feature groups:
  1. stylometric scalars (burstiness, function-word profile, punctuation,
     lexical diversity, contraction rate);
  2. a Graham-style Bayesian log-odds word lexicon (learned, not hand-picked);
  3. char 4-gram log-odds (register texture that survives word swaps).
Calibrates with Platt scaling on a held-out split. Emits data/model.json,
which slopscore.py picks up automatically as an optional channel.

Why not SVM/HMM/deep nets: head-to-heads show ≤1pt vs LR for text (no
dependency justified); HMMs add nothing over burstiness scalars; the deep
net in the loop is the LLM running the skill. See references/evidence.md.

Usage:
    python3 train_model.py corpus.jsonl [--out ../data/model.json]
corpus.jsonl lines: {"label": "human"|"ai", "text": "..."}

Retrain per model generation (6-12 months): detector signal decays as the
post-training register shifts. Ship weights, keep the trainer.
"""
import json
import math
import random
import re
import sys
from collections import Counter
from pathlib import Path

WORD = re.compile(r"[a-z’']+")
SENT = re.compile(r"(?<=[.!?])[\")”’]?\s+(?=[A-Z“\"(0-9])")
FUNCTION_WORDS = [
    "the", "of", "and", "to", "a", "in", "that", "it", "is", "was", "i",
    "you", "for", "with", "but", "so", "not", "this", "as", "are", "we",
    "on", "be", "have", "or", "at", "which", "however", "while", "these",
]


def sentences(text):
    out = []
    for para in re.split(r"\n\s*\n", text):
        for s in SENT.split(para.replace("\n", " ").strip()):
            if len(s.split()) >= 2:
                out.append(s)
    return out


def scalar_features(text):
    low = text.lower()
    words = WORD.findall(low)
    n = max(len(words), 1)
    sents = sentences(text)
    slens = [len(s.split()) for s in sents] or [1]
    mean_sl = sum(slens) / len(slens)
    var_sl = (sum((x - mean_sl) ** 2 for x in slens) / max(len(slens) - 1, 1))
    burst = math.sqrt(var_sl) / mean_sl if mean_sl else 0
    counts = Counter(words)
    feats = {
        "burstiness": burst,
        "mean_sent_len": mean_sl / 30.0,
        "ttr": len(counts) / n,
        "contraction": sum(v for w, v in counts.items() if "’" in w or "'" in w) / n,
        "comma": text.count(",") / n,
        "semicolon": text.count(";") / n,
        "emdash": (text.count("—") + text.count("--")) / n,
        "question": text.count("?") / n,
        "exclaim": text.count("!") / n,
        "colon": text.count(":") / n,
        "paren": text.count("(") / n,
        "avg_word_len": sum(map(len, words)) / n / 8.0,
        "first_person": (counts["i"] + counts["we"] + counts["my"] + counts["our"]) / n,
        "second_person": (counts["you"] + counts["your"]) / n,
    }
    for fw in FUNCTION_WORDS:
        feats["fw_" + fw] = counts[fw] / n
    return feats


def logodds_tables(docs, labels, min_count=8):
    """Laplace-smoothed log-odds for words and char 4-grams."""
    wc = {"human": Counter(), "ai": Counter()}
    cc = {"human": Counter(), "ai": Counter()}
    for text, lab in zip(docs, labels):
        low = text.lower()
        wc[lab].update(WORD.findall(low))
        squashed = re.sub(r"\s+", " ", low)
        cc[lab].update(squashed[i:i + 4] for i in range(len(squashed) - 3))
    tables = {}
    for name, tab in [("word", wc), ("char", cc)]:
        th, ta = sum(tab["human"].values()), sum(tab["ai"].values())
        vocab = {t for t in (tab["human"] | tab["ai"])
                 if tab["human"][t] + tab["ai"][t] >= min_count}
        lo = {}
        for t in vocab:
            ph = (tab["human"][t] + 1) / (th + len(vocab))
            pa = (tab["ai"][t] + 1) / (ta + len(vocab))
            v = math.log(pa / ph)
            if abs(v) >= 0.25:          # keep only informative entries
                lo[t] = round(v, 4)
        tables[name] = lo
    return tables


def logodds_features(text, tables):
    low = text.lower()
    feats = {}
    for name, tokens in [("word", WORD.findall(low)),
                         ("char", [re.sub(r"\s+", " ", low)[i:i + 4]
                                   for i in range(len(re.sub(r"\s+", " ", low)) - 3)])]:
        lo = tables[name]
        vals = [lo[t] for t in tokens if t in lo]
        if not vals:
            feats[name + "_mean"] = 0.0
            feats[name + "_topk"] = 0.0
            continue
        feats[name + "_mean"] = sum(vals) / len(vals)
        k = min(15, len(vals))
        feats[name + "_topk"] = sum(sorted(vals, key=abs, reverse=True)[:k]) / k
    return feats


def featurize(text, tables):
    f = scalar_features(text)
    f.update(logodds_features(text, tables))
    return f


def train_lr(X, y, names, l2=1e-3, lr=0.5, epochs=400):
    w = [0.0] * len(names)
    b = 0.0
    n = len(X)
    for _ in range(epochs):
        gw = [0.0] * len(names)
        gb = 0.0
        for xi, yi in zip(X, y):
            z = b + sum(wj * xj for wj, xj in zip(w, xi))
            p = 1 / (1 + math.exp(-max(min(z, 30), -30)))
            d = p - yi
            for j, xj in enumerate(xi):
                gw[j] += d * xj
            gb += d
        w = [wj - lr * (gj / n + l2 * wj) for wj, gj in zip(w, gw)]
        b -= lr * gb / n
    return w, b


def platt(scores, y):
    a, bb = 1.0, 0.0
    for _ in range(300):
        ga = gb = 0.0
        for s, yi in zip(scores, y):
            p = 1 / (1 + math.exp(-max(min(a * s + bb, 30), -30)))
            ga += (p - yi) * s
            gb += (p - yi)
        a -= 0.1 * ga / len(scores)
        bb -= 0.1 * gb / len(scores)
    return a, bb


def auc(scores, y):
    pairs = sorted(zip(scores, y))
    pos = sum(y)
    neg = len(y) - pos
    if not pos or not neg:
        return float("nan")
    rank_sum = 0
    for rank, (_, yi) in enumerate(pairs, 1):
        if yi:
            rank_sum += rank
    return (rank_sum - pos * (pos + 1) / 2) / (pos * neg)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv \
        else Path(__file__).resolve().parent.parent / "data" / "model.json"
    rows = [json.loads(l) for l in open(args[0]) if l.strip()]
    random.Random(7).shuffle(rows)
    docs = [r["text"] for r in rows]
    labels = [r["label"] for r in rows]
    y = [1 if l == "ai" else 0 for l in labels]

    n = len(rows)
    i1, i2 = int(n * .7), int(n * .85)
    tables = logodds_tables(docs[:i1], labels[:i1])

    feats = [featurize(t, tables) for t in docs]
    names = sorted(feats[0])
    mat = [[f[k] for k in names] for f in feats]
    means = [sum(col) / n for col in zip(*mat)]
    stds = [max(math.sqrt(sum((v - m) ** 2 for v in col) / n), 1e-9)
            for col, m in zip(zip(*mat), means)]
    Z = [[(v - m) / s for v, m, s in zip(row, means, stds)] for row in mat]

    w, b = train_lr(Z[:i1], y[:i1], names)
    raw = [bi + sum(wj * xj for wj, xj in zip(w, z)) for z, bi in
           ((zz, b) for zz in Z)]
    a, pb = platt(raw[i1:i2], y[i1:i2])

    test_p = [1 / (1 + math.exp(-(a * s + pb))) for s in raw[i2:]]
    test_y = y[i2:]
    acc = sum((p > .5) == bool(yi) for p, yi in zip(test_p, test_y)) / len(test_y)
    print(f"n={n} features={len(names)} lexicon={len(tables['word'])}w/"
          f"{len(tables['char'])}c")
    print(f"held-out test: AUC={auc(test_p, test_y):.4f} acc={acc:.4f}")

    model = {"names": names, "means": means, "stds": stds, "w": w, "b": b,
             "platt_a": a, "platt_b": pb, "tables": tables,
             "meta": {"n_train": i1, "trained": "see learned-log.md",
                      "min_tokens": 60, "abstain": [0.35, 0.65]}}
    out.write_text(json.dumps(model))
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
