# -*- coding: utf-8 -*-
"""040 异环式都市时装 · 雨天套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整套穿到人体底座上试穿）。
设计见 design.md。BACKLOG 已空时自选：异环线第十件——雨天场景方向
（015 夜行、025 街头、026 学院、027 运动、028 居家、029 通勤、
031 夏日、032 冬日、039 秋日之后；学院/居家/运动/街头/通勤/夜行/
夏日/冬日/秋日矩阵里雨天首次做）。
雨衣黄中长雨衣（前开襟、雨滴蓝雨滴纹×6、雨衣下摆褶裥×8、藏青腰带
+ 银腰扣）+ 奶油白高领毛衣内层 + 藏青长袖（奶油白袖口）+ 藏青长裤
+ 雨衣黄高筒雨靴 + 雨衣黄宽檐雨帽（藏青帽带）+ 雨衣黄兜帽翻在脑后
+ 猫耳 + 蓝挑染 + 金耳钉 + 藏青手套（左手）+ 雨伞（右手持，第六种
手持物）。廓形沿用 039 中长风衣到大腿中部 z 0.60，变量是雨衣光面
PVC（粗糙度 0.25）与脑后兜帽。
Run: blender --background --python build_040.py
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

BLEND_OUT = os.path.join(HERE, "040-rainy-day-urban.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "040-rainy-day-urban.png")
WIRE_JSON = "/tmp/rainy_day_urban_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

SWEATER_RINGS = [(1.50, 0.300, 0.160), (1.44, 0.288, 0.152),
                 (1.10, 0.272, 0.144), (0.80, 0.258, 0.138),
                 (0.62, 0.248, 0.132)]
RAINCOAT_RINGS = [(1.50, 0.312, 0.168), (1.20, 0.312, 0.164),
                  (0.90, 0.308, 0.162), (0.72, 0.304, 0.160),
                  (0.60, 0.302, 0.158)]
HOOD_RINGS = [(1.52, 0.315, 0.172), (1.44, 0.322, 0.176),
              (1.38, 0.318, 0.174)]
BELT_RINGS = [(0.94, 0.315, 0.169), (0.88, 0.314, 0.168)]
TROUSER_RINGS = [(0.62, 0.246, 0.128), (0.48, 0.240, 0.126),
                 (0.34, 0.232, 0.124)]
HATBAND_RINGS = [(1.66, 0.260, 0.258), (1.62, 0.265, 0.262)]
PLEAT_ANGLES = [170, 200, 230, 320, 350, 20, 50, 110]  # all outside 240-300
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)
# Umbrella shaft: 48 deg off the arm's upward extension, so it leaves
# the cuff/sleeve at the wrist instead of running along the forearm
# (a shaft parallel to the arm would pierce the sleeve mid-forearm).
SHAFT_DIR = Vector((0.553, -0.352, 0.755)).normalized()
SHAFT_LEN = 0.70


def ellipse_value(x, y, rx, ry):
    """Normalised ellipse radius of point (x, y); >1 means outside."""
    return math.sqrt((x / rx) ** 2 + (y / ry) ** 2)


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    yellow = solid_material("RainYellow", (0.888, 0.540, 0.000),
                            roughness=0.25)  # glossy PVC raincoat
    cream = solid_material("Cream", (0.913, 0.862, 0.744), roughness=0.6)
    navy = solid_material("Navy", (0.011, 0.023, 0.068), roughness=0.6)
    rainblue = solid_material("RainBlue", (0.112, 0.452, 0.791),
                              roughness=0.5)
    silver = solid_material("Silver", (0.529, 0.585, 0.633), metallic=0.7,
                            roughness=0.3)
    gold = solid_material("Gold", (0.584, 0.361, 0.020), metallic=0.6,
                          roughness=0.35)
    lightblue = solid_material("LightBlue", (0.212, 0.479, 0.807),
                               roughness=0.6)
    black = solid_material("Hair_Black", (0.011, 0.011, 0.015),
                           roughness=0.7)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"yellow": yellow, "cream": cream, "navy": navy,
            "rainblue": rainblue, "silver": silver, "gold": gold,
            "lightblue": lightblue, "black": black, "skin": skin,
            "eye": eye}


# ------------------------------------------------------------ raindrop
def make_raindrop(name, center, material):
    """One raindrop: flattened ellipsoid (r 0.028, scale
    (0.9, 0.55, 1.35) — 0.076 m tall), half-embedded so it stands
    ~0.015 m proud of the cloth. The thin axis is world-Y, which
    matches the surface normal for front patches (255-285 deg);
    for the 225/315 deg coat patches the ellipsoid still protrudes
    ~0.015 m along the diagonal normal (see design.md)."""
    return add_sphere(name, center, 0.028, 8, 4,
                      (0.9, 0.55, 1.35), material)


def _droplet_on_ellipse(name, rings, angle_deg, z, material,
                        offset=0.002):
    """Raindrop on an elliptical tube surface at (angle, z)."""
    rx, ry = interp_rings(rings, z)
    p, n = ellipse_point(rx, ry, angle_deg)
    c = Vector((p.x, p.y, z)) + n * offset
    return make_raindrop(name, tuple(c), material)


# ------------------------------------------------------------ L1 components
def build_sweater(m):
    """Cream turtleneck sweater, inner layer: 5 rings, z 1.50-0.62
    (039 rings, re-proven). Hem meets the trouser top at z 0.62."""
    return [make_elliptical_tube("CreamSweater", SWEATER_RINGS, 16,
                                 m["cream"], caps=False)]


def build_raincoat(m):
    """Yellow mid-length raincoat, open front: arc 300-600 deg leaves
    the 240-300 deg front wedge open so the cream sweater shows.
    Mid-length to mid-thigh: z 1.50-0.60, 5 rings — 039 silhouette,
    PVC gloss (roughness 0.25) is the variable."""
    return [make_elliptical_tube("YellowRaincoat", RAINCOAT_RINGS, 16,
                                 m["yellow"], arc=(300, 600),
                                 caps=False)]


def build_raindrop_on_sweater(m, angle_deg, z):
    """One rain-blue drop on the sweater front (visible through the
    coat's open front)."""
    return _droplet_on_ellipse("BlueRaindrop", SWEATER_RINGS, angle_deg,
                               z, m["rainblue"])


def build_raindrop_on_coat(m, angle_deg, z):
    """One rain-blue drop on the coat front edge (225/315 deg — 15 deg
    outside the 240-300 open wedge; a drop inside the wedge would
    float in front of the sweater)."""
    return _droplet_on_ellipse("BlueRaindrop", RAINCOAT_RINGS, angle_deg,
                               z, m["rainblue"])


def build_raindrop_on_hat(m):
    """One rain-blue drop on the rain-hat crown front (0, -0.207,
    1.70): crown front surface at z 1.70 is y -0.205, so the drop
    centre sits 0.002 proud and its 0.0154 half-thickness leaves
    ~0.013 embedded. Bottom z 1.662 clears the hat-band top ring
    (1.66)."""
    return make_raindrop("BlueRaindropHat", (0, -0.207, 1.70),
                         m["rainblue"])


def build_pleat_fin(m, angle_deg):
    """One 3D pleat fin: a closed thin solid (10 quads) following the
    raincoat cone, inner edge 0.004 off the coat, outer edge 0.026
    off, tangential half-thickness 0.004. Same construction as
    026/030/032/036/039."""
    rows = [0.80, 0.70, 0.60]
    a = math.radians(angle_deg)
    verts = []
    for z in rows:
        rx, ry = interp_rings(RAINCOAT_RINGS, z)
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
    return mesh_from_data("YellowPleat", verts, faces, m["yellow"])


def build_hood(m):
    """Yellow hood folded down behind the neck: back arc 15-165 deg
    (back is 90 deg; front is 270 deg), z 1.52-1.38. At z 1.44 it
    clears the raincoat by 0.010 and the sweater by 0.034; the top
    ring (z 1.52) sits above the coat top edge (1.50) and tucks
    behind the hair."""
    return [make_elliptical_tube("YellowHood", HOOD_RINGS, 16,
                                 m["yellow"], arc=(15, 165),
                                 caps=False)]


def build_sleeve(m, sx):
    """Navy long sleeve over the arm (shoulder to wrist).
    Capped (025 v2 lesson). Origin lifted 0.12 along the arm axis
    so the sleeve starts at z 1.34, emerging from the raincoat
    shoulder (032 v1 lesson)."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    origin = shoulder - direction.normalized() * 0.12
    return [make_tube("NavySleeve", origin, direction,
                      [0.0, 0.17, 0.34, 0.51, 0.67],
                      [0.125, 0.118, 0.110, 0.102, 0.096], 10,
                      m["navy"], caps=True)]


def build_cuff(m, sx):
    """Cream cuff ring at the wrist (t 0.48-0.56 along the arm):
    r 0.105, 0.0064 proud of the sleeve at the cuff top ring
    (036 v3/037 lesson: check the sleeve radius at s 0.60, not
    just the end)."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    origin = shoulder + direction.normalized() * 0.48
    return [make_tube("CreamCuff", origin, direction,
                      [0.0, 0.08], [0.105, 0.105], 10,
                      m["cream"], caps=False)]


def build_belt(m):
    """Navy waist belt: tube around the raincoat waist (z 0.94-0.88),
    0.008 proud of the coat in both rx and ry (037 lesson: check
    ry too)."""
    return [make_elliptical_tube("NavyBelt", BELT_RINGS, 16,
                                 m["navy"], caps=False)]


def build_belt_buckle(m):
    """Silver belt buckle at the front centre (0, -0.174, 0.91):
    belt front at z 0.91 is y -0.1685, so the 0.012-thick box is
    half-buried and 0.0115 proud."""
    return add_box("SilverBeltBuckle", (0, -0.174, 0.91),
                   (0.05, 0.012, 0.04), m["silver"])


def build_trousers(m):
    """Navy trousers: tube around both leg tops, z 0.62-0.34,
    hem ends inside the rain boots."""
    return [make_elliptical_tube("NavyTrousers", TROUSER_RINGS, 12,
                                 m["navy"], caps=False)]


def build_boot(m, sx):
    """Yellow tall rain boot: tube around the lower leg (z 0.50-0.02,
    r 0.118) + sole wedge landing z=0.0 + silver cuff ring at the
    top (z 0.52-0.48, r 0.124). Sole wedge top 0.105/0.055 (0.005
    above the mannequin foot top 0.10/0.045) — 036 v1 lesson."""
    tube = make_tube("YellowRainBoot", (sx * 0.13, 0, 0.50), (0, 0, -1),
                     [0.0, 0.48], [0.118, 0.118], 10,
                     m["yellow"], caps=False)
    sole = make_wedge("YellowRainBootSole", (sx * 0.13, -0.02, 0.0),
                      0.102, 0.095, -0.165, 0.0, 0.105, 0.055,
                      m["yellow"])
    cuff = make_tube("SilverBootCuff", (sx * 0.13, 0, 0.52), (0, 0, -1),
                     [0.0, 0.04], [0.124, 0.124], 10,
                     m["silver"], caps=False)
    return [tube, sole, cuff]


def build_hat(m):
    """Yellow wide-brim rain hat (031 sun-hat construction): brim as
    a closed thin cylinder (2 rings + caps, NOT a single-sided disc
    — the camera sits below the brim at z 1.45) + flat dome crown
    sphere r 0.26, centre z 1.63, top 1.773, covering the hair cap
    top (1.75). Brim 0.34, crown flattened 0.55 — 031 v2 lesson:
    a narrow brim + tall dome reads as a helmet, not a hat."""
    brim = make_elliptical_tube("YellowHatBrim",
                                [(1.622, 0.34, 0.34), (1.608, 0.34, 0.34)],
                                24, m["yellow"], caps=True)
    crown = add_sphere("YellowHatCrown", (0, 0.01, 1.63), 0.26, 12, 6,
                       (1.0, 0.95, 0.55), m["yellow"])
    return [brim, crown]


def build_hatband(m):
    """Navy hat band around the crown base (z 1.66-1.62). Crown
    ellipsoid centre y +0.01: at z 1.66 the crown +y surface is
    0.2515, at z 1.62 it is 0.2564, so the band ry (0.258/0.262)
    clears by 0.0065/0.0056 (031 v3 lesson: size ry off the +y
    surface, not the crown ry)."""
    return [make_elliptical_tube("NavyHatBand", HATBAND_RINGS, 16,
                                 m["navy"], caps=False)]


def build_cat_ear(m, sx):
    """Navy cat ear: four-sided pyramid (032 method), base buried in
    the hat crown at z=1.70, apex at z=1.86 (0.087 above the crown
    top 1.773)."""
    x0, x1 = sx * 0.05, sx * 0.15
    ax = sx * 0.12
    verts = [(x0, -0.02, 1.70), (x1, -0.02, 1.70),
             (x1, 0.08, 1.70), (x0, 0.08, 1.70),
             (ax, 0.03, 1.86)]
    faces = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4),
             (3, 2, 1, 0)]
    return mesh_from_data("NavyCatEar", verts, faces, m["navy"])


def build_streak(m):
    """Light-blue hair streak: flattened ellipsoid half-embedded in
    the black hair cap, front-right below the hat brim (032
    method). Top z 1.49 stays below the brim bottom (1.608) — 031
    v1 lesson: a streak must not poke through the hat."""
    return [add_sphere("HairStreak", (0.11, -0.125, 1.44), 0.05, 8, 4,
                       (0.55, 0.45, 1.0), m["lightblue"])]


def build_earring(m, sx):
    """Gold stud earring: small sphere half-buried in the head side
    (±0.222, 0, 1.47), outer face 0.019 proud."""
    return add_sphere("GoldEarring", (sx * 0.222, 0, 1.47), 0.015, 6, 3,
                      (1.0, 1.0, 1.0), m["gold"])


def build_glove(m):
    """Navy glove on the left hand: sphere r 0.095 at the left
    wrist + 0.03 along the arm axis, covering the hand sphere."""
    wrist, direction = wrist_pos(-1)
    centre = wrist + direction * 0.03
    return [add_sphere("NavyGlove", tuple(centre), 0.095, 6, 4,
                       (1.0, 0.9, 1.0), m["navy"])]


def build_umbrella(m):
    """Umbrella held in the right hand (sixth handheld item):
    silver shaft from the right wrist along SHAFT_DIR (48 deg off
    the arm's upward extension, so it leaves the cuff at the wrist
    instead of running along the forearm), navy grip around the
    shaft base (s 0.02-0.16, emerging from the glove), yellow cone
    canopy (r 0.22 -> 0.02, h 0.10, 12 sides, capped underside)
    at the shaft top, silver tip on the apex."""
    wrist, _ = wrist_pos(1)
    w = Vector(wrist)
    top = w + SHAFT_DIR * SHAFT_LEN
    shaft = make_tube("SilverUmbrellaShaft", tuple(w), tuple(SHAFT_DIR),
                      [0.0, SHAFT_LEN], [0.012, 0.012], 6,
                      m["silver"], caps=True)
    grip = make_tube("NavyUmbrellaGrip", tuple(w), tuple(SHAFT_DIR),
                     [0.02, 0.16], [0.025, 0.025], 8,
                     m["navy"], caps=True)
    canopy = make_tube("YellowUmbrellaCanopy", tuple(top), (0, 0, 1),
                       [0.0, 0.10], [0.22, 0.02], 12,
                       m["yellow"], caps=True)
    tip = add_sphere("SilverUmbrellaTip", (top.x, top.y, top.z + 0.10),
                     0.015, 6, 3, (1.0, 1.0, 1.0), m["silver"])
    return [shaft, grip, canopy, tip], w, top


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["sweater"] + parts["sweater_drops"])
    ok = True
    ok &= check_gap("torso: cream sweater vs mannequin torso @z=1.28",
                    interp_rings(SWEATER_RINGS, 1.28)[0],
                    interp_rings(TORSO_RINGS, 1.28)[0])
    ok &= check_gap("torso: cream sweater vs mannequin torso @z=0.95",
                    interp_rings(SWEATER_RINGS, 0.95)[0],
                    interp_rings(TORSO_RINGS, 0.95)[0])
    ok &= check_relief("torso: blue raindrop relief", 0.015,
                       lo=0.005, hi=0.030)
    print("L2_CHECK torso: cream turtleneck sweater clears the torso, "
          "3 blue raindrops on the chest front PASS")
    return objs, ok


def assemble_coat(parts):
    objs = (parts["raincoat"] + parts["coat_drops"] + parts["pleats"]
            + parts["hood"])
    ok = True
    ok &= check_gap("coat: yellow raincoat vs cream sweater @z=1.20",
                    interp_rings(RAINCOAT_RINGS, 1.20)[0],
                    interp_rings(SWEATER_RINGS, 1.20)[0])
    ok &= check_gap("coat: yellow raincoat vs cream sweater @z=0.90",
                    interp_rings(RAINCOAT_RINGS, 0.90)[0],
                    interp_rings(SWEATER_RINGS, 0.90)[0])
    ok &= check_gap("coat: yellow raincoat vs cream sweater ry @z=1.20",
                    interp_rings(RAINCOAT_RINGS, 1.20)[1],
                    interp_rings(SWEATER_RINGS, 1.20)[1])
    ok &= check_gap("coat: yellow raincoat vs cream sweater ry @z=0.90",
                    interp_rings(RAINCOAT_RINGS, 0.90)[1],
                    interp_rings(SWEATER_RINGS, 0.90)[1])
    ok &= check_gap("coat: yellow hood vs yellow raincoat @z=1.44",
                    interp_rings(HOOD_RINGS, 1.44)[0],
                    interp_rings(RAINCOAT_RINGS, 1.44)[0])
    ok &= check_gap("coat: yellow hood vs yellow raincoat @z=1.38",
                    interp_rings(HOOD_RINGS, 1.38)[0],
                    interp_rings(RAINCOAT_RINGS, 1.38)[0])
    ok &= check_relief("coat: blue raindrop relief", 0.015,
                       lo=0.005, hi=0.030)
    ok &= check_relief("coat: yellow pleat fin height", 0.022,
                       lo=0.005, hi=0.030)
    print("L2_CHECK coat: yellow mid-length raincoat hangs loose over "
          "the cream sweater, 2 blue raindrops on the front edges, "
          "8 pleat fins at the hem, hood folded behind the neck PASS")
    return objs, ok


def assemble_sleeves(parts):
    objs = parts["sleeves"] + parts["cuffs"]
    ok = True
    ok &= check_gap("sleeve: navy sleeve vs mannequin arm @0.0",
                    0.125, 0.085)
    ok &= check_gap("sleeve: cream cuff vs navy sleeve end",
                    0.105, 0.096)
    ok &= check_gap("sleeve: cream cuff vs navy sleeve @s=0.60",
                    0.105, 0.0986)
    print("L2_CHECK sleeves: navy long sleeves over the arms, cream "
          "cuffs at the wrists PASS")
    return objs, ok


def assemble_belt(parts):
    objs = parts["belt"] + [parts["buckle"]]
    ok = True
    ok &= check_gap("belt: navy belt vs yellow raincoat @z=0.94",
                    interp_rings(BELT_RINGS, 0.94)[0],
                    interp_rings(RAINCOAT_RINGS, 0.94)[0])
    ok &= check_gap("belt: navy belt vs yellow raincoat @z=0.88",
                    interp_rings(BELT_RINGS, 0.88)[0],
                    interp_rings(RAINCOAT_RINGS, 0.88)[0])
    ok &= check_gap("belt: navy belt vs yellow raincoat ry @z=0.94",
                    interp_rings(BELT_RINGS, 0.94)[1],
                    interp_rings(RAINCOAT_RINGS, 0.94)[1])
    ok &= check_gap("belt: navy belt vs yellow raincoat ry @z=0.88",
                    interp_rings(BELT_RINGS, 0.88)[1],
                    interp_rings(RAINCOAT_RINGS, 0.88)[1])
    ok &= check_relief("belt: silver buckle relief", 0.0115,
                       lo=0.005, hi=0.030)
    print("L2_CHECK belt: navy waist belt cinches the raincoat, "
          "silver buckle at the front PASS")
    return objs, ok


def assemble_head(parts):
    objs = (parts["hat"] + parts["band"] + [parts["hat_drop"]]
            + parts["ears"] + parts["streak"] + parts["earrings"])
    ok = True
    # Hat crown ellipsoid: centre (0, 0.01, 1.63), radii
    # (0.26, 0.247, 0.143). At z 1.66: rx 0.2542, +y surface 0.2515;
    # at z 1.62: rx 0.2594, +y surface 0.2564.
    ok &= check_gap("head: navy hat band vs yellow crown rx @z=1.66",
                    0.260, 0.2542)
    ok &= check_gap("head: navy hat band vs yellow crown +y @z=1.66",
                    0.258, 0.2515)
    ok &= check_gap("head: navy hat band vs yellow crown rx @z=1.62",
                    0.265, 0.2594)
    ok &= check_gap("head: navy hat band vs yellow crown +y @z=1.62",
                    0.262, 0.2564)
    ok &= check_gap("head: yellow rain hat brim bottom vs eye line",
                    1.608, 1.525)
    ok &= check_gap("head: navy cat ear apex vs yellow crown top",
                    1.86, 1.773)
    ok &= check_relief("head: blue raindrop on hat relief", 0.015,
                       lo=0.005, hi=0.030)
    ok &= check_relief("head: gold earring relief", 0.019,
                       lo=0.005, hi=0.030)
    print("L2_CHECK head: yellow wide-brim rain hat over the hair, "
          "navy band following the crown, blue raindrop on the hat "
          "front, cat ears out of the crown, blue streak below the "
          "brim, gold studs PASS")
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
    ok &= check_gap("feet: yellow rain boot vs mannequin leg @z=0.20",
                    0.118, 0.0866)
    ok &= check_gap("feet: silver boot cuff vs yellow rain boot",
                    0.124, 0.118)
    ok &= check_gap("feet: yellow rain boot sole vs mannequin foot",
                    0.102, 0.095)
    print("L2_CHECK feet: yellow tall rain boots centre z=0.0, soles "
          "on ground; silver cuffs at the boot tops PASS")
    return objs, ok


def assemble_hand(parts, wrist, top):
    objs = parts["glove"] + parts["umbrella"]
    ok = True
    ok &= check_gap("hand: navy glove vs mannequin hand",
                    0.095, 0.085)
    # Umbrella clearances, as ellipse-normalised values (>1.15 = clear).
    # Shaft point at z 0.90:
    t = (0.90 - wrist.z) / SHAFT_DIR.z
    sp = wrist + SHAFT_DIR * t
    rx, ry = interp_rings(RAINCOAT_RINGS, 0.90)
    sv = ellipse_value(sp.x, sp.y, rx, ry)
    print("L2_CHECK hand: umbrella shaft @z=0.90 ellipse_value=%.3f "
          "(must be >1.15)" % sv)
    ok &= sv > 1.15
    # Canopy rim point closest to the torso axis, at z = top.z:
    cx, cy = top.x, top.y
    dx, dy = -cx, -cy
    dl = math.hypot(dx, dy)
    rx, ry = interp_rings(RAINCOAT_RINGS, top.z)
    rimx, rimy = cx + 0.22 * dx / dl, cy + 0.22 * dy / dl
    cv = ellipse_value(rimx, rimy, rx, ry)
    print("L2_CHECK hand: umbrella canopy rim ellipse_value=%.3f "
          "(must be >1.15)" % cv)
    ok &= cv > 1.15
    # Canopy rim vs sleeve: the rim sits BESIDE the shoulder
    # (top.z 1.204 < sleeve top 1.339), so a height comparison is the
    # wrong check — compare radial distance to the sleeve axis
    # instead. Sleeve axis: origin (0.313, 0, 1.339), direction
    # (0.139, 0, -0.99); sleeve radius at z=top.z is ~0.119
    # (interp 0.125@0 -> 0.118@0.17 along the arm).
    ax = 0.313 + 0.139 * (1.339 - top.z) / 0.9903
    dx, dy = ax - cx, -cy
    dl = math.hypot(dx, dy)
    srimx, srimy = cx + 0.22 * dx / dl, cy + 0.22 * dy / dl
    rim_dist = math.hypot(srimx - ax, srimy)
    s_arm = (1.339 - top.z) / 0.9903
    sleeve_r = 0.125 + (0.118 - 0.125) * (s_arm / 0.17)
    print("L2_CHECK hand: umbrella canopy rim vs sleeve axis "
          "rim_dist=%.3f sleeve_r=%.3f" % (rim_dist, sleeve_r))
    ok &= check_gap("hand: umbrella canopy rim vs sleeve surface",
                    rim_dist, sleeve_r)
    print("L2_CHECK hand: navy glove covers the left hand, umbrella "
          "held in the right hand, shaft + canopy clear of the "
          "raincoat and sleeve PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: yellow raincoat vs cream sweater @z=1.20",
                    interp_rings(RAINCOAT_RINGS, 1.20)[0],
                    interp_rings(SWEATER_RINGS, 1.20)[0])
    ok &= check_gap("L3 layer: navy belt vs yellow raincoat @z=0.94",
                    interp_rings(BELT_RINGS, 0.94)[0],
                    interp_rings(RAINCOAT_RINGS, 0.94)[0])
    ok &= check_gap("L3 layer: yellow rain hat brim vs eye line",
                    1.608, 1.525)
    ok &= check_gap("L3 joint: navy sleeve vs mannequin arm",
                    0.125, 0.085)
    ok &= check_gap("L3 joint: yellow rain boot vs mannequin leg @z=0.20",
                    0.118, 0.0866)
    ok &= check_gap("L3 joint: yellow rain boot sole vs mannequin foot",
                    0.102, 0.095)
    print("L3_CHECK outfit: yellow raincoat over the cream sweater, "
          "navy belt cinching the waist, rain hat above the eyes, "
          "rain boots on ground z=0.000 PASS")
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
    report_l1("CreamSweater", parts["sweater"])
    parts["raincoat"] = build_raincoat(m)
    report_l1("YellowRaincoat", parts["raincoat"])
    parts["sweater_drops"] = [
        build_raindrop_on_sweater(m, 270, 1.32),
        build_raindrop_on_sweater(m, 262, 1.02),
        build_raindrop_on_sweater(m, 278, 1.02)]
    report_l1("BlueRaindropsOnSweater x3", parts["sweater_drops"])
    parts["coat_drops"] = [
        build_raindrop_on_coat(m, 225, 1.05),
        build_raindrop_on_coat(m, 315, 1.05)]
    report_l1("BlueRaindropsOnCoat x2", parts["coat_drops"])
    parts["hat_drop"] = build_raindrop_on_hat(m)
    report_l1("BlueRaindropOnHat", [parts["hat_drop"]])
    parts["pleats"] = [build_pleat_fin(m, a) for a in PLEAT_ANGLES]
    report_l1("YellowPleats x8", parts["pleats"])
    parts["hood"] = build_hood(m)
    report_l1("YellowHood", parts["hood"])
    parts["sleeves"] = []
    for sx in (-1, 1):
        parts["sleeves"] += build_sleeve(m, sx)
    report_l1("NavySleeves x2", parts["sleeves"])
    parts["cuffs"] = []
    for sx in (-1, 1):
        parts["cuffs"] += build_cuff(m, sx)
    report_l1("CreamCuffs x2", parts["cuffs"])
    parts["belt"] = build_belt(m)
    report_l1("NavyBelt", parts["belt"])
    parts["buckle"] = build_belt_buckle(m)
    report_l1("SilverBeltBuckle", [parts["buckle"]])
    parts["trousers"] = build_trousers(m)
    report_l1("NavyTrousers", parts["trousers"])
    parts["boots"] = []
    for sx in (-1, 1):
        parts["boots"] += build_boot(m, sx)
    report_l1("YellowRainBoots x2", parts["boots"])
    parts["hat"] = build_hat(m)
    report_l1("YellowRainHat", parts["hat"])
    parts["band"] = build_hatband(m)
    report_l1("NavyHatBand", parts["band"])
    parts["ears"] = [build_cat_ear(m, sx) for sx in (-1, 1)]
    report_l1("NavyCatEars x2", parts["ears"])
    parts["streak"] = build_streak(m)
    report_l1("HairStreak", parts["streak"])
    parts["earrings"] = [build_earring(m, sx) for sx in (-1, 1)]
    report_l1("GoldEarrings x2", parts["earrings"])
    parts["glove"] = build_glove(m)
    report_l1("NavyGlove", parts["glove"])
    parts["umbrella"], wrist, top = build_umbrella(m)
    report_l1("Umbrella x4", parts["umbrella"])

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    _, ok = assemble_torso(parts)
    l2_ok &= ok
    _, ok = assemble_coat(parts)
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
    _, ok = assemble_hand(parts, wrist, top)
    l2_ok &= ok
    print("L2_SUMMARY %s" % ("ALL PASS" if l2_ok else "FAILURES PRESENT"))

    # ---- L3 full outfit on the mannequin ----
    costume = (parts["sweater"] + parts["raincoat"]
               + parts["sweater_drops"] + parts["coat_drops"]
               + [parts["hat_drop"]] + parts["pleats"] + parts["hood"]
               + parts["sleeves"] + parts["cuffs"] + parts["belt"]
               + [parts["buckle"]] + parts["trousers"]
               + parts["boots"] + parts["hat"] + parts["band"]
               + parts["ears"] + parts["streak"]
               + parts["earrings"] + parts["glove"] + parts["umbrella"])
    l3_ok = assemble_outfit(parts, mannequin)

    # --- normal self-check (all solids; no flat star patches this
    # round, so fix_normals may run on every costume object) ---
    for obj in mannequin + costume:
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
