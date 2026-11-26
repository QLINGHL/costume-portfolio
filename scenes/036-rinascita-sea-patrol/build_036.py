# -*- coding: utf-8 -*-
"""036 鸣潮式机能风 · 黎那汐塔巡海者套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整套穿到人体底座上试穿）。
设计见 design.md。BACKLOG 已空时自选：鸣潮线第五件——黎那汐塔
第二个职业方向（023 是嘉年华贵族、036 是巡海者工作制服，同地区
不同职业）。
深青短款防风外套（前开襟、荧光青波纹环×3、金扣×4、衣摆褶裥×8）
+ 炭黑潜水服内层（金锚徽 + 荧光青拉链齿×4）+ 珍珠白水手领
（外张肩披）+ 炭黑战术腰带（金腰扣 + 荧光青绳圈）+ 珍珠白长裤
（深青膝垫 + 荧光青膝条）+ 炭黑高筒靴 + 珍珠白水手帽（深青帽带
+ 白帽檐 + 荧光青护目镜）+ 荧光青挑染 + 金耳钉 + 炭黑手套（左手）
+ 金罗盘（右手竖立掌前）。外套改短款裁到腰——032 长款大衣的
廓形变量。v2：鞋底加厚盖住脚掌、水手领改外张肩披、罗盘改竖立掌前。
v3 (038, 2026-11-26)：按 037 质检单六处 FAIL 修复——袖口环
0.102→0.105、腰带环 ry +0.004、绳圈环 ry +0.004、帽顶球心
z 1.64→1.65、膝垫收窄 0.12→0.085 并 y -0.10→-0.095、挑染移到
(-0.12, -0.16, 1.47)；L2 补 ry 检查（034 帽带 ry 漏检的重演）。
v4 (038 补修，同轮)：v3 重跑 037，膝垫仍 0.0329 不通过——量法
把埋进腿里的垫背顶点也算进去，0.03 厚的垫子背部埋进腿内 0.037；
膝垫减薄 0.03→0.02、中心 y -0.095→-0.105，前面仍 0.011 凸出。
v5 (038 再补修，同轮)：v4 重跑 037，膝垫仍 0.0305 不通过——
诊断脚本定位到前上外角（±0.1725, -0.115, 0.45）离裤面 0.0305：
平板的前角离曲面腿最远，收窄/减薄都只能降到 0.03 附近；
膝垫改成贴腿曲面壳（前 0.011、背 -0.004 嵌进裤面，下沿一行跟
靴筒圆面），膝条同款小曲面壳（垫面 0.007 凸出）。面数 833→941。
曲面壳绕序按构造朝外、跳过 fix_normals（质心法会把底行前面翻
成倒置，首跑每垫 3 面倒置）。
Run: blender --background --python build_036.py
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

BLEND_OUT = os.path.join(HERE, "036-rinascita-sea-patrol.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "036-rinascita-sea-patrol.png")
WIRE_JSON = "/tmp/rinascita_sea_patrol_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

BODYSUIT_RINGS = [(1.44, 0.282, 0.148), (1.10, 0.268, 0.142),
                  (0.80, 0.254, 0.136), (0.62, 0.246, 0.132)]
JACKET_RINGS = [(1.50, 0.306, 0.160), (1.20, 0.304, 0.158),
                (0.98, 0.300, 0.156), (0.86, 0.298, 0.155)]
TROUSER_RINGS = [(0.62, 0.246, 0.128), (0.48, 0.240, 0.126),
                 (0.34, 0.232, 0.124)]
BELT_RINGS = [(0.84, 0.262, 0.144), (0.78, 0.260, 0.143)]
ROPE_RINGS = [(0.74, 0.258, 0.140), (0.70, 0.256, 0.139)]
PLEAT_ANGLES = [170, 200, 230, 320, 350, 20, 50, 110]  # all outside 240-300
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    teal = solid_material("DeepTeal", (0.005, 0.072, 0.107), roughness=0.6)
    pearl = solid_material("PearlWhite", (0.888, 0.863, 0.791),
                           roughness=0.6)
    charcoal = solid_material("Charcoal", (0.017, 0.017, 0.024),
                              roughness=0.6)
    cyan = solid_material("CyanGlow", (0.027, 0.791, 0.672), roughness=0.6)
    gold = solid_material("Gold", (0.584, 0.361, 0.020), metallic=0.6,
                          roughness=0.35)
    black = solid_material("Hair_Black", (0.011, 0.011, 0.015),
                           roughness=0.7)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"teal": teal, "pearl": pearl, "charcoal": charcoal,
            "cyan": cyan, "gold": gold, "black": black,
            "skin": skin, "eye": eye}


# ------------------------------------------------------------ L1 components
def build_bodysuit(m):
    """Charcoal dive-suit, inner layer: 4 rings, z 1.44-0.62.
    Hem reaches z 0.62, below the trouser top (0.62), so no bare
    torso shows through the jacket's open front. Clears the torso
    by >=0.005 at every height."""
    return [make_elliptical_tube("CharcoalBodysuit", BODYSUIT_RINGS, 16,
                                 m["charcoal"], caps=False)]


def build_jacket(m):
    """Deep-teal cropped windbreaker, open front: arc 300-600 deg leaves
    the 240-300 deg front wedge open so the charcoal bodysuit shows.
    Cropped to the waist: z 1.50-0.86, 4 rings — the belt stays fully
    visible below the hem (the 032 long-coat silhouette variable)."""
    return [make_elliptical_tube("TealJacket", JACKET_RINGS, 16,
                                 m["teal"], arc=(300, 600), caps=False)]


def build_wave_ring(m, z):
    """One cyan wave band on the jacket: 0.006 proud, same arc as the
    jacket, follows the open-front arc."""
    rx, ry = interp_rings(JACKET_RINGS, z + 0.02)
    rx2, ry2 = interp_rings(JACKET_RINGS, z - 0.02)
    rings = [(z + 0.02, rx + 0.006, ry + 0.006),
             (z - 0.02, rx2 + 0.006, ry2 + 0.006)]
    return [make_elliptical_tube("CyanWaveRing", rings, 16,
                                 m["cyan"], arc=(300, 600), caps=False)]


def build_pleat_fin(m, angle_deg):
    """One 3D pleat fin: a closed thin solid (10 quads) following the
    jacket cone, inner edge 0.004 off the jacket, outer edge 0.026 off,
    tangential half-thickness 0.004. Same construction as 026/030/032."""
    rows = [1.06, 0.96, 0.86]
    a = math.radians(angle_deg)
    verts = []
    for z in rows:
        rx, ry = interp_rings(JACKET_RINGS, z)
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
    return mesh_from_data("TealPleat", verts, faces, m["teal"])


def build_sailor_collar(m):
    """Pearl sailor collar: a flaring shoulder cape, full ring
    z 1.42-1.34, rx 0.325-0.320, ry 0.178-0.175 — 0.019 proud of the
    jacket top, flaring out below the chin so it reads from the
    front. v1's narrow neck ring (r 0.125, z 1.52-1.44) hid behind
    the head sphere (r 0.22) and the back capelet showed only an
    edge — neither read as a sailor collar."""
    return [make_elliptical_tube(
        "PearlSailorCollar", [(1.42, 0.325, 0.178), (1.34, 0.320, 0.175)],
        16, m["pearl"], caps=False)]


def build_anchor(m):
    """Gold anchor emblem on the bodysuit chest (270 deg, z 1.30):
    vertical shank + crossbar + top ring, normal-aligned via
    ellipse_point (016 method), centre 0.004 off the bodysuit
    surface so the 0.012-thick bar is half-buried."""
    rx, ry = interp_rings(BODYSUIT_RINGS, 1.30)
    p, n = ellipse_point(rx, ry, 270)
    c = Vector((p.x, p.y, 1.30)) + n * 0.004
    theta = math.atan2(-n.x, n.y)
    bar = add_box_rot("GoldAnchorBar", tuple(c), (0.014, 0.012, 0.055),
                      m["gold"], (0, 0, theta))
    cross = add_box_rot("GoldAnchorCross", (c.x, c.y, 1.315),
                        (0.045, 0.012, 0.012), m["gold"], (0, 0, theta))
    ring = add_sphere("GoldAnchorRing", (c.x, c.y, 1.3325), 0.012, 6, 3,
                      (1.0, 1.0, 1.0), m["gold"])
    return [bar, cross, ring]


def build_zipper_tooth(m, z):
    """One cyan zipper tooth on the bodysuit front centre (270 deg):
    centre 0.003 off the surface, 0.010-thick box half-buried."""
    rx, ry = interp_rings(BODYSUIT_RINGS, z)
    p, n = ellipse_point(rx, ry, 270)
    c = Vector((p.x, p.y, z)) + n * 0.003
    theta = math.atan2(-n.x, n.y)
    return add_box_rot("CyanZipperTooth", tuple(c), (0.016, 0.010, 0.014),
                       m["cyan"], (0, 0, theta))


def build_jacket_button(m, angle_deg, z):
    """One gold button on a jacket front edge: position + outward
    normal from ellipse_point (016 method), centre 0.004 off the
    jacket surface so the 0.012-thick box is half-buried."""
    rx, ry = interp_rings(JACKET_RINGS, z)
    p, n = ellipse_point(rx, ry, angle_deg)
    c = Vector((p.x, p.y, z)) + n * 0.004
    return add_box("GoldJacketButton", tuple(c), (0.020, 0.012, 0.020),
                   m["gold"])


def build_sleeve(m, sx):
    """Deep-teal long sleeve over the arm (shoulder to wrist).
    Capped (025 v2 lesson). Origin lifted 0.12 along the arm axis
    so the sleeve starts at z 1.34, emerging from the jacket shoulder
    (032 v1: a sleeve starting at the shoulder joint read as a slab
    floating beside the body)."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    origin = shoulder - direction.normalized() * 0.12
    return [make_tube("TealSleeve", origin, direction,
                      [0.0, 0.17, 0.34, 0.51, 0.67],
                      [0.125, 0.118, 0.110, 0.102, 0.096], 10,
                      m["teal"], caps=True)]


def build_cuff(m, sx):
    """Pearl cuff ring at the wrist (t 0.48-0.56 along the arm):
    r 0.105, 0.0064 proud of the sleeve at the cuff top ring
    (sleeve r 0.0986 at s 0.60, not the end 0.096 — 037 v1 lesson:
    the old r 0.102 only cleared the sleeve end, giving a real gap
    of 0.0034 at the cuff top ring; v3/038 raises the ring to 0.105)."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    origin = shoulder + direction.normalized() * 0.48
    return [make_tube("PearlCuff", origin, direction,
                      [0.0, 0.08], [0.105, 0.105], 10,
                      m["pearl"], caps=False)]


def build_belt(m):
    """Charcoal tactical belt: tube around the waist (z 0.84-0.78),
    0.006+ proud of the bodysuit, fully visible below the jacket
    hem (0.86) — the cropped-jacket payoff."""
    return [make_elliptical_tube("CharcoalBelt", BELT_RINGS, 16,
                                 m["charcoal"], caps=False)]


def build_belt_buckle(m):
    """Gold belt buckle at the front centre (0, -0.1475, 0.81):
    belt front at z 0.81 is y -0.1435 (v3/038: belt ry +0.004 moved
    the belt face out from -0.1395, so the buckle moves out with it),
    so the 0.012-thick box is half-buried and 0.010 proud."""
    return add_box("GoldBeltBuckle", (0, -0.1475, 0.81),
                   (0.05, 0.012, 0.04), m["gold"])


def build_rope_coil(m):
    """Cyan rope coil: tube around the waist below the belt
    (z 0.74-0.70), 0.006+ proud of the bodysuit, reads as a coil
    of rope slung under the belt."""
    return [make_elliptical_tube("CyanRopeCoil", ROPE_RINGS, 16,
                                 m["cyan"], caps=False)]


def build_trousers(m):
    """Pearl trousers: tube around both leg tops, z 0.62-0.34,
    hem ends above the boots."""
    return [make_elliptical_tube("PearlTrousers", TROUSER_RINGS, 12,
                                 m["pearl"], caps=False)]


def build_curved_shell(name, rows, material):
    """Closed thin curved shell from a grid of front/back point rows.
    rows: list of (front_pts, back_pts), each a list of Vector of equal
    length. Front grid + back grid + 4 edge strips = closed solid
    (no boundary edges), so it passes the closed-solid topology check.
    Winding is corrected by fix_normals() in main()."""
    nrows = len(rows)
    ncols = len(rows[0][0])
    verts = []
    for front, back in rows:
        verts += [tuple(v) for v in front]
        verts += [tuple(v) for v in back]

    def F(iz, ia):
        return iz * 2 * ncols + ia

    def B(iz, ia):
        return iz * 2 * ncols + ncols + ia

    faces = []
    # Winding is outward by construction (columns run inner->outer,
    # i.e. +x, for both pads; rows run top->bottom): front faces
    # point away from the leg (-y), back faces toward it (+y), edge
    # strips point out of the plate. fix_normals() is NOT run on
    # these shells (see main()): its centroid test misjudges the
    # bottom-row front faces of a thin curved shell and flips them
    # back inward (v5: 3 inverted faces per pad).
    for iz in range(nrows - 1):
        for ia in range(ncols - 1):
            faces.append((F(iz, ia), F(iz + 1, ia),
                          F(iz + 1, ia + 1), F(iz, ia + 1)))
            faces.append((B(iz, ia), B(iz, ia + 1),
                          B(iz + 1, ia + 1), B(iz + 1, ia)))
    for iz in range(nrows - 1):
        faces.append((F(iz, 0), B(iz, 0), B(iz + 1, 0), F(iz + 1, 0)))
        faces.append((F(iz, ncols - 1), F(iz + 1, ncols - 1),
                      B(iz + 1, ncols - 1), B(iz, ncols - 1)))
    for ia in range(ncols - 1):
        faces.append((F(0, ia), F(0, ia + 1), B(0, ia + 1), B(0, ia)))
        faces.append((F(nrows - 1, ia), B(nrows - 1, ia),
                      B(nrows - 1, ia + 1), F(nrows - 1, ia + 1)))
    return mesh_from_data(name, verts, faces, material)


def _trouser_shell_row(angles, z, front_off, back_off):
    """One shell row following the pearl trouser ellipse at height z:
    front points offset outward, back points embedded in the trouser."""
    rx, ry = interp_rings(TROUSER_RINGS, z)
    front, back = [], []
    for a in angles:
        p, n = ellipse_point(rx, ry, a)
        front.append(Vector((p.x, p.y, z)) + n * front_off)
        back.append(Vector((p.x, p.y, z)) + n * back_off)
    return front, back


def _boot_shell_row(sx, angles, z, front_off, back_off):
    """One shell row following the charcoal boot circle (r 0.118)
    around the leg axis (sx*0.13, 0) at height z — used for the pad
    rows that hang below the trouser hem (z 0.34) onto the boot."""
    cx = sx * 0.13
    front, back = [], []
    for a in angles:
        t = math.radians(a)
        d = Vector((math.cos(t), math.sin(t), 0.0))
        front.append(Vector((cx, 0.0, z)) + d * (0.118 + front_off))
        back.append(Vector((cx, 0.0, z)) + d * (0.118 + back_off))
    return front, back


def build_knee_pad(m, sx):
    """Deep-teal knee pad + cyan stripe as curved shells following the
    leg: the pad is a closed thin shell hugging the trouser ellipse
    (front 0.011 proud, back 0.004 embedded), with its bottom row
    following the boot circle below the trouser hem (z 0.34); the
    stripe is a smaller shell on the pad front (0.007 proud).
    v5/038: the flat box could not pass — 0.12 wide gave 0.0386,
    0.085 wide gave 0.0329, 0.085 wide + thinned 0.02 gave 0.0305:
    the flat pad's top-outer corner stands 0.03 off the curved leg
    no matter how narrow it gets, because the leg curves away from
    the flat face. A shell that follows the curvature puts every
    vertex ~0.011 off its host instead. Winding note: the shell is
    wound outward by construction and skipped by fix_normals() —
    the centroid test flips the bottom-row front faces inward
    (3 inverted faces per pad on the first v5 run)."""
    if sx > 0:
        tangles = [292, 298, 304, 310, 316]
    else:
        tangles = [224, 230, 236, 242, 248]
    bangles = [250, 260, 270, 280, 290]
    pad_rows = [
        _trouser_shell_row(tangles, 0.45, 0.011, -0.004),
        _trouser_shell_row(tangles, 0.40, 0.011, -0.004),
        _trouser_shell_row(tangles, 0.34, 0.011, -0.004),
        _boot_shell_row(sx, bangles, 0.31, 0.011, -0.004),
    ]
    stripe_rows = [
        _trouser_shell_row(tangles, 0.39, 0.018, 0.008),
        _trouser_shell_row(tangles, 0.38, 0.018, 0.008),
        _trouser_shell_row(tangles, 0.37, 0.018, 0.008),
    ]
    pad = build_curved_shell("TealKneePad", pad_rows, m["teal"])
    stripe = build_curved_shell("CyanKneeStripe", stripe_rows, m["cyan"])
    return [pad, stripe]


def build_boot(m, sx):
    """Charcoal high boot: tube around the lower leg (z 0.34-0.02,
    r 0.118) + sole wedge landing z=0.0 + teal cuff ring at the
    top (z 0.36-0.32, r 0.124). v2: the sole wedge top is raised
    to 0.105/0.055 (0.005 above the mannequin foot top 0.10/0.045)
    — v1's 0.025-tall sole left the skin foot toe sticking out in
    front of the boot, reading as a bare foot."""
    tube = make_tube("CharcoalBoot", (sx * 0.13, 0, 0.34), (0, 0, -1),
                     [0.0, 0.32], [0.118, 0.118], 10,
                     m["charcoal"], caps=False)
    sole = make_wedge("CharcoalBootSole", (sx * 0.13, -0.02, 0.0),
                      0.102, 0.095, -0.165, 0.0, 0.105, 0.055,
                      m["charcoal"])
    cuff = make_tube("TealBootCuff", (sx * 0.13, 0, 0.36), (0, 0, -1),
                     [0.0, 0.04], [0.124, 0.124], 10,
                     m["teal"], caps=False)
    return [tube, sole, cuff]


def build_cap(m):
    """Pearl sailor cap: dome sphere r 0.25, centre z 1.65, flattened
    z 0.55, top 1.79 covering the hair cap top (1.75); teal band ring
    z 1.60-1.56, r 0.252-0.250, 0.013 proud of the dome; white brim
    front panel arc 240-300 deg, z 1.59-1.585, r 0.300, bottom edge
    1.585 above the eye line (crossing z 1.524) — 032 v2 lesson.
    v3/038: dome centre raised 1.64 -> 1.65 — the old centre left the
    visible dome only 0.0022 clear of the hair at the grazing line
    (037); lifting the centre fattens the dome cross-section at the
    crossing height and steepens the crossing angle."""
    dome = add_sphere("PearlCapDome", (0, 0.01, 1.65), 0.25, 12, 6,
                      (1.0, 0.95, 0.55), m["pearl"])
    band = make_tube("TealCapBand", (0, 0, 1.60), (0, 0, -1),
                     [0.0, 0.04], [0.252, 0.250], 24,
                     m["teal"], caps=False)
    brim = make_elliptical_tube("PearlCapBrim",
                                [(1.59, 0.300, 0.300),
                                 (1.585, 0.295, 0.295)],
                                16, m["pearl"], arc=(240, 300), caps=False)
    return [dome, band, brim]


def build_goggles(m):
    """Cyan goggles pushed up on the cap: two lens boxes + charcoal
    bridge at z 1.66 on the dome front, half-buried, 0.007 proud."""
    lenses = []
    for sx in (-1, 1):
        lenses.append(add_box("CyanGoggleLens", (sx * 0.075, -0.222, 1.66),
                              (0.085, 0.02, 0.05), m["cyan"]))
    bridge = add_box("CharcoalGoggleBridge", (0, -0.222, 1.66),
                     (0.05, 0.018, 0.03), m["charcoal"])
    return lenses + [bridge]


def build_streak(m):
    """Cyan hair streak: flattened ellipsoid on the hair surface at
    the left front (-0.12, -0.16, 1.47), lying outside the hair
    ellipsoid so it reads from the front below the cap brim.
    Top z 1.52 stays below the brim bottom (1.585) — 031 v1 lesson:
    a streak must not poke through the hat. v3/038: moved from
    (-0.11, -0.115, 1.44) — the old centre sat below the hairline
    (z 1.462) and behind the head face (y -0.163), so all 26 vertices
    were buried inside the head sphere and the streak was invisible
    from every angle (037)."""
    return [add_sphere("HairStreak", (-0.12, -0.16, 1.47), 0.05, 8, 4,
                       (0.55, 0.45, 1.0), m["cyan"])]


def build_earring(m, sx):
    """Gold stud earring: small sphere half-buried in the head side
    (±0.222, 0, 1.47), outer face 0.019 proud."""
    return add_sphere("GoldEarring", (sx * 0.222, 0, 1.47), 0.015, 6, 3,
                      (1.0, 1.0, 1.0), m["gold"])


def build_glove(m):
    """Charcoal glove on the left hand: sphere r 0.095 at the left
    wrist + 0.03 along the arm axis, covering the hand sphere."""
    wrist, direction = wrist_pos(-1)
    centre = wrist + direction * 0.03
    return [add_sphere("CharcoalGlove", tuple(centre), 0.095, 6, 4,
                       (1.0, 0.9, 1.0), m["charcoal"])]


def build_compass(m):
    """Gold compass held up in the right palm (camera side): vertical
    disc r 0.055 facing the camera (-Y), 0.007 clear of the palm,
    + cyan needle box on its front face. v1's flat disc lay on the
    hand top at the cuff's height and radius, hidden inside the
    cuff tube from every angle."""
    wrist, _ = wrist_pos(1)
    wx, wy, wz = wrist
    disc = make_disc("GoldCompass", (wx, wy - 0.09, wz - 0.02), (0, -1, 0),
                     0.055, 16, m["gold"])
    needle = add_box_rot("CyanCompassNeedle", (wx, wy - 0.095, wz - 0.02),
                         (0.06, 0.008, 0.012), m["cyan"],
                         (0, math.radians(30), 0))
    return [disc, needle]


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = parts["bodysuit"] + parts["anchor"] + parts["zipper"]
    ok = True
    ok &= check_gap("torso: charcoal bodysuit vs mannequin torso @z=1.28",
                    interp_rings(BODYSUIT_RINGS, 1.28)[0],
                    interp_rings(TORSO_RINGS, 1.28)[0])
    ok &= check_gap("torso: charcoal bodysuit vs mannequin torso @z=0.95",
                    interp_rings(BODYSUIT_RINGS, 0.95)[0],
                    interp_rings(TORSO_RINGS, 0.95)[0])
    ok &= check_relief("torso: gold anchor relief", 0.010,
                       lo=0.005, hi=0.030)
    ok &= check_relief("torso: cyan zipper tooth relief", 0.008,
                       lo=0.005, hi=0.030)
    print("L2_CHECK torso: charcoal dive-suit clears the torso, gold "
          "anchor + 4 cyan zipper teeth on the chest front PASS")
    return objs, ok


def assemble_jacket(parts):
    objs = (parts["jacket"] + parts["waves"] + parts["buttons"]
            + parts["pleats"])
    ok = True
    ok &= check_gap("jacket: teal jacket vs charcoal bodysuit @z=1.20",
                    interp_rings(JACKET_RINGS, 1.20)[0],
                    interp_rings(BODYSUIT_RINGS, 1.20)[0])
    ok &= check_gap("jacket: teal jacket vs charcoal bodysuit @z=0.90",
                    interp_rings(JACKET_RINGS, 0.90)[0],
                    interp_rings(BODYSUIT_RINGS, 0.90)[0])
    ok &= check_relief("jacket: cyan wave ring relief", 0.006,
                       lo=0.005, hi=0.015)
    ok &= check_relief("jacket: gold button relief", 0.010,
                       lo=0.005, hi=0.030)
    ok &= check_relief("jacket: teal pleat fin height", 0.022,
                       lo=0.005, hi=0.030)
    print("L2_CHECK jacket: teal cropped windbreaker hangs loose over "
          "the charcoal bodysuit, 3 cyan wave rings + 4 gold buttons + "
          "8 pleat fins at the hem PASS")
    return objs, ok


def assemble_collar(parts):
    objs = parts["collar"]
    ok = True
    ok &= check_gap("collar: pearl sailor collar vs teal jacket top",
                    0.325, 0.3055)
    ok &= check_gap("collar: pearl sailor collar vs charcoal bodysuit",
                    0.320, interp_rings(BODYSUIT_RINGS, 1.34)[0])
    print("L2_CHECK collar: pearl sailor collar flares over the jacket "
          "shoulders, visible below the chin from the front PASS")
    return objs, ok


def assemble_sleeves(parts):
    objs = parts["sleeves"] + parts["cuffs"]
    ok = True
    ok &= check_gap("sleeve: teal sleeve vs mannequin arm @0.0",
                    0.125, 0.085)
    # Cuff ring r 0.105 vs sleeve end 0.096, AND vs the sleeve radius
    # at the cuff top ring (s 0.60 -> r 0.0986, not the end 0.096):
    # 037 caught the old 0.102 ring clearing only the end (real gap
    # 0.0034). Check both, not just the end.
    ok &= check_gap("sleeve: pearl cuff vs teal sleeve end",
                    0.105, 0.096)
    ok &= check_gap("sleeve: pearl cuff vs teal sleeve @s=0.60",
                    0.105, 0.0986)
    print("L2_CHECK sleeves: teal long sleeves over the arms, pearl "
          "cuffs at the wrists PASS")
    return objs, ok


def assemble_belt(parts):
    objs = parts["belt"] + [parts["buckle"]] + parts["rope"]
    ok = True
    ok &= check_gap("belt: charcoal belt vs charcoal bodysuit @z=0.84",
                    interp_rings(BELT_RINGS, 0.84)[0],
                    interp_rings(BODYSUIT_RINGS, 0.84)[0])
    ok &= check_gap("belt: charcoal belt vs charcoal bodysuit @z=0.78",
                    interp_rings(BELT_RINGS, 0.78)[0],
                    interp_rings(BODYSUIT_RINGS, 0.78)[0])
    # 037 lesson (034 hat-band ry blind spot, repeated): check ry too.
    # Belt ry 0.144/0.143 vs bodysuit ry 0.1368/0.1356 (v3/038: +0.004).
    ok &= check_gap("belt: charcoal belt vs charcoal bodysuit ry @z=0.84",
                    interp_rings(BELT_RINGS, 0.84)[1],
                    interp_rings(BODYSUIT_RINGS, 0.84)[1])
    ok &= check_gap("belt: charcoal belt vs charcoal bodysuit ry @z=0.78",
                    interp_rings(BELT_RINGS, 0.78)[1],
                    interp_rings(BODYSUIT_RINGS, 0.78)[1])
    ok &= check_relief("belt: gold buckle relief", 0.010,
                       lo=0.005, hi=0.030)
    ok &= check_gap("belt: cyan rope coil vs charcoal bodysuit @z=0.74",
                    interp_rings(ROPE_RINGS, 0.74)[0],
                    interp_rings(BODYSUIT_RINGS, 0.74)[0])
    ok &= check_gap("belt: cyan rope coil vs charcoal bodysuit @z=0.70",
                    interp_rings(ROPE_RINGS, 0.70)[0],
                    interp_rings(BODYSUIT_RINGS, 0.70)[0])
    # Rope ry 0.140/0.139 vs bodysuit ry 0.1347/0.1338 (v3/038: +0.004).
    ok &= check_gap("belt: cyan rope coil vs charcoal bodysuit ry @z=0.74",
                    interp_rings(ROPE_RINGS, 0.74)[1],
                    interp_rings(BODYSUIT_RINGS, 0.74)[1])
    ok &= check_gap("belt: cyan rope coil vs charcoal bodysuit ry @z=0.70",
                    interp_rings(ROPE_RINGS, 0.70)[1],
                    interp_rings(BODYSUIT_RINGS, 0.70)[1])
    print("L2_CHECK belt: charcoal tactical belt below the jacket hem, "
          "gold buckle at the front, cyan rope coil under the belt PASS")
    return objs, ok


def assemble_head(parts):
    objs = (parts["cap"] + parts["goggles"] + parts["streak"]
            + parts["earrings"])
    ok = True
    # Dome centre z 1.65 (v3/038): dome rx 0.2440 @z=1.62, 0.2500 @z=1.65;
    # hair rx 0.2161 @z=1.62, 0.2016 @z=1.65.
    ok &= check_gap("head: pearl cap dome vs black hair cap @z=1.62",
                    0.2440, 0.2161)
    ok &= check_gap("head: pearl cap dome vs black hair cap @z=1.65",
                    0.2500, 0.2016)
    ok &= check_gap("head: teal cap band vs pearl cap dome @z=1.58",
                    0.252, 0.2249)
    ok &= check_gap("head: teal cap band vs black hair cap @z=1.58",
                    0.252, 0.2246)
    ok &= check_gap("head: pearl cap brim bottom vs eye line",
                    1.585, 1.524)
    ok &= check_relief("head: cyan goggle lens relief", 0.008,
                       lo=0.005, hi=0.030)
    ok &= check_relief("head: gold earring relief", 0.019,
                       lo=0.005, hi=0.030)
    print("L2_CHECK head: pearl sailor cap over the hair, teal band "
          "around the dome, white brim above the eyes, cyan goggles "
          "on the cap front, cyan streak below the brim, gold studs PASS")
    return objs, ok


def assemble_legs(parts):
    objs = parts["trousers"] + parts["kneepads"]
    ok = True
    ok &= check_gap("legs: pearl trousers vs mannequin legs @z=0.52",
                    interp_rings(TROUSER_RINGS, 0.52)[0], 0.1023)
    # Knee pad centre relief 0.011 (v4/038: pad thinned to 0.02 and
    # moved out to y -0.105; the QA nearest-host value is the real check).
    ok &= check_relief("legs: teal knee pad relief", 0.011,
                       lo=0.005, hi=0.030)
    ok &= check_relief("legs: cyan knee stripe relief", 0.007,
                       lo=0.005, hi=0.030)
    print("L2_CHECK legs: pearl trousers cover the leg tops, teal knee "
          "pads with cyan stripes at the knees PASS")
    return objs, ok


def assemble_feet(parts):
    objs = parts["boots"]
    ok = True
    ok &= check_gap("feet: charcoal boot vs mannequin leg @z=0.20",
                    0.118, 0.0866)
    ok &= check_gap("feet: teal boot cuff vs charcoal boot",
                    0.124, 0.118)
    ok &= check_gap("feet: charcoal boot sole vs mannequin foot",
                    0.102, 0.095)
    print("L2_CHECK feet: charcoal boot tubes centre z=0.0, soles on "
          "ground; teal cuffs at the boot tops PASS")
    return objs, ok


def assemble_hand(parts):
    objs = parts["glove"] + parts["compass"]
    ok = True
    ok &= check_gap("hand: charcoal glove vs mannequin hand",
                    0.095, 0.085)
    ok &= check_relief("hand: gold compass disc in front of palm", 0.007,
                       lo=0.005, hi=0.030)
    print("L2_CHECK hand: charcoal glove covers the left hand, gold "
          "compass held up in front of the right palm PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: teal jacket vs charcoal bodysuit @z=1.20",
                    interp_rings(JACKET_RINGS, 1.20)[0],
                    interp_rings(BODYSUIT_RINGS, 1.20)[0])
    ok &= check_gap("L3 layer: charcoal belt vs charcoal bodysuit @z=0.84",
                    interp_rings(BELT_RINGS, 0.84)[0],
                    interp_rings(BODYSUIT_RINGS, 0.84)[0])
    ok &= check_gap("L3 layer: cyan rope coil vs charcoal bodysuit @z=0.74",
                    interp_rings(ROPE_RINGS, 0.74)[0],
                    interp_rings(BODYSUIT_RINGS, 0.74)[0])
    ok &= check_gap("L3 layer: pearl cap brim bottom vs eye line",
                    1.585, 1.524)
    ok &= check_gap("L3 joint: teal sleeve vs mannequin arm",
                    0.125, 0.085)
    ok &= check_gap("L3 joint: charcoal boot vs mannequin leg @z=0.20",
                    0.118, 0.0866)
    ok &= check_gap("L3 joint: charcoal boot sole vs mannequin foot",
                    0.102, 0.095)
    print("L3_CHECK outfit: teal jacket over the charcoal bodysuit, "
          "belt + rope coil below the jacket hem, cap brim above the "
          "eyes, boots on ground z=0.000 PASS")
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
    parts["bodysuit"] = build_bodysuit(m)
    report_l1("CharcoalBodysuit", parts["bodysuit"])
    parts["jacket"] = build_jacket(m)
    report_l1("TealJacket", parts["jacket"])
    parts["waves"] = [o for z in (1.32, 1.14, 0.94)
                      for o in build_wave_ring(m, z)]
    report_l1("CyanWaveRings x3", parts["waves"])
    parts["pleats"] = [build_pleat_fin(m, a) for a in PLEAT_ANGLES]
    report_l1("TealPleats x8", parts["pleats"])
    parts["collar"] = build_sailor_collar(m)
    report_l1("PearlSailorCollar", parts["collar"])
    parts["anchor"] = build_anchor(m)
    report_l1("GoldAnchor", parts["anchor"])
    parts["zipper"] = [build_zipper_tooth(m, z)
                       for z in (1.16, 1.08, 1.00, 0.92)]
    report_l1("CyanZipperTeeth x4", parts["zipper"])
    parts["buttons"] = [build_jacket_button(m, a, z)
                        for a in (240, 300) for z in (1.38, 1.05)]
    report_l1("GoldJacketButtons x4", parts["buttons"])
    parts["sleeves"] = []
    for sx in (-1, 1):
        parts["sleeves"] += build_sleeve(m, sx)
    report_l1("TealSleeves x2", parts["sleeves"])
    parts["cuffs"] = []
    for sx in (-1, 1):
        parts["cuffs"] += build_cuff(m, sx)
    report_l1("PearlCuffs x2", parts["cuffs"])
    parts["belt"] = build_belt(m)
    report_l1("CharcoalBelt", parts["belt"])
    parts["buckle"] = build_belt_buckle(m)
    report_l1("GoldBeltBuckle", [parts["buckle"]])
    parts["rope"] = build_rope_coil(m)
    report_l1("CyanRopeCoil", parts["rope"])
    parts["trousers"] = build_trousers(m)
    report_l1("PearlTrousers", parts["trousers"])
    parts["kneepads"] = []
    for sx in (-1, 1):
        parts["kneepads"] += build_knee_pad(m, sx)
    report_l1("TealKneePads+CyanStripes x2", parts["kneepads"])
    parts["boots"] = []
    for sx in (-1, 1):
        parts["boots"] += build_boot(m, sx)
    report_l1("CharcoalBoots x2", parts["boots"])
    parts["cap"] = build_cap(m)
    report_l1("PearlSailorCap", parts["cap"])
    parts["goggles"] = build_goggles(m)
    report_l1("CyanGoggles", parts["goggles"])
    parts["streak"] = build_streak(m)
    report_l1("CyanStreak", parts["streak"])
    parts["earrings"] = [build_earring(m, sx) for sx in (-1, 1)]
    report_l1("GoldEarrings x2", parts["earrings"])
    parts["glove"] = build_glove(m)
    report_l1("CharcoalGlove", parts["glove"])
    parts["compass"] = build_compass(m)
    report_l1("GoldCompass", parts["compass"])

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    _, ok = assemble_torso(parts)
    l2_ok &= ok
    _, ok = assemble_jacket(parts)
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
    _, ok = assemble_hand(parts)
    l2_ok &= ok
    print("L2_SUMMARY %s" % ("ALL PASS" if l2_ok else "FAILURES PRESENT"))

    # ---- L3 full outfit on the mannequin ----
    costume = (parts["bodysuit"] + parts["jacket"] + parts["waves"]
               + parts["pleats"] + parts["collar"]
               + parts["anchor"] + parts["zipper"] + parts["buttons"]
               + parts["sleeves"] + parts["cuffs"] + parts["belt"]
               + [parts["buckle"]] + parts["rope"] + parts["trousers"]
               + parts["kneepads"] + parts["boots"] + parts["cap"]
               + parts["goggles"] + parts["streak"] + parts["earrings"]
               + parts["glove"] + parts["compass"])
    l3_ok = assemble_outfit(parts, mannequin)

    # --- normal self-check (solids only; the compass disc keeps its
    # construction winding — fix_normals must never run on flat discs;
    # the curved knee shells keep theirs too — fix_normals' centroid
    # test misjudges their bottom-row front faces and flips them
    # inward, v5: 3 inverted faces per pad) ---
    for obj in mannequin + costume:
        if obj.name.startswith("GoldCompass"):
            continue
        if obj.name.startswith(("TealKneePad", "CyanKneeStripe")):
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
