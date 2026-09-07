#!/usr/bin/env python3
"""Read-only, dependency-free checks for GitHub motion, logos, and share artwork."""
from pathlib import Path
from html.parser import HTMLParser
from fractions import Fraction
import hashlib
import json
import re
import struct

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
MCP_URL = "https://mcp.zero-slop.ai/mcp"
MCP_GUIDE_URL = "https://zero-slop.ai/#mcp"
SHELL_DIMENSIONS = (900, 580)
SHELL_DURATION_MS = 15_150
SHELL_GIF_BLOB = "dd642cbe7b73d06ceff3e2511a553bcfd244e369"
SHELL_SOURCE_COMMIT = "5b9ef28f5807e5d8cbf577f1a514920e3970f116"
SHELL_INTRODUCED_COMMIT = "91ee2fc15e18ceea484daf2beb3e72ce6c234a2d"
SHELL_SOURCE_HASHES = {
    "before": "bb276a80c09c16eebd4f4ecb32842413828a52ef16272b4a554b88b993cbff8a",
    "after": "4fa6dbbb40d2d7dfa3349be679a6a6aff393772d5f11995e81ecea83c80e2472",
}
OFFICIAL_LOGO_HASHES = {
    "zero-slop-logo-primary.svg": "800efb95549dbd7d08043b601639a5a5d2f354a54f704f2c140d135f1a9d7e55",
    "zero-slop-logo-primary.png": "34f9a839ce7f9bb0da63787f02cb922323f5ebc7ea55b932f1c11edfbd4006b9",
    "zero-slop-logo-reversed.svg": "49f9e46dc25d5b17da34b270d60c4cdfb76c232a8dbda5a73d7e0edacee12b57",
    "zero-slop-logo-reversed.png": "644615e98281338fdba1b66b6c415561e0601c9dd69807e2296afd9b9451c84f",
    "zero-slop-mark-orange.svg": "17db12f1d3db5622ff9648bb3f9ed9ac6af714152c03d4e6737e528d83559e05",
    "zero-slop-app-icon-transparent-512.png": "32985bd074903861f73488bddcdc587f6c0a360ad24db575bf0e5880d4009843",
    "zero-slop-github-300.png": "40cde47cfc566b4d310f79f33294639ccee3be85813d5dc68e163fd66b7f3daf",
}
APPROVED_SOCIAL_PREVIEWS = {
    "zero-slop-github-preview-1280x640.png": ((1280, 640), "35037ead8642ac34ae77abde7daafb7d50ddbb975e1450b8878f50d9a526e4f7"),
    "zero-slop-github-preview-640x320.png": ((640, 320), "dafaa0969dd513a3dd912044871237120ac28ff4aabe4e7c1db8db0b218a3afe"),
}
SHELL_FLAGS = [
    "In today's fast-paced",
    "We're thrilled to",
    "It's not just a redesign, it's",
    "cutting-edge",
    "leveraged",
]


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
            require(len(payload) >= 24, "Truncated WebP animation frame")
            delays.append(int.from_bytes(payload[12:15], "little"))
            frame_pos, frame_tags = 16, []
            while frame_pos + 8 <= len(payload):
                frame_tag = payload[frame_pos:frame_pos + 4]
                frame_size = int.from_bytes(payload[frame_pos + 4:frame_pos + 8], "little")
                require(frame_pos + 8 + frame_size <= len(payload), "Truncated WebP frame image")
                frame_tags.append(frame_tag)
                frame_pos += 8 + frame_size + (frame_size % 2)
            require(frame_tags == [b"VP8L"], "Every WebP frame must use lossless encoding")
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

    def presentation(track_children):
        """Return edited track duration and its start on the media timeline.

        MP4 may retain reordered H.264 decode samples outside
        the presented interval. A single rate-1 edit maps that interval onto
        the movie timeline; mdhd alone is not the displayed film duration.
        """
        header = payload(one(track_children, b"tkhd"), 24)
        require(header[0] in (0, 1), "Unsupported MP4 track-header version")
        offset, number_format = (20, ">I") if header[0] == 0 else (28, ">Q")
        require(len(header) >= offset + struct.calcsize(number_format),
                "Truncated MP4 track duration")
        track_ticks = struct.unpack_from(number_format, header, offset)[0]
        edits = [item for item in track_children if item[0] == b"edts"]
        require(len(edits) <= 1, "Unexpected duplicate MP4 edit container")
        media_start = 0
        if edits:
            edit = payload(one(children(edits[0]), b"elst"), 8)
            require(edit[0] in (0, 1), "Unsupported MP4 edit-list version")
            require(struct.unpack_from(">I", edit, 4)[0] == 1,
                    "Expected one continuous MP4 presentation edit")
            edit_format = ">Iihh" if edit[0] == 0 else ">Qqhh"
            require(len(edit) == 8 + struct.calcsize(edit_format), "Invalid MP4 edit list")
            segment_ticks, media_start, rate_integer, rate_fraction = struct.unpack_from(edit_format, edit, 8)
            require(segment_ticks == track_ticks and media_start >= 0,
                    "MP4 presentation edit differs from track duration or contains a gap")
            require((rate_integer, rate_fraction) == (1, 0), "MP4 presentation must play at normal speed")
        return Fraction(track_ticks, movie_scale), media_start

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
    media = children(one(track_children, b"mdia"))
    require(payload(one(media, b"hdlr"), 12)[8:12] == b"vide", "MP4 track must be video, not audio")
    track_header = payload(one(track_children, b"tkhd"), 8)
    track_dimensions = tuple(value / 65536 for value in struct.unpack(">II", track_header[-8:]))
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
    decode_runs = list(struct.iter_unpack(">II", time_table[8:]))
    frame_count, sample_ticks = 0, 0
    for count, delta in decode_runs:
        require(count > 0 and delta > 0, "Invalid MP4 sample timing")
        frame_count += count
        sample_ticks += count * delta
    require(sample_ticks == ticks, "MP4 samples do not match media duration")
    size_table = payload(one(samples, b"stsz"), 12)
    require(struct.unpack_from(">I", size_table, 8)[0] == frame_count, "MP4 sample counts disagree")
    require(ticks > 0, "MP4 has no duration")
    presented_duration, video_start = presentation(track_children)
    require(presented_duration == Fraction(movie_ticks, movie_scale),
            "MP4 movie and presented video durations differ")
    # Validate visible cadence, not decode cadence. B-frame reordering can
    # produce nonuniform DTS deltas even when displayed frames are evenly spaced.
    # Composition offsets may extend the visible span beyond mdhd's decode
    # span; the complete presentation grid below is the coverage check.
    require(0 < frame_count <= 100_000, "Unexpected video sample count")
    composition_boxes = [item for item in samples if item[0] == b"ctts"]
    require(len(composition_boxes) <= 1, "Duplicate MP4 composition-offset table")
    offsets = [0] * frame_count
    if composition_boxes:
        composition = payload(composition_boxes[0], 8)
        require(composition[0] in (0, 1), "Unsupported MP4 composition-offset version")
        composition_count = struct.unpack_from(">I", composition, 4)[0]
        require(len(composition) == 8 + composition_count * 8,
                "Invalid MP4 composition-offset table")
        offset_runs = list(struct.iter_unpack(">II" if composition[0] == 0 else ">Ii", composition[8:]))
        require(all(count > 0 for count, _ in offset_runs)
                and sum(count for count, _ in offset_runs) == frame_count,
                "Composition offsets do not match video sample count")
        offsets = [offset for count, offset in offset_runs for _ in range(count)]
    decode_time, sample_index, presentation_times = 0, 0, []
    for count, delta in decode_runs:
        for _ in range(count):
            presentation_times.append(decode_time + offsets[sample_index])
            decode_time += delta
            sample_index += 1
    presented_ticks = presented_duration * scale
    require(all(Fraction(time - video_start) == index * presented_ticks / frame_count
                for index, time in enumerate(sorted(presentation_times))),
            "Video presentation timestamps are not a complete, evenly spaced frame grid")
    duration = float(presented_duration)

    return dimensions, duration, frame_count, frame_count / duration


class PlayerTags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.visible_text = []
        self.links = []
        self._link = None
        self._noncontent = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if tag in ("script", "style", "template"):
            self._noncontent.append(tag)
        if tag == "a":
            self._link = {"href": attrs.get("href"), "text": []}

    def handle_endtag(self, tag):
        if self._noncontent and self._noncontent[-1] == tag:
            self._noncontent.pop()
        if tag == "a" and self._link is not None:
            self.links.append((self._link["href"], " ".join(self._link["text"])))
            self._link = None

    def handle_data(self, data):
        if not self._noncontent:
            self.visible_text.append(data)
            if self._link is not None:
                self._link["text"].append(data)


def check_mcp_player(parsed):
    # A URL in an href, script or style is not a user-visible connection address.
    words = " ".join(parsed.visible_text).split()
    require(MCP_URL in [word.strip(".,;:()[]{}<>") for word in words],
            "Player must display the exact MCP connection URL as text or code")
    guides = [label for href, label in parsed.links if href == MCP_GUIDE_URL]
    require(guides and all(re.search(r"\bsetup\s+guide\b", label, re.I) for label in guides),
            "The MCP website link must be labelled as a setup guide, not the endpoint")


def check_evidence():
    evidence = json.loads((ROOT / "growth/demo-evidence.json").read_text())
    require(evidence["kind"] == "Restored dark-shell README animation",
            "Evidence must identify the restored historical shell animation")
    require(evidence["durationMs"] == SHELL_DURATION_MS, "Evidence duration is stale")
    require(evidence.get("audio") == "none" and "originalScore" not in evidence,
            "Evidence must identify a silent film without a score")
    require(evidence.get("sourceCommit") == SHELL_SOURCE_COMMIT
            and evidence.get("masterIntroducedCommit") == SHELL_INTRODUCED_COMMIT
            and evidence.get("gifGitBlob") == SHELL_GIF_BLOB,
            "Evidence must identify the exact restored GIF and its historical commits")
    server = json.loads((ROOT / "server.json").read_text())
    require(evidence.get("mcpURL") == server["remotes"][0]["url"] == MCP_URL,
            "Evidence MCP URL must match the canonical server.json connection endpoint")
    require(evidence.get("terminalRenderer") == "HTML/CSS terminal reconstruction"
            and "sceneRenderer" not in evidence,
            "Evidence must identify the historical HTML/CSS shell renderer")
    for field, file_key in (("before", "source"), ("after", "edit")):
        require(evidence[file_key] == f"growth/shell-demo.{field}.md",
                f"Evidence {field} must use the historical shell example")
        path = (ROOT / evidence[file_key]).resolve()
        require(path.is_relative_to(ROOT), "Evidence source must stay in the repository")
        text = path.read_text().strip()
        require(evidence[field] == text, f"Evidence {field} text is stale")
        require(hashlib.sha256(text.encode()).hexdigest() == evidence[f"{field}Sha256"] == SHELL_SOURCE_HASHES[field],
                f"Evidence {field} hash differs from the historical shell example")
        require("40%" in text, f"Missing protected detail in {field}")
    require((evidence["beforeScore"], evidence["afterScore"]) == (100, 9.5),
            "Evidence must retain the historical displayed scores")
    require(evidence["flags"] == SHELL_FLAGS and all(flag in evidence["before"] for flag in SHELL_FLAGS),
            "Evidence must retain the five source-bound historical flags")
    require(evidence["protectedDetail"] == "40%", "Evidence protected detail is stale")


def main():
    gif_bytes = (ASSETS / "zero-slop-demo.gif").read_bytes()
    git_blob = hashlib.sha1(f"blob {len(gif_bytes)}\0".encode() + gif_bytes).hexdigest()
    require(len(gif_bytes) == 45_862 and git_blob == SHELL_GIF_BLOB,
            "The GIF master must be the exact historical dark-shell Git blob")
    master_delays = gif_info(ASSETS / "zero-slop-demo.gif")[1]
    for suffix, reader in (("gif", gif_info), ("webp", webp_info)):
        path = ASSETS / f"zero-slop-demo.{suffix}"
        dimensions, delays = reader(path)
        require(dimensions == SHELL_DIMENSIONS, f"Unexpected {suffix} dimensions")
        require(len(delays) == 34, f"Unexpected {suffix} frame count")
        require(sum(delays) == SHELL_DURATION_MS, f"Unexpected {suffix} duration")
        require(delays == master_delays, f"The {suffix} frame holds must match the GIF master")
        # Preserve the compact original and a lossless animated WebP derivative.
        budget = 45_862 if suffix == "gif" else 2_000_000
        require(path.stat().st_size <= budget, f"{suffix} exceeds {budget / 1_000_000:g} MB budget")
        print(f"{suffix}: {len(delays)} frames, {sum(delays)} ms, {path.stat().st_size} bytes")
    video = ASSETS / "zero-slop-demo.mp4"
    dimensions, duration, frame_count, fps = mp4_info(video)
    require(dimensions == SHELL_DIMENSIONS, "Unexpected MP4 dimensions")
    require(abs(duration - SHELL_DURATION_MS / 1000) < 0.000001
            and frame_count == 303 and abs(fps - 20) < 0.000001,
            "Expected the complete 15.15-second historical animation at 20 fps")
    require(video.stat().st_size <= 9_000_000, "MP4 exceeds 9 MB budget")
    print(f"mp4: H.264, {dimensions[0]}×{dimensions[1]}, {fps:g} fps, {duration:g} s, {video.stat().st_size} bytes; silent, fast-start")
    require(png_info(ASSETS / "zero-slop-demo-poster.png")[0] == SHELL_DIMENSIONS, "Poster dimensions")
    for name, colour_type in (("logo-300.png", 2), ("logo-mark-300.png", 6)):
        require(png_info(ASSETS / "logo" / name) == ((300, 300), colour_type), f"Logo dimensions/alpha: {name}")
    for name, colour_type in (("zero-slop-mark-300-white.png", 2), ("zero-slop-mark-300-transparent.png", 6)):
        require(png_info(ASSETS / "logo/studio" / name) == ((300, 300), colour_type), f"Gold logo dimensions/alpha: {name}")
    require(png_info(ASSETS / "logo/studio/zero-slop-mark-3d-1200.png")[0] == (1200, 1200), "3D logo dimensions")
    logo_svg = (ASSETS / "logo/studio/zero-slop-mark.svg").read_text()
    require(all(color in logo_svg for color in ("#e2a500", "#12100c", "#8c3f22")), "Archived studio palette must survive")
    for name, expected_hash in OFFICIAL_LOGO_HASHES.items():
        require(hashlib.sha256((ASSETS / "logo" / name).read_bytes()).hexdigest() == expected_hash,
                f"Official supplied logo must remain unchanged: {name}")
    require((ASSETS / "logo/logo-mark.svg").read_bytes() == (ASSETS / "logo/zero-slop-mark-orange.svg").read_bytes(),
            "Compatibility SVG must match the official rust mark")
    for name, (dimensions, expected_hash) in APPROVED_SOCIAL_PREVIEWS.items():
        preview = ASSETS / "social" / name
        require(png_info(preview)[0] == dimensions, f"Approved share image dimensions: {name}")
        require(hashlib.sha256(preview.read_bytes()).hexdigest() == expected_hash,
                f"Approved share artwork must remain unchanged: {name}")
    require((ASSETS / "social-preview.png").read_bytes() == (ASSETS / "social/zero-slop-github-preview-1280x640.png").read_bytes(),
            "Repository social preview must match the approved full-size artwork")
    readme = (ROOT / "README.md").read_text()
    require('src="assets/logo/zero-slop-logo-primary.svg"' in readme,
            "README must use the supplied primary logo")
    require('media="(prefers-color-scheme: dark)" srcset="assets/logo/zero-slop-logo-reversed.svg"' in readme,
            "README must use the supplied reversed logo on dark backgrounds")
    require(readme.index('prefers-reduced-motion: reduce') < readme.index('image/webp'), "Static preference must precede animated sources")
    for asset in ('zero-slop-demo-poster.png', 'zero-slop-demo.webp', 'zero-slop-demo.gif'):
        require(asset in readme, f"Missing README fallback: {asset}")
    image_match = re.search(r'<img src="assets/zero-slop-demo\.gif(?:\?[^"<>]*)?"([^>]*)>', readme)
    require(image_match is not None, "Missing README animation image")
    image_tag = image_match.group(1)
    require('height=' not in image_tag, "GitHub constrains width only; a fixed height distorts the animation")
    player = (ASSETS / "zero-slop-demo.html").read_text()
    parsed = PlayerTags()
    parsed.feed(player)
    videos = [attrs for tag, attrs in parsed.tags if tag == "video"]
    require(len(videos) == 1, "Expected one native video player")
    # Native controls provide manual playback. A muted attribute is optional
    # because the MP4 itself must contain no audio track.
    require(all(attr in videos[0] for attr in ("controls", "playsinline")), "Missing native playback and mute controls")
    require("autoplay" not in videos[0] and videos[0].get("preload") == "metadata", "Video must wait for manual play and preload metadata only")
    require(videos[0].get("poster") == "zero-slop-demo-poster.png", "Missing native video poster")
    require(any(tag == "source" and attrs.get("src") == "zero-slop-demo.mp4" and attrs.get("type") == "video/mp4" for tag, attrs in parsed.tags), "Missing MP4 player source")
    require(re.search(r"prefers-reduced-motion\s*:\s*reduce", player), "Missing reduced-motion preference")
    require(not any(tag == "audio" or (tag == "script" and "src" in attrs) for tag, attrs in parsed.tags), "Keep the silent player self-contained")
    check_mcp_player(parsed)
    check_evidence()
    print("Poster, logos, approved share artwork, media fallbacks, manual-play video, MCP endpoint and source evidence OK")


if __name__ == "__main__":
    main()
