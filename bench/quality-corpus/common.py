"""Strict contracts shared by the blind quality packet and evaluator."""
import hashlib
import json
import re
from pathlib import Path

MAX_ITEMS = 5000
MAX_TEXT_CHARS = 100000
ID = re.compile(r"q\d{3,8}\Z")
SAFE_NAME = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
SPLITS = {"dev", "test"}
GENRES = {"general", "linkedin", "x", "email", "blog", "newsletter",
          "research", "professional", "social"}


class ContractError(ValueError):
    pass


def text_sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_json(path, label, limit=20 * 1024 * 1024):
    source = Path(path)
    if not source.is_file():
        raise ContractError(f"{label} is not a readable file: {source}")
    try:
        if source.stat().st_size > limit:
            raise ContractError(f"{label} exceeds {limit} bytes")
        return json.loads(source.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"{label} must be readable UTF-8 JSON: {exc}") from exc


def load_manifest(path):
    data = read_json(path, "manifest")
    if (not isinstance(data, dict)
            or set(data) != {"schema", "corpus_kind", "label_protocol_sha256", "items"}
            or data.get("schema") != 1
            or data.get("corpus_kind") != "blind_slop_quality_panel"
            or not re.fullmatch(r"[0-9a-f]{64}", data.get("label_protocol_sha256", ""))
            or not isinstance(data.get("items"), list)
            or not 2 <= len(data["items"]) <= MAX_ITEMS):
        raise ContractError("manifest has an invalid root contract")
    ids, source_splits = set(), {}
    expected = {"id", "source_id", "split", "genre", "method", "text", "text_sha256"}
    for index, item in enumerate(data["items"], 1):
        if not isinstance(item, dict) or set(item) != expected:
            raise ContractError(f"manifest item {index} has missing or unexpected fields")
        item_id, source_id = item["id"], item["source_id"]
        if not isinstance(item_id, str) or not ID.fullmatch(item_id) or item_id in ids:
            raise ContractError(f"manifest item {index} has an invalid or duplicate id")
        ids.add(item_id)
        if (not isinstance(source_id, str) or not SAFE_NAME.fullmatch(source_id)
                or item["split"] not in SPLITS or item["genre"] not in GENRES
                or not isinstance(item["method"], str)
                or not SAFE_NAME.fullmatch(item["method"])):
            raise ContractError(f"manifest item {index} has invalid metadata")
        if source_id in source_splits and source_splits[source_id] != item["split"]:
            raise ContractError(f"source {source_id!r} leaks across dev and test")
        source_splits[source_id] = item["split"]
        text = item["text"]
        if (not isinstance(text, str) or not text.strip()
                or len(text) > MAX_TEXT_CHARS
                or item["text_sha256"] != text_sha256(text)):
            raise ContractError(f"manifest item {index} has invalid text or hash")
    if {item["split"] for item in data["items"]} != SPLITS:
        raise ContractError("manifest must contain both dev and test items")
    return data
