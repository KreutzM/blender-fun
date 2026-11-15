"""Validate Owli render files and that the project is a real Blender file."""
from pathlib import Path
import os
import struct
import sys
import json

root=Path(sys.argv[1] if len(sys.argv)>1 else "output/owli")
angles=[int(x) for x in os.environ.get("OWLI_VIEWS","0,45,90,135,180,225,270,315").split(",")]
pct=int(os.environ.get("OWLI_RESOLUTION","75"))
expected=(1200*pct//100,)*2
project=root/"owli_parametric.blend"
if not project.exists() or project.stat().st_size < 100_000:
    raise SystemExit("Missing parametric 3D .blend")
if project.open("rb").read(7)!=b"BLENDER":
    raise SystemExit("Invalid BLEND header")
manifest=json.loads((root/"owli_manifest.json").read_text())
if manifest["views_degrees"]!=angles:
    raise SystemExit("Manifest angles do not match render")
if manifest["model_objects"]<50:
    raise SystemExit("Unexpectedly small procedural model")
for angle in angles:
    p=root/("owli_%03d.png"%angle)
    if not p.exists() or p.stat().st_size < 15_000:
        raise SystemExit("Missing or tiny image "+str(p))
    with p.open("rb") as f: hdr=f.read(24)
    if hdr[:8]!=bytes([137,80,78,71,13,10,26,10]):
        raise SystemExit("Wrong PNG magic "+str(p))
    dims=struct.unpack(">II",hdr[16:24])
    if dims!=expected:
        raise SystemExit("Wrong image dimensions "+str((dims,expected)))
print("OWLI_VERIFIED",len(angles),"angles",expected,"object_count",
      manifest["model_objects"],"blend_bytes",project.stat().st_size)
