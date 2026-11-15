"""Validate output video with ffprobe; also check storyboard and project."""
import json
from pathlib import Path
import subprocess
import sys

if len(sys.argv) != 3:
    raise SystemExit("Usage: check_flythrough.py video.mp4 storyboard.png")
video, board = map(Path, sys.argv[1:])
project = video.parent / "reference_flythrough.blend"
assert video.stat().st_size > 100_000, "MP4 missing or suspiciously small"
assert board.stat().st_size > 10_000, "Storyboard missing or suspiciously small"
assert project.stat().st_size > 100_000, "BLEND missing or empty"
assert project.open("rb").read(7) == b"BLENDER", "Invalid Blender project"
info = json.loads(subprocess.check_output([
    "ffprobe","-v","error",
    "-show_entries","format=duration:stream=codec_name,codec_type,width,height,avg_frame_rate",
    "-of","json",str(video)], text=True))
stream=next(s for s in info["streams"] if s["codec_type"]=="video")
assert stream["codec_name"]=="h264", stream
assert (stream["width"],stream["height"])==(1280,720),stream
length=float(info["format"]["duration"])
assert 14.8 <= length <= 16.2, length
print(f"FLYTHROUGH_VALID duration={length:.2f}s, 1280x720, H.264, "
      f"size={video.stat().st_size:,} B, editable project={project.stat().st_size:,} B")
