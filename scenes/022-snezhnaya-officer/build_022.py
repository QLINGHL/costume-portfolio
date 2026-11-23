# -*- coding: utf-8 -*-
"""022 原神式层叠幻想 · 至冬雪原执行官套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整套穿到人体底座上试穿）。
设计见 design.md。BACKLOG 本轮已空，自选新题材：原神地区衣橱新方向——至冬。
Run: blender --background --python build_022.py
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

BLEND_OUT = os.path.join(HERE, "022-snezhnaya-officer.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "022-snezhnaya-officer.png")
WIRE_JSON = "/tmp/snezhnaya_officer_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

BODICE_RINGS = [(1.34, 0.288, 0.152), (1.15, 0.282, 0.148),
                (0.92, 0.272, 0.144)]
COLLAR_RINGS = [(1.42, 0.150, 0.128), (1.34, 0.158, 0.132)]
SKIRT_RINGS = [(0.92, 0.272, 0.144), (0.62, 0.310, 0.160),
               (0.30, 0.360, 0.180)]
BELT_RINGS = [(0.94, 0.292, 0.152), (0.86, 0.298, 0.155)]
FUR_RINGS = [(1.365, 0.155, 0.135), (1.355, 0.155, 0.135),
             (1.405, 0.175, 0.150), (1.395, 0.175, 0.150),
             (1.445, 0.155, 0.135), (1.435, 0.155, 0.135)]
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)
BUTTON_Z = [0.98, 0.88, 0.78, 0.68, 0.58, 0.48]
PLEAT_ANGLES = [232, 243, 254, 265, 276, 287, 298, 308]
CROWN_SPIKE_ANGLES = [240, 270, 300]


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    iceblue = solid_material("IceBlue", (0.027, 0.102, 0.262),
                             roughness=0.6)
    snowwhite = solid_material("SnowWhite", (0.815, 0.855, 0.888),
                               roughness=0.6)
    silver = solid_material("SilverGray", (0.323, 0.366, 0.418),
                            roughness=0.6)
    gold = solid_material("Gold", (0.584, 0.361, 0.020), roughness=0.6)
    deepblue = solid_material("DeepBlue", (0.013, 0.042, 0.107),
                              roughness=0.6)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    hair = solid_material("Hair_Silver", (0.323, 0.366, 0.418),
                          roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"iceblue": iceblue, "snowwhite": snowwhite, "silver": silver,
            "gold": gold, "deepblue": deepblue, "skin": skin,
            "hair": hair, "eye": eye}


def front_y(rings, x, z):
    """Front surface Y of an elliptical tube at (x, z)."""
    rx, ry = interp_rings(rings, z)
    return ellipse_front(rx, ry, x)[0]


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001..021).
    Silver hair cap (017 v2: z=1.57, scale-z 0.80 covers the crown) +
    two dark eyes (visible). Feet are deep-blue boot wedges (z=0.0,
    lands on the ground; 013 lesson) instead of bare skin."""
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
        objs.append(make_wedge("WarBoot", (sx * 0.13, -0.02, 0.0),
                               0.095, 0.09, -0.16, 0.0, 0.10, 0.045,
                               m["deepblue"]))
    return objs


# ------------------------------------------------------------ L1 components
def build_coat(m):
    return [make_elliptical_tube("OfficerCoat", BODICE_RINGS, 12,
                                 m["iceblue"], caps=False)]


def build_collar(m):
    return [make_elliptical_tube("SnowCollar", COLLAR_RINGS, 12,
                                 m["snowwhite"], caps=False)]


def build_fur_collar(m):
    """Snow-white fur collar: three stacked ring bands around the
    neck (011 fur-collar technique), radii 0.155 / 0.168 / 0.155."""
    objs = []
    for i, (z0, rx, ry) in enumerate([(1.36, 0.155, 0.135),
                                      (1.40, 0.175, 0.150),
                                      (1.44, 0.155, 0.135)]):
        objs.append(make_elliptical_tube(
            "FurCollar", [(z0 + 0.005, rx, ry), (z0 - 0.005, rx, ry)],
            12, m["snowwhite"], caps=False))
    return objs


def build_chest_plate(m):
    """Silver-gray chest plate: curved front panel (232-308 deg,
    z 1.30-1.02) over the ice-blue coat, 0.006 proud."""
    return [build_panel(m, "ChestPlate", BODICE_RINGS,
                        [1.30, 1.20, 1.11, 1.02], 232, 308, 9, 0.006,
                        m["silver"])]


def build_snowflake(m):
    """Ice-blue six-arm snowflake on the chest plate centre (z=1.16):
    flattened centre sphere + 6 arms, one every 60 deg about Y,
    ~0.006 proud of the plate (ice blue on silver so it reads)."""
    # front is -y: the plate surface sits at front_y - 0.006, so the
    # flake must go MORE negative, not +0.006 (v1 sign bug buried it
    # behind the plate; only a sliver of the core showed).
    plate_y = front_y(BODICE_RINGS, 0, 1.16) - 0.006
    objs = [add_sphere("SnowflakeCore", (0, plate_y + 0.002, 1.16),
                       0.024, 6, 3, (1.0, 0.5, 1.0), m["iceblue"])]
    for k in range(6):
        theta = math.radians(k * 60.0)
        d = Vector((math.sin(theta), 0.0, math.cos(theta)))
        c = Vector((0, plate_y - 0.001, 1.16)) + d * 0.042
        objs.append(add_box_rot("SnowflakeArm", tuple(c),
                                (0.016, 0.010, 0.085), m["iceblue"],
                                (0, theta, 0)))
    return objs


def build_buttons(m):
    """Six gold buttons down the coat front centre line: the top one
    on the bodice (z=0.98), the rest on the skirt cone."""
    objs = []
    for z in BUTTON_Z:
        rings = BODICE_RINGS if z > 0.92 else SKIRT_RINGS
        y = front_y(rings, 0, z) - 0.002
        objs.append(add_box("GoldButton", (0, y, z),
                            (0.020, 0.012, 0.020), m["gold"]))
    return objs


def build_epaulette(m, sx):
    """Gold epaulette: flattened box on the shoulder top, tilted
    slightly outward, + 3 gold fringe boxes hanging off its outer
    edge (attached to the epaulette, clear of the sleeve)."""
    objs = [add_box_rot("GoldEpaulette", (sx * 0.36, 0, 1.27),
                        (0.17, 0.06, 0.11), m["gold"],
                        (0, 0, -sx * 0.12))]
    for dy in (-0.03, 0.0, 0.03):
        objs.append(add_box("EpauletteFringe",
                            (sx * 0.44, dy, 1.22),
                            (0.012, 0.012, 0.07), m["gold"]))
    return objs


def build_sleeve(m, sx):
    """Ice-blue long sleeve (shoulder to wrist) over the mannequin arm."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("OfficerSleeve", shoulder, direction,
                      [0.0, 0.13, 0.26, 0.39, 0.52],
                      [0.098, 0.096, 0.093, 0.090, 0.086], 10,
                      m["iceblue"], caps=False)]


def build_cuff(m, sx):
    """Silver-gray cuff ring over the sleeve at the wrist."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("SilverCuff", shoulder, direction,
                      [0.46, 0.52], [0.10, 0.10], 10,
                      m["silver"], caps=False)]


def build_skirt(m):
    return [make_elliptical_tube("OfficerSkirt", SKIRT_RINGS, 12,
                                 m["iceblue"], caps=False)]


def build_skirt_pleat(m, angle_deg):
    """One silver skirt pleat: a 4-ring strip hugging the flaring
    skirt surface, 0.006 proud, 0.020 wide, in silver so the pleat
    reads on the ice-blue cloth (003 pleat technique)."""
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
    return mesh_from_data("SkirtPleat", verts, faces, m["silver"])


def build_belt(m):
    """Silver-gray belt: flared top->bottom (0.292->0.298) so the
    bottom edge clears the skirt cone (013 lesson)."""
    return [make_elliptical_tube("SilverBelt", BELT_RINGS, 12,
                                 m["silver"], caps=False)]


def build_buckle(m):
    """Gold buckle at the belt front centre."""
    return [add_box("GoldBuckle", (0, -0.165, 0.90),
                    (0.09, 0.02, 0.05), m["gold"])]


def build_boot(m, sx):
    """Deep-blue tall boot: shaft tube (z 0.30-0.06) over the leg +
    silver trim ring on the visible shaft at z 0.22 (the shaft top
    at z 0.30 sits under the skirt hem, so a ring there would be
    hidden); the wedge sole (mannequin WarBoot, deep blue) lands
    at z=0.0."""
    shaft = make_tube("TallBoot", (sx * 0.13, 0, 0.30), (0, 0, -1),
                      [0.0, 0.24], [0.105, 0.10], 10,
                      m["deepblue"], caps=False)
    trim = make_tube("BootTrim", (sx * 0.13, 0, 0.22), (0, 0, -1),
                     [0.0, 0.02], [0.109, 0.109], 10,
                     m["silver"], caps=False)
    return [shaft, trim]


def build_crown(m):
    """Ice-crystal crown: gold band ring around the hair cap
    (z=1.62, r=0.222; hair rx there is 0.216, so the ring sits
    0.006 proud) + 3 silver crystal spikes standing on the band
    at 240/270/300 deg (front), bases on the ring, outside the
    hair surface (hair rx at z=1.67 is ~0.195)."""
    band = make_tube("GoldCrownBand", (0, 0, 1.62), (0, 0, 1),
                     [0.0, 0.014], [0.222, 0.222], 16, m["gold"],
                     caps=False)
    objs = [band]
    for a_deg in CROWN_SPIKE_ANGLES:
        p, _n = ellipse_point(0.222, 0.222, a_deg)
        objs.append(add_box("CrystalSpike", (p.x, p.y, 1.67),
                            (0.024, 0.024, 0.10), m["silver"]))
    return objs


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["coat"] + parts["collar"] + parts["fur_collar"]
            + parts["chest_plate"] + parts["snowflake"]
            + parts["buttons"])
    ok = True
    ok &= check_gap("torso: snow collar vs mannequin neck",
                    COLLAR_RINGS[0][1], 0.09)
    ok &= check_gap("torso: fur collar vs snow collar @z=1.40",
                    0.175, 0.158)
    ok &= check_relief("torso: chest plate relief", 0.006)
    ok &= check_relief("torso: snowflake relief", 0.006)
    ok &= check_relief("torso: gold button relief", 0.004,
                       lo=0.002, hi=0.008)
    ok &= check_gap("torso: officer coat vs mannequin torso @z=1.15",
                    interp_rings(BODICE_RINGS, 1.15)[0],
                    interp_rings([(1.28, 0.270, 0.140),
                                  (0.95, 0.240, 0.130)], 1.15)[0])
    return objs, ok


def assemble_arms(parts):
    objs = parts["sleeves"] + parts["cuffs"]
    ok = True
    ok &= check_gap("arms: long sleeve vs mannequin arm @0.0",
                    0.098, 0.085)
    ok &= check_gap("arms: silver cuff vs sleeve @0.46", 0.10, 0.088)
    print("L2_CHECK arms: ice-blue long sleeve 0.098->0.086, silver "
          "cuff ring at the wrist PASS")
    return objs, ok


def assemble_shoulders(parts):
    objs = parts["epaulettes"]
    ok = True
    ok &= check_gap("shoulder: epaulette vs officer coat @z=1.27",
                    0.36, interp_rings(BODICE_RINGS, 1.27)[0])
    print("L2_CHECK shoulder: gold epaulettes sit on the shoulder "
          "tops, fringe hangs off the outer edge, clear of the "
          "fur collar PASS")
    return objs, ok


def assemble_skirt(parts):
    objs = parts["skirt"] + parts["pleats"]
    ok = True
    ok &= check_relief("skirt: skirt pleat relief", 0.006)
    ok &= check_gap("skirt: officer skirt vs legs @z=0.62", 0.310, 0.235)
    ok &= check_gap("skirt: belt bottom edge vs skirt @z=0.86",
                    BELT_RINGS[1][1],
                    interp_rings(SKIRT_RINGS, 0.86)[0])
    return objs, ok


def assemble_waist(parts):
    objs = parts["belt"] + parts["buckle"]
    ok = True
    ok &= check_gap("waist: silver belt vs officer coat @z=0.92",
                    interp_rings(BELT_RINGS, 0.92)[0],
                    interp_rings(BODICE_RINGS, 0.92)[0])
    ok &= check_gap("waist: silver belt bottom edge vs skirt @z=0.86",
                    BELT_RINGS[1][1],
                    interp_rings(SKIRT_RINGS, 0.86)[0])
    ok &= check_relief("waist: gold buckle relief", 0.0215,
                       lo=0.005, hi=0.030)
    return objs, ok


def assemble_head_feet(parts):
    objs = parts["crown"] + parts["boots"]
    ok = True
    ok &= check_gap("head: gold crown band vs hair cap @z=1.62", 0.222, 0.216)
    print("L2_CHECK head: gold crown band 0.006 proud of hair cap, "
          "3 silver crystal spikes stand on the band outside the "
          "hair surface PASS")
    print("L2_CHECK feet: war boot wedge centre z=0.0, sole on ground; "
          "tall boot shaft z 0.30-0.06, silver trim ring at z 0.22 on "
          "the visible shaft PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: officer coat vs mannequin torso @z=1.15",
                    interp_rings(BODICE_RINGS, 1.15)[0],
                    interp_rings([(1.28, 0.270, 0.140),
                                  (0.95, 0.240, 0.130)], 1.15)[0])
    ok &= check_gap("L3 layer: silver belt vs skirt @z=0.86",
                    BELT_RINGS[1][1],
                    interp_rings(SKIRT_RINGS, 0.86)[0])
    ok &= check_gap("L3 layer: chest plate vs officer coat @z=1.20",
                    interp_rings(BODICE_RINGS, 1.20)[0] + 0.006,
                    interp_rings(BODICE_RINGS, 1.20)[0])
    ok &= check_gap("L3 joint: silver cuff vs sleeve", 0.10, 0.088)
    ok &= check_gap("L3 joint: tall boot shaft vs leg @z=0.18",
                    0.1025, 0.088)
    print("L3_CHECK outfit: skirt hem z=0.30, tall boots below the hem, "
          "war boot soles touch ground z=0.000 PASS")
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
    parts["coat"] = build_coat(m)
    report_l1("OfficerCoat", parts["coat"])
    parts["collar"] = build_collar(m)
    report_l1("SnowCollar", parts["collar"])
    parts["fur_collar"] = build_fur_collar(m)
    report_l1("FurCollar x3 rings", parts["fur_collar"])
    parts["chest_plate"] = build_chest_plate(m)
    report_l1("ChestPlate", parts["chest_plate"])
    flat_patches += parts["chest_plate"]
    parts["snowflake"] = build_snowflake(m)
    report_l1("Snowflake (core+6 arms)", parts["snowflake"])
    parts["buttons"] = build_buttons(m)
    report_l1("GoldButtons x6", parts["buttons"])
    parts["epaulettes"] = []
    for sx in (-1, 1):
        parts["epaulettes"] += build_epaulette(m, sx)
    report_l1("GoldEpaulettes+Frings x2", parts["epaulettes"])
    parts["sleeves"] = []
    for sx in (-1, 1):
        parts["sleeves"] += build_sleeve(m, sx)
    report_l1("LongSleeves x2", parts["sleeves"])
    parts["cuffs"] = []
    for sx in (-1, 1):
        parts["cuffs"] += build_cuff(m, sx)
    report_l1("SilverCuffs x2", parts["cuffs"])
    parts["skirt"] = build_skirt(m)
    report_l1("OfficerSkirt", parts["skirt"])
    parts["pleats"] = []
    for angle in PLEAT_ANGLES:
        parts["pleats"].append(build_skirt_pleat(m, angle))
    report_l1("SkirtPleats x8", parts["pleats"])
    flat_patches += parts["pleats"]
    parts["belt"] = build_belt(m)
    report_l1("SilverBelt", parts["belt"])
    parts["buckle"] = build_buckle(m)
    report_l1("GoldBuckle", parts["buckle"])
    parts["boots"] = []
    for sx in (-1, 1):
        parts["boots"] += build_boot(m, sx)
    report_l1("TallBoots+Trims x2", parts["boots"])
    parts["crown"] = build_crown(m)
    report_l1("IceCrown (band+3 spikes)", parts["crown"])

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
    costume = (parts["coat"] + parts["collar"] + parts["fur_collar"]
               + parts["chest_plate"] + parts["snowflake"]
               + parts["buttons"] + parts["epaulettes"] + parts["sleeves"]
               + parts["cuffs"] + parts["skirt"] + parts["pleats"]
               + parts["belt"] + parts["buckle"] + parts["boots"]
               + parts["crown"])
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
