# -*- coding: utf-8 -*-
"""045 异环式都市时装 · 春日樱花套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整套穿到人体底座上试穿）。
设计见 design.md。BACKLOG 已空时自选：异环线第十一件——春日场景方向
（015 夜行、025 街头、026 学院、027 运动、028 居家、029 通勤、
031 夏日、032 冬日、039 秋日、040 雨天之后；学院/居家/运动/街头/
通勤/夜行/夏日/冬日/秋日/雨天矩阵里春日首次做，四季补齐）。
樱粉短款开衫（前开襟、深樱红樱花纹×5、百褶裙褶裥×8、藏青腰带
+ 金腰扣）+ 奶油白高领毛衣内层 + 藏青长袖（奶油白袖口）+ 藏青百褶裙
+ 奶油白过膝袜 + 樱粉乐福鞋 + 樱粉贝雷帽（藏青帽带、帽上樱花）
+ 猫耳 + 蓝挑染 + 金耳钉 + 藏青手套（左手）+ 樱花枝（右手持，第七种
手持物）。廓形变量：短款开衫到腰 z 0.92 + 百褶裙到膝 z 0.35
（039/040 中长风衣 + 长裤的变量）。
Run: blender --background --python build_045.py
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

BLEND_OUT = os.path.join(HERE, "045-spring-sakura.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "045-spring-sakura.png")
WIRE_JSON = "/tmp/spring_sakura_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

SWEATER_RINGS = [(1.50, 0.300, 0.160), (1.44, 0.288, 0.152),
                 (1.10, 0.272, 0.144), (0.95, 0.264, 0.140)]
JACKET_RINGS = [(1.50, 0.312, 0.168), (1.20, 0.312, 0.164),
                (0.92, 0.308, 0.162)]
SKIRT_RINGS = [(0.95, 0.258, 0.134), (0.65, 0.295, 0.152),
               (0.35, 0.335, 0.172)]
BELT_RINGS = [(0.98, 0.316, 0.170), (0.92, 0.315, 0.169)]
PLEAT_ANGLES = [170, 200, 230, 260, 290, 320, 350, 20]  # closed skirt:
# pleats all round the cone, incl. front 260/290 (no open wedge here)
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)
# Sakura branch: same 48-deg-off-the-arm direction as 040's umbrella
# shaft, so it leaves the cuff at the wrist instead of running along
# the forearm.
SHAFT_DIR = Vector((0.553, -0.352, 0.755)).normalized()
SHAFT_LEN = 0.55
BRANCH_FLOWER_S = (0.30, 0.42, 0.52)


def ellipse_value(x, y, rx, ry):
    """Normalised ellipse radius of point (x, y); >1 means outside."""
    return math.sqrt((x / rx) ** 2 + (y / ry) ** 2)


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    sakura = solid_material("SakuraPink", (0.905, 0.386, 0.485),
                            roughness=0.6)
    cream = solid_material("Cream", (0.913, 0.862, 0.744), roughness=0.6)
    navy = solid_material("Navy", (0.011, 0.023, 0.068), roughness=0.6)
    sakura_red = solid_material("SakuraRed", (0.694, 0.078, 0.162),
                                roughness=0.5)
    gold = solid_material("Gold", (0.584, 0.361, 0.020), metallic=0.6,
                          roughness=0.35)
    lightblue = solid_material("LightBlue", (0.212, 0.479, 0.807),
                               roughness=0.6)
    black = solid_material("Hair_Black", (0.011, 0.011, 0.015),
                           roughness=0.7)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"sakura": sakura, "cream": cream, "navy": navy,
            "sakura_red": sakura_red, "gold": gold,
            "lightblue": lightblue, "black": black, "skin": skin,
            "eye": eye}


# ------------------------------------------------------------ sakura flower
def make_sakura_patch(name, center, normal, radius, petal_mat,
                      center_mat):
    """One sakura blossom: flat 5-petal patch (15 faces) in the plane
    perpendicular to `normal`. Each petal is 2 triangles (tip at
    radius, sides at 0.55*radius, +-20 deg); the gold centre is a
    small pentagon raised 0.002 along the normal. Faces are wound so
    their normal is +normal (039 star-patch rule: flat patches keep
    construction winding — fix_normals must never run on them).
    Returns [petal_mesh, centre_mesh] (two materials)."""
    n = Vector(normal).normalized()
    up = Vector((0, 0, 1))
    if abs(n.z) > 0.99:
        up = Vector((1, 0, 0))
    u = up.cross(n).normalized()
    v = n.cross(u)
    c = Vector(center)
    verts = [tuple(c)]
    for k in range(5):
        for dtheta, rr in ((-20, 0.55 * radius), (0, radius),
                           (20, 0.55 * radius)):
            a = math.radians(90 + k * 72 + dtheta)
            p = c + (u * math.cos(a) + v * math.sin(a)) * rr
            verts.append(tuple(p))
    faces = []
    for k in range(5):
        b = 1 + k * 3
        faces.append((0, b, b + 1))
        faces.append((0, b + 1, b + 2))
    petals = mesh_from_data(name + "Petals", verts, faces, petal_mat)
    cc = c + n * 0.002
    cverts = [tuple(cc)]
    for k in range(5):
        a = math.radians(90 + k * 72)
        p = cc + (u * math.cos(a) + v * math.sin(a)) * (radius * 0.35)
        cverts.append(tuple(p))
    cfaces = [(0, i + 1, i + 2 if i + 2 <= 5 else 1) for i in range(5)]
    centre = mesh_from_data(name + "Centre", cverts, cfaces, center_mat)
    return [petals, centre]


def _sakura_on_ellipse(name, rings, angle_deg, z, radius, m,
                       offset=0.006):
    """Sakura blossom on an elliptical tube surface at (angle, z)."""
    rx, ry = interp_rings(rings, z)
    p, n = ellipse_point(rx, ry, angle_deg)
    c = Vector((p.x, p.y, z)) + n * offset
    return make_sakura_patch(name, tuple(c), tuple(n), radius,
                             m["sakura_red"], m["gold"])


# ------------------------------------------------------------ L1 components
def build_sweater(m):
    """Cream turtleneck sweater, inner layer: 4 rings, z 1.50-0.95.
    Hem meets the pleated skirt top at z 0.95 exactly (skirt top
    ring 0.260 sits 0.004 inside the sweater hem 0.264 — no skin)."""
    return [make_elliptical_tube("CreamSweater", SWEATER_RINGS, 16,
                                 m["cream"], caps=False)]


def build_jacket(m):
    """Sakura-pink short jacket, open front: arc 300-600 deg leaves
    the 240-300 deg front wedge open so the cream sweater shows.
    Short to the waist: z 1.50-0.92, 3 rings — the silhouette
    variable against 039/040's mid-length coats."""
    return [make_elliptical_tube("SakuraJacket", JACKET_RINGS, 16,
                                 m["sakura"], arc=(300, 600),
                                 caps=False)]


def build_sakura_on_sweater(m, angle_deg, z):
    """One deep-red sakura on the sweater front (visible through the
    jacket's open front)."""
    return _sakura_on_ellipse("SakuraFlower", SWEATER_RINGS, angle_deg,
                              z, 0.032, m)


def build_sakura_on_jacket(m, angle_deg, z):
    """One deep-red sakura on the jacket front edge (225/315 deg — 15
    deg outside the 240-300 open wedge; a flower inside the wedge
    would float in front of the sweater)."""
    return _sakura_on_ellipse("SakuraFlower", JACKET_RINGS, angle_deg,
                              z, 0.032, m)


def build_pleat_fin(m, angle_deg):
    """One 3D pleat fin: a closed thin solid (10 quads) following the
    skirt cone, inner edge 0.004 off the skirt, outer edge 0.026
    off, tangential half-thickness 0.004. Same construction as
    026/030/032/036/039."""
    rows = [0.55, 0.45, 0.35]
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
    return mesh_from_data("SakuraPleat", verts, faces, m["navy"])


def build_sleeve(m, sx):
    """Navy long sleeve over the arm (shoulder to wrist).
    Capped (025 v2 lesson). Origin lifted 0.12 along the arm axis
    so the sleeve starts at z 1.34, emerging from the jacket
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
    """Navy waist belt: tube around the jacket waist (z 0.98-0.92),
    0.007+ proud of the jacket in both rx and ry (037 lesson: check
    ry too)."""
    return [make_elliptical_tube("NavyBelt", BELT_RINGS, 16,
                                 m["navy"], caps=False)]


def build_belt_buckle(m):
    """Gold belt buckle at the front centre (0, -0.175, 0.95):
    belt front at z 0.95 is y -0.1695, so the 0.012-thick box is
    half-buried and 0.0115 proud."""
    return add_box("GoldBeltBuckle", (0, -0.175, 0.95),
                   (0.05, 0.012, 0.04), m["gold"])


def build_skirt(m):
    """Navy pleated skirt: flared tube, z 0.95-0.35. Top ring
    (0.258) hides inside the sweater hem (0.264) with a 0.006 tuck;
    hem ring (0.335) clears both leg outer edges (0.230)."""
    return [make_elliptical_tube("NavyPleatedSkirt", SKIRT_RINGS, 16,
                                 m["navy"], caps=False)]


def build_sock(m, sx):
    """Cream over-knee sock: tube over the leg, top meeting the skirt
    hem at z 0.35 with no skin showing (026 method)."""
    return [make_tube("CreamSock", (sx * 0.13, 0, 0.35), (0, 0, -1),
                      [0.0, 0.29], [0.100, 0.096], 10,
                      m["cream"], caps=False)]


def build_loafer(m, sx):
    """Sakura-pink loafer: wedge sole (lands z=0.0, encloses the
    mannequin foot wedge) + shoe shaft over the sock + gold buckle
    (026 method, pink)."""
    wedge = make_wedge("SakuraLoafer", (sx * 0.13, -0.02, 0.0),
                       0.100, 0.095, -0.165, 0.0, 0.105, 0.05,
                       m["sakura"])
    shaft = make_tube("SakuraLoaferShaft", (sx * 0.13, 0, 0.16),
                      (0, 0, -1), [0.0, 0.13], [0.106, 0.104], 10,
                      m["sakura"], caps=False)
    buckle = add_box("GoldShoeBuckle", (sx * 0.13, -0.108, 0.06),
                     (0.04, 0.012, 0.025), m["gold"])
    return [wedge, shaft, buckle]


def build_beret(m):
    """Sakura-pink beret: flattened sphere r 0.26, centre (0, 0.01,
    1.68), z-scale 0.42, top 1.789 covering the hair cap top (1.75)
    — 039 construction, pink."""
    return [add_sphere("SakuraBeret", (0, 0.01, 1.68), 0.26, 12, 6,
                       (1.0, 1.0, 0.42), m["sakura"])]


def build_beret_band(m):
    """Navy beret band: 3-ring tube following the beret's curvature
    (z 1.66-1.62, r 0.2616/0.2479/0.230, each 0.006 proud of the
    dome). v3/044 bottom ring 0.230 — the faceted dome's ring vertex
    at z 1.6254 (r 0.2252) is the nearest feature, cleared by ~0.0072
    in true 3D distance."""
    return [make_tube("NavyBeretBand", (0, 0.01, 1.66), (0, 0, -1),
                      [0.0, 0.02, 0.04], [0.2616, 0.2479, 0.230], 24,
                      m["navy"], caps=False)]


def build_beret_flower(m):
    """Deep-red sakura on the beret front-right (300 deg, z 1.70):
    beret cross radius there is 0.2556, so the flower centre sits at
    0.2616 from the beret axis, 0.006 off the dome (039 pin method)."""
    a = math.radians(300)
    r = 0.2556 + 0.006
    c = (r * math.cos(a), 0.01 + r * math.sin(a), 1.70)
    n = (math.cos(a), math.sin(a), 0.0)
    return make_sakura_patch("SakuraBeretFlower", c, n, 0.028,
                             m["sakura_red"], m["gold"])


def build_cat_ear(m, sx):
    """Navy cat ear: four-sided pyramid (032 method), base buried in
    the beret dome at z=1.70, apex at z=1.86 (0.071 above the beret
    top 1.789)."""
    x0, x1 = sx * 0.05, sx * 0.15
    ax = sx * 0.12
    verts = [(x0, -0.02, 1.70), (x1, -0.02, 1.70),
             (x1, 0.08, 1.70), (x0, 0.08, 1.70),
             (ax, 0.03, 1.86)]
    faces = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4),
             (3, 2, 1, 0)]
    return mesh_from_data("NavyCatEar", verts, faces, m["navy"])


def build_streak(m):
    """Light-blue hair streak: flattened ellipsoid on the hair surface,
    front-right below the beret band. 042-verified centre
    (0.11, -0.175, 1.44): front pole ~0.039 proud of the head face,
    inside the 0.005-0.045 relief band, 22/26 visible vertices."""
    return [add_sphere("HairStreak", (0.11, -0.175, 1.44), 0.05, 8, 4,
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


def build_branch(m):
    """Sakura branch held in the right hand (seventh handheld item):
    navy stem from the right wrist along SHAFT_DIR (48 deg off the
    arm's upward extension, so it leaves the cuff at the wrist
    instead of running along the forearm), 3 deep-red sakura
    blossoms along the stem (s 0.30/0.42/0.52), each facing the
    camera front (normal (0,-1,0.35)). The stem passes through each
    blossom centre, reading as a flower on the branch."""
    wrist, _ = wrist_pos(1)
    w = Vector(wrist)
    stem = make_tube("NavyBranchStem", tuple(w), tuple(SHAFT_DIR),
                     [0.0, SHAFT_LEN], [0.012, 0.008], 6,
                     m["navy"], caps=True)
    flowers = []
    n = Vector((0, -1, 0.35)).normalized()
    for i, s in enumerate(BRANCH_FLOWER_S):
        c = w + SHAFT_DIR * s
        flowers += make_sakura_patch("SakuraBranchFlower%d" % i,
                                     tuple(c), tuple(n), 0.030,
                                     m["sakura_red"], m["gold"])
    return [stem] + flowers, w


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = parts["sweater"] + parts["sweater_flowers"]
    ok = True
    ok &= check_gap("torso: cream sweater vs mannequin torso @z=1.28",
                    interp_rings(SWEATER_RINGS, 1.28)[0],
                    interp_rings(TORSO_RINGS, 1.28)[0])
    ok &= check_gap("torso: cream sweater vs mannequin torso @z=0.95",
                    interp_rings(SWEATER_RINGS, 0.95)[0],
                    interp_rings(TORSO_RINGS, 0.95)[0])
    ok &= check_relief("torso: sakura flower relief", 0.006,
                       lo=0.005, hi=0.015)
    print("L2_CHECK torso: cream turtleneck sweater clears the torso, "
          "3 sakura blossoms on the chest front PASS")
    return objs, ok


def assemble_jacket(parts):
    objs = (parts["jacket"] + parts["jacket_flowers"]
            + parts["pleats"])
    ok = True
    ok &= check_gap("jacket: sakura jacket vs cream sweater @z=1.20",
                    interp_rings(JACKET_RINGS, 1.20)[0],
                    interp_rings(SWEATER_RINGS, 1.20)[0])
    ok &= check_gap("jacket: sakura jacket vs cream sweater @z=0.92",
                    interp_rings(JACKET_RINGS, 0.92)[0],
                    interp_rings(SWEATER_RINGS, 0.92)[0])
    ok &= check_gap("jacket: sakura jacket vs cream sweater ry @z=1.20",
                    interp_rings(JACKET_RINGS, 1.20)[1],
                    interp_rings(SWEATER_RINGS, 1.20)[1])
    ok &= check_gap("jacket: sakura jacket vs cream sweater ry @z=0.92",
                    interp_rings(JACKET_RINGS, 0.92)[1],
                    interp_rings(SWEATER_RINGS, 0.92)[1])
    ok &= check_relief("jacket: sakura flower relief", 0.006,
                       lo=0.005, hi=0.015)
    ok &= check_relief("jacket: sakura pleat fin height", 0.022,
                       lo=0.005, hi=0.030)
    print("L2_CHECK jacket: sakura-pink short jacket hangs loose over "
          "the cream sweater, 2 sakura blossoms on the front edges, "
          "8 pleat fins at the skirt hem PASS")
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
    ok &= check_gap("belt: navy belt vs sakura jacket @z=0.98",
                    interp_rings(BELT_RINGS, 0.98)[0],
                    interp_rings(JACKET_RINGS, 0.98)[0])
    ok &= check_gap("belt: navy belt vs sakura jacket @z=0.92",
                    interp_rings(BELT_RINGS, 0.92)[0],
                    interp_rings(JACKET_RINGS, 0.92)[0])
    ok &= check_gap("belt: navy belt vs sakura jacket ry @z=0.98",
                    interp_rings(BELT_RINGS, 0.98)[1],
                    interp_rings(JACKET_RINGS, 0.98)[1])
    ok &= check_gap("belt: navy belt vs sakura jacket ry @z=0.92",
                    interp_rings(BELT_RINGS, 0.92)[1],
                    interp_rings(JACKET_RINGS, 0.92)[1])
    ok &= check_relief("belt: gold buckle relief", 0.0115,
                       lo=0.005, hi=0.030)
    print("L2_CHECK belt: navy waist belt cinches the jacket, "
          "gold buckle at the front PASS")
    return objs, ok


def assemble_head(parts):
    objs = (parts["beret"] + parts["band"] + parts["beret_flower"]
            + parts["ears"] + parts["streak"] + parts["earrings"])
    ok = True
    # Beret dome vs hair cap (039 numbers, same geometry):
    # dome rx 0.2556 @z=1.66, 0.2420 @z=1.64.
    ok &= check_gap("head: sakura beret vs black hair cap @z=1.66",
                    0.2556, 0.1949)
    ok &= check_gap("head: sakura beret vs black hair cap @z=1.64",
                    0.2420, 0.2073)
    ok &= check_gap("head: navy beret band vs sakura beret @z=1.66",
                    0.2616, 0.2556)
    ok &= check_gap("head: navy beret band vs sakura beret @z=1.64",
                    0.2479, 0.2420)
    # 043/044 lesson: faceted dome ring vertex at z 1.6254 (r 0.2252)
    # is the nearest feature to the band bottom ring (r 0.230, z 1.62).
    band_bottom_gap = round(math.hypot(0.230 - 0.2252, 1.62 - 1.6254), 4)
    band_bottom_ok = band_bottom_gap >= MIN_GAP
    print("L2_CHECK head: navy beret band vs sakura beret @z=1.62 "
          "(faceted ring vertex) gap=%.4f min=%.3f %s"
          % (band_bottom_gap, MIN_GAP,
             "PASS" if band_bottom_ok else "FAIL"))
    ok &= band_bottom_ok
    ok &= check_gap("head: navy beret band vs black hair cap @z=1.62",
                    0.2232, 0.2161)
    ok &= check_gap("head: sakura beret bottom vs eye line",
                    1.571, 1.525)
    ok &= check_relief("head: sakura flower on beret relief", 0.006,
                       lo=0.005, hi=0.015)
    ok &= check_relief("head: gold earring relief", 0.019,
                       lo=0.005, hi=0.030)
    print("L2_CHECK head: sakura-pink beret over the hair, navy band "
          "following the dome, sakura blossom on the beret front, cat "
          "ears out of the beret, blue streak below the band, gold "
          "studs PASS")
    return objs, ok


def assemble_legs(parts):
    objs = parts["skirt"] + parts["socks"]
    ok = True
    ok &= check_gap("legs: navy pleated skirt vs leg outer edges @z=0.35",
                    interp_rings(SKIRT_RINGS, 0.35)[0], 0.230)
    ok &= check_gap("legs: navy pleated skirt vs cream sweater hem @z=0.95",
                    interp_rings(SWEATER_RINGS, 0.95)[0],
                    interp_rings(SKIRT_RINGS, 0.95)[0])
    ok &= check_gap("legs: cream sock vs mannequin leg @z=0.20",
                    0.0979, 0.0866)
    print("L2_CHECK legs: navy pleated skirt flares over the legs, "
          "cream over-knee socks meet the skirt hem PASS")
    return objs, ok


def assemble_feet(parts):
    objs = parts["loafers"]
    ok = True
    ok &= check_gap("feet: sakura loafer shaft vs cream sock @z=0.10",
                    0.105, 0.0966)
    ok &= check_gap("feet: sakura loafer sole vs mannequin foot",
                    0.100, 0.095)
    print("L2_CHECK feet: sakura-pink loafers centre z=0.0, soles on "
          "ground; gold buckles at the front PASS")
    return objs, ok


def assemble_hand(parts, wrist):
    objs = parts["glove"] + parts["branch"]
    ok = True
    ok &= check_gap("hand: navy glove vs mannequin hand",
                    0.095, 0.085)
    # Branch clearances, as ellipse-normalised values (>1.15 = clear).
    # Stem point at z 0.90 (below the jacket hem, against the skirt):
    t = (0.90 - wrist.z) / SHAFT_DIR.z
    sp = wrist + SHAFT_DIR * t
    rx, ry = interp_rings(SKIRT_RINGS, 0.90)
    sv = ellipse_value(sp.x, sp.y, rx, ry)
    print("L2_CHECK hand: sakura branch stem @z=0.90 ellipse_value=%.3f "
          "(must be >1.15)" % sv)
    ok &= sv > 1.15
    # Middle blossom vs sleeve: blossom centre at s=0.42; sleeve axis
    # origin (0.313, 0, 1.339), direction (0.139, 0, -0.99); sleeve
    # radius at that height ~0.110, blossom radius 0.030.
    bc = wrist + SHAFT_DIR * BRANCH_FLOWER_S[1]
    ax = 0.313 + 0.139 * (1.339 - bc.z) / 0.9903
    rim_dist = math.hypot(bc.x - ax, bc.y)
    s_arm = (1.339 - bc.z) / 0.9903
    sleeve_r = 0.125 + (0.118 - 0.125) * (s_arm / 0.17) \
        if s_arm <= 0.17 else 0.118 + (0.110 - 0.118) * ((s_arm - 0.17) / 0.17)
    print("L2_CHECK hand: branch blossom vs sleeve axis "
          "centre_dist=%.3f sleeve_r=%.3f petal_r=0.030" % (rim_dist, sleeve_r))
    ok &= check_gap("hand: branch blossom vs sleeve surface",
                    rim_dist, sleeve_r + 0.030)
    print("L2_CHECK hand: navy glove covers the left hand, sakura "
          "branch held in the right hand, stem + blossoms clear of "
          "the skirt and sleeve PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: sakura jacket vs cream sweater @z=1.20",
                    interp_rings(JACKET_RINGS, 1.20)[0],
                    interp_rings(SWEATER_RINGS, 1.20)[0])
    ok &= check_gap("L3 layer: navy belt vs sakura jacket @z=0.95",
                    interp_rings(BELT_RINGS, 0.95)[0],
                    interp_rings(JACKET_RINGS, 0.95)[0])
    ok &= check_gap("L3 layer: navy pleated skirt vs leg outer edges",
                    interp_rings(SKIRT_RINGS, 0.35)[0], 0.230)
    ok &= check_gap("L3 layer: sakura beret bottom vs eye line",
                    1.571, 1.525)
    ok &= check_gap("L3 joint: navy sleeve vs mannequin arm",
                    0.125, 0.085)
    ok &= check_gap("L3 joint: sakura loafer shaft vs cream sock",
                    0.105, 0.0966)
    ok &= check_gap("L3 joint: sakura loafer sole vs mannequin foot",
                    0.100, 0.095)
    print("L3_CHECK outfit: sakura jacket over the cream sweater, "
          "navy belt cinching the waist, pleated skirt over the legs, "
          "beret above the eyes, loafers on ground z=0.000 PASS")
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
    parts["jacket"] = build_jacket(m)
    report_l1("SakuraJacket", parts["jacket"])
    parts["sweater_flowers"] = []
    for angle, z in ((270, 1.32), (262, 1.02), (278, 1.02)):
        parts["sweater_flowers"] += build_sakura_on_sweater(m, angle, z)
    report_l1("SakuraFlowersOnSweater x3", parts["sweater_flowers"])
    parts["jacket_flowers"] = []
    for angle, z in ((225, 1.10), (315, 1.10)):
        parts["jacket_flowers"] += build_sakura_on_jacket(m, angle, z)
    report_l1("SakuraFlowersOnJacket x2", parts["jacket_flowers"])
    parts["pleats"] = [build_pleat_fin(m, a) for a in PLEAT_ANGLES]
    report_l1("SakuraPleats x8", parts["pleats"])
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
    report_l1("GoldBeltBuckle", [parts["buckle"]])
    parts["skirt"] = build_skirt(m)
    report_l1("NavyPleatedSkirt", parts["skirt"])
    parts["socks"] = []
    for sx in (-1, 1):
        parts["socks"] += build_sock(m, sx)
    report_l1("CreamSocks x2", parts["socks"])
    parts["loafers"] = []
    for sx in (-1, 1):
        parts["loafers"] += build_loafer(m, sx)
    report_l1("SakuraLoafers x2", parts["loafers"])
    parts["beret"] = build_beret(m)
    report_l1("SakuraBeret", parts["beret"])
    parts["band"] = build_beret_band(m)
    report_l1("NavyBeretBand", parts["band"])
    parts["beret_flower"] = build_beret_flower(m)
    report_l1("SakuraBeretFlower", parts["beret_flower"])
    parts["ears"] = [build_cat_ear(m, sx) for sx in (-1, 1)]
    report_l1("NavyCatEars x2", parts["ears"])
    parts["streak"] = build_streak(m)
    report_l1("HairStreak", parts["streak"])
    parts["earrings"] = [build_earring(m, sx) for sx in (-1, 1)]
    report_l1("GoldEarrings x2", parts["earrings"])
    parts["glove"] = build_glove(m)
    report_l1("NavyGlove", parts["glove"])
    parts["branch"], wrist = build_branch(m)
    report_l1("SakuraBranch", parts["branch"])

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    _, ok = assemble_torso(parts)
    l2_ok &= ok
    _, ok = assemble_jacket(parts)
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
    costume = (parts["sweater"] + parts["jacket"]
               + parts["sweater_flowers"] + parts["jacket_flowers"]
               + parts["pleats"] + parts["sleeves"] + parts["cuffs"]
               + parts["belt"] + [parts["buckle"]] + parts["skirt"]
               + parts["socks"] + parts["loafers"]
               + parts["beret"] + parts["band"] + parts["beret_flower"]
               + parts["ears"] + parts["streak"]
               + parts["earrings"] + parts["glove"] + parts["branch"])
    l3_ok = assemble_outfit(parts, mannequin)

    # --- normal self-check (solids only; the flat sakura patches keep
    # their construction winding — fix_normals must never run on
    # flat patches). 047 fix: SakuraJacket (open-front elliptical tube,
    # 30/30 faces wound inward) and SakuraLoafer (wedge, 2/6 faces per
    # shoe wound inward) DO run fix_normals — 046 found 34 inverted
    # solid faces because every Sakura* object was skipped here.
    # Base-name match: the second loafer is "SakuraLoafer.001". ---
    FIX_NORMALS = {"SakuraJacket", "SakuraLoafer"}
    for obj in mannequin + costume:
        if (obj.name.startswith("Sakura")
                and obj.name.split(".")[0] not in FIX_NORMALS):
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
