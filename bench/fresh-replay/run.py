#!/usr/bin/env python3
"""Run one pinned editing workflow through the same Codex model and corpus."""
import argparse
import datetime as dt
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CORPUS = ROOT / "bench" / "search-corpus" / "corpus.json"
SCHEMA = HERE / "schema.json"
DEFAULT_CODEX = Path("/Applications/ChatGPT.app/Contents/Resources/codex")


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def build_prompt(method_label, instruction_name, corpus):
    return f"""You are running a controlled editing benchmark for {method_label}.

Read {instruction_name} completely and use that workflow for every item below.
Do not inspect any competing skill, prior benchmark output, or evaluation result.
Edit each draft for its named genre. Preserve every supplied claim, name, number,
link, quotation, qualification, and intended point. Add no facts or personal
experience. Return only the JSON required by the response schema, in corpus order.
The `text` field must contain the finished rewrite, without a change log or report.

Corpus:
{json.dumps(corpus, ensure_ascii=False, indent=1)}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--instruction", default="SKILL.md")
    parser.add_argument("--revision", required=True)
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--reasoning", default="high")
    parser.add_argument("--batch-size", type=int, default=3)
    parser.add_argument("--codex", type=Path, default=DEFAULT_CODEX)
    parser.add_argument("--suite-dir", type=Path, default=HERE,
                        help="directory for outputs/ and runs/ (default: this suite)")
    args = parser.parse_args()

    instruction = (args.root / args.instruction).resolve()
    if not instruction.is_file():
        parser.error(f"instruction file does not exist: {instruction}")
    corpus = json.loads(CORPUS.read_text())
    expected = [row["id"] for row in corpus]
    if not 1 <= args.batch_size <= len(corpus):
        parser.error("--batch-size must be between 1 and the corpus size")

    suite_dir = args.suite_dir.resolve()
    suite_dir.mkdir(parents=True, exist_ok=True)
    output_path = suite_dir / "outputs" / f"{args.method}.json"
    run_path = suite_dir / "runs" / f"{args.method}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run_path.parent.mkdir(parents=True, exist_ok=True)
    rewrites, batches = {}, []
    with tempfile.TemporaryDirectory(prefix="zero-slop-replay-") as temporary:
        for offset in range(0, len(corpus), args.batch_size):
            selected = corpus[offset:offset + args.batch_size]
            selected_ids = [row["id"] for row in selected]
            prompt = build_prompt(args.label, args.instruction, selected)
            raw_output = Path(temporary) / f"response-{offset}.json"
            command = [
                str(args.codex), "exec", "-m", args.model,
                "-c", f'model_reasoning_effort="{args.reasoning}"',
                "-s", "read-only", "--ephemeral", "--ignore-user-config",
                "--ignore-rules", "--output-schema", str(SCHEMA), "-o",
                str(raw_output), "-C", str(args.root.resolve()), "-",
            ]
            completed = subprocess.run(command, input=prompt, text=True)
            if completed.returncode:
                raise SystemExit(completed.returncode)
            payload = json.loads(raw_output.read_text())
            rows = payload.get("rewrites")
            if (not isinstance(rows, list)
                    or [row.get("id") for row in rows] != selected_ids):
                raise SystemExit(
                    f"model output does not cover batch {selected_ids} exactly in order"
                )
            for row in rows:
                rewrites[row["id"]] = row["text"].strip()
            batches.append({
                "ids": selected_ids,
                "prompt_sha256": sha256_bytes(prompt.encode()),
                "response_sha256": sha256_bytes(raw_output.read_bytes()),
            })

    if list(rewrites) != expected:
        raise SystemExit("combined model output does not cover the corpus exactly in order")
    if any(not text for text in rewrites.values()):
        raise SystemExit("model returned an empty rewrite")

    output_path.write_text(json.dumps(rewrites, ensure_ascii=False, indent=1) + "\n")
    version = subprocess.run(
        [str(args.codex), "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    record = {
        "schema": 1,
        "method": args.method,
        "label": args.label,
        "revision": args.revision,
        "model": args.model,
        "reasoning_effort": args.reasoning,
        "batch_size": args.batch_size,
        "codex_cli": version,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "instruction_sha256": sha256_bytes(instruction.read_bytes()),
        "corpus_sha256": sha256_bytes(CORPUS.read_bytes()),
        "batches": batches,
        "output_sha256": sha256_bytes(output_path.read_bytes()),
        "limits": "The model and CLI are pinned; the hosted inference settings and seed are not exposed.",
    }
    run_path.write_text(json.dumps(record, indent=1) + "\n")
    print(f"wrote {output_path} and {run_path}")


if __name__ == "__main__":
    main()
