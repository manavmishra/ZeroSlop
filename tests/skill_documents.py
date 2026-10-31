"""Read the entry and its mandatory workflow for instruction-contract tests."""
from pathlib import Path


REQUIRED_READ = (
    "Before starting the eight-role pipeline, read and follow the complete detailed "
    "workflow in references/detailed-workflow.md. Keep every rule in this entry "
    "and the existing references."
)
WORKFLOW_LINK = "[Detailed workflow](references/detailed-workflow.md)"


def compose_required_skill(entry, workflow):
    if REQUIRED_READ not in entry or WORKFLOW_LINK not in entry:
        raise AssertionError("The entry must require reading the complete workflow")
    if not workflow.startswith("## Detailed workflow\n"):
        raise AssertionError("The required workflow is missing or malformed")
    return entry + "\n\n" + workflow


def read_required_skill(root):
    root = Path(root)
    return compose_required_skill(
        (root / "SKILL.md").read_text(encoding="utf-8"),
        (root / "references/detailed-workflow.md").read_text(encoding="utf-8"),
    )
