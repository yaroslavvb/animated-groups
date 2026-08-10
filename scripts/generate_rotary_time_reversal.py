#!/usr/bin/env python3
"""Generate the tetragonal 4-prime quarter-turn/playback-reversal example."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from animated_groups.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main(["rotary-time-reversal", *sys.argv[1:]]))

