"""Keep the public runtime security inventory aligned with the shipped skill."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_plugin


class SecurityInventory(unittest.TestCase):
    def test_public_module_inventory_matches_portable_runtime(self):
        expected = {path.relative_to(ROOT).as_posix()
                    for path in build_plugin.wanted(ROOT / "scripts")
                    if path.suffix == ".py"}
        listed = re.findall(r"^\| `(scripts/[^`]+\.py)` \|",
                            (ROOT / "SECURITY.md").read_text(), re.MULTILINE)
        self.assertEqual(len(listed), len(set(listed)), "Duplicate security inventory rows")
        self.assertEqual(set(listed), expected)


if __name__ == "__main__":
    unittest.main()
