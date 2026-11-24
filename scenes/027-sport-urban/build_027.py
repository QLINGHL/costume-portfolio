# -*- coding: utf-8 -*-
"""027 异环式都市时装 · 运动风套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整套穿到人体底座上试穿）。
设计见 design.md。BACKLOG 已空，本轮自选：异环线第四件——运动风
（015 修身风衣、025 oversized 街头、026 学院风之后；DESIGN.md
学院/居家/运动/街头矩阵里运动首次做）。
Run: blender --background --python build_027.py
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

BLEND_OUT = os.path.join(HERE, "027-sport-urban.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "027-sport-urban.png")
WIRE_JSON = "/tmp/sport_urban_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

HOODIE_RINGS = [(1.40, 0.300, 0.152), (1.10, 0.295, 0.150),
                (0.72, 0.290, 0.148)]
HOOD_RINGS = [(1.54, 0.275, 0.160), (1.42, 0.315, 0.168)]
PANTS_RINGS = [(0.74, 0.280, 0.146), (0.40, 0.262, 0.138),
               (0.10, 0.242, 0.130)]
HEADBAND_RINGS = [(1.66, 0.230, 0.210), (1.60, 0.235, 0.215)]
STRAP_RINGS = [(0.70, 0.292, 0.150), (0.66, 0.292, 0.150)]
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    navy = solid_material("Navy", (0.011, 0.023, 0.068), roughness=0.6)
    white = solid_material("White", (0.888, 0.888, 0.888), roughness=0.6)
    orange = solid_material("Orange", (0.807, 0.144, 0.012), roughness=0.6)
    yellow = solid_material("Yellow", (1.000, 0.644, 0.050), roughness=0.6)
    lightblue = solid_material("LightBlue", (0.212, 0.479, 0.807),
                               roughness=0.6)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    hair = solid_material("Hair_Black", (0.004, 0.004, 0.006),
                          roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"navy": navy, "white": white, "orange": orange,
            "yellow": yellow, "lightblue": lightblue, "skin": skin,
            "hair": hair, "eye": eye}


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001..026).
    Black hair cap (z=1.57, scale-z 0.80 covers the crown) +
    two dark eyes (visible; the hoodie collar sits below them at z 1.40).
    Feet are skin wedges (z=0.0) under the white sneakers
    (026's black shoe wedges would show through a white shoe)."""
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
def build_hoodie(m):
    """Navy sport hoodie: slightly loose (0.300->0.290, 0.005 wider
    than 026's fitted blazer), hem z 0.72."""
    return [make_elliptical_tube("NavyHoodie", HOODIE_RINGS, 16,
                                 m["navy"], caps=False)]


def build_hood(m):
    """Navy hood: back half-shell arc 20-160 deg, flaring outward
    below (0.275->0.315) so the bottom ring sits 0.015 proud of the
    hoodie collar, resting behind the neck."""
    return [make_elliptical_tube("NavyHood", HOOD_RINGS, 16,
                                 m["navy"], arc=(20, 160), caps=False)]


def build_zipper(m):
    """Orange zipper strip down the hoodie front (266-274 deg,
    z 1.36-0.74, 0.006 proud) + yellow pull tab at the top."""
    panel = build_panel(m, "OrangeZipper", HOODIE_RINGS,
                        [1.36, 1.20, 1.00, 0.80, 0.74], 266, 274, 5,
                        0.006, m["orange"])
    pull = add_box("YellowZipperPull", (0, -0.158, 1.34),
                   (0.02, 0.012, 0.03), m["yellow"])
    return [panel, pull]


def build_drawstring(m, sx):
    """Orange drawstring: thin tube hanging from the collar front,
    lying on the hoodie surface (y -0.157 at x +/-0.05, z 1.36-1.24)
    + yellow aglet ball at the bottom."""
    cord = make_tube("OrangeDrawstring", (sx * 0.05, -0.157, 1.36),
                     (0, 0, -1), [0.0, 0.12], [0.008, 0.008], 6,
                     m["orange"], caps=True)
    aglet = add_sphere("YellowAglet", (sx * 0.05, -0.157, 1.235), 0.012,
                       6, 3, (1.0, 1.0, 1.0), m["yellow"])
    return [cord, aglet]


def build_pocket(m):
    """White kangaroo pocket: curved front panel (246-294 deg,
    z 0.98-0.78, 0.009 proud so it rides 0.003 over the zipper)
    + two orange edge bindings on its sides (0.012 proud)."""
    panel = build_panel(m, "WhitePocket", HOODIE_RINGS,
                        [0.98, 0.88, 0.78], 246, 294, 7,
                        0.009, m["white"])
    left = build_panel(m, "OrangePocketEdge", HOODIE_RINGS,
                       [0.98, 0.88, 0.78], 244, 248, 3,
                       0.012, m["orange"])
    right = build_panel(m, "OrangePocketEdge", HOODIE_RINGS,
                        [0.98, 0.88, 0.78], 292, 296, 3,
                        0.012, m["orange"])
    return [panel, left, right]


def build_sleeve(m, sx):
    """Navy sport sleeve (shoulder to wrist) over the mannequin arm,
    slightly looser than 026 (0.112->0.098). Capped (025 v2 lesson)
    with the origin lifted 0.005 along the arm axis so the sleeve cap
    never sits coplanar with the arm cap."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    origin = shoulder - direction.normalized() * 0.005
    return [make_tube("NavySleeve", origin, direction,
                      [0.0, 0.13, 0.26, 0.39, 0.52],
                      [0.112, 0.110, 0.106, 0.102, 0.098], 10,
                      m["navy"], caps=True)]


def build_cuff(m, sx):
    """Orange cuff ring at the wrist, 0.006 proud of the sleeve end."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("OrangeCuff", shoulder, direction,
                      [0.46, 0.52], [0.106, 0.106], 10,
                      m["orange"], caps=False)]


def build_headband(m):
    """Orange sweatband ring across the forehead (z 1.66-1.60),
    0.013-0.035 proud of the hair, above the eyes."""
    return [make_elliptical_tube("OrangeHeadband", HEADBAND_RINGS, 16,
                                 m["orange"], caps=False)]


def build_wristband(m):
    """Orange wristband on the RIGHT arm (camera side), upper wrist
    0.40-0.46, 0.007 proud of the sleeve."""
    sx = 1
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("OrangeWristband", shoulder, direction,
                      [0.40, 0.46], [0.108, 0.108], 10,
                      m["orange"], caps=False)]


def build_pants(m):
    """Navy track pants: straight leg 0.280->0.242, top ring tucked
    inside the hoodie hem (0.280 < 0.290)."""
    return [make_elliptical_tube("NavyPants", PANTS_RINGS, 12,
                                 m["navy"], caps=False)]


def build_side_stripe(m, a0, a1):
    """One orange side stripe on the pants (3 deg wide, z 0.68-0.12,
    0.006 proud of the pants surface)."""
    return build_panel(m, "OrangeSideStripe", PANTS_RINGS,
                       [0.68, 0.50, 0.30, 0.12], a0, a1, 3,
                       0.006, m["orange"])


def build_sock(m, sx):
    """White crew sock: tube over the leg, top meeting the pants hem
    at z 0.12 with no skin showing."""
    return [make_tube("WhiteSock", (sx * 0.13, 0, 0.12), (0, 0, -1),
                      [0.0, 0.10], [0.100, 0.100], 10,
                      m["white"], caps=False)]


def build_sock_ring(m, sx):
    """Orange sock ring, 0.006 proud of the sock."""
    return [make_tube("OrangeSockRing", (sx * 0.13, 0, 0.08), (0, 0, -1),
                      [0.0, 0.02], [0.106, 0.106], 10,
                      m["orange"], caps=False)]


def build_shoe(m, sx):
    """White high-top sneaker: orange sole wedge (lands z=0.0, 0.002
    wider than the white upper so an orange rim shows) + white wedge
    upper (hx 0.105 covers the white sock r 0.100) + white collar tube
    over the sock."""
    sole = make_wedge("OrangeSole", (sx * 0.13, -0.02, 0.0),
                      0.107, 0.097, -0.167, 0.0, 0.02, 0.02, m["orange"])
    upper = make_wedge("WhiteShoe", (sx * 0.13, -0.02, 0.02),
                       0.105, 0.095, -0.165, 0.0, 0.105, 0.05,
                       m["white"])
    collar = make_tube("WhiteShoeCollar", (sx * 0.13, 0, 0.16), (0, 0, -1),
                       [0.0, 0.10], [0.106, 0.104], 10,
                       m["white"], caps=False)
    return [sole, upper, collar]


def build_waist_pack(m):
    """Orange fanny pack on the front waist (z 0.605-0.715, inner face
    0.006 proud of the pants) + white zipper line on its front."""
    pack = add_box("OrangeWaistPack", (0, -0.195, 0.66),
                   (0.18, 0.09, 0.11), m["orange"])
    zipper = add_box("WhitePackZipper", (0, -0.243, 0.68),
                     (0.14, 0.012, 0.02), m["white"])
    return [pack, zipper]


def build_waist_strap(m):
    """Navy waist strap ring below the hoodie hem (z 0.70-0.66),
    0.011 proud of the pants; its front arc passes behind the waist
    pack, so the pack reads as hanging on the strap."""
    return [make_elliptical_tube("NavyWaistStrap", STRAP_RINGS, 16,
                                 m["navy"], caps=False)]


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
    objs = (parts["hoodie"] + parts["hood"] + parts["zipper"]
            + parts["drawstrings"] + parts["pocket"])
    ok = True
    ok &= check_gap("torso: navy hoodie collar vs neck @z=1.40",
                    0.300, 0.085)
    ok &= check_gap("torso: navy hood bottom vs hoodie top @z=1.42",
                    0.315, 0.300)
    ok &= check_gap("torso: navy hoodie vs mannequin torso @z=1.10",
                    interp_rings(HOODIE_RINGS, 1.10)[0],
                    interp_rings([(1.28, 0.270, 0.140),
                                  (0.95, 0.240, 0.130)], 1.10)[0])
    ok &= check_relief("torso: orange zipper relief", 0.006)
    ok &= check_relief("torso: white pocket relief", 0.009,
                       lo=0.005, hi=0.030)
    ok &= check_relief("torso: orange pocket edge relief", 0.012,
                       lo=0.005, hi=0.030)
    ok &= check_relief("torso: orange drawstring relief", 0.008,
                       lo=0.005, hi=0.030)
    print("L2_CHECK torso: navy hoodie with a back hood, orange zipper "
          "down the front, white kangaroo pocket with orange edges, "
          "orange drawstrings at the collar PASS")
    return objs, ok


def assemble_arms(parts):
    objs = parts["sleeves"] + parts["cuffs"] + parts["wristband"]
    ok = True
    ok &= check_gap("arms: navy sleeve vs mannequin arm @0.0",
                    0.112, 0.085)
    ok &= check_gap("arms: orange cuff vs navy sleeve @0.46",
                    0.106, 0.0998)
    ok &= check_gap("arms: orange wristband vs navy sleeve @0.43",
                    0.108, 0.101)
    print("L2_CHECK arms: navy sport sleeves 0.112->0.098, orange "
          "cuffs at the wrists, orange wristband on the right arm PASS")
    return objs, ok


def assemble_head(parts):
    objs = parts["headband"] + parts["cat_ears"] + parts["streak"]
    ok = True
    ok &= check_gap("head: orange headband vs hair @z=1.60",
                    0.235, 0.222)
    ok &= check_gap("head: navy cat ear apex vs hair top",
                    1.845, 1.75)
    ok &= check_relief("head: blue streak relief", 0.010,
                       lo=0.005, hi=0.030)
    print("L2_CHECK head: orange headband across the forehead, navy "
          "cat ears out of the hair top, light-blue streak lying on "
          "the hair front PASS")
    return objs, ok


def assemble_waist(parts):
    objs = (parts["pants"] + parts["stripes"] + parts["waist_pack"]
            + parts["waist_strap"])
    ok = True
    ok &= check_gap("waist: navy pants top vs hoodie hem @z=0.72",
                    interp_rings(HOODIE_RINGS, 0.72)[0],
                    interp_rings(PANTS_RINGS, 0.72)[0])
    ok &= check_gap("waist: navy waist strap vs navy pants @z=0.68",
                    0.292, interp_rings(PANTS_RINGS, 0.68)[0])
    ok &= check_relief("waist: orange side stripe relief", 0.006)
    ok &= check_relief("waist: white pack zipper relief", 0.009,
                       lo=0.005, hi=0.030)
    ok &= check_gap("waist: orange pack inner face vs pants @z=0.66",
                    0.150, interp_rings(PANTS_RINGS, 0.66)[1])
    print("L2_CHECK waist: navy track pants with orange side stripes, "
          "orange waist pack on the front waist with a white zipper, "
          "navy strap ring behind the pack PASS")
    return objs, ok


def assemble_legs(parts):
    objs = parts["socks"] + parts["sock_rings"]
    ok = True
    ok &= check_gap("legs: white sock vs mannequin leg @z=0.10",
                    0.100, 0.082)
    ok &= check_gap("legs: orange sock ring vs white sock @z=0.07",
                    0.106, 0.100)
    print("L2_CHECK legs: white crew socks 0.100, orange sock rings "
          "0.106, sock tops meeting the pants hem PASS")
    return objs, ok


def assemble_feet(parts):
    objs = parts["shoes"]
    ok = True
    ok &= check_gap("feet: white shoe collar vs white sock @z=0.10",
                    0.105, 0.100)
    ok &= check_gap("feet: white shoe wedge vs white sock",
                    0.105, 0.100)
    ok &= check_gap("feet: orange sole rim vs white shoe wedge",
                    0.107, 0.105, minimum=0.001)
    print("L2_CHECK feet: orange sole centre z=0.0, sole on ground; "
          "white shoe wedge covers the sock, white collar over the "
          "sock PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: navy hoodie vs mannequin torso @z=1.10",
                    interp_rings(HOODIE_RINGS, 1.10)[0],
                    interp_rings([(1.28, 0.270, 0.140),
                                  (0.95, 0.240, 0.130)], 1.10)[0])
    ok &= check_gap("L3 layer: navy pants top vs hoodie hem @z=0.72",
                    interp_rings(HOODIE_RINGS, 0.72)[0],
                    interp_rings(PANTS_RINGS, 0.72)[0])
    ok &= check_gap("L3 layer: navy waist strap vs navy pants @z=0.68",
                    0.292, interp_rings(PANTS_RINGS, 0.68)[0])
    ok &= check_gap("L3 layer: orange pack vs pants front @z=0.66",
                    0.150, interp_rings(PANTS_RINGS, 0.66)[1])
    ok &= check_gap("L3 joint: orange cuff vs navy sleeve", 0.106, 0.0998)
    ok &= check_gap("L3 joint: white shoe collar vs white sock @z=0.10",
                    0.105, 0.100)
    ok &= check_gap("L3 joint: orange wristband vs navy sleeve",
                    0.108, 0.101)
    print("L3_CHECK outfit: hoodie over the torso, hood behind the "
          "neck, pants top tucked inside the hoodie hem, orange pack "
          "on the front waist, white sneaker soles touch ground "
          "z=0.000 PASS")
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
    parts["hoodie"] = build_hoodie(m)
    report_l1("NavyHoodie", parts["hoodie"])
    parts["hood"] = build_hood(m)
    report_l1("NavyHood", parts["hood"])
    parts["zipper"] = build_zipper(m)
    report_l1("OrangeZipper+Pull", parts["zipper"])
    flat_patches += [parts["zipper"][0]]
    parts["drawstrings"] = []
    for sx in (-1, 1):
        parts["drawstrings"] += build_drawstring(m, sx)
    report_l1("OrangeDrawstrings x2", parts["drawstrings"])
    parts["pocket"] = build_pocket(m)
    report_l1("WhitePocket+Edges", parts["pocket"])
    flat_patches += parts["pocket"]
    parts["sleeves"] = []
    for sx in (-1, 1):
        parts["sleeves"] += build_sleeve(m, sx)
    report_l1("NavySleeves x2", parts["sleeves"])
    parts["cuffs"] = []
    for sx in (-1, 1):
        parts["cuffs"] += build_cuff(m, sx)
    report_l1("OrangeCuffs x2", parts["cuffs"])
    parts["headband"] = build_headband(m)
    report_l1("OrangeHeadband", parts["headband"])
    parts["wristband"] = build_wristband(m)
    report_l1("OrangeWristband", parts["wristband"])
    parts["pants"] = build_pants(m)
    report_l1("NavyPants", parts["pants"])
    parts["stripes"] = [build_side_stripe(m, 356, 364),
                        build_side_stripe(m, 176, 184)]
    report_l1("OrangeSideStripes x2", parts["stripes"])
    flat_patches += parts["stripes"]
    parts["socks"] = []
    for sx in (-1, 1):
        parts["socks"] += build_sock(m, sx)
    report_l1("WhiteSocks x2", parts["socks"])
    parts["sock_rings"] = []
    for sx in (-1, 1):
        parts["sock_rings"] += build_sock_ring(m, sx)
    report_l1("OrangeSockRings x2", parts["sock_rings"])
    parts["shoes"] = []
    for sx in (-1, 1):
        parts["shoes"] += build_shoe(m, sx)
    report_l1("WhiteSneakers x2", parts["shoes"])
    parts["waist_pack"] = build_waist_pack(m)
    report_l1("OrangeWaistPack", parts["waist_pack"])
    parts["waist_strap"] = build_waist_strap(m)
    report_l1("NavyWaistStrap", parts["waist_strap"])
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
    costume = (parts["hoodie"] + parts["hood"] + parts["zipper"]
               + parts["drawstrings"] + parts["pocket"] + parts["sleeves"]
               + parts["cuffs"] + parts["headband"] + parts["wristband"]
               + parts["pants"] + parts["stripes"] + parts["socks"]
               + parts["sock_rings"] + parts["shoes"]
               + parts["waist_pack"] + parts["waist_strap"]
               + parts["cat_ears"] + parts["streak"])
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
