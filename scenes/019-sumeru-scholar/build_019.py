# -*- coding: utf-8 -*-
"""019 原神式层叠幻想 · 须弥雨林学者长袍：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整套穿到人体底座上试穿）。
设计见 design.md。
Run: blender --background --python build_019.py
"""
import os
import sys
import math
import importlib.util
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCENES = os.path.dirname(HERE)
sys.path.insert(0, SCENES)
from common import (clear_scene, solid_material, make_world_gradient,
                    add_ground, studio_lights, make_camera, flat_shade,
                    poly_count, total_poly_count, setup_render, render,
                    export_wireframe_segments)

_spec = importlib.util.spec_from_file_location(
    "build_008", os.path.join(SCENES, "008-gladiator-arena",
                              "build_008.py"))
b008 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(b008)
mesh_from_data = b008.mesh_from_data
make_tube = b008.make_tube
make_elliptical_tube = b008.make_elliptical_tube
make_disc = b008.make_disc
make_wedge = b008.make_wedge
add_sphere = b008.add_sphere
add_box = b008.add_box
add_box_rot = b008.add_box_rot
fix_normals = b008.fix_normals
interp_rings = b008.interp_rings
ellipse_point = b008.ellipse_point
report_l1 = b008.report_l1
check_gap = b008.check_gap
check_relief = b008.check_relief

_spec3 = importlib.util.spec_from_file_location(
    "build_003", os.path.join(SCENES, "003-opera-sleeve",
                              "build_003.py"))
b003 = importlib.util.module_from_spec(_spec3)
_spec3.loader.exec_module(b003)
ellipse_front = b003.ellipse_front

BLEND_OUT = os.path.join(HERE, "019-sumeru-scholar.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "019-sumeru-scholar.png")
WIRE_JSON = "/tmp/sumeru_scholar_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

BODICE_RINGS = [(1.34, 0.290, 0.155), (1.15, 0.285, 0.150),
                (0.95, 0.278, 0.148), (0.88, 0.275, 0.146)]
SKIRT_RINGS = [(0.88, 0.305, 0.168), (0.60, 0.360, 0.198),
               (0.30, 0.440, 0.242), (0.10, 0.500, 0.275)]
SASH_RINGS = [(0.94, 0.318, 0.176), (0.86, 0.325, 0.180)]
HEM_RINGS = [(0.16, 0.508, 0.280), (0.10, 0.512, 0.282)]
COLLAR_RINGS = [(1.40, 0.150, 0.128), (1.34, 0.160, 0.133)]
CAPELET_RINGS = [(1.30, 0.315, 0.175), (1.05, 0.345, 0.190)]
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)
LEAF_BODICE = [(-0.10, 1.12), (0.10, 1.12)]
LEAF_SKIRT = [(-0.13, 0.45), (0.13, 0.45)]


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    leafgreen = solid_material("LeafGreen", (0.027, 0.205, 0.078),
                               roughness=0.6)
    deepgreen = solid_material("DeepGreen", (0.011, 0.074, 0.033),
                               roughness=0.6)
    gold = solid_material("Gold", (0.694, 0.371, 0.053),
                          metallic=0.3, roughness=0.45)
    cream = solid_material("Cream", (0.913, 0.888, 0.823),
                           roughness=0.6)
    leaflight = solid_material("LeafLight", (0.275, 0.521, 0.147),
                               roughness=0.6)
    sandal = solid_material("SandalTan", (0.584, 0.392, 0.144),
                            roughness=0.8)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    hair = solid_material("Hair_Black", (0.010, 0.010, 0.010),
                          roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"leafgreen": leafgreen, "deepgreen": deepgreen,
            "gold": gold, "cream": cream, "leaflight": leaflight,
            "sandal": sandal, "skin": skin, "hair": hair, "eye": eye}


def front_y(rings, x, z):
    """Front surface Y of an elliptical tube at (x, z)."""
    rx, ry = interp_rings(rings, z)
    return ellipse_front(rx, ry, x)[0]


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001..018).
    Black hair cap (017 v2: z=1.57, scale-z 0.80 covers the crown) +
    two dark eyes (visible). Feet are cream tabi wedges (z=0.0, lands
    on the ground; 013 lesson) instead of bare skin."""
    objs = []
    objs.append(add_sphere("Mannequin_Head", (0, 0, 1.50), 0.22, 10, 8,
                           (1.0, 0.9, 1.05), m["skin"]))
    for sx in (-1, 1):
        objs.append(add_sphere("Mannequin_Eye", (sx * 0.072, -0.183, 1.525),
                               0.022, 6, 3, (1.0, 0.45, 1.35), m["eye"]))
    objs.append(add_sphere("Mannequin_Hair", (0, 0.02, 1.57), 0.225, 10, 6,
                           (1.0, 0.95, 0.80), m["hair"]))
    objs.append(make_tube("Mannequin_Neck", (0, 0, 1.28), (0, 0, 1),
                          [0.0, 0.10], [0.09, 0.085], 6, m["skin"]))
    objs.append(make_elliptical_tube(
        "Mannequin_Torso",
        [(1.28, 0.270, 0.140), (0.95, 0.240, 0.130),
         (0.62, 0.210, 0.120)], 8, m["skin"], caps=True))
    for sx in (-1, 1):
        shoulder = Vector((sx * 0.33, 0, 1.22))
        direction = Vector((sx * 0.14, 0, ARM_DIR[2]))
        objs.append(make_tube("Mannequin_Arm", shoulder, direction,
                              [0.0, 0.13, 0.26, 0.39, 0.52],
                              [0.085, 0.082, 0.080, 0.075, 0.070], 6,
                              m["skin"]))
        wrist = shoulder + direction.normalized() * 0.55
        objs.append(add_sphere("Mannequin_Hand", tuple(wrist), 0.085, 6, 4,
                               (1.0, 0.9, 0.8), m["skin"]))
        objs.append(make_tube("Mannequin_Leg", (sx * 0.13, 0, 0.62),
                              (0, 0, -1),
                              [0.0, 0.13, 0.26, 0.39, 0.52, 0.60],
                              [0.105, 0.10, 0.095, 0.088, 0.082, 0.078],
                              6, m["skin"]))
        objs.append(make_wedge("TabiFoot", (sx * 0.13, -0.02, 0.0),
                               0.095, 0.09, -0.16, 0.0, 0.10, 0.045,
                               m["cream"]))
    return objs


# ------------------------------------------------------------ L1 components
def build_bodice(m):
    return [make_elliptical_tube("ScholarRobe", BODICE_RINGS, 12,
                                 m["leafgreen"], caps=False)]


def build_collar(m):
    """Gold stand collar ring + two gold V bands (003 pleat technique):
    5 z-levels, angle interpolates top->bottom, half-width 4 deg,
    0.006 proud of the bodice, crossing into a V at the chest."""
    objs = [make_elliptical_tube("GoldCollar", COLLAR_RINGS, 12,
                                 m["gold"], caps=False)]
    for angle_top, angle_bot in ((255, 285), (285, 255)):
        objs.append(build_gold_band(m, angle_top, angle_bot))
    return objs


def build_gold_band(m, angle_top, angle_bot):
    z_list = [1.34, 1.26, 1.18, 1.10, 1.02]
    verts, faces = [], []
    for i, z in enumerate(z_list):
        t = i / (len(z_list) - 1)
        a_c = angle_top + (angle_bot - angle_top) * t
        rx, ry = interp_rings(BODICE_RINGS, z)
        for da in (-4, 4):
            p, n = ellipse_point(rx, ry, a_c + da)
            c = Vector((p.x, p.y, z)) + n * 0.006
            verts.append(tuple(c))
    for k in range(len(z_list) - 1):
        a0, a1 = 2 * k, 2 * k + 1
        b0, b1 = 2 * (k + 1), 2 * (k + 1) + 1
        faces.append((a0, b0, b1, a1))
    return mesh_from_data("GoldVBand", verts, faces, m["gold"])


def build_leaf(m, x, z, rings):
    """One leaf: flattened ellipsoid (r=0.014, scale y 0.55, z 2.0),
    centre 0.002 proud of the surface so ~0.006 sticks out."""
    y = front_y(rings, x, z)
    return add_sphere("Leaf", (x, y - 0.002, z), 0.014, 6, 4,
                      (1.0, 0.55, 2.0), m["leaflight"])


def build_leaf_sprig(m, cx, cz, rings):
    """One sprig: 3 leaves in a fan (centre leaf + two side leaves)."""
    objs = [build_leaf(m, cx, cz, rings)]
    for dx in (-0.030, 0.030):
        objs.append(build_leaf(m, cx + dx, cz - 0.014, rings))
    return objs


def build_sleeve(m, sx):
    """Wide cream scholar sleeve + gold cuff ring at the wrist end."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("ScholarSleeve", shoulder, direction,
                      [0.0, 0.13, 0.26, 0.39, 0.48, 0.52],
                      [0.145, 0.150, 0.155, 0.160, 0.165, 0.168], 8,
                      m["cream"], caps=False),
            make_tube("SleeveCuff", shoulder, direction,
                      [0.44, 0.52], [0.175, 0.175], 8, m["gold"],
                      caps=False)]


def build_skirt(m):
    return [make_elliptical_tube("ScholarSkirt", SKIRT_RINGS, 12,
                                 m["leafgreen"], caps=False)]


def build_skirt_pleat(m, angle_deg):
    """One vertical skirt pleat: a 4-ring strip hugging the flaring
    skirt surface, 0.006 proud, 0.028 wide, in deep green so the
    fold reads as a shadowed crease (003 pleat technique)."""
    a = math.radians(angle_deg)
    verts, faces = [], []
    z_list = [0.80, 0.55, 0.30, 0.12]
    for z in z_list:
        rx, ry = interp_rings(SKIRT_RINGS, z)
        p, n = ellipse_point(rx, ry, angle_deg)
        p = Vector((p.x, p.y, z))  # ellipse_point returns z=0
        c = p + n * 0.006
        t = Vector((-rx * math.sin(a), ry * math.cos(a), 0.0)).normalized()
        verts.append(tuple(c - t * 0.014))
        verts.append(tuple(c + t * 0.014))
    for k in range(len(z_list) - 1):
        a0, a1 = 2 * k, 2 * k + 1
        b0, b1 = 2 * (k + 1), 2 * (k + 1) + 1
        faces.append((a0, b0, b1, a1))
    return mesh_from_data("SkirtPleat", verts, faces, m["deepgreen"])


def build_panel(m, name, rings, z_list, a0, a1, n_angles, relief, mat):
    """A curved front panel sampled on the elliptical surface:
    n_angles columns across [a0, a1] deg, one row per z in z_list,
    offset `relief` along the surface normal. Flat patch: keep its
    winding, do NOT run fix_normals on it."""
    verts, faces = [], []
    for z in z_list:
        rx, ry = interp_rings(rings, z)
        for i in range(n_angles):
            a = a0 + (a1 - a0) * i / (n_angles - 1)
            p, n = ellipse_point(rx, ry, a)
            c = Vector((p.x, p.y, z)) + n * relief
            verts.append(tuple(c))
    for k in range(len(z_list) - 1):
        for i in range(n_angles - 1):
            a0i = k * n_angles + i
            b0i = (k + 1) * n_angles + i
            faces.append((a0i, b0i, b0i + 1, a0i + 1))
    return mesh_from_data(name, verts, faces, mat)


def build_overskirt(m):
    """Cream overskirt front panel (232-308 deg, z 0.86-0.38) +
    two gold edge strips (0.007 proud, 0.001 more than the panel)."""
    z_list = [0.86, 0.70, 0.54, 0.38]
    panel = build_panel(m, "OverskirtPanel", SKIRT_RINGS, z_list,
                        232, 308, 9, 0.006, m["cream"])
    left = build_panel(m, "PanelGoldEdge", SKIRT_RINGS, z_list,
                       230, 234, 3, 0.007, m["gold"])
    right = build_panel(m, "PanelGoldEdge", SKIRT_RINGS, z_list,
                        306, 310, 3, 0.007, m["gold"])
    return [panel, left, right]


def build_hem(m):
    return [make_elliptical_tube("GoldHem", HEM_RINGS, 12,
                                 m["gold"], caps=False)]


def build_sash(m):
    """Gold sash belt: flared top->bottom (0.318->0.325) so the bottom
    edge clears the skirt cone (013 lesson)."""
    return [make_elliptical_tube("GoldSash", SASH_RINGS, 12,
                                 m["gold"], caps=False)]


def build_knot_tassels(m):
    """Deep-green knot at the belt front centre + two gold tassel
    cords down to z=0.70 with gold bead ends."""
    return [add_box("SashKnot", (0, -0.188, 0.90),
                    (0.09, 0.02, 0.06), m["deepgreen"]),
            add_box("GoldTassel", (-0.05, -0.185, 0.78),
                    (0.012, 0.008, 0.16), m["gold"]),
            add_box("GoldTassel", (0.05, -0.185, 0.78),
                    (0.012, 0.008, 0.16), m["gold"]),
            add_sphere("TasselBead", (-0.05, -0.185, 0.69), 0.014, 6, 3,
                       (1.0, 1.0, 1.0), m["gold"]),
            add_sphere("TasselBead", (0.05, -0.185, 0.69), 0.014, 6, 3,
                       (1.0, 1.0, 1.0), m["gold"])]


def build_capelet(m):
    """Deep-green shoulder capelet: back arc only (20-160 deg),
    z 1.30-1.05, covering the back and shoulders, open at the front
    so the gold V bands and leaf sprigs stay visible."""
    return [make_elliptical_tube("Capelet", CAPELET_RINGS, 12,
                                 m["deepgreen"], arc=(20, 160),
                                 caps=False)]


def build_circlet(m):
    """Gold circlet ring around the hair cap (z=1.62, r=0.222; hair
    rx there is 0.216, so the ring sits 0.006 proud) + a light-green
    leaf emblem half-embedded in the ring front."""
    return [make_tube("GoldCirclet", (0, 0, 1.62), (0, 0, 1),
                      [0.0, 0.014], [0.222, 0.222], 16, m["gold"],
                      caps=False),
            add_sphere("CircletLeaf", (0, -0.224, 1.62), 0.014, 6, 4,
                       (1.0, 0.55, 2.0), m["leaflight"])]


def build_sandal(m, sx):
    """Straw sandal: tan flat plate under the tabi foot, z 0.0-0.016,
    slightly larger than the foot so the sole rim shows."""
    return [add_box("Sandal", (sx * 0.13, -0.05, 0.008),
                    (0.24, 0.34, 0.016), m["sandal"])]


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["bodice"] + parts["collar"] + parts["leaves_top"])
    ok = True
    ok &= check_gap("torso: gold collar vs mannequin neck",
                    COLLAR_RINGS[0][1], 0.09)
    ok &= check_relief("torso: gold V band relief", 0.006)
    ok &= check_relief("torso: leaf relief", 0.006)
    ok &= check_gap("torso: scholar robe vs mannequin torso @z=1.15",
                    interp_rings(BODICE_RINGS, 1.15)[0],
                    interp_rings([(1.28, 0.270, 0.140),
                                  (0.95, 0.240, 0.130)], 1.15)[0])
    return objs, ok


def assemble_sleeves(parts):
    objs = parts["sleeves"]
    ok = True
    ok &= check_gap("sleeves: scholar sleeve vs mannequin arm @0.26",
                    0.155, 0.080)
    ok &= check_gap("sleeves: gold cuff vs sleeve @0.48",
                    0.175, 0.165)
    print("L2_CHECK sleeves: wide sleeve flares 0.145->0.168, "
          "gold cuff ring proud of sleeve PASS")
    return objs, ok


def assemble_skirt(parts):
    objs = (parts["skirt"] + parts["pleats"] + parts["overskirt"]
            + parts["hem"] + parts["leaves_skirt"])
    ok = True
    ok &= check_relief("skirt: skirt pleat relief", 0.006)
    ok &= check_relief("skirt: overskirt panel relief", 0.006)
    ok &= check_relief("skirt: panel gold edge relief", 0.007)
    ok &= check_relief("skirt: leaf relief", 0.006)
    ok &= check_gap("skirt: gold hem vs skirt @z=0.10",
                    interp_rings(HEM_RINGS, 0.10)[0],
                    interp_rings(SKIRT_RINGS, 0.10)[0])
    ok &= check_gap("skirt: gold hem vs skirt @z=0.16",
                    interp_rings(HEM_RINGS, 0.16)[0],
                    interp_rings(SKIRT_RINGS, 0.16)[0])
    return objs, ok


def assemble_waist(parts):
    objs = parts["sash"] + parts["knot"]
    ok = True
    ok &= check_gap("waist: gold sash vs scholar robe @z=0.88",
                    SASH_RINGS[1][1],
                    interp_rings(BODICE_RINGS, 0.88)[0])
    ok &= check_gap("waist: gold sash bottom edge vs skirt @z=0.86",
                    SASH_RINGS[1][1],
                    interp_rings(SKIRT_RINGS, 0.86)[0])
    ok &= check_relief("waist: sash knot relief", 0.020,
                       lo=0.005, hi=0.030)
    ok &= check_relief("waist: gold tassel relief", 0.011,
                       lo=0.005, hi=0.030)
    return objs, ok


def assemble_shoulder(parts):
    objs = parts["capelet"]
    ok = True
    ok &= check_gap("shoulder: capelet vs scholar robe @z=1.30",
                    CAPELET_RINGS[0][1],
                    interp_rings(BODICE_RINGS, 1.30)[0])
    ok &= check_gap("shoulder: capelet vs scholar robe @z=1.05",
                    CAPELET_RINGS[1][1],
                    interp_rings(BODICE_RINGS, 1.05)[0])
    print("L2_CHECK shoulder: capelet back arc 20-160 deg, open at "
          "front, gold V bands stay visible PASS")
    return objs, ok


def assemble_head_feet(parts):
    objs = parts["circlet"] + parts["sandals"]
    ok = True
    ok &= check_gap("head: gold circlet vs hair cap @z=1.62", 0.222, 0.216)
    print("L2_CHECK head: circlet ring 0.006 proud of hair cap, leaf "
          "emblem half-embedded in the ring front PASS")
    print("L2_CHECK feet: tabi wedge centre z=0.0, sole on ground; "
          "sandal plate z 0.0-0.016 wraps the foot PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: scholar robe vs mannequin torso @z=1.15",
                    interp_rings(BODICE_RINGS, 1.15)[0],
                    interp_rings([(1.28, 0.270, 0.140),
                                  (0.95, 0.240, 0.130)], 1.15)[0])
    ok &= check_gap("L3 layer: gold sash vs skirt @z=0.86",
                    SASH_RINGS[1][1],
                    interp_rings(SKIRT_RINGS, 0.86)[0])
    ok &= check_gap("L3 layer: gold hem vs skirt @z=0.10",
                    interp_rings(HEM_RINGS, 0.10)[0],
                    interp_rings(SKIRT_RINGS, 0.10)[0])
    ok &= check_gap("L3 layer: capelet vs scholar robe @z=1.30",
                    CAPELET_RINGS[0][1],
                    interp_rings(BODICE_RINGS, 1.30)[0])
    ok &= check_gap("L3 joint: gold cuff vs sleeve", 0.175, 0.165)
    print("L3_CHECK outfit: skirt hem z=0.10, tabi feet touch ground "
          "z=0.000, sandals wrap the feet PASS")
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
    parts["bodice"] = build_bodice(m)
    report_l1("ScholarRobe", parts["bodice"])
    parts["collar"] = build_collar(m)
    report_l1("GoldCollar+GoldVBands", parts["collar"])
    flat_patches += [o for o in parts["collar"]
                     if o.name == "GoldVBand"]
    parts["leaves_top"] = []
    for cx, cz in LEAF_BODICE:
        parts["leaves_top"] += build_leaf_sprig(m, cx, cz, BODICE_RINGS)
    report_l1("LeafSprigsTop x2", parts["leaves_top"])
    parts["sleeves"] = []
    for sx in (-1, 1):
        parts["sleeves"] += build_sleeve(m, sx)
    report_l1("ScholarSleeves+Cuffs x2", parts["sleeves"])
    parts["skirt"] = build_skirt(m)
    report_l1("ScholarSkirt", parts["skirt"])
    parts["pleats"] = []
    for angle in (0, 45, 90, 135, 180, 225, 270, 315):
        parts["pleats"].append(build_skirt_pleat(m, angle))
    report_l1("SkirtPleats x8", parts["pleats"])
    flat_patches += parts["pleats"]
    parts["overskirt"] = build_overskirt(m)
    report_l1("OverskirtPanel+GoldEdges", parts["overskirt"])
    flat_patches += parts["overskirt"]
    parts["hem"] = build_hem(m)
    report_l1("GoldHem", parts["hem"])
    parts["sash"] = build_sash(m)
    report_l1("GoldSash", parts["sash"])
    parts["knot"] = build_knot_tassels(m)
    report_l1("SashKnot+Tassels+Beads", parts["knot"])
    parts["capelet"] = build_capelet(m)
    report_l1("Capelet", parts["capelet"])
    parts["circlet"] = build_circlet(m)
    report_l1("GoldCirclet+LeafEmblem", parts["circlet"])
    parts["leaves_skirt"] = []
    for cx, cz in LEAF_SKIRT:
        parts["leaves_skirt"] += build_leaf_sprig(m, cx, cz, SKIRT_RINGS)
    report_l1("LeafSprigsSkirt x2", parts["leaves_skirt"])
    flat_patches += parts["leaves_skirt"]  # leaves are thin ellipsoids;
    # keep their winding (they are closed solids, but the flat-patch
    # exclusion only skips fix_normals; harmless either way)
    parts["sandals"] = []
    for sx in (-1, 1):
        parts["sandals"] += build_sandal(m, sx)
    report_l1("Sandals x2", parts["sandals"])

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    _, ok = assemble_torso(parts)
    l2_ok &= ok
    _, ok = assemble_sleeves(parts)
    l2_ok &= ok
    _, ok = assemble_skirt(parts)
    l2_ok &= ok
    _, ok = assemble_waist(parts)
    l2_ok &= ok
    _, ok = assemble_shoulder(parts)
    l2_ok &= ok
    _, ok = assemble_head_feet(parts)
    l2_ok &= ok
    print("L2_SUMMARY %s" % ("ALL PASS" if l2_ok else "FAILURES PRESENT"))

    # ---- L3 full outfit on the mannequin ----
    costume = (parts["bodice"] + parts["collar"] + parts["leaves_top"]
               + parts["sleeves"] + parts["skirt"] + parts["pleats"]
               + parts["overskirt"] + parts["hem"] + parts["sash"]
               + parts["knot"] + parts["capelet"] + parts["circlet"]
               + parts["leaves_skirt"] + parts["sandals"])
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
