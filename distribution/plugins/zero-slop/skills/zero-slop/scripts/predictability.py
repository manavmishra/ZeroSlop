#!/usr/bin/env python3
"""predictability — see how easily the AI assistant can guess the original wording.

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

Probe selection and scoring are deterministic, so the Python is fully testable. The
model's three guesses can vary unless the host provides deterministic generation. It is
a corroborating channel reported beside the surface score, never folded into it — the
surface score stays traceable to spans, and this says whether a model finds the prose
predictable.
"""
import json
import re
import sys
import argparse
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
    # Preserve character offsets while blanking code. Probe contexts slice this
    # cleaned text; shrinking a fenced block made every later offset point into
    # the wrong word in the original document.
    text = re.sub(r"```.*?```", lambda m: " " * len(m.group(0)), text, flags=re.S)
    text = re.sub(r"`[^`]*`", lambda m: " " * len(m.group(0)), text)
    return [(m.group(0), m.start(), m.end()) for m in re.finditer(r"[A-Za-z][A-Za-z'-]+", text)]


def _without_code(text):
    text = re.sub(r"```.*?```", lambda m: " " * len(m.group(0)), text, flags=re.S)
    return re.sub(r"`[^`]*`", lambda m: " " * len(m.group(0)), text)


def _norm(w):
    return re.sub(r"[^a-z]", "", w.lower())


def _morph_roots(word):
    """Conservative English inflection roots; never equate by prefix alone."""
    word = _norm(word)
    roots = {word}
    for suffix in ("ingly", "edly", "ing", "ied", "ed", "es", "s", "ly"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            stem = word[:-len(suffix)]
            roots.add(stem)
            if suffix in {"ing", "ed", "edly", "ingly"}:
                roots.add(stem + "e")
            if suffix == "ied":
                roots.add(stem + "y")
    return roots


def probes(text, k=12, window=45):
    """Deterministically pick up to k content words to mask.

    Eligible = alphabetic, >=4 letters, not a stopword, not the document's first word.
    They are taken at an even stride across the eligible list so the probes span the
    whole piece, and the selection is a pure function of the text — same input, same
    probes, which is what makes the score reproducible and the scorer testable.
    """
    if not isinstance(k, int) or isinstance(k, bool) or k < 1:
        raise ValueError("k must be a positive integer")
    if not isinstance(window, int) or isinstance(window, bool) or window < 0:
        raise ValueError("window must be a non-negative integer")
    clean = _without_code(text)
    ws = _words(clean)
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
        before = clean[:s]
        ctx_words = re.findall(r"\S+", before)[-window:]
        context = " ".join(ctx_words) + " ___"
        out.append({"id": pid, "context": context, "answer": _norm(w)})
    return out


def _hit(answer, guesses):
    """A guess counts if it matches the answer up to case and light morphology —
    exact, or a shared 4-letter stem, so "raised"/"raise" and "quickly"/"quick" land."""
    a = _norm(answer)
    answer_roots = _morph_roots(a)
    for g in guesses:
        gg = _norm(g)
        if not gg:
            continue
        if gg == a or answer_roots & _morph_roots(gg):
            return True
    return False


def score(text, predictions, k=12):
    """predictions: {id: [top guesses]}. Returns the predictability reading.

    predictability = share of masked words the model's top-three guesses recovered,
    0–100. Higher means more machine-predictable. The descriptive bands are operating
    thresholds, not calibrated probabilities, and the result is never silently folded
    into the surface score.
    """
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    if not isinstance(predictions, dict):
        raise ValueError("predictions must be a JSON object keyed by probe id")
    pr = probes(text, k=k)
    if not pr:
        return {"predictability": None, "hits": 0, "total": 0,
                "reading": "too short to probe", "backend": "harness-model"}
    preds = {}
    for key, guesses in predictions.items():
        try:
            probe_id = int(key)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid probe id: {key!r}") from exc
        if probe_id in preds:
            raise ValueError(f"duplicate probe id after normalization: {key!r}")
        if isinstance(guesses, str):
            guesses = [guesses]
        if (not isinstance(guesses, list) or not guesses or len(guesses) > 20
                or not all(isinstance(g, str) and len(g) <= 200 for g in guesses)):
            raise ValueError(f"predictions for probe {probe_id} must be a string list")
        preds[probe_id] = guesses
    expected = {p["id"] for p in pr}
    if set(preds) != expected:
        missing, extra = sorted(expected - set(preds)), sorted(set(preds) - expected)
        raise ValueError(f"prediction ids do not match probes: missing={missing}, extra={extra}")
    hits = 0
    for p in pr:
        g = preds.get(p["id"], [])
        if _hit(p["answer"], g[:3]):
            hits += 1
    total = len(pr)
    val = round(100 * hits / total, 1)
    if val >= 50:
        reading = "easy to guess — much of the wording follows familiar patterns"
    elif val >= 33:
        reading = "moderately easy to guess"
    else:
        reading = "hard to guess — the wording is less predictable"
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
    assert _hit("raised", ["raise"]), "light morphology must match"
    assert not _hit("station", ["statue"]), "shared prefixes are not morphology"
    print(f"predictability selftest OK — {len(pr)} probes, all-right=100.0, all-wrong=0.0")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--selftest", action="store_true")
    mode.add_argument("--probes", metavar="TEXT_FILE")
    mode.add_argument("--score", nargs=2, metavar=("TEXT_FILE", "PREDICTIONS_JSON"))
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if args.probes:
        try:
            text = Path(args.probes).read_text()
        except (OSError, UnicodeDecodeError) as exc:
            ap.error(f"cannot read text: {exc}")
        blanks = [{"id": p["id"], "context": p["context"]} for p in probes(text)]
        print(json.dumps(blanks, indent=1))
        return 0
    if args.score:
        try:
            text = Path(args.score[0]).read_text()
            preds = json.loads(Path(args.score[1]).read_text())
            r = score(text, preds)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            ap.error(str(exc))
        print(f"How easy the original wording was to guess: {r['predictability']}/100")
        print(f"  The model guessed {r['hits']} of {r['total']} hidden words. {r['reading']}.")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
