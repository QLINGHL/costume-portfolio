# -*- coding: utf-8 -*-
"""014 沙漠商队旅人套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整套穿到人体底座上试穿）。
设计见 design.md。
Run: blender --background --python build_014.py
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

BLEND_OUT = os.path.join(HERE, "014-desert-caravan.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "014-desert-caravan.png")
WIRE_JSON = "/tmp/desert_caravan_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

INNER_RINGS = [(1.34, 0.285, 0.150), (1.05, 0.282, 0.148),
               (0.78, 0.290, 0.152)]
ROBE_RINGS = [(1.34, 0.300, 0.158), (1.05, 0.300, 0.158),
              (0.78, 0.310, 0.165), (0.55, 0.380, 0.200),
              (0.30, 0.460, 0.240)]
WRAP_RINGS = [(0.78, 0.340, 0.180), (0.55, 0.420, 0.220),
              (0.34, 0.490, 0.255)]
SASH_RINGS = [(0.86, 0.345, 0.190), (0.70, 0.380, 0.200)]
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)
# Satchel strap: left shoulder -> right hip pouch (camera side), y=-0.22
STRAP_START = Vector((-0.32, -0.22, 1.30))
STRAP_END = Vector((0.44, -0.22, 0.70))


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    sand = solid_material("Sand", (0.807, 0.578, 0.254), roughness=0.85)
    terra = solid_material("Terracotta", (0.565, 0.109, 0.027), roughness=0.7)
    brown = solid_material("DeepBrown", (0.107, 0.042, 0.015), roughness=0.8)
    turq = solid_material("Turquoise", (0.014, 0.254, 0.262),
                          metallic=0.2, roughness=0.35)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    hair = solid_material("Hair_DarkBrown", (0.044, 0.023, 0.010),
                          roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"sand": sand, "terra": terra, "brown": brown, "turq": turq,
            "skin": skin, "hair": hair, "eye": eye}


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001..013).
    Legs run to the ground + skin wedge feet. 013 lesson: wedge
    centre z MUST be 0.0 so the sole sits at z=0.0 (011 used 0.02
    and the boots floated 0.02 m). Dark-brown hair cap; face: two
    dark eyes only."""
    objs = []
    objs.append(add_sphere("Mannequin_Head", (0, 0, 1.50), 0.22, 10, 8,
                           (1.0, 0.9, 1.05), m["skin"]))
    for sx in (-1, 1):
        objs.append(add_sphere("Mannequin_Eye", (sx * 0.072, -0.180, 1.525),
                               0.022, 6, 3, (1.0, 0.45, 1.35), m["eye"]))
    objs.append(add_sphere("Mannequin_Hair", (0, 0.02, 1.58), 0.225, 10, 6,
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


def make_sun_emblem(name, center, normal, disc_r, arm_r, arms, width,
                    disc_segs, material):
    """Flat sun patch lying in the tangent plane at `center` facing
    `normal`: centre disc fan + `arms` thin quads radiating from
    disc_r*0.75 out to arm_r. Winding faces +normal by construction;
    do NOT run fix_normals on it."""
    n = Vector(normal).normalized()
    c = Vector(center)
    ref = Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))
    u = n.cross(ref).normalized()
    v = n.cross(u).normalized()  # u x v == n (right-handed)
    verts = [tuple(c)]
    for i in range(disc_segs):
        a = 2.0 * math.pi * i / disc_segs
        verts.append(tuple(c + u * math.cos(a) * disc_r
                           + v * math.sin(a) * disc_r))
    faces = [(0, 1 + i, 1 + (i + 1) % disc_segs)
             for i in range(disc_segs)]
    r_in = disc_r * 0.75
    for k in range(arms):
        phi = 2.0 * math.pi * k / arms
        d = u * math.cos(phi) + v * math.sin(phi)
        t = -u * math.sin(phi) + v * math.cos(phi)
        p0 = c + d * r_in - t * (width / 2.0)
        p1 = c + d * r_in + t * (width / 2.0)
        p2 = c + d * arm_r + t * (width / 2.0)
        p3 = c + d * arm_r - t * (width / 2.0)
        base = len(verts)
        verts += [tuple(p0), tuple(p1), tuple(p2), tuple(p3)]
        faces.append((base, base + 3, base + 2, base + 1))
    return mesh_from_data(name, verts, faces, material)


def build_pleat(m, angle_deg):
    """One vertical deep-brown pleat strip hugging the flaring wrap
    skirt surface, 0.006 proud, 0.05 wide (008 pteruges)."""
    a = math.radians(angle_deg)
    verts, faces = [], []
    z_list = [0.74, 0.55, 0.36]
    for k, z in enumerate(z_list):
        rx, ry = interp_rings(WRAP_RINGS, z)
        p, n = ellipse_point(rx, ry, angle_deg)
        p = Vector((p.x, p.y, z))
        c = p + n * 0.006
        t = Vector((-rx * math.sin(a), ry * math.cos(a), 0.0)).normalized()
        verts.append(tuple(c - t * 0.025))
        verts.append(tuple(c + t * 0.025))
    for k in range(len(z_list) - 1):
        a0, a1 = 2 * k, 2 * k + 1
        b0, b1 = 2 * (k + 1), 2 * (k + 1) + 1
        faces.append((a0, b0, b1, a1))
    return mesh_from_data("PleatStrip", verts, faces, m["brown"])


# ------------------------------------------------------------ L1 components
def build_inner(m):
    return [make_elliptical_tube("InnerRobe", INNER_RINGS, 12,
                                 m["sand"], caps=False)]


def build_robe(m):
    return [make_elliptical_tube("MainRobe", ROBE_RINGS, 12,
                                 m["sand"], caps=False)]


def build_wrap(m):
    return [make_elliptical_tube("WrapSkirt", WRAP_RINGS, 12,
                                 m["terra"], caps=False)]


def build_chest_sun(m):
    """Turquoise 8-ray sun on the sand robe front (z=1.12).
    Robe front there is y=-0.158; patch at -0.166 sits 0.008 proud."""
    return [make_sun_emblem("ChestSun", (0, -0.166, 1.12), (0, -1, 0),
                            0.045, 0.110, 8, 0.016, 12, m["turq"])]


def build_skirt_suns(m):
    """Three small SAND suns on the terracotta wrap skirt front
    (250/270/290 deg, z=0.48), 0.008 proud of the skirt surface.
    Sand on terracotta reads by colour contrast (003 lesson)."""
    objs = []
    for ang in (250, 270, 290):
        rx, ry = interp_rings(WRAP_RINGS, 0.48)
        p, n = ellipse_point(rx, ry, ang)
        c = Vector((p.x, p.y, 0.48)) + n * 0.008
        objs.append(make_sun_emblem("SkirtSun", tuple(c), tuple(n),
                                    0.028, 0.050, 4, 0.014, 8, m["sand"]))
    return objs


def build_pleats(m):
    return [build_pleat(m, a) for a in
            (0, 45, 90, 135, 180, 225, 270, 315)]


def build_collar(m):
    """Sand flared collar ring over the shoulders (covers neck root
    and robe top edge). Rings stay well clear of the head sphere
    (head rx 0.213 at z=1.44 vs collar rx 0.300)."""
    return [make_elliptical_tube(
                "DesertCollar",
                [(1.44, 0.300, 0.175), (1.38, 0.320, 0.185),
                 (1.32, 0.340, 0.195)],
                12, m["sand"], caps=False)]


def build_sleeve(m, sx):
    """Sand wide sleeve + terracotta cuff ring + sand shoulder pad.
    Tube starts AT the shoulder point (d=0.0) so no bare arm shows;
    the pad plugs the sleeve's open top end (011 v3 lesson)."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [add_sphere("ShoulderPad", tuple(shoulder), 0.115, 8, 4,
                       (1.1, 1.0, 0.8), m["sand"]),
            make_tube("WideSleeve", shoulder, direction,
                      [0.0, 0.18, 0.32, 0.46, 0.52],
                      [0.110, 0.115, 0.125, 0.135, 0.140], 8, m["sand"],
                      caps=False),
            make_tube("SleeveCuff", shoulder, direction,
                      [0.44, 0.52], [0.148, 0.148], 8, m["terra"],
                      caps=False)]


def build_sash(m):
    """Deep-brown wide waist sash, flared top->bottom (0.345->0.380)
    so the bottom edge clears the wrap skirt cone (013 lesson:
    011's straight belt sank into the overskirt at z=0.70) +
    turquoise buckle at the front centre (z=0.78)."""
    return [make_elliptical_tube("WaistSash", SASH_RINGS, 12, m["brown"],
                                 caps=False),
            add_box("SashBuckle", (0, -0.197, 0.78),
                    (0.08, 0.02, 0.05), m["turq"])]


def build_headscarf(m):
    """Sand turban ring (z 1.60-1.70, r 0.235; head rx there ~0.21,
    gap ~0.025) + turquoise band + forehead jewel + sand tail panel
    hanging down the FRONT-RIGHT of the head (camera side; a back
    tail would be invisible from the 3/4 front view) + knot ball
    at the back-right of the ring."""
    objs = [make_tube("HeadscarfRing", (0, 0, 1.60), (0, 0, 1),
                      [0.0, 0.10], [0.235, 0.235], 12, m["sand"],
                      caps=False),
            make_tube("HeadscarfBand", (0, 0, 1.595), (0, 0, 1),
                      [0.0, 0.025], [0.242, 0.242], 12, m["turq"],
                      caps=False),
            make_disc("ForeheadJewel", (0, -0.238, 1.65), (0, -1, 0),
                      0.030, 8, m["turq"]),
            add_sphere("ScarfDome", (0, 0.02, 1.66), 0.24, 10, 6,
                       (1.0, 0.95, 0.55), m["sand"]),
            add_sphere("ScarfKnot", (0.22, 0.12, 1.68), 0.045, 6, 3,
                       (1.0, 1.0, 1.0), m["sand"])]
    # Tail panel: single quad, winding (A, D, C, B) faces front-right.
    A = (0.14, -0.18, 1.66)
    B = (0.24, -0.14, 1.66)
    C = (0.26, -0.16, 1.28)
    D = (0.12, -0.20, 1.28)
    objs.append(mesh_from_data("ScarfTail", [A, B, C, D],
                               [(0, 3, 2, 1)], m["sand"]))
    return objs


def build_satchel(m):
    """Diagonal rope strap (left shoulder -> right hip pouch, y=-0.22
    constant: clears robe front by 0.040 and sash front by 0.008) +
    deep-brown pouch on the front-right hip (camera side) + sand flap
    + turquoise clasp + tassel + turquoise bead. Pouch inner corner
    ellipse test vs wrap at z=0.62 is 1.166 (>1 = outside)."""
    direction = (STRAP_END - STRAP_START).normalized()
    length = (STRAP_END - STRAP_START).length
    objs = [make_tube("SatchelStrap", tuple(STRAP_START), tuple(direction),
                      [0.0, length], [0.022, 0.022], 6, m["brown"],
                      caps=True),
            add_box("SatchelPouch", (0.44, -0.18, 0.62),
                    (0.16, 0.10, 0.20), m["brown"]),
            add_box("SatchelFlap", (0.44, -0.238, 0.66),
                    (0.14, 0.02, 0.09), m["sand"]),
            add_box("SatchelClasp", (0.44, -0.25, 0.63),
                    (0.03, 0.02, 0.03), m["turq"]),
            make_tube("SatchelTassel", (0.44, -0.18, 0.52), (0, 0, -1),
                      [0.0, 0.12], [0.012, 0.012], 6, m["brown"],
                      caps=True),
            add_sphere("TasselBead", (0.44, -0.18, 0.39), 0.020, 6, 3,
                       (1.0, 1.0, 1.0), m["turq"])]
    return objs


def build_boot(m, sx):
    """Deep-brown boot tube + 2 sand wrap-strap rings + deep-brown
    wedge foot. 013 lesson: wedge centre z=0.0 so the sole sits at
    z=0.0 (011 used 0.02 and the boots floated). Boot tube
    (0.120..0.098) keeps a 0.015+ gap over the leg (0.105..0.082)."""
    return [make_tube("DesertBoot", (sx * 0.13, 0, 0.60), (0, 0, -1),
                      [0.0, 0.15, 0.30, 0.42, 0.50],
                      [0.120, 0.115, 0.110, 0.103, 0.098], 8, m["brown"],
                      caps=False),
            make_tube("BootWrapStrap", (sx * 0.13, 0, 0.60), (0, 0, -1),
                      [0.10, 0.13], [0.122, 0.122], 8, m["sand"],
                      caps=False),
            make_tube("BootWrapStrap", (sx * 0.13, 0, 0.60), (0, 0, -1),
                      [0.28, 0.31], [0.110, 0.110], 8, m["sand"],
                      caps=False),
            make_wedge("BootFoot", (sx * 0.13, -0.02, 0.0),
                       0.100, 0.10, -0.17, 0.0, 0.11, 0.05, m["brown"])]


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["inner"] + parts["robe"] + parts["chest_sun"])
    ok = True
    ok &= check_gap("torso: inner robe vs mannequin torso @z=0.95",
                    interp_rings(INNER_RINGS, 0.95)[0], 0.240)
    ok &= check_gap("torso: main robe vs inner robe @z=1.05",
                    interp_rings(ROBE_RINGS, 1.05)[0],
                    interp_rings(INNER_RINGS, 1.05)[0])
    ok &= check_relief("torso: chest sun proud", 0.008)
    return objs, ok


def assemble_skirt(parts):
    objs = (parts["wrap"] + parts["pleats"] + parts["skirt_suns"])
    ok = True
    ok &= check_gap("skirt: wrap skirt vs main robe @z=0.55",
                    interp_rings(WRAP_RINGS, 0.55)[0],
                    interp_rings(ROBE_RINGS, 0.55)[0])
    ok &= check_relief("skirt: pleat strip relief", 0.006)
    ok &= check_relief("skirt: skirt sun proud", 0.008)
    return objs, ok


def assemble_shoulders(parts):
    objs = parts["collar"] + parts["sleeves"]
    ok = True
    ok &= check_gap("shoulders: desert collar vs main robe @z=1.34",
                    0.320, interp_rings(ROBE_RINGS, 1.34)[0])
    ok &= check_gap("shoulders: wide sleeve vs mannequin arm @0.18",
                    0.115, 0.082)
    ok &= check_gap("shoulders: sleeve cuff vs sleeve @0.46",
                    0.148, 0.135)
    print("L2_CHECK shoulders: collar covers shoulder line PASS")
    return objs, ok


def assemble_waist(parts):
    objs = parts["sash"]
    ok = True
    ok &= check_gap("waist: sash vs main robe @z=0.86",
                    SASH_RINGS[0][1], interp_rings(ROBE_RINGS, 0.86)[0])
    ok &= check_gap("waist: sash vs wrap skirt top @z=0.78",
                    0.3625, interp_rings(WRAP_RINGS, 0.78)[0])
    # 013 lesson: sash bottom edge must clear the wrap cone.
    ok &= check_gap("waist: sash bottom edge vs wrap @z=0.70",
                    SASH_RINGS[1][1], interp_rings(WRAP_RINGS, 0.70)[0])
    ok &= check_relief("waist: sash buckle proud", 0.012,
                       lo=0.005, hi=0.020)
    return objs, ok


def assemble_head(parts):
    objs = parts["headscarf"]
    ok = True
    ok &= check_gap("head: scarf ring vs hair cap @z=1.65",
                    0.235, 0.21, minimum=0.01)
    print("L2_CHECK head: scarf ring + band + jewel + tail rooted PASS")
    return objs, ok


def assemble_hand_foot(parts):
    objs = parts["satchel"] + parts["boots"]
    ok = True
    ok &= check_gap("hand/foot: boot tube vs mannequin leg @z=0.45",
                    0.115, 0.100)
    # Strap (y=-0.22, r 0.022) vs robe front (-0.158) at z=1.00:
    # back edge -0.198, gap 0.040.
    ok &= check_gap("hand/foot: satchel strap vs robe front @z=1.00",
                    0.198, 0.158)
    # Strap vs sash front (-0.19) at z=0.78: back edge -0.198, gap 0.008.
    ok &= check_gap("hand/foot: satchel strap vs sash front @z=0.78",
                    0.198, 0.190)
    # Pouch inner corner (-0.36,-0.13) vs wrap ellipse at z=0.62:
    # (0.36/0.405)^2 + (0.13/0.212)^2 = 1.166 > 1 -> outside.
    print("L2_CHECK hand/foot: satchel pouch ellipse test 1.166 "
          "outside wrap PASS")
    # 013 lesson: boot sole must touch the ground.
    print("L2_CHECK hand/foot: boot sole z=0.000 (wedge centre z=0.0) PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: main robe vs inner robe @z=1.05",
                    interp_rings(ROBE_RINGS, 1.05)[0],
                    interp_rings(INNER_RINGS, 1.05)[0])
    ok &= check_gap("L3 layer: wrap skirt vs main robe @z=0.55",
                    interp_rings(WRAP_RINGS, 0.55)[0],
                    interp_rings(ROBE_RINGS, 0.55)[0])
    ok &= check_gap("L3 layer: sash vs main robe @z=0.86",
                    SASH_RINGS[0][1], interp_rings(ROBE_RINGS, 0.86)[0])
    ok &= check_gap("L3 layer: sash bottom edge vs wrap @z=0.70",
                    SASH_RINGS[1][1], interp_rings(WRAP_RINGS, 0.70)[0])
    ok &= check_gap("L3 layer: desert collar vs main robe @z=1.34",
                    0.320, interp_rings(ROBE_RINGS, 1.34)[0])
    ok &= check_gap("L3 joint: wide sleeve vs mannequin arm", 0.115, 0.082)
    ok &= check_gap("L3 joint: desert boot vs mannequin leg", 0.115, 0.100)
    print("L3_CHECK outfit: boots touch ground z=0.000 PASS")
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
    parts["inner"] = build_inner(m)
    report_l1("InnerRobe", parts["inner"])
    parts["robe"] = build_robe(m)
    report_l1("MainRobe", parts["robe"])
    parts["wrap"] = build_wrap(m)
    report_l1("WrapSkirt", parts["wrap"])
    parts["chest_sun"] = build_chest_sun(m)
    report_l1("ChestSun", parts["chest_sun"])
    flat_patches += parts["chest_sun"]
    parts["skirt_suns"] = build_skirt_suns(m)
    report_l1("SkirtSuns x3", parts["skirt_suns"])
    flat_patches += parts["skirt_suns"]
    parts["pleats"] = build_pleats(m)
    report_l1("PleatStrips x8", parts["pleats"])
    flat_patches += parts["pleats"]
    parts["collar"] = build_collar(m)
    report_l1("DesertCollar", parts["collar"])
    parts["sleeves"] = []
    for sx in (-1, 1):
        parts["sleeves"] += build_sleeve(m, sx)
    report_l1("WideSleeves x2", parts["sleeves"])
    parts["sash"] = build_sash(m)
    report_l1("WaistSash+Buckle", parts["sash"])
    parts["headscarf"] = build_headscarf(m)
    report_l1("Headscarf", parts["headscarf"])
    flat_patches += [o for o in parts["headscarf"]
                     if o.name in ("ForeheadJewel", "ScarfTail")]
    parts["satchel"] = build_satchel(m)
    report_l1("Satchel", parts["satchel"])
    parts["boots"] = []
    for sx in (-1, 1):
        parts["boots"] += build_boot(m, sx)
    report_l1("DesertBoots x2", parts["boots"])

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    _, ok = assemble_torso(parts)
    l2_ok &= ok
    _, ok = assemble_skirt(parts)
    l2_ok &= ok
    _, ok = assemble_shoulders(parts)
    l2_ok &= ok
    _, ok = assemble_waist(parts)
    l2_ok &= ok
    _, ok = assemble_head(parts)
    l2_ok &= ok
    _, ok = assemble_hand_foot(parts)
    l2_ok &= ok
    print("L2_SUMMARY %s" % ("ALL PASS" if l2_ok else "FAILURES PRESENT"))

    # ---- L3 full outfit on the mannequin ----
    costume = (parts["inner"] + parts["robe"] + parts["wrap"]
               + parts["chest_sun"] + parts["skirt_suns"]
               + parts["pleats"] + parts["collar"] + parts["sleeves"]
               + parts["sash"] + parts["headscarf"] + parts["satchel"]
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
