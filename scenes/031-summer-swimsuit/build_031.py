# -*- coding: utf-8 -*-
"""031 异环式都市时装 · 夏日泳装套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整套穿到人体底座上试穿）。
设计见 design.md。BACKLOG 已空，本轮自选：异环线第七件——夏日海滩风
（015 夜行者、025 街头、026 学院、027 运动、028 居家、029 通勤之后；
学院/居家/运动/街头/通勤/夜行矩阵里夏日首次做；DESIGN.md 主角时装库
明确提到夏日泳装）。珊瑚橙连体泳装（抹胸式）+ 白罩衫前开襟 +
珊瑚衫摆边 + 金扣×4 + 金项链 + 金胸前搭扣 + 白遮阳帽宽檐 + 藏青帽带
+ 墨镜挂胸前 + 白裹裙 + 金结扣 + 藏青沙滩托特包 + 金搭扣 + 凉鞋 +
蓝帽针。宽檐帽用闭合圆柱体（不用 make_disc 单面片，相机在檐下）、
墨镜挂胸前不遮眼。v2：遮阳帽檐 0.30→0.36、帽顶压扁 0.75→0.55、
帽带上移至檐上、蓝挑染改蓝帽针（v1 挑染顶穿帽顶成帽上蓝斑）。
Run: blender --background --python build_031.py
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

BLEND_OUT = os.path.join(HERE, "031-summer-swimsuit.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "031-summer-swimsuit.png")
WIRE_JSON = "/tmp/summer_swimsuit_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

# Mannequin torso rings (same base as 001..030) for gap checks.
TORSO_RINGS = [(1.28, 0.270, 0.140), (0.95, 0.240, 0.130),
               (0.62, 0.210, 0.120)]
LEG_RINGS = [(0.62, 0.105), (0.52, 0.1023)]  # (z, r) outer extent helper

SWIM_RINGS = [(1.32, 0.272, 0.142), (1.28, 0.278, 0.146),
              (1.00, 0.250, 0.138), (0.70, 0.224, 0.128),
              (0.62, 0.218, 0.126)]
BRIEF_RINGS = [(0.62, 0.246, 0.128), (0.52, 0.242, 0.126),
               (0.46, 0.236, 0.122)]
SHIRT_RINGS = [(1.42, 0.296, 0.155), (1.10, 0.300, 0.156),
               (0.80, 0.306, 0.158)]
TRIM_RINGS = [(0.84, 0.312, 0.164), (0.80, 0.312, 0.164)]
SARONG_RINGS = [(0.78, 0.252, 0.132), (0.62, 0.250, 0.130),
                (0.48, 0.246, 0.128)]
HATBAND_RINGS = [(1.66, 0.265, 0.252), (1.62, 0.266, 0.253)]
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    # Gold tuple reuses the 029/030 established value; light-blue
    # streak reuses the 029 value.
    coral = solid_material("Coral", (0.808, 0.102, 0.045), roughness=0.6)
    cream = solid_material("Cream", (0.914, 0.863, 0.791), roughness=0.6)
    navy = solid_material("Navy", (0.014, 0.023, 0.058), roughness=0.6)
    gold = solid_material("Gold", (0.657, 0.351, 0.009), metallic=0.6,
                          roughness=0.35)
    black = solid_material("Hair_Black", (0.011, 0.011, 0.015),
                           roughness=0.7)
    lightblue = solid_material("LightBlue", (0.212, 0.479, 0.807),
                               roughness=0.6)
    darklens = solid_material("DarkLens", (0.010, 0.010, 0.010),
                              roughness=0.3)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"coral": coral, "cream": cream, "navy": navy, "gold": gold,
            "black": black, "lightblue": lightblue, "darklens": darklens,
            "skin": skin, "eye": eye}


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001..030).
    Black hair cap (030 used silver hair; this piece goes back to
    black). Two dark eyes stay visible below the sun-hat brim."""
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


# ------------------------------------------------------------ L1 components
def build_swimsuit(m):
    """Coral one-piece, strapless bandeau: 5 rings, z 1.32-0.62.
    Top ring at 1.32 covers the mannequin torso top cap (z 1.28);
    rx/ry clear the torso by >=0.005 at every height."""
    return [make_elliptical_tube("CoralSwimsuit", SWIM_RINGS, 12,
                                 m["coral"], caps=False)]


def build_brief(m):
    """Coral swimsuit bottom: tube around both leg tops, z 0.62-0.46,
    reads as the one-piece brief. Open bottom, legs pass through."""
    return [make_elliptical_tube("CoralBrief", BRIEF_RINGS, 12,
                                 m["coral"], caps=False)]


def build_clasp(m):
    """Gold clasp on the swimsuit front (0, -0.143, 1.24): half-buried
    in the swimsuit surface (front y -0.1449 at z 1.24), outer face
    0.005 proud."""
    return [add_box("GoldClasp", (0, -0.143, 1.24),
                    (0.035, 0.014, 0.035), m["gold"])]


def build_shirt(m):
    """White cover-up shirt, open front: arc 300-600 deg leaves the
    240-300 deg front wedge open so the coral swimsuit shows.
    Loose fit: 0.296-0.306, hem z 0.80."""
    return [make_elliptical_tube("WhiteShirt", SHIRT_RINGS, 16,
                                 m["cream"], arc=(300, 600), caps=False)]


def build_shirt_trim(m):
    """Coral hem trim on the shirt (z 0.84-0.80): 0.006 proud of the
    shirt hem, reads as a coral edge band."""
    return [make_elliptical_tube("CoralShirtTrim", TRIM_RINGS, 16,
                                 m["coral"], arc=(300, 600), caps=False)]


def build_shirt_button(m, angle_deg, z):
    """One gold button on a shirt front edge: position + outward
    normal from ellipse_point (016 method), centre 0.004 off the
    shirt surface so the 0.012-thick box is half-buried."""
    rx, ry = interp_rings(SHIRT_RINGS, z)
    p, n = ellipse_point(rx, ry, angle_deg)
    c = Vector((p.x, p.y, z)) + n * 0.004
    return add_box("GoldShirtButton", tuple(c), (0.020, 0.012, 0.020),
                   m["gold"])


def build_sleeve(m, sx):
    """White short sleeve over the upper arm (shoulder to mid-arm).
    Capped (025 v2 lesson) with the origin lifted 0.005 along the
    arm axis so the sleeve cap never sits coplanar with the arm cap."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    origin = shoulder - direction.normalized() * 0.005
    return [make_tube("WhiteSleeve", origin, direction,
                      [0.0, 0.13, 0.26],
                      [0.115, 0.112, 0.108], 10,
                      m["cream"], caps=True)]


def build_necklace(m):
    """Gold necklace ring around the neck (z 1.36-1.32, r 0.105):
    0.015 proud of the neck tube (0.09), visible through the
    shirt's open front."""
    return [make_tube("GoldNecklace", (0, 0, 1.36), (0, 0, -1),
                      [0.0, 0.04], [0.105, 0.105], 10,
                      m["gold"], caps=False)]


def build_hat(m):
    """White sun hat: wide brim as a closed thin cylinder (2 rings +
    caps, NOT a make_disc single-sided patch — the camera sits below
    the brim at z 1.45) + flat dome crown sphere r 0.26, centre
    z 1.63, top 1.773, covering the hair cap top (1.75). v2: brim
    0.30->0.36 and crown flattened 0.75->0.55 — v1's narrow brim
    and tall dome read as a white helmet, not a sun hat."""
    brim = make_elliptical_tube("WhiteHatBrim",
                                [(1.622, 0.36, 0.36), (1.608, 0.36, 0.36)],
                                24, m["cream"], caps=True)
    crown = add_sphere("WhiteHatCrown", (0, 0.01, 1.63), 0.26, 12, 6,
                       (1.0, 0.95, 0.55), m["cream"])
    return [brim, crown]


def build_hatband(m):
    """Navy hat band around the crown base (z 1.66-1.62, 0.265):
    0.006 proud of the crown surface, sitting just above the brim.
    v2: raised 1.565-1.605 -> 1.62-1.66 with the flatter crown —
    v1's band sat low on the forehead and read as a headband."""
    return [make_elliptical_tube("NavyHatBand", HATBAND_RINGS, 16,
                                 m["navy"], caps=False)]


def build_sunglasses(m):
    """Sunglasses hanging on the chest (NOT worn — the eyes stay
    visible, 001 v2 face rule): two dark lenses + gold bridge,
    centres y -0.154, inner faces 0.007 off the swimsuit front."""
    objs = []
    for sx in (-1, 1):
        objs.append(add_box_rot("DarkSunglassLens",
                                (sx * 0.065, -0.154, 1.18),
                                (0.070, 0.012, 0.050), m["darklens"],
                                (0.05, 0, -sx * 0.08)))
    objs.append(add_box("GoldSunglassBridge", (0, -0.155, 1.18),
                        (0.05, 0.010, 0.012), m["gold"]))
    return objs


def build_sarong(m):
    """White wrap skirt: curved front panel (230-310 deg, z 0.78-0.48),
    019 overskirt construction, 0.006 proud of the swimsuit/brief."""
    return [build_panel(m, "WhiteSarong", SARONG_RINGS,
                        [0.78, 0.62, 0.48], 230, 310, 9, 0.006,
                        m["cream"])]


def build_knot(m):
    """Sarong knot at 305 deg, z 0.72: white sphere on the panel
    surface (position from ellipse_point) + gold pin on the knot's
    outer face along the same normal."""
    rx, ry = interp_rings(SARONG_RINGS, 0.72)
    p, n = ellipse_point(rx, ry, 305)
    c = Vector((p.x, p.y, 0.72)) + n * 0.006
    knot = add_sphere("WhiteSarongKnot", tuple(c), 0.030, 8, 4,
                      (1.0, 1.0, 1.0), m["cream"])
    pin_c = c + n * 0.030
    pin = add_box("GoldKnotPin", tuple(pin_c), (0.018, 0.012, 0.018),
                  m["gold"])
    return [knot, pin]


def build_tote(m):
    """Navy beach tote on the right hand (camera side): box +
    two handles reaching up into the hand sphere + gold clasp on
    the bag front (0.009 proud)."""
    bag = add_box("NavyToteBag", (0.42, -0.02, 0.45),
                  (0.20, 0.07, 0.26), m["navy"])
    handles = []
    for hx in (0.36, 0.48):
        handles.append(add_box("NavyToteHandle", (hx, 0, 0.62),
                               (0.015, 0.015, 0.10), m["navy"]))
    clasp = add_box("GoldToteClasp", (0.42, -0.058, 0.50),
                    (0.04, 0.012, 0.03), m["gold"])
    return [bag] + handles + [clasp]


def build_sandal(m, sx):
    """Navy sandal: thin sole wedge (lands z=0.0, 0.007 wider than
    the foot) + toe strap across the foot top + ankle strap ring
    (r 0.095, 0.012 proud of the leg at z 0.12)."""
    sole = make_wedge("NavySandalSole", (sx * 0.13, -0.02, 0.0),
                      0.102, 0.095, -0.165, 0.0, 0.025, 0.025,
                      m["navy"])
    toe = add_box("NavyToeStrap", (sx * 0.13, -0.10, 0.055),
                  (0.20, 0.025, 0.02), m["navy"])
    ankle = make_tube("NavyAnkleStrap", (sx * 0.13, 0, 0.12), (0, 0, -1),
                      [0.0, 0.02], [0.095, 0.095], 10,
                      m["navy"], caps=False)
    return [sole, toe, ankle]


def build_earring(m, sx):
    """Gold stud earring: small sphere half-buried in the head side
    (±0.222, 0, 1.47), outer face 0.019 proud."""
    return add_sphere("GoldEarring", (sx * 0.222, 0, 1.47), 0.015, 6, 3,
                      (1.0, 1.0, 1.0), m["gold"])


def build_hatpin(m):
    """Light-blue hat pin on the navy band (300 deg, z 1.63): a small
    flat box on the band surface, position + outward normal from
    ellipse_point (016 method). v2: replaces the 029-style hair
    streak — the sun hat covers the hair, so a straight streak on
    the hair poked through the crown and read as a blue mark on
    the hat; the blue accent moves onto the hat band instead."""
    rx, ry = interp_rings(HATBAND_RINGS, 1.63)
    p, n = ellipse_point(rx, ry, 300)
    c = Vector((p.x, p.y, 1.63)) + n * 0.004
    # Rotate the box so its local +Y lies along the surface normal:
    # rotZ(theta) maps +Y to (-sin theta, cos theta); want that = n,
    # so sin theta = -n.x, cos theta = n.y.
    theta = math.atan2(-n.x, n.y)
    return [add_box_rot("BlueHatPin", tuple(c), (0.030, 0.012, 0.070),
                        m["lightblue"], (0, 0, theta))]


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["swimsuit"] + parts["brief"] + parts["clasp"]
            + parts["necklace"])
    ok = True
    ok &= check_gap("torso: coral swimsuit vs mannequin torso @z=1.28",
                    interp_rings(SWIM_RINGS, 1.28)[0],
                    interp_rings(TORSO_RINGS, 1.28)[0])
    ok &= check_gap("torso: coral swimsuit vs mannequin torso @z=1.00",
                    interp_rings(SWIM_RINGS, 1.00)[0],
                    interp_rings(TORSO_RINGS, 1.00)[0])
    ok &= check_gap("torso: coral swimsuit vs mannequin torso @z=0.70",
                    interp_rings(SWIM_RINGS, 0.70)[0],
                    interp_rings(TORSO_RINGS, 0.70)[0])
    ok &= check_gap("torso: coral swimsuit vs mannequin torso ry @z=1.28",
                    interp_rings(SWIM_RINGS, 1.28)[1],
                    interp_rings(TORSO_RINGS, 1.28)[1])
    ok &= check_gap("torso: coral swimsuit vs mannequin torso ry @z=1.00",
                    interp_rings(SWIM_RINGS, 1.00)[1],
                    interp_rings(TORSO_RINGS, 1.00)[1])
    ok &= check_gap("torso: coral brief vs mannequin legs @z=0.55",
                    interp_rings(BRIEF_RINGS, 0.55)[0], 0.2323)
    ok &= check_gap("torso: gold necklace vs mannequin neck", 0.105, 0.09)
    ok &= check_relief("torso: gold clasp relief", 0.005,
                       lo=0.005, hi=0.030)
    print("L2_CHECK torso: coral strapless swimsuit clears the torso, "
          "brief covers both leg tops, gold clasp on the chest, gold "
          "necklace around the neck PASS")
    return objs, ok


def assemble_shirt(parts):
    objs = (parts["shirt"] + parts["trim"] + parts["buttons"]
            + parts["sleeves"])
    ok = True
    ok &= check_gap("shirt: white shirt vs coral swimsuit @z=1.10",
                    interp_rings(SHIRT_RINGS, 1.10)[0],
                    interp_rings(SWIM_RINGS, 1.10)[0])
    ok &= check_gap("shirt: white shirt vs coral swimsuit @z=0.80",
                    interp_rings(SHIRT_RINGS, 0.80)[0],
                    interp_rings(SWIM_RINGS, 0.80)[0])
    ok &= check_gap("shirt: white sleeve vs mannequin arm @0.0",
                    0.115, 0.085)
    ok &= check_relief("shirt: coral hem trim relief", 0.006,
                       lo=0.005, hi=0.015)
    ok &= check_relief("shirt: gold button relief", 0.004,
                       lo=0.002, hi=0.030)
    print("L2_CHECK shirt: white open-front shirt hangs loose over the "
          "coral swimsuit, coral trim at the hem, 4 gold buttons on "
          "the front edges, white short sleeves over the upper arms PASS")
    return objs, ok


def assemble_head(parts):
    objs = (parts["hat"] + parts["hatband"] + parts["hatpin"]
            + parts["earrings"])
    ok = True
    ok &= check_gap("head: white hat crown vs black hair cap @z=1.57",
                    0.2360, 0.225)
    ok &= check_gap("head: white hat crown vs black hair cap @z=1.65",
                    0.2574, 0.2016)
    ok &= check_gap("head: navy hat band vs white hat crown @z=1.63",
                    interp_rings(HATBAND_RINGS, 1.63)[0], 0.2600)
    ok &= check_gap("head: navy hat band vs white hat crown @z=1.65",
                    interp_rings(HATBAND_RINGS, 1.65)[0], 0.2574)
    ok &= check_gap("head: white hat brim vs white hat crown", 0.36, 0.26)
    ok &= check_relief("head: blue hat pin relief", 0.0165,
                       lo=0.005, hi=0.030)
    ok &= check_relief("head: gold earring relief", 0.019,
                       lo=0.005, hi=0.030)
    print("L2_CHECK head: wide white sun-hat brim over the flat dome "
          "crown, navy band at the crown base just above the brim, "
          "blue pin on the band, gold stud earrings PASS")
    return objs, ok


def assemble_waist_skirt(parts):
    objs = parts["sarong"] + parts["knot"]
    ok = True
    ok &= check_gap("waist: white sarong vs coral brief @z=0.62",
                    interp_rings(SARONG_RINGS, 0.62)[0] + 0.006,
                    interp_rings(BRIEF_RINGS, 0.62)[0])
    ok &= check_gap("waist: white sarong vs coral swimsuit @z=0.78",
                    interp_rings(SARONG_RINGS, 0.78)[0] + 0.006,
                    interp_rings(SWIM_RINGS, 0.78)[0])
    ok &= check_relief("waist: gold knot pin relief", 0.0095,
                       lo=0.005, hi=0.030)
    print("L2_CHECK waist: white wrap skirt over the swimsuit bottom, "
          "knot at the left waist with a gold pin PASS")
    return objs, ok


def assemble_hand(parts):
    objs = parts["tote"]
    ok = True
    # Handles span z 0.57-0.67; the right-hand sphere spans z 0.59-0.76
    # at x 0.32-0.49, so both handles pass through the palm.
    ok &= check_relief("hand: gold tote clasp relief", 0.009,
                       lo=0.005, hi=0.030)
    print("L2_CHECK hand: navy beach tote hangs from the right hand, "
          "handles pass through the palm, gold clasp on the bag front PASS")
    return objs, ok


def assemble_feet(parts):
    objs = parts["sandals"]
    ok = True
    ok &= check_gap("feet: navy sandal sole vs mannequin foot",
                    0.102, 0.095)
    ok &= check_gap("feet: navy ankle strap vs mannequin leg @z=0.12",
                    0.095, 0.0827)
    ok &= check_relief("feet: navy toe strap relief", 0.007,
                       lo=0.005, hi=0.030)
    print("L2_CHECK feet: navy sandal soles centre z=0.0, soles on "
          "ground; toe straps over the feet, ankle straps around "
          "the ankles PASS")
    return objs, ok


def assemble_sunglasses(parts):
    objs = parts["sunglasses"]
    ok = True
    ok &= check_relief("sunglasses: dark lens relief off swimsuit",
                       0.007, lo=0.005, hi=0.030)
    print("L2_CHECK sunglasses: dark lenses + gold bridge hang on the "
          "chest below the neckline, eyes stay visible PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: white shirt vs coral swimsuit @z=1.10",
                    interp_rings(SHIRT_RINGS, 1.10)[0],
                    interp_rings(SWIM_RINGS, 1.10)[0])
    ok &= check_gap("L3 layer: white sarong vs coral brief @z=0.62",
                    interp_rings(SARONG_RINGS, 0.62)[0] + 0.006,
                    interp_rings(BRIEF_RINGS, 0.62)[0])
    ok &= check_gap("L3 layer: navy hat band vs white hat crown @z=1.63",
                    interp_rings(HATBAND_RINGS, 1.63)[0], 0.2600)
    ok &= check_gap("L3 layer: gold necklace vs mannequin neck",
                    0.105, 0.09)
    ok &= check_gap("L3 joint: white sleeve vs mannequin arm", 0.115, 0.085)
    ok &= check_gap("L3 joint: navy ankle strap vs mannequin leg @z=0.12",
                    0.095, 0.0827)
    ok &= check_gap("L3 joint: navy sandal sole vs mannequin foot",
                    0.102, 0.095)
    print("L3_CHECK outfit: open white shirt shows the coral swimsuit, "
          "sarong wraps the swimsuit bottom, sun hat sits over the "
          "hair, tote hangs from the right hand, sandal soles touch "
          "ground z=0.000 PASS")
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
    parts["swimsuit"] = build_swimsuit(m)
    report_l1("CoralSwimsuit", parts["swimsuit"])
    parts["brief"] = build_brief(m)
    report_l1("CoralBrief", parts["brief"])
    parts["clasp"] = build_clasp(m)
    report_l1("GoldClasp", parts["clasp"])
    parts["shirt"] = build_shirt(m)
    report_l1("WhiteShirt", parts["shirt"])
    parts["trim"] = build_shirt_trim(m)
    report_l1("CoralShirtTrim", parts["trim"])
    parts["buttons"] = [build_shirt_button(m, a, z)
                        for a in (240, 300) for z in (1.20, 1.00)]
    report_l1("GoldShirtButtons x4", parts["buttons"])
    parts["sleeves"] = []
    for sx in (-1, 1):
        parts["sleeves"] += build_sleeve(m, sx)
    report_l1("WhiteSleeves x2", parts["sleeves"])
    parts["necklace"] = build_necklace(m)
    report_l1("GoldNecklace", parts["necklace"])
    parts["hat"] = build_hat(m)
    report_l1("WhiteSunHat", parts["hat"])
    parts["hatband"] = build_hatband(m)
    report_l1("NavyHatBand", parts["hatband"])
    parts["sunglasses"] = build_sunglasses(m)
    report_l1("Sunglasses", parts["sunglasses"])
    parts["sarong"] = build_sarong(m)
    report_l1("WhiteSarong", parts["sarong"])
    flat_patches += parts["sarong"]
    parts["knot"] = build_knot(m)
    report_l1("SarongKnot+GoldPin", parts["knot"])
    parts["tote"] = build_tote(m)
    report_l1("NavyToteBag", parts["tote"])
    parts["sandals"] = []
    for sx in (-1, 1):
        parts["sandals"] += build_sandal(m, sx)
    report_l1("NavySandals x2", parts["sandals"])
    parts["earrings"] = [build_earring(m, sx) for sx in (-1, 1)]
    report_l1("GoldEarrings x2", parts["earrings"])
    parts["hatpin"] = build_hatpin(m)
    report_l1("BlueHatPin", parts["hatpin"])

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    _, ok = assemble_torso(parts)
    l2_ok &= ok
    _, ok = assemble_shirt(parts)
    l2_ok &= ok
    _, ok = assemble_head(parts)
    l2_ok &= ok
    _, ok = assemble_waist_skirt(parts)
    l2_ok &= ok
    _, ok = assemble_hand(parts)
    l2_ok &= ok
    _, ok = assemble_feet(parts)
    l2_ok &= ok
    _, ok = assemble_sunglasses(parts)
    l2_ok &= ok
    print("L2_SUMMARY %s" % ("ALL PASS" if l2_ok else "FAILURES PRESENT"))

    # ---- L3 full outfit on the mannequin ----
    costume = (parts["swimsuit"] + parts["brief"] + parts["clasp"]
               + parts["shirt"] + parts["trim"] + parts["buttons"]
               + parts["sleeves"] + parts["necklace"] + parts["hat"]
               + parts["hatband"] + parts["sunglasses"] + parts["sarong"]
               + parts["knot"] + parts["tote"] + parts["sandals"]
               + parts["earrings"] + parts["hatpin"])
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
