# -*- coding: utf-8 -*-
"""001 云纹战袍套装：璃月风层叠战袍（立领长袍 + 腰封 + 肩甲 + 开衩裙摆）
Neutral mannequin (~1.7 m, same proportions as blender-portfolio 002) +
layered costume: inner robe -> main robe -> overskirt -> pauldrons/accessories.
Flat shading, Eevee beauty + projected-edge wireframe.
Run: blender --background --python build_001.py
"""
import os
import sys
import math
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))
from common import (clear_scene, solid_material, make_world_gradient,
                    add_ground, studio_lights, make_camera, flat_shade,
                    poly_count, total_poly_count, setup_render, render,
                    export_wireframe_segments)

BLEND_OUT = os.path.join(HERE, "001-cloud-robe.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "001-cloud-robe.png")
WIRE_JSON = "/tmp/cloud_robe_wire.json"


def mesh_from_data(name, verts, faces, material=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    if material is not None:
        mesh.materials.append(material)
    flat_shade(obj)
    return obj


def make_tube(name, origin, direction, distances, radii, sides, material):
    """Closed circular tube along `direction`; one ring per (distance, radius).
    Cap winding copied from blender-portfolio 002 (QA-verified outward)."""
    d = Vector(direction).normalized()
    ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    u = d.cross(ref).normalized()
    v = d.cross(u).normalized()
    o = Vector(origin)
    verts, faces = [], []
    for dist, r in zip(distances, radii):
        c = o + d * dist
        for i in range(sides):
            a = 2.0 * math.pi * i / sides
            p = c + (u * math.cos(a) + v * math.sin(a)) * r
            verts.append(tuple(p))
    n_rings = len(distances)
    for k in range(n_rings - 1):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((k * sides + i, k * sides + j,
                          (k + 1) * sides + j, (k + 1) * sides + i))
    top_c = len(verts)
    verts.append(tuple(o + d * distances[0]))
    bot_c = len(verts)
    verts.append(tuple(o + d * distances[-1]))
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((top_c, j, i))
        faces.append((bot_c, (n_rings - 1) * sides + i,
                      (n_rings - 1) * sides + j))
    return mesh_from_data(name, verts, faces, material)


def make_box_tube(name, rings, material):
    """Rectangular tube from (z, half_x, half_y) rings. Winding copied from
    blender-portfolio 002 (QA 008 verified outward after flip)."""
    verts, faces = [], []
    for z, hx, hy in rings:
        verts += [(hx, -hy, z), (hx, hy, z), (-hx, hy, z), (-hx, -hy, z)]
    for k in range(len(rings) - 1):
        for i in range(4):
            j = (i + 1) % 4
            faces.append((k * 4 + i, (k + 1) * 4 + i, (k + 1) * 4 + j,
                          k * 4 + j))
    n = len(rings)
    faces.append(((n - 1) * 4, (n - 1) * 4 + 3, (n - 1) * 4 + 2,
                  (n - 1) * 4 + 1))
    faces.append((0, 1, 2, 3))
    return mesh_from_data(name, verts, faces, material)


def make_elliptical_tube(name, rings, sides, material, arc=None, caps=True):
    """Elliptical tube along Z. rings: list of (z, rx, ry).
    arc: (start_deg, end_deg) for a partial panel, None for a full 360 tube.
    Angle 0 = +X, 90 = +Y (back), 270 = -Y (front). Garment shells default
    to caps=False (a robe is an open shell, not a closed solid)."""
    if arc is None:
        angles = [2.0 * math.pi * i / sides for i in range(sides)]
        closed = True
    else:
        a0 = math.radians(arc[0])
        a1 = math.radians(arc[1])
        angles = [a0 + (a1 - a0) * i / (sides - 1) for i in range(sides)]
        closed = False
    n = len(angles)
    verts, faces = [], []
    for z, rx, ry in rings:
        for a in angles:
            verts.append((rx * math.cos(a), ry * math.sin(a), z))
    nr = len(rings)
    for k in range(nr - 1):
        for i in range(n - 1):
            j = i + 1
            faces.append((k * n + i, k * n + j, (k + 1) * n + j,
                          (k + 1) * n + i))
        if closed:
            i = n - 1
            j = 0
            faces.append((k * n + i, k * n + j, (k + 1) * n + j,
                          (k + 1) * n + i))
    if caps and closed:
        top_c = len(verts)
        verts.append((0, 0, rings[0][0]))
        bot_c = len(verts)
        verts.append((0, 0, rings[-1][0]))
        for i in range(n):
            j = (i + 1) % n
            faces.append((top_c, j, i))
            faces.append((bot_c, (nr - 1) * n + i, (nr - 1) * n + j))
    return mesh_from_data(name, verts, faces, material)


def add_sphere(name, location, radius, segments, rings, scale, material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings,
                                         radius=radius, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)
    flat_shade(obj)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def add_box(name, location, scale, material):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    flat_shade(obj)
    return obj


def add_cylinder(name, location, radius, depth, vertices, material,
                 rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius,
                                        depth=depth, location=location,
                                        rotation=rotation)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(material)
    flat_shade(obj)
    return obj


def fix_normals(obj):
    """Flip any face whose normal points toward the mesh centroid.
    Guards against the inverted-face class of bugs (blender-portfolio
    016/021). Returns the number of flipped faces."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    centroid = Vector((0, 0, 0))
    for v in bm.verts:
        centroid += v.co
    centroid /= max(1, len(bm.verts))
    flipped = 0
    for f in bm.faces:
        if f.normal.dot(f.calc_center_median() - centroid) < 0:
            f.normal_flip()
            flipped += 1
    bm.to_mesh(obj.data)
    bm.free()
    return flipped


def main():
    clear_scene()
    world = make_world_gradient()
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.75
    add_ground()
    studio_lights(target=(0, 0, 0.9))
    # v1 render was overexposed (vermilion read as salmon pink): halve the
    # studio light energies so the palette reads as specified.
    for obj in bpy.context.scene.objects:
        if obj.type == 'LIGHT':
            obj.data.energy *= 0.45

    # --- palette: 3 main colors + 1 gold accent (see design.md) ---
    teal = solid_material("Robe_Teal", (0.16, 0.42, 0.40), roughness=0.8)
    ink = solid_material("Inner_Ink", (0.10, 0.14, 0.26), roughness=0.85)
    red = solid_material("Sash_Red", (0.62, 0.16, 0.12), roughness=0.8)
    gold = solid_material("Trim_Gold", (0.78, 0.58, 0.20),
                          metallic=0.6, roughness=0.35)
    skin = solid_material("Skin", (0.85, 0.62, 0.48), roughness=0.7)
    hair = solid_material("Hair_Dark", (0.16, 0.10, 0.06), roughness=0.85)
    boot = solid_material("Boot_Brown", (0.25, 0.16, 0.10), roughness=0.9)

    mannequin = []
    costume = []

    # ================= mannequin (neutral base, ~1.7 m, 002 proportions) ==
    mannequin.append(add_sphere("Mannequin_Head", (0, 0, 1.50), 0.22, 8, 6,
                                (1.0, 0.9, 1.05), skin))
    mannequin.append(add_sphere("Mannequin_Hair", (0, 0, 1.56), 0.235, 8, 5,
                                (1.0, 0.92, 0.85), hair))
    mannequin.append(make_tube("Mannequin_Neck", (0, 0, 1.28), (0, 0, 1),
                               [0.0, 0.10], [0.09, 0.085], 6, skin))
    mannequin.append(make_elliptical_tube(
        "Mannequin_Torso",
        [(1.28, 0.270, 0.140), (0.95, 0.240, 0.130),
         (0.62, 0.210, 0.120)],
        8, skin, caps=True))
    for sx in (-1, 1):
        shoulder = Vector((sx * 0.33, 0, 1.22))
        direction = Vector((sx * 0.14, 0, -1))
        mannequin.append(make_tube("Mannequin_Arm", shoulder, direction,
                                   [0.0, 0.13, 0.26, 0.39, 0.52],
                                   [0.085, 0.082, 0.080, 0.075, 0.070],
                                   6, skin))
        wrist = shoulder + direction.normalized() * 0.55
        mannequin.append(add_sphere("Mannequin_Hand", tuple(wrist), 0.085,
                                    6, 4, (1.0, 0.9, 0.8), skin))
        mannequin.append(make_tube("Mannequin_Leg", (sx * 0.13, 0, 0.62),
                                   (0, 0, -1),
                                   [0.0, 0.13, 0.26, 0.39, 0.52],
                                   [0.105, 0.10, 0.095, 0.088, 0.082],
                                   6, skin))
        # No Mannequin_Foot: the costume boots provide the feet; a second
        # box at the same place z-fights with BootFoot (seen in v1 render).

    # ================= costume: inner layer ===============================
    # Inner robe: full elliptical shell, shoulders to below knee.
    # Mannequin torso is an elliptical tube (v2): a box torso's flat front
    # face poked through the elliptical robe at |x| > 0.17 (v1 render).
    costume.append(make_elliptical_tube(
        "InnerRobe",
        [(1.30, 0.300, 0.170), (1.10, 0.290, 0.165), (0.85, 0.280, 0.160),
         (0.60, 0.290, 0.170), (0.35, 0.310, 0.185)],
        8, ink, caps=False))

    # ================= costume: middle layer ==============================
    # Main robe: +0.02 rx / +0.015 ry outside the inner robe.
    costume.append(make_elliptical_tube(
        "MainRobe",
        [(1.30, 0.320, 0.185), (1.10, 0.310, 0.180), (0.85, 0.300, 0.175),
         (0.60, 0.310, 0.185), (0.35, 0.330, 0.200)],
        8, teal, caps=False))
    # Standing collar (teal) + gold band at its base (rim at top would be
    # buried in the jaw, so the trim sits at the collar base instead).
    costume.append(make_elliptical_tube(
        "Collar", [(1.40, 0.142, 0.125), (1.34, 0.148, 0.130),
                   (1.28, 0.155, 0.135)],
        8, teal, caps=False))
    costume.append(make_elliptical_tube(
        "CollarRim", [(1.31, 0.158, 0.138), (1.28, 0.158, 0.138)],
        8, gold, caps=False))
    # Waist sash (red) + gold buckle at the front.
    costume.append(make_elliptical_tube(
        "Sash", [(0.98, 0.318, 0.192), (0.88, 0.312, 0.188)],
        8, red, caps=False))
    costume.append(add_box("Buckle", (0, -0.20, 0.93), (0.09, 0.03, 0.06),
                           gold))
    # Wide bell sleeves (flared) + gold cuff bands.
    for sx in (-1, 1):
        shoulder = Vector((sx * 0.34, 0, 1.24))
        direction = Vector((sx * 0.25, 0, -1))
        costume.append(make_tube("Sleeve", shoulder, direction,
                                 [0.0, 0.15, 0.30, 0.45],
                                 [0.130, 0.145, 0.165, 0.185], 8, teal))
        cuff_origin = shoulder + direction.normalized() * 0.38
        costume.append(make_tube("Cuff", cuff_origin, direction,
                                 [0.0, 0.07], [0.190, 0.192], 8, gold))
    # Main-robe hem band (gold): hidden behind the overskirt front/back,
    # visible through the side slits.
    costume.append(make_elliptical_tube(
        "HemBand", [(0.36, 0.336, 0.206), (0.33, 0.336, 0.206)],
        8, gold, caps=False))

    # ================= costume: outer layer ===============================
    # Shoulder pauldrons (flattened gold half-spheres).
    for sx in (-1, 1):
        costume.append(add_sphere("Pauldron", (sx * 0.36, 0, 1.28), 0.15,
                                  8, 5, (1.15, 1.0, 0.55), gold))
    # Overskirt front/back panels (red), side slits ~70 deg each side.
    # Front arc centred on -Y (270 deg), back arc centred on +Y (90 deg).
    costume.append(make_elliptical_tube(
        "Overskirt_Front",
        [(0.95, 0.325, 0.195), (0.70, 0.335, 0.205),
         (0.45, 0.345, 0.215), (0.30, 0.350, 0.220)],
        8, red, arc=(215, 325), caps=False))
    costume.append(make_elliptical_tube(
        "Overskirt_Back",
        [(0.95, 0.325, 0.195), (0.70, 0.335, 0.205),
         (0.45, 0.345, 0.215), (0.30, 0.350, 0.220)],
        8, red, arc=(35, 145), caps=False))
    # Gold hem bands on the overskirt panels (same arcs, +0.004 radius).
    costume.append(make_elliptical_tube(
        "OverskirtHem_Front",
        [(0.32, 0.354, 0.224), (0.28, 0.356, 0.226)],
        8, gold, arc=(215, 325), caps=False))
    costume.append(make_elliptical_tube(
        "OverskirtHem_Back",
        [(0.32, 0.354, 0.224), (0.28, 0.356, 0.226)],
        8, gold, arc=(35, 145), caps=False))

    # ================= costume: boots =====================================
    for sx in (-1, 1):
        costume.append(make_tube("Boot", (sx * 0.13, 0, 0.55), (0, 0, -1),
                                 [0.0, 0.15, 0.30, 0.45],
                                 [0.120, 0.115, 0.110, 0.115], 8, boot))
        costume.append(add_box("BootFoot", (sx * 0.13, -0.04, 0.055),
                               (0.17, 0.30, 0.11), boot))

    # ================= costume: accessories ===============================
    # Gold pendant on a cord, hanging from the sash at the front.
    costume.append(make_tube("PendantCord", (0.05, -0.20, 0.88), (0, 0, -1),
                             [0.0, 0.16], [0.008, 0.008], 4, gold))
    costume.append(add_cylinder("Pendant", (0.05, -0.205, 0.70), 0.045,
                                0.012, 12, gold, rotation=(math.pi / 2, 0, 0)))
    # Hairpin through the hair + gold bead at the end.
    costume.append(add_cylinder("Hairpin", (0, 0.03, 1.63), 0.012, 0.50,
                                8, gold, rotation=(0, math.pi / 2, 0)))
    costume.append(add_sphere("HairpinBead", (0.26, 0.03, 1.63), 0.028,
                              6, 4, (1.0, 1.0, 1.0), gold))

    # --- normal self-check (flip any inward-facing face) ---
    for obj in mannequin + costume:
        flipped = fix_normals(obj)
        if flipped:
            print("NORMALS_FIXED %s flipped=%d" % (obj.name, flipped))

    # --- render: front beauty shot ---
    cam = make_camera("Camera", (0, -3.6, 1.0), (0, 0, 0.85), lens=40.0)
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)
    render(RENDER_OUT)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
    print("BLEND_SAVED:", BLEND_OUT)

    # --- wireframe: projected visible edges (PIL overlay, drawn outside) ---
    export_wireframe_segments(mannequin + costume, cam, WIRE_JSON)

    # --- poly counts (measured, not invented) ---
    counts = {}
    for o in costume:
        counts[o.name] = poly_count(o)
    total = total_poly_count(costume)
    tris = sum(1 for o in costume for p in o.data.polygons
               if len(p.vertices) == 3)
    quads = sum(1 for o in costume for p in o.data.polygons
                if len(p.vertices) == 4)
    ngons = sum(1 for o in costume for p in o.data.polygons
                if len(p.vertices) > 4)
    print("COSTUME_POLY total=%d tris=%d quads=%d ngons=%d"
          % (total, tris, quads, ngons))
    for name in sorted(counts):
        print("COSTUME_POLY %s=%d" % (name, counts[name]))
    print("MANNEQUIN_POLY total=%d" % total_poly_count(mannequin))


if __name__ == "__main__":
    main()
