"""Animation-ready Owli: bone controls, mesh-binding, blink morphs, demonstration."""
import bpy, os, json, math, runpy
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get("OWLI_RIG_OUTPUT","output/owli_rig")).resolve()
OUT.mkdir(parents=True,exist_ok=True)
os.environ["OWLI_BUILD_ONLY"]="1"
runpy.run_path(str(ROOT/"scenes/owli.py"),run_name="__main__")
scene=bpy.context.scene
scene.render.resolution_x=720
scene.render.resolution_y=720
scene.render.resolution_percentage=int(os.environ.get("OWLI_RIG_SCALE","75"))
scene.cycles.samples=int(os.environ.get("OWLI_RIG_SAMPLES","5"))
scene.cycles.use_denoising=os.environ.get("OWLI_NO_DENOISE","0")!="1"
FPS=int(os.environ.get("OWLI_RIG_FPS","8"))
LAST=FPS*6
scene.render.fps=FPS;scene.frame_start=1;scene.frame_end=LAST
scene.render.image_settings.file_format="PNG"
scene.render.image_settings.color_mode="RGBA"

rigcol=bpy.data.collections.new("00 | RIG / select and pose")
scene.collection.children.link(rigcol)
data=bpy.data.armatures.new("Owli armature")
arm=bpy.data.objects.new("Owli | rig",data)
rigcol.objects.link(arm);arm.show_in_front=True
bpy.context.view_layer.objects.active=arm
bpy.ops.object.mode_set(mode="EDIT")
eb=data.edit_bones
def bone(n,a,b,parent=None):
    ob=eb.new(n);ob.head=a;ob.tail=b
    if parent:ob.parent=eb[parent]
    return ob
bone("root",(0,0,.10),(0,0,.70))
bone("body",(0,.08,.71),(0,.08,2.76),"root")
bone("head",(0,-.02,2.86),(0,-.02,4.19),"body")
bone("face",(0,-.85,3.62),(0,-.85,4.11),"head")
for sign in (-1,1):
    side="R" if sign<0 else "L"
    bone("wing."+side,(sign*.78,0,2.52),(sign*1.38,0,2.06),"body")
    bone("foot."+side,(sign*.47,-.70,.92),(sign*.47,-.83,.72),"root")
    for toe in range(3):
        x=sign*.47+(toe-1)*.18
        bone("toe."+side+"."+str(toe),(x,-.74,.92),(x,-1.04,.78),"foot."+side)
    bone("toe."+side+".rear",(sign*.47,-.70,.86),(sign*.47,-.58,.66),"foot."+side)
    bone("gaze."+side,(sign*.51,-.83,3.45),(sign*.51,-1.04,3.45),"head")
bone("tail",(0,.49,1.22),(0,.55,.57),"body")
bpy.ops.object.mode_set(mode="OBJECT")
for b in arm.pose.bones:b.rotation_mode="XYZ"
arm.pose.bones["face"]["blink.L"]=0.0
arm.pose.bones["face"]["blink.R"]=0.0
arm["controls"]="Pose Mode: head, wing.L/R, gaze.L/R, tail, feet + toes. Face bone custom blink.L/R: 0=open, 1=closed."
arm["model_source"]="scenes/owli.py and config/owli.json"
assign={}
def bind(ob,bn):
    before=ob.matrix_world.copy()
    ob.parent=arm;ob.parent_type="BONE";ob.parent_bone=bn
    # Compute the new parent bone matrix before compensating the child.
    # Without an evaluated pose, freshly created eyelids may jump to the feet.
    bpy.context.view_layer.update()
    ob.matrix_world=before
    bpy.context.view_layer.update()
    delta=(ob.matrix_world.translation-before.translation).length
    if delta>.015:
        raise RuntimeError("Rig parenting displaced "+ob.name+": "+str(delta))
    assign[ob.name]=bn

for collection in list(bpy.data.collections):
    code=collection.name[:2]
    if code not in ("01","02","03","04","05","06","07","08","09","10","11","12","13"):continue
    if code=="11":continue # the wooden perch must remain fixed in space
    for ob in list(collection.objects):
        name=ob.name
        bn="body"
        if code in ("02","04","05","06","07","08","13"):bn="head"
        if code=="09":
            if name.startswith(("Wing.L","Wing 1")):bn="wing.L"
            elif name.startswith(("Wing.R","Wing -1")):bn="wing.R"
            else:raise ValueError("Wing not separated into sides: "+name)
        if code=="10":bn="tail"
        if code=="12":
            side="R" if (" -1 " in name or name.endswith(" -1")) else "L"
            bn="foot."+side
            if " toe " in name:
                t=name.split(" toe ",1)[1].split(" ",1)[0]
                if t in ("0","1","2"):bn="toe."+side+"."+t
            elif "hind toe" in name:bn="toe."+side+".rear"
        if code=="07" and name.startswith(("Eye -1","Eye 1")):
            side="R" if name.startswith("Eye -1") else "L"
            if "dark glossy socket" not in name:bn="gaze."+side
        bind(ob,bn)

# Actual eyelid meshes use open and closed 3D shape keys; a driver connects
# each to the corresponding face bone property so it remains editable in Blender.
lids=[]
ivory=bpy.data.materials.get("06 Ivory mask and bib")
proportions=json.loads((ROOT/"config/owli.json").read_text())["proportions"]
for sign in (-1,1):
    side="R" if sign<0 else "L"
    radius=.35*float(proportions["eye_scale"])*1.14
    vx=[];closed=[];faces=[];ns=20;nr=6
    for i in range(ns+1):
        x=-radius+2*radius*i/ns
        arc=radius*math.sqrt(max(0,1-(x/radius)**2))
        for j in range(nr+1):
            t=j/nr
            y=-1.055-.035*math.sqrt(max(0,1-(x/radius)**2))
            top=arc+.025
            vx.append((x,y,top-(.04)*t))
            closed.append((x,y,top-(2*arc+.025)*t))
    for i in range(ns):
        for j in range(nr):
            a=i*(nr+1)+j;faces.append((a,a+nr+1,a+nr+2,a+1))
    mesh=bpy.data.meshes.new("Eyelid "+side)
    mesh.from_pydata(vx,[],faces);mesh.update()
    ob=bpy.data.objects.new("Eyelid."+side+" | 0=open 1=closed",mesh)
    bpy.data.collections["06 | Face"].objects.link(ob)
    ob.location=(sign*.51,0,3.45)
    if ivory:mesh.materials.append(ivory)
    ob.shape_key_add(name="Open",from_mix=False)
    target=ob.shape_key_add(name="Closed",from_mix=False)
    for point,v in zip(target.data,closed):point.co=v
    mod=ob.modifiers.new("Thin soft eyelid","SOLIDIFY");mod.thickness=.012
    bind(ob,"head")
    print("OWLI_LID_WORLD",side,tuple(round(v,3) for v in ob.matrix_world.translation),flush=True)
    d=target.driver_add("value").driver
    d.type="SCRIPTED"
    var=d.variables.new();var.name="blink";var.type="SINGLE_PROP"
    var.targets[0].id=arm
    var.targets[0].data_path='pose.bones["face"]["blink.'+side+'"]'
    d.expression="max(0,min(1,blink))"
    lids.append(ob.name)

cam=scene.camera
cam.location=(0,-10,3.05)
cam.rotation_euler=(Vector((0,0,2.25))-cam.location).to_track_quat("-Z","Y").to_euler()
cam.data.ortho_scale=5.6

def keyrot(bone_name,frame,axis,value):
    pb=arm.pose.bones[bone_name];pb.rotation_euler[axis]=value
    pb.keyframe_insert(data_path="rotation_euler",frame=frame,group=bone_name)
def keyblink(side,frame,value):
    pb=arm.pose.bones["face"];pb["blink."+side]=float(value)
    pb.keyframe_insert(data_path='["blink.'+side+'"]',frame=frame,group="face")
# Neutral starting and ending keyframes, so user can inspect the idle pose.
for frame in (1,LAST):
    for bn in ["head","wing.L","wing.R","tail","gaze.L","gaze.R"]:
        for axis in range(3):keyrot(bn,frame,axis,0)
    for side in ("L","R"):
        keyblink(side,frame,0)
        for part in ("0","1","2","rear"):
            keyrot("toe."+side+"."+part,frame,0,0)
# Gaze, gentle head tilt, feathered wing greeting and a toe grip.
for time,value in ((1.1,-.19),(2.3,.17),(3.6,-.12),(5.1,0)):
    keyrot("head",round(time*FPS),1,value)
for time,value in ((2.4,0),(3.1,.92),(3.75,-.22),(4.35,.70),(5.2,0)):
    f=round(time*FPS)
    keyrot("wing.L",f,1,value);keyrot("wing.R",f,1,-value)
for time,value in ((.75,-.10),(1.65,.14),(2.7,0)):
    f=round(time*FPS)
    for side in ("L","R"):keyrot("gaze."+side,f,2,value)
for side in ("L","R"):
    for time,value in ((.87,0),(1.0,1),(1.14,0),(4.60,0),(4.75,1),(4.92,0)):
        keyblink(side,max(1,round(time*FPS)),value)
for time,value in ((2.35,0),(2.48,1),(2.66,0)):
    keyblink("R",round(time*FPS),value)
for time,value in ((2.8,0),(3.3,.20),(4.3,0)):
    for side in ("L","R"):
        for toe in ("0","1","2"):
            keyrot("toe."+side+"."+toe,round(time*FPS),0,value)
for time,value in ((1,0),(2.6,.14),(4.8,-.10),(LAST/FPS,0)):
    keyrot("tail",round(time*FPS),0,value)

# Verify the animated properties actually change the evaluated 3D pose.
scene.frame_set(1)
bpy.context.view_layer.update()
wing_rest=arm.pose.bones["wing.L"].matrix.copy()
scene.frame_set(round(3.1*FPS))
bpy.context.view_layer.update()
wing_raised=arm.pose.bones["wing.L"].matrix.copy()
assert (wing_rest.translation-wing_raised.translation).length < .001
assert max(abs(wing_raised[i][j]-wing_rest[i][j]) for i in range(3) for j in range(3))>.15, "Wing bone not animated"
scene.frame_set(round(2.48*FPS))
bpy.context.view_layer.update()
eyelid=bpy.data.objects.get("Eyelid.R | 0=open 1=closed")
assert eyelid and eyelid.data.shape_keys
blink_eval=eyelid.data.shape_keys.key_blocks["Closed"].value
assert blink_eval>.6, "Blink driver did not close the eyelid"
print("OWLI_RIG_MOTION_VERIFIED", "wing_rotation_changed",True,"blink_closed",blink_eval,flush=True)
scene.frame_set(1)
bpy.context.view_layer.update()
project=OUT/"owli_rigged.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(project))
assert len(lids)==2 and len(assign)>50
assert sum(v=="wing.L" for v in assign.values())>6
assert sum(v=="wing.R" for v in assign.values())>6
report={"bone_count":len(arm.pose.bones),"bones":sorted(arm.pose.bones.keys()),
        "bound_objects":len(assign),"eyelids":lids,"frames":LAST,"fps":FPS,
        "wing_L":sum(v=="wing.L" for v in assign.values()),
        "wing_R":sum(v=="wing.R" for v in assign.values()),
        "blender_version":bpy.app.version_string,"blend_file":project.name}
(OUT/"rig_report.json").write_text(json.dumps(report,indent=2))
print("OWLI_RIG_READY",report,flush=True)
for name,second in (("pose_idle.png",0),("pose_glance.png",1.65),
                    ("pose_wink.png",2.48),("pose_wings.png",3.1)):
    scene.frame_set(max(1,min(LAST,round(second*FPS))))
    scene.render.filepath=str(OUT/name)
    bpy.ops.render.render(write_still=True)
    print("OWLI_RIG_STILL",name,flush=True)
scene.frame_set(1)
frames=OUT/"frames";frames.mkdir(exist_ok=True)
scene.render.filepath=str(frames/"frame_")
bpy.ops.render.render(animation=True)
print("OWLI_RIG_FRAMES_COMPLETE",LAST,flush=True)
