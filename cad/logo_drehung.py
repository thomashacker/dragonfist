"""
VietVoDao-Logo als 3D-Münze, eine volle Drehung als Bildfolge für den Präsentationsmodus.
blender -b -P logo_drehung.py -- <ausgabe-ordner> [bilder] [pixel]
Danach legt `-- <ordner> <bilder> <pixel> blatt` alle Bilder als Raster in app/assets/logo3d.jpg (12 Spalten).
"""
import math
import sys
from pathlib import Path

import bmesh
import bpy

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
AUS = Path(ARGS[0]) if ARGS else Path(__file__).resolve().parent / "ausgabe" / "logo3d"
N = int(ARGS[1]) if len(ARGS) > 1 else 96
PX = int(ARGS[2]) if len(ARGS) > 2 else 360
ASSETS = Path(__file__).resolve().parent.parent / "app" / "assets"
BILD, BLATT, SPALTEN = ASSETS / "vietvodao.png", ASSETS / "logo3d.jpg", 12
R, DICKE = 1.0, 0.14


def leeren():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def material_flaeche():
    m = bpy.data.materials.new("Logo")
    m.use_nodes = True
    n, l = m.node_tree.nodes, m.node_tree.links
    bsdf = next(x for x in n if x.type == "BSDF_PRINCIPLED")
    tex = n.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(BILD))
    gold = (1.0, 0.72, 0.25, 1)
    mix = n.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = gold
    l.new(tex.outputs["Alpha"], mix.inputs["Factor"])
    l.new(tex.outputs["Color"], mix.inputs["B"])
    l.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    bump = n.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    bump.inputs["Distance"].default_value = 0.02
    l.new(tex.outputs["Color"], bump.inputs["Height"])
    l.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.35
    bsdf.inputs["Metallic"].default_value = 0.15
    for name, v in (("Coat Weight", 0.6), ("Coat Roughness", 0.05)):
        if name in bsdf.inputs:
            bsdf.inputs[name].default_value = v
    return m


def material_rand():
    m = bpy.data.materials.new("Rand")
    m.use_nodes = True
    bsdf = next(x for x in m.node_tree.nodes if x.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (1.0, 0.66, 0.2, 1)
    bsdf.inputs["Metallic"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = 0.18
    return m


def muenze():
    me = bpy.data.meshes.new("Muenze")
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=128, radius1=R, radius2=R, depth=DICKE)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=__import__("mathutils").Matrix.Rotation(math.pi / 2, 3, "X"))
    uv = bm.loops.layers.uv.new()
    for f in bm.faces:
        ny = f.normal.y
        if abs(ny) > 0.9:
            f.material_index = 0
            for lp in f.loops:
                x, z = lp.vert.co.x, lp.vert.co.z
                lp[uv].uv = ((x if ny < 0 else -x) / (2 * R) + 0.5, z / (2 * R) + 0.5)
        else:
            f.material_index = 1
            f.smooth = True
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("Muenze", me)
    bpy.context.collection.objects.link(ob)
    me.materials.append(material_flaeche())
    me.materials.append(material_rand())
    bev = ob.modifiers.new("Fase", "BEVEL")
    bev.width, bev.segments, bev.limit_method = 0.03, 4, "ANGLE"
    return ob


def licht(name, typ, ort, energie, farbe=(1, 1, 1), groesse=1.0):
    li = bpy.data.lights.new(name, typ)
    li.energy, li.color = energie, farbe
    if typ == "AREA":
        li.size = groesse
    ob = bpy.data.objects.new(name, li)
    ob.location = ort
    bpy.context.collection.objects.link(ob)
    ziel = ob.constraints.new("TRACK_TO")
    ziel.target = bpy.data.objects["Muenze"]
    return ob


def szene():
    sc = bpy.context.scene
    for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            sc.render.engine = e
            break
        except TypeError:
            pass
    sc.render.resolution_x = sc.render.resolution_y = PX
    sc.render.image_settings.file_format = "PNG"
    sc.render.film_transparent = False
    w = bpy.data.worlds.new("Welt")
    w.use_nodes = True
    next(x for x in w.node_tree.nodes if x.type == "BACKGROUND").inputs["Color"].default_value = (0, 0, 0, 1)
    sc.world = w
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Punchy"
    except TypeError:
        pass
    cam = bpy.data.objects.new("Kamera", bpy.data.cameras.new("Kamera"))
    cam.data.lens = 108
    cam.location = (0, -7.2, 0.35)
    cam.rotation_euler = (math.radians(87.2), 0, 0)
    bpy.context.collection.objects.link(cam)
    sc.camera = cam
    licht("Haupt", "AREA", (-2.5, -4, 3), 600, groesse=3)
    licht("Fuell", "AREA", (3, -4, -1), 150, (0.7, 0.8, 1), 4)
    licht("Kante_rot", "SPOT", (3.5, 2.5, 1.5), 1800, (1, 0.35, 0.05))
    licht("Kante_blau", "SPOT", (-3.5, 2.5, -1), 1800, (0.1, 0.45, 1))
    glow(sc)
    return sc


def glow(sc):
    """Bloom über den Compositor, falls die Blender-Version ihn so anbietet."""
    try:
        if hasattr(sc, "compositing_node_group"):
            g = bpy.data.node_groups.new("Glow", "CompositorNodeTree")
            n, l = g.nodes, g.links
            ein, aus = n.new("CompositorNodeRLayers"), n.new("NodeGroupOutput")
            g.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
            gl = n.new("CompositorNodeGlare")
            for k, v in (("glare_type", "BLOOM"), ("quality", "HIGH")):
                hasattr(gl, k) and setattr(gl, k, v)
            for k, v in (("Threshold", 0.8), ("Strength", 0.5), ("Size", 0.6)):
                k in gl.inputs and setattr(gl.inputs[k], "default_value", v)
            l.new(ein.outputs["Image"], gl.inputs["Image"])
            l.new(gl.outputs["Image"], aus.inputs[0])
            sc.compositing_node_group = g
            sc.render.use_compositing = True
    except Exception as e:
        print("kein Bloom:", e)


def blatt():
    import numpy as np
    zeilen = math.ceil(N / SPALTEN)
    gross = np.zeros((zeilen * PX, SPALTEN * PX, 4), np.float32)
    for i in range(N):
        im = bpy.data.images.load(str(AUS / f"{i:03d}.png"))
        px = np.empty(PX * PX * 4, np.float32)
        im.pixels.foreach_get(px)
        z, sp = divmod(i, SPALTEN)
        gross[(zeilen - 1 - z) * PX:(zeilen - z) * PX, sp * PX:(sp + 1) * PX] = px.reshape(PX, PX, 4)
        bpy.data.images.remove(im)
    out = bpy.data.images.new("Blatt", SPALTEN * PX, zeilen * PX)
    out.pixels.foreach_set(gross.ravel())
    out.filepath_raw, out.file_format = str(BLATT), "JPEG"
    bpy.context.scene.render.image_settings.quality = 88
    out.save()


def main():
    if "blatt" in ARGS:
        return blatt()
    leeren()
    ob = muenze()
    sc = szene()
    AUS.mkdir(parents=True, exist_ok=True)
    for i in range(N):
        ob.rotation_euler = (0, 0, 2 * math.pi * i / N)
        sc.render.filepath = str(AUS / f"{i:03d}.png")
        bpy.ops.render.render(write_still=True)


main()
