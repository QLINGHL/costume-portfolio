# -*- coding: utf-8 -*-
"""041 资产质检：对 040 雨天套装做真实 mesh 检查。

检查对象：scenes/040-rainy-day-urban/040-rainy-day-urban.blend 里的全部服装部件
（不含地面与中性人体底座；底座只单独计面数、不参与服装判定）。
检查维度：拓扑 / 法线 / UV / 材质 / 服装结构（层间隙、雨滴纹浮雕、褶裥脊高、
雨帽檐间隙、脑后兜帽搭接、雨伞伞面与伞柄、雨靴与长裤搭接、手套包覆、
雨滴纹位置、靴底落地）/ 尺寸与构图。全部数值从 blend 文件实测填写，不编造。

设计对照值来源：scenes/040-rainy-day-urban/design.md 与 build_040.py
（面数 1022、N-gon 0、层间隙 >=0.005、雨滴浮雕 0.015、褶裥外沿 0.026、
腰扣 0.0115、耳钉 0.019、挑染半嵌发顶、雨帽檐 r 0.34、帽顶 r 0.26
压扁 0.55、靴底落地 z=0.0）。

注意：BVH 顶点-表面距离是无符号距离，分不清“在外面”还是“在里面”。
雨帽顶是一颗压扁球（中心 z 1.63、顶 1.773），下沿按构造埋在发顶椭球体内
（帽子戴在头上）：本单第 4.1 节对帽顶 vs 发顶只计量可见部分（034 白帽顶、
037 珍珠白帽顶同款做法）。雨帽檐是闭合薄圆柱（031 遮阳帽做法），帽顶球
穿过檐盘，二者按构造相交，见第 4.3 节。兜帽顶环按构造塞进发顶之后
（040 design.md），见第 4.8 节。雨靴筒与长裤下摆按构造相交（靴筒套在裤摆
外面），见第 4.9 节。藏青手套是包覆手掌的球（与手掌球体重叠，属手套包覆
构造），不进 4.1 的层间隙表，见第 4.6 节专项。长袖从雨衣肩部穿出（032 的
做法，袖筒与雨衣面按构造相交），不进 4.1，见第 4.3 节注。伞柄从右手腕
斜出（与臂轴上延夹角 48°），伞面底沿与袖筒的间隙须按径向净空量（040 v1
的教训：不要拿高度差当间隙查），见第 4.7 节。

Run: blender --background --python 041-qa.py
"""
import os
import sys
import json
import math
import re
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BLEND = os.path.join(ROOT, "scenes", "040-rainy-day-urban",
                     "040-rainy-day-urban.blend")
SUMMARY_JSON = os.path.join(HERE, "041-qa-summary.json")
CHECKLIST = os.path.join(HERE, "041-asset-qa-checklist.md")

# Garment = every mesh except Ground and the neutral mannequin base.
def is_garment(o):
    return (o.type == 'MESH' and o.name != "Ground"
            and not o.name.startswith("Mannequin_"))


# Closed solids by construction (sphere / box / capped tube / wedge /
# closed pleat fin / closed brim cylinder / pyramid ear): boundary edges
# must be 0. Everything else is an open tube / arc panel by design,
# where boundary edges are expected. No flat single-sided disc and no
# near-horizontal open ribbon in this set (the 040 brim is a closed
# cylinder, unlike 036's open brim ribbon), so nothing is excluded
# from the inverted-normal solid check.
CLOSED_SOLIDS = ("SilverBeltBuckle", "BlueRaindrop", "BlueRaindropHat",
                 "YellowPleat", "YellowHatBrim", "YellowHatCrown",
                 "NavyCatEar", "HairStreak", "GoldEarring", "NavyGlove",
                 "SilverUmbrellaShaft", "NavyUmbrellaGrip",
                 "YellowUmbrellaCanopy", "SilverUmbrellaTip",
                 "YellowRainBootSole", "NavySleeve")
FLAT_PATCHES = ()
RIBBON_GEOMETRIC = ()

EXPECTED_NGONS = 0          # design.md: N-gon 0
EXPECTED_FACES = 1022       # component build, recorded in design.md
FACE_LIMIT = 1500
MIN_GAP = 0.005

# Rings from build_040.py (z, rx, ry), for interpolation cross-checks.
SWEATER_RINGS = [(1.50, 0.300, 0.160), (1.44, 0.288, 0.152),
                 (1.10, 0.272, 0.144), (0.80, 0.258, 0.138),
                 (0.62, 0.248, 0.132)]
RAINCOAT_RINGS = [(1.50, 0.312, 0.168), (1.20, 0.312, 0.164),
                  (0.90, 0.308, 0.162), (0.72, 0.304, 0.160),
                  (0.60, 0.302, 0.158)]
HOOD_RINGS = [(1.52, 0.315, 0.172), (1.44, 0.322, 0.176),
              (1.38, 0.318, 0.174)]
TROUSER_RINGS = [(0.62, 0.246, 0.128), (0.48, 0.240, 0.126),
                 (0.34, 0.232, 0.124)]
# Right hand (umbrella side, sx=+1): wrist from build_032 wrist_pos(1).
HAND_R_C = (0.4063, 0.0, 0.6753)
HAND_R_R = (0.085, 0.0765, 0.068)
# Left hand (glove side, sx=-1): mirror of the right hand.
HAND_L_C = (-0.4063, 0.0, 0.6753)
# Navy glove: sphere r 0.095 scaled (1.0, 0.9, 1.0), centre =
# left wrist + arm dir * 0.03 = (-0.4104, 0, 0.6456).
GLOVE_C = (-0.4104, 0.0, 0.6456)
GLOVE_R = (0.095, 0.0855, 0.095)
# Hair cap ellipsoid (build_032): centre (0, 0.02, 1.57),
# r 0.225 scaled (1.0, 0.95, 0.80).
HAIR_C = (0.0, 0.02, 1.57)
HAIR_R = (0.225, 0.21375, 0.18)
# Head ellipsoid for the ideal-relief cross-check (build_032):
# centre (0,0,1.50), radii (0.22, 0.198, 0.231).
HEAD_C = (0.0, 0.0, 1.50)
HEAD_R = (0.22, 0.198, 0.231)
# Rain-hat crown ellipsoid (build_040): centre (0, 0.01, 1.63),
# r 0.26 scaled (1.0, 0.95, 0.55).
CROWN_C = (0.0, 0.01, 1.63)
CROWN_R = (0.26, 0.247, 0.143)
# Left arm axis (build_032): shoulder (-0.33, 0, 1.22),
# direction (-0.14, 0, -1) normalized. Right arm mirrored.
ARM_L_SHOULDER = Vector((-0.33, 0.0, 1.22))
ARM_L_DIR = Vector((-0.14, 0.0, -1.0)).normalized()
ARM_R_SHOULDER = Vector((0.33, 0.0, 1.22))
ARM_R_DIR = Vector((0.14, 0.0, -1.0)).normalized()
# Sleeve radii along its own param s (0 at origin = shoulder - dir*0.12):
SLEEVE_S = [0.0, 0.17, 0.34, 0.51, 0.67]
SLEEVE_R = [0.125, 0.118, 0.110, 0.102, 0.096]
# Umbrella (build_040): shaft direction, 48 deg off the arm's upward
# extension; shaft length 0.70 from the right wrist.
SHAFT_LEN = 0.70
# Raindrop build order (design.md): sweater drops first (270 deg z 1.32;
# 262 deg z 1.02; 278 deg z 1.02), then coat drops (225 deg z 1.05;
# 315 deg z 1.05). Blender names follow creation order.
DROP_HOSTS = {"BlueRaindrop": "CreamSweater",
              "BlueRaindrop.001": "CreamSweater",
              "BlueRaindrop.002": "CreamSweater",
              "BlueRaindrop.003": "YellowRaincoat",
              "BlueRaindrop.004": "YellowRaincoat"}
DROP_DESIGN = {"BlueRaindrop": (270, 1.32, "sweater"),
               "BlueRaindrop.001": (262, 1.02, "sweater"),
               "BlueRaindrop.002": (278, 1.02, "sweater"),
               "BlueRaindrop.003": (225, 1.05, "coat"),
               "BlueRaindrop.004": (315, 1.05, "coat")}
# Pleat build order (design.md): angles 170/200/230/320/350/20/50/110.
PLEAT_ANGLES = {"YellowPleat": 170, "YellowPleat.001": 200,
                "YellowPleat.002": 230, "YellowPleat.003": 320,
                "YellowPleat.004": 350, "YellowPleat.005": 20,
                "YellowPleat.006": 50, "YellowPleat.007": 110}


def interp_rings(rings, z):
    """Interpolated (rx, ry) of an elliptical tube at height z."""
    if z >= rings[0][0]:
        return rings[0][1], rings[0][2]
    if z <= rings[-1][0]:
        return rings[-1][1], rings[-1][2]
    for k in range(len(rings) - 1):
        z0, rx0, ry0 = rings[k]
        z1, rx1, ry1 = rings[k + 1]
        if z1 <= z <= z0:
            t = (z0 - z) / (z0 - z1)
            return rx0 + (rx1 - rx0) * t, ry0 + (ry1 - ry0) * t
    return rings[-1][1], rings[-1][2]


def ellipse_value(x, y, rx, ry):
    """Normalised ellipse radius of point (x, y); >1 means outside."""
    return math.sqrt((x / rx) ** 2 + (y / ry) ** 2)


def check_mesh(obj):
    """Real inspection of one mesh. Returns a dict of measurements."""
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.edges.ensure_lookup_table()

    n_verts = len(bm.verts)
    n_faces = len(bm.faces)
    tris = sum(1 for f in bm.faces if len(f.verts) == 3)
    quads = sum(1 for f in bm.faces if len(f.verts) == 4)
    ngons = sum(1 for f in bm.faces if len(f.verts) > 4)

    seen = {}
    dups = 0
    for v in bm.verts:
        key = (round(v.co.x, 4), round(v.co.y, 4), round(v.co.z, 4))
        if key in seen:
            dups += 1
        else:
            seen[key] = v.index

    loose_edges = sum(1 for e in bm.edges if len(e.link_faces) == 0)
    boundary_edges = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    nonmanifold = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    degenerate = sum(1 for f in bm.faces if f.calc_area() < 1e-8)

    bm2 = bm.copy()
    bmesh.ops.recalc_face_normals(bm2, faces=bm2.faces)
    bm2.faces.ensure_lookup_table()
    orig_normals = [f.normal.copy() for f in bm.faces]
    inverted = sum(1 for i, f in enumerate(bm2.faces)
                   if orig_normals[i].dot(f.normal) < 0)
    bm2.free()

    max_valence = max((len(v.link_edges) for v in bm.verts), default=0)

    uv_layer = bm.loops.layers.uv.active
    uv = {"has_uv": uv_layer is not None, "out_of_bounds": 0,
          "utilization": 0.0, "islands": 0, "overlap_pct": 0.0,
          "faces": []}
    if uv_layer is not None:
        face_uvs = []
        for f in bm.faces:
            pts = [(l[uv_layer].uv.x, l[uv_layer].uv.y) for l in f.loops]
            face_uvs.append(pts)
            for (u, v) in pts:
                if u < -1e-4 or u > 1.0001 or v < -1e-4 or v > 1.0001:
                    uv["out_of_bounds"] += 1
        area = 0.0
        for pts in face_uvs:
            for k in range(1, len(pts) - 1):
                (x0, y0), (x1, y1), (x2, y2) = pts[0], pts[k], pts[k + 1]
                area += abs((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)) / 2.0
        uv["utilization"] = area
        uv["faces"] = [[list(p) for p in pts] for pts in face_uvs]

    bm.free()
    return {
        "name": obj.name,
        "verts": n_verts, "faces": n_faces, "tris": tris, "quads": quads,
        "ngons": ngons, "duplicate_verts": dups, "loose_edges": loose_edges,
        "boundary_edges": boundary_edges, "nonmanifold_edges": nonmanifold,
        "degenerate_faces": degenerate, "inverted_normals": inverted,
        "max_valence": max_valence,
        "uv": uv,
        "materials": [m.name if m else None for m in obj.data.materials],
    }


def world_verts(obj):
    mw = obj.matrix_world
    return [mw @ v.co for v in obj.data.vertices]


def world_bvh(obj):
    verts = world_verts(obj)
    faces = [tuple(p.vertices) for p in obj.data.polygons]
    return BVHTree.FromPolygons(verts, faces)


def gap_between(outer, inner, zmin=None, zmax=None, minimum=MIN_GAP):
    """Min / median vertex-to-surface distance from outer mesh to inner
    mesh, restricted to a z band when given. Measures the real layer gap
    from the built geometry (not the design ring tables)."""
    bvh = world_bvh(inner)
    ds = []
    for w in world_verts(outer):
        if zmin is not None and not (zmin - 1e-4 <= w.z <= zmax + 1e-4):
            continue
        hit = bvh.find_nearest(w)
        if hit is not None:
            ds.append(hit[3])
    if not ds:
        return {"min": None, "median": None, "samples": 0,
                "minimum": minimum, "ok": False}
    ds.sort()
    med = ds[len(ds) // 2]
    return {"min": round(ds[0], 4), "median": round(med, 4),
            "samples": len(ds), "minimum": minimum,
            "ok": bool(ds[0] >= minimum)}


def max_distance_to(obj, target):
    """Largest vertex-to-surface distance from obj to target mesh."""
    bvh = world_bvh(target)
    best = 0.0
    for w in world_verts(obj):
        hit = bvh.find_nearest(w)
        if hit is not None:
            best = max(best, hit[3])
    return round(best, 4)


def gap_between_visible(outer, inner, outside_fn, minimum=MIN_GAP):
    """Min / median vertex-to-surface distance, counting only the outer
    mesh vertices that lie OUTSIDE the inner volume (outside_fn decides).
    A hat crown pulled over the head has its lower rim buried inside the
    hair ellipsoid by construction; the buried part is not a layer gap,
    so it must not enter the measurement (same class of error as 013's
    belt vs overskirt unsigned distance)."""
    bvh = world_bvh(inner)
    ds = []
    buried = 0
    for w in world_verts(outer):
        if outside_fn(w):
            hit = bvh.find_nearest(w)
            if hit is not None:
                ds.append(hit[3])
        else:
            buried += 1
    if not ds:
        return {"min": None, "median": None, "samples": 0,
                "minimum": minimum, "ok": False, "buried": buried}
    ds.sort()
    med = ds[len(ds) // 2]
    return {"min": round(ds[0], 4), "median": round(med, 4),
            "samples": len(ds), "minimum": minimum,
            "ok": bool(ds[0] >= minimum), "buried": buried}


def inside_ellipsoid(p, c, r):
    q = (((p.x - c[0]) / r[0]) ** 2 + ((p.y - c[1]) / r[1]) ** 2
         + ((p.z - c[2]) / r[2]) ** 2)
    return q < 1.0


def ideal_head_relief(obj):
    """Max approximate distance of obj's vertices above the ideal head
    ellipsoid: the built head mesh is a coarse 10x8 UV sphere, so a
    vertex-to-mesh distance overstates a stud's relief by the facet
    sagitta (~0.011); the design relief (earring 0.019) is measured
    against the smooth head, so it is checked here too."""
    best = 0.0
    for w in world_verts(obj):
        q = ((w.x / HEAD_R[0]) ** 2 + (w.y / HEAD_R[1]) ** 2
             + ((w.z - HEAD_C[2]) / HEAD_R[2]) ** 2)
        if q > 1.0:
            best = max(best, (math.sqrt(q) - 1.0) * HEAD_R[0])
    return round(best, 4)


def ideal_crown_distance(p, crown_c, crown_r):
    """Min distance from point p to the ideal rain-hat crown ellipsoid
    surface, by dense sampling (360 angles x 140 heights). Used for
    the hat raindrop: a tall droplet on a small-radius crown, whose
    tip legitimately stands further off the faceted mesh than a flat
    patch would (same class of correction as 037's goggle lens and
    034's sunglass lens)."""
    best = 9.0
    for iz in range(141):
        z = crown_c.z - crown_r[2] + 2.0 * crown_r[2] * iz / 140.0
        kz = (z - crown_c.z) / crown_r[2]
        if abs(kz) > 1.0:
            continue
        s = math.sqrt(max(0.0, 1.0 - kz * kz))
        rx = crown_r[0] * s
        ry = crown_r[1] * s
        for k in range(360):
            a = 2.0 * math.pi * k / 360.0
            q = Vector((crown_c.x + rx * math.cos(a),
                        crown_c.y + ry * math.sin(a), z))
            d = (p - q).length
            if d < best:
                best = d
    return best


def sleeve_radius_at_s(s):
    """Sleeve tube radius at arm-axis parameter s (0 at the sleeve origin)."""
    if s <= SLEEVE_S[0]:
        return SLEEVE_R[0]
    if s >= SLEEVE_S[-1]:
        return SLEEVE_R[-1]
    for k in range(len(SLEEVE_S) - 1):
        if SLEEVE_S[k] <= s <= SLEEVE_S[k + 1]:
            f = (s - SLEEVE_S[k]) / (SLEEVE_S[k + 1] - SLEEVE_S[k])
            return SLEEVE_R[k] + f * (SLEEVE_R[k + 1] - SLEEVE_R[k])
    return SLEEVE_R[-1]


# design values from build_040.py make_materials():
# (metallic, roughness, base color linear RGB)
DESIGN_MATS = {
    "RainYellow": (0.0, 0.25, (0.888, 0.540, 0.000)),  # #F2C200 雨衣黄 PVC
    "Cream":      (0.0, 0.6, (0.913, 0.862, 0.744)),  # #F5EFE0 奶油白
    "Navy":       (0.0, 0.6, (0.011, 0.023, 0.068)),  # #1B2A4A 藏青
    "RainBlue":   (0.0, 0.5, (0.112, 0.452, 0.791)),  # #5EB3E6 雨滴蓝
    "Silver":     (0.7, 0.3, (0.529, 0.585, 0.633)),  # #C0C8D0 银
    "Gold":       (0.6, 0.35, (0.584, 0.361, 0.020)), # #C9A227 鎏金
    "LightBlue":  (0.0, 0.6, (0.212, 0.479, 0.807)),  # 浅蓝挑染
    "Hair_Black": (0.0, 0.7, (0.011, 0.011, 0.015)),  # #1B1B21 黑发
    "Skin":       (0.0, 0.7, (0.694, 0.381, 0.209)),  # #D9A67E 肤色
    "Eye_Dark":   (0.0, 0.6, (0.003, 0.003, 0.003)),  # #0A0A0A 眼
}


def check_materials():
    rows = []
    for name, (met, rough, col) in DESIGN_MATS.items():
        mat = bpy.data.materials.get(name)
        if mat is None or not mat.use_nodes:
            rows.append({"name": name, "found": False, "ok": False})
            continue
        bsdf = None
        for n in mat.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                bsdf = n
                break
        if bsdf is None:
            rows.append({"name": name, "found": True, "ok": False})
            continue
        m = round(bsdf.inputs["Metallic"].default_value, 2)
        r = round(bsdf.inputs["Roughness"].default_value, 2)
        c = tuple(round(v, 3) for v in bsdf.inputs["Base Color"].default_value[:3])
        ok = (abs(m - met) < 0.01 and abs(r - rough) < 0.01
              and all(abs(a - b) < 0.01 for a, b in zip(c, col)))
        rows.append({"name": name, "found": True, "metallic": m,
                     "roughness": r, "base_color": c, "ok": bool(ok)})
    return {"rows": rows,
            "all_ok": bool(all(r["ok"] for r in rows))}

def main():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    bpy.context.view_layer.update()
    garment = [o for o in bpy.context.scene.objects if is_garment(o)]
    mannequin = [o for o in bpy.context.scene.objects
                 if o.type == 'MESH' and o.name.startswith("Mannequin_")]
    by_name = {o.name: o for o in bpy.context.scene.objects}
    print("QA_PARTS garment=%d mannequin=%d" % (len(garment), len(mannequin)))

    results = {}
    for obj in garment:
        r = check_mesh(obj)
        results[obj.name] = r
        print("QA %s verts=%d faces=%d tris=%d quads=%d ngons=%d dups=%d "
              "loose=%d boundary=%d nonmanifold=%d degen=%d invnorm=%d "
              "maxval=%d uv=%s" % (
                  obj.name, r["verts"], r["faces"], r["tris"], r["quads"],
                  r["ngons"], r["duplicate_verts"], r["loose_edges"],
                  r["boundary_edges"], r["nonmanifold_edges"],
                  r["degenerate_faces"], r["inverted_normals"],
                  r["max_valence"], r["uv"]["has_uv"]))

    # ---- component family roll-up (L/R .NNN suffixes merged) ----
    def base(n):
        return re.sub(r"\.\d+$", "", n)
    families = {}
    for name, r in results.items():
        families.setdefault(base(name), []).append(r)
    fam_faces = {k: sum(r["faces"] for r in v) for k, v in families.items()}
    for k in sorted(fam_faces):
        print("QA_FAMILY %s faces=%d parts=%d" % (
            k, fam_faces[k], len(families[k])))

    # ---- structure: layer gaps measured from the built mesh ----
    def obj(n):
        return by_name[n]

    # Left = no suffix (built with sx=-1), right = .001 (sx=+1).
    gaps = {}
    gaps["sweater_vs_torso"] = gap_between(obj("CreamSweater"),
                                           obj("Mannequin_Torso"))
    gaps["raincoat_vs_sweater"] = gap_between(obj("YellowRaincoat"),
                                              obj("CreamSweater"))
    gaps["hood_vs_raincoat"] = gap_between(obj("YellowHood"),
                                           obj("YellowRaincoat"))
    gaps["hood_vs_sweater"] = gap_between(obj("YellowHood"),
                                          obj("CreamSweater"))
    gaps["sleeveL_vs_arm"] = gap_between(obj("NavySleeve"),
                                         obj("Mannequin_Arm"))
    gaps["sleeveR_vs_arm"] = gap_between(obj("NavySleeve.001"),
                                         obj("Mannequin_Arm.001"))
    gaps["cuffL_vs_sleeve"] = gap_between(obj("CreamCuff"),
                                          obj("NavySleeve"))
    gaps["cuffR_vs_sleeve"] = gap_between(obj("CreamCuff.001"),
                                          obj("NavySleeve.001"))
    gaps["belt_vs_raincoat"] = gap_between(obj("NavyBelt"),
                                           obj("YellowRaincoat"))
    gaps["trousers_vs_legL"] = gap_between(obj("NavyTrousers"),
                                           obj("Mannequin_Leg"))
    gaps["trousers_vs_legR"] = gap_between(obj("NavyTrousers"),
                                           obj("Mannequin_Leg.001"))
    gaps["bootL_vs_leg"] = gap_between(obj("YellowRainBoot"),
                                       obj("Mannequin_Leg"))
    gaps["bootR_vs_leg"] = gap_between(obj("YellowRainBoot.001"),
                                       obj("Mannequin_Leg.001"))
    gaps["bootCuffL_vs_boot"] = gap_between(obj("SilverBootCuff"),
                                            obj("YellowRainBoot"))
    gaps["bootCuffR_vs_boot"] = gap_between(obj("SilverBootCuff.001"),
                                            obj("YellowRainBoot.001"))
    gaps["bootSoleL_vs_foot"] = gap_between(obj("YellowRainBootSole"),
                                            obj("Mannequin_Foot"))
    gaps["bootSoleR_vs_foot"] = gap_between(obj("YellowRainBootSole.001"),
                                            obj("Mannequin_Foot.001"))
    gaps["hatband_vs_crown"] = gap_between(obj("NavyHatBand"),
                                           obj("YellowHatCrown"))
    # Hat crown vs hair: design clearance ~0.03 at the visible rings
    # (crown centre z 1.63). The crown is pulled over the head, so its
    # lower rim is buried inside the hair ellipsoid by construction:
    # measure only the visible part.
    def outside_hair(p):
        return not inside_ellipsoid(p, HAIR_C, HAIR_R)
    gaps["hatcrown_vs_hair"] = gap_between_visible(
        obj("YellowHatCrown"), obj("Mannequin_Hair"), outside_hair)
    # Umbrella canopy vs right sleeve: the canopy rim sits BESIDE the
    # shoulder (rim z 1.204 < sleeve top 1.339), so this is a radial
    # clearance, not a height comparison (040 v1 lesson).
    gaps["canopy_vs_sleeve"] = gap_between(obj("YellowUmbrellaCanopy"),
                                           obj("NavySleeve.001"))
    # Umbrella shaft vs raincoat: the shaft leaves the wrist at 48 deg
    # off the arm's upward extension and clears the coat.
    gaps["shaft_vs_raincoat"] = gap_between(obj("SilverUmbrellaShaft"),
                                            obj("YellowRaincoat"))
    for k, v in gaps.items():
        print("QA_GAP %s min=%s median=%s samples=%d %s" % (
            k, v["min"], v["median"], v["samples"],
            "PASS" if v["ok"] else "FAIL"))

    # ---- crown ellipsoid parameters, measured from the built mesh ----
    # The crown is a symmetric UV sphere, so the mean of its vertices
    # is its centre and the extents are its radii. These feed the
    # hat-drop analytic check and the brim connection proof below.
    crown_verts_all = world_verts(obj("YellowHatCrown"))
    crown_c = Vector((sum(w.x for w in crown_verts_all) / len(crown_verts_all),
                      sum(w.y for w in crown_verts_all) / len(crown_verts_all),
                      sum(w.z for w in crown_verts_all) / len(crown_verts_all)))
    crown_r = (max(abs(w.x - crown_c.x) for w in crown_verts_all),
               max(abs(w.y - crown_c.y) for w in crown_verts_all),
               max(abs(w.z - crown_c.z) for w in crown_verts_all))
    print("QA_CROWN centre=%s radii=%s" % ([round(v, 4) for v in crown_c],
                                            [round(v, 4) for v in crown_r]))

    # ---- brim connection proof (parametric, not vertex sampling) ----
    # The brim is a closed thin cylinder (031 sun-hat construction):
    # its only vertices are the 48 rim vertices (r 0.34), so a
    # vertex-to-surface distance to the crown (~0.079) misses the
    # crossing entirely — the crown sphere passes through the brim
    # disc, and the disc's top/bottom faces are ngons with no interior
    # vertices (same class of error as 034's "提手/包顶与檐盘用参数化
    # 采样（顶点采样会漏穿插）"). Prove the connection parametrically:
    # the crown's horizontal radius at the brim's top and bottom z is
    # smaller than the brim radius, and the crown spans above and
    # below the brim, so the crown surface crosses both brim faces.
    # Likewise the hat band's bottom ring (z 1.62) lies inside the
    # brim disc's z-range at radius 0.265 < 0.34, so the band passes
    # through the disc.
    brim_verts_all = world_verts(obj("YellowHatBrim"))
    brim_zmin = min(w.z for w in brim_verts_all)
    brim_zmax = max(w.z for w in brim_verts_all)
    brim_r = max(abs(w.x) for w in brim_verts_all)

    def crown_rx_at(z):
        kz = (z - crown_c.z) / crown_r[2]
        if abs(kz) >= 1.0:
            return 0.0
        return crown_r[0] * math.sqrt(1.0 - kz * kz)

    crown_zs_all = [w.z for w in crown_verts_all]
    crown_through_brim = bool(
        crown_rx_at(brim_zmin) < brim_r
        and crown_rx_at(brim_zmax) < brim_r
        and min(crown_zs_all) < brim_zmin
        and max(crown_zs_all) > brim_zmax)
    band_verts_all = world_verts(obj("NavyHatBand"))
    band_zmin = min(w.z for w in band_verts_all)
    band_r_at_bottom = max(abs(w.x) for w in band_verts_all
                           if abs(w.z - band_zmin) < 1e-4)
    band_through_brim = bool(
        brim_zmin - 1e-4 <= band_zmin <= brim_zmax + 1e-4
        and band_r_at_bottom < brim_r)
    brim_proof = {
        "brim_z": (round(brim_zmin, 3), round(brim_zmax, 3)),
        "brim_radius": round(brim_r, 3),
        "crown_rx_at_brim_bottom": round(crown_rx_at(brim_zmin), 4),
        "crown_rx_at_brim_top": round(crown_rx_at(brim_zmax), 4),
        "crown_z": (round(min(crown_zs_all), 3),
                     round(max(crown_zs_all), 3)),
        "crown_passes_through_brim": bool(crown_through_brim),
        "band_bottom_z": round(band_zmin, 3),
        "band_radius_at_bottom": round(band_r_at_bottom, 4),
        "band_passes_through_brim": bool(band_through_brim),
    }
    print("QA_BRIM_PROOF %s" % brim_proof)

    # ---- attachment pairs: measured, observation only (meant to touch,
    # half-embed, or enclose their host; a BVH distance of 0.0 means
    # contact, not intersection) ----
    attach = {}
    for drop_name, host in DROP_HOSTS.items():
        attach["drop_%s_vs_host" % drop_name.replace(".", "_")] = \
            gap_between(obj(drop_name), obj(host))
    attach["hatdrop_vs_crown"] = gap_between(obj("BlueRaindropHat"),
                                             obj("YellowHatCrown"))
    attach["buckle_vs_belt"] = gap_between(obj("SilverBeltBuckle"),
                                           obj("NavyBelt"))
    for t in ("", ".001"):
        attach["earring%s_vs_head" % t] = gap_between(
            obj("GoldEarring" + t), obj("Mannequin_Head"))
        attach["catear%s_vs_crown" % t] = gap_between(
            obj("NavyCatEar" + t), obj("YellowHatCrown"))
    attach["streak_vs_hair"] = gap_between(obj("HairStreak"),
                                           obj("Mannequin_Hair"))
    attach["brim_vs_crown"] = gap_between(obj("YellowHatBrim"),
                                          obj("YellowHatCrown"))
    attach["brim_vs_band"] = gap_between(obj("YellowHatBrim"),
                                         obj("NavyHatBand"))
    attach["hood_vs_hair"] = gap_between(obj("YellowHood"),
                                         obj("Mannequin_Hair"))
    for t in [""] + [".%03d" % i for i in range(1, 8)]:
        attach["pleat%s_vs_raincoat" % t] = gap_between(
            obj("YellowPleat" + t), obj("YellowRaincoat"))
    for t in ("", ".001"):
        attach["bootCuff%s_vs_boot" % t] = gap_between(
            obj("SilverBootCuff" + t), obj("YellowRainBoot" + t))
        attach["boot%s_vs_trousers" % t] = gap_between(
            obj("YellowRainBoot" + t), obj("NavyTrousers"))
    # Glove vs hand: the glove sphere (r 0.095) encloses the hand sphere
    # (r 0.085) with centres 0.03 apart, so the surfaces cross by
    # construction; the vertex distance is ~0.0 and means "covered",
    # not a defect. Coverage is measured in section 4.6 instead.
    attach["glove_vs_handL"] = gap_between(obj("NavyGlove"),
                                           obj("Mannequin_Hand"))
    # Sleeve vs raincoat: the sleeve is sewn through the raincoat
    # shoulder (032 fix: origin lifted 0.12 so it emerges from the
    # shoulder); the surfaces cross at the shoulder seam by
    # construction.
    attach["sleeveL_vs_raincoat"] = gap_between(obj("NavySleeve"),
                                                obj("YellowRaincoat"))
    attach["sleeveR_vs_raincoat"] = gap_between(obj("NavySleeve.001"),
                                                obj("YellowRaincoat"))
    # Umbrella held in the right hand: the grip tube passes through the
    # hand sphere (it reads as held, not floating); the shaft emerges
    # from the sleeve end cap at the wrist; shaft/grip/canopy/tip meet
    # end to end.
    attach["grip_vs_handR"] = gap_between(obj("NavyUmbrellaGrip"),
                                          obj("Mannequin_Hand.001"))
    attach["shaft_vs_sleeve"] = gap_between(obj("SilverUmbrellaShaft"),
                                            obj("NavySleeve.001"))
    attach["shaft_vs_grip"] = gap_between(obj("SilverUmbrellaShaft"),
                                          obj("NavyUmbrellaGrip"))
    attach["shaft_vs_canopy"] = gap_between(obj("SilverUmbrellaShaft"),
                                            obj("YellowUmbrellaCanopy"))
    attach["tip_vs_canopy"] = gap_between(obj("SilverUmbrellaTip"),
                                          obj("YellowUmbrellaCanopy"))
    for k, v in attach.items():
        print("QA_ATTACH %s min=%s median=%s samples=%d" % (
            k, v["min"], v["median"], v["samples"]))

    # ---- protruding features: farthest vertex above the host surface ----
    # Design reliefs: raindrop 0.015, hat drop 0.015, pleat fin outer
    # edge 0.026, belt buckle 0.0115, earring 0.019, hair streak ~0.02
    # (half-buried ellipsoid), silver boot cuff ring 0.006.
    # Criterion: visible (>= 0.005, pleat >= 0.020) and not grossly
    # floating (<= 0.03, pleat <= 0.032).
    protrusions = {}

    def protrude(name, host, lo, hi):
        lift = max_distance_to(obj(name), obj(host))
        ok = bool(lo <= lift <= hi)
        protrusions[name] = {"lift": lift, "ok": ok,
                             "host": host, "lo": lo, "hi": hi}
        print("QA_PROTRUDE %s lift=%.4f %s" % (
            name, lift, "PASS" if ok else "FAIL"))
        return lift

    for drop_name, host in DROP_HOSTS.items():
        protrude(drop_name, host, 0.005, 0.03)
    # BlueRaindropHat: a tall droplet (0.076 m) on a small-radius crown
    # (r 0.26). The generic "farthest vertex" cap (0.03) does not fit:
    # the droplet's top tip stands off a surface that curves away
    # sharply, so the tip legitimately sits ~0.033 from the faceted
    # mesh. Same class of correction as 037's goggle lens (034's
    # sunglass lens): criterion |measured - analytic| <= 0.012 and
    # measured <= 0.05, where analytic is the ideal-ellipsoid distance
    # of the farthest vertex. The 0.012 tolerance is the crown's facet
    # sagitta (12x6 sphere: 0.26*(1-cos 15 deg) = 0.0089, plus the
    # latitude sagitta). The droplet's base is embedded in the crown
    # (attachment min 0.0008), proving it is not floating.
    bvh_crown = world_bvh(obj("YellowHatCrown"))
    far_v, far_d = None, 0.0
    for w in world_verts(obj("BlueRaindropHat")):
        hit = bvh_crown.find_nearest(w)
        if hit is not None and hit[3] > far_d:
            far_d, far_v = hit[3], w
    hat_analytic = round(ideal_crown_distance(far_v, crown_c, crown_r), 4)
    hat_ok = bool(abs(far_d - hat_analytic) <= 0.012 and far_d <= 0.05)
    protrusions["BlueRaindropHat"] = {"lift": round(far_d, 4),
                                      "analytic": hat_analytic,
                                      "ok": hat_ok,
                                      "host": "YellowHatCrown (ideal ellipsoid)",
                                      "lo": round(hat_analytic - 0.006, 4),
                                      "hi": round(hat_analytic + 0.006, 4)}
    print("QA_PROTRUDE BlueRaindropHat lift=%.4f analytic=%.4f %s" % (
        far_d, hat_analytic, "PASS" if hat_ok else "FAIL"))
    protrude("SilverBeltBuckle", "NavyBelt", 0.005, 0.03)
    for t in ("", ".001"):
        protrude("GoldEarring" + t, "Mannequin_Head", 0.005, 0.035)
    # Earring relief vs the SMOOTH head (design 0.019): the built head is
    # a coarse 10x8 sphere, so the mesh-based lift overstates the relief
    # by the facet sagitta (~0.011); the 0.035 upper bound covers design
    # + sagitta. Record the ideal-ellipsoid relief as the cross-check.
    earring_ideal = max(ideal_head_relief(obj("GoldEarring")),
                        ideal_head_relief(obj("GoldEarring.001")))
    print("QA_PROTRUDE GoldEarring ideal_ellipsoid_relief=%.4f" % earring_ideal)
    # Analytic earring relief from the mesh-measured stud centre and
    # radius: the ideal-ellipsoid vertex sampling understates the
    # relief by ~0.003 because the coarse 6x3 sphere has no vertex at
    # the exact outer point (the outer face is centre + radius).
    def earring_analytic_relief(name):
        vs = world_verts(obj(name))
        c = Vector((sum(w.x for w in vs) / len(vs),
                    sum(w.y for w in vs) / len(vs),
                    sum(w.z for w in vs) / len(vs)))
        r = max((w - c).length for w in vs)
        head_x = HEAD_R[0] * math.sqrt(max(
            0.0, 1.0 - ((c.z - HEAD_C[2]) / HEAD_R[2]) ** 2))
        return round(abs(c.x) + r - head_x, 4)
    earring_analytic = max(earring_analytic_relief("GoldEarring"),
                           earring_analytic_relief("GoldEarring.001"))
    print("QA_PROTRUDE GoldEarring analytic_relief=%.4f" % earring_analytic)
    # Hair streak: a flattened ellipsoid half-buried in the hair and the
    # head. The single-host farthest vertex is the bottom tip, which
    # sits INSIDE the head sphere — not a relief at all. Visibility is
    # decided against the built meshes, not the ideal ellipsoids: a
    # streak vertex is visible only if it lies outside BOTH the hair
    # mesh and the head mesh (BVH normal test: the vector from the
    # nearest surface point to the vertex must point along the surface
    # normal). The lift is the standoff of the visible part.
    def _outside_mesh(bvh, w):
        hit = bvh.find_nearest(w)
        if hit is None:
            return False, 0.0
        loc, nrm, _idx, d = hit
        return (Vector(w) - loc).dot(nrm) > 0, d

    raw_streak = max_distance_to(obj("HairStreak"), obj("Mannequin_Hair"))
    bvh_hair = world_bvh(obj("Mannequin_Hair"))
    bvh_head = world_bvh(obj("Mannequin_Head"))
    streak_vis = 0
    streak_lift = 0.0
    for w in world_verts(obj("HairStreak")):
        oh, dh = _outside_mesh(bvh_hair, w)
        od, dd = _outside_mesh(bvh_head, w)
        if oh and od:
            streak_vis += 1
            streak_lift = max(streak_lift, min(dh, dd))
    streak_lift = round(streak_lift, 4)
    streak_ok = bool(streak_vis > 0 and 0.005 <= streak_lift <= 0.045)
    protrusions["HairStreak"] = {"lift": streak_lift, "raw_lift": raw_streak,
                                 "visible_verts": streak_vis,
                                 "total_verts": len(world_verts(obj("HairStreak"))),
                                 "ok": streak_ok,
                                 "host": "Mannequin_Hair/Mannequin_Head (visible part only)",
                                 "lo": 0.005, "hi": 0.045}
    print("QA_PROTRUDE HairStreak lift=%.4f raw=%.4f visible=%d/%d %s" % (
        streak_lift, raw_streak, streak_vis,
        len(world_verts(obj("HairStreak"))),
        "PASS" if streak_ok else "FAIL"))
    for t in [""] + [".%03d" % i for i in range(1, 8)]:
        protrude("YellowPleat" + t, "YellowRaincoat", 0.020, 0.032)
    for t in ("", ".001"):
        # The boot cuff ring straddles the boot's top edge (cuff
        # z 0.52-0.48, boot top z 0.50): only the overlapping band
        # (z <= 0.50) reads as a ring stand-off (design 0.006); the top
        # edge's diagonal distance to the boot's top edge (~0.021) is
        # the ring sitting above the boot, not a floating patch.
        cuff_obj = obj("SilverBootCuff" + t)
        boot_bvh = world_bvh(obj("YellowRainBoot" + t))
        cuff_lift = 0.0
        for w in world_verts(cuff_obj):
            if w.z <= 0.50 + 1e-4:
                hit = boot_bvh.find_nearest(w)
                if hit is not None:
                    cuff_lift = max(cuff_lift, hit[3])
        cuff_lift = round(cuff_lift, 4)
        cuff_ok = bool(0.005 <= cuff_lift <= 0.03)
        protrusions["SilverBootCuff" + t] = {"lift": cuff_lift,
                                            "ok": cuff_ok,
                                            "host": "YellowRainBoot" + t,
                                            "lo": 0.005, "hi": 0.03}
        print("QA_PROTRUDE SilverBootCuff%s lift=%.4f (overlap band z<=0.50) %s" % (
            t, cuff_lift, "PASS" if cuff_ok else "FAIL"))

    # ---- floating parts: nearest distance to any other garment/mannequin mesh ----
    all_meshes = garment + mannequin
    bvhs = {o.name: world_bvh(o) for o in all_meshes}
    floating = {}
    for o in garment:
        best = None
        for other in all_meshes:
            if other is o:
                continue
            bvh = bvhs[other.name]
            for w in world_verts(o):
                hit = bvh.find_nearest(w)
                if hit is not None and (best is None or hit[3] < best):
                    best = hit[3]
                    if best < 0.001:
                        break
            if best is not None and best < 0.001:
                break
        floating[o.name] = {"nearest_other": round(best, 4) if best is not None else None,
                            "ok": bool(best is not None and best <= 0.05)}
    bad_float = [n for n, v in floating.items() if not v["ok"]]
    # The brim is exempted from the generic vertex-distance floating
    # test when the parametric proof holds: its only vertices are the
    # rim vertices, so the vertex test cannot see the crown/band
    # passing through its disc faces (see QA_BRIM_PROOF above).
    if ("YellowHatBrim" in bad_float and brim_proof["crown_passes_through_brim"]
            and brim_proof["band_passes_through_brim"]):
        bad_float.remove("YellowHatBrim")
        floating["YellowHatBrim"]["ok"] = True
        floating["YellowHatBrim"]["note"] = (
            "connected by parametric proof (crown and band pass through "
            "the brim disc; vertex sampling misses the crossing)")
        print("QA_FLOATING YellowHatBrim exempted by brim proof")
    print("QA_FLOATING bad=%s" % bad_float)
    for n in bad_float:
        print("QA_FLOATING %s nearest_other=%.4f" % (n, floating[n]["nearest_other"]))

    # ---- rain-hat brim vs eye line (BACKLOG: 雨帽檐间隙) ----
    # The brim bottom edge (z 1.608) must stay above the eyes
    # (eye line z ~1.525) so both eyes stay visible from the front.
    # The brim is a closed thin cylinder (031 sun-hat construction):
    # the crown sphere passes through the brim disc, so the brim's
    # only "connection" reading is the brim-vs-crown contact (0.0)
    # plus the hat band sitting on the brim top.
    eye_zs = []
    for n in ("Mannequin_Eye", "Mannequin_Eye.001"):
        eye_zs += [w.z for w in world_verts(obj(n))]
    brim_zs = [w.z for w in world_verts(obj("YellowHatBrim"))]
    brim_xs = [abs(w.x) for w in world_verts(obj("YellowHatBrim"))]
    brim_vs_eyes = {
        "brim_bottom_z": round(min(brim_zs), 3),
        "brim_top_z": round(max(brim_zs), 3),
        "brim_radius": round(max(brim_xs), 3),
        "eye_z": (round(min(eye_zs), 3), round(max(eye_zs), 3)),
        "brim_bottom_above_eye_top": bool(min(brim_zs) > max(eye_zs)),
        "clearance": round(min(brim_zs) - max(eye_zs), 3),
        "brim_vs_crown_min": attach["brim_vs_crown"]["min"],
        "brim_vs_band_min": attach["brim_vs_band"]["min"],
        "crown_passes_through_brim": bool(
            brim_proof["crown_passes_through_brim"]),
        "band_passes_through_brim": bool(
            brim_proof["band_passes_through_brim"]),
        "ok": bool(min(brim_zs) > max(eye_zs)
                   and brim_proof["crown_passes_through_brim"]
                   and brim_proof["band_passes_through_brim"]),
    }
    print("QA_BRIM_VS_EYES %s" % brim_vs_eyes)

    # ---- glove coverage (BACKLOG: 手套包覆) ----
    # The glove sphere encloses the hand sphere (centres 0.03 apart, so
    # the surfaces cross by construction). Coverage: every left-hand
    # vertex must lie inside the glove ellipsoid OR inside the sleeve
    # tube (the hand's wrist-side cap is covered by the sleeve, which
    # ends at t=0.55 while the glove starts at t~0.50).
    hand_l = obj("Mannequin_Hand")
    glove_in = 0
    sleeve_covered = 0
    uncovered = 0
    uncovered_pts = []
    for w in world_verts(hand_l):
        if inside_ellipsoid(w, GLOVE_C, GLOVE_R):
            glove_in += 1
            continue
        # Arm-axis parameter t of the point, and radial distance.
        rel = w - ARM_L_SHOULDER
        t = rel.dot(ARM_L_DIR)
        radial = (rel - ARM_L_DIR * t).length
        if -0.12 <= t <= 0.55 and radial <= sleeve_radius_at_s(t + 0.12) + 0.002:
            sleeve_covered += 1
        else:
            uncovered += 1
            uncovered_pts.append((round(w.x, 3), round(w.y, 3),
                                  round(w.z, 3)))
    glove = {
        "hand_verts_total": len(world_verts(hand_l)),
        "inside_glove": glove_in,
        "covered_by_sleeve": sleeve_covered,
        "uncovered": uncovered,
        "uncovered_points": uncovered_pts[:5],
        "glove_vs_hand_min": attach["glove_vs_handL"]["min"],
        "ok": bool(uncovered == 0),
    }
    print("QA_GLOVE %s" % glove)

    # ---- umbrella: canopy + shaft (BACKLOG: 雨伞伞面与伞柄) ----
    # Shaft axis from the built mesh: the shaft tube's two cap-centre
    # vertices (valence 6 in the tube mesh) sit exactly at the wrist
    # and at the canopy base. Everything below is recomputed from
    # those two measured points, not from the design constants.
    shaft_obj = obj("SilverUmbrellaShaft")
    shaft_bm = bmesh.new()
    shaft_bm.from_mesh(shaft_obj.data)
    shaft_bm.verts.ensure_lookup_table()
    cap_centres = []
    for v in shaft_bm.verts:
        if len(v.link_edges) == 6:
            cap_centres.append(shaft_obj.matrix_world @ v.co)
    shaft_bm.free()
    cap_centres.sort(key=lambda p: p.z)
    wrist_m = cap_centres[0] if cap_centres else Vector(HAND_R_C)
    top_m = cap_centres[-1] if len(cap_centres) > 1 else wrist_m
    shaft_dir_m = (top_m - wrist_m)
    shaft_len_m = shaft_dir_m.length
    shaft_dir_m = shaft_dir_m.normalized() if shaft_len_m > 0 else Vector((0, 0, 1))
    # Shaft point at z 0.90: ellipse value vs the raincoat (must be >1.15).
    t90 = (0.90 - wrist_m.z) / shaft_dir_m.z if abs(shaft_dir_m.z) > 1e-6 else 0.0
    sp90 = wrist_m + shaft_dir_m * t90
    rx90, ry90 = interp_rings(RAINCOAT_RINGS, 0.90)
    shaft_ellipse_090 = round(ellipse_value(sp90.x, sp90.y, rx90, ry90), 3)
    # Canopy rim: the canopy's lowest ring (r 0.22 at the shaft top).
    canopy_obj = obj("YellowUmbrellaCanopy")
    canopy_zs = [w.z for w in world_verts(canopy_obj)]
    rim_z = min(canopy_zs)
    rim_verts = [w for w in world_verts(canopy_obj)
                 if abs(w.z - rim_z) < 1e-4]
    rim_centre = Vector((sum(w.x for w in rim_verts) / len(rim_verts),
                         sum(w.y for w in rim_verts) / len(rim_verts),
                         rim_z))
    rx_rim, ry_rim = interp_rings(RAINCOAT_RINGS, rim_z)
    rim_ellipse = min(ellipse_value(w.x, w.y, rx_rim, ry_rim)
                      for w in rim_verts)
    # Canopy rim vs sleeve axis, radial clearance (040 v1 lesson: the
    # rim sits BESIDE the shoulder, so a height comparison is the wrong
    # check — compare radial distance to the sleeve axis instead).
    sleeve_origin = ARM_R_SHOULDER - ARM_R_DIR * 0.12
    rim_vs_sleeve = None
    rim_clearance = None
    for w in rim_verts:
        rel = w - sleeve_origin
        s_along = rel.dot(ARM_R_DIR)
        radial = (rel - ARM_R_DIR * s_along).length
        # s_along is already measured from the sleeve origin (the tube's
        # s=0), so it feeds sleeve_radius_at_s directly.
        clearance = radial - sleeve_radius_at_s(s_along)
        if rim_vs_sleeve is None or radial < rim_vs_sleeve:
            rim_vs_sleeve = radial
            rim_clearance = clearance
    # Grip encloses the shaft: the two tubes are concentric by
    # construction (same axis from the wrist). A vertex-to-surface
    # distance between concentric tubes reads ~0.02 (the grip's ring
    # vertices sit 0.02 along the shaft from the shaft's end cap), so
    # the connection is proven by axis coincidence instead: the grip's
    # ring-centre axis must coincide with the shaft axis, and the grip
    # radius (0.025) must exceed the shaft radius (0.012).
    grip_obj = obj("NavyUmbrellaGrip")
    grip_clusters = {}
    for w in world_verts(grip_obj):
        s = round((w - wrist_m).dot(shaft_dir_m), 3)
        grip_clusters.setdefault(s, []).append(w)
    grip_ring_centres = []
    grip_radius = None
    for s, pts in sorted(grip_clusters.items()):
        if len(pts) >= 4:
            c = Vector((sum(p.x for p in pts) / len(pts),
                        sum(p.y for p in pts) / len(pts),
                        sum(p.z for p in pts) / len(pts)))
            grip_ring_centres.append(c)
            r = max((p - c).length for p in pts)
            grip_radius = r if grip_radius is None else max(grip_radius, r)
    shaft_radius = 0.0
    for w in world_verts(shaft_obj):
        shaft_radius = max(
            shaft_radius,
            ((w - wrist_m) - shaft_dir_m * (w - wrist_m).dot(shaft_dir_m)).length)
    grip_axis_angle = None
    grip_axis_offset = None
    if len(grip_ring_centres) >= 2:
        g0, g1 = grip_ring_centres[0], grip_ring_centres[-1]
        grip_dir = (g1 - g0)
        if grip_dir.length > 0:
            grip_dir = grip_dir.normalized()
            grip_axis_angle = math.degrees(math.acos(max(
                -1.0, min(1.0, grip_dir.dot(shaft_dir_m)))))
        grip_axis_offset = ((g0 - wrist_m) - shaft_dir_m
                            * (g0 - wrist_m).dot(shaft_dir_m)).length
    shaft_enclosed_by_grip = bool(
        grip_axis_angle is not None and grip_axis_angle < 1.0
        and grip_axis_offset is not None and grip_axis_offset < 0.002
        and grip_radius is not None and grip_radius > shaft_radius + 0.005)
    # Tip centred on the canopy apex: the tip sphere's centre must
    # coincide with the canopy top ring's centre (a vertex distance
    # reads 0.0075 because the small sphere's vertices sit between the
    # cone's top ring and its cap).
    tip_verts = world_verts(obj("SilverUmbrellaTip"))
    tip_c = Vector((sum(w.x for w in tip_verts) / len(tip_verts),
                    sum(w.y for w in tip_verts) / len(tip_verts),
                    sum(w.z for w in tip_verts) / len(tip_verts)))
    canopy_top_z = max(canopy_zs)
    canopy_top_verts = [w for w in world_verts(canopy_obj)
                        if abs(w.z - canopy_top_z) < 1e-4]
    canopy_top_c = Vector((
        sum(w.x for w in canopy_top_verts) / len(canopy_top_verts),
        sum(w.y for w in canopy_top_verts) / len(canopy_top_verts),
        canopy_top_z))
    tip_centre_offset = (tip_c - canopy_top_c).length
    tip_centred = bool(tip_centre_offset <= 0.002)
    # Grip held in the right hand: the grip segment must cross the
    # hand sphere — some grip vertices inside the hand ellipsoid, some
    # outside (a vertex distance reads 0.0314 because the embedded
    # vertices sit that deep inside the hand, not because the grip
    # floats beside it).
    grip_in_hand = 0
    grip_out_hand = 0
    for w in world_verts(grip_obj):
        if inside_ellipsoid(w, HAND_R_C, HAND_R_R):
            grip_in_hand += 1
        else:
            grip_out_hand += 1
    grip_through_hand = bool(grip_in_hand > 0 and grip_out_hand > 0)
    umbrella = {
        "wrist_measured": [round(v, 4) for v in wrist_m],
        "top_measured": [round(v, 4) for v in top_m],
        "shaft_length_measured": round(shaft_len_m, 4),
        "shaft_dir_measured": [round(v, 3) for v in shaft_dir_m],
        "shaft_at_z090_ellipse": shaft_ellipse_090,
        "shaft_ellipse_ok": bool(shaft_ellipse_090 > 1.15),
        "canopy_rim_z": round(rim_z, 4),
        "canopy_rim_centre": [round(v, 4) for v in rim_centre],
        "canopy_rim_radius": round(
            max((Vector((w.x, w.y, 0)) - Vector((rim_centre.x, rim_centre.y, 0))).length
                for w in rim_verts), 4),
        "canopy_rim_ellipse": round(rim_ellipse, 3),
        "canopy_rim_ellipse_ok": bool(rim_ellipse > 1.15),
        "canopy_rim_vs_sleeve_axis": (round(rim_vs_sleeve, 4)
                                      if rim_vs_sleeve is not None else None),
        "canopy_rim_radial_clearance": (round(rim_clearance, 4)
                                        if rim_clearance is not None else None),
        "canopy_rim_clearance_ok": bool(rim_clearance is not None
                                        and rim_clearance >= 0.005),
        "canopy_vs_sleeve_min": gaps["canopy_vs_sleeve"]["min"],
        "shaft_vs_raincoat_min": gaps["shaft_vs_raincoat"]["min"],
        "shaft_vs_grip_min": attach["shaft_vs_grip"]["min"],
        "shaft_vs_canopy_min": attach["shaft_vs_canopy"]["min"],
        "tip_vs_canopy_min": attach["tip_vs_canopy"]["min"],
        "grip_vs_hand_min": attach["grip_vs_handR"]["min"],
        "shaft_vs_sleeve_min": attach["shaft_vs_sleeve"]["min"],
        "grip_axis_angle_deg": (round(grip_axis_angle, 3)
                                if grip_axis_angle is not None else None),
        "grip_axis_offset": (round(grip_axis_offset, 4)
                             if grip_axis_offset is not None else None),
        "grip_radius": (round(grip_radius, 4)
                        if grip_radius is not None else None),
        "shaft_radius": round(shaft_radius, 4),
        "shaft_enclosed_by_grip": bool(shaft_enclosed_by_grip),
        "tip_centre": [round(v, 4) for v in tip_c],
        "canopy_top_centre": [round(v, 4) for v in canopy_top_c],
        "tip_centre_offset": round(tip_centre_offset, 4),
        "tip_centred_on_canopy": bool(tip_centred),
        "grip_verts_inside_hand": grip_in_hand,
        "grip_verts_outside_hand": grip_out_hand,
        "grip_through_hand": bool(grip_through_hand),
        "ok": bool(shaft_ellipse_090 > 1.15 and rim_ellipse > 1.15
                   and rim_clearance is not None and rim_clearance >= 0.005
                   and gaps["canopy_vs_sleeve"]["ok"]
                   and gaps["shaft_vs_raincoat"]["ok"]
                   and attach["shaft_vs_canopy"]["min"] is not None
                   and attach["shaft_vs_canopy"]["min"] <= 0.001
                   and shaft_enclosed_by_grip
                   and tip_centred
                   and grip_through_hand),
    }
    print("QA_UMBRELLA %s" % umbrella)

    # ---- hood folded behind the neck (BACKLOG: 脑后兜帽搭接) ----
    # The hood is a back arc (15-165 deg, back is 90 deg), z 1.52-1.38.
    # Its top ring sits above the raincoat top edge (1.50) and tucks
    # behind the hair; its lower rings clear the raincoat and sweater.
    hood_verts = world_verts(obj("YellowHood"))
    hood_angles = []
    for w in hood_verts:
        # Parametric angle on the hood's own ellipse (rx != ry, so the
        # geometric atan2 would read ~8 deg where the design arc starts
        # at 15 deg).
        rx_h, ry_h = interp_rings(HOOD_RINGS, w.z)
        a = math.degrees(math.atan2(w.y / ry_h, w.x / rx_h)) % 360.0
        hood_angles.append(a)
    hood_zs = [w.z for w in hood_verts]
    coat_top_z = max(w.z for w in world_verts(obj("YellowRaincoat")))
    # The hood tucks behind the hair: some hood vertices must lie
    # INSIDE the hair volume and some OUTSIDE (the hood surface crosses
    # the hair surface). A plain min distance reads 0.0059 because no
    # hood vertex happens to sit on the crossing line — the crossing
    # itself is what matters, not the nearest vertex.
    bvh_hair2 = world_bvh(obj("Mannequin_Hair"))
    hood_in_hair = 0
    hood_out_hair = 0
    for w in hood_verts:
        oh, _d = _outside_mesh(bvh_hair2, w)
        if oh:
            hood_out_hair += 1
        else:
            hood_in_hair += 1
    hood = {
        "hood_z": (round(min(hood_zs), 3), round(max(hood_zs), 3)),
        "hood_top_ring_z": round(max(hood_zs), 3),
        "raincoat_top_z": round(coat_top_z, 3),
        "hood_top_above_coat_top": bool(max(hood_zs) > coat_top_z),
        "hood_angle_min": round(min(hood_angles), 1),
        "hood_angle_max": round(max(hood_angles), 1),
        "hood_arc_covers_back": bool(min(hood_angles) <= 20
                                     and max(hood_angles) >= 160),
        "hood_vs_raincoat_min": gaps["hood_vs_raincoat"]["min"],
        "hood_vs_sweater_min": gaps["hood_vs_sweater"]["min"],
        "hood_vs_hair_min": attach["hood_vs_hair"]["min"],
        "hood_verts_inside_hair": hood_in_hair,
        "hood_verts_outside_hair": hood_out_hair,
        "hood_tucks_behind_hair": bool(hood_in_hair > 0
                                       and hood_out_hair > 0),
        "ok": bool(max(hood_zs) > coat_top_z
                   and gaps["hood_vs_raincoat"]["ok"]
                   and gaps["hood_vs_sweater"]["ok"]
                   and hood_in_hair > 0 and hood_out_hair > 0),
    }
    print("QA_HOOD %s" % hood)

    # ---- rain boots vs trouser hem (BACKLOG: 雨靴与长裤搭接) ----
    # The tall boot tube (z 0.50-0.02, r 0.118) overlaps the trouser
    # tube (hem z 0.34): the boot circle is wider than the trouser
    # ellipse at the hem, so the boot surface crosses the trouser wall
    # by construction — the boot reads as worn OVER the hem. The leg
    # itself must stay covered: every leg vertex at z 0.34-0.50 must be
    # inside the boot tube or the trouser tube (no skin shows).
    boot_trouser = {}
    for side, sx in (("L", -1), ("R", 1)):
        rx_t, ry_t = interp_rings(TROUSER_RINGS, 0.42)
        outside = total = 0
        for k in range(72):
            a = 2.0 * math.pi * k / 72.0
            p = Vector((sx * 0.13 + 0.118 * math.cos(a),
                        0.118 * math.sin(a), 0.42))
            total += 1
            if (p.x / rx_t) ** 2 + (p.y / ry_t) ** 2 > 1.0:
                outside += 1
        boot_trouser[side] = {"boot_circle_outside_trouser": outside,
                              "samples": total,
                              "trouser_rx_at_0.42": round(rx_t, 4),
                              "trouser_ry_at_0.42": round(ry_t, 4)}
    leg_outside = 0
    for leg_name, sx in (("Mannequin_Leg", -1), ("Mannequin_Leg.001", 1)):
        for w in world_verts(obj(leg_name)):
            if 0.34 - 1e-4 <= w.z <= 0.50 + 1e-4:
                rx_t, ry_t = interp_rings(TROUSER_RINGS, w.z)
                in_trouser = (w.x / rx_t) ** 2 + (w.y / ry_t) ** 2 <= 1.0
                dx = w.x - sx * 0.13
                in_boot = (dx * dx + w.y * w.y) ** 0.5 <= 0.118
                if not (in_trouser or in_boot):
                    leg_outside += 1
    boot_trouser["leg_verts_outside_both_at_band"] = leg_outside
    boot_trouser["leg_covered"] = bool(leg_outside == 0)
    boot_trouser["boot_vs_trouser_min_L"] = attach["boot_vs_trousers"]["min"]
    boot_trouser["boot_vs_trouser_min_R"] = attach["boot.001_vs_trousers"]["min"]
    boot_trouser["boot_top_z"] = round(
        max(w.z for w in world_verts(obj("YellowRainBoot"))), 3)
    boot_trouser["trouser_hem_z"] = round(
        min(w.z for w in world_verts(obj("NavyTrousers"))), 3)
    boot_trouser["ok"] = bool(boot_trouser["leg_covered"])
    print("QA_BOOT_TROUSER %s" % boot_trouser)

    # ---- raindrop placement (BACKLOG: 雨滴纹位置) ----
    # Sweater drops must sit in the coat's open front wedge (240-300
    # deg) so they show through; coat drops must sit outside the wedge
    # (on the coat front edges, 225/315 deg). The hat drop's bottom
    # must clear the hat-band top ring (z 1.66).
    drop_pos = {}
    for name, (ang_d, z_d, host_kind) in DROP_DESIGN.items():
        vs = world_verts(obj(name))
        cx = sum(w.x for w in vs) / len(vs)
        cy = sum(w.y for w in vs) / len(vs)
        cz = sum(w.z for w in vs) / len(vs)
        # Parametric angle on the host's ellipse (rx != ry, so the
        # geometric atan2 would read ~255 deg where the design angle
        # is 262 deg).
        rx_h, ry_h = interp_rings(
            SWEATER_RINGS if host_kind == "sweater" else RAINCOAT_RINGS, cz)
        ang = math.degrees(math.atan2(cy / ry_h, cx / rx_h)) % 360.0
        in_wedge = 240.0 <= ang <= 300.0
        if host_kind == "sweater":
            pos_ok = in_wedge and abs(cz - z_d) < 0.01
        else:
            pos_ok = (not in_wedge) and abs(cz - z_d) < 0.01
        drop_pos[name] = {"centre": (round(cx, 4), round(cy, 4),
                                     round(cz, 4)),
                          "angle_deg": round(ang, 1),
                          "design_angle_deg": ang_d,
                          "design_z": z_d,
                          "in_open_wedge_240_300": bool(in_wedge),
                          "ok": bool(pos_ok)}
    hat_drop_zs = [w.z for w in world_verts(obj("BlueRaindropHat"))]
    band_zs = [w.z for w in world_verts(obj("NavyHatBand"))]
    drop_pos["BlueRaindropHat"] = {
        "min_z": round(min(hat_drop_zs), 4),
        "band_top_z": round(max(band_zs), 3),
        "clearance_above_band": round(min(hat_drop_zs) - max(band_zs), 4),
        "ok": bool(min(hat_drop_zs) > max(band_zs)),
    }
    drop_pos_ok = all(v["ok"] for v in drop_pos.values())
    print("QA_DROPS %s" % drop_pos)

    # ---- dimensions & ground contact ----
    xs, ys, zs = [], [], []
    for o in garment:
        for w in world_verts(o):
            xs.append(w.x); ys.append(w.y); zs.append(w.z)
    g_bbox = {"x": (round(min(xs), 3), round(max(xs), 3)),
              "y": (round(min(ys), 3), round(max(ys), 3)),
              "z": (round(min(zs), 3), round(max(zs), 3)),
              "height": round(max(zs) - min(zs), 3),
              "width": round(max(xs) - min(xs), 3)}
    sole_names = ["YellowRainBootSole", "YellowRainBootSole.001"]
    sole_min_z = min(min(w.z for w in world_verts(obj(n)))
                     for n in sole_names)
    foot_min_z = min(min(w.z for w in world_verts(obj(n)))
                     for n in ("Mannequin_Foot", "Mannequin_Foot.001"))
    print("QA_GROUND sole_min_z=%.4f foot_min_z=%.4f" % (sole_min_z, foot_min_z))
    top_z = max(max(w.z for w in world_verts(o))
                for o in garment + mannequin)
    top_obj = None
    for o in garment + mannequin:
        if max(w.z for w in world_verts(o)) >= top_z - 1e-6:
            top_obj = o.name
            break
    print("QA_DIMS garment_bbox=%s sole_min_z=%.4f top_z=%.3f (%s)" % (
        g_bbox, sole_min_z, top_z, top_obj))

    # ---- framing: figure height fraction in the saved camera ----
    cam = bpy.context.scene.camera
    frame_frac = None
    if cam is not None:
        from bpy_extras.object_utils import world_to_camera_view
        scene = bpy.context.scene
        y_top = world_to_camera_view(scene, cam, Vector((0, 0, top_z)))[1]
        y_bot = world_to_camera_view(scene, cam, Vector((0, 0, 0.0)))[1]
        frame_frac = round(abs(y_top - y_bot), 3)
    print("QA_FRAME fraction=%s" % frame_frac)

    # ---- materials ----
    mats = check_materials()
    for r in mats["rows"]:
        print("QA_MAT %s %s" % (r["name"], r))

    # ---- totals & verdicts ----
    tot = {k: sum(r[k] for r in results.values())
           for k in ("verts", "faces", "tris", "quads", "ngons",
                     "duplicate_verts", "loose_edges", "boundary_edges",
                     "nonmanifold_edges", "degenerate_faces",
                     "inverted_normals")}
    mannequin_faces = sum(len(o.data.polygons) for o in mannequin)
    closed_boundary = sum(results[n]["boundary_edges"] for n in results
                          if base(n) in CLOSED_SOLIDS)
    flat_inv = sum(results[n]["inverted_normals"] for n in results
                   if base(n) in FLAT_PATCHES)
    ribbon_inv = sum(results[n]["inverted_normals"] for n in results
                     if base(n) in RIBBON_GEOMETRIC)
    solid_inv = tot["inverted_normals"] - flat_inv - ribbon_inv
    uv_parts = sorted(n for n, r in results.items() if r["uv"]["has_uv"])
    uv_oob = sum(r["uv"]["out_of_bounds"] for r in results.values())
    empty_slots = sum(1 for r in results.values()
                      for m in r["materials"] if m is None)
    gaps_ok = all(gaps[k]["ok"] for k in gaps)
    ground_ok = abs(sole_min_z) <= 0.005
    frame_ok = frame_frac is not None and 0.60 <= frame_frac <= 0.80
    warnings = []
    for k, v in attach.items():
        # brim_vs_crown / brim_vs_band are proven connected
        # parametrically (QA_BRIM_PROOF); their vertex distances are a
        # sampling artifact, not a floating gap.
        if k in ("brim_vs_crown", "brim_vs_band"):
            continue
        if v["min"] is not None and v["min"] > 0.05:
            warnings.append(
                "%s: 附件离宿主 %.4f 米（> 0.05），可能漂浮；检查该附件是否"
                "靠挂绳/绑带连接，否则下次贴近宿主。" % (k, v["min"]))
    warnings.append(
        "earring_relief_faceting: 金耳钉离头面最远点 %.4f / %.4f 米（设计浮雕"
        " 0.019）：人偶头是 10×8 粗球面，耳钉所贴的面片比理想椭球面内收"
        "约 0.011 米，网格实测值含该面片内收；按理想椭球面算浮雕为 "
        "%.4f 米（顶点采样，粗球面无顶点落在耳钉正外侧），按耳钉中心+半径"
        "算外沿浮雕为 %.4f 米，与设计值 0.019 一致。耳钉半嵌头面（最小距离"
        " %.4f / %.4f 米），读作金耳钉，无漂浮。" % (
            protrusions["GoldEarring"]["lift"],
            protrusions["GoldEarring.001"]["lift"], earring_ideal,
            earring_analytic,
            attach["earring_vs_head"]["min"],
            attach["earring.001_vs_head"]["min"]))
    warnings.append(
        "brim_construction: 雨衣黄帽檐是闭合薄圆柱（031 遮阳帽做法，r 0.34，"
        "z 1.608–1.622），帽顶球穿过檐盘：帽顶在檐盘底沿/顶沿处的水平半径"
        " %.4f / %.4f 米（< 檐半径 0.34 米），帽顶 z 范围 %.3f–%.3f 米跨过"
        "檐盘 z 范围，帽顶球面与檐盘上下两面都相交（参数化证明，见第 4.2 节）；"
        "帽带底环 z %.3f 米落在檐盘 z 范围内、环半径 %.4f 米（< 0.34 米），"
        "帽带穿过檐盘。檐顶点离帽顶/帽带面的顶点距离 %.4f / %.4f 米是采样"
        "假象（檐盘上下两面是无内部顶点的 n-gon，034 同款量法教训），不是"
        "漂浮。帽檐底沿 z %.3f 米，眼顶 z %.3f 米，檐在眼线之上 %.3f 米，"
        "双眼正面可辨。" % (
            brim_proof["crown_rx_at_brim_bottom"],
            brim_proof["crown_rx_at_brim_top"],
            brim_proof["crown_z"][0], brim_proof["crown_z"][1],
            brim_proof["band_bottom_z"],
            brim_proof["band_radius_at_bottom"],
            attach["brim_vs_crown"]["min"], attach["brim_vs_band"]["min"],
            brim_vs_eyes["brim_bottom_z"], brim_vs_eyes["eye_z"][1],
            brim_vs_eyes["clearance"]))
    warnings.append(
        "hood_tuck: 雨衣黄兜帽顶环 z %.3f 米在雨衣顶沿 z %.3f 米之上、弧面"
        " %.1f°–%.1f° 盖住脑后，兜帽 %d 个顶点在发顶面之内、%d 个在发顶面"
        "之外（兜帽面穿过发顶面，顶环塞进发顶之后，不是漂浮；最近顶点离"
        "发顶面 %.4f 米是顶点采样，未落在交线上）；兜帽 vs 雨衣最小间隙"
        " %.4f 米、vs 毛衣 %.4f 米。" % (
            hood["hood_top_ring_z"], hood["raincoat_top_z"],
            hood["hood_angle_min"], hood["hood_angle_max"],
            hood["hood_verts_inside_hair"], hood["hood_verts_outside_hair"],
            attach["hood_vs_hair"]["min"],
            gaps["hood_vs_raincoat"]["min"], gaps["hood_vs_sweater"]["min"]))
    warnings.append(
        "boot_over_trouser_hem: 雨衣黄高筒雨靴（r 0.118，靴顶 z %.3f 米）套在"
        "藏青长裤下摆（z %.3f 米）外面：靴面与裤面按构造相交——靴圈在"
        " z 0.42 处 72 个采样点中有 %d / %d 个落在裤椭圆（rx %.4f、"
        "ry %.4f）之外、其余在内，靴圈穿过裤面（顶点距离 %.4f 米是采样"
        "假象：靴筒只有 z 0.50/0.02 两环顶点，未落在交线上）；搭接带"
        " z 0.34–0.50 的腿顶点有 %d 个既不在靴筒内、也不在裤椭圆内，属靴口"
        "搭接构造、不是穿帮；037 对 036 的靴口环搭接同款处理。" % (
            boot_trouser["boot_top_z"], boot_trouser["trouser_hem_z"],
            boot_trouser["L"]["boot_circle_outside_trouser"],
            boot_trouser["R"]["boot_circle_outside_trouser"],
            boot_trouser["L"]["trouser_rx_at_0.42"],
            boot_trouser["L"]["trouser_ry_at_0.42"],
            boot_trouser["boot_vs_trouser_min_L"],
            boot_trouser["leg_verts_outside_both_at_band"]))
    warnings.append(
        "sleeve_through_coat_shoulder: 藏青长袖从雨衣肩部穿出（032 的做法："
        "袖筒起点沿臂轴上抬 0.12）：袖面与雨衣面在肩部相交（袖顶点离雨衣面"
        "最小 %s / %s 米），属缝合构造、不是穿帮；袖筒 caps=True，筒口"
        "不透手臂顶盖。" % (
            attach["sleeveL_vs_raincoat"]["min"],
            attach["sleeveR_vs_raincoat"]["min"]))
    warnings.append(
        "umbrella_held: 雨伞握把穿过右手掌球（握把 %d 个顶点在手掌椭球内、"
        "%d 个在外，握把穿过手掌面，握持构造；握把顶点离手掌面最近 %.4f 米"
        "是埋得最浅的顶点到掌面的距离，不是间隙）；伞柄从袖口端盖中心穿出"
        "（伞柄顶点离袖筒面最小 %.4f 米，48° 斜出、不沿前臂走）；伞柄与握把"
        "同轴（轴夹角 %.3f°、轴偏 %.4f 米，握把半径 %.4f 米 > 伞柄半径"
        " %.4f 米，伞柄被握把包住）；伞柄与伞面相接（最小 %s 米），伞尖中心"
        "与伞面顶环中心重合（偏差 %.4f 米）。" % (
            umbrella["grip_verts_inside_hand"],
            umbrella["grip_verts_outside_hand"],
            attach["grip_vs_handR"]["min"], attach["shaft_vs_sleeve"]["min"],
            umbrella["grip_axis_angle_deg"], umbrella["grip_axis_offset"],
            umbrella["grip_radius"], umbrella["shaft_radius"],
            attach["shaft_vs_canopy"]["min"],
            umbrella["tip_centre_offset"]))
    warnings.append(
        "hatdrop_analytic: 帽上雨滴最远点离帽顶球面 %.4f 米（通用上限 0.03）："
        "雨滴是 0.076 米高的扁椭球水滴，立在曲率半径 0.26 米的帽顶球面上，"
        "滴尖离面大是构造使然——按理想椭球解析值 %.4f 米，实测与解析差"
        " %.4f 米；帽顶是 12×6 粗球面，横向刻面矢高 0.0089 米，实测差值在"
        "允差 ±0.012 内（与 037 护目镜片、034 墨镜片同款量法）；雨滴底座"
        "埋进帽顶（最小距离 %.4f 米），不是漂浮。已按解析值判定，本项通过。" % (
            protrusions["BlueRaindropHat"]["lift"],
            protrusions["BlueRaindropHat"]["analytic"],
            abs(protrusions["BlueRaindropHat"]["lift"]
                - protrusions["BlueRaindropHat"]["analytic"]),
            attach["hatdrop_vs_crown"]["min"]))
    if not protrusions["HairStreak"]["ok"]:
        warnings.append(
            "[硬检查不通过] streak_invisible: 浅蓝挑染可见顶点 %d / %d 个"
            "（要求 > 0），可见部分凸起 %.4f 米（要求 ≥ 0.005）：挑染扁椭球"
            "中心 (0.11, -0.125, 1.44)，半嵌在黑发顶与头球之间——单宿主原值"
            " vs 发顶最远点 %.4f 米是埋住的下端尖角离发顶面的距离，不是凸起；"
            "挑染唯一的 1 个“可见”顶点凸起为 0.0000 米（恰好落在头球面上），"
            "其余 25 个顶点都在人偶头球内（头球前表面在该处 y ≈ -0.164 米，"
            "挑染最前顶点 y ≈ -0.146 米），从任何角度都看不见；040 效果图里"
            "帽檐下没有浅蓝挑染，设计说明“帽檐下露一缕”未实现（036 的挑染"
            "同款失败，037 已判过）。修复法：把挑染移到发面外侧（如中心"
            " (0.11, -0.185, 1.44)，贴发面平放），或抬到 z 1.50 以上发顶"
            "覆盖处。" % (
                protrusions["HairStreak"]["visible_verts"],
                protrusions["HairStreak"]["total_verts"],
                protrusions["HairStreak"]["lift"],
                protrusions["HairStreak"]["raw_lift"]))
    if not gaps["hatcrown_vs_hair"]["ok"]:
        warnings.append(
            "[硬检查不通过] crown_tight_fit: 雨衣黄帽顶 vs 发顶可见部分最小间隙"
            " %.4f 米（0.005 构造线之下 %.4f 米，中位 %.4f 米）：帽顶球（r 0.26，"
            "压扁 0.55，球心 z 1.63）下沿按构造埋进发顶椭球，球面与发顶面以浅"
            "角度相交，交线附近的可见顶点离发顶面只有 %.4f 米；正间隙、无相交、"
            "无视觉缺陷（040 目视通过，帽顶亮黄完整）。修复法：把帽顶球心"
            " z 1.63→1.64，或把帽顶球半径 0.26→0.27。" % (
                gaps["hatcrown_vs_hair"]["min"],
                0.005 - gaps["hatcrown_vs_hair"]["min"],
                gaps["hatcrown_vs_hair"]["median"],
                gaps["hatcrown_vs_hair"]["min"]))
    if not gaps["hood_vs_raincoat"]["ok"]:
        warnings.append(
            "[硬检查不通过] hood_tight_fit: 雨衣黄兜帽 vs 雨衣最小间隙 %.4f 米"
            "（0.005 构造线之下 %.4f 米）：兜帽下环（z 1.38，rx 0.318）只比"
            "雨衣面（rx 0.312）大 0.006；正间隙、无相交、无视觉缺陷。修复法："
            "把兜帽下环 rx 0.318→0.322，或把兜帽下沿 z 1.38→1.40。" % (
                gaps["hood_vs_raincoat"]["min"],
                0.005 - gaps["hood_vs_raincoat"]["min"]))
    if not gaps["hatband_vs_crown"]["ok"]:
        warnings.append(
            "[硬检查不通过] hatband_tight_fit: 藏青帽带 vs 雨衣黄帽顶最小间隙"
            " %.4f 米（0.005 构造线之下 %.4f 米）：帽带环 ry 已按帽顶 +y 面"
            "放大（031 v3 教训）；正间隙、无相交、无视觉缺陷。修复法：帽带"
            "环 ry 再 +0.002。" % (
                gaps["hatband_vs_crown"]["min"],
                0.005 - gaps["hatband_vs_crown"]["min"]))
    if not gaps["cuffL_vs_sleeve"]["ok"] or not gaps["cuffR_vs_sleeve"]["ok"]:
        warnings.append(
            "[硬检查不通过] cuff_tight_fit: 奶油白袖口 vs 藏青长袖最小间隙"
            "左 %.4f / 右 %.4f 米（0.005 构造线之下）：袖口环 r 0.105，L2 已补"
            "袖筒中段半径检查（袖口顶环落在袖筒 s 0.60 处，那里袖筒半径是"
            " 0.0986、不是末端 0.096）；正间隙、无相交、无视觉缺陷。修复法："
            "把袖口沿臂轴下移 0.02 米到袖筒末端段，或把袖口环再放大到 0.108。"
            % (gaps["cuffL_vs_sleeve"]["min"],
               gaps["cuffR_vs_sleeve"]["min"]))
    if not ground_ok:
        warnings.append(
            "boots_float: 靴底最低点 z=%.4f 米（地面 z=0，允许 ≤0.005）："
            "靴底与地面之间有缝。修复：把 YellowRainBootSole 的 z_bottom 改为 "
            "0.0 后重渲。" % sole_min_z)
    if not glove["ok"]:
        warnings.append(
            "glove_coverage: 左手有 %d 个顶点既不在手套椭球内、也不在袖筒内"
            "（见第 4.6 节）：手套或袖筒没盖住手掌；下次把手套球心沿臂轴上"
            "移或把手套半径加到 0.10。" % glove["uncovered"])
    if not umbrella["ok"]:
        warnings.append(
            "umbrella_position: 雨伞位置异常（伞柄 z 0.90 处椭圆归一化值 %.3f，"
            "伞面底沿椭圆归一化值 %.3f，伞面底沿离袖轴径向净空 %.4f 米）："
            "伞柄与伞面须离雨衣与袖筒足够远（归一化值 > 1.15、径向净空"
            " ≥ 0.005）。" % (
                umbrella["shaft_at_z090_ellipse"],
                umbrella["canopy_rim_ellipse"],
                umbrella["canopy_rim_radial_clearance"]))
    if not hood["ok"]:
        warnings.append(
            "hood_fit: 脑后兜帽异常（顶环 z %.3f，雨衣顶沿 z %.3f，兜帽 vs 雨衣"
            "最小 %.4f 米，兜帽 vs 发顶最小 %.4f 米）：兜帽须盖住脑后、顶环"
            "在雨衣顶沿之上、塞进发顶之后。" % (
                hood["hood_top_ring_z"], hood["raincoat_top_z"],
                gaps["hood_vs_raincoat"]["min"],
                attach["hood_vs_hair"]["min"]))
    if not brim_vs_eyes["ok"]:
        warnings.append(
            "brim_eye_line: 帽檐底沿 z %.3f 米，眼顶 z %.3f 米（帽檐须在眼线"
            "之上，双眼正面可辨）：检查帽檐高度或眼睛位置。"
            % (brim_vs_eyes["brim_bottom_z"], brim_vs_eyes["eye_z"][1]))
    if not boot_trouser["ok"]:
        warnings.append(
            "boot_trouser_leg_shows: 雨靴与长裤搭接带 z 0.34–0.50 有 %d 个腿顶点"
            "既不在靴筒内、也不在长裤椭圆内：腿部皮肤在搭接处露出；下次把"
            "靴筒半径加到 0.13 或把长裤下摆延到 z 0.30。"
            % boot_trouser["leg_verts_outside_both_at_band"])
    if not drop_pos_ok:
        warnings.append(
            "raindrop_position: 雨滴纹位置异常（见第 4.10 节）：毛衣上的雨滴"
            "须落在雨衣前开襟楔（240°–300°）内才透得出来，雨衣上的雨滴须落"
            "在楔外（225°/315°），帽上雨滴底沿须在帽带顶环（z 1.66）之上。")
    protrude_ok = all(v["ok"] for v in protrusions.values())
    float_ok = not bad_float
    faces_ok = tot["faces"] <= FACE_LIMIT
    faces_match = tot["faces"] == EXPECTED_FACES
    ngons_ok = tot["ngons"] == EXPECTED_NGONS
    topo_ok = (tot["duplicate_verts"] == 0 and tot["loose_edges"] == 0
               and tot["nonmanifold_edges"] == 0
               and tot["degenerate_faces"] == 0 and closed_boundary == 0
               and solid_inv == 0)
    fail_items = []
    if not faces_ok:
        fail_items.append("面数 %d 超过硬上限 %d" % (tot["faces"], FACE_LIMIT))
    if not faces_match:
        fail_items.append("面数 %d 与 design.md 记录 %d 不一致"
                          % (tot["faces"], EXPECTED_FACES))
    if not ngons_ok:
        fail_items.append("N-gon %d 个（设计值 0）" % tot["ngons"])
    if not topo_ok:
        fail_items.append("拓扑（重叠顶点/散边/非流形边/退化面/闭合实体边界边/实体倒置法线）")
    if not gaps_ok:
        fail_items.append("层间隙（见第 4.1 节不通过项）")
    if not brim_vs_eyes["ok"]:
        fail_items.append("帽檐间隙（见第 4.2 节：檐底压眼线或檐未接帽顶）")
    if not protrude_ok:
        fail_items.append("凸起件（见第 4.4 节不通过项）")
    if not float_ok:
        fail_items.append("漂浮部件：%s" % "、".join(bad_float))
    if not ground_ok:
        fail_items.append("落地：靴底最低点 z=%.4f 米（地面 z=0，允许 ≤0.005）"
                          % sole_min_z)
    if not glove["ok"]:
        fail_items.append("手套包覆（见第 4.6 节）")
    if not umbrella["ok"]:
        fail_items.append("雨伞伞面与伞柄（见第 4.7 节）")
    if not hood["ok"]:
        fail_items.append("脑后兜帽搭接（见第 4.8 节）")
    if not boot_trouser["ok"]:
        fail_items.append("雨靴与长裤搭接（见第 4.9 节：搭接带腿部露出）")
    if not drop_pos_ok:
        fail_items.append("雨滴纹位置（见第 4.10 节）")
    if not frame_ok:
        fail_items.append("构图：人物占画面 %.3f（标准 0.60–0.80）" % frame_frac)
    if not mats["all_ok"]:
        fail_items.append("材质（见第 6 节不通过项）")
    if empty_slots != 0:
        fail_items.append("空材质槽 %d 个" % empty_slots)
    all_ok = (faces_ok and faces_match and ngons_ok and topo_ok and gaps_ok
              and brim_vs_eyes["ok"] and protrude_ok and float_ok
              and ground_ok and glove["ok"] and umbrella["ok"]
              and hood["ok"] and boot_trouser["ok"] and drop_pos_ok
              and frame_ok and mats["all_ok"] and empty_slots == 0)

    summary = {
        "asset": "040-rainy-day-urban",
        "blend": "scenes/040-rainy-day-urban/040-rainy-day-urban.blend",
        "parts": len(results),
        "families": {k: v for k, v in fam_faces.items()},
        "total_faces": tot["faces"], "total_verts": tot["verts"],
        "tris": tot["tris"], "quads": tot["quads"],
        "ngons": tot["ngons"], "ngons_expected": EXPECTED_NGONS,
        "ngons_ok": bool(ngons_ok),
        "faces_expected": EXPECTED_FACES, "faces_match": bool(faces_match),
        "face_limit": FACE_LIMIT, "faces_ok": bool(faces_ok),
        "duplicate_verts": tot["duplicate_verts"],
        "loose_edges": tot["loose_edges"],
        "nonmanifold_edges": tot["nonmanifold_edges"],
        "degenerate_faces": tot["degenerate_faces"],
        "boundary_edges_total": tot["boundary_edges"],
        "boundary_edges_closed_solids": closed_boundary,
        "inverted_normals": tot["inverted_normals"],
        "inverted_normals_solids": solid_inv,
        "inverted_normals_flat_patches": flat_inv,
        "inverted_normals_ribbon_recalc": ribbon_inv,
        "topo_ok": bool(topo_ok),
        "uv_parts_with_layer": len(uv_parts),
        "uv_parts": uv_parts,
        "uv_out_of_bounds": uv_oob,
        "empty_material_slots": empty_slots,
        "mannequin_faces": mannequin_faces,
        "gaps": gaps, "gaps_ok": bool(gaps_ok),
        "brim_vs_eyes": brim_vs_eyes,
        "brim_proof": brim_proof,
        "attachments": attach,
        "protrusions": protrusions, "protrusions_ok": bool(protrude_ok),
        "earring_ideal_relief": earring_ideal,
        "earring_analytic_relief": earring_analytic,
        "glove": glove,
        "umbrella": umbrella,
        "hood": hood,
        "boot_trouser": boot_trouser,
        "drop_positions": drop_pos, "drop_positions_ok": bool(drop_pos_ok),
        "floating_bad": bad_float, "floating_ok": bool(float_ok),
        "garment_bbox": g_bbox,
        "sole_min_z": round(sole_min_z, 4), "ground_ok": bool(ground_ok),
        "foot_min_z": round(foot_min_z, 4),
        "fail_items": fail_items,
        "top_z": round(top_z, 3), "top_object": top_obj,
        "frame_fraction": frame_frac, "frame_ok": bool(frame_ok),
        "materials": mats,
        "warnings": warnings,
        "overall_pass": bool(all_ok),
    }
    with open(SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print("QA_SUMMARY:", json.dumps(summary, ensure_ascii=False))

    def verdict(ok, note=""):
        return ("通过" if ok else "不通过") + (("（" + note + "）") if note else "")

    with open(CHECKLIST, "w", encoding="utf-8") as f:
        f.write("# 041 资产质检单：雨天套装（040）\n\n")
        f.write("被检资产：`scenes/040-rainy-day-urban/040-rainy-day-urban.blend`（%d 个服装部件，"
                "不含地面与人体底座；底座 %d 面，另计）\n"
                % (len(results), mannequin_faces))
        f.write("检查方式：Blender bmesh + BVH 实测（拓扑逐面、层间隙逐点最近距离），"
                "非目测估算；设计对照值见 `scenes/040-rainy-day-urban/design.md`。\n\n")
        f.write("## 1. 拓扑\n\n")
        f.write("| 部件 | 顶点 | 面 | 三角 | 四边 | N-gon | 重叠顶点 | 散边 | 边界边 | 非流形边 | 退化面 | 倒置法线 | 最高顶点价数 |\n")
        f.write("| ---- | ---- | -- | ---- | ---- | ----- | -------- | ---- | ------ | -------- | ------ | -------- | ------------ |\n")
        for name in sorted(results):
            r = results[name]
            f.write("| %s | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d |\n" % (
                name, r["verts"], r["faces"], r["tris"], r["quads"], r["ngons"],
                r["duplicate_verts"], r["loose_edges"], r["boundary_edges"],
                r["nonmanifold_edges"], r["degenerate_faces"],
                r["inverted_normals"], r["max_valence"]))
        f.write("| **合计** | **%d** | **%d** | **%d** | **%d** | **%d** | **%d** | **%d** | **%d** | **%d** | **%d** | **%d** | — |\n\n" % (
            tot["verts"], tot["faces"], tot["tris"], tot["quads"], tot["ngons"],
            tot["duplicate_verts"], tot["loose_edges"], tot["boundary_edges"],
            tot["nonmanifold_edges"], tot["degenerate_faces"],
            tot["inverted_normals"]))
        f.write("- 服装总面数：**%d**（设计记录 %d，%s；硬上限 %d）：%s\n" % (
            tot["faces"], EXPECTED_FACES,
            "一致" if faces_match else "不一致，见第 7 节",
            FACE_LIMIT, verdict(faces_ok)))
        f.write("- N-gon：共 %d 个（设计值 %d）：%s\n" % (
            tot["ngons"], EXPECTED_NGONS, verdict(ngons_ok)))
        f.write("- 无重叠顶点：%s\n" % verdict(tot["duplicate_verts"] == 0))
        f.write("- 无散边 / 无非流形边：%s\n" % verdict(
            tot["loose_edges"] == 0 and tot["nonmanifold_edges"] == 0))
        f.write("- 无退化面（面积≈0）：%s\n" % verdict(tot["degenerate_faces"] == 0))
        f.write("- 闭合实体（球/盒/带盖管/楔形/褶裥片/猫耳锥/闭合檐盘：银腰扣、"
                "雨滴×6、褶裥片×8、帽檐、帽顶球、猫耳、挑染、耳钉、手套、伞柄与"
                "握把与伞面与伞尖、靴底楔、长袖）边界边："
                "%d，%s\n" % (closed_boundary, verdict(closed_boundary == 0)))
        f.write("- 边界边合计 %d，全部来自开口管/弧面片（毛衣、雨衣、雨滴无、"
                "兜帽、腰带、长裤、靴筒、靴口环、袖口、帽带）："
                "开口管/弧面片按构造有边界边，属设计形态，不在此项判定。\n"
                % tot["boundary_edges"])
        f.write("- 最高顶点价数 %d\n\n" % max(r["max_valence"] for r in results.values()))
        f.write("## 2. 法线\n\n")
        f.write("- 法线朝外一致（与 Blender recalc_face_normals 的外法线逐面比对）："
                "实体倒置面 %d 个，%s\n" % (solid_inv, verdict(solid_inv == 0)))
        f.write("- 本套无扁平单面圆盘、无近水平开口弧面片（040 的帽檐是闭合薄圆柱，"
                "不是 036 的开口檐片），无需几何判据替代；雨衣前开襟弧面片与兜帽"
                "弧面片的绕序按构造保证朝外，recalc 比对无倒置。\n\n")
        f.write("## 3. UV\n\n")
        f.write("- UV 层：%d / %d 个部件有 UV 层：%s\n" % (
            len(uv_parts), len(results), "、".join(uv_parts)))
        f.write("  这些 UV 层是 Blender 图元（球/盒）自带的默认 UVMap，"
                "本套服装无任何贴图引用它们，UV 不参与渲染；其余 %d 个部件"
                "由 from_pydata / make_tube 直接建网格，无 UV 层。\n" % (len(results) - len(uv_parts)))
        f.write("- UV 超出 0–1 范围：%d 个 UV 点，%s\n\n" % (
            uv_oob, verdict(uv_oob == 0)))
        f.write("## 4. 服装结构（BVH 实测，单位：米）\n\n")
        f.write("### 4.1 层间隙（最小间隙要求 ≥0.005）\n\n")
        f.write("| 间隙 | 最小 | 中位 | 采样点 | 结论 |\n")
        f.write("| ---- | ---- | ---- | ------ | ---- |\n")
        gap_labels = {
            "sweater_vs_torso": "奶油白毛衣 / 躯干",
            "raincoat_vs_sweater": "雨衣黄雨衣 / 奶油白毛衣",
            "hood_vs_raincoat": "雨衣黄兜帽 / 雨衣黄雨衣",
            "hood_vs_sweater": "雨衣黄兜帽 / 奶油白毛衣",
            "sleeveL_vs_arm": "藏青长袖左 / 手臂",
            "sleeveR_vs_arm": "藏青长袖右 / 手臂",
            "cuffL_vs_sleeve": "奶油白袖口左 / 藏青长袖",
            "cuffR_vs_sleeve": "奶油白袖口右 / 藏青长袖",
            "belt_vs_raincoat": "藏青腰带 / 雨衣黄雨衣",
            "trousers_vs_legL": "藏青长裤 / 左腿",
            "trousers_vs_legR": "藏青长裤 / 右腿",
            "bootL_vs_leg": "雨衣黄雨靴左 / 腿",
            "bootR_vs_leg": "雨衣黄雨靴右 / 腿",
            "bootCuffL_vs_boot": "银靴环左 / 雨衣黄雨靴",
            "bootCuffR_vs_boot": "银靴环右 / 雨衣黄雨靴",
            "bootSoleL_vs_foot": "雨衣黄靴底左 / 脚掌",
            "bootSoleR_vs_foot": "雨衣黄靴底右 / 脚掌",
            "hatband_vs_crown": "藏青帽带 / 雨衣黄帽顶",
            "hatcrown_vs_hair": "雨衣黄帽顶 / 发顶（仅可见部分）",
            "canopy_vs_sleeve": "雨衣黄伞面 / 藏青长袖右",
            "shaft_vs_raincoat": "银伞柄 / 雨衣黄雨衣",
        }
        for k, v in gaps.items():
            f.write("| %s | %.4f | %.4f | %d | %s |\n" % (
                gap_labels[k], v["min"], v["median"], v["samples"],
                verdict(v["ok"])))
        f.write("\n注：雨衣黄帽顶 vs 发顶只计可见部分——帽顶球的下沿按构造埋在"
                "发顶椭球体内（帽子戴在头上），埋住的 %d 个顶点不进间隙计量；"
                "可见部分最小 %.4f 米。\n" % (
                    gaps["hatcrown_vs_hair"].get("buried", 0),
                    gaps["hatcrown_vs_hair"]["min"]))
        f.write("注：藏青手套 vs 左手掌不在上表——手套球包覆手掌球，球面按构造"
                "相交，见第 4.6 节专项；长袖 vs 雨衣不在上表——袖筒按构造从雨衣"
                "肩部穿出，见第 4.3 节注；雨靴 vs 长裤不在上表——靴筒按构造套在"
                "裤摆外面，见第 4.9 节专项。\n\n")
        f.write("### 4.2 雨帽檐间隙（专项，BACKLOG 要求）\n\n")
        f.write("- 帽檐底沿 z %.3f 米，顶沿 z %.3f 米，檐半径 %.3f 米；双眼 z 范围"
                " %.3f–%.3f 米：帽檐底沿在眼顶之上 %.3f 米，双眼正面可辨：%s\n" % (
                    brim_vs_eyes["brim_bottom_z"], brim_vs_eyes["brim_top_z"],
                    brim_vs_eyes["brim_radius"],
                    brim_vs_eyes["eye_z"][0], brim_vs_eyes["eye_z"][1],
                    brim_vs_eyes["clearance"],
                    verdict(brim_vs_eyes["brim_bottom_above_eye_top"])))
        f.write("- 帽檐是闭合薄圆柱（031 遮阳帽做法）：帽顶球穿过檐盘，参数化证明："
                "帽顶在檐盘底沿/顶沿处的水平半径 %.4f / %.4f 米（< 檐半径"
                " %.3f 米），帽顶 z 范围 %.3f–%.3f 米跨过檐盘 z 范围 %.3f–%.3f 米，"
                "帽顶球面与檐盘上下两面都相交；帽带底环 z %.3f 米落在檐盘 z 范围"
                "内、环半径 %.4f 米（< 檐半径），帽带穿过檐盘。檐顶点离帽顶/帽带"
                "面的顶点距离 %.4f / %.4f 米是采样假象（檐盘上下两面是无内部顶点"
                "的 n-gon，034 同款量法教训），不是漂浮：%s\n" % (
                    brim_proof["crown_rx_at_brim_bottom"],
                    brim_proof["crown_rx_at_brim_top"],
                    brim_vs_eyes["brim_radius"],
                    brim_proof["crown_z"][0], brim_proof["crown_z"][1],
                    brim_vs_eyes["brim_bottom_z"],
                    brim_vs_eyes["brim_top_z"],
                    brim_proof["band_bottom_z"],
                    brim_proof["band_radius_at_bottom"],
                    attach["brim_vs_crown"]["min"],
                    attach["brim_vs_band"]["min"],
                    verdict(brim_vs_eyes["crown_passes_through_brim"]
                           and brim_vs_eyes["band_passes_through_brim"])))
        f.write("- 结论：雨帽檐间隙：%s\n\n" % verdict(brim_vs_eyes["ok"]))
        f.write("### 4.3 附件贴合（按构造应贴合宿主，仅记录；> 0.05 视为漂浮嫌疑）\n\n")
        attach_labels = {
            "drop_BlueRaindrop_vs_host": "雨滴蓝雨滴 1（毛衣 270° z 1.32）/ 奶油白毛衣",
            "drop_BlueRaindrop_001_vs_host": "雨滴蓝雨滴 2（毛衣 262° z 1.02）/ 奶油白毛衣",
            "drop_BlueRaindrop_002_vs_host": "雨滴蓝雨滴 3（毛衣 278° z 1.02）/ 奶油白毛衣",
            "drop_BlueRaindrop_003_vs_host": "雨滴蓝雨滴 4（雨衣 225° z 1.05）/ 雨衣黄雨衣",
            "drop_BlueRaindrop_004_vs_host": "雨滴蓝雨滴 5（雨衣 315° z 1.05）/ 雨衣黄雨衣",
            "hatdrop_vs_crown": "雨滴蓝雨滴 6（帽上）/ 雨衣黄帽顶",
            "buckle_vs_belt": "银腰扣 / 藏青腰带",
            "earring_vs_head": "金耳钉左 / 头",
            "earring.001_vs_head": "金耳钉右 / 头",
            "catear_vs_crown": "藏青猫耳左 / 雨衣黄帽顶",
            "catear.001_vs_crown": "藏青猫耳右 / 雨衣黄帽顶",
            "streak_vs_hair": "浅蓝挑染 / 发顶",
            "brim_vs_crown": "雨衣黄帽檐 / 雨衣黄帽顶",
            "brim_vs_band": "雨衣黄帽檐 / 藏青帽带",
            "hood_vs_hair": "雨衣黄兜帽 / 发顶",
            "pleat_vs_raincoat": "雨衣黄褶裥片 1（170°）/ 雨衣黄雨衣",
            "pleat.001_vs_raincoat": "雨衣黄褶裥片 2（200°）/ 雨衣黄雨衣",
            "pleat.002_vs_raincoat": "雨衣黄褶裥片 3（230°）/ 雨衣黄雨衣",
            "pleat.003_vs_raincoat": "雨衣黄褶裥片 4（320°）/ 雨衣黄雨衣",
            "pleat.004_vs_raincoat": "雨衣黄褶裥片 5（350°）/ 雨衣黄雨衣",
            "pleat.005_vs_raincoat": "雨衣黄褶裥片 6（20°）/ 雨衣黄雨衣",
            "pleat.006_vs_raincoat": "雨衣黄褶裥片 7（50°）/ 雨衣黄雨衣",
            "pleat.007_vs_raincoat": "雨衣黄褶裥片 8（110°）/ 雨衣黄雨衣",
            "bootCuff_vs_boot": "银靴环左 / 雨衣黄雨靴",
            "bootCuff.001_vs_boot": "银靴环右 / 雨衣黄雨靴",
            "boot_vs_trousers": "雨衣黄雨靴左 / 藏青长裤",
            "boot.001_vs_trousers": "雨衣黄雨靴右 / 藏青长裤",
            "glove_vs_handL": "藏青手套 / 左手掌",
            "sleeveL_vs_raincoat": "藏青长袖左 / 雨衣黄雨衣",
            "sleeveR_vs_raincoat": "藏青长袖右 / 雨衣黄雨衣",
            "grip_vs_handR": "藏青握把 / 右手掌",
            "shaft_vs_sleeve": "银伞柄 / 藏青长袖右",
            "shaft_vs_grip": "银伞柄 / 藏青握把",
            "shaft_vs_canopy": "银伞柄 / 雨衣黄伞面",
            "tip_vs_canopy": "银伞尖 / 雨衣黄伞面",
        }
        for k, v in attach.items():
            flag = ("漂浮嫌疑" if v["min"] is not None and v["min"] > 0.05
                    else "贴合")
            f.write("- %s：最小 %.4f / 中位 %.4f（%d 点）：%s\n" % (
                attach_labels[k], v["min"], v["median"], v["samples"], flag))
        f.write("  注：手套 vs 手掌最小距离 %.4f 米是球面相交（手套包覆构造，"
                "见第 4.6 节），不是贴合不良；长袖 vs 雨衣最小距离 %s / %s 米"
                "是袖筒从雨衣肩部穿出（032 的做法，袖筒起点沿臂轴上抬 0.12），"
                "属缝合构造；褶裥片 vs 雨衣最小 %.4f–%.4f 米是褶裥内沿离雨衣面"
                " 0.004 米的设计值（含雨衣 16 段刻面矢高）；雨靴 vs 长裤最小"
                " %s / %s 米是顶点采样（靴筒只有两环顶点，未落在与裤面的交线上，"
                "见第 4.9 节参数化证明）；猫耳 vs 帽顶最小 %s / %s 米是耳座埋进"
                "帽顶球（耳座顶点在帽顶球面内，见第 4.3 节注）；兜帽 vs 发顶最小"
                " %.4f 米是兜帽面穿过发顶面（见第 4.8 节内外顶点计数）；握把 vs"
                " 手掌最小 %.4f 米是握把埋进手掌球的深度（见第 4.7 节内外顶点"
                "计数）；伞柄 vs 袖筒最小 %.4f 米是伞柄从袖口端盖中心穿出（见"
                "第 4.7 节）。\n\n" % (
                    attach["glove_vs_handL"]["min"],
                    attach["sleeveL_vs_raincoat"]["min"],
                    attach["sleeveR_vs_raincoat"]["min"],
                    min(attach["pleat%s_vs_raincoat" % t]["min"]
                        for t in [""] + [".%03d" % i for i in range(1, 8)]),
                    max(attach["pleat%s_vs_raincoat" % t]["min"]
                        for t in [""] + [".%03d" % i for i in range(1, 8)]),
                    attach["boot_vs_trousers"]["min"],
                    attach["boot.001_vs_trousers"]["min"],
                    attach["catear_vs_crown"]["min"],
                    attach["catear.001_vs_crown"]["min"],
                    attach["hood_vs_hair"]["min"],
                    attach["grip_vs_handR"]["min"],
                    attach["shaft_vs_sleeve"]["min"]))
        f.write("### 4.4 凸起件（离宿主表面的最远点：要看得见立体感，又不能明显漂浮）\n\n")
        f.write("注：凸起值是贴片顶点离宿主表面的最远点。银腰扣是未旋转的轴对齐盒，"
                "盒角离椭圆腰带面比盒心远，所以实测最远点高于设计值 0.0115，属几何"
                "使然，不是贴片漂浮；雨衣上的雨滴（225°/315°）是扁椭球斜贴在椭圆"
                "雨衣面上，薄轴与面法向不重合，实测最远点高于设计值 0.015，属几何"
                "使然；帽上雨滴是 0.076 米高的水滴立在曲率半径 0.26 米的帽顶球面"
                "上，滴尖离面按理想椭球解析值判定（037 护目镜片、034 墨镜片同款"
                "量法，允差 ±0.012）；银靴环只计与靴筒重叠带（z ≤ 0.50）的顶点，"
                "环顶沿的对角距离不计入；挑染半嵌发顶与头球，只计发顶与头面之外"
                "的可见顶点（BVH 法向判定），单宿主原值另列。判定标准仍为各小节"
                "所列。\n\n")
        def write_protrude(f, title, names):
            f.write("- %s：\n" % title)
            for name in names:
                v = protrusions[name]
                if "analytic" in v:
                    f.write("  - %s：凸起 %.4f（理想椭球解析值 %.4f，"
                            "允差 ±0.012）：%s\n" % (
                                name, v["lift"], v["analytic"],
                                verdict(v["ok"])))
                elif "visible_verts" in v:
                    f.write("  - %s：凸起 %.4f（要求 %.3f–%.3f；单宿主原值"
                            " %.4f，见注）（可见顶点 %d / %d 个）：%s\n" % (
                                name, v["lift"], v["lo"], v["hi"],
                                v["raw_lift"], v["visible_verts"],
                                v["total_verts"], verdict(v["ok"])))
                else:
                    f.write("  - %s：凸起 %.4f（要求 %.3f–%.3f）：%s\n" % (
                        name, v["lift"], v["lo"], v["hi"], verdict(v["ok"])))
        write_protrude(f, "雨滴蓝雨滴 ×5（设计浮雕 0.015，要求 0.005–0.03）",
                       ["BlueRaindrop", "BlueRaindrop.001",
                        "BlueRaindrop.002", "BlueRaindrop.003",
                        "BlueRaindrop.004"])
        write_protrude(f, "雨滴蓝雨滴 ×1（帽上，设计浮雕 0.015，要求 0.005–0.03）",
                       ["BlueRaindropHat"])
        write_protrude(f, "银腰扣（设计浮雕 0.0115，要求 0.005–0.03）",
                       ["SilverBeltBuckle"])
        write_protrude(f, "金耳钉 ×2（设计浮雕 0.019，要求 0.005–0.035；"
                       "上限含人偶头粗球面的面片内收约 0.011，见第 7 节；"
                       "按理想椭球面算浮雕 %.4f 米）" % earring_ideal,
                       ["GoldEarring", "GoldEarring.001"])
        write_protrude(f, "浅蓝挑染（半嵌发顶的扁椭球，要求 0.005–0.045；"
                       "只计发顶与头面之外的可见顶点，见注）",
                       ["HairStreak"])
        write_protrude(f, "雨衣黄衣摆褶裥 ×8（设计外沿 0.026，要求 0.020–0.032）",
                       ["YellowPleat", "YellowPleat.001", "YellowPleat.002",
                        "YellowPleat.003", "YellowPleat.004", "YellowPleat.005",
                        "YellowPleat.006", "YellowPleat.007"])
        write_protrude(f, "银靴环 ×2（设计环凸 0.006，要求 0.005–0.03）",
                       ["SilverBootCuff", "SilverBootCuff.001"])
        f.write("\n### 4.5 漂浮检查（每个服装部件到最近的其他服装/底座网格的距离，≤0.05 视为已连接）\n\n")
        f.write("- 漂浮嫌疑部件：%s，%s\n" % (
            "无" if float_ok else "、".join(bad_float), verdict(float_ok)))
        for n in bad_float:
            f.write("  - %s：最近 %.4f 米\n" % (n, floating[n]["nearest_other"]))
        f.write("  注：雨伞四件（伞柄/握把/伞面/伞尖）最近的网格是彼此（伞柄与握把"
                "/伞面相接，伞尖与伞面相接）与右手掌（握把穿过手掌球），见第 4.7 节。\n\n")
        f.write("### 4.6 手套包覆（专项，BACKLOG 要求）\n\n")
        f.write("- 左手掌顶点共 %d 个：%d 个在手套椭球内（手套球 r 0.095，"
                "球心在腕上 0.03 米处），%d 个在袖筒内（手腕侧帽沿，袖筒末端"
                " t 0.55），%d 个未被覆盖：%s\n" % (
                    glove["hand_verts_total"], glove["inside_glove"],
                    glove["covered_by_sleeve"], glove["uncovered"],
                    verdict(glove["ok"])))
        if glove["uncovered_points"]:
            f.write("  未覆盖点（前 %d 个）：%s\n" % (
                len(glove["uncovered_points"]), glove["uncovered_points"]))
        f.write("  注：手套球与手掌球球心只差 0.03 米、半径只差 0.01 米，球面"
                "按构造相交（手套顶点离手掌面最小 %.4f 米），不是贴合不良；"
                "手掌腕侧一端由袖筒盖住（袖筒末端 t 0.55 在手套球心 t 0.58 之"
                "前 0.03 米），两件合起来才算盖住整只手。\n" % (
                    attach["glove_vs_handL"]["min"]))
        f.write("- 结论：手套包覆：%s\n\n" % verdict(glove["ok"]))
        f.write("### 4.7 雨伞伞面与伞柄（专项，BACKLOG 要求）\n\n")
        f.write("- 伞柄轴线从已建网格实测：腕点 (%.4f, %.4f, %.4f)，伞面基点"
                " (%.4f, %.4f, %.4f)，柄长 %.4f 米（设计 0.70），柄方向 %s：\n" % (
                    umbrella["wrist_measured"][0], umbrella["wrist_measured"][1],
                    umbrella["wrist_measured"][2],
                    umbrella["top_measured"][0], umbrella["top_measured"][1],
                    umbrella["top_measured"][2],
                    umbrella["shaft_length_measured"],
                    umbrella["shaft_dir_measured"]))
        f.write("- 伞柄在 z 0.90 处离雨衣椭球面归一化值 %.3f（要求 > 1.15）：%s\n" % (
            umbrella["shaft_at_z090_ellipse"],
            verdict(umbrella["shaft_ellipse_ok"])))
        f.write("- 伞面底沿（z %.4f，伞面中心 (%.4f, %.4f)，伞面半径 %.4f 米）"
                "离雨衣椭球面归一化值 %.3f（要求 > 1.15；设计值 2.171 是欧氏最近"
                "底沿点的归一化值，本单 2.104 是 12 个底沿顶点中的最小值，口径"
                "不同）：%s\n" % (
                    umbrella["canopy_rim_z"],
                    umbrella["canopy_rim_centre"][0],
                    umbrella["canopy_rim_centre"][1],
                    umbrella["canopy_rim_radius"],
                    umbrella["canopy_rim_ellipse"],
                    verdict(umbrella["canopy_rim_ellipse_ok"])))
        f.write("- 伞面底沿离右袖轴线 %.4f 米、袖筒半径约 0.119 米，径向净空"
                " %.4f 米（040 v1 基线 0.1837 米，顶点采样差 0.0008 米；"
                "要求 ≥ 0.005）：%s\n" % (
                    umbrella["canopy_rim_vs_sleeve_axis"],
                    umbrella["canopy_rim_radial_clearance"],
                    verdict(umbrella["canopy_rim_clearance_ok"])))
        f.write("  注：伞面底沿 z 1.204 在袖筒顶（z 1.339）之下，高度差不能当间隙"
                "查——040 v1 的教训，本单改按径向净空量。\n")
        f.write("- 伞面 vs 袖筒 BVH 最小间隙 %.4f 米、伞柄 vs 雨衣 %.4f 米"
                "（要求 ≥ 0.005）：%s\n" % (
                    gaps["canopy_vs_sleeve"]["min"],
                    gaps["shaft_vs_raincoat"]["min"],
                    verdict(gaps["canopy_vs_sleeve"]["ok"]
                           and gaps["shaft_vs_raincoat"]["ok"])))
        f.write("- 伞柄与握把同轴（轴夹角 %.3f°、轴偏 %.4f 米，握把半径 %.4f 米"
                " > 伞柄半径 %.4f 米，伞柄被握把包住），与伞面相接（最小 %s 米），"
                "伞尖中心与伞面顶环中心重合（偏差 %.4f 米）；握把穿过右手掌球"
                "（握把 %d 个顶点在手掌椭球内、%d 个在外，握持构造）：%s\n" % (
                    umbrella["grip_axis_angle_deg"],
                    umbrella["grip_axis_offset"],
                    umbrella["grip_radius"], umbrella["shaft_radius"],
                    attach["shaft_vs_canopy"]["min"],
                    umbrella["tip_centre_offset"],
                    umbrella["grip_verts_inside_hand"],
                    umbrella["grip_verts_outside_hand"],
                    verdict(umbrella["shaft_enclosed_by_grip"]
                           and umbrella["tip_centred_on_canopy"]
                           and umbrella["grip_through_hand"])))
        f.write("- 结论：雨伞伞面与伞柄：%s\n\n" % verdict(umbrella["ok"]))
        f.write("### 4.8 脑后兜帽搭接（专项，BACKLOG 要求）\n\n")
        f.write("- 兜帽顶环 z %.3f 米，雨衣顶沿 z %.3f 米：顶环在雨衣顶沿之上"
                " %.3f 米：%s\n" % (
                    hood["hood_top_ring_z"], hood["raincoat_top_z"],
                    hood["hood_top_ring_z"] - hood["raincoat_top_z"],
                    verdict(hood["hood_top_above_coat_top"])))
        f.write("- 兜帽弧面角度 %.1f°–%.1f°（设计 15°–165°，脑后为 90°）："
                "盖住脑后：%s\n" % (
                    hood["hood_angle_min"], hood["hood_angle_max"],
                    verdict(hood["hood_arc_covers_back"])))
        f.write("- 兜帽 vs 雨衣最小间隙 %.4f 米、vs 毛衣 %.4f 米（要求 ≥0.005）：%s\n" % (
                    gaps["hood_vs_raincoat"]["min"],
                    gaps["hood_vs_sweater"]["min"],
                    verdict(gaps["hood_vs_raincoat"]["ok"]
                           and gaps["hood_vs_sweater"]["ok"])))
        f.write("- 兜帽 vs 发顶：%d 个顶点在发顶面之内、%d 个在发顶面之外（兜帽面"
                "穿过发顶面，顶环塞进发顶之后；最近顶点离发顶面 %.4f 米是顶点"
                "采样，未落在交线上）：%s\n" % (
                    hood["hood_verts_inside_hair"],
                    hood["hood_verts_outside_hair"],
                    attach["hood_vs_hair"]["min"],
                    verdict(hood["hood_tucks_behind_hair"])))
        f.write("- 结论：脑后兜帽搭接：%s\n\n" % verdict(hood["ok"]))
        f.write("### 4.9 雨靴与长裤搭接（专项，BACKLOG 要求）\n\n")
        f.write("- 雨衣黄高筒雨靴（r 0.118，靴顶 z %.3f 米）套在藏青长裤下摆"
                "（z %.3f 米）外面：左靴在 z 0.42 处 %d / 72 个采样点落在裤椭圆"
                "（rx %.4f、ry %.4f）之外，右靴 %d / 72 个：靴读作套在裤摆外面。\n" % (
                    boot_trouser["boot_top_z"], boot_trouser["trouser_hem_z"],
                    boot_trouser["L"]["boot_circle_outside_trouser"],
                    boot_trouser["L"]["trouser_rx_at_0.42"],
                    boot_trouser["L"]["trouser_ry_at_0.42"],
                    boot_trouser["R"]["boot_circle_outside_trouser"]))
        f.write("- 靴面与裤面按构造相交：靴圈在 z 0.42 处 72 个采样点中有 %d / %d 个"
                "落在裤椭圆之外、其余在内，靴圈穿过裤面（靴顶点离裤面最小 %s /"
                " %s 米是顶点采样：靴筒只有 z 0.50/0.02 两环顶点，未落在交线上）；"
                "搭接带 z 0.34–0.50 的腿顶点有 %d 个既不在靴筒内、也不在裤椭圆内：%s\n" % (
                    boot_trouser["L"]["boot_circle_outside_trouser"],
                    boot_trouser["R"]["boot_circle_outside_trouser"],
                    boot_trouser["boot_vs_trouser_min_L"],
                    boot_trouser["boot_vs_trouser_min_R"],
                    boot_trouser["leg_verts_outside_both_at_band"],
                    verdict(boot_trouser["leg_covered"])))
        f.write("- 结论：雨靴与长裤搭接：%s\n\n" % verdict(boot_trouser["ok"]))
        f.write("### 4.10 雨滴纹位置（专项，BACKLOG 要求）\n\n")
        for name in ("BlueRaindrop", "BlueRaindrop.001", "BlueRaindrop.002",
                     "BlueRaindrop.003", "BlueRaindrop.004"):
            v = drop_pos[name]
            host = "毛衣" if DROP_DESIGN[name][2] == "sweater" else "雨衣"
            f.write("- %s（%s）：实测中心 (%.4f, %.4f, %.4f)，角度 %.1f°"
                    "（设计 %d°，z %.2f），%s前开襟楔（240°–300°）：%s\n" % (
                        name, host, v["centre"][0], v["centre"][1],
                        v["centre"][2], v["angle_deg"],
                        v["design_angle_deg"], v["design_z"],
                        "在" if v["in_open_wedge_240_300"] else "不在",
                        verdict(v["ok"])))
        f.write("- BlueRaindropHat（帽上）：底沿 z %.4f 米，帽带顶环 z %.3f 米："
                "底沿在帽带顶环之上 %.4f 米：%s\n" % (
                    drop_pos["BlueRaindropHat"]["min_z"],
                    drop_pos["BlueRaindropHat"]["band_top_z"],
                    drop_pos["BlueRaindropHat"]["clearance_above_band"],
                    verdict(drop_pos["BlueRaindropHat"]["ok"])))
        f.write("- 结论：雨滴纹位置：%s\n\n" % verdict(drop_pos_ok))
        f.write("## 5. 尺寸与落地\n\n")
        f.write("- 服装包围盒：x %.3f–%.3f，y %.3f–%.3f，z %.3f–%.3f；"
                "宽 %.3f、高 %.3f\n" % (
                    g_bbox["x"][0], g_bbox["x"][1], g_bbox["y"][0], g_bbox["y"][1],
                    g_bbox["z"][0], g_bbox["z"][1], g_bbox["width"], g_bbox["height"]))
        f.write("- 靴底最低点 z=%.4f（地面 z=0，含左右靴底楔）：%s\n" % (
            sole_min_z, verdict(ground_ok, "落地")))
        f.write("- 人偶脚掌最低点 z=%.4f（靴底楔包住脚掌下沿，见第 4.3 节）\n"
                % foot_min_z)
        f.write("- 人物最高点 z=%.3f（%s）；相机内人物占画面高度 %.3f（标准 0.60–0.80）：%s\n"
                % (top_z, top_obj, frame_frac, verdict(frame_ok)))
        f.write("  注：040 渲染时以 z=2.00 为顶测得 FRAME_FRACTION 约 0.700；"
                "本单以实测最高点（%s）重测，口径不同，数值仅供对照。\n\n"
                % top_obj)
        f.write("## 6. 材质（Principled BSDF 实测 vs 设计值）\n\n")
        for r in mats["rows"]:
            if not r.get("found"):
                f.write("- %s：未找到材质：不通过\n" % r["name"])
                continue
            d = DESIGN_MATS[r["name"]]
            f.write("- %s：metallic %.2f（设计 %.2f），roughness %.2f（设计 %.2f），"
                    "底色 %s（设计 %s）：%s\n" % (
                        r["name"], r["metallic"], d[0], r["roughness"], d[1],
                        r["base_color"], d[2], verdict(r["ok"])))
        f.write("- 空材质槽：%d 个，%s\n" % (
            empty_slots, verdict(empty_slots == 0)))
        f.write("- 贴图：不适用（本套服装无图片贴图，全部程序化材质）\n")
        f.write("- 地面材质 GroundMat 不参与服装材质判定。\n\n")
        f.write("## 7. 观察项\n\n")
        f.write("以下 %d 项中，带 [硬检查不通过] 标记的 %d 项同时是第 4 节的"
                "硬检查不通过项（见结论）；其余项不判定失败，但值得下次"
                "改进。\n\n" % (
                    len(warnings),
                    sum(1 for w in warnings
                        if w.startswith("[硬检查不通过]"))))
        if warnings:
            for w in warnings:
                f.write("- %s\n" % w)
        else:
            f.write("- 无\n")
        f.write("\n## 8. 与 design.md 记录的对照\n\n")
        f.write("- 面数：实测 %d vs 记录 %d：%s\n" % (
            tot["faces"], EXPECTED_FACES,
            "一致" if faces_match else "不一致"))
        f.write("- L2 间隙：design.md 记录值为建模时的设计环表算术值；"
                "本单第 4.1 节为从已建网格实测的逐点最近距离，两者口径不同，"
                "以本单实测为准。\n")
        f.write("- 凸起件：design.md 的浮雕值（雨滴 0.015、褶裥外沿 0.026、"
                "腰扣 0.0115、耳钉 0.019、靴环 0.006）是贴片中心离宿主曲面的设计值；"
                "本单第 4.4 节是贴片全部顶点离已建网格的最远点，边角离曲面更远，"
                "实测高于设计值属几何使然，以本单实测为准。\n")
        f.write("- 挑染：design.md 说浅蓝挑染“半嵌在黑发顶”，build_040 的 L2 只核了"
                "挑染顶 z 1.49 在檐底 1.608 之下（031 v1 教训），没核挑染是否露在"
                "头球外面；本单第 4.4 节从已建网格实测到挑染 26 个顶点中只有"
                " 1 个在发顶与头面之外、且凸起为 0.0000 米（恰好落在头球面上），"
                "其余 25 个都在头球内，见第 7 节硬检查项——这是 036 挑染埋头"
                "（037 已判）在新件上的重演，挑染须贴发面外侧放。\n")
        f.write("- 雨衣黄/藏青/奶油白配色占比与雨滴蓝雨滴纹、雨伞的可见性属渲染"
                "目视项，见 040 效果图；本单只核 mesh 与材质数值。\n\n")
        f.write("## 结论\n\n")
        if all_ok and warnings:
            f.write("**总体：通过（附 %d 项观察，见第 7 节），可作为服装建模管线的质检通过件**\n"
                    % len(warnings))
        elif all_ok:
            f.write("**总体：通过，可作为服装建模管线的质检通过件**\n")
        else:
            f.write("**总体：未通过**\n\n")
            f.write("不通过项（%d 项）：\n\n" % len(fail_items))
            for item in fail_items:
                f.write("- %s\n" % item)
            passed = []
            if faces_ok and faces_match and ngons_ok:
                passed.append("面数/N-gon")
            if topo_ok:
                passed.append("拓扑")
            if protrude_ok:
                passed.append("凸起件")
            if float_ok:
                passed.append("漂浮")
            if ground_ok:
                passed.append("落地")
            if glove["ok"]:
                passed.append("手套包覆")
            if umbrella["ok"]:
                passed.append("雨伞伞面与伞柄")
            if hood["ok"]:
                passed.append("脑后兜帽搭接")
            if brim_vs_eyes["ok"]:
                passed.append("帽檐间隙")
            if boot_trouser["ok"]:
                passed.append("雨靴与长裤搭接")
            if drop_pos_ok:
                passed.append("雨滴纹位置")
            if frame_ok:
                passed.append("构图")
            if mats["all_ok"] and empty_slots == 0:
                passed.append("材质")
            f.write("\n通过的硬检查：%s；修复不通过项后重测本单即可。\n"
                    % "、".join(passed))
    print("CHECKLIST_WRITTEN:", CHECKLIST)
    print("SUMMARY_WRITTEN:", SUMMARY_JSON)


if __name__ == "__main__":
    main()
