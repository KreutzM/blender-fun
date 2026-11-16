"""Produce an explicit browser-runtime GLB from procedural Owli.

This is an export candidate, NOT evidence of successful Three.js integration.
Blender drivers and bone custom properties are not portable as glTF controls;
the application must drive the exported jaw/bones and blendshapes explicitly.
"""
from pathlib import Path
import bpy
import hashlib
import json
import os
import runpy

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.getenv("OWLI_EXPORT_DIR","output/owli_glb")).resolve()
OUT.mkdir(parents=True,exist_ok=True)
os.environ["OWLI_VIEWS"]="0"
os.environ["OWLI_RIG_OUTPUT"]=str(OUT)
os.environ["OWLI_RIG_BUILD_ONLY"]="1"
os.environ["OWLI_BUILD_ONLY"]="1"

runpy.run_path(str(ROOT/"scripts"/"rig_owli.py"),run_name="__main__")
scene=bpy.context.scene
arm=bpy.data.objects.get("Owli | rig")
assert arm and "jaw" in arm.pose.bones
assert "face" in arm.pose.bones
# glTF does not preserve Blender driver expressions. Neutralize driver-fed
# facial properties before exporting. Animation stays in the editable BLEND,
# but the browser will apply its own semantic controls to GLB nodes/morphs.
face=arm.pose.bones["face"]
for key in ("mouth_open","mouth_wide","mouth_narrow","blink.L","blink.R"):
    face[key]=0.0
scene.frame_set(1)
bpy.context.view_layer.update()

include_collections=(
    "01 | Body","02 | Head","03 | Body feathers","04 | Head feathers",
    "05 | Crest","06 | Face","07 | Eyes","08 | Beak","09 | Wings",
    "10 | Tail","11 | Branch","12 | Feet","13 | AI Emblem")
objects=[arm]
for name in include_collections:
    objects.extend(bpy.data.collections[name].objects[:])
seen=set()
objects=[ob for ob in objects if not (ob.name in seen or seen.add(ob.name))]
assert len(objects)>70,len(objects)
# Do not export camera, floor, lights, hidden auxiliary rigs or studio props.
assert all(ob.type in ("MESH","CURVE","ARMATURE") for ob in objects)
bpy.ops.object.select_all(action="DESELECT")
for ob in objects: ob.select_set(True)
bpy.context.view_layer.objects.active=arm

target=OUT/"owli_avatar.glb"
bpy.ops.export_scene.gltf(
    filepath=str(target),export_format="GLB",
    use_selection=True,export_animations=False,
    export_skins=True,export_morph=True,
    export_morph_normal=True,export_apply=False,
    export_cameras=False,export_lights=False,
)
sha=hashlib.sha256(target.read_bytes()).hexdigest()
report={
    "id":"owli-classic-parametric-v1",
    "source_repo":"KreutzM/blender-fun",
    "blender_version":bpy.app.version_string,
    "format":"GLB",
    "binary":"owli_avatar.glb",
    "sha256":sha,
    "bytes":target.stat().st_size,
    "exported_objects":len(objects),
    "semantic_mapping_candidate":{
      "jaw":"jaw",
      "mouth_wide":{"mesh":"Beak | lower articulated mandible","morph":"Wide"},
      "mouth_narrow":{"mesh":"Beak | lower articulated mandible","morph":"Narrow"},
      "blink_left":{"mesh":"Eyelid.L | 0=open 1=closed","morph":"Closed"},
      "blink_right":{"mesh":"Eyelid.R | 0=open 1=closed","morph":"Closed"},
      "gaze_left":"gaze.L","gaze_right":"gaze.R",
      "head":"head","wing_left":"wing.L","wing_right":"wing.R"
    },
    "notes":[
      "Explicit candidate mapping must be revalidated against actual exported glTF names",
      "Blender drivers/custom bone properties are not exported as live glTF controls",
      "Browser CharacterAdapter must drive jaw rotation and morphs directly",
      "No runtime browser import or visual QA implied by export validation",
      "Studio lights/background omitted; character retains perch"
    ]
}
(OUT/"owli_export_manifest.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print("OWLI_GLB_EXPORTED",target,"bytes",target.stat().st_size,"sha256",sha,flush=True)
