#!/usr/bin/env python3
"""check_svg — catch overflow in a hand-authored SVG before it ships.

A diagram is code, and it fails the same way code does: text wider than the box
that holds it, a connector routed through a shape it is not touching, a label
past the canvas edge. None of that is visible in the source, so measure it.

    python3 scripts/check_svg.py assets/engine.svg

The font metrics assume a monospace face, where every glyph is one advance wide.
Advance ratio 0.60 of the font size is correct for SF Mono, Menlo, Consolas and
DejaVu Sans Mono, the stack the diagrams request.
"""
import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "{http://www.w3.org/2000/svg}"
ADVANCE = 0.60          # monospace glyph width as a fraction of font-size
PAD = 6                 # px of breathing room a label needs inside its box


def parse_styles(src):
    """class name -> {property: value} from the embedded <style> block."""
    out = {}
    block = re.search(r"<style>(.*?)</style>", src, re.S)
    if not block:
        return out
    # only the light-mode rules; the dark overrides do not change geometry
    body = block.group(1).split("@media")[0]
    for sel, decls in re.findall(r"\.([\w-]+)\s*\{([^}]*)\}", body):
        d = {}
        for kv in decls.split(";"):
            if ":" in kv:
                k, v = kv.split(":", 1)
                d[k.strip()] = v.strip()
        out.setdefault(sel, {}).update(d)
    return out


def font_size(cls, styles, default=12.0):
    for c in cls.split():
        fs = styles.get(c, {}).get("font-size")
        if fs:
            return float(fs.replace("px", ""))
    return default


def letter_spacing(cls, styles):
    for c in cls.split():
        ls = styles.get(c, {}).get("letter-spacing")
        if ls:
            if ls.endswith("em"):
                return float(ls[:-2]) * font_size(cls, styles)
            return float(ls.replace("px", ""))
    return 0.0


def text_width(s, cls, styles):
    fs = font_size(cls, styles)
    return len(s) * (fs * ADVANCE + letter_spacing(cls, styles))


def path_points(d):
    """Absolute M/L polyline points. Enough for orthogonal connectors."""
    pts, cur = [], None
    for cmd, args in re.findall(r"([MLHVml])\s*([-\d.,\s]*)", d):
        nums = [float(n) for n in re.findall(r"-?\d*\.?\d+", args)]
        if cmd in "ML":
            for i in range(0, len(nums) - 1, 2):
                cur = (nums[i], nums[i + 1]); pts.append(cur)
        elif cmd == "H" and cur:
            for n in nums:
                cur = (n, cur[1]); pts.append(cur)
        elif cmd == "V" and cur:
            for n in nums:
                cur = (cur[0], n); pts.append(cur)
    return pts


def seg_hits_box(p, q, box, slack=2.0):
    """Does an orthogonal segment pass through the interior of a box?"""
    x, y, w, h = box
    x0, y0, x1, y1 = x + slack, y + slack, x + w - slack, y + h - slack
    if abs(p[1] - q[1]) < 0.01:                      # horizontal
        lo, hi = sorted((p[0], q[0]))
        return y0 < p[1] < y1 and lo < x1 and x0 < hi
    if abs(p[0] - q[0]) < 0.01:                      # vertical
        lo, hi = sorted((p[1], q[1]))
        return x0 < p[0] < x1 and lo < y1 and y0 < hi
    return False


def elements(root, local_name):
    """Yield SVG elements with or without an explicit XML namespace."""
    return (node for node in root.iter()
            if node.tag.rsplit("}", 1)[-1] == local_name)


def main(path):
    try:
        src = Path(path).read_text()
        root = ET.fromstring(src)
    except (OSError, UnicodeDecodeError, ET.ParseError) as exc:
        print(f"{path}: cannot read valid SVG: {exc}")
        return 2
    if root.tag.rsplit("}", 1)[-1] != "svg":
        print(f"{path}: root element is not svg")
        return 2
    styles = parse_styles(src)
    try:
        vb = [float(v) for v in root.get("viewBox", "").split()]
        if len(vb) != 4 or vb[2] <= 0 or vb[3] <= 0:
            raise ValueError
    except ValueError:
        print(f"{path}: SVG needs a four-number, positive viewBox")
        return 2
    min_x, min_y, W, H = vb
    max_x, max_y = min_x + W, min_y + H
    problems = []

    rects = []
    for r in elements(root, "rect"):
        try:
            box = tuple(float(r.get(k, 0)) for k in ("x", "y", "width", "height"))
            if box[2] < 0 or box[3] < 0:
                raise ValueError
        except (TypeError, ValueError):
            problems.append("rectangle has invalid geometry")
            continue
        rects.append({"box": box, "cls": r.get("class", "")})
    solid = [r for r in rects if r["cls"] not in ("grp", "grl", "grt")]
    # 1. text must fit the canvas and the box it sits in
    for t in elements(root, "text"):
        s = "".join(t.itertext())
        cls = t.get("class", "")
        try:
            x, y = float(t.get("x")), float(t.get("y"))
        except (TypeError, ValueError):
            problems.append(f"text has invalid coordinates: {s[:38]!r}")
            continue
        try:
            w = text_width(s, cls, styles)
        except ValueError:
            problems.append(f"text has invalid font geometry: {s[:38]!r}")
            continue
        anchor = t.get("text-anchor")
        if not anchor:
            anchor = next((styles.get(c, {}).get("text-anchor")
                           for c in cls.split() if styles.get(c, {}).get("text-anchor")),
                          "start")
        left = x - w / 2 if anchor == "middle" else x - w if anchor == "end" else x
        right = left + w
        if left < min_x:
            problems.append(f"text past left canvas by {min_x - left:.0f}px: {s[:38]!r}")
        if right > max_x:
            problems.append(f"text past right canvas by {right - max_x:.0f}px: {s[:38]!r}")
        try:
            fs = font_size(cls, styles)
        except ValueError:
            problems.append(f"text has invalid font size: {s[:38]!r}")
            continue
        if y - fs < min_y or y > max_y:
            problems.append(f"text past vertical canvas edge: {s[:38]!r}")
        owner = None
        for r in solid:
            bx, by, bw, bh = r["box"]
            if bx <= x <= bx + bw and by - 2 <= y <= by + bh + 2:
                owner = r["box"]; break
        if owner:
            bx, by, bw, bh = owner
            if left < bx + PAD - 0.01 or right > bx + bw - PAD + 0.01:
                overflow = max(bx + PAD - left, right - (bx + bw - PAD))
                problems.append(
                    f"text overflows its box by {overflow:.0f}px "
                    f"(needs {PAD}px pad): {s[:38]!r}")

    # 2. solid boxes must not overlap each other
    for i, a in enumerate(solid):
        ax, ay, aw, ah = a["box"]
        for b in solid[i + 1:]:
            bx, by, bw, bh = b["box"]
            if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
                problems.append(f"box overlap: {a['cls']}@{ax},{ay} x {b['cls']}@{bx},{by}")

    # 3. connectors must not cut through boxes they do not terminate on
    for p in elements(root, "path"):
        d = p.get("d", "")
        if not d or p.get("class") not in ("ln", "lp"):
            continue
        if re.search(r"[mlhvzCQSTAZqcstaz]", d):
            problems.append("connector uses unsupported relative or curved path commands")
            continue
        pts = path_points(d)
        if len(pts) < 2:
            problems.append("connector has fewer than two parseable points")
            continue
        for a, b in zip(pts, pts[1:]):
            # Dashed containers are annotation frames, not shapes. A connector
            # leaving or entering a labelled region necessarily crosses its
            # frame, and that reads correctly; only solid boxes are obstacles.
            for r in solid:
                box = r["box"]
                # endpoints legitimately touch their source/target
                if any(box[0] - 3 <= e[0] <= box[0] + box[2] + 3 and
                       box[1] - 3 <= e[1] <= box[1] + box[3] + 3 for e in (a, b)):
                    continue
                if seg_hits_box(a, b, box):
                    problems.append(
                        f"connector crosses {r['cls'] or 'box'}@{box[0]:.0f},{box[1]:.0f}: "
                        f"segment {a}->{b}")

    if problems:
        print(f"{path}: {len(problems)} problem(s)")
        for p in dict.fromkeys(problems):
            print("  -", p)
        return 1
    print(f"{path}: clean — text fits, no overlaps, no connectors through shapes")
    return 0


def cli(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("path", nargs="?", default="assets/engine.svg")
    args = parser.parse_args(argv)
    return main(args.path)


if __name__ == "__main__":
    sys.exit(cli())
