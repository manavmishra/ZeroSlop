"""Fixed text adapters for existing checks and explicitly approved private learning.

No caller-selected paths, commands or credentials. Only the version tool can
request existing public release metadata; no drafts or private state are sent.
"""
import json
import math
import re

import reader_review
import register
import slopscore
import mcp_workflow_tools as workflow

MAX_TEXT = 20000
MAX_DEPTH = 12
MAX_ITEMS = 1000
MAX_NODES = 20000
MAX_MESSAGE_BYTES = 128 * 1024


class InputError(ValueError):
    """The tool input is outside the supported bounded contract."""


class UnknownTool(InputError):
    """A tool name is not in the fixed registry."""


class PacketError(InputError):
    """A produced packet cannot be supplied intact to a continuation."""


def bounded(value, depth=0, budget=None, *, allow_floats=False):
    """Validate finite JSON data, including nested helper packets."""
    budget = [MAX_NODES] if budget is None else budget
    budget[0] -= 1
    if depth > MAX_DEPTH or budget[0] < 0:
        raise InputError("Input structure exceeds the supported bound")
    if value is None or type(value) in (bool, int):
        return
    if type(value) is float and allow_floats and math.isfinite(value):
        return
    if isinstance(value, str):
        if len(value) > MAX_TEXT:
            raise InputError("Text exceeds 20000 characters")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise InputError("Text must be valid UTF-8") from exc
        return
    if isinstance(value, (dict, list)):
        if len(value) > MAX_ITEMS:
            raise InputError("Collection exceeds 1000 items")
        if isinstance(value, dict):
            for key, item in value.items():
                if not isinstance(key, str):
                    raise InputError("Object keys must be strings")
                bounded(key, depth + 1, budget, allow_floats=allow_floats)
                bounded(item, depth + 1, budget, allow_floats=allow_floats)
        else:
            for item in value:
                bounded(item, depth + 1, budget, allow_floats=allow_floats)
        return
    raise InputError("Only strings, integers, booleans, null and JSON collections are supported")


TEXT = {"type": "string", "maxLength": MAX_TEXT}
OBJECT = {"type": "object"}
BOOLEAN = {"type": "boolean"}


def _tool(name, title, description, properties, required):
    return {"name": name, "title": title, "description": description,
            "inputSchema": {"type": "object", "properties": properties,
                            "required": required, "additionalProperties": False},
            "annotations": {"readOnlyHint": True, "destructiveHint": False,
                            "idempotentHint": True, "openWorldHint": False}}


CORE_TOOLS = [
    _tool("score", "Check writing", "Offline heuristic check; not an authorship or completed editorial verdict. Reads bundled rules and existing private rules without writing notes.",
          {"text": TEXT, "formal": BOOLEAN,
           "genre": {"type": "string", "maxLength": 64},
           "voice": {"type": "string", "minLength": 1, "maxLength": 64, "pattern": "^[A-Za-z0-9._-]+$"}}, ["text"]),
    _tool("fidelity", "Compare source details", "Compare supplied original and rewrite for protected details. Does not certify semantic equivalence; no adjudication bypass.",
          {"original": TEXT, "rewrite": TEXT, "adjudication": OBJECT}, ["original", "rewrite"]),
    _tool("register_measure", "Measure document register", "Return existing document-level register measurements; contextual review remains required.", {"text": TEXT}, ["text"]),
    _tool("register_read", "Prepare final-review questions", "Prepare existing source-bound editorial questions. The host supplies contextual answers; this tool does not invent them.", {"text": TEXT}, ["text"]),
    _tool("register_verdict", "Validate final-review answers", "Validate supplied answers and coverage against the exact text using existing gates.", {"text": TEXT, "answers": OBJECT}, ["text", "answers"]),
    _tool("register_delta", "Compare wording changes", "Return existing source-to-rewrite changes for contextual review.", {"original": TEXT, "rewrite": TEXT}, ["original", "rewrite"]),
    _tool("reader_prepare", "Prepare audience review", "Prepare exact-source passage packets for an explicit simulated audience review. No inference or proof of context isolation.", {"text": TEXT, "audience": {"type": "string", "maxLength": 2000}}, ["text", "audience"]),
    _tool("reader_skim", "Prepare opening preview", "Return a bounded preview from a validated manifest, not a reader reaction.", {"manifest": OBJECT}, ["manifest"]),
    _tool("reader_next", "Prepare next review passage", "Return the next passage and supplied prior notes. Context isolation is the caller's responsibility; defaults to retrospective.",
          {"manifest": OBJECT, "reader": {"type": "string", "enum": ["R1", "R2"]}, "notes": OBJECT,
           "context_mode": {"type": "string", "enum": ["sequential", "retrospective"]}}, ["manifest", "reader"]),
    _tool("reader_recall", "Prepare notes-only follow-up", "Return a validated notes-only packet after a reader finishes or stops; not evidence of human memory.", {"manifest": OBJECT, "reader": {"type": "string", "enum": ["R1", "R2"]}, "notes": OBJECT}, ["manifest", "reader", "notes"]),
    _tool("reader_report", "Validate simulated review report", "Return JSON or escaped standalone HTML for validated supplied reader journals and skim review; no inference, learning, file output or human-feedback claim.",
          {"manifest": OBJECT, "reviews": {"type": "array", "minItems": 2, "maxItems": 2, "items": OBJECT}, "skim_review": OBJECT, "previous": OBJECT,
           "format": {"type": "string", "enum": ["json", "html"]}}, ["manifest", "reviews", "skim_review"]),
]

# Static source-defined registration only. No import path, tool name or
# dispatcher is supplied by a request. Duplicate names fail at startup.
TOOLS = CORE_TOOLS + workflow.EXTRA_TOOLS
WORKFLOW_NAMES = frozenset(tool["name"] for tool in workflow.EXTRA_TOOLS)
if len({tool["name"] for tool in TOOLS}) != len(TOOLS):
    raise ValueError("Duplicate fixed tool names")


def _validate_schema(value, schema):
    kind = schema["type"]
    valid = {"string": isinstance(value, str), "boolean": type(value) is bool,
             "object": isinstance(value, dict), "array": isinstance(value, list),
             "integer": type(value) is int,
             "number": type(value) is int or type(value) is float and math.isfinite(value)}[kind]
    if not valid:
        raise InputError("Argument type does not match the tool schema")
    if "enum" in schema and value not in schema["enum"]:
        raise InputError("Unsupported argument choice")
    if "const" in schema and (type(value) is not type(schema["const"]) or value != schema["const"]):
        raise InputError("Required consent or constant argument is missing")
    if kind == "string" and len(value) > schema.get("maxLength", MAX_TEXT):
        raise InputError("Argument text exceeds the supported bound")
    if kind == "string" and (len(value) < schema.get("minLength", 0) or
                              "pattern" in schema and re.fullmatch(schema["pattern"], value) is None):
        raise InputError("Argument text does not match the supported format")
    if kind in ("integer", "number"):
        if "minimum" in schema and value < schema["minimum"] or "maximum" in schema and value > schema["maximum"]:
            raise InputError("Argument number exceeds the supported bound")
    if kind == "object":
        if not schema.get("minProperties", 0) <= len(value) <= schema.get("maxProperties", MAX_ITEMS):
            raise InputError("Argument object exceeds the supported bound")
        properties = schema.get("properties", {})
        if not set(schema.get("required", ())) <= set(value):
            raise InputError("Missing object fields")
        for key, item in value.items():
            if key in properties:
                _validate_schema(item, properties[key])
            elif schema.get("additionalProperties", True) is False:
                raise InputError("Unsupported object fields")
            elif isinstance(schema.get("additionalProperties"), dict):
                _validate_schema(item, schema["additionalProperties"])
            else:
                # Untyped packets do not gain numeric coercion. Numeric helper
                # inputs must declare an explicit schema for those values.
                bounded(item)
    if kind == "array":
        if not schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", MAX_ITEMS):
            raise InputError("Argument collection exceeds the supported bound")
        for item in value:
            _validate_schema(item, schema["items"])


def tool_spec(name):
    """Resolve only reviewed, code-defined tool names."""
    spec = next((tool for tool in TOOLS if tool["name"] == name), None)
    if spec is None:
        raise UnknownTool("Unknown tool")
    return spec


def validate_arguments(spec, arguments):
    if not isinstance(arguments, dict):
        raise InputError("Arguments must be an object")
    bounded(arguments, allow_floats=True)
    schema = spec["inputSchema"]
    if set(arguments) - set(schema["properties"]) or not set(schema["required"]) <= set(arguments):
        raise InputError("Missing or unsupported arguments")
    for key, value in arguments.items():
        _validate_schema(value, schema["properties"][key])


def _reader_packet(manifest):
    """Reject an unusable producer result, never truncate source passages.

    Preflight the same bounded params tree and compact UTF-8 wire encoding used
    by the consumer. Later journals still share this per-request wire ceiling.
    """
    params = {"name": "reader_next", "arguments": {"manifest": manifest, "reader": "R1", "context_mode": "retrospective"}}
    try:
        bounded(params)
        # A 200-character control-string ID is the largest JSON representation
        # of the permitted ID text, including its escaped UTF-8 wire bytes.
        continuation = {"jsonrpc": "2.0", "id": "\x00" * 200, "method": "tools/call", "params": params}
        if len((encode(continuation) + "\n").encode("utf-8")) > MAX_MESSAGE_BYTES:
            raise PacketError("Prepared packet cannot fit the continuation request")
    except InputError as exc:
        raise PacketError("Prepared packet exceeds continuation limits; text was not truncated") from exc
    return manifest


def call(name, arguments):
    """Fixed dispatch only; caller text cannot select files or commands."""
    spec = tool_spec(name)
    validate_arguments(spec, arguments)
    if name == "score":
        result = slopscore.score_text(arguments["text"], slopscore.load_patterns(voice=arguments.get("voice")), formal=arguments.get("formal", False))
        result["shape"] = slopscore.shape_metrics(arguments["text"], genre=arguments.get("genre", "general"))
        return result
    if name == "fidelity":
        adjudicated = slopscore.validate_adjudication(arguments["adjudication"], arguments["original"]) if "adjudication" in arguments else None
        return slopscore.fidelity(arguments["original"], arguments["rewrite"], adjudicated=adjudicated)
    if name == "register_measure":
        return register.measure(arguments["text"])
    if name == "register_read":
        return register.read_packet(arguments["text"], "supplied text")
    if name == "register_verdict":
        code, report = register.verdict(arguments["text"], arguments["answers"])
        return {"exit_code": code, "report": report}
    if name == "register_delta":
        return register.delta(arguments["original"], arguments["rewrite"])
    if name == "reader_prepare":
        return _reader_packet(reader_review.prepare(arguments["text"], arguments["audience"]))
    if name == "reader_skim":
        return reader_review.skim(arguments["manifest"])
    if name == "reader_next":
        return reader_review.next_passage(arguments["manifest"], arguments["reader"], arguments.get("notes"), arguments.get("context_mode", "retrospective"))
    if name == "reader_recall":
        return reader_review.recall(arguments["manifest"], arguments["reader"], arguments["notes"])
    if name == "reader_report":
        if arguments.get("format", "json") == "html":
            return {"html": reader_review.report(arguments["manifest"], arguments["reviews"], arguments["skim_review"], arguments.get("previous"))}
        return reader_review.report_data(arguments["manifest"], arguments["reviews"], arguments["skim_review"], arguments.get("previous"))
    if name in WORKFLOW_NAMES:
        # Preserve helper semantics for direct Python callers. The protocol
        # entrypoint catches SystemExit without swallowing KeyboardInterrupt.
        return workflow.call(name, arguments)
    raise UnknownTool("Unknown tool")


def jsonable(value):
    """Normalize existing helper tuples/sets without changing gate decisions."""
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    if isinstance(value, set):
        return sorted(jsonable(item) for item in value)
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    return value


def encode(value):
    return json.dumps(jsonable(value), ensure_ascii=False, allow_nan=False, separators=(",", ":"))
