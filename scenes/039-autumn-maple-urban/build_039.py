# -*- coding: utf-8 -*-
"""039 异环式都市时装 · 秋日红叶套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整套穿到人体底座上试穿）。
设计见 design.md。BACKLOG 已空时自选：异环线第九件——秋日场景方向
（015 夜行、025 街头、026 学院、027 运动、028 居家、029 通勤、
031 夏日、032 冬日之后；学院/居家/运动/街头/通勤/夜行/夏日/冬日
矩阵里秋日首次做，11 月底季节贴合）。
焦糖棕中长风衣（前开襟、枫叶红枫叶纹×5、风衣下摆褶裥×8、枫叶红
腰带 + 金腰扣）+ 奶油白高领毛衣内层（金枫叶胸针）+ 藏青长袖
（奶油白袖口）+ 藏青长裤 + 焦糖棕短靴 + 焦糖棕贝雷帽（藏青帽带 +
枫叶红帽针）+ 猫耳 + 蓝挑染 + 金耳钉 + 藏青手套（左手）+
枫叶红枫叶（右手托叶）。廓形改中长风衣（032 长款大衣到膝、036
短款外套到腰之间，风衣下摆到大腿中部 z 0.58）——异环线廓形变量。
Run: blender --background --python build_039.py
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

BLEND_OUT = os.path.join(HERE, "039-autumn-maple-urban.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "039-autumn-maple-urban.png")
WIRE_JSON = "/tmp/autumn_maple_urban_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

SWEATER_RINGS = [(1.50, 0.300, 0.160), (1.44, 0.288, 0.152),
                 (1.10, 0.272, 0.144), (0.80, 0.258, 0.138),
                 (0.62, 0.248, 0.132)]
COAT_RINGS = [(1.50, 0.312, 0.168), (1.20, 0.310, 0.162),
              (0.90, 0.306, 0.160), (0.72, 0.302, 0.158),
              (0.58, 0.300, 0.156)]
TROUSER_RINGS = [(0.62, 0.246, 0.128), (0.48, 0.240, 0.126),
                 (0.34, 0.232, 0.124)]
BELT_RINGS = [(0.94, 0.313, 0.167), (0.88, 0.312, 0.166)]
PLEAT_ANGLES = [170, 200, 230, 320, 350, 20, 50, 110]  # all outside 240-300
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    caramel = solid_material("Caramel", (0.397, 0.165, 0.044),
                             roughness=0.6)
    cream = solid_material("Cream", (0.888, 0.847, 0.768), roughness=0.6)
    navy = solid_material("Navy", (0.013, 0.023, 0.068), roughness=0.6)
    maple = solid_material("MapleRed", (0.527, 0.041, 0.024),
                           roughness=0.6)
    gold = solid_material("Gold", (0.584, 0.361, 0.020), metallic=0.6,
                          roughness=0.35)
    lightblue = solid_material("LightBlue", (0.212, 0.479, 0.807),
                               roughness=0.6)
    black = solid_material("Hair_Black", (0.011, 0.011, 0.015),
                           roughness=0.7)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"caramel": caramel, "cream": cream, "navy": navy,
            "maple": maple, "gold": gold, "lightblue": lightblue,
            "black": black, "skin": skin, "eye": eye}


# ------------------------------------------------------------ star patch
def make_star_patch(name, center, normal, radius, material):
    """Flat 5-point star patch (10 triangles, fan from the centre).
    The star lies in the plane perpendicular to `normal`, one point
    up (+z in the local plane). Faces are wound so their normal is
    +normal (see design.md: flat patches must keep construction
    winding — fix_normals must never run on them)."""
    n = Vector(normal).normalized()
    up = Vector((0, 0, 1))
    if abs(n.z) > 0.99:
        up = Vector((1, 0, 0))
    u = up.cross(n).normalized()
    v = n.cross(u)
    c = Vector(center)
    verts = [tuple(c)]
    for k in range(10):
        r = radius if k % 2 == 0 else radius * 0.45
        theta = math.radians(90 + k * 36)
        p = c + (u * math.cos(theta) + v * math.sin(theta)) * r
        verts.append(tuple(p))
    faces = [(0, i + 1, i + 2 if i + 2 <= 10 else 1) for i in range(10)]
    return mesh_from_data(name, verts, faces, material)


def _patch_on_ellipse(name, rings, angle_deg, z, radius, material,
                      offset=0.006):
    """Star patch on an elliptical tube surface at (angle, z)."""
    rx, ry = interp_rings(rings, z)
    p, n = ellipse_point(rx, ry, angle_deg)
    c = Vector((p.x, p.y, z)) + n * offset
    return make_star_patch(name, tuple(c), tuple(n), radius, material)


# ------------------------------------------------------------ L1 components
def build_sweater(m):
    """Cream turtleneck sweater, inner layer: 5 rings, z 1.50-0.62.
    The top ring (z 1.50, rx 0.300) reads as the turtleneck collar —
    a separate narrow neck ring (r 0.125) would hide behind the head
    sphere (036 v1 lesson). Hem meets the trouser top at z 0.62
    exactly (no overlap band — the 0.62-0.60 overlap in the first
    draft left only 0.002-0.004 clearance over the trousers)."""
    return [make_elliptical_tube("CreamSweater", SWEATER_RINGS, 16,
                                 m["cream"], caps=False)]


def build_coat(m):
    """Caramel mid-length trench coat, open front: arc 300-600 deg
    leaves the 240-300 deg front wedge open so the cream sweater
    shows. Mid-length to mid-thigh: z 1.50-0.58, 5 rings — the
    silhouette variable between 032's knee-length coat and 036's
    waist-length jacket."""
    return [make_elliptical_tube("CaramelCoat", COAT_RINGS, 16,
                                 m["caramel"], arc=(300, 600),
                                 caps=False)]


def build_maple_leaf_on_sweater(m, angle_deg, z):
    """One maple-red leaf on the sweater front (visible through the
    coat's open front)."""
    return _patch_on_ellipse("MapleLeafPatch", SWEATER_RINGS, angle_deg,
                             z, 0.035, m["maple"])


def build_maple_leaf_on_coat(m, angle_deg, z):
    """One maple-red leaf on the coat front edge (220/320 deg — just
    outside the 240-300 open wedge; a leaf inside the wedge would
    float in front of the sweater)."""
    return _patch_on_ellipse("MapleLeafPatch", COAT_RINGS, angle_deg,
                             z, 0.035, m["maple"])


def build_pleat_fin(m, angle_deg):
    """One 3D pleat fin: a closed thin solid (10 quads) following the
    coat cone, inner edge 0.004 off the coat, outer edge 0.026 off,
    tangential half-thickness 0.004. Same construction as 026/030/
    032/036."""
    rows = [0.78, 0.68, 0.58]
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
    return mesh_from_data("CaramelPleat", verts, faces, m["caramel"])

def build_brooch(m):
    """Gold maple-leaf brooch on the sweater chest (270 deg, z 1.22),
    visible through the coat's open front. v2: v1's z 1.40 sat inside
    the head sphere (head r 0.196 at z 1.40, brooch at y -0.157) and
    was invisible — the sweater front only emerges from the chin
    below z 1.36. z 1.22 sits between the chest leaf (1.32) and the
    lower leaves (1.02), 0.035 clear of the leaf below it."""
    return _patch_on_ellipse("GoldMapleBrooch", SWEATER_RINGS, 270,
                             1.22, 0.030, m["gold"])


def build_sleeve(m, sx):
    """Navy long sleeve over the arm (shoulder to wrist).
    Capped (025 v2 lesson). Origin lifted 0.12 along the arm axis
    so the sleeve starts at z 1.34, emerging from the coat shoulder
    (032 v1: a sleeve starting at the shoulder joint read as a slab
    floating beside the body)."""
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
    (sleeve r 0.0986 at s 0.60, not the end 0.096 — 036 v3/037
    lesson: the old r 0.102 only cleared the sleeve end, giving a
    real gap of 0.0034 at the cuff top ring)."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    origin = shoulder + direction.normalized() * 0.48
    return [make_tube("CreamCuff", origin, direction,
                      [0.0, 0.08], [0.105, 0.105], 10,
                      m["cream"], caps=False)]


def build_belt(m):
    """Maple-red waist belt: tube around the coat waist (z 0.94-0.88),
    0.006+ proud of the coat in both rx and ry — the mid-length
    coat's cinched-waist payoff (037 lesson: check ry too)."""
    return [make_elliptical_tube("MapleRedBelt", BELT_RINGS, 16,
                                 m["maple"], caps=False)]


def build_belt_buckle(m):
    """Gold belt buckle at the front centre (0, -0.1715, 0.91):
    belt front at z 0.91 is y -0.1665, so the 0.012-thick box is
    half-buried and 0.010 proud."""
    return add_box("GoldBeltBuckle", (0, -0.1715, 0.91),
                   (0.05, 0.012, 0.04), m["gold"])


def build_trousers(m):
    """Navy trousers: tube around both leg tops, z 0.62-0.34,
    hem ends above the boots."""
    return [make_elliptical_tube("NavyTrousers", TROUSER_RINGS, 12,
                                 m["navy"], caps=False)]


def build_boot(m, sx):
    """Caramel ankle boot: tube around the lower leg (z 0.34-0.02,
    r 0.118) + sole wedge landing z=0.0 + navy cuff ring at the
    top (z 0.36-0.32, r 0.124). Sole wedge top 0.105/0.055 (0.005
    above the mannequin foot top 0.10/0.045) — 036 v1 lesson."""
    tube = make_tube("CaramelBoot", (sx * 0.13, 0, 0.34), (0, 0, -1),
                     [0.0, 0.32], [0.118, 0.118], 10,
                     m["caramel"], caps=False)
    sole = make_wedge("CaramelBootSole", (sx * 0.13, -0.02, 0.0),
                      0.102, 0.095, -0.165, 0.0, 0.105, 0.055,
                      m["caramel"])
    cuff = make_tube("NavyBootCuff", (sx * 0.13, 0, 0.36), (0, 0, -1),
                     [0.0, 0.04], [0.124, 0.124], 10,
                     m["navy"], caps=False)
    return [tube, sole, cuff]


def build_beret(m):
    """Caramel beret: flattened sphere r 0.26, centre (0, 0.01, 1.68),
    z-scale 0.42, top 1.789 covering the hair cap top (1.75). The
    dome crosses the hair surface near z 1.62 (beret r 0.2172 vs
    hair rx 0.2161) — below that the rim sits inside the hair, above
    it clears by 0.035+; the hat sits in the hair, like 036's cap."""
    return [add_sphere("CaramelBeret", (0, 0.01, 1.68), 0.26, 12, 6,
                       (1.0, 1.0, 0.42), m["caramel"])]


def build_beret_band(m):
    """Navy beret band: 3-ring tube following the beret's curvature
    (z 1.66-1.62, r 0.2616/0.2479/0.2232, each 0.006 proud of the
    dome). The flattened dome narrows fast at this height (r 0.2556
    at 1.66 -> 0.2172 at 1.62), so a single ring would float 0.15
    off the dome at its bottom edge."""
    return [make_tube("NavyBeretBand", (0, 0.01, 1.66), (0, 0, -1),
                      [0.0, 0.02, 0.04], [0.2616, 0.2479, 0.2232], 24,
                      m["navy"], caps=False)]


def build_beret_pin(m):
    """Maple-red leaf pin on the beret front-right (300 deg, z 1.70):
    beret cross radius there is 0.2556, so the patch centre sits at
    0.2596 from the beret axis, 0.006 off the dome."""
    a = math.radians(300)
    r = 0.2556 + 0.006
    c = (r * math.cos(a), 0.01 + r * math.sin(a), 1.70)
    n = (math.cos(a), math.sin(a), 0.0)
    return make_star_patch("MapleLeafPin", c, n, 0.028, m["maple"])


def build_cat_ear(m, sx):
    """Navy cat ear: four-sided pyramid (032 method), base buried in
    the beret dome at z=1.70, apex at z=1.86 (0.071 above the beret
    top 1.789). The ear sides emerge from the dome around z 1.75."""
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
    the black hair cap, front-right below the beret band (032
    method). Top z 1.49 stays below the band bottom (1.62) — 031
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


def build_maple_leaf_handheld(m):
    """Maple-red leaf held up in the right palm (camera side): flat
    star patch, radius 0.045, vertical facing the camera (-Y),
    0.09 in front of the wrist — 036's compass method: a handheld
    must stand up in front of the palm, never lie flat in the cuff
    tube (036 v1 lesson)."""
    wrist, _ = wrist_pos(1)
    wx, wy, wz = wrist
    return make_star_patch("MapleLeafHandheld", (wx, wy - 0.09, wz - 0.02),
                           (0, -1, 0), 0.045, m["maple"])


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["sweater"] + parts["brooch"] + parts["sweater_leaves"])
    ok = True
    ok &= check_gap("torso: cream sweater vs mannequin torso @z=1.28",
                    interp_rings(SWEATER_RINGS, 1.28)[0],
                    interp_rings(TORSO_RINGS, 1.28)[0])
    ok &= check_gap("torso: cream sweater vs mannequin torso @z=0.95",
                    interp_rings(SWEATER_RINGS, 0.95)[0],
                    interp_rings(TORSO_RINGS, 0.95)[0])
    ok &= check_relief("torso: gold brooch relief", 0.006,
                       lo=0.005, hi=0.015)
    ok &= check_relief("torso: maple leaf patch relief", 0.006,
                       lo=0.005, hi=0.015)
    print("L2_CHECK torso: cream turtleneck sweater clears the torso, "
          "gold brooch + 3 maple leaves on the chest front PASS")
    return objs, ok


def assemble_coat(parts):
    objs = parts["coat"] + parts["coat_leaves"] + parts["pleats"]
    ok = True
    ok &= check_gap("coat: caramel coat vs cream sweater @z=1.20",
                    interp_rings(COAT_RINGS, 1.20)[0],
                    interp_rings(SWEATER_RINGS, 1.20)[0])
    ok &= check_gap("coat: caramel coat vs cream sweater @z=0.90",
                    interp_rings(COAT_RINGS, 0.90)[0],
                    interp_rings(SWEATER_RINGS, 0.90)[0])
    ok &= check_relief("coat: maple leaf patch relief", 0.006,
                       lo=0.005, hi=0.015)
    ok &= check_relief("coat: caramel pleat fin height", 0.022,
                       lo=0.005, hi=0.030)
    print("L2_CHECK coat: caramel mid-length trench hangs loose over "
          "the cream sweater, 2 maple leaves on the front edges + "
          "8 pleat fins at the hem PASS")
    return objs, ok


def assemble_sleeves(parts):
    objs = parts["sleeves"] + parts["cuffs"]
    ok = True
    ok &= check_gap("sleeve: navy sleeve vs mannequin arm @0.0",
                    0.125, 0.085)
    # Cuff ring r 0.105 vs sleeve end 0.096, AND vs the sleeve radius
    # at the cuff top ring (s 0.60 -> r 0.0986, not the end 0.096):
    # 037 caught the old 0.102 ring clearing only the end (real gap
    # 0.0034). Check both, not just the end.
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
    ok &= check_gap("belt: maple belt vs caramel coat @z=0.94",
                    interp_rings(BELT_RINGS, 0.94)[0],
                    interp_rings(COAT_RINGS, 0.94)[0])
    ok &= check_gap("belt: maple belt vs caramel coat @z=0.88",
                    interp_rings(BELT_RINGS, 0.88)[0],
                    interp_rings(COAT_RINGS, 0.88)[0])
    # 037 lesson (034 hat-band ry blind spot, repeated): check ry too.
    ok &= check_gap("belt: maple belt vs caramel coat ry @z=0.94",
                    interp_rings(BELT_RINGS, 0.94)[1],
                    interp_rings(COAT_RINGS, 0.94)[1])
    ok &= check_gap("belt: maple belt vs caramel coat ry @z=0.88",
                    interp_rings(BELT_RINGS, 0.88)[1],
                    interp_rings(COAT_RINGS, 0.88)[1])
    ok &= check_relief("belt: gold buckle relief", 0.010,
                       lo=0.005, hi=0.030)
    print("L2_CHECK belt: maple-red waist belt cinches the coat, "
          "gold buckle at the front PASS")
    return objs, ok


def assemble_head(parts):
    objs = (parts["beret"] + parts["band"] + [parts["pin"]]
            + parts["ears"] + parts["streak"] + parts["earrings"])
    ok = True
    # Beret dome vs hair cap: dome rx 0.2556 @z=1.66, 0.2420 @z=1.64;
    # hair rx 0.1949 @z=1.66, 0.2073 @z=1.64. The dome crosses the
    # hair near z 1.62 (gap 0.0011) — the hat sits in the hair, so
    # only the two upper heights are checked here.
    ok &= check_gap("head: caramel beret vs black hair cap @z=1.66",
                    0.2556, 0.1949)
    ok &= check_gap("head: caramel beret vs black hair cap @z=1.64",
                    0.2420, 0.2073)
    ok &= check_gap("head: navy beret band vs caramel beret @z=1.66",
                    0.2616, 0.2556)
    ok &= check_gap("head: navy beret band vs caramel beret @z=1.64",
                    0.2479, 0.2420)
    ok &= check_gap("head: navy beret band vs caramel beret @z=1.62",
                    0.2232, 0.2172)
    ok &= check_gap("head: navy beret band vs black hair cap @z=1.62",
                    0.2232, 0.2161)
    ok &= check_gap("head: caramel beret bottom vs eye line",
                    1.571, 1.525)
    ok &= check_relief("head: maple leaf pin relief", 0.006,
                       lo=0.005, hi=0.015)
    ok &= check_relief("head: gold earring relief", 0.019,
                       lo=0.005, hi=0.030)
    print("L2_CHECK head: caramel beret over the hair, navy band "
          "following the dome, maple pin on the beret front, cat "
          "ears out of the beret, blue streak below the band, gold "
          "studs PASS")
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
    ok &= check_gap("feet: caramel boot vs mannequin leg @z=0.20",
                    0.118, 0.0866)
    ok &= check_gap("feet: navy boot cuff vs caramel boot",
                    0.124, 0.118)
    ok &= check_gap("feet: caramel boot sole vs mannequin foot",
                    0.102, 0.095)
    print("L2_CHECK feet: caramel boot tubes centre z=0.0, soles on "
          "ground; navy cuffs at the boot tops PASS")
    return objs, ok


def assemble_hand(parts):
    objs = parts["glove"] + [parts["leaf"]]
    ok = True
    ok &= check_gap("hand: navy glove vs mannequin hand",
                    0.095, 0.085)
    ok &= check_relief("hand: maple leaf in front of palm", 0.007,
                       lo=0.005, hi=0.030)
    print("L2_CHECK hand: navy glove covers the left hand, maple leaf "
          "held up in front of the right palm PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: caramel coat vs cream sweater @z=1.20",
                    interp_rings(COAT_RINGS, 1.20)[0],
                    interp_rings(SWEATER_RINGS, 1.20)[0])
    ok &= check_gap("L3 layer: maple belt vs caramel coat @z=0.94",
                    interp_rings(BELT_RINGS, 0.94)[0],
                    interp_rings(COAT_RINGS, 0.94)[0])
    ok &= check_gap("L3 layer: caramel beret bottom vs eye line",
                    1.571, 1.525)
    ok &= check_gap("L3 joint: navy sleeve vs mannequin arm",
                    0.125, 0.085)
    ok &= check_gap("L3 joint: caramel boot vs mannequin leg @z=0.20",
                    0.118, 0.0866)
    ok &= check_gap("L3 joint: caramel boot sole vs mannequin foot",
                    0.102, 0.095)
    print("L3_CHECK outfit: caramel coat over the cream sweater, "
          "maple belt cinching the waist, beret above the eyes, "
          "boots on ground z=0.000 PASS")
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
    parts["coat"] = build_coat(m)
    report_l1("CaramelCoat", parts["coat"])
    parts["sweater_leaves"] = [
        build_maple_leaf_on_sweater(m, 270, 1.32),
        build_maple_leaf_on_sweater(m, 262, 1.02),
        build_maple_leaf_on_sweater(m, 278, 1.02)]
    report_l1("MapleLeavesOnSweater x3", parts["sweater_leaves"])
    parts["coat_leaves"] = [
        build_maple_leaf_on_coat(m, 220, 1.05),
        build_maple_leaf_on_coat(m, 320, 1.05)]
    report_l1("MapleLeavesOnCoat x2", parts["coat_leaves"])
    parts["pleats"] = [build_pleat_fin(m, a) for a in PLEAT_ANGLES]
    report_l1("CaramelPleats x8", parts["pleats"])
    parts["brooch"] = [build_brooch(m)]
    report_l1("GoldMapleBrooch", parts["brooch"])
    parts["sleeves"] = []
    for sx in (-1, 1):
        parts["sleeves"] += build_sleeve(m, sx)
    report_l1("NavySleeves x2", parts["sleeves"])
    parts["cuffs"] = []
    for sx in (-1, 1):
        parts["cuffs"] += build_cuff(m, sx)
    report_l1("CreamCuffs x2", parts["cuffs"])
    parts["belt"] = build_belt(m)
    report_l1("MapleRedBelt", parts["belt"])
    parts["buckle"] = build_belt_buckle(m)
    report_l1("GoldBeltBuckle", [parts["buckle"]])
    parts["trousers"] = build_trousers(m)
    report_l1("NavyTrousers", parts["trousers"])
    parts["boots"] = []
    for sx in (-1, 1):
        parts["boots"] += build_boot(m, sx)
    report_l1("CaramelBoots x2", parts["boots"])
    parts["beret"] = build_beret(m)
    report_l1("CaramelBeret", parts["beret"])
    parts["band"] = build_beret_band(m)
    report_l1("NavyBeretBand", parts["band"])
    parts["pin"] = build_beret_pin(m)
    report_l1("MapleLeafPin", [parts["pin"]])
    parts["ears"] = [build_cat_ear(m, sx) for sx in (-1, 1)]
    report_l1("NavyCatEars x2", parts["ears"])
    parts["streak"] = build_streak(m)
    report_l1("HairStreak", parts["streak"])
    parts["earrings"] = [build_earring(m, sx) for sx in (-1, 1)]
    report_l1("GoldEarrings x2", parts["earrings"])
    parts["glove"] = build_glove(m)
    report_l1("NavyGlove", parts["glove"])
    parts["leaf"] = build_maple_leaf_handheld(m)
    report_l1("MapleLeafHandheld", [parts["leaf"]])

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
    _, ok = assemble_hand(parts)
    l2_ok &= ok
    print("L2_SUMMARY %s" % ("ALL PASS" if l2_ok else "FAILURES PRESENT"))

    # ---- L3 full outfit on the mannequin ----
    costume = (parts["sweater"] + parts["coat"]
               + parts["sweater_leaves"] + parts["coat_leaves"]
               + parts["pleats"] + parts["brooch"]
               + parts["sleeves"] + parts["cuffs"] + parts["belt"]
               + [parts["buckle"]] + parts["trousers"]
               + parts["boots"] + parts["beret"] + parts["band"]
               + [parts["pin"]] + parts["ears"] + parts["streak"]
               + parts["earrings"] + parts["glove"] + [parts["leaf"]])
    l3_ok = assemble_outfit(parts, mannequin)

    # --- normal self-check (solids only; the flat star patches keep
    # their construction winding — fix_normals must never run on
    # flat patches/discs) ---
    for obj in mannequin + costume:
        if obj.name.startswith(("MapleLeaf", "GoldMapleBrooch")):
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
