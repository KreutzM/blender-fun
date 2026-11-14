# Winter scene with snowman — headless Blender 4.5 script (v2)
import bpy, math, random, sys, os
from mathutils import Vector

# CLI: blender -b -P scenes/winter_scene.py -- output/winter_scene.png
# Keep the original quality by default; CI can choose a quicker preview.
script_args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(script_args[0] if script_args else "output/winter_scene.png")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
SAMPLES = int(os.environ.get("BLENDER_SAMPLES", "48"))
RES = (1920, 1080)
RES_PERCENT = int(os.environ.get("BLENDER_RESOLUTION_PERCENT", "100"))
if not (1 <= SAMPLES <= 4096 and 1 <= RES_PERCENT <= 100):
    raise ValueError("Invalid samples or resolution percentage")

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

def link(obj):
    scene.collection.objects.link(obj)
    return obj

def mat_rgb(name, rgb, rough=0.5, emit=None, emit_strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    b.inputs["Roughness"].default_value = rough
    if emit is not None:
        b.inputs["Emission Color"].default_value = (*emit, 1.0)
        b.inputs["Emission Strength"].default_value = emit_strength
    return m

def sphere(loc, r, mat, scale=None, seg=32, ring=16):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=seg, ring_count=ring)
    o = bpy.context.active_object
    if scale: o.scale = scale
    o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return o

def cone(loc, r, depth, mat, verts=12):
    bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=0.02, depth=depth, location=loc, vertices=verts)
    o = bpy.context.active_object
    o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return o

def cyl(loc, r, depth, mat, rot=(0,0,0), verts=12):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=rot, vertices=verts)
    o = bpy.context.active_object
    o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return o

def box(loc, dims, mat, rot=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot)
    o = bpy.context.active_object
    o.scale = (dims[0]/2, dims[1]/2, dims[2]/2)
    o.data.materials.append(mat)
    return o

def torus(loc, major, minor, mat, rot=(0,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return o

# ---------- materials ----------
snow      = mat_rgb("Snow",      (0.93, 0.95, 0.99), 0.32)
snow_dark = mat_rgb("SnowGround",(0.85, 0.89, 0.97), 0.5)
coal      = mat_rgb("Coal",      (0.02, 0.02, 0.02), 0.35)
carrot    = mat_rgb("Carrot",    (0.87, 0.28, 0.04), 0.5)
scarf     = mat_rgb("Scarf",     (0.78, 0.05, 0.09), 0.65)
hat_black = mat_rgb("Hat",       (0.03, 0.03, 0.04), 0.5)
wood      = mat_rgb("Wood",      (0.22, 0.12, 0.06), 0.7)
pine      = mat_rgb("Pine",      (0.05, 0.16, 0.10), 0.7)
moon_mat  = mat_rgb("Moon",      (0.95, 0.93, 0.88), 0.6, emit=(1.0, 0.97, 0.85), emit_strength=3.0)

# ---------- ground ----------
bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
g = bpy.context.active_object
g.data.materials.append(snow_dark)
random.seed(7)
for i in range(14):
    x = random.uniform(-14, 14); y = random.uniform(-12, 14)
    if abs(x) < 3.5 and abs(y) < 3.5: continue
    r = random.uniform(0.7, 2.2)
    sphere((x, y, -0.02), r, snow, scale=(1, 1, 0.4))
# settle mound under snowman
sphere((0, 0, 0.0), 1.3, snow, scale=(1, 1, 0.22))

# ---------- snowman (faces -Y toward camera) ----------
HZ, HR = 2.85, 0.44     # head center/radius
MZ, MR = 1.95, 0.62     # mid center/radius

def head_front(x, z, push=0.0):
    dy2 = HR*HR - x*x - (z-HZ)*(z-HZ)
    return -math.sqrt(max(dy2, 0.0)) - push

def mid_front(x, z, push=0.0):
    dy2 = MR*MR - x*x - (z-MZ)*(z-MZ)
    return -math.sqrt(max(dy2, 0.0)) - push

sphere((0, 0, 0.76), 0.85, snow, scale=(1, 1, 1.05))
sphere((0, 0, MZ), MR, snow)
sphere((0, 0, HZ), HR, snow)

# eyes: centers ON the head surface so half protrudes
for ex in (-0.15, 0.15):
    sphere((ex, head_front(ex, 2.95), 2.95), 0.06, coal)
# smile: ends higher than center
for i in range(6):
    a = -0.55 + 1.1*i/5.0
    px = 0.30*math.sin(a)
    pz = 2.68 + 0.10*(a/0.55)**2
    sphere((px, head_front(px, pz) , pz), 0.032, coal)
# carrot nose: base embedded in head
nose = cone((0, -0.62, 2.86), 0.07, 0.42, carrot, verts=10)
nose.rotation_euler = (-math.radians(90), 0, 0)
# buttons: centers on mid surface
for dz in (1.75, 2.00, 2.25):
    sphere((0, mid_front(0, dz), dz), 0.055, coal)

# scarf: wrapped band at neck + knot + hanging tail on mid surface
neck_z = 2.50
torus((0, 0, neck_z), 0.34, 0.08, scarf, rot=(math.radians(8), 0, 0))  # flat ring around neck
knot_y = -0.42
sphere((0.16, knot_y, neck_z - 0.04), 0.085, scarf)
# tail from knot down the front of mid body: one clean strip, straight cut end
z0, z1 = neck_z - 0.10, 1.72
y0 = -math.sqrt(max(MR*MR - 0.16**2 - (z0-MZ)**2, 0.01)) - 0.04
y1 = -math.sqrt(max(MR*MR - 0.16**2 - (z1-MZ)**2, 0.01)) - 0.04
mid_pt = ((y0+y1)/2, (z0+z1)/2)
tilt = math.degrees(math.atan2(-(y1-y0), z0-z1))
tail = box((0.16, mid_pt[0], mid_pt[1]), (0.11, 0.07, math.hypot(y1-y0, z1-z0)+0.08), scarf,
           rot=(math.radians(tilt), 0, 0))

# top hat (head top = 3.29)
cyl((0, 0, 3.30), 0.34, 0.04, hat_black)
cyl((0, 0, 3.50), 0.24, 0.36, hat_black)
cyl((0, 0, 3.38), 0.245, 0.05, scarf)

# stick arms — bases inside mid body
arm_L = cyl((0.55, 0, 2.02), 0.035, 1.0, wood, rot=(0, math.radians(70), 0))
for a in (30, -14):
    cyl((1.12, 0, 2.23), 0.02, 0.26, wood, rot=(0, math.radians(70-a), 0))
arm_R = cyl((-0.53, 0, 1.93), 0.035, 0.95, wood, rot=(0, math.radians(-105), 0))
for a in (22, -16):
    cyl((-1.08, 0, 1.78), 0.02, 0.26, wood, rot=(0, math.radians(-105+a), 0))

# ---------- pine trees: background arc within camera view ----------
def tree(x, y, h=2.4):
    cyl((x, y, 0.25*h - 0.05), 0.05*h/2.4, 0.5*h, wood)
    z = 0.45*h
    for k in range(3):
        cone((x, y, z), (0.42 - 0.11*k)*h/2.4, 0.55*h, pine)
        z += 0.30*h
    z = 0.50*h
    for k in range(3):
        cone((x, y, z), (0.36 - 0.10*k)*h/2.4, 0.22*h, snow)
        z += 0.30*h

random.seed(21)
# view direction from camera (2.2,-8) toward origin ≈ world azimuth 110°; keep a gap right behind the snowman
tree_angles = [72, 83, 94, 126, 137, 148]
for a_deg in tree_angles:
    a = math.radians(a_deg + random.uniform(-4, 4))
    r = random.uniform(7.0, 11.0)
    tree(r*math.cos(a), r*math.sin(a), h=random.uniform(1.8, 2.8))
for a_deg in (80, 88, 132, 140):
    a = math.radians(a_deg + random.uniform(-4, 4))
    r = random.uniform(14.0, 19.0)
    tree(r*math.cos(a), r*math.sin(a), h=random.uniform(2.4, 3.6))
# side filler mounds/rocks where no trees stand
for (mx, my, mr) in ((-7.5, 1.5, 1.4), (7.5, 2.5, 1.2), (-5.5, 12.0, 1.8), (9.5, 9.0, 1.5),
                     (-9.5, 8.5, 1.6), (6.0, -5.0, 1.0), (-6.5, -4.5, 0.9)):
    sphere((mx, my, -0.02), mr, snow, scale=(1, 1, 0.35))

# snowy rocks
for (rx, ry, rr) in ((-4.2, 3.6, 0.6), (4.6, -3.0, 0.5), (3.2, 5.2, 0.4)):
    sphere((rx, ry, rr*0.25), rr, snow_dark, scale=(1, 1.2, 0.5))

# ---------- moon: frame LEFT, upper (screen-right ≈ (0.94,0.34) from cam) ----------
moon_loc = Vector((-9.5, 14.5, 6.5))
sphere(tuple(moon_loc), 1.4, moon_mat)

# ---------- falling snow: mostly lower half ----------
snowflake = mat_rgb("Flake", (1, 1, 1), 0.3, emit=(1, 1, 1), emit_strength=0.5)
random.seed(99)
n = 0
while n < 170:
    x = random.uniform(-11, 11); y = random.uniform(-2.0, 16)
    z = random.uniform(0.35, 5.5)
    if abs(x) < 1.7 and abs(y) < 1.7 and z < 3.7: continue
    if math.hypot(x - 2.2, y + 8.0) < 4.0: continue   # keep flakes away from camera
    sphere((x, y, z), random.uniform(0.012, 0.03), snowflake, seg=8, ring=6)
    n += 1

# ---------- world: night-blue vertical gradient ----------
world = bpy.data.worlds["World"] if "World" in bpy.data.worlds else bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
nt = world.node_tree
bg = nt.nodes["Background"]
tex = nt.nodes.new("ShaderNodeTexCoord")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
ramp = nt.nodes.new("ShaderNodeValToRGB")
map_ = nt.nodes.new("ShaderNodeMapRange")
map_.inputs["From Min"].default_value = -1.0
map_.inputs["From Max"].default_value = 1.0
nt.links.new(tex.outputs["Generated"], sep.inputs["Vector"])
nt.links.new(sep.outputs["Z"], map_.inputs["Value"])
nt.links.new(map_.outputs["Result"], ramp.inputs["Fac"])
cr = ramp.color_ramp
cr.elements[0].position = 0.30; cr.elements[0].color = (0.42, 0.52, 0.70, 1)
e1 = cr.elements.new(0.52); e1.color = (0.10, 0.17, 0.34, 1)
cr.elements[1].position = 0.80; cr.elements[1].color = (0.02, 0.045, 0.12, 1)
nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 1.1

# ---------- lights: sun aligned with the moon ----------
sun = bpy.data.lights.new("Moonlight", 'SUN')
sun.energy = 8.0; sun.angle = math.radians(4)
sun.color = (0.70, 0.78, 1.0)
so = bpy.data.objects.new("Moonlight", sun); link(so)
to_moon = (Vector((0, 0, 2)) - moon_loc).normalized()   # photons travel from moon toward scene
so.rotation_euler = to_moon.to_track_quat('-Z', 'Y').to_euler()

key = bpy.data.lights.new("Key", 'POINT')
key.energy = 500; key.color = (0.75, 0.83, 1.0)
ko = bpy.data.objects.new("Key", key); link(ko)
ko.location = (-5.0, 8.0, 8.0)

fill = bpy.data.lights.new("Fill", 'POINT')
fill.energy = 110; fill.color = (1.0, 0.62, 0.40)
fo = bpy.data.objects.new("Fill", fill); link(fo)
fo.location = (3.5, -4.5, 2.0)

# ---------- camera (TRACK_TO, snowman centered) ----------
target = bpy.data.objects.new("CamTarget", None); link(target)
target.location = (0.0, 0.0, 1.80)
cam_data = bpy.data.cameras.new("Camera"); cam_data.lens = 40
cam = bpy.data.objects.new("Camera", cam_data); link(cam)
cam.location = (2.2, -8.0, 2.0)
con = cam.constraints.new('TRACK_TO')
con.target = target
con.track_axis = 'TRACK_NEGATIVE_Z'
con.up_axis = 'UP_Y'
scene.camera = cam

# ---------- render settings ----------
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = SAMPLES
scene.cycles.max_bounces = 4
scene.view_settings.view_transform = 'Filmic'
try:
    den = bpy.data.denoisers.get("OPENIMAGEDENOISE") if hasattr(bpy.data, "denoisers") else None
    if den is not None:
        scene.cycles.denoiser = den
    scene.cycles.use_denoising = True
except Exception as ex:
    scene.cycles.use_denoising = False
    print("DENONISER-UNAVAILABLE:", ex)
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.resolution_percentage = RES_PERCENT
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = OUT
# Save an editable project alongside the image; no need to rebuild from Python.
blend_out = os.path.splitext(OUT)[0] + ".blend"
bpy.ops.wm.save_as_mainfile(filepath=blend_out)
bpy.ops.render.render(write_still=True)
print("SAVED", OUT, "denoising:", scene.cycles.use_denoising)