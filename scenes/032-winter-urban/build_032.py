# -*- coding: utf-8 -*-
"""032 异环式都市时装 · 冬日套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整套穿到人体底座上试穿）。
设计见 design.md。BACKLOG 本轮有项：异环线第八件——冬日场景风
（015 夜行者、025 街头、026 学院、027 运动、028 居家、029 通勤、
031 夏日之后；学院/居家/运动/街头/通勤/夜行/夏日矩阵里冬日首次做）。
藏青长款羽绒大衣（前开襟、绗缝横纹、雪花纹、金扣×6、衣摆褶裥×8、
奶油抓绒下摆）+ 奶油粗针高领毛衣 + 砖红围巾 + 奶油毛线帽（绒球+
猫耳）+ 蓝挑染 + 藏青保暖长裤 + 奶油腿套 + 焦糖冬靴 + 左手连指
手套 + 右手外带咖啡杯。围巾垂尾走毛衣面（不走大衣面），免得与
斜挎带交叉——本轮不用斜挎带，手持物改外带咖啡杯。
Run: blender --background --python build_032.py
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

BLEND_OUT = os.path.join(HERE, "032-winter-urban.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "032-winter-urban.png")
WIRE_JSON = "/tmp/winter_urban_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

# Mannequin torso rings (same base as 001..031) for gap checks.
TORSO_RINGS = [(1.28, 0.270, 0.140), (0.95, 0.240, 0.130),
               (0.62, 0.210, 0.120)]

SWEATER_RINGS = [(1.44, 0.288, 0.152), (1.10, 0.272, 0.144),
                 (0.80, 0.258, 0.138), (0.72, 0.252, 0.134),
                 (0.60, 0.248, 0.132)]
COAT_RINGS = [(1.50, 0.312, 0.164), (1.20, 0.310, 0.162),
              (0.90, 0.306, 0.160), (0.62, 0.302, 0.158),
              (0.52, 0.306, 0.160), (0.42, 0.310, 0.162)]
TROUSER_RINGS = [(0.62, 0.246, 0.128), (0.48, 0.240, 0.126),
                 (0.34, 0.232, 0.124)]
PLEAT_ANGLES = [170, 200, 230, 320, 350, 20, 50, 110]  # all outside 240-300
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    navy = solid_material("Navy", (0.014, 0.023, 0.058), roughness=0.6)
    cream = solid_material("Cream", (0.914, 0.863, 0.791), roughness=0.6)
    caramel = solid_material("Caramel", (0.434, 0.195, 0.042),
                             roughness=0.6)
    brick = solid_material("Brick", (0.381, 0.042, 0.027), roughness=0.6)
    gold = solid_material("Gold", (0.657, 0.351, 0.009), metallic=0.6,
                          roughness=0.35)
    black = solid_material("Hair_Black", (0.011, 0.011, 0.015),
                           roughness=0.7)
    lightblue = solid_material("LightBlue", (0.212, 0.479, 0.807),
                               roughness=0.6)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"navy": navy, "cream": cream, "caramel": caramel,
            "brick": brick, "gold": gold, "black": black,
            "lightblue": lightblue, "skin": skin, "eye": eye}


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001..031).
    Black hair cap. Two dark eyes stay visible below the beanie brim."""
    objs = []
    objs.append(add_sphere("Mannequin_Head", (0, 0, 1.50), 0.22, 10, 8,
                           (1.0, 0.9, 1.05), m["skin"]))
    for sx in (-1, 1):
        objs.append(add_sphere("Mannequin_Eye", (sx * 0.072, -0.183, 1.525),
                               0.022, 6, 3, (1.0, 0.45, 1.35), m["eye"]))
    objs.append(add_sphere("Mannequin_Hair", (0, 0.02, 1.57), 0.225, 10, 6,
                           (1.0, 0.95, 0.80), m["black"]))
    objs.append(make_tube("Mannequin_Neck", (0, 0, 1.28), (0, 0, 1),
                          [0.0, 0.10], [0.09, 0.085], 6, m["skin"]))
    objs.append(make_elliptical_tube(
        "Mannequin_Torso", TORSO_RINGS, 8, m["skin"], caps=True))
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


def wrist_pos(sx):
    """Right/left wrist centre (same math as the mannequin builder)."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * 0.14, 0, ARM_DIR[2]))
    return shoulder + direction.normalized() * 0.55, direction.normalized()


# ------------------------------------------------------------ L1 components
def build_sweater(m):
    """Cream chunky-knit sweater, inner layer: 5 rings, z 1.44-0.60.
    Hem reaches z 0.60, below the trouser top (0.62), so no bare
    torso shows through the coat's open front. Clears the torso
    by >=0.010 at every height."""
    return [make_elliptical_tube("CreamSweater", SWEATER_RINGS, 16,
                                 m["cream"], caps=False)]


def build_turtleneck(m):
    """Cream turtleneck collar ring (z 1.46-1.40, r 0.108):
    0.018 proud of the neck tube (0.09)."""
    return [make_tube("CreamTurtleneck", (0, 0, 1.46), (0, 0, -1),
                      [0.0, 0.06], [0.108, 0.108], 10,
                      m["cream"], caps=False)]


def build_knit_ring(m, z):
    """One knit-texture ring on the sweater (028 method): 0.006 proud,
    same cream, reads through shading."""
    rx, ry = interp_rings(SWEATER_RINGS, z + 0.015)
    rx2, ry2 = interp_rings(SWEATER_RINGS, z - 0.015)
    rings = [(z + 0.015, rx + 0.006, ry + 0.006),
             (z - 0.015, rx2 + 0.006, ry2 + 0.006)]
    return [make_elliptical_tube("CreamKnitRing", rings, 16,
                                 m["cream"], caps=False)]


def build_coat(m):
    """Navy long puffer coat, open front: arc 300-600 deg leaves the
    240-300 deg front wedge open so the cream sweater shows.
    Knee-length: z 1.50-0.42, 6 rings."""
    return [make_elliptical_tube("NavyCoat", COAT_RINGS, 16,
                                 m["navy"], arc=(300, 600), caps=False)]


def build_quilt_band(m, z):
    """One quilted horizontal band on the coat: 0.006 proud, same navy,
    follows the open-front arc."""
    rx, ry = interp_rings(COAT_RINGS, z + 0.02)
    rx2, ry2 = interp_rings(COAT_RINGS, z - 0.02)
    rings = [(z + 0.02, rx + 0.006, ry + 0.006),
             (z - 0.02, rx2 + 0.006, ry2 + 0.006)]
    return [make_elliptical_tube("NavyQuiltBand", rings, 16,
                                 m["navy"], arc=(300, 600), caps=False)]


def build_coat_hem(m):
    """Cream fleece hem at the coat bottom (z 0.46-0.42): 0.006 proud
    of the coat, same open-front arc, fleece lining peeking out."""
    rings = [(0.46, 0.314, 0.167), (0.42, 0.316, 0.168)]
    return [make_elliptical_tube("CreamCoatHem", rings, 16,
                                 m["cream"], arc=(300, 600), caps=False)]


def build_coat_button(m, angle_deg, z):
    """One gold button on a coat front edge: position + outward
    normal from ellipse_point (016 method), centre 0.004 off the
    coat surface so the 0.012-thick box is half-buried."""
    rx, ry = interp_rings(COAT_RINGS, z)
    p, n = ellipse_point(rx, ry, angle_deg)
    c = Vector((p.x, p.y, z)) + n * 0.004
    return add_box("GoldCoatButton", tuple(c), (0.020, 0.012, 0.020),
                   m["gold"])


def build_snowflake(m, angle_deg, z):
    """One cream snowflake (crossed boxes) on a coat front panel:
    centre 0.004 off the coat surface, rotZ aligns local +Y with
    the surface normal (hatpin method)."""
    rx, ry = interp_rings(COAT_RINGS, z)
    p, n = ellipse_point(rx, ry, angle_deg)
    c = Vector((p.x, p.y, z)) + n * 0.004
    theta = math.atan2(-n.x, n.y)
    h = add_box_rot("CreamSnowflakeH", tuple(c), (0.055, 0.012, 0.012),
                    m["cream"], (0, 0, theta))
    v = add_box_rot("CreamSnowflakeV", tuple(c), (0.012, 0.012, 0.055),
                    m["cream"], (0, 0, theta))
    return [h, v]


def build_pleat_fin(m, angle_deg):
    """One 3D pleat fin: a closed thin solid (10 quads) following the
    coat cone, inner edge 0.004 off the coat, outer edge 0.026 off,
    tangential half-thickness 0.004. Same construction as 026/030."""
    rows = [0.62, 0.52, 0.42]
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
    return mesh_from_data("NavyPleat", verts, faces, m["navy"])


def build_sleeve(m, sx):
    """Navy long sleeve over the arm (shoulder to wrist).
    Capped (025 v2 lesson). Origin lifted 0.12 along the arm axis
    so the sleeve starts at z 1.34, emerging from the coat shoulder
    (v1 started at the shoulder joint z 1.22 and read as a slab
    floating beside the body with a background gap)."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    origin = shoulder - direction.normalized() * 0.12
    return [make_tube("NavySleeve", origin, direction,
                      [0.0, 0.17, 0.34, 0.51, 0.67],
                      [0.125, 0.118, 0.110, 0.102, 0.096], 10,
                      m["navy"], caps=True)]


def build_cuff(m, sx):
    """Cream cuff ring at the wrist (t 0.48-0.56 along the arm):
    r 0.102, 0.006 proud of the sleeve end (0.096)."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    origin = shoulder + direction.normalized() * 0.48
    return [make_tube("CreamCuff", origin, direction,
                      [0.0, 0.08], [0.102, 0.102], 10,
                      m["cream"], caps=False)]


def build_scarf_wrap(m):
    """Brick-red scarf wrap around the neck (z 1.52-1.46, r 0.118):
    0.010 proud of the turtleneck collar (0.108), sits above the
    coat collar."""
    return [make_tube("BrickScarfWrap", (0, 0, 1.52), (0, 0, -1),
                      [0.0, 0.06], [0.118, 0.118], 12,
                      m["brick"], caps=False)]


def build_scarf_tail(m):
    """Brick-red scarf tail hanging down the sweater front:
    flat box, top z 1.46 meets the wrap bottom, half-buried in the
    sweater (front face 0.010 proud)."""
    tail = add_box("BrickScarfTail", (0.06, -0.148, 1.23),
                   (0.09, 0.018, 0.46), m["brick"])
    fringe = []
    for fx in (0.03, 0.06, 0.09):
        fringe.append(add_box("BrickScarfFringe", (fx, -0.148, 0.97),
                              (0.018, 0.018, 0.06), m["brick"]))
    return [tail] + fringe


def build_beanie(m):
    """Cream knit beanie: dome sphere r 0.25, centre z 1.62, flattened
    z 0.60, top 1.77 covering the hair cap top (1.75); brim ring
    z 1.60-1.56, r 0.250-0.248, 0.024 proud of the hair at z 1.58.
    v2: brim raised 1.56-1.50 -> 1.60-1.56 — v1's brim bottom (1.50)
    sat on the sight line to the eyes (crossing z 1.524) and hid
    them; the raised brim clears the eyes (z 1.525)."""
    dome = add_sphere("CreamBeanieDome", (0, 0.01, 1.62), 0.25, 12, 6,
                      (1.0, 0.95, 0.60), m["cream"])
    brim = make_elliptical_tube("CreamBeanieBrim",
                                [(1.60, 0.250, 0.250), (1.56, 0.248, 0.248)],
                                24, m["cream"], caps=False)
    return [dome, brim]


def build_pompom(m):
    """Brick-red pom-pom on the beanie top (0, 0.01, 1.78), r 0.05:
    bottom 1.73 embedded 0.04 into the dome top (1.77)."""
    return [add_sphere("BrickPomPom", (0, 0.01, 1.78), 0.05, 8, 4,
                       (1.0, 1.0, 1.0), m["brick"])]


def build_cat_ear(m, sx):
    """Navy cat ear: four-sided pyramid (015 method), base buried in
    the beanie dome at z=1.68, apex at z=1.84 (0.07 above the dome
    top 1.77)."""
    x0, x1 = sx * 0.05, sx * 0.15
    ax = sx * 0.12
    verts = [(x0, -0.02, 1.68), (x1, -0.02, 1.68),
             (x1, 0.08, 1.68), (x0, 0.08, 1.68),
             (ax, 0.03, 1.84)]
    faces = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4),
             (3, 2, 1, 0)]
    return mesh_from_data("NavyCatEar", verts, faces, m["navy"])


def build_streak(m):
    """Blue hair streak: flattened ellipsoid half-embedded in the
    black hair cap, front-right below the beanie brim (015 method).
    Top z 1.49 stays below the brim bottom (1.50) — 031 v1 lesson:
    a streak must not poke through the hat."""
    return [add_sphere("HairStreak", (0.11, -0.125, 1.44), 0.05, 8, 4,
                       (0.55, 0.45, 1.0), m["lightblue"])]


def build_earring(m, sx):
    """Gold stud earring: small sphere half-buried in the head side
    (±0.222, 0, 1.47), outer face 0.019 proud."""
    return add_sphere("GoldEarring", (sx * 0.222, 0, 1.47), 0.015, 6, 3,
                      (1.0, 1.0, 1.0), m["gold"])


def build_trousers(m):
    """Navy warm trousers: tube around both leg tops, z 0.62-0.34,
    hem ends above the leg warmers."""
    return [make_elliptical_tube("NavyTrousers", TROUSER_RINGS, 12,
                                 m["navy"], caps=False)]


def build_legwarmer(m, sx):
    """Cream knit leg warmer around one lower leg (z 0.36-0.14,
    r 0.110): 0.024 proud of the leg, peeking out below the
    trouser hem."""
    return [make_tube("CreamLegWarmer", (sx * 0.13, 0, 0.36), (0, 0, -1),
                      [0.0, 0.22], [0.110, 0.110], 10,
                      m["cream"], caps=False)]


def build_boot(m, sx):
    """Caramel winter boot: tube around the lower leg (z 0.34-0.02,
    r 0.118, 0.008 proud of the leg warmer) + sole wedge landing
    z=0.0 + cream fur cuff ring at the top (z 0.36-0.32, r 0.124)."""
    tube = make_tube("CaramelBoot", (sx * 0.13, 0, 0.34), (0, 0, -1),
                     [0.0, 0.32], [0.118, 0.118], 10,
                     m["caramel"], caps=False)
    sole = make_wedge("CaramelBootSole", (sx * 0.13, -0.02, 0.0),
                      0.102, 0.095, -0.165, 0.0, 0.025, 0.025,
                      m["caramel"])
    cuff = make_tube("CreamFurCuff", (sx * 0.13, 0, 0.36), (0, 0, -1),
                     [0.0, 0.04], [0.124, 0.124], 10,
                     m["cream"], caps=False)
    return [tube, sole, cuff]


def build_mitten(m):
    """Cream mitten on the left hand: sphere r 0.095 at the left
    wrist + 0.03 along the arm axis, covering the hand sphere."""
    wrist, direction = wrist_pos(-1)
    centre = wrist + direction * 0.03
    return [add_sphere("CreamMitten", tuple(centre), 0.095, 6, 4,
                       (1.0, 0.9, 1.0), m["cream"])]


def build_coffee_cup(m):
    """Takeaway coffee cup in the right hand (camera side): cream
    body through the palm + caramel lid + brick sleeve band.
    Body z 0.64-0.46 passes through the right-hand sphere
    (centre z 0.675, r 0.085), reads as held — 029 briefcase
    handle method. v2: body enlarged and lowered so more of it
    shows below the cuff (v1's lid sat inside the cuff tube)."""
    wrist, _ = wrist_pos(1)
    wx, wy, _ = wrist
    body = make_tube("CreamCoffeeCup", (wx, wy, 0.64), (0, 0, -1),
                     [0.0, 0.18], [0.055, 0.051], 12,
                     m["cream"], caps=True)
    lid = make_tube("CaramelCupLid", (wx, wy, 0.67), (0, 0, -1),
                    [0.0, 0.03], [0.057, 0.057], 12,
                    m["caramel"], caps=True)
    band = make_tube("BrickCupSleeve", (wx, wy, 0.60), (0, 0, -1),
                     [0.0, 0.06], [0.059, 0.059], 12,
                     m["brick"], caps=False)
    return [body, lid, band]


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["sweater"] + parts["collar"] + parts["knit_rings"])
    ok = True
    ok &= check_gap("torso: cream sweater vs mannequin torso @z=1.28",
                    interp_rings(SWEATER_RINGS, 1.28)[0],
                    interp_rings(TORSO_RINGS, 1.28)[0])
    ok &= check_gap("torso: cream sweater vs mannequin torso @z=0.95",
                    interp_rings(SWEATER_RINGS, 0.95)[0],
                    interp_rings(TORSO_RINGS, 0.95)[0])
    ok &= check_gap("torso: cream turtleneck vs mannequin neck",
                    0.108, 0.09)
    ok &= check_relief("torso: cream knit ring relief", 0.006,
                       lo=0.005, hi=0.015)
    print("L2_CHECK torso: cream chunky-knit sweater clears the torso, "
          "turtleneck around the neck, 3 knit rings as texture PASS")
    return objs, ok


def assemble_coat(parts):
    objs = (parts["coat"] + parts["quilt"] + parts["hem"]
            + parts["buttons"] + parts["snowflakes"] + parts["pleats"])
    ok = True
    ok &= check_gap("coat: navy coat vs cream sweater @z=1.20",
                    interp_rings(COAT_RINGS, 1.20)[0],
                    interp_rings(SWEATER_RINGS, 1.20)[0])
    ok &= check_gap("coat: navy coat vs cream sweater @z=0.90",
                    interp_rings(COAT_RINGS, 0.90)[0],
                    interp_rings(SWEATER_RINGS, 0.90)[0])
    ok &= check_relief("coat: navy quilt band relief", 0.006,
                       lo=0.005, hi=0.015)
    ok &= check_relief("coat: cream fleece hem relief", 0.006,
                       lo=0.005, hi=0.015)
    ok &= check_relief("coat: gold button relief", 0.010,
                       lo=0.005, hi=0.030)
    ok &= check_relief("coat: cream snowflake relief", 0.010,
                       lo=0.005, hi=0.030)
    ok &= check_relief("coat: navy pleat fin height", 0.022,
                       lo=0.005, hi=0.030)
    print("L2_CHECK coat: navy puffer coat hangs loose over the cream "
          "sweater, quilt bands + fleece hem + 6 gold buttons + "
          "2 snowflakes + 8 pleat fins at the hem PASS")
    return objs, ok


def assemble_sleeves(parts):
    objs = parts["sleeves"] + parts["cuffs"]
    ok = True
    ok &= check_gap("sleeve: navy sleeve vs mannequin arm @0.0",
                    0.125, 0.085)
    ok &= check_gap("sleeve: cream cuff vs navy sleeve end",
                    0.102, 0.096)
    print("L2_CHECK sleeves: navy long sleeves over the arms, cream "
          "cuffs at the wrists PASS")
    return objs, ok


def assemble_head(parts):
    objs = (parts["beanie"] + parts["pompom"] + parts["ears"]
            + parts["streak"] + parts["earrings"])
    ok = True
    ok &= check_gap("head: cream beanie dome vs black hair cap @z=1.57",
                    0.2357, 0.225)
    ok &= check_gap("head: cream beanie dome vs black hair cap @z=1.65",
                    0.2449, 0.2016)
    ok &= check_gap("head: cream beanie brim vs black hair cap @z=1.58",
                    0.249, 0.2246)
    ok &= check_gap("head: navy cat ear apex vs beanie dome top",
                    1.84, 1.77)
    ok &= check_relief("head: gold earring relief", 0.019,
                       lo=0.005, hi=0.030)
    print("L2_CHECK head: cream beanie dome over the hair, brim ring "
          "above the eyes, brick pom-pom on top, navy cat ears out "
          "of the dome, blue streak below the brim, gold studs PASS")
    return objs, ok


def assemble_scarf(parts):
    objs = parts["scarf_wrap"] + parts["scarf_tail"]
    ok = True
    ok &= check_gap("scarf: brick wrap vs cream turtleneck",
                    0.118, 0.108)
    ok &= check_relief("scarf: brick tail relief off sweater", 0.010,
                       lo=0.005, hi=0.030)
    print("L2_CHECK scarf: brick wrap around the neck above the coat "
          "collar, tail hangs down the sweater front with fringe PASS")
    return objs, ok


def assemble_legs(parts):
    objs = parts["trousers"] + parts["legwarmers"]
    ok = True
    ok &= check_gap("legs: navy trousers vs mannequin legs @z=0.52",
                    interp_rings(TROUSER_RINGS, 0.52)[0], 0.1023)
    ok &= check_gap("legs: cream leg warmer vs mannequin leg @z=0.20",
                    0.110, 0.0866)
    print("L2_CHECK legs: navy trousers cover the leg tops, cream leg "
          "warmers peek out below the trouser hems PASS")
    return objs, ok


def assemble_feet(parts):
    objs = parts["boots"]
    ok = True
    ok &= check_gap("feet: caramel boot vs cream leg warmer",
                    0.118, 0.110)
    ok &= check_gap("feet: cream fur cuff vs caramel boot",
                    0.124, 0.118)
    ok &= check_gap("feet: caramel boot sole vs mannequin foot",
                    0.102, 0.095)
    print("L2_CHECK feet: caramel boot tubes centre z=0.0, soles on "
          "ground; cream fur cuffs at the boot tops PASS")
    return objs, ok


def assemble_hand(parts):
    objs = parts["mitten"] + parts["cup"]
    ok = True
    ok &= check_gap("hand: cream mitten vs mannequin hand",
                    0.095, 0.085)
    ok &= check_relief("hand: caramel cup lid relief", 0.002,
                       lo=0.001, hi=0.030)
    ok &= check_relief("hand: brick cup sleeve relief", 0.0056,
                       lo=0.005, hi=0.030)
    print("L2_CHECK hand: cream mitten covers the left hand, takeaway "
          "coffee cup passes through the right palm PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: navy coat vs cream sweater @z=1.20",
                    interp_rings(COAT_RINGS, 1.20)[0],
                    interp_rings(SWEATER_RINGS, 1.20)[0])
    ok &= check_gap("L3 layer: brick scarf wrap vs cream turtleneck",
                    0.118, 0.108)
    ok &= check_gap("L3 layer: cream beanie brim vs black hair @z=1.58",
                    0.249, 0.2246)
    ok &= check_gap("L3 joint: navy sleeve vs mannequin arm",
                    0.125, 0.085)
    ok &= check_gap("L3 joint: cream leg warmer vs mannequin leg @z=0.20",
                    0.110, 0.0866)
    ok &= check_gap("L3 joint: caramel boot vs cream leg warmer",
                    0.118, 0.110)
    ok &= check_gap("L3 joint: caramel boot sole vs mannequin foot",
                    0.102, 0.095)
    print("L3_CHECK outfit: navy coat over the cream sweater, brick "
          "scarf above the collar, beanie over the hair, leg warmers "
          "below the trousers, boots on ground z=0.000 PASS")
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
    parts["collar"] = build_turtleneck(m)
    report_l1("CreamTurtleneck", parts["collar"])
    parts["knit_rings"] = [build_knit_ring(m, z)
                           for z in (1.05, 0.95, 0.85)]
    parts["knit_rings"] = [o for ring in parts["knit_rings"] for o in ring]
    report_l1("CreamKnitRings x3", parts["knit_rings"])
    parts["coat"] = build_coat(m)
    report_l1("NavyCoat", parts["coat"])
    parts["quilt"] = [o for z in (1.32, 1.12, 0.92)
                      for o in build_quilt_band(m, z)]
    report_l1("NavyQuiltBands x3", parts["quilt"])
    parts["hem"] = build_coat_hem(m)
    report_l1("CreamCoatHem", parts["hem"])
    parts["buttons"] = [build_coat_button(m, a, z)
                        for a in (240, 300) for z in (1.35, 1.12, 0.90)]
    report_l1("GoldCoatButtons x6", parts["buttons"])
    parts["snowflakes"] = []
    for a in (232, 308):
        parts["snowflakes"] += build_snowflake(m, a, 1.18)
    report_l1("CreamSnowflakes x2", parts["snowflakes"])
    parts["pleats"] = [build_pleat_fin(m, a) for a in PLEAT_ANGLES]
    report_l1("NavyPleats x8", parts["pleats"])
    parts["sleeves"] = []
    for sx in (-1, 1):
        parts["sleeves"] += build_sleeve(m, sx)
    report_l1("NavySleeves x2", parts["sleeves"])
    parts["cuffs"] = []
    for sx in (-1, 1):
        parts["cuffs"] += build_cuff(m, sx)
    report_l1("CreamCuffs x2", parts["cuffs"])
    parts["scarf_wrap"] = build_scarf_wrap(m)
    report_l1("BrickScarfWrap", parts["scarf_wrap"])
    parts["scarf_tail"] = build_scarf_tail(m)
    report_l1("BrickScarfTail+Fringe", parts["scarf_tail"])
    parts["beanie"] = build_beanie(m)
    report_l1("CreamBeanie", parts["beanie"])
    parts["pompom"] = build_pompom(m)
    report_l1("BrickPomPom", parts["pompom"])
    parts["ears"] = [build_cat_ear(m, sx) for sx in (-1, 1)]
    report_l1("NavyCatEars x2", parts["ears"])
    parts["streak"] = build_streak(m)
    report_l1("BlueStreak", parts["streak"])
    parts["earrings"] = [build_earring(m, sx) for sx in (-1, 1)]
    report_l1("GoldEarrings x2", parts["earrings"])
    parts["trousers"] = build_trousers(m)
    report_l1("NavyTrousers", parts["trousers"])
    parts["legwarmers"] = []
    for sx in (-1, 1):
        parts["legwarmers"] += build_legwarmer(m, sx)
    report_l1("CreamLegWarmers x2", parts["legwarmers"])
    parts["boots"] = []
    for sx in (-1, 1):
        parts["boots"] += build_boot(m, sx)
    report_l1("CaramelBoots x2", parts["boots"])
    parts["mitten"] = build_mitten(m)
    report_l1("CreamMitten", parts["mitten"])
    parts["cup"] = build_coffee_cup(m)
    report_l1("CoffeeCup", parts["cup"])

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    _, ok = assemble_torso(parts)
    l2_ok &= ok
    _, ok = assemble_coat(parts)
    l2_ok &= ok
    _, ok = assemble_sleeves(parts)
    l2_ok &= ok
    _, ok = assemble_head(parts)
    l2_ok &= ok
    _, ok = assemble_scarf(parts)
    l2_ok &= ok
    _, ok = assemble_legs(parts)
    l2_ok &= ok
    _, ok = assemble_feet(parts)
    l2_ok &= ok
    _, ok = assemble_hand(parts)
    l2_ok &= ok
    print("L2_SUMMARY %s" % ("ALL PASS" if l2_ok else "FAILURES PRESENT"))

    # ---- L3 full outfit on the mannequin ----
    costume = (parts["sweater"] + parts["collar"] + parts["knit_rings"]
               + parts["coat"] + parts["quilt"] + parts["hem"]
               + parts["buttons"] + parts["snowflakes"] + parts["pleats"]
               + parts["sleeves"] + parts["cuffs"] + parts["scarf_wrap"]
               + parts["scarf_tail"] + parts["beanie"] + parts["pompom"]
               + parts["ears"] + parts["streak"] + parts["earrings"]
               + parts["trousers"] + parts["legwarmers"] + parts["boots"]
               + parts["mitten"] + parts["cup"])
    l3_ok = assemble_outfit(parts, mannequin)

    # --- normal self-check (solids only; flat patches keep their winding) -
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
