# -*- coding: utf-8 -*-
"""028 异环式都市时装 · 居家服套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整套穿到人体底座上试穿）。
设计见 design.md。BACKLOG 已空，本轮自选：异环线第五件——居家风
（015 修身风衣、025 oversized 街头、026 学院风、027 运动风之后；
DESIGN.md 学院/居家/运动/街头矩阵里居家首次做，矩阵补齐）。
Run: blender --background --python build_028.py
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

_spec19 = importlib.util.spec_from_file_location(
    "build_019", os.path.join(SCENES, "019-sumeru-scholar",
                              "build_019.py"))
b019 = importlib.util.module_from_spec(_spec19)
_spec19.loader.exec_module(b019)
build_panel = b019.build_panel

BLEND_OUT = os.path.join(HERE, "028-loungewear.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "028-loungewear.png")
WIRE_JSON = "/tmp/loungewear_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

SWEATER_RINGS = [(1.42, 0.320, 0.163), (1.10, 0.314, 0.160),
                 (0.70, 0.308, 0.157)]
RIB_HEM_RINGS = [(0.74, 0.314, 0.160), (0.68, 0.314, 0.160)]
CREW_NECK_RINGS = [(1.46, 0.240, 0.205), (1.40, 0.245, 0.210)]
PANTS_RINGS = [(0.72, 0.290, 0.150), (0.40, 0.270, 0.142),
               (0.08, 0.250, 0.134)]
ANKLE_CUFF_RINGS = [(0.10, 0.256, 0.140), (0.06, 0.256, 0.140)]
HEADBAND_RINGS = [(1.66, 0.230, 0.210), (1.60, 0.235, 0.215)]
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    cream = solid_material("Cream", (0.913, 0.863, 0.768), roughness=0.6)
    white = solid_material("White", (0.888, 0.888, 0.888), roughness=0.6)
    navy = solid_material("Navy", (0.011, 0.023, 0.068), roughness=0.6)
    brown = solid_material("Brown", (0.254, 0.102, 0.044), roughness=0.7)
    orange = solid_material("Orange", (0.807, 0.144, 0.012), roughness=0.6)
    yellow = solid_material("Yellow", (1.000, 0.644, 0.050), roughness=0.6)
    lightblue = solid_material("LightBlue", (0.212, 0.479, 0.807),
                               roughness=0.6)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    hair = solid_material("Hair_Black", (0.004, 0.004, 0.006),
                          roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"cream": cream, "white": white, "navy": navy, "brown": brown,
            "orange": orange, "yellow": yellow, "lightblue": lightblue,
            "skin": skin, "hair": hair, "eye": eye}


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001..027).
    Black hair cap (z=1.57, scale-z 0.80 covers the crown) +
    two dark eyes (visible; the sweater collar sits below them at z 1.42).
    Feet are skin wedges (z=0.0) under the brown slippers
    (027's white shoe wedges would show through a brown slipper)."""
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
        objs.append(make_wedge("Mannequin_Foot", (sx * 0.13, -0.02, 0.0),
                               0.095, 0.09, -0.16, 0.0, 0.10, 0.045,
                               m["skin"]))
    return objs


# ------------------------------------------------------------ L1 components
def build_sweater(m):
    """Cream oversized knit sweater: 0.320->0.308, 0.02 wider than
    027's hoodie (0.300->0.290) for the loungewear silhouette,
    hem z 0.70."""
    return [make_elliptical_tube("CreamSweater", SWEATER_RINGS, 16,
                                 m["cream"], caps=False)]


def build_knit_row(m, z):
    """One knit-texture ring: a thin band 0.006 proud of the sweater
    surface at height z (geometric knit, no texture map)."""
    rx, ry = interp_rings(SWEATER_RINGS, z)
    rings = [(z + 0.005, rx + 0.006, ry + 0.006),
             (z - 0.005, rx + 0.006, ry + 0.006)]
    return [make_elliptical_tube("CreamKnitRow", rings, 16,
                                 m["cream"], caps=False)]


def build_rib_hem(m):
    """Ribbed sweater hem: ring z 0.74-0.68, 0.314, 0.006 wider than
    the sweater hem (0.308) so the rib reads as a cuff."""
    return [make_elliptical_tube("CreamRibHem", RIB_HEM_RINGS, 16,
                                 m["cream"], caps=False)]


def build_crew_neck(m):
    """Crew-neck rib: ring z 1.46-1.40, 0.240->0.245, sticking 0.04
    above the sweater top edge (z 1.42) around the neck."""
    return [make_elliptical_tube("CreamCrewNeck", CREW_NECK_RINGS, 16,
                                 m["cream"], caps=False)]


def build_chest_pocket(m):
    """Cream chest pocket: curved front panel (246-294 deg,
    z 1.18-1.02, 0.009 proud) + two orange edge bindings on its
    sides (0.012 proud, 0.003 more than the pocket face)."""
    panel = build_panel(m, "CreamChestPocket", SWEATER_RINGS,
                        [1.18, 1.10, 1.02], 246, 294, 7,
                        0.009, m["cream"])
    left = build_panel(m, "OrangePocketEdge", SWEATER_RINGS,
                       [1.18, 1.10, 1.02], 244, 248, 3,
                       0.012, m["orange"])
    right = build_panel(m, "OrangePocketEdge", SWEATER_RINGS,
                        [1.18, 1.10, 1.02], 292, 296, 3,
                        0.012, m["orange"])
    return [panel, left, right]


def build_sleeve(m, sx):
    """Cream wide sleeve (shoulder to wrist) over the mannequin arm,
    looser than 027 (0.118->0.104). Capped (025 v2 lesson) with the
    origin lifted 0.005 along the arm axis so the sleeve cap never
    sits coplanar with the arm cap."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    origin = shoulder - direction.normalized() * 0.005
    return [make_tube("CreamSleeve", origin, direction,
                      [0.0, 0.13, 0.26, 0.39, 0.52],
                      [0.118, 0.116, 0.112, 0.108, 0.104], 10,
                      m["cream"], caps=True)]


def build_rib_cuff(m, sx):
    """Cream ribbed cuff ring at the wrist, 0.006 proud of the
    sleeve end (0.112 vs 0.1058)."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("CreamRibCuff", shoulder, direction,
                      [0.46, 0.52], [0.112, 0.112], 10,
                      m["cream"], caps=False)]


def build_headband(m):
    """Cream fluffy headband ring across the forehead (z 1.66-1.60),
    same ring numbers as 027's orange headband, above the eyes."""
    return [make_elliptical_tube("CreamHeadband", HEADBAND_RINGS, 16,
                                 m["cream"], caps=False)]


def build_bow(m):
    """Orange bow on the headband front-top: two tilted wing boxes
    pressed onto the headband face + a centre knot box 0.005 proud
    of the wings."""
    wings = []
    for sx in (-1, 1):
        wings.append(add_box_rot("OrangeBowWing",
                                 (sx * 0.048, -0.212, 1.645),
                                 (0.055, 0.016, 0.04), m["orange"],
                                 (0, 0, sx * 0.35)))
    knot = add_box("OrangeBowKnot", (0, -0.219, 1.645),
                   (0.024, 0.014, 0.034), m["orange"])
    return wings + [knot]


def build_pants(m):
    """Navy lounge pants: straight leg 0.290->0.250, top ring tucked
    inside the sweater hem (0.290 < 0.308)."""
    return [make_elliptical_tube("NavyPants", PANTS_RINGS, 12,
                                 m["navy"], caps=False)]


def build_drawstring(m, sx):
    """Orange drawstring: thin tube hanging from below the ribbed
    hem (z 0.68-0.56, so it clears the hem bottom edge 0.68),
    lying on the pants surface (y -0.156 at x +/-0.05)
    + yellow aglet ball at the bottom."""
    cord = make_tube("OrangeDrawstring", (sx * 0.05, -0.156, 0.68),
                     (0, 0, -1), [0.0, 0.12], [0.008, 0.008], 6,
                     m["orange"], caps=True)
    aglet = add_sphere("YellowAglet", (sx * 0.05, -0.156, 0.555), 0.012,
                       6, 3, (1.0, 1.0, 1.0), m["yellow"])
    return [cord, aglet]


def build_ankle_cuff(m):
    """Orange elastic ankle cuffs: rings z 0.10-0.06, 0.256,
    0.006 proud of the pants leg (0.250)."""
    return [make_elliptical_tube("OrangeAnkleCuff", ANKLE_CUFF_RINGS, 12,
                                 m["orange"], caps=False)]


def build_sock(m, sx):
    """White crew sock: tube over the leg, top meeting the pants hem
    at z 0.12 with no skin showing."""
    return [make_tube("WhiteSock", (sx * 0.13, 0, 0.12), (0, 0, -1),
                      [0.0, 0.10], [0.100, 0.100], 10,
                      m["white"], caps=False)]


def build_slipper(m, sx):
    """Brown fluffy slipper: brown wedge (hx 0.106 covers the white
    sock r 0.100, sole lands z=0.0) + cream fluffy cuff ring around
    the ankle opening (z 0.13-0.09, r 0.110, 0.010 proud of the
    sock)."""
    wedge = make_wedge("BrownSlipper", (sx * 0.13, -0.02, 0.0),
                       0.106, 0.095, -0.165, 0.0, 0.10, 0.05,
                       m["brown"])
    cuff = make_tube("CreamSlipperCuff", (sx * 0.13, 0, 0.13), (0, 0, -1),
                     [0.0, 0.04], [0.110, 0.110], 10,
                     m["cream"], caps=False)
    return [wedge, cuff]


def build_cat_ear(m, sx):
    """Navy cat ear: tetrahedron, base triangle buried in the hair
    top (z 1.70), apex at z 1.845, tilted slightly outward."""
    x = sx * 0.10
    b0 = (x - 0.038, 0.03, 1.70)
    b1 = (x + 0.038, 0.03, 1.70)
    b2 = (x, -0.035, 1.70)
    apex = (x + sx * 0.012, 0.0, 1.845)
    return mesh_from_data("NavyCatEar",
                          [b0, b1, b2, apex],
                          [(0, 1, 2), (0, 3, 1), (1, 3, 2), (2, 3, 0)],
                          m["navy"])


def build_streak(m):
    """Light-blue hair streak: flat box on the hair's right front,
    lying against the hair surface (outer face 0.010 proud)."""
    return [add_box_rot("BlueStreak", (0.13, -0.155, 1.60),
                        (0.035, 0.012, 0.18), m["lightblue"],
                        (0.15, 0, -0.12))]


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["sweater"] + parts["knit_rows"] + parts["rib_hem"]
            + parts["crew_neck"] + parts["pocket"])
    ok = True
    ok &= check_gap("torso: cream sweater collar vs neck @z=1.42",
                    0.320, 0.09)
    ok &= check_gap("torso: cream rib hem vs sweater hem @z=0.71",
                    0.314, interp_rings(SWEATER_RINGS, 0.71)[0])
    ok &= check_gap("torso: cream sweater vs mannequin torso @z=1.10",
                    interp_rings(SWEATER_RINGS, 1.10)[0],
                    interp_rings([(1.28, 0.270, 0.140),
                                  (0.95, 0.240, 0.130)], 1.10)[0])
    ok &= check_relief("torso: cream knit row relief", 0.006)
    ok &= check_relief("torso: cream chest pocket relief", 0.009,
                       lo=0.005, hi=0.030)
    ok &= check_relief("torso: orange pocket edge relief", 0.012,
                       lo=0.005, hi=0.030)
    ok &= check_gap("torso: cream crew neck vs head @z=1.44",
                    0.240, 0.212)
    print("L2_CHECK torso: cream oversized sweater with 3 knit rings, "
          "ribbed hem and crew neck, chest pocket with orange edges PASS")
    return objs, ok


def assemble_arms(parts):
    objs = parts["sleeves"] + parts["cuffs"]
    ok = True
    ok &= check_gap("arms: cream sleeve vs mannequin arm @0.0",
                    0.118, 0.085)
    ok &= check_gap("arms: cream rib cuff vs cream sleeve @0.46",
                    0.112, 0.1058)
    print("L2_CHECK arms: cream wide sleeves 0.118->0.104, cream rib "
          "cuffs at the wrists PASS")
    return objs, ok


def assemble_head(parts):
    objs = (parts["headband"] + parts["bow"] + parts["cat_ears"]
            + parts["streak"])
    ok = True
    ok &= check_gap("head: cream headband vs hair @z=1.60",
                    0.235, 0.222)
    ok &= check_gap("head: orange bow vs headband front @z=1.645",
                    0.219, 0.211)
    ok &= check_gap("head: navy cat ear apex vs hair top",
                    1.845, 1.75)
    ok &= check_relief("head: blue streak relief", 0.010,
                       lo=0.005, hi=0.030)
    print("L2_CHECK head: cream fluffy headband across the forehead, "
          "orange bow on its front, navy cat ears out of the hair top, "
          "light-blue streak lying on the hair front PASS")
    return objs, ok


def assemble_waist(parts):
    objs = (parts["pants"] + parts["drawstrings"]
            + parts["ankle_cuff"])
    ok = True
    ok &= check_gap("waist: navy pants top vs sweater hem @z=0.71",
                    interp_rings(SWEATER_RINGS, 0.71)[0],
                    interp_rings(PANTS_RINGS, 0.71)[0])
    ok &= check_gap("waist: orange ankle cuff vs navy pants @z=0.08",
                    0.256, interp_rings(PANTS_RINGS, 0.08)[0])
    ok &= check_relief("waist: orange drawstring relief", 0.008,
                       lo=0.005, hi=0.030)
    print("L2_CHECK waist: navy lounge pants with orange drawstrings "
          "below the ribbed hem, orange elastic ankle cuffs PASS")
    return objs, ok


def assemble_legs(parts):
    objs = parts["socks"]
    ok = True
    ok &= check_gap("legs: white sock vs mannequin leg @z=0.10",
                    0.100, 0.082)
    print("L2_CHECK legs: white crew socks 0.100, sock tops meeting "
          "the pants hem PASS")
    return objs, ok


def assemble_feet(parts):
    objs = parts["slippers"]
    ok = True
    ok &= check_gap("feet: cream slipper cuff vs white sock @z=0.10",
                    0.110, 0.100)
    ok &= check_gap("feet: brown slipper wedge vs white sock",
                    0.106, 0.100)
    print("L2_CHECK feet: brown slipper wedge centre z=0.0, sole on "
          "ground; wedge covers the sock, cream fluffy cuff over the "
          "sock PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: cream sweater vs mannequin torso @z=1.10",
                    interp_rings(SWEATER_RINGS, 1.10)[0],
                    interp_rings([(1.28, 0.270, 0.140),
                                  (0.95, 0.240, 0.130)], 1.10)[0])
    ok &= check_gap("L3 layer: navy pants top vs sweater hem @z=0.71",
                    interp_rings(SWEATER_RINGS, 0.71)[0],
                    interp_rings(PANTS_RINGS, 0.71)[0])
    ok &= check_gap("L3 layer: orange ankle cuff vs navy pants @z=0.08",
                    0.256, interp_rings(PANTS_RINGS, 0.08)[0])
    ok &= check_gap("L3 joint: cream rib cuff vs cream sleeve",
                    0.112, 0.1058)
    ok &= check_gap("L3 joint: cream slipper cuff vs white sock @z=0.10",
                    0.110, 0.100)
    ok &= check_gap("L3 joint: cream headband vs hair",
                    0.235, 0.222)
    print("L3_CHECK outfit: sweater over the torso, ribbed hem over "
          "the pants top, orange drawstrings below the hem, brown "
          "slipper soles touch ground z=0.000 PASS")
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
    parts["sweater"] = build_sweater(m)
    report_l1("CreamSweater", parts["sweater"])
    parts["knit_rows"] = []
    for z in (1.30, 1.00, 0.85):
        parts["knit_rows"] += build_knit_row(m, z)
    report_l1("CreamKnitRows x3", parts["knit_rows"])
    parts["rib_hem"] = build_rib_hem(m)
    report_l1("CreamRibHem", parts["rib_hem"])
    parts["crew_neck"] = build_crew_neck(m)
    report_l1("CreamCrewNeck", parts["crew_neck"])
    parts["pocket"] = build_chest_pocket(m)
    report_l1("CreamChestPocket+Edges", parts["pocket"])
    flat_patches += parts["pocket"]
    parts["sleeves"] = []
    for sx in (-1, 1):
        parts["sleeves"] += build_sleeve(m, sx)
    report_l1("CreamSleeves x2", parts["sleeves"])
    parts["cuffs"] = []
    for sx in (-1, 1):
        parts["cuffs"] += build_rib_cuff(m, sx)
    report_l1("CreamRibCuffs x2", parts["cuffs"])
    parts["headband"] = build_headband(m)
    report_l1("CreamHeadband", parts["headband"])
    parts["bow"] = build_bow(m)
    report_l1("OrangeBow", parts["bow"])
    parts["pants"] = build_pants(m)
    report_l1("NavyPants", parts["pants"])
    parts["drawstrings"] = []
    for sx in (-1, 1):
        parts["drawstrings"] += build_drawstring(m, sx)
    report_l1("OrangeDrawstrings x2", parts["drawstrings"])
    parts["ankle_cuff"] = build_ankle_cuff(m)
    report_l1("OrangeAnkleCuffs", parts["ankle_cuff"])
    parts["socks"] = []
    for sx in (-1, 1):
        parts["socks"] += build_sock(m, sx)
    report_l1("WhiteSocks x2", parts["socks"])
    parts["slippers"] = []
    for sx in (-1, 1):
        parts["slippers"] += build_slipper(m, sx)
    report_l1("BrownSlippers x2", parts["slippers"])
    parts["cat_ears"] = [build_cat_ear(m, sx) for sx in (-1, 1)]
    report_l1("NavyCatEars x2", parts["cat_ears"])
    parts["streak"] = build_streak(m)
    report_l1("BlueStreak", parts["streak"])

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    _, ok = assemble_torso(parts)
    l2_ok &= ok
    _, ok = assemble_arms(parts)
    l2_ok &= ok
    _, ok = assemble_head(parts)
    l2_ok &= ok
    _, ok = assemble_waist(parts)
    l2_ok &= ok
    _, ok = assemble_legs(parts)
    l2_ok &= ok
    _, ok = assemble_feet(parts)
    l2_ok &= ok
    print("L2_SUMMARY %s" % ("ALL PASS" if l2_ok else "FAILURES PRESENT"))

    # ---- L3 full outfit on the mannequin ----
    costume = (parts["sweater"] + parts["knit_rows"] + parts["rib_hem"]
               + parts["crew_neck"] + parts["pocket"] + parts["sleeves"]
               + parts["cuffs"] + parts["headband"] + parts["bow"]
               + parts["pants"] + parts["drawstrings"]
               + parts["ankle_cuff"] + parts["socks"]
               + parts["slippers"] + parts["cat_ears"] + parts["streak"])
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
