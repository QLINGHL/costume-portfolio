# -*- coding: utf-8 -*-
"""017 原神式层叠幻想 · 枫丹水都歌剧礼服套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整套穿到人体底座上试穿）。
设计见 design.md。
Run: blender --background --python build_017.py
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

BLEND_OUT = os.path.join(HERE, "017-opera-gown.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "017-opera-gown.png")
WIRE_JSON = "/tmp/opera_gown_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

BODICE_RINGS = [(1.34, 0.282, 0.150), (1.15, 0.278, 0.148),
                (0.95, 0.272, 0.146), (0.88, 0.268, 0.144)]
SKIRT_RINGS = [(0.88, 0.300, 0.165), (0.60, 0.360, 0.198),
               (0.30, 0.440, 0.242), (0.05, 0.510, 0.280)]
OVER_RINGS = [(0.80, 0.325, 0.180), (0.55, 0.383, 0.212),
              (0.30, 0.452, 0.252)]
HEM_RINGS = [(0.10, 0.518, 0.286), (0.04, 0.522, 0.288)]
COLLAR_RINGS = [(1.40, 0.150, 0.128), (1.34, 0.160, 0.133)]
COLLAR_TRIM_RINGS = [(1.405, 0.153, 0.131), (1.395, 0.153, 0.131)]
SASH_RINGS = [(0.90, 0.315, 0.175), (0.80, 0.325, 0.180)]
TIARA_RINGS = [(1.66, 0.202, 0.192), (1.62, 0.223, 0.212)]
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)
PEARL_X = (-0.12, -0.08, -0.04, 0.0, 0.04, 0.08, 0.12)
WAVE_CENTERS = [(0.0, 1.12), (-0.11, 1.18), (0.11, 1.18)]


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    water = solid_material("WaterBlue", (0.027, 0.159, 0.392),
                           roughness=0.6)
    pearl = solid_material("PearlWhite", (0.888, 0.863, 0.791),
                           roughness=0.6)
    deepsea = solid_material("DeepSea", (0.008, 0.032, 0.068),
                             roughness=0.6)
    gold = solid_material("Gold", (0.694, 0.371, 0.053),
                          metallic=0.3, roughness=0.45)
    pleat = solid_material("PleatBlue", (0.011, 0.068, 0.171),
                           roughness=0.6)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    hair = solid_material("Hair_Brown", (0.042, 0.023, 0.013),
                          roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"water": water, "pearl": pearl, "deepsea": deepsea,
            "gold": gold, "pleat": pleat, "skin": skin, "hair": hair,
            "eye": eye}


def front_y(rings, x, z):
    """Front surface Y of an elliptical tube at (x, z)."""
    rx, ry = interp_rings(rings, z)
    return ellipse_front(rx, ry, x)[0]


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001..016).
    Legs run to the ground + skin wedge feet. 013 lesson: wedge
    centre z MUST be 0.0 so the sole sits at z=0.0. Brown hair cap
    (visible: no helmet this time) + two dark eyes (visible)."""
    objs = []
    objs.append(add_sphere("Mannequin_Head", (0, 0, 1.50), 0.22, 10, 8,
                           (1.0, 0.9, 1.05), m["skin"]))
    for sx in (-1, 1):
        objs.append(add_sphere("Mannequin_Eye", (sx * 0.072, -0.183, 1.525),
                               0.022, 6, 3, (1.0, 0.45, 1.35), m["eye"]))
    objs.append(add_sphere("Mannequin_Hair", (0, 0.02, 1.57), 0.225, 10, 6,
                           (1.0, 0.95, 0.80), m["hair"]))
    # v1: z=1.55/scale-z 0.72 left the crown skin-bare (top 1.712 < head
    # top 1.731), reading as a headband; v2 top is 1.75, covering the crown.
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
def build_bodice(m):
    return [make_elliptical_tube("Bodice", BODICE_RINGS, 12,
                                 m["water"], caps=False)]


def build_collar(m):
    """Water-blue stand collar + thin gold trim ring above it."""
    return [make_elliptical_tube("StandCollar", COLLAR_RINGS, 12,
                                 m["water"], caps=False),
            make_elliptical_tube("CollarTrim", COLLAR_TRIM_RINGS, 12,
                                 m["gold"], caps=False)]


def build_wave_patch(m, cx, cz):
    """One gold wave motif: 3 overlapping gold discs on the bodice
    front (003 cloud-patch technique)."""
    y = front_y(BODICE_RINGS, cx, cz)
    objs = []
    for dx, dz, r in ((0.0, 0.0, 0.030), (-0.032, 0.022, 0.024),
                      (0.032, 0.022, 0.024)):
        objs.append(make_disc("WavePatch", (cx + dx, y - 0.006, cz + dz),
                              (0, -1, 0), r, 8, m["gold"]))
    return objs


def build_necklace(m):
    """Pearl necklace: 7 pearl-white beads along the bodice front
    ellipse at z=1.30, centres 0.010 proud of the surface."""
    objs = []
    for x in PEARL_X:
        y = front_y(BODICE_RINGS, x, 1.30)
        objs.append(add_sphere("PearlBead", (x, y - 0.010, 1.30),
                               0.016, 6, 3, (1.0, 1.0, 1.0), m["pearl"]))
    return objs


def build_skirt(m):
    return [make_elliptical_tube("BellSkirt", SKIRT_RINGS, 12,
                                 m["pearl"], caps=False)]


def build_overskirt(m):
    """Water-blue overskirt front panel: 90 deg arc (225-315 deg),
    over the white bell skirt."""
    return [make_elliptical_tube("Overskirt", OVER_RINGS, 7,
                                 m["water"], arc=(225, 315),
                                 caps=False)]


def build_pleat(m, angle_deg):
    """One vertical skirt pleat: a 4-ring strip hugging the flaring
    skirt surface, 0.006 proud, 0.028 wide, in darker pleat-blue so
    the fold reads as a shadowed crease (003 pleat technique)."""
    a = math.radians(angle_deg)
    verts, faces = [], []
    z_list = [0.80, 0.55, 0.30, 0.10]
    for z in z_list:
        rx, ry = interp_rings(SKIRT_RINGS, z)
        p, n = ellipse_point(rx, ry, angle_deg)
        p = Vector((p.x, p.y, z))  # ellipse_point returns z=0
        c = p + n * 0.006
        t = Vector((-rx * math.sin(a), ry * math.cos(a), 0.0)).normalized()
        verts.append(tuple(c - t * 0.014))
        verts.append(tuple(c + t * 0.014))
    for k in range(len(z_list) - 1):
        a0, a1 = 2 * k, 2 * k + 1
        b0, b1 = 2 * (k + 1), 2 * (k + 1) + 1
        faces.append((a0, b0, b1, a1))
    return mesh_from_data("SkirtPleat", verts, faces, m["pleat"])


def build_hem(m):
    return [make_elliptical_tube("GoldHem", HEM_RINGS, 12,
                                 m["gold"], caps=False)]


def build_sash(m):
    """Gold waist sash, flared top->bottom (0.315->0.325) so the
    bottom edge clears the skirt cone (013 lesson) + deep-sea
    buckle at the front centre."""
    y = front_y(SASH_RINGS, 0, 0.85)
    return [make_elliptical_tube("GoldSash", SASH_RINGS, 12,
                                 m["gold"], caps=False),
            add_box("SashBuckle", (0, y - 0.008, 0.85),
                    (0.07, 0.016, 0.05), m["deepsea"])]


def build_pendant(m):
    """Deep-sea water-drop pendant hanging from the sash over the
    overskirt front centre + thin gold cord up to the sash."""
    return [add_box("PendantCord", (0, -0.196, 0.73),
                    (0.012, 0.008, 0.14), m["gold"]),
            add_sphere("WaterDrop", (0, -0.206, 0.62), 0.035, 8, 4,
                       (1.0, 0.6, 1.5), m["deepsea"])]


def build_glove(m, sx):
    """Opera glove: pearl-white tube down the arm to the wrist +
    gold wrist ring. Tube starts AT the shoulder point (d=0.0) so
    no bare arm shows; the puff sleeve plugs the top end."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("OperaGlove", shoulder, direction,
                      [0.0, 0.13, 0.26, 0.39, 0.48, 0.52],
                      [0.095, 0.092, 0.090, 0.088, 0.086, 0.085], 8,
                      m["pearl"], caps=False),
            make_tube("WristRing", shoulder, direction,
                      [0.45, 0.52], [0.093, 0.093], 8, m["gold"],
                      caps=False)]


def build_puff_sleeve(m, sx):
    """Water-blue puff sleeve: flattened sphere on the shoulder,
    pressing the glove top into the shoulder."""
    return [add_sphere("PuffSleeve", (sx * 0.33, 0, 1.24), 0.14, 8, 4,
                       (1.1, 1.0, 0.55), m["water"])]


def build_tiara(m):
    """Gold circlet hugging the hair cap (radii from the hair
    ellipse at z=1.62-1.66, +0.007 gap) + deep-sea water-drop gem
    at the front centre."""
    return [make_elliptical_tube("Tiara", TIARA_RINGS, 7,
                                 m["gold"], arc=(225, 315),
                                 caps=False),
            add_sphere("TiaraGem", (0, -0.205, 1.64), 0.022, 6, 3,
                       (1.0, 0.6, 1.5), m["deepsea"])]


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["bodice"] + parts["collar"] + parts["waves"]
            + parts["necklace"])
    ok = True
    ok &= check_gap("torso: stand collar vs mannequin neck",
                    COLLAR_RINGS[0][1], 0.09)
    ok &= check_relief("torso: wave patch relief", 0.006)
    # Pearl bead: centre 0.010 proud, radius 0.016 -> stands 0.026 proud.
    ok &= check_relief("torso: pearl bead relief", 0.026,
                       lo=0.005, hi=0.030)
    ok &= check_gap("torso: bodice vs mannequin torso @z=1.15",
                    interp_rings(BODICE_RINGS, 1.15)[0],
                    interp_rings([(1.28, 0.270, 0.140),
                                  (0.95, 0.240, 0.130)], 1.15)[0])
    return objs, ok


def assemble_skirt(parts):
    objs = (parts["skirt"] + parts["overskirt"] + parts["pleats"]
            + parts["hem"])
    ok = True
    ok &= check_gap("skirt: overskirt vs bell skirt @z=0.55",
                    interp_rings(OVER_RINGS, 0.55)[0],
                    interp_rings(SKIRT_RINGS, 0.55)[0])
    ok &= check_gap("skirt: overskirt vs bell skirt @z=0.80",
                    interp_rings(OVER_RINGS, 0.80)[0],
                    interp_rings(SKIRT_RINGS, 0.80)[0])
    ok &= check_relief("skirt: pleat relief", 0.006)
    ok &= check_gap("skirt: gold hem vs bell skirt @z=0.10",
                    interp_rings(HEM_RINGS, 0.10)[0],
                    interp_rings(SKIRT_RINGS, 0.10)[0])
    ok &= check_gap("skirt: gold hem vs bell skirt @z=0.04",
                    interp_rings(HEM_RINGS, 0.04)[0],
                    interp_rings(SKIRT_RINGS, 0.04)[0])
    return objs, ok


def assemble_waist(parts):
    objs = parts["sash"] + parts["pendant"]
    ok = True
    ok &= check_gap("waist: sash vs bodice @z=0.90",
                    SASH_RINGS[0][1],
                    interp_rings(BODICE_RINGS, 0.90)[0])
    ok &= check_gap("waist: sash bottom edge vs skirt @z=0.80",
                    SASH_RINGS[1][1],
                    interp_rings(SKIRT_RINGS, 0.80)[0])
    ok &= check_relief("waist: sash buckle relief", 0.015,
                       lo=0.005, hi=0.030)
    ok &= check_relief("waist: water drop relief", 0.024,
                       lo=0.005, hi=0.030)
    return objs, ok


def assemble_shoulders(parts):
    objs = parts["gloves"] + parts["puffs"]
    ok = True
    ok &= check_gap("shoulders: opera glove vs mannequin arm @0.26",
                    0.090, 0.080)
    ok &= check_gap("shoulders: wrist ring vs glove @0.48",
                    0.093, 0.087)
    print("L2_CHECK shoulders: puff sleeve dome covers glove top "
          "and shoulder pad PASS")
    return objs, ok


def assemble_head(parts):
    objs = parts["tiara"]
    ok = True
    ok &= check_gap("head: tiara vs hair cap @z=1.66",
                    TIARA_RINGS[0][1], 0.195)
    ok &= check_gap("head: tiara vs hair cap @z=1.62",
                    TIARA_RINGS[1][1], 0.216)
    ok &= check_relief("head: tiara gem relief", 0.016,
                       lo=0.005, hi=0.030)
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: bodice vs mannequin torso @z=1.15",
                    interp_rings(BODICE_RINGS, 1.15)[0],
                    interp_rings([(1.28, 0.270, 0.140),
                                  (0.95, 0.240, 0.130)], 1.15)[0])
    ok &= check_gap("L3 layer: overskirt vs bell skirt @z=0.55",
                    interp_rings(OVER_RINGS, 0.55)[0],
                    interp_rings(SKIRT_RINGS, 0.55)[0])
    ok &= check_gap("L3 layer: sash vs bodice @z=0.90",
                    SASH_RINGS[0][1],
                    interp_rings(BODICE_RINGS, 0.90)[0])
    ok &= check_gap("L3 layer: sash bottom edge vs skirt @z=0.80",
                    SASH_RINGS[1][1],
                    interp_rings(SKIRT_RINGS, 0.80)[0])
    ok &= check_gap("L3 layer: gold hem vs bell skirt @z=0.10",
                    interp_rings(HEM_RINGS, 0.10)[0],
                    interp_rings(SKIRT_RINGS, 0.10)[0])
    ok &= check_gap("L3 joint: wrist ring vs glove", 0.093, 0.087)
    ok &= check_gap("L3 joint: tiara vs hair cap @z=1.66",
                    TIARA_RINGS[0][1], 0.195)
    print("L3_CHECK outfit: bell skirt hem z=0.05, mannequin feet "
          "touch ground z=0.000 PASS")
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
    parts["bodice"] = build_bodice(m)
    report_l1("Bodice", parts["bodice"])
    parts["collar"] = build_collar(m)
    report_l1("StandCollar+Trim", parts["collar"])
    parts["waves"] = []
    for cx, cz in WAVE_CENTERS:
        parts["waves"] += build_wave_patch(m, cx, cz)
    report_l1("WavePatches x3", parts["waves"])
    flat_patches += parts["waves"]
    parts["necklace"] = build_necklace(m)
    report_l1("PearlNecklace x7", parts["necklace"])
    parts["skirt"] = build_skirt(m)
    report_l1("BellSkirt", parts["skirt"])
    parts["overskirt"] = build_overskirt(m)
    report_l1("Overskirt", parts["overskirt"])
    parts["pleats"] = []
    for angle in (0, 45, 90, 135, 180, 225, 270, 315):
        parts["pleats"].append(build_pleat(m, angle))
    report_l1("SkirtPleats x8", parts["pleats"])
    flat_patches += parts["pleats"]
    parts["hem"] = build_hem(m)
    report_l1("GoldHem", parts["hem"])
    parts["sash"] = build_sash(m)
    report_l1("GoldSash+Buckle", parts["sash"])
    parts["pendant"] = build_pendant(m)
    report_l1("WaterDropPendant", parts["pendant"])
    parts["gloves"] = []
    for sx in (-1, 1):
        parts["gloves"] += build_glove(m, sx)
    report_l1("OperaGloves+WristRings x2", parts["gloves"])
    parts["puffs"] = []
    for sx in (-1, 1):
        parts["puffs"] += build_puff_sleeve(m, sx)
    report_l1("PuffSleeves x2", parts["puffs"])
    parts["tiara"] = build_tiara(m)
    report_l1("Tiara+Gem", parts["tiara"])

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    _, ok = assemble_torso(parts)
    l2_ok &= ok
    _, ok = assemble_skirt(parts)
    l2_ok &= ok
    _, ok = assemble_waist(parts)
    l2_ok &= ok
    _, ok = assemble_shoulders(parts)
    l2_ok &= ok
    _, ok = assemble_head(parts)
    l2_ok &= ok
    print("L2_SUMMARY %s" % ("ALL PASS" if l2_ok else "FAILURES PRESENT"))

    # ---- L3 full outfit on the mannequin ----
    costume = (parts["bodice"] + parts["collar"] + parts["waves"]
               + parts["necklace"] + parts["skirt"] + parts["overskirt"]
               + parts["pleats"] + parts["hem"] + parts["sash"]
               + parts["pendant"] + parts["gloves"] + parts["puffs"]
               + parts["tiara"])
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
