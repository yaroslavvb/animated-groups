#!/usr/bin/env python3
"""Transcode every gallery GIF to a seekable MP4 playback proxy."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Sequence

from generate_posters import ROOT, _local_path, parse_sources


def _run(command: Sequence[str]) -> None:
    subprocess.run(command, check=True)


def generate_videos(
    index_path: Path,
    *,
    fps: int = 20,
    frames: int = 60,
    crf: int = 18,
    keyframe_interval: int = 10,
) -> tuple[Path, ...]:
    if fps <= 0:
        raise ValueError("fps must be positive")
    if frames <= 1:
        raise ValueError("frames must be greater than one")
    if not 0 <= crf <= 51:
        raise ValueError("crf must be between 0 and 51")
    if not 1 <= keyframe_interval <= frames:
        raise ValueError("keyframe interval must be between 1 and the frame count")

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise FileNotFoundError("ffmpeg is required to generate the MP4 playback proxies")

    index_path = index_path.resolve()
    root = index_path.parent
    jobs: list[tuple[Path, Path]] = []

    for source in parse_sources(index_path):
        gif_path = _local_path(root, source.gif, kind="GIF source")
        video_path = _local_path(root, source.video, kind="video destination")
        if gif_path.suffix.lower() != ".gif":
            raise ValueError(f"motion source is not a GIF: {source.gif!r}")
        if video_path.suffix.lower() != ".mp4":
            raise ValueError(f"video destination is not MP4: {source.video!r}")
        if not gif_path.is_file():
            raise FileNotFoundError(f"GIF source does not exist: {gif_path}")
        jobs.append((gif_path, video_path))

    if len({video for _, video in jobs}) != len(jobs):
        raise ValueError("video destinations must be unique")

    written: list[Path] = []
    for gif_path, video_path in jobs:
        video_path.parent.mkdir(parents=True, exist_ok=True)
        _run(
            (
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(gif_path),
                "-an",
                "-vf",
                f"fps={fps},format=yuv420p",
                "-frames:v",
                str(frames),
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                str(crf),
                "-g",
                str(keyframe_interval),
                "-keyint_min",
                str(keyframe_interval),
                "-sc_threshold",
                "0",
                "-movflags",
                "+faststart",
                str(video_path),
            )
        )
        written.append(video_path)
        print(f"{video_path.relative_to(root)} <- {gif_path.relative_to(root)}")

    return tuple(written)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--index",
        type=Path,
        default=ROOT / "index.html",
        help="gallery HTML to parse (default: project index.html)",
    )
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--crf", type=int, default=18)
    parser.add_argument("--keyframe-interval", type=int, default=10)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        written = generate_videos(
            args.index,
            fps=args.fps,
            frames=args.frames,
            crf=args.crf,
            keyframe_interval=args.keyframe_interval,
        )
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        parser.error(str(error))
    print(f"Wrote {len(written)} MP4 playback proxies.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
