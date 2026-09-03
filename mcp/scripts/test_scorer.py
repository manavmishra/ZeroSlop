#!/usr/bin/env python3
"""Parity and safety checks for the vendored scorer Worker bundle."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCORER = ROOT / "mcp" / "scorer" / "src"
VENDORED = {
    "scripts/slopscore.py": "engine/slopscore.py",
    "scripts/register.py": "engine/register.py",
    "scripts/rerank.py": "engine/rerank.py",
    "scripts/safeio.py": "engine/safeio.py",
    "data/patterns.json": "data/patterns.json",
    "data/learned.json": "data/learned.json",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_core():
    sys.path.insert(0, str(SCORER))
    spec = importlib.util.spec_from_file_location("scorer_core", SCORER / "scorer_core.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    manifest = json.loads((SCORER / "scorer-manifest.json").read_text())
    assert set(manifest) == {"version", *VENDORED}, "unexpected scorer manifest surface"
    for source, target in VENDORED.items():
        expected = manifest[source]
        assert digest(ROOT / source) == expected, f"stale scorer copy: {source}"
        assert digest(SCORER / target) == expected, f"modified vendored scorer: {target}"

    core = load_core()
    sloppy = (
        "In today's rapidly evolving landscape, it is important to note that "
        "this innovative solution seamlessly empowers teams to unlock value."
    )
    clean = "The importer now maps CSV headers automatically."
    before = core.report(sloppy, "general")
    after = core.report(clean, "general")
    assert before["score"] > after["score"]
    assert before["flags"]

    ranked = core.rank(sloppy, {"source": sloppy, "clean": clean}, "general")
    assert ranked["name"] == "clean"
    assert ranked["preserved"]
    assert not ranked["invented"]
    assert core.health()["scorerVersion"] == manifest["version"]
    print("scorer parity and boundary checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
