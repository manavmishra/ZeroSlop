#!/usr/bin/env python3
"""Encode Blender's deterministic PNG sequence as a silent, fast-start MP4.

This is a maintainer-only release helper. Blender owns the scene, camera,
materials and frame pixels; this wrapper only performs the final H.264 mux.
It prefers the bundled imageio-ffmpeg binary and fails with a useful message
when no encoder is available.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def ffmpeg_path() -> str:
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        found = shutil.which("ffmpeg")
        if found:
            return found
        raise SystemExit(
            "No FFmpeg encoder found. Install imageio-ffmpeg or provide ffmpeg on PATH."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=Path, required=True, help="Directory containing frame-####.png")
    parser.add_argument("--output", type=Path, required=True, help="Silent MP4 destination")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--crf", type=int, default=20, help="H.264 quality target (lower is larger)")
    args = parser.parse_args()

    frames = sorted(args.frames.glob("frame-*.png"))
    first = args.frames / "frame-0001.png"
    last = args.frames / "frame-0720.png"
    if not first.exists() or not last.exists() or len(frames) != 720:
        raise SystemExit(
            f"Expected exactly 720 frames (frame-0001.png … frame-0720.png) in {args.frames}; found {len(frames)}"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg_path(),
        "-y",
        "-framerate",
        str(args.fps),
        "-start_number",
        "1",
        "-i",
        str(args.frames / "frame-%04d.png"),
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "slow",
        "-crf",
        str(args.crf),
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(args.output),
    ]
    subprocess.run(command, check=True)
    print(f"Wrote silent Blender MP4: {args.output}")


if __name__ == "__main__":
    main()
