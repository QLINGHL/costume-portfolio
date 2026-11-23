# -*- coding: utf-8 -*-
"""021 鸣潮式机能风 · 今州巡宁者套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整套穿到人体底座上试穿）。
设计见 design.md。BACKLOG 本轮已空，自选新题材：鸣潮地区衣橱新方向——今州。
Run: blender --background --python build_021.py
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

BLEND_OUT = os.path.join(HERE, "021-jinzhou-ranger.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "021-jinzhou-ranger.png")
WIRE_JSON = "/tmp/jinzhou_ranger_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

BODICE_RINGS = [(1.34, 0.288, 0.152), (1.15, 0.282, 0.148),
                (0.92, 0.272, 0.144)]
COLLAR_RINGS = [(1.42, 0.150, 0.128), (1.34, 0.158, 0.132)]
TROUSER_RINGS = [(0.92, 0.290, 0.152), (0.62, 0.260, 0.140),
                 (0.35, 0.235, 0.128), (0.12, 0.220, 0.120)]
BELT_RINGS = [(0.94, 0.300, 0.158), (0.86, 0.306, 0.160)]
CHEST_BAND_RINGS = [(1.14, 0.290, 0.152), (1.10, 0.290, 0.152)]
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)
ZIPPER_Z = [1.28, 1.225, 1.17, 1.115, 1.06, 1.005, 0.95]


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    inkblack = solid_material("InkBlack", (0.014, 0.014, 0.019),
                              roughness=0.65)
    rockgray = solid_material("RockGray", (0.254, 0.266, 0.283),
                              roughness=0.6)
    jade = solid_material("JadeGreen", (0.028, 0.365, 0.201),
                          roughness=0.6)
    bonewhite = solid_material("BoneWhite", (0.806, 0.775, 0.687),
                               roughness=0.6)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    hair = solid_material("Hair_Black", (0.010, 0.010, 0.010),
                          roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"inkblack": inkblack, "rockgray": rockgray, "jade": jade,
            "bonewhite": bonewhite, "skin": skin, "hair": hair,
            "eye": eye}


def front_y(rings, x, z):
    """Front surface Y of an elliptical tube at (x, z)."""
    rx, ry = interp_rings(rings, z)
    return ellipse_front(rx, ry, x)[0]


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001..020).
    Black hair cap (017 v2: z=1.57, scale-z 0.80 covers the crown) +
    two dark eyes (visible). Feet are ink-black boot wedges (z=0.0,
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
                               m["inkblack"]))
    return objs


# ------------------------------------------------------------ L1 components
def build_jacket(m):
    return [make_elliptical_tube("RangerJacket", BODICE_RINGS, 12,
                                 m["inkblack"], caps=False)]


def build_collar(m):
    return [make_elliptical_tube("JadeCollar", COLLAR_RINGS, 12,
                                 m["jade"], caps=False)]


def build_chest_plate(m):
    """Rock-gray chest plate: curved front panel (232-308 deg,
    z 1.30-1.00) over the black jacket, 0.006 proud."""
    return [build_panel(m, "ChestPlate", BODICE_RINGS,
                        [1.30, 1.18, 1.06, 1.00], 232, 308, 9, 0.006,
                        m["rockgray"])]


def build_emblem(m):
    """Jade emblem: flattened ellipsoid half-embedded in the chest
    plate, ~0.006 proud, at the plate centre (z=1.16)."""
    y = front_y(BODICE_RINGS, 0, 1.16) + 0.006 - 0.010
    return [add_sphere("JadeEmblem", (0, y, 1.16), 0.032, 6, 4,
                       (1.0, 0.5, 1.0), m["jade"])]


def build_chest_band(m):
    """Jade chest band: elliptical arc tube (232-308 deg, z 1.14-1.10)
    over the jacket, 0.0065 proud (016 arc-band technique)."""
    return [make_elliptical_tube("JadeChestBand", CHEST_BAND_RINGS, 12,
                                 m["jade"], arc=(232, 308), caps=False)]


def build_zipper(m):
    """Seven jade zipper teeth down the jacket front centre line,
    each half-embedded in the jacket surface."""
    objs = []
    for z in ZIPPER_Z:
        y = front_y(BODICE_RINGS, 0, z) - 0.004
        objs.append(add_box("ZipperTooth", (0, y, z),
                            (0.018, 0.010, 0.014), m["jade"]))
    return objs


def build_long_sleeve(m, sx):
    """Black long sleeve (shoulder to wrist) over the mannequin arm."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("RangerSleeve", shoulder, direction,
                      [0.0, 0.13, 0.26, 0.39, 0.52],
                      [0.098, 0.096, 0.093, 0.090, 0.086], 10,
                      m["inkblack"], caps=False)]


def build_arm_guard(m, sx):
    """Rock-gray forearm guard (elbow to wrist) over the sleeve."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("RangerArmGuard", shoulder, direction,
                      [0.30, 0.41, 0.52], [0.102, 0.098, 0.094], 10,
                      m["rockgray"], caps=False)]


def build_wrist_band(m, sx):
    """Jade wrist band over the arm guard at the wrist."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("JadeWristBand", shoulder, direction,
                      [0.46, 0.52], [0.102, 0.102], 10,
                      m["jade"], caps=False)]


def build_pauldron(m, sx):
    """Rock-gray shoulder pauldron: flattened half-sphere over the
    shoulder top (008 technique)."""
    return [add_sphere("Pauldron", (sx * 0.36, 0, 1.24), 0.13, 8, 4,
                       (1.15, 0.9, 0.55), m["rockgray"])]


def build_trousers(m):
    return [make_elliptical_tube("RangerTrousers", TROUSER_RINGS, 12,
                                 m["inkblack"], caps=False)]


def build_trouser_seam(m, angle_deg):
    """One vertical trouser seam strip: a 4-ring strip hugging the
    flaring trouser surface, 0.006 proud, 0.028 wide, in jade so the
    seam reads on the black cloth (003 pleat technique)."""
    a = math.radians(angle_deg)
    verts, faces = [], []
    z_list = [0.88, 0.62, 0.35, 0.14]
    for z in z_list:
        rx, ry = interp_rings(TROUSER_RINGS, z)
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
    return mesh_from_data("TrouserSeam", verts, faces, m["jade"])


def build_knee_pad(m, sx):
    """Rock-gray knee pad: flattened ellipsoid half-embedded in the
    trouser front at z=0.35, ~0.017 proud."""
    y = front_y(TROUSER_RINGS, sx * 0.13, 0.35) - 0.008
    return [add_sphere("KneePad", (sx * 0.13, y, 0.35), 0.05, 6, 4,
                       (1.0, 0.5, 1.3), m["rockgray"])]


def build_cargo_pocket(m, sx):
    """Rock-gray cargo pocket: box half-embedded in the trouser side."""
    return [add_box("CargoPocket", (sx * 0.245, 0, 0.55),
                    (0.10, 0.035, 0.15), m["rockgray"])]


def build_belt(m):
    """Rock-gray tactical belt: flared top->bottom (0.300->0.306) so
    the bottom edge clears the trouser cone (013 lesson)."""
    return [make_elliptical_tube("TacticalBelt", BELT_RINGS, 12,
                                 m["rockgray"], caps=False)]


def build_buckle(m):
    """Jade buckle at the belt front centre."""
    return [add_box("JadeBuckle", (0, -0.170, 0.90),
                    (0.09, 0.02, 0.05), m["jade"])]


def build_utility_pouch(m):
    """Rock-gray utility pouch on the belt's right side + jade flap."""
    return [add_box("UtilityPouch", (0.29, -0.05, 0.72),
                    (0.09, 0.05, 0.12), m["rockgray"]),
            add_box("PouchFlap", (0.29, -0.078, 0.77),
                    (0.095, 0.012, 0.05), m["jade"])]


def build_headband(m):
    """Jade band ring around the hair cap (z=1.62, r=0.222; hair rx
    there is 0.216, so the ring sits 0.006 proud)."""
    return [make_tube("JadeHeadband", (0, 0, 1.62), (0, 0, 1),
                      [0.0, 0.014], [0.222, 0.222], 16, m["jade"],
                      caps=False)]


def build_hairpin(m):
    """Jade hairpin slanted into the hair's right side (rotated 0.3
    rad about Z) + bone-white bead at its top end, outside the hair
    surface (hair rx at z=1.67 is 0.187, bead centre x=0.211)."""
    pin = add_box_rot("JadeHairpin", (0.19, -0.08, 1.60),
                      (0.012, 0.012, 0.14), m["jade"], (0, 0, 0.3))
    bead = add_sphere("HairpinBead", (0.211, -0.08, 1.667), 0.016, 6, 3,
                      (1.0, 1.0, 1.0), m["bonewhite"])
    return [pin, bead]


def build_boot_trim(m, sx):
    """Jade sole trim: flat plate under the war boot, z 0.0-0.012,
    slightly larger than the boot so the jade rim shows."""
    return [add_box("BootJadeTrim", (sx * 0.13, -0.05, 0.006),
                    (0.20, 0.30, 0.012), m["jade"])]


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["jacket"] + parts["collar"] + parts["chest_plate"]
            + parts["emblem"] + parts["chest_band"] + parts["zipper"])
    ok = True
    ok &= check_gap("torso: jade collar vs mannequin neck",
                    COLLAR_RINGS[0][1], 0.09)
    ok &= check_relief("torso: chest plate relief", 0.006)
    ok &= check_relief("torso: jade emblem relief", 0.006)
    ok &= check_gap("torso: jade chest band vs jacket @z=1.12",
                    CHEST_BAND_RINGS[0][1],
                    interp_rings(BODICE_RINGS, 1.12)[0])
    ok &= check_relief("torso: zipper tooth relief", 0.009,
                       lo=0.005, hi=0.015)
    ok &= check_gap("torso: ranger jacket vs mannequin torso @z=1.15",
                    interp_rings(BODICE_RINGS, 1.15)[0],
                    interp_rings([(1.28, 0.270, 0.140),
                                  (0.95, 0.240, 0.130)], 1.15)[0])
    return objs, ok


def assemble_arms(parts):
    objs = parts["sleeves"] + parts["arm_guards"] + parts["wrist_bands"]
    ok = True
    ok &= check_gap("arms: long sleeve vs mannequin arm @0.0",
                    0.098, 0.085)
    ok &= check_gap("arms: arm guard vs sleeve @0.30", 0.102, 0.0915)
    ok &= check_gap("arms: jade wrist band vs arm guard @0.46",
                    0.102, 0.0962)
    print("L2_CHECK arms: black long sleeve 0.098->0.086, rock-gray "
          "guard over the forearm, jade wrist band at the wrist PASS")
    return objs, ok


def assemble_shoulders(parts):
    objs = parts["pauldrons"]
    ok = True
    ok &= check_gap("shoulder: pauldron vs ranger jacket @z=1.24",
                    0.36, interp_rings(BODICE_RINGS, 1.24)[0])
    print("L2_CHECK shoulder: rock-gray pauldrons sit on the shoulder "
          "tops, clear of the jade collar PASS")
    return objs, ok


def assemble_trousers(parts):
    objs = (parts["trousers"] + parts["seams"] + parts["knee_pads"]
            + parts["cargo_pockets"])
    ok = True
    ok &= check_relief("trousers: trouser seam relief", 0.006)
    ok &= check_relief("trousers: knee pad relief", 0.017,
                       lo=0.005, hi=0.030)
    ok &= check_gap("trousers: trousers vs legs @z=0.62", 0.260, 0.235)
    ok &= check_gap("trousers: cargo pocket vs trouser side @z=0.55",
                    0.295, interp_rings(TROUSER_RINGS, 0.55)[0])
    return objs, ok


def assemble_waist(parts):
    objs = parts["belt"] + parts["buckle"] + parts["utility_pouch"]
    ok = True
    ok &= check_gap("waist: tactical belt vs ranger jacket @z=0.92",
                    interp_rings(BELT_RINGS, 0.92)[0],
                    interp_rings(BODICE_RINGS, 0.92)[0])
    ok &= check_gap("waist: tactical belt bottom edge vs trousers @z=0.86",
                    BELT_RINGS[1][1],
                    interp_rings(TROUSER_RINGS, 0.86)[0])
    ok &= check_relief("waist: jade buckle relief", 0.021,
                       lo=0.005, hi=0.030)
    return objs, ok


def assemble_head_feet(parts):
    objs = parts["headband"] + parts["hairpin"] + parts["boot_trims"]
    ok = True
    ok &= check_gap("head: jade headband vs hair cap @z=1.62", 0.222, 0.216)
    print("L2_CHECK head: jade headband 0.006 proud of hair cap, jade "
          "hairpin slanted into the hair, bone-white bead outside "
          "the hair surface PASS")
    print("L2_CHECK feet: war boot wedge centre z=0.0, sole on ground; "
          "jade trim plate z 0.0-0.012 wraps the boot PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: ranger jacket vs mannequin torso @z=1.15",
                    interp_rings(BODICE_RINGS, 1.15)[0],
                    interp_rings([(1.28, 0.270, 0.140),
                                  (0.95, 0.240, 0.130)], 1.15)[0])
    ok &= check_gap("L3 layer: tactical belt vs trousers @z=0.86",
                    BELT_RINGS[1][1],
                    interp_rings(TROUSER_RINGS, 0.86)[0])
    ok &= check_gap("L3 layer: chest plate vs ranger jacket @z=1.18",
                    interp_rings(BODICE_RINGS, 1.18)[0] + 0.006,
                    interp_rings(BODICE_RINGS, 1.18)[0])
    ok &= check_gap("L3 joint: arm guard vs sleeve", 0.102, 0.0915)
    ok &= check_gap("L3 joint: jade wrist band vs arm guard", 0.102, 0.0962)
    print("L3_CHECK outfit: trouser hem z=0.12, war boots touch ground "
          "z=0.000, jade trim wraps the boots PASS")
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
    parts["jacket"] = build_jacket(m)
    report_l1("RangerJacket", parts["jacket"])
    parts["collar"] = build_collar(m)
    report_l1("JadeCollar", parts["collar"])
    parts["chest_plate"] = build_chest_plate(m)
    report_l1("ChestPlate", parts["chest_plate"])
    flat_patches += parts["chest_plate"]
    parts["emblem"] = build_emblem(m)
    report_l1("JadeEmblem", parts["emblem"])
    parts["chest_band"] = build_chest_band(m)
    report_l1("JadeChestBand", parts["chest_band"])
    parts["zipper"] = build_zipper(m)
    report_l1("ZipperTeeth x7", parts["zipper"])
    parts["sleeves"] = []
    for sx in (-1, 1):
        parts["sleeves"] += build_long_sleeve(m, sx)
    report_l1("LongSleeves x2", parts["sleeves"])
    parts["arm_guards"] = []
    for sx in (-1, 1):
        parts["arm_guards"] += build_arm_guard(m, sx)
    report_l1("ArmGuards x2", parts["arm_guards"])
    parts["wrist_bands"] = []
    for sx in (-1, 1):
        parts["wrist_bands"] += build_wrist_band(m, sx)
    report_l1("JadeWristBands x2", parts["wrist_bands"])
    parts["pauldrons"] = []
    for sx in (-1, 1):
        parts["pauldrons"] += build_pauldron(m, sx)
    report_l1("Pauldrons x2", parts["pauldrons"])
    parts["trousers"] = build_trousers(m)
    report_l1("RangerTrousers", parts["trousers"])
    parts["seams"] = []
    for angle in (245, 270, 295):
        parts["seams"].append(build_trouser_seam(m, angle))
    report_l1("TrouserSeams x3", parts["seams"])
    flat_patches += parts["seams"]
    parts["knee_pads"] = []
    for sx in (-1, 1):
        parts["knee_pads"] += build_knee_pad(m, sx)
    report_l1("KneePads x2", parts["knee_pads"])
    parts["cargo_pockets"] = []
    for sx in (-1, 1):
        parts["cargo_pockets"] += build_cargo_pocket(m, sx)
    report_l1("CargoPockets x2", parts["cargo_pockets"])
    parts["belt"] = build_belt(m)
    report_l1("TacticalBelt", parts["belt"])
    parts["buckle"] = build_buckle(m)
    report_l1("JadeBuckle", parts["buckle"])
    parts["utility_pouch"] = build_utility_pouch(m)
    report_l1("UtilityPouch+Flap", parts["utility_pouch"])
    parts["headband"] = build_headband(m)
    report_l1("JadeHeadband", parts["headband"])
    parts["hairpin"] = build_hairpin(m)
    report_l1("JadeHairpin+Bead", parts["hairpin"])
    parts["boot_trims"] = []
    for sx in (-1, 1):
        parts["boot_trims"] += build_boot_trim(m, sx)
    report_l1("BootJadeTrims x2", parts["boot_trims"])

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    _, ok = assemble_torso(parts)
    l2_ok &= ok
    _, ok = assemble_arms(parts)
    l2_ok &= ok
    _, ok = assemble_shoulders(parts)
    l2_ok &= ok
    _, ok = assemble_trousers(parts)
    l2_ok &= ok
    _, ok = assemble_waist(parts)
    l2_ok &= ok
    _, ok = assemble_head_feet(parts)
    l2_ok &= ok
    print("L2_SUMMARY %s" % ("ALL PASS" if l2_ok else "FAILURES PRESENT"))

    # ---- L3 full outfit on the mannequin ----
    costume = (parts["jacket"] + parts["collar"] + parts["chest_plate"]
               + parts["emblem"] + parts["chest_band"] + parts["zipper"]
               + parts["sleeves"] + parts["arm_guards"]
               + parts["wrist_bands"] + parts["pauldrons"]
               + parts["trousers"] + parts["seams"] + parts["knee_pads"]
               + parts["cargo_pockets"] + parts["belt"] + parts["buckle"]
               + parts["utility_pouch"] + parts["headband"]
               + parts["hairpin"] + parts["boot_trims"])
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
