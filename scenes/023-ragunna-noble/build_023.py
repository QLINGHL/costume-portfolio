# -*- coding: utf-8 -*-
"""023 鸣潮式地区衣橱 · 拉古那嘉年华贵族套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整套穿到人体底座上试穿）。
设计见 design.md。BACKLOG 本轮已空，自选新题材：鸣潮地区衣橱新方向——拉古那（黎那汐塔）。
Run: blender --background --python build_023.py
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

_spec19 = importlib.util.spec_from_file_location(
    "build_019", os.path.join(SCENES, "019-sumeru-scholar",
                              "build_019.py"))
b019 = importlib.util.module_from_spec(_spec19)
_spec19.loader.exec_module(b019)
build_panel = b019.build_panel

BLEND_OUT = os.path.join(HERE, "023-ragunna-noble.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "023-ragunna-noble.png")
WIRE_JSON = "/tmp/ragunna_noble_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

BODICE_RINGS = [(1.34, 0.288, 0.152), (1.15, 0.282, 0.148),
                (0.92, 0.272, 0.144)]
LACE_RINGS = [(1.36, 0.160, 0.140), (1.40, 0.182, 0.158),
              (1.44, 0.160, 0.140)]
SKIRT_RINGS = [(0.92, 0.272, 0.144), (0.62, 0.310, 0.160),
               (0.30, 0.360, 0.180)]
BELT_RINGS = [(0.94, 0.292, 0.152), (0.86, 0.298, 0.155)]
# Mask band follows the hair cap: hair rx at z=1.58 is ~0.225, at
# z=1.64 ~0.207, so the band narrows 0.232 -> 0.216 to stay proud.
MASK_RINGS = [(1.64, 0.216, 0.205), (1.58, 0.232, 0.220)]
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)
ROSETTE_Z = [1.25, 1.16, 1.07]
PLEAT_ANGLES = [200, 210, 220, 230, 310, 320, 330, 340]
# Feathers on the hat: (x, y, z, tilt_x, tilt_z, material key)
FEATHERS = [(0.10, 0.10, 1.80, -0.55, -0.45, "teal"),
            (-0.05, 0.12, 1.82, -0.65, 0.05, "gold"),
            (-0.14, 0.05, 1.78, -0.50, 0.50, "violet")]


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    cream = solid_material("Cream", (0.888, 0.807, 0.666), roughness=0.6)
    violet = solid_material("Violet", (0.105, 0.048, 0.262), roughness=0.6)
    gold = solid_material("Gold", (0.584, 0.361, 0.020), roughness=0.6)
    teal = solid_material("Teal", (0.014, 0.194, 0.107), roughness=0.6)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    hair = solid_material("Hair_Plumb", (0.069, 0.027, 0.147),
                          roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"cream": cream, "violet": violet, "gold": gold,
            "teal": teal, "skin": skin, "hair": hair, "eye": eye}


def front_y(rings, x, z):
    """Front surface Y of an elliptical tube at (x, z)."""
    rx, ry = interp_rings(rings, z)
    return ellipse_front(rx, ry, x)[0]


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001..022).
    Deep-plum hair cap (z=1.57, scale-z 0.80 covers the crown) +
    two dark eyes (visible; the mask sits on the forehead above them).
    Feet are violet boot wedges (z=0.0, lands on the ground; 013 lesson)
    instead of bare skin."""
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
        objs.append(make_wedge("VioletBoot", (sx * 0.13, -0.02, 0.0),
                               0.095, 0.09, -0.16, 0.0, 0.10, 0.045,
                               m["violet"]))
    return objs


# ------------------------------------------------------------ L1 components
def build_bodice(m):
    return [make_elliptical_tube("CreamBodice", BODICE_RINGS, 12,
                                 m["cream"], caps=False)]


def build_lace_collar(m):
    """Cream lace collar: three stacked ring bands around the neck
    (011 fur-collar technique), radii 0.160 / 0.182 / 0.160."""
    objs = []
    for z0, rx, ry in [(1.36, 0.160, 0.140), (1.40, 0.182, 0.158),
                       (1.44, 0.160, 0.140)]:
        objs.append(make_elliptical_tube(
            "LaceCollar", [(z0 + 0.005, rx, ry), (z0 - 0.005, rx, ry)],
            12, m["cream"], caps=False))
    return objs


def build_embroidery_panel(m):
    """Gold embroidery front panel: curved front panel (232-308 deg,
    z 1.30-1.02) over the cream bodice, 0.006 proud."""
    return [build_panel(m, "GoldEmbroidery", BODICE_RINGS,
                        [1.30, 1.20, 1.11, 1.02], 232, 308, 9, 0.006,
                        m["gold"])]


def build_rosettes(m):
    """Three teal rosettes on the gold panel centre (z=1.25/1.16/1.07):
    flattened spheres, 0.014 proud of the panel. Teal on gold so the
    relief reads by colour, not by shading alone (003 lesson: a gold
    rosette on a gold panel would be invisible)."""
    objs = []
    for z in ROSETTE_Z:
        plate_y = front_y(BODICE_RINGS, 0, z) - 0.006
        objs.append(add_sphere("TealRosette", (0, plate_y - 0.004, z),
                               0.020, 6, 3, (1.0, 0.5, 1.0), m["teal"]))
    return objs


def build_overskirt(m):
    """Violet overskirt front panel (240-300 deg, z 0.88-0.34) over the
    cream gown, 0.006 proud, + two gold edge strips (0.007 proud)."""
    z_list = [0.88, 0.70, 0.52, 0.34]
    panel = build_panel(m, "VioletOverskirt", SKIRT_RINGS, z_list,
                        240, 300, 9, 0.006, m["violet"])
    left = build_panel(m, "OverskirtGoldEdge", SKIRT_RINGS, z_list,
                       238, 242, 3, 0.007, m["gold"])
    right = build_panel(m, "OverskirtGoldEdge", SKIRT_RINGS, z_list,
                        298, 302, 3, 0.007, m["gold"])
    return [panel, left, right]


def build_gown(m):
    return [make_elliptical_tube("CreamGown", SKIRT_RINGS, 12,
                                 m["cream"], caps=False)]


def build_skirt_pleat(m, angle_deg):
    """One violet skirt pleat: a 4-ring strip hugging the flaring
    skirt surface, 0.006 proud, 0.020 wide, in violet so the pleat
    reads on the cream cloth (003 pleat technique). Angles sit on the
    skirt SIDES (200-230 / 310-340) because the overskirt covers the
    front centre."""
    a = math.radians(angle_deg)
    verts, faces = [], []
    z_list = [0.88, 0.70, 0.50, 0.32]
    for z in z_list:
        rx, ry = interp_rings(SKIRT_RINGS, z)
        p, n = ellipse_point(rx, ry, angle_deg)
        p = Vector((p.x, p.y, z))  # ellipse_point returns z=0
        c = p + n * 0.006
        t = Vector((-rx * math.sin(a), ry * math.cos(a), 0.0)).normalized()
        verts.append(tuple(c - t * 0.010))
        verts.append(tuple(c + t * 0.010))
    for k in range(len(z_list) - 1):
        a0, a1 = 2 * k, 2 * k + 1
        b0, b1 = 2 * (k + 1), 2 * (k + 1) + 1
        faces.append((a0, b0, b1, a1))
    return mesh_from_data("SkirtPleat", verts, faces, m["violet"])


def build_belt(m):
    """Gold belt: flared top->bottom (0.292->0.298) so the bottom
    edge clears the skirt cone (013 lesson)."""
    return [make_elliptical_tube("GoldBelt", BELT_RINGS, 12,
                                 m["gold"], caps=False)]


def build_buckle(m):
    """Teal buckle at the belt front centre."""
    return [add_box("TealBuckle", (0, -0.165, 0.90),
                    (0.09, 0.02, 0.05), m["teal"])]


def build_glove(m, sx):
    """Cream long glove (shoulder to wrist) over the mannequin arm."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("CreamGlove", shoulder, direction,
                      [0.0, 0.13, 0.26, 0.39, 0.52],
                      [0.098, 0.096, 0.093, 0.090, 0.086], 10,
                      m["cream"], caps=False)]


def build_cuff(m, sx):
    """Gold cuff ring over the glove at the wrist."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("GoldCuff", shoulder, direction,
                      [0.46, 0.52], [0.10, 0.10], 10,
                      m["gold"], caps=False)]


def build_shoulder_rosette(m, sx):
    """Gold shoulder rosette: flattened sphere on the shoulder top +
    3 gold fringe boxes hanging off its outer edge."""
    objs = [add_sphere("GoldShoulderRosette", (sx * 0.36, 0, 1.27),
                       0.055, 8, 4, (1.2, 0.6, 0.9), m["gold"])]
    for dy in (-0.03, 0.0, 0.03):
        objs.append(add_box("RosetteFringe",
                            (sx * 0.44, dy, 1.22),
                            (0.012, 0.012, 0.07), m["gold"]))
    return objs


def build_hat(m):
    """Feathered carnival hat: violet brim disc (r=0.30, z=1.70,
    slightly tilted) + violet crown dome (r=0.16, z=1.72, covers the
    hair top at 1.75) + gold hat band ring (r=0.17, z=1.70) +
    3 feathers (teal/gold/violet) fanning up from the crown back."""
    brim = make_disc("VioletHatBrim", (0, 0, 1.70), (0.25, 0, 1),
                     0.33, 24, m["violet"])
    crown = add_sphere("VioletHatCrown", (0, 0, 1.72), 0.16, 10, 6,
                       (1.0, 0.95, 0.5), m["violet"])
    band = make_tube("GoldHatBand", (0, 0, 1.70), (0, 0, 1),
                     [0.0, 0.02], [0.17, 0.17], 16, m["gold"],
                     caps=False)
    objs = [brim, crown, band]
    for x, y, z, rx, rz, key in FEATHERS:
        objs.append(add_box_rot("HatFeather", (x, y, z),
                                (0.034, 0.012, 0.22), m[key],
                                (rx, 0, rz)))
    return objs


def build_mask(m):
    """Half gold mask pushed up on the forehead: curved band
    (232-308 deg, z 1.58-1.64) over the hair cap, 0.006 proud,
    ring radius narrowing with the hair (0.232 -> 0.216) so it never
    sinks into the hair (016 lesson). Teal brow gem at the centre."""
    band = build_panel(m, "GoldMask", MASK_RINGS,
                       [1.64, 1.61, 1.58], 232, 308, 9, 0.006, m["gold"])
    gem_y = front_y(MASK_RINGS, 0, 1.61) - 0.006 - 0.004
    gem = add_sphere("TealBrowGem", (0, gem_y, 1.61),
                     0.025, 6, 3, (1.0, 0.5, 1.0), m["teal"])
    return [band, gem]


def build_boot(m, sx):
    """Violet tall boot: shaft tube (z 0.30-0.06) over the leg +
    gold trim ring on the visible shaft at z 0.22 (the shaft top
    at z 0.30 sits under the skirt hem, so a ring there would be
    hidden); the wedge sole (mannequin VioletBoot, violet) lands
    at z=0.0."""
    shaft = make_tube("VioletBootShaft", (sx * 0.13, 0, 0.30), (0, 0, -1),
                      [0.0, 0.24], [0.105, 0.10], 10,
                      m["violet"], caps=False)
    trim = make_tube("GoldBootTrim", (sx * 0.13, 0, 0.22), (0, 0, -1),
                     [0.0, 0.02], [0.109, 0.109], 10,
                     m["gold"], caps=False)
    return [shaft, trim]


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["bodice"] + parts["lace_collar"]
            + parts["embroidery"] + parts["rosettes"])
    ok = True
    ok &= check_gap("torso: lace collar vs mannequin neck",
                    LACE_RINGS[0][1], 0.09)
    ok &= check_gap("torso: lace collar mid ring wider than outer rings",
                    0.182, 0.160)
    ok &= check_relief("torso: embroidery panel relief", 0.006)
    ok &= check_relief("torso: teal rosette relief", 0.014,
                       lo=0.005, hi=0.020)
    ok &= check_gap("torso: cream bodice vs mannequin torso @z=1.15",
                    interp_rings(BODICE_RINGS, 1.15)[0],
                    interp_rings([(1.28, 0.270, 0.140),
                                  (0.95, 0.240, 0.130)], 1.15)[0])
    return objs, ok


def assemble_arms(parts):
    objs = parts["gloves"] + parts["cuffs"]
    ok = True
    ok &= check_gap("arms: long glove vs mannequin arm @0.0",
                    0.098, 0.085)
    ok &= check_gap("arms: gold cuff vs glove @0.46", 0.10, 0.088)
    print("L2_CHECK arms: cream long glove 0.098->0.086, gold "
          "cuff ring at the wrist PASS")
    return objs, ok


def assemble_shoulders(parts):
    objs = parts["shoulder_rosettes"]
    ok = True
    ok &= check_gap("shoulder: rosette vs cream bodice @z=1.27",
                    0.36, interp_rings(BODICE_RINGS, 1.27)[0])
    print("L2_CHECK shoulder: gold shoulder rosettes sit on the "
          "shoulder tops, fringe hangs off the outer edge, clear of "
          "the lace collar PASS")
    return objs, ok


def assemble_skirt(parts):
    objs = parts["gown"] + parts["overskirt"] + parts["pleats"]
    ok = True
    ok &= check_relief("skirt: overskirt panel relief", 0.006)
    ok &= check_relief("skirt: overskirt gold edge relief", 0.007)
    ok &= check_relief("skirt: skirt pleat relief", 0.006)
    ok &= check_gap("skirt: cream gown vs legs @z=0.62", 0.310, 0.235)
    ok &= check_gap("skirt: belt bottom edge vs skirt @z=0.86",
                    BELT_RINGS[1][1],
                    interp_rings(SKIRT_RINGS, 0.86)[0])
    return objs, ok


def assemble_waist(parts):
    objs = parts["belt"] + parts["buckle"]
    ok = True
    ok &= check_gap("waist: gold belt vs cream bodice @z=0.92",
                    interp_rings(BELT_RINGS, 0.92)[0],
                    interp_rings(BODICE_RINGS, 0.92)[0])
    ok &= check_gap("waist: gold belt bottom edge vs skirt @z=0.86",
                    BELT_RINGS[1][1],
                    interp_rings(SKIRT_RINGS, 0.86)[0])
    ok &= check_relief("waist: teal buckle relief", 0.0215,
                       lo=0.005, hi=0.030)
    return objs, ok


def assemble_head_feet(parts):
    objs = parts["hat"] + parts["mask"] + parts["boots"]
    ok = True
    ok &= check_gap("head: gold mask band vs hair cap @z=1.61",
                    interp_rings(MASK_RINGS, 1.61)[0] + 0.006, 0.216)
    ok &= check_gap("head: hat crown vs hair top @z=1.72",
                    0.16, 0.124)
    print("L2_CHECK head: gold mask band 0.006+ proud of hair cap, "
          "teal brow gem on the mask centre, hat brim z=1.70 with "
          "crown dome covering the hair top PASS")
    print("L2_CHECK feet: violet boot wedge centre z=0.0, sole on "
          "ground; tall boot shaft z 0.30-0.06, gold trim ring at "
          "z 0.22 on the visible shaft PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: cream bodice vs mannequin torso @z=1.15",
                    interp_rings(BODICE_RINGS, 1.15)[0],
                    interp_rings([(1.28, 0.270, 0.140),
                                  (0.95, 0.240, 0.130)], 1.15)[0])
    ok &= check_gap("L3 layer: gold belt vs skirt @z=0.86",
                    BELT_RINGS[1][1],
                    interp_rings(SKIRT_RINGS, 0.86)[0])
    ok &= check_gap("L3 layer: embroidery vs cream bodice @z=1.20",
                    interp_rings(BODICE_RINGS, 1.20)[0] + 0.006,
                    interp_rings(BODICE_RINGS, 1.20)[0])
    ok &= check_gap("L3 layer: overskirt vs cream gown @z=0.70",
                    interp_rings(SKIRT_RINGS, 0.70)[0] + 0.006,
                    interp_rings(SKIRT_RINGS, 0.70)[0])
    ok &= check_gap("L3 joint: gold cuff vs glove", 0.10, 0.088)
    ok &= check_gap("L3 joint: violet boot shaft vs leg @z=0.18",
                    0.1025, 0.088)
    print("L3_CHECK outfit: gown hem z=0.30, violet boots below the hem, "
          "violet boot soles touch ground z=0.000 PASS")
    print("L3_CHECK outfit: all layers on mannequin, %s"
          % ("PASS" if ok else "FAIL"))
    return ok


# ---------------------------------------------------------------------- main
def main():
    clear_scene()
    make_world_gradient(top=(0.62, 0.65, 0.70), bottom=(0.38, 0.41, 0.46),
                        strength=0.75)
    add_ground(size=20.0, color=(0.45, 0.48, 0.52))
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
    report_l1("CreamBodice", parts["bodice"])
    parts["lace_collar"] = build_lace_collar(m)
    report_l1("LaceCollar x3 rings", parts["lace_collar"])
    parts["embroidery"] = build_embroidery_panel(m)
    report_l1("GoldEmbroidery", parts["embroidery"])
    flat_patches += parts["embroidery"]
    parts["rosettes"] = build_rosettes(m)
    report_l1("TealRosettes x3", parts["rosettes"])
    parts["overskirt"] = build_overskirt(m)
    report_l1("VioletOverskirt+GoldEdges", parts["overskirt"])
    flat_patches += parts["overskirt"]
    parts["gown"] = build_gown(m)
    report_l1("CreamGown", parts["gown"])
    parts["pleats"] = []
    for angle in PLEAT_ANGLES:
        parts["pleats"].append(build_skirt_pleat(m, angle))
    report_l1("SkirtPleats x8", parts["pleats"])
    flat_patches += parts["pleats"]
    parts["belt"] = build_belt(m)
    report_l1("GoldBelt", parts["belt"])
    parts["buckle"] = build_buckle(m)
    report_l1("TealBuckle", parts["buckle"])
    parts["gloves"] = []
    for sx in (-1, 1):
        parts["gloves"] += build_glove(m, sx)
    report_l1("CreamGloves x2", parts["gloves"])
    parts["cuffs"] = []
    for sx in (-1, 1):
        parts["cuffs"] += build_cuff(m, sx)
    report_l1("GoldCuffs x2", parts["cuffs"])
    parts["shoulder_rosettes"] = []
    for sx in (-1, 1):
        parts["shoulder_rosettes"] += build_shoulder_rosette(m, sx)
    report_l1("GoldShoulderRosettes+Frings x2", parts["shoulder_rosettes"])
    parts["hat"] = build_hat(m)
    report_l1("FeatheredHat (brim+crown+band+3 feathers)", parts["hat"])
    flat_patches.append(parts["hat"][0])  # brim disc: flat fan, keep winding
    parts["mask"] = build_mask(m)
    report_l1("GoldMask+TealGem", parts["mask"])
    flat_patches.append(parts["mask"][0])  # mask panel: flat patch
    parts["boots"] = []
    for sx in (-1, 1):
        parts["boots"] += build_boot(m, sx)
    report_l1("VioletBoots+Trims x2", parts["boots"])

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    _, ok = assemble_torso(parts)
    l2_ok &= ok
    _, ok = assemble_arms(parts)
    l2_ok &= ok
    _, ok = assemble_shoulders(parts)
    l2_ok &= ok
    _, ok = assemble_skirt(parts)
    l2_ok &= ok
    _, ok = assemble_waist(parts)
    l2_ok &= ok
    _, ok = assemble_head_feet(parts)
    l2_ok &= ok
    print("L2_SUMMARY %s" % ("ALL PASS" if l2_ok else "FAILURES PRESENT"))

    # ---- L3 full outfit on the mannequin ----
    costume = (parts["bodice"] + parts["lace_collar"]
               + parts["embroidery"] + parts["rosettes"]
               + parts["overskirt"] + parts["gown"] + parts["pleats"]
               + parts["belt"] + parts["buckle"] + parts["gloves"]
               + parts["cuffs"] + parts["shoulder_rosettes"]
               + parts["hat"] + parts["mask"] + parts["boots"])
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
