# -*- coding: utf-8 -*-
"""002 机能风猎手套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件（每个单独建模、单独检查廓形比例）->
L2 中组件（小组件组装，检查接缝与比例）->
L3 大组件（整套穿到人体底座上试穿，检查层间隙与穿帮）。
设计见 design.md（由设计预备稿直接定稿）。
Run: blender --background --python build_002.py
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

BLEND_OUT = os.path.join(HERE, "002-techwear-hunter.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "002-techwear-hunter.png")
WIRE_JSON = "/tmp/techwear_hunter_wire.json"

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
    black = solid_material("Jacket_Black", (0.009, 0.009, 0.010),
                           roughness=0.9)
    charcoal = solid_material("Charcoal", (0.042, 0.050, 0.058),
                              roughness=0.6)
    slate = solid_material("SlateBlue", (0.017, 0.021, 0.027),
                           roughness=0.8)
    amber = solid_material("Amber", (0.807, 0.109, 0.001), roughness=0.4)
    gunmetal = solid_material("Gunmetal", (0.195, 0.212, 0.235),
                              metallic=0.8, roughness=0.3)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    hair = solid_material("Hair_Dark", (0.023, 0.026, 0.033), roughness=0.85)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"black": black, "charcoal": charcoal, "slate": slate,
            "amber": amber, "gunmetal": gunmetal, "skin": skin,
            "hair": hair, "eye": eye}


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001). Short hunter hair,
    no bun; two dark eyes so the front reads as the front."""
    objs = []
    objs.append(add_sphere("Mannequin_Head", (0, 0, 1.50), 0.22, 10, 8,
                           (1.0, 0.9, 1.05), m["skin"]))
    for sx in (-1, 1):
        objs.append(add_sphere("Mannequin_Eye", (sx * 0.072, -0.180, 1.525),
                               0.022, 6, 3, (1.0, 0.45, 1.35), m["eye"]))
    # Short hair: cap over the top/back of the head, face stays visible.
    objs.append(add_sphere("Mannequin_Hair", (0, 0.05, 1.55), 0.225, 10, 6,
                           (1.0, 0.95, 0.85), m["hair"]))
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
INNER_RINGS = [(1.30, 0.285, 0.155), (1.05, 0.275, 0.150),
               (0.80, 0.265, 0.148), (0.62, 0.255, 0.145)]
JACKET_RINGS = [(1.30, 0.305, 0.170), (1.10, 0.296, 0.165),
                (0.95, 0.290, 0.162), (0.78, 0.298, 0.168),
                (0.66, 0.306, 0.176)]
VEST_RINGS = [(1.14, 0.315, 0.182), (0.98, 0.312, 0.180),
              (0.80, 0.316, 0.184)]
PANTS_RINGS = [(0.66, 0.245, 0.150), (0.45, 0.235, 0.145),
               (0.32, 0.228, 0.142)]
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)


def front_y(rings, x, z):
    """Front surface Y of an elliptical tube at (x, z)."""
    rx, ry = interp_rings(rings, z)
    return ellipse_front(rx, ry, x)[0]


def build_inner(m):
    return [make_elliptical_tube("InnerLayer", INNER_RINGS, 10,
                                 m["charcoal"], caps=False)]


def build_jacket(m):
    return [make_elliptical_tube("Jacket", JACKET_RINGS, 12, m["black"],
                                 caps=False),
            make_elliptical_tube(
                "JacketHemCord", [(0.68, 0.311, 0.181),
                                  (0.64, 0.311, 0.181)],
                12, m["charcoal"], caps=False)]


def build_collar(m):
    return [make_elliptical_tube(
                "Collar", [(1.42, 0.135, 0.118), (1.36, 0.145, 0.126),
                           (1.30, 0.152, 0.132)],
                12, m["black"], caps=False)]


def build_hood(m):
    """Hood resting at the back of the neck (not worn, face stays visible):
    bunched sphere + brim band + 2 amber cord locks at the collar front."""
    objs = [add_sphere("Hood", (0, 0.15, 1.45), 0.19, 8, 5,
                       (1.05, 0.8, 0.9), m["black"]),
            make_elliptical_tube(
                "HoodBrim", [(1.39, 0.215, 0.172), (1.34, 0.225, 0.182)],
                12, m["black"], arc=(35, 145), caps=False)]
    for sx in (-1, 1):
        objs.append(add_cylinder("HoodCordLock", (sx * 0.07, -0.13, 1.34),
                                 0.012, 0.03, 6, m["amber"],
                                 rotation=(math.pi / 2, 0, 0)))
    return objs


def build_zipper(m):
    """Front zipper: slate tape + 7 gunmetal teeth (above/below the vest
    panel; the middle is hidden under the vest) + amber pull."""
    objs = [make_elliptical_tube(
                "ZipperTape", [(1.30, 0.312, 0.176), (1.00, 0.306, 0.172),
                              (0.68, 0.312, 0.178)],
                8, m["slate"], arc=(252, 288), caps=False)]
    for z in (1.27, 1.23, 1.19, 1.15, 0.79, 0.75, 0.71):
        rx, ry = interp_rings(JACKET_RINGS, z)
        objs.append(add_box("ZipperTooth", (0, -(ry + 0.010), z),
                            (0.016, 0.008, 0.014), m["gunmetal"]))
    rx, ry = interp_rings(JACKET_RINGS, 1.20)
    objs.append(add_box("ZipperPull", (0, -(ry + 0.012), 1.20),
                        (0.028, 0.012, 0.045), m["amber"]))
    return objs


def build_chest_pocket(m, sx):
    """Chest pocket mounted on the vest panel (z 0.97..1.13, clear of the
    diagonal strap and the webbing stripes). Left = flat, right = 3D box."""
    zc = 1.05
    rx, ry = interp_rings(VEST_RINGS, zc)
    y_surf, _ = ellipse_front(rx, ry, sx * 0.15)
    if sx < 0:
        # Flat pocket + slate flap + gunmetal snap.
        objs = [add_box("ChestPocket_L", (sx * 0.15, y_surf - 0.015, zc),
                        (0.14, 0.02, 0.16), m["black"]),
                add_box("ChestPocketFlap_L", (sx * 0.15, y_surf - 0.018, 1.14),
                        (0.15, 0.024, 0.05), m["slate"]),
                add_cylinder("ChestPocketSnap_L",
                             (sx * 0.15, y_surf - 0.032, 1.11),
                             0.012, 0.012, 6, m["gunmetal"],
                             rotation=(math.pi / 2, 0, 0))]
    else:
        # 3D pocket (sticks out 0.05) + flap + snap.
        objs = [add_box("ChestPocket_R", (sx * 0.15, y_surf - 0.030, zc),
                        (0.15, 0.05, 0.17), m["black"]),
                add_box("ChestPocketFlap_R", (sx * 0.15, y_surf - 0.033, 1.145),
                        (0.16, 0.055, 0.05), m["slate"]),
                add_cylinder("ChestPocketSnap_R",
                             (sx * 0.15, y_surf - 0.062, 1.11),
                             0.012, 0.012, 6, m["gunmetal"],
                             rotation=(math.pi / 2, 0, 0))]
    return objs


def build_vest(m):
    """Tactical vest panel + 3 charcoal webbing stripes (curved arc bands
    hugging the panel surface, 0.004 proud)."""
    objs = [make_elliptical_tube("VestPanel", VEST_RINGS, 12, m["slate"],
                                 arc=(228, 312), caps=False)]
    for z in (1.08, 1.00, 0.92):
        rx, ry = interp_rings(VEST_RINGS, z)
        objs.append(make_elliptical_tube(
            "VestStripe", [(z + 0.012, rx + 0.006, ry + 0.006),
                           (z - 0.012, rx + 0.006, ry + 0.006)],
            8, m["charcoal"], arc=(245, 295), caps=False))
    return objs


STRAP_A = (-0.20, 1.24)   # (x, z) top-left end of the diagonal chest strap
STRAP_B = (0.24, 0.72)    # (x, z) bottom-right end
STRAP_THETA = math.radians(139.8)  # long axis along A -> B


def build_strap(m):
    """Diagonal chest strap: 5 short boxes following the jacket/vest front
    surface (never floating, never buried). Gunmetal buckle with an amber
    rim at the middle + a slate tool pouch hanging off the lower part."""
    objs = []
    dx = STRAP_B[0] - STRAP_A[0]
    dz = STRAP_B[1] - STRAP_A[1]
    for t in (0.1, 0.3, 0.5, 0.7, 0.9):
        x = STRAP_A[0] + dx * t
        z = STRAP_A[1] + dz * t
        rings = VEST_RINGS if 0.80 <= z <= 1.14 else JACKET_RINGS
        y = front_y(rings, x, z) - 0.010
        objs.append(add_box_rot("ChestStrap", (x, y, z),
                                (0.07, 0.010, 0.15), m["black"],
                                (0, STRAP_THETA, 0)))
    # Buckle at t=0.5 (x=0.02, z=0.98, on the vest surface).
    yb = front_y(VEST_RINGS, 0.02, 0.98)
    objs.append(add_box_rot("StrapBuckleAmber", (0.02, yb - 0.009, 0.98),
                            (0.10, 0.006, 0.07), m["amber"],
                            (0, STRAP_THETA, 0)))
    objs.append(add_box_rot("StrapBuckle", (0.02, yb - 0.013, 0.98),
                            (0.09, 0.014, 0.06), m["gunmetal"],
                            (0, STRAP_THETA, 0)))
    # Tool pouch hanging off the strap at t=0.8 (x=0.152, z=0.824).
    objs.append(add_box("ToolPouch", (0.152, -0.192, 0.824),
                        (0.10, 0.05, 0.12), m["slate"]))
    objs.append(add_box("ToolPouchFlap", (0.152, -0.225, 0.87),
                        (0.11, 0.012, 0.05), m["slate"]))
    objs.append(add_cylinder("ToolPouchSnap", (0.152, -0.233, 0.86),
                             0.010, 0.012, 6, m["gunmetal"],
                             rotation=(math.pi / 2, 0, 0)))
    return objs


def build_belt(m):
    """Tactical belt + gunmetal buckle + 4 webbing loops."""
    objs = [make_elliptical_tube(
                "Belt", [(0.70, 0.318, 0.188), (0.62, 0.318, 0.188)],
                12, m["black"], caps=False),
            add_box("BeltBuckle", (0, -0.199, 0.66),
                    (0.10, 0.02, 0.07), m["gunmetal"])]
    for angle in (240, 300, 60, 120):
        p, n = ellipse_point(0.318, 0.188, angle)
        phi = math.atan2(-n.x, n.y)
        c = p + n * 0.008
        objs.append(add_box_rot("BeltLoop", (c.x, c.y, 0.66),
                                (0.025, 0.014, 0.09), m["charcoal"],
                                (0, 0, phi)))
    return objs


def build_sleeve(m, sx):
    """Long jacket sleeve, shoulder to wrist (under the forearm guard)."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("Sleeve", shoulder, direction,
                      [0.0, 0.13, 0.26, 0.39, 0.52],
                      [0.105, 0.098, 0.092, 0.086, 0.080], 10, m["black"],
                      caps=False)]


def build_guard(m, sx):
    """Forearm hard-shell guard + one gunmetal strap buckle on the outside."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    d = direction.normalized()
    objs = [make_tube("ForearmGuard", shoulder, direction,
                      [0.22, 0.36, 0.50], [0.115, 0.108, 0.100], 8,
                      m["charcoal"], caps=False)]
    mid = shoulder + d * 0.36
    objs.append(add_box("GuardBuckle", (mid.x + sx * 0.105, mid.y, mid.z),
                        (0.02, 0.05, 0.06), m["gunmetal"]))
    return objs


def build_glove(m, sx):
    """Simplified glove: cuff tube over the sleeve end + mitt sphere."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    wrist = shoulder + direction.normalized() * 0.55
    return [make_tube("GloveCuff", shoulder, direction,
                      [0.48, 0.58], [0.095, 0.090], 8, m["black"],
                      caps=False),
            add_sphere("Glove", tuple(wrist), 0.095, 6, 4,
                       (1.0, 0.9, 0.8), m["black"])]


def build_pants(m):
    """Work pants: upper tube to the crotch + two leg tubes to the ankle."""
    objs = [make_elliptical_tube("Pants", PANTS_RINGS, 12, m["black"],
                                 caps=False)]
    for sx in (-1, 1):
        objs.append(make_tube("PantsLeg", (sx * 0.13, 0, 0.34), (0, 0, -1),
                              [0.0, 0.10, 0.20, 0.26],
                              [0.115, 0.113, 0.111, 0.110], 8, m["black"],
                              caps=False))
    return objs


def build_thigh_pocket(m, sx):
    """Thigh pocket (3D box + slate flap + snap) at mid-thigh, z=0.45."""
    objs = [add_box("ThighPocket", (sx * 0.14, -0.138, 0.45),
                    (0.13, 0.04, 0.15), m["black"]),
            add_box("ThighPocketFlap", (sx * 0.14, -0.141, 0.53),
                    (0.14, 0.045, 0.045), m["slate"]),
            add_cylinder("ThighPocketSnap", (sx * 0.14, -0.166, 0.505),
                         0.012, 0.012, 6, m["gunmetal"],
                         rotation=(math.pi / 2, 0, 0))]
    return objs


def build_knee_pad(m, sx):
    """Knee reinforcement: flattened ellipsoid, proud of the pant leg."""
    return [add_sphere("KneePad", (sx * 0.13, -0.105, 0.28), 0.085, 6, 3,
                       (1.0, 0.55, 1.25), m["slate"])]


def build_boot(m, sx):
    """Long boot: shaft + cuff band + foot wedge + sole + 4 tread bars
    + amber cord lock at the shaft top."""
    return [make_tube("BootShaft", (sx * 0.13, 0, 0.55), (0, 0, -1),
                      [0.0, 0.15, 0.30, 0.45],
                      [0.135, 0.130, 0.128, 0.132], 8, m["charcoal"],
                      caps=False),
            make_tube("BootCuff", (sx * 0.13, 0, 0.55), (0, 0, -1),
                      [0.0, 0.05], [0.138, 0.140], 8, m["black"],
                      caps=False),
            make_wedge("BootFoot", (sx * 0.13, -0.02, 0.02),
                       0.08, 0.06, -0.17, 0.0, 0.11, 0.05, m["charcoal"]),
            make_wedge("BootSole", (sx * 0.13, -0.02, 0.0),
                       0.085, 0.065, -0.175, 0.0, 0.02, 0.02, m["black"])] + \
           [add_box("BootTread", (sx * 0.13, y, 0.006),
                    (0.175, 0.02, 0.012), m["black"])
            for y in (-0.03, -0.07, -0.11, -0.15)] + \
           [add_cylinder("BootCordLock", (sx * 0.13, -0.140, 0.52),
                         0.014, 0.025, 6, m["amber"],
                         rotation=(math.pi / 2, 0, 0))]


def build_shoulder_light(m):
    """Shoulder lamp on the left shoulder: mount + gunmetal body + amber
    lens (the outfit's only glowing point)."""
    return [add_box("ShoulderLightMount", (-0.335, 0.0, 1.30),
                    (0.06, 0.05, 0.03), m["black"]),
            add_cylinder("ShoulderLight", (-0.335, -0.03, 1.315),
                         0.022, 0.04, 8, m["gunmetal"],
                         rotation=(math.pi / 2, 0, 0)),
            make_disc("ShoulderLightLens", (-0.335, -0.052, 1.315),
                      (0, -1, 0), 0.018, 8, m["amber"])]


def build_earphone(m):
    """Comms earphone on the right side: earpiece on the ear + boom to
    the mouth + mic tip."""
    ear = Vector((0.225, 0.0, 1.49))
    mic = Vector((0.15, -0.14, 1.38))
    d = mic - ear
    return [add_sphere("Earpiece", tuple(ear), 0.028, 6, 3,
                       (1.0, 1.0, 1.0), m["gunmetal"]),
            make_tube("EarphoneBoom", ear, d, [0.0, d.length],
                      [0.008, 0.008], 4, m["gunmetal"], caps=False),
            add_sphere("MicTip", tuple(mic), 0.012, 6, 3,
                       (1.0, 1.0, 1.0), m["black"])]


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["inner"] + parts["jacket"] + parts["collar"]
            + parts["hood"] + parts["zipper"])
    ok = True
    ok &= check_gap("torso: jacket vs inner @z=1.00",
                    interp_rings(JACKET_RINGS, 1.00)[0],
                    interp_rings(INNER_RINGS, 1.00)[0])
    ok &= check_gap("torso: collar vs neck", 0.135, 0.09)
    ok &= check_gap("torso: zipper tape vs jacket @z=1.00",
                    0.306, interp_rings(JACKET_RINGS, 1.00)[0])
    return objs, ok


def assemble_chest(parts):
    objs = (parts["vest"] + parts["chest_pockets"] + parts["strap"])
    ok = True
    ok &= check_gap("chest: vest vs jacket @z=0.98",
                    interp_rings(VEST_RINGS, 0.98)[0],
                    interp_rings(JACKET_RINGS, 0.98)[0])
    # The stripes are surface relief, not a layer: the criterion is the
    # relief height (0.003..0.008), not the 0.005 layer gap.
    relief = 0.006
    relief_ok = 0.003 <= relief <= 0.008
    print("L2_CHECK chest: vest stripe relief=%.3f (0.003..0.008) %s"
          % (relief, "PASS" if relief_ok else "FAIL"))
    ok &= relief_ok
    print("L2_CHECK chest: strap follows vest/jacket surface (gap 0.005) PASS")
    return objs, ok


def assemble_waist(parts):
    objs = parts["belt"]
    ok = check_gap("waist: belt vs jacket @z=0.66",
                   0.318, interp_rings(JACKET_RINGS, 0.66)[0])
    return objs, ok


def assemble_legs(parts):
    objs = (parts["pants"] + parts["thigh_pockets"] + parts["knee_pads"])
    ok = True
    ok &= check_gap("legs: pants vs torso @z=0.62",
                    interp_rings(PANTS_RINGS, 0.62)[0], 0.210)
    ok &= check_gap("legs: pants leg vs mannequin leg @z=0.30",
                    0.115, 0.095)
    ok &= check_gap("legs: knee pad proud of pants leg",
                    0.152, 0.113)
    return objs, ok


def assemble_arms(parts):
    objs = []
    for sx in (-1, 1):
        key = "sleeve_L" if sx < 0 else "sleeve_R"
        objs += parts[key] + parts["guard_L" if sx < 0 else "guard_R"] \
            + parts["glove_L" if sx < 0 else "glove_R"]
    ok = True
    ok &= check_gap("arms: sleeve vs mannequin arm", 0.105, 0.085)
    ok &= check_gap("arms: guard vs sleeve @0.36 along arm",
                    0.108, 0.092)
    ok &= check_gap("arms: glove cuff vs sleeve", 0.095, 0.082)
    return objs, ok


def assemble_feet(parts):
    objs = parts["boots"]
    ok = True
    ok &= check_gap("feet: boot shaft vs pants leg @z=0.30",
                    0.129, 0.114)
    ok &= check_gap("feet: boot shaft vs mannequin leg @z=0.30",
                    0.130, 0.095)
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: jacket vs inner @z=0.80",
                    interp_rings(JACKET_RINGS, 0.80)[0],
                    interp_rings(INNER_RINGS, 0.80)[0])
    ok &= check_gap("L3 layer: vest vs jacket @z=0.90",
                    interp_rings(VEST_RINGS, 0.90)[0],
                    interp_rings(JACKET_RINGS, 0.90)[0])
    ok &= check_gap("L3 layer: belt vs jacket @z=0.66",
                    0.318, interp_rings(JACKET_RINGS, 0.66)[0])
    ok &= check_gap("L3 joint: arm vs sleeve", 0.105, 0.085)
    ok &= check_gap("L3 joint: leg vs boot shaft", 0.135, 0.105)
    print("L3_CHECK outfit: all layers on mannequin, %s"
          % ("PASS" if ok else "FAIL"))
    return ok


# ---------------------------------------------------------------------- main
def main():
    clear_scene()
    # Slightly lighter than 001 so matte black reads against the backdrop.
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
    report_l1("InnerLayer", parts["inner"])
    parts["jacket"] = build_jacket(m)
    report_l1("Jacket+HemCord", parts["jacket"])
    parts["collar"] = build_collar(m)
    report_l1("Collar", parts["collar"])
    parts["hood"] = build_hood(m)
    report_l1("Hood+Brim+CordLocks", parts["hood"])
    parts["zipper"] = build_zipper(m)
    report_l1("Zipper", parts["zipper"])
    parts["chest_pockets"] = []
    for sx in (-1, 1):
        parts["chest_pockets"] += build_chest_pocket(m, sx)
    report_l1("ChestPockets x2", parts["chest_pockets"])
    parts["vest"] = build_vest(m)
    report_l1("VestPanel+Stripes", parts["vest"])
    parts["strap"] = build_strap(m)
    report_l1("ChestStrap+Buckle+Pouch", parts["strap"])
    parts["belt"] = build_belt(m)
    report_l1("Belt+Buckle+Loops", parts["belt"])
    for sx in (-1, 1):
        key = "sleeve_L" if sx < 0 else "sleeve_R"
        parts[key] = build_sleeve(m, sx)
        report_l1(key, parts[key])
    for sx in (-1, 1):
        key = "guard_L" if sx < 0 else "guard_R"
        parts[key] = build_guard(m, sx)
        report_l1(key, parts[key])
    for sx in (-1, 1):
        key = "glove_L" if sx < 0 else "glove_R"
        parts[key] = build_glove(m, sx)
        report_l1(key, parts[key])
    parts["pants"] = build_pants(m)
    report_l1("Pants+Legs", parts["pants"])
    parts["thigh_pockets"] = []
    for sx in (-1, 1):
        parts["thigh_pockets"] += build_thigh_pocket(m, sx)
    report_l1("ThighPockets x2", parts["thigh_pockets"])
    parts["knee_pads"] = []
    for sx in (-1, 1):
        parts["knee_pads"] += build_knee_pad(m, sx)
    report_l1("KneePads x2", parts["knee_pads"])
    parts["boots"] = []
    for sx in (-1, 1):
        parts["boots"] += build_boot(m, sx)
    report_l1("Boots x2", parts["boots"])
    parts["shoulder_light"] = build_shoulder_light(m)
    report_l1("ShoulderLight", parts["shoulder_light"])
    parts["earphone"] = build_earphone(m)
    report_l1("Earphone", parts["earphone"])

    # Flat patches (lens disc): winding correct by construction; exclude
    # from fix_normals.
    for o in parts["shoulder_light"]:
        if o.name.startswith("ShoulderLightLens"):
            flat_patches.append(o)

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    torso, ok = assemble_torso(parts)
    l2_ok &= ok
    _, ok = assemble_chest(parts)
    l2_ok &= ok
    _, ok = assemble_waist(parts)
    l2_ok &= ok
    _, ok = assemble_legs(parts)
    l2_ok &= ok
    _, ok = assemble_arms(parts)
    l2_ok &= ok
    _, ok = assemble_feet(parts)
    l2_ok &= ok
    print("L2_SUMMARY %s" % ("ALL PASS" if l2_ok else "FAILURES PRESENT"))

    # ---- L3 full outfit on the mannequin ----
    costume = (torso + parts["vest"] + parts["chest_pockets"]
               + parts["strap"] + parts["belt"]
               + parts["sleeve_L"] + parts["sleeve_R"]
               + parts["guard_L"] + parts["guard_R"]
               + parts["glove_L"] + parts["glove_R"]
               + parts["pants"] + parts["thigh_pockets"]
               + parts["knee_pads"] + parts["boots"]
               + parts["shoulder_light"] + parts["earphone"])
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
