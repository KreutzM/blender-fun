"""Validate exported GLB structure with Python stdlib, fail on missing rig/morph."""
from pathlib import Path
import hashlib
import json
import struct
import sys
root=Path(sys.argv[1] if len(sys.argv)>1 else "output/owli_glb")
glb=root/"owli_avatar.glb"
raw=glb.read_bytes()
assert len(raw)>200_000,"Missing/suspiciously small GLB"
magic,version,length=struct.unpack_from("<4sII",raw,0)
assert magic==b"glTF" and version==2 and length==len(raw),"Invalid GLB 2.0"
chunk_length,chunk_type=struct.unpack_from("<I4s",raw,12)
assert chunk_type==b"JSON","Invalid GLB JSON chunk"
model=json.loads(raw[20:20+chunk_length])
names={x.get("name","") for x in model.get("nodes",[])}
mesh_names={x.get("name","") for x in model.get("meshes",[])}
assert len(names)>=65,(len(names),sorted(names)[:30])
assert len(mesh_names)>=30,len(mesh_names)
assert any("jaw" == n or n.endswith("_jaw") for n in names),\
       "No articulated jaw node exported: "+str(sorted(n for n in names if "jaw" in n.lower()))
assert any("Beak" in x and "lower" in x for x in mesh_names),\
       "No distinct articulated lower beak mesh"
morph_sets=[]
for mesh in model.get("meshes",[]):
    names_in=mesh.get("extras",{}).get("targetNames",[])
    for prim in mesh.get("primitives",[]):
        if prim.get("targets"): morph_sets.append((mesh.get("name",""),names_in,len(prim["targets"])))
assert morph_sets,"No glTF morph targets survived"
assert any("Wide" in names or "Narrow" in names for _,names,_ in morph_sets),\
       "No mouth width/narrow shape keys in GLB"
assert any("Closed" in names and "Eyelid" in mesh for mesh,names,_ in morph_sets),\
       "No blink shape keys in GLB"
assert not model.get("cameras"),"Studio camera leaked into runtime GLB"
assert not model.get("extensions",{}).get("KHR_lights_punctual"),"Studio lights leaked"
manifest=json.loads((root/"owli_export_manifest.json").read_text(encoding="utf-8"))
assert manifest["sha256"]==hashlib.sha256(raw).hexdigest()
report={"nodes":len(names),"meshes":len(mesh_names),"morph_meshes":len(morph_sets),
        "morph_sets":morph_sets[:15],"bytes":len(raw),
        "has_skin":bool(model.get("skins"))}
(root/"owli_glb_structure_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print("OWLI_GLB_STRUCTURE_VERIFIED",json.dumps(report,ensure_ascii=False),flush=True)
