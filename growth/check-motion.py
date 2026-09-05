#!/usr/bin/env python3
"""Read-only, dependency-free checks for the GitHub motion and logo exports."""
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def png_info(path):
    data = path.read_bytes()
    require(data[:8] == b"\x89PNG\r\n\x1a\n", f"Invalid PNG: {path}")
    return struct.unpack(">II", data[16:24]), data[25]


def gif_info(path):
    data = path.read_bytes()
    require(data[:6] == b"GIF89a", "Expected an animated GIF89a export")
    dimensions = struct.unpack("<HH", data[6:10])
    packed = data[10]
    pos = 13 + (3 * 2 ** ((packed & 7) + 1) if packed & 128 else 0)
    delays = []
    pending = None

    def skip_blocks(offset):
        while True:
            size = data[offset]
            offset += 1
            if size == 0:
                return offset
            offset += size
            require(offset <= len(data), "Truncated GIF sub-block")

    while pos < len(data):
        block = data[pos]
        pos += 1
        if block == 0x3B:
            return dimensions, delays
        if block == 0x21:
            extension = data[pos]
            pos += 1
            if extension == 0xF9:
                require(data[pos] == 4, "Invalid GIF graphic control")
                pending = int.from_bytes(data[pos + 2:pos + 4], "little") * 10
            pos = skip_blocks(pos)
        elif block == 0x2C:
            flags = data[pos + 8]
            pos += 9
            if flags & 128:
                pos += 3 * 2 ** ((flags & 7) + 1)
            pos += 1  # LZW minimum code size.
            pos = skip_blocks(pos)
            require(pending is not None and pending >= 20, "Missing/too-short frame delay")
            delays.append(pending)
            pending = None
        else:
            raise ValueError(f"Unexpected GIF block: {block:#x}")
    raise ValueError("Missing GIF trailer")


def webp_info(path):
    data = path.read_bytes()
    require(data[:4] == b"RIFF" and data[8:12] == b"WEBP", "Invalid WebP")
    pos, dimensions, delays = 12, None, []
    while pos + 8 <= len(data):
        tag = data[pos:pos + 4]
        size = int.from_bytes(data[pos + 4:pos + 8], "little")
        payload = data[pos + 8:pos + 8 + size]
        require(len(payload) == size, "Truncated WebP chunk")
        if tag == b"VP8X":
            dimensions = tuple(int.from_bytes(payload[i:i + 3], "little") + 1 for i in (4, 7))
        elif tag == b"ANMF":
            delays.append(int.from_bytes(payload[12:15], "little"))
        pos += 8 + size + (size % 2)
    return dimensions, delays


def main():
    for suffix, reader in (("gif", gif_info), ("webp", webp_info)):
        path = ASSETS / f"zero-slop-demo.{suffix}"
        dimensions, delays = reader(path)
        require(dimensions == (1040, 560), f"Unexpected {suffix} dimensions")
        require(10 <= len(delays) <= 90, f"Unexpected {suffix} frame count")
        require(sum(delays) == 8400, f"Unexpected {suffix} duration")
        require(path.stat().st_size <= 400_000, f"{suffix} exceeds 400 kB budget")
        print(f"{suffix}: {len(delays)} frames, {sum(delays)} ms, {path.stat().st_size} bytes")
    require(png_info(ASSETS / "zero-slop-demo-poster.png")[0] == (1040, 560), "Poster dimensions")
    for name, colour_type in (("logo-300.png", 2), ("logo-mark-300.png", 6)):
        require(png_info(ASSETS / "logo" / name) == ((300, 300), colour_type), f"Logo dimensions/alpha: {name}")
    readme = (ROOT / "README.md").read_text()
    require(readme.index('prefers-reduced-motion: reduce') < readme.index('image/webp'), "Static preference must precede animated sources")
    for asset in ('zero-slop-demo-poster.png', 'zero-slop-demo.webp', 'zero-slop-demo.gif'):
        require(asset in readme, f"Missing README fallback: {asset}")
    player = (ASSETS / "zero-slop-demo.html").read_text()
    require('prefers-reduced-motion: reduce' in player and 'id="toggle"' in player, "Player motion controls")
    require('<audio' not in player and '<script src=' not in player, "Keep playback silent and self-contained")
    print("Poster, 300px logos, media fallbacks and silent player OK")


if __name__ == "__main__":
    main()
