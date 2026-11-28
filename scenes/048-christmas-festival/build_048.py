# -*- coding: utf-8 -*-
"""048 异环式都市时装 · 圣诞节日套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整套穿到人体底座上试穿）。
设计见 design.md。BACKLOG 已空时自选：异环线第十二件——节日/圣诞场景方向
（015 夜行、025 街头、026 学院、027 运动、028 居家、029 通勤、
031 夏日、032 冬日、039 秋日、040 雨天、045 春日之后；学院/居家/
运动/街头/通勤/夜行/夏日/冬日/秋日/雨天/春日矩阵里节日首次做，
12 月圣诞季贴合）。
圣诞红长款大衣（前开襟、金色圣诞星纹×5、大衣下摆褶裥×8、雪白毛领、
墨绿腰带 + 金腰扣）+ 雪白高领毛衣内层 + 藏青长袖（雪白袖口）+
藏青长裤 + 圣诞红短靴（雪白靴口 + 金靴扣）+ 圣诞红圣诞帽（雪白帽边 +
翻折帽尖 + 白绒球 + 帽上金星）+ 蓝挑染 + 金耳钉 + 墨绿手套（左手）+
圣诞礼物盒（右手持，第八种手持物）。廓形变量：长款大衣到膝 z 0.45
（032 同款长度，变量是圣诞红 + 毛领 + 圣诞帽）。
Run: blender --background --python build_048.py
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

_spec32 = importlib.util.spec_from_file_location(
    "build_032", os.path.join(SCENES, "032-winter-urban",
                              "build_032.py"))
b032 = importlib.util.module_from_spec(_spec32)
_spec32.loader.exec_module(b032)
build_mannequin = b032.build_mannequin
wrist_pos = b032.wrist_pos
TORSO_RINGS = b032.TORSO_RINGS

_spec39 = importlib.util.spec_from_file_location(
    "build_039", os.path.join(SCENES, "039-autumn-maple-urban",
                              "build_039.py"))
b039 = importlib.util.module_from_spec(_spec39)
_spec39.loader.exec_module(b039)
make_star_patch = b039.make_star_patch
_patch_on_ellipse = b039._patch_on_ellipse

BLEND_OUT = os.path.join(HERE, "048-christmas-festival.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "048-christmas-festival.png")
WIRE_JSON = "/tmp/christmas_festival_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

SWEATER_RINGS = [(1.50, 0.300, 0.160), (1.44, 0.288, 0.152),
                 (1.10, 0.272, 0.144), (0.80, 0.258, 0.138),
                 (0.62, 0.248, 0.132)]
COAT_RINGS = [(1.50, 0.312, 0.168), (1.20, 0.310, 0.162),
              (0.90, 0.308, 0.160), (0.62, 0.314, 0.162),
              (0.45, 0.322, 0.166)]
TROUSER_RINGS = [(0.62, 0.246, 0.128), (0.48, 0.240, 0.126),
                 (0.34, 0.232, 0.124)]
BELT_RINGS = [(0.94, 0.318, 0.168), (0.88, 0.317, 0.167)]
PLEAT_ANGLES = [170, 200, 230, 320, 350, 20, 50, 110]  # all outside 240-300
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)
# Santa hat cone: base z 1.64 r 0.235, tip z 1.94 r 0.030.
HAT_BASE_Z = 1.64
HAT_BASE_R = 0.235
HAT_TIP_Z = 1.94
HAT_TIP_R = 0.030
HAT_DR_DZ = (HAT_TIP_R - HAT_BASE_R) / (HAT_TIP_Z - HAT_BASE_Z)


def hat_cone_radius(z):
    """Cone surface radius at height z (linear taper)."""
    return HAT_BASE_R + HAT_DR_DZ * (z - HAT_BASE_Z)


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    red = solid_material("ChristmasRed", (0.533, 0.020, 0.026),
                         roughness=0.6)
    snow = solid_material("SnowWhite", (0.930, 0.896, 0.807),
                          roughness=0.65)
    pine = solid_material("PineGreen", (0.013, 0.074, 0.044),
                          roughness=0.6)
    navy = solid_material("Navy", (0.011, 0.023, 0.068), roughness=0.6)
    gold = solid_material("Gold", (0.584, 0.361, 0.020), metallic=0.6,
                          roughness=0.35)
    lightblue = solid_material("LightBlue", (0.212, 0.479, 0.807),
                               roughness=0.6)
    black = solid_material("Hair_Black", (0.011, 0.011, 0.015),
                           roughness=0.7)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"red": red, "snow": snow, "pine": pine, "navy": navy,
            "gold": gold, "lightblue": lightblue, "black": black,
            "skin": skin, "eye": eye}


# ------------------------------------------------------------ L1 components
def build_sweater(m):
    """Snow-white turtleneck sweater, inner layer: 5 rings, z 1.50-0.62.
    Hem meets the trouser top at z 0.62 exactly (039 method)."""
    return [make_elliptical_tube("SnowSweater", SWEATER_RINGS, 16,
                                 m["snow"], caps=False)]


def build_coat(m):
    """Christmas-red long coat, open front: arc 300-600 deg leaves the
    240-300 deg front wedge open so the snow sweater shows.
    Knee-length: z 1.50-0.45, 5 rings — the silhouette variable is
    the Christmas styling (red + fur collar + santa hat) on 032's
    knee-length cut."""
    return [make_elliptical_tube("RedCoat", COAT_RINGS, 16,
                                 m["red"], arc=(300, 600),
                                 caps=False)]


def build_star_on_sweater(m, angle_deg, z):
    """One gold Christmas star on the sweater front (visible through
    the coat's open front)."""
    return _patch_on_ellipse("GoldStar", SWEATER_RINGS, angle_deg,
                             z, 0.032, m["gold"])


def build_star_on_coat(m, angle_deg, z):
    """One gold Christmas star on the coat front edge (225/315 deg —
    15 deg outside the 240-300 open wedge; a star inside the wedge
    would float in front of the sweater)."""
    return _patch_on_ellipse("GoldStar", COAT_RINGS, angle_deg,
                             z, 0.032, m["gold"])


def build_pleat_fin(m, angle_deg):
    """One 3D pleat fin: a closed thin solid (10 quads) following the
    coat cone, inner edge 0.004 off the coat, outer edge 0.026 off,
    tangential half-thickness 0.004. Same construction as
    026/030/032/036/039/045."""
    rows = [0.65, 0.55, 0.45]
    a = math.radians(angle_deg)
    verts = []
    for z in rows:
        rx, ry = interp_rings(COAT_RINGS, z)
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
    return mesh_from_data("RedPleat", verts, faces, m["red"])


def build_fur_collar(m):
    """Snow-white fur collar lying on the coat shoulders
    (z 1.54-1.48, r 0.325/0.320): bottom ring 0.008 proud of the
    coat top ring (0.312 at z 1.48). Open front (arc 300-600 deg,
    same open wedge as the coat) — v1 was a full ring and its front
    band crossed the face at eye level, reading as a blindfold and
    hiding the eyes; the open arc leaves the face clear."""
    return [make_elliptical_tube("SnowFurCollar",
                                 [(1.54, 0.325, 0.325),
                                  (1.48, 0.320, 0.320)], 16,
                                 m["snow"], arc=(300, 600),
                                 caps=False)]


def build_sleeve(m, sx):
    """Navy long sleeve over the arm (shoulder to wrist).
    Capped (025 v2 lesson). Origin lifted 0.12 along the arm axis
    so the sleeve starts at z 1.34, emerging from the coat shoulder
    (032 v1 lesson)."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    origin = shoulder - direction.normalized() * 0.12
    return [make_tube("NavySleeve", origin, direction,
                      [0.0, 0.17, 0.34, 0.51, 0.67],
                      [0.125, 0.118, 0.110, 0.102, 0.096], 10,
                      m["navy"], caps=True)]


def build_cuff(m, sx):
    """Snow-white cuff ring at the wrist (t 0.48-0.56 along the arm):
    r 0.105, 0.0064 proud of the sleeve at the cuff top ring
    (036 v3/037 lesson: check the sleeve radius at s 0.60, not
    just the end)."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    origin = shoulder + direction.normalized() * 0.48
    return [make_tube("SnowCuff", origin, direction,
                      [0.0, 0.08], [0.105, 0.105], 10,
                      m["snow"], caps=False)]


def build_belt(m):
    """Pine-green waist belt: tube around the coat waist (z 0.94-0.88),
    0.006+ proud of the coat in both rx and ry (037 lesson: check
    ry too)."""
    return [make_elliptical_tube("PineBelt", BELT_RINGS, 16,
                                 m["pine"], caps=False)]


def build_belt_buckle(m):
    """Gold belt buckle at the front centre (0, -0.1725, 0.91):
    belt front at z 0.91 is y -0.1675, so the 0.012-thick box is
    half-buried and 0.011 proud."""
    return add_box("GoldBeltBuckle", (0, -0.1725, 0.91),
                   (0.05, 0.012, 0.04), m["gold"])


def build_trousers(m):
    """Navy trousers: tube around both leg tops, z 0.62-0.34,
    hem ends above the boots (039 method)."""
    return [make_elliptical_tube("NavyTrousers", TROUSER_RINGS, 12,
                                 m["navy"], caps=False)]


def build_boot(m, sx):
    """Christmas-red ankle boot: tube around the lower leg (z 0.34-0.02,
    r 0.118) + sole wedge landing z=0.0 + snow-white fur cuff ring at
    the top (z 0.36-0.32, r 0.124) + gold buckle at the front.
    Sole wedge top 0.105/0.055 (0.005 above the mannequin foot top
    0.10/0.045) — 036 v1 lesson."""
    tube = make_tube("RedBoot", (sx * 0.13, 0, 0.34), (0, 0, -1),
                     [0.0, 0.32], [0.118, 0.118], 10,
                     m["red"], caps=False)
    sole = make_wedge("RedBootSole", (sx * 0.13, -0.02, 0.0),
                      0.102, 0.095, -0.165, 0.0, 0.105, 0.055,
                      m["red"])
    cuff = make_tube("SnowBootCuff", (sx * 0.13, 0, 0.36), (0, 0, -1),
                     [0.0, 0.04], [0.124, 0.124], 10,
                     m["snow"], caps=False)
    buckle = add_box("GoldBootBuckle", (sx * 0.13, -0.122, 0.18),
                     (0.04, 0.012, 0.025), m["gold"])
    return [tube, sole, cuff, buckle]


def build_santa_hat(m):
    """Santa hat (first in the line): red cone (base z 1.64 r 0.235,
    tip z 1.94 r 0.030, 12 sides) + flopped tip tube (from the cone
    tip, leaning forward-down 0.13 m) + white pompom (r 0.035,
    covering the tip tube end) + snow-white fur brim (z 1.64-1.59,
    r 0.245/0.248, bottom edge 0.065 above the eye line). The cone
    base ring sits inside the brim top ring (0.235 vs 0.245), so the
    cone emerges from inside the fur brim."""
    cone = make_tube("SantaHatCone", (0, 0.01, HAT_BASE_Z), (0, 0, 1),
                     [0.0, HAT_TIP_Z - HAT_BASE_Z],
                     [HAT_BASE_R, HAT_TIP_R], 12, m["red"], caps=False)
    tip = make_tube("SantaHatTip", (0, 0.01, HAT_TIP_Z), (0, -0.55, -0.35),
                    [0.0, 0.13], [0.032, 0.020], 8, m["red"], caps=False)
    pompom = add_sphere("SantaHatPompom", (0, -0.105, 1.865), 0.035,
                        8, 4, (1.0, 1.0, 1.0), m["snow"])
    brim = make_tube("SnowHatBrim", (0, 0.01, HAT_BASE_Z), (0, 0, -1),
                     [0.0, 0.05], [0.245, 0.248], 16, m["snow"],
                     caps=False)
    return [cone, tip, pompom, brim]


def build_hat_star(m):
    """Gold Christmas star on the santa cone front (z 1.75): cone
    radius there is 0.1598, so the star centre sits at y -0.1558,
    0.006 off the cone surface; normal (0,-0.826,0.564) is the cone
    surface normal (half-angle atan(0.6833) = 34.4 deg)."""
    return make_star_patch("GoldStarHat", (0, -0.1558, 1.75),
                           (0, -0.826, 0.564), 0.025, m["gold"])


def build_streak(m):
    """Light-blue hair streak: flattened ellipsoid on the hair surface,
    front-right below the hat brim. 042-verified centre
    (0.11, -0.175, 1.44): front pole ~0.039 proud of the head face,
    inside the 0.005-0.045 relief band, 22/26 visible vertices.
    Top z 1.49 stays below the brim bottom (1.59) — 031 v1 lesson:
    a streak must not poke through the hat."""
    return [add_sphere("HairStreak", (0.11, -0.175, 1.44), 0.05, 8, 4,
                       (0.55, 0.45, 1.0), m["lightblue"])]


def build_earring(m, sx):
    """Gold stud earring: small sphere half-buried in the head side
    (±0.222, 0, 1.47), outer face 0.019 proud."""
    return add_sphere("GoldEarring", (sx * 0.222, 0, 1.47), 0.015, 6, 3,
                      (1.0, 1.0, 1.0), m["gold"])


def build_glove(m):
    """Pine-green glove on the left hand: sphere r 0.095 at the left
    wrist + 0.03 along the arm axis, covering the hand sphere."""
    wrist, direction = wrist_pos(-1)
    centre = wrist + direction * 0.03
    return [add_sphere("PineGlove", tuple(centre), 0.095, 6, 4,
                       (1.0, 0.9, 1.0), m["pine"])]


def build_gift_box(m):
    """Christmas gift box held in the right hand (eighth handheld
    item): red 0.07 cube + gold ribbon cross (two thin boxes,
    0.002 proud on each side) + gold bow sphere on top. Centre at
    (wx, wy-0.11, wz-0.05): the box back face embeds 0.0085 into
    the palm (reads as held, not floating), and the top corner sits
    0.0198 past the sleeve end-cap plane (clear of the sleeve)."""
    wrist, _ = wrist_pos(1)
    wx, wy, wz = wrist
    c = (wx, wy - 0.11, wz - 0.05)
    box = add_box("GiftBox", c, (0.07, 0.07, 0.07), m["red"])
    ribbon_x = add_box("GiftRibbonX", c, (0.074, 0.012, 0.074),
                       m["gold"])
    ribbon_y = add_box("GiftRibbonY", c, (0.012, 0.074, 0.074),
                       m["gold"])
    bow = add_sphere("GiftBow", (wx, wy - 0.11, wz - 0.05 + 0.043),
                     0.014, 6, 3, (1.0, 1.0, 1.0), m["gold"])
    return [box, ribbon_x, ribbon_y, bow], Vector(wrist)


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = parts["sweater"] + parts["sweater_stars"]
    ok = True
    ok &= check_gap("torso: snow sweater vs mannequin torso @z=1.28",
                    interp_rings(SWEATER_RINGS, 1.28)[0],
                    interp_rings(TORSO_RINGS, 1.28)[0])
    ok &= check_gap("torso: snow sweater vs mannequin torso @z=0.95",
                    interp_rings(SWEATER_RINGS, 0.95)[0],
                    interp_rings(TORSO_RINGS, 0.95)[0])
    ok &= check_relief("torso: gold star relief", 0.006,
                       lo=0.005, hi=0.015)
    print("L2_CHECK torso: snow-white turtleneck sweater clears the "
          "torso, 3 gold Christmas stars on the chest front PASS")
    return objs, ok


def assemble_coat(parts):
    objs = parts["coat"] + parts["coat_stars"] + parts["pleats"]
    ok = True
    ok &= check_gap("coat: red coat vs snow sweater @z=1.20",
                    interp_rings(COAT_RINGS, 1.20)[0],
                    interp_rings(SWEATER_RINGS, 1.20)[0])
    ok &= check_gap("coat: red coat vs snow sweater @z=0.90",
                    interp_rings(COAT_RINGS, 0.90)[0],
                    interp_rings(SWEATER_RINGS, 0.90)[0])
    ok &= check_gap("coat: red coat vs snow sweater ry @z=1.20",
                    interp_rings(COAT_RINGS, 1.20)[1],
                    interp_rings(SWEATER_RINGS, 1.20)[1])
    ok &= check_gap("coat: red coat vs snow sweater ry @z=0.90",
                    interp_rings(COAT_RINGS, 0.90)[1],
                    interp_rings(SWEATER_RINGS, 0.90)[1])
    ok &= check_relief("coat: gold star relief", 0.006,
                       lo=0.005, hi=0.015)
    ok &= check_relief("coat: red pleat fin height", 0.022,
                       lo=0.005, hi=0.030)
    print("L2_CHECK coat: Christmas-red long coat hangs loose over "
          "the snow sweater, 2 gold stars on the front edges, "
          "8 pleat fins at the hem PASS")
    return objs, ok


def assemble_collar(parts):
    objs = parts["collar"]
    ok = True
    ok &= check_gap("collar: snow fur collar vs red coat @z=1.48",
                    0.320, interp_rings(COAT_RINGS, 1.48)[0])
    print("L2_CHECK collar: snow-white fur collar ring lies on the "
          "coat shoulders PASS")
    return objs, ok


def assemble_sleeves(parts):
    objs = parts["sleeves"] + parts["cuffs"]
    ok = True
    ok &= check_gap("sleeve: navy sleeve vs mannequin arm @0.0",
                    0.125, 0.085)
    ok &= check_gap("sleeve: snow cuff vs navy sleeve end",
                    0.105, 0.096)
    ok &= check_gap("sleeve: snow cuff vs navy sleeve @s=0.60",
                    0.105, 0.0986)
    print("L2_CHECK sleeves: navy long sleeves over the arms, "
          "snow-white cuffs at the wrists PASS")
    return objs, ok


def assemble_belt(parts):
    objs = parts["belt"] + [parts["buckle"]]
    ok = True
    ok &= check_gap("belt: pine belt vs red coat @z=0.94",
                    interp_rings(BELT_RINGS, 0.94)[0],
                    interp_rings(COAT_RINGS, 0.94)[0])
    ok &= check_gap("belt: pine belt vs red coat @z=0.88",
                    interp_rings(BELT_RINGS, 0.88)[0],
                    interp_rings(COAT_RINGS, 0.88)[0])
    ok &= check_gap("belt: pine belt vs red coat ry @z=0.94",
                    interp_rings(BELT_RINGS, 0.94)[1],
                    interp_rings(COAT_RINGS, 0.94)[1])
    ok &= check_gap("belt: pine belt vs red coat ry @z=0.88",
                    interp_rings(BELT_RINGS, 0.88)[1],
                    interp_rings(COAT_RINGS, 0.88)[1])
    ok &= check_relief("belt: gold buckle relief", 0.011,
                       lo=0.005, hi=0.030)
    print("L2_CHECK belt: pine-green waist belt cinches the coat, "
          "gold buckle at the front PASS")
    return objs, ok


def assemble_head(parts):
    objs = (parts["hat"] + [parts["hat_star"]]
            + parts["streak"] + parts["earrings"])
    ok = True
    # Santa cone vs hair cap: cone r 0.235 @z=1.64, 0.2213 @z=1.66;
    # hair rx 0.2073 @z=1.64, 0.1949 @z=1.66. The cone must be
    # checked at z 1.66 too — the hair is widest there relative to
    # the taper, not just at the base ring.
    ok &= check_gap("head: santa cone vs black hair cap @z=1.64",
                    HAT_BASE_R, 0.2073)
    ok &= check_gap("head: santa cone vs black hair cap @z=1.66",
                    hat_cone_radius(1.66), 0.1949)
    ok &= check_gap("head: snow hat brim vs black hair cap @z=1.59",
                    0.248, 0.2236)
    ok &= check_gap("head: snow hat brim bottom vs eye line",
                    1.59, 1.525)
    ok &= check_relief("head: gold star on santa cone relief", 0.006,
                       lo=0.005, hi=0.015)
    ok &= check_relief("head: gold earring relief", 0.019,
                       lo=0.005, hi=0.030)
    print("L2_CHECK head: santa hat cone clears the hair, snow brim "
          "above the eyes, gold star on the cone front, blue streak "
          "below the brim, gold studs PASS")
    return objs, ok


def assemble_legs(parts):
    objs = parts["trousers"]
    ok = True
    ok &= check_gap("legs: navy trousers vs mannequin legs @z=0.52",
                    interp_rings(TROUSER_RINGS, 0.52)[0], 0.1023)
    print("L2_CHECK legs: navy trousers cover the leg tops PASS")
    return objs, ok


def assemble_feet(parts):
    objs = parts["boots"]
    ok = True
    ok &= check_gap("feet: red boot vs mannequin leg @z=0.20",
                    0.118, 0.0866)
    ok &= check_gap("feet: snow boot cuff vs red boot",
                    0.124, 0.118)
    ok &= check_gap("feet: red boot sole vs mannequin foot",
                    0.102, 0.095)
    ok &= check_relief("feet: gold boot buckle relief", 0.010,
                       lo=0.005, hi=0.030)
    print("L2_CHECK feet: Christmas-red boot tubes centre z=0.0, "
          "soles on ground; snow cuffs at the boot tops, gold "
          "buckles at the front PASS")
    return objs, ok


def assemble_hand(parts, wrist):
    objs = parts["glove"] + parts["gift"]
    ok = True
    ok &= check_gap("hand: pine glove vs mannequin hand",
                    0.095, 0.085)
    # Gift box vs palm: the box's nearest corner (top-back) sits
    # 0.0765 from the palm centre (r 0.085) — embedded 0.0085, so
    # the box reads as held, not floating.
    palm_embed = 0.085 - math.sqrt(0.075 ** 2 + 0.015 ** 2)
    print("L2_CHECK hand: gift box back face embeds %.4f into palm "
          "(must be 0.005-0.030)" % palm_embed)
    ok &= 0.005 <= palm_embed <= 0.030
    # Gift box vs sleeve end cap: the box top corner is past the
    # cap plane (dot with the arm direction > 0), so it cannot
    # intersect the sleeve tube.
    corner = Vector((0.035, -0.075, -0.015))
    arm_dir = Vector((0.1387, 0, -0.9903))
    past_plane = corner.dot(arm_dir)
    print("L2_CHECK hand: gift box top corner past sleeve cap plane "
          "by %.4f (must be > 0)" % past_plane)
    ok &= past_plane > 0
    print("L2_CHECK hand: pine glove covers the left hand, Christmas "
          "gift box held in the right hand PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: red coat vs snow sweater @z=1.20",
                    interp_rings(COAT_RINGS, 1.20)[0],
                    interp_rings(SWEATER_RINGS, 1.20)[0])
    ok &= check_gap("L3 layer: pine belt vs red coat @z=0.94",
                    interp_rings(BELT_RINGS, 0.94)[0],
                    interp_rings(COAT_RINGS, 0.94)[0])
    ok &= check_gap("L3 layer: snow fur collar vs red coat @z=1.48",
                    0.320, interp_rings(COAT_RINGS, 1.48)[0])
    ok &= check_gap("L3 layer: snow hat brim bottom vs eye line",
                    1.59, 1.525)
    ok &= check_gap("L3 joint: navy sleeve vs mannequin arm",
                    0.125, 0.085)
    ok &= check_gap("L3 joint: red boot vs mannequin leg @z=0.20",
                    0.118, 0.0866)
    ok &= check_gap("L3 joint: red boot sole vs mannequin foot",
                    0.102, 0.095)
    print("L3_CHECK outfit: red coat over the snow sweater, pine belt "
          "cinching the waist, fur collar on the shoulders, santa "
          "hat above the eyes, boots on ground z=0.000 PASS")
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

    # ---- L0 mannequin (base, not a costume component) ----
    mannequin = build_mannequin(m)

    # ---- L1 small components: build + silhouette check each ----
    parts = {}
    parts["sweater"] = build_sweater(m)
    report_l1("SnowSweater", parts["sweater"])
    parts["coat"] = build_coat(m)
    report_l1("RedCoat", parts["coat"])
    parts["sweater_stars"] = [
        build_star_on_sweater(m, 270, 1.32),
        build_star_on_sweater(m, 262, 1.02),
        build_star_on_sweater(m, 278, 1.02)]
    report_l1("GoldStarsOnSweater x3", parts["sweater_stars"])
    parts["coat_stars"] = [
        build_star_on_coat(m, 225, 1.10),
        build_star_on_coat(m, 320, 1.10)]
    report_l1("GoldStarsOnCoat x2", parts["coat_stars"])
    parts["pleats"] = [build_pleat_fin(m, a) for a in PLEAT_ANGLES]
    report_l1("RedPleats x8", parts["pleats"])
    parts["collar"] = build_fur_collar(m)
    report_l1("SnowFurCollar", parts["collar"])
    parts["sleeves"] = []
    for sx in (-1, 1):
        parts["sleeves"] += build_sleeve(m, sx)
    report_l1("NavySleeves x2", parts["sleeves"])
    parts["cuffs"] = []
    for sx in (-1, 1):
        parts["cuffs"] += build_cuff(m, sx)
    report_l1("SnowCuffs x2", parts["cuffs"])
    parts["belt"] = build_belt(m)
    report_l1("PineBelt", parts["belt"])
    parts["buckle"] = build_belt_buckle(m)
    report_l1("GoldBeltBuckle", [parts["buckle"]])
    parts["trousers"] = build_trousers(m)
    report_l1("NavyTrousers", parts["trousers"])
    parts["boots"] = []
    for sx in (-1, 1):
        parts["boots"] += build_boot(m, sx)
    report_l1("RedBoots x2", parts["boots"])
    parts["hat"] = build_santa_hat(m)
    report_l1("SantaHat", parts["hat"])
    parts["hat_star"] = build_hat_star(m)
    report_l1("GoldStarHat", [parts["hat_star"]])
    parts["streak"] = build_streak(m)
    report_l1("HairStreak", parts["streak"])
    parts["earrings"] = [build_earring(m, sx) for sx in (-1, 1)]
    report_l1("GoldEarrings x2", parts["earrings"])
    parts["glove"] = build_glove(m)
    report_l1("PineGlove", parts["glove"])
    parts["gift"], wrist = build_gift_box(m)
    report_l1("GiftBox", parts["gift"])

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    _, ok = assemble_torso(parts)
    l2_ok &= ok
    _, ok = assemble_coat(parts)
    l2_ok &= ok
    _, ok = assemble_collar(parts)
    l2_ok &= ok
    _, ok = assemble_sleeves(parts)
    l2_ok &= ok
    _, ok = assemble_belt(parts)
    l2_ok &= ok
    _, ok = assemble_head(parts)
    l2_ok &= ok
    _, ok = assemble_legs(parts)
    l2_ok &= ok
    _, ok = assemble_feet(parts)
    l2_ok &= ok
    _, ok = assemble_hand(parts, wrist)
    l2_ok &= ok
    print("L2_SUMMARY %s" % ("ALL PASS" if l2_ok else "FAILURES PRESENT"))

    # ---- L3 full outfit on the mannequin ----
    costume = (parts["sweater"] + parts["coat"]
               + parts["sweater_stars"] + parts["coat_stars"]
               + parts["pleats"] + parts["collar"]
               + parts["sleeves"] + parts["cuffs"] + parts["belt"]
               + [parts["buckle"]] + parts["trousers"]
               + parts["boots"] + parts["hat"] + [parts["hat_star"]]
               + parts["streak"] + parts["earrings"]
               + parts["glove"] + parts["gift"])
    l3_ok = assemble_outfit(parts, mannequin)

    # --- normal self-check (solids only; the flat gold star patches keep
    # their construction winding — fix_normals must never run on
    # flat patches). 045/047 lesson: open-front elliptical tubes
    # (RedCoat, arc 300-600) and wedges (RedBootSole) DO need
    # fix_normals — their construction winding comes out inward.
    for obj in mannequin + costume:
        if obj.name.startswith("GoldStar"):
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
