#!/usr/bin/env python3
from __future__ import annotations

import math
import shutil
import struct
import subprocess
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "build" / "assets"
PNG_PATH = ASSETS / "icon-1024.png"
ICONSET = ASSETS / "HermesVibe.iconset"
ICNS_PATH = ASSETS / "HermesVibe.icns"


def write_png(path: Path, width: int, height: int, rows: list[bytes]) -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + row for row in rows)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def rounded_rect_alpha(x: int, y: int, size: int, radius: int) -> int:
    inset = radius
    cx = min(max(x, inset), size - inset - 1)
    cy = min(max(y, inset), size - inset - 1)
    distance = math.hypot(x - cx, y - cy)
    if distance <= radius - 2:
        return 255
    if distance >= radius + 2:
        return 0
    return max(0, min(255, int((radius + 2 - distance) / 4 * 255)))


def make_icon_png(path: Path, size: int = 1024) -> None:
    rows: list[bytes] = []
    radius = 190
    for y in range(size):
        row = bytearray()
        for x in range(size):
            alpha = rounded_rect_alpha(x, y, size, radius)
            if alpha == 0:
                row.extend((0, 0, 0, 0))
                continue

            t = (x + y) / (size * 2)
            r = int(14 + 24 * t)
            g = int(25 + 60 * t)
            b = int(33 + 78 * t)

            in_left_bar = 276 <= x <= 372 and 250 <= y <= 774
            in_right_bar = 652 <= x <= 748 and 250 <= y <= 774
            in_cross = 338 <= x <= 686 and 462 <= y <= 562
            in_spark = (x - 512) ** 2 + (y - 512) ** 2 <= 58**2
            in_mark = in_left_bar or in_right_bar or in_cross or in_spark

            if in_mark:
                mix = max(0, min(1, (y - 230) / 560))
                r = int(125 + 32 * (1 - mix))
                g = int(199 + 28 * mix)
                b = int(255 - 125 * mix)

            row.extend((r, g, b, alpha))
        rows.append(bytes(row))
    write_png(path, size, size, rows)


def main() -> None:
    if not shutil.which("sips") or not shutil.which("iconutil"):
        raise SystemExit("sips and iconutil are required on macOS to build .icns assets")
    ASSETS.mkdir(parents=True, exist_ok=True)
    if ICONSET.exists():
        shutil.rmtree(ICONSET)
    ICONSET.mkdir()
    make_icon_png(PNG_PATH)

    sizes = [16, 32, 64, 128, 256, 512, 1024]
    for size in sizes:
        output = ICONSET / f"icon_{size}x{size}.png"
        subprocess.run(["sips", "-z", str(size), str(size), str(PNG_PATH), "--out", str(output)], check=True, stdout=subprocess.DEVNULL)
        if size <= 512:
            output_2x = ICONSET / f"icon_{size}x{size}@2x.png"
            subprocess.run(["sips", "-z", str(size * 2), str(size * 2), str(PNG_PATH), "--out", str(output_2x)], check=True, stdout=subprocess.DEVNULL)

    subprocess.run(["iconutil", "-c", "icns", str(ICONSET), "-o", str(ICNS_PATH)], check=True)
    print(ICNS_PATH)


if __name__ == "__main__":
    main()
