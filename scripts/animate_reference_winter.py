"""A cinematic, continuous 15.5-second tour of the procedural winter scene.

The path uses time-indexed cubic Hermite splines (continuous velocity), and
the camera always looks at a smoothly interpolated focal point. It is not a
panorama/flat-image animation: every frame is freshly ray-traced in Blender.
"""
import math
import os
import runpy
from pathlib import Path

import bpy
from mathutils import Vector

os.environ["BLENDER_SKIP_RENDER"] = "1"
runpy.run_path(str(Path(__file__).resolve().parents[1] / "scenes" / "reference_winter.py"),
               run_name="__main__")

scene = bpy.context.scene
cam = scene.camera
assert cam is not None
# Asset coordinates taken directly from reference_winter.py:
# snowman (-3.2, -2.2), cottage (4.1, 8.1), porch facing y=5.77.
# time, camera position, point of interest, 35-mm-equivalent aesthetic lens.
STOPS = [
    (0.0,  (8.0, -20.0, 7.4), (0.5, 3.0, 2.8), 35.0),  # Whole snowy storybook world
    (2.5,  (1.7, -11.5, 5.6), (-2.7, -2.2, 2.8), 35.0), # Snowman and delicate snow
    (5.0,  (-4.7, -6.9, 3.85), (-3.2, -2.2, 3.35), 43.0), # Face, carrot, hat, scarf
    (7.4,  (-.2, -7.3, 3.6), (-2.6, -.8, 2.35), 33.0), # Branches and snowy trail
    (9.6,  (2.2, -3.4, 3.9), (4.1, 5.7, 2.5), 34.0), # Footprints, porch and windows
    (12.3, (7.0, .2, 5.8), (4.1, 6.1, 3.5), 36.0), # Roof snow, lanterns, chimney
    (15.5, (9.5, -15.0, 8.2), (1.1, 5.1, 3.5), 35.0), # Pull back through the winter forest
]

SOURCE_FPS = int(os.getenv("FLYTHROUGH_SOURCE_FPS", "8"))
SECONDS = STOPS[-1][0]
TOTAL = int(round(SECONDS * SOURCE_FPS)) + 1
if not (4 <= SOURCE_FPS <= 30 and 40 <= TOTAL <= 900):
    raise ValueError("Flythrough frame budget is invalid")

def hermite(t, stops, property_index):
    """Smooth positions, look-at target and focal length with eased endpoints."""
    segment = 0
    while segment + 2 < len(stops) and t > stops[segment + 1][0]:
        segment += 1
    left, right = stops[segment], stops[segment + 1]
    dt = right[0] - left[0]
    u = max(0.0, min(1.0, (t - left[0]) / dt))
    u2, u3 = u * u, u * u * u
    p = Vector(left[property_index]) if property_index != 3 else Vector((left[3],0,0))
    q = Vector(right[property_index]) if property_index != 3 else Vector((right[3],0,0))
    if segment == 0:
        v0 = Vector((0,) * len(p))
    else:
        prev = stops[segment - 1]
        pre = Vector(prev[property_index]) if property_index != 3 else Vector((prev[3],0,0))
        v0 = (q - pre) / (right[0] - prev[0])
    if segment + 2 == len(stops):
        v1 = Vector((0,) * len(p))
    else:
        nxt = stops[segment + 2]
        np = Vector(nxt[property_index]) if property_index != 3 else Vector((nxt[3],0,0))
        v1 = (np - p) / (nxt[0] - left[0])
    return (2*u3-3*u2+1)*p + (u3-2*u2+u)*dt*v0 + (-2*u3+3*u2)*q + (u3-u2)*dt*v1

for i in range(TOTAL):
    frame=i+1
    t=SECONDS*i/(TOTAL-1)
    location=hermite(t,STOPS,1)
    target=hermite(t,STOPS,2)
    focal=hermite(t,STOPS,3)[0]
    cam.location=location
    cam.rotation_euler=(target-location).to_track_quat("-Z","Y").to_euler()
    cam.data.lens=focal
    cam.keyframe_insert(data_path="location",frame=frame)
    cam.keyframe_insert(data_path="rotation_euler",frame=frame)
    cam.data.keyframe_insert(data_path="lens",frame=frame)

scene.frame_start=1
scene.frame_end=TOTAL
scene.render.fps=SOURCE_FPS
scene.frame_set(1)
# Avoid relying on texture file paths or an external render cache.
scene.render.image_settings.file_format="PNG"
scene.render.image_settings.color_mode="RGB"
scene.render.filepath=os.path.abspath("output/frames/frame_")
scene.render.use_file_extension=True

project=os.path.abspath("output/reference_flythrough.blend")
bpy.ops.wm.save_as_mainfile(filepath=project)
print("CAMERA_TOUR_READY", "frames",TOTAL,"fps",SOURCE_FPS,
      "seconds",SECONDS,"project",project,flush=True)

# First render a six-panel contact sheet for quick visual scrutiny.
# Storyboard is low-cost; the full animation is a separate render pass.
full_samples=scene.cycles.samples
full_scale=scene.render.resolution_percentage
board_dir=Path("output/storyboard")
board_dir.mkdir(parents=True, exist_ok=True)
for j,t in enumerate((0,2.7,5.1,8.5,11.8,15.5)):
    frame=1+round(t*SOURCE_FPS)
    scene.frame_set(frame)
    scene.cycles.samples=4
    scene.render.resolution_percentage=30
    scene.render.filepath=str(board_dir / f"shot_{j+1:02d}.png")
    bpy.ops.render.render(write_still=True)
    print("STORYBOARD_RENDERED",j+1,"frame",frame,flush=True)
scene.cycles.samples=full_samples
scene.render.resolution_percentage=full_scale
scene.render.filepath=os.path.abspath("output/frames/frame_")
scene.frame_set(1)
bpy.ops.render.render(animation=True)
print("CAMERA_TOUR_RENDER_COMPLETE",TOTAL,flush=True)
