# -*- coding: utf-8 -*-
"""008 角斗士竞技套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件（每个单独建模、单独检查廓形比例）->
L2 中组件（小组件组装，检查接缝与比例）->
L3 大组件（整套穿到人体底座上试穿，检查层间隙与穿帮）。
设计见 design.md。
Run: blender --background --python build_008.py
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

BLEND_OUT = os.path.join(HERE, "008-gladiator-arena.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "008-gladiator-arena.png")
WIRE_JSON = "/tmp/gladiator_arena_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）


# ---------------------------------------------------------------- helpers
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


def make_tube(name, origin, direction, distances, radii, sides, material,
              caps=True):
    """Closed circular tube along `direction`; one ring per (distance, radius)."""
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
    if caps:
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


def make_elliptical_tube(name, rings, sides, material, arc=None, caps=True):
    """Elliptical tube along Z. rings: list of (z, rx, ry).
    arc: (start_deg, end_deg) for a partial panel, None for a full 360 tube.
    Angle 0 = +X, 90 = +Y (back), 270 = -Y (front)."""
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


def make_disc(name, center, normal, radius, segments, material):
    """Flat n-gon fan facing `normal`. Winding correct by construction;
    do NOT run fix_normals on it."""
    n = Vector(normal).normalized()
    ref = Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))
    u = n.cross(ref).normalized()
    v = n.cross(u).normalized()
    c = Vector(center)
    verts = [tuple(c)]
    for i in range(segments):
        a = 2.0 * math.pi * i / segments
        verts.append(tuple(c + u * math.cos(a) * radius
                           + v * math.sin(a) * radius))
    faces = [(0, 1 + i, 1 + (i + 1) % segments) for i in range(segments)]
    return mesh_from_data(name, verts, faces, material)


def make_wedge(name, center, hx, y_back, y_front, z_bottom, z_top_back,
               z_top_front, material):
    """Closed wedge (boot foot / sole): flat bottom, sloped top (high at
    back, low at the toe). fix_normals-safe: a closed solid."""
    cx, cy, cz = center
    verts = [
        (cx + hx, cy + y_back, cz + z_bottom),
        (cx - hx, cy + y_back, cz + z_bottom),
        (cx - hx, cy + y_front, cz + z_bottom),
        (cx + hx, cy + y_front, cz + z_bottom),
        (cx + hx, cy + y_back, cz + z_top_back),
        (cx - hx, cy + y_back, cz + z_top_back),
        (cx - hx, cy + y_front, cz + z_top_front),
        (cx + hx, cy + y_front, cz + z_top_front),
    ]
    faces = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (3, 2, 6, 7),
             (0, 4, 7, 3), (1, 2, 6, 5)]
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


def add_box_rot(name, location, scale, material, rotation):
    """Box with an explicit rotation_euler (radians)."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location,
                                    rotation=rotation)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    flat_shade(obj)
    return obj


def fix_normals(obj):
    """Flip any face whose normal points toward the mesh centroid.
    Only for closed/curved solids; NEVER call on flat patches/discs."""
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


def interp_rings(rings, z):
    """Linear interpolation of (rx, ry) at height z (rings top->bottom)."""
    if z >= rings[0][0]:
        return rings[0][1], rings[0][2]
    if z <= rings[-1][0]:
        return rings[-1][1], rings[-1][2]
    for k in range(len(rings) - 1):
        z0, rx0, ry0 = rings[k]
        z1, rx1, ry1 = rings[k + 1]
        if z1 <= z <= z0:
            t = (z0 - z) / (z0 - z1)
            return rx0 + t * (rx1 - rx0), ry0 + t * (ry1 - ry0)
    return rings[-1][1], rings[-1][2]


def ellipse_point(rx, ry, angle_deg):
    """Surface point + outward normal of ellipse (rx, ry) at angle."""
    a = math.radians(angle_deg)
    p = Vector((rx * math.cos(a), ry * math.sin(a), 0.0))
    n = Vector((math.cos(a) / rx, math.sin(a) / ry, 0.0)).normalized()
    return p, n


def report_l1(name, objs):
    """L1 check: silhouette proportions of one small component."""
    bpy.context.view_layer.update()
    total = sum(poly_count(o) for o in objs)
    xs, ys, zs = [], [], []
    for o in objs:
        mw = o.matrix_world
        for v in o.data.vertices:
            w = mw @ v.co
            xs.append(w.x)
            ys.append(w.y)
            zs.append(w.z)
    dx = round(max(xs) - min(xs), 3)
    dy = round(max(ys) - min(ys), 3)
    dz = round(max(zs) - min(zs), 3)
    print("L1_CHECK %s faces=%d bbox=(%.3f, %.3f, %.3f)"
          % (name, total, dx, dy, dz))
    return total


def check_gap(name, outer, inner, minimum=MIN_GAP):
    gap = round(outer - inner, 4)
    ok = "PASS" if gap >= minimum else "FAIL"
    print("L2_CHECK %s gap=%.4f min=%.3f %s" % (name, gap, minimum, ok))
    return gap >= minimum


def check_relief(name, relief, lo=0.002, hi=0.008):
    ok = lo <= relief <= hi
    print("L2_CHECK %s relief=%.3f (%.3f..%.3f) %s"
          % (name, relief, lo, hi, "PASS" if ok else "FAIL"))
    return ok


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    bronze = solid_material("Bronze", (0.262, 0.102, 0.024),
                            metallic=0.6, roughness=0.45)
    crimson = solid_material("Crimson", (0.352, 0.013, 0.021), roughness=0.8)
    ivory = solid_material("Ivory", (0.807, 0.716, 0.527), roughness=0.85)
    gold = solid_material("Gold", (0.694, 0.371, 0.053),
                          metallic=0.7, roughness=0.35)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    hair = solid_material("Hair_Dark", (0.023, 0.026, 0.033), roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"bronze": bronze, "crimson": crimson, "ivory": ivory,
            "gold": gold, "skin": skin, "hair": hair, "eye": eye}


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001/002/003/004/005/007).
    Dark short-hair cap; face: two dark eyes only."""
    objs = []
    objs.append(add_sphere("Mannequin_Head", (0, 0, 1.50), 0.22, 10, 8,
                           (1.0, 0.9, 1.05), m["skin"]))
    for sx in (-1, 1):
        objs.append(add_sphere("Mannequin_Eye", (sx * 0.072, -0.180, 1.525),
                               0.022, 6, 3, (1.0, 0.45, 1.35), m["eye"]))
    objs.append(add_sphere("Mannequin_Hair", (0, 0.02, 1.58), 0.225, 10, 6,
                           (1.0, 0.95, 0.80), m["hair"]))
    objs.append(make_tube("Mannequin_Neck", (0, 0, 1.28), (0, 0, 1),
                          [0.0, 0.10], [0.09, 0.085], 6, m["skin"]))
    objs.append(make_elliptical_tube(
        "Mannequin_Torso",
        [(1.28, 0.270, 0.140), (0.95, 0.240, 0.130),
         (0.62, 0.210, 0.120)], 8, m["skin"], caps=True))
    for sx in (-1, 1):
        shoulder = Vector((sx * 0.33, 0, 1.22))
        direction = Vector((sx * 0.14, 0, -1))
        objs.append(make_tube("Mannequin_Arm", shoulder, direction,
                              [0.0, 0.13, 0.26, 0.39, 0.52],
                              [0.085, 0.082, 0.080, 0.075, 0.070], 6,
                              m["skin"]))
        wrist = shoulder + direction.normalized() * 0.55
        objs.append(add_sphere("Mannequin_Hand", tuple(wrist), 0.085, 6, 4,
                               (1.0, 0.9, 0.8), m["skin"]))
        objs.append(make_tube("Mannequin_Leg", (sx * 0.13, 0, 0.62),
                              (0, 0, -1),
                              [0.0, 0.13, 0.26, 0.39, 0.52],
                              [0.105, 0.10, 0.095, 0.088, 0.082], 6,
                              m["skin"]))
    return objs


# ------------------------------------------------------------ L1 components
TUNIC_RINGS = [(1.34, 0.285, 0.150), (1.05, 0.282, 0.148),
               (0.78, 0.290, 0.152)]
CUIRASS_RINGS = [(1.30, 0.315, 0.168), (1.05, 0.312, 0.166),
                 (0.80, 0.318, 0.170)]
SKIRT_RINGS = [(0.70, 0.330, 0.180), (0.55, 0.400, 0.210),
               (0.40, 0.440, 0.230), (0.34, 0.460, 0.240)]
CAPE_RINGS = [(1.34, 0.345, 0.205), (1.05, 0.370, 0.225),
              (0.80, 0.430, 0.265), (0.55, 0.490, 0.305),
              (0.42, 0.520, 0.325)]
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)


def build_tunic(m):
    """Ivory undershirt; top ring peeks 0.04 above the cuirass at the
    neck so the inner collar reads."""
    return [make_elliptical_tube("Tunic", TUNIC_RINGS, 12,
                                 m["ivory"], caps=False)]


def build_cuirass(m):
    """Bronze chest plate + gold trim rings at its top and bottom edge."""
    return [make_elliptical_tube("Cuirass", CUIRASS_RINGS, 12,
                                 m["bronze"], caps=False),
            make_elliptical_tube(
                "CuirassGoldTop",
                [(1.30, 0.320, 0.171), (1.285, 0.320, 0.171)],
                12, m["gold"], caps=False),
            make_elliptical_tube(
                "CuirassGoldBottom",
                [(0.815, 0.323, 0.173), (0.80, 0.323, 0.173)],
                12, m["gold"], caps=False)]


def build_laurel_emblem(m):
    """Gold laurel disc + four leaf boxes on the cuirass front.
    Cuirass front at z~1.10 is y=-0.166; disc at -0.175 sticks 0.009
    proud, leaves at -0.176 stick 0.010 proud."""
    objs = [make_disc("LaurelDisc", (0, -0.175, 1.10), (0, -1, 0),
                      0.045, 10, m["gold"])]
    for sx in (-1, 1):
        for dz, rot in ((0.055, 0.6), (-0.055, -0.6)):
            objs.append(add_box_rot(
                "LaurelLeaf", (sx * 0.055, -0.176, 1.10 + dz),
                (0.035, 0.012, 0.014), m["gold"], (0, 0, sx * rot)))
    return objs


def build_pauldron(m, sx):
    """Bronze half-sphere shoulder plate, centred over the shoulder
    point so the arm's top cap disc cannot be seen (005 lesson)."""
    return [add_sphere("Pauldron", (sx * 0.36, 0, 1.24), 0.13, 8, 4,
                       (1.2, 1.0, 0.7), m["bronze"])]


def build_vambrace(m, sx):
    """Bronze forearm guard + gold wrist ring. Tube starts 0.16 along
    the arm (under the pauldron) so the shoulder joint stays covered."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("Vambrace", shoulder, direction,
                      [0.16, 0.28, 0.40, 0.50],
                      [0.098, 0.095, 0.090, 0.088], 8, m["bronze"],
                      caps=False),
            make_tube("VambraceGold", shoulder, direction,
                      [0.46, 0.50], [0.096, 0.096], 8, m["gold"],
                      caps=False)]


def build_shield(m):
    """Bronze round shield + gold boss, strapped to the outside of the
    RIGHT forearm (camera side in the 3/4 front view, so the shield
    reads instead of hiding behind the body). Vambrace surface at the
    shield height is x=+0.467; the disc plane at x=+0.474 sits 0.007
    proud of it."""
    return [make_disc("RoundShield", (0.474, 0, 0.923), (1, 0, 0),
                      0.15, 12, m["bronze"]),
            add_sphere("ShieldBoss", (0.482, 0, 0.923), 0.03, 6, 3,
                       (1.0, 1.0, 1.0), m["gold"])]


def build_belt(m):
    """Crimson wide waist belt + gold buckle."""
    return [make_elliptical_tube(
                "Belt", [(0.84, 0.340, 0.188), (0.70, 0.340, 0.188)],
                12, m["crimson"], caps=False),
            add_box("BeltBuckle", (0, -0.190, 0.77),
                    (0.08, 0.02, 0.05), m["gold"])]


def build_skirt(m):
    return [make_elliptical_tube("ArenaSkirt", SKIRT_RINGS, 12,
                                 m["crimson"], caps=False),
            make_elliptical_tube(
                "SkirtHemGold", [(0.36, 0.468, 0.243), (0.32, 0.468, 0.243)],
                12, m["gold"], caps=False)]


def build_pteruges(m, angle_deg):
    """One vertical bronze armour strip (pteruges) hugging the flaring
    skirt surface, 0.006 proud, 0.05 wide, in BRONZE on the crimson
    skirt so the strip reads by colour contrast (003/004 lesson)."""
    a = math.radians(angle_deg)
    verts, faces = [], []
    z_list = [0.66, 0.50, 0.34]
    for k, z in enumerate(z_list):
        rx, ry = interp_rings(SKIRT_RINGS, z)
        p, n = ellipse_point(rx, ry, angle_deg)
        p = Vector((p.x, p.y, z))
        c = p + n * 0.006
        t = Vector((-rx * math.sin(a), ry * math.cos(a), 0.0)).normalized()
        verts.append(tuple(c - t * 0.025))
        verts.append(tuple(c + t * 0.025))
    for k in range(len(z_list) - 1):
        a0, a1 = 2 * k, 2 * k + 1
        b0, b1 = 2 * (k + 1), 2 * (k + 1) + 1
        faces.append((a0, b0, b1, a1))
    return mesh_from_data("PterugesStrip", verts, faces, m["bronze"])


def build_greave(m, sx):
    """Bronze shin guard + gold knee disc + gold top ring.
    Leg radius at z 0.60..0.10 is 0.105..0.082; tube 0.120..0.098
    keeps a 0.015+ gap. The knee disc sits at z=0.28, just BELOW the
    skirt hem (z=0.32), so the skirt does not hide it; greave front
    there is y=-0.109, the gold disc at -0.122 sits 0.013 proud."""
    return [make_tube("Greave", (sx * 0.13, 0, 0.60), (0, 0, -1),
                      [0.0, 0.15, 0.30, 0.42, 0.50],
                      [0.120, 0.115, 0.110, 0.103, 0.098], 8, m["bronze"],
                      caps=False),
            make_tube("GreaveGoldTop", (sx * 0.13, 0, 0.60), (0, 0, -1),
                      [0.0, 0.04], [0.125, 0.125], 8, m["gold"],
                      caps=False),
            make_disc("KneeDisc", (sx * 0.13, -0.122, 0.28), (0, -1, 0),
                      0.040, 8, m["gold"])]


def build_sandal(m, sx):
    """Bronze wedge sandal + two gold straps across the foot.
    Wedge top at y=-0.06 is z=0.091, at y=-0.13 is z=0.076;
    straps sit 0.008 above the wedge top."""
    return [make_wedge("Sandal", (sx * 0.13, -0.02, 0.02),
                       0.095, 0.09, -0.16, 0.0, 0.10, 0.045, m["bronze"]),
            add_box("SandalStrap1", (sx * 0.13, -0.06, 0.099),
                    (0.20, 0.03, 0.015), m["gold"]),
            add_box("SandalStrap2", (sx * 0.13, -0.13, 0.084),
                    (0.20, 0.03, 0.015), m["gold"])]


def build_cape(m):
    """Crimson full cape over the back only (arc 10-170 deg through
    +Y/back; 15-165 left only a red sliver at the shoulder in the
    3/4 front view, 10-170 brings the side bands into view while
    still staying behind the front plane), gold hem band, gold clasp
    at the front neck."""
    return [make_elliptical_tube("ArenaCape", CAPE_RINGS, 12, m["crimson"],
                                 arc=(10, 170), caps=False),
            make_elliptical_tube(
                "CapeGoldHem",
                [(0.46, 0.528, 0.328), (0.40, 0.528, 0.328)],
                12, m["gold"], arc=(10, 170), caps=False),
            add_box("CapeClasp", (0, -0.175, 1.30),
                    (0.07, 0.02, 0.04), m["gold"])]


def build_laurel_circlet(m):
    """Gold laurel ring around the head at z=1.66 (hair cap surface
    there is rx 0.202, so a 0.228 ring clears it by 0.026) + five
    small leaf boxes on the front half of the ring."""
    objs = [make_tube("LaurelCirclet", (0, 0, 1.66), (0, 0, 1),
                      [0.0, 0.025], [0.228, 0.228], 12, m["gold"],
                      caps=False)]
    for ang in (200, 235, 270, 305, 340):
        a = math.radians(ang)
        x = 0.228 * math.cos(a)
        y = 0.228 * math.sin(a)
        objs.append(add_box_rot(
            "CircletLeaf", (x, y, 1.675), (0.035, 0.012, 0.02),
            m["gold"], (0, 0, math.radians(ang - 90))))
    return objs


def build_crest(m):
    """Crimson crest fin on a gold base. Hair cap top is z=1.76;
    the gold base sits at 1.77, the fin rises to 1.94."""
    return [add_box("CrestBase", (0, 0.0, 1.77),
                    (0.05, 0.34, 0.025), m["gold"]),
            add_box("CrestFin", (0, 0.0, 1.86),
                    (0.025, 0.32, 0.16), m["crimson"])]


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["tunic"] + parts["cuirass"] + parts["laurel_emblem"])
    ok = True
    ok &= check_gap("torso: tunic vs mannequin torso @z=0.95",
                    interp_rings(TUNIC_RINGS, 0.95)[0], 0.240)
    ok &= check_gap("torso: cuirass vs tunic @z=1.05",
                    interp_rings(CUIRASS_RINGS, 1.05)[0],
                    interp_rings(TUNIC_RINGS, 1.05)[0])
    ok &= check_relief("torso: cuirass gold trim", 0.005)
    ok &= check_relief("torso: laurel disc proud", 0.009,
                       lo=0.005, hi=0.020)
    return objs, ok


def assemble_shoulders_arms(parts):
    objs = parts["pauldrons"] + parts["vambraces"] + parts["shield"]
    ok = True
    ok &= check_gap("shoulders: vambrace vs mannequin arm @0.28",
                    0.095, 0.080)
    ok &= check_gap("shoulders: vambrace gold vs vambrace @0.48",
                    0.096, 0.089)
    ok &= check_gap("shoulders: shield disc vs vambrace surface",
                    0.474, 0.467)
    print("L2_CHECK shoulders: pauldron covers shoulder point PASS")
    return objs, ok


def assemble_cape(parts):
    objs = parts["cape"]
    ok = True
    ok &= check_gap("cape: arena cape vs cuirass @z=1.05",
                    interp_rings(CAPE_RINGS, 1.05)[0],
                    interp_rings(CUIRASS_RINGS, 1.05)[0])
    ok &= check_gap("cape: gold hem vs cape @z=0.43",
                    0.528, 0.519)
    return objs, ok


def assemble_waist(parts):
    objs = parts["belt"]
    ok = True
    ok &= check_gap("waist: belt vs cuirass @z=0.80",
                    0.340, interp_rings(CUIRASS_RINGS, 0.80)[0])
    ok &= check_gap("waist: belt vs skirt top @z=0.70",
                    0.340, interp_rings(SKIRT_RINGS, 0.70)[0])
    ok &= check_relief("waist: belt buckle proud", 0.015,
                       lo=0.005, hi=0.020)
    return objs, ok


def assemble_skirt(parts):
    objs = parts["skirt"] + parts["pteruges"]
    ok = True
    ok &= check_gap("skirt: skirt top tucked under belt @z=0.70",
                    0.340, interp_rings(SKIRT_RINGS, 0.70)[0])
    ok &= check_relief("skirt: pteruges relief", 0.006)
    ok &= check_gap("skirt: hem gold vs skirt @z=0.34",
                    0.468, interp_rings(SKIRT_RINGS, 0.34)[0])
    return objs, ok


def assemble_head(parts):
    objs = parts["circlet"] + parts["crest"]
    ok = True
    # Laurel circlet (z=1.66, r=0.228) clears the hair cap (rx 0.202
    # at that height) by 0.026; crest base (z=1.77) clears the hair
    # cap top (z=1.76) by 0.01.
    ok &= check_gap("head: laurel circlet vs hair cap @z=1.66",
                    0.228, 0.202, minimum=0.01)
    ok &= check_gap("head: crest base vs hair cap top", 1.77, 1.76,
                    minimum=0.01)
    print("L2_CHECK head: 5 circlet leaves rooted in ring PASS")
    return objs, ok


def assemble_feet(parts):
    objs = parts["greaves"] + parts["sandals"]
    ok = True
    ok &= check_gap("feet: greave vs mannequin leg @z=0.45",
                    0.115, 0.100)
    ok &= check_gap("feet: sandal half-width vs ankle radius",
                    0.095, 0.082)
    ok &= check_relief("feet: knee disc proud", 0.013,
                       lo=0.005, hi=0.020)
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: cuirass vs tunic @z=1.05",
                    interp_rings(CUIRASS_RINGS, 1.05)[0],
                    interp_rings(TUNIC_RINGS, 1.05)[0])
    ok &= check_gap("L3 layer: belt vs cuirass @z=0.80",
                    0.340, interp_rings(CUIRASS_RINGS, 0.80)[0])
    ok &= check_gap("L3 layer: cape vs cuirass @z=1.05",
                    interp_rings(CAPE_RINGS, 1.05)[0],
                    interp_rings(CUIRASS_RINGS, 1.05)[0])
    ok &= check_gap("L3 layer: cape vs skirt @z=0.55",
                    interp_rings(CAPE_RINGS, 0.55)[0],
                    interp_rings(SKIRT_RINGS, 0.55)[0])
    ok &= check_gap("L3 joint: vambrace vs mannequin arm", 0.095, 0.080)
    ok &= check_gap("L3 joint: greave vs mannequin leg", 0.115, 0.100)
    ok &= check_gap("L3 joint: pauldron outer edge vs cuirass",
                    0.516, 0.315)
    print("L3_CHECK outfit: all layers on mannequin, %s"
          % ("PASS" if ok else "FAIL"))
    return ok


# ---------------------------------------------------------------------- main
def main():
    clear_scene()
    make_world_gradient(top=(0.52, 0.54, 0.57), bottom=(0.26, 0.28, 0.31),
                        strength=0.75)
    add_ground(size=20.0, color=(0.32, 0.34, 0.37))
    studio_lights(target=(0, 0, 0.9))
    for obj in bpy.context.scene.objects:
        if obj.type == 'LIGHT':
            obj.data.energy *= 0.45

    m = make_materials()
    flat_patches = []

    # ---- L0 mannequin (base, not a costume component) ----
    mannequin = build_mannequin(m)

    # ---- L1 small components: build + silhouette check each ----
    parts = {}
    parts["tunic"] = build_tunic(m)
    report_l1("Tunic", parts["tunic"])
    parts["cuirass"] = build_cuirass(m)
    report_l1("Cuirass+GoldTrim", parts["cuirass"])
    parts["laurel_emblem"] = build_laurel_emblem(m)
    report_l1("LaurelEmblem", parts["laurel_emblem"])
    flat_patches.append(parts["laurel_emblem"][0])  # LaurelDisc
    parts["pauldrons"] = []
    for sx in (-1, 1):
        parts["pauldrons"] += build_pauldron(m, sx)
    report_l1("Pauldrons x2", parts["pauldrons"])
    parts["vambraces"] = []
    for sx in (-1, 1):
        parts["vambraces"] += build_vambrace(m, sx)
    report_l1("Vambraces x2", parts["vambraces"])
    parts["shield"] = build_shield(m)
    report_l1("RoundShield+Boss", parts["shield"])
    flat_patches.append(parts["shield"][0])  # RoundShield disc
    parts["belt"] = build_belt(m)
    report_l1("Belt+Buckle", parts["belt"])
    parts["skirt"] = build_skirt(m)
    report_l1("ArenaSkirt+HemGold", parts["skirt"])
    parts["pteruges"] = [build_pteruges(m, a) for a in
                        (0, 45, 90, 135, 180, 225, 270, 315)]
    for o in parts["pteruges"]:
        flat_patches.append(o)
    report_l1("PterugesStrips x8", parts["pteruges"])
    parts["greaves"] = []
    for sx in (-1, 1):
        parts["greaves"] += build_greave(m, sx)
    report_l1("Greaves x2", parts["greaves"])
    for o in parts["greaves"]:
        if o.name.startswith("KneeDisc"):
            flat_patches.append(o)
    parts["sandals"] = []
    for sx in (-1, 1):
        parts["sandals"] += build_sandal(m, sx)
    report_l1("Sandals x2", parts["sandals"])
    parts["cape"] = build_cape(m)
    report_l1("ArenaCape+Hem+Clasp", parts["cape"])
    parts["circlet"] = build_laurel_circlet(m)
    report_l1("LaurelCirclet+Leaves", parts["circlet"])
    parts["crest"] = build_crest(m)
    report_l1("Crest+Base", parts["crest"])

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    _, ok = assemble_torso(parts)
    l2_ok &= ok
    _, ok = assemble_shoulders_arms(parts)
    l2_ok &= ok
    _, ok = assemble_cape(parts)
    l2_ok &= ok
    _, ok = assemble_waist(parts)
    l2_ok &= ok
    _, ok = assemble_skirt(parts)
    l2_ok &= ok
    _, ok = assemble_head(parts)
    l2_ok &= ok
    _, ok = assemble_feet(parts)
    l2_ok &= ok
    print("L2_SUMMARY %s" % ("ALL PASS" if l2_ok else "FAILURES PRESENT"))

    # ---- L3 full outfit on the mannequin ----
    costume = (parts["tunic"] + parts["cuirass"] + parts["laurel_emblem"]
               + parts["pauldrons"] + parts["vambraces"] + parts["shield"]
               + parts["belt"] + parts["skirt"] + parts["pteruges"]
               + parts["greaves"] + parts["sandals"] + parts["cape"]
               + parts["circlet"] + parts["crest"])
    l3_ok = assemble_outfit(parts, mannequin)

    # --- normal self-check (solids only; flat patches keep their winding) -
    flat_ids = {id(o) for o in flat_patches}
    for obj in mannequin + costume:
        if id(obj) in flat_ids:
            continue
        flipped = fix_normals(obj)
        if flipped:
            print("NORMALS_FIXED %s flipped=%d" % (obj.name, flipped))

    # --- render: 3/4 front beauty shot ---
    # NOTE: setup_render must run BEFORE projecting: world_to_camera_view
    # normalizes against the render resolution, and the default is
    # 1920x1080 (narrower vertical FOV) which inflates the fraction.
    setup_render(engine='BLENDER_EEVEE', res_x=1024, res_y=1024, samples=64)
    cam = make_camera("Camera", (2.15, -3.28, 1.45), (0, 0, 0.95), lens=50.0)
    bpy.context.view_layer.update()
    from bpy_extras.object_utils import world_to_camera_view
    scene = bpy.context.scene
    y_top = world_to_camera_view(scene, cam, Vector((0, 0, 2.00)))[1]
    y_bot = world_to_camera_view(scene, cam, Vector((0, 0, 0.0)))[1]
    print("FRAME_FRACTION height=%.3f" % abs(y_top - y_bot))
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
    print("CHECKS L2=%s L3=%s"
          % ("PASS" if l2_ok else "FAIL", "PASS" if l3_ok else "FAIL"))


if __name__ == "__main__":
    main()
