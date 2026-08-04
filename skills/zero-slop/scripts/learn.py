#!/usr/bin/env python3
"""learn — the reflect loop: turn writers' own edits into detector evidence.

The most honest training signal a linter can get is the edit a writer makes
*after* it hands back a rewrite. If the skill returns a draft and the writer
strips a phrase before publishing, that phrase was a tell the meter missed.
Unlike a benchmark, that label comes from the genre, the voice, and the model
generation the user actually faces.

    python3 scripts/learn.py --reflect --produced out.md --shipped final.md
    python3 scripts/learn.py --promote                  # mint patterns that cleared threshold
    python3 scripts/learn.py --confirm drafts/          # re-earn weight on real slop
    python3 scripts/learn.py --stats                    # the learning curve

Why an edit does not immediately become a pattern
-------------------------------------------------
A single diff cannot distinguish a stylistic tell from a writer cutting a
sentence for length. An early version of this script watched one writer delete
"the people is the standard we hold ourselves to" and proposed it as an AI
tell; it was just content. So `--reflect` only *records an observation*. A span
becomes a pattern when it has been independently cut PROMOTE_AT times across
different documents, which is a property no single idiosyncratic edit can fake
and that gets strictly better as more people use the skill.

Three gates stand between an observation and a shipped pattern:

  1. Recurrence  — seen in PROMOTE_AT distinct documents (default 3).
  2. Novelty     — not already scored by the existing meter.
  3. Safety      — must not fire on data/corpus/must-not-flag/, the certified
                   human writing. This is the one that matters: a pattern
                   learned from one writer's edit must never start convicting
                   Lincoln, an SRE runbook, or a terse engineering note.
                   Learning that corrupts the meter is worse than not learning.

On regex brittleness
--------------------
Literal n-grams are brittle by construction: they miss inflection, insertions,
and next year's phrasing. Two mitigations here, and one architectural answer.
Generated patterns tolerate inflection (`moves/moved/moving the needle`) and
permit a short insertion for longer spans (`at the very end of the day`). The
architectural answer is that this pattern list is one channel of five — rhythm,
followability, formatting, and register are all phrasing-independent, and the
frequency-derived lexicon in calibrate.py generalizes where regexes cannot.
Patterns are the precise instrument for known constructions, never the whole
detector. See references/evidence.md.

Stdlib only, no network, no subprocess — same contract as the rest of the repo.
"""
import argparse
import difflib
import json
import re
import sys
from datetime import date
from pathlib import Path

import os

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CORPUS = DATA / "corpus" / "must-not-flag"
LOG = DATA / "learned-log.md"

# Reflection evidence is derived from the user's own drafts, so it is private by
# default and lives outside the repository — a checkout should never carry one
# person's writing. Override with ZERO_SLOP_HOME to relocate or to share a
# deliberate team-scoped store.
HOME = Path(os.environ.get("ZERO_SLOP_HOME",
                           Path.home() / ".zero-slop")).expanduser()
OBS = HOME / "reflections.json"

# An edit has to be worth generalizing. One-word cuts are usually taste; very
# long ones are unique to the draft and would never fire twice.
MIN_WORDS, MAX_WORDS = 2, 7
# Independent documents a span must be cut from before it earns a pattern.
PROMOTE_AT = 3
# Learned patterns start low and earn weight back through --confirm.
START_WEIGHT = 2.5
# Suffixes stripped so a pattern matches inflected forms of the same construction.
SUFFIXES = ("ing", "ed", "es", "s")
CONTEXT = 34
# Single words are the lexicon's business, not the pattern list's. They are also
# riskier — one word convicts far more text than a six-word construction — so
# they need more corroboration before they count.
LEXICON_PROMOTE_AT = 5
LEXICON_MIN_LEN = 6
# Words too common to ever be a tell, whatever the diff says.
STOPWORDS = set("""about above after again against because been before being
between both cannot could during each from further having however itself more
most other over should some such than that their them then there these they
this those through under until very were what when where which while with
would your""".split())


def load(p, default=None):
    p = Path(p)
    if not p.exists() and default is not None:
        return default
    return json.loads(p.read_text())


def words(t):
    return re.findall(r"\S+", t)


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def is_content_specific(span):
    """Reject spans that belong to one document rather than to a style.

    Digits and mid-span proper nouns mean the writer cut a fact, not a tell.
    Learning "raised 12M in Series B" as an AI pattern would be nonsense.
    """
    toks = span.split()
    if re.search(r"\d", span):
        return "contains a figure"
    caps = [w for w in toks[1:] if w[:1].isupper()]
    if caps:
        return f"proper noun ({caps[0].strip('.,')})"
    return None


def lexicon_candidates(produced, shipped):
    """Single words the writer struck. These belong in the lexicon, not in a regex.

    Why route them differently: a regex encodes one phrasing and dies when the
    next model generation rephrases. A lexicon term is phrasing-independent — it
    fires wherever the word appears — which is the channel that actually
    generalizes across eras. The excess-frequency method in calibrate.py works
    on exactly this representation, so a term learned here can later have its
    weight re-derived from corpus statistics rather than guessed.
    """
    a, b = words(produced), words(shipped)
    sm = difflib.SequenceMatcher(None, [norm(w) for w in a], [norm(w) for w in b])
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace"):
            for w in a[i1:i2]:
                n = norm(w)
                if (len(n) >= LEXICON_MIN_LEN and n not in STOPWORDS
                        and not re.search(r"\d", n) and not w[:1].isupper()):
                    out.append(n)
    return out


def stem(tok):
    for s in SUFFIXES:
        if len(tok) > len(s) + 3 and tok.endswith(s):
            return tok[: -len(s)]
    return tok


def to_regex(span):
    """Inflection-tolerant, insertion-tolerant, word-bounded.

    Content words match their own inflections; for spans of four or more tokens
    a single short insertion is allowed, which is what turns "at the end of the
    day" into something that also catches "at the very end of the day".
    """
    toks = norm(span).split()
    parts = []
    for t in toks:
        st = stem(t)
        parts.append(re.escape(st) + r"\w{0,3}" if st != t or len(t) > 5
                     else re.escape(t))
    gap = r"\s+(?:\w+\s+)?" if len(toks) >= 4 else r"\s+"
    return r"\b" + gap.join(parts) + r"\b"


def already_caught(span, pats, lex):
    for p in pats:
        try:
            if re.search(p["rx"], span, re.I):
                return p["name"]
        except re.error:
            continue
    low = span.lower()
    for term in lex:
        if term.lower() in low:
            return f"lexicon:{term}"
    return None


# A learned span that borrows this many consecutive words from certified human
# writing is too close to it, even when the full pattern does not match.
OVERLAP_NGRAM = 4


def corpus_files():
    return [f for f in sorted(CORPUS.rglob("*"))
            if f.is_file() and f.suffix in (".txt", ".md")]


def fp_gate(rx, span=None):
    """Return the human sample this pattern endangers, or None if it is safe.

    Two checks. The direct one asks whether the pattern fires on certified human
    writing. The second asks whether the span *borrows* from it: a pattern like
    "all men are created equal here" does not match the Gettysburg Address
    literally, because of that trailing word, yet it is built almost entirely
    out of it. Learning it would put the meter one small edit away from
    convicting Lincoln, so overlap is disqualifying on its own.
    """
    try:
        cre = re.compile(rx, re.I)
    except re.error as e:
        return f"regex error: {e}"
    files = corpus_files()
    for f in files:
        if cre.search(f.read_text()):
            return f.name
    if span:
        toks = norm(span).split()
        if len(toks) >= OVERLAP_NGRAM:
            grams = {" ".join(toks[i:i + OVERLAP_NGRAM])
                     for i in range(len(toks) - OVERLAP_NGRAM + 1)}
            for f in files:
                body = " ".join(norm(f.read_text()).split())
                for g in grams:
                    if g in body:
                        return f"{f.name} (borrows {g!r})"
    return None


def survived_hits(produced, shipped, pats):
    """Patterns that fired on the draft and whose text the writer KEPT anyway.

    This is the other half of the loop, and the half that makes it safe. Learning
    only from deletions gives a meter that can grow and never shrink, which ends
    at a detector that flags everything. A span the meter convicted that a human
    read, considered, and published unchanged is evidence the meter was wrong.
    Enough of those and the weight comes down, or the sentence joins the
    must-not-flag corpus so no future pattern can convict it either.
    """
    kept = shipped if isinstance(shipped, str) else ""
    out = []
    for p in pats:
        try:
            cre = re.compile(p["rx"], re.I)
        except re.error:
            continue
        for m in cre.finditer(produced):
            if m.group(0).lower() in kept.lower():
                out.append({"pattern": p["name"], "weight": p.get("w"),
                            "quote": m.group(0)[:70]})
                break
    return out


def diff_spans(produced, shipped):
    """Spans the skill emitted that the writer removed before publishing."""
    a, b = words(produced), words(shipped)
    sm = difflib.SequenceMatcher(None, [norm(w) for w in a], [norm(w) for w in b])
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace") and MIN_WORDS <= i2 - i1 <= MAX_WORDS:
            out.append({
                "span": " ".join(a[i1:i2]),
                "before": " ".join(a[max(0, i1 - 5):i1])[-CONTEXT:],
                "after": " ".join(a[i2:i2 + 5])[:CONTEXT],
                "replaced_with": " ".join(b[j1:j2]) if tag == "replace" else "",
            })
    return out


def reflect(produced, shipped, doc_id):
    base = load(DATA / "patterns.json")
    learned = load(DATA / "learned.json")
    pats = base["patterns"] + learned.get("patterns", [])
    lex = list(base.get("lexicon", {})) + list(learned.get("lexicon", {}))
    obs = load(OBS, {"_comment": "Reflect-loop evidence. 'observations' are spans "
                                 "writers cut that the meter missed; 'false_positives' "
                                 "are patterns that fired on text the writer kept. "
                                 "Both need corroboration before they change anything.",
                     "observations": {}, "false_positives": {}})
    obs.setdefault("false_positives", {})

    doc = doc_id or Path(produced).name
    today = str(date.today())
    prod_text = Path(produced).read_text()
    ship_text = Path(shipped).read_text()

    obs.setdefault("lexicon_candidates", {})
    base_lex = {k.lower() for k in base.get("lexicon", {})}
    base_lex |= {k.lower() for k in base.get("riders", {})}
    base_lex |= {k.lower() for k in learned.get("lexicon", {})}
    for w in lexicon_candidates(prod_text, ship_text):
        if any(w.startswith(t_) or t_.startswith(w) for t_ in base_lex):
            continue                        # the lexicon already speaks to this
        rec = obs["lexicon_candidates"].setdefault(
            w, {"count": 0, "docs": [], "first_seen": today})
        if doc not in rec["docs"]:
            rec["count"] += 1
            rec["docs"].append(doc)
            rec["last_seen"] = today

    # The meter was wrong here: it convicted text a human read and published.
    fps = survived_hits(prod_text, ship_text, pats)
    for h in fps:
        rec = obs["false_positives"].setdefault(
            h["pattern"], {"count": 0, "docs": [], "first_seen": today,
                           "weight": h["weight"], "quotes": []})
        if doc in rec["docs"]:
            continue
        rec["count"] += 1
        rec["docs"].append(doc)
        rec["last_seen"] = today
        if len(rec["quotes"]) < 3:
            rec["quotes"].append(h["quote"])
    recorded = skipped = agreed = 0
    fresh = []

    for d in diff_spans(prod_text, ship_text):
        key = norm(d["span"])
        if not key:
            continue
        if already_caught(d["span"], pats, lex):
            agreed += 1
            continue
        why = is_content_specific(d["span"])
        if why:
            skipped += 1
            continue
        rec = obs["observations"].setdefault(
            key, {"count": 0, "docs": [], "first_seen": today,
                  "last_seen": today, "examples": []})
        if doc in rec["docs"]:
            continue                      # one vote per document
        rec["count"] += 1
        rec["docs"].append(doc)
        rec["last_seen"] = today
        if len(rec["examples"]) < 3:
            rec["examples"].append(f"…{d['before']} [{d['span']}] {d['after']}…".strip())
        recorded += 1
        fresh.append((key, rec["count"]))

    OBS.parent.mkdir(parents=True, exist_ok=True)
    OBS.write_text(json.dumps(obs, indent=1) + "\n")

    print(f"reflect: {Path(produced).name} → {Path(shipped).name}\n")
    print(f"  {agreed} edit(s) the meter already caught — it was right, "
          f"the writer agreed")
    print(f"  {skipped} content-specific cut(s) ignored (figures, proper nouns)")
    print(f"  {recorded} missed-tell observation(s) recorded")
    print(f"  {len(fps)} pattern(s) fired on text the writer KEPT "
          f"(false-positive evidence)\n")
    for h in fps:
        rec = obs["false_positives"][h["pattern"]]
        state = "REVIEW" if rec["count"] >= PROMOTE_AT else f"{rec['count']}/{PROMOTE_AT}"
        print(f"    ✗ {state:>6}  {h['pattern']:24s} kept: {h['quote'][:34]!r}")
    if fps:
        print()
    for key, n in fresh:
        bar = "▮" * n + "▯" * max(0, PROMOTE_AT - n)
        state = "READY" if n >= PROMOTE_AT else f"{n}/{PROMOTE_AT}"
        print(f"    {bar}  {state:>5}  {key[:52]!r}")
    lex_ready = [(w, r["count"]) for w, r in obs["lexicon_candidates"].items()
                 if r["count"] >= LEXICON_PROMOTE_AT]
    lex_pend = [(w, r["count"]) for w, r in obs["lexicon_candidates"].items()
                if 0 < r["count"] < LEXICON_PROMOTE_AT]
    if lex_ready or lex_pend:
        print("  lexicon candidates (single words, "
              f"{LEXICON_PROMOTE_AT} documents needed):")
        for w, n in sorted(lex_ready + lex_pend, key=lambda x: -x[1])[:8]:
            state = "READY" if n >= LEXICON_PROMOTE_AT else f"{n}/{LEXICON_PROMOTE_AT}"
            print(f"    {state:>6}  {w}")
        print()
    ready = [k for k, v in obs["observations"].items() if v["count"] >= PROMOTE_AT]
    if ready:
        print(f"\n  {len(ready)} span(s) at threshold. Run --promote to mint them.")
    else:
        print(f"\n  nothing at threshold yet. Patterns need {PROMOTE_AT} "
              f"independent documents.")
    return 0


def promote(apply_, cat, weight):
    """Mint patterns from observations that cleared recurrence, novelty and safety."""
    obs = load(OBS, {"observations": {}})
    base, learned = load(DATA / "patterns.json"), load(DATA / "learned.json")
    pats = base["patterns"] + learned.get("patterns", [])
    lex = list(base.get("lexicon", {})) + list(learned.get("lexicon", {}))
    known = {p["name"] for p in pats}

    eligible, blocked, dup = [], [], []
    for key, rec in sorted(obs.get("observations", {}).items(),
                           key=lambda kv: -kv[1]["count"]):
        if rec["count"] < PROMOTE_AT or rec.get("promoted"):
            continue
        rx = to_regex(key)
        if already_caught(key, pats, lex):
            dup.append((key, already_caught(key, pats, lex)))
            continue
        hit = fp_gate(rx, key)
        (blocked if hit else eligible).append((key, rec, rx, hit))

    print(f"promote: {len(eligible)} eligible, {len(blocked)} blocked by the "
          f"safety gate, {len(dup)} already covered\n")
    for key, hit in dup:
        print(f"  covered   {key[:44]!r} ← {hit}")
    for key, rec, rx, hit in blocked:
        print(f"  REJECTED  {key[:44]!r}")
        print(f"            would convict {hit}; not learned at any threshold")
    for key, rec, rx, _ in eligible:
        print(f"  ready     {key[:44]!r}  cut from {rec['count']} documents")
        print(f"            rx {rx[:76]}")

    # Single words enter as *riders*, never as always-on lexicon terms. A word
    # like "robust" or "elevated" is ordinary technical vocabulary until a
    # marketing register shares its sentence; shipping it always-on is how a
    # meter starts convicting runbooks. Context-gated is the safe default, and
    # a term only graduates to always-on if excess-frequency data from
    # calibrate.py later justifies it.
    lex_ready = [(w, r) for w, r in obs.get("lexicon_candidates", {}).items()
                 if r["count"] >= LEXICON_PROMOTE_AT and not r.get("promoted")]
    lex_safe = []
    for w, r in lex_ready:
        hit = fp_gate(r"\b" + re.escape(w), None)
        if hit:
            print(f"  REJECTED  lexicon {w!r} appears in {hit}")
        else:
            lex_safe.append((w, r))
    for w, r in lex_safe:
        print(f"  ready     lexicon {w!r} cut from {r['count']} documents "
              f"-> rider (context-gated)")

    if not eligible and not lex_safe:
        return 0
    if not apply_:
        print(f"\n  dry run. Re-run with --apply to mint {len(eligible)} pattern(s)"
              f" and {len(lex_safe)} rider(s).")
        return 0

    today = str(date.today())
    added = []
    for key, rec, rx, _ in eligible:
        stem_name = re.sub(r"[^a-z0-9]+", "-", key)[:34].strip("-")
        name, i = stem_name, 2
        while name in known:
            name, i = f"{stem_name}-{i}", i + 1
        known.add(name)
        added.append({"name": name, "cat": cat, "rx": rx, "w": weight,
                      "first_seen": today, "last_confirmed": today,
                      "source": "reflect", "seen_in_docs": rec["count"],
                      # the span only — never the captured context, which is
                      # the author's own writing and must not leave their machine
                      "example": key[:90]})
        rec["promoted"] = today
    learned.setdefault("patterns", []).extend(added)
    for w, r in lex_safe:
        learned.setdefault("riders", {})[w] = round(weight / 2, 2)
        r["promoted"] = today
    (DATA / "learned.json").write_text(json.dumps(learned, indent=1) + "\n")
    OBS.parent.mkdir(parents=True, exist_ok=True)
    OBS.write_text(json.dumps(obs, indent=1) + "\n")
    with LOG.open("a") as fh:
        if lex_safe:
            fh.write(f"\n- {today} — Reflect loop added {len(lex_safe)} "
                     f"context-gated rider(s) ({', '.join(w for w, _ in lex_safe)}) "
                     f"after each was struck from {LEXICON_PROMOTE_AT}+ documents. "
                     f"Entered as riders, not always-on lexicon terms.\n")
        fh.write(f"\n- {today} — Reflect loop promoted {len(added)} pattern(s) "
                 f"after each was independently cut from {PROMOTE_AT}+ documents "
                 f"({', '.join(a['name'] for a in added)}); "
                 f"{len(blocked)} rejected by the false-positive gate. "
                 f"Source documents are not recorded: reflection evidence stays "
                 f"on the machine that produced it.\n")
    print(f"\n  minted {len(added)} pattern(s) → data/learned.json")
    print("  run: python3 scripts/calibrate.py --selftest")
    return 0


def demote(apply_):
    """Act on false-positive evidence: lower the weight of patterns humans overrule.

    A pattern that repeatedly convicts text writers then publish unchanged is
    measuring the tool's taste, not the reader's. Halving its weight is the
    conservative move; a base pattern is never edited in place, it gets a
    lower-weighted override in learned.json, which keeps the base taxonomy
    auditable and the change reversible.
    """
    obs = load(OBS, {"false_positives": {}})
    base, learned = load(DATA / "patterns.json"), load(DATA / "learned.json")
    base_by = {p["name"]: p for p in base["patterns"]}
    learned_by = {p["name"]: p for p in learned.get("patterns", [])}

    due = [(n, r) for n, r in obs.get("false_positives", {}).items()
           if r["count"] >= PROMOTE_AT and not r.get("demoted")]
    if not due:
        pend = len(obs.get("false_positives", {}))
        print(f"demote: nothing at threshold ({pend} pattern(s) under observation, "
              f"{PROMOTE_AT} kept-instances needed)")
        return 0
    print(f"demote: {len(due)} pattern(s) overruled by writers {PROMOTE_AT}+ times\n")
    for n, r in due:
        cur = learned_by.get(n, base_by.get(n, {})).get("w", r.get("weight", 0))
        print(f"  {n:26s} w {cur} -> {round(cur/2, 2)}  kept in {r['count']} docs")
        for q in r["quotes"][:2]:
            print(f"      writer published: {q!r}")
    if not apply_:
        print("\n  dry run. Re-run with --apply to lower these weights.")
        return 0
    today = str(date.today())
    for n, r in due:
        cur = learned_by.get(n, base_by.get(n, {})).get("w", r.get("weight", 2))
        new_w = round(cur / 2, 2)
        if n in learned_by:
            learned_by[n]["w"] = new_w
            learned_by[n]["demoted"] = today
        else:
            src = dict(base_by[n]); src["w"] = new_w
            src["demoted"] = today; src["source"] = "reflect-fp"
            learned.setdefault("patterns", []).append(src)
        r["demoted"] = today
    (DATA / "learned.json").write_text(json.dumps(learned, indent=1) + "\n")
    OBS.parent.mkdir(parents=True, exist_ok=True)
    OBS.write_text(json.dumps(obs, indent=1) + "\n")
    with LOG.open("a") as fh:
        fh.write(f"\n- {today} — Reflect loop lowered {len(due)} pattern weight(s) "
                 f"after writers published the flagged text unchanged in "
                 f"{PROMOTE_AT}+ documents ({', '.join(n for n, _ in due)}).\n")
    print(f"\n  lowered {len(due)} weight(s) in data/learned.json")
    return 0


def export(out, yes):
    """Package what was learned for upstream, carrying evidence but never text.

    The privacy argument rests on the recurrence threshold rather than on
    scrubbing. A span only becomes exportable once it has been cut from
    PROMOTE_AT independent documents, so by construction it is a phrase that
    recurs across unrelated writing — a generic construction, not anyone's
    sentence. Everything that could identify a document is left behind: no
    quotes, no context, no filenames, no paths, no author, and dates coarsened
    to the month so a contribution cannot be correlated with a commit time.

    What ships is the same shape as data/learned.json, so a maintainer can read
    the diff before merging. The user reviews the exact payload here first, and
    nothing is written without --yes.
    """
    obs = load(OBS, {"observations": {}, "false_positives": {}})
    payload = {"_comment": "Zero Slop reflect-loop contribution. Contains only "
                           "spans observed in " + str(PROMOTE_AT) + "+ independent "
                           "documents, with no source text, filenames or dates "
                           "finer than a month.",
               "schema": 1, "promote_at": PROMOTE_AT,
               "spans": [], "false_positives": []}
    for key, rec in sorted(obs.get("observations", {}).items(),
                           key=lambda kv: -kv[1]["count"]):
        if rec["count"] < PROMOTE_AT:
            continue
        rx = to_regex(key)
        if fp_gate(rx, key):
            continue                      # never ship a pattern that endangers the corpus
        payload["spans"].append({"span": key, "rx": rx, "documents": rec["count"],
                                 "month": rec.get("first_seen", "")[:7]})
    for name, rec in sorted(obs.get("false_positives", {}).items(),
                            key=lambda kv: -kv[1]["count"]):
        if rec["count"] >= PROMOTE_AT:
            payload["false_positives"].append(
                {"pattern": name, "kept_in_documents": rec["count"],
                 "month": rec.get("first_seen", "")[:7]})

    n = len(payload["spans"]) + len(payload["false_positives"])
    if not n:
        print(f"export: nothing has reached the {PROMOTE_AT}-document threshold yet. "
              f"Nothing below it is shareable, by design.")
        return 0
    print("export: this is the complete contents of the contribution.\n")
    print(json.dumps(payload, indent=1))
    print(f"\n  {len(payload['spans'])} span(s), "
          f"{len(payload['false_positives'])} false-positive report(s).")
    print("  No source text, filenames, or author information is included.")
    if not yes:
        print(f"\n  Nothing written. Re-run with --yes --out {out} to save it, "
              f"then attach that file to a pull request.")
        return 0
    Path(out).write_text(json.dumps(payload, indent=1) + "\n")
    print(f"\n  wrote {out}. Review it once more, then open a PR against "
          f"data/learned.json.")
    return 0


def merge(path, apply_, cat, weight):
    """Maintainer side: fold a reviewed contribution into the shared taxonomy.

    Contributions are untrusted input. Every span is re-gated locally against
    this checkout's corpus rather than trusting the sender's claim, because the
    contributor's corpus may be older, smaller, or edited.
    """
    c = load(path)
    if c.get("schema") != 1:
        print(f"merge: unrecognised contribution schema {c.get('schema')!r}")
        return 1
    base, learned = load(DATA / "patterns.json"), load(DATA / "learned.json")
    known = {p["name"] for p in base["patterns"] + learned.get("patterns", [])}
    lex = list(base.get("lexicon", {})) + list(learned.get("lexicon", {}))
    pats = base["patterns"] + learned.get("patterns", [])

    accept, reject = [], []
    for s in c.get("spans", []):
        if s.get("documents", 0) < PROMOTE_AT:
            reject.append((s["span"], f"below threshold ({s.get('documents')})"))
        elif already_caught(s["span"], pats, lex):
            reject.append((s["span"], "already covered"))
        elif fp_gate(s["rx"], s["span"]):
            reject.append((s["span"], f"unsafe here: {fp_gate(s['rx'], s['span'])}"))
        else:
            accept.append(s)
    print(f"merge: {len(accept)} accepted, {len(reject)} rejected\n")
    for span, why in reject:
        print(f"  reject  {span[:44]!r}  {why}")
    for s in accept:
        print(f"  accept  {s['span'][:44]!r}  seen in {s['documents']} documents")
    for fp in c.get("false_positives", []):
        print(f"  note    writers kept text flagged by {fp['pattern']!r} "
              f"in {fp['kept_in_documents']} documents")
    if not accept or not apply_:
        if accept:
            print(f"\n  dry run. Re-run with --apply to add {len(accept)} pattern(s).")
        return 0
    today = str(date.today())
    added = []
    for s in accept:
        stem_name = re.sub(r"[^a-z0-9]+", "-", s["span"])[:34].strip("-")
        name, i = stem_name, 2
        while name in known:
            name, i = f"{stem_name}-{i}", i + 1
        known.add(name)
        added.append({"name": name, "cat": cat, "rx": s["rx"], "w": weight,
                      "first_seen": today, "last_confirmed": today,
                      "source": "contributed", "seen_in_docs": s["documents"],
                      "example": s["span"][:90]})
    learned.setdefault("patterns", []).extend(added)
    (DATA / "learned.json").write_text(json.dumps(learned, indent=1) + "\n")
    with LOG.open("a") as fh:
        fh.write(f"\n- {today} — Merged a reflect-loop contribution: "
                 f"{len(added)} pattern(s) ({', '.join(a['name'] for a in added)}), "
                 f"{len(reject)} rejected on re-gating against this corpus.\n")
    print(f"\n  merged {len(added)} pattern(s). Run: "
          f"python3 scripts/calibrate.py --selftest")
    return 0


def confirm(target):
    """Re-earn weight. Patterns that keep firing stay; the rest decay out."""
    p = DATA / "learned.json"
    d = load(p)
    t = Path(target)
    files = [t] if t.is_file() else sorted(
        f for f in t.rglob("*") if f.suffix in (".md", ".txt"))
    text = "\n".join(f.read_text() for f in files)
    today, n = str(date.today()), 0
    for pat in d.get("patterns", []):
        try:
            if re.search(pat["rx"], text, re.I):
                pat["last_confirmed"] = today
                pat["confirmations"] = pat.get("confirmations", 0) + 1
                n += 1
        except re.error:
            continue
    p.write_text(json.dumps(d, indent=1) + "\n")
    print(f"confirmed {n}/{len(d.get('patterns', []))} learned pattern(s) "
          f"against {len(files)} file(s)")
    return 0


def stats():
    base, learned = load(DATA / "patterns.json"), load(DATA / "learned.json")
    obs = load(OBS, {"observations": {}}).get("observations", {})
    lp = learned.get("patterns", [])
    allp = base["patterns"] + lp
    prov = sum(1 for p in allp if p.get("first_seen"))
    pending = {k: v for k, v in obs.items() if not v.get("promoted")}
    ready = sum(1 for v in pending.values() if v["count"] >= PROMOTE_AT)
    corpus = [f for f in CORPUS.rglob("*") if f.is_file()]
    print(f"  taxonomy      {len(allp)} patterns ({len(base['patterns'])} base, "
          f"{len(lp)} learned)")
    print(f"  provenance    {prov}/{len(allp)} dated — decay is live"
          if prov == len(allp) else
          f"  provenance    {prov}/{len(allp)} dated — decay is BLIND on the rest")
    src = {}
    for p in lp:
        k = p.get("source", "manual")
        src[k] = src.get(k, 0) + 1
    print(f"  learned via   {', '.join(f'{k}={v}' for k, v in sorted(src.items())) or 'nothing yet'}")
    print(f"  observing     {len(pending)} span(s) awaiting recurrence, "
          f"{ready} at the {PROMOTE_AT}-document threshold")
    print(f"  re-confirmed  {sum(1 for p in lp if p.get('confirmations'))} pattern(s) "
          f"have fired again since being added")
    print(f"  safety corpus {len(corpus)} human samples every new pattern must clear")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--reflect", action="store_true",
                    help="record what the writer changed about the skill's output")
    ap.add_argument("--produced", help="what the skill returned")
    ap.add_argument("--shipped", help="what the writer actually published")
    ap.add_argument("--doc-id", help="document identity (defaults to filename); "
                                     "one vote per document")
    ap.add_argument("--promote", action="store_true",
                    help="mint patterns from observations that cleared threshold")
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument("--cat", default="reflect-learned")
    ap.add_argument("--weight", type=float, default=START_WEIGHT)
    ap.add_argument("--confirm", metavar="PATH")
    ap.add_argument("--demote", action="store_true",
                    help="lower weights on patterns writers repeatedly overruled")
    ap.add_argument("--export", action="store_true",
                    help="package learnings for upstream, with no source text")
    ap.add_argument("--out", default="zero-slop-contribution.json")
    ap.add_argument("--yes", action="store_true", help="confirm writing the export")
    ap.add_argument("--merge", metavar="FILE",
                    help="maintainer: fold a reviewed contribution in, re-gated locally")
    ap.add_argument("--stats", action="store_true")
    a = ap.parse_args()

    if a.stats:
        return stats()
    if a.confirm:
        return confirm(a.confirm)
    if a.export:
        return export(a.out, a.yes)
    if a.merge:
        return merge(a.merge, a.apply, "contributed", a.weight)
    if a.demote:
        return demote(a.apply)
    if a.promote:
        return promote(a.apply, a.cat, a.weight)
    if a.reflect:
        if not (a.produced and a.shipped):
            ap.error("--reflect needs --produced and --shipped")
        return reflect(a.produced, a.shipped, a.doc_id)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
