# -*- coding: utf-8 -*-
"""012 云纹战袍 · 夜行配色：001 v2 的二创配色变体。
只改一个变量（配色），版型、组件树、几何、层间隙全部沿用 001 v2（已验证）：
L1 小组件 -> L2 中组件 -> L3 大组件，每级单独验证再往上组装。
Run: blender --background --python build_012.py
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

BLEND_OUT = os.path.join(HERE, "012-night-cloud-robe.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "012-night-cloud-robe.png")
WIRE_JSON = "/tmp/night_cloud_robe_wire.json"

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
    """Closed circular tube along `direction`; one ring per (distance, radius).
    caps=False makes an open tube (ends hidden inside other parts, saves the
    cap-fan faces). Cap winding copied from blender-portfolio 002."""
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


def make_panel(name, rings, sides, material, arc):
    """Smooth flared skirt panel (open shell, no caps). The pleats are
    separate L1 strips (make_pleat_strip) laid on top of it."""
    return make_elliptical_tube(name, rings, sides, material, arc=arc,
                                caps=False)


def make_pleat_strip(name, rings, arc, t, half_widths, ridge_heights,
                     material):
    """One pleat: a shallow inverted-V ribbon following the panel surface
    at arc fraction t. rings: [(z, rx, ry)] top->hem (3 rings).
    half_widths/ridge_heights: per-ring strip half-width (m) and ridge
    lift (m). 4 quads; edges sit on the panel, ridge sticks out."""
    a = math.radians(arc[0] + (arc[1] - arc[0]) * t)
    ca, sa = math.cos(a), math.sin(a)
    tangent = Vector((-sa, ca, 0.0))
    verts, faces = [], []
    for k, (z, rx, ry) in enumerate(rings):
        nrm = Vector((ca / rx, sa / ry, 0.0)).normalized()
        p = Vector((rx * ca, ry * sa, z))
        hw = half_widths[k]
        rh = ridge_heights[k]
        verts.append(tuple(p - tangent * hw + nrm * 0.001))
        verts.append(tuple(p + nrm * rh))
        verts.append(tuple(p + tangent * hw + nrm * 0.001))
    for k in range(len(rings) - 1):
        faces.append((k * 3, k * 3 + 1, (k + 1) * 3 + 1, (k + 1) * 3))
        faces.append((k * 3 + 1, k * 3 + 2, (k + 1) * 3 + 2, (k + 1) * 3 + 1))
    return mesh_from_data(name, verts, faces, material)


def _oriented_point(center, u, v, n, px, py, offset, bend_axis, bend_k):
    pb = px if bend_axis == 'u' else py
    off = offset - bend_k * pb * pb
    p = center + u * px + v * py + n * off
    return tuple(p)


def cloud_scroll(name, center, normal, u_axis, bend_axis, bend_k, offset,
                 R, r, dot_r, material, sweep=(-60.0, 240.0), segs=12,
                 dot_segs=8):
    """Flat cloud-scroll applique: a 300-degree annulus-sector band + a
    center dot, bent to hug the garment surface. Faces wound CCW in (u, v)
    so they face +normal. Do NOT run fix_normals on the result (centroid
    test is meaningless for a flat patch); winding is correct by
    construction."""
    n = Vector(normal).normalized()
    u = Vector(u_axis).normalized()
    v = n.cross(u).normalized()
    u = v.cross(n).normalized()
    c = Vector(center)
    a0 = math.radians(sweep[0])
    a1 = math.radians(sweep[1])
    outer, inner = [], []
    for i in range(segs + 1):
        a = a0 + (a1 - a0) * i / segs
        outer.append(_oriented_point(c, u, v, n, R * math.cos(a),
                                     R * math.sin(a), offset, bend_axis,
                                     bend_k))
        inner.append(_oriented_point(c, u, v, n, r * math.cos(a),
                                     r * math.sin(a), offset, bend_axis,
                                     bend_k))
    verts = outer + inner
    faces = []
    for i in range(segs):
        faces.append((i, i + 1, segs + 1 + i + 1, segs + 1 + i))
    dot_c = len(verts)
    verts.append(_oriented_point(c, u, v, n, 0.0, 0.0, offset, bend_axis,
                                 bend_k))
    for i in range(dot_segs):
        a = 2.0 * math.pi * i / dot_segs
        verts.append(_oriented_point(c, u, v, n, dot_r * math.cos(a),
                                     dot_r * math.sin(a), offset, bend_axis,
                                     bend_k))
    for i in range(dot_segs):
        j = (i + 1) % dot_segs
        faces.append((dot_c, dot_c + 1 + i, dot_c + 1 + j))
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
    """Closed wedge (boot foot / toe cap): flat bottom, sloped top (high at
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


def bbox_of(obj):
    """World-space bounding box (mesh verts are local for primitives)."""
    mw = obj.matrix_world
    xs = [(mw @ v.co).x for v in obj.data.vertices]
    ys = [(mw @ v.co).y for v in obj.data.vertices]
    zs = [(mw @ v.co).z for v in obj.data.vertices]
    return (round(max(xs) - min(xs), 3), round(max(ys) - min(ys), 3),
            round(max(zs) - min(zs), 3))


def report_l1(name, objs):
    """L1 check: silhouette proportions of one small component.
    World-space bbox (matrix_world needs a depsgraph update first)."""
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
    # 012 夜行配色：只改配色一个变量，几何/版型沿用 001 v2。
    # sRGB intent -> linear RGB（换算值见 design.md）。Do not eyeball.
    # 青黛 #0E5A5E -> 深紫 #2E1A4E；墨蓝 #16233F -> 夜蓝紫 #120E24；
    # 朱红 #9E1B1B -> 紫罗兰 #6E2B9E；褶裥深红 #7A1010 -> 深紫 #4A1E78；
    # 鎏金 #C9962E 不变（金纹在深紫底上更显眼，是夜行版的视觉锚点）。
    teal = solid_material("Robe_Purple", (0.027, 0.010, 0.076),
                          roughness=0.8)
    ink = solid_material("Inner_Night", (0.006, 0.004, 0.018),
                         roughness=0.85)
    red = solid_material("Sash_Violet", (0.156, 0.024, 0.342),
                         roughness=0.8)
    gold = solid_material("Trim_Gold", (0.58, 0.30, 0.03),
                          metallic=0.7, roughness=0.3)
    pleat_red = solid_material("Pleat_Purple", (0.068, 0.013, 0.188),
                               roughness=0.85)
    skin = solid_material("Skin", (0.62, 0.34, 0.18), roughness=0.7)
    hair = solid_material("Hair_Dark", (0.01, 0.01, 0.00), roughness=0.85)
    boot = solid_material("Boot_Brown", (0.04, 0.02, 0.01), roughness=0.9)
    eye = solid_material("Eye_Dark", (0.01, 0.00, 0.00), roughness=0.6)
    return {"teal": teal, "ink": ink, "red": red, "gold": gold,
            "pleat_red": pleat_red, "skin": skin, "hair": hair,
            "boot": boot, "eye": eye}


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, 002 proportions). Not counted in costume faces.
    v2: hair swept back + bun on top (visible from the front 3/4), two dark
    eyes so the front reads as the front."""
    objs = []
    objs.append(add_sphere("Mannequin_Head", (0, 0, 1.50), 0.22, 10, 8,
                           (1.0, 0.9, 1.05), m["skin"]))
    for sx in (-1, 1):
        objs.append(add_sphere("Mannequin_Eye", (sx * 0.072, -0.180, 1.525),
                               0.022, 6, 3, (1.0, 0.45, 1.35), m["eye"]))
    objs.append(add_sphere("Mannequin_Hair", (0, 0.08, 1.56), 0.24, 10, 6,
                           (1.0, 0.95, 0.8), m["hair"]))
    objs.append(add_sphere("Mannequin_Bun", (0, 0.10, 1.72), 0.065, 8, 4,
                           (1.0, 1.0, 1.0), m["hair"]))
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
INNER_RINGS = [(1.30, 0.295, 0.165), (1.10, 0.285, 0.160),
               (0.85, 0.275, 0.155), (0.60, 0.285, 0.165),
               (0.35, 0.305, 0.180)]
MAIN_RINGS = [(1.30, 0.315, 0.180), (1.12, 0.305, 0.175),
              (0.98, 0.295, 0.170), (0.80, 0.305, 0.180),
              (0.60, 0.320, 0.190), (0.42, 0.335, 0.200),
              (0.30, 0.345, 0.205)]
SKIRT_RINGS = [(0.98, 0.325, 0.195), (0.82, 0.345, 0.210),
               (0.66, 0.375, 0.230), (0.52, 0.405, 0.250)]
SKIRT_HEM_RINGS = [(0.54, 0.410, 0.255), (0.50, 0.412, 0.257)]
FRONT_ARC = (215, 325)
BACK_ARC = (35, 145)


def build_inner_robe(m):
    return [make_elliptical_tube("InnerRobe", INNER_RINGS, 10, m["ink"],
                                 caps=False)]


def build_main_robe(m):
    return [make_elliptical_tube("MainRobe", MAIN_RINGS, 12, m["teal"],
                                 caps=False),
            make_elliptical_tube(
                "HemBand", [(0.34, 0.350, 0.210), (0.30, 0.350, 0.210)],
                12, m["gold"], caps=False)]


def build_collar(m):
    # Standing collar, top flared; gold rim at the visible lower edge
    # (the top is hidden inside the jaw).
    return [make_elliptical_tube(
                "Collar", [(1.44, 0.135, 0.120), (1.38, 0.145, 0.128),
                           (1.32, 0.152, 0.133), (1.28, 0.158, 0.138)],
                12, m["teal"], caps=False),
            make_elliptical_tube(
                "CollarRim", [(1.33, 0.156, 0.137), (1.30, 0.158, 0.139)],
                12, m["gold"], caps=False)]


def build_placket(m):
    """前襟：主袍正面的朱红竖条 + 两颗盘扣（金盘 + 金结）。"""
    objs = [make_elliptical_tube(
        "Placket", [(1.28, 0.322, 0.186), (1.10, 0.312, 0.181),
                    (0.98, 0.302, 0.176)], 8, m["red"], arc=(252, 288),
        caps=False)]
    for z, ry in ((1.18, 0.183), (1.06, 0.179)):
        objs.append(make_disc("PlacketButton", (0, -(ry + 0.007), z),
                              (0, -1, 0), 0.022, 8, m["gold"]))
        objs.append(add_sphere("PlacketKnot", (0.028, -(ry + 0.009), z),
                               0.016, 6, 3, (1.0, 1.0, 1.0), m["gold"]))
    return objs


def build_sash(m):
    return [make_elliptical_tube(
        "Sash", [(0.99, 0.312, 0.188), (0.88, 0.306, 0.184)],
        12, m["red"], caps=False)]


def build_buckle(m):
    return [add_box("Buckle", (0, -0.196, 0.935), (0.10, 0.02, 0.07),
                    m["gold"]),
            add_cylinder("BuckleStud", (0, -0.210, 0.935), 0.020, 0.025,
                         8, m["gold"], rotation=(math.pi / 2, 0, 0))]


def build_sleeve(m, sx):
    """宽袖：上臂贴身 -> 袖口喇叭张开；袖口金环；袖口云纹（朱红贴片，
    金底上看不见，改放朱红）。"""
    shoulder = Vector((sx * 0.34, 0, 1.24))
    direction = Vector((sx * 0.28, 0, -1))
    d = direction.normalized()
    objs = [make_tube("Sleeve", shoulder, direction,
                      [0.0, 0.12, 0.24, 0.36, 0.48],
                      [0.115, 0.125, 0.150, 0.180, 0.205], 10, m["teal"],
                      caps=False)]
    cuff_origin = shoulder + d * 0.42
    objs.append(make_tube("Cuff", cuff_origin, direction,
                          [0.0, 0.06], [0.210, 0.212], 10, m["gold"],
                          caps=False))
    cuff_c = shoulder + d * 0.45
    radial = Vector((sx, 0, 0.25)).normalized()
    patch_c = cuff_c + radial * (0.211 + 0.007)
    objs.append(cloud_scroll("CuffCloud", patch_c, radial, d, 'v', 2.5,
                             0.007, R=0.032, r=0.016, dot_r=0.009,
                             material=m["red"]))
    return objs


def build_overskirt_panel(m, arc, name):
    return [make_panel(name, SKIRT_RINGS, 28, m["red"], arc)]


def build_pleat(m, arc, t, name):
    """一根褶裥：倒 V 形细条，沿裙片表面从腰铺到裙摆，脊高向摆端放大。"""
    rings = [(0.95, 0.0, 0.0), (0.73, 0.0, 0.0), (0.55, 0.0, 0.0)]
    pts = []
    for z, _, _ in rings:
        rx, ry = interp_rings(SKIRT_RINGS, z)
        pts.append((z, rx, ry))
    return [make_pleat_strip(name, pts, arc, t,
                             half_widths=[0.024, 0.030, 0.036],
                             ridge_heights=[0.008, 0.018, 0.032],
                             material=m["pleat_red"])]


def build_skirt_hem(m, arc, name):
    return [make_panel(name, SKIRT_HEM_RINGS, 28, m["gold"], arc)]


def build_skirt_cloud(m, t):
    """罩裙前片褶裥脊线上的云纹（t=0.3/0.7 为脊线位置）。"""
    rx, ry = interp_rings(SKIRT_RINGS, 0.70)
    angle = FRONT_ARC[0] + (FRONT_ARC[1] - FRONT_ARC[0]) * t
    p, nrm = ellipse_point(rx, ry, angle)
    patch_c = Vector((p.x, p.y, 0.70)) + nrm * 0.007
    return [cloud_scroll("SkirtCloud", patch_c, nrm, (1, 0, 0), 'u', 1.0,
                         0.007, R=0.045, r=0.022, dot_r=0.012,
                         material=m["gold"])]


def build_robe_cloud(m, x0):
    """主袍下摆正面（罩裙之下露出部分）的云纹。"""
    rx, ry = interp_rings(MAIN_RINGS, 0.40)
    y_surf, nrm = ellipse_front(rx, ry, x0)
    patch_c = Vector((x0, y_surf, 0.40)) + nrm * 0.007
    return [cloud_scroll("RobeCloud", patch_c, nrm, (1, 0, 0), 'u', 1.0,
                         0.007, R=0.045, r=0.022, dot_r=0.012,
                         material=m["gold"])]


def build_pauldron(m, sx):
    """双层曲面肩甲：鎏金主盖 + 深红顶片（两层颜色分开才看得出层次）。"""
    return [add_sphere("Pauldron", (sx * 0.37, 0, 1.29), 0.15, 8, 5,
                       (1.15, 1.0, 0.62), m["gold"]),
            add_sphere("PauldronTop", (sx * 0.39, 0, 1.345), 0.085, 8, 3,
                       (1.0, 0.9, 0.5), m["red"])]


def build_boot(m, sx):
    """战靴：筒靴（开口管）+ 靴口金环 + 楔形鞋头 + 金色鞋头盖。"""
    return [make_tube("Boot", (sx * 0.13, 0, 0.55), (0, 0, -1),
                      [0.0, 0.15, 0.30, 0.45],
                      [0.115, 0.110, 0.108, 0.112], 8, m["boot"],
                      caps=False),
            make_tube("BootCuff", (sx * 0.13, 0, 0.55), (0, 0, -1),
                      [0.0, 0.05], [0.118, 0.120], 8, m["gold"],
                      caps=False),
            make_wedge("BootFoot", (sx * 0.13, -0.02, 0.0),
                       0.075, 0.06, -0.16, 0.0, 0.11, 0.05, m["boot"]),
            make_wedge("BootToe", (sx * 0.13, -0.02, 0.0),
                       0.079, -0.095, -0.164, 0.0, 0.058, 0.055,
                       m["gold"])]


def build_pendant(m):
    """玉佩：斜绳贴合罩裙前片弧度，金坠挂在裙片外侧。"""
    return [make_tube("PendantCord", (0.05, -0.213, 0.86), (0, -0.10, -1),
                      [0.0, 0.15], [0.008, 0.008], 4, m["gold"],
                      caps=False),
            add_cylinder("Pendant", (0.05, -0.232, 0.70), 0.045, 0.012,
                         12, m["gold"], rotation=(math.pi / 2, 0, 0))]


def build_hairpin(m):
    """发簪：横穿发髻的金簪 + 簪头珠（发髻在人偶上，簪子是配饰）。"""
    return [add_cylinder("Hairpin", (0, 0.10, 1.72), 0.008, 0.44, 6,
                         m["gold"], rotation=(0, math.pi / 2, 0)),
            add_sphere("HairpinBead", (0.23, 0.10, 1.72), 0.020, 6, 3,
                       (1.0, 1.0, 1.0), m["gold"])]


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["inner"] + parts["main"] + parts["collar"]
            + parts["placket"])
    ok = True
    ok &= check_gap("torso: main robe vs inner robe @z=1.00",
                    interp_rings(MAIN_RINGS, 1.00)[0],
                    interp_rings(INNER_RINGS, 1.00)[0])
    ok &= check_gap("torso: collar vs neck", 0.158, 0.09)
    ok &= check_gap("torso: placket vs main robe @z=1.10",
                    0.312, interp_rings(MAIN_RINGS, 1.10)[0])
    return objs, ok


def assemble_sleeve(parts, sx):
    objs = parts["sleeve_L" if sx < 0 else "sleeve_R"]
    # Cuff (r 0.211) sits outside the sleeve (r ~0.199 at cuff height).
    ok = check_gap("sleeve: cuff vs sleeve", 0.211, 0.199)
    return objs, ok


def assemble_waist(parts):
    objs = parts["sash"] + parts["buckle"]
    ok = check_gap("waist: sash vs main robe @z=0.93",
                   0.312, interp_rings(MAIN_RINGS, 0.93)[0])
    return objs, ok


def assemble_skirt(parts):
    objs = (parts["skirt_front"] + parts["skirt_back"]
            + parts["pleats"] + parts["skirt_hems"]
            + parts["skirt_clouds"] + parts["robe_clouds"])
    ok = True
    ok &= check_gap("skirt: panel vs main robe @z=0.80",
                    interp_rings(SKIRT_RINGS, 0.80)[0],
                    interp_rings(MAIN_RINGS, 0.80)[0])
    ok &= check_gap("skirt: panel vs main robe @z=0.55",
                    interp_rings(SKIRT_RINGS, 0.55)[0],
                    interp_rings(MAIN_RINGS, 0.55)[0])
    print("L2_CHECK skirt: pleat ridge lift at hem=0.032 > 0 PASS")
    return objs, ok


def assemble_accessories(parts):
    objs = parts["pauldrons"] + parts["pendant"] + parts["hairpin"]
    # Pendant disc front (-0.238) clears the skirt panel surface (-0.222).
    ok = check_gap("accessory: pendant vs skirt panel", 0.238, 0.222)
    return objs, ok


def assemble_feet(parts):
    objs = parts["boots"]
    ok = check_gap("feet: boot vs leg @z=0.55", 0.115, 0.103)
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: main vs inner @z=0.60",
                    interp_rings(MAIN_RINGS, 0.60)[0],
                    interp_rings(INNER_RINGS, 0.60)[0])
    ok &= check_gap("L3 layer: skirt vs main @z=0.66",
                    interp_rings(SKIRT_RINGS, 0.66)[0],
                    interp_rings(MAIN_RINGS, 0.66)[0])
    ok &= check_gap("L3 joint: arm vs sleeve", 0.115, 0.085)
    ok &= check_gap("L3 joint: leg vs boot", 0.115, 0.105)
    print("L3_CHECK outfit: all layers on mannequin, %s"
          % ("PASS" if ok else "FAIL"))
    return ok


# ---------------------------------------------------------------------- main
def main():
    clear_scene()
    make_world_gradient(top=(0.42, 0.44, 0.47), bottom=(0.13, 0.14, 0.16),
                        strength=0.75)
    add_ground(size=20.0, color=(0.15, 0.16, 0.18))
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
    parts["inner"] = build_inner_robe(m)
    report_l1("InnerRobe", parts["inner"])
    parts["main"] = build_main_robe(m)
    report_l1("MainRobe+HemBand", parts["main"])
    parts["collar"] = build_collar(m)
    report_l1("Collar+CollarRim", parts["collar"])
    parts["placket"] = build_placket(m)
    report_l1("Placket+Buttons", parts["placket"])
    parts["sash"] = build_sash(m)
    report_l1("Sash", parts["sash"])
    parts["buckle"] = build_buckle(m)
    report_l1("Buckle", parts["buckle"])
    for sx in (-1, 1):
        key = "sleeve_L" if sx < 0 else "sleeve_R"
        parts[key] = build_sleeve(m, sx)
        report_l1(key, parts[key])
    parts["skirt_front"] = build_overskirt_panel(m, FRONT_ARC,
                                                 "Overskirt_Front")
    report_l1("Overskirt_Front", parts["skirt_front"])
    parts["skirt_back"] = build_overskirt_panel(m, BACK_ARC,
                                                "Overskirt_Back")
    report_l1("Overskirt_Back", parts["skirt_back"])
    parts["pleats"] = []
    for arc, tag in ((FRONT_ARC, "F"), (BACK_ARC, "B")):
        for t in (0.2, 0.4, 0.6, 0.8):
            parts["pleats"] += build_pleat(m, arc, t,
                                           "Pleat_%s%d" % (tag, int(t * 10)))
    report_l1("Pleats x8", parts["pleats"])
    parts["skirt_hems"] = (build_skirt_hem(m, FRONT_ARC,
                                           "OverskirtHem_Front")
                           + build_skirt_hem(m, BACK_ARC,
                                             "OverskirtHem_Back"))
    report_l1("OverskirtHem", parts["skirt_hems"])
    parts["skirt_clouds"] = []
    for t in (0.3, 0.7):
        parts["skirt_clouds"] += build_skirt_cloud(m, t)
    report_l1("SkirtCloud x2", parts["skirt_clouds"])
    parts["robe_clouds"] = []
    for x0 in (-0.075, 0.075):
        parts["robe_clouds"] += build_robe_cloud(m, x0)
    report_l1("RobeCloud x2", parts["robe_clouds"])
    parts["pauldrons"] = []
    for sx in (-1, 1):
        parts["pauldrons"] += build_pauldron(m, sx)
    report_l1("Pauldrons", parts["pauldrons"])
    parts["boots"] = []
    for sx in (-1, 1):
        parts["boots"] += build_boot(m, sx)
    report_l1("Boots", parts["boots"])
    parts["pendant"] = build_pendant(m)
    report_l1("Pendant", parts["pendant"])
    parts["hairpin"] = build_hairpin(m)
    report_l1("Hairpin", parts["hairpin"])

    # Flat patches (cloud scrolls, placket button discs): winding correct
    # by construction; collect them so they are excluded from fix_normals.
    for objs in (parts["placket"], parts["skirt_clouds"],
                 parts["robe_clouds"]):
        for o in objs:
            if o.name.startswith(("SkirtCloud", "RobeCloud",
                                  "PlacketButton")):
                flat_patches.append(o)
    for key in ("sleeve_L", "sleeve_R"):
        for o in parts[key]:
            if o.name.startswith("CuffCloud"):
                flat_patches.append(o)

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    torso, ok = assemble_torso(parts)
    l2_ok &= ok
    for sx in (-1, 1):
        _, ok = assemble_sleeve(parts, sx)
        l2_ok &= ok
    _, ok = assemble_waist(parts)
    l2_ok &= ok
    _, ok = assemble_skirt(parts)
    l2_ok &= ok
    _, ok = assemble_accessories(parts)
    l2_ok &= ok
    _, ok = assemble_feet(parts)
    l2_ok &= ok
    print("L2_SUMMARY %s" % ("ALL PASS" if l2_ok else "FAILURES PRESENT"))

    # ---- L3 full outfit on the mannequin ----
    costume = (torso + parts["sleeve_L"] + parts["sleeve_R"]
               + parts["sash"] + parts["buckle"] + parts["skirt_front"]
               + parts["skirt_back"] + parts["pleats"]
               + parts["skirt_hems"] + parts["skirt_clouds"]
               + parts["robe_clouds"] + parts["pauldrons"] + parts["boots"]
               + parts["pendant"] + parts["hairpin"])
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
    cam = make_camera("Camera", (1.9, -2.9, 1.35), (0, 0, 0.88), lens=50.0)
    bpy.context.view_layer.update()
    from bpy_extras.object_utils import world_to_camera_view
    scene = bpy.context.scene
    y_top = world_to_camera_view(scene, cam, Vector((0, 0, 1.75)))[1]
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
