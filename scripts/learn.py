#!/usr/bin/env python3
"""learn — learn privately from changes a writer makes later.

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
becomes a pattern when it has been cut in PROMOTE_AT content-distinct edit pairs.
Content hashing prevents filename or caller-ID duplication from earning extra votes;
it does not authenticate different writers, so learned rules remain private until a
maintainer reviews and tests an explicit export.

Three gates stand between an observation and a shipped pattern:

  1. Recurrence  — seen in PROMOTE_AT content-distinct edit pairs (default 3).
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
from functools import wraps
import hashlib
import json
import math
import os
import re
import sys
from datetime import date
from pathlib import Path

from safeio import atomic_write_text, file_locks, is_within

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CORPUS = DATA / "corpus" / "must-not-flag"
SHARED = DATA / "learned.json"
SHARED_LOG = DATA / "learned-log.md"

# Reflection evidence is derived from the user's own drafts, so it is private by
# default and lives outside the repository — a checkout should never carry one
# person's writing. Override with ZERO_SLOP_HOME to relocate or to share a
# deliberate team-scoped store.
HOME = Path(os.environ.get("ZERO_SLOP_HOME",
                           Path.home() / ".zero-slop")).expanduser()
OBS = HOME / "reflections.json"
LOCAL = HOME / "learned.json"
LOCAL_LOG = HOME / "learned-log.md"

# An edit has to be worth generalizing. One-word cuts are usually taste; very
# long ones are unique to the draft and would never fire twice.
MIN_WORDS, MAX_WORDS = 3, 9
# Content-distinct edit pairs a span must recur in before it earns a pattern.
PROMOTE_AT = 3
# Learned patterns start low; --confirm keeps current evidence from aging out.
START_WEIGHT = 2.5
DECAY_MONTHS = 18
# Suffixes stripped so a pattern matches inflected forms of the same construction.
SUFFIXES = ("ing", "ed", "es", "s")
CONTEXT = 34
# Single words are the lexicon's business, not the pattern list's. They are also
# riskier — one word convicts far more text than a six-word construction — so
# they need more corroboration before they count.
LEXICON_PROMOTE_AT = 5
LEXICON_MIN_LEN = 6
VOICE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
# Words too common to ever be a tell, whatever the diff says.
STOPWORDS = set("""about above after again against because been before being
between both cannot could during each from further having however itself more
most other over should some such than that their them then there these they
this those through under until very were what when where which while with
would your""".split())

# Editorial reasons are deliberately few and stable. They describe why a change
# helped; they are not model probabilities.
REASON_LABELS = {
    "unspecified", "hollow_substance", "semantic_redundancy",
    "vague_reference", "canned_framing", "genre_mismatch",
    "local_repetition", "unsupported_attribution", "reader_process_leak",
    "rhythm", "formatting", "grammar", "fidelity", "other",
}
GENRES = {
    "general", "linkedin", "x", "email", "blog", "newsletter",
    "research", "professional", "social",
}
MAX_RETRIEVAL_RESULTS = 20
MAX_RETRIEVAL_TEXT = 500000
MAX_RETRIEVAL_PREFERENCES = 50000
MAX_FEEDBACK_BYTES = 1024 * 1024


def validate_label(label, allowed, kind):
    if label not in allowed:
        raise SystemExit(f"unknown {kind} {label!r}; choose one of: "
                         + ", ".join(sorted(allowed)))
    return label


def valid_counts(value, allowed, maximum):
    return (isinstance(value, dict)
            and all(isinstance(key, str) and key in allowed
                    and isinstance(count, int) and not isinstance(count, bool)
                    and count >= 0
                    for key, count in value.items())
            and sum(value.values()) <= maximum)


def bump_count(record, field, label):
    counts = record.setdefault(field, {})
    counts[label] = counts.get(label, 0) + 1


def text_sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path, obj, *, private=False):
    """Durably replace JSON; private observations are owner-readable only."""
    atomic_write_text(path, json.dumps(obj, indent=1) + "\n",
                      mode=0o600 if private else None)


def state_locked(*path_providers):
    """Serialize a read-modify-write operation across processes."""
    def decorate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            paths = [p(*args, **kwargs) if callable(p) else p
                     for p in path_providers]
            with file_locks(paths):
                return fn(*args, **kwargs)
        return wrapped
    return decorate


def append_log(path, entry, *, private=False):
    current = path.read_text() if path.exists() else ""
    atomic_write_text(path, current + entry, mode=0o600 if private else None)


def empty_learned(scope="local"):
    return {"_comment": f"Zero Slop {scope} learning overlay.",
            "patterns": [], "lexicon": {}, "riders": {},
            "fix_preferences": []}


def empty_observations():
    return {"_comment": "Private reflect-loop evidence. Observations, false "
                        "positives, and recurring fixes need corroboration before "
                        "they change the live overlay.",
            "observations": {}, "false_positives": {},
            "lexicon_candidates": {}, "fix_observations": {}}


def learned_layers():
    """Shared reviewed rules first, then the private live overlay."""
    return (load_learned(SHARED, "shared"),
            load_learned(LOCAL, "local"))


def safe_voice_name(name):
    if not VOICE_NAME.fullmatch(name or "") or name in (".", ".."):
        raise SystemExit(
            "voice name must be 1-64 letters, digits, dots, underscores, or hyphens"
        )
    return name


def load(p, default=None):
    p = Path(p)
    if not p.exists() and default is not None:
        return default
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        raise SystemExit(
            f"{p} is not readable, valid JSON. Repair or restore it before re-running."
        )


def load_learned(path, scope):
    """Load an overlay without ever normalizing malformed state into a write."""
    data = load(path, empty_learned(scope))
    valid = (isinstance(data, dict)
             and isinstance(data.get("patterns", []), list)
             and isinstance(data.get("lexicon", {}), dict)
             and isinstance(data.get("riders", {}), dict)
             and isinstance(data.get("fix_preferences", []), list))
    if valid:
        names = set()
        for pattern in data.get("patterns", []):
            if (not isinstance(pattern, dict)
                    or not isinstance(pattern.get("name"), str)
                    or not 1 <= len(pattern["name"]) <= 128
                    or not isinstance(pattern.get("cat"), str)
                    or not 1 <= len(pattern["cat"]) <= 64
                    or not isinstance(pattern.get("rx"), str)
                    or len(pattern["rx"]) > 2000
                    or re.search(r"\\[1-9]|\(\?<*[=!]|\([^()]*[+*][^()]*\)[+*]",
                                 pattern["rx"])
                    or not isinstance(pattern.get("w"), (int, float))
                    or isinstance(pattern.get("w"), bool)
                    or not math.isfinite(pattern["w"])
                    or not 0 <= pattern["w"] <= 10
                    or pattern["name"] in names):
                valid = False
                break
            names.add(pattern["name"])
            try:
                re.compile(pattern["rx"])
            except re.error:
                valid = False
                break
            for key in ("first_seen", "last_confirmed", "decayed"):
                if key in pattern and not isinstance(pattern[key], str):
                    valid = False
                    break
            if ("confirmations" in pattern
                    and (not isinstance(pattern["confirmations"], int)
                         or isinstance(pattern["confirmations"], bool)
                         or pattern["confirmations"] < 0)):
                valid = False
                break
            for key in ("source_span", "preferred_fix"):
                if (key in pattern
                        and (not isinstance(pattern[key], str)
                             or not 1 <= len(pattern[key]) <= 500)):
                    valid = False
                    break
            if ("fix_seen_in_docs" in pattern
                    and (not isinstance(pattern["fix_seen_in_docs"], int)
                         or isinstance(pattern["fix_seen_in_docs"], bool)
                         or pattern["fix_seen_in_docs"] < 0)):
                valid = False
                break
            evidence_n = pattern.get("seen_in_docs", pattern.get("fix_seen_in_docs", 0))
            if ("reasons" in pattern
                    and not valid_counts(pattern["reasons"], REASON_LABELS, evidence_n)):
                valid = False
                break
            if ("genres" in pattern
                    and not valid_counts(pattern["genres"], GENRES, evidence_n)):
                valid = False
                break
        for field in ("lexicon", "riders"):
            for term, weight in data.get(field, {}).items():
                if (not isinstance(term, str) or not 1 <= len(term) <= 80
                        or not isinstance(weight, (int, float))
                        or isinstance(weight, bool) or not math.isfinite(weight)
                        or not 0 <= weight <= 10):
                    valid = False
                    break
        preference_spans = set()
        for pref in data.get("fix_preferences", []):
            if (not isinstance(pref, dict)
                    or not isinstance(pref.get("source_span"), str)
                    or not 1 <= len(pref.get("source_span", "")) <= 500
                    or not isinstance(pref.get("preferred_fix"), str)
                    or not 1 <= len(pref.get("preferred_fix", "")) <= 500
                    or not isinstance(pref.get("seen_in_pairs", 0), int)
                    or isinstance(pref.get("seen_in_pairs", 0), bool)
                    or pref.get("seen_in_pairs", 0) < 0
                    or ("active" in pref and not isinstance(pref["active"], bool))
                    or pref.get("source_span") in preference_spans
                    or ("reasons" in pref and not valid_counts(
                        pref["reasons"], REASON_LABELS, pref.get("seen_in_pairs", 0)))
                    or ("genres" in pref and not valid_counts(
                        pref["genres"], GENRES, pref.get("seen_in_pairs", 0)))
                    or any(key in pref and not isinstance(pref[key], str)
                           for key in ("first_seen", "last_confirmed", "decayed"))):
                valid = False
                break
            preference_spans.add(pref["source_span"])
    if not valid:
        raise SystemExit(
            f"{path} has an invalid learning-overlay schema; repair it before re-running."
        )
    return data


def load_observations():
    """Load private evidence without silently repairing malformed structure."""
    data = load(OBS, empty_observations())
    fields = ("observations", "false_positives", "lexicon_candidates",
              "fix_observations")
    if not isinstance(data, dict) or any(
            not isinstance(data.get(field, {}), dict) for field in fields):
        raise SystemExit(f"{OBS} has an invalid reflection schema; repair it before re-running.")
    key_limits = {"observations": 500, "false_positives": 128,
                  "lexicon_candidates": 80, "fix_observations": 500}
    for field in fields:
        for key, rec in data.get(field, {}).items():
            if (not isinstance(key, str) or not key.strip()
                    or len(key) > key_limits[field]):
                raise SystemExit(
                    f"{OBS} has an invalid reflection schema; repair it before re-running."
                )
            docs = rec.get("docs", []) if isinstance(rec, dict) else []
            if (not isinstance(rec, dict)
                    or not isinstance(rec.get("count", 0), int)
                    or isinstance(rec.get("count", 0), bool)
                    or rec.get("count", 0) < 0
                    or not isinstance(docs, list)
                    or not all(isinstance(doc, str) and doc for doc in docs)
                    or len(docs) != len(set(docs))
                    or rec.get("count", 0) != len(docs)):
                raise SystemExit(
                    f"{OBS} has an invalid reflection schema; repair it before re-running."
                )
            if ("reasons" in rec
                    and not valid_counts(rec["reasons"], REASON_LABELS, rec["count"])):
                raise SystemExit(
                    f"{OBS} has an invalid reflection schema; repair it before re-running."
                )
            if ("genres" in rec
                    and not valid_counts(rec["genres"], GENRES, rec["count"])):
                raise SystemExit(
                    f"{OBS} has an invalid reflection schema; repair it before re-running."
                )
            list_field = ("examples" if field == "observations" else
                          "quotes" if field == "false_positives" else None)
            if (list_field and (not isinstance(rec.get(list_field), list)
                                or not all(isinstance(value, str)
                                           for value in rec[list_field]))):
                raise SystemExit(
                    f"{OBS} has an invalid reflection schema; repair it before re-running."
                )
            if field == "false_positives":
                weight = rec.get("weight")
                if (not isinstance(weight, (int, float))
                        or isinstance(weight, bool)
                        or not math.isfinite(weight)
                        or not 0 <= weight <= 10):
                    raise SystemExit(
                        f"{OBS} has an invalid reflection schema; repair it before re-running."
                    )
            if field == "fix_observations":
                applied_count = rec.get("applied_count", 0)
                if (not isinstance(applied_count, int)
                        or isinstance(applied_count, bool)
                        or applied_count < 0
                        or applied_count > rec.get("count", 0)):
                    raise SystemExit(
                        f"{OBS} has an invalid reflection schema; repair it before re-running."
                    )
                replacements = rec.get("replacements", {})
                if not isinstance(replacements, dict):
                    raise SystemExit(
                        f"{OBS} has an invalid reflection schema; repair it before re-running."
                    )
                for replacement, fix in replacements.items():
                    fix_docs = fix.get("docs", []) if isinstance(fix, dict) else []
                    if (not isinstance(fix, dict)
                            or not isinstance(replacement, str)
                            or not 1 <= len(replacement) <= 500
                            or not isinstance(fix.get("count", 0), int)
                            or isinstance(fix.get("count", 0), bool)
                            or fix.get("count", 0) < 0
                            or not isinstance(fix_docs, list)
                            or not all(isinstance(doc, str) and doc for doc in fix_docs)
                            or len(fix_docs) != len(set(fix_docs))
                            or fix.get("count", 0) != len(fix_docs)
                            or not set(fix_docs).issubset(set(docs))
                            or ("reasons" in fix and not valid_counts(
                                fix["reasons"], REASON_LABELS, fix.get("count", 0)))
                            or ("genres" in fix and not valid_counts(
                                fix["genres"], GENRES, fix.get("count", 0)))):
                        raise SystemExit(
                            f"{OBS} has an invalid reflection schema; repair it before re-running."
                        )
    return data


def bounded_weight(value):
    """Argparse type for weights that the scorer can load safely."""
    try:
        weight = float(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("weight must be a number from 0 to 10") from exc
    if not math.isfinite(weight) or not 0 <= weight <= 10:
        raise argparse.ArgumentTypeError("weight must be a finite number from 0 to 10")
    return weight


def words(t):
    return re.findall(r"\S+", t)


def norm(s):
    """Lowercase, keeping the punctuation that carries meaning.

    Apostrophes and hyphens are part of the token: stripping them turned
    "it's worth pointing out" into a pattern for "its", which matched nothing —
    and a regex that matches nothing passes the safety gate trivially, so the
    gate reported success on a pattern that could never fire.
    """
    return re.sub(r"[^a-z0-9 '\u2019-]", "", s.lower()).strip()


def is_all_function_words(span):
    """A span of nothing but grammar is not a style tell.

    "for us", "over time", "in practice" all cleared recurrence, novelty and the
    safety corpus, then shipped as AI tells and fired on ordinary sentences.
    A construction has to carry at least one content word to be a construction.
    """
    toks = [t for t in norm(span).split() if t]
    return not any(t not in STOPWORDS and len(t) > 3 for t in toks)


def is_content_specific(span):
    """Reject spans that belong to one document rather than to a style.

    Digits and mid-span proper nouns mean the writer cut a fact, not a tell.
    Learning "raised 12M in Series B" as an AI pattern would be nonsense.
    """
    toks = span.split()
    if re.search(r"\d", span):
        return "contains a figure"
    # every token, not toks[1:]: a cut starting at a sentence boundary
    # was leaking brand names ("Acme really improved the flow")
    caps = [w for w in toks if w[:1].isupper() and w.lower() not in STOPWORDS]
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
    for tok in toks:
        st = stem(tok)
        body = re.escape(st) + r"\w{0,3}" if st != tok or len(tok) > 5 else re.escape(tok)
        # straight and curly apostrophes are the same word; so are hyphen and space
        body = body.replace(re.escape("'"), "['\u2019]").replace("\\-", "[-\\s]")
        parts.append(body)
    # One optional insertion across the whole span, not between every pair: with
    # a gap at each join a 7-token pattern accepted six filler words and matched
    # sentences it had nothing to do with.
    if len(toks) >= 4:
        joined = r"\s+".join(parts)
        alts = [r"\s+".join(parts[:i] + [r"\w+"] + parts[i:]) for i in range(1, len(parts))]
        return r"\b(?:" + "|".join([joined] + alts) + r")\b"
    return r"\b" + r"\s+".join(parts) + r"\b"


def already_caught(span, pats, lex):
    for p in pats:
        try:
            if re.search(p["rx"], span, re.I):
                return p["name"]
        except re.error:
            continue
    low = span.lower()
    for term in lex:
        if re.search(r"\b" + re.escape(term.lower()) + r"\w*", low):
            return f"lexicon:{term}"
    return None


# A learned span that borrows this many consecutive words from certified human
# writing is too close to it, even when the full pattern does not match.
OVERLAP_NGRAM = 4


def corpus_files():
    return [f for f in sorted(CORPUS.rglob("*"))
            if f.is_file() and f.suffix.lower() in (".txt", ".md")
            and f.name.lower() != "readme.md"]


def required_text(path, label):
    """Read user-supplied prose with a clean, path-specific failure."""
    target = Path(path)
    if not target.exists() or not target.is_file():
        raise SystemExit(f"{label} is not a readable file: {target}")
    try:
        return target.read_text()
    except (OSError, UnicodeDecodeError) as exc:
        raise SystemExit(f"cannot read {label} at {target}: {exc}") from exc


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
    if not files:
        return "safety corpus missing or empty"
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
    opcodes = sm.get_opcodes()

    def sentence_replacement(src_start, src_end):
        """Recover the edited sentence when SequenceMatcher reports a deletion.

        A rewrite such as "This puts wood ... on latency for us" -> "Latency
        dropped" is represented as a deletion, a one-word equality, and a
        replacement. Looking only at the deletion loses the human fix. Bound the
        lookup to the affected source sentence and collect its aligned target
        words; recurrence gates still require the same fix in multiple
        content-distinct edit pairs before it can become guidance.
        """
        sent_start = src_start
        while sent_start > 0 and not re.search(r"[.!?][\"')\]]*$", a[sent_start - 1]):
            sent_start -= 1
        sent_end = src_end
        while sent_end < len(a):
            if re.search(r"[.!?][\"')\]]*$", a[sent_end]):
                sent_end += 1
                break
            sent_end += 1
        target_ranges = []
        for _, oi1, oi2, oj1, oj2 in opcodes:
            overlaps = oi1 < sent_end and oi2 > sent_start
            insertion_inside = oi1 == oi2 and sent_start <= oi1 <= sent_end
            if (overlaps or insertion_inside) and oj2 > oj1:
                target_ranges.append((oj1, oj2))
        if not target_ranges:
            return ""
        j1 = min(r[0] for r in target_ranges)
        j2 = max(r[1] for r in target_ranges)
        return " ".join(b[j1:j2])

    out = []
    for tag, i1, i2, j1, j2 in opcodes:
        if tag in ("delete", "replace") and MIN_WORDS <= i2 - i1 <= MAX_WORDS:
            replacement = " ".join(b[j1:j2]) if tag == "replace" else ""
            if not replacement:
                replacement = sentence_replacement(i1, i2)
            out.append({
                "span": " ".join(a[i1:i2]),
                "before": " ".join(a[max(0, i1 - 5):i1])[-CONTEXT:],
                "after": " ".join(a[i2:i2 + 5])[:CONTEXT],
                "replaced_with": replacement,
            })
    return out


def load_edit_feedback(path, produced, shipped, diffs):
    """Load optional per-edit reason labels bound to an exact before/after pair."""
    source = Path(path)
    if not source.is_file():
        raise SystemExit(f"feedback is not a readable file: {source}")
    try:
        if source.stat().st_size > MAX_FEEDBACK_BYTES:
            raise SystemExit(f"feedback exceeds {MAX_FEEDBACK_BYTES} bytes")
        payload = json.loads(source.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"feedback must be readable UTF-8 JSON: {exc}") from exc
    if (not isinstance(payload, dict)
            or set(payload) != {"schema", "source_sha256", "target_sha256", "edits"}
            or payload.get("schema") != 1
            or payload.get("source_sha256") != text_sha256(produced)
            or payload.get("target_sha256") != text_sha256(shipped)
            or not isinstance(payload.get("edits"), list)
            or len(payload["edits"]) > 1000):
        raise SystemExit("feedback schema or source/target hash is invalid")
    available = {norm(item["span"]): item["span"] for item in diffs if norm(item["span"])}
    labels = {}
    for index, item in enumerate(payload["edits"], 1):
        if (not isinstance(item, dict)
                or set(item) != {"source_span", "reason", "genre"}
                or not isinstance(item.get("source_span"), str)
                or not 1 <= len(item["source_span"]) <= 500):
            raise SystemExit(f"feedback edit {index} is malformed")
        key = norm(item["source_span"])
        if key not in available or key in labels:
            raise SystemExit(f"feedback edit {index} has an unknown or duplicate source_span")
        labels[key] = (
            validate_label(item.get("reason"), REASON_LABELS, "reason label"),
            validate_label(item.get("genre"), GENRES, "genre"),
        )
    return labels


@state_locked(lambda *a, **k: OBS)
def reflect(produced, shipped, doc_id=None, *, reason="unspecified", genre="general",
            feedback=None):
    reason = validate_label(reason, REASON_LABELS, "reason label")
    genre = validate_label(genre, GENRES, "genre")
    base = load(DATA / "patterns.json")
    shared, local = learned_layers()
    pats = (base["patterns"] + shared.get("patterns", [])
            + local.get("patterns", []))
    lex = (list(base.get("lexicon", {})) + list(base.get("riders", {}))
           + list(shared.get("lexicon", {})) + list(shared.get("riders", {}))
           + list(local.get("lexicon", {})) + list(local.get("riders", {})))
    obs = load_observations()
    obs.setdefault("false_positives", {})
    obs.setdefault("fix_observations", {})

    today = str(date.today())
    prod_text = required_text(produced, "produced draft")
    ship_text = required_text(shipped, "shipped draft")
    # A vote is one unique edit pair, regardless of filenames or caller-supplied
    # labels. Otherwise three copies of the same before/after text could cross
    # the recurrence threshold by changing only --doc-id. The optional label is
    # accepted for CLI compatibility but never grants another vote.
    doc = hashlib.sha256(
        (prod_text + "\0" + ship_text).encode()).hexdigest()[:16]
    diffs = diff_spans(prod_text, ship_text)
    edit_labels = (load_edit_feedback(feedback, prod_text, ship_text, diffs)
                   if feedback else {})
    caught_words = {word for d in diffs if already_caught(d["span"], pats, lex)
                     for word in norm(d["span"]).split()}

    obs.setdefault("lexicon_candidates", {})
    base_lex = {k.lower() for k in base.get("lexicon", {})}
    base_lex |= {k.lower() for k in base.get("riders", {})}
    for layer in (shared, local):
        base_lex |= {k.lower() for k in layer.get("lexicon", {})}
        base_lex |= {k.lower() for k in layer.get("riders", {})}
    for w in lexicon_candidates(prod_text, ship_text):
        if w in caught_words:
            continue                         # a narrower known phrase already catches it
        if any(w.startswith(t_) or t_.startswith(w) for t_ in base_lex):
            continue                        # the lexicon already speaks to this
        rec = obs["lexicon_candidates"].setdefault(
            w, {"count": 0, "docs": [], "first_seen": today})
        if doc not in rec["docs"]:
            rec["count"] += 1
            rec["docs"].append(doc)
            rec["last_seen"] = today
            bump_count(rec, "reasons", reason)
            bump_count(rec, "genres", genre)

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
    recorded = skipped = agreed = fix_recorded = 0
    fresh = []

    for d in diffs:
        key = norm(d["span"])
        if not key:
            continue
        edit_reason, edit_genre = edit_labels.get(key, (reason, genre))
        caught = already_caught(d["span"], pats, lex)
        why = is_content_specific(d["span"]) or (
            "all function words" if is_all_function_words(d["span"]) else None)
        if caught:
            agreed += 1
        elif why:
            skipped += 1
            continue

        # Learn recurring human fixes for both known tells and tells the meter
        # missed. Keep this evidence separate from detector observations so an
        # existing base pattern can still teach the rewrite pass. A number in a
        # replacement is likely draft-specific fact, not reusable guidance.
        replacement = norm(d.get("replaced_with", ""))
        if (replacement and 1 <= len(replacement.split()) <= MAX_WORDS
                and not re.search(r"\d", d.get("replaced_with", ""))):
            frec = obs["fix_observations"].setdefault(
                key, {"count": 0, "docs": [], "first_seen": today,
                      "last_seen": today, "replacements": {}})
            choice = frec["replacements"].setdefault(
                replacement, {"count": 0, "docs": []})
            if doc not in choice["docs"]:
                choice["docs"].append(doc)
                choice["count"] += 1
                bump_count(choice, "reasons", edit_reason)
                bump_count(choice, "genres", edit_genre)
                frec["count"] = len(set(frec["docs"] + [doc]))
                if doc not in frec["docs"]:
                    frec["docs"].append(doc)
                    bump_count(frec, "reasons", edit_reason)
                    bump_count(frec, "genres", edit_genre)
                frec["last_seen"] = today
                fix_recorded += 1

        if caught:
            continue
        rec = obs["observations"].setdefault(
            key, {"count": 0, "docs": [], "first_seen": today,
                  "last_seen": today, "examples": []})
        if doc in rec["docs"]:
            continue                      # one vote per unique edit pair
        rec["count"] += 1
        rec["docs"].append(doc)
        rec["last_seen"] = today
        bump_count(rec, "reasons", edit_reason)
        bump_count(rec, "genres", edit_genre)
        if len(rec["examples"]) < 3:
            rec["examples"].append(f"…{d['before']} [{d['span']}] {d['after']}…".strip())
        recorded += 1
        fresh.append((key, rec["count"]))

    write_json(OBS, obs, private=True)

    print(f"reflect: {Path(produced).name} → {Path(shipped).name}\n")
    print(f"  {agreed} edit(s) Zero Slop had already flagged — the writer agreed")
    print(f"  {skipped} content-specific cut(s) ignored (figures, proper nouns)")
    print(f"  {recorded} new phrase(s) saved for review")
    print(f"  {fix_recorded} repeated replacement(s) saved")
    print(f"  {len(fps)} flag(s) appeared in text the writer kept\n")
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
        print("  single words under review ("
              f"{LEXICON_PROMOTE_AT} edit pairs needed):")
        for w, n in sorted(lex_ready + lex_pend, key=lambda x: -x[1])[:8]:
            state = "READY" if n >= LEXICON_PROMOTE_AT else f"{n}/{LEXICON_PROMOTE_AT}"
            print(f"    {state:>6}  {w}")
        print()
    ready = [k for k, v in obs["observations"].items() if v["count"] >= PROMOTE_AT]
    if ready:
        print(f"\n  {len(ready)} phrase(s) are ready. Run --promote --apply to "
              "activate them locally, or use --auto-apply with --reflect.")
    else:
        print(f"\n  nothing is ready yet. A phrase needs {PROMOTE_AT} "
              f"content-distinct edit pairs.")
    return 0


@state_locked(lambda *a, **k: OBS,
              lambda *a, **k: LOCAL,
              lambda *a, **k: LOCAL_LOG)
def promote(apply_, cat, weight):
    """Mint safe, recurrent patterns into the private live overlay."""
    obs = load_observations()
    base = load(DATA / "patterns.json")
    shared, learned = learned_layers()
    pats = (base["patterns"] + shared.get("patterns", [])
            + learned.get("patterns", []))
    lex = (list(base.get("lexicon", {})) + list(base.get("riders", {}))
           + list(shared.get("lexicon", {})) + list(shared.get("riders", {}))
           + list(learned.get("lexicon", {})) + list(learned.get("riders", {})))
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

    print(f"promote: {len(eligible)} ready, {len(blocked)} blocked by the "
          f"human-writing check, {len(dup)} already covered\n")
    for key, hit in dup:
        print(f"  covered   {key[:44]!r} ← {hit}")
    for key, rec, rx, hit in blocked:
        print(f"  REJECTED  {key[:44]!r}")
        print(f"            would flag {hit}; not learned at any threshold")
    for key, rec, rx, _ in eligible:
        print(f"  ready     {key[:44]!r}  cut from {rec['count']} edit pairs")
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
        print(f"  ready     lexicon {w!r} cut from {r['count']} edit pairs "
              f"-> rider (context-gated)")

    fix_ready = []
    for key, rec in sorted(obs.get("fix_observations", {}).items()):
        choices = sorted(rec.get("replacements", {}).items(),
                         key=lambda item: (-item[1].get("count", 0), item[0]))
        if not choices:
            continue
        top_fix, top = choices[0]
        runner_up = choices[1][1].get("count", 0) if len(choices) > 1 else 0
        if (top.get("count", 0) < PROMOTE_AT
                or top.get("count", 0) <= runner_up
                or top.get("count", 0) <= rec.get("applied_count", 0)):
            continue
        # A known detector rule has already cleared repository review. A missed
        # tell must clear the same human-corpus gate before it can influence
        # rewrite guidance.
        if not already_caught(key, pats, lex) and fp_gate(to_regex(key), key):
            continue
        fix_ready.append((key, top_fix, top, rec))
        print(f"  ready     fix {key[:32]!r} -> {top_fix[:32]!r} "
              f"from {top['count']} edit pairs")

    if not eligible and not lex_safe and not fix_ready:
        return 0
    if not apply_:
        print(f"\n  dry run. Re-run with --apply to mint {len(eligible)} pattern(s)"
              f", {len(lex_safe)} rider(s), and {len(fix_ready)} fix preference(s).")
        return 0

    today = str(date.today())
    added = []
    for key, rec, rx, _ in eligible:
        # A readable name is the author's phrase. Tracked files get a digest;
        # the readable form stays in ~/.zero-slop/ where the author can see it.
        stem_name = "learned-" + hashlib.sha256(key.encode()).hexdigest()[:10]
        name, i = stem_name, 2
        while name in known:
            name, i = f"{stem_name}-{i}", i + 1
        known.add(name)
        pattern = {"name": name, "cat": cat, "rx": rx, "w": weight,
                   "first_seen": today, "last_confirmed": today,
                   "source": "reflect", "seen_in_docs": rec["count"],
                   "reasons": dict(sorted(rec.get("reasons", {}).items())),
                   "genres": dict(sorted(rec.get("genres", {}).items())),
                   "digest": hashlib.sha256(key.encode()).hexdigest()[:12],
                   # These readable fields stay in the private overlay and let
                   # the rewrite pass learn from repeated human replacements.
                   "source_span": key}
        added.append(pattern)
        rec["promoted"] = today
    learned.setdefault("patterns", []).extend(added)
    for w, r in lex_safe:
        # half the pattern start-weight: a single word convicts far more
        # text than a phrase, so it enters quieter and earns weight back
        learned.setdefault("riders", {})[w] = round(START_WEIGHT / 2, 2)
        r["promoted"] = today
    preferences = {p["source_span"]: p
                   for p in learned.setdefault("fix_preferences", [])}
    for key, preferred, evidence, rec in fix_ready:
        pref = preferences.get(key)
        if pref is None:
            pref = {"source_span": key, "first_seen": rec.get("first_seen", today),
                    "source": "reflect"}
            learned["fix_preferences"].append(pref)
            preferences[key] = pref
        pref.update(preferred_fix=preferred,
                    seen_in_pairs=evidence["count"],
                    reasons=dict(sorted(evidence.get("reasons", {}).items())),
                    genres=dict(sorted(evidence.get("genres", {}).items())),
                    last_confirmed=rec.get("last_seen", today), active=True)
        pref.pop("decayed", None)
        rec["applied_count"] = evidence["count"]
        rec["promoted"] = today
    write_json(LOCAL, learned, private=True)
    write_json(OBS, obs, private=True)
    entry = ""
    if lex_safe:
        entry += (f"\n- {today} — Reflect loop added {len(lex_safe)} "
                  f"context-gated rider(s) ({', '.join(w for w, _ in lex_safe)}) "
                  f"after each was struck from {LEXICON_PROMOTE_AT}+ edit pairs. "
                  f"Entered as riders, not always-on lexicon terms.\n")
    if added:
        entry += (f"\n- {today} — Reflect loop promoted {len(added)} pattern(s) "
                  f"after each was cut from {PROMOTE_AT}+ content-distinct edit pairs "
                  f"({', '.join(a['name'] for a in added)}); "
                  f"{len(blocked)} rejected by the human-writing check. "
                  f"Source documents are not recorded: learning records stay "
                  f"on the machine that produced it.\n")
    if fix_ready:
        entry += (f"\n- {today} — Reflect loop activated or reconfirmed "
                  f"{len(fix_ready)} private rewrite preference(s) after the same "
                  f"replacement recurred in {PROMOTE_AT}+ edit pairs.\n")
    append_log(LOCAL_LOG, entry, private=True)
    print(f"\n  activated {len(added)} pattern(s) and "
          f"{len(fix_ready)} fix preference(s) in {LOCAL}")
    print("  Zero Slop will use this private settings file on its next run")
    print("  run: python3 scripts/calibrate.py --selftest")
    return 0


@state_locked(lambda *a, **k: OBS,
              lambda *a, **k: LOCAL,
              lambda *a, **k: LOCAL_LOG)
def demote(apply_):
    """Act on false-positive evidence: lower the weight of patterns humans overrule.

    A pattern that repeatedly convicts text writers then publish unchanged is
    measuring the tool's taste, not the reader's. Halving its weight is the
    conservative move; a base pattern is never edited in place, it gets a
    lower-weighted override in learned.json, which keeps the base taxonomy
    auditable and the change reversible.
    """
    obs = load_observations()
    base = load(DATA / "patterns.json")
    shared, learned = learned_layers()
    base_by = {p["name"]: p for p in base["patterns"] + shared.get("patterns", [])}
    learned_by = {p["name"]: p for p in learned.get("patterns", [])}

    all_due = [(n, r) for n, r in obs.get("false_positives", {}).items()
               if r["count"] >= PROMOTE_AT and not r.get("demoted")]
    due = [(n, r) for n, r in all_due if n in learned_by or n in base_by]
    retired = [n for n, _ in all_due if n not in learned_by and n not in base_by]
    if retired:
        print(f"demote: ignored {len(retired)} observation(s) for rules no longer installed")
    if not due:
        pend = len(obs.get("false_positives", {}))
        print(f"demote: nothing at threshold ({pend} pattern(s) under observation, "
              f"{PROMOTE_AT} content-distinct kept instances needed)")
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
    write_json(LOCAL, learned, private=True)
    write_json(OBS, obs, private=True)
    append_log(LOCAL_LOG,
               f"\n- {today} — Reflect loop lowered {len(due)} pattern weight(s) "
               f"after writers published the flagged text unchanged in "
               f"{PROMOTE_AT}+ content-distinct edit pairs ({', '.join(n for n, _ in due)}).\n",
               private=True)
    print(f"\n  lowered {len(due)} weight(s) in {LOCAL}")
    return 0


def export(out, yes):
    """Package what was learned for upstream, carrying evidence but never text.

    A span only becomes exportable once it has been cut from PROMOTE_AT
    content-distinct edit pairs. The payload omits context, filenames, paths,
    authors, and precise dates, but the learned span itself is still user prose.
    That is why export prints the complete payload and requires explicit --yes;
    recurrence is a quality gate, not a privacy guarantee or proof of authorship.

    What ships is the same shape as data/learned.json, so a maintainer can read
    the diff before merging. The user reviews the exact payload here first, and
    nothing is written without --yes.
    """
    obs = load_observations()
    payload = {"_comment": "Zero Slop reflect-loop contribution. Contains only "
                           "spans observed in " + str(PROMOTE_AT) + "+ content-distinct "
                           "edit pairs, with no context, filenames or dates finer "
                           "than a month. Spans remain user prose; review before sharing.",
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
    print("  Short recurrent spans only. No surrounding context, filenames, author,\n"
          "  or dates finer than a month. The spans are still user prose; read the\n"
          "  complete payload above before deciding whether to share it.")
    if not yes:
        print(f"\n  Nothing written. Re-run with --yes --out {out} to save it, "
              f"then attach that file to a pull request.")
        return 0
    dest = Path(out).resolve()
    if not is_within(dest, Path.cwd()):
        raise SystemExit(f"refusing to write outside the working directory: {dest}")
    if DATA.resolve() in dest.parents:
        raise SystemExit(f"refusing to write into data/: {dest}")
    if dest.exists():
        raise SystemExit(f"{dest} exists; choose another --out")
    atomic_write_text(dest, json.dumps(payload, indent=1) + "\n", mode=0o600)
    print(f"\n  wrote {out}. Review it once more, then open a PR against "
          f"data/learned.json.")
    return 0


@state_locked(lambda *a, **k: SHARED,
              lambda *a, **k: SHARED_LOG)
def merge(path, apply_, cat, weight):
    """Maintainer side: fold a reviewed contribution into the shared taxonomy.

    Contributions are untrusted input. Every span is re-gated locally against
    this checkout's corpus rather than trusting the sender's claim, because the
    contributor's corpus may be older, smaller, or edited.
    """
    c = load(path)
    if not isinstance(c, dict):
        print("merge: contribution must be a JSON object")
        return 1
    if c.get("schema") != 1:
        print(f"merge: unrecognised contribution schema {c.get('schema')!r}")
        return 1
    if not isinstance(c.get("spans", []), list):
        print("merge: spans must be a list")
        return 1
    if not isinstance(c.get("false_positives", []), list):
        print("merge: false_positives must be a list")
        return 1
    seen_false_positives = set()
    for fp in c.get("false_positives", []):
        if (not isinstance(fp, dict) or not isinstance(fp.get("pattern"), str)
                or not 1 <= len(fp["pattern"]) <= 128
                or not isinstance(fp.get("kept_in_documents"), int)
                or isinstance(fp.get("kept_in_documents"), bool)
                or fp["kept_in_documents"] < 0
                or fp["pattern"] in seen_false_positives):
            print("merge: false_positives contains a malformed or duplicate entry")
            return 1
        seen_false_positives.add(fp["pattern"])
    base, learned = load(DATA / "patterns.json"), load_learned(SHARED, "shared")
    known = {p["name"] for p in base["patterns"] + learned.get("patterns", [])}
    lex = list(base.get("lexicon", {})) + list(learned.get("lexicon", {}))
    pats = base["patterns"] + learned.get("patterns", [])

    accept, reject = [], []
    seen_spans = set()
    for s in c.get("spans", []):
        if not isinstance(s, dict) or not isinstance(s.get("span"), str):
            reject.append((str(s)[:40], "malformed entry")); continue
        if len(s["span"]) > 500:
            reject.append((s["span"][:40], "span exceeds 500 characters")); continue
        n = len(norm(s["span"]).split())
        if not (MIN_WORDS <= n <= MAX_WORDS):
            reject.append((s["span"], f"{n} words, outside {MIN_WORDS}-{MAX_WORDS}")); continue
        documents = s.get("documents")
        if (not isinstance(documents, int) or isinstance(documents, bool)
                or documents < 0):
            reject.append((s["span"], "documents must be a non-negative integer")); continue
        normalized = norm(s["span"])
        if normalized in seen_spans:
            reject.append((s["span"], "duplicate span in contribution")); continue
        seen_spans.add(normalized)
        # Never trust a contributed regex: rebuild it from the bounded span
        # locally, so crafted input cannot smuggle catastrophic backtracking
        # into the meter or the safety-corpus scan.
        s["rx"] = to_regex(s["span"])
        if is_content_specific(s["span"]) or is_all_function_words(s["span"]):
            reject.append((s["span"], "content-specific or all function words")); continue
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
        print(f"  accept  {s['span'][:44]!r}  seen in {s['documents']} edit pairs")
    for fp in c.get("false_positives", []):
        print(f"  note    writers kept text flagged by {fp['pattern']!r} "
              f"in {fp['kept_in_documents']} edit pairs")
    if not accept or not apply_:
        if accept:
            print(f"\n  dry run. Re-run with --apply to add {len(accept)} pattern(s).")
        return 0
    today = str(date.today())
    added = []
    for s in accept:
        stem_name = "contrib-" + hashlib.sha256(s["span"].encode()).hexdigest()[:10]
        name, i = stem_name, 2
        while name in known:
            name, i = f"{stem_name}-{i}", i + 1
        known.add(name)
        added.append({"name": name, "cat": cat, "rx": s["rx"], "w": weight,
                      "first_seen": today, "last_confirmed": today,
                      "source": "contributed", "seen_in_docs": s["documents"],
                      "digest": hashlib.sha256(s["span"].encode()).hexdigest()[:12]})
    learned.setdefault("patterns", []).extend(added)
    write_json(SHARED, learned)
    append_log(SHARED_LOG,
               f"\n- {today} — Merged a reflect-loop contribution: "
               f"{len(added)} pattern(s) ({', '.join(a['name'] for a in added)}), "
               f"{len(reject)} rejected on re-gating against this corpus.\n")
    print(f"\n  merged {len(added)} pattern(s). Run: "
          f"python3 scripts/calibrate.py --selftest")
    return 0


@state_locked(lambda *a, **k: LOCAL)
def confirm(target):
    """Refresh evidence. Patterns that keep firing stay; the rest decay out."""
    p = LOCAL
    d = load_learned(p, "local")
    t = Path(target)
    if not t.exists():
        raise SystemExit(f"confirmation path does not exist: {t}")
    files = [t] if t.is_file() else sorted(
        f for f in t.rglob("*") if f.is_file() and f.suffix.lower() in (".md", ".txt"))
    if not files:
        raise SystemExit(f"confirmation path contains no .md or .txt files: {t}")
    try:
        text = "\n".join(f.read_text() for f in files)
    except (OSError, UnicodeDecodeError) as exc:
        raise SystemExit(f"cannot read confirmation corpus at {t}: {exc}") from exc
    if not text.strip():
        raise SystemExit(f"confirmation corpus contains no text: {t}")
    today, n = str(date.today()), 0
    for pat in d.get("patterns", []):
        try:
            if re.search(pat["rx"], text, re.I):
                pat["last_confirmed"] = today
                pat["confirmations"] = pat.get("confirmations", 0) + 1
                pat.pop("decayed", None)
                n += 1
        except re.error:
            continue
    write_json(p, d, private=True)
    print(f"confirmed {n}/{len(d.get('patterns', []))} learned pattern(s) "
          f"against {len(files)} file(s)")
    return 0


@state_locked(lambda *a, **k: LOCAL)
def decay_local():
    """Reduce stale detector rules and retire stale rewrite preferences."""
    learned = load_learned(LOCAL, "local")
    today, changed, fixes_changed = date.today(), 0, 0
    for pat in learned.get("patterns", []):
        confirmed = pat.get("last_confirmed")
        if not confirmed:
            continue
        try:
            year, month, _ = (int(x) for x in confirmed.split("-"))
        except (TypeError, ValueError):
            continue
        age = (today.year - year) * 12 + today.month - month
        if (age > DECAY_MONTHS and pat.get("w", 0) > 0.5
                and not pat.get("decayed")):
            pat["w"] = round(pat["w"] / 2, 2)
            pat["decayed"] = str(today)
            changed += 1
    for pref in learned.get("fix_preferences", []):
        confirmed = pref.get("last_confirmed")
        if not confirmed or not pref.get("active", True):
            continue
        try:
            year, month, _ = (int(x) for x in confirmed.split("-"))
        except (AttributeError, TypeError, ValueError):
            continue
        age = (today.year - year) * 12 + today.month - month
        if age > DECAY_MONTHS:
            pref["active"] = False
            pref["decayed"] = str(today)
            fixes_changed += 1
    if changed or fixes_changed or LOCAL.exists():
        write_json(LOCAL, learned, private=True)
    print(f"decayed {changed} local pattern(s) and retired {fixes_changed} "
          f"rewrite preference(s) unconfirmed for over {DECAY_MONTHS} months")
    return 0


def all_preferences(learned):
    """Read current and prerelease preference shapes without mutating either."""
    preference_count = (len(learned.get("fix_preferences", []))
                        + len(learned.get("patterns", [])))
    if preference_count > MAX_RETRIEVAL_PREFERENCES:
        raise SystemExit(
            f"learning overlay exceeds the {MAX_RETRIEVAL_PREFERENCES}-record "
            "retrieval limit; archive or review stale evidence first"
        )
    rows = [{"when": p["source_span"], "prefer": p["preferred_fix"],
             "edit_pairs": p.get("seen_in_pairs", 0),
             "reasons": p.get("reasons", {}), "genres": p.get("genres", {})}
            for p in learned.get("fix_preferences", [])
            if p.get("active", True) and p.get("source_span")
            and p.get("preferred_fix")]
    seen = {row["when"] for row in rows}
    rows.extend({"when": p["source_span"], "prefer": p["preferred_fix"],
                 "edit_pairs": p.get("fix_seen_in_docs", 0),
                 "reasons": p.get("reasons", {}), "genres": p.get("genres", {})}
                for p in learned.get("patterns", [])
                if p.get("source_span") not in seen and p.get("preferred_fix"))
    return rows


def retrieval_tokens(text):
    return {token for token in norm(text).split()
            if (len(token) > 2 or token.isdigit()) and token not in STOPWORDS}


def retrieve_preferences(text, reason=None, genre=None, limit=5, learned=None):
    """Retrieve relevant local fixes with a deterministic lexical rank.

    Similarity is source-token coverage, not a probability. A result must share
    at least half of its content-bearing source tokens with the current draft.
    Reason and genre labels narrow and rerank that evidence; they never permit a
    lexically unrelated replacement to surface.
    """
    if not isinstance(text, str) or not text.strip():
        return []
    if len(text) > MAX_RETRIEVAL_TEXT:
        raise SystemExit(f"retrieval input exceeds {MAX_RETRIEVAL_TEXT} characters")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_RETRIEVAL_RESULTS:
        raise SystemExit(f"retrieval limit must be 1-{MAX_RETRIEVAL_RESULTS}")
    if reason is not None:
        validate_label(reason, REASON_LABELS, "reason label")
    if genre is not None:
        validate_label(genre, GENRES, "genre")
    if learned is None:
        learned = load_learned(LOCAL, "local")
    query_norm = " ".join(norm(text).split())
    query_tokens = retrieval_tokens(text)
    ranked = []
    for row in all_preferences(learned):
        source_norm = " ".join(norm(row["when"]).split())
        source_tokens = retrieval_tokens(row["when"])
        if not source_tokens:
            continue
        exact = bool(source_norm and re.search(
            r"(?<!\w)" + re.escape(source_norm) + r"(?!\w)", query_norm
        ))
        similarity = 1.0 if exact else len(source_tokens & query_tokens) / len(source_tokens)
        if similarity < 0.5:
            continue
        reasons, genres = row.get("reasons", {}), row.get("genres", {})
        if reason is not None and reasons and reason not in reasons:
            continue
        if genre is not None and genres and genre not in genres:
            continue
        reason_match = bool(reason is not None and reasons.get(reason, 0))
        genre_match = bool(genre is not None and genres.get(genre, 0))
        recurrence = min(0.05, 0.01 * row.get("edit_pairs", 0))
        rank_score = similarity + 0.15 * reason_match + 0.05 * genre_match + recurrence
        ranked.append({**row, "similarity": round(similarity, 3),
                       "rank_score": round(rank_score, 3),
                       "reason_match": reason_match, "genre_match": genre_match})
    ranked.sort(key=lambda row: (-row["rank_score"], -row["edit_pairs"],
                                 row["when"], row["prefer"]))
    return ranked[:limit]


def guide(as_json=False, target=None, reason=None, genre=None, limit=5):
    """Return private rewrite preferences learned from repeated human edits."""
    learned = load_learned(LOCAL, "local")
    if target is None:
        rows = all_preferences(learned)
    else:
        text = required_text(target, "retrieval draft")
        rows = retrieve_preferences(text, reason=reason, genre=genre,
                                    limit=limit, learned=learned)
    if as_json:
        print(json.dumps({"result_kind": "retrieved_rewrite_preferences",
                          "calibrated_probability": False,
                          "rewrite_preferences": rows}, indent=1))
    elif not rows:
        print("rewrite guidance: no relevant recurring local replacement preferences")
    else:
        print("rewrite guidance retrieved from recurring local edits:")
        for row in rows:
            print(f"  when {row['when']!r}, consider {row['prefer']!r} "
                  f"({row['edit_pairs']} edit pairs)")
        print("  These are suggestions, not automatic replacements. Preserve meaning and facts.")
    return 0


def build_voice(name, sample_path):
    """Build a private exemption profile for existing watchlist terms.

    This exact-term scan covers only the scorer's current lexicon and riders.
    It does not infer arbitrary phrases, cadence, syntax, humor, tone, or a
    complete writing style. The resulting profile changes scoring only when
    the caller explicitly selects it with ``--voice NAME``.
    """
    import slopscore
    name = safe_voice_name(name)
    base = slopscore.load_patterns()
    terms = list(base.get("lexicon", {})) + list(base.get("riders", {}))
    src = Path(sample_path)
    if not src.exists():
        raise SystemExit(f"voice sample path does not exist: {src}")
    files = [src] if src.is_file() else sorted(
        f for f in src.rglob("*") if f.is_file() and f.suffix.lower() in (".md", ".txt"))
    if not files:
        raise SystemExit(f"voice sample contains no .md or .txt files: {src}")
    try:
        blob = " ".join(f.read_text() for f in files).lower()
    except (OSError, UnicodeDecodeError) as exc:
        raise SystemExit(f"cannot read voice sample at {src}: {exc}") from exc
    if not blob.strip():
        raise SystemExit(f"voice sample contains no text: {src}")
    keep = sorted({term for term in terms
                   if re.search(r"\b" + re.escape(term.lower()) + r"\b", blob)})
    prof = {"_comment": f"Named scoring profile for {name}. Exact matches for "
                        "existing lexicon or rider terms found at least once "
                        "in the supplied sample are "
                        "zero-weighted only when this profile is selected with "
                        "--voice NAME. This does not model the author's full style. "
                        "Derived by learn.py --voice; edit freely.",
            "keep": keep, "mute": []}
    dest = slopscore._voice_path(name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with file_locks([dest]):
        atomic_write_text(dest, json.dumps(prof, indent=1) + "\n", mode=0o600)
    print(f"wrote {dest}")
    print(f"  {len(keep)} existing watchlist terms found; scoring ignores them "
          f"only when this profile is selected: {', '.join(keep[:12])}"
          f"{'...' if len(keep) > 12 else ''}")
    print("  this profile does not learn cadence, syntax, humor, tone, arbitrary "
          "phrases, or full writing style")
    print(f"  use it: python3 scripts/slopscore.py --voice {name} draft.md")
    return 0


def stats():
    base = load(DATA / "patterns.json")
    shared, local = learned_layers()
    obs = load_observations().get("observations", {})
    shared_patterns = shared.get("patterns", [])
    local_patterns = local.get("patterns", [])
    lp = shared_patterns + local_patterns
    allp = base["patterns"] + lp
    prov = sum(1 for p in allp if p.get("first_seen"))
    pending = {k: v for k, v in obs.items() if not v.get("promoted")}
    ready = sum(1 for v in pending.values() if v["count"] >= PROMOTE_AT)
    corpus = corpus_files()
    print(f"  phrase rules  {len(allp)} ({len(base['patterns'])} built in, "
          f"{len(shared_patterns)} shared, {len(local_patterns)} local)")
    print(f"  dated rules   {prov}/{len(allp)} — old rules can retire"
          if prov == len(allp) else
          f"  dated rules   {prov}/{len(allp)} — undated rules cannot retire automatically")
    src = {}
    for p in lp:
        k = p.get("source", "manual")
        src[k] = src.get(k, 0) + 1
    print(f"  learned via   {', '.join(f'{k}={v}' for k, v in sorted(src.items())) or 'nothing yet'}")
    print(f"  under review  {len(pending)} phrase(s), {ready} ready after "
          f"{PROMOTE_AT} matching edit pairs")
    print(f"  re-confirmed  {sum(1 for p in lp if p.get('confirmations'))} pattern(s) "
          f"have fired again since being added")
    active_fixes = sum(1 for p in local.get("fix_preferences", [])
                       if p.get("active", True))
    print(f"  fix memory    {active_fixes} active recurring local replacement "
          "preference(s)")
    print(f"  safety set    {len(corpus)} human samples every new phrase rule must clear")
    print(f"  private rules {LOCAL} (loaded for every writing check)")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--reflect", action="store_true",
                    help="record what the writer changed about the skill's output")
    ap.add_argument("--produced", help="what the skill returned")
    ap.add_argument("--shipped", help="what the writer actually published")
    ap.add_argument("--doc-id", help="optional diagnostic label; duplicate edit "
                                     "content still counts as one vote")
    ap.add_argument("--reason", help="editorial reason label for --reflect, or a "
                                     "retrieval filter for --guide --for")
    ap.add_argument("--genre", help="genre label for --reflect or --guide --for")
    ap.add_argument("--feedback", metavar="JSON",
                    help="optional source-bound per-edit reason labels for --reflect")
    ap.add_argument("--promote", action="store_true",
                    help="mint patterns from observations that cleared threshold")
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument("--auto-apply", action="store_true",
                    help="after --reflect, activate/demote locally when all gates pass")
    ap.add_argument("--cat", default="reflect-learned")
    ap.add_argument("--weight", type=bounded_weight, default=START_WEIGHT)
    ap.add_argument("--confirm", metavar="PATH")
    ap.add_argument("--demote", action="store_true",
                    help="lower weights on patterns writers repeatedly overruled")
    ap.add_argument("--export", action="store_true",
                    help="package learnings for upstream, with no source text")
    ap.add_argument("--out", default="zero-slop-contribution.json")
    ap.add_argument("--yes", action="store_true", help="confirm writing the export")
    ap.add_argument("--merge", metavar="FILE",
                    help="maintainer: fold a reviewed contribution in, re-gated locally")
    ap.add_argument("--voice", metavar="NAME",
                    help="build a private scoring profile from exact watchlist matches")
    ap.add_argument("--from", dest="sample", metavar="PATH",
                    help="the writing sample for --voice")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--guide", action="store_true",
                    help="show recurring private rewrite preferences")
    ap.add_argument("--for", dest="guide_target", metavar="DRAFT",
                    help="with --guide, retrieve only preferences relevant to this draft")
    ap.add_argument("--limit", type=int, default=5,
                    help=f"maximum retrieved preferences (1-{MAX_RETRIEVAL_RESULTS})")
    ap.add_argument("--json", action="store_true", help="machine-readable --guide output")
    ap.add_argument("--decay", action="store_true",
                    help="halve stale patterns in the private live overlay")
    a = ap.parse_args()

    if a.voice:
        if not a.sample:
            ap.error("--voice needs --from <file-or-dir of your writing>")
        return build_voice(a.voice, a.sample)
    if a.stats:
        return stats()
    if a.guide:
        if (a.reason or a.genre) and not a.guide_target:
            ap.error("--reason and --genre need --guide --for <draft>")
        return guide(a.json, a.guide_target, a.reason, a.genre, a.limit)
    if a.decay:
        return decay_local()
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
        result = reflect(a.produced, a.shipped, a.doc_id,
                         reason=a.reason or "unspecified",
                         genre=a.genre or "general", feedback=a.feedback)
        if a.auto_apply:
            promote(True, a.cat, a.weight)
            demote(True)
            decay_local()
        return result
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
