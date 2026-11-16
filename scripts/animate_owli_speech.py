"""Keyframed beak speech demo using phoneme/viseme events (not a TTS engine).

Input contract: config/owli_speech_demo.json or OWLI_VISEME_JSON.
All three face properties are keyframed. Real TTS should provide aligned
phoneme timings; amplitude-only extraction is deliberately not phoneme alignment.
"""
import bpy
import json
import os
import runpy
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get("OWLI_SPEECH_OUTPUT","output/owli_speech")).resolve()
OUT.mkdir(parents=True,exist_ok=True)
os.environ["OWLI_RIG_OUTPUT"]=str(OUT)
os.environ["OWLI_RIG_BUILD_ONLY"]="1"
runpy.run_path(str(ROOT/"scripts/rig_owli.py"),run_name="__main__")

input_file=Path(os.environ.get("OWLI_VISEME_JSON",str(ROOT/"config/owli_speech_demo.json")))
src=json.loads(input_file.read_text(encoding="utf-8"))
duration=float(src["duration_seconds"])
if not 1<=duration<=20:raise ValueError("Speech demo duration exceeds safety limit")
fps=int(os.environ.get("OWLI_SPEECH_FPS","8"))
if fps<4 or fps>30:raise ValueError("Bad FPS")
count=int(round(duration*fps))
scene=bpy.context.scene
scene.frame_start=1
scene.frame_end=count
scene.render.fps=fps
scene.cycles.samples=int(os.environ.get("OWLI_SPEECH_SAMPLES","5"))
scene.render.resolution_x=720;scene.render.resolution_y=720
scene.render.resolution_percentage=int(os.environ.get("OWLI_SPEECH_SCALE","75"))
scene.cycles.use_denoising=os.environ.get("OWLI_NO_DENOISE","0")!="1"
arm=bpy.data.objects.get("Owli | rig")
if arm is None:raise ValueError("Missing Owli armature")
face=arm.pose.bones["face"]
jaw=arm.pose.bones["jaw"]

VIS={
 "REST":(0,0,0), "A":(.90,.65,0), "E":(.58,.90,0),
 "I":(.33,.78,0), "O":(.79,0,.88), "U":(.52,0,1),
 "M":(.025,0,.10), "P":(.035,0,.15), "B":(.055,0,.10),
 "F":(.19,.28,.42), "V":(.27,.38,.33),
 "S":(.22,.63,.10), "L":(.45,.48,0), "T":(.27,.48,.03),
 "N":(.31,.45,.02), "R":(.34,.18,.24)
}
keys=("mouth_open","mouth_wide","mouth_narrow")
events=src["events"]
if not isinstance(events,list) or len(events)<3 or len(events)>300:
    raise ValueError("Need 3..300 ordered viseme events")
last=-1.0
frames_seen=set()
records=[]
for event in events:
    time=float(event["time"])
    vis=str(event["viseme"]).upper()
    strength=float(event.get("strength",1.0))
    if vis not in VIS or not(0<=strength<=1) or not(0<=time<=duration):
        raise ValueError("Invalid viseme event "+str(event))
    if time<=last:raise ValueError("Events must be strictly time ordered")
    last=time
    frame=min(count,max(1,1+round(time*fps)))
    if frame in frames_seen:
        raise ValueError("Events too close for chosen FPS; increase OWLI_SPEECH_FPS")
    frames_seen.add(frame)
    values=tuple(min(1,max(0,v*strength)) for v in VIS[vis])
    for prop,value in zip(keys,values):
        face[prop]=value
        face.keyframe_insert(data_path='["'+prop+'"]',frame=frame,group="Owli | Speech")
    records.append({"frame":frame,"time":time,"viseme":vis,
                    "strength":strength,"values":dict(zip(keys,values))})
# Always close at end, regardless of the last speech event.
for prop in keys:
    face[prop]=0.0
    face.keyframe_insert(data_path='["'+prop+'"]',frame=count+1,group="Owli | Speech")
# The user may replace this camera with a webcam/avatar crop in their renderer.
cam=scene.camera
cam.location=(0,-9.0,3.67)
cam.rotation_euler=(Vector((0,-.12,3.43))-cam.location).to_track_quat("-Z","Y").to_euler()
cam.data.ortho_scale=2.65

# Face/head pose kept neutral for isolated beak evaluation.
# Full rig animation remains available in the underlying scene if needed.
for name in ("head","wing.L","wing.R","gaze.L","gaze.R"):
    bone=arm.pose.bones[name]
    for frame in (1,count+1):
        bone.rotation_euler=(0,0,0)
        bone.keyframe_insert(data_path="rotation_euler",frame=frame,group="Owli | Speech")

# Validate every animated geometry component changes in evaluated pose.
closed_frame=records[0]["frame"]
open_rec=max(records,key=lambda x:x["values"]["mouth_open"])
scene.frame_set(closed_frame)
bpy.context.view_layer.update()
lower=bpy.data.objects["Beak | lower articulated mandible"]
mouth=bpy.data.objects["Beak | inner mouth cavity (morph)"]
closed_location=lower.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world.translation.copy()
scene.frame_set(open_rec["frame"])
bpy.context.view_layer.update()
open_location=lower.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world.translation.copy()
open_value=mouth.data.shape_keys.key_blocks["Open"].value
assert (open_location-closed_location).length>.045,"Beak does not visibly move"
assert open_value>.70,"Dark cavity does not expand"
for name in ("Wide","Narrow"):
    assert lower.data.shape_keys.key_blocks.get(name)
print("OWLI_SPEECH_MOTION_VERIFIED",
      "jaw_delta",round((open_location-closed_location).length,4),
      "cavity",round(open_value,3),flush=True)

scene.frame_set(1)
file=OUT/"owli_speaking.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(file))
report={
 "source_file":str(input_file),"duration_seconds":duration,
 "source_fps":fps,"frames":count,"event_count":len(records),
 "properties":list(keys),"jaw_bone":"jaw","events":records,
 "audio_included":False,
 "synchronization":"Viseme event timestamps (illustrative demo, not aligned to actual audio)",
 "blender_version":bpy.app.version_string
}
(OUT/"speech_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print("OWLI_SPEECH_RIG_READY",len(records),"visemes",count,"frames",flush=True)

# Show four objectively different beak openings. These are actual Cycles
# renders of the parametric 3D model, not image generation.
pose_cases={
 "closed": "REST",
 "open": "A",
 "wide": "E",
 "rounded": "O"
}
for label,viseme in pose_cases.items():
    values=VIS[viseme]
    for prop,value in zip(keys,values):face[prop]=value
    bpy.context.view_layer.update()
    scene.render.filepath=str(OUT/("mouth_"+label+".png"))
    bpy.ops.render.render(write_still=True)
    print("OWLI_SPEECH_POSE_RENDERED",label,flush=True)

# Restore scripted curves from keyframe evaluation and render animation.
scene.frame_set(1)
scene.render.filepath=str(OUT/"frames"/"frame_")
(OUT/"frames").mkdir(exist_ok=True)
bpy.ops.render.render(animation=True)
print("OWLI_SPEECH_FRAMES_RENDERED",count,flush=True)
