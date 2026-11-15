#!/usr/bin/env python3
"""Owli — procedural, editable 360-degree Blender mascot.

Reference: user-supplied 'Owli – 360° Charakter-Referenzblatt', Variante A.
Axis convention: X = right, Y = back (+Y), Z = up. Front faces -Y.
Scene is fully generated from config/owli.json; no imported model or 2D billboard.
Blender 4.5.15; python scenes/owli.py -- OUTPUT_DIR
"""
import bpy
import json
import math
import os
import random
import sys
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
args = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
OUT = Path(args[0] if args else "output/owli").resolve()
OUT.mkdir(parents=True, exist_ok=True)
CONFIG = Path(os.getenv("OWLI_CONFIG", str(ROOT / "config" / "owli.json")))
cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
p = cfg["proportions"]
quality = cfg["model_detail"]
palette = cfg["palette"]
rng = random.Random(int(cfg.get("seed", 2026)))
head_scale = float(p["head_scale"])
body_width = float(p["body_width"])
eye_scale = float(p["eye_scale"])
wingspan = float(p["wing_spread"])
feather_detail = max(0.4, min(2.0, float(quality["feather_density"])))
samples = int(os.getenv("OWLI_SAMPLES", "12"))
resolution = int(os.getenv("OWLI_RESOLUTION", "75"))
view_degrees = [int(x) for x in os.getenv("OWLI_VIEWS", "0,45,90,135,180,225,270,315").split(",")]
if not (1 <= samples <= 128 and 30 <= resolution <= 100):
    raise ValueError("Bad samples / resolution")
if not (0.8 <= head_scale <= 1.2 and 0.75 <= body_width <= 1.25 and
        0.8 <= eye_scale <= 1.2 and 0.0 <= wingspan <= 1.0):
    raise ValueError("Owli proportion outside supported range")
if len(view_degrees) != len(set(view_degrees)) or not view_degrees or any(d < 0 or d >= 360 for d in view_degrees):
    raise ValueError("OWLI_VIEWS must contain unique angles in [0,360)")

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = samples
scene.cycles.use_denoising = True
scene.render.resolution_x = 1200
scene.render.resolution_y = 1200
scene.render.resolution_percentage = resolution
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.film_transparent = False
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"

# All geometry can be edited independently via the Outliner collections.
collections = {}
def coll(name):
    if name not in collections:
        c = bpy.data.collections.new(name)
        scene.collection.children.link(c)
        collections[name] = c
    return collections[name]

def move_to(obj, collection):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll(collection).objects.link(obj)
    return obj

def hexrgb(key):
    color = palette[key].lstrip("#")
    return tuple(int(color[i:i+2], 16)/255 for i in (0,2,4))

def mat(name, key, rough=.68, metallic=0, glow=0, gradient=False):
    m = bpy.data.materials.new(name)
    m.use_nodes=True
    bs=m.node_tree.nodes.get("Principled BSDF")
    rgb=hexrgb(key)
    bs.inputs["Base Color"].default_value=(*rgb,1)
    bs.inputs["Roughness"].default_value=rough
    bs.inputs["Metallic"].default_value=metallic
    if glow:
        bs.inputs["Emission Color"].default_value=(*rgb,1)
        bs.inputs["Emission Strength"].default_value=glow
    if gradient:
        n=m.node_tree.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value=105
        bump=m.node_tree.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value=.11
        bump.inputs["Distance"].default_value=.012
        m.node_tree.links.new(n.outputs["Fac"],bump.inputs["Height"])
        m.node_tree.links.new(bump.outputs["Normal"],bs.inputs["Normal"])
    return m

M={
 "navy":mat("01 Deep midnight blue / feather roots","navy",gradient=True),
 "blue":mat("02 Cobalt blue / feather plates","cobalt",gradient=True),
 "blue2":mat("03 Sapphire bright blue","sapphire",gradient=True),
 "cyan":mat("04 Turquoise feather highlights","cyan",gradient=True),
 "turquoise":mat("05 Cool teal secondary feathers","turquoise",gradient=True),
 "white":mat("06 Ivory mask and bib","white",rough=.91,gradient=True),
 "cream":mat("07 Warm ivory plumage","cream",rough=.92),
 "orange":mat("08 Orange breast accent / beak","orange",rough=.47),
 "gold":mat("09 Golden feather band","gold",rough=.55),
 "eye_dark":mat("10 Near-black iris/pupil","eye_dark",rough=.11),
 "iris":mat("11 Bright blue iris","sapphire",rough=.09,metallic=.06),
 "iris_cyan":mat("12 Turquoise eye detail","cyan",rough=.12,glow=.15),
 "glow":mat("13 Cyan bioluminescent AI circuitry","cyan",rough=.18,glow=3.5),
 "black":mat("14 Charcoal claws","eye_dark",rough=.35),
 "branch":mat("15 Warm natural branch","wood",rough=.84,gradient=True),
 "wood_light":mat("16 Branch end grain","wood_light",rough=.8),
 "eye_reflection":mat("17 White crisp eye glints","white",rough=.02,glow=.7),
 "bg":mat("18 Studio seamless background","background",rough=.96),
}

def uv(name, center, scale, material, collection, segments=36, rings=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=center)
    obj=bpy.context.object
    obj.name=name
    obj.scale=scale
    obj.data.materials.append(material)
    for poly in obj.data.polygons: poly.use_smooth=True
    return move_to(obj,collection)

def cylinder(name, at, radius, depth, material, collection, vertices=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=at)
    obj=bpy.context.object; obj.name=name
    obj.data.materials.append(material)
    for poly in obj.data.polygons: poly.use_smooth=True
    return move_to(obj,collection)

def cone_between(name, start, end, r0, r1, material, collection, vertices=16):
    a,b=Vector(start),Vector(end)
    d=b-a
    bpy.ops.mesh.primitive_cone_add(vertices=vertices,radius1=r0,radius2=r1,
                                    depth=d.length,location=(a+b)*.5)
    o=bpy.context.object; o.name=name
    o.rotation_euler=d.to_track_quat("Z","Y").to_euler()
    o.data.materials.append(material)
    for poly in o.data.polygons:poly.use_smooth=True
    return move_to(o,collection)

def line(name, coords, radius, material, collection):
    c=bpy.data.curves.new(name,"CURVE"); c.dimensions="3D"
    c.resolution_u=16; c.bevel_depth=radius; c.bevel_resolution=3
    spl=c.splines.new("BEZIER")
    spl.bezier_points.add(len(coords)-1)
    for b,pt in zip(spl.bezier_points,coords):
        b.co=pt; b.handle_left_type="AUTO"; b.handle_right_type="AUTO"
    o=bpy.data.objects.new(name,c)
    coll(collection).objects.link(o)
    o.data.materials.append(material)
    return o

# Thousands of organic 3D feather strips share exactly one optimized mesh object
# per region. Each feather has a finite surface ridge and tapered silhouette,
# never a textured transparent plane or a 2D sprite.
class FeatherMesh:
    def __init__(self, name, collection):
        self.name,self.collection=name,collection
        self.v=[];self.f=[];self.mi=[];self.materials=[]
    def add(self, root, tip, width, normal, material, arch=.17):
        root,tip,n=Vector(root),Vector(tip),Vector(normal).normalized()
        a=tip-root
        side=n.cross(a)
        if side.length < 0.001: side=Vector((1,0,0))
        side.normalize()
        if material not in self.materials:self.materials.append(material)
        idx=self.materials.index(material)
        start=len(self.v); rows=6
        for i in range(rows+1):
            t=i/rows
            center=root+a*t+n*(.025+arch*math.sin(math.pi*t))
            w=width*(.12+.88*math.sin(math.pi*t)**.6)*(1-t)**.48
            for x in (-1,0,1):
                pp=center+side*(w*x*.5)+n*(.028 if x==0 else 0)
                self.v.append(tuple(pp))
        for i in range(rows):
            for j in range(2):
                aa=start+i*3+j
                self.f.append((aa,aa+1,aa+4,aa+3))
                self.mi.append(idx)
    def commit(self):
        mesh=bpy.data.meshes.new(self.name)
        mesh.from_pydata(self.v,[],self.f)
        mesh.update()
        for m in self.materials:mesh.materials.append(m)
        for poly,mi in zip(mesh.polygons,self.mi):
            poly.material_index=mi
            poly.use_smooth=True
        ob=bpy.data.objects.new(self.name,mesh)
        coll(self.collection).objects.link(ob)
        return ob

# Head, body and tail share the consistent proportions of the concept sheet:
# head 45%, torso 45%, feet and exposed tail 10% of overall height.
HC=Vector((0,-.03,3.26))
BC=Vector((0,.10,1.94))
HR=Vector((1.03,.75,.94))*head_scale
BR=Vector((.86*body_width,.71,1.07))
uv("Body | rounded chibi silhouette",BC,BR,M["navy"],"01 | Body")
uv("Head | broad owl crown",HC,HR,M["blue"],"02 | Head")

# Body feathers: dense overlapping strata that wrap the entire 360° body.
feathers=FeatherMesh("Body | 360 degree layered feathers","03 | Body feathers")
num_levels=max(10,int(15*feather_detail))
for j in range(num_levels):
    theta=.33+j*(2.14/(num_levels-1))
    slots=max(18,int((32+12*math.sin(theta))*feather_detail))
    for k in range(slots):
        phi=2*math.pi*(k+(j%2)*.5)/slots
        theta_j=theta+rng.uniform(-.025,.025)
        normal=Vector((math.sin(theta_j)*math.sin(phi)/max(.1,BR.x),
                       -math.sin(theta_j)*math.cos(phi)/BR.y,
                       math.cos(theta_j)/BR.z)).normalized()
        root=BC+Vector((BR.x*math.sin(theta_j)*math.sin(phi),
                        -BR.y*math.sin(theta_j)*math.cos(phi),
                        BR.z*math.cos(theta_j)))+normal*.03
        toward_front=abs(math.atan2(math.sin(phi),math.cos(phi)))
        if toward_front < .71 and root.z < 2.72:
            if root.z>2.48: material=M["gold"] if k%3 else M["orange"]
            elif root.z>2.17: material=M["turquoise"] if k%4 else M["cyan"]
            else: material=M["white"] if k%5 else M["cream"]
        else:
            material=[M["navy"],M["blue"],M["blue2"],M["cyan"],M["blue"]][(k+j)%5]
        length=(.33 if root.z>1.3 else .27)*rng.uniform(.89,1.17)
        tip=root+Vector((.017*math.sin(phi),0,-length))+normal*(.08*length)
        feathers.add(root,tip,.22*(32/slots)*rng.uniform(.80,1.25),
                     normal,material,arch=.04)
feathers.commit()

# Plumage on head: only at the crown, rear and temples; keep face fully clear.
head_feathers=FeatherMesh("Head | iridescent feathers and tufts","04 | Head feathers")
for j in range(max(7,int(10*feather_detail))):
    theta=.11+j*(1.80/(max(7,int(10*feather_detail))-1))
    slots=max(20,int(43*feather_detail))
    for k in range(slots):
        phi=2*math.pi*(k+(j%2)*.5)/slots
        forward=abs(math.atan2(math.sin(phi),math.cos(phi)))
        if theta>.68 and forward<1.13:
            continue  # The large white eye mask is clear.
        n=Vector((math.sin(theta)*math.sin(phi)/HR.x,
                  -math.sin(theta)*math.cos(phi)/HR.y,
                  math.cos(theta)/HR.z)).normalized()
        root=HC+Vector((HR.x*math.sin(theta)*math.sin(phi),
                        -HR.y*math.sin(theta)*math.cos(phi),
                        HR.z*math.cos(theta)))+n*.03
        length=(.26+.07*math.sin(theta))*rng.uniform(.8,1.2)
        mat_use=[M["blue"],M["navy"],M["blue2"],M["cyan"]][(k+j)%4]
        head_feathers.add(root,root+Vector((0,0,-length))+n*.055,
                          .19*(43/slots),n,mat_use,arch=.04)
head_feathers.commit()

# Distinctive owl ear-like V-crests, in feather fans with true volume.
crest=FeatherMesh("Crown | pointed sweeping ear plumes","05 | Crest")
for side in (-1,1):
    for j in range(10):
        fx=j/9
        root=HC+Vector((side*(.32+.50*fx),-.25+.20*fx,.68+.03*fx))*head_scale
        tip=root+Vector((side*(.23+.32*fx),.02,.29+.40*fx))*head_scale
        crest.add(root,tip,.18+.08*fx,Vector((0,-1,0)),
                  [M["navy"],M["blue"],M["blue2"],M["cyan"]][j%4],arch=.09)
crest.commit()

# Large ivory heart-shaped facial disks, with subtle cheek plumes.
for sign in (-1,1):
    face=uv(("Left" if sign<0 else "Right")+" | white facial ruff",
            (sign*.50,-.672,3.34),(.59*head_scale,.205,.62*head_scale),
            M["white"],"06 | Face")
    cheeks=FeatherMesh("Cheek ruff | "+str(sign),"06 | Face")
    for k in range(10):
        angle=(-.88+k/9*1.76)
        root=(sign*(.48+.35*math.cos(angle)), -.83, 3.14+.31*math.sin(angle))
        tip=(root[0]+sign*.14,root[1]+.07,root[2]-.18)
        cheeks.add(root,tip,.14,Vector((0,-1,0)),M["cream"],arch=.015)
    cheeks.commit()

# Oversized glassy eyes, deep blue rings, complex iris geometry and true
# catchlight spheres; every eye can be manipulated separately in Blender.
eye_r=.35*eye_scale
for sign in (-1,1):
    x=sign*.51; z=3.45
    uv("Eye %s | dark glossy socket"%sign,(x,-.841,z),
       (eye_r*1.26,.16,eye_r*1.26),M["eye_dark"],"07 | Eyes")
    uv("Eye %s | luminous blue iris"%sign,(x,-.982,z),
       (eye_r*1.04,.10,eye_r*1.04),M["iris"],"07 | Eyes")
    uv("Eye %s | inner turquoise corona"%sign,(x,-1.075,z),
       (eye_r*.79,.035,eye_r*.79),M["iris_cyan"],"07 | Eyes")
    uv("Eye %s | pupil"%sign,(x,-1.113,z+.016),
       (eye_r*.62,.046,eye_r*.62),M["eye_dark"],"07 | Eyes")
    uv("Eye %s | main glint"%sign,(x-sign*.095,-1.170,z+.132),
       (.073,.018,.073),M["eye_reflection"],"07 | Eyes",16,12)
    uv("Eye %s | little glint"%sign,(x+sign*.11,-1.167,z-.075),
       (.025,.012,.025),M["eye_reflection"],"07 | Eyes",12,8)
    # Delicate circuitry-like radial dots within the visible iris ring.
    for k in range(10):
        a=math.tau*k/10
        rad=eye_r*.79
        uv("Eye %s | iris jewel %d"%(sign,k),
           (x+rad*math.cos(a),-1.102,z+rad*math.sin(a)),
           (.014,.008,.014),M["eye_reflection"],"07 | Eyes",8,6)

# Symmetrical white brow V at the bridge and thick sculptural eyebrow feathers.
brows=FeatherMesh("Face | V-shaped white eyebrow feathers","06 | Face")
for sign in (-1,1):
    for j in range(7):
        root=(sign*(.06+j*.105),-.83+(.06*j/7),3.98-(j/7)*.02)
        tip=(sign*(.14+j*.123),-.84,3.72-(j/7)*.15)
        brows.add(root,tip,.17,Vector((0,-1,0)),M["white"],arch=.02)
brows.commit()

# Orange tapered beak, full three-dimensional hooked geometry.
cone_between("Beak | pointed upper orange ridge",
             (0,-.86,3.26),(0,-1.075,2.96),.145,.018,
             M["orange"],"08 | Beak",24)
uv("Beak | golden highlight",(0,-1.025,3.18),
   (.075,.035,.092),M["gold"],"08 | Beak",16,10)

# Folded wings with substantial volume, sweeping primaries and blue coverts.
wingfeathers=FeatherMesh("Wings | layered primary and covert feathers","09 | Wings")
for side in (-1,1):
    for j in range(6):
        a=j/5
        uv("Wing %s | thick base layer %d"%(side,j),
           (side*(.79+.10*a+wingspan*.12),.055+.11*a,2.25-.18*a),
           (.27+.05*a,.29,.64-.04*a),M["blue"],"09 | Wings",24,14)
    for row in range(max(7,int(10*feather_detail))):
        t=row/max(1,int(10*feather_detail))
        for k in range(6):
            u=k/5
            root=Vector((side*(.81+u*.21+wingspan*.3),-.24+u*.10,
                        2.62-row*.149+u*.07))
            tip=root+Vector((side*(.13+wingspan*.27),-.025,-(.46+.12*u)))
            wingfeathers.add(root,tip,.25,Vector((side*.25,-1,.05)),
                [M["navy"],M["blue"],M["blue2"],M["cyan"],M["turquoise"]][(k+row)%5],
                arch=.08)
wingfeathers.commit()

# Rear fan tail of staggered tapered blue feathers, visible from 180°.
tail=FeatherMesh("Tail | fan with 3D tapered vanes","10 | Tail")
for j in range(13):
    q=(j-6)/6
    root=Vector((q*.38,.50,.90+(.10-abs(q)*.07)))
    tip=Vector((q*.70,.56,.35-abs(q)*.05))
    tail.add(root,tip,.20,Vector((0,1,0)),
             [M["navy"],M["blue"],M["blue2"],M["cyan"]][j%4],.04)
tail.commit()

# Feet clutch the wooden perch; each toe wraps around the branch rather than
# simply resting on top. Four toes per foot, black hooked nails.
branch_z=.72
cone_between("Natural wood perch",(-2.15,-.89,branch_z),
             (2.15,-.89,branch_z),.11,.11,M["branch"],"11 | Branch",24)
for i in (-1,1):
    uv("Scaly orange foot palm %s"%i,(i*.47,-.73,.87),
       (.26,.21,.14),M["orange"],"12 | Feet",22,14)
    for toe in range(4):
        xx=i*.47+(toe-1.5)*.12
        points=[
            (xx,-.73,.93),
            (xx,-.99,.95),
            (xx,-1.05,.79),
            (xx,-1.02,.65)]
        line("Foot %s toe %d orange curve"%(i,toe),points,.065,
             M["orange"],"12 | Feet")
        cone_between("Foot %s toe %d hooked charcoal talon"%(i,toe),
             (xx,-1.02,.68),(xx,-.99,.57),.059,.002,M["black"],"12 | Feet",12)
    # Opposing rear toe grips around the opposite side of the perch.
    line("Foot %s hind toe"%i,
       [(i*.47,-.73,.85),(i*.51,-.62,.77),(i*.52,-.72,.62)],
       .058,M["orange"],"12 | Feet")

# Signature forehead AI motif: luminous cyan signal tree made of real curves
# and orb geometry, raised slightly from the feather surface.
# Center of forehead at z=4.09 and front -Y.
line("AI crest | main circuit stem",[(0,-.82,3.91),(0,-.862,4.11),(0,-.82,4.25)],
     .024,M["glow"],"13 | AI Emblem")
uv("AI crest | central core",(0,-.895,4.10),(.079,.050,.079),
   M["glow"],"13 | AI Emblem",20,12)
uv("AI crest | antenna node",(0,-.837,4.30),(.066,.043,.066),
   M["glow"],"13 | AI Emblem",20,12)
for sign in (-1,1):
    for j in range(2):
        x=sign*(.20+j*.14)
        line("AI crest | branching signal",
            [(0,-.85,4.095),(x*.49,-.856,4.19+j*.03),(x,-.79,4.20+j*.075)],
            .015,M["glow"],"13 | AI Emblem")
        uv("AI crest | terminal signal",
            (x,-.795,4.20+j*.075),(.033,.03,.033),
            M["glow"],"13 | AI Emblem",12,8)
    for j in range(4):
        x=sign*(.10+j*.11)
        uv("AI crest | stardust", (x,-.78,4.36+j*.035),(.014,.015,.014),
           M["glow"],"13 | AI Emblem",10,7)

# Neutral studio setup. Stage is not part of the mascot collection, so it can
# be hidden or deleted for export to game engines.
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.05))
stage=bpy.context.object;stage.name="Studio sweep | separate from mascot"
stage.data.materials.append(M["bg"])
move_to(stage,"90 | Studio")
world=bpy.data.worlds.new("Neutral studio ambient")
scene.world=world
world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Color"].default_value=(.48,.60,.80,1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value=.60

def area(name,pos,power,size,color):
    data=bpy.data.lights.new(name,"AREA");data.energy=power
    data.shape="DISK";data.size=size;data.color=color
    obj=bpy.data.objects.new(name,data);coll("90 | Studio").objects.link(obj)
    obj.location=pos;obj.rotation_euler=(Vector((0,0,2.2))-obj.location).to_track_quat("-Z","Y").to_euler()
area("Soft key | white",(-5,-7,8),950,7,(.82,.92,1))
area("Cyan rim", (4,5,7),1100,6,(.23,.73,1))
area("Warm amber accent",(5,-3,4),350,4,(1,.78,.49))

camera_data=bpy.data.cameras.new("Owli 360 degree studio camera")
cam=bpy.data.objects.new("Owli 360 degree studio camera",camera_data)
coll("90 | Studio").objects.link(cam)
camera_data.type="ORTHO"
camera_data.ortho_scale=6.0
camera_data.lens=45
scene.camera=cam

def camera_angle(deg):
    theta=math.radians(deg)
    target=Vector((0,0,2.30))
    cam.location=(10.0*math.sin(theta),-10.0*math.cos(theta),3.02)
    cam.rotation_euler=(target-cam.location).to_track_quat("-Z","Y").to_euler()
camera_angle(0)

# Store an editable project plus machine-readable settings before rendering.
project=OUT/"owli_parametric.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(project))
manifest={
 "character":"Owli","variant":"A – Classic Owli",
 "source":"User-provided 360° reference sheet, 2026-11-15",
 "blender_version":bpy.app.version_string,
 "config":cfg,"views_degrees":view_degrees,
 "model_objects":sum(1 for o in bpy.data.objects if o.name!=stage.name and o!=cam
                       and not any(o.name==n for n in ("Soft key | white","Cyan rim","Warm amber accent"))),
 "feather_meshes":[o.name for o in bpy.data.objects if "feathers" in o.name.lower()],
 "output_blend":project.name}
(OUT/"owli_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
print("OWLI_MODEL_READY",manifest["model_objects"],"objects",
      "samples",samples,"resolution_pct",resolution,flush=True)
for degree in view_degrees:
    camera_angle(degree)
    scene.render.filepath=str(OUT/("owli_%03d.png"%degree))
    bpy.ops.render.render(write_still=True)
    print("OWLI_VIEW_RENDERED",degree,flush=True)
print("OWLI_COMPLETE",len(view_degrees),"views and",project,flush=True)
