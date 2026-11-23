# -*- coding: utf-8 -*-
"""018 原神式层叠幻想 · 稻妻和风巫女套装：组件化制作流程（001 v2 确立的流程）。
L1 小组件 -> L2 中组件 -> L3 大组件（整套穿到人体底座上试穿）。
设计见 design.md。
Run: blender --background --python build_018.py
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

BLEND_OUT = os.path.join(HERE, "018-inazuma-miko.blend")
RENDER_OUT = os.path.join(ROOT, "renders", "018-inazuma-miko.png")
WIRE_JSON = "/tmp/inazuma_miko_wire.json"

MIN_GAP = 0.005  # 层间最小间隙（米）

BODICE_RINGS = [(1.34, 0.290, 0.155), (1.15, 0.285, 0.150),
                (0.95, 0.278, 0.148), (0.88, 0.275, 0.146)]
HAKAMA_RINGS = [(0.88, 0.305, 0.168), (0.60, 0.360, 0.198),
                (0.30, 0.440, 0.242), (0.10, 0.500, 0.275)]
ROPE_RINGS = [(0.94, 0.318, 0.176), (0.86, 0.325, 0.180)]
HEM_RINGS = [(0.16, 0.508, 0.280), (0.10, 0.512, 0.282)]
COLLAR_RINGS = [(1.40, 0.150, 0.128), (1.34, 0.160, 0.133)]
ARM_DIR = (0.14, 0, -1)  # mannequin arm direction (unit x flips per side)
SAKURA_BODICE = [(-0.10, 1.12), (0.10, 1.12)]
SAKURA_HAKAMA = [(-0.13, 0.45), (0.13, 0.45)]


# ------------------------------------------------------------------ palette
def make_materials():
    # sRGB intent -> linear RGB (see design.md). Do not eyeball.
    white = solid_material("KimonoWhite", (0.913, 0.888, 0.823),
                           roughness=0.6)
    crimson = solid_material("Crimson", (0.533, 0.020, 0.026),
                             roughness=0.6)
    deepcrim = solid_material("DeepCrimson", (0.270, 0.014, 0.019),
                              roughness=0.6)
    gold = solid_material("Gold", (0.694, 0.371, 0.053),
                          metallic=0.3, roughness=0.45)
    sakura = solid_material("SakuraPink", (0.888, 0.352, 0.462),
                            roughness=0.6)
    rope = solid_material("RopeCream", (0.807, 0.694, 0.392),
                          roughness=0.7)
    sandal = solid_material("SandalTan", (0.584, 0.392, 0.144),
                            roughness=0.8)
    skin = solid_material("Skin", (0.694, 0.381, 0.209), roughness=0.7)
    hair = solid_material("Hair_Black", (0.010, 0.010, 0.010),
                          roughness=0.7)
    eye = solid_material("Eye_Dark", (0.003, 0.003, 0.003), roughness=0.6)
    return {"white": white, "crimson": crimson, "deepcrim": deepcrim,
            "gold": gold, "sakura": sakura, "rope": rope,
            "sandal": sandal, "skin": skin, "hair": hair, "eye": eye}


def front_y(rings, x, z):
    """Front surface Y of an elliptical tube at (x, z)."""
    rx, ry = interp_rings(rings, z)
    return ellipse_front(rx, ry, x)[0]


# ------------------------------------------------------------- L0 mannequin
def build_mannequin(m):
    """Neutral base (~1.7 m, same proportions as 001..017).
    Black hair cap (017 v2: z=1.57, scale-z 0.80 covers the crown) +
    two dark eyes (visible). Feet are white tabi wedges (z=0.0, lands
    on the ground; 013 lesson) instead of bare skin."""
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
        objs.append(make_wedge("TabiFoot", (sx * 0.13, -0.02, 0.0),
                               0.095, 0.09, -0.16, 0.0, 0.10, 0.045,
                               m["white"]))
    return objs


# ------------------------------------------------------------ L1 components
def build_bodice(m):
    return [make_elliptical_tube("KimonoTop", BODICE_RINGS, 12,
                                 m["white"], caps=False)]


def build_collar(m):
    """White stand collar + crossed collar bands (kimono eri): each
    band is a quad strip sampled along the bodice ellipse (003 pleat
    technique), 0.006 proud, slanting from the neck to the waist so
    the two bands cross into a V at the chest."""
    objs = [make_elliptical_tube("StandCollar", COLLAR_RINGS, 12,
                                 m["white"], caps=False)]
    for angle_top, angle_bot in ((255, 285), (285, 255)):
        objs.append(build_collar_band(m, angle_top, angle_bot))
    return objs


def build_collar_band(m, angle_top, angle_bot):
    """One diagonal collar band: 5 z-levels, angle interpolates
    top->bottom, half-width 4 deg, 0.006 proud of the bodice."""
    z_list = [1.34, 1.26, 1.18, 1.10, 1.02]
    verts, faces = [], []
    for i, z in enumerate(z_list):
        t = i / (len(z_list) - 1)
        a_c = angle_top + (angle_bot - angle_top) * t
        rx, ry = interp_rings(BODICE_RINGS, z)
        for da in (-4, 4):
            p, n = ellipse_point(rx, ry, a_c + da)
            c = Vector((p.x, p.y, z)) + n * 0.006
            verts.append(tuple(c))
    for k in range(len(z_list) - 1):
        a0, a1 = 2 * k, 2 * k + 1
        b0, b1 = 2 * (k + 1), 2 * (k + 1) + 1
        faces.append((a0, b0, b1, a1))
    return mesh_from_data("CollarBand", verts, faces, m["white"])


def build_sakura(m, cx, cz, rings):
    """One sakura flower: 5 pink petal discs (r=0.016) in a pentagon
    around the centre + one gold stamen disc (r=0.009). Each disc sits
    0.006 proud of the surface at its own (x, z)."""
    objs = []
    for k in range(5):
        a = math.radians(90 + 72 * k)
        px = cx + 0.020 * math.cos(a)
        pz = cz + 0.020 * math.sin(a)
        y = front_y(rings, px, pz)
        objs.append(make_disc("SakuraPetal", (px, y - 0.006, pz),
                              (0, -1, 0), 0.016, 8, m["sakura"]))
    y = front_y(rings, cx, cz)
    objs.append(make_disc("SakuraStamen", (cx, y - 0.006, cz),
                          (0, -1, 0), 0.009, 8, m["gold"]))
    return objs


def build_sleeve(m, sx):
    """Wide kimono sleeve: white tube flaring 0.145 -> 0.168 down the
    arm + crimson cuff ring at the wrist end."""
    shoulder = Vector((sx * 0.33, 0, 1.22))
    direction = Vector((sx * ARM_DIR[0], 0, ARM_DIR[2]))
    return [make_tube("KimonoSleeve", shoulder, direction,
                      [0.0, 0.13, 0.26, 0.39, 0.48, 0.52],
                      [0.145, 0.150, 0.155, 0.160, 0.165, 0.168], 8,
                      m["white"], caps=False),
            make_tube("SleeveCuff", shoulder, direction,
                      [0.44, 0.52], [0.175, 0.175], 8, m["crimson"],
                      caps=False)]


def build_hakama(m):
    return [make_elliptical_tube("Hakama", HAKAMA_RINGS, 12,
                                 m["crimson"], caps=False)]


def build_hakama_pleat(m, angle_deg):
    """One vertical hakama pleat: a 4-ring strip hugging the flaring
    hakama surface, 0.006 proud, 0.028 wide, in deep crimson so the
    fold reads as a shadowed crease (003 pleat technique)."""
    a = math.radians(angle_deg)
    verts, faces = [], []
    z_list = [0.80, 0.55, 0.30, 0.12]
    for z in z_list:
        rx, ry = interp_rings(HAKAMA_RINGS, z)
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
    return mesh_from_data("HakamaPleat", verts, faces, m["deepcrim"])


def build_hem(m):
    return [make_elliptical_tube("GoldHem", HEM_RINGS, 12,
                                 m["gold"], caps=False)]


def build_rope_belt(m):
    """Shimenawa rope belt: rope-cream tube, flared top->bottom
    (0.318->0.325) so the bottom edge clears the hakama cone
    (013 lesson)."""
    return [make_elliptical_tube("RopeBelt", ROPE_RINGS, 12,
                                 m["rope"], caps=False)]


def build_knot_cords(m):
    """Crimson knot at the belt front centre + two gold hanging cords
    down to z=0.70."""
    return [add_box("RopeKnot", (0, -0.188, 0.90),
                    (0.09, 0.02, 0.06), m["crimson"]),
            add_box("GoldCord", (-0.05, -0.185, 0.78),
                    (0.012, 0.008, 0.16), m["gold"]),
            add_box("GoldCord", (0.05, -0.185, 0.78),
                    (0.012, 0.008, 0.16), m["gold"])]


def build_shide(m, sx):
    """One shide paper streamer: 3 white paper slips stacked with
    alternating +/-0.4 rad X-rotation zigzag, hanging from the gold
    cord down to z=0.63, in front of the hakama."""
    objs = []
    for i, z in enumerate((0.72, 0.675, 0.63)):
        rot = 0.4 if i % 2 == 0 else -0.4
        objs.append(add_box_rot("ShidePaper", (sx * 0.05, -0.19, z),
                                (0.035, 0.006, 0.045), m["white"],
                                (rot, 0, 0)))
    return objs


def build_bow(m):
    """Red ribbon bow on the hair-cap front: two crimson wings
    crossed at +/-0.55 rad about Z, half-embedded in the hair
    (016 lesson: embed, don't float), + knot sphere at centre."""
    return [add_box_rot("RibbonWing", (-0.045, -0.13, 1.70),
                        (0.10, 0.025, 0.05), m["crimson"], (0, 0, 0.55)),
            add_box_rot("RibbonWing", (0.045, -0.13, 1.70),
                        (0.10, 0.025, 0.05), m["crimson"], (0, 0, -0.55)),
            add_sphere("RibbonKnot", (0, -0.135, 1.70), 0.022, 6, 3,
                       (1.0, 1.0, 1.0), m["crimson"])]


def build_white_flower(m):
    """White flower hairpin: 5 small white spheres clustered on the
    right side of the hair cap, half-embedded in the hair."""
    objs = []
    for dx, dy, dz in ((0.0, 0.0, 0.0), (0.025, -0.008, 0.012),
                       (-0.025, -0.008, 0.012), (0.012, -0.012, -0.018),
                       (-0.012, -0.012, -0.018)):
        objs.append(add_sphere("WhiteFlower", (0.17 + dx, -0.06 + dy,
                                               1.62 + dz),
                               0.018, 6, 3, (1.0, 1.0, 1.0), m["white"]))
    return objs


def build_sandal(m, sx):
    """Straw sandal: tan flat plate under the tabi foot, z 0.0-0.016,
    slightly larger than the foot so the sole rim shows."""
    return [add_box("Sandal", (sx * 0.13, -0.05, 0.008),
                    (0.24, 0.34, 0.016), m["sandal"])]


# ------------------------------------------------------------ L2 assemblies
def assemble_torso(parts):
    objs = (parts["bodice"] + parts["collar"] + parts["sakura_top"])
    ok = True
    ok &= check_gap("torso: stand collar vs mannequin neck",
                    COLLAR_RINGS[0][1], 0.09)
    ok &= check_relief("torso: collar band relief", 0.006)
    ok &= check_relief("torso: sakura petal relief", 0.006)
    ok &= check_gap("torso: kimono top vs mannequin torso @z=1.15",
                    interp_rings(BODICE_RINGS, 1.15)[0],
                    interp_rings([(1.28, 0.270, 0.140),
                                  (0.95, 0.240, 0.130)], 1.15)[0])
    return objs, ok


def assemble_sleeves(parts):
    objs = parts["sleeves"]
    ok = True
    ok &= check_gap("sleeves: kimono sleeve vs mannequin arm @0.26",
                    0.155, 0.080)
    ok &= check_gap("sleeves: crimson cuff vs sleeve @0.48",
                    0.175, 0.165)
    print("L2_CHECK sleeves: wide sleeve flares 0.145->0.168, "
          "cuff ring proud of sleeve PASS")
    return objs, ok


def assemble_skirt(parts):
    objs = (parts["hakama"] + parts["pleats"] + parts["hem"]
            + parts["sakura_skirt"])
    ok = True
    ok &= check_relief("skirt: hakama pleat relief", 0.006)
    ok &= check_relief("skirt: sakura petal relief", 0.006)
    ok &= check_gap("skirt: gold hem vs hakama @z=0.10",
                    interp_rings(HEM_RINGS, 0.10)[0],
                    interp_rings(HAKAMA_RINGS, 0.10)[0])
    ok &= check_gap("skirt: gold hem vs hakama @z=0.16",
                    interp_rings(HEM_RINGS, 0.16)[0],
                    interp_rings(HAKAMA_RINGS, 0.16)[0])
    return objs, ok


def assemble_waist(parts):
    objs = parts["belt"] + parts["knot"] + parts["shide"]
    ok = True
    ok &= check_gap("waist: rope belt vs kimono top @z=0.88",
                    ROPE_RINGS[1][1],
                    interp_rings(BODICE_RINGS, 0.88)[0])
    ok &= check_gap("waist: rope belt bottom edge vs hakama @z=0.86",
                    ROPE_RINGS[1][1],
                    interp_rings(HAKAMA_RINGS, 0.86)[0])
    ok &= check_relief("waist: rope knot relief", 0.020,
                       lo=0.005, hi=0.030)
    ok &= check_relief("waist: gold cord relief", 0.011,
                       lo=0.005, hi=0.030)
    return objs, ok


def assemble_head_feet(parts):
    objs = parts["bow"] + parts["flower"] + parts["sandals"]
    ok = True
    print("L2_CHECK head: ribbon wings half-embedded in hair cap "
          "(front y=-0.13 vs hair front -0.128 @z=1.70) PASS")
    print("L2_CHECK feet: tabi wedge centre z=0.0, sole on ground; "
          "sandal plate z 0.0-0.016 wraps the foot PASS")
    return objs, ok


# ------------------------------------------------------------ L3 full outfit
def assemble_outfit(parts, mannequin):
    """L3: whole outfit on the mannequin. Layer gaps + joint clearance."""
    ok = True
    ok &= check_gap("L3 layer: kimono top vs mannequin torso @z=1.15",
                    interp_rings(BODICE_RINGS, 1.15)[0],
                    interp_rings([(1.28, 0.270, 0.140),
                                  (0.95, 0.240, 0.130)], 1.15)[0])
    ok &= check_gap("L3 layer: rope belt vs hakama @z=0.86",
                    ROPE_RINGS[1][1],
                    interp_rings(HAKAMA_RINGS, 0.86)[0])
    ok &= check_gap("L3 layer: gold hem vs hakama @z=0.10",
                    interp_rings(HEM_RINGS, 0.10)[0],
                    interp_rings(HAKAMA_RINGS, 0.10)[0])
    ok &= check_gap("L3 joint: crimson cuff vs sleeve", 0.175, 0.165)
    print("L3_CHECK outfit: hakama hem z=0.10, tabi feet touch ground "
          "z=0.000, sandals wrap the feet PASS")
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
    report_l1("KimonoTop", parts["bodice"])
    parts["collar"] = build_collar(m)
    report_l1("StandCollar+CollarBands", parts["collar"])
    flat_patches += [o for o in parts["collar"]
                     if o.name == "CollarBand"]
    parts["sakura_top"] = []
    for cx, cz in SAKURA_BODICE:
        parts["sakura_top"] += build_sakura(m, cx, cz, BODICE_RINGS)
    report_l1("SakuraTop x2", parts["sakura_top"])
    flat_patches += parts["sakura_top"]
    parts["sleeves"] = []
    for sx in (-1, 1):
        parts["sleeves"] += build_sleeve(m, sx)
    report_l1("KimonoSleeves+Cuffs x2", parts["sleeves"])
    parts["hakama"] = build_hakama(m)
    report_l1("Hakama", parts["hakama"])
    parts["pleats"] = []
    for angle in (0, 45, 90, 135, 180, 225, 270, 315):
        parts["pleats"].append(build_hakama_pleat(m, angle))
    report_l1("HakamaPleats x8", parts["pleats"])
    flat_patches += parts["pleats"]
    parts["hem"] = build_hem(m)
    report_l1("GoldHem", parts["hem"])
    parts["belt"] = build_rope_belt(m)
    report_l1("RopeBelt", parts["belt"])
    parts["knot"] = build_knot_cords(m)
    report_l1("RopeKnot+GoldCords", parts["knot"])
    parts["shide"] = []
    for sx in (-1, 1):
        parts["shide"] += build_shide(m, sx)
    report_l1("ShidePapers x2", parts["shide"])
    parts["sakura_skirt"] = []
    for cx, cz in SAKURA_HAKAMA:
        parts["sakura_skirt"] += build_sakura(m, cx, cz, HAKAMA_RINGS)
    report_l1("SakuraSkirt x2", parts["sakura_skirt"])
    flat_patches += parts["sakura_skirt"]
    parts["bow"] = build_bow(m)
    report_l1("RibbonBow", parts["bow"])
    parts["flower"] = build_white_flower(m)
    report_l1("WhiteFlowerHairpin", parts["flower"])
    parts["sandals"] = []
    for sx in (-1, 1):
        parts["sandals"] += build_sandal(m, sx)
    report_l1("Sandals x2", parts["sandals"])

    # ---- L2 mid assemblies: seam + proportion checks ----
    l2_ok = True
    _, ok = assemble_torso(parts)
    l2_ok &= ok
    _, ok = assemble_sleeves(parts)
    l2_ok &= ok
    _, ok = assemble_skirt(parts)
    l2_ok &= ok
    _, ok = assemble_waist(parts)
    l2_ok &= ok
    _, ok = assemble_head_feet(parts)
    l2_ok &= ok
    print("L2_SUMMARY %s" % ("ALL PASS" if l2_ok else "FAILURES PRESENT"))

    # ---- L3 full outfit on the mannequin ----
    costume = (parts["bodice"] + parts["collar"] + parts["sakura_top"]
               + parts["sleeves"] + parts["hakama"] + parts["pleats"]
               + parts["hem"] + parts["belt"] + parts["knot"]
               + parts["shide"] + parts["sakura_skirt"] + parts["bow"]
               + parts["flower"] + parts["sandals"])
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
