#!/usr/bin/env python3
"""calibrate — derive tell weights from evidence instead of intuition.

Two jobs, both stdlib-only and offline:

  1. WEIGHTS FROM DATA.  Given a folder of known-human writing and a folder of
     known-AI drafts, compute each lexicon term's *excess frequency* in the AI
     set — the method Kobak et al. used to find the LLM vocabulary in 15M
     PubMed abstracts. Terms the two corpora use equally get weight ~0. Terms
     the AI set over-uses get weight proportional to the log-ratio. This makes
     the meter self-calibrating: point it at this month's model output and the
     weights follow the current era, not 2024's.

  2. FALSE-POSITIVE REGRESSION.  Any pattern change is checked against a
     corpus of writing that must never be flagged. A pattern that fires on
     known-good human prose is rejected before it can ship. This is what makes
     continuous updating safe rather than reckless.

Usage:
    python3 calibrate.py --human dir/ --ai dir/ [--out data/calibrated.json]
    python3 calibrate.py --selftest              # run the FP regression only
    python3 calibrate.py --decay                 # age out unconfirmed patterns

Provenance: every weight written carries `first_seen`, `last_confirmed`, and
`n_obs`, so a future maintainer can tell a well-evidenced tell from a guess.
"""
import json
import math
import re
import sys
import argparse
from collections import Counter
from datetime import date
from pathlib import Path

from safeio import atomic_write_text, file_locks

DATA = Path(__file__).resolve().parent.parent / "data"
WORD = re.compile(r"[a-z’']+")
MIN_OBS = 5          # a term needs this many AI-side occurrences to earn a weight
MAX_WEIGHT = 6.0     # cap so no single word can convict alone
DECAY_MONTHS = 18    # unconfirmed patterns lose half their weight after this


def _json_texts(obj):
    """Extract prose from supported JSON corpus shapes without scoring JSON syntax."""
    if isinstance(obj, str):
        return [obj]
    values = obj.values() if isinstance(obj, dict) else obj if isinstance(obj, list) else []
    texts = []
    for value in values:
        if isinstance(value, str):
            texts.append(value)
        elif isinstance(value, dict) and isinstance(value.get("draft"), str):
            texts.append(value["draft"])
    return texts


def read_corpus(d):
    root = Path(d)
    if not root.exists():
        raise ValueError(f"corpus directory does not exist: {root}")
    if not root.is_dir():
        raise ValueError(f"corpus path is not a directory: {root}")
    texts = []
    for p in sorted(root.rglob("*")):
        if p.suffix.lower() in (".txt", ".md", ".json") and p.is_file():
            try:
                t = p.read_text(errors="ignore")
            except OSError as exc:
                raise ValueError(f"cannot read corpus file: {p}") from exc
            if p.suffix.lower() == ".json":
                try:
                    extracted = _json_texts(json.loads(t))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid JSON corpus file: {p}") from exc
                texts.extend(value for value in extracted if value.strip())
            elif t.strip():
                texts.append(t)
    if not texts:
        raise ValueError(f"corpus contains no non-empty .txt, .md, or supported JSON text: {root}")
    return texts


def freqs(texts):
    c = Counter()
    total = 0
    for t in texts:
        w = WORD.findall(t.lower())
        c.update(w)
        total += len(w)
    if total == 0:
        raise ValueError("corpus contains no words")
    return c, total


def excess_weights(human_dir, ai_dir):
    hc, hn = freqs(read_corpus(human_dir))
    ac, an = freqs(read_corpus(ai_dir))
    out = {}
    for term, n_ai in ac.items():
        if n_ai < MIN_OBS or len(term) < 4:
            continue
        p_ai = n_ai / an
        p_hu = (hc.get(term, 0) + 0.5) / hn      # smoothed: unseen != impossible
        ratio = p_ai / p_hu
        if ratio <= 2.0:                          # not over-represented enough
            continue
        w = round(min(math.log2(ratio) * 1.2, MAX_WEIGHT), 1)
        if w >= 1.0:
            out[term] = {"w": w, "n_obs": n_ai, "ratio": round(ratio, 1)}
    return out, hn, an


def shape_selftest():
    """Run the shape channel against genres that mimic broetry structurally.

    Hostile setting: every sample is declared `social`, the only genre where
    the channel engages. Anything that flags here is a documented boundary,
    not a silent one.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import slopscore
    d = DATA / "corpus" / "must-not-flag-shape"
    if not d.exists():
        print("no shape corpus — shape channel untested")
        return 1
    KNOWN = {"lyrics"}          # see data/corpus/must-not-flag-shape/README.md
    flagged, total = [], 0
    files = sorted(d.glob("*.txt"))
    if not files:
        print(f"shape corpus at {d} is empty — shape channel untested")
        return 1
    for p in files:
        total += 1
        m = slopscore.shape_metrics(p.read_text(), genre="social")
        if m.get("broetry"):
            tag = "known boundary" if p.stem in KNOWN else "REGRESSION"
            flagged.append((p.stem, tag))
            print(f"  {tag:14s} {p.name}  solo={m['solo_frac']} run={m['max_fragment_run']}")
    new = [f for f, t in flagged if t == "REGRESSION"]
    print(f"shape regression: {total - len(flagged)}/{total} silent, "
          f"{len([f for f,t in flagged if t=='known boundary'])} known boundary, "
          f"{len(new)} new")
    return 1 if new else 0


def selftest(fp_dir=None):
    """No pattern may fire on writing that must never be flagged."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import slopscore
    data = slopscore.load_patterns()
    fp_dir = Path(fp_dir or DATA / "corpus" / "must-not-flag")
    if not fp_dir.exists():
        print(f"no false-positive corpus at {fp_dir} — nothing to check")
        return 1
    files = sorted(p for p in fp_dir.rglob("*")
                   if p.is_file() and p.suffix.lower() in (".txt", ".md")
                   and p.name.lower() != "readme.md")
    if not files:
        print(f"false-positive corpus at {fp_dir} is empty — nothing to check")
        return 1
    failures = []
    for p in files:
        r = slopscore.score_text(p.read_text(), data)
        if r["ai_likelihood"] > 25:
            failures.append((p.name, r["ai_likelihood"],
                             [h["name"] for h in r["hits"]][:4]))
    for name, score, hits in failures:
        print(f"  FAIL {score:5.1f}  {name}  ← {', '.join(hits) or 'no lexical hits'}")
    n = len(files)
    print(f"false-positive regression: {n - len(failures)}/{n} passed")
    return 1 if failures else 0


def decay():
    """Halve the weight of patterns not re-confirmed within DECAY_MONTHS."""
    p = DATA / "learned.json"
    with file_locks([p]):
        try:
            d = json.loads(p.read_text())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SystemExit(f"cannot read valid learned state at {p}: {exc}") from exc
        if not isinstance(d, dict) or not isinstance(d.get("patterns", []), list):
            raise SystemExit(f"invalid learned-state schema at {p}")
        for index, pat in enumerate(d.get("patterns", [])):
            if (not isinstance(pat, dict)
                    or not isinstance(pat.get("w"), (int, float))
                    or isinstance(pat.get("w"), bool)
                    or not math.isfinite(pat["w"])
                    or not 0 <= pat["w"] <= 10
                    or ("last_confirmed" in pat
                        and not isinstance(pat["last_confirmed"], str))
                    or ("decayed" in pat and not isinstance(pat["decayed"], str))):
                raise SystemExit(
                    f"invalid learned pattern at index {index} in {p}"
                )
        today = date.today()
        changed = 0
        for index, pat in enumerate(d.get("patterns", [])):
            lc = pat.get("last_confirmed")
            if not lc:
                continue
            try:
                confirmed = date.fromisoformat(lc)
            except ValueError as exc:
                raise SystemExit(
                    f"invalid last_confirmed date at pattern index {index}"
                ) from exc
            y, m = confirmed.year, confirmed.month
            months = (today.year - y) * 12 + (today.month - m)
            weight = pat["w"]
            # One stale interval earns one decay. Re-running the command must be
            # idempotent; a later confirmation clears this marker and starts a
            # fresh interval.
            if months > DECAY_MONTHS and weight > 0.5 and not pat.get("decayed"):
                pat["w"] = round(weight / 2, 2)
                pat["decayed"] = str(today)
                changed += 1
        atomic_write_text(p, json.dumps(d, indent=1) + "\n")
    print(f"decayed {changed} pattern(s) unconfirmed for over {DECAY_MONTHS} months")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--selftest", action="store_true")
    mode.add_argument("--decay", action="store_true")
    ap.add_argument("--human", metavar="DIR")
    ap.add_argument("--ai", metavar="DIR")
    ap.add_argument("--out", metavar="FILE")
    args = ap.parse_args(argv)
    if args.selftest:
        fp_status = selftest()
        shape_status = shape_selftest()
        return 1 if fp_status or shape_status else 0
    if args.decay:
        return decay()
    if not args.human or not args.ai:
        ap.error("calibration needs --human DIR and --ai DIR")
    try:
        weights, hn, an = excess_weights(args.human, args.ai)
    except ValueError as exc:
        ap.error(str(exc))
    print(f"human corpus {hn:,} words · ai corpus {an:,} words")
    print(f"terms over-represented in AI text (ratio > 2, n >= {MIN_OBS}): {len(weights)}")
    for t, v in sorted(weights.items(), key=lambda kv: -kv[1]["w"])[:25]:
        print(f"  {v['w']:4.1f}  {t:18s} {v['ratio']:6.1f}x  n={v['n_obs']}")
    out = Path(args.out) if args.out else DATA / "calibrated.json"
    protected = {(DATA / "patterns.json").resolve(), (DATA / "learned.json").resolve()}
    if out.resolve() in protected:
        ap.error(f"refusing to overwrite tracked detector state: {out}; write a separate calibration file")
    today = str(date.today())
    payload = {"_comment": "Weights derived from corpus excess frequency by "
                           "calibrate.py. Merge into learned.json after "
                           "--selftest passes.",
               "calibrated": today,
               "lexicon": {t: v["w"] for t, v in weights.items()},
               "provenance": {t: dict(v, first_seen=today, last_confirmed=today)
                              for t, v in weights.items()}}
    try:
        with file_locks([out]):
            atomic_write_text(out, json.dumps(payload, indent=1) + "\n")
    except OSError as exc:
        ap.error(f"cannot write calibration output {out}: {exc}")
    print(f"\nwrote {out}")
    print("next: review, merge the lexicon into data/learned.json, then run "
          "`python3 calibrate.py --selftest` before shipping")
    return 0


if __name__ == "__main__":
    sys.exit(main())
