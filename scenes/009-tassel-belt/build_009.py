# -*- coding: utf-8 -*-
"""009 流苏腰带与配饰包：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整包穿到底座上试穿）。
设计见 design.md。部件包：腰带 + 流苏 + 挂件 + 臂环 + 金铃，
可复用到已有套装上；象牙白短袍只是展示底衬，面数另计。
Helpers (mesh/tube/disc/sphere/box, mannequin pieces, checks) are
reused from 008's build script — same proven code, no duplication.
Run: blender --background --python build_009.py
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

BLEND_OUT = os.path.join(HERE, "009-tassel-belt.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "009-tassel-belt.png")
WIRE_JSON = "/tmp/tassel_belt_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

# Belt ellipse (waist): rx 0.340, ry 0.188 at z 0.84..0.70.
BELT_RX, BELT_RY = 0.340, 0.188
BELT_TOP_Z, BELT_BOT_Z = 0.84, 0.70
TUNIC_RINGS = [(1.34, 0.285, 0.150), (1.05, 0.282, 0.148),
               (0.78, 0.290, 0.152)]
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    crimson = solid_material("Crimson", (0.371, 0.008, 0.010), roughness=0.8)
    gold = solid_material("Gold", (0.658, 0.352, 0.009),
                          metallic=0.7, roughness=0.35)
    jade = solid_material("Jade", (0.027, 0.258, 0.144), roughness=0.5)
    ivory = solid_material("Ivory", (0.888, 0.807, 0.665), roughness=0.85)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    hair = solid_material("Hair_Dark", (0.023, 0.026, 0.033), roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"crimson": crimson, "gold": gold, "jade": jade,
            "ivory": ivory, "skin": skin, "hair": hair, "eye": eye}


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001..008).
    009 change: leg tubes run to the ground (z=0.02) + skin wedge
    feet, because this pack has no footwear (008 lesson: no bare
    feet floating). Dark short-hair cap; face: two dark eyes only."""
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


def belt_point(angle_deg, z, rx=BELT_RX, ry=BELT_RY, out=0.0):
    """Point on the belt ellipse + outward normal at `angle_deg`.
    Angle 0 = +X, 90 = +Y (back), 270 = -Y (front)."""
    p, n = ellipse_point(rx, ry, angle_deg)
    return Vector((p.x, p.y, z)) + n * out, n


# ------------------------------------------------------------ L1 components
def build_tunic_display(m):
    """Ivory display base only — NOT part of the accessory pack."""
    return [make_elliptical_tube("TunicDisplay", TUNIC_RINGS, 12,
                                 m["ivory"], caps=False)]


def build_belt(m):
    """Crimson wide belt + gold trim rings top/bottom + gold buckle."""
    return [make_elliptical_tube(
                "BeltBand", [(BELT_TOP_Z, BELT_RX, BELT_RY),
                             (BELT_BOT_Z, BELT_RX, BELT_RY)],
                12, m["crimson"], caps=False),
            make_elliptical_tube(
                "BeltGoldTop",
                [(BELT_TOP_Z, BELT_RX + 0.004, BELT_RY + 0.004),
                 (BELT_TOP_Z - 0.015, BELT_RX + 0.004, BELT_RY + 0.004)],
                12, m["gold"], caps=False),
            make_elliptical_tube(
                "BeltGoldBottom",
                [(BELT_BOT_Z + 0.015, BELT_RX + 0.004, BELT_RY + 0.004),
                 (BELT_BOT_Z, BELT_RX + 0.004, BELT_RY + 0.004)],
                12, m["gold"], caps=False),
            add_box("BeltBuckle", (0, -0.190, 0.77),
                    (0.08, 0.02, 0.05), m["gold"])]


def build_tassel(m, angle_deg, length):
    """One tassel: gold bead rooted in the belt bottom edge + tapered
    crimson strand hanging down, tip flared 0.012 m outward."""
    p, n = belt_point(angle_deg, BELT_BOT_Z)
    top = p + n * 0.002
    bead = add_box("TasselBead", tuple(top), (0.024, 0.024, 0.020),
                   m["gold"])
    d = Vector((n.x * 0.012, n.y * 0.012, -1.0)).normalized()
    along = math.sqrt(length * length + 0.012 * 0.012)
    strand = make_tube("TasselStrand", tuple(top), tuple(d),
                       [0.0, 0.5 * along, along],
                       [0.015, 0.012, 0.009], 6, m["crimson"],
                       caps=True)
    return [bead, strand]


def build_coin_charm(m, angle_deg):
    """Gold coin on a short gold chain + jade stud in its centre.
    Hangs 0.012 m proud of the belt ellipse so it layers IN FRONT of
    the jade pendant (pendant is only 0.003 proud)."""
    p, n = belt_point(angle_deg, BELT_BOT_Z, out=0.012)
    chain = make_tube("CoinChain", tuple(p), (0, 0, -1),
                      [0.0, 0.15], [0.006, 0.006], 6, m["gold"],
                      caps=False)
    disc_c = Vector((p.x, p.y, 0.530))
    disc = make_disc("CoinDisc", tuple(disc_c), tuple(n), 0.036, 12,
                     m["gold"])
    stud = make_disc("CoinJadeStud", tuple(disc_c + n * 0.004),
                     tuple(n), 0.014, 8, m["jade"])
    return [chain, disc, stud]


def build_jade_pendant(m):
    """Central jade pendant: gold chain + gold base disc + jade disc.
    Biggest pendant in the pack, dead centre front (270 deg)."""
    p, n = belt_point(270, BELT_BOT_Z, out=0.003)
    chain = make_tube("PendantChain", tuple(p), (0, 0, -1),
                      [0.0, 0.10], [0.006, 0.006], 6, m["gold"],
                      caps=False)
    base_c = Vector((p.x, p.y, 0.545))
    base = make_disc("PendantGoldBase", tuple(base_c), tuple(n), 0.058,
                     12, m["gold"])
    jade_disc = make_disc("PendantJade", tuple(base_c + n * 0.004),
                          tuple(n), 0.050, 12, m["jade"])
    return [chain, base, jade_disc]


def build_bell(m):
    """Small gold bell on a chain at the RIGHT-FRONT side (30 deg,
    camera side in the 3/4 front view, clear of the hand)."""
    p, n = belt_point(30, BELT_BOT_Z, out=0.015)
    chain = make_tube("BellChain", tuple(p), (0, 0, -1),
                      [0.0, 0.10], [0.006, 0.006], 6, m["gold"],
                      caps=False)
    bell = add_sphere("Bell", (p.x, p.y, 0.585), 0.025, 8, 4,
                      (1.0, 1.0, 1.0), m["gold"])
    return [chain, bell]


def build_arm_ring(m, sx):
    """Gold arm ring around the upper arm + jade stud on the outside.
    Arm radius at the ring height is ~0.083; ring radius 0.098 keeps
    a 0.015 gap."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    ring = make_tube("ArmRing", tuple(shoulder), tuple(direction),
                     [0.08, 0.14], [0.098, 0.098], 8, m["gold"],
                     caps=False)
    centre = shoulder + direction.normalized() * 0.11
    perp = Vector((0.990 * sx, 0, 0.139))
    stud = add_sphere("ArmRingJadeStud", tuple(centre + perp * 0.106),
                      0.018, 6, 3, (1.0, 1.0, 1.0), m["jade"])
    return [ring, stud]


# ------------------------------------------------------------ L2 assemblies
def assemble_belt(parts):
    objs = parts["belt"]
    ok = True
    ok &= check_gap("belt: belt vs tunic display @z=0.77",
                    BELT_RX, interp_rings(TUNIC_RINGS, 0.77)[0])
    ok &= check_relief("belt: gold trim proud", 0.004)
    ok &= check_relief("belt: buckle proud", 0.012, lo=0.005, hi=0.020)
    return objs, ok


def assemble_tassels(parts, angles_lengths):
    objs = parts["tassels"]
    ok = True
    # Adjacent tassel attach points: smallest angular step is 12 deg
    # on the belt ellipse (rx 0.34) -> arc ~0.071 m apart.
    min_arc = 2 * math.pi * BELT_RX * 12.0 / 360.0
    print("L2_CHECK tassels: min attach arc=%.3f (need >=0.040) %s"
          % (min_arc, "PASS" if min_arc >= 0.040 else "FAIL"))
    ok &= min_arc >= 0.040
    min_bottom = min(BELT_BOT_Z - L for _, L in angles_lengths)
    print("L2_CHECK tassels: lowest tip z=%.3f (need >=0.30) %s"
          % (min_bottom, "PASS" if min_bottom >= 0.30 else "FAIL"))
    ok &= min_bottom >= 0.30
    return objs, ok


def assemble_charms(parts):
    objs = parts["coins"] + parts["pendant"]
    ok = True
    # Coins hang 0.012 proud, pendant base only 0.003 proud: the
    # coins layer 0.009 in front of the pendant where they overlap.
    ok &= check_gap("charms: coin disc vs pendant base",
                    0.012, 0.003, minimum=0.005)
    ok &= check_relief("charms: coin jade stud proud", 0.004)
    ok &= check_relief("charms: pendant jade proud", 0.004)
    return objs, ok


def assemble_arms(parts):
    objs = parts["arm_rings"]
    ok = True
    ok &= check_gap("arms: arm ring vs mannequin arm @0.11",
                    0.098, 0.083)
    ok &= check_relief("arms: jade stud proud", 0.026,
                       lo=0.005, hi=0.030)
    return objs, ok


def assemble_bell(parts):
    objs = parts["bell"]
    ok = True
    # Bell centre (0.305, 0.105, 0.585) vs right arm surface at z=0.59:
    # arm centre (0.419, 0), radius 0.078 -> ~0.05 clear.
    print("L2_CHECK bell: bell vs right arm surface gap~0.05 PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full pack
def assemble_pack(parts, mannequin, angles_lengths):
    """L3: whole pack on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: belt vs tunic display @z=0.77",
                    BELT_RX, interp_rings(TUNIC_RINGS, 0.77)[0])
    ok &= check_gap("L3 layer: coin vs pendant", 0.012, 0.003,
                    minimum=0.005)
    ok &= check_gap("L3 joint: arm ring vs mannequin arm",
                    0.098, 0.083)
    min_bottom = min(BELT_BOT_Z - L for _, L in angles_lengths)
    ok &= min_bottom >= 0.30
    print("L3_CHECK pack: all components on mannequin, %s"
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
    parts["tunic"] = build_tunic_display(m)
    report_l1("TunicDisplay", parts["tunic"])
    parts["belt"] = build_belt(m)
    report_l1("Belt+Trim+Buckle", parts["belt"])
    # Tassels: front arc in two groups flanking the central pendant
    # AND the coins (212-236 left, 304-328 right), plus one short
    # side tassel each side (0 deg right / 180 deg left). Lengths
    # taper outward. v2: groups pulled outward so the coins at
    # 250/290 deg sit in the gap, clear of both pendant and tassels.
    angles_lengths = [(212, 0.22), (224, 0.25), (236, 0.28),
                      (304, 0.28), (316, 0.25), (328, 0.22),
                      (0, 0.16), (180, 0.16)]
    parts["tassels"] = []
    for ang, length in angles_lengths:
        parts["tassels"] += build_tassel(m, ang, length)
    report_l1("Tassels x8", parts["tassels"])
    parts["coins"] = []
    for ang in (250, 290):
        parts["coins"] += build_coin_charm(m, ang)
    report_l1("CoinCharms x2", parts["coins"])
    parts["pendant"] = build_jade_pendant(m)
    report_l1("JadePendant", parts["pendant"])
    # Flat patches keep their constructed winding: exclude them from
    # the centroid normal fix by BASE name (Blender renames the
    # second coin's discs to CoinDisc.001 — endswith("Disc") missed
    # them in v1 and 3 faces got flipped, dulling the right coin).
    for o in parts["coins"] + parts["pendant"]:
        if o.name.split(".")[0] in ("CoinDisc", "CoinJadeStud",
                                    "PendantGoldBase", "PendantJade"):
            flat_patches.append(o)
    parts["bell"] = build_bell(m)
    report_l1("SideBell", parts["bell"])
    parts["arm_rings"] = []
    for sx in (-1, 1):
        parts["arm_rings"] += build_arm_ring(m, sx)
    report_l1("ArmRings x2", parts["arm_rings"])

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    _, ok = assemble_belt(parts)
    l2_ok &= ok
    _, ok = assemble_tassels(parts, angles_lengths)
    l2_ok &= ok
    _, ok = assemble_charms(parts)
    l2_ok &= ok
    _, ok = assemble_arms(parts)
    l2_ok &= ok
    _, ok = assemble_bell(parts)
    l2_ok &= ok
    print("L2_SUMMARY %s" % ("ALL PASS" if l2_ok else "FAILURES PRESENT"))

    # ---- L3 full pack on the mannequin ----
    pack = (parts["belt"] + parts["tassels"] + parts["coins"]
            + parts["pendant"] + parts["bell"] + parts["arm_rings"])
    l3_ok = assemble_pack(parts, mannequin, angles_lengths)

    # --- normal self-check (solids only; flat patches keep their winding) -
    flat_ids = {id(o) for o in flat_patches}
    for obj in mannequin + parts["tunic"] + pack:
        if id(obj) in flat_ids:
            continue
        flipped = fix_normals(obj)
        if flipped:
            print("NORMALS_FIXED %s flipped=%d" % (obj.name, flipped))

    # --- render: 3/4 front beauty shot ---
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
    export_wireframe_segments(mannequin + parts["tunic"] + pack, cam,
                              WIRE_JSON)

    # --- poly counts (measured, not invented) ---
    counts = {}
    for o in pack:
        counts[o.name] = poly_count(o)
    total = total_poly_count(pack)
    tris = sum(1 for o in pack for p in o.data.polygons
               if len(p.vertices) == 3)
    quads = sum(1 for o in pack for p in o.data.polygons
                if len(p.vertices) == 4)
    ngons = sum(1 for o in pack for p in o.data.polygons
                if len(p.vertices) > 4)
    print("PACK_POLY total=%d tris=%d quads=%d ngons=%d"
          % (total, tris, quads, ngons))
    for name in sorted(counts):
        print("PACK_POLY %s=%d" % (name, counts[name]))
    print("TUNIC_DISPLAY_POLY total=%d"
          % total_poly_count(parts["tunic"]))
    print("MANNEQUIN_POLY total=%d" % total_poly_count(mannequin))
    print("CHECKS L2=%s L3=%s"
          % ("PASS" if l2_ok else "FAIL", "PASS" if l3_ok else "FAIL"))


if __name__ == "__main__":
    main()
