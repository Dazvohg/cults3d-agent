"""Render fotorrealista de un STL con Blender (se ejecuta DENTRO de Blender, sin interfaz).

blender -b -P tools/render_blender.py -- --stl pieza.stl --out render.png
        [--color "#C8B69A"] [--angle 35] [--size 1600x1200] [--samples 64] [--rot 0,0,0]

Look de "estudio de producto": plástico PLA mate con líneas de capa sutiles, fondo infinito
claro (cyclorama), luz principal suave + relleno + contraluz, sombra de contacto.
"""
import math
import sys

import bpy
from mathutils import Vector


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = {"color": "#C8B69A", "angle": "35", "size": "1600x1200", "samples": "64", "rot": "0,0,0"}
    for i in range(0, len(a), 2):
        o[a[i].lstrip("-")] = a[i + 1]
    return o


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple((int(h[i:i + 2], 16) / 255) ** 2.2 for i in (0, 2, 4)) + (1.0,)


o = args()
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = int(o["samples"])
# Denoise only if this Blender build ships OpenImageDenoise (official builds do; some distro packages don't)
scene.cycles.use_denoising = bool(getattr(bpy.app.build_options, "openimagedenoise", False))
w, h = (int(x) for x in o["size"].split("x"))
scene.render.resolution_x, scene.render.resolution_y = w, h
scene.render.film_transparent = False
for vt in ("AgX", "Filmic", "Standard"):
    try:
        scene.view_settings.view_transform = vt
        break
    except TypeError:
        continue
for lk in ("AgX - Punchy", "AgX - Medium High Contrast", "Medium High Contrast", "None"):
    try:
        scene.view_settings.look = lk
        break
    except TypeError:
        continue

# ---- model
try:
    bpy.ops.wm.stl_import(filepath=o["stl"])
except Exception:
    bpy.ops.import_mesh.stl(filepath=o["stl"])
obj = bpy.context.selected_objects[0]
obj.scale = (0.001, 0.001, 0.001)  # mm -> m
rx, ry, rz = (math.radians(float(v)) for v in o["rot"].split(","))
obj.rotation_euler = (rx, ry, rz)
bpy.context.view_layer.update()
bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
obj.location = (0, 0, 0)
bpy.context.view_layer.update()
zmin = min((obj.matrix_world @ Vector(c)).z for c in obj.bound_box)
obj.location.z -= zmin
bpy.context.view_layer.update()
bpy.ops.object.shade_flat()
dims = obj.dimensions
size = max(dims)
print("DBG dims", tuple(round(x,4) for x in dims), "view", scene.view_settings.view_transform)

# PLA material: slightly rough plastic + fine horizontal layer lines (bump from a wave texture)
mat = bpy.data.materials.new("PLA")
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = hex_rgb(o["color"])
bsdf.inputs["Roughness"].default_value = 0.55
for key in ("Specular IOR Level", "Specular"):
    if key in bsdf.inputs:
        bsdf.inputs[key].default_value = 0.35
        break
tc = nt.nodes.new("ShaderNodeTexCoord")
wave = nt.nodes.new("ShaderNodeTexWave")
wave.wave_type = "BANDS"
wave.bands_direction = "Z"
wave.inputs["Scale"].default_value = 1.0 / 0.0002 / 1000 * 1.0  # ~0.2 mm layers in object space (mm units)
bump = nt.nodes.new("ShaderNodeBump")
bump.inputs["Strength"].default_value = 0.08
nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
nt.links.new(wave.outputs["Color"], bump.inputs["Height"])
nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
obj.data.materials.append(mat)

# ---- cyclorama backdrop (floor curving up into a wall)
bpy.ops.mesh.primitive_plane_add(size=size * 12, location=(0, 0, 0))
floor = bpy.context.active_object
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.subdivide(number_cuts=30)
bpy.ops.object.mode_set(mode="OBJECT")
for v in floor.data.vertices:
    y = v.co.y
    edge = size * 1.2
    if y > edge:
        v.co.z = (y - edge) ** 2 / (size * 3)
bpy.ops.object.shade_smooth()
bg = bpy.data.materials.new("Backdrop")
bg.use_nodes = True
b2 = bg.node_tree.nodes["Principled BSDF"]
b2.inputs["Base Color"].default_value = (0.86, 0.86, 0.85, 1)
b2.inputs["Roughness"].default_value = 0.9
floor.data.materials.append(bg)

# ---- world: soft neutral ambient
world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.9, 0.9, 0.92, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.2

# ---- lights (key, fill, rim) sized to the object
def area(name, loc, energy, s):
    bpy.ops.object.light_add(type="AREA", location=loc)
    lt = bpy.context.active_object
    lt.data.energy = energy
    lt.data.size = s
    lt.name = name
    d = Vector((0, 0, dims.z / 2)) - lt.location
    lt.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return lt

k = size * 2.2
area("key", (-k, -k, k * 1.3), 120 * k ** 2, size * 2.5)
area("fill", (k * 1.2, -k * 0.6, k * 0.6), 35 * k ** 2, size * 3)
area("rim", (0, k * 1.2, k), 80 * k ** 2, size * 1.5)

# ---- camera: 3/4 view from ~30 deg elevation, distance computed from the bounding sphere
bpy.ops.object.camera_add()
cam = bpy.context.active_object
scene.camera = cam
cam.data.lens = 70
cam.data.sensor_fit = "AUTO"
r = 0.5 * math.sqrt(dims.x ** 2 + dims.y ** 2 + dims.z ** 2)
half_h = math.atan(math.tan(cam.data.angle / 2) * min(w, h) / max(w, h))  # vertical half-FOV
dist = r / math.sin(half_h) * 1.18  # whole bounding sphere inside the frame, with a margin
az, el = math.radians(float(o["angle"])), math.radians(30)
target = Vector((0, 0, dims.z * 0.5))
cam.location = target + Vector((dist * math.cos(el) * math.sin(az), -dist * math.cos(el) * math.cos(az), dist * math.sin(el)))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.clip_start = 0.001
cam.data.clip_end = 100

scene.render.filepath = o["out"]
scene.render.image_settings.file_format = "PNG"
bpy.ops.render.render(write_still=True)
