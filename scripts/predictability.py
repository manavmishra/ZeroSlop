#!/usr/bin/env python3
"""predictability — the model channel, powered by whatever model is running the skill.

The strongest signal that a machine wrote something is that a machine finds it
predictable: the words sit where a language model would have put them. Detectors
measure this with token log-probabilities, but Zero Slop ships no model and Claude's
API exposes no logprobs, so this computes the same thing a different way — a cloze
probe the harness's own model answers.

It masks a spread of content words, hands the blanks (context only, answer withheld)
to the model executing the skill, and measures how often the model's guesses hit the
word the author actually used. High agreement means the text is what the model would
have written — machine-predictable. Human writing picks the less-likely word more
often, and the score falls. This works with any harness model (Claude, GPT, …) because
it needs only generation, never logprobs, and Zero Slop supplies no model of its own.

The protocol is three steps, so any agent can drive it:

    python3 scripts/predictability.py --probes draft.md > probes.json     # 1. blanks
    # 2. the agent fills {id: [top-3 guesses]} from each context, into preds.json
    python3 scripts/predictability.py --score draft.md preds.json         # 3. reading

Deterministic end to end (fixed probe selection, no randomness), so the Python is fully
testable; only the middle step needs the model. It is a corroborating channel reported
beside the surface score, never folded into it — the surface score stays traceable to
spans, and this says whether a model finds the prose predictable.
"""
import json
import re
import sys
from pathlib import Path

# Function words carry no predictability signal (everyone writes "the", "of"), so
# probes land on content words only.
STOP = set("""the a an and or but if then else of to in on at by for with from into
over under again once here there when while as is are was were be been being have has
had do does did will would can could should may might must not no nor so than too very
this that these those it its their your our his her they them we you i he she who whom
which what how why about after before between during through above below up down out off
only just also even still yet more most less least own same other such both each any all
some few many much one two three""".split())


def _words(text):
    """(word, start, end) for alphabetic tokens, code and quotes stripped out."""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)
    return [(m.group(0), m.start(), m.end()) for m in re.finditer(r"[A-Za-z][A-Za-z'-]+", text)]


def _norm(w):
    return re.sub(r"[^a-z]", "", w.lower())


def probes(text, k=12, window=45):
    """Deterministically pick up to k content words to mask.

    Eligible = alphabetic, >=4 letters, not a stopword, not the document's first word.
    They are taken at an even stride across the eligible list so the probes span the
    whole piece, and the selection is a pure function of the text — same input, same
    probes, which is what makes the score reproducible and the scorer testable.
    """
    ws = _words(text)
    eligible = [i for i, (w, s, e) in enumerate(ws)
                if len(_norm(w)) >= 4 and _norm(w) not in STOP and i > 0]
    if not eligible:
        return []
    k = min(k, len(eligible))
    stride = len(eligible) / k
    picks = [eligible[int(j * stride)] for j in range(k)]

    out = []
    for pid, wi in enumerate(picks):
        w, s, e = ws[wi]
        before = text[:s]
        ctx_words = re.findall(r"\S+", before)[-window:]
        context = " ".join(ctx_words) + " ___"
        out.append({"id": pid, "context": context, "answer": _norm(w)})
    return out


def _hit(answer, guesses):
    """A guess counts if it matches the answer up to case and light morphology —
    exact, or a shared 4-letter stem, so "raised"/"raise" and "quickly"/"quick" land."""
    a = _norm(answer)
    for g in guesses:
        gg = _norm(g)
        if not gg:
            continue
        if gg == a or (len(a) >= 4 and len(gg) >= 4 and (a.startswith(gg[:4]) or gg.startswith(a[:4]))):
            return True
    return False


def score(text, predictions, k=12):
    """predictions: {id: [top guesses]}. Returns the predictability reading.

    predictability = share of masked words the model's guesses recovered, 0–100.
    Higher means more machine-predictable. The band is calibrated on the corpora in
    bench/ and reported, never silently folded into the surface score.
    """
    pr = probes(text, k=k)
    if not pr:
        return {"predictability": None, "hits": 0, "total": 0,
                "reading": "too short to probe", "backend": "harness-model"}
    preds = {int(kk): vv for kk, vv in predictions.items()}
    hits = 0
    for p in pr:
        g = preds.get(p["id"], [])
        if isinstance(g, str):
            g = [g]
        if _hit(p["answer"], g):
            hits += 1
    total = len(pr)
    val = round(100 * hits / total, 1)
    if val >= 50:
        reading = "high — a model finds this very predictable (machine-like)"
    elif val >= 33:
        reading = "moderate — somewhat predictable"
    else:
        reading = "low — the word choices surprise a model (human-like)"
    return {"predictability": val, "hits": hits, "total": total,
            "reading": reading, "backend": "harness-model"}


def _selftest():
    """The scaffold is deterministic; prove it without a model, both extremes."""
    text = ("The startup raised a substantial round from investors who believed in the "
            "mission. Revenue climbed steadily through the difficult second quarter, and "
            "the founders remained cautiously optimistic about the coming year ahead.")
    pr = probes(text, k=6)
    assert pr and probes(text, k=6) == pr, "probe selection must be deterministic"
    allright = {p["id"]: [p["answer"]] for p in pr}
    allwrong = {p["id"]: ["xyzzy"] for p in pr}
    hi = score(text, allright, k=6)
    lo = score(text, allwrong, k=6)
    assert hi["predictability"] == 100.0, hi
    assert lo["predictability"] == 0.0, lo
    # morphology: a stemmed guess still hits
    stem = {p["id"]: [p["answer"][:4]] for p in pr}
    assert score(text, stem, k=6)["predictability"] == 100.0
    print(f"predictability selftest OK — {len(pr)} probes, all-right=100.0, all-wrong=0.0")
    return 0


def main():
    argv = sys.argv[1:]
    if "--selftest" in argv:
        return _selftest()
    if "--probes" in argv:
        text = Path(argv[argv.index("--probes") + 1]).read_text()
        blanks = [{"id": p["id"], "context": p["context"]} for p in probes(text)]
        print(json.dumps(blanks, indent=1))
        return 0
    if "--score" in argv:
        i = argv.index("--score")
        text = Path(argv[i + 1]).read_text()
        preds = json.loads(Path(argv[i + 2]).read_text())
        r = score(text, preds)
        print(f"predictability: {r['predictability']}/100  ({r['hits']}/{r['total']} recovered)")
        print(f"  {r['reading']}")
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
