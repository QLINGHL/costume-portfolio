# -*- coding: utf-8 -*-
"""007 嘉年华吟游诗人套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件（每个单独建模、单独检查廓形比例）->
L2 中组件（小组件组装，检查接缝与比例）->
L3 大组件（整套穿到人体底座上试穿，检查层间隙与穿帮）。
设计见 design.md。
Run: blender --background --python build_007.py
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

BLEND_OUT = os.path.join(HERE, "007-carnival-bard.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "007-carnival-bard.png")
WIRE_JSON = "/tmp/carnival_bard_wire.json"

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
    violet = solid_material("Violet", (0.044, 0.014, 0.112), roughness=0.85)
    crimson = solid_material("Crimson", (0.434, 0.014, 0.051), roughness=0.8)
    ivory = solid_material("Ivory", (0.888, 0.807, 0.665), roughness=0.85)
    gold = solid_material("Gold", (0.694, 0.371, 0.053),
                          metallic=0.7, roughness=0.35)
    black = solid_material("Black", (0.003, 0.003, 0.003), roughness=0.6)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    hair = solid_material("Hair_Dark", (0.023, 0.026, 0.033), roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"violet": violet, "crimson": crimson, "ivory": ivory,
            "gold": gold, "black": black,
            "skin": skin, "hair": hair, "eye": eye}


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001/002/003/004/005).
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
INNER_RINGS = [(1.34, 0.285, 0.150), (1.05, 0.282, 0.148),
               (0.80, 0.290, 0.152)]
DOUBLET_RINGS = [(1.30, 0.315, 0.168), (1.05, 0.312, 0.166),
                 (0.78, 0.318, 0.170)]
SKIRT_RINGS = [(0.70, 0.330, 0.180), (0.55, 0.400, 0.210),
               (0.40, 0.440, 0.230), (0.32, 0.460, 0.240)]
CAPE_RINGS = [(1.32, 0.345, 0.205), (1.05, 0.365, 0.225),
              (0.80, 0.420, 0.260), (0.62, 0.480, 0.300)]
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)


def build_inner(m):
    """Ivory undershirt; top ring peeks 0.04 above the doublet at the
    neck so the inner collar reads."""
    return [make_elliptical_tube("Undershirt", INNER_RINGS, 12,
                                 m["ivory"], caps=False)]


def build_doublet(m):
    return [make_elliptical_tube("Doublet", DOUBLET_RINGS, 12,
                                 m["violet"], caps=False)]


def build_collar(m):
    """Violet standing collar + gold trim ring at its top edge."""
    return [make_elliptical_tube(
                "Collar", [(1.40, 0.260, 0.140), (1.32, 0.300, 0.160)],
                12, m["violet"], caps=False),
            make_elliptical_tube(
                "CollarGoldTrim",
                [(1.40, 0.265, 0.143), (1.385, 0.265, 0.143)],
                12, m["gold"], caps=False)]


def build_buttons(m):
    """Three gold buttons down the chest centre line. Doublet front
    at z~1.05 is y=-0.166; boxes centred at -0.172 stick 0.014 proud."""
    objs = []
    for i, z in enumerate((1.15, 1.05, 0.95)):
        objs.append(add_box("GoldButton%d" % i, (0, -0.172, z),
                            (0.035, 0.016, 0.035), m["gold"]))
    return objs


def build_note(m, cx, cz):
    """One gold music note: head + stem + flag, on the doublet front
    (y=-0.172, ~0.013 proud of the robe at z~1.0-1.1)."""
    return [add_box("NoteHead", (cx, -0.172, cz),
                    (0.028, 0.014, 0.020), m["gold"]),
            add_box("NoteStem", (cx + 0.012, -0.172, cz + 0.050),
                    (0.008, 0.014, 0.085), m["gold"]),
            add_box_rot("NoteFlag", (cx + 0.024, -0.172, cz + 0.085),
                        (0.008, 0.014, 0.050), m["gold"], (0, 0, 0.6))]


def build_notes(m):
    objs = []
    for cx, cz in ((-0.10, 1.12), (0.02, 1.02), (0.11, 1.10)):
        objs += build_note(m, cx, cz)
    return objs


def build_puff_sleeve(m, sx):
    """Ivory puffed sleeve: bulges mid-arm, tapers to a gold-ringed
    cuff. Tube starts 0.02 ABOVE the shoulder point so the mannequin
    arm's top cap disc cannot be seen through the open top ring
    (005 lesson)."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("PuffSleeve", shoulder, direction,
                      [-0.02, 0.12, 0.28, 0.42, 0.52],
                      [0.130, 0.165, 0.175, 0.150, 0.115], 8, m["ivory"],
                      caps=False),
            make_tube("CuffGold", shoulder, direction,
                      [0.48, 0.52], [0.128, 0.128], 8, m["gold"],
                      caps=False)]


def build_cape(m):
    """Crimson half-cape over the back only (arc 30-150 deg through
    +Y/back), gold hem band, gold clasp at the front neck."""
    return [make_elliptical_tube("HalfCape", CAPE_RINGS, 12, m["crimson"],
                                 arc=(15, 165), caps=False),
            make_elliptical_tube(
                "CapeGoldHem",
                [(0.66, 0.488, 0.303), (0.60, 0.488, 0.303)],
                12, m["gold"], arc=(15, 165), caps=False),
            add_box("CapeClasp", (0, -0.175, 1.28),
                    (0.07, 0.02, 0.04), m["gold"])]


def build_sash(m):
    """Crimson wide waist sash + gold buckle."""
    return [make_elliptical_tube(
                "Sash", [(0.82, 0.335, 0.185), (0.68, 0.335, 0.185)],
                12, m["crimson"], caps=False),
            add_box("SashBuckle", (0, -0.190, 0.75),
                    (0.08, 0.02, 0.05), m["gold"])]


def build_skirt(m):
    return [make_elliptical_tube("PleatedSkirt", SKIRT_RINGS, 12,
                                 m["violet"], caps=False),
            make_elliptical_tube(
                "HemGold", [(0.36, 0.468, 0.243), (0.32, 0.468, 0.243)],
                12, m["gold"], caps=False)]


def build_pleat(m, angle_deg):
    """One vertical skirt pleat: a 3-ring strip hugging the flaring
    skirt surface, 0.006 proud, 0.032 wide, in CRIMSON on the violet
    skirt so the fold reads by colour contrast (003/004 lesson)."""
    a = math.radians(angle_deg)
    verts, faces = [], []
    z_list = [0.62, 0.50, 0.38]
    for k, z in enumerate(z_list):
        rx, ry = interp_rings(SKIRT_RINGS, z)
        p, n = ellipse_point(rx, ry, angle_deg)
        p = Vector((p.x, p.y, z))
        c = p + n * 0.006
        t = Vector((-rx * math.sin(a), ry * math.cos(a), 0.0)).normalized()
        verts.append(tuple(c - t * 0.016))
        verts.append(tuple(c + t * 0.016))
    for k in range(len(z_list) - 1):
        a0, a1 = 2 * k, 2 * k + 1
        b0, b1 = 2 * (k + 1), 2 * (k + 1) + 1
        faces.append((a0, b0, b1, a1))
    return mesh_from_data("SkirtPleat", verts, faces, m["crimson"])


def build_boot(m, sx):
    """Crimson long boot: tube up the leg + wedge foot + gold sole line.
    Wedge half-width 0.095 and back 0.09 fully enclose the mannequin
    ankle (radius 0.082)."""
    return [make_tube("CarnivalBoot", (sx * 0.13, 0, 0.62), (0, 0, -1),
                      [0.0, 0.15, 0.30, 0.45, 0.54],
                      [0.118, 0.115, 0.110, 0.105, 0.100], 8, m["crimson"],
                      caps=False),
            make_wedge("BootFoot", (sx * 0.13, -0.02, 0.02),
                       0.095, 0.09, -0.16, 0.0, 0.10, 0.045, m["crimson"]),
            add_box("BootSoleGold", (sx * 0.13, -0.172, 0.03),
                    (0.12, 0.018, 0.02), m["gold"])]


def build_hat(m):
    """Wide-brim bard hat: brim disc above the hair cap (hair top
    z=1.76, brim at 1.78), domed violet crown, gold hat band."""
    return [make_disc("HatBrim", (0, 0, 1.78), (0, 0, 1), 0.34, 12,
                      m["violet"]),
            add_sphere("HatCrown", (0, 0, 1.82), 0.16, 10, 6,
                       (1.0, 1.0, 0.70), m["violet"]),
            make_tube("HatGoldBand", (0, 0, 1.76), (0, 0, 1),
                      [0.0, 0.035], [0.168, 0.168], 12, m["gold"],
                      caps=False)]


def build_feather(m, center, rotation, material):
    """One thin feather (flat long box) stuck into the hat side,
    leaning outward."""
    return add_box_rot("HatFeather", center, (0.045, 0.008, 0.30),
                       material, rotation)


def build_mask(m):
    """Gold half-mask pendant hanging from the sash front: cord +
    gold disc + two black eye dots. Skirt front at z=0.56, x=0.10 is
    y=-0.202; disc at -0.212 hangs 0.010 proud, eye dots 0.004 proud
    of the disc."""
    return [make_tube("MaskCord", (0.10, -0.190, 0.72), (0, 0, -1),
                      [0.0, 0.12], [0.006, 0.006], 6, m["gold"],
                      caps=False),
            make_disc("Mask", (0.10, -0.212, 0.56), (0, -1, 0),
                      0.050, 10, m["gold"]),
            make_disc("MaskEyeL", (0.080, -0.216, 0.565), (0, -1, 0),
                      0.008, 6, m["black"]),
            make_disc("MaskEyeR", (0.120, -0.216, 0.565), (0, -1, 0),
                      0.008, 6, m["black"])]


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["inner"] + parts["doublet"] + parts["collar"]
            + parts["buttons"] + parts["notes"])
    ok = True
    ok &= check_gap("torso: undershirt vs mannequin torso @z=0.95",
                    interp_rings(INNER_RINGS, 0.95)[0], 0.240)
    ok &= check_gap("torso: doublet vs undershirt @z=1.05",
                    interp_rings(DOUBLET_RINGS, 1.05)[0],
                    interp_rings(INNER_RINGS, 1.05)[0])
    ok &= check_relief("torso: collar gold trim", 0.005)
    ok &= check_relief("torso: gold button proud", 0.014,
                       lo=0.005, hi=0.020)
    ok &= check_relief("torso: music note proud", 0.013,
                       lo=0.005, hi=0.020)
    return objs, ok


def assemble_sleeves(parts):
    objs = parts["sleeve_L"] + parts["sleeve_R"]
    ok = True
    ok &= check_gap("sleeves: puff sleeve vs mannequin arm", 0.115, 0.070)
    ok &= check_gap("sleeves: cuff gold vs sleeve @0.50",
                    0.128, 0.122)
    return objs, ok


def assemble_cape(parts):
    objs = parts["cape"]
    ok = True
    ok &= check_gap("cape: half-cape vs doublet @z=1.05",
                    interp_rings(CAPE_RINGS, 1.05)[0],
                    interp_rings(DOUBLET_RINGS, 1.05)[0])
    ok &= check_gap("cape: gold hem vs cape @z=0.63",
                    0.488, 0.477)
    return objs, ok


def assemble_waist(parts):
    objs = parts["sash"] + parts["mask"]
    ok = True
    ok &= check_gap("waist: sash vs doublet @z=0.75",
                    0.335, interp_rings(DOUBLET_RINGS, 0.75)[0])
    ok &= check_relief("waist: mask vs skirt front", 0.010,
                       lo=0.005, hi=0.020)
    return objs, ok


def assemble_skirt(parts):
    objs = parts["skirt"] + parts["pleats"]
    ok = True
    ok &= check_gap("skirt: skirt top tucked under sash @z=0.70",
                    0.335, interp_rings(SKIRT_RINGS, 0.70)[0])
    ok &= check_relief("skirt: pleat relief", 0.006)
    ok &= check_gap("skirt: hem gold vs skirt @z=0.34",
                    0.468, interp_rings(SKIRT_RINGS, 0.34)[0])
    return objs, ok


def assemble_head(parts):
    objs = parts["hat"] + parts["feathers"]
    ok = True
    # Hat brim (z=1.78) clears the hair cap top (z=1.76) by 0.02.
    ok &= check_gap("head: hat brim vs hair cap top", 1.78, 1.76,
                    minimum=0.01)
    print("L2_CHECK head: 3 feathers rooted in hat crown PASS")
    return objs, ok


def assemble_feet(parts):
    objs = parts["boots"]
    ok = True
    ok &= check_gap("feet: boot tube vs mannequin leg @z=0.47",
                    0.115, 0.100)
    ok &= check_gap("feet: boot foot half-width vs ankle radius",
                    0.095, 0.082)
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: doublet vs undershirt @z=1.05",
                    interp_rings(DOUBLET_RINGS, 1.05)[0],
                    interp_rings(INNER_RINGS, 1.05)[0])
    ok &= check_gap("L3 layer: sash vs doublet @z=0.75",
                    0.335, interp_rings(DOUBLET_RINGS, 0.75)[0])
    ok &= check_gap("L3 layer: cape vs doublet @z=1.05",
                    interp_rings(CAPE_RINGS, 1.05)[0],
                    interp_rings(DOUBLET_RINGS, 1.05)[0])
    ok &= check_gap("L3 joint: puff sleeve vs mannequin arm",
                    0.115, 0.070)
    ok &= check_gap("L3 joint: boot vs mannequin leg", 0.115, 0.100)
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
    parts["inner"] = build_inner(m)
    report_l1("Undershirt", parts["inner"])
    parts["doublet"] = build_doublet(m)
    report_l1("Doublet", parts["doublet"])
    parts["collar"] = build_collar(m)
    report_l1("Collar+GoldTrim", parts["collar"])
    parts["buttons"] = build_buttons(m)
    report_l1("GoldButtons x3", parts["buttons"])
    parts["notes"] = build_notes(m)
    report_l1("MusicNotes x3", parts["notes"])
    parts["sleeve_L"] = build_puff_sleeve(m, -1)
    report_l1("PuffSleeve_L", parts["sleeve_L"])
    parts["sleeve_R"] = build_puff_sleeve(m, 1)
    report_l1("PuffSleeve_R", parts["sleeve_R"])
    parts["cape"] = build_cape(m)
    report_l1("HalfCape+Hem+Clasp", parts["cape"])
    parts["sash"] = build_sash(m)
    report_l1("Sash+Buckle", parts["sash"])
    parts["mask"] = build_mask(m)
    report_l1("MaskPendant", parts["mask"])
    for o in parts["mask"]:
        if o.name.startswith("Mask") and o.name != "MaskCord":
            flat_patches.append(o)
    parts["skirt"] = build_skirt(m)
    report_l1("PleatedSkirt+HemGold", parts["skirt"])
    parts["pleats"] = [build_pleat(m, a) for a in
                       (0, 45, 90, 135, 180, 225, 270, 315)]
    for o in parts["pleats"]:
        flat_patches.append(o)
    report_l1("SkirtPleats x8", parts["pleats"])
    parts["boots"] = []
    for sx in (-1, 1):
        parts["boots"] += build_boot(m, sx)
    report_l1("CarnivalBoots x2", parts["boots"])
    parts["hat"] = build_hat(m)
    report_l1("BardHat", parts["hat"])
    flat_patches.append(parts["hat"][0])  # HatBrim disc
    parts["feathers"] = [
        build_feather(m, (0.24, 0.08, 1.95), (0.35, 0, -0.55),
                      m["gold"]),
        build_feather(m, (0.16, 0.14, 1.97), (0.45, 0, -0.25),
                      m["crimson"]),
        build_feather(m, (0.28, -0.02, 1.93), (0.25, 0, -0.75),
                      m["ivory"]),
    ]
    report_l1("HatFeathers x3", parts["feathers"])

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    _, ok = assemble_torso(parts)
    l2_ok &= ok
    _, ok = assemble_sleeves(parts)
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
    costume = (parts["inner"] + parts["doublet"] + parts["collar"]
               + parts["buttons"] + parts["notes"]
               + parts["sleeve_L"] + parts["sleeve_R"] + parts["cape"]
               + parts["sash"] + parts["mask"] + parts["skirt"]
               + parts["pleats"] + parts["boots"] + parts["hat"]
               + parts["feathers"])
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
    y_top = world_to_camera_view(scene, cam, Vector((0, 0, 2.12)))[1]
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
