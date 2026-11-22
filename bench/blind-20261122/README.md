# Matched skill-guided editing comparison

This maintainer-only harness compares pinned open-source skill workflows through one existing Codex CLI account, model and reasoning setting. It does not exercise competitor SaaS products, establish human truth, detect AI authorship, or change Zero Slop's production workflow. Historical benchmark artifacts remain unchanged.

`run.py` adapts the corpus-order checks, structured output contract and hash receipts from `bench/fresh-replay/run.py`, and the anonymous packet/mapping separation from `bench/incumbent-blind-replay/judge.py`.

## Protocol

Freeze a corpus and its SHA256, then supply an arm configuration: a JSON list of `[anonymous_internal_key, git_checkout, pinned_revision, relative_instruction_path, runtime_paths]`. A bare-host control uses `["bare-host", null, null, null, []]`. Record candidate freeze before opening any held-out set. Use a new suite directory for every attempt; the runner refuses to overwrite an existing suite.

The default run selects the first eight drafts, eight per batch, at most two concurrent calls, and a 180-second per-call timeout. Defaults are `gpt-6.2-astra` and `ultra`; explicit model changes must apply to every arm and be recorded as a different experiment. The executable path is configurable with `--codex`.

```sh
python3 bench/blind-20261122/run.py \
  --corpus /absolute/path/frozen-development.json \
  --arms /absolute/path/pinned-arms.json \
  --suite /absolute/path/new-run-directory \
  --limit 8 --batch-size 8 --workers 2 --timeout 180
```

Corpus input may be a list or an object with `drafts`. Only `id`, `genre`, `brief`, `source`, `text` and `voice_constraints` reach the editor. Labels, target spans, clean rationales and protected-span annotations do not. The same prompt and schema apply to every arm, apart from the arm's instruction path. Findings require an exact source substring and one action (`edit`, `keep`, `ask`); final text is separate. Missing or invalid output becomes a recorded failure, never an invented rewrite.

Runtime files come from `git archive` at the pinned commit. Only specified paths are copied, excluding project instructions, caches, tests and private learning. Each process receives one runtime root, its own fresh session, no user config or exec rules, read-only sandbox, and no other arm's outputs. Optional commands must be reviewed before executing a new external runtime. For the November 22 pilot, avoid-ai-writing's normalize/check-style helpers and local validation dependencies were inspected for process/network calls; no such calls were found in those dependency entrypoints. Its full `references/patterns.md` is included, and no-ai-slop includes `eval.md`. Nothing is truncated to make the time budget pass.

The prompt prohibits network, personal profiles, private learning and version checks. Read-only sandboxing does not constitute a filesystem read jail: model adherence and recorded command inspection remain necessary. A skill helper requiring writes uses its documented fallback rather than weakened sandboxing. Fresh empty private-learning state is selected through `ZERO_SLOP_HOME` and incidental notes are disabled. Existing CLI authentication is reused; the harness creates no key, signup, plan or API credential.

## Receipts and review

Each run records pinned revision, hashes for every copied runtime file, aggregate runtime hash, original corpus hash, selected input hash, model/settings, CLI version, complete command, input prompt hash, raw output hash, elapsed time, start/end times and failure reason. Raw model JSONL permits checking the commands and reference reads that actually occurred; staged-file inclusion alone is not proof that a model read a file. Hosted seeds and backend inference configuration are not exposed.

`judge-packets/anonymous.json` contains source, brief and anonymously shuffled finished texts. It omits method names, method findings, runtime roots, score labels and expectations. `private-maps/mapping.json` provides the separate unblinding map (directory mode 0700, file mode 0600). A deterministic seed makes position assignment reproducible; it does not make hosted generation deterministic. Keep mappings and raw prompts/logs outside a judge's workspace. Source identifiers are replaced by item numbers in packets. Judge packets are preparation artifacts, not judgment results.

Assess detection, editing, source fidelity and voice independently. Preserve abstentions and failures as separate outcomes. Use the preregistered source-group paired bootstrap and screen when assessing a sealed confirmation set; a small development pilot is not confirmatory evidence. Native regex meters must be reported separately from host-model skill-guided editing. Publishing requires applicable independent review and release authority.

## Local checks

```sh
python3 -m unittest discover -s bench/blind-20261122 -p 'test_*.py'
```
