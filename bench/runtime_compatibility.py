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
PINNED_FILES = frozenset({
    "scripts/slopscore.py", "scripts/register.py", "scripts/rerank.py",
    "scripts/safeio.py", "scripts/predictability.py",
    "data/patterns.json", "data/learned.json",
})


def exact_code_compatible(measured_version, current_version, *, root=ROOT, evidence_path=EVIDENCE):
    """True only for the reviewed 2.11.6 -> 2.12.0 pair and all exact hashes."""
    if (measured_version, current_version) != ("2.11.6", "2.12.0"):
        return False
    try:
        evidence = json.loads(Path(evidence_path).read_text())
        if (evidence.get("schema") != 1
                or evidence.get("result_kind") != "exact_code_equivalence_not_new_measurement"
                or evidence.get("measured_version") != measured_version
                or evidence.get("compatible_version") != current_version
                or evidence.get("measured_commit") != "0d866036b210b90e23fa9f7b4146316cf40c255e"
                or set(evidence.get("files", {})) != PINNED_FILES):
            return False
        return all(hashlib.sha256((Path(root) / name).read_bytes()).hexdigest() == expected
                   for name, expected in evidence["files"].items())
    except (OSError, ValueError, TypeError, AttributeError):
        return False


def reports_match(measured, recomputed, *, root=ROOT):
    """Compare all report data; normalize only an independently verified version.

    Deep copies avoid relabeling either historical artifacts or fresh output.
    """
    if measured == recomputed:
        return True
    old = measured.get("scorer", {}).get("version")
    new = recomputed.get("scorer", {}).get("version")
    if not exact_code_compatible(old, new, root=root):
        return False
    normalized = copy.deepcopy(recomputed)
    normalized["scorer"]["version"] = old
    return measured == normalized
