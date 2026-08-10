#!/usr/bin/env python3
"""Build the systematic data catalog and its selected looping GIF gallery."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from animated_groups.catalog.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
