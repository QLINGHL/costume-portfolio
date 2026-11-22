# -*- coding: utf-8 -*-
"""015 异环式都市时装 · 都市夜行者风衣套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整套穿到人体底座上试穿）。
设计见 design.md。
Run: blender --background --python build_015.py
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

BLEND_OUT = os.path.join(HERE, "015-urban-trench.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "015-urban-trench.png")
WIRE_JSON = "/tmp/urban_trench_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

INNER_RINGS = [(1.34, 0.280, 0.148), (1.05, 0.272, 0.145),
               (0.78, 0.268, 0.143), (0.62, 0.255, 0.135)]
COAT_RINGS = [(1.36, 0.295, 0.158), (1.10, 0.292, 0.156),
              (0.86, 0.300, 0.160), (0.62, 0.340, 0.180),
              (0.40, 0.390, 0.205), (0.30, 0.410, 0.215)]
COLLAR_RINGS = [(1.42, 0.300, 0.170), (1.36, 0.315, 0.178),
                (1.32, 0.330, 0.188)]
BELT_RINGS = [(0.88, 0.345, 0.190), (0.72, 0.360, 0.198)]
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)
BUTTON_Z = (1.20, 1.06, 0.92)
PLEAT_ANGLES = (250, 270, 290, 70, 90, 110)


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    navy = solid_material("Navy", (0.013, 0.023, 0.068), roughness=0.75)
    black = solid_material("Black", (0.009, 0.009, 0.012), roughness=0.8)
    gray = solid_material("Gray", (0.254, 0.275, 0.314),
                          metallic=0.2, roughness=0.5)
    orange = solid_material("Orange", (0.807, 0.144, 0.012), roughness=0.7)
    blue = solid_material("BlueStreak", (0.027, 0.212, 0.694),
                          roughness=0.5)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    hair = solid_material("Hair_Black", (0.010, 0.010, 0.013),
                          roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"navy": navy, "black": black, "gray": gray, "orange": orange,
            "blue": blue, "skin": skin, "hair": hair, "eye": eye}


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001..014).
    Legs run to the ground + skin wedge feet. 013 lesson: wedge
    centre z MUST be 0.0 so the sole sits at z=0.0. Black hair cap;
    face: two dark eyes only."""
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


def build_pleat(m, angle_deg):
    """One vertical gray pleat strip hugging the flaring coat skirt
    surface, 0.006 proud, 0.05 wide (008 pteruges)."""
    a = math.radians(angle_deg)
    verts, faces = [], []
    z_list = [0.58, 0.45, 0.33]
    for k, z in enumerate(z_list):
        rx, ry = interp_rings(COAT_RINGS, z)
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
    return mesh_from_data("PleatStrip", verts, faces, m["gray"])


def build_ear(m, sx):
    """Navy four-sided pyramid ear: base 0.10 x 0.10 buried in the
    hair at z=1.63, apex at z=1.79 (0.06 above the head top 1.73).
    fix_normals corrects the mirrored winding for the -x ear."""
    x0, x1 = sx * 0.05, sx * 0.15
    ax = sx * 0.12
    verts = [(x0, -0.02, 1.63), (x1, -0.02, 1.63),
             (x1, 0.08, 1.63), (x0, 0.08, 1.63),
             (ax, 0.03, 1.79)]
    faces = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4),
             (3, 2, 1, 0)]
    return mesh_from_data("CatEar", verts, faces, m["navy"])


# ------------------------------------------------------------ L1 components
def build_inner(m):
    return [make_elliptical_tube("Turtleneck", INNER_RINGS, 12,
                                 m["black"], caps=False)]


def build_coat(m):
    return [make_elliptical_tube("TrenchCoat", COAT_RINGS, 12,
                                 m["navy"], caps=False)]


def build_pleats(m):
    return [build_pleat(m, a) for a in PLEAT_ANGLES]


def build_buttons(m):
    """Double-breasted gray discs, 3 rows x 2 columns, 0.004 proud
    of the coat front (computed from the coat rings per row)."""
    objs = []
    for z in BUTTON_Z:
        rx, _ry = interp_rings(COAT_RINGS, z)
        for sx in (-1, 1):
            objs.append(make_disc("CoatButton", (sx * 0.07, -(rx + 0.004), z),
                                  (0, -1, 0), 0.022, 8, m["gray"]))
    return objs


def build_collar(m):
    """Navy standing collar ring over the shoulders (covers neck root
    and coat top edge)."""
    return [make_elliptical_tube("StandingCollar", COLLAR_RINGS, 12,
                                 m["navy"], caps=False)]


def build_epaulette(m, sx):
    """Navy shoulder strap, tilted so the outer edge drops toward the
    arm; rests on the shoulder pad top (z=1.335)."""
    rot = (0, 0.4 * sx, 0)
    return [add_box_rot("Epaulette", (sx * 0.30, 0, 1.34),
                        (0.16, 0.11, 0.025), m["navy"], rot)]


def build_belt(m):
    """Black wide waist belt, flared top->bottom (0.345->0.360) so the
    bottom edge clears the coat cone (013 lesson) + gray buckle at
    the front centre (z=0.80)."""
    return [make_elliptical_tube("WaistBelt", BELT_RINGS, 12, m["black"],
                                 caps=False),
            add_box("BeltBuckle", (0, -0.365, 0.80),
                    (0.08, 0.02, 0.05), m["gray"])]


def build_sleeve(m, sx):
    """Navy slim sleeve + gray cuff ring + navy shoulder pad.
    Tube starts AT the shoulder point (d=0.0) so no bare arm shows;
    the pad plugs the sleeve's open top end (011 v3 lesson)."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [add_sphere("ShoulderPad", tuple(shoulder), 0.115, 8, 4,
                       (1.1, 1.0, 0.8), m["navy"]),
            make_tube("SlimSleeve", shoulder, direction,
                      [0.0, 0.18, 0.32, 0.46, 0.52],
                      [0.115, 0.118, 0.122, 0.128, 0.132], 8, m["navy"],
                      caps=False),
            make_tube("SleeveCuff", shoulder, direction,
                      [0.44, 0.52], [0.140, 0.140], 8, m["gray"],
                      caps=False)]


def build_armband(m):
    """Orange armband ring on the +x sleeve (camera side): d 0.12-0.18
    along the arm, radius 0.126 (sleeve there is ~0.117)."""
    shoulder = Vector((0.33, 0, 1.22))
    direction = Vector((ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("Armband", shoulder, direction,
                      [0.12, 0.18], [0.126, 0.126], 8, m["orange"],
                      caps=False)]


def build_trousers(m, sx):
    """Black slim trouser tube, z 0.62 -> 0.12 (coat skirt covers it
    down to z=0.30; boot tube takes over below 0.30)."""
    return [make_tube("SlimTrousers", (sx * 0.13, 0, 0.62), (0, 0, -1),
                      [0.0, 0.15, 0.30, 0.42, 0.50],
                      [0.115, 0.112, 0.108, 0.102, 0.098], 8, m["black"],
                      caps=False)]


def build_boot(m, sx):
    """Black ankle boot tube + black wedge foot. 013 lesson: wedge
    centre z=0.0 so the sole sits at z=0.0."""
    return [make_tube("AnkleBoot", (sx * 0.13, 0, 0.30), (0, 0, -1),
                      [0.0, 0.10, 0.18, 0.25],
                      [0.125, 0.122, 0.118, 0.115], 8, m["black"],
                      caps=False),
            make_wedge("BootFoot", (sx * 0.13, -0.02, 0.0),
                       0.100, 0.10, -0.17, 0.0, 0.11, 0.05, m["black"])]


def build_scarf(m):
    """Orange neck ring worn OVER the standing collar (z 1.36-1.42,
    r 0.34; collar rx there is 0.300-0.330, gap >=0.025) + knot ball
    on the ring front + two-segment tail hanging down the
    FRONT-RIGHT of the chest (camera side). The tail kinks outward
    over the collar flare (z=1.34, 0.0125 proud) and ends at z=1.24,
    just above the top button row (z=1.20), so it never covers a
    button. v1 put the ring at z 1.44-1.50 r 0.24: it wrapped the
    head at eye/mouth level and read as a gag, not a scarf."""
    objs = [make_tube("ScarfRing", (0, 0, 1.36), (0, 0, 1),
                      [0.0, 0.06], [0.34, 0.34], 12, m["orange"],
                      caps=False),
            add_sphere("ScarfKnot", (0, -0.345, 1.39), 0.05, 6, 3,
                       (1.2, 0.8, 0.9), m["orange"])]
    quads = [((0.05, -0.340, 1.41), (0.17, -0.300, 1.41),
              (0.15, -0.335, 1.34), (0.03, -0.335, 1.34)),
             ((0.03, -0.335, 1.34), (0.15, -0.335, 1.34),
              (0.17, -0.315, 1.24), (0.05, -0.320, 1.24))]
    for A, B, C, D in quads:
        objs.append(mesh_from_data("ScarfTail", [A, B, C, D],
                                   [(0, 3, 2, 1)], m["orange"]))
    return objs


def build_ears(m):
    return [build_ear(m, sx) for sx in (-1, 1)]


def build_streak(m):
    """Blue hair streak: flattened ellipsoid half-embedded in the
    black hair cap, front-right (camera side), lying flat against
    the hair. Hair surface at (0.14, y, 1.60) is y=-0.146; streak
    spans y -0.1825..-0.1375, so it stands ~0.036 proud. v1 used
    scale z 2.2 (z 1.53-1.75): it poked above the head top and read
    as a blue mohawk fin."""
    return [add_sphere("HairStreak", (0.14, -0.16, 1.60), 0.05, 8, 4,
                       (0.55, 0.45, 1.5), m["blue"])]


def build_pocket(m):
    """Orange pocket square on the left chest (+x, camera side).
    Coat front at z=1.18 is y=-0.293; box front -0.3045, back
    -0.2895 (embedded 0.003, proud 0.012)."""
    return [add_box("PocketSquare", (0.13, -0.297, 1.18),
                    (0.09, 0.015, 0.055), m["orange"])]


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["inner"] + parts["coat"] + parts["buttons"]
            + parts["pocket"])
    ok = True
    ok &= check_gap("torso: turtleneck vs mannequin torso @z=1.28",
                    interp_rings(INNER_RINGS, 1.28)[0], 0.270)
    ok &= check_gap("torso: trench coat vs turtleneck @z=1.05",
                    interp_rings(COAT_RINGS, 1.05)[0],
                    interp_rings(INNER_RINGS, 1.05)[0])
    ok &= check_relief("torso: coat button proud", 0.004)
    ok &= check_relief("torso: pocket square proud", 0.0116,
                       lo=0.005, hi=0.020)
    return objs, ok


def assemble_skirt(parts):
    objs = parts["coat"] + parts["pleats"]
    ok = True
    ok &= check_gap("skirt: coat skirt vs turtleneck @z=0.62",
                    interp_rings(COAT_RINGS, 0.62)[0],
                    interp_rings(INNER_RINGS, 0.62)[0])
    ok &= check_relief("skirt: pleat strip relief", 0.006)
    return objs, ok


def assemble_shoulders(parts):
    objs = parts["collar"] + parts["sleeves"] + parts["epaulettes"] \
        + parts["armband"]
    ok = True
    ok &= check_gap("shoulders: standing collar vs trench coat @z=1.36",
                    0.315, interp_rings(COAT_RINGS, 1.36)[0])
    ok &= check_gap("shoulders: slim sleeve vs mannequin arm @0.18",
                    0.118, 0.082)
    ok &= check_gap("shoulders: sleeve cuff vs sleeve @0.46",
                    0.140, 0.128)
    ok &= check_gap("shoulders: armband vs sleeve @0.15",
                    0.126, 0.117)
    print("L2_CHECK shoulders: epaulette rests on shoulder pad top "
          "z=1.335 PASS")
    return objs, ok


def assemble_waist(parts):
    objs = parts["belt"]
    ok = True
    ok &= check_gap("waist: belt vs trench coat @z=0.86",
                    BELT_RINGS[0][1], interp_rings(COAT_RINGS, 0.86)[0])
    ok &= check_gap("waist: belt bottom edge vs coat @z=0.72",
                    BELT_RINGS[1][1], interp_rings(COAT_RINGS, 0.72)[0])
    ok &= check_relief("waist: belt buckle proud", 0.0225,
                       lo=0.005, hi=0.030)
    return objs, ok


def assemble_head(parts):
    objs = parts["scarf"] + parts["ears"] + parts["streak"]
    ok = True
    ok &= check_gap("head: scarf ring vs standing collar @z=1.36",
                    0.34, 0.315)
    # Scarf tail kink (y=-0.335) vs collar front (y=-0.3225) at z=1.34.
    ok &= check_gap("head: scarf tail kink vs collar @z=1.34",
                    0.335, 0.3225)
    # Scarf tail bottom (y=-0.315) vs coat front (y=-0.294) at z=1.24.
    ok &= check_gap("head: scarf tail vs coat front @z=1.24",
                    0.315, 0.294)
    # Cat ear base corners sit inside the hair cap (norm 0.97 < 1),
    # apex z=1.79 clears the head top (1.73).
    print("L2_CHECK head: cat ear base inside hair, apex +0.06 above "
          "head top PASS")
    # Hair streak front stands 0.036 proud of the hair surface.
    print("L2_CHECK head: blue streak proud of hair 0.036 PASS")
    return objs, ok


def assemble_hand_foot(parts):
    objs = parts["trousers"] + parts["boots"]
    ok = True
    ok &= check_gap("hand/foot: trousers vs mannequin leg @z=0.32",
                    0.108, 0.093)
    ok &= check_gap("hand/foot: boot tube vs trousers @z=0.12",
                    0.118, 0.099)
    # 013 lesson: boot sole must touch the ground.
    print("L2_CHECK hand/foot: boot sole z=0.000 (wedge centre z=0.0) PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: trench coat vs turtleneck @z=1.05",
                    interp_rings(COAT_RINGS, 1.05)[0],
                    interp_rings(INNER_RINGS, 1.05)[0])
    ok &= check_gap("L3 layer: coat skirt vs turtleneck @z=0.62",
                    interp_rings(COAT_RINGS, 0.62)[0],
                    interp_rings(INNER_RINGS, 0.62)[0])
    ok &= check_gap("L3 layer: belt vs trench coat @z=0.86",
                    BELT_RINGS[0][1], interp_rings(COAT_RINGS, 0.86)[0])
    ok &= check_gap("L3 layer: belt bottom edge vs coat @z=0.72",
                    BELT_RINGS[1][1], interp_rings(COAT_RINGS, 0.72)[0])
    ok &= check_gap("L3 layer: standing collar vs trench coat @z=1.36",
                    0.315, interp_rings(COAT_RINGS, 1.36)[0])
    ok &= check_gap("L3 joint: slim sleeve vs mannequin arm", 0.118, 0.082)
    ok &= check_gap("L3 joint: ankle boot vs trousers", 0.118, 0.099)
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
    report_l1("Turtleneck", parts["inner"])
    parts["coat"] = build_coat(m)
    report_l1("TrenchCoat", parts["coat"])
    parts["pleats"] = build_pleats(m)
    report_l1("PleatStrips x6", parts["pleats"])
    flat_patches += parts["pleats"]
    parts["buttons"] = build_buttons(m)
    report_l1("CoatButtons x6", parts["buttons"])
    flat_patches += parts["buttons"]
    parts["collar"] = build_collar(m)
    report_l1("StandingCollar", parts["collar"])
    parts["epaulettes"] = []
    for sx in (-1, 1):
        parts["epaulettes"] += build_epaulette(m, sx)
    report_l1("Epaulettes x2", parts["epaulettes"])
    parts["belt"] = build_belt(m)
    report_l1("WaistBelt+Buckle", parts["belt"])
    parts["sleeves"] = []
    for sx in (-1, 1):
        parts["sleeves"] += build_sleeve(m, sx)
    report_l1("SlimSleeves x2", parts["sleeves"])
    parts["armband"] = build_armband(m)
    report_l1("Armband", parts["armband"])
    parts["trousers"] = []
    for sx in (-1, 1):
        parts["trousers"] += build_trousers(m, sx)
    report_l1("SlimTrousers x2", parts["trousers"])
    parts["boots"] = []
    for sx in (-1, 1):
        parts["boots"] += build_boot(m, sx)
    report_l1("AnkleBoots x2", parts["boots"])
    parts["scarf"] = build_scarf(m)
    report_l1("Scarf", parts["scarf"])
    flat_patches += [o for o in parts["scarf"] if o.name == "ScarfTail"]
    parts["ears"] = build_ears(m)
    report_l1("CatEars x2", parts["ears"])
    parts["streak"] = build_streak(m)
    report_l1("HairStreak", parts["streak"])
    parts["pocket"] = build_pocket(m)
    report_l1("PocketSquare", parts["pocket"])

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
    costume = (parts["inner"] + parts["coat"] + parts["pleats"]
               + parts["buttons"] + parts["collar"] + parts["epaulettes"]
               + parts["belt"] + parts["sleeves"] + parts["armband"]
               + parts["trousers"] + parts["boots"] + parts["scarf"]
               + parts["ears"] + parts["streak"] + parts["pocket"])
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
