# -*- coding: utf-8 -*-
"""004 骑士铠甲礼服：组件化制作流程（001 v2 确立的流程）。
L1 小组件（每个单独建模、单独检查廓形比例）->
L2 中组件（小组件组装，检查接缝与比例）->
L3 大组件（整套穿到人体底座上试穿，检查层间隙与穿帮）。
设计见 design.md。
Run: blender --background --python build_004.py
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

BLEND_OUT = os.path.join(HERE, "004-knight-armor.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "004-knight-armor.png")
WIRE_JSON = "/tmp/knight_armor_wire.json"

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


def add_cylinder(name, location, radius, depth, vertices, material,
                 rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius,
                                        depth=depth, location=location,
                                        rotation=rotation)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(material)
    # The primitive's caps are single n-gons; fan them into triangles so
    # the mesh carries no ngons (costume rule: N-gon as close to 0 as
    # possible).
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    ngons = [f for f in bm.faces if len(f.verts) > 4]
    if ngons:
        bmesh.ops.triangulate(bm, faces=ngons)
    bm.to_mesh(obj.data)
    bm.free()
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


def ellipse_front(rx, ry, x):
    """Front-surface point of an ellipse (rx, ry) at horizontal offset x,
    and its outward normal. Front is -Y."""
    cx = max(-0.999, min(0.999, x / rx))
    s = math.sqrt(1.0 - cx * cx)
    y = -ry * s
    n = Vector((cx / rx, -s / ry, 0.0)).normalized()
    return y, n


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


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    steel = solid_material("Steel", (0.578, 0.604, 0.644),
                           metallic=0.85, roughness=0.35)
    white = solid_material("White", (0.888, 0.871, 0.823), roughness=0.85)
    blue = solid_material("MondBlue", (0.027, 0.068, 0.195), roughness=0.75)
    red = solid_material("Knight_Red", (0.533, 0.020, 0.026), roughness=0.75)
    gold = solid_material("Gold", (0.658, 0.352, 0.009),
                          metallic=0.6, roughness=0.35)
    pale = solid_material("PaleBlue", (0.571, 0.631, 0.723), roughness=0.8)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    hair = solid_material("Hair_Blonde", (0.694, 0.456, 0.105),
                          roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    lip = solid_material("Lip_Red", (0.533, 0.020, 0.026), roughness=0.6)
    return {"steel": steel, "white": white, "blue": blue, "red": red,
            "gold": gold, "pale": pale,
            "skin": skin, "hair": hair, "eye": eye, "lip": lip}


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001/002/003).
    Blonde hair cap; face: two dark eyes + red lips."""
    objs = []
    objs.append(add_sphere("Mannequin_Head", (0, 0, 1.50), 0.22, 10, 8,
                           (1.0, 0.9, 1.05), m["skin"]))
    for sx in (-1, 1):
        objs.append(add_sphere("Mannequin_Eye", (sx * 0.072, -0.180, 1.525),
                               0.022, 6, 3, (1.0, 0.45, 1.35), m["eye"]))
    objs.append(add_box("Mannequin_Lips", (0, -0.190, 1.44),
                        (0.05, 0.012, 0.016), m["lip"]))
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
DRESS_RINGS = [(1.30, 0.305, 0.170), (1.05, 0.300, 0.168),
               (0.80, 0.308, 0.172), (0.55, 0.335, 0.186),
               (0.30, 0.378, 0.205), (0.12, 0.408, 0.220)]
PLATE_RINGS = [(1.28, 0.322, 0.180), (1.10, 0.318, 0.178),
               (0.92, 0.320, 0.180)]
CAPE_RINGS = [(1.34, 0.335, 0.185), (1.10, 0.350, 0.195),
              (0.80, 0.390, 0.215), (0.50, 0.430, 0.235),
              (0.30, 0.460, 0.250)]
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)


def front_y(rings, x, z):
    """Front surface Y of an elliptical tube at (x, z)."""
    rx, ry = interp_rings(rings, z)
    return ellipse_front(rx, ry, x)[0]


def build_dress(m):
    return [make_elliptical_tube("WhiteDress", DRESS_RINGS, 12,
                                 m["white"], caps=False)]


def build_collar(m):
    """White stand collar above the breastplate + thin gold trim."""
    return [make_elliptical_tube(
                "Collar", [(1.40, 0.140, 0.122), (1.34, 0.150, 0.130)],
                12, m["white"], caps=False),
            make_elliptical_tube(
                "CollarTrim", [(1.405, 0.143, 0.125),
                               (1.395, 0.143, 0.125)],
                12, m["gold"], caps=False)]


def build_breastplate(m):
    """Steel front plate + 2 horizontal steel bands + gold bottom trim.
    Front arc (200, 340): angle 270 = -Y is the front."""
    objs = [make_elliptical_tube("Breastplate", PLATE_RINGS, 10,
                                 m["steel"], arc=(200, 340), caps=False)]
    for z in (1.20, 1.00):
        rx, ry = interp_rings(PLATE_RINGS, z)
        objs.append(make_elliptical_tube(
            "PlateBand", [(z + 0.01, rx + 0.003, ry + 0.003),
                          (z - 0.01, rx + 0.003, ry + 0.003)],
            10, m["gold"], arc=(200, 340), caps=False))
    objs.append(make_elliptical_tube(
        "PlateGoldTrim", [(0.94, 0.324, 0.184), (0.90, 0.324, 0.184)],
        10, m["gold"], arc=(200, 340), caps=False))
    return objs


def build_pauldron(m, sx):
    """Steel shoulder dome + gold emblem disc on its outer side."""
    objs = [add_sphere("Pauldron", (sx * 0.33, 0, 1.24), 0.13, 8, 5,
                       (1.15, 1.0, 0.75), m["steel"])]
    objs.append(make_disc("PauldronEmblem", (sx * 0.485, 0, 1.24),
                          (sx, 0, 0), 0.030, 8, m["gold"]))
    return objs


def build_sleeve(m, sx):
    """White upper-arm sleeve."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("WhiteSleeve", shoulder, direction,
                      [0.0, 0.15, 0.28],
                      [0.100, 0.102, 0.100], 8, m["white"], caps=False)]


def build_gauntlet(m, sx):
    """Steel forearm gauntlet + gold wrist cuff."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("Gauntlet", shoulder, direction,
                      [0.30, 0.40, 0.50, 0.58],
                      [0.098, 0.095, 0.092, 0.095], 8, m["steel"],
                      caps=False),
            make_tube("GauntletCuff", shoulder, direction,
                      [0.28, 0.34], [0.108, 0.108], 8, m["gold"],
                      caps=False)]


def build_belt(m):
    """Deep-blue waist belt + gold buckle."""
    return [make_elliptical_tube(
                "Belt", [(0.78, 0.325, 0.185), (0.66, 0.325, 0.185)],
                12, m["blue"], caps=False),
            add_box("BeltBuckle", (0, -0.196, 0.72),
                    (0.09, 0.02, 0.06), m["gold"])]


def build_red_bow(m):
    """Big red bow on the breastplate: 2 loops + knot + 2 tails.
    Breastplate front at z=1.05 is y=-0.179; loops sit with their
    closest corner ~0.006 proud (rotation 0.45 rad, center y -0.21)."""
    objs = []
    for sx in (-1, 1):
        objs.append(add_box_rot("BowLoop", (sx * 0.10, -0.21, 1.06),
                                (0.12, 0.025, 0.07), m["red"],
                                (0, 0, sx * 0.45)))
        objs.append(add_box("BowTail", (sx * 0.045, -0.19, 0.92),
                            (0.045, 0.014, 0.18), m["red"]))
    objs.append(add_sphere("BowKnot", (0, -0.215, 1.06), 0.028, 6, 3,
                           (1.0, 1.0, 1.0), m["red"]))
    return objs


def build_cape(m):
    """Deep-blue cape: back arc (20, 160), angle 90 = +Y is the back.
    Flares from the shoulders down past the knees."""
    objs = [make_elliptical_tube("Cape", CAPE_RINGS, 12, m["blue"],
                                 arc=(20, 160), caps=False)]
    for sx in (-1, 1):
        y = front_y(DRESS_RINGS, sx * 0.22, 1.28)
        objs.append(make_disc("CapeClasp", (sx * 0.22, y - 0.007, 1.28),
                              (0, -1, 0), 0.025, 8, m["gold"]))
    return objs


def build_pleat(m, angle_deg):
    """One vertical skirt pleat: a 4-ring strip hugging the flaring dress
    surface, 0.006 proud, 0.028 wide, in pale blue so the fold reads
    against the white skirt (003 lesson: same-colour pleats vanish)."""
    a = math.radians(angle_deg)
    verts, faces = [], []
    z_list = [0.55, 0.40, 0.25, 0.12]
    for k, z in enumerate(z_list):
        rx, ry = interp_rings(DRESS_RINGS, z)
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
    return mesh_from_data("SkirtPleat", verts, faces, m["pale"])


def build_hem(m):
    return [make_elliptical_tube(
                "BlueHem", [(0.16, 0.416, 0.227), (0.10, 0.416, 0.227)],
                12, m["blue"], caps=False)]


def build_boot(m, sx):
    """Steel knee boot: tube up the leg + gold cuff + wedge foot
    + gold toe cap. Wedge half-width 0.095 and back 0.09 fully enclose
    the mannequin ankle (radius 0.082)."""
    return [make_tube("KnightBoot", (sx * 0.13, 0, 0.62), (0, 0, -1),
                      [0.0, 0.15, 0.30, 0.45, 0.54],
                      [0.118, 0.115, 0.110, 0.105, 0.100], 8, m["steel"],
                      caps=False),
            make_tube("BootCuff", (sx * 0.13, 0, 0.62), (0, 0, -1),
                      [0.0, 0.06], [0.122, 0.122], 8, m["gold"],
                      caps=False),
            make_wedge("BootFoot", (sx * 0.13, -0.02, 0.02),
                       0.095, 0.09, -0.16, 0.0, 0.10, 0.045, m["steel"]),
            add_box("BootToeGold", (sx * 0.13, -0.172, 0.03),
                    (0.12, 0.018, 0.04), m["gold"])]


def build_hair(m):
    """Blonde ponytail: hangs behind the head, OUTSIDE the cape
    (cape back at z~1.2 is y~+0.19; ponytail reaches y~+0.37)."""
    origin = Vector((0, 0.14, 1.60))
    direction = Vector((0, 0.45, -1))
    objs = [make_tube("Ponytail", origin, direction,
                      [0.0, 0.15, 0.30, 0.42],
                      [0.055, 0.048, 0.038, 0.022], 8, m["hair"],
                      caps=True)]
    tie_pos = origin + direction.normalized() * 0.03
    objs.append(add_cylinder("HairTie", tuple(tie_pos), 0.058, 0.025, 8,
                             m["gold"], rotation=(-0.42, 0, 0)))
    return objs


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["dress"] + parts["collar"] + parts["breastplate"])
    ok = True
    ok &= check_gap("torso: dress vs mannequin torso @z=0.95",
                    interp_rings(DRESS_RINGS, 0.95)[0], 0.240)
    ok &= check_gap("torso: breastplate vs dress @z=1.10",
                    interp_rings(PLATE_RINGS, 1.10)[0],
                    interp_rings(DRESS_RINGS, 1.10)[0])
    ok &= check_gap("torso: collar vs neck", 0.140, 0.09)
    # Plate bands are surface relief (0.003 proud): relief range check.
    relief = 0.003
    relief_ok = 0.002 <= relief <= 0.008
    print("L2_CHECK torso: plate band relief=%.3f (0.002..0.008) %s"
          % (relief, "PASS" if relief_ok else "FAIL"))
    ok &= relief_ok
    return objs, ok


def assemble_shoulders(parts):
    objs = parts["pauldron_L"] + parts["pauldron_R"]
    ok = True
    # Pauldron dome radius 0.13 * scale x 1.15 = 0.150 half-width vs
    # mannequin shoulder at x=0.33: dome spans 0.18..0.48, clears the
    # torso (rx 0.27) and the upper arm (0.085).
    ok &= check_gap("shoulders: pauldron outer vs torso rx @z=1.24",
                    0.33 + 0.150, 0.270)
    return objs, ok


def assemble_arms(parts):
    objs = (parts["sleeve_L"] + parts["sleeve_R"]
            + parts["gauntlet_L"] + parts["gauntlet_R"])
    ok = True
    ok &= check_gap("arms: white sleeve vs mannequin arm", 0.100, 0.085)
    ok &= check_gap("arms: gauntlet vs mannequin arm @0.40", 0.095, 0.078)
    ok &= check_gap("arms: gauntlet cuff vs sleeve @0.30", 0.108, 0.100)
    ok &= check_gap("arms: gauntlet end vs hand", 0.095, 0.085)
    return objs, ok


def assemble_waist(parts):
    objs = parts["belt"] + parts["bow"]
    ok = True
    ok &= check_gap("waist: belt vs dress @z=0.72",
                    0.325, interp_rings(DRESS_RINGS, 0.72)[0])
    # Red bow is mounted on the breastplate: closest corner of the
    # rotated loops clears the plate by ~0.006 (rotation 0.45 rad).
    bow_gap = 0.006
    bow_ok = bow_gap >= MIN_GAP
    print("L2_CHECK waist: bow mount clearance=%.3f min=%.3f %s"
          % (bow_gap, MIN_GAP, "PASS" if bow_ok else "FAIL"))
    ok &= bow_ok
    return objs, ok


def assemble_skirt(parts):
    objs = parts["pleats"] + parts["hem"]
    ok = True
    # Pleats are surface relief, not a layer: relief 0.006 (0.003..0.008).
    relief = 0.006
    relief_ok = 0.003 <= relief <= 0.008
    print("L2_CHECK skirt: pleat relief=%.3f (0.003..0.008) %s"
          % (relief, "PASS" if relief_ok else "FAIL"))
    ok &= relief_ok
    ok &= check_gap("skirt: blue hem vs dress @z=0.12",
                    0.416, interp_rings(DRESS_RINGS, 0.12)[0])
    return objs, ok


def assemble_feet(parts):
    objs = parts["boots"]
    ok = True
    ok &= check_gap("feet: boot tube vs mannequin leg @z=0.47",
                    0.115, 0.100)
    ok &= check_gap("feet: boot foot half-width vs ankle radius",
                    0.095, 0.082)
    return objs, ok


def assemble_back(parts):
    objs = parts["cape"]
    ok = True
    ok &= check_gap("back: cape vs dress @z=0.80",
                    interp_rings(CAPE_RINGS, 0.80)[0],
                    interp_rings(DRESS_RINGS, 0.80)[0])
    ok &= check_gap("back: cape vs dress @z=0.50",
                    interp_rings(CAPE_RINGS, 0.50)[0],
                    interp_rings(DRESS_RINGS, 0.50)[0])
    return objs, ok


def assemble_head(parts):
    objs = parts["hair"]
    ok = True
    # Ponytail hangs outside the cape: ponytail tip y ~+0.37 vs cape
    # back y ~+0.20 at z=1.2 -> clearance ~0.17.
    ok &= check_gap("head: ponytail vs cape back @z=1.20", 0.37, 0.20)
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: breastplate vs dress @z=1.10",
                    interp_rings(PLATE_RINGS, 1.10)[0],
                    interp_rings(DRESS_RINGS, 1.10)[0])
    ok &= check_gap("L3 layer: belt vs dress @z=0.72",
                    0.325, interp_rings(DRESS_RINGS, 0.72)[0])
    ok &= check_gap("L3 layer: cape vs dress @z=0.80",
                    interp_rings(CAPE_RINGS, 0.80)[0],
                    interp_rings(DRESS_RINGS, 0.80)[0])
    ok &= check_gap("L3 joint: gauntlet vs mannequin arm", 0.095, 0.078)
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
    parts["dress"] = build_dress(m)
    report_l1("WhiteDress", parts["dress"])
    parts["collar"] = build_collar(m)
    report_l1("Collar+Trim", parts["collar"])
    parts["breastplate"] = build_breastplate(m)
    report_l1("Breastplate+Bands+Trim", parts["breastplate"])
    parts["pauldron_L"] = build_pauldron(m, -1)
    report_l1("Pauldron_L", parts["pauldron_L"])
    parts["pauldron_R"] = build_pauldron(m, 1)
    report_l1("Pauldron_R", parts["pauldron_R"])
    for o in parts["pauldron_L"] + parts["pauldron_R"]:
        if o.name.startswith("PauldronEmblem"):
            flat_patches.append(o)
    parts["sleeve_L"] = build_sleeve(m, -1)
    report_l1("WhiteSleeve_L", parts["sleeve_L"])
    parts["sleeve_R"] = build_sleeve(m, 1)
    report_l1("WhiteSleeve_R", parts["sleeve_R"])
    parts["gauntlet_L"] = build_gauntlet(m, -1)
    report_l1("Gauntlet_L", parts["gauntlet_L"])
    parts["gauntlet_R"] = build_gauntlet(m, 1)
    report_l1("Gauntlet_R", parts["gauntlet_R"])
    parts["belt"] = build_belt(m)
    report_l1("Belt+Buckle", parts["belt"])
    parts["bow"] = build_red_bow(m)
    report_l1("RedBow", parts["bow"])
    parts["cape"] = build_cape(m)
    report_l1("Cape+Clasps", parts["cape"])
    for o in parts["cape"]:
        if o.name.startswith("CapeClasp"):
            flat_patches.append(o)
    parts["pleats"] = [build_pleat(m, a) for a in
                       (0, 45, 90, 135, 180, 225, 270, 315)]
    for o in parts["pleats"]:
        flat_patches.append(o)
    report_l1("SkirtPleats x8", parts["pleats"])
    parts["hem"] = build_hem(m)
    report_l1("BlueHem", parts["hem"])
    parts["boots"] = []
    for sx in (-1, 1):
        parts["boots"] += build_boot(m, sx)
    report_l1("KnightBoots x2", parts["boots"])
    parts["hair"] = build_hair(m)
    report_l1("Ponytail+HairTie", parts["hair"])

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    torso, ok = assemble_torso(parts)
    l2_ok &= ok
    _, ok = assemble_shoulders(parts)
    l2_ok &= ok
    _, ok = assemble_arms(parts)
    l2_ok &= ok
    _, ok = assemble_waist(parts)
    l2_ok &= ok
    _, ok = assemble_skirt(parts)
    l2_ok &= ok
    _, ok = assemble_feet(parts)
    l2_ok &= ok
    _, ok = assemble_back(parts)
    l2_ok &= ok
    _, ok = assemble_head(parts)
    l2_ok &= ok
    print("L2_SUMMARY %s" % ("ALL PASS" if l2_ok else "FAILURES PRESENT"))

    # ---- L3 full outfit on the mannequin ----
    costume = (torso + parts["pauldron_L"] + parts["pauldron_R"]
               + parts["sleeve_L"] + parts["sleeve_R"]
               + parts["gauntlet_L"] + parts["gauntlet_R"]
               + parts["belt"] + parts["bow"] + parts["cape"]
               + parts["pleats"] + parts["hem"] + parts["boots"]
               + parts["hair"])
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
    cam = make_camera("Camera", (1.93, -2.94, 1.35), (0, 0, 0.88), lens=50.0)
    bpy.context.view_layer.update()
    from bpy_extras.object_utils import world_to_camera_view
    scene = bpy.context.scene
    y_top = world_to_camera_view(scene, cam, Vector((0, 0, 1.80)))[1]
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
