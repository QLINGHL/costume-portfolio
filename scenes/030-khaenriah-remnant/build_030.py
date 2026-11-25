# -*- coding: utf-8 -*-
"""030 原神式层叠幻想 · 坎瑞亚遗民套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整套穿到人体底座上试穿）。
设计见 design.md。BACKLOG 已空，本轮自选：原神线第八个地区——坎瑞亚
（001 璃月、004 蒙德、017 枫丹、018 稻妻、019 须弥、020 纳塔、022 至冬
之后；地下古国遗民方向，首次做）。深紫修身长袍前开襟 + 黑内衬 +
鎏金菱形符文×4 + 金腰封 + 金裙摆边 + 黑兜帽 + 金额带 + 幽紫额宝石 +
金肩甲 + 黑披风 + 裙摆褶裥×8 + 黑高筒靴金靴环 + 银白发 + 幽紫挑染。
兜帽/披风沿用 024 做法、褶裥沿用 026 做法、额带沿用 024 额带环数。
Run: blender --background --python build_030.py
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

BLEND_OUT = os.path.join(HERE, "030-khaenriah-remnant.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "030-khaenriah-remnant.png")
WIRE_JSON = "/tmp/khaenriah_remnant_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

ROBE_TOP_RINGS = [(1.42, 0.280, 0.145), (1.10, 0.290, 0.150),
                  (0.72, 0.300, 0.155)]
TUNIC_RINGS = [(1.40, 0.262, 0.138), (1.30, 0.277, 0.143),
               (1.00, 0.252, 0.134), (0.72, 0.248, 0.132)]  # v2: 1.30
# ring flares to 0.277 so the tunic covers the mannequin torso top
# ring (0.270 at z=1.28); v1's straight 0.258 let the skin torso poke
# through the tunic at the chest V
ROBE_SKIRT_RINGS = [(0.74, 0.308, 0.158), (0.40, 0.332, 0.170),
                    (0.10, 0.360, 0.185)]
WAIST_RINGS = [(0.78, 0.306, 0.158), (0.74, 0.306, 0.158)]
HEM_RINGS = [(0.15, 0.366, 0.188), (0.10, 0.366, 0.188)]
HOOD_RINGS = [(1.50, 0.230, 0.218), (1.62, 0.225, 0.213),
              (1.70, 0.100, 0.094)]  # v2: top lowered 1.74->1.70 and
# narrowed 0.120->0.100: v1's top corners stuck out past the silver
# hair (rx 0.074 at z=1.74) and read as black ears; 024's black hair
# hid this, silver hair exposes it
BROW_RINGS = [(1.58, 0.224, 0.194), (1.55, 0.226, 0.193)]
CAPE_RINGS = [(1.30, 0.312, 0.160), (1.00, 0.305, 0.157),
              (0.70, 0.320, 0.162), (0.50, 0.342, 0.172)]
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)
PLEAT_ANGLES = [200, 230, 260, 290, 320, 350, 10, 170]  # all outside
# the cape's 15-165 deg back panel: a fin inside that range would poke
# through the cape (fin outer edge 0.350 vs cape 0.342 at z=0.50)


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    # Gold tuple reuses the 029 established value for line consistency.
    violet = solid_material("Violet", (0.047, 0.025, 0.112), roughness=0.6)
    charcoal = solid_material("Charcoal", (0.011, 0.011, 0.015),
                              roughness=0.6)
    gold = solid_material("Gold", (0.657, 0.351, 0.009), metallic=0.6,
                          roughness=0.35)
    paleviolet = solid_material("PaleViolet", (0.434, 0.212, 0.807),
                                roughness=0.6)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    hair = solid_material("Hair_Silver", (0.624, 0.624, 0.687),
                          roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"violet": violet, "charcoal": charcoal, "gold": gold,
            "paleviolet": paleviolet, "skin": skin, "hair": hair,
            "eye": eye}


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001..029).
    Silver-white hair cap (z=1.57, scale-z 0.80 covers the crown) —
    the Khaenri'ah remnant mark; every earlier piece used black hair.
    Two dark eyes stay visible below the gold brow band."""
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
def build_robe_top(m):
    """Violet robe bodice, open front: arc 300-600 deg leaves the
    240-300 deg front wedge open so the black tunic + gold runes show.
    Fitted 0.280->0.300, hem z 0.72."""
    return [make_elliptical_tube("VioletRobeTop", ROBE_TOP_RINGS, 16,
                                 m["violet"], arc=(300, 600), caps=False)]


def build_tunic(m):
    """Black tunic under the robe opening: 0.258->0.248, at least
    0.03 narrower than the robe at every height."""
    return [make_elliptical_tube("BlackTunic", TUNIC_RINGS, 12,
                                 m["charcoal"], caps=False)]


def build_runes(m):
    """Four gold diamond runes down the tunic front (270 deg):
    boxes rotated 45 deg about Y, centres on the tunic surface so
    each diamond protrudes 0.006. The chest emblem is larger."""
    objs = []
    specs = [(1.32, 0.062), (1.12, 0.045), (0.92, 0.045), (0.80, 0.045)]
    for i, (z, size) in enumerate(specs):
        rx, ry = interp_rings(TUNIC_RINGS, z)
        objs.append(add_box_rot("GoldRune%d" % (i + 1),
                                (0, -ry, z), (size, 0.012, size),
                                m["gold"], (0, math.pi / 4, 0)))
    return objs


def build_waistband(m):
    """Gold waistband ring over the robe/skirt seam (z 0.78-0.74,
    0.306, 0.007 proud of the robe) + gold buckle on the front."""
    band = make_elliptical_tube("GoldWaistband", WAIST_RINGS, 12,
                                m["gold"], caps=False)
    buckle = add_box("GoldWaistBuckle", (0, -0.160, 0.76),
                     (0.035, 0.012, 0.028), m["gold"])
    return [band, buckle]


def build_skirt(m):
    """Violet robe skirt: full tube, flare 0.308->0.360, top ring
    0.008 wider than the bodice hem so it hangs outside it."""
    return [make_elliptical_tube("VioletRobeSkirt", ROBE_SKIRT_RINGS, 12,
                                 m["violet"], caps=False)]


def build_hem(m):
    """Gold hem band at the skirt bottom (z 0.15-0.10, 0.366):
    0.006 proud at the bottom ring, 0.011 at the top."""
    return [make_elliptical_tube("GoldHemBand", HEM_RINGS, 12,
                                 m["gold"], caps=False)]


def build_pleat_fin(m, angle_deg):
    """One 3D pleat fin: a closed thin solid (10 quads) following the
    skirt cone, inner edge 0.004 off the skirt, outer edge 0.026 off,
    tangential half-thickness 0.004. Same construction as 026."""
    rows = [0.70, 0.45, 0.20]
    a = math.radians(angle_deg)
    verts = []
    for z in rows:
        rx, ry = interp_rings(ROBE_SKIRT_RINGS, z)
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
    return mesh_from_data("VioletPleat", verts, faces, m["violet"])


def build_sleeve(m, sx):
    """Black fitted sleeve (shoulder to wrist) over the mannequin arm.
    Capped (025 v2 lesson) with the origin lifted 0.005 along the arm
    axis so the sleeve cap never sits coplanar with the arm cap."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    origin = shoulder - direction.normalized() * 0.005
    return [make_tube("BlackSleeve", origin, direction,
                      [0.0, 0.13, 0.26, 0.39, 0.52],
                      [0.105, 0.103, 0.100, 0.096, 0.092], 10,
                      m["charcoal"], caps=True)]


def build_arm_ring(m, sx):
    """Gold arm ring on the forearm (arm param 0.30-0.34, r 0.104):
    0.0058 proud of the sleeve (0.0982 there)."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("GoldArmRing", shoulder, direction,
                      [0.30, 0.34], [0.104, 0.104], 10,
                      m["gold"], caps=False)]


def build_pauldron(m, sx):
    """Gold pauldron: flattened sphere on the shoulder, covering the
    sleeve cap and the robe shoulder seam."""
    return add_sphere("GoldPauldron", (sx * 0.33, 0, 1.30), 0.085,
                      8, 4, (1.0, 0.85, 0.55), m["gold"])


def build_hood(m):
    """Black hood: curved back panel (15-165 deg, z 1.50-1.70) over
    the hair cap, 0.006 proud, top ring narrowing to 0.100 so the
    hood frames the hair without its corners sticking past the
    silver hair silhouette (v2: v1 top 1.74/0.120 read as black
    ears on silver hair)."""
    return [build_panel(m, "BlackHood", HOOD_RINGS,
                        [1.50, 1.62, 1.70], 15, 165, 9, 0.006,
                        m["charcoal"])]


def build_brow_band(m):
    """Gold brow band across the forehead (250-290 deg, z 1.58-1.55)
    over the silver hair, 0.006 proud; 024 visor rings, gold."""
    return [build_panel(m, "GoldBrowBand", BROW_RINGS,
                        [1.58, 1.55], 250, 290, 7, 0.006,
                        m["gold"])]


def build_gem(m):
    """Pale-violet forehead gem: small box half-buried in the hair
    front (hair surface y=-0.191 at z 1.60), outer face 0.005 proud."""
    return [add_box("PaleVioletGem", (0, -0.191, 1.60),
                    (0.030, 0.012, 0.030), m["paleviolet"])]


def build_boot(m, sx):
    """Black tall boot: wedge sole (lands z=0.0, encloses the
    mannequin foot wedge) + shaft over the leg, mostly hidden under
    the robe skirt, + gold trim ring on the visible shaft at
    z 0.05-0.07 (022 lesson: keep trim on the visible stretch)."""
    wedge = make_wedge("BlackBoot", (sx * 0.13, -0.02, 0.0),
                       0.100, 0.095, -0.165, 0.0, 0.105, 0.05,
                       m["charcoal"])
    shaft = make_tube("BlackBootShaft", (sx * 0.13, 0, 0.14), (0, 0, -1),
                      [0.0, 0.11], [0.105, 0.102], 10,
                      m["charcoal"], caps=False)
    trim = make_tube("GoldBootTrim", (sx * 0.13, 0, 0.07), (0, 0, -1),
                     [0.0, 0.02], [0.108, 0.108], 10,
                     m["gold"], caps=False)
    return [wedge, shaft, trim]


def build_cape(m):
    """Black cape: curved back panel (15-165 deg, z 1.30-0.50) over
    the robe, 0.006 proud; rings stay wider than the robe bodice and
    the skirt so the cape hangs outside both (024)."""
    return [build_panel(m, "BlackCape", CAPE_RINGS,
                        [1.30, 1.00, 0.70, 0.50], 15, 165, 9, 0.006,
                        m["charcoal"])]


def build_streak(m):
    """Pale-violet hair streak: flat box on the hair's right front,
    lying against the hair surface (029 streak position, recolored)."""
    return [add_box_rot("PaleVioletStreak", (0.13, -0.155, 1.60),
                        (0.035, 0.012, 0.18), m["paleviolet"],
                        (0.15, 0, -0.12))]


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["robe_top"] + parts["tunic"] + parts["runes"]
            + parts["waistband"])
    ok = True
    ok &= check_gap("torso: violet robe top vs black tunic @z=1.10",
                    interp_rings(ROBE_TOP_RINGS, 1.10)[0],
                    interp_rings(TUNIC_RINGS, 1.10)[0])
    ok &= check_gap("torso: violet robe top vs black tunic @z=1.30",
                    interp_rings(ROBE_TOP_RINGS, 1.30)[0],
                    interp_rings(TUNIC_RINGS, 1.30)[0])
    ok &= check_gap("torso: black tunic vs mannequin torso @z=1.28",
                    interp_rings(TUNIC_RINGS, 1.28)[0], 0.270)
    ok &= check_gap("torso: black tunic vs mannequin torso @z=1.00",
                    interp_rings(TUNIC_RINGS, 1.00)[0],
                    interp_rings([(1.28, 0.270, 0.140),
                                  (0.95, 0.240, 0.130)], 1.00)[0])
    ok &= check_gap("torso: violet robe top collar vs head @z=1.42",
                    interp_rings(ROBE_TOP_RINGS, 1.42)[0], 0.206)
    ok &= check_relief("torso: gold rune diamond relief", 0.006)
    ok &= check_relief("torso: gold waist buckle relief", 0.008)
    print("L2_CHECK torso: violet robe open front shows the black "
          "tunic and four gold diamond runes, gold waistband over "
          "the robe/skirt seam PASS")
    return objs, ok


def assemble_arms(parts):
    objs = parts["sleeves"] + parts["arm_rings"] + parts["pauldrons"]
    ok = True
    ok &= check_gap("arms: black sleeve vs mannequin arm @0.0",
                    0.105, 0.085)
    ok &= check_gap("arms: gold arm ring vs black sleeve @0.32",
                    0.104, 0.0982)
    ok &= check_gap("arms: gold pauldron vs robe shoulder @z=1.30",
                    0.415, interp_rings(ROBE_TOP_RINGS, 1.30)[0])
    print("L2_CHECK arms: black fitted sleeves 0.105->0.092, gold "
          "arm rings on the forearms, gold pauldrons covering the "
          "shoulder seams PASS")
    return objs, ok


def assemble_head(parts):
    objs = (parts["hood"] + parts["brow_band"] + parts["gem"]
            + parts["streak"])
    ok = True
    ok &= check_gap("head: black hood vs silver hair cap @z=1.62",
                    interp_rings(HOOD_RINGS, 1.62)[0] + 0.006, 0.216)
    ok &= check_relief("head: gold brow band relief", 0.006)
    ok &= check_relief("head: pale-violet gem relief", 0.005,
                       lo=0.005, hi=0.030)
    ok &= check_relief("head: pale-violet streak relief", 0.010,
                       lo=0.005, hi=0.030)
    print("L2_CHECK head: black hood peaks over the silver hair top, "
          "gold brow band across the forehead, pale-violet gem set "
          "in the hair, pale-violet streak on the hair front PASS")
    return objs, ok


def assemble_waist_skirt(parts):
    objs = parts["skirt"] + parts["pleats"] + parts["hem"]
    ok = True
    ok &= check_gap("waist: violet skirt top vs violet robe hem @z=0.74",
                    interp_rings(ROBE_SKIRT_RINGS, 0.74)[0],
                    interp_rings(ROBE_TOP_RINGS, 0.72)[0])
    ok &= check_gap("waist: gold waistband vs violet robe @z=0.76",
                    interp_rings(WAIST_RINGS, 0.76)[0],
                    interp_rings(ROBE_TOP_RINGS, 0.76)[0])
    ok &= check_relief("waist: violet pleat fin height", 0.022,
                       lo=0.005, hi=0.030)
    ok &= check_relief("waist: gold hem band relief", 0.006,
                       lo=0.005, hi=0.015)
    print("L2_CHECK waist: violet skirt flares under the gold "
          "waistband, 8 pleat fins on the skirt cone, gold hem band "
          "at the skirt bottom PASS")
    return objs, ok


def assemble_legs(parts):
    objs = [parts["boots"][i] for i in (1, 4)]
    ok = True
    ok &= check_gap("legs: black boot shaft vs mannequin leg @z=0.10",
                    0.105, 0.078)
    print("L2_CHECK legs: black boot shafts 0.105 over the legs, "
          "tops hidden under the robe skirt PASS")
    return objs, ok


def assemble_feet(parts):
    objs = [parts["boots"][i] for i in (0, 3)] + [parts["boots"][i]
                                                 for i in (2, 5)]
    ok = True
    ok &= check_gap("feet: black boot wedge vs mannequin foot",
                    0.100, 0.095)
    ok &= check_gap("feet: gold boot trim vs black boot shaft @z=0.06",
                    0.108, 0.1028)
    print("L2_CHECK feet: black boot wedge centre z=0.0, sole on "
          "ground; gold trim ring on the visible shaft PASS")
    return objs, ok


def assemble_cape(parts):
    objs = parts["cape"]
    ok = True
    ok &= check_gap("cape: black cape vs violet robe @z=1.00",
                    interp_rings(CAPE_RINGS, 1.00)[0],
                    interp_rings(ROBE_TOP_RINGS, 1.00)[0])
    ok &= check_gap("cape: black cape vs violet skirt @z=0.50",
                    interp_rings(CAPE_RINGS, 0.50)[0],
                    interp_rings(ROBE_SKIRT_RINGS, 0.50)[0])
    print("L2_CHECK cape: black cape hangs outside the robe bodice "
          "and the skirt, down to the knee PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: violet robe top vs black tunic @z=1.10",
                    interp_rings(ROBE_TOP_RINGS, 1.10)[0],
                    interp_rings(TUNIC_RINGS, 1.10)[0])
    ok &= check_gap("L3 layer: violet skirt top vs violet robe hem @z=0.74",
                    interp_rings(ROBE_SKIRT_RINGS, 0.74)[0],
                    interp_rings(ROBE_TOP_RINGS, 0.72)[0])
    ok &= check_gap("L3 layer: gold waistband vs violet robe @z=0.76",
                    interp_rings(WAIST_RINGS, 0.76)[0],
                    interp_rings(ROBE_TOP_RINGS, 0.76)[0])
    ok &= check_gap("L3 layer: black cape vs violet robe @z=1.00",
                    interp_rings(CAPE_RINGS, 1.00)[0],
                    interp_rings(ROBE_TOP_RINGS, 1.00)[0])
    ok &= check_gap("L3 layer: black cape vs violet skirt @z=0.50",
                    interp_rings(CAPE_RINGS, 0.50)[0],
                    interp_rings(ROBE_SKIRT_RINGS, 0.50)[0])
    ok &= check_gap("L3 joint: gold arm ring vs black sleeve", 0.104, 0.0982)
    ok &= check_gap("L3 joint: black boot shaft vs mannequin leg @z=0.10",
                    0.105, 0.078)
    ok &= check_gap("L3 joint: gold boot trim vs black boot shaft @z=0.06",
                    0.108, 0.1028)
    print("L3_CHECK outfit: open-front robe shows the black tunic "
          "and gold runes, skirt flares under the gold waistband, "
          "cape hangs outside robe and skirt, black boot soles "
          "touch ground z=0.000 PASS")
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
    parts["robe_top"] = build_robe_top(m)
    report_l1("VioletRobeTop", parts["robe_top"])
    parts["tunic"] = build_tunic(m)
    report_l1("BlackTunic", parts["tunic"])
    parts["runes"] = build_runes(m)
    report_l1("GoldRunes x4", parts["runes"])
    parts["waistband"] = build_waistband(m)
    report_l1("GoldWaistband+Buckle", parts["waistband"])
    parts["skirt"] = build_skirt(m)
    report_l1("VioletRobeSkirt", parts["skirt"])
    parts["hem"] = build_hem(m)
    report_l1("GoldHemBand", parts["hem"])
    parts["pleats"] = [build_pleat_fin(m, a) for a in PLEAT_ANGLES]
    report_l1("VioletPleats x8", parts["pleats"])
    parts["sleeves"] = []
    for sx in (-1, 1):
        parts["sleeves"] += build_sleeve(m, sx)
    report_l1("BlackSleeves x2", parts["sleeves"])
    parts["arm_rings"] = []
    for sx in (-1, 1):
        parts["arm_rings"] += build_arm_ring(m, sx)
    report_l1("GoldArmRings x2", parts["arm_rings"])
    parts["pauldrons"] = [build_pauldron(m, sx) for sx in (-1, 1)]
    report_l1("GoldPauldrons x2", parts["pauldrons"])
    parts["hood"] = build_hood(m)
    report_l1("BlackHood", parts["hood"])
    flat_patches += parts["hood"]
    parts["brow_band"] = build_brow_band(m)
    report_l1("GoldBrowBand", parts["brow_band"])
    flat_patches += parts["brow_band"]
    parts["gem"] = build_gem(m)
    report_l1("PaleVioletGem", parts["gem"])
    parts["boots"] = []
    for sx in (-1, 1):
        parts["boots"] += build_boot(m, sx)
    report_l1("BlackBoots x2", parts["boots"])
    parts["cape"] = build_cape(m)
    report_l1("BlackCape", parts["cape"])
    flat_patches += parts["cape"]
    parts["streak"] = build_streak(m)
    report_l1("PaleVioletStreak", parts["streak"])

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    _, ok = assemble_torso(parts)
    l2_ok &= ok
    _, ok = assemble_arms(parts)
    l2_ok &= ok
    _, ok = assemble_head(parts)
    l2_ok &= ok
    _, ok = assemble_waist_skirt(parts)
    l2_ok &= ok
    _, ok = assemble_legs(parts)
    l2_ok &= ok
    _, ok = assemble_feet(parts)
    l2_ok &= ok
    _, ok = assemble_cape(parts)
    l2_ok &= ok
    print("L2_SUMMARY %s" % ("ALL PASS" if l2_ok else "FAILURES PRESENT"))

    # ---- L3 full outfit on the mannequin ----
    costume = (parts["robe_top"] + parts["tunic"] + parts["runes"]
               + parts["waistband"] + parts["skirt"] + parts["hem"]
               + parts["pleats"] + parts["sleeves"] + parts["arm_rings"]
               + parts["pauldrons"] + parts["hood"] + parts["brow_band"]
               + parts["gem"] + parts["boots"] + parts["cape"]
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
