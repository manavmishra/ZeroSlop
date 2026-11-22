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

## Preparing API-native web-policy replays

`web_policy_replay.mjs` performs no inference. It snapshots the pinned website entrypoint and its local imports, adds temporary exports without changing the original source file, and invokes the real packet/protection functions. It prepares verbatim policy text, API-native packets, model response schema and hash receipts. `check` reuses the actual provider parser and local response validator; it distinguishes rejected or missing responses from accepted text. Acceptance is not proof of semantic fidelity.

```sh
node bench/blind-20261122/web_policy_replay.mjs prepare \
  --repo /absolute/path/website-checkout --revision FULL_COMMIT \
  --input /absolute/path/unlabeled-input.json --out /absolute/path/new-preparation \
  --contract structured --batch-size 4
node bench/blind-20261122/web_policy_replay.mjs check \
  --prepared /absolute/path/new-preparation \
  --responses /absolute/path/recorded-host-responses.json \
  --out /absolute/path/local-validation.json
```

Use `--contract plaintext` for the published plaintext response policy. The response file contains `responses`, each with `id` and the exact `provider_response` string; the outer envelope is a benchmark transport, not the website API. Prepared cases deliberately use empty diagnostics in both policy arms. They do not expose the full skill experiment's author fact notes or voice brief, because those fields are absent from the actual API packet. Keep the experiments separate.

The Codex replay embeds the exact `SYSTEM_PROMPT` in a user-level benchmark request. It cannot reproduce the provider's system-message priority, backend, seed or hosted limits. This adapter also does not run the gateway's routing, scoring, quota, fallback or final status policy. Calling it a complete gateway or SaaS replay would be incorrect. The pinned source hashes and saved random protected-token maps bind the exact policy packets that were prepared.

Preflight used the actual pinned website source at `15f6cd09825ad3c8fee94fb3325f6aeb5046a515` and prototype `d90b6c4372cf5169fc1a7aa9464929c935347820`: manually constructed fictional fixture responses tested plaintext restoration, structured keep and rejection of an invented quote. These fixtures were not model generations or product benchmark results.

## Actual offline gateway policy replay

`gateway_policy_replay.mjs` now supplies the separate full local policy adapter. It archives the pinned gateway and scorer, bundles the actual pipeline, executes the real Python scorer and captures the actual gateway editor envelope. It then uses the real pinned website packet/protection/parser functions and replays captured host responses through actual gateway selection. Production fetches are disabled. The public signing fixture is only used locally; it is not an API credential or production quota bypass.

```sh
node bench/blind-20261122/gateway_policy_replay.mjs prepare \
  --core-repo /absolute/path/core --core-revision FULL_CORE_COMMIT \
  --web-repo /absolute/path/website --web-revision FULL_WEB_COMMIT \
  --input /absolute/path/unlabeled-input.json --out /absolute/path/new-preparation \
  --contract structured --batch-size 4
python3 bench/blind-20261122/run_gateway_replay.py \
  --arms /absolute/path/prepared-arms.json --suite /absolute/path/new-run \
  --timeout 600 --workers 2
```

`prepared-arms.json` is a list of objects with `name` and `prepared` paths. Preparation does not call a model. The run command does call the existing Codex account and must wait for the coordinator's explicit candidate freeze before confirmation. Only actual gateway-requested cases enter inference. Baseline early-clear cases retain their genuine no-call result. The scheduler is block/arm round-robin, with a common host model/settings/schema/budget and no tools or automatic retries. Every output is retained even when a website validator rejects it; the actual gateway then handles that rejection. Evaluator input appears in `evaluation-runs.json`; raw provider strings, host traces and receipts remain separate.

For a reviewed code-only validation change, `prepare --protocol-cache /absolute/path/previous-preparation` can reuse realized token maps. It requires the same editorial policy, exact native diagnostic context, identical canonical source-protection coverage and identical user packets. Compare whole batch prompt hashes before sharing an existing model generation. This is transparent generation reuse, not a second independent observation.

`run_panel.py` handles the separate twelve-case/four-arm portable panel. Pass `--corpus`, `--arms`, `--selection` and `--suite`; frozen selection IDs/order and seed are checked before execution. It uses deterministic arm permutations within each four-case block, fresh runtimes and two workers. All references remain included. These full-context skill results must not be pooled with the API-native product comparison.

See `CONFIRMATION-PROPOSAL.md` for the accepted focused scope. The declined seven-arm/sixty-case proposal is retained only as history.
