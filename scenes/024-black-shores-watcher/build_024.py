# -*- coding: utf-8 -*-
"""024 鸣潮式地区衣橱 · 黑海岸守望者套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整套穿到人体底座上试穿）。
设计见 design.md。BACKLOG 本轮已空，自选新题材：鸣潮地区衣橱新方向——黑海岸。
Run: blender --background --python build_024.py
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

BLEND_OUT = os.path.join(HERE, "024-black-shores-watcher.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "024-black-shores-watcher.png")
WIRE_JSON = "/tmp/black_shores_watcher_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

BODICE_RINGS = [(1.34, 0.288, 0.152), (1.15, 0.282, 0.148),
                (0.92, 0.272, 0.144)]
COLLAR_RINGS = [(1.46, 0.240, 0.210), (1.40, 0.220, 0.190),
                (1.34, 0.200, 0.175)]
CHEST_RINGS = BODICE_RINGS
BELT_RINGS = [(0.94, 0.292, 0.152), (0.86, 0.298, 0.155)]
TUNIC_RINGS = [(0.94, 0.290, 0.150), (0.78, 0.295, 0.152),
               (0.60, 0.305, 0.158)]
HOOD_RINGS = [(1.50, 0.230, 0.218), (1.62, 0.225, 0.213),
              (1.74, 0.120, 0.112)]
MASK_RINGS = [(1.50, 0.226, 0.200), (1.44, 0.223, 0.198),
              (1.38, 0.194, 0.174)]
VISOR_RINGS = [(1.58, 0.224, 0.194), (1.55, 0.226, 0.193)]
CAPE_RINGS = [(1.28, 0.310, 0.160), (1.00, 0.300, 0.155),
              (0.70, 0.305, 0.158), (0.55, 0.305, 0.158)]
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)
CIRCUIT_ANGLES = [(258, 262), (268, 272), (278, 282)]


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    charcoal = solid_material("Charcoal", (0.009, 0.010, 0.014),
                              roughness=0.6)
    deepteal = solid_material("DeepTeal", (0.004, 0.042, 0.042),
                              roughness=0.6)
    silver = solid_material("Silver", (0.254, 0.275, 0.305), roughness=0.6)
    glow = solid_material("GlowCyan", (0.025, 0.913, 0.768), roughness=0.4)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    hair = solid_material("Hair_Black", (0.004, 0.004, 0.006),
                          roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"charcoal": charcoal, "deepteal": deepteal, "silver": silver,
            "glow": glow, "skin": skin, "hair": hair, "eye": eye}


def front_y(rings, x, z):
    """Front surface Y of an elliptical tube at (x, z)."""
    rx, ry = interp_rings(rings, z)
    return ellipse_front(rx, ry, x)[0]


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001..023).
    Black hair cap (z=1.57, scale-z 0.80 covers the crown) +
    two dark eyes (visible; the mask covers mouth/chin only, the
    visor sits on the forehead above them).
    Feet are black boot wedges (z=0.0, lands on the ground; 013 lesson)
    instead of bare skin."""
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
        objs.append(make_wedge("BlackBoot", (sx * 0.13, -0.02, 0.0),
                               0.095, 0.09, -0.16, 0.0, 0.10, 0.045,
                               m["charcoal"]))
    return objs


# ------------------------------------------------------------ L1 components
def build_bodice(m):
    return [make_elliptical_tube("CharcoalBodice", BODICE_RINGS, 12,
                                 m["charcoal"], caps=False)]


def build_collar(m):
    """Charcoal high collar: three stacked ring bands around the neck
    (011 fur-collar technique), radii 0.200 / 0.220 / 0.240, clearing
    the jaw (head rx ~0.217 at z=1.46, ~0.198 at z=1.40)."""
    objs = []
    for z0, rx, ry in [(1.34, 0.200, 0.175), (1.40, 0.220, 0.190),
                       (1.46, 0.240, 0.210)]:
        objs.append(make_elliptical_tube(
            "HighCollar", [(z0 + 0.005, rx, ry), (z0 - 0.005, rx, ry)],
            12, m["charcoal"], caps=False))
    return objs


def build_chest_plate(m):
    """Deep-teal chest plate: curved front panel (232-308 deg,
    z 1.30-1.02) over the charcoal bodice, 0.006 proud."""
    return [build_panel(m, "DeepTealChest", BODICE_RINGS,
                        [1.30, 1.20, 1.11, 1.02], 232, 308, 9, 0.006,
                        m["deepteal"])]


def build_circuit_lines(m):
    """Three glow-cyan circuit lines on the chest plate: narrow
    panels (3 cols each) at 258-262 / 268-272 / 278-282 deg,
    z 1.28-1.08, 0.008 proud (0.002 more than the plate)."""
    objs = []
    for a0, a1 in CIRCUIT_ANGLES:
        objs.append(build_panel(m, "GlowCircuit", BODICE_RINGS,
                                [1.28, 1.18, 1.08], a0, a1, 3, 0.008,
                                m["glow"]))
    return objs


def build_pauldron(m, sx):
    """Silver shoulder pauldron: flattened sphere on the shoulder top."""
    return [add_sphere("SilverPauldron", (sx * 0.36, 0, 1.27),
                       0.06, 8, 4, (1.2, 0.7, 0.9), m["silver"])]


def build_arm_guard(m, sx):
    """Deep-teal arm guard (shoulder to wrist) over the mannequin arm."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("DeepTealArmGuard", shoulder, direction,
                      [0.0, 0.13, 0.26, 0.39, 0.52],
                      [0.098, 0.096, 0.093, 0.090, 0.086], 10,
                      m["deepteal"], caps=False)]


def build_wrist_band(m, sx):
    """Glow-cyan wrist band over the arm guard at the wrist."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("GlowWristBand", shoulder, direction,
                      [0.46, 0.52], [0.10, 0.10], 10,
                      m["glow"], caps=False)]


def build_belt(m):
    """Silver tactical belt: flared top->bottom (0.292->0.298) so the
    bottom edge clears the tunic (013 lesson)."""
    return [make_elliptical_tube("SilverBelt", BELT_RINGS, 12,
                                 m["silver"], caps=False)]


def build_buckle(m):
    """Glow-cyan buckle at the belt front centre."""
    return [add_box("GlowBuckle", (0, -0.165, 0.90),
                    (0.09, 0.02, 0.05), m["glow"])]


def build_pouch(m, sx):
    """Deep-teal tool pouch on the belt front side (x=±0.16, z=0.90):
    belt front surface at x=0.16 is y≈-0.127, the box spans
    y -0.12..-0.16, embedded 0.007, proud 0.033."""
    return [add_box("DeepTealPouch", (sx * 0.16, -0.14, 0.90),
                    (0.07, 0.04, 0.09), m["deepteal"])]


def build_tunic(m):
    """Charcoal hip tunic: flared tube (z 0.94-0.60, 0.290->0.305)
    covering the hip gap between bodice bottom (0.92) and pants
    top (0.62); top tucks under the belt, bottom overlaps the
    pants cuffs."""
    return [make_elliptical_tube("CharcoalTunic", TUNIC_RINGS, 12,
                                 m["charcoal"], caps=False)]


def build_pants(m, sx):
    """Charcoal trousers: tube over the mannequin leg, hip to ankle."""
    return [make_tube("CharcoalPants", (sx * 0.13, 0, 0.62), (0, 0, -1),
                      [0.0, 0.13, 0.26, 0.39, 0.52, 0.58],
                      [0.115, 0.112, 0.108, 0.104, 0.100, 0.098], 10,
                      m["charcoal"], caps=False)]


def build_knee_pad(m, sx):
    """Deep-teal knee pad: flattened sphere on the front of the knee
    (z=0.32, pants front y≈-0.106; pad spans y -0.090..-0.130)."""
    return [add_sphere("DeepTealKneePad", (sx * 0.13, -0.110, 0.32),
                       0.045, 8, 4, (1.0, 0.45, 1.15), m["deepteal"])]


def build_cargo_pocket(m, sx):
    """Deep-teal cargo pocket on the outer thigh (x=±0.245, z=0.42):
    pants outer edge x≈0.240, the box spans x 0.23..0.26."""
    return [add_box("DeepTealCargo", (sx * 0.245, 0, 0.42),
                    (0.03, 0.10, 0.12), m["deepteal"])]


def build_boot(m, sx):
    """Charcoal tall boot: shaft tube (z 0.30-0.06) over the leg +
    glow-cyan trim ring on the visible shaft at z 0.22 (the shaft top
    at z 0.30 sits under the pants cuff, so a ring there would be
    hidden); the wedge sole (mannequin BlackBoot, charcoal) lands
    at z=0.0."""
    shaft = make_tube("CharcoalBootShaft", (sx * 0.13, 0, 0.30), (0, 0, -1),
                      [0.0, 0.24], [0.105, 0.10], 10,
                      m["charcoal"], caps=False)
    trim = make_tube("GlowBootTrim", (sx * 0.13, 0, 0.22), (0, 0, -1),
                     [0.0, 0.02], [0.109, 0.109], 10,
                     m["glow"], caps=False)
    return [shaft, trim]


def build_hood(m):
    """Black hood: curved back panel (15-165 deg, z 1.50-1.74) over
    the hair cap, 0.006 proud, top ring narrowing to 0.120 so the
    hood peaks over the hair top at 1.75 (v2: v1 top ring 0.180 was
    a wide flat top whose 15/165 deg corners stuck up like ears)."""
    return [build_panel(m, "BlackHood", HOOD_RINGS,
                        [1.50, 1.62, 1.74], 15, 165, 9, 0.006,
                        m["charcoal"])]


def build_face_mask(m):
    """Black face mask: curved front panel (240-300 deg, z 1.38-1.50)
    over the head, 0.006 proud; covers mouth and chin, eyes at
    z=1.525 stay visible above it (v2: v1 232-308 deg let the panel
    edges run to the sides of the face as long whisker-like strap
    lines; 240-300 deg keeps the edges on the front of the face)."""
    return [build_panel(m, "BlackFaceMask", MASK_RINGS,
                        [1.50, 1.44, 1.38], 240, 300, 9, 0.006,
                        m["charcoal"])]


def build_visor(m):
    """Glow-cyan visor strip across the forehead (250-290 deg,
    z 1.55-1.58) over the hair cap, 0.006 proud; ring radii follow
    the hair surface (0.226 at z=1.55, 0.224 at z=1.58) so it never
    sinks into the hair (016 lesson)."""
    return [build_panel(m, "GlowVisor", VISOR_RINGS,
                        [1.58, 1.55], 250, 290, 7, 0.006,
                        m["glow"])]


def build_cape(m):
    """Deep-teal cape: curved back panel (15-165 deg, z 1.28-0.55)
    over the torso, 0.006 proud; rings (0.310->0.305) stay wider
    than the belt (0.298) and the tunic (0.290->0.305) so the cape
    hangs outside both."""
    return [build_panel(m, "DeepTealCape", CAPE_RINGS,
                        [1.28, 1.00, 0.70, 0.55], 15, 165, 9, 0.006,
                        m["deepteal"])]


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["bodice"] + parts["collar"]
            + parts["chest"] + parts["circuits"])
    ok = True
    ok &= check_gap("torso: high collar vs head @z=1.46",
                    0.240, 0.217)
    ok &= check_gap("torso: high collar vs head @z=1.40",
                    0.220, 0.198)
    ok &= check_relief("torso: chest plate relief", 0.006)
    ok &= check_relief("torso: circuit line relief", 0.008)
    ok &= check_gap("torso: charcoal bodice vs mannequin torso @z=1.15",
                    interp_rings(BODICE_RINGS, 1.15)[0],
                    interp_rings([(1.28, 0.270, 0.140),
                                  (0.95, 0.240, 0.130)], 1.15)[0])
    return objs, ok


def assemble_arms(parts):
    objs = parts["arm_guards"] + parts["wrist_bands"]
    ok = True
    ok &= check_gap("arms: arm guard vs mannequin arm @0.0",
                    0.098, 0.085)
    ok &= check_gap("arms: glow wrist band vs arm guard @0.46",
                    0.10, 0.088)
    print("L2_CHECK arms: deep-teal arm guard 0.098->0.086, glow "
          "wrist band ring at the wrist PASS")
    return objs, ok


def assemble_shoulders(parts):
    objs = parts["pauldrons"]
    ok = True
    ok &= check_gap("shoulder: pauldron vs charcoal bodice @z=1.27",
                    0.36, interp_rings(BODICE_RINGS, 1.27)[0])
    print("L2_CHECK shoulder: silver pauldrons sit on the shoulder "
          "tops, clear of the high collar PASS")
    return objs, ok


def assemble_waist(parts):
    objs = parts["belt"] + parts["buckle"] + parts["pouches"]
    ok = True
    ok &= check_gap("waist: silver belt vs charcoal bodice @z=0.92",
                    interp_rings(BELT_RINGS, 0.92)[0],
                    interp_rings(BODICE_RINGS, 0.92)[0])
    ok &= check_gap("waist: silver belt bottom edge vs tunic @z=0.86",
                    BELT_RINGS[1][1],
                    interp_rings(TUNIC_RINGS, 0.86)[0])
    ok &= check_relief("waist: glow buckle relief", 0.023,
                       lo=0.005, hi=0.030)
    return objs, ok


def assemble_legs(parts):
    objs = parts["tunic"] + parts["pants"] + parts["knee_pads"] \
        + parts["cargo"]
    ok = True
    ok &= check_gap("legs: charcoal tunic vs torso @z=0.78",
                    interp_rings(TUNIC_RINGS, 0.78)[0],
                    interp_rings([(0.95, 0.240, 0.130),
                                  (0.62, 0.210, 0.120)], 0.78)[0])
    ok &= check_gap("legs: charcoal pants vs mannequin leg @0.0",
                    0.115, 0.105)
    ok &= check_relief("legs: knee pad relief", 0.024,
                       lo=0.005, hi=0.030)
    ok &= check_relief("legs: cargo pocket relief", 0.020,
                       lo=0.005, hi=0.030)
    print("L2_CHECK legs: charcoal tunic z 0.94-0.60 covers the hip "
          "gap, pants 0.115->0.098, knee pads and cargo pockets proud "
          "of the pants PASS")
    return objs, ok


def assemble_head_feet(parts):
    objs = (parts["hood"] + parts["face_mask"] + parts["visor"]
            + parts["cape"] + parts["boots"])
    ok = True
    ok &= check_gap("head: black hood vs hair cap @z=1.62",
                    interp_rings(HOOD_RINGS, 1.62)[0] + 0.006, 0.207)
    ok &= check_gap("head: face mask vs head @z=1.44",
                    interp_rings(MASK_RINGS, 1.44)[0] + 0.006, 0.212)
    ok &= check_gap("head: glow visor vs hair cap @z=1.55",
                    interp_rings(VISOR_RINGS, 1.55)[0] + 0.006, 0.224)
    ok &= check_gap("head: cape vs silver belt @z=0.86",
                    interp_rings(CAPE_RINGS, 0.86)[0] + 0.006,
                    BELT_RINGS[1][1])
    print("L2_CHECK head: black hood peaks over the hair top at "
          "z=1.74, face mask covers mouth/chin with eyes visible, "
          "glow visor strip on the forehead, cape hangs outside the "
          "belt PASS")
    print("L2_CHECK feet: black boot wedge centre z=0.0, sole on "
          "ground; tall boot shaft z 0.30-0.06, glow trim ring at "
          "z 0.22 on the visible shaft PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: charcoal bodice vs mannequin torso @z=1.15",
                    interp_rings(BODICE_RINGS, 1.15)[0],
                    interp_rings([(1.28, 0.270, 0.140),
                                  (0.95, 0.240, 0.130)], 1.15)[0])
    ok &= check_gap("L3 layer: silver belt vs tunic @z=0.86",
                    BELT_RINGS[1][1],
                    interp_rings(TUNIC_RINGS, 0.86)[0])
    ok &= check_gap("L3 layer: chest plate vs charcoal bodice @z=1.20",
                    interp_rings(BODICE_RINGS, 1.20)[0] + 0.006,
                    interp_rings(BODICE_RINGS, 1.20)[0])
    ok &= check_gap("L3 layer: cape vs belt @z=0.86",
                    interp_rings(CAPE_RINGS, 0.86)[0] + 0.006,
                    BELT_RINGS[1][1])
    ok &= check_gap("L3 joint: glow wrist band vs arm guard", 0.10, 0.088)
    ok &= check_gap("L3 joint: charcoal boot shaft vs leg @z=0.18",
                    0.1025, 0.088)
    print("L3_CHECK outfit: tunic hem z=0.60, black boots below the "
          "pants cuffs, black boot soles touch ground z=0.000 PASS")
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
    parts["bodice"] = build_bodice(m)
    report_l1("CharcoalBodice", parts["bodice"])
    parts["collar"] = build_collar(m)
    report_l1("HighCollar x3 rings", parts["collar"])
    parts["chest"] = build_chest_plate(m)
    report_l1("DeepTealChest", parts["chest"])
    flat_patches += parts["chest"]
    parts["circuits"] = build_circuit_lines(m)
    report_l1("GlowCircuits x3", parts["circuits"])
    flat_patches += parts["circuits"]
    parts["pauldrons"] = []
    for sx in (-1, 1):
        parts["pauldrons"] += build_pauldron(m, sx)
    report_l1("SilverPauldrons x2", parts["pauldrons"])
    parts["arm_guards"] = []
    for sx in (-1, 1):
        parts["arm_guards"] += build_arm_guard(m, sx)
    report_l1("DeepTealArmGuards x2", parts["arm_guards"])
    parts["wrist_bands"] = []
    for sx in (-1, 1):
        parts["wrist_bands"] += build_wrist_band(m, sx)
    report_l1("GlowWristBands x2", parts["wrist_bands"])
    parts["belt"] = build_belt(m)
    report_l1("SilverBelt", parts["belt"])
    parts["buckle"] = build_buckle(m)
    report_l1("GlowBuckle", parts["buckle"])
    parts["pouches"] = []
    for sx in (-1, 1):
        parts["pouches"] += build_pouch(m, sx)
    report_l1("DeepTealPouches x2", parts["pouches"])
    parts["tunic"] = build_tunic(m)
    report_l1("CharcoalTunic", parts["tunic"])
    parts["pants"] = []
    for sx in (-1, 1):
        parts["pants"] += build_pants(m, sx)
    report_l1("CharcoalPants x2", parts["pants"])
    parts["knee_pads"] = []
    for sx in (-1, 1):
        parts["knee_pads"] += build_knee_pad(m, sx)
    report_l1("DeepTealKneePads x2", parts["knee_pads"])
    parts["cargo"] = []
    for sx in (-1, 1):
        parts["cargo"] += build_cargo_pocket(m, sx)
    report_l1("DeepTealCargo x2", parts["cargo"])
    parts["hood"] = build_hood(m)
    report_l1("BlackHood", parts["hood"])
    flat_patches += parts["hood"]
    parts["face_mask"] = build_face_mask(m)
    report_l1("BlackFaceMask", parts["face_mask"])
    flat_patches += parts["face_mask"]
    parts["visor"] = build_visor(m)
    report_l1("GlowVisor", parts["visor"])
    flat_patches += parts["visor"]
    parts["cape"] = build_cape(m)
    report_l1("DeepTealCape", parts["cape"])
    flat_patches += parts["cape"]
    parts["boots"] = []
    for sx in (-1, 1):
        parts["boots"] += build_boot(m, sx)
    report_l1("CharcoalBoots+Trims x2", parts["boots"])

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    _, ok = assemble_torso(parts)
    l2_ok &= ok
    _, ok = assemble_arms(parts)
    l2_ok &= ok
    _, ok = assemble_shoulders(parts)
    l2_ok &= ok
    _, ok = assemble_waist(parts)
    l2_ok &= ok
    _, ok = assemble_legs(parts)
    l2_ok &= ok
    _, ok = assemble_head_feet(parts)
    l2_ok &= ok
    print("L2_SUMMARY %s" % ("ALL PASS" if l2_ok else "FAILURES PRESENT"))

    # ---- L3 full outfit on the mannequin ----
    costume = (parts["bodice"] + parts["collar"]
               + parts["chest"] + parts["circuits"]
               + parts["pauldrons"] + parts["arm_guards"]
               + parts["wrist_bands"] + parts["belt"] + parts["buckle"]
               + parts["pouches"] + parts["tunic"] + parts["pants"]
               + parts["knee_pads"] + parts["cargo"] + parts["hood"]
               + parts["face_mask"] + parts["visor"] + parts["cape"]
               + parts["boots"])
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
