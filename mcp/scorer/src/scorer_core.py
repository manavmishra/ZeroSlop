"""Pure-Python boundary around Zero Slop's shipped scoring modules."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ENGINE = HERE / "engine"
sys.path.insert(0, str(ENGINE))

# A server run must never load or create a maintainer's private learning data.
os.environ.setdefault("ZERO_SLOP_HOME", "/tmp/zero-slop-mcp")
os.environ.setdefault("ZERO_SLOP_NO_NOTES", "1")

import register  # noqa: E402
import rerank  # noqa: E402
import slopscore  # noqa: E402


MAX_CHARS = 20_000
VALID_GENRES = {"general", "social", "email", "research", "professional"}
PATTERNS = slopscore.load_patterns()
MANIFEST = json.loads((HERE / "scorer-manifest.json").read_text())


class ScorerInputError(ValueError):
    """An invalid gateway-to-scorer request."""


def _text(value: Any, label: str = "text") -> str:
    if not isinstance(value, str) or not value.strip():
        raise ScorerInputError(f"{label} must be non-empty text")
    if len(value) > MAX_CHARS:
        raise ScorerInputError(f"{label} exceeds {MAX_CHARS} characters")
    return value


def _genre(value: Any) -> str:
    genre = value if isinstance(value, str) else "general"
    if genre not in VALID_GENRES:
        raise ScorerInputError("unsupported genre")
    return genre


def _unique_hits(report: dict[str, Any]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for hit in sorted(report["hits"], key=lambda item: -item["w"]):
        key = str(hit["quote"]).strip().casefold()
        if key and key not in seen:
            seen.add(key)
            unique.append(hit)
    return unique


def _register_report(text: str) -> dict[str, Any]:
    measured = register.measure(text)
    rows = register.verdicts(measured)
    findings = [
        {
            "name": register.LABEL.get(key, key),
            "rate": round(float(value), 1),
            "budget": float(budget),
            "found": int(measured[key]["count"]),
            "quote": str((measured[key].get("hits") or [""])[0]),
        }
        for key, value, budget, ok in rows
        if not ok
    ]
    return {
        "measured": measured["words"] >= register.MIN_WORDS,
        "words": int(measured["words"]),
        "checked": len(rows),
        "findings": findings,
        "twoPartContrasts": int(measured.get("antithesis_pair", {}).get("count", 0)),
        "announcements": int(measured.get("significance_scaffolding", {}).get("count", 0)),
    }


def report(text: Any, genre: Any = "general") -> dict[str, Any]:
    source = _text(text)
    kind = _genre(genre)
    raw = slopscore.score_text(source, PATTERNS, formal=kind in {"research", "professional"})
    measured_text, _normalization = slopscore.normalize_for_detection(slopscore.strip_noise(source))
    hits = _unique_hits(raw)
    shape = slopscore.shape_metrics(source, genre=kind)
    register_report = _register_report(source)
    return {
        "score": round(float(raw["ai_likelihood"]), 1),
        "band": slopscore.band(raw["ai_likelihood"]),
        "words": int(raw["n_words"]),
        "sentences": int(raw["n_sentences"]),
        "flaggedPhrases": len(hits),
        "sentenceVariety": "natural" if raw["burstiness"] >= 0.45 else "too even",
        "readability": "needs work" if raw["followability_penalty"] > 2 else "clear",
        "punctuation": {
            # The public report promises counts. The scorer's density is a
            # fractional value per 100 words and fails the gateway's integer
            # schema on ordinary drafts containing a dash or CLI flag.
            "dashes": len(re.findall(r"—|--", measured_text)),
            "emoji": int(raw["emoji_count"]),
            "hashtags": int(raw["hashtags"]),
        },
        "highWeightFlags": sum(1 for hit in raw["hits"] if hit.get("w", 0) >= 4),
        "shape": {
            "measured": bool(shape["measured"]),
            "broetry": bool(shape.get("broetry")),
            "oneSentenceParagraphShare": shape.get("solo_frac"),
            "longestFragmentRun": shape.get("max_fragment_run"),
        },
        "register": register_report,
        "flags": [
            {
                "phrase": str(hit["quote"]),
                "strength": float(hit["w"]),
                "issue": slopscore.CAT_MEANING.get(
                    hit["cat"], ("generic wording", "rewrite plainly")
                )[0],
                "direction": slopscore.CAT_MEANING.get(
                    hit["cat"], ("generic wording", "rewrite plainly")
                )[1],
            }
            for hit in hits[:24]
        ],
    }


def rank(original: Any, candidates: Any, genre: Any = "general") -> dict[str, Any]:
    source = _text(original, "original")
    kind = _genre(genre)
    if not isinstance(candidates, dict) or not candidates:
        raise ScorerInputError("candidates must be a non-empty object")
    cleaned = {str(name): _text(value, f"candidate {name}") for name, value in candidates.items()}
    ranked = rerank.rank(source, cleaned, kind, None)
    top = ranked[0]
    return {
        "name": str(top["name"]),
        "text": str(top["text"]),
        "preserved": bool(top["preserved"]),
        "invented": bool(top["invented"]),
        "after": round(float(top["after_ai"]), 1),
        "before": round(float(top["before_ai"]), 1),
        "ranked": [
            {
                "name": str(item["name"]),
                "after": round(float(item["after_ai"]), 1),
                "preserved": bool(item["preserved"]),
                "invented": bool(item["invented"]),
            }
            for item in ranked
        ],
    }


def delta(original: Any, rewrite: Any) -> dict[str, Any]:
    return register.delta(_text(original, "original"), _text(rewrite, "rewrite"))


def health() -> dict[str, Any]:
    return {"ok": True, "scorerVersion": MANIFEST["version"], "engineFiles": 6}
