"""Maintainer-only exception for historical measurements of identical code.

No fuzzy versions, ranges, generic 'unchanged scorer' bypass or runtime behavior.
The public record remains a measurement of its original release. Callers retain
their own data/vector checks; this only resolves an otherwise stale version label.
"""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = Path(__file__).with_name("runtime-compatibility.json")
PAIR_EVIDENCE = {
    ("2.11.6", "2.12.0"): EVIDENCE,
    ("2.11.6", "2.12.1"): Path(__file__).with_name("runtime-compatibility-2.12.1.json"),
    ("2.11.6", "2.12.2"): Path(__file__).with_name("runtime-compatibility-2.12.2.json"),
    ("2.11.6", "2.12.3"): Path(__file__).with_name("runtime-compatibility-2.12.3.json"),
    ("2.11.6", "2.12.4"): Path(__file__).with_name("runtime-compatibility-2.12.4.json"),
    ("2.11.6", "2.12.5"): Path(__file__).with_name("runtime-compatibility-2.12.5.json"),
    ("2.11.6", "2.12.6"): Path(__file__).with_name("runtime-compatibility-2.12.6.json"),
    ("2.11.6", "2.12.7"): Path(__file__).with_name("runtime-compatibility-2.12.7.json"),
    ("2.11.6", "2.12.8"): Path(__file__).with_name("runtime-compatibility-2.12.8.json"),
    ("2.11.6", "2.12.9"): Path(__file__).with_name("runtime-compatibility-2.12.9.json"),
    ("2.12.12", "2.12.13"): Path(__file__).with_name("runtime-compatibility-2.12.13.json"),
    ("2.12.12", "2.12.14"): Path(__file__).with_name("runtime-compatibility-2.12.14-from-2.12.12.json"),
    ("2.12.13", "2.12.14"): Path(__file__).with_name("runtime-compatibility-2.12.14-from-2.12.13.json"),
    ("2.12.12", "2.12.15"): Path(__file__).with_name("runtime-compatibility-2.12.15-from-2.12.12.json"),
    ("2.12.13", "2.12.15"): Path(__file__).with_name("runtime-compatibility-2.12.15-from-2.12.13.json"),
}
PAIR_COMMITS = {
    pair: "0d866036b210b90e23fa9f7b4146316cf40c255e"
    for pair in PAIR_EVIDENCE if pair[0] == "2.11.6"
}
PAIR_COMMITS[("2.12.12", "2.12.13")] = "d065464b64d2ae46d72fde83f3c0b5da40bd149a"
PAIR_COMMITS[("2.12.12", "2.12.14")] = "d065464b64d2ae46d72fde83f3c0b5da40bd149a"
PAIR_COMMITS[("2.12.13", "2.12.14")] = "5dc573740f79b32449ec5f25e9a1c443e7ab8e36"
PAIR_COMMITS[("2.12.12", "2.12.15")] = "d065464b64d2ae46d72fde83f3c0b5da40bd149a"
PAIR_COMMITS[("2.12.13", "2.12.15")] = "5dc573740f79b32449ec5f25e9a1c443e7ab8e36"
PINNED_FILES = frozenset({
    "scripts/slopscore.py", "scripts/register.py", "scripts/rerank.py",
    "scripts/safeio.py", "scripts/predictability.py",
    "data/patterns.json", "data/learned.json",
})


def exact_code_compatible(measured_version, current_version, *, root=ROOT, evidence_path=None):
    """True only for an explicitly reviewed pair and its complete exact hashes."""
    try:
        selected = PAIR_EVIDENCE.get((measured_version, current_version))
        if selected is None:
            return False
        evidence = json.loads(Path(selected if evidence_path is None else evidence_path).read_text())
        if (evidence.get("schema") != 1
                or evidence.get("result_kind") != "exact_code_equivalence_not_new_measurement"
                or evidence.get("measured_version") != measured_version
                or evidence.get("compatible_version") != current_version
                or evidence.get("measured_commit") != PAIR_COMMITS.get((measured_version, current_version))
                or set(evidence.get("files", {})) != PINNED_FILES):
            return False
        return all(hashlib.sha256((Path(root) / name).read_bytes()).hexdigest() == expected
                   for name, expected in evidence["files"].items())
    except (OSError, ValueError, TypeError, AttributeError):
        return False


def reports_match(measured, recomputed, *, root=ROOT, evidence_path=None):
    """Compare all report data; normalize only an independently verified version.

    Deep copies avoid relabeling either historical artifacts or fresh output.
    """
    if measured == recomputed:
        return True
    old = measured.get("scorer", {}).get("version")
    new = recomputed.get("scorer", {}).get("version")
    if not exact_code_compatible(old, new, root=root, evidence_path=evidence_path):
        return False
    normalized = copy.deepcopy(recomputed)
    normalized["scorer"]["version"] = old
    return measured == normalized
