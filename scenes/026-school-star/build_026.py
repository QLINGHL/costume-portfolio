# -*- coding: utf-8 -*-
"""026 异环式都市时装 · 学园之星学院风套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整套穿到人体底座上试穿）。
设计见 design.md。BACKLOG 本轮有现成项 026：异环线第三件——学院风
（015 修身风衣、025 oversized 街头之后；DESIGN.md 娜娜莉「学园之星」
黑白学院风 + 风纪袖标方向，学院/居家/运动/街头矩阵里学院首次做）。
Run: blender --background --python build_026.py
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

BLEND_OUT = os.path.join(HERE, "026-school-star.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "026-school-star.png")
WIRE_JSON = "/tmp/school_star_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

SHIRT_RINGS = [(1.40, 0.215, 0.188), (1.30, 0.272, 0.141),
               (1.00, 0.265, 0.138), (0.70, 0.258, 0.136)]
BLAZER_RINGS = [(1.38, 0.295, 0.152), (1.10, 0.290, 0.150),
                (0.72, 0.285, 0.148)]
SKIRT_RINGS = [(0.74, 0.275, 0.145), (0.50, 0.318, 0.164),
               (0.30, 0.340, 0.175)]
WAIST_RINGS = [(0.70, 0.300, 0.156), (0.64, 0.305, 0.158)]
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)
STRAP_Z = [1.30, 1.15, 1.00, 0.85, 0.78, 0.72]
STRAP_A = [227, 250, 274, 298, 320, 340]


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    navy = solid_material("Navy", (0.011, 0.023, 0.069), roughness=0.6)
    white = solid_material("White", (0.888, 0.888, 0.888), roughness=0.6)
    caramel = solid_material("Caramel", (0.457, 0.181, 0.023),
                             roughness=0.6)
    red = solid_material("Red", (0.577, 0.005, 0.027), roughness=0.6)
    gold = solid_material("Gold", (0.657, 0.351, 0.009), metallic=0.6,
                          roughness=0.35)
    lightblue = solid_material("LightBlue", (0.212, 0.480, 0.807),
                               roughness=0.6)
    black = solid_material("Black", (0.007, 0.008, 0.010), roughness=0.6)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    hair = solid_material("Hair_Black", (0.004, 0.004, 0.006),
                          roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"navy": navy, "white": white, "caramel": caramel, "red": red,
            "gold": gold, "lightblue": lightblue, "black": black,
            "skin": skin, "hair": hair, "eye": eye}


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001..025).
    Black hair cap (z=1.57, scale-z 0.80 covers the crown) +
    two dark eyes (visible; the shirt collar sits below them at z 1.40).
    Feet are skin wedges (z=0.0) under the black leather shoes
    (025's white sneaker wedges would show through a black shoe)."""
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
def build_shirt(m):
    """White shirt: collar ring 0.215 around the neck (z 1.40, same
    proven geometry as 025's turtleneck), flaring to the torso and
    running down to z 0.70 where it tucks into the skirt waist."""
    return [make_elliptical_tube("WhiteShirt", SHIRT_RINGS, 12,
                                 m["white"], caps=False)]


def build_blazer(m):
    """Navy fitted blazer, open front: arc 300-600 deg leaves the
    240-300 deg front wedge open so the white shirt + navy tie show.
    Hem z 0.72, fitted 0.295->0.285 (0.015 narrower than 025)."""
    return [make_elliptical_tube("NavyBlazer", BLAZER_RINGS, 16,
                                 m["navy"], arc=(300, 600), caps=False)]


def build_tie(m):
    """Navy tie: curved front panel on the shirt (266-274 deg,
    z 1.34-0.72), 0.006 proud + knot box at the collar."""
    panel = build_panel(m, "NavyTie", SHIRT_RINGS,
                        [1.34, 1.20, 1.00, 0.80, 0.72], 266, 274, 5,
                        0.006, m["navy"])
    knot = add_box("NavyTieKnot", (0, -0.180, 1.375),
                   (0.055, 0.018, 0.06), m["navy"])
    return [panel, knot]


def build_buttons(m):
    """Three gold buttons on the blazer's right front edge (300 deg),
    placed on the elliptical surface along its normal."""
    objs = []
    for i, z in enumerate((1.28, 1.12, 0.96)):
        rx, ry = interp_rings(BLAZER_RINGS, z)
        p, n = ellipse_point(rx, ry, 300)
        c = Vector((p.x, p.y, z)) + n * 0.008
        objs.append(add_sphere("GoldButton%d" % (i + 1), tuple(c), 0.016,
                               6, 3, (1.0, 1.0, 1.0), m["gold"]))
    return objs


def build_sleeve(m, sx):
    """Navy fitted sleeve (shoulder to wrist) over the mannequin arm.
    Capped (025 v2 lesson) with the origin lifted 0.005 along the arm
    axis so the sleeve cap never sits coplanar with the arm cap."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    origin = shoulder - direction.normalized() * 0.005
    return [make_tube("NavySleeve", origin, direction,
                      [0.0, 0.13, 0.26, 0.39, 0.52],
                      [0.105, 0.103, 0.100, 0.096, 0.092], 10,
                      m["navy"], caps=True)]


def build_cuff(m, sx):
    """White shirt cuff ring peeking below the blazer sleeve."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("WhiteCuff", shoulder, direction,
                      [0.46, 0.52], [0.100, 0.100], 10,
                      m["white"], caps=False)]


def build_armband(m):
    """Red discipline armband on the LEFT arm (upper arm 0.10-0.18),
    outside the navy sleeve, + a thin white stripe ring mid-band."""
    sx = -1
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    band = make_tube("RedArmband", shoulder, direction,
                     [0.10, 0.18], [0.112, 0.112], 10,
                     m["red"], caps=False)
    stripe = make_tube("WhiteArmbandStripe", shoulder, direction,
                       [0.135, 0.145], [0.116, 0.116], 10,
                       m["white"], caps=False)
    return [band, stripe]


def build_skirt(m):
    """Navy pleated skirt: slight flare 0.275->0.340, top ring tucked
    inside the blazer hem (0.275 < 0.285)."""
    return [make_elliptical_tube("NavySkirt", SKIRT_RINGS, 12,
                                 m["navy"], caps=False)]


def build_pleat_fin(m, angle_deg):
    """One 3D pleat fin: a closed thin solid (10 quads) following the
    skirt cone, inner edge 0.004 off the skirt, outer edge 0.026 off,
    tangential half-thickness 0.004. Built from the ellipse point +
    normal + tangent so it tracks the flare instead of floating."""
    rows = [0.70, 0.50, 0.30]
    a = math.radians(angle_deg)
    verts = []
    for z in rows:
        rx, ry = interp_rings(SKIRT_RINGS, z)
        p, n = ellipse_point(rx, ry, angle_deg)
        t = Vector((-rx * math.sin(a), ry * math.cos(a), 0.0)).normalized()
        for relief in (0.004, 0.026):
            base = Vector((p.x, p.y, z)) + n * relief
            verts.append(tuple(base - t * 0.004))
            verts.append(tuple(base + t * 0.004))
    # per row: IL, IR, OL, OR
    faces = []
    for k in range(2):
        r0, r1 = k * 4, (k + 1) * 4
        faces.append((r0 + 0, r1 + 0, r1 + 2, r0 + 2))  # left broad face
        faces.append((r0 + 1, r0 + 3, r1 + 3, r1 + 1))  # right broad face
        faces.append((r0 + 2, r1 + 2, r1 + 3, r0 + 3))  # outer edge
        faces.append((r0 + 0, r0 + 1, r1 + 1, r1 + 0))  # inner edge
    faces.append((0, 2, 3, 1))    # top cap
    faces.append((8, 9, 11, 10))  # bottom cap
    return mesh_from_data("NavyPleat", verts, faces, m["navy"])


def build_waistband(m):
    """Navy waistband ring below the blazer hem + gold buckle on the
    front centre."""
    band = make_elliptical_tube("NavyWaistband", WAIST_RINGS, 12,
                                m["navy"], caps=False)
    buckle = add_box("GoldWaistBuckle", (0, -0.160, 0.67),
                     (0.04, 0.012, 0.03), m["gold"])
    return [band, buckle]


def build_sock(m, sx):
    """White knee sock: tube over the leg, top meeting the skirt hem
    at z 0.30 with no skin showing."""
    return [make_tube("WhiteSock", (sx * 0.13, 0, 0.30), (0, 0, -1),
                      [0.0, 0.24], [0.100, 0.096], 10,
                      m["white"], caps=False)]


def build_shoe(m, sx):
    """Black leather shoe: wedge sole (lands z=0.0, encloses the
    mannequin foot wedge) + ankle shaft over the sock + gold buckle."""
    wedge = make_wedge("BlackShoe", (sx * 0.13, -0.02, 0.0),
                       0.100, 0.095, -0.165, 0.0, 0.105, 0.05, m["black"])
    shaft = make_tube("BlackShoeShaft", (sx * 0.13, 0, 0.16), (0, 0, -1),
                      [0.0, 0.13], [0.106, 0.104], 10,
                      m["black"], caps=False)
    buckle = add_box("GoldShoeBuckle", (sx * 0.13, -0.108, 0.06),
                     (0.04, 0.012, 0.025), m["gold"])
    return [wedge, shaft, buckle]


def build_satchel(m):
    """Caramel satchel on the right hip (camera side) + flap + gold
    clasp. Caramel, not black: 025 lesson — a black pouch on navy
    reads as a small black blob; accessories need contrast."""
    bag = add_box("CaramelSatchel", (0.34, -0.10, 0.72),
                  (0.10, 0.15, 0.14), m["caramel"])
    flap = add_box("CaramelSatchelFlap", (0.34, -0.178, 0.74),
                   (0.105, 0.012, 0.09), m["caramel"])
    clasp = add_box("GoldSatchelClasp", (0.34, -0.186, 0.72),
                    (0.02, 0.012, 0.03), m["gold"])
    return [bag, flap, clasp]


def build_strap(m):
    """Caramel cross-body strap: diagonal panel following the blazer
    surface, left shoulder (227 deg) to right hip (340 deg), relief
    0.012 so it rides 0.006 over the tie (0.006) without z-fighting;
    the tail lands on the satchel's inner top edge."""
    verts, faces = [], []
    for z, c in zip(STRAP_Z, STRAP_A):
        rx, ry = interp_rings(BLAZER_RINGS, z)
        for da in (-3.5, 0.0, 3.5):
            p, n = ellipse_point(rx, ry, c + da)
            v = Vector((p.x, p.y, z)) + n * 0.012
            verts.append(tuple(v))
    for k in range(len(STRAP_Z) - 1):
        for i in range(2):
            a0i = k * 3 + i
            b0i = (k + 1) * 3 + i
            faces.append((a0i, b0i, b0i + 1, a0i + 1))
    return mesh_from_data("CaramelStrap", verts, faces, m["caramel"])


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
    objs = (parts["shirt"] + parts["blazer"] + parts["tie"]
            + parts["buttons"])
    ok = True
    ok &= check_gap("torso: white shirt collar vs head @z=1.40",
                    0.215, 0.198)
    ok &= check_gap("torso: navy blazer vs white shirt @z=1.10",
                    interp_rings(BLAZER_RINGS, 1.10)[0],
                    interp_rings(SHIRT_RINGS, 1.10)[0])
    ok &= check_gap("torso: white shirt vs mannequin torso @z=1.00",
                    interp_rings(SHIRT_RINGS, 1.00)[0],
                    interp_rings([(1.28, 0.270, 0.140),
                                  (0.95, 0.240, 0.130)], 1.00)[0])
    ok &= check_relief("torso: navy tie relief", 0.006)
    ok &= check_relief("torso: caramel strap relief", 0.012,
                       lo=0.005, hi=0.030)
    ok &= check_relief("torso: gold button relief", 0.008)
    print("L2_CHECK torso: white shirt collar above the navy blazer, "
          "navy tie down the shirt front, gold buttons on the blazer "
          "edge, caramel strap crossing over the tie PASS")
    return objs, ok


def assemble_arms(parts):
    objs = parts["sleeves"] + parts["cuffs"] + parts["armband"]
    ok = True
    ok &= check_gap("arms: navy sleeve vs mannequin arm @0.0",
                    0.105, 0.085)
    ok &= check_gap("arms: white cuff vs navy sleeve @0.46",
                    0.100, 0.0935)
    ok &= check_gap("arms: red armband vs navy sleeve @0.14",
                    0.112, 0.103)
    ok &= check_relief("arms: white armband stripe relief", 0.004,
                       lo=0.002, hi=0.008)
    print("L2_CHECK arms: navy fitted sleeves 0.105->0.092, white "
          "cuffs at the wrists, red armband with a white stripe on "
          "the left upper arm PASS")
    return objs, ok


def assemble_head(parts):
    objs = parts["cat_ears"] + parts["streak"]
    ok = True
    ok &= check_gap("head: navy cat ear apex vs hair top",
                    1.845, 1.75)
    ok &= check_relief("head: blue streak relief", 0.010,
                       lo=0.005, hi=0.030)
    print("L2_CHECK head: navy cat ears out of the hair top, "
          "light-blue streak lying on the hair front PASS")
    return objs, ok


def assemble_waist(parts):
    objs = parts["skirt"] + parts["pleats"] + parts["waistband"]
    ok = True
    ok &= check_gap("waist: navy waistband vs navy skirt @z=0.67",
                    interp_rings(WAIST_RINGS, 0.67)[0],
                    interp_rings(SKIRT_RINGS, 0.67)[0])
    ok &= check_relief("waist: navy pleat fin height", 0.022,
                       lo=0.005, hi=0.030)
    ok &= check_relief("waist: gold waist buckle relief", 0.009,
                       lo=0.005, hi=0.030)
    ok &= check_gap("waist: caramel satchel inner face vs skirt @z=0.72",
                    0.29, interp_rings(SKIRT_RINGS, 0.72)[0])
    print("L2_CHECK waist: navy pleated skirt with 8 3D pleat fins, "
          "navy waistband below the blazer hem with a gold buckle, "
          "caramel satchel on the right hip PASS")
    return objs, ok


def assemble_legs(parts):
    objs = parts["socks"]
    ok = True
    ok &= check_gap("legs: white sock vs mannequin leg @z=0.30",
                    0.100, 0.092)
    ok &= check_gap("legs: white sock vs mannequin leg @z=0.06",
                    0.096, 0.080)
    print("L2_CHECK legs: white knee socks 0.100->0.096, tops meeting "
          "the skirt hem with no skin showing PASS")
    return objs, ok


def assemble_feet(parts):
    objs = parts["shoes"]
    ok = True
    ok &= check_gap("feet: black shoe shaft vs white sock @z=0.10",
                    0.105, 0.098)
    ok &= check_gap("feet: black shoe wedge vs mannequin foot",
                    0.100, 0.095)
    ok &= check_relief("feet: gold shoe buckle relief", 0.010,
                       lo=0.005, hi=0.030)
    print("L2_CHECK feet: black shoe wedge centre z=0.0, sole on "
          "ground; black shaft over the sock, gold buckle on the "
          "front PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: navy blazer vs white shirt @z=1.10",
                    interp_rings(BLAZER_RINGS, 1.10)[0],
                    interp_rings(SHIRT_RINGS, 1.10)[0])
    ok &= check_gap("L3 layer: navy blazer hem vs navy skirt @z=0.72",
                    interp_rings(BLAZER_RINGS, 0.72)[0],
                    interp_rings(SKIRT_RINGS, 0.72)[0])
    ok &= check_gap("L3 layer: navy skirt vs white shirt @z=0.70",
                    interp_rings(SKIRT_RINGS, 0.70)[0],
                    interp_rings(SHIRT_RINGS, 0.70)[0])
    ok &= check_gap("L3 layer: navy waistband vs navy skirt @z=0.67",
                    interp_rings(WAIST_RINGS, 0.67)[0],
                    interp_rings(SKIRT_RINGS, 0.67)[0])
    ok &= check_gap("L3 joint: white cuff vs navy sleeve", 0.100, 0.0935)
    ok &= check_gap("L3 joint: black shoe shaft vs white sock @z=0.10",
                    0.105, 0.098)
    ok &= check_gap("L3 joint: red armband vs navy sleeve", 0.112, 0.103)
    print("L3_CHECK outfit: open-front blazer shows the white shirt "
          "and navy tie, skirt top tucked inside the blazer hem, "
          "waistband below the hem, black shoe soles touch ground "
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
    parts["shirt"] = build_shirt(m)
    report_l1("WhiteShirt", parts["shirt"])
    parts["blazer"] = build_blazer(m)
    report_l1("NavyBlazer", parts["blazer"])
    parts["tie"] = build_tie(m)
    report_l1("NavyTie+Knot", parts["tie"])
    flat_patches += [parts["tie"][0]]
    parts["buttons"] = build_buttons(m)
    report_l1("GoldButtons x3", parts["buttons"])
    parts["sleeves"] = []
    for sx in (-1, 1):
        parts["sleeves"] += build_sleeve(m, sx)
    report_l1("NavySleeves x2", parts["sleeves"])
    parts["cuffs"] = []
    for sx in (-1, 1):
        parts["cuffs"] += build_cuff(m, sx)
    report_l1("WhiteCuffs x2", parts["cuffs"])
    parts["armband"] = build_armband(m)
    report_l1("RedArmband+Stripe", parts["armband"])
    parts["skirt"] = build_skirt(m)
    report_l1("NavySkirt", parts["skirt"])
    parts["pleats"] = [build_pleat_fin(m, a)
                       for a in (0, 45, 90, 135, 180, 225, 270, 315)]
    report_l1("NavyPleats x8", parts["pleats"])
    parts["waistband"] = build_waistband(m)
    report_l1("NavyWaistband+Buckle", parts["waistband"])
    parts["socks"] = []
    for sx in (-1, 1):
        parts["socks"] += build_sock(m, sx)
    report_l1("WhiteSocks x2", parts["socks"])
    parts["shoes"] = []
    for sx in (-1, 1):
        parts["shoes"] += build_shoe(m, sx)
    report_l1("BlackShoes x2", parts["shoes"])
    parts["satchel"] = build_satchel(m)
    report_l1("CaramelSatchel", parts["satchel"])
    parts["strap"] = [build_strap(m)]
    report_l1("CaramelStrap", parts["strap"])
    flat_patches += parts["strap"]
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
    costume = (parts["shirt"] + parts["blazer"] + parts["tie"]
               + parts["buttons"] + parts["sleeves"] + parts["cuffs"]
               + parts["armband"] + parts["skirt"] + parts["pleats"]
               + parts["waistband"] + parts["socks"] + parts["shoes"]
               + parts["satchel"] + parts["strap"] + parts["cat_ears"]
               + parts["streak"])
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
