"""Check animatable bones, eyelids and actual MP4/BLEND output."""
import json,subprocess,sys
from pathlib import Path
p=Path(sys.argv[1] if len(sys.argv)>1 else "output/owli_rig")
r=json.loads((p/"rig_report.json").read_text())
assert r["bone_count"]>=19,r
assert r["wing_L"]>6 and r["wing_R"]>6,r
assert len(r["eyelids"])==2,r
assert r["bound_objects"]>50,r
bl=p/"owli_rigged.blend"
assert bl.stat().st_size>250_000
with bl.open("rb") as f:assert f.read(7)==b"BLENDER"
for n in ("pose_idle.png","pose_glance.png","pose_wink.png","pose_wings.png","pose_sheet.png"):
    assert (p/n).stat().st_size>12_000,n
mp4=p/"owli_animation.mp4"
assert mp4.stat().st_size>50_000
info=json.loads(subprocess.check_output(["ffprobe","-v","error",
"-show_entries","format=duration:stream=codec_type,codec_name,width,height",
"-of","json",str(mp4)],text=True))
duration=float(info["format"]["duration"])
assert 5.5<=duration<=6.5,duration
vid=next(x for x in info["streams"] if x["codec_type"]=="video")
assert vid["codec_name"]=="h264" and vid["width"]>=480
print("OWLI_RIG_VERIFIED",r["bone_count"],"bones",r["bound_objects"],
      "objects",round(duration,2),"seconds")
