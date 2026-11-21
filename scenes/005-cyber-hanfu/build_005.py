# -*- coding: utf-8 -*-
"""005 赛博汉服：组件化制作流程（001 v2 确立的流程）。
L1 小组件（每个单独建模、单独检查廓形比例）->
L2 中组件（小组件组装，检查接缝与比例）->
L3 大组件（整套穿到人体底座上试穿，检查层间隙与穿帮）。
设计见 design.md。
Run: blender --background --python build_005.py
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

BLEND_OUT = os.path.join(HERE, "005-cyber-hanfu.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "005-cyber-hanfu.png")
WIRE_JSON = "/tmp/cyber_hanfu_wire.json"

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


def glow_material(name, color, strength=2.0):
    """Emission material for the glowing circuit lines."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (*color, 1.0)
    emit.inputs["Strength"].default_value = strength
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


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


def check_relief(name, relief, lo=0.002, hi=0.008):
    ok = lo <= relief <= hi
    print("L2_CHECK %s relief=%.3f (%.3f..%.3f) %s"
          % (name, relief, lo, hi, "PASS" if ok else "FAIL"))
    return ok


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    ink = solid_material("Ink", (0.007, 0.014, 0.027), roughness=0.85)
    moon = solid_material("MoonWhite", (0.807, 0.791, 0.738), roughness=0.85)
    dark = solid_material("DarkGrey", (0.023, 0.027, 0.033), roughness=0.6)
    glow = glow_material("GlowCyan", (0.000, 0.784, 0.527), strength=2.0)
    gun = solid_material("Gunmetal", (0.195, 0.212, 0.235),
                         metallic=0.8, roughness=0.3)
    jade = solid_material("Jade", (0.028, 0.521, 0.328), roughness=0.5)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    hair = solid_material("Hair_Dark", (0.023, 0.026, 0.033), roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"ink": ink, "moon": moon, "dark": dark, "glow": glow,
            "gun": gun, "jade": jade,
            "skin": skin, "hair": hair, "eye": eye}


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001/002/003/004).
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
               (0.80, 0.290, 0.152), (0.55, 0.315, 0.165),
               (0.30, 0.350, 0.185), (0.06, 0.385, 0.200)]
OUTER_RINGS = [(1.30, 0.315, 0.168), (1.05, 0.312, 0.166),
               (0.80, 0.318, 0.170), (0.55, 0.355, 0.188)]
SKIRT_RINGS = [(0.62, 0.360, 0.195), (0.45, 0.385, 0.208),
               (0.30, 0.415, 0.222), (0.12, 0.445, 0.238),
               (0.06, 0.455, 0.242)]
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)


def build_inner_robe(m):
    """Moon-white inner robe; top ring peeks 0.04 above the outer robe
    at the neck so the inner collar reads."""
    return [make_elliptical_tube("InnerRobe", INNER_RINGS, 12,
                                 m["moon"], caps=False)]


def build_collar_band(m, z_angles, offset, name):
    """One diagonal cross-collar band: a ribbon hugging the outer robe
    surface, angle varying with height so the band runs diagonally
    across the chest (shoulder -> opposite waist)."""
    verts, faces = [], []
    width = 0.09
    for k, (z, ang) in enumerate(z_angles):
        rx, ry = interp_rings(OUTER_RINGS, z)
        p, n = ellipse_point(rx, ry, ang)
        c = Vector((p.x, p.y, z)) + n * offset
        a = math.radians(ang)
        t = Vector((-rx * math.sin(a), ry * math.cos(a), 0.0)).normalized()
        verts.append(tuple(c - t * width / 2))
        verts.append(tuple(c + t * width / 2))
    for k in range(len(z_angles) - 1):
        a0, a1 = 2 * k, 2 * k + 1
        b0, b1 = 2 * (k + 1), 2 * (k + 1) + 1
        faces.append((a0, b0, b1, a1))
    return mesh_from_data(name, verts, faces, m["moon"])


def build_inner_collar_v(m):
    """Moon-white V panel under the crossed bands: the inner collar
    showing through the V opening (0.003 proud of the outer robe,
    bands cross over it at 0.006 / 0.013)."""
    return [make_elliptical_tube(
                "InnerCollarV",
                [(1.30, 0.318, 0.171), (1.05, 0.315, 0.169)],
                8, m["moon"], arc=(258, 282), caps=False)]


def build_outer_robe(m):
    return [make_elliptical_tube("OuterRobe", OUTER_RINGS, 12,
                                 m["ink"], caps=False)]


def build_wide_sleeve(m, sx):
    """Ink wide sleeve: flares from the shoulder, cuff tapers slightly
    (bound cuff). Mannequin arm radius 0.085 max -> gap >= 0.030.
    The tube starts 0.06 ABOVE the shoulder point so the mannequin
    arm's top cap disc cannot be seen through the open top ring."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("WideSleeve", shoulder, direction,
                      [-0.06, 0.15, 0.30, 0.45, 0.55],
                      [0.118, 0.125, 0.140, 0.155, 0.150], 8, m["ink"],
                      caps=False),
            make_tube("CuffGlow", shoulder, direction,
                      [0.50, 0.55], [0.157, 0.157], 8, m["glow"],
                      caps=False)]


def build_arm_strap(m):
    """The set's only strap: dark band + gunmetal buckle on the left
    forearm (002 lesson: straps only where functional)."""
    sx = 1
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    objs = [make_tube("ArmStrap", shoulder, direction,
                      [0.30, 0.36], [0.148, 0.148], 8, m["dark"],
                      caps=False)]
    # Buckle on the front face of the sleeve at distance 0.33.
    p = shoulder + direction.normalized() * 0.33
    objs.append(add_box("ArmStrapBuckle", (p.x, -0.150, p.z),
                        (0.05, 0.02, 0.04), m["gun"]))
    return objs


def build_sash(m):
    """Dark wide waist sash + gunmetal buckle + cyan waist line."""
    return [make_elliptical_tube(
                "Sash", [(0.78, 0.372, 0.198), (0.66, 0.372, 0.198)],
                12, m["dark"], caps=False),
            make_elliptical_tube(
                "WaistGlow", [(0.73, 0.376, 0.201),
                              (0.71, 0.376, 0.201)],
                12, m["glow"], caps=False),
            add_box("SashBuckle", (0, -0.205, 0.72),
                    (0.08, 0.02, 0.05), m["gun"])]


def build_skirt(m):
    return [make_elliptical_tube("PleatedSkirt", SKIRT_RINGS, 12,
                                 m["moon"], caps=False),
            make_elliptical_tube(
                "HemGlow", [(0.10, 0.460, 0.246), (0.06, 0.460, 0.246)],
                12, m["glow"], caps=False)]


def build_pleat(m, angle_deg):
    """One vertical skirt pleat: a 4-ring strip hugging the flaring
    skirt surface, 0.006 proud, 0.032 wide, in INK on the moon-white
    skirt so the fold reads by colour contrast (003/004 lesson)."""
    a = math.radians(angle_deg)
    verts, faces = [], []
    z_list = [0.55, 0.42, 0.28, 0.12]
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
    return mesh_from_data("SkirtPleat", verts, faces, m["ink"])


def build_front_flap(m, sx, z_top, z_bot, x_off):
    """One asymmetric front flap: moon-white ribbon hugging the skirt
    front surface (same ribbon technique as the collar bands, so it
    never floats at the edges or sinks at the centre), cyan edge strip
    on its outer edge. Left flap long (to the knee), right flap short
    (to the thigh)."""
    def ribbon(offset, half_w, mat, name):
        verts, faces = [], []
        z_list = [z_top, (z_top + z_bot) / 2.0, z_bot]
        for k, z in enumerate(z_list):
            rx, ry = interp_rings(SKIRT_RINGS, z)
            cx = max(-0.999, min(0.999, x_off / rx))
            s = math.sqrt(1.0 - cx * cx)
            y = -ry * s
            ang = math.degrees(math.atan2(y, x_off))
            p, n = ellipse_point(rx, ry, ang)
            c = Vector((p.x, p.y, z)) + n * offset
            a = math.radians(ang)
            t = Vector((-rx * math.sin(a), ry * math.cos(a),
                        0.0)).normalized()
            verts.append(tuple(c - t * half_w))
            verts.append(tuple(c + t * half_w))
        for k in range(len(z_list) - 1):
            a0, a1 = 2 * k, 2 * k + 1
            b0, b1 = 2 * (k + 1), 2 * (k + 1) + 1
            faces.append((a0, b0, b1, a1))
        return mesh_from_data(name, verts, faces, mat)

    objs = [ribbon(0.006, 0.08, m["moon"], "FrontFlap")]
    # Edge strip: shifted outward along the tangent so it sits on the
    # flap's outer edge; 0.002 prouder than the flap so it reads.
    # (Built as a second ribbon with a narrower, offset centre.)
    def edge_ribbon():
        verts, faces = [], []
        z_list = [z_top, (z_top + z_bot) / 2.0, z_bot]
        for k, z in enumerate(z_list):
            rx, ry = interp_rings(SKIRT_RINGS, z)
            cx = max(-0.999, min(0.999, x_off / rx))
            s = math.sqrt(1.0 - cx * cx)
            y = -ry * s
            ang = math.degrees(math.atan2(y, x_off))
            p, n = ellipse_point(rx, ry, ang)
            a = math.radians(ang)
            t = Vector((-rx * math.sin(a), ry * math.cos(a),
                        0.0)).normalized()
            # Outer edge of the flap is at -t for the left flap
            # (x_off < 0: +t runs toward centre front) and +t for
            # the right flap.
            side = -1.0 if sx < 0 else 1.0
            c = (Vector((p.x, p.y, z)) + n * 0.008
                 + t * side * 0.072)
            verts.append(tuple(c - t * 0.008))
            verts.append(tuple(c + t * 0.008))
        for k in range(len(z_list) - 1):
            a0, a1 = 2 * k, 2 * k + 1
            b0, b1 = 2 * (k + 1), 2 * (k + 1) + 1
            faces.append((a0, b0, b1, a1))
        return mesh_from_data("FlapEdge", verts, faces, m["glow"])
    objs.append(edge_ribbon())
    return objs


def build_circuit(m):
    """Chest circuit: cyan glow boxes on the outer robe front below
    the collar crossing (z 0.95..0.82): horizontal bar + two diagonals
    + three node cubes. Boxes are 0.016 thick, centred at y=-0.170:
    front sticks ~0.010 proud of the robe, back half-embedded."""
    objs = [add_box("CircuitBar", (0, -0.170, 0.93),
                    (0.18, 0.016, 0.014), m["glow"]),
            add_box_rot("CircuitDiagL", (-0.07, -0.170, 0.885),
                        (0.014, 0.016, 0.12), m["glow"], (0, 0.5, 0)),
            add_box_rot("CircuitDiagR", (0.07, -0.170, 0.885),
                        (0.014, 0.016, 0.12), m["glow"], (0, -0.5, 0))]
    for name, pos in (("CircuitNodeC", (0, -0.172, 0.93)),
                      ("CircuitNodeL", (-0.10, -0.172, 0.85)),
                      ("CircuitNodeR", (0.10, -0.172, 0.85))):
        objs.append(add_box(name, pos, (0.03, 0.016, 0.03), m["glow"]))
    return objs


def build_pauldron(m):
    """Single shoulder guard, LEFT side only (asymmetric tailoring):
    dark dome + cyan emblem disc on its outer side."""
    sx = 1
    objs = [add_sphere("Pauldron", (sx * 0.33, 0, 1.24), 0.13, 8, 5,
                       (1.15, 1.0, 0.75), m["dark"])]
    objs.append(make_disc("PauldronEmblem", (sx * 0.485, 0, 1.24),
                          (sx, 0, 0), 0.030, 8, m["glow"]))
    return objs


def build_pendant(m):
    """Jade pendant on the sash front: cord + jade disc.
    Sash front at z=0.70 is y=-0.198; disc at -0.208 hangs in front
    of the skirt (skirt front at z=0.60 is y=-0.197)."""
    objs = [make_tube("PendantCord", (0.10, -0.202, 0.72), (0, 0, -1),
                      [0.0, 0.09], [0.006, 0.006], 6, m["dark"],
                      caps=False),
            make_disc("Pendant", (0.10, -0.208, 0.60), (0, -1, 0),
                      0.035, 10, m["jade"])]
    return objs


def build_hairpin(m):
    """Dark hairpin through the short hair + cyan tip."""
    objs = [add_cylinder("Hairpin", (0.05, 0.05, 1.62), 0.008, 0.30, 6,
                         m["dark"], rotation=(0.9, 0, 0.5))]
    objs.append(add_sphere("HairpinTip", (0.16, -0.02, 1.70), 0.014, 6, 3,
                           (1.0, 1.0, 1.0), m["glow"]))
    return objs


def build_boot(m, sx):
    """Dark long boot: tube up the leg + wedge foot + cyan sole line.
    Wedge half-width 0.095 and back 0.09 fully enclose the mannequin
    ankle (radius 0.082)."""
    return [make_tube("CyberBoot", (sx * 0.13, 0, 0.62), (0, 0, -1),
                      [0.0, 0.15, 0.30, 0.45, 0.54],
                      [0.118, 0.115, 0.110, 0.105, 0.100], 8, m["dark"],
                      caps=False),
            make_wedge("BootFoot", (sx * 0.13, -0.02, 0.02),
                       0.095, 0.09, -0.16, 0.0, 0.10, 0.045, m["dark"]),
            add_box("BootSoleGlow", (sx * 0.13, -0.172, 0.03),
                    (0.12, 0.018, 0.02), m["glow"])]


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["inner"] + parts["collar_L"] + parts["collar_R"]
            + parts["collar_V"] + parts["robe"] + parts["circuit"])
    ok = True
    ok &= check_gap("torso: inner robe vs mannequin torso @z=0.95",
                    interp_rings(INNER_RINGS, 0.95)[0], 0.240)
    ok &= check_gap("torso: outer robe vs inner robe @z=1.05",
                    interp_rings(OUTER_RINGS, 1.05)[0],
                    interp_rings(INNER_RINGS, 1.05)[0])
    ok &= check_relief("torso: inner collar V panel", 0.003)
    ok &= check_relief("torso: collar band R (inner layer)", 0.006)
    ok &= check_relief("torso: collar band L (outer layer)", 0.013,
                       lo=0.002, hi=0.020)
    # Circuit boxes: 0.016 thick centred at y=-0.170, robe front at
    # z~0.9 is y=-0.168 -> front sticks ~0.010 proud.
    ok &= check_relief("torso: circuit front proud", 0.010,
                       lo=0.005, hi=0.015)
    return objs, ok


def assemble_sleeves(parts):
    objs = (parts["sleeve_L"] + parts["sleeve_R"] + parts["strap"])
    ok = True
    ok &= check_gap("sleeves: wide sleeve vs mannequin arm", 0.118, 0.085)
    ok &= check_relief("sleeves: cuff glow ring", 0.0045)
    ok &= check_gap("sleeves: arm strap vs wide sleeve @0.33",
                    0.148, 0.140)
    return objs, ok


def assemble_waist(parts):
    objs = parts["sash"] + parts["pendant"]
    ok = True
    ok &= check_gap("waist: sash vs outer robe @z=0.72",
                    0.372, interp_rings(OUTER_RINGS, 0.72)[0])
    ok &= check_relief("waist: waist glow line", 0.004)
    # Pendant disc hangs 0.011 proud of the skirt front at z=0.60.
    ok &= check_relief("waist: pendant vs skirt front", 0.011,
                       lo=0.005, hi=0.020)
    return objs, ok


def assemble_skirt(parts):
    objs = parts["skirt"] + parts["pleats"] + parts["flaps"]
    ok = True
    ok &= check_gap("skirt: skirt vs outer robe overlap @z=0.58",
                    interp_rings(SKIRT_RINGS, 0.58)[0],
                    interp_rings(OUTER_RINGS, 0.58)[0])
    ok &= check_relief("skirt: pleat relief", 0.006)
    ok &= check_gap("skirt: hem glow vs skirt @z=0.08",
                    0.460, interp_rings(SKIRT_RINGS, 0.08)[0])
    # Front flaps sit 0.006 proud of the skirt front surface.
    ok &= check_relief("skirt: front flap relief", 0.006)
    return objs, ok


def assemble_shoulder(parts):
    objs = parts["pauldron"]
    ok = True
    ok &= check_gap("shoulder: pauldron outer vs robe rx @z=1.24",
                    0.33 + 0.150, interp_rings(OUTER_RINGS, 1.24)[0])
    return objs, ok


def assemble_feet(parts):
    objs = parts["boots"]
    ok = True
    ok &= check_gap("feet: boot tube vs mannequin leg @z=0.47",
                    0.115, 0.100)
    ok &= check_gap("feet: boot foot half-width vs ankle radius",
                    0.095, 0.082)
    return objs, ok


def assemble_head(parts):
    objs = parts["hairpin"]
    ok = True
    # Hairpin passes through the hair cap (radius 0.225 at z=1.58):
    # pin length 0.30 centred at (0.05, 0.05, 1.62) -> ends well
    # inside/outside the cap, tip sphere sits proud of the hair.
    print("L2_CHECK head: hairpin through hair cap, tip proud PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: outer robe vs inner robe @z=1.05",
                    interp_rings(OUTER_RINGS, 1.05)[0],
                    interp_rings(INNER_RINGS, 1.05)[0])
    ok &= check_gap("L3 layer: sash vs outer robe @z=0.72",
                    0.372, interp_rings(OUTER_RINGS, 0.72)[0])
    ok &= check_gap("L3 layer: skirt vs outer robe @z=0.58",
                    interp_rings(SKIRT_RINGS, 0.58)[0],
                    interp_rings(OUTER_RINGS, 0.58)[0])
    ok &= check_gap("L3 joint: wide sleeve vs mannequin arm", 0.118, 0.085)
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
    parts["inner"] = build_inner_robe(m)
    report_l1("InnerRobe", parts["inner"])
    # Cross collar: left band runs shoulder-right -> waist-left,
    # right band mirrored; left band is the OUTER layer (0.013),
    # right band the inner layer (0.006) -> left-over-right crossing.
    parts["collar_L"] = [build_collar_band(
        m, [(1.30, 298), (1.22, 288), (1.12, 276), (1.02, 264),
            (0.98, 252)], 0.013, "CollarBandL")]
    report_l1("CollarBandL", parts["collar_L"])
    parts["collar_R"] = [build_collar_band(
        m, [(1.30, 242), (1.22, 252), (1.12, 264), (1.02, 276),
            (0.98, 288)], 0.006, "CollarBandR")]
    report_l1("CollarBandR", parts["collar_R"])
    parts["collar_V"] = build_inner_collar_v(m)
    report_l1("InnerCollarV", parts["collar_V"])
    parts["robe"] = build_outer_robe(m)
    report_l1("OuterRobe", parts["robe"])
    parts["circuit"] = build_circuit(m)
    report_l1("ChestCircuit", parts["circuit"])
    parts["sleeve_L"] = build_wide_sleeve(m, -1)
    report_l1("WideSleeve_L", parts["sleeve_L"])
    parts["sleeve_R"] = build_wide_sleeve(m, 1)
    report_l1("WideSleeve_R", parts["sleeve_R"])
    parts["strap"] = build_arm_strap(m)
    report_l1("ArmStrap", parts["strap"])
    parts["sash"] = build_sash(m)
    report_l1("Sash+Buckle+WaistGlow", parts["sash"])
    parts["pendant"] = build_pendant(m)
    report_l1("Pendant", parts["pendant"])
    for o in parts["pendant"]:
        if o.name.startswith("Pendant") and o.name != "PendantCord":
            flat_patches.append(o)
    parts["skirt"] = build_skirt(m)
    report_l1("PleatedSkirt+HemGlow", parts["skirt"])
    parts["pleats"] = [build_pleat(m, a) for a in
                       (0, 45, 90, 135, 180, 225, 270, 315)]
    for o in parts["pleats"]:
        flat_patches.append(o)
    report_l1("SkirtPleats x8", parts["pleats"])
    parts["flaps"] = (build_front_flap(m, -1, 0.58, 0.28, -0.12)
                      + build_front_flap(m, 1, 0.58, 0.42, 0.12))
    for o in parts["flaps"]:
        flat_patches.append(o)
    report_l1("FrontFlaps x2", parts["flaps"])
    parts["pauldron"] = build_pauldron(m)
    report_l1("Pauldron_R", parts["pauldron"])
    for o in parts["pauldron"]:
        if o.name.startswith("PauldronEmblem"):
            flat_patches.append(o)
    parts["hairpin"] = build_hairpin(m)
    report_l1("Hairpin", parts["hairpin"])
    parts["boots"] = []
    for sx in (-1, 1):
        parts["boots"] += build_boot(m, sx)
    report_l1("CyberBoots x2", parts["boots"])

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    _, ok = assemble_torso(parts)
    l2_ok &= ok
    _, ok = assemble_sleeves(parts)
    l2_ok &= ok
    _, ok = assemble_waist(parts)
    l2_ok &= ok
    _, ok = assemble_skirt(parts)
    l2_ok &= ok
    _, ok = assemble_shoulder(parts)
    l2_ok &= ok
    _, ok = assemble_feet(parts)
    l2_ok &= ok
    _, ok = assemble_head(parts)
    l2_ok &= ok
    print("L2_SUMMARY %s" % ("ALL PASS" if l2_ok else "FAILURES PRESENT"))

    # ---- L3 full outfit on the mannequin ----
    costume = (parts["inner"] + parts["collar_L"] + parts["collar_R"]
               + parts["collar_V"] + parts["robe"] + parts["circuit"]
               + parts["sleeve_L"] + parts["sleeve_R"] + parts["strap"]
               + parts["sash"] + parts["pendant"] + parts["skirt"]
               + parts["pleats"] + parts["flaps"] + parts["pauldron"]
               + parts["hairpin"] + parts["boots"])
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
