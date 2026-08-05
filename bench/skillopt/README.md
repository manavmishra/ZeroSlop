# Tuning SKILL.md with SkillOpt

Zero Slop's rewrite quality is bounded by one thing: how good the instructions in
`SKILL.md` are. Microsoft's [SkillOpt](https://github.com/microsoft/SkillOpt) treats
that markdown as trainable text — it runs the skill on a task set, scores each
rewrite, proposes edits to the instructions, and keeps only the edits that strictly
improve a held-out score. This folder is everything SkillOpt needs to do that for
Zero Slop.

**This is a maintainer / CI job, not part of using the skill.** The optimizer needs
an LLM to run the rewrites, so it needs network and a model key. Nothing here runs
when someone de-slops a draft; the shipped scorer stays offline and dependency-free.
What SkillOpt produces is a better `SKILL.md` to commit — a one-time improvement to
the instructions everyone then runs locally.

## What an optimizer needs, and what Zero Slop already supplies

| SkillOpt needs | Zero Slop provides |
|---|---|
| a trainable file | `SKILL.md` — the rewrite instructions, pointed to by `env.skill_init` |
| a task set with a val split | `make_split.py` writes `data/zeroslop_split/` from the 50-draft benchmark |
| a reward per rollout | `reward.py` — `hard` (fidelity) and `soft` (de-slop quality), both in [0,1] |
| the rollout | `env.py` runs the candidate skill on each draft (the one LLM step) |
| a validation gate | SkillOpt's own: an edit is kept only if the held-out score strictly improves |

The reward is the point. Fidelity is the `hard` signal — every figure, name, quote
and link kept, nothing invented — reported *separately* from the `soft` de-slop
quality, so the optimizer cannot buy a cleaner score by dropping a fact or inventing
a detail. That just sends `hard` to zero, and SkillOpt gates on both.

## Run it now, without the optimizer

The reward runs today, offline, on the shipped skill's own benchmark rewrites — the
baseline a tuned `SKILL.md` has to beat:

```bash
python3 bench/skillopt/make_split.py     # write the train/val/test split
python3 bench/skillopt/reward.py --baseline
```

## Wire it into SkillOpt

```bash
pip install skillopt          # Python 3.10+; supports Claude / OpenAI / Azure backends
```

1. Copy this folder into the SkillOpt checkout as `skillopt/envs/zeroslop/`, or add
   it to `PYTHONPATH`.
2. Register the adapter in `scripts/train.py` and `scripts/eval_only.py`, as the
   guide shows:

   ```python
   try:
       from skillopt.envs.zeroslop.env import ZeroSlopAdapter
       _ENV_REGISTRY["zeroslop"] = ZeroSlopAdapter
   except ImportError:
       pass
   ```
3. Set a backend: `export ZS_OPT_MODEL=...`, `OPENAI_API_KEY=...` (and
   `OPENAI_BASE_URL=...` for a compatible endpoint), or replace `rewrite_with_skill`
   in `env.py` with SkillOpt's own model client.
4. Launch:

   ```bash
   python scripts/train.py --config bench/skillopt/config.yaml
   ```

SkillOpt writes a `best_skill.md`. Diff it against `SKILL.md`, run the full test
suite and `calibrate.py --selftest` against the candidate, and commit it only if the
gate, the discrimination corpus, and the must-not-flag safety corpus all still pass.
The optimizer improves the wording; those guards make sure it never improves the
score by loosening a rule that matters.

## How this relates to the reflect loop

The reflect loop (`scripts/learn.py`) and SkillOpt tune different halves of the same
skill. Reflect learns new *tells* for the detector from what writers cut — it sharpens
what the meter catches. SkillOpt tunes the *instructions* the rewrite follows — it
sharpens how the fix is made. Both are validation-gated against the same corpora, and
neither is allowed to raise a score by weakening fidelity. SkillOpt's `skillopt-sleep`
mode can run this on a schedule, the same shape as the reflect loop's nightly promote.
