#!/usr/bin/env python3
"""Create method-hidden A/B packets and run two fresh editorial reviews."""
import argparse
import datetime as dt
import hashlib
import json
import random
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CORPUS = ROOT / "bench" / "search-corpus" / "corpus.json"
SCHEMA = HERE / "judgment-schema.json"
DEFAULT_CODEX = Path("/Applications/ChatGPT.app/Contents/Resources/codex")
METHODS = ("zero-slop", "avoid-ai-writing")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prompt(rows):
    return f"""You are an independent editorial reviewer in a controlled A/B test.

The methods behind A and B are deliberately withheld. Do not infer or discuss them.
For each item, compare both edits with the source and choose A, B, or tie.

Use this fixed order of importance:
1. Source preservation: retain every claim, name, number, qualification, intended
   point, and legitimate format. Added facts or changed meaning are serious faults.
2. Naturalness: remove canned, templated, performatively punchy, or assistant-like
   prose without flattening the writer into clipped generic copy.
3. Clarity and cohesion: make the argument easy to follow and appropriately shaped
   for its genre.
4. Mechanics: grammar, spelling, punctuation, and consistency.

Do not reward an edit for being longer, shorter, or more aggressive. If one version
changes source meaning and the other does not, the source-preserving version wins.
Use tie only when neither has a material editorial advantage. Give a concise,
text-specific reason. Score each dimension from 1 (poor) to 5 (excellent).
Return only the required JSON, in the supplied order.

Items:
{json.dumps(rows, ensure_ascii=False, indent=1)}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--passes", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=3)
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--reasoning", default="high")
    parser.add_argument("--codex", type=Path, default=DEFAULT_CODEX)
    args = parser.parse_args()
    if args.passes != 2:
        parser.error("the published protocol requires exactly two passes")

    corpus = json.loads(CORPUS.read_text())
    outputs = {
        method: json.loads((HERE / "outputs" / f"{method}.json").read_text())
        for method in METHODS
    }
    expected = [row["id"] for row in corpus]
    if any(list(outputs[method]) != expected for method in METHODS):
        raise SystemExit("rewrite outputs do not match the frozen corpus")

    records = []
    with tempfile.TemporaryDirectory(prefix="zero-slop-review-") as temporary:
        for pass_index in range(1, args.passes + 1):
            rng = random.Random(20260826 + pass_index)
            packet, mapping = [], {}
            for item in corpus:
                order = list(METHODS)
                rng.shuffle(order)
                mapping[item["id"]] = {"A": order[0], "B": order[1]}
                packet.append({
                    "id": item["id"], "genre": item["genre"],
                    "source": item["text"],
                    "A": outputs[order[0]][item["id"]],
                    "B": outputs[order[1]][item["id"]],
                })
            (HERE / "packets").mkdir(exist_ok=True)
            (HERE / "maps").mkdir(exist_ok=True)
            (HERE / "judgments").mkdir(exist_ok=True)
            packet_path = HERE / "packets" / f"pass-{pass_index}.json"
            map_path = HERE / "maps" / f"pass-{pass_index}.json"
            packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=1) + "\n")
            map_path.write_text(json.dumps(mapping, indent=1) + "\n")
            judgments = []
            batches = []
            for offset in range(0, len(packet), args.batch_size):
                selected = packet[offset:offset + args.batch_size]
                request = prompt(selected)
                response = Path(temporary) / f"pass-{pass_index}-{offset}.json"
                command = [
                    str(args.codex), "exec", "-m", args.model,
                    "-c", f'model_reasoning_effort="{args.reasoning}"',
                    "-s", "read-only", "--ephemeral", "--ignore-user-config",
                    "--ignore-rules", "--skip-git-repo-check",
                    "--output-schema", str(SCHEMA),
                    "-o", str(response), "-C", str(temporary), "-",
                ]
                completed = subprocess.run(command, input=request, text=True)
                if completed.returncode:
                    raise SystemExit(completed.returncode)
                rows = json.loads(response.read_text())["judgments"]
                ids = [row["id"] for row in selected]
                if [row.get("id") for row in rows] != ids:
                    raise SystemExit(f"review output does not cover {ids} in order")
                judgments.extend(rows)
                batches.append({
                    "ids": ids,
                    "prompt_sha256": hashlib.sha256(request.encode()).hexdigest(),
                    "response_sha256": sha(response),
                })
            judgment_path = HERE / "judgments" / f"pass-{pass_index}.json"
            judgment_path.write_text(
                json.dumps({"judgments": judgments}, ensure_ascii=False, indent=1) + "\n"
            )
            records.append({
                "pass": pass_index, "seed": 20260826 + pass_index,
                "packet_sha256": sha(packet_path), "mapping_sha256": sha(map_path),
                "judgment_sha256": sha(judgment_path), "batches": batches,
            })
    run = {
        "schema": 1, "result_kind": "method_hidden_editorial_review_run",
        "model": args.model, "reasoning_effort": args.reasoning,
        "batch_size": args.batch_size,
        "codex_cli": subprocess.run([str(args.codex), "--version"], capture_output=True,
                                     text=True, check=True).stdout.strip(),
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "corpus_sha256": sha(CORPUS), "passes": records,
        "limits": "The method labels are withheld and positions reshuffled per pass; hosted inference seeds are not exposed.",
    }
    (HERE / "review-run.json").write_text(json.dumps(run, indent=1) + "\n")
    print(f"wrote two method-hidden review passes under {HERE}")


if __name__ == "__main__":
    main()
