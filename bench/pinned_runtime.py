"""Offline maintainer fixtures from fixed, measured Git objects, never today's bytes."""
import importlib.util
from pathlib import Path
import subprocess

from runtime_compatibility import ROOT, PINNED_FILES

COMMITS = {
    "2.11.6": "0d866036b210b90e23fa9f7b4146316cf40c255e",
    "2.12.12": "d065464b64d2ae46d72fde83f3c0b5da40bd149a",
    "2.12.13": "5dc573740f79b32449ec5f25e9a1c443e7ab8e36",
}


def populate(destination, version):
    """Materialize only the reviewed seven files; absent Git history is a failure."""
    commit = COMMITS[version]
    destination = Path(destination)
    for name in sorted(PINNED_FILES):
        result = subprocess.run(
            ["git", "show", f"{commit}:{name}"], cwd=ROOT,
            capture_output=True, check=True, timeout=15,
        )
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(result.stdout)
    return destination


def scorer(root, name):
    """Load exact scorer bytes with an empty private-learning location for replay."""
    spec = importlib.util.spec_from_file_location(name, Path(root) / "scripts/slopscore.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.HOME = Path(root) / "empty-private-home"
    return module
