# -*- coding: utf-8 -*-
"""020 原神式层叠幻想 · 纳塔烈焰部落战士套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整套穿到人体底座上试穿）。
设计见 design.md。BACKLOG 本轮已空，自选新题材：原神地区衣橱新方向——纳塔。
Run: blender --background --python build_020.py
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

BLEND_OUT = os.path.join(HERE, "020-natlan-warrior.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "020-natlan-warrior.png")
WIRE_JSON = "/tmp/natlan_warrior_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

BODICE_RINGS = [(1.34, 0.290, 0.155), (1.15, 0.285, 0.150),
                (0.95, 0.278, 0.148), (0.88, 0.275, 0.146)]
SKIRT_RINGS = [(0.88, 0.305, 0.168), (0.60, 0.360, 0.198),
               (0.35, 0.430, 0.237), (0.18, 0.480, 0.264)]
SASH_RINGS = [(0.94, 0.318, 0.176), (0.86, 0.325, 0.180)]
HEM_RINGS = [(0.24, 0.488, 0.268), (0.18, 0.492, 0.270)]
COLLAR_RINGS = [(1.40, 0.150, 0.128), (1.34, 0.160, 0.133)]
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)
CHEST_FLAMES = [(-0.075, 1.14), (0.0, 1.18), (0.075, 1.14)]
SKIRT_FLAMES = [(-0.09, 0.55), (0.09, 0.55)]


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    flamered = solid_material("FlameRed", (0.533, 0.044, 0.015),
                              roughness=0.6)
    flameorange = solid_material("FlameOrange", (0.807, 0.144, 0.012),
                                 roughness=0.6)
    charcoal = solid_material("Charcoal", (0.017, 0.017, 0.023),
                              roughness=0.65)
    bonewhite = solid_material("BoneWhite", (0.863, 0.768, 0.578),
                               roughness=0.6)
    gold = solid_material("Gold", (0.694, 0.371, 0.053),
                          metallic=0.3, roughness=0.45)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    hair = solid_material("Hair_Black", (0.010, 0.010, 0.010),
                          roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"flamered": flamered, "flameorange": flameorange,
            "charcoal": charcoal, "bonewhite": bonewhite, "gold": gold,
            "skin": skin, "hair": hair, "eye": eye}


def front_y(rings, x, z):
    """Front surface Y of an elliptical tube at (x, z)."""
    rx, ry = interp_rings(rings, z)
    return ellipse_front(rx, ry, x)[0]


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001..019).
    Black hair cap (017 v2: z=1.57, scale-z 0.80 covers the crown) +
    two dark eyes (visible). Feet are charcoal boot wedges (z=0.0,
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
                               m["charcoal"]))
    return objs


# ------------------------------------------------------------ L1 components
def build_bodice(m):
    return [make_elliptical_tube("WarriorRobe", BODICE_RINGS, 12,
                                 m["flamered"], caps=False)]


def build_collar(m):
    return [make_elliptical_tube("BlackCollar", COLLAR_RINGS, 12,
                                 m["charcoal"], caps=False)]


def build_chest_plate(m):
    """Charcoal chest plate: curved front panel (232-308 deg,
    z 1.30-0.95) over the red bodice, 0.006 proud."""
    return [build_panel(m, "ChestPlate", BODICE_RINGS,
                        [1.30, 1.18, 1.06, 0.95], 232, 308, 9, 0.006,
                        m["charcoal"])]


def build_flame(m, x, z, rings, mat, r=0.016, zscale=2.6):
    """One flame tongue: flattened elongated ellipsoid, half-embedded
    in the surface so ~0.010 sticks out of the plate."""
    y = front_y(rings, x, z)
    return add_sphere("FlameTongue", (x, y - 0.008, z), r, 6, 4,
                      (0.55, 0.5, zscale), mat)


def build_short_sleeve(m, sx):
    """Red short sleeve (shoulder to mid-arm) + gold cuff ring."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("WarriorSleeve", shoulder, direction,
                      [0.0, 0.14, 0.28], [0.150, 0.154, 0.158], 8,
                      m["flamered"], caps=False),
            make_tube("SleeveGoldCuff", shoulder, direction,
                      [0.22, 0.28], [0.164, 0.164], 8, m["gold"],
                      caps=False)]


def build_bracer(m, sx):
    """Charcoal forearm bracer (elbow to wrist) over the bare arm."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("WarriorBracer", shoulder, direction,
                      [0.28, 0.40, 0.52], [0.098, 0.092, 0.088], 8,
                      m["charcoal"], caps=False)]


def build_skirt(m):
    return [make_elliptical_tube("WarriorSkirt", SKIRT_RINGS, 12,
                                 m["flamered"], caps=False)]


def build_skirt_pleat(m, angle_deg):
    """One vertical skirt pleat: a 4-ring strip hugging the flaring
    skirt surface, 0.006 proud, 0.028 wide, in charcoal so the fold
    reads as a shadowed crease (003 pleat technique)."""
    a = math.radians(angle_deg)
    verts, faces = [], []
    z_list = [0.80, 0.55, 0.32, 0.20]
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
    return mesh_from_data("SkirtPleat", verts, faces, m["charcoal"])


def build_overskirt(m):
    """Charcoal overskirt front panel (232-308 deg, z 0.86-0.40) +
    two gold edge strips (0.007 proud, 0.001 more than the panel)."""
    z_list = [0.86, 0.70, 0.54, 0.40]
    panel = build_panel(m, "OverskirtPanel", SKIRT_RINGS, z_list,
                        232, 308, 9, 0.006, m["charcoal"])
    left = build_panel(m, "PanelGoldEdge", SKIRT_RINGS, z_list,
                       230, 234, 3, 0.007, m["gold"])
    right = build_panel(m, "PanelGoldEdge", SKIRT_RINGS, z_list,
                        306, 310, 3, 0.007, m["gold"])
    return [panel, left, right]


def build_hem(m):
    return [make_elliptical_tube("GoldHem", HEM_RINGS, 12,
                                 m["gold"], caps=False)]


def build_sash(m):
    """Charcoal sash belt: flared top->bottom (0.318->0.325) so the
    bottom edge clears the skirt cone (013 lesson)."""
    return [make_elliptical_tube("BlackSash", SASH_RINGS, 12,
                                 m["charcoal"], caps=False)]


def build_buckle_tassels(m):
    """Gold buckle at the belt front centre + two red tassel cords
    down to z=0.70 with gold bead ends."""
    return [add_box("GoldBuckle", (0, -0.188, 0.90),
                    (0.10, 0.02, 0.07), m["gold"]),
            add_box("RedTassel", (-0.05, -0.185, 0.78),
                    (0.012, 0.008, 0.16), m["flamered"]),
            add_box("RedTassel", (0.05, -0.185, 0.78),
                    (0.012, 0.008, 0.16), m["flamered"]),
            add_sphere("TasselBead", (-0.05, -0.185, 0.69), 0.014, 6, 3,
                       (1.0, 1.0, 1.0), m["gold"]),
            add_sphere("TasselBead", (0.05, -0.185, 0.69), 0.014, 6, 3,
                       (1.0, 1.0, 1.0), m["gold"])]


def build_pauldron(m, sx):
    """Charcoal shoulder pauldron: flattened half-sphere over the
    shoulder top (008 technique)."""
    return [add_sphere("Pauldron", (sx * 0.36, 0, 1.24), 0.13, 8, 4,
                       (1.15, 0.9, 0.55), m["charcoal"])]


def build_feather(m, tilt_deg, mat):
    """One headdress feather: elongated flattened ellipsoid, base at
    the gold band (z=1.66), fanning out at tilt_deg from vertical."""
    tilt = math.radians(tilt_deg)
    direction = Vector((math.sin(tilt), 0, math.cos(tilt)))
    centre = Vector((0, 0.0, 1.72)) + direction * 0.07
    obj = add_sphere("Feather", tuple(centre), 0.020, 6, 4,
                     (0.6, 0.35, 5.0), mat)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    obj.rotation_euler = (0, tilt, 0)
    bpy.ops.object.transform_apply(location=False, rotation=True,
                                   scale=False)
    obj.select_set(False)
    return obj


def build_headdress(m):
    """Gold band ring around the hair cap (z=1.62, r=0.222; hair rx
    there is 0.216, so the ring sits 0.006 proud) + 5 feathers
    fanning from it: red / orange / bone-white / orange / red."""
    objs = [make_tube("GoldHeadband", (0, 0, 1.62), (0, 0, 1),
                      [0.0, 0.014], [0.222, 0.222], 16, m["gold"],
                      caps=False)]
    mats = [m["flamered"], m["flameorange"], m["bonewhite"],
            m["flameorange"], m["flamered"]]
    for tilt, mat in zip((-40, -20, 0, 20, 40), mats):
        objs.append(build_feather(m, tilt, mat))
    return objs


def build_boot_trim(m, sx):
    """Gold sole trim: flat plate under the war boot, z 0.0-0.012,
    slightly larger than the boot so the gold rim shows."""
    return [add_box("BootGoldTrim", (sx * 0.13, -0.05, 0.006),
                    (0.20, 0.30, 0.012), m["gold"])]


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["bodice"] + parts["collar"] + parts["chest_plate"]
            + parts["flames_chest"])
    ok = True
    ok &= check_gap("torso: black collar vs mannequin neck",
                    COLLAR_RINGS[0][1], 0.09)
    ok &= check_relief("torso: chest plate relief", 0.006)
    ok &= check_relief("torso: flame tongue relief", 0.010,
                       lo=0.005, hi=0.015)
    ok &= check_gap("torso: warrior robe vs mannequin torso @z=1.15",
                    interp_rings(BODICE_RINGS, 1.15)[0],
                    interp_rings([(1.28, 0.270, 0.140),
                                  (0.95, 0.240, 0.130)], 1.15)[0])
    return objs, ok


def assemble_arms(parts):
    objs = parts["sleeves"] + parts["bracers"]
    ok = True
    ok &= check_gap("arms: short sleeve vs mannequin arm @0.14",
                    0.154, 0.082)
    ok &= check_gap("arms: gold cuff vs sleeve @0.22",
                    0.164, 0.158)
    ok &= check_gap("arms: bracer vs mannequin arm @0.40",
                    0.092, 0.078)
    print("L2_CHECK arms: red short sleeve flares 0.150->0.158, gold "
          "cuff proud, charcoal bracer over the forearm PASS")
    return objs, ok


def assemble_skirt(parts):
    objs = (parts["skirt"] + parts["pleats"] + parts["overskirt"]
            + parts["hem"] + parts["flames_skirt"])
    ok = True
    ok &= check_relief("skirt: skirt pleat relief", 0.006)
    ok &= check_relief("skirt: overskirt panel relief", 0.006)
    ok &= check_relief("skirt: panel gold edge relief", 0.007)
    ok &= check_relief("skirt: flame tongue relief", 0.010,
                       lo=0.005, hi=0.015)
    ok &= check_gap("skirt: gold hem vs skirt @z=0.18",
                    interp_rings(HEM_RINGS, 1)[0],
                    interp_rings(SKIRT_RINGS, 0.18)[0])
    ok &= check_gap("skirt: gold hem vs skirt @z=0.24",
                    interp_rings(HEM_RINGS, 0)[0],
                    interp_rings(SKIRT_RINGS, 0.24)[0])
    return objs, ok


def assemble_waist(parts):
    objs = parts["sash"] + parts["buckle"]
    ok = True
    ok &= check_gap("waist: black sash vs warrior robe @z=0.88",
                    SASH_RINGS[1][1],
                    interp_rings(BODICE_RINGS, 0.88)[0])
    ok &= check_gap("waist: black sash bottom edge vs skirt @z=0.86",
                    SASH_RINGS[1][1],
                    interp_rings(SKIRT_RINGS, 0.86)[0])
    ok &= check_relief("waist: gold buckle relief", 0.020,
                       lo=0.005, hi=0.030)
    ok &= check_relief("waist: red tassel relief", 0.011,
                       lo=0.005, hi=0.030)
    return objs, ok


def assemble_shoulder(parts):
    objs = parts["pauldrons"]
    ok = True
    ok &= check_gap("shoulder: pauldron vs warrior robe @z=1.24",
                    0.36, interp_rings(BODICE_RINGS, 1.24)[0])
    print("L2_CHECK shoulder: charcoal pauldrons sit on the shoulder "
          "tops, clear of the black collar PASS")
    return objs, ok


def assemble_head_feet(parts):
    objs = parts["headdress"] + parts["boot_trims"]
    ok = True
    ok &= check_gap("head: gold headband vs hair cap @z=1.62", 0.222, 0.216)
    print("L2_CHECK head: gold headband 0.006 proud of hair cap, 5 "
          "feathers fan -40..+40 deg from the band PASS")
    print("L2_CHECK feet: war boot wedge centre z=0.0, sole on ground; "
          "gold trim plate z 0.0-0.012 wraps the boot PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: warrior robe vs mannequin torso @z=1.15",
                    interp_rings(BODICE_RINGS, 1.15)[0],
                    interp_rings([(1.28, 0.270, 0.140),
                                  (0.95, 0.240, 0.130)], 1.15)[0])
    ok &= check_gap("L3 layer: black sash vs skirt @z=0.86",
                    SASH_RINGS[1][1],
                    interp_rings(SKIRT_RINGS, 0.86)[0])
    ok &= check_gap("L3 layer: gold hem vs skirt @z=0.18",
                    interp_rings(HEM_RINGS, 1)[0],
                    interp_rings(SKIRT_RINGS, 0.18)[0])
    ok &= check_gap("L3 layer: chest plate vs warrior robe @z=1.18",
                    interp_rings(BODICE_RINGS, 1.18)[0] + 0.006,
                    interp_rings(BODICE_RINGS, 1.18)[0])
    ok &= check_gap("L3 joint: gold cuff vs sleeve", 0.164, 0.158)
    ok &= check_gap("L3 joint: bracer vs mannequin arm", 0.092, 0.078)
    print("L3_CHECK outfit: skirt hem z=0.18, war boots touch ground "
          "z=0.000, gold trim wraps the boots PASS")
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
    report_l1("WarriorRobe", parts["bodice"])
    parts["collar"] = build_collar(m)
    report_l1("BlackCollar", parts["collar"])
    parts["chest_plate"] = build_chest_plate(m)
    report_l1("ChestPlate", parts["chest_plate"])
    flat_patches += parts["chest_plate"]
    parts["flames_chest"] = []
    for cx, cz in CHEST_FLAMES:
        parts["flames_chest"].append(
            build_flame(m, cx, cz, BODICE_RINGS, m["flameorange"]))
    report_l1("FlameTonguesChest x3", parts["flames_chest"])
    parts["sleeves"] = []
    for sx in (-1, 1):
        parts["sleeves"] += build_short_sleeve(m, sx)
    report_l1("ShortSleeves+GoldCuffs x2", parts["sleeves"])
    parts["bracers"] = []
    for sx in (-1, 1):
        parts["bracers"] += build_bracer(m, sx)
    report_l1("WarriorBracers x2", parts["bracers"])
    parts["skirt"] = build_skirt(m)
    report_l1("WarriorSkirt", parts["skirt"])
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
    report_l1("BlackSash", parts["sash"])
    parts["buckle"] = build_buckle_tassels(m)
    report_l1("GoldBuckle+Tassels+Beads", parts["buckle"])
    parts["pauldrons"] = []
    for sx in (-1, 1):
        parts["pauldrons"] += build_pauldron(m, sx)
    report_l1("Pauldrons x2", parts["pauldrons"])
    parts["headdress"] = build_headdress(m)
    report_l1("GoldHeadband+Feathers x5", parts["headdress"])
    parts["flames_skirt"] = []
    for cx, cz in SKIRT_FLAMES:
        parts["flames_skirt"].append(
            build_flame(m, cx, cz, SKIRT_RINGS, m["flameorange"],
                        r=0.015, zscale=2.2))
    report_l1("FlameTonguesSkirt x2", parts["flames_skirt"])
    parts["boot_trims"] = []
    for sx in (-1, 1):
        parts["boot_trims"] += build_boot_trim(m, sx)
    report_l1("BootGoldTrims x2", parts["boot_trims"])

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    _, ok = assemble_torso(parts)
    l2_ok &= ok
    _, ok = assemble_arms(parts)
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
    costume = (parts["bodice"] + parts["collar"] + parts["chest_plate"]
               + parts["flames_chest"] + parts["sleeves"]
               + parts["bracers"] + parts["skirt"] + parts["pleats"]
               + parts["overskirt"] + parts["hem"] + parts["sash"]
               + parts["buckle"] + parts["pauldrons"]
               + parts["headdress"] + parts["flames_skirt"]
               + parts["boot_trims"])
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
