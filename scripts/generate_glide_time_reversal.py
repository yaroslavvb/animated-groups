#!/usr/bin/env python3
"""Generate the non-split half-cell glide/playback-reversal example."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from animated_groups.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main(["glide-time-reversal", *sys.argv[1:]]))

