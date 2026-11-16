"""Validate real orbit rendering, editable Blender source and video."""
import sys,json,struct
from pathlib import Path
import subprocess
p=Path(sys.argv[1] if len(sys.argv)>1 else "output/owli_orbit")
report=json.loads((p/"orbit_report.json").read_text(encoding="utf-8"))
assert report["frames"]==report["source_fps"]*10
assert report["rig_bones"]>=20
project=p/"owli_orbit_speaking.blend"
assert project.stat().st_size>250_000
with project.open("rb") as f: assert f.read(7)==b"BLENDER"
for frame in report["snapshots"]:
    still=p/f"shot_{int(frame):03d}.png"
    assert still.stat().st_size>15000,still
video=p/"owli_orbit_speaking.mp4"
assert video.stat().st_size>70000
data=json.loads(subprocess.check_output(["ffprobe","-v","error",
 "-show_entries","format=duration:stream=codec_name,codec_type,width,height",
 "-of","json",str(video)],text=True))
v=next(x for x in data["streams"] if x["codec_type"]=="video")
assert v["codec_name"]=="h264" and v["width"]==720 and v["height"]==720
duration=float(data["format"]["duration"])
assert 9.6<duration<10.4
board=p/"owli_orbit_storyboard.png"
assert board.stat().st_size>25000
print("OWLI_ORBIT_VERIFIED",round(duration,2),"seconds",
      report["camera_angle_deg"],"degrees",report["rig_bones"],"bones")
