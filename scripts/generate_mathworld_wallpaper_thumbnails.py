#!/usr/bin/env python3
"""Generate the 17 compact wallpaper-group thumbnails used by the catalog.

The source is MathWorld's vector plate, whose patterns were created with
Artlandia SymmetryWorks.  The plate labels use crystallographic notation; the
catalog supplies its own Conway orbifold labels in HTML, so these crops retain
only the pattern artwork.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from urllib.request import urlopen

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://mathworld.wolfram.com/images/eps-svg/WallpaperGroups_700.svg"
OUTPUT = ROOT / "output" / "mathworld-wallpaper-groups"
TMP = ROOT / "tmp" / "mathworld-wallpaper"

# Cells in a 1400-pixel rendering of the 436.27 x 376.84 point source plate.
# The y ranges begin below MathWorld's crystallographic labels.
CROP_BOXES = {
    "p1": (0, 55, 280, 300),
    "pg": (280, 55, 560, 300),
    "pgg": (560, 55, 840, 300),
    "pm": (840, 55, 1120, 300),
    "cm": (1120, 55, 1400, 300),
    "cmm": (0, 395, 280, 630),
    "pmg": (280, 395, 560, 630),
    "pmm": (560, 395, 840, 630),
    "p2": (840, 395, 1120, 630),
    "p4": (1120, 395, 1400, 630),
    "p4m": (0, 715, 280, 945),
    "p4g": (280, 715, 560, 945),
    "p3": (560, 715, 840, 945),
    "p3m1": (840, 715, 1120, 945),
    "p31m": (1120, 715, 1400, 945),
    "p6": (0, 1010, 280, 1210),
    "p6m": (280, 1010, 560, 1210),
}


def main() -> int:
    TMP.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source = TMP / "WallpaperGroups_700.svg"
    rendered = TMP / "WallpaperGroups_1400.png"
    source.write_bytes(urlopen(SOURCE_URL).read())
    subprocess.run(
        [
            "rsvg-convert",
            "-w",
            "1400",
            "-b",
            "white",
            "-o",
            str(rendered),
            str(source),
        ],
        check=True,
    )

    with Image.open(rendered) as plate:
        for group, box in CROP_BOXES.items():
            crop = plate.crop(box)
            fitted = ImageOps.contain(crop, (320, 220), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (320, 240), "white")
            canvas.paste(
                fitted.convert("RGB"),
                ((canvas.width - fitted.width) // 2, (canvas.height - fitted.height) // 2),
            )
            canvas.save(
                OUTPUT / f"{group}.webp",
                "WEBP",
                quality=92,
                method=6,
            )
            print(f"wrote {(OUTPUT / f'{group}.webp').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
