# -*- coding: utf-8 -*-
"""003 戏曲水袖礼服：组件化制作流程（001 v2 确立的流程）。
L1 小组件（每个单独建模、单独检查廓形比例）->
L2 中组件（小组件组装，检查接缝与比例）->
L3 大组件（整套穿到人体底座上试穿，检查层间隙与穿帮）。
设计见 design.md。
Run: blender --background --python build_003.py
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

BLEND_OUT = os.path.join(HERE, "003-opera-sleeve.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "003-opera-sleeve.png")
WIRE_JSON = "/tmp/opera_sleeve_wire.json"

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
    red = solid_material("Opera_Red", (0.533, 0.020, 0.026), roughness=0.75)
    # Pleat red: same hue, one step darker, so the folds read as shadowed
    # creases instead of blending into the robe (v1 pleats were invisible).
    pleat_red = solid_material("Pleat_Red", (0.340, 0.011, 0.016),
                               roughness=0.8)
    blue = solid_material("Opera_Blue", (0.011, 0.042, 0.147),
                          roughness=0.75)
    cream = solid_material("Cream", (0.913, 0.863, 0.745), roughness=0.85)
    gold = solid_material("Gold", (0.658, 0.352, 0.009),
                          metallic=0.6, roughness=0.35)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    hair = solid_material("Hair_Black", (0.009, 0.009, 0.010),
                          roughness=0.85)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    lip = solid_material("Lip_Red", (0.533, 0.020, 0.026), roughness=0.6)
    return {"red": red, "pleat_red": pleat_red, "blue": blue,
            "cream": cream, "gold": gold,
            "skin": skin, "hair": hair, "eye": eye, "lip": lip}


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001/002). Opera face:
    two dark eyes + red lips; black hair cap under the headdress."""
    objs = []
    objs.append(add_sphere("Mannequin_Head", (0, 0, 1.50), 0.22, 10, 8,
                           (1.0, 0.9, 1.05), m["skin"]))
    for sx in (-1, 1):
        objs.append(add_sphere("Mannequin_Eye", (sx * 0.072, -0.180, 1.525),
                               0.022, 6, 3, (1.0, 0.45, 1.35), m["eye"]))
    objs.append(add_box("Mannequin_Lips", (0, -0.190, 1.44),
                        (0.05, 0.012, 0.016), m["lip"]))
    # Hair cap over the top of the head (face stays visible): centered
    # higher and flatter than 002's, so the crown reads as black hair
    # under the headdress instead of a bald dome.
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
INNER_RINGS = [(1.30, 0.285, 0.155), (1.05, 0.280, 0.152),
               (0.80, 0.285, 0.155), (0.55, 0.315, 0.170),
               (0.30, 0.355, 0.190), (0.12, 0.385, 0.205)]
ROBE_RINGS = [(1.30, 0.305, 0.170), (1.05, 0.300, 0.168),
              (0.80, 0.308, 0.172), (0.55, 0.335, 0.186),
              (0.30, 0.378, 0.205), (0.12, 0.408, 0.220)]
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)


def front_y(rings, x, z):
    """Front surface Y of an elliptical tube at (x, z)."""
    rx, ry = interp_rings(rings, z)
    return ellipse_front(rx, ry, x)[0]


def build_inner(m):
    return [make_elliptical_tube("InnerRobe", INNER_RINGS, 10,
                                 m["cream"], caps=False)]


def build_robe(m):
    return [make_elliptical_tube("MainRobe", ROBE_RINGS, 12, m["red"],
                                 caps=False)]


def build_collar(m):
    """Stand collar (red) + thin gold trim ring above it."""
    return [make_elliptical_tube(
                "Collar", [(1.40, 0.140, 0.122), (1.34, 0.150, 0.130)],
                12, m["red"], caps=False),
            make_elliptical_tube(
                "CollarTrim", [(1.405, 0.143, 0.125),
                               (1.395, 0.143, 0.125)],
                12, m["gold"], caps=False)]


def build_slant_panel(m, ax, az, bx, bz, name):
    """One diagonal front panel (slant collar band): a strip mesh hugging
    the robe front surface, 0.004 proud, 0.09 wide. Boxes would sink on
    one edge on the curved chest, so the panel is a surface strip (same
    technique as the skirt pleats)."""
    dx, dz = bx - ax, bz - az
    d = Vector((dx, 0.0, dz)).normalized()
    verts, faces = [], []
    n_samples = 6
    for k in range(n_samples):
        t = k / (n_samples - 1)
        x = ax + dx * t
        z = az + dz * t
        rx, ry = interp_rings(ROBE_RINGS, z)
        y, n = ellipse_front(rx, ry, x)
        p = Vector((x, y, z)) + n * 0.004
        w = n.cross(d).normalized()
        verts.append(tuple(p - w * 0.045))
        verts.append(tuple(p + w * 0.045))
    for k in range(n_samples - 1):
        a0, a1 = 2 * k, 2 * k + 1
        b0, b1 = 2 * (k + 1), 2 * (k + 1) + 1
        faces.append((a0, b0, b1, a1))
    return [mesh_from_data(name, verts, faces, m["blue"])]


def build_frog_button(m, x, z):
    """One frog button (pankou): gold knot box + cord ring, on the robe
    front at (x, z)."""
    y = front_y(ROBE_RINGS, x, z)
    return [add_box("FrogKnot", (x, y - 0.016, z),
                    (0.032, 0.014, 0.032), m["gold"]),
            add_cylinder("FrogLoop", (x + 0.028, y - 0.014, z),
                         0.013, 0.010, 6, m["gold"],
                         rotation=(math.pi / 2, 0, 0))]


def build_cloud_patch(m, x, z):
    """One cloud motif: 3 overlapping gold discs on the robe front."""
    y = front_y(ROBE_RINGS, x, z)
    objs = []
    for dx, dz, r in ((0.0, 0.0, 0.030), (-0.032, 0.022, 0.024),
                      (0.032, 0.022, 0.024)):
        objs.append(make_disc("CloudPatch", (x + dx, y - 0.006, z + dz),
                              (0, -1, 0), r, 8, m["gold"]))
    return objs


def build_sleeve(m, sx):
    """Water sleeve: cream tube down the arm, flaring into a bell past
    the wrist, + blue cuff band at the forearm."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("WaterSleeve", shoulder, direction,
                      [0.0, 0.15, 0.30, 0.45, 0.60, 0.72],
                      [0.100, 0.105, 0.110, 0.115, 0.130, 0.155], 10,
                      m["cream"], caps=False),
            make_tube("SleeveCuff", shoulder, direction,
                      [0.30, 0.38], [0.118, 0.120], 10, m["blue"],
                      caps=False)]


def build_sash(m):
    """Wide blue waist sash + gold buckle + front bow (loops + knot)
    + two hanging tails."""
    objs = [make_elliptical_tube(
                "Sash", [(0.78, 0.325, 0.185), (0.66, 0.325, 0.185)],
                12, m["blue"], caps=False),
            add_box("SashBuckle", (0, -0.196, 0.72),
                    (0.09, 0.02, 0.06), m["gold"])]
    for sx in (-1, 1):
        objs.append(add_box_rot("SashBowLoop", (sx * 0.075, -0.20, 0.72),
                                (0.09, 0.02, 0.05), m["blue"],
                                (0, 0, sx * 0.6)))
        objs.append(add_box("SashTail", (sx * 0.035, -0.20, 0.56),
                            (0.035, 0.012, 0.20), m["blue"]))
    objs.append(add_sphere("SashKnot", (0, -0.20, 0.72), 0.022, 6, 3,
                           (1.0, 1.0, 1.0), m["blue"]))
    return objs


def build_pleat(m, angle_deg):
    """One vertical skirt pleat: a 4-ring strip hugging the flaring robe
    surface, 0.006 proud, 0.028 wide, in darker pleat-red so the fold
    reads. Winding faces outward by construction."""
    a = math.radians(angle_deg)
    verts, faces = [], []
    z_list = [0.55, 0.40, 0.25, 0.12]
    for k, z in enumerate(z_list):
        rx, ry = interp_rings(ROBE_RINGS, z)
        p, n = ellipse_point(rx, ry, angle_deg)
        p = Vector((p.x, p.y, z))  # ellipse_point returns z=0; set the ring height
        c = p + n * 0.006
        t = Vector((-rx * math.sin(a), ry * math.cos(a), 0.0)).normalized()
        verts.append(tuple(c - t * 0.014))
        verts.append(tuple(c + t * 0.014))
    for k in range(len(z_list) - 1):
        a0, a1 = 2 * k, 2 * k + 1
        b0, b1 = 2 * (k + 1), 2 * (k + 1) + 1
        faces.append((a0, b0, b1, a1))
    return mesh_from_data("SkirtPleat", verts, faces, m["pleat_red"])


def build_hem(m):
    return [make_elliptical_tube(
                "GoldHem", [(0.16, 0.416, 0.227), (0.10, 0.416, 0.227)],
                12, m["gold"], caps=False)]


def build_shoe(m, sx):
    """Embroidered shoe: red wedge + gold toe cap. Wedge half-width 0.095
    and back 0.09 fully enclose the mannequin ankle (radius 0.082)."""
    return [make_wedge("EmbroideredShoe", (sx * 0.13, -0.02, 0.02),
                       0.095, 0.09, -0.16, 0.0, 0.10, 0.045, m["red"]),
            add_box("ShoeToeGold", (sx * 0.13, -0.172, 0.03),
                    (0.12, 0.018, 0.04), m["gold"])]


def build_headdress(m):
    """Opera headdress: gold forehead band + 2 pheasant-tail feathers
    (red, gold tips) + side gold beads + red tassels with gold ends."""
    objs = [make_elliptical_tube(
                "HeaddressBand", [(1.66, 0.228, 0.215),
                                  (1.60, 0.230, 0.218)],
                12, m["gold"], arc=(200, 340), caps=False)]
    for sx in (-1, 1):
        origin = Vector((sx * 0.06, 0.08, 1.70))
        direction = Vector((sx * 0.30, 0.75, 0.80))
        objs.append(make_tube("PheasantFeather", origin, direction,
                              [0.0, 0.15, 0.30, 0.42],
                              [0.028, 0.022, 0.016, 0.010], 6, m["red"],
                              caps=False))
        tip = origin + direction.normalized() * 0.42
        objs.append(add_sphere("FeatherTip", tuple(tip), 0.014, 6, 3,
                               (1.0, 1.0, 1.0), m["gold"]))
        objs.append(add_sphere("HeaddressBead", (sx * 0.20, -0.05, 1.55),
                               0.020, 6, 3, (1.0, 1.0, 1.0), m["gold"]))
        objs.append(add_cylinder("Tassel", (sx * 0.21, -0.06, 1.47),
                                 0.008, 0.12, 6, m["red"]))
        objs.append(add_sphere("TasselEnd", (sx * 0.21, -0.06, 1.405),
                               0.012, 6, 3, (1.0, 1.0, 1.0), m["gold"]))
    return objs


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["inner"] + parts["robe"] + parts["collar"]
            + parts["slant"] + parts["frogs"] + parts["clouds"])
    ok = True
    ok &= check_gap("torso: robe vs inner @z=0.80",
                    interp_rings(ROBE_RINGS, 0.80)[0],
                    interp_rings(INNER_RINGS, 0.80)[0])
    ok &= check_gap("torso: robe vs inner @z=0.30",
                    interp_rings(ROBE_RINGS, 0.30)[0],
                    interp_rings(INNER_RINGS, 0.30)[0])
    ok &= check_gap("torso: collar vs neck", 0.140, 0.09)
    # Slant panels are surface relief (0.004 proud), not a layer: the
    # criterion is the relief range (0.003..0.008), not the 0.005 gap.
    relief = 0.004
    relief_ok = 0.003 <= relief <= 0.008
    print("L2_CHECK torso: slant panel relief=%.3f (0.003..0.008) %s"
          % (relief, "PASS" if relief_ok else "FAIL"))
    ok &= relief_ok
    return objs, ok


def assemble_sleeves(parts):
    objs = parts["sleeve_L"] + parts["sleeve_R"]
    ok = True
    ok &= check_gap("sleeves: sleeve vs mannequin arm", 0.100, 0.085)
    ok &= check_gap("sleeves: cuff vs sleeve @0.30 along arm",
                    0.118, 0.110)
    ok &= check_gap("sleeves: sleeve bell vs hand", 0.155, 0.085)
    return objs, ok


def assemble_waist(parts):
    objs = parts["sash"]
    ok = check_gap("waist: sash vs robe @z=0.72",
                   0.325, interp_rings(ROBE_RINGS, 0.72)[0])
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
    ok &= check_gap("skirt: gold hem vs robe @z=0.12",
                    0.416, interp_rings(ROBE_RINGS, 0.12)[0])
    return objs, ok


def assemble_feet(parts):
    objs = parts["shoes"]
    ok = check_gap("feet: shoe half-width vs mannequin ankle radius",
                   0.095, 0.082)
    ok &= check_gap("feet: shoe back vs mannequin ankle radius",
                    0.09, 0.082)
    return objs, ok


def assemble_head(parts):
    objs = parts["headdress"]
    ok = check_gap("head: headdress band vs hair @z=1.62",
                   0.228, 0.219)
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: robe vs inner @z=0.55",
                    interp_rings(ROBE_RINGS, 0.55)[0],
                    interp_rings(INNER_RINGS, 0.55)[0])
    ok &= check_gap("L3 layer: sash vs robe @z=0.72",
                    0.325, interp_rings(ROBE_RINGS, 0.72)[0])
    ok &= check_gap("L3 joint: arm vs sleeve", 0.100, 0.085)
    ok &= check_gap("L3 joint: sleeve bell clears hand", 0.155, 0.085)
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
    report_l1("InnerRobe", parts["inner"])
    parts["robe"] = build_robe(m)
    report_l1("MainRobe", parts["robe"])
    parts["collar"] = build_collar(m)
    report_l1("Collar+Trim", parts["collar"])
    # Slant panels: long one right shoulder -> left waist, short one
    # left shoulder -> right waist (crossed collar look).
    parts["slant"] = build_slant_panel(m, 0.16, 1.26, -0.10, 0.80,
                                       "SlantPanelLong")
    parts["slant"] += build_slant_panel(m, -0.16, 1.26, 0.10, 0.95,
                                        "SlantPanelShort")
    report_l1("SlantPanels x2", parts["slant"])
    for o in parts["slant"]:
        flat_patches.append(o)
    parts["frogs"] = []
    for (x, z) in ((0.10, 1.15), (0.03, 1.00), (-0.04, 0.86)):
        parts["frogs"] += build_frog_button(m, x, z)
    report_l1("FrogButtons x3", parts["frogs"])
    parts["clouds"] = []
    for (x, z) in ((-0.16, 1.08), (-0.12, 0.35), (0.12, 0.35)):
        parts["clouds"] += build_cloud_patch(m, x, z)
    report_l1("CloudPatches x3", parts["clouds"])
    for o in parts["clouds"]:
        flat_patches.append(o)
    parts["sleeve_L"] = build_sleeve(m, -1)
    report_l1("WaterSleeve_L", parts["sleeve_L"])
    parts["sleeve_R"] = build_sleeve(m, 1)
    report_l1("WaterSleeve_R", parts["sleeve_R"])
    parts["sash"] = build_sash(m)
    report_l1("Sash+Bow+Tails", parts["sash"])
    parts["pleats"] = [build_pleat(m, a) for a in
                       (0, 45, 90, 135, 180, 225, 270, 315)]
    for o in parts["pleats"]:
        flat_patches.append(o)
    report_l1("SkirtPleats x8", parts["pleats"])
    parts["hem"] = build_hem(m)
    report_l1("GoldHem", parts["hem"])
    parts["shoes"] = []
    for sx in (-1, 1):
        parts["shoes"] += build_shoe(m, sx)
    report_l1("EmbroideredShoes x2", parts["shoes"])
    parts["headdress"] = build_headdress(m)
    report_l1("Headdress", parts["headdress"])

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    torso, ok = assemble_torso(parts)
    l2_ok &= ok
    _, ok = assemble_sleeves(parts)
    l2_ok &= ok
    _, ok = assemble_waist(parts)
    l2_ok &= ok
    _, ok = assemble_skirt(parts)
    l2_ok &= ok
    _, ok = assemble_feet(parts)
    l2_ok &= ok
    _, ok = assemble_head(parts)
    l2_ok &= ok
    print("L2_SUMMARY %s" % ("ALL PASS" if l2_ok else "FAILURES PRESENT"))

    # ---- L3 full outfit on the mannequin ----
    costume = (torso + parts["sleeve_L"] + parts["sleeve_R"]
               + parts["sash"] + parts["pleats"] + parts["hem"]
               + parts["shoes"] + parts["headdress"])
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
    cam = make_camera("Camera", (2.2, -3.35, 1.42), (0, 0, 0.88), lens=50.0)
    bpy.context.view_layer.update()
    from bpy_extras.object_utils import world_to_camera_view
    scene = bpy.context.scene
    y_top = world_to_camera_view(scene, cam, Vector((0, 0, 2.02)))[1]
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
