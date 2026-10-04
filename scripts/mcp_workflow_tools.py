"""Fixed text-only MCP adapters for the portable workflow's existing helpers.

No caller can select a path, Python command, regex or shell program. Reads use
bundled data or the existing private overlay. State changes require explicit
human opt-in; that declaration is not proof of identity or a sandbox boundary.
"""
import contextlib
import io
import re

import calibrate
import learn
import predictability
import rerank
import rescue
import slopscore
import version_check

TEXT = {"type": "string", "maxLength": 20000}
OBJECT = {"type": "object"}
BOOLEAN = {"type": "boolean"}
OPT_IN = {"type": "boolean", "const": True}
GENRE = {"type": "string", "enum": sorted(learn.GENRES)}
REASON = {"type": "string", "enum": sorted(learn.REASON_LABELS)}
DOCUMENTS = {"type": "object", "minProperties": 1, "maxProperties": 20,
             "additionalProperties": TEXT}
SAMPLES = {"type": "array", "minItems": 1, "maxItems": 20, "items": TEXT}


def _tool(name, title, description, properties, required, *, writes=False, network=False,
          destructive=False):
    return {"name": name, "title": title, "description": description,
            "inputSchema": {"type": "object", "properties": properties,
                            "required": required, "additionalProperties": False},
            "annotations": {"readOnlyHint": not writes, "destructiveHint": destructive,
                            "idempotentHint": not writes, "openWorldHint": network}}


EXTRA_TOOLS = [
    _tool("heatmap", "Explain flagged phrases", "Existing offline phrase-by-phrase guide. No editorial approval or inference.",
          {"text": TEXT, "formal": BOOLEAN, "voice": {"type": "string", "maxLength": 64}}, ["text"]),
    _tool("portfolio", "Check related drafts", "Existing cross-draft repetition diagnostic from named supplied texts; names are labels, never paths.", {"documents": DOCUMENTS}, ["documents"]),
    _tool("predictability_probes", "Prepare wording probes", "Existing deterministic cloze contexts. The host supplies guesses without reading ahead; no model call by this tool.", {"text": TEXT}, ["text"]),
    _tool("predictability_score", "Check supplied guesses", "Existing separate predictability diagnostic; not folded into the writing score.", {"text": TEXT, "predictions": OBJECT}, ["text", "predictions"]),
    _tool("rerank", "Compare supplied rewrites", "Existing source-fidelity-first ranking. Does not generate rewrites or certify semantic equivalence.",
          {"original": TEXT, "candidates": DOCUMENTS, "genre": GENRE, "adjudication": OBJECT}, ["original", "candidates"]),
    _tool("rescue", "Apply conservative fallback", "Existing deterministic availability fallback. Its output still needs the normal score, facts and editorial checks.", {"text": TEXT}, ["text"]),
    _tool("learn_guide", "Retrieve private edit preferences", "Existing lexical guidance from private repeated edits. Advisory, not automatic replacement or a calibrated probability.",
          {"text": TEXT, "reason": REASON, "genre": GENRE, "limit": {"type": "integer", "minimum": 1, "maximum": 20}}, ["text"]),
    _tool("learn_reflect", "Record approved private edit evidence", "STATE CHANGE. Only after the human writer explicitly opts in to record this edit. Existing recurrence, novelty and human-corpus gates remain. Separate activation_opt_in is required to activate eligible rules; no shared taxonomy writes.",
          {"produced": TEXT, "shipped": TEXT, "opt_in": OPT_IN, "reason": REASON,
           "genre": GENRE, "feedback": OBJECT, "activation_opt_in": OPT_IN}, ["produced", "shipped", "opt_in"], writes=True),
    _tool("learn_promote", "Activate eligible private evidence", "STATE CHANGE. Requires separate affirmative human activation consent. Runs existing recurrence, novelty and human-writing safety gates; never shared rules.", {"opt_in": OPT_IN}, ["opt_in"], writes=True),
    _tool("learn_demote", "Apply recurring private false-positive evidence", "STATE CHANGE. Requires affirmative human approval; existing recurrence gates cannot be skipped.", {"opt_in": OPT_IN}, ["opt_in"], writes=True, destructive=True),
    _tool("learn_voice", "Build a private watchlist profile", "STATE CHANGE. With human approval, records only existing watchlist terms from the supplied sample; never a full style model. Named profile takes effect only when explicitly selected.",
          {"name": {"type": "string", "maxLength": 64}, "sample": TEXT, "opt_in": OPT_IN}, ["name", "sample", "opt_in"], writes=True, destructive=True),
    _tool("learn_stats", "Inspect private learning counts", "Existing shared/private rule and evidence counts. Reads private state; no drafts transmitted or rules changed.", {}, []),
    _tool("learn_confirm", "Reconfirm private rules", "STATE CHANGE. Requires human approval for this supplied sample; refreshes existing local confirmations without accepting paths.", {"text": TEXT, "opt_in": OPT_IN}, ["text", "opt_in"], writes=True),
    _tool("learn_decay", "Retire stale private evidence", "STATE CHANGE. Requires human approval; runs existing eighteen-month private decay rules. Never changes the shared taxonomy.", {"opt_in": OPT_IN}, ["opt_in"], writes=True, destructive=True),
    _tool("calibrate_compare", "Compare supplied vocabulary samples", "Existing excess-frequency calculation. Returns proposed statistics only, not admitted quality accuracy or activated rules.", {"human": SAMPLES, "ai": SAMPLES}, ["human", "ai"]),
    _tool("calibrate_selftest", "Check bundled human-writing regression samples", "Runs the existing fixed bundled safety corpus. No caller paths, writes or network; the corpus is a regression floor, not universal proof.", {}, []),
    _tool("version", "Inspect installed release", "Only when check_for_updates is true, performs the existing bounded metadata-only public GitHub version query. No draft, credentials or text sent; respects ZS_NO_UPDATE_CHECK and fails open.", {"check_for_updates": BOOLEAN}, [] , network=True),
]


class _DiagnosticOutput(io.StringIO):
    """Bound printer output without interrupting an already approved transaction."""
    def __init__(self):
        super().__init__()
        self.truncated = False

    def write(self, text):
        remaining = max(0, 65536 - self.tell())
        if len(text) > remaining:
            self.truncated = True
        super().write(text[:remaining])
        return len(text)


def _declared_guidance(text):
    """Keep CLI behavior canonical but route this host's follow-up advice to MCP."""
    prefix = "mcp__plugin_zero-slop_zero-slop-local__"
    text = re.sub(r"python3 (?:scripts/)?slopscore\.py --voice ([A-Za-z0-9._-]+) draft\.md",
                  lambda match: f"declared MCP tool {prefix}score with supplied text and voice={match.group(1)!r}", text)
    text = re.sub(r"python3 (?:scripts/)?calibrate\.py --selftest",
                  f"declared MCP tool {prefix}calibrate_selftest", text)
    return text.replace("Run --promote --apply to activate them locally, or use --auto-apply with --reflect.",
                        f"Only after separate affirmative human activation approval, call declared MCP tool {prefix}learn_promote with opt_in=true. Do not infer approval from this result.")


def _printed(operation, *args, **kwargs):
    output = _DiagnosticOutput()
    with contextlib.redirect_stdout(output):
        code = operation(*args, **kwargs)
    return {"exit_code": code, "diagnostic": _declared_guidance(output.getvalue()),
            "diagnostic_truncated": output.truncated}


def _consent(arguments):
    if arguments.get("opt_in") is not True:
        raise ValueError("Explicit human opt-in is required")


def call(name, args):
    """Called only after the MCP entry point's closed schema/bound validation."""
    if name == "heatmap":
        return {"guide": slopscore.render_heatmap(args["text"], slopscore.load_patterns(voice=args.get("voice")), formal=args.get("formal", False))}
    if name == "portfolio":
        return slopscore.portfolio_metrics(args["documents"].items())
    if name == "predictability_probes":
        return predictability.probes(args["text"])
    if name == "predictability_score":
        return predictability.score(args["text"], args["predictions"])
    if name == "rerank":
        ruling = slopscore.validate_adjudication(args["adjudication"], args["original"]) if "adjudication" in args else None
        return rerank.rank(args["original"], args["candidates"], genre=args.get("genre"), adjudicated=ruling)
    if name == "rescue":
        return {"text": rescue.rescue_text(args["text"]), "editorial_verification_complete": False}
    if name == "learn_guide":
        return {"result_kind": "retrieved_rewrite_preferences", "calibrated_probability": False,
                "rewrite_preferences": learn.retrieve_preferences(args["text"], reason=args.get("reason"), genre=args.get("genre"), limit=args.get("limit", 5))}
    if name == "learn_stats":
        return _printed(learn.stats)
    if name in {"learn_reflect", "learn_promote", "learn_demote", "learn_voice", "learn_confirm", "learn_decay"}:
        _consent(args)
        if name == "learn_reflect":
            result = _printed(learn.reflect_text, args["produced"], args["shipped"], reason=args.get("reason", "unspecified"), genre=args.get("genre", "general"), feedback=args.get("feedback"))
            if args.get("activation_opt_in") is True:
                result["activation"] = _printed(learn.promote, True, "reflect-learned", learn.START_WEIGHT)
                result["demotion"] = _printed(learn.demote, True)
            return result
        if name == "learn_promote":
            return _printed(learn.promote, True, "reflect-learned", learn.START_WEIGHT)
        if name == "learn_demote":
            return _printed(learn.demote, True)
        if name == "learn_voice":
            return _printed(learn.build_voice_text, args["name"], args["sample"])
        if name == "learn_confirm":
            return _printed(learn.confirm_text, args["text"])
        return _printed(learn.decay_local)
    if name == "calibrate_compare":
        weights, human_words, ai_words = calibrate.excess_weights_from_texts(args["human"], args["ai"])
        return {"weights": weights, "human_words": human_words, "ai_words": ai_words,
                "rules_activated": False, "quality_accuracy_established": False}
    if name == "calibrate_selftest":
        return _printed(calibrate.selftest)
    if name == "version":
        if args.get("check_for_updates", False):
            return version_check.check()
        return {"local": version_check.local_version(), "latest": None,
                "checked": False, "update_available": False, "command": None}
    raise ValueError("Unknown workflow tool")
