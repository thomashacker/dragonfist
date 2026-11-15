"""
In Blender ausführen (Text-Editor -> Öffnen -> Run Script), nachdem `python stufen.py` gelaufen ist.
Ersetzt jede Stufe aus ausgabe/stufen/ durch eine frische Collection gleichen Namens,
beschriftet die Ansichten und entfernt Stufen, die es nicht mehr gibt.
"""
import os
import re

import bpy
from mathutils import Vector

ORDNER = os.path.join(os.path.dirname(bpy.data.filepath) or os.getcwd(),
                      "ausgabe", "stufen")

TITEL = {
    "1_Rahmen": "Kiste komplett (Stufen 1-7)",
    "8_Gitter_ohne_Pfosten": "Gitter ohne Pfosten",
    "9_Kaefig_mit_Sensoren_und_Kabeln": "Käfig mit Sensoren, Schrauben, Kabeln",
    "10_Druckteile_flach": "Druckteile, so wie gedruckt",
    "11_Elektronik_Nest": "Elektronik-Nest: Pico + Wago",
}


def _name(name):
    # glTF-Import liest die UTF-8-Namen als Latin-1 („EmpfÃ¤nger“) – zurückdrehen
    try:
        return name.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return name


def _collection_entfernen(coll):
    for o in list(coll.all_objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(coll)


def _titel(coll, text):
    meshes = [o for o in coll.objects if o.type == 'MESH']
    if not meshes:
        return
    ecken = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    lo = Vector((min(v.x for v in ecken), min(v.y for v in ecken), min(v.z for v in ecken)))
    hi = Vector((max(v.x for v in ecken), max(v.y for v in ecken), max(v.z for v in ecken)))
    kurve = bpy.data.curves.new(f"Titel {coll.name}", 'FONT')
    kurve.body = text
    kurve.size = 0.03
    kurve.align_x = 'CENTER'
    obj = bpy.data.objects.new(f"Titel {coll.name}", kurve)
    obj.location = ((lo.x + hi.x) / 2, lo.y, hi.z + 0.04)
    obj.rotation_euler = (1.5708, 0, 0)          # liest sich von vorne (Sicht des Kindes)
    obj.color = (1, 1, 1, 1)
    coll.objects.link(obj)


def stufe_laden(name):
    sc = bpy.context.scene
    alt = bpy.data.collections.get(name)
    sichtbar = True
    if alt:
        sichtbar = not alt.hide_viewport
        _collection_entfernen(alt)
    coll = bpy.data.collections.new(name)
    sc.collection.children.link(coll)
    coll.hide_viewport = not sichtbar
    vorher = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(ORDNER, name + ".glb"))
    for o in [o for o in bpy.data.objects if o not in vorher]:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)
        o.name = _name(o.name)
        o.select_set(False)
        if o.type == 'MESH' and o.active_material and o.active_material.node_tree:
            bsdf = next((n for n in o.active_material.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if bsdf:
                o.color = bsdf.inputs["Base Color"].default_value[:]
                if "IR-Strahl" in o.name:
                    bsdf.inputs["Emission Color"].default_value = (1, 0.1, 0.1, 1)
                    bsdf.inputs["Emission Strength"].default_value = 3.0
    if name in TITEL:
        _titel(coll, TITEL[name])
    return coll


def alle_laden():
    namen = sorted((d[:-4] for d in os.listdir(ORDNER) if d.endswith(".glb")),
                   key=lambda n: int(n.split("_")[0]))
    # Stufen, die es nicht mehr gibt (z. B. umbenannt), wegräumen
    for coll in list(bpy.context.scene.collection.children):
        if re.match(r"^\d+_", coll.name) and coll.name not in namen:
            _collection_entfernen(coll)
    for name in namen:
        stufe_laden(name)
    for daten in (bpy.data.meshes, bpy.data.materials, bpy.data.curves):
        for d in list(daten):
            if d.users == 0:
                daten.remove(d)


if __name__ == "__main__":
    alle_laden()
