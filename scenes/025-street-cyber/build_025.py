# -*- coding: utf-8 -*-
"""025 异环式都市时装 · 赛博街头潮服套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整套穿到人体底座上试穿）。
设计见 design.md。BACKLOG 本轮已空，自选新题材：异环线第二件——
赛博街头潮服（廓形改 oversized 街头，015 修身风衣的对照）。
Run: blender --background --python build_025.py
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

BLEND_OUT = os.path.join(HERE, "025-street-cyber.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "025-street-cyber.png")
WIRE_JSON = "/tmp/street_cyber_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

TURTLENECK_RINGS = [(1.40, 0.215, 0.188), (1.34, 0.210, 0.182),
                    (1.15, 0.272, 0.142), (0.95, 0.258, 0.136)]
JACKET_RINGS = [(1.36, 0.310, 0.160), (1.00, 0.305, 0.157),
                (0.60, 0.300, 0.155)]
CHAIN_RINGS = [(1.375, 0.222, 0.196), (1.365, 0.222, 0.196)]
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)
GRAFFITI = [(248, 260, 1.24, 1.18), (276, 288, 1.16, 1.10),
            (250, 262, 1.06, 1.00)]


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    navy = solid_material("Navy", (0.011, 0.023, 0.069), roughness=0.6)
    black = solid_material("Black", (0.007, 0.008, 0.010), roughness=0.6)
    neon = solid_material("NeonGreen", (0.041, 1.000, 0.144), roughness=0.4)
    silver = solid_material("Silver", (0.479, 0.515, 0.565), roughness=0.6)
    white = solid_material("White", (0.888, 0.888, 0.888), roughness=0.6)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    hair = solid_material("Hair_Black", (0.004, 0.004, 0.006),
                          roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"navy": navy, "black": black, "neon": neon, "silver": silver,
            "white": white, "skin": skin, "hair": hair, "eye": eye}


def front_y(rings, x, z):
    """Front surface Y of an elliptical tube at (x, z)."""
    rx, ry = interp_rings(rings, z)
    return ellipse_front(rx, ry, x)[0]


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001..024).
    Black hair cap (z=1.57, scale-z 0.80 covers the crown) +
    two dark eyes (visible; the cap brim sits above them at z 1.58).
    Feet are white sneaker wedges (z=0.0, lands on the ground; 013 lesson)
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
        objs.append(make_wedge("WhiteSneaker", (sx * 0.13, -0.02, 0.0),
                               0.095, 0.09, -0.16, 0.0, 0.10, 0.045,
                               m["white"]))
    return objs


# ------------------------------------------------------------ L1 components
def build_turtleneck(m):
    return [make_elliptical_tube("BlackTurtleneck", TURTLENECK_RINGS, 12,
                                 m["black"], caps=False)]


def build_jacket(m):
    """Navy oversized longline jacket: loose tube (z 1.36-0.60,
    0.310->0.300), hem at 0.60 presses over the pants top (0.62)
    so the hip never shows skin (024 tunic lesson)."""
    return [make_elliptical_tube("NavyJacket", JACKET_RINGS, 12,
                                 m["navy"], caps=False)]


def build_zipper(m):
    """Neon zipper: narrow front panel (266-274 deg, z 1.30-0.70)
    over the navy jacket, 0.006 proud."""
    return [build_panel(m, "NeonZipper", JACKET_RINGS,
                        [1.30, 1.10, 0.90, 0.70], 266, 274, 3, 0.006,
                        m["neon"])]


def build_graffiti(m):
    """Three neon graffiti strips on the jacket front, staggered in
    angle and height so they never cover the zipper (2 deg clear on
    each side) and sit 0.008 proud (0.002 more than the zipper)."""
    objs = []
    for i, (a0, a1, z0, z1) in enumerate(GRAFFITI):
        objs.append(build_panel(m, "NeonGraffiti%d" % (i + 1),
                                JACKET_RINGS, [z0, z1], a0, a1, 5, 0.008,
                                m["neon"]))
    return objs


def build_cap(m):
    """Navy baseball cap: flattened sphere on the head top
    (top 1.759 covers the hair top 1.75; front edge z 1.573 stays
    above the eyes at 1.525)."""
    return [add_sphere("NavyCap", (0, 0.01, 1.63), 0.235, 10, 6,
                       (1.0, 0.95, 0.55), m["navy"])]


def build_brim(m):
    """Neon cap brim: flat box above the forehead (z 1.60), tilted
    0.15 rad so the front edge dips down; back edge embeds into the
    cap front."""
    return [add_box_rot("NeonBrim", (0, -0.26, 1.60),
                        (0.22, 0.12, 0.015), m["neon"], (0.15, 0, 0))]


def build_cap_button(m):
    """Neon cap top button: small flattened sphere on the cap top."""
    return [add_sphere("NeonCapButton", (0, 0.01, 1.755), 0.02, 6, 3,
                       (1.0, 1.0, 0.6), m["neon"])]


def build_chain(m):
    """Silver chain necklace: elliptical tube band around the
    turtleneck collar (z 1.37, ring 0.222 vs turtleneck 0.2125)."""
    return [make_elliptical_tube("SilverChain", CHAIN_RINGS, 12,
                                 m["silver"], caps=False)]


def build_chain_bead(m):
    """Neon chain bead: small box on the chain front centre,
    embedded 0.006 into the chain ring."""
    return [add_box("NeonChainBead", (0, -0.20, 1.37),
                    (0.035, 0.02, 0.035), m["neon"])]


def build_waist_pouch(m):
    """Navy waist pouch on the jacket front (z 0.88) + neon zipper
    strip on the pouch face."""
    pouch = add_box("NavyWaistPouch", (0.02, -0.168, 0.88),
                    (0.11, 0.035, 0.09), m["navy"])
    strip = add_box("NeonPouchZip", (0.02, -0.186, 0.90),
                    (0.09, 0.012, 0.015), m["neon"])
    return [pouch, strip]


def build_sleeve(m, sx):
    """Navy oversized sleeve (shoulder to wrist) over the mannequin arm.
    Capped (v2: v1 caps=False left the top ring open and the mannequin
    arm's skin top-cap showed through the 0.030 annular gap as a beige
    wedge at the shoulder); origin lifted 0.005 along the arm axis so
    the sleeve cap never sits coplanar with the arm cap (no z-fight)."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    origin = shoulder - direction.normalized() * 0.005
    return [make_tube("NavySleeve", origin, direction,
                      [0.0, 0.13, 0.26, 0.39, 0.52],
                      [0.115, 0.112, 0.108, 0.104, 0.100], 10,
                      m["navy"], caps=True)]


def build_cuff(m, sx):
    """Neon cuff ring over the sleeve at the wrist."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("NeonCuff", shoulder, direction,
                      [0.46, 0.52], [0.112, 0.112], 10,
                      m["neon"], caps=False)]


def build_pants(m, sx):
    """Charcoal cargo trousers: tube over the mannequin leg, hip to ankle."""
    return [make_tube("CharcoalPants", (sx * 0.13, 0, 0.62), (0, 0, -1),
                      [0.0, 0.13, 0.26, 0.39, 0.52, 0.58],
                      [0.115, 0.112, 0.108, 0.104, 0.100, 0.098], 10,
                      m["black"], caps=False)]


def build_knee_patch(m, sx):
    """Neon knee patch: flat box on the front of the knee (z=0.32,
    pants front y=-0.106; patch spans y -0.1085..-0.1235)."""
    return [add_box("NeonKneePatch", (sx * 0.13, -0.116, 0.32),
                    (0.07, 0.015, 0.09), m["neon"])]


def build_cargo_pocket(m, sx):
    """Navy cargo pocket on the outer thigh (x=±0.245, z=0.42):
    pants outer edge x≈0.234, the box spans x 0.23..0.26."""
    return [add_box("NavyCargo", (sx * 0.245, 0, 0.42),
                    (0.03, 0.10, 0.12), m["navy"])]


def build_pocket_flap(m, sx):
    """Navy pocket flap on the jacket front hem (z=0.70, x=±0.15)
    + neon button on the flap face."""
    flap = add_box("NavyPocketFlap", (sx * 0.15, -0.145, 0.70),
                   (0.11, 0.03, 0.06), m["navy"])
    button = add_box("NeonFlapButton", (sx * 0.15, -0.158, 0.70),
                     (0.02, 0.012, 0.02), m["neon"])
    return [flap, button]


def build_sneaker(m, sx):
    """White high-top sneaker: shaft tube (z 0.28-0.05) over the leg +
    neon sole stripe ring on the visible shaft at z 0.05 (the shaft
    top at z 0.28 sits under the pants cuff, so a ring there would be
    hidden); the wedge sole (mannequin WhiteSneaker, white) lands
    at z=0.0."""
    shaft = make_tube("WhiteSneakerShaft", (sx * 0.13, 0, 0.28), (0, 0, -1),
                      [0.0, 0.23], [0.105, 0.10], 10,
                      m["white"], caps=False)
    stripe = make_tube("NeonSoleStripe", (sx * 0.13, 0, 0.05), (0, 0, -1),
                       [0.0, 0.02], [0.109, 0.109], 10,
                       m["neon"], caps=False)
    return [shaft, stripe]


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["turtleneck"] + parts["jacket"]
            + parts["zipper"] + parts["graffiti"])
    ok = True
    ok &= check_gap("torso: turtleneck collar vs head @z=1.40",
                    0.215, 0.198)
    ok &= check_gap("torso: turtleneck vs mannequin torso @z=1.15",
                    interp_rings(TURTLENECK_RINGS, 1.15)[0],
                    interp_rings([(1.28, 0.270, 0.140),
                                  (0.95, 0.240, 0.130)], 1.15)[0])
    ok &= check_gap("torso: navy jacket vs turtleneck @z=1.15",
                    interp_rings(JACKET_RINGS, 1.15)[0],
                    interp_rings(TURTLENECK_RINGS, 1.15)[0])
    ok &= check_relief("torso: neon zipper relief", 0.006)
    ok &= check_relief("torso: neon graffiti relief", 0.008)
    print("L2_CHECK torso: black turtleneck under navy oversized "
          "jacket, neon zipper down the front centre, three neon "
          "graffiti strips staggered clear of the zipper PASS")
    return objs, ok


def assemble_arms(parts):
    objs = parts["sleeves"] + parts["cuffs"]
    ok = True
    ok &= check_gap("arms: navy sleeve vs mannequin arm @0.0",
                    0.115, 0.085)
    ok &= check_gap("arms: neon cuff vs navy sleeve @0.46",
                    0.112, 0.100)
    print("L2_CHECK arms: navy oversized sleeves 0.115->0.100, neon "
          "cuff rings at the wrists PASS")
    return objs, ok


def assemble_head(parts):
    objs = (parts["cap"] + parts["brim"] + parts["cap_button"]
            + parts["chain"] + parts["chain_bead"])
    ok = True
    ok &= check_gap("head: navy cap top vs hair top",
                    1.759, 1.75)
    ok &= check_gap("head: neon brim bottom vs eyes",
                    1.584, 1.525)
    ok &= check_gap("head: silver chain vs turtleneck @z=1.37",
                    0.222,
                    interp_rings(TURTLENECK_RINGS, 1.37)[0])
    ok &= check_relief("head: neon chain bead relief", 0.014,
                       lo=0.005, hi=0.030)
    print("L2_CHECK head: navy cap covers the hair top, neon brim "
          "above the eyes, silver chain around the turtleneck collar "
          "with a neon bead on the front PASS")
    return objs, ok


def assemble_waist(parts):
    objs = parts["waist_pouch"] + parts["pocket_flaps"]
    ok = True
    ok &= check_gap("waist: navy waist pouch front vs jacket @z=0.88",
                    0.1855, interp_rings(JACKET_RINGS, 0.88)[1])
    ok &= check_relief("waist: neon pouch zip relief", 0.0065,
                       lo=0.005, hi=0.030)
    ok &= check_relief("waist: neon flap button relief", 0.004,
                       lo=0.002, hi=0.030)
    print("L2_CHECK waist: navy waist pouch on the jacket front with "
          "a neon zip strip, navy pocket flaps on the jacket hem with "
          "neon buttons PASS")
    return objs, ok


def assemble_legs(parts):
    objs = parts["pants"] + parts["knee_patches"] + parts["cargo"]
    ok = True
    ok &= check_gap("legs: charcoal pants vs mannequin leg @0.0",
                    0.115, 0.105)
    ok &= check_relief("legs: neon knee patch relief", 0.0175,
                       lo=0.005, hi=0.030)
    ok &= check_relief("legs: navy cargo pocket relief", 0.020,
                       lo=0.005, hi=0.030)
    print("L2_CHECK legs: charcoal cargo pants 0.115->0.098, neon "
          "knee patches and navy cargo pockets proud of the pants "
          "PASS")
    return objs, ok


def assemble_feet(parts):
    objs = parts["sneakers"]
    ok = True
    ok &= check_gap("feet: white sneaker shaft vs leg @z=0.18",
                    0.1025, 0.088)
    ok &= check_gap("feet: neon sole stripe vs shaft @z=0.05",
                    0.109, 0.10)
    print("L2_CHECK feet: white sneaker wedge centre z=0.0, sole on "
          "ground; white high-top shaft z 0.28-0.05, neon sole stripe "
          "at z 0.05 on the visible shaft PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: navy jacket vs turtleneck @z=1.15",
                    interp_rings(JACKET_RINGS, 1.15)[0],
                    interp_rings(TURTLENECK_RINGS, 1.15)[0])
    ok &= check_gap("L3 layer: navy jacket hem vs pants @z=0.60",
                    interp_rings(JACKET_RINGS, 0.60)[0], 0.245)
    ok &= check_gap("L3 layer: zipper vs navy jacket @z=1.10",
                    interp_rings(JACKET_RINGS, 1.10)[0] + 0.006,
                    interp_rings(JACKET_RINGS, 1.10)[0])
    ok &= check_gap("L3 layer: silver chain vs turtleneck @z=1.37",
                    0.222,
                    interp_rings(TURTLENECK_RINGS, 1.37)[0])
    ok &= check_gap("L3 joint: neon cuff vs navy sleeve", 0.112, 0.100)
    ok &= check_gap("L3 joint: white sneaker shaft vs leg @z=0.18",
                    0.1025, 0.088)
    print("L3_CHECK outfit: longline jacket hem z=0.60 presses over "
          "the pants top, white sneakers below the pants cuffs, "
          "white sneaker soles touch ground z=0.000 PASS")
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
    parts["turtleneck"] = build_turtleneck(m)
    report_l1("BlackTurtleneck", parts["turtleneck"])
    parts["jacket"] = build_jacket(m)
    report_l1("NavyJacket", parts["jacket"])
    parts["zipper"] = build_zipper(m)
    report_l1("NeonZipper", parts["zipper"])
    flat_patches += parts["zipper"]
    parts["graffiti"] = build_graffiti(m)
    report_l1("NeonGraffiti x3", parts["graffiti"])
    flat_patches += parts["graffiti"]
    parts["cap"] = build_cap(m)
    report_l1("NavyCap", parts["cap"])
    parts["brim"] = build_brim(m)
    report_l1("NeonBrim", parts["brim"])
    parts["cap_button"] = build_cap_button(m)
    report_l1("NeonCapButton", parts["cap_button"])
    parts["chain"] = build_chain(m)
    report_l1("SilverChain", parts["chain"])
    parts["chain_bead"] = build_chain_bead(m)
    report_l1("NeonChainBead", parts["chain_bead"])
    parts["waist_pouch"] = build_waist_pouch(m)
    report_l1("NavyWaistPouch+Zip", parts["waist_pouch"])
    parts["sleeves"] = []
    for sx in (-1, 1):
        parts["sleeves"] += build_sleeve(m, sx)
    report_l1("NavySleeves x2", parts["sleeves"])
    parts["cuffs"] = []
    for sx in (-1, 1):
        parts["cuffs"] += build_cuff(m, sx)
    report_l1("NeonCuffs x2", parts["cuffs"])
    parts["pants"] = []
    for sx in (-1, 1):
        parts["pants"] += build_pants(m, sx)
    report_l1("CharcoalPants x2", parts["pants"])
    parts["knee_patches"] = []
    for sx in (-1, 1):
        parts["knee_patches"] += build_knee_patch(m, sx)
    report_l1("NeonKneePatches x2", parts["knee_patches"])
    parts["cargo"] = []
    for sx in (-1, 1):
        parts["cargo"] += build_cargo_pocket(m, sx)
    report_l1("NavyCargo x2", parts["cargo"])
    parts["pocket_flaps"] = []
    for sx in (-1, 1):
        parts["pocket_flaps"] += build_pocket_flap(m, sx)
    report_l1("NavyPocketFlaps+Buttons x2", parts["pocket_flaps"])
    parts["sneakers"] = []
    for sx in (-1, 1):
        parts["sneakers"] += build_sneaker(m, sx)
    report_l1("WhiteSneakers+Stripes x2", parts["sneakers"])

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
    costume = (parts["turtleneck"] + parts["jacket"]
               + parts["zipper"] + parts["graffiti"]
               + parts["cap"] + parts["brim"] + parts["cap_button"]
               + parts["chain"] + parts["chain_bead"]
               + parts["waist_pouch"] + parts["sleeves"] + parts["cuffs"]
               + parts["pants"] + parts["knee_patches"] + parts["cargo"]
               + parts["pocket_flaps"] + parts["sneakers"])
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
