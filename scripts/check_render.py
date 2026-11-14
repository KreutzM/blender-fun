"""Validate minimal render artifacts without external Python dependencies."""
import os
import struct
import sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit("Usage: check_render.py image.png project.blend")

png = Path(sys.argv[1])
blend = Path(sys.argv[2])
if not png.is_file() or png.stat().st_size < 10_000:
    raise SystemExit(f"PNG missing or unexpectedly small: {png}")
with png.open("rb") as file:
    header = file.read(24)
if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
    raise SystemExit("Invalid PNG signature/header")
width, height = struct.unpack(">II", header[16:24])
pct = int(os.getenv("BLENDER_RESOLUTION_PERCENT", "100"))
expected = (1920 * pct // 100, 1080 * pct // 100)
if (width, height) != expected:
    raise SystemExit(f"Wrong image dimensions: {(width, height)} vs {expected}")
if not blend.is_file() or blend.stat().st_size < 1024:
    raise SystemExit(f"BLEND project missing or empty: {blend}")
with blend.open("rb") as file:
    if file.read(7) != b"BLENDER":
        raise SystemExit("Invalid .blend header")
print(f"OK: PNG {width}x{height} ({png.stat().st_size:,} B), "
      f"BLEND {blend.stat().st_size:,} B")
