#!/usr/bin/env python3
"""env — the SkillOpt environment that optimizes Zero Slop's SKILL.md.

This wires Zero Slop into SkillOpt's environment contract (docs/guide/new-benchmark.md):
a `run_batch` that runs a candidate skill on the task set and returns a `hard`/`soft`
score per rollout, plus the `SplitDataLoader` and `EnvAdapter` subclasses SkillOpt
loads. The scoring is delegated to reward.py; the only thing this file adds is the
rollout — running the skill's instructions on each draft to produce a rewrite.

To use it, copy this folder to `skillopt/envs/zeroslop/` in a SkillOpt checkout (or
add this directory to PYTHONPATH), point `env.skill_init` at Zero Slop's SKILL.md,
and register the adapter as the guide describes. See this folder's README.

The rollout needs an LLM — that is the one part Zero Slop does not ship, because the
skill is a set of instructions an agent follows, and running them means calling a
model. `rewrite_with_skill` uses an OpenAI-compatible endpoint from the environment
(`ZS_OPT_MODEL`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`); swap it for SkillOpt's own
model client if you prefer. Nothing here runs during normal use of the skill — this
is a maintainer/CI file, and the user-facing scorer stays offline and dependency-free.
"""
import json
import os
from pathlib import Path

import reward  # same folder; the (hard, soft) scoring lives there

HERE = Path(__file__).resolve().parent

# The instruction Zero Slop's rewrite loop follows, in one line for the rollout.
# The full method is in SKILL.md; SkillOpt is tuning exactly this text.
_TASK = ("De-slop this draft: remove the AI register while keeping every fact, "
         "name, number, quote and link exactly, and inventing nothing. Return only "
         "the rewritten text.\n\nDRAFT:\n{draft}")


def rewrite_with_skill(skill_content, draft, *, max_completion_tokens=4096):
    """Run the candidate skill on one draft and return the rewrite text.

    Reference implementation against an OpenAI-compatible API. The candidate
    SKILL.md is the system prompt — that is the whole point: SkillOpt edits it and
    watches the reward move.
    """
    try:
        from openai import OpenAI
    except ImportError as e:  # pragma: no cover - maintainer environment
        raise RuntimeError(
            "rollout needs an LLM client: `pip install openai`, or replace "
            "rewrite_with_skill with SkillOpt's model client") from e
    client = OpenAI(base_url=os.getenv("OPENAI_BASE_URL") or None)
    resp = client.chat.completions.create(
        model=os.getenv("ZS_OPT_MODEL", "gpt-4o-mini"),
        max_tokens=max_completion_tokens,
        messages=[{"role": "system", "content": skill_content},
                  {"role": "user", "content": _TASK.format(draft=draft)}],
    )
    return resp.choices[0].message.content


def run_batch(*, items, skill_content, out_root, workers=4,
              max_completion_tokens=4096):
    """SkillOpt's rollout entry point. One result dict per item:
    {'id', 'hard', 'soft'}, with the conversation persisted for inspection."""
    from concurrent.futures import ThreadPoolExecutor
    out_root = Path(out_root)

    def one(item):
        rw = rewrite_with_skill(skill_content, item["draft"],
                                max_completion_tokens=max_completion_tokens)
        s = reward.score(item["draft"], rw, item.get("genre"))
        pred = out_root / "predictions" / str(item["id"])
        pred.mkdir(parents=True, exist_ok=True)
        (pred / "conversation.json").write_text(json.dumps(
            {"id": item["id"], "draft": item["draft"], "rewrite": rw, **s}, indent=1))
        return {"id": item["id"], **s}

    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(one, items))


def _load_split(split_path):
    rows = []
    for line in Path(split_path).read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


# ---- SkillOpt base-class subclasses ----------------------------------------
# Imported lazily so this file still imports for reference without SkillOpt
# installed; the adapter only runs inside a SkillOpt checkout.
try:  # pragma: no cover - requires the skillopt package
    from skillopt.envs.base import SplitDataLoader, EnvAdapter

    class ZeroSlopDataLoader(SplitDataLoader):
        def load_split_items(self, split_path):
            return _load_split(split_path)

    class ZeroSlopAdapter(EnvAdapter):
        def build_train_env(self, batch_size, seed, **kw):
            return {"loader": ZeroSlopDataLoader(), "batch_size": batch_size}

        def build_eval_env(self, env_num, split, seed, **kw):
            return {"loader": ZeroSlopDataLoader(), "split": split}

        def rollout(self, env_manager, skill_content, out_dir, **kw):
            items = kw.get("items") or env_manager["loader"].load_split_items(
                kw["split_path"])
            return run_batch(items=items, skill_content=skill_content,
                             out_root=out_dir, workers=kw.get("workers", 4))

        def get_task_types(self):
            return ["linkedin", "blog", "social", "reddit", "newsletter",
                    "email", "research"]
except ImportError:  # SkillOpt not installed — reward.py and run_batch still work
    ZeroSlopDataLoader = ZeroSlopAdapter = None


if __name__ == "__main__":
    print("SkillOpt env for Zero Slop. Reward: reward.py · split: make_split.py")
    print("See README.md for install, registration, and run steps.")
