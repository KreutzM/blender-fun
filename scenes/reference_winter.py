# Reference winter scene – "Midnight at the Winter Cabin"
# Procedural, deterministic Blender 4.5 / Cycles illustration.
# No external assets, add-ons, downloads, or textures are required.
import bpy
import math
import os
import random
import sys
from mathutils import Vector

SEED = 20261114
rng = random.Random(SEED)
argv = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0] if argv else "output/reference_winter.png")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
SAMPLES = int(os.getenv("BLENDER_SAMPLES", "48"))
SCALE = int(os.getenv("BLENDER_RESOLUTION_PERCENT", "100"))
if not (1 <= SAMPLES <= 512 and 10 <= SCALE <= 100):
    raise ValueError("Bad render quality settings")

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = SAMPLES
scene.cycles.max_bounces = 5
scene.cycles.use_denoising = True
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = SCALE
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.film_transparent = False
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'

# ---------------------------------------------------------------------------
# A small, consistent library of physically based materials.
# ---------------------------------------------------------------------------
def material(name, rgb, rough=0.7, metallic=0, emission=0, grain=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    p = nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*rgb, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metallic
    if emission:
        p.inputs["Emission Color"].default_value = (*rgb, 1)
        p.inputs["Emission Strength"].default_value = emission
    if grain:
        tex = nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = grain
        tex.inputs["Detail"].default_value = 3
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.15
        bump.inputs["Distance"].default_value = 0.055
        links.new(tex.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], p.inputs["Normal"])
    return mat

SNOW = material("Snow | soft pearl", (0.79,0.86,0.96), .82, grain=64)
SNOW_BLUE = material("Snow | shaded powder", (.50,.66,.84), .9, grain=49)
SNOW_WARM = material("Snow | amber reflections", (.94,.78,.57), .79, grain=65)
ICE = material("Frozen pond | pale turquoise", (.17,.42,.52), .20, metallic=.27, grain=180)
PATH = material("Worn snowy footpath", (.40,.54,.63), .96, grain=70)
WOOD = material("Cabin | red cedar", (.27,.105,.067), .82, grain=28)
WOOD_DARK = material("Cabin | deep trim", (.105,.052,.038), .78, grain=36)
WOOD_LIGHT = material("Fence | pine", (.43,.26,.16), .83, grain=40)
ROOF = material("Slate roof", (.115,.19,.235), .72, grain=90)
PINE_A = material("Evergreen | spruce blue", (.040,.165,.17), .85, grain=45)
PINE_B = material("Evergreen | pine dark", (.045,.115,.111), .8, grain=45)
PINE_C = material("Evergreen | fir mid", (.08,.20,.19), .85, grain=45)
BARK = material("Tree trunk bark", (.18,.095,.063), .89, grain=35)
CHARCOAL = material("Charcoal | eyes and buttons", (.014,.021,.028), .62)
HAT = material("Felt black cylinder", (.025,.027,.035), .92, grain=80)
SCARF = material("Woven cranberry red", (.63,.037,.062), .98, grain=92)
SCARF_LIGHT = material("Scarf trim ivory", (.94,.77,.59), .88)
CARROT = material("Carrot orange", (.94,.255,.028), .64, grain=50)
BRASS = material("Brass", (.64,.34,.10), .30, metallic=.68)
WINDOW = material("Warm windows | golden", (1.0,.47,.13), .3, emission=3.5)
WINDOW_BRIGHT = material("Warm windows | inner", (1.0,.75,.34), .35, emission=3.8)
LAMP = material("Lantern glass", (1.0,.70,.28), .3, emission=4.0)
MOON = material("Moon | ivory luminous", (.80,.88,1.0), .95, emission=3.0)
STAR = material("Starlight", (.83,.91,1.0), .99, emission=2.5)
MOUNTAIN = material("Far mountains | blue", (.16,.25,.38), .99)
MOUNTAIN_FAR = material("Far mountains | haze", (.25,.35,.50), .99)
MOUNTAIN_SNOW = material("Mountain snow | distant", (.46,.59,.73), .88)

def smooth(obj):
    if obj.type == 'MESH':
        for p in obj.data.polygons:
            p.use_smooth = True
    return obj

def cube(name, loc, dims, mat, rot=None, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if rot is not None:
        obj.rotation_euler = rot
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new("Small rounded edges", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        obj.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
    return obj

def sphere(name, loc, radius, mat, scale=(1,1,1), seg=20, rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, radius=radius, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    smooth(obj)
    return obj

def cylinder(name, loc, radius, height, mat, vertices=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=height, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return obj

def tube(name, points, r, mat, resolution=3):
    c = bpy.data.curves.new(name, "CURVE")
    c.dimensions = "3D"
    c.bevel_depth = r
    c.bevel_resolution = resolution
    sp = c.splines.new('POLY')
    sp.points.add(len(points)-1)
    for p, xyz in zip(sp.points, points):
        p.co = (*xyz,1)
    ob = bpy.data.objects.new(name,c)
    scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    return ob

def segment(name, a, b, radius, mat, verts=9):
    a, b = Vector(a),Vector(b)
    mid = (a+b)*.5
    d=b-a
    o=cylinder(name, mid, radius, d.length, mat, verts)
    o.rotation_euler = d.to_track_quat('Z','Y').to_euler()
    return o

def mesh(name, coords, faces, mat, smooth_faces=False):
    m=bpy.data.meshes.new(name)
    m.from_pydata(coords, [], faces)
    m.update()
    o=bpy.data.objects.new(name,m)
    scene.collection.objects.link(o)
    o.data.materials.append(mat)
    if smooth_faces:
        smooth(o)
    return o

def area(name, loc, power, color, size, aim):
    d=bpy.data.lights.new(name,'AREA')
    d.energy=power
    d.color=color
    d.shape='DISK'
    d.size=size
    obj=bpy.data.objects.new(name,d)
    scene.collection.objects.link(obj)
    obj.location=loc
    obj.rotation_euler=(Vector(aim)-obj.location).to_track_quat('-Z','Y').to_euler()
    return obj

def point(name,loc,power,color,radius=2):
    d=bpy.data.lights.new(name,'POINT')
    d.energy=power
    d.color=color
    d.shadow_soft_size=radius
    o=bpy.data.objects.new(name,d)
    scene.collection.objects.link(o)
    o.location=loc
    return o

# ---------------------------------------------------------------------------
# Painterly midnight backdrop + mountain silhouettes, entirely geometry.
# ---------------------------------------------------------------------------
scene.world.color=(.10,.14,.21)
world_nodes=scene.world.node_tree
if not scene.world.use_nodes:
    scene.world.use_nodes=True
wbg=scene.world.node_tree.nodes.get("Background")
wbg.inputs["Color"].default_value=(.12,.16,.27,1)
wbg.inputs["Strength"].default_value=.30

sky = material("Sky placeholder", (.08,.12,.23))
sky.use_nodes=True
n=sky.node_tree.nodes
n.clear()
out=n.new("ShaderNodeOutputMaterial")
out.location=(450,80)
em=n.new("ShaderNodeEmission")
em.location=(220,80)
geo=n.new("ShaderNodeNewGeometry")
geo.location=(-640,150)
sep=n.new("ShaderNodeSeparateXYZ")
sep.location=(-400,150)
ramp=n.new("ShaderNodeValToRGB")
ramp.location=(-100,150)
ramp.color_ramp.elements[0].position=.0
ramp.color_ramp.elements[0].color=(.35,.32,.43,1)
ramp.color_ramp.elements[1].position=1.
ramp.color_ramp.elements[1].color=(.009,.025,.082,1)
e=ramp.color_ramp.elements.new(.15)
e.color=(.16,.24,.38,1)
e=ramp.color_ramp.elements.new(.38)
e.color=(.045,.096,.215,1)
mapnode=n.new("ShaderNodeMapRange")
mapnode.inputs["From Min"].default_value=0
mapnode.inputs["From Max"].default_value=60
sky.node_tree.links.new(geo.outputs["Position"],sep.inputs[0])
sky.node_tree.links.new(sep.outputs["Z"],mapnode.inputs["Value"])
sky.node_tree.links.new(mapnode.outputs["Result"],ramp.inputs["Fac"])
sky.node_tree.links.new(ramp.outputs["Color"],em.inputs["Color"])
sky.node_tree.links.new(em.outputs[0],out.inputs["Surface"])
mesh("Hand-painted twilight sky", [(-220,74,-25),(220,74,-25),(220,74,145),(-220,74,145)], [(0,1,2,3)],sky)

def mountain(name, y, peaks, mat, cap_mat, base_z=-2.0):
    verts=[]
    for x,z in peaks:
        verts.extend([(x,y,base_z),(x,y,z)])
    faces=[]
    for i in range(len(peaks)-1):
        a=i*2
        faces.append((a,a+2,a+3,a+1))
    mesh(name,verts,faces,mat)
    # Individual bright snow ridges, tapered to avoid cartoon straight bands.
    for i,(x,z) in enumerate(peaks):
        if z<5.3: continue
        span=2.3 if y<44 else 3.3
        mesh(name+" snowy peak "+str(i),
             [(x-span,y-.055,z-2.1),(x,y-.065,z),
              (x+span*.85,y-.05,z-2.0),(x,y-.11,z-1.15)],
             [(0,1,3),(3,1,2)],cap_mat)

far_peaks=[(-100,4),(-45,7),(-32,11),(-22,6),(-12,13),(-4,8),(7,13),(23,6),(40,12),(62,6),(100,6)]
middle_peaks=[(-100,2),(-37,5),(-26,9),(-19,6),(-12,10),(-5,4),(4,7),(12,10),(25,4),(42,8),(100,3)]
mountain("Distant alpine peaks",55,far_peaks,MOUNTAIN_FAR,MOUNTAIN_SNOW)
mountain("Layer of forest mountains",38,middle_peaks,MOUNTAIN,MOUNTAIN_SNOW)

# Moon and pinprick stars behind the mountain skyline.
sphere("Full winter moon", (-26,58,25),2.05,MOON,seg=48,rings=24)
for j in range(145):
    x=rng.uniform(-72,42)
    z=rng.uniform(13,43)
    if (x+26)**2+(z-25)**2 < 15: continue
    s=rng.uniform(.035,.11)
    sphere("Star %03d"%j,(x,64,z),s,STAR,seg=8,rings=5)
# Distant atmospheric bright moon halo in three thin rings, restrained.
for j,(rad,alpha) in enumerate([(2.45,.25),(2.9,.11),(3.4,.045)]):
    halo=material("Moon halo %d"%j,(.60,.75,1.0),emission=alpha)
    points=[]
    for i in range(97):
        a=math.tau*i/96
        points.append((-26+rad*math.cos(a),58.3,25+rad*math.sin(a)))
    tube("Halo outline %d"%j,points,.022,halo,1)

# ---------------------------------------------------------------------------
# Snow-covered, undulating ground.
# ---------------------------------------------------------------------------
N=90
terrain=[]
for j in range(N+1):
    y=-28+85*j/N
    for i in range(N+1):
        x=-54+110*i/N
        dz=.13*math.sin(x*.36)+.10*math.sin(y*.27)+.045*math.sin(2.1*x+1.7*y)
        terrain.append((x,y,-.15+dz))
terrain_faces=[(j*(N+1)+i,j*(N+1)+i+1,(j+1)*(N+1)+i+1,(j+1)*(N+1)+i)
               for j in range(N) for i in range(N)]
mesh("Rolling snow terrain | subtly sculpted",terrain,terrain_faces,SNOW,smooth_faces=True)

def pine(name, x,y,h,variant=0):
    # A trunk with individually irregular overlapping boughs and powdered caps.
    bark=BARK
    needle=[PINE_A,PINE_B,PINE_C][variant%3]
    segment(name+" | trunk",(x,y,0),(x,y,h*.90),h*.034,bark,8)
    tiers=7 if h>4 else 5
    for level in range(tiers):
        frac=level/(tiers-1)
        z=.33*h+frac*.57*h
        radius=(.42*h)*(1-frac)**1.22
        center_x=x+math.sin(frac*9+variant)*.045
        # 12 zigzagged needle edges produce branch-like silhouettes.
        sides=16
        rr=[radius*rng.uniform(.80,1.15) for _ in range(sides)]
        tip=(center_x,y,z+h*.17)
        vertices=[tip]
        vertices.extend((center_x+rr[k]*math.cos(math.tau*k/sides),
                         y+rr[k]*math.sin(math.tau*k/sides),
                         z+rng.uniform(-.11,.12)) for k in range(sides))
        mesh(name+" | spruce bough %d"%level, vertices,
             [(0,1+k,1+(k+1)%sides) for k in range(sides)], needle)
        # Snow on each top branch: irregular bright islands, not white cones.
        cs=[(center_x,y,z+h*.12)]
        inner=[]
        outer=[]
        for k in range(sides):
            a=math.tau*k/sides
            inner.append((center_x+rr[k]*.34*math.cos(a),
                          y+rr[k]*.34*math.sin(a),z+h*.11))
            outer.append((center_x+rr[k]*.80*math.cos(a),
                          y+rr[k]*.80*math.sin(a),z+.023))
        snowverts=inner+outer
        ff=[]
        for k in range(sides):
            if k%5 in (1,3) and h>3: continue
            j=(k+1)%sides
            ff.append((k,j,sides+j,sides+k))
        mesh(name+" | snow powdered tiers %d"%level,snowverts,ff,SNOW_BLUE if y>12 else SNOW)
    sphere(name+" | icy tip",(x,y,h*.99),h*.11,SNOW,seg=12,rings=8)

# Far forest is layered and subdued.
for i in range(31):
    x=rng.uniform(-36,27)
    y=rng.uniform(20,33)
    pine("Distance fir %02d"%i,x,y,rng.uniform(2.4,5.8),i)
# Foreground framing trees (leave a cinematic opening at center).
trees=[
 (-10,3,6.5),(-11,11,8.3),(-7,15,7.4),(-15,21,9.5),
 (11,7,7.0),(12,14,8.3),(9,20,6.2),(15,23,10.0),
 (-7,8,4.5),(-8,21,6.0),(8,20,4.4),(11,26,6.0),
 (-5,23,4.0),(0,27,5.8),(5,25,5.2)]
for i,(x,y,h) in enumerate(trees):
    pine("Feature pine %02d"%i,x,y,h,i%3)

# ---------------------------------------------------------------------------
# Cozy timber cabin at mid right of the visual.
# ---------------------------------------------------------------------------
CX,CY=4.1,8.1
front=CY-2.33
cube("Cabin main timber structure",(CX,CY,1.62),(5.8,4.6,3.24),WOOD,bevel=.12)
# Period log courses; staggered by slight irregularity.
for i in range(10):
    z=.18+i*.30
    cube("Horizontal cedar log %02d"%i,(CX,front-.07,z),
         (5.95,.20,.16),WOOD_LIGHT if i%5==0 else WOOD,bevel=.055)
for side in (-1,1):
    xx=CX+side*2.88
    for z in (.12,1.38,2.77):
        cube("Cabin corner trim",(xx,front-.16,z),(0.17,.25,.58),WOOD_DARK,bevel=.025)

# Steep gable roof: sloped slate under a fluffy, overhanging snow blanket.
low=3.18
high=5.20
left=CX-3.30
right=CX+3.30
ridge=CX
front_roof=front-.52
back_roof=CY+2.7
def roof_quad(name,p1,p2,p3,p4,mat):
    mesh(name,[p1,p2,p3,p4],[(0,1,2,3)],mat)
for side in (-1,1):
    ex=CX+side*3.37
    rx=CX
    roof_quad("A-frame slate roof %s"%side,
       (ex,front_roof,low),(ex,back_roof,low),
       (rx,back_roof,high),(rx,front_roof,high),ROOF)
    roof_quad("Thick pillowy roof snow %s"%side,
       (ex,front_roof,low+.15),(ex,back_roof,low+.15),
       (rx,back_roof,high+.21),(rx,front_roof,high+.21),SNOW)
    # Snow blanket edge has undulating icicles facing the viewer.
    points=[]
    for k in range(24):
        yy=front_roof+(back_roof-front_roof)*k/23
        points.append((ex,yy,low+.14+.018*math.sin(k*1.7)))
    tube("Roof snow cornice %s"%side,points,.15,SNOW,3)

# Front-facing triangular timber gable, front of wall.
mesh("Gable end cedar",
    [(CX-2.85,front-.045,3.2),(CX+2.85,front-.045,3.2),(CX,front-.045,5.03)],
    [(0,1,2)],WOOD)
for k in range(15):
    xx=CX-2.72+k*.39
    height=3.2+(1-abs(xx-CX)/2.85)*1.7
    cube("Gable vertical inlay %02d"%k,(xx,front-.115,3.38),(0.065,.09,max(.16,height-3.38)),WOOD_DARK,bevel=.012)

# Chimney with cap and accumulated snow.
chimney_x=CX+1.63
cube("Stone chimney",(chimney_x,CY+.75,4.54),(.68,.78,2.8),WOOD_DARK,bevel=.09)
cube("Chimney snowy rim",(chimney_x,CY+.75,5.97),(.92,.94,.15),SNOW,bevel=.035)
for i in range(5):
    v=i*.43
    sphere("Soft rising chimney smoke %d"%i,
        (chimney_x-.13*i,CY+.82+i*.1,6.2+v),.17+.07*i,
        SNOW_BLUE,seg=12,rings=8)

def framed_window(x,z,width=.96,height=1.13):
    y=front-.23
    cube("Glowing cabin window",(x,y,z),(width,.055,height),WINDOW,bevel=.022)
    # warm square panes with crossbars, thick rustic trim
    for edge in (-1,1):
        cube("Window side casement",(x+edge*width*.52,y-.085,z),(.12,.17,height+.18),WOOD_DARK,bevel=.018)
        cube("Window horizontal casement",(x,y-.08,z+edge*height*.52),(width+.18,.16,.12),WOOD_DARK,bevel=.016)
    cube("Window central mullion",(x,y-.105,z),(.08,.18,height),WOOD_LIGHT)
    cube("Window transverse mullion",(x,y-.11,z), (width,.15,.07),WOOD_LIGHT)
    cube("Window small interior flare",(x,y-.004,z),(width*.83,.012,height*.83),WINDOW_BRIGHT)
    point("Window light cast",(x,y-1.4,z),115,(1.0,.53,.21),1.6)
framed_window(CX-1.67,1.91)
framed_window(CX+1.58,1.91)

# Elegant wooden door and entrance.
cube("Front oak door",(CX,front-.28,1.12),(1.06,.12,2.18),WOOD_DARK,bevel=.055)
for i in (-.30,0,.30):
    cube("Door vertical plank",(CX+i,front-.36,1.17),(.24,.035,1.98),WOOD,bevel=.014)
sphere("Brass door knob",(CX+.36,front-.43,1.13),.065,BRASS,seg=12,rings=8)
cube("First porch step",(CX,front-.8,.12),(2.55,1.4,.24),WOOD_LIGHT,bevel=.07)
cube("Second porch step",(CX,front-1.45,.065),(3.1,.75,.13),WOOD_LIGHT,bevel=.07)
# Overhanging porch lanterns with glass and warm light.
for sign in (-1,1):
    x=CX+sign*.79
    cube("Wall lantern housing",(x,front-.42,2.46),(.26,.29,.42),WOOD_DARK,bevel=.035)
    cube("Lantern amber flame",(x,front-.59,2.46),(.15,.085,.22),LAMP)
    point("Porch amber lighting",(x,front-1.15,2.3),180,(1.0,.49,.18),1.6)

# Christmas garland above the door.
tube("Fir garland arch",[(CX+q,front-.43,2.81+.24*math.cos(q*2.8))
                         for q in [-.76+i*.06 for i in range(26)]],.09,PINE_B)
for i in range(9):
    ang=i*math.tau/9
    sphere("Golden tiny garland light",(CX+.68*math.cos(ang),front-.53,2.82+.12*math.sin(ang)),
           .048,LAMP,seg=10,rings=6)

# Icicles along the close eave.
for i in range(24):
    xx=CX-3.1+i*.27
    icicle_h=rng.uniform(.055,.28)
    segment("Front roof icicle %02d"%i,
            (xx,front_roof-.045,3.35),
            (xx,front_roof-.045,3.35-icicle_h),rng.uniform(.012,.024),ICE,6)

# ---------------------------------------------------------------------------
# A winding icy path, footfalls, snowdrifts, lanterns and rustic fencing.
# ---------------------------------------------------------------------------
def pathx(y):
    t=(y+13)/18.5
    return .5+3.1*t+.60*math.sin(t*math.pi*1.65)

ys=[-13+i*.39 for i in range(50)]
pathpoints=[]
for y in ys:
    c=pathx(y)
    w=1.10+(.34 if y<-3 else 0)
    pathpoints.extend([(c-w,y,.015),(c+w,y,.015)])
faces=[(i*2,i*2+1,i*2+3,i*2+2) for i in range(len(ys)-1)]
mesh("Winding silver-blue snow trail",pathpoints,faces,PATH)
for i in range(23):
    y=-11.5+i*.69
    x=pathx(y)+(0.27 if i%2 else -.27)
    ob=sphere("Footprint %02d"%i,(x,y,.055),.23,PATH,scale=(.61,1.45,.14),seg=12,rings=7)
    ob.rotation_euler[2]=rng.uniform(-.22,.22)

for i in range(22):
    y=rng.uniform(-12,15)
    x=rng.uniform(-12,14)
    if abs(x-pathx(y))<2.4 or abs(x-CX)<4.6 and abs(y-CY)<3.5:
        continue
    s=rng.uniform(.35,1.45)
    sphere("Wind-sculpted snowdrift %02d"%i,(x,y,-.07),
           s,SNOW,scale=(rng.uniform(1.15,1.75),rng.uniform(.85,1.25),rng.uniform(.12,.25)))

def rustic_fence(side):
    for i in range(8):
        y=-8.3+i*1.78
        x=pathx(y)+side*2.25
        segment("Rustic fence post", (x,y,.05),(x,y,1.10),.09,WOOD_LIGHT)
        sphere("Snow cap on fence",(x,y,1.12),.145,SNOW,scale=(1,1,.28),seg=12,rings=7)
        if i:
            yp=-8.3+(i-1)*1.78
            xp=pathx(yp)+side*2.25
            segment("Fence rails top",(xp,yp,.82),(x,y,.82),.062,WOOD_LIGHT)
            segment("Fence rails lower",(xp,yp,.46),(x,y,.46),.047,WOOD_DARK)
rustic_fence(-1)
rustic_fence(+1)

for i,(x,y) in enumerate([(-.75,-7.0),(4.2,-.8),(2.0,-10.2)]):
    segment("Lantern trail pole %d"%i,(x,y,.0),(x,y,1.68),.065,WOOD_DARK)
    cube("Lantern frame %d"%i,(x,y,1.72),(.34,.34,.48),WOOD_DARK,bevel=.055)
    cube("Lantern lit pane %d"%i,(x,y-.19,1.70),(.23,.03,.31),LAMP,bevel=.014)
    cube("Lantern cap %d"%i,(x,y,2.0),(.47,.48,.10),SNOW,bevel=.034)
    point("Path pool of warm light %d"%i,(x,y,1.68),85,(1.0,.51,.24),1.5)

# ---------------------------------------------------------------------------
# Snowman: sculpted snow, expressive charcoal face, scarf, branches, hat.
# ---------------------------------------------------------------------------
SX,SY=-3.2,-2.2
B=Vector((SX,SY,.95))
M=Vector((SX,SY,2.22))
H=Vector((SX,SY,3.43))
sphere("Snowman | heavy asymmetrical lower snowball",B,1.02,SNOW,scale=(1.02,.96,.97),seg=48,rings=28)
sphere("Snowman | middle snowball",M,.75,SNOW,scale=(1.04,1.0,.98),seg=48,rings=28)
sphere("Snowman | head",H,.56,SNOW,seg=48,rings=28)
# Face oriented toward the actual camera, slightly rightwards.
F=Vector((.27,-.963,0)).normalized()
R=Vector((.963,.27,0)).normalized()
def on_face(c,r,sx,sz,push=0):
    dep=math.sqrt(max(.001,r*r-sx*sx-sz*sz))
    return c+R*sx+Vector((0,0,sz))+F*(dep+push)
for ex in (-.19,.19):
    sphere("Snowman glossy coal eye",on_face(H,.56,ex,.095,.019),.073,CHARCOAL,seg=20,rings=12)
for i in range(8):
    theta=-.85+i*1.7/7
    x=.29*math.sin(theta)
    z=-.20+.14*(theta/.85)**2
    sphere("Snowman charcoal smile",on_face(H,.56,x,z,.025),.035,CHARCOAL,seg=12,rings=8)
nose=on_face(H,.56,0,-.055,.20)
carrot=cylinder("Carrot base",nose,.125,.04,CARROT,16)
carrot.rotation_euler=F.to_track_quat('Z','Y').to_euler()
ob=bpy.ops.mesh.primitive_cone_add(vertices=18,radius1=.13,radius2=.005,depth=.55,location=nose+F*.11)
obj=bpy.context.object
obj.name="Hand-shaped carrot nose"
obj.rotation_euler=F.to_track_quat('Z','Y').to_euler()
obj.data.materials.append(CARROT)
for dz in (-.25,.02,.28):
    sphere("Snowman coal button",on_face(M,.75,0,dz,.03),.076,CHARCOAL,seg=16,rings=9)
# Scarlet scarf: round collar with hand draped fabric, ribbed fringes.
collar_points=[]
for i in range(49):
    a=math.tau*i/48
    collar_points.append((SX+.57*math.cos(a),SY+.57*math.sin(a),2.94+.03*math.sin(a*2)))
tube("Knitted cranberry collar",collar_points,.15,SCARF,4)
knot=on_face(M,.75,.20,.62,.24)
sphere("Soft scarf knot",knot,.17,SCARF,scale=(1,1,.86),seg=18,rings=12)
tail=[]
for i in range(16):
    t=i/15
    a=knot+Vector((.13*t,-.06*t,-.85*t))
    tail.append(tuple(a))
tube("Long scarf tail flowing toward ground",tail,.11,SCARF,4)
for p in range(5):
    a=Vector(tail[-1])+Vector(((p-2)*.035,0,-.13))
    segment("Scarf woven fringe %d"%p,tail[-1],a,.015,SCARF_LIGHT,6)
# Black felt stove pipe hat, ribbon and brim.
cylinder("Wide velvet hat brim",(SX,SY,4.02),.59,.085,HAT,36)
cylinder("Tall felt stovepipe",(SX,SY,4.33),.37,.59,HAT,32)
cylinder("Cranberry satin hatband",(SX,SY,4.18),.38,.13,SCARF,32)
cylinder("Hat crown top",(SX,SY,4.65),.38,.07,HAT,32)
# Branched stick arms with small snow deposits.
for sign in (-1,1):
    a=Vector((SX+sign*.60,SY,2.31))
    b=Vector((SX+sign*1.34,SY-.12,2.48))
    c=Vector((SX+sign*1.72,SY-.18,2.75))
    segment("Snowman forked arm",a,b,.067,BARK,11)
    segment("Snowman branch extension",b,c,.038,BARK,8)
    segment("Finger branch A",b.lerp(c,.61),c+Vector((sign*.08,0,.35)),.023,BARK,7)
    segment("Finger branch B",b.lerp(c,.52),c+Vector((sign*.04,-.18,-.18)),.024,BARK,7)
    sphere("Fluffy snow on arm",(SX+sign*1.28,SY-.12,2.53),.14,SNOW,scale=(1.6,.7,.4),seg=12,rings=7)
# Snowman base in softer warm light.
sphere("Snow bank beneath snowman",(SX,SY,.07),1.6,SNOW,scale=(1.15,1.0,.12))

# Blue glistening sparkles and a restrained snowfall (away from lens).
for i in range(115):
    x=rng.uniform(-14,18)
    y=rng.uniform(-2,30)
    z=rng.uniform(.5,10.5)
    if (x-SX)**2+(y-SY)**2 < 6.5 and z<4.8:
        continue
    if (x-6)**2+(y+17)**2 < 35:
        continue
    s=rng.uniform(.012,.038)
    sphere("Distant floating ice crystal %03d"%i,(x,y,z),s,STAR if i%5==0 else SNOW,seg=8,rings=5)

# ---------------------------------------------------------------------------
# Cinematic lighting: moonlit blue key + warm windows and snow bounce.
# ---------------------------------------------------------------------------
moon_lamp=bpy.data.lights.new("Cool blue winter moonlight",'SUN')
moon_lamp.energy=1.9
moon_lamp.angle=math.radians(5)
moon_lamp.color=(.49,.68,1.0)
moon_obj=bpy.data.objects.new("Cool blue winter moonlight",moon_lamp)
scene.collection.objects.link(moon_obj)
moon_obj.rotation_euler=Vector((.42,.35,-1.0)).to_track_quat('-Z','Y').to_euler()
area("Soft cold rim on snowman",(-10,6,12),630,(.57,.73,1.0),11,(0,0,1))
area("Quiet amber bounce from cottage",(6,2.0,7.0),450,(1.0,.65,.36),8,(-1,-3,1))
area("Blue foreground fill",(2,-11,9),220,(.65,.78,1.0),10,(0,0,0))

# Camera: deliberate storybook thirds, snowman in left foreground,
# warm cabin on right, path leading the eye and alpine mountains beyond.
camera_data=bpy.data.cameras.new("Cinematic camera | 40mm")
cam=bpy.data.objects.new("Cinematic camera | 40mm",camera_data)
scene.collection.objects.link(cam)
cam.location=(7.7,-19.1,7.1)
target=Vector((.65,3.3,2.8))
cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
camera_data.lens=40
camera_data.clip_end=500
scene.camera=cam

# Minimal post-processing: no aggressive bloom or sharpening.
scene.render.filepath=OUT
blend_file=os.path.splitext(OUT)[0]+".blend"
bpy.ops.wm.save_as_mainfile(filepath=blend_file)
print("REFERENCE_SCENE objects:",len(bpy.data.objects),"samples:",SAMPLES,"resolution_percent:",SCALE,flush=True)
bpy.ops.render.render(write_still=True)
print("REFERENCE_RENDER_SAVED",OUT,flush=True)
