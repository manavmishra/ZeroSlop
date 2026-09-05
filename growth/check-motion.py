#!/usr/bin/env python3
"""Read-only, dependency-free checks for the GitHub motion and logo exports."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib
import json
import re
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


def mp4_info(path):
    """Inspect ISO-BMFF metadata without codecs or platform dependencies."""
    data = path.read_bytes()

    def boxes(start, end):
        result = []
        while start < end:
            require(end - start >= 8, "Truncated MP4 box header")
            size, tag = struct.unpack_from(">I4s", data, start)
            header = 8
            if size == 1:
                require(end - start >= 16, "Truncated MP4 extended size")
                size = struct.unpack_from(">Q", data, start + 8)[0]
                header = 16
            elif size == 0:
                size = end - start
            require(header <= size <= end - start, f"Invalid MP4 box size: {tag!r}")
            result.append((tag, start + header, start + size, start))
            start += size
        return result

    def one(items, tag):
        matches = [item for item in items if item[0] == tag]
        require(len(matches) == 1, f"Expected one MP4 {tag!r} box")
        return matches[0]

    def children(box):
        return boxes(box[1], box[2])

    def payload(box, minimum=0):
        value = data[box[1]:box[2]]
        require(len(value) >= minimum, f"Truncated MP4 {box[0]!r} payload")
        return value

    def timing(box):
        value = payload(box, 20)
        require(value[0] in (0, 1), "Unsupported MP4 timing version")
        offset, duration_format = (12, ">I") if value[0] == 0 else (20, ">Q")
        require(len(value) >= offset + 4 + struct.calcsize(duration_format), "Truncated MP4 timing")
        scale = struct.unpack_from(">I", value, offset)[0]
        duration = struct.unpack_from(duration_format, value, offset + 4)[0]
        require(scale > 0, "Invalid MP4 timescale")
        return scale, duration

    top = boxes(0, len(data))
    one(top, b"ftyp")
    movie = one(top, b"moov")
    media_boxes = [box for box in top if box[0] == b"mdat"]
    require(media_boxes and movie[3] < min(box[3] for box in media_boxes), "MP4 must be fast-start: moov before mdat")
    movie_children = children(movie)
    movie_scale, movie_ticks = timing(one(movie_children, b"mvhd"))
    tracks = [box for box in movie_children if box[0] == b"trak"]
    require(len(tracks) == 1, "Expected exactly one MP4 video track and no audio")
    track_children = children(tracks[0])
    track_header = payload(one(track_children, b"tkhd"), 8)
    track_dimensions = tuple(value / 65536 for value in struct.unpack(">II", track_header[-8:]))
    media = children(one(track_children, b"mdia"))
    require(payload(one(media, b"hdlr"), 12)[8:12] == b"vide", "MP4 track is not video")
    scale, ticks = timing(one(media, b"mdhd"))
    samples = children(one(children(one(media, b"minf")), b"stbl"))
    description_box = one(samples, b"stsd")
    description = payload(description_box, 8)
    require(struct.unpack_from(">I", description, 4)[0] == 1, "Expected one MP4 sample description")
    codec = one(boxes(description_box[1] + 8, description_box[2]), b"avc1")
    visual = payload(codec, 78)
    dimensions = struct.unpack_from(">HH", visual, 24)
    require(track_dimensions == dimensions, "MP4 display and encoded dimensions differ")
    config = one(boxes(codec[1] + 78, codec[2]), b"avcC")
    require(payload(config, 7)[0] == 1, "Invalid H.264 decoder configuration")
    time_table = payload(one(samples, b"stts"), 8)
    entry_count = struct.unpack_from(">I", time_table, 4)[0]
    require(len(time_table) == 8 + entry_count * 8, "Invalid MP4 sample time table")
    frame_count, sample_ticks = 0, 0
    for count, delta in struct.iter_unpack(">II", time_table[8:]):
        require(count > 0 and delta > 0, "Invalid MP4 sample timing")
        frame_count += count
        sample_ticks += count * delta
    require(sample_ticks == ticks, "MP4 samples do not match media duration")
    size_table = payload(one(samples, b"stsz"), 12)
    require(struct.unpack_from(">I", size_table, 8)[0] == frame_count, "MP4 sample counts disagree")
    require(ticks > 0, "MP4 has no duration")
    duration = ticks / scale
    require(abs(movie_ticks / movie_scale - duration) < 0.000001, "MP4 movie and media durations differ")
    return dimensions, duration, frame_count, frame_count / duration


class PlayerTags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def check_evidence():
    evidence = json.loads((ROOT / "growth/demo-evidence.json").read_text())
    require(evidence["durationMs"] == 36_000, "Evidence duration is stale")
    for field, file_key in (("before", "source"), ("after", "edit")):
        path = (ROOT / evidence[file_key]).resolve()
        require(path.is_relative_to(ROOT), "Evidence source must stay in the repository")
        text = path.read_text().strip()
        require(evidence[field] == text, f"Evidence {field} text is stale")
        require(hashlib.sha256(text.encode()).hexdigest() == evidence[f"{field}Sha256"], f"Evidence {field} hash is stale")
        require("40%" in text, f"Missing protected detail in {field}")
    require((evidence["beforeScore"], evidence["afterScore"]) == (99.3, 9.5), "Review changed example scores")
    require(len(evidence["flags"]) == 4 and all(flag in evidence["before"] for flag in evidence["flags"]), "Evidence flag list is stale")
    require(evidence["protectedDetail"] == "40%", "Evidence protected detail is stale")


def main():
    for suffix, reader in (("gif", gif_info), ("webp", webp_info)):
        path = ASSETS / f"zero-slop-demo.{suffix}"
        dimensions, delays = reader(path)
        require(dimensions == (960, 540), f"Unexpected {suffix} dimensions")
        require(10 <= len(delays) <= 300, f"Unexpected {suffix} frame count")
        require(sum(delays) == 36_000, f"Unexpected {suffix} duration")
        require(path.stat().st_size <= 2_000_000, f"{suffix} exceeds 2 MB budget")
        print(f"{suffix}: {len(delays)} frames, {sum(delays)} ms, {path.stat().st_size} bytes")
    video = ASSETS / "zero-slop-demo.mp4"
    dimensions, duration, frame_count, fps = mp4_info(video)
    require(dimensions == (1920, 1080), "Unexpected MP4 dimensions")
    require(abs(duration - 36) < 0.000001 and frame_count == 1080 and abs(fps - 30) < 0.000001, "Expected a 36-second, 30 fps MP4")
    require(video.stat().st_size <= 9_000_000, "MP4 exceeds 9 MB budget")
    print(f"mp4: H.264, {dimensions[0]}×{dimensions[1]}, {fps:g} fps, {duration:g} s, {video.stat().st_size} bytes; silent, fast-start")
    require(png_info(ASSETS / "zero-slop-demo-poster.png")[0] == (1280, 720), "Poster dimensions")
    for name, colour_type in (("logo-300.png", 2), ("logo-mark-300.png", 6)):
        require(png_info(ASSETS / "logo" / name) == ((300, 300), colour_type), f"Logo dimensions/alpha: {name}")
    readme = (ROOT / "README.md").read_text()
    require(readme.index('prefers-reduced-motion: reduce') < readme.index('image/webp'), "Static preference must precede animated sources")
    for asset in ('zero-slop-demo-poster.png', 'zero-slop-demo.webp', 'zero-slop-demo.gif'):
        require(asset in readme, f"Missing README fallback: {asset}")
    image_tag = readme.split('<img src="assets/zero-slop-demo.gif"', 1)[1].split('>', 1)[0]
    require('height=' not in image_tag, "GitHub constrains width only; a fixed height distorts the animation")
    player = (ASSETS / "zero-slop-demo.html").read_text()
    parsed = PlayerTags()
    parsed.feed(player)
    videos = [attrs for tag, attrs in parsed.tags if tag == "video"]
    require(len(videos) == 1, "Expected one native video player")
    require(all(attr in videos[0] for attr in ("controls", "playsinline", "muted")), "Missing native video controls")
    require("autoplay" not in videos[0] and videos[0].get("preload") == "metadata", "Video must wait for manual play and preload metadata only")
    require(videos[0].get("poster") == "zero-slop-demo-poster.png", "Missing native video poster")
    require(any(tag == "source" and attrs.get("src") == "zero-slop-demo.mp4" and attrs.get("type") == "video/mp4" for tag, attrs in parsed.tags), "Missing MP4 player source")
    require(re.search(r"prefers-reduced-motion\s*:\s*reduce", player), "Missing reduced-motion preference")
    require(not any(tag == "audio" or (tag == "script" and "src" in attrs) for tag, attrs in parsed.tags), "Keep playback silent and self-contained")
    check_evidence()
    print("Poster, 300px logos, media fallbacks, manual-play video and source evidence OK")


if __name__ == "__main__":
    main()
