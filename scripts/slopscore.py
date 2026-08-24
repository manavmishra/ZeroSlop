#!/usr/bin/env python3
"""slopscore — check writing for common AI-style patterns.

The 0-to-100 writing score covers familiar phrases, sentence variety,
readability, formatting, and tone. Lower is better. The score describes the
writing; it does not identify who wrote it, decide whether the ideas are useful,
or check whether every claim is true. Zero Slop handles those questions in its
editorial review.

Usage (runnable from any cwd; data resolves relative to this script):
    python3 slopscore.py <file>            # pretty report
    python3 slopscore.py --json <file>     # machine-readable
    python3 slopscore.py --dna a.md b.md   # show what changed
    python3 slopscore.py --fidelity a.md b.md  # facts kept? anything added?
    cat text | python3 slopscore.py        # stdin
    python3 slopscore.py --explain <file>  # report + reasons + line-by-line map
    python3 slopscore.py --heatmap <file>  # line-by-line map only
    python3 slopscore.py --portfolio <dir> # repeated wording across related drafts
    python3 slopscore.py --formal <file>   # use the rules for professional writing

The phrase lists live beside this script in ../data/patterns.json and
../data/learned.json. Editing those files requires no code change.
"""
import bisect
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
VOICE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")


def _voice_path(name):
    """Resolve a profile name without letting it become a filesystem path."""
    if not VOICE_NAME.fullmatch(name or "") or name in (".", ".."):
        raise ValueError(
            "voice name must be 1-64 letters, digits, dots, underscores, or hyphens"
        )
    root = (HOME / "voices").resolve()
    path = (root / f"{name}.json").resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:  # defense in depth if the name rule changes
        raise ValueError("voice profile resolves outside the voice directory") from exc
    return path


def _merge_learned(base, learned_path):
    """Merge one validated layer; malformed entries never break scoring."""
    if not learned_path.exists():
        return
    try:
        learned = json.loads(learned_path.read_text())
        if not isinstance(learned, dict):
            raise ValueError("learned data must be an object")
        raw_patterns = learned.get("patterns", [])
        if not isinstance(raw_patterns, list):
            raise ValueError("learned patterns must be a list")
        valid_patterns = []
        for q in raw_patterns:
            if not isinstance(q, dict):
                continue
            name, rx, weight, category = (q.get("name"), q.get("rx"),
                                          q.get("w"), q.get("cat"))
            if (not isinstance(name, str) or not 1 <= len(name) <= 128
                    or not isinstance(category, str) or not 1 <= len(category) <= 64
                    or not isinstance(rx, str)
                    or not isinstance(weight, (int, float))
                    or isinstance(weight, bool)
                    or not math.isfinite(weight) or not 0 <= weight <= 10
                    or len(rx) > 2000
                    or re.search(r"\\[1-9]|\(\?<*[=!]|\([^()]*[+*][^()]*\)[+*]", rx)):
                continue
            try:
                re.compile(rx)
            except re.error:
                continue
            valid_patterns.append(q)

        # Later layers win by name. This is how a private false-positive update
        # can lower one shared weight without editing the installed taxonomy.
        by_name = {q["name"]: q for q in base["patterns"]}
        order = [q["name"] for q in base["patterns"]]
        for q in valid_patterns:
            if q["name"] not in by_name:
                order.append(q["name"])
            by_name[q["name"]] = q
        base["patterns"] = [by_name[name] for name in order]
        for field in ("lexicon", "riders"):
            raw = learned.get(field, {})
            if not isinstance(raw, dict):
                continue
            clean = {term: weight for term, weight in raw.items()
                     if isinstance(term, str) and 1 <= len(term) <= 80
                     and isinstance(weight, (int, float))
                     and not isinstance(weight, bool)
                     and math.isfinite(weight) and 0 <= weight <= 10}
            base.setdefault(field, {}).update(clean)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError, ValueError, TypeError):
        return


def load_patterns(voice=None):
    base = json.loads((DATA_DIR / "patterns.json").read_text())
    _merge_learned(base, DATA_DIR / "learned.json")       # reviewed, shared
    _merge_learned(base, HOME / "learned.json")           # private, live
    if voice:
        _apply_voice(base, voice)
    return base


def _apply_voice(base, name):
    """Apply one explicitly selected private scoring profile.

    ``keep`` zero-weights existing lexicon and rider terms. ``mute`` lists the
    labels of existing patterns, but the sample-based builder does not populate
    it. This changes only the local score; it does not infer or model the
    writer's full style, and an unselected profile has no effect.
    """
    prof_path = _voice_path(name)
    if not prof_path.exists():
        return
    try:
        prof = json.loads(prof_path.read_text())
        if not isinstance(prof, dict):
            return
        keep_raw, mute_raw = prof.get("keep", []), prof.get("mute", [])
        if not isinstance(keep_raw, list) or not isinstance(mute_raw, list):
            return
    except (json.JSONDecodeError, UnicodeDecodeError, OSError, TypeError):
        return
    keep = {k.lower() for k in keep_raw if isinstance(k, str)}
    for term in list(base.get("lexicon", {})):
        if term.lower() in keep:
            base["lexicon"][term] = 0
    for term in list(base.get("riders", {})):
        if term.lower() in keep:
            base["riders"][term] = 0
    for pat in base["patterns"]:
        if pat["name"] in {m for m in mute_raw if isinstance(m, str)}:
            pat["w"] = 0


SENT_SPLIT = re.compile(r"(?<=[.!?])[\")”’]?\s+(?=[A-Z“\"(0-9])")
WORD = re.compile(r"[A-Za-z’']+")


def strip_noise(text):
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    # Markdown table rules are layout syntax, not repeated dashes in prose.
    # Leave the table's words available to the language and rhythm checks, but
    # remove delimiter rows such as ``|---|---:|`` before punctuation scoring.
    text = re.sub(
        r"(?m)^[ \t]*\|?[ \t]*:?-{3,}:?[ \t]*"
        r"(?:\|[ \t]*:?-{3,}:?[ \t]*)+\|?[ \t]*$",
        " ",
        text,
    )
    # Inline `code` spans still render as visible prose, so their words are
    # scored; only the backticks go. Fenced blocks are genuinely code.
    text = re.sub(r"`([^`\n]*)`", r"\1", text)
    # URLs are otherwise noise, but a model-specific tracking parameter is a
    # machine artifact in its own right. Preserve only the artifact token so
    # ordinary URL text cannot affect prose rhythm or vocabulary.
    text = re.sub(
        r"https?://\S+",
        lambda m: " " + " ".join(re.findall(
            r"utm_source=(?:chatgpt(?:\.com)?|openai)", m.group(0), re.I
        )) + " ",
        text,
    )
    return text


def _sentence_spans(text):
    """(start, end) spans of ``sentences(text)`` in ``text`` coordinates.

    Newlines inside a paragraph flatten to spaces, which preserves length, so
    a span's slice differs from its sentence string only by that replacement.
    Rider hits are sentence-scoped but dedup against pattern hits needs
    document offsets; this keeps one sentence definition for both.
    """
    spans = []
    start = 0
    breaks = [m.span() for m in re.finditer(r"\n\s*\n", text)]
    for para_end, next_start in breaks + [(len(text), len(text))]:
        flat = text[start:para_end].replace("\n", " ")
        prev = 0
        cuts = [m.span() for m in SENT_SPLIT.finditer(flat)]
        for cut_start, cut_end in cuts + [(len(flat), len(flat))]:
            seg = flat[prev:cut_start]
            core = seg.strip()
            if len(WORD.findall(core)) >= 2:
                lead = len(seg) - len(seg.lstrip())
                spans.append((start + prev + lead,
                              start + prev + lead + len(core)))
            prev = cut_end
        start = next_start
    return spans


def sentences(text):
    return [text[a:b].replace("\n", " ") for a, b in _sentence_spans(text)]


def _merge_spans(spans):
    merged = []
    for s, e in sorted(spans):
        if merged and s <= merged[-1][1]:
            if e > merged[-1][1]:
                merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return merged


def _span_covered(span, merged):
    """True if [s, e) intersects any interval in a merged, sorted list."""
    s, e = span
    i = bisect.bisect_left(merged, (e,))
    return i > 0 and merged[i - 1][1] > s


def cv(values):
    if len(values) < 2:
        return 1.0
    m = sum(values) / len(values)
    if m == 0:
        return 1.0
    var = sum((v - m) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(var) / m


def score_text(text, data, formal=False):
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    raw = text
    text = strip_noise(text)
    words = WORD.findall(text)
    n_words = len(words)
    word_den = max(n_words, 1)
    sent_spans = _sentence_spans(text)
    sents = [text[a:b].replace("\n", " ") for a, b in sent_spans]
    hits = []
    pattern_spans = []  # (start, end, rx) per pattern hit, for dedup below

    # 1. Pattern tells (regex, weighted)
    for p in data["patterns"]:
        if not p.get("w"):
            continue
        for m in re.finditer(p["rx"], text, re.I | (re.M if p.get("m") else 0)):
            hits.append({
                "cat": p["cat"], "name": p["name"], "w": p["w"],
                "quote": m.group(0)[:90].strip(),
            })
            pattern_spans.append((m.start(), m.end(), p["rx"]))

    # 2. Lexicon. Two tiers, because context decides. Always-on terms
    # ("delve", "tapestry") almost never appear in honest prose. Rider terms
    # ("robust", "landscape", "elevated") are ordinary technical vocabulary
    # and only count when a marketing-register trigger shares their sentence —
    # so "elevated write volume" in a runbook is silent while "elevate your
    # brand with our seamless platform" fires. Sentence-scoped, not global.
    #
    # A term a pattern already charges is the same evidence counted twice —
    # "is a testament to" must convict the phrase once, not the phrase plus
    # the word. The pattern owns the term when its regex writes the term out
    # ("testament" in puffery-testament) or matches the term's own text
    # ("game.?chang" on "game-changing"); an independent tell that merely
    # lands inside another tell's span — a lexicon word inside a
    # rhetorical-structure match — still counts. Overlapping lexicon stems
    # ("game-chang", "game-changing") collapse to one hit the same way.
    claimed = _merge_spans([(s, e) for s, e, _ in pattern_spans])

    def _pattern_owns(span, term, matched):
        if not _span_covered(span, claimed):
            return False
        s, e = span
        return any(ps < e and s < pe
                   and (term in rx.lower() or re.search(rx, matched, re.I))
                   for ps, pe, rx in pattern_spans)

    candidates = []
    for term, w in data["lexicon"].items():
        if not w:
            continue
        for m in re.finditer(r"\b" + re.escape(term) + r"\w*", text, re.I):
            if _pattern_owns(m.span(), term, m.group(0)):
                continue
            candidates.append((m.start(), m.end(), term, w, m.group(0).lower()))
    candidates.sort(key=lambda c: (c[0], -c[1]))
    last_end = 0
    for s, e, term, w, quote in candidates:
        if s < last_end:
            continue
        last_end = e
        hits.append({"cat": "lexicon", "name": term, "w": w, "quote": quote})
    riders, triggers = data.get("riders", {}), data.get("rider_triggers", [])
    if riders:
        for (a, _), sent in zip(sent_spans, sents):
            sl = sent.lower()
            if not any(t in sl for t in triggers):
                continue
            for term, w in riders.items():
                if not w:
                    continue
                for m in re.finditer(r"\b" + re.escape(term) + r"\w*", sent, re.I):
                    if _pattern_owns((a + m.start(), a + m.end()),
                                     term, m.group(0)):
                        continue
                    hits.append({"cat": "rider", "name": term, "w": w,
                                 "quote": m.group(0).lower()})

    pattern_weight = sum(h["w"] for h in hits)
    # Density window is floored at 60 words (a single tell in a 7-word tweet
    # must not read as 100/100) and the long-text dilution is bounded by also
    # tracking absolute weight: a 2000-word piece cannot hide 20 tells. The
    # absolute floor scales with length past 1,000 words, because a fixed
    # floor convicts on sheer accumulation — weight 42 anywhere meant a
    # book-length text with one mild tell every couple thousand words scored
    # the same as a tell-dense post and could never pass the gate.
    tell_density = 100.0 * pattern_weight / max(n_words, 60)
    weight_floor = min(pattern_weight / 3.0, 14.0) * min(1.0, 1000.0 / word_den)
    tell_density = max(tell_density, weight_floor)

    # 3. Rhythm: burstiness = coefficient of variation of sentence lengths.
    # Human prose ~0.55-0.75; machine prose clusters ~0.25-0.45.
    slens = [len(WORD.findall(s)) for s in sents]
    burstiness = cv(slens)
    # Short texts give unstable CV estimates — scale the penalty in by length.
    length_conf = min(1.0, len(sents) / 8.0)
    uniformity_penalty = 0.0 if formal else (
        max(0.0, (0.42 - burstiness)) * 35 * length_conf)

    # 4. Punctuation / formatting densities (per 100 words)
    # Fenced code is not prose. Counting CLI flags such as `--gate` as dash-heavy
    # style made technical READMEs look machine-written, so formatting channels
    # operate on the same code-stripped text as the language channels.
    emdash = 100.0 * len(re.findall(r"—|--", text)) / max(n_words, 120)
    # Capped: dash-heavy but otherwise excellent prose (Lincoln, Dickinson)
    # must not be convicted on punctuation alone.
    emdash_penalty = min(max(0.0, emdash - 0.6) * 6, 8.0)
    emoji = len(re.findall(r"[\U0001F300-\U0001FAFF✅✨⚡\U0001F449\U0001F447\U0001F680\U0001F525]", text))
    emoji_penalty = min(emoji * 2.0, 12)
    # Bold as mid-sentence emphasis is the tell (WP:AICATCH); bold used as a
    # label at the start of a line/list item is ordinary document formatting.
    bold = 0
    for match in re.finditer(r"\*\*[^*\n]{2,60}\*\*", raw):
        prefix = raw[raw.rfind("\n", 0, match.start()) + 1:match.start()]
        if re.match(r"[\s>*#-]*(?:\d+\.\s*)?$", prefix):
            continue
        if re.match(r"[ \t]*\|", prefix):
            continue  # bold totals in a Markdown table are ordinary layout
        bold += 1
    bold_penalty = min(max(0, bold - 1) * 1.5, 9)
    hashtags = len(re.findall(r"(?<!\S)#\w+", text))
    hashtag_penalty = min(hashtags * 1.2, 8)

    # 5. Register: contraction scarcity in casual genres reads machine-formal.
    contractions = len(re.findall(r"\b\w+[’'](?:t|s|re|ve|ll|d|m)\b", text))
    contraction_rate = 100.0 * contractions / word_den
    formality_penalty = 0.0 if formal else (
        3.0 if contraction_rate < 0.4 and n_words > 80 else 0.0)

    # 6. Followability: density without accessibility reads machine-compressed,
    # not expert. Signals: noun-phrase chains (many commas, no verbs between),
    # heavy polysyllabic ratio, and overlong sentences. Formal genres exempt
    # (their register legitimately runs denser).
    poly_ratio = sum(1 for w in words if len(w) >= 9) / word_den
    chain_frac = sum(1 for s in sents if s.count(",") >= 4) / max(len(sents), 1)
    overlong_frac = sum(1 for L in slens if L > 38) / max(len(slens), 1)
    followability_penalty = 0.0 if formal else min(
        max(0.0, poly_ratio - 0.14) * 40 + chain_frac * 9 + overlong_frac * 7,
        12.0)

    # Clusters convict, singles don't. Em-dash density and missing contractions
    # are stylistic habits, not evidence on their own — 19th-century oratory and
    # plenty of excellent formal prose trip both. So corroborate them against
    # lexical evidence: with no tells present they contribute little. Emoji and
    # hashtags stay at full strength (they convict alone), and burstiness is an
    # independent statistical signal, so neither is scaled. Bold emphasis rides
    # in the stylistic sum below: heavy mid-sentence bold is a real tell in
    # company, but on its own it is a formatting habit, and seven bold spans
    # with zero other evidence must not reach the gate.
    # The floor was 0.45, which handed style 45% weight on text with no lexical
    # evidence whatsoever. Measured against genuine human technical prose that
    # convicted 5 of 8 documents: AGENTS.md scored 59.2 on one weight-2.5 hit in
    # 392 words. Corroboration has to be earned, so the floor is now low enough
    # that dashes and formal register alone cannot carry a verdict.
    corroboration = min(1.0, 0.10 + tell_density / 2.5)
    stylistic = ((emdash_penalty + formality_penalty) * corroboration
                 + uniformity_penalty + followability_penalty + bold_penalty)
    # No lexical evidence at all means no cluster, and the rule is that
    # clusters convict. Style alone (dashes, long sentences, formal register,
    # even rhythm, bold-heavy emphasis) describes plenty of excellent human
    # prose — 19th-century oratory, dense technical writing — so with zero
    # emoji or hashtag spam, style can raise suspicion but must never convict.
    # The cap releases gradually as lexical evidence accumulates. A step
    # release at density 1.5 rebuilt the cliff this clamp exists to prevent:
    # one weight-1 arrow in a 66-word note crossed the threshold and unlocked
    # the whole stylistic budget in a single jump, 20 to 87. Interpolating the
    # cap between density 1.5 and 4 means each increment of lexical evidence
    # buys a proportional amount of style; a lone weak hit still charges its
    # own density, but never someone else's category.
    if emoji == 0 and hashtags == 0:
        release = min(1.0, max(0.0, (tell_density - 1.5) / 2.5))
        stylistic = min(stylistic, 3.5 + release * max(0.0, stylistic - 3.5))
    evidence = (
        tell_density * 1.15
        + stylistic
        + emoji_penalty
        + hashtag_penalty
    )
    ai_likelihood = round(100 / (1 + math.exp(-(evidence - 9.0) / 4.0)), 1)

    cats = {}
    for h in hits:
        cats[h["cat"]] = round(cats.get(h["cat"], 0) + h["w"], 1)

    return {
        "score_kind": "heuristic_surface_meter",
        "calibrated_probability": False,
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


# ── cross-draft portfolio channel ────────────────────────────────────────────
# A single draft cannot reveal that ten unrelated posts all begin with the same
# five words. The Slop Index measures opener repetition across repeated samples
# of one prompt, and Shaib et al. (arXiv:2509.19163) identify repetition and
# templatedness as separate slop dimensions. This channel reports that evidence
# across a directory of drafts. It deliberately stays outside the 0–100 score:
# the current corpus is too small to calibrate a safe universal weight, and
# repeated domain language can be legitimate.
PORTFOLIO_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "has", "have", "he", "her", "his", "i", "in", "is", "it", "its", "of",
    "on", "or", "our", "she", "that", "the", "their", "they", "this", "to",
    "was", "we", "were", "will", "with", "you", "your",
}


def portfolio_metrics(documents, opener_words=5, phrase_words=5):
    """Return interpretable repetition evidence across several drafts.

    ``documents`` is an iterable of ``(name, text)`` pairs. Exact opener and
    phrase matches are normalized to lowercase words. The result is a
    diagnostic, not a score or authorship verdict.
    """
    if (not isinstance(opener_words, int) or isinstance(opener_words, bool)
            or opener_words < 1 or not isinstance(phrase_words, int)
            or isinstance(phrase_words, bool) or phrase_words < 1):
        raise ValueError("opener_words and phrase_words must be positive integers")
    docs, names = [], set()
    for name, text in documents:
        name = str(name)
        if name in names:
            raise ValueError(f"duplicate document name: {name}")
        if not isinstance(text, str):
            raise ValueError(f"document {name!r} is not text")
        names.add(name)
        docs.append((name, WORD.findall(strip_noise(text).lower())))
    out = {
        "score_kind": "portfolio_template_diagnostic",
        "calibrated_probability": False,
        "measured": len(docs) >= 3,
        "n_documents": len(docs),
        "opener_words": opener_words,
        "phrase_words": phrase_words,
        "repeated_openers": [],
        "shared_phrases": [],
        "reason": "",
    }
    if len(docs) < 3:
        out["reason"] = "needs at least 3 drafts"
        return out

    opener_docs = {}
    phrase_docs = {}
    for name, words in docs:
        if len(words) >= opener_words:
            opener = " ".join(words[:opener_words])
            opener_docs.setdefault(opener, set()).add(name)
        seen = set()
        for i in range(max(0, len(words) - phrase_words + 1)):
            gram_words = words[i:i + phrase_words]
            # Common glue shared by several documents is not a useful template.
            if all(w in PORTFOLIO_STOPWORDS for w in gram_words):
                continue
            seen.add(" ".join(gram_words))
        for phrase in seen:
            phrase_docs.setdefault(phrase, set()).add(name)

    repeated = [(opener, sorted(names)) for opener, names in opener_docs.items()
                if len(names) >= 2]
    repeated.sort(key=lambda item: (-len(item[1]), item[0]))
    repeated_opener_texts = {opener for opener, _ in repeated}
    shared = [(phrase, sorted(names)) for phrase, names in phrase_docs.items()
              if len(names) >= 2 and phrase not in repeated_opener_texts]
    shared.sort(key=lambda item: (-len(item[1]), item[0]))
    out["repeated_openers"] = [
        {"text": opener, "documents": names, "document_count": len(names)}
        for opener, names in repeated
    ]
    out["shared_phrases"] = [
        {"text": phrase, "documents": names, "document_count": len(names)}
        for phrase, names in shared[:20]
    ]
    return out


def render_portfolio(result):
    """Plain-language portfolio report for the command-line interface."""
    out = ["", "  RELATED DRAFTS · repeated wording", "",
           "  This check is separate from the 0-to-100 writing score."]
    if not result["measured"]:
        return out + [f"  Not checked: {result['reason']}.", ""]
    out.append(f"  Drafts checked: {result['n_documents']}")
    if result["repeated_openers"]:
        out.append("  repeated openings:")
        for row in result["repeated_openers"][:8]:
            out.append(f"    {row['document_count']:>2} drafts  {row['text']!r}")
    else:
        out.append("  repeated openings: none")
    if result["shared_phrases"]:
        out.append("  shared five-word phrases:")
        for row in result["shared_phrases"][:8]:
            out.append(f"    {row['document_count']:>2} drafts  {row['text']!r}")
    else:
        out.append("  shared five-word phrases: none")
    return out + ["  Suggestion: vary repeated openings and stock wording while keeping facts and voice.", ""]



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
    # Lists and dialogue were excluded from ``prose`` above, so they must also be
    # excluded from the fragment-run half of the verdict. Otherwise three short
    # bullets after an ordinary post can manufacture a broetry failure.
    frag, run, best = [len(WORD.findall(s))
                       for s in sentences("\n\n".join(prose))], 0, 0
    for L in frag:
        run = run + 1 if L < 7 else 0
        best = max(best, run)
    out.update(measured=True, solo_frac=round(solo / len(prose), 2),
               max_fragment_run=best, reason="")
    out["broetry"] = out["solo_frac"] >= SHAPE_SOLO_THRESHOLD and best >= 3
    return out


def band(score):
    if score < 25:
        return "clear"
    if score < 50:
        return "some issues"
    if score < 75:
        return "needs work"
    return "major rewrite"


# Plain-English names and fixes, keyed by pattern category. The internal
# category is a maintenance label; a writer needs to know what it is and what
# to do instead.
CAT_MEANING = {
    "linkedin":      ("canned LinkedIn phrase", "say what happened without the stock opening"),
    "marketing":     ("promotional language", "name what it does; cut the adjectives"),
    "scaffolding":   ("empty setup", "delete the opening and keep the point"),
    "hedging":       ("empty hedge", "commit, or cut the sentence"),
    "lexicon":       ("overused AI-style word", "use the plain word"),
    "rider":         ("buzzword used as promotion", "use the plain word, or drop the hype around it"),
    "performed":     ("staged sincerity", "say the thing instead of announcing it"),
    "contrast":      ("repeated 'not this, but that' formula", "state the point directly"),
    "puffery":       ("unearned significance", "state the fact, let the reader judge"),
    "drama":         ("manufactured drama", "the fact should carry the weight"),
    "triads":        ("rule of three", "two items, or one, or a real list"),
    "filler":        ("filler word", "cut it; the sentence survives"),
    "stakes":        ("manufactured stakes", "start where the reader needs to start"),
    "verbs":         ("weak verb", "use the direct verb"),
    "assistant":     ("assistant voice", "delete; you are not a chatbot"),
    "artifact":      ("unfinished template language", "fill it in or remove it"),
    "overcorrection":("forced edgy phrasing", "restore a natural speaking voice"),
    "spec-notation": ("shorthand inside a sentence", "write it as a sentence"),
    "cliche":        ("stock cliché", "disassemble it: say the actual trade-off or change"),
    "rhetorical":    ("staged question or setup", "make the point without the setup"),
    "email":         ("form-letter email phrase", "say the actual ask in the first sentence"),
    "misc":          ("generic AI-style wording", "rewrite plainly"),
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
        out.append(f"  WRITING CHECK · {total} sentences · no flagged phrases")
        out.append("  " + "·" * min(total, 40) + "   all clean")
        return out

    out.append(f"  WHERE TO EDIT · {total} sentences · {len(dirty)} flagged "
               f"· strongest first")
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
    out.append(f'  draft overview  {" ".join(shape)}   █ heavy  ▓ moderate  '
               f'▒ mild  · clean')
    return out


def gate_value():
    """Return (threshold, raw_token) for --gate, consuming its argument."""
    if "--gate" not in sys.argv:
        return None, None
    i = sys.argv.index("--gate")
    try:
        tok = sys.argv[i + 1]
        value = float(tok)
        if not math.isfinite(value) or not 0 <= value <= 100:
            raise ValueError
        return value, tok
    except (IndexError, ValueError):
        raise SystemExit("--gate needs a finite threshold from 0 to 100")


CHANNELS = [
    # label, how to pull the number, which direction is better, how to show it
    ("word choice",   lambda r: sum(h["w"] for h in r["hits"]
                                    if h["cat"] in ("lexicon", "rider")), "low"),
    ("phrasing",      lambda r: sum(h["w"] for h in r["hits"]
                                    if h["cat"] not in ("lexicon", "rider")), "low"),
    ("sentence variety", lambda r: r["burstiness"], "high"),
    ("readability",   lambda r: r["followability_penalty"], "low"),
    ("formatting",    lambda r: r["emdash_per_100w"] + r["emoji_count"]
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
are artificial bookmark despite hey modern please researchers save unpopular welcome
""".split())
NOT_NAME_WORDS = {word.lower() for word in NOT_NAMES} | COMMON_WORDS


def facts(text, _other=""):
    """Checkable claims in a draft: figures, named entities, quotes, links."""
    # URLs contain lowercase forms of the names they point at ("acme.io" made
    # "Acme" look like a sentence opener in the source and an invention in the
    # rewrite), so entity detection runs on the text with links removed.
    urls = text  # links keep their spelled forms; numbers in a slug are not facts
    prose = _spell_to_digits(re.sub(r"https?://\S+", " ", text))
    # Ordered-list markers describe structure, not quantities. Treating the
    # ``1.`` in a three-item list as a dropped fact penalises a faithful prose
    # rewrite and hides real numeric changes in noise.
    prose = re.sub(r"(?m)^\s*\d+[.)]\s+", "", prose)
    other = _spell_to_digits(_other)
    other = re.sub(r"(?m)^\s*\d+[.)]\s+", "", other)
    out = {}
    for kind, rx in FACT_RX:
        found = set()
        for m in re.finditer(rx, urls if kind == "url" else prose):
            v = (m.group(1) if m.lastindex else m.group(0)).strip()
            if kind == "name":
                if v in NOT_NAMES or len(v) < 3:
                    continue
                low = v.lower()
                tokens = re.findall(r"[a-z]+", low)
                # A title-cased run made entirely of ordinary sentence words is
                # not an entity (for example, "Shipped Tuesday").
                if tokens and all(token in NOT_NAME_WORDS for token in tokens):
                    continue
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
INTERIOR_STATE_RX = re.compile(
    r"\b(?:I|we)\s+(?:was|were|am|felt|feel|got)\s+"
    r"(?:(?:very|really|extremely|quite|so)\s+)?(?P<state>[A-Za-z]+)", re.I)
INTERIOR_COGNITION_RX = re.compile(
    r"\b(?:I|we)\s+(?P<cognition>remember(?:ed)?|recall(?:ed)?|realise(?:d)?|"
    r"realize(?:d)?|knew|fear(?:ed)?|hope(?:d)?|worr(?:y|ied)|panic(?:ked)?|"
    r"struggl(?:e|ed)|doubt(?:ed)?)\b", re.I)
INTERIOR_BODY_RX = re.compile(
    r"\b(?:my|our)\s+(?P<body>heart|stomach|gut|chest|hands|mind)\b", re.I)
INTERIOR_IMPERSONAL_RX = re.compile(
    r"\bit\s+felt\s+(?P<impersonal>surreal|unreal|impossible|inevitable|like)\b", re.I)
INTERIOR_BARE_RX = re.compile(
    r"\bfelt\s+(?P<bare>familiar|natural|surreal|foreign|inevitable|effortless)\b", re.I)
COGNITION_CANON = {
    "remembered": "remember", "recalled": "remember", "recall": "remember",
    "realised": "realize", "realise": "realize", "realized": "realize",
    "feared": "fear", "hoped": "hope", "worried": "worry",
    "panicked": "panic", "struggled": "struggle", "doubted": "doubt",
}


def interior_claims(text):
    """Inner-state assertions, reduced to a comparable core so paraphrase of an
    existing one does not read as a new invention."""
    out = {m.group("state").lower() for m in INTERIOR_STATE_RX.finditer(text)}
    for m in INTERIOR_COGNITION_RX.finditer(text):
        word = m.group("cognition").lower()
        out.add(COGNITION_CANON.get(word, word))
    out.update("body:" + m.group("body").lower()
               for m in INTERIOR_BODY_RX.finditer(text))
    out.update(m.group("impersonal").lower()
               for m in INTERIOR_IMPERSONAL_RX.finditer(text))
    out.update(m.group("bare").lower() for m in INTERIOR_BARE_RX.finditer(text))
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
    def entity_tokens(entity):
        return {w for w in re.findall(r"[a-z]+", entity.lower())
                if w not in NOT_NAME_WORDS}

    def entity_match(entity, candidates):
        """Exact names and honest shortenings match; partial renames do not."""
        left = entity_tokens(entity)
        if not left:
            return False
        for candidate in candidates:
            right = entity_tokens(candidate)
            if right and (left == right or left < right or right < left):
                return True
        return False
    # Interior experience is the fabrication the judges actually caught, and the
    # one no entity check sees: nothing was renamed, a feeling was added.
    ia, ib = interior_claims(before), interior_claims(after)
    new_interior = ib - ia
    for kind, _ in FACT_RX:
        if kind == "name":
            dropped = {e for e in a[kind] if not entity_match(e, b[kind])}
            added = {e for e in b[kind] if not entity_match(e, a[kind])}
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
# used by scripts/rerank.py to pick the best of N candidates. Fidelity is
# reported alongside, never folded in, so a candidate can never win by dropping
# or inventing a fact however clean it reads.
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
    out = ["", "  FACT AND MEANING CHECK · original vs edited text", ""]
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
            "  Result: " + ("facts preserved; nothing added"
                             if r["preserved"] and not r["invented"] else
                             ("FACTS DROPPED" if not r["preserved"] else "")
                             + (" · CONTENT INVENTED" if r["invented"] else "")),
            "  This checks figures, names, quotes, links, and stated feelings.",
            "  Your AI assistant still compares the full meaning because a changed claim",
            "  or emphasis may use all the same names and numbers.", ""]
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
    out = ["", "  WHAT CHANGED · before → after", ""]
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
            f"  writing score {a['ai_likelihood']:.1f} → {b['ai_likelihood']:.1f}"
            f"   ({band(a['ai_likelihood'])} → {band(b['ai_likelihood'])})",
            f"  length        {a['n_words']} → {b['n_words']} words "
            f"({(b['n_words']-a['n_words'])/max(a['n_words'],1)*100:+.0f}%)",
            f"  flagged phrases {len(a['hits'])} → {len(b['hits'])}"]
    kept = {h["name"] for h in b["hits"]}
    fixed = [h["name"] for h in a["hits"] if h["name"] not in kept]
    if fixed:
        out.append("  fixed         " + ", ".join(sorted(set(fixed))[:6]))
    if kept:
        out.append("  still present " + ", ".join(sorted(kept)[:6]))
    # A shorter text with the same tells is not a better text.
    if b["n_words"] < a["n_words"] * 0.75 and len(b["hits"]) >= len(a["hits"]):
        out.append("  note          got shorter without fixing flagged phrases — "
                   "check this is an edit, not a deletion")
    return out + [""]


def _required_option_value(argv, flag):
    if flag not in argv:
        return None
    if argv.count(flag) > 1:
        raise SystemExit(f"{flag} may be supplied only once")
    index = argv.index(flag)
    if index + 1 >= len(argv) or argv[index + 1].startswith("--"):
        raise SystemExit(f"{flag} needs a value")
    return argv[index + 1]


def _read_text_file(path):
    try:
        return Path(path).read_text()
    except (OSError, UnicodeDecodeError) as exc:
        raise SystemExit(f"cannot read {path}: {exc}") from exc


def _text_files(root_arg):
    root = Path(root_arg)
    if not root.exists():
        raise SystemExit(f"directory does not exist: {root}")
    if not root.is_dir():
        raise SystemExit(f"expected a directory, got: {root}")
    return sorted(p for p in root.rglob("*") if p.suffix.lower() in
                  (".md", ".txt", ".markdown") and p.is_file())


def main():
    argv = sys.argv[1:]
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    value_flags = {"--gate", "--genre", "--voice"}
    bool_flags = {"--json", "--explain", "--formal", "--fidelity", "--dna",
                  "--portfolio", "--batch", "--heatmap"}
    unknown = [arg for arg in argv if arg.startswith("--")
               and arg not in value_flags | bool_flags]
    if unknown:
        raise SystemExit(f"unknown option: {unknown[0]}")
    for flag in value_flags:
        _required_option_value(argv, flag)
    modes = [flag for flag in ("--fidelity", "--dna", "--portfolio", "--batch")
             if flag in argv]
    if len(modes) > 1:
        raise SystemExit("choose only one mode: " + ", ".join(modes))

    gv, _ = gate_value()
    # Values that belong to a flag (--gate 25, --genre social, --voice manav)
    # are not positional file arguments. Drop each flag and the token after it.
    VALUE_FLAGS = value_flags
    args, skip = [], False
    for a in argv:
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
        genre = _required_option_value(argv, "--genre")
    if formal: genre = "formal"
    voice = None
    if "--voice" in sys.argv:
        voice = _required_option_value(argv, "--voice")
    try:
        data = load_patterns(voice=voice)
    except ValueError as exc:
        sys.exit(str(exc))

    if "--fidelity" in sys.argv:
        if len(args) != 2:
            sys.exit("--fidelity needs exactly two files: before and after")
        before, after = _read_text_file(args[0]), _read_text_file(args[1])
        for line in render_fidelity(before, after):
            print(line)
        r = fidelity(before, after)
        sys.exit(0 if (r["preserved"] and not r["invented"]) else 1)

    if "--dna" in sys.argv:
        if len(args) != 2:
            sys.exit("--dna needs exactly two files: before and after")
        for line in dna(_read_text_file(args[0]), _read_text_file(args[1]),
                        data, formal=formal):
            print(line)
        return

    if "--portfolio" in sys.argv:
        if len(args) > 1:
            raise SystemExit("--portfolio accepts one directory")
        root = Path(args[0]) if args else Path(".")
        files = _text_files(root)
        if not files:
            raise SystemExit(f"no .md, .txt, or .markdown files under {root}")
        result = portfolio_metrics((str(p), _read_text_file(p)) for p in files)
        if as_json:
            print(json.dumps(result, ensure_ascii=False, indent=1))
        else:
            for line in render_portfolio(result):
                print(line)
        return

    if "--batch" in sys.argv:
        if len(args) > 1:
            raise SystemExit("--batch accepts one directory")
        root = Path(args[0]) if args else Path(".")
        files = _text_files(root)
        if not files:
            raise SystemExit(f"no .md, .txt, or .markdown files under {root}")
        rows = []
        for p in files:
            r = score_text(_read_text_file(p), data, formal=formal)
            rows.append((r["ai_likelihood"], p, band(r["ai_likelihood"])))
        rows.sort(key=lambda x: -x[0])
        for sc, p, b in rows:
            print(f"{sc:6.1f}  {b:12s} {p}")
        worst = max(sc for sc, _, _ in rows)
        sys.exit(1 if gv is not None and worst > gv else 0)

    if len(args) > 1:
        raise SystemExit("score mode accepts one file, or '-' for stdin")
    # No file argument, or the conventional "-", means read stdin.
    text = sys.stdin.read() if (not args or args[0] == "-") else _read_text_file(args[0])
    r = score_text(text, data, formal=formal)
    if as_json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        if gv is None:
            return
        # --json --gate is documented CI usage; returning here exited 0 on a
        # failing document, so a broken gate silently passed every build.
        sh_j = shape_metrics(text, genre=genre)
        sys.exit(0 if (r["ai_likelihood"] <= gv and not sh_j.get("broetry")) else 1)
    print(f"Writing score: {r['ai_likelihood']}/100  [{band(r['ai_likelihood'])}]")
    print("  Lower is better. This describes the writing, not who wrote it.")
    unique_hits = []
    seen_quotes = set()
    for hit in sorted(r["hits"], key=lambda item: -item["w"]):
        key = hit["quote"].strip().lower()
        if key and key not in seen_quotes:
            seen_quotes.add(key)
            unique_hits.append(hit)
    print(f"  Flagged phrases : {len(unique_hits)} across {r['n_words']} words")
    variety = "natural" if r["burstiness"] >= 0.45 else "too even"
    print(f"  Sentence variety: {variety}")
    print(f"  Punctuation      : {r['emoji_count']} emoji, {r['bold_spans']} bold spans, "
          f"{r['hashtags']} hashtags, {r['emdash_per_100w']:.2f} em dashes per 100 words")
    if r["followability_penalty"] > 2:
        print(f"  Readability      : needs work — "
              f"{r['comma_chain_frac']:.0%} of sentences chain clauses with commas; "
              f"{r['overlong_frac']:.0%} are unusually long")
    else:
        print("  Readability      : clear")
    if r["categories"]:
        top = sorted(r["categories"].items(), key=lambda kv: -kv[1])[:8]
        labels = [CAT_MEANING.get(k, (k, ""))[0] for k, _ in top]
        print("  Main issues      : " + ", ".join(labels))
    sh = shape_metrics(text, genre=genre)
    r["shape"] = sh
    print("  Page layout      : " + (
        f"too many short, one-sentence paragraphs ({sh['solo_frac']:.0%}); "
        f"longest fragment run {sh['max_fragment_run']}" if sh.get("broetry")
        else (f"looks natural ({sh['solo_frac']:.0%} one-sentence paragraphs)" if sh["measured"]
              else "not checked for this kind of writing")))
    print("  What Zero Slop checked: word choice, formatting, sentence rhythm, "
          "readability, and tone" + (", plus page layout" if sh["measured"] else ""))
    print("  What your AI assistant reviews: strength of the ideas, voice, and factual accuracy"
          + ("" if sh["measured"] else "; page layout was not checked"))
    if explain:
        if unique_hits:
            print(f"\n  Flagged phrases ({len(unique_hits)}), strongest first:")
            for h in unique_hits:
                name, fix = CAT_MEANING.get(h["cat"], ("generic wording", "rewrite plainly"))
                print(f"    {h['quote']!r} — {name}; {fix}")
        else:
            print("\n  Flagged phrases: none. The remaining score comes from sentence rhythm and formatting.")
    if "--heatmap" in sys.argv or explain:
        for line in render_heatmap(text, data, formal=formal):
            print(line)
    if gv is not None:
        ok = r["ai_likelihood"] <= gv and not sh.get("broetry")
        why = "" if ok else (" (page layout needs work)" if sh.get("broetry") and r["ai_likelihood"] <= gv else "")
        verdict = "PASSED" if ok else "NEEDS WORK"
        print(f"  Check against {gv:g}: {verdict}{why}. This covers writing patterns and "
              f"layout; your AI assistant still reviews the ideas, voice, and facts.")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
