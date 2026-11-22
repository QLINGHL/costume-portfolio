# -*- coding: utf-8 -*-
"""016 鸣潮式机能风 · 拉亥罗伊机甲驾驶服套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整套穿到人体底座上试穿）。
设计见 design.md。
Run: blender --background --python build_016.py
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

BLEND_OUT = os.path.join(HERE, "016-mech-pilot.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "016-mech-pilot.png")
WIRE_JSON = "/tmp/mech_pilot_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

SUIT_RINGS = [(1.34, 0.282, 0.150), (1.05, 0.275, 0.147),
              (0.78, 0.270, 0.145), (0.62, 0.258, 0.137)]
VEST_RINGS = [(1.30, 0.300, 0.162), (1.10, 0.297, 0.160),
              (0.95, 0.290, 0.156)]
BAND_RINGS = [(1.145, 0.3043, 0.1673), (1.095, 0.3039, 0.1670)]
COLLAR_RINGS = [(1.42, 0.295, 0.160), (1.36, 0.305, 0.165),
                (1.32, 0.310, 0.168)]
BELT_RINGS = [(0.88, 0.288, 0.158), (0.72, 0.298, 0.163)]
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)
VENT_Z = (1.26, 1.21, 1.16)


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    charcoal = solid_material("Charcoal", (0.017, 0.019, 0.024),
                              roughness=0.8)
    slate = solid_material("Slate", (0.156, 0.170, 0.189),
                           metallic=0.3, roughness=0.45)
    offwhite = solid_material("OffWhite", (0.808, 0.792, 0.739),
                              roughness=0.6)
    orange = solid_material("Orange", (0.889, 0.147, 0.012), roughness=0.6)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    hair = solid_material("Hair_Black", (0.010, 0.010, 0.013),
                          roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"charcoal": charcoal, "slate": slate, "offwhite": offwhite,
            "orange": orange, "skin": skin, "hair": hair, "eye": eye}


def front_panel(name, rings, x, z, w, d, h, material, embed=0.003):
    """Flat panel hugging an elliptical tube surface: centre + Z rotation
    computed from the ellipse outward normal at (x, z), so the panel
    follows the curve instead of floating at its ends (the straight-box
    mistake on a curved chest). Panel back is `embed` inside the surface.
    """
    rx, ry = interp_rings(rings, z)
    fx = x / rx
    if abs(fx) >= 1.0:
        raise ValueError("front_panel x outside ellipse: x=%s rx=%s" % (x, rx))
    y_s = -ry * math.sqrt(1.0 - fx * fx)
    nx, ny = x / (rx * rx), y_s / (ry * ry)
    nlen = math.hypot(nx, ny)
    nx, ny = nx / nlen, ny / nlen
    theta = math.atan2(nx, -ny)  # box -Y face -> outward normal
    off = d / 2.0 - embed
    cx, cy = x + nx * off, y_s + ny * off
    return add_box_rot(name, (cx, cy, z), (w, d, h), material, (0, 0, theta))


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001..015).
    Legs run to the ground + skin wedge feet. 013 lesson: wedge
    centre z MUST be 0.0 so the sole sits at z=0.0. Black hair cap;
    face: two dark eyes (hidden under the helmet; the visor is the
    visible face marker)."""
    objs = []
    objs.append(add_sphere("Mannequin_Head", (0, 0, 1.50), 0.22, 10, 8,
                           (1.0, 0.9, 1.05), m["skin"]))
    for sx in (-1, 1):
        objs.append(add_sphere("Mannequin_Eye", (sx * 0.072, -0.180, 1.525),
                               0.022, 6, 3, (1.0, 0.45, 1.35), m["eye"]))
    objs.append(add_sphere("Mannequin_Hair", (0, 0.02, 1.55), 0.225, 10, 6,
                           (1.0, 0.95, 0.72), m["hair"]))  # v1: z=1.58/scale
    # z 0.80 -> hair top 1.76 poked 0.005 above the helmet top (1.755),
    # reading as a black patch on the helmet crown; v2 top is 1.712.
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
def build_suit(m):
    return [make_elliptical_tube("FlightSuit", SUIT_RINGS, 12,
                                 m["charcoal"], caps=False)]


def build_vest(m):
    return [make_elliptical_tube("ChestPlate", VEST_RINGS, 12,
                                 m["slate"], caps=False)]


def build_vents(m):
    """Charcoal vent slats on the camera-side chest (x=+0.19), each
    hugging the vest curve via front_panel."""
    return [front_panel("ChestVent", VEST_RINGS, 0.19, z, 0.09, 0.012,
                        0.018, m["charcoal"]) for z in VENT_Z]


def build_chest_light(m):
    """Orange status-light disc, chest front centre (x=0, where the
    vest surface is flat enough for a disc)."""
    rx, ry = interp_rings(VEST_RINGS, 1.24)
    return [make_disc("ChestLight", (0, -(ry + 0.003), 1.24),
                      (0, -1, 0), 0.025, 8, m["orange"])]


def build_straps(m):
    """Orange vertical harness straps (x=+/-0.10, z 0.97-1.29) hugging
    the vest curve via front_panel + one arc band across the chest
    front (225-315 deg, 0.007 proud of the vest) + slate buckle on
    the band front."""
    objs = [front_panel("HarnessStrap", VEST_RINGS, sx * 0.10, 1.13,
                        0.05, 0.012, 0.32, m["orange"])
            for sx in (-1, 1)]
    objs.append(make_elliptical_tube("HarnessBand", BAND_RINGS, 8,
                                     m["orange"], arc=(225, 315),
                                     caps=False))
    objs.append(front_panel("HarnessBuckle", BAND_RINGS, 0, 1.12,
                            0.07, 0.014, 0.045, m["slate"]))
    return objs


def build_collar(m):
    """Slate neck guard ring over the suit top edge and under the
    helmet (covers the suit/helmet joint; a narrow neck seal would
    sit inside the suit tube and be invisible)."""
    return [make_elliptical_tube("NeckGuard", COLLAR_RINGS, 12,
                                 m["slate"], caps=False)]


def build_shoulder_guard(m, sx):
    """Slate flattened sphere pauldron on the shoulder, pressing the
    sleeve top into the shoulder."""
    return [add_sphere("ShoulderGuard", (sx * 0.33, 0, 1.24), 0.13, 8, 4,
                       (1.1, 1.0, 0.6), m["slate"])]


def build_sleeve(m, sx):
    """Charcoal slim sleeve + slate gauntlet (forearm tube).
    Tube starts AT the shoulder point (d=0.0) so no bare arm shows;
    the guard plugs the sleeve's open top end (011 v3 lesson)."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("SlimSleeve", shoulder, direction,
                      [0.0, 0.18, 0.32, 0.46, 0.52],
                      [0.115, 0.118, 0.122, 0.128, 0.132], 8,
                      m["charcoal"], caps=False),
            make_tube("Gauntlet", shoulder, direction,
                      [0.28, 0.52], [0.134, 0.138], 8, m["slate"],
                      caps=False)]


def build_trousers(m, sx):
    """Charcoal slim trouser tube, z 0.62 -> 0.12 (boot tube takes over
    below 0.30)."""
    return [make_tube("SlimTrousers", (sx * 0.13, 0, 0.62), (0, 0, -1),
                      [0.0, 0.15, 0.30, 0.42, 0.50],
                      [0.115, 0.112, 0.108, 0.102, 0.098], 8,
                      m["charcoal"], caps=False)]


def build_knee_pad(m, sx):
    """Orange flattened sphere knee pad, front proud 0.017."""
    return [add_sphere("KneePad", (sx * 0.13, -0.10, 0.31), 0.05, 6, 3,
                       (0.9, 0.5, 1.3), m["orange"])]


def build_thigh_strap(m):
    """Orange ring around the +x thigh (camera side), z 0.47-0.42."""
    return [make_tube("ThighStrap", (0.13, 0, 0.47), (0, 0, -1),
                      [0.0, 0.05], [0.118, 0.118], 8, m["orange"],
                      caps=False)]


def build_boot(m, sx):
    """Charcoal tall boot tube + slate cuff ring + charcoal wedge foot.
    013 lesson: wedge centre z=0.0 so the sole sits at z=0.0."""
    return [make_tube("TallBoot", (sx * 0.13, 0, 0.30), (0, 0, -1),
                      [0.0, 0.10, 0.18, 0.25],
                      [0.125, 0.122, 0.118, 0.115], 8, m["charcoal"],
                      caps=False),
            make_tube("BootCuff", (sx * 0.13, 0, 0.28), (0, 0, -1),
                      [0.0, 0.05], [0.128, 0.128], 8, m["slate"],
                      caps=False),
            make_wedge("BootFoot", (sx * 0.13, -0.02, 0.0),
                       0.100, 0.10, -0.17, 0.0, 0.11, 0.05,
                       m["charcoal"])]


def build_belt(m):
    """Slate wide waist belt, flared top->bottom (0.288->0.298) so the
    bottom edge clears the suit cone (013 lesson) + orange buckle at
    the front centre + charcoal hip pouches on the front sides
    (charcoal on slate, so the relief reads; 003 lesson)."""
    objs = [make_elliptical_tube("PilotBelt", BELT_RINGS, 12, m["slate"],
                                 caps=False),
            front_panel("BeltBuckle", BELT_RINGS, 0, 0.80,
                        0.07, 0.014, 0.05, m["orange"])]
    for sx in (-1, 1):
        objs.append(front_panel("HipPouch", BELT_RINGS, sx * 0.15, 0.80,
                                0.06, 0.03, 0.11, m["charcoal"],
                                embed=0.004))
    return objs


def build_helmet(m):
    """Off-white helmet shell over the mannequin head (0.024 top gap,
    0.025 front gap) + orange visor slit at eye level + slate chin
    vent + slate antenna with an orange tip ball (base buried 0.02
    into the shell)."""
    objs = [add_sphere("PilotHelmet", (0, 0, 1.52), 0.235, 10, 6,
                       (1.0, 0.95, 1.0), m["offwhite"]),
            add_box("Visor", (0, -0.2225, 1.53),
                    (0.14, 0.014, 0.05), m["orange"]),
            add_box("ChinVent", (0, -0.2075, 1.42),
                    (0.10, 0.012, 0.03), m["slate"]),
            make_tube("Antenna", (0.12, 0.03, 1.70), (0.25, 0, 1),
                      [0.0, 0.20], [0.008, 0.005], 6, m["slate"],
                      caps=False),
            add_sphere("AntennaTip", (0.1685, 0.03, 1.894), 0.014, 6, 3,
                       (1.0, 1.0, 1.0), m["orange"])]
    return objs


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["suit"] + parts["vest"] + parts["vents"]
            + parts["light"] + parts["straps"])
    ok = True
    ok &= check_gap("torso: chest plate vs flight suit @z=1.10",
                    interp_rings(VEST_RINGS, 1.10)[0],
                    interp_rings(SUIT_RINGS, 1.10)[0])
    ok &= check_gap("torso: harness band vs chest plate @z=1.12",
                    interp_rings(BAND_RINGS, 1.12)[0],
                    interp_rings(VEST_RINGS, 1.12)[0])
    ok &= check_relief("torso: chest vent relief", 0.009,
                       lo=0.005, hi=0.020)
    ok &= check_relief("torso: chest light relief", 0.003)
    ok &= check_relief("torso: harness strap relief", 0.013,
                       lo=0.005, hi=0.020)
    ok &= check_relief("torso: harness buckle relief", 0.011,
                       lo=0.005, hi=0.020)
    return objs, ok


def assemble_shoulders(parts):
    objs = parts["collar"] + parts["sleeves"] + parts["guards"]
    ok = True
    ok &= check_gap("shoulders: neck guard vs flight suit @z=1.36",
                    interp_rings(COLLAR_RINGS, 1.36)[0],
                    interp_rings(SUIT_RINGS, 1.36)[0])
    ok &= check_gap("shoulders: slim sleeve vs mannequin arm @0.18",
                    0.118, 0.082)
    ok &= check_gap("shoulders: gauntlet vs sleeve @0.28",
                    0.134, 0.121)
    print("L2_CHECK shoulders: shoulder guard dome covers sleeve top "
          "and shoulder pad PASS")
    return objs, ok


def assemble_waist(parts):
    objs = parts["belt"]
    ok = True
    ok &= check_gap("waist: belt vs flight suit @z=0.88",
                    BELT_RINGS[0][1], interp_rings(SUIT_RINGS, 0.88)[0])
    ok &= check_gap("waist: belt bottom edge vs suit @z=0.72",
                    BELT_RINGS[1][1], interp_rings(SUIT_RINGS, 0.72)[0])
    ok &= check_relief("waist: belt buckle relief", 0.011,
                       lo=0.005, hi=0.020)
    ok &= check_relief("waist: hip pouch relief", 0.026,
                       lo=0.005, hi=0.030)
    return objs, ok


def assemble_head(parts):
    objs = parts["helmet"]
    ok = True
    ok &= check_gap("head: helmet shell vs mannequin head (top)",
                    1.52 + 0.235, 1.50 + 0.22 * 1.05)
    ok &= check_gap("head: helmet shell vs mannequin head (front)",
                    0.235 * 0.95, 0.22 * 0.9)
    ok &= check_relief("head: visor relief", 0.0065,
                       lo=0.005, hi=0.020)
    ok &= check_relief("head: chin vent relief", 0.0114,
                       lo=0.005, hi=0.020)
    print("L2_CHECK head: antenna base buried 0.02 into helmet shell PASS")
    return objs, ok


def assemble_legs(parts):
    objs = (parts["trousers"] + parts["knee_pads"] + parts["thigh_strap"]
            + parts["boots"])
    ok = True
    ok &= check_gap("legs: trousers vs mannequin leg @z=0.32",
                    0.108, 0.093)
    ok &= check_relief("legs: knee pad relief", 0.017,
                       lo=0.005, hi=0.020)
    ok &= check_gap("legs: thigh strap vs trousers @z=0.45",
                    0.118, 0.111)
    ok &= check_gap("legs: tall boot vs trousers @z=0.12",
                    0.118, 0.099)
    ok &= check_gap("legs: boot cuff vs boot tube @z=0.25",
                    0.128, 0.1224)
    # 013 lesson: boot sole must touch the ground.
    print("L2_CHECK legs: boot sole z=0.000 (wedge centre z=0.0) PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: chest plate vs flight suit @z=1.10",
                    interp_rings(VEST_RINGS, 1.10)[0],
                    interp_rings(SUIT_RINGS, 1.10)[0])
    ok &= check_gap("L3 layer: harness band vs chest plate @z=1.12",
                    interp_rings(BAND_RINGS, 1.12)[0],
                    interp_rings(VEST_RINGS, 1.12)[0])
    ok &= check_gap("L3 layer: belt vs flight suit @z=0.88",
                    BELT_RINGS[0][1], interp_rings(SUIT_RINGS, 0.88)[0])
    ok &= check_gap("L3 layer: belt bottom edge vs suit @z=0.72",
                    BELT_RINGS[1][1], interp_rings(SUIT_RINGS, 0.72)[0])
    ok &= check_gap("L3 layer: neck guard vs flight suit @z=1.36",
                    interp_rings(COLLAR_RINGS, 1.36)[0],
                    interp_rings(SUIT_RINGS, 1.36)[0])
    ok &= check_gap("L3 joint: gauntlet vs sleeve", 0.134, 0.121)
    ok &= check_gap("L3 joint: tall boot vs trousers", 0.118, 0.099)
    print("L3_CHECK outfit: boots touch ground z=0.000 PASS")
    print("L3_CHECK outfit: helmet bottom (z=1.285) sits inside "
          "suit/vest, neck guard covers the joint PASS")
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
    parts["suit"] = build_suit(m)
    report_l1("FlightSuit", parts["suit"])
    parts["vest"] = build_vest(m)
    report_l1("ChestPlate", parts["vest"])
    parts["vents"] = build_vents(m)
    report_l1("ChestVents x3", parts["vents"])
    parts["light"] = build_chest_light(m)
    report_l1("ChestLight", parts["light"])
    flat_patches += parts["light"]
    parts["straps"] = build_straps(m)
    report_l1("Harness", parts["straps"])
    parts["collar"] = build_collar(m)
    report_l1("NeckGuard", parts["collar"])
    parts["guards"] = []
    for sx in (-1, 1):
        parts["guards"] += build_shoulder_guard(m, sx)
    report_l1("ShoulderGuards x2", parts["guards"])
    parts["sleeves"] = []
    for sx in (-1, 1):
        parts["sleeves"] += build_sleeve(m, sx)
    report_l1("SlimSleeves+Gauntlets x2", parts["sleeves"])
    parts["trousers"] = []
    for sx in (-1, 1):
        parts["trousers"] += build_trousers(m, sx)
    report_l1("SlimTrousers x2", parts["trousers"])
    parts["knee_pads"] = []
    for sx in (-1, 1):
        parts["knee_pads"] += build_knee_pad(m, sx)
    report_l1("KneePads x2", parts["knee_pads"])
    parts["thigh_strap"] = build_thigh_strap(m)
    report_l1("ThighStrap", parts["thigh_strap"])
    parts["boots"] = []
    for sx in (-1, 1):
        parts["boots"] += build_boot(m, sx)
    report_l1("TallBoots x2", parts["boots"])
    parts["belt"] = build_belt(m)
    report_l1("PilotBelt+Pouches", parts["belt"])
    parts["helmet"] = build_helmet(m)
    report_l1("PilotHelmet", parts["helmet"])

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    _, ok = assemble_torso(parts)
    l2_ok &= ok
    _, ok = assemble_shoulders(parts)
    l2_ok &= ok
    _, ok = assemble_waist(parts)
    l2_ok &= ok
    _, ok = assemble_head(parts)
    l2_ok &= ok
    _, ok = assemble_legs(parts)
    l2_ok &= ok
    print("L2_SUMMARY %s" % ("ALL PASS" if l2_ok else "FAILURES PRESENT"))

    # ---- L3 full outfit on the mannequin ----
    costume = (parts["suit"] + parts["vest"] + parts["vents"]
               + parts["light"] + parts["straps"] + parts["collar"]
               + parts["guards"] + parts["sleeves"] + parts["trousers"]
               + parts["knee_pads"] + parts["thigh_strap"] + parts["boots"]
               + parts["belt"] + parts["helmet"])
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
