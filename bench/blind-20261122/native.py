"""Fixed operating points on the development set; no authorship claims."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bench"))
import pinned_runtime

parser = argparse.ArgumentParser()
parser.add_argument("--corpus", required=True, type=Path)
parser.add_argument("--avoid-root", required=True, type=Path)
parser.add_argument("--candidate-revision", default="HEAD")
args = parser.parse_args()
raw = args.corpus.read_bytes()
drafts = json.loads(raw)["drafts"]
pinned_runtime.COMMITS.update({"2.12.40": "42e4c952de7216ae915270b8cb0658ec08857650",
                               "2.12.41": "cd8429d079b867270964e9ea8d0b8d500cdc7849"})
candidate_commit = subprocess.check_output(
    ["git", "rev-parse", f"{args.candidate_revision}^{{commit}}"], cwd=ROOT, text=True).strip()
pinned_runtime.COMMITS["candidate"] = candidate_commit
methods = {}
receipts = {}
with tempfile.TemporaryDirectory(prefix="zs-native-comparison-") as temporary:
    for version in ("2.12.13", "2.12.40", "2.12.41", "candidate"):
        root = pinned_runtime.populate(Path(temporary) / version, version)
        receipts[version] = {"commit": pinned_runtime.COMMITS[version],
                             "files": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                                       for name in sorted(pinned_runtime.PINNED_FILES)},
                             "private_learning": "empty per-runtime location"}
        module = pinned_runtime.scorer(root, "native_" + version.replace(".", "_"))
        data = module.load_patterns()
        methods[version] = []
        for draft in drafts:
            result = module.score_text(draft["text"], data)
            methods[version].append({"id": draft["id"], "score": result["ai_likelihood"],
                                     "flagged": result["ai_likelihood"] >= 25,
                                     "findings": result["hits"]})

avoid_root = args.avoid_root.resolve()
subprocess.run(["git", "-C", str(avoid_root), "diff", "--exit-code", "HEAD", "--", "detector"],
               check=True, capture_output=True)
receipts["avoid-current-published-gate"] = {
    "commit": subprocess.check_output(["git", "-C", str(avoid_root), "rev-parse", "HEAD"], text=True).strip(),
    "detector_files": {str(path.relative_to(avoid_root)): hashlib.sha256(path.read_bytes()).hexdigest()
                       for path in sorted((avoid_root / "detector").rglob("*.js"))},
    "private_learning": "not used by this detector"}
script = r"""
const fs = require('node:fs');
const detector = require(process.argv[1] + '/detector/patterns.js');
const rows = JSON.parse(fs.readFileSync(0,'utf8'));
console.log(JSON.stringify(rows.map(row => {
  const result = detector.analyzeText(row.text,{contextMode:'technical',sourceMode:'rendered-markdown'});
  return {id:row.id,score:result.score,issues:result.issues.length,flagged:result.issues.length>6,
          declined:Boolean(result.tooShort || result.tooLong),findings:result.issues};
})));
"""
methods["avoid-current-published-gate"] = json.loads(subprocess.check_output(
    ["node", "-e", script, str(args.avoid_root.resolve())], input=json.dumps(drafts), text=True))
labels = {row["id"]: row["expected_label"] == "slop" for row in drafts}
summaries = {}
for name, rows in methods.items():
    counts = {"tp": 0, "tn": 0, "fp": 0, "fn": 0}
    for row in rows:
        expected, predicted = labels[row["id"]], row["flagged"]
        counts[("t" if expected == predicted else "f") + ("p" if predicted else "n")] += 1
    summaries[name] = counts
print(json.dumps({"scope": "Synthetic editorial-quality development labels, not AI provenance or field accuracy",
                  "corpus_sha256": hashlib.sha256(raw).hexdigest(),
                  "operating_points": {"zero_slop": "default non-formal score>=25",
                                       "avoid": "published CLI count>6, technical/rendered-markdown"},
                  "runtime_receipts": receipts, "summaries": summaries, "rows": methods}, indent=2))
