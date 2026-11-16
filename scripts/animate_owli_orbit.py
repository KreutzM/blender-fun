"""Continuous 315-degree studio orbit around Owli while his beak speaks.

This uses the actual mesh/rig, not a 2D billboard. Frames are ray-traced with
Blender Cycles; FFmpeg generates a smooth H.264 video for visual QA.
"""
import math
import os
import runpy
import json
from pathlib import Path
from mathutils import Vector
import bpy

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.getenv("OWLI_ORBIT_OUTPUT","output/owli_orbit")).resolve()
OUT.mkdir(parents=True,exist_ok=True)
os.environ["OWLI_RIG_OUTPUT"]=str(OUT)
os.environ["OWLI_RIG_BUILD_ONLY"]="1"
os.environ["OWLI_VIEWS"]="0"
runpy.run_path(str(ROOT/"scripts/rig_owli.py"),run_name="__main__")

scene=bpy.context.scene
fps=int(os.getenv("OWLI_ORBIT_FPS","6"))
duration=10
count=fps*duration
assert 4<=fps<=12 and count<=120
scene.frame_start=1
scene.frame_end=count
scene.render.fps=fps
scene.render.resolution_x=800
scene.render.resolution_y=800
scene.render.resolution_percentage=int(os.getenv("OWLI_ORBIT_SCALE","68"))
scene.cycles.samples=int(os.getenv("OWLI_ORBIT_SAMPLES","4"))
scene.cycles.use_denoising=True
scene.render.image_settings.file_format="PNG"
scene.render.image_settings.color_mode="RGB"

arm=bpy.data.objects["Owli | rig"]
face=arm.pose.bones["face"]
cam=scene.camera
cam.data.type="ORTHO"
cam.data.ortho_scale=5.85
cam.data.lens=45
face_keys=("mouth_open","mouth_wide","mouth_narrow")
snapshot_frames={}
for i in range(count):
    frame=i+1
    t=duration*i/(count-1)
    u=t/duration
    # 315 degrees of genuine parallax, slow arrival/departure.
    angle=math.radians(315)*(u-.045*math.sin(math.tau*u))
    r=9.0+.35*math.sin(math.pi*u)
    cam.location=(r*math.sin(angle),-r*math.cos(angle),
                  3.05+.23*math.sin(math.tau*u))
    target=Vector((0,.03,2.36))
    cam.rotation_euler=(target-cam.location).to_track_quat("-Z","Y").to_euler()
    cam.keyframe_insert(data_path="location",frame=frame)
    cam.keyframe_insert(data_path="rotation_euler",frame=frame)

    # Viseme-like rhythm, speech pauses, varying width and roundness.
    speaking=(.25<t<2.9) or (3.4<t<6.25) or (6.8<t<9.35)
    envelope=max(0,math.sin(2.35*math.pi*t))**2
    opening=(.16+.74*envelope) if speaking else 0
    wide=(.45+.38*math.sin(1.68*math.pi*t)) if speaking else 0
    narrow=(.35+.34*math.sin(1.33*math.pi*t+.5)) if speaking else 0
    for prop,value in zip(face_keys,(opening,wide,narrow)):
        face[prop]=max(0,min(1,value))
        face.keyframe_insert(data_path='["'+prop+'"]',frame=frame,group="Orbit speech")

    blink=0
    for blink_at in (1.9,5.15,8.25):
        blink=max(blink,max(0,1-abs(t-blink_at)/.18))
    for side in ("L","R"):
        face["blink."+side]=blink
        face.keyframe_insert(data_path='["blink.'+side+'"]',frame=frame,group="Orbit speech")

    pb=arm.pose.bones["head"]
    pb.rotation_euler[1]=.055*math.sin(1.7*t)
    pb.rotation_euler[2]=.07*math.sin(.9*t)
    pb.keyframe_insert(data_path="rotation_euler",frame=frame,group="Orbit gestures")
    gesture=max(0,1-abs(t-4.5)/1.20)
    for side,mult in (("L",1),("R",-1)):
        wing=arm.pose.bones["wing."+side]
        wing.rotation_euler[1]=mult*(.13+.42*gesture)*math.sin(2.2*t)
        wing.keyframe_insert(data_path="rotation_euler",frame=frame,group="Orbit gestures")
    if i in (0,round((count-1)*.24),round((count-1)*.50),round((count-1)*.74),count-1):
        snapshot_frames[frame]=round(math.degrees(angle))

scene.frame_set(1)
bpy.context.view_layer.update()
project=OUT/"owli_orbit_speaking.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(project))
print("OWLI_ORBIT_READY",count,"frames",
      "angle_end",round(math.degrees(angle)),"rig",len(arm.pose.bones),flush=True)
for frame,degree in snapshot_frames.items():
    scene.frame_set(frame)
    scene.render.filepath=str(OUT/f"shot_{frame:03d}.png")
    bpy.ops.render.render(write_still=True)
    print("OWLI_ORBIT_SHOT",frame,degree,flush=True)
scene.frame_set(1)
frame_dir=OUT/"frames"
frame_dir.mkdir(exist_ok=True)
scene.render.filepath=str(frame_dir/"frame_")
bpy.ops.render.render(animation=True)
(OUT/"orbit_report.json").write_text(json.dumps({
 "seconds":duration,"source_fps":fps,"frames":count,
 "camera_angle_deg":315,"snapshots":snapshot_frames,
 "speech_mode":"procedural viseme-like demo, no actual audio",
 "rig_bones":len(arm.pose.bones),"blender_version":bpy.app.version_string,
 "blend":project.name},indent=2),encoding="utf-8")
print("OWLI_ORBIT_COMPLETE",count,flush=True)
