# Contributing to Zero Slop

Zero Slop is a portable Agent Skill with a small, offline runtime. Useful
contributions are narrow, source-preserving, and reproducible.

## Before you start

- Use an issue form for bugs, false positives, and feature proposals.
- Do not paste confidential drafts, private learning data, credentials, or
  personal voice profiles into an issue.
- Keep all workflow wording harness-neutral. Claude Code and Codex are examples,
  not limits.
- Do not treat the writing score as an authorship detector.

For a new or changed pattern, include real examples that should trigger and
controls that must stay quiet. Shared patterns are reviewed rules; private
preferences belong under `$ZERO_SLOP_HOME`.

## Development

There is no build step. Python 3 and Node.js are enough to run the full checks.

```sh
python3 tests/test_all.py
python3 scripts/calibrate.py --selftest
python3 scripts/register.py --selftest
python3 bench/make_charts.py --check
python3 scripts/build_plugin.py --check
python3 scripts/build_bundle.py --check
python3 scripts/build_skill_zip.py --check
```

Validate the pattern files directly:

```sh
python3 -c "import json; json.load(open('data/patterns.json')); json.load(open('data/learned.json'))"
```

If your change affects the published package, also run:

```sh
npm pack --dry-run
```

## Pull requests

Keep a pull request focused on one problem. Explain the failure before the
change, show the smallest reproduction, and report the commands you ran.

Runtime changes must preserve the security contract in [`SECURITY.md`](SECURITY.md):
drafts stay local, optional version checks are the only metadata request, and
runtime code does not use `eval`, `exec`, pickle, or subprocess execution.

By contributing, you agree that your work may be distributed under the
repository's [MIT License](LICENSE).
