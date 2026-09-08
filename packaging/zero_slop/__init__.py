"""Zero Slop — score AI-sounding prose and check what a rewrite changed.

The scorer runs offline and uses only the Python standard library.

    from zero_slop import score_text, load_patterns

    data = load_patterns()
    score_text("We are thrilled to announce...", data)["ai_likelihood"]
"""

from zero_slop.scripts.slopscore import load_patterns, score_text

__all__ = ["load_patterns", "score_text", "__version__"]
__version__ = "2.11.1"
