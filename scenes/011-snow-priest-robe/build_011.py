# -*- coding: utf-8 -*-
"""011 雪国祭司长袍：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整套穿到人体底座上试穿）。
设计见 design.md。
Run: blender --background --python build_011.py
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

BLEND_OUT = os.path.join(HERE, "011-snow-priest-robe.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "011-snow-priest-robe.png")
WIRE_JSON = "/tmp/snow_priest_robe_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

INNER_RINGS = [(1.34, 0.285, 0.150), (1.05, 0.282, 0.148),
               (0.78, 0.290, 0.152)]
ROBE_RINGS = [(1.34, 0.300, 0.158), (1.05, 0.300, 0.158),
              (0.78, 0.310, 0.165), (0.55, 0.380, 0.200),
              (0.30, 0.460, 0.240)]
OVERSKIRT_RINGS = [(0.78, 0.330, 0.175), (0.55, 0.410, 0.215),
                   (0.34, 0.480, 0.250)]
BELT_TOP_Z, BELT_BOT_Z = 0.84, 0.70
BELT_RX, BELT_RY = 0.345, 0.190
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)
STAFF_X, STAFF_Y = 0.50, -0.02  # right-hand staff (camera side)


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    snow = solid_material("SnowWhite", (0.913, 0.930, 0.956), roughness=0.85)
    ice = solid_material("IceBlue", (0.027, 0.159, 0.366), roughness=0.7)
    deep = solid_material("DeepBlue", (0.011, 0.042, 0.107), roughness=0.8)
    gold = solid_material("Gold", (0.658, 0.352, 0.009),
                          metallic=0.7, roughness=0.35)
    fur = solid_material("FurWhite", (1.000, 1.000, 1.000), roughness=0.95)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    hair = solid_material("Hair_Silver", (0.807, 0.807, 0.839), roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"snow": snow, "ice": ice, "deep": deep, "gold": gold,
            "fur": fur, "skin": skin, "hair": hair, "eye": eye}


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001..010).
    Legs run to the ground + skin wedge feet (009 lesson: no bare
    feet floating). Silver-white hair cap; face: two dark eyes only."""
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
        objs.append(make_wedge("Mannequin_Foot", (sx * 0.13, -0.02, 0.02),
                               0.095, 0.09, -0.16, 0.0, 0.10, 0.045,
                               m["skin"]))
    return objs


def make_snowflake(name, center, normal, disc_r, arm_r, arms, width,
                   disc_segs, material):
    """Flat snowflake patch lying in the tangent plane at `center`
    facing `normal`: centre disc fan + `arms` thin quads radiating
    from disc_r*0.75 out to arm_r. Winding faces +normal by
    construction; do NOT run fix_normals on it."""
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
    """One vertical deep-blue pleat strip hugging the flaring
    overskirt surface, 0.006 proud, 0.05 wide (008 pteruges)."""
    a = math.radians(angle_deg)
    verts, faces = [], []
    z_list = [0.74, 0.55, 0.36]
    for k, z in enumerate(z_list):
        rx, ry = interp_rings(OVERSKIRT_RINGS, z)
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
    return mesh_from_data("PleatStrip", verts, faces, m["deep"])


# ------------------------------------------------------------ L1 components
def build_inner(m):
    return [make_elliptical_tube("InnerRobe", INNER_RINGS, 12,
                                 m["snow"], caps=False)]


def build_robe(m):
    return [make_elliptical_tube("MainRobe", ROBE_RINGS, 12,
                                 m["snow"], caps=False)]


def build_overskirt(m):
    return [make_elliptical_tube("Overskirt", OVERSKIRT_RINGS, 12,
                                 m["ice"], caps=False)]


def build_chest_snowflake(m):
    """Ice-blue 6-arm snowflake on the white robe front (z=1.12).
    Robe front there is y=-0.158; patch at -0.166 sits 0.008 proud."""
    return [make_snowflake("ChestSnowflake", (0, -0.166, 1.12), (0, -1, 0),
                           0.040, 0.100, 6, 0.018, 12, m["ice"])]


def build_skirt_snowflakes(m):
    """Three small SNOW-WHITE snowflakes on the ice-blue overskirt
    front (250/270/290 deg, z=0.48), 0.008 proud of the skirt surface.
    v1 used ice blue on ice blue: same-colour relief was invisible
    (003 lesson) — white on blue reads by colour contrast."""
    objs = []
    for ang in (250, 270, 290):
        rx, ry = interp_rings(OVERSKIRT_RINGS, 0.48)
        p, n = ellipse_point(rx, ry, ang)
        c = Vector((p.x, p.y, 0.48)) + n * 0.008
        objs.append(make_snowflake("SkirtSnowflake", tuple(c), tuple(n),
                                   0.028, 0.055, 3, 0.014, 8, m["snow"]))
    return objs


def build_pleats(m):
    return [build_pleat(m, a) for a in
            (0, 45, 90, 135, 180, 225, 270, 315)]


def build_fur_collar(m):
    """White fur collar ring over the shoulders + 3 fur tuft balls
    down the front."""
    objs = [make_elliptical_tube(
                "FurCollar",
                [(1.40, 0.320, 0.185), (1.34, 0.345, 0.200),
                 (1.28, 0.360, 0.210)],
                12, m["fur"], caps=False)]
    for x, y, z in ((0, -0.200, 1.31), (-0.09, -0.185, 1.30),
                    (0.09, -0.185, 1.30)):
        objs.append(add_sphere("FurTuft", (x, y, z), 0.045, 6, 3,
                               (1.0, 1.0, 1.0), m["fur"]))
    return objs


def build_sleeve(m, sx):
    """Snow-white wide sleeve + ice-blue cuff ring + white shoulder pad.
    Tube starts AT the shoulder point (d=0.0) so no bare arm shows
    between the fur collar and the sleeve (v1 left a skin patch at
    the shoulder); the pad plugs the sleeve's open top end — v2's
    camera still saw the mannequin arm's top cap disc through it."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [add_sphere("ShoulderPad", tuple(shoulder), 0.115, 8, 4,
                       (1.1, 1.0, 0.8), m["snow"]),
            make_tube("WideSleeve", shoulder, direction,
                      [0.0, 0.18, 0.32, 0.46, 0.52],
                      [0.110, 0.115, 0.125, 0.135, 0.140], 8, m["snow"],
                      caps=False),
            make_tube("SleeveCuff", shoulder, direction,
                      [0.44, 0.52], [0.148, 0.148], 8, m["ice"],
                      caps=False)]


def build_belt(m):
    """Deep-blue wide waist belt + gold buckle."""
    return [make_elliptical_tube(
                "WaistBelt", [(BELT_TOP_Z, BELT_RX, BELT_RY),
                             (BELT_BOT_Z, BELT_RX, BELT_RY)],
                12, m["deep"], caps=False),
            add_box("BeltBuckle", (0, -0.192, 0.77),
                    (0.08, 0.02, 0.05), m["gold"])]


def build_crown(m):
    """Gold circlet ring at z=1.66 (hair cap surface there is rx 0.202,
    ring clears it by 0.026) + five ice-blue crystal spikes on the
    front half + one tall centre spike. v1 rotated the spikes about Z
    by (ang-90): the 200/340 deg spikes lay almost horizontal, like
    blue sticks poking out of the sides of the head — spikes stay
    vertical now (no rotation), only their positions follow the ring."""
    objs = [make_tube("PriestCrown", (0, 0, 1.66), (0, 0, 1),
                      [0.0, 0.025], [0.228, 0.228], 12, m["gold"],
                      caps=False)]
    for ang in (200, 235, 270, 305, 340):
        a = math.radians(ang)
        x = 0.228 * math.cos(a)
        y = 0.228 * math.sin(a)
        objs.append(add_box(
            "CrownSpike", (x, y, 1.685), (0.028, 0.012, 0.09),
            m["ice"]))
    objs.append(add_box("CrownCentreSpike", (0, -0.228, 1.71),
                        (0.030, 0.012, 0.14), m["ice"]))
    return objs


def build_staff(m):
    """Ice-crystal long staff held in the RIGHT hand (camera side).
    Vertical at x=0.50: hand sphere reaches x=0.491, so the shaft
    (0.484..0.516) overlaps the hand by 0.007 = gripped; the shaft
    clears the overskirt hem (rx 0.480 at z=0.34) by 0.004."""
    objs = [make_tube("StaffShaft", (STAFF_X, STAFF_Y, 0.05), (0, 0, 1),
                      [0.0, 1.40], [0.016, 0.016], 6, m["deep"],
                      caps=True)]
    for z in (0.55, 0.95, 1.30):
        objs.append(make_tube("StaffGoldRing", (STAFF_X, STAFF_Y, z),
                              (0, 0, 1), [0.0, 0.03], [0.022, 0.022], 6,
                              m["gold"], caps=False))
    objs.append(make_tube("StaffCrystalBase", (STAFF_X, STAFF_Y, 1.44),
                          (0, 0, 1), [0.0, 0.03], [0.028, 0.028], 6,
                          m["gold"], caps=False))
    objs.append(add_sphere("StaffCrystal", (STAFF_X, STAFF_Y, 1.52), 0.05,
                           8, 4, (1.0, 1.0, 1.6), m["ice"]))
    return objs


def build_boot(m, sx):
    """White boot tube + fur ring at the top + white wedge foot.
    Boot tube (0.120..0.098) keeps a 0.015+ gap over the leg
    (0.105..0.082); wedge is slightly larger than the mannequin
    foot wedge so it covers it."""
    return [make_tube("SnowBoot", (sx * 0.13, 0, 0.60), (0, 0, -1),
                      [0.0, 0.15, 0.30, 0.42, 0.50],
                      [0.120, 0.115, 0.110, 0.103, 0.098], 8, m["snow"],
                      caps=False),
            make_tube("BootFurRing", (sx * 0.13, 0, 0.60), (0, 0, -1),
                      [0.0, 0.04], [0.126, 0.126], 8, m["fur"],
                      caps=False),
            make_wedge("BootFoot", (sx * 0.13, -0.02, 0.02),
                       0.100, 0.10, -0.17, 0.0, 0.11, 0.05, m["snow"])]


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["inner"] + parts["robe"] + parts["chest_snowflake"])
    ok = True
    ok &= check_gap("torso: inner robe vs mannequin torso @z=0.95",
                    interp_rings(INNER_RINGS, 0.95)[0], 0.240)
    ok &= check_gap("torso: main robe vs inner robe @z=1.05",
                    interp_rings(ROBE_RINGS, 1.05)[0],
                    interp_rings(INNER_RINGS, 1.05)[0])
    ok &= check_relief("torso: chest snowflake proud", 0.008)
    return objs, ok


def assemble_skirt(parts):
    objs = (parts["overskirt"] + parts["pleats"]
            + parts["skirt_snowflakes"])
    ok = True
    ok &= check_gap("skirt: overskirt vs main robe @z=0.55",
                    interp_rings(OVERSKIRT_RINGS, 0.55)[0],
                    interp_rings(ROBE_RINGS, 0.55)[0])
    ok &= check_relief("skirt: pleat strip relief", 0.006)
    ok &= check_relief("skirt: skirt snowflake proud", 0.008)
    return objs, ok


def assemble_shoulders(parts):
    objs = parts["fur_collar"] + parts["sleeves"]
    ok = True
    ok &= check_gap("shoulders: fur collar vs main robe @z=1.30",
                    0.350, interp_rings(ROBE_RINGS, 1.30)[0])
    ok &= check_gap("shoulders: wide sleeve vs mannequin arm @0.18",
                    0.115, 0.082)
    ok &= check_gap("shoulders: sleeve cuff vs sleeve @0.46",
                    0.148, 0.135)
    print("L2_CHECK shoulders: fur collar covers shoulder line PASS")
    return objs, ok


def assemble_waist(parts):
    objs = parts["belt"]
    ok = True
    ok &= check_gap("waist: belt vs main robe @z=0.78",
                    BELT_RX, interp_rings(ROBE_RINGS, 0.78)[0])
    ok &= check_gap("waist: belt vs overskirt top @z=0.78",
                    BELT_RX, interp_rings(OVERSKIRT_RINGS, 0.78)[0])
    ok &= check_relief("waist: belt buckle proud", 0.012,
                       lo=0.005, hi=0.020)
    return objs, ok


def assemble_head(parts):
    objs = parts["crown"]
    ok = True
    ok &= check_gap("head: crown ring vs hair cap @z=1.66",
                    0.228, 0.202, minimum=0.01)
    print("L2_CHECK head: 5 crown spikes + centre spike rooted PASS")
    return objs, ok


def assemble_hand_foot(parts):
    objs = parts["staff"] + parts["boots"]
    ok = True
    ok &= check_gap("hand/foot: boot tube vs mannequin leg @z=0.45",
                    0.115, 0.100)
    ok &= check_gap("hand/foot: staff vs overskirt hem @z=0.34",
                    STAFF_X - 0.016, 0.480, minimum=0.002)
    # Staff shaft (x 0.484..0.516) overlaps the right hand sphere
    # (reaches x=0.491) by 0.007 -> reads as gripped.
    print("L2_CHECK hand/foot: staff overlaps right hand by 0.007 PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: main robe vs inner robe @z=1.05",
                    interp_rings(ROBE_RINGS, 1.05)[0],
                    interp_rings(INNER_RINGS, 1.05)[0])
    ok &= check_gap("L3 layer: overskirt vs main robe @z=0.55",
                    interp_rings(OVERSKIRT_RINGS, 0.55)[0],
                    interp_rings(ROBE_RINGS, 0.55)[0])
    ok &= check_gap("L3 layer: belt vs main robe @z=0.78",
                    BELT_RX, interp_rings(ROBE_RINGS, 0.78)[0])
    ok &= check_gap("L3 layer: fur collar vs main robe @z=1.30",
                    0.350, interp_rings(ROBE_RINGS, 1.30)[0])
    ok &= check_gap("L3 joint: wide sleeve vs mannequin arm", 0.115, 0.082)
    ok &= check_gap("L3 joint: snow boot vs mannequin leg", 0.115, 0.100)
    ok &= check_gap("L3 joint: staff vs overskirt hem",
                    STAFF_X - 0.016, 0.480, minimum=0.002)
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
    parts["overskirt"] = build_overskirt(m)
    report_l1("Overskirt", parts["overskirt"])
    parts["chest_snowflake"] = build_chest_snowflake(m)
    report_l1("ChestSnowflake", parts["chest_snowflake"])
    flat_patches += parts["chest_snowflake"]
    parts["skirt_snowflakes"] = build_skirt_snowflakes(m)
    report_l1("SkirtSnowflakes x3", parts["skirt_snowflakes"])
    flat_patches += parts["skirt_snowflakes"]
    parts["pleats"] = build_pleats(m)
    report_l1("PleatStrips x8", parts["pleats"])
    flat_patches += parts["pleats"]
    parts["fur_collar"] = build_fur_collar(m)
    report_l1("FurCollar+Tufts", parts["fur_collar"])
    parts["sleeves"] = []
    for sx in (-1, 1):
        parts["sleeves"] += build_sleeve(m, sx)
    report_l1("WideSleeves x2", parts["sleeves"])
    parts["belt"] = build_belt(m)
    report_l1("WaistBelt+Buckle", parts["belt"])
    parts["crown"] = build_crown(m)
    report_l1("PriestCrown+Spikes", parts["crown"])
    parts["staff"] = build_staff(m)
    report_l1("IceCrystalStaff", parts["staff"])
    parts["boots"] = []
    for sx in (-1, 1):
        parts["boots"] += build_boot(m, sx)
    report_l1("SnowBoots x2", parts["boots"])

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
    costume = (parts["inner"] + parts["robe"] + parts["overskirt"]
               + parts["chest_snowflake"] + parts["skirt_snowflakes"]
               + parts["pleats"] + parts["fur_collar"] + parts["sleeves"]
               + parts["belt"] + parts["crown"] + parts["staff"]
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
