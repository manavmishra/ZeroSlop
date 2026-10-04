#!/usr/bin/env python3
"""build_plugin — mirror the root skill into skills/zero-slop/ for plugin installs.

Two install conventions want two different layouts:

  * the skills CLI, a direct `git clone`, and claude.ai zip uploads read the
    skill from the repository root (`SKILL.md` beside `references/`);
  * the Claude Code / Cowork plugin system reads `skills/<name>/SKILL.md`,
    because one plugin may ship several skills.

Rather than maintain two copies by hand — which drifts the moment someone
edits one and forgets the other — the root is the single source of truth and
this script regenerates the nested copy. CI runs it with --check so a pull
request that edits the root without rebuilding fails loudly.

    python3 scripts/build_plugin.py            # rebuild the mirror
    python3 scripts/build_plugin.py --check    # verify it is current (CI)
"""
import argparse
import filecmp
import json
import re
import stat
import sys
from pathlib import Path
from safeio import atomic_write_bytes, is_within

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "skills" / "zero-slop"
# What constitutes the skill. Docs, benchmarks and manifests stay at the root:
# a plugin payload should carry the runtime, not the marketing.
ITEMS = ["SKILL.md", "references", "scripts", "data"]
# Never mirror personal state, caches, or maintainer/build utilities. The plugin
# carries only files the installed skill can execute at runtime.
EXCLUDE = {
    "voices", "__pycache__", "build_plugin.py", "build_bundle.py",
    "build_onepager_pdf.py", "build_skill_zip.py", "check_svg.py",
    # A maintainer check against GitHub and npm, not something an installed
    # skill should carry or run.
    "check_distribution_manifests.py", "check_release_version.py",
    "check_release_surfaces.py",
    "contextual.py", "contextual-signals.md", ".DS_Store",
    "make-readme-gif.mjs", "growth-snapshot.mjs", "build_marketplace_package.py",
}
# Host execution adapters are not part of the portable ten-module runtime.
# Keep this separate from maintainer exclusions and add it only to Anthropic.
MCP_RUNTIME = frozenset({"mcp_stdio.py", "mcp_local_tools.py", "mcp_workflow_tools.py"})

ANTHROPIC_OVERLAY = Path("distribution/host-overlays/anthropic")
LOCAL_TOOL_PREFIX = "mcp__plugin_zero-slop_zero-slop-local__"
_PYTHON_COMMAND = re.compile(
    r"\bpython(?:3)?[ \t]+(?:<skill-root>/|\./)?scripts/"
    r"(?P<module>[a-z_]+)\.py(?P<args>(?:[^\n`\\]|\\\r?\n[ \t]*)*)"
)
_INLINE_COMMAND = re.compile(
    r"(?<![/\w])(?P<module>slopscore|register|reader_review|predictability|"
    r"rerank|rescue|learn|calibrate|version_check)\.py"
    r"(?P<args>[ \t]+--[^`\n]*)"
)
_UNROUTED_COMMAND = re.compile(
    r"\bpython[0-9.]*[^\n`]*scripts/[a-z_]+\.py|(?<![/\w])[a-z_]+\.py[ \t]+--"
)


def _bounded_source(root, relative):
    """Read a fixed, bounded source template; never follow a package symlink."""
    root = Path(root).absolute()
    path = root / relative
    if (any(p.is_symlink() for p in (path, *path.parents))
            or not is_within(path, root) or not path.is_file()
            or path.stat().st_size > 1024 * 1024):
        raise ValueError("missing or unsafe Anthropic overlay source")
    return path.read_bytes()


def _overlay_source(root, name):
    return _bounded_source(root, ANTHROPIC_OVERLAY / name)


def _route_commands(text, routes, tool_names):
    """Route examples without executing them or replacing editorial behavior."""
    def replace(match):
        module, arguments = match.group("module", "args")
        route = routes.get(module)
        if not isinstance(route, dict):
            raise ValueError(f"unrouted Python helper: {module}")
        arguments = re.sub(r"\\\r?\n[ \t]*", " ", arguments).strip()
        arguments = arguments.split("#", 1)[0].strip()
        flags = set(re.findall(r"--[a-z][a-z-]*", arguments))
        if flags - set(route["flags"]):
            raise ValueError(f"unrouted {module} options: {sorted(flags - set(route['flags']))}")
        maintenance = flags.intersection(route.get("maintainer_flags", []))
        if maintenance:
            return f"maintainer-only {module} check (not an installed MCP operation)"
        choices = [rule["tool"] for rule in route["select"]
                   if rule.get("flag") in flags or
                   rule.get("command") == arguments.split(" ", 1)[0]]
        if len(choices) > 1:
            raise ValueError(f"ambiguous {module} operation")
        selected = choices[0] if choices else route.get("default")
        if selected not in tool_names:
            raise ValueError(f"missing declared local tool: {selected}")
        arguments = re.sub(r"\s+>\s*(\S+)", r"; save returned output as \1", arguments)
        return (f"MCP tool {LOCAL_TOOL_PREFIX}{selected}" +
                (f"; example inputs: {arguments}" if arguments else ""))

    routed = _PYTHON_COMMAND.sub(replace, text)
    routed = _INLINE_COMMAND.sub(replace, routed)
    if _UNROUTED_COMMAND.search(routed):
        raise ValueError("unrouted installed helper command")
    return routed


def anthropic_payload(root, canonical_files, tools):
    """Pure Anthropic-folder overlay; callers must archive canonical files instead.

    Canonical runtime files, other-host routing and the OpenAI ZIP stay host-free.
    Tool descriptors must come from the real local adapter, not a stub inventory.
    """
    routes = json.loads(_overlay_source(root, "routing.json"))
    if not isinstance(routes, dict) or routes.get("schema") != 1:
        raise ValueError("invalid Anthropic routing schema")
    if not isinstance(tools, (list, tuple)):
        raise ValueError("local tool descriptors must be a sequence")
    names = [tool.get("name") for tool in tools if isinstance(tool, dict)]
    if (len(names) != len(tools) or not all(isinstance(name, str) for name in names)
            or len(set(names)) != len(names)):
        raise ValueError("invalid or duplicate local tool descriptors")
    required = set(routes["required_tools"])
    if not required <= set(names):
        raise ValueError("missing declared local tools: " + ", ".join(sorted(required - set(names))))
    files = dict(canonical_files)
    server = "skills/zero-slop/scripts/mcp_stdio.py"
    for name in sorted(MCP_RUNTIME):
        target = "skills/zero-slop/scripts/" + name
        if target in files:
            raise ValueError("local adapter leaked into the canonical runtime payload")
        files[target] = _bounded_source(root, Path("scripts") / name)
    config = json.loads(_overlay_source(root, ".mcp.json"))
    remote = json.loads(files[".mcp.json"])
    if (remote != {"mcpServers": {"zero-slop": {"type": "http", "url": "https://mcp.zero-slop.ai/mcp"}}}
            or config["mcpServers"].get("zero-slop") != remote["mcpServers"]["zero-slop"]
            or config["mcpServers"].get("zero-slop-local") != {
                "command": "python3", "args": ["-B", "${CLAUDE_PLUGIN_ROOT}/" + server]}
            or set(config) != {"mcpServers"}
            or set(config["mcpServers"]) != {"zero-slop", "zero-slop-local"}):
        raise ValueError("unexpected Anthropic MCP configuration")
    intro = _overlay_source(root, "local-routing.md").decode("utf-8")
    for name, content in canonical_files.items():
        if name.startswith("skills/zero-slop/") and name.endswith(".md"):
            text = _route_commands(content.decode("utf-8"), routes["modules"], set(names))
            for wording in routes.get("wording", []):
                if wording["file"] == name:
                    if text.count(wording["before"]) != 1:
                        raise ValueError("Anthropic wording source changed")
                    text = text.replace(wording["before"], wording["after"], 1)
            if name == "skills/zero-slop/SKILL.md":
                anchor = "# Zero Slop\n"
                if text.count(anchor) != 1:
                    raise ValueError("Anthropic skill heading is missing or ambiguous")
                text = text.replace(anchor, anchor + "\n" + intro + "\n", 1)
            files[name] = text.encode("utf-8")
    files[".mcp.json"] = (json.dumps(config, indent=2) + "\n").encode("utf-8")
    return dict(sorted(files.items()))


def wanted(src: Path):
    return [p for p in src.rglob("*")
            if p.is_file() and not p.is_symlink()
            and not any(part in EXCLUDE for part in p.parts)
            and not (src.name == "scripts" and p.parent == src and p.name in MCP_RUNTIME)]


def build(check=False):
    stale, copied = [], 0
    if DEST.is_symlink() or not is_within(DEST, ROOT):
        print(f"refusing plugin destination outside the repository: {DEST}")
        return 1
    missing = []
    for item in ITEMS:
        source = ROOT / item
        expected = source.is_file() if item == "SKILL.md" else source.is_dir()
        if not expected or source.is_symlink():
            missing.append(item)
    if missing:
        print("plugin source is incomplete or unsafe: " + ", ".join(missing))
        return 1
    DEST.mkdir(parents=True, exist_ok=True)
    destination_links = sorted(
        (path for path in DEST.rglob("*") if path.is_symlink()),
        key=lambda path: len(path.parts), reverse=True,
    )
    if destination_links and check:
        stale.extend(str(path.relative_to(ROOT)) + " (symlink)"
                     for path in destination_links)
    elif destination_links:
        for path in destination_links:
            path.unlink()
    live = set()
    for item in ITEMS:
        src = ROOT / item
        if src.is_file():
            pairs = [(src, DEST / item)]
        else:
            links = [path for path in src.rglob("*") if path.is_symlink()]
            if links:
                print(f"refusing symlinked plugin source: {links[0]}")
                return 1
            pairs = [(p, DEST / p.relative_to(ROOT)) for p in wanted(src)]
        for s, d in pairs:
            live.add(d)
            if check:
                unsafe_parent = any(parent.is_symlink()
                                    for parent in d.parents if parent != DEST.parent)
                if (d.is_symlink() or unsafe_parent or not d.exists()
                        or not filecmp.cmp(s, d, shallow=False)):
                    stale.append(str(d.relative_to(ROOT)))
            else:
                d.parent.mkdir(parents=True, exist_ok=True)
                atomic_write_bytes(d, s.read_bytes(),
                                   mode=stat.S_IMODE(s.stat().st_mode))
                copied += 1
    # anything in the mirror that no longer exists at the root is stale
    if DEST.exists():
        for p in DEST.rglob("*"):
            if (p.is_file() or p.is_symlink()) and p not in live:
                if check:
                    stale.append(str(p.relative_to(ROOT)) + " (orphan)")
                else:
                    p.unlink()
        if not check:
            # Remove directories left empty when a source subtree is retired.
            # Deepest-first order keeps the mirror free of obsolete names.
            directories = sorted(
                (p for p in DEST.rglob("*") if p.is_dir() and not p.is_symlink()),
                key=lambda p: len(p.parts),
                reverse=True,
            )
            for directory in directories:
                if not any(directory.iterdir()):
                    directory.rmdir()
    if check:
        if stale:
            print("plugin mirror is out of date:")
            for s in stale:
                print("  -", s)
            print("\nrun: python3 scripts/build_plugin.py")
            return 1
        print("plugin mirror is current")
        return 0
    print(f"mirrored {copied} files into skills/zero-slop/")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    return build(check=args.check)


if __name__ == "__main__":
    sys.exit(main())
