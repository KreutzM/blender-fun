"""Check a real speaking .blend, viseme report, images and decoded MP4."""
from pathlib import Path
import json,subprocess,sys
p=Path(sys.argv[1] if len(sys.argv)>1 else "output/owli_speech")
r=json.loads((p/"speech_report.json").read_text(encoding="utf-8"))
assert r["event_count"]>=10 and r["frames"]>=35,r
assert r["audio_included"] is False
assert set(r["properties"])=={"mouth_open","mouth_wide","mouth_narrow"}
assert any(x["values"]["mouth_open"]>.8 for x in r["events"])
assert any(x["values"]["mouth_wide"]>.7 for x in r["events"])
assert any(x["values"]["mouth_narrow"]>.8 for x in r["events"])
project=p/"owli_speaking.blend"
assert project.stat().st_size>200_000
with project.open("rb") as f:assert f.read(7)==b"BLENDER"
for n in ("mouth_closed.png","mouth_open.png","mouth_wide.png",
          "mouth_rounded.png","mouth_contact_sheet.png"):
    assert (p/n).stat().st_size>10000,n
mp4=p/"owli_speech_demo.mp4"
assert mp4.stat().st_size>30000
data=json.loads(subprocess.check_output(["ffprobe","-v","error",
"-show_entries","format=duration:stream=codec_type,codec_name,width,height",
"-of","json",str(mp4)],text=True))
duration=float(data["format"]["duration"])
video=next(s for s in data["streams"] if s["codec_type"]=="video")
assert abs(duration-r["duration_seconds"])<.45
assert video["codec_name"]=="h264" and video["width"]>=480
print("OWLI_SPEECH_VERIFIED",r["event_count"],"events",duration,
      "seconds",video["width"],video["height"])
