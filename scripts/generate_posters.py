#!/usr/bin/env python3
"""Extract the first frame of every gallery GIF as a lossless WebP poster."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
import sys
from typing import Sequence

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def _classes(attributes: dict[str, str | None]) -> set[str]:
    return set((attributes.get("class") or "").split())


@dataclass(frozen=True)
class PosterSource:
    gif: str
    poster: str
    video: str


class _GalleryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sources: list[PosterSource] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = dict(attrs)
        if tag != "img" or "motion-image" not in _classes(attributes):
            return

        missing = [
            name
            for name in (
                "src",
                "data-poster-src",
                "data-motion-src",
                "data-video-src",
            )
            if not attributes.get(name)
        ]
        if missing:
            raise ValueError(
                "motion image is missing " + ", ".join(missing)
            )

        source = attributes["src"] or ""
        poster = attributes["data-poster-src"] or ""
        motion = attributes["data-motion-src"] or ""
        video = attributes["data-video-src"] or ""
        if source != poster:
            raise ValueError(
                f"motion image src must equal data-poster-src: {source!r} != {poster!r}"
            )
        self.sources.append(PosterSource(gif=motion, poster=poster, video=video))


def _local_path(root: Path, value: str, *, kind: str) -> Path:
    path = Path(value)
    if path.is_absolute() or "?" in value or "#" in value or "://" in value:
        raise ValueError(f"{kind} must be a plain local relative path: {value!r}")

    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"{kind} escapes the project root: {value!r}") from error
    return resolved


def parse_sources(index_path: Path) -> tuple[PosterSource, ...]:
    parser = _GalleryParser()
    parser.feed(index_path.read_text(encoding="utf-8"))
    parser.close()

    if len(parser.sources) != 33:
        raise ValueError(
            f"expected exactly 33 motion images in {index_path}, found {len(parser.sources)}"
        )
    if len(set(parser.sources)) != len(parser.sources):
        raise ValueError("motion images must have 33 unique GIF/poster path pairs")
    return tuple(parser.sources)


def generate_posters(index_path: Path) -> tuple[Path, ...]:
    index_path = index_path.resolve()
    root = index_path.parent
    sources = parse_sources(index_path)
    jobs: list[tuple[Path, Path]] = []

    for source in sources:
        gif_path = _local_path(root, source.gif, kind="GIF source")
        poster_path = _local_path(root, source.poster, kind="poster destination")
        if gif_path.suffix.lower() != ".gif":
            raise ValueError(f"motion source is not a GIF: {source.gif!r}")
        if poster_path.suffix.lower() != ".webp":
            raise ValueError(f"poster destination is not WebP: {source.poster!r}")
        if not gif_path.is_file():
            raise FileNotFoundError(f"GIF source does not exist: {gif_path}")
        jobs.append((gif_path, poster_path))

    written: list[Path] = []
    for gif_path, poster_path in jobs:
        with Image.open(gif_path) as image:
            image.seek(0)
            first_frame = image.convert("RGB")
            poster_path.parent.mkdir(parents=True, exist_ok=True)
            first_frame.save(
                poster_path,
                format="WEBP",
                lossless=True,
                quality=100,
                method=6,
                exact=True,
            )
        written.append(poster_path)
        print(
            f"{poster_path.relative_to(root)} <- {gif_path.relative_to(root)} frame 0"
        )

    return tuple(written)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--index",
        type=Path,
        default=ROOT / "index.html",
        help="gallery HTML to parse (default: project index.html)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        written = generate_posters(args.index)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"Wrote {len(written)} lossless WebP posters.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
