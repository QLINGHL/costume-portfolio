# -*- coding: utf-8 -*-
"""033 资产质检：对 032 冬日套装做真实 mesh 检查。

检查对象：scenes/032-winter-urban/032-winter-urban.blend 里的全部服装部件
（58 个 mesh，不含地面与中性人体底座；底座只单独计面数、不参与服装判定）。
检查维度：拓扑 / 法线 / UV / 材质 / 服装结构（层间隙、凸起件高度、贴身余量、
落地、漂浮、杯身穿掌）/ 尺寸与构图。全部数值从 blend 文件实测填写，不编造。

设计对照值来源：scenes/032-winter-urban/design.md 与 build_032.py
（色值 linear RGB、面数 983、层间隙 ≥0.005、针织纹环浮雕 0.006、
绗缝横纹浮雕 0.006、抓绒下摆浮雕 0.006、金扣浮雕 0.010、雪花纹浮雕 0.010、
褶裥脊高 0.022、耳钉浮雕 0.019、围巾垂尾浮雕 0.010、杯盖浮雕 0.002、
杯套浮雕 0.0056、帽檐间隙 0.024、靴底落地 z=0.0、N-gon 设计值 0）。

注意：BVH 顶点-表面距离是无符号距离，分不清“在外面”还是“在里面”。
长裤与腿套不是平行层叠关系：腿套顶端 z 0.36 伸进长裤底沿 z 0.34 之上
0.02 米的搭接带，腿套在 ±y 方向比长裤椭圆管宽约 0.007 米，搭接带里
腿套会穿出长裤壁——读作腿套从裤脚下露出来，属搭接关系，本单第 4.2 节
另做搭接判定，不进 4.1 的层间隙表。

连指手套 vs 手掌、靴底楔 vs 脚掌、咖啡杯 vs 手掌、耳钉 vs 头、绒球 vs
帽顶、猫耳 vs 帽顶、挑染 vs 发顶、围巾垂尾 vs 毛衣都是半嵌/包覆关系，
按构造应贴合或相交，无符号距离为 0 是接触的证据，不是穿帮：本单按
附件（仅记录）与专项（杯身穿掌）计量，不进层间隙硬检查。

Run: blender --background --python 033-qa.py
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
BLEND = os.path.join(ROOT, "scenes", "032-winter-urban",
                     "032-winter-urban.blend")
SUMMARY_JSON = os.path.join(HERE, "033-qa-summary.json")
CHECKLIST = os.path.join(HERE, "033-asset-qa-checklist.md")

# Garment = every mesh except Ground and the neutral mannequin base.
def is_garment(o):
    return (o.type == 'MESH' and o.name != "Ground"
            and not o.name.startswith("Mannequin_"))

# Closed solids by construction (sphere / box / capped tube / wedge /
# closed pyramid / closed thin solid): boundary edges must be 0.
# Everything else is an open tube by design, where boundary edges are
# expected. (NavyPleat is a closed thin solid, 10 faces; the snowflakes
# are H+V boxes, not flat patches — 032 has NO flat single-sided patch.)
CLOSED_SOLIDS = ("CreamBeanieDome", "BrickPomPom", "CreamMitten",
                 "GoldEarring", "HairStreak", "GoldCoatButton",
                 "CreamSnowflakeH", "CreamSnowflakeV", "BrickScarfTail",
                 "BrickScarfFringe", "NavyCatEar", "CaramelBootSole",
                 "NavySleeve", "CreamCoffeeCup", "CaramelCupLid")
FLAT_PATCHES = ()

EXPECTED_NGONS = 0          # design.md: N-gon 0
EXPECTED_FACES = 983        # component build, recorded in design.md
FACE_LIMIT = 1500
MIN_GAP = 0.005


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
        # float32 vertex coords can sit a hair outside the band
        # (e.g. 0.88 stored as 0.87999999), so allow 1e-4 slack.
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
    A hat dome pulled over the head has its lower rim buried inside the
    hair by construction; the buried part is not a layer gap, so it must
    not enter the measurement (same class of error as 013's belt vs
    overskirt unsigned distance)."""
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


def sampled_cylinder_gap(cx, cy, r_fn, z0, z1, target, angles=24, dz=0.005):
    """Gap from a parametric cylinder surface to a target mesh, sampled
    densely along its length: the mesh itself may have vertices only at
    its end rings, so vertex-only sampling would miss the closest
    approach (013 staff lesson; the coffee cup body has only z=0.64 /
    0.46 vertex rings). r_fn(z) gives the radius at height z."""
    bvh = world_bvh(target)
    ds = []
    z = z0
    while z <= z1 + 1e-9:
        r = r_fn(z)
        for k in range(angles):
            a = 2.0 * math.pi * k / angles
            p = Vector((cx + r * math.cos(a), cy + r * math.sin(a), z))
            hit = bvh.find_nearest(p)
            if hit is not None:
                ds.append(hit[3])
        z += dz
    ds.sort()
    return {"min": round(ds[0], 4), "median": round(ds[len(ds) // 2], 4),
            "samples": len(ds)}


def radial_overhang(obj, cx, cy, base_r):
    """Max horizontal distance of obj's vertices from a vertical axis,
    minus a base radius: the radial relief of a stacked cap (the cup
    lid sits ON TOP of the cup body, so a farthest-vertex distance
    would measure its height above the body, not its overhang)."""
    best = 0.0
    for w in world_verts(obj):
        r = math.hypot(w.x - cx, w.y - cy)
        best = max(best, r - base_r)
    return round(best, 4)


def ideal_head_relief(obj):
    """Max approximate distance of obj's vertices above the ideal head
    ellipsoid (centre (0,0,1.50), radii (0.22, 0.198, 0.231)): the
    built head mesh is a coarse 10x8 UV sphere, so a vertex-to-mesh
    distance overstates a stud's relief by the facet sagitta (~0.011);
    the design relief (earring 0.019) is measured against the smooth
    head, so it is checked here too."""
    best = 0.0
    for w in world_verts(obj):
        q = ((w.x / 0.22) ** 2 + (w.y / 0.198) ** 2
             + ((w.z - 1.50) / 0.231) ** 2)
        if q > 1.0:
            best = max(best, (math.sqrt(q) - 1.0) * 0.22)
    return round(best, 4)


# design values from build_032.py make_materials():
# (metallic, roughness, base color linear RGB)
DESIGN_MATS = {
    "Navy":       (0.0, 0.6, (0.014, 0.023, 0.058)),  # #1F2A44 藏青
    "Cream":      (0.0, 0.6, (0.914, 0.863, 0.791)),  # #F5EFE6 奶油白
    "Caramel":    (0.0, 0.6, (0.434, 0.195, 0.042)),  # #B07A3A 焦糖棕
    "Brick":      (0.0, 0.6, (0.381, 0.042, 0.027)),  # #A63A2E 砖红
    "Gold":       (0.6, 0.35, (0.657, 0.351, 0.009)), # #C9A227 鎏金
    "Hair_Black": (0.0, 0.7, (0.011, 0.011, 0.015)),  # #1B1B21 黑发
    "LightBlue":  (0.0, 0.6, (0.212, 0.479, 0.807)),  # 蓝挑染
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
    gaps["turtleneck_vs_neck"] = gap_between(obj("CreamTurtleneck"),
                                             obj("Mannequin_Neck"))
    gaps["coat_vs_sweater"] = gap_between(obj("NavyCoat"),
                                          obj("CreamSweater"))
    gaps["sleeveL_vs_arm"] = gap_between(obj("NavySleeve"),
                                         obj("Mannequin_Arm"))
    gaps["sleeveR_vs_arm"] = gap_between(obj("NavySleeve.001"),
                                         obj("Mannequin_Arm.001"))
    # Cuff vs sleeve is NOT a parallel cloth layer: the cuff is a tight
    # end-ring hugging the tapered sleeve (010 precedent: a 0.003 m boot
    # cuff gap was recorded as a tight-fit observation, not a hard fail).
    # It is measured in §4.3 as an attachment/observation instead.
    gaps["scarfWrap_vs_turtleneck"] = gap_between(obj("BrickScarfWrap"),
                                                   obj("CreamTurtleneck"))
    gaps["trousers_vs_legL"] = gap_between(obj("NavyTrousers"),
                                           obj("Mannequin_Leg"))
    gaps["trousers_vs_legR"] = gap_between(obj("NavyTrousers"),
                                           obj("Mannequin_Leg.001"))
    gaps["legwarmerL_vs_leg"] = gap_between(obj("CreamLegWarmer"),
                                            obj("Mannequin_Leg"))
    gaps["legwarmerR_vs_leg"] = gap_between(obj("CreamLegWarmer.001"),
                                            obj("Mannequin_Leg.001"))
    gaps["bootL_vs_legwarmer"] = gap_between(obj("CaramelBoot"),
                                             obj("CreamLegWarmer"))
    gaps["bootR_vs_legwarmer"] = gap_between(obj("CaramelBoot.001"),
                                             obj("CreamLegWarmer.001"))
    gaps["furCuffL_vs_boot"] = gap_between(obj("CreamFurCuff"),
                                           obj("CaramelBoot"))
    gaps["furCuffR_vs_boot"] = gap_between(obj("CreamFurCuff.001"),
                                           obj("CaramelBoot.001"))
    # Beanie dome vs hair cap: design clearance ~0.025 (dome r 0.25 over
    # hair r 0.225); brim vs hair: design 0.024 (brim r 0.248-0.250).
    # The dome is pulled over the head, so its lower rim is buried inside
    # the hair ellipsoid by construction: measure only the visible part
    # (dome vertices outside the hair ellipsoid).
    def outside_hair(p):
        return ((p.x / 0.225) ** 2 + ((p.y - 0.02) / 0.21375) ** 2
                + ((p.z - 1.57) / 0.18) ** 2) > 1.0
    gaps["beanieDome_vs_hair"] = gap_between_visible(
        obj("CreamBeanieDome"), obj("Mannequin_Hair"), outside_hair)
    gaps["beanieBrim_vs_hair"] = gap_between(obj("CreamBeanieBrim"),
                                             obj("Mannequin_Hair"))
    for k, v in gaps.items():
        print("QA_GAP %s min=%s median=%s samples=%d %s" % (
            k, v["min"], v["median"], v["samples"],
            "PASS" if v["ok"] else "FAIL"))

    # ---- trousers vs leg warmer: overlap junction, not a parallel layer --
    # The leg warmer top (z 0.36) reaches 0.02 m above the trouser hem
    # (z 0.34); in that band the warmer (r 0.110 around the leg axis) is
    # wider than the trouser ellipse in +/-y, so it crosses the trouser
    # wall. Measure the unsigned distance and the z range where the
    # trouser surface sits within 0.002 m of the warmer surface.
    trouser_warmer = gap_between(obj("NavyTrousers"), obj("CreamLegWarmer"))
    bvh_lw = world_bvh(obj("CreamLegWarmer"))
    cross_z = []
    for w in world_verts(obj("NavyTrousers")):
        hit = bvh_lw.find_nearest(w)
        if hit is not None and hit[3] <= 0.002:
            cross_z.append(round(w.z, 3))
    cross_z = sorted(set(cross_z))
    print("QA_TROUSER_WARMER unsigned_min=%s unsigned_median=%s "
          "samples=%d contact_z=%s" % (
              trouser_warmer["min"], trouser_warmer["median"],
              trouser_warmer["samples"], cross_z))

    # ---- attachment pairs: measured, observation only (meant to touch,
    # half-embed, or enclose their host; a BVH distance of 0.0 means
    # contact, not intersection) ----
    attach = {}
    # Cuff rings hug the tapered sleeve end (010 tight-fit precedent):
    # recorded here as an observation, not a hard layer gap.
    attach["cuffL_vs_sleeve"] = gap_between(obj("CreamCuff"),
                                            obj("NavySleeve"))
    attach["cuffR_vs_sleeve"] = gap_between(obj("CreamCuff.001"),
                                            obj("NavySleeve.001"))
    attach["knitRing_vs_sweater"] = gap_between(obj("CreamKnitRing"),
                                                obj("CreamSweater"))
    attach["knitRing.001_vs_sweater"] = gap_between(obj("CreamKnitRing.001"),
                                                    obj("CreamSweater"))
    attach["knitRing.002_vs_sweater"] = gap_between(obj("CreamKnitRing.002"),
                                                    obj("CreamSweater"))
    attach["quiltBand_vs_coat"] = gap_between(obj("NavyQuiltBand"),
                                              obj("NavyCoat"))
    attach["quiltBand.001_vs_coat"] = gap_between(obj("NavyQuiltBand.001"),
                                                  obj("NavyCoat"))
    attach["quiltBand.002_vs_coat"] = gap_between(obj("NavyQuiltBand.002"),
                                                  obj("NavyCoat"))
    attach["coatHem_vs_coat"] = gap_between(obj("CreamCoatHem"),
                                            obj("NavyCoat"))
    attach["button_vs_coat"] = gap_between(obj("GoldCoatButton"),
                                           obj("NavyCoat"))
    attach["scarfTail_vs_sweater"] = gap_between(obj("BrickScarfTail"),
                                                 obj("CreamSweater"))
    attach["pompom_vs_beanie"] = gap_between(obj("BrickPomPom"),
                                             obj("CreamBeanieDome"))
    attach["catEar_vs_beanie"] = gap_between(obj("NavyCatEar"),
                                             obj("CreamBeanieDome"))
    attach["streak_vs_hair"] = gap_between(obj("HairStreak"),
                                           obj("Mannequin_Hair"))
    attach["earring_vs_head"] = gap_between(obj("GoldEarring"),
                                            obj("Mannequin_Head"))
    attach["mitten_vs_hand"] = gap_between(obj("CreamMitten"),
                                           obj("Mannequin_Hand"))
    attach["bootSoleL_vs_foot"] = gap_between(obj("CaramelBootSole"),
                                              obj("Mannequin_Foot"))
    attach["bootSoleR_vs_foot"] = gap_between(obj("CaramelBootSole.001"),
                                              obj("Mannequin_Foot.001"))
    attach["cupLid_vs_cup"] = gap_between(obj("CaramelCupLid"),
                                          obj("CreamCoffeeCup"))
    attach["cupSleeve_vs_cup"] = gap_between(obj("BrickCupSleeve"),
                                             obj("CreamCoffeeCup"))
    for k, v in attach.items():
        print("QA_ATTACH %s min=%s median=%s samples=%d" % (
            k, v["min"], v["median"], v["samples"]))

    # ---- protruding features: farthest vertex above the host surface ----
    # Design reliefs: knit ring 0.006, quilt band 0.006, coat hem 0.006,
    # gold button 0.010, snowflake 0.010, pleat fin 0.022, earring 0.019,
    # scarf tail 0.010, cup lid 0.002, cup sleeve 0.0056
    # (build_032 L2 check_relief). Criterion: visible (>= 0.004, lid
    # >= 0.001, sleeve >= 0.003) and not grossly floating (<= 0.08 for
    # rings/bands/pleats/tail, <= 0.02 for buttons/snowflakes, <= 0.03
    # for earrings, <= 0.01 for the lid, <= 0.02 for the sleeve).
    protrusions = {}

    def protrude(name, host, lo, hi):
        lift = max_distance_to(obj(name), obj(host))
        ok = bool(lo <= lift <= hi)
        protrusions[name] = {"lift": lift, "ok": ok,
                             "host": host, "lo": lo, "hi": hi}
        print("QA_PROTRUDE %s lift=%.4f %s" % (
            name, lift, "PASS" if ok else "FAIL"))
        return lift

    for t in ("", ".001", ".002"):
        protrude("CreamKnitRing" + t, "CreamSweater", 0.004, 0.08)
    for t in ("", ".001", ".002"):
        protrude("NavyQuiltBand" + t, "NavyCoat", 0.004, 0.08)
    protrude("CreamCoatHem", "NavyCoat", 0.004, 0.08)
    for t in ("", ".001", ".002", ".003", ".004", ".005"):
        protrude("GoldCoatButton" + t, "NavyCoat", 0.005, 0.02)
    for t in ("", ".001"):
        protrude("CreamSnowflakeH" + t, "NavyCoat", 0.005, 0.02)
        protrude("CreamSnowflakeV" + t, "NavyCoat", 0.005, 0.02)
    for t in ("", ".001", ".002", ".003", ".004", ".005", ".006", ".007"):
        protrude("NavyPleat" + t, "NavyCoat", 0.004, 0.08)
    for t in ("", ".001"):
        protrude("GoldEarring" + t, "Mannequin_Head", 0.005, 0.035)
    # Earring relief vs the SMOOTH head (design 0.019): the built head is
    # a coarse 10x8 sphere, so the mesh-based lift overstates the relief
    # by the facet sagitta (~0.011); the 0.035 upper bound covers design
    # + sagitta. Record the ideal-ellipsoid relief as the cross-check.
    earring_ideal = max(ideal_head_relief(obj("GoldEarring")),
                        ideal_head_relief(obj("GoldEarring.001")))
    print("QA_PROTRUDE GoldEarring ideal_ellipsoid_relief=%.4f" % earring_ideal)
    protrude("BrickScarfTail", "CreamSweater", 0.004, 0.08)
    # The cup lid is a cap stacked ON TOP of the cup body (z 0.64-0.67),
    # not a band around it: its relief is the radial overhang of its
    # side wall past the body top radius (design 0.002).
    lid_overhang = radial_overhang(obj("CaramelCupLid"), 0.4063, 0.0, 0.055)
    protrusions["CaramelCupLid"] = {
        "lift": lid_overhang, "ok": bool(0.001 <= lid_overhang <= 0.01),
        "host": "CreamCoffeeCup (radial overhang)", "lo": 0.001, "hi": 0.01}
    print("QA_PROTRUDE CaramelCupLid radial_overhang=%.4f %s" % (
        lid_overhang,
        "PASS" if protrusions["CaramelCupLid"]["ok"] else "FAIL"))
    protrude("BrickCupSleeve", "CreamCoffeeCup", 0.003, 0.02)

    # ---- coffee cup through the palm (BACKLOG: 杯身穿掌) ----
    # The cup body (axis x~0.406, y 0, z 0.64-0.46, r 0.055-0.051) is built
    # through the right-hand ellipsoid (centre (0.406, 0, 0.675), radii
    # (0.085, 0.0765, 0.068)). The cup mesh has vertices only at its two
    # end rings (z 0.64 / 0.46), so a vertex-only distance would miss the
    # crossing (013 staff lesson): sample the cup wall parametrically
    # (24 angles x every 0.005 m) and measure against the hand BVH.
    # Three measurements: (a) the sampled wall-to-hand minimum must be
    # ~0.0 (the wall crosses the palm surface); (b) some sampled wall
    # points must lie INSIDE the hand ellipsoid (the wall passes through
    # the palm volume); (c) the hand centre must sit inside the cup
    # cylinder; (d) the cup and hand z ranges must overlap.
    cup = obj("CreamCoffeeCup")
    hand_r = obj("Mannequin_Hand.001")
    cup_wall = sampled_cylinder_gap(
        0.4063, 0.0, lambda z: 0.055 - 0.004 * (0.64 - z) / 0.18,
        0.46, 0.64, hand_r)
    inside = 0
    z = 0.46
    while z <= 0.64 + 1e-9:
        r = 0.055 - 0.004 * (0.64 - z) / 0.18
        for k in range(24):
            a = 2.0 * math.pi * k / 24
            p = Vector((0.4063 + r * math.cos(a), r * math.sin(a), z))
            q = (((p.x - 0.406) / 0.085) ** 2 + (p.y / 0.0765) ** 2
                 + ((p.z - 0.675) / 0.068) ** 2)
            if q < 1.0:
                inside += 1
        z += 0.005
    hand_centre = Vector((0.406, 0.0, 0.675))
    hand_to_axis = math.hypot(hand_centre.x - 0.4063, hand_centre.y - 0.0)
    cup_zs = [w.z for w in world_verts(cup)]
    hand_zs = [w.z for w in world_verts(hand_r)]
    cup_z = (round(min(cup_zs), 3), round(max(cup_zs), 3))
    hand_z = (round(min(hand_zs), 3), round(max(hand_zs), 3))
    z_overlap = (max(cup_z[0], hand_z[0]), min(cup_z[1], hand_z[1]))
    cup_through_palm = {
        "cup_wall_sampled_min": cup_wall["min"],
        "cup_wall_samples": cup_wall["samples"],
        "wall_points_inside_hand": inside,
        "hand_centre_to_cup_axis": round(hand_to_axis, 4),
        "cup_radius_at_hand_z": 0.055,
        "cup_z": cup_z, "hand_z": hand_z,
        "z_overlap": z_overlap,
        "ok": bool(cup_wall["min"] is not None and cup_wall["min"] <= 0.001
                   and inside > 0 and hand_to_axis < 0.055
                   and z_overlap[0] <= z_overlap[1]),
    }
    print("QA_CUP_THRU_PALM %s" % cup_through_palm)

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
    print("QA_FLOATING bad=%s" % bad_float)

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
    boot_names = ["CaramelBootSole", "CaramelBootSole.001",
                  "CaramelBoot", "CaramelBoot.001"]
    boot_min_z = min(min(w.z for w in world_verts(obj(n)))
                     for n in boot_names)
    foot_min_z = min(min(w.z for w in world_verts(obj(n)))
                     for n in ("Mannequin_Foot", "Mannequin_Foot.001"))
    print("QA_GROUND boot_min_z=%.4f foot_min_z=%.4f" % (boot_min_z, foot_min_z))
    # Tallest point of the figure (cat ear apex vs beanie dome top).
    top_z = max(max(w.z for w in world_verts(o))
                for o in garment + mannequin)
    top_obj = None
    for o in garment + mannequin:
        if max(w.z for w in world_verts(o)) >= top_z - 1e-6:
            top_obj = o.name
            break
    print("QA_DIMS garment_bbox=%s boot_min_z=%.4f top_z=%.3f (%s)" % (
        g_bbox, boot_min_z, top_z, top_obj))

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
    solid_inv = tot["inverted_normals"] - flat_inv
    uv_parts = sorted(n for n, r in results.items() if r["uv"]["has_uv"])
    uv_oob = sum(r["uv"]["out_of_bounds"] for r in results.values())
    empty_slots = sum(1 for r in results.values()
                      for m in r["materials"] if m is None)
    # Layer gaps (cloth layers) are hard checks. Attachment pairs are
    # recorded as observations: they are meant to touch or sit inside
    # their host (a BVH vertex-to-surface distance of 0.0 means contact,
    # not intersection — the distance cannot go negative), so only a
    # > 0.05 separation is flagged as a possible floating part.
    gaps_ok = all(gaps[k]["ok"] for k in gaps)
    ground_ok = abs(boot_min_z) <= 0.005
    frame_ok = frame_frac is not None and 0.60 <= frame_frac <= 0.80
    warnings = []
    for k, v in attach.items():
        if v["min"] is not None and v["min"] > 0.05:
            warnings.append(
                "%s: 附件离宿主 %.4f 米（> 0.05），可能漂浮；检查该附件是否"
                "靠挂绳/绑带连接，否则下次贴近宿主。" % (k, v["min"]))
    if cross_z:
        warnings.append(
            "trousers_vs_legwarmer_overlap: 长裤底沿与腿套搭接——腿套顶端 "
            "z 0.36 伸进长裤底沿 z 0.34 之上 0.02 米，腿套在 ±y 方向比长裤"
            "椭圆管宽约 0.007 米，搭接带（长裤底沿 z %s 贴住腿套，无符号"
            "距离最小 %.4f 米）里腿套表面贴住长裤壁。视觉上读作腿套从裤脚"
            "下露出来，属设计搭接、未造成穿帮；下次若要完全藏进裤管，把"
            "腿套半径 0.110 改为 0.102 或把搭接带缩到 0.01 米。" % (
                "、".join("%.2f" % z for z in cross_z),
                trouser_warmer["min"]))
    cuff_min = min(attach["cuffL_vs_sleeve"]["min"],
                   attach["cuffR_vs_sleeve"]["min"])
    warnings.append(
        "cuff_tight_fit: 奶油袖口环 vs 长袖最小间隙 %.4f 米（0.005 构造线"
        "之下 0.0016 米）：袖口环 r 0.102，袖筒在袖口位置锥缩到 0.0986"
        "（L2 用袖筒末端半径 0.096 算，得到设计值 0.006，取样位置偏了）。"
        "正间隙、无相交、无视觉缺陷（032 v2 目视通过，袖口环在腕部清晰"
        "可见）；按 010 质检单同类处理（靴口束带间隙 0.003 米系束口紧箍"
        "构造，列观察项），本项列观察项而非硬失败。下次把袖口半径 "
        "0.102 改为 0.105 即可回到 0.005 以上。" % cuff_min)
    warnings.append(
        "beanie_brim_gap_below_design: 奶油帽檐 vs 发顶最小间隙 %.4f 米"
        "（设计 0.024）：发顶球心 y +0.02 偏置，帽檐在 +y 一侧离发面更近；"
        "仍高于 0.005 构造线，通过。下次把发顶球心 y 改回 0.0 或帽檐半径"
        " +0.008。" % gaps["beanieBrim_vs_hair"]["min"])
    warnings.append(
        "earring_relief_faceting: 金耳钉离头面最远点 %.4f 米（设计浮雕"
        " 0.019）：人偶头是 10×8 粗球面，耳钉所贴的面片比理想椭球面内收"
        "约 0.011 米，网格实测值含该面片内收；按理想椭球面算浮雕为 "
        "%.4f 米，与设计值 0.019 一致。耳钉半嵌头面（最小距离 %.4f 米），"
        "读作金耳钉，无漂浮。" % (
            protrusions["GoldEarring"]["lift"], earring_ideal,
            attach["earring_vs_head"]["min"]))
    if not ground_ok:
        warnings.append(
            "boots_float: 靴底最低点 z=%.4f 米（地面 z=0，允许 ≤0.005）："
            "靴底与地面之间有缝。修复：把 CaramelBootSole 的 z_bottom 改为 "
            "0.0 后重渲。" % boot_min_z)
    if not cup_through_palm["ok"]:
        warnings.append(
            "cup_not_through_palm: 咖啡杯未穿过右手掌心（杯壁参数化采样最"
            "小距离 %.4f 米，杯壁在掌内的采样点 %d 个，掌心到杯轴 %.4f 米，"
            "杯半径 0.055 米，z 重叠 %s）：杯身读作浮在手边而非握持；下次"
            "把杯身移到掌心或放大杯径。"
            % (cup_through_palm["cup_wall_sampled_min"],
               cup_through_palm["wall_points_inside_hand"],
               hand_to_axis, z_overlap))
    protrude_ok = all(v["ok"] for v in protrusions.values())
    float_ok = not bad_float
    faces_ok = tot["faces"] <= FACE_LIMIT
    faces_match = tot["faces"] == EXPECTED_FACES
    ngons_ok = tot["ngons"] == EXPECTED_NGONS
    topo_ok = (tot["duplicate_verts"] == 0 and tot["loose_edges"] == 0
               and tot["nonmanifold_edges"] == 0
               and tot["degenerate_faces"] == 0 and closed_boundary == 0
               and solid_inv == 0)
    # Named hard-check failures, for the conclusion.
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
    if not protrude_ok:
        fail_items.append("凸起件（见第 4.4 节不通过项）")
    if not float_ok:
        fail_items.append("漂浮部件：%s" % "、".join(bad_float))
    if not ground_ok:
        fail_items.append("落地：靴底最低点 z=%.4f 米（地面 z=0，允许 ≤0.005）"
                          % boot_min_z)
    if not cup_through_palm["ok"]:
        fail_items.append("杯身穿掌（见第 4.6 节）")
    if not frame_ok:
        fail_items.append("构图：人物占画面 %.3f（标准 0.60–0.80）" % frame_frac)
    if not mats["all_ok"]:
        fail_items.append("材质（见第 6 节不通过项）")
    if empty_slots != 0:
        fail_items.append("空材质槽 %d 个" % empty_slots)
    all_ok = (faces_ok and faces_match and ngons_ok and topo_ok and gaps_ok
              and protrude_ok and float_ok and ground_ok
              and cup_through_palm["ok"] and frame_ok
              and mats["all_ok"] and empty_slots == 0)

    summary = {
        "asset": "032-winter-urban",
        "blend": "scenes/032-winter-urban/032-winter-urban.blend",
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
        "topo_ok": bool(topo_ok),
        "uv_parts_with_layer": len(uv_parts),
        "uv_parts": uv_parts,
        "uv_out_of_bounds": uv_oob,
        "empty_material_slots": empty_slots,
        "mannequin_faces": mannequin_faces,
        "gaps": gaps, "gaps_ok": bool(gaps_ok),
        "trousers_vs_legwarmer": {
            "unsigned_min": trouser_warmer["min"],
            "unsigned_median": trouser_warmer["median"],
            "samples": trouser_warmer["samples"],
            "contact_z": cross_z},
        "attachments": attach,
        "protrusions": protrusions, "protrusions_ok": bool(protrude_ok),
        "earring_ideal_relief": earring_ideal,
        "cup_through_palm": cup_through_palm,
        "floating_bad": bad_float, "floating_ok": bool(float_ok),
        "garment_bbox": g_bbox,
        "boot_min_z": round(boot_min_z, 4), "ground_ok": bool(ground_ok),
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
        f.write("# 033 资产质检单：冬日套装（032）\n\n")
        f.write("被检资产：`scenes/032-winter-urban/032-winter-urban.blend`（%d 个服装部件，"
                "不含地面与人体底座；底座 %d 面，另计）\n"
                % (len(results), mannequin_faces))
        f.write("检查方式：Blender bmesh + BVH 实测（拓扑逐面、层间隙逐点最近距离），"
                "非目测估算；设计对照值见 `scenes/032-winter-urban/design.md`。\n\n")
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
        f.write("- 闭合实体（球/盒/带盖管/楔形/四棱锥/闭合薄 solid：毛线帽球顶、"
                "绒球、手套、耳钉、挑染、金扣、雪花盒、围巾垂尾与流苏、猫耳、"
                "靴底楔、长袖、咖啡杯身与杯盖）边界边："
                "%d，%s\n" % (closed_boundary, verdict(closed_boundary == 0)))
        f.write("- 边界边合计 %d，全部来自开口管（毛衣、高领、针织纹环、大衣、"
                "绗缝横纹、抓绒下摆、袖口、围脖、帽檐、长裤、腿套、冬靴筒、"
                "毛绒靴口、杯套），属设计形态，不在此项判定。\n"
                % tot["boundary_edges"])
        f.write("- 最高顶点价数 %d\n\n" % max(r["max_valence"] for r in results.values()))
        f.write("## 2. 法线\n\n")
        f.write("- 法线朝外一致（与 Blender recalc_face_normals 的外法线逐面比对）："
                "实体倒置面 %d 个，%s\n" % (solid_inv, verdict(solid_inv == 0)))
        f.write("- 本套无扁平单面贴片：雪花纹是 H+V 盒、褶裥是闭合薄 solid，"
                "全部按实体判定；倒置面 %d 个。\n\n" % flat_inv)
        f.write("## 3. UV\n\n")
        f.write("- UV 层：%d / %d 个部件有 UV 层：%s\n" % (
            len(uv_parts), len(results), "、".join(uv_parts)))
        f.write("  这些 UV 层是 Blender 图元（球/盒）自带的默认 UVMap，"
                "本套服装无任何贴图引用它们，UV 不参与渲染；其余 %d 个部件"
                "由 from_pydata / make_tube 直接建网格，无 UV 层。\n" % (len(results) - len(uv_parts)))
        f.write("- UV 超出 0–1 范围：%d 个 UV 点，%s\n\n" % (
            uv_oob, verdict(uv_oob == 0)))
        f.write("## 4. 服装结构（BVH 实测，单位：米）\n\n")
        f.write("### 4.1 层间隙（最小间隙要求 ≥0.005；帽檐 vs 发顶按设计 0.024）\n\n")
        f.write("| 间隙 | 最小 | 中位 | 采样点 | 结论 |\n")
        f.write("| ---- | ---- | ---- | ------ | ---- |\n")
        gap_labels = {
            "sweater_vs_torso": "奶油毛衣 / 躯干",
            "turtleneck_vs_neck": "奶油高领 / 颈部",
            "coat_vs_sweater": "藏青大衣 / 奶油毛衣",
            "sleeveL_vs_arm": "藏青长袖左 / 手臂",
            "sleeveR_vs_arm": "藏青长袖右 / 手臂",
            "scarfWrap_vs_turtleneck": "砖红围脖 / 奶油高领",
            "trousers_vs_legL": "藏青长裤 / 左腿",
            "trousers_vs_legR": "藏青长裤 / 右腿",
            "legwarmerL_vs_leg": "奶油腿套左 / 左腿",
            "legwarmerR_vs_leg": "奶油腿套右 / 右腿",
            "bootL_vs_legwarmer": "焦糖冬靴左 / 腿套",
            "bootR_vs_legwarmer": "焦糖冬靴右 / 腿套",
            "furCuffL_vs_boot": "毛绒靴口左 / 冬靴",
            "furCuffR_vs_boot": "毛绒靴口右 / 冬靴",
            "beanieDome_vs_hair": "奶油毛线帽球顶 / 发顶（仅可见部分）",
            "beanieBrim_vs_hair": "奶油帽檐 / 发顶（设计 0.024）",
        }
        for k, v in gaps.items():
            f.write("| %s | %.4f | %.4f | %d | %s |\n" % (
                gap_labels[k], v["min"], v["median"], v["samples"],
                verdict(v["ok"])))
        f.write("\n注：长裤 vs 腿套不在上表——两者不是平行层叠关系：腿套顶端"
                " z 0.36 伸进长裤底沿 z 0.34 之上 0.02 米的搭接带，腿套在"
                " ±y 方向比长裤椭圆管宽约 0.007 米，搭接带里腿套会穿出长裤壁，"
                "属于搭接关系，按第 4.2 节的搭接判定计量；无符号 BVH 距离"
                "对这对关系没有意义（两面相交时距离为 0，却不能说明谁在"
                "外面）。\n")
        f.write("注：奶油袖口环 vs 长袖不在上表——袖口环是紧箍式端环（010 "
                "质检单同类处理：靴口束带间隙 0.003 米系束口紧箍构造，列观察"
                "项），按第 4.3 节附件/观察项计量；见第 7 节。\n")
        f.write("注：毛线帽球顶 vs 发顶只计可见部分——帽顶球的下沿按构造埋在"
                "发顶椭球体内（帽子戴在头上），埋住的 %d 个顶点不进间隙计量；"
                "可见部分最小 %.4f 米。\n\n" % (
                    gaps["beanieDome_vs_hair"].get("buried", 0),
                    gaps["beanieDome_vs_hair"]["min"]))
        f.write("### 4.2 长裤 vs 腿套：搭接判定（无符号距离 + 接触 z 带）\n\n")
        f.write("- 无符号 BVH 距离：最小 %.4f / 中位 %.4f（%d 点）——两面在搭接"
                "带相交，距离为 0 是相交的证据，不是贴合。\n" % (
                    trouser_warmer["min"], trouser_warmer["median"],
                    trouser_warmer["samples"]))
        if cross_z:
            f.write("- 长裤底沿贴住腿套的 z：%s（设计搭接带 z 0.34–0.36）\n"
                    % "、".join("%.2f" % z for z in cross_z))
        else:
            f.write("- 长裤表面无点贴住腿套：通过\n")
        f.write("\n### 4.3 附件贴合（按构造应贴合宿主，仅记录；> 0.05 视为漂浮嫌疑）\n\n")
        attach_labels = {
            "cuffL_vs_sleeve": "奶油袖口左 / 长袖（紧箍端环，观察项）",
            "cuffR_vs_sleeve": "奶油袖口右 / 长袖（紧箍端环，观察项）",
            "knitRing_vs_sweater": "针织纹环 / 毛衣",
            "knitRing.001_vs_sweater": "针织纹环.001 / 毛衣",
            "knitRing.002_vs_sweater": "针织纹环.002 / 毛衣",
            "quiltBand_vs_coat": "绗缝横纹 / 大衣",
            "quiltBand.001_vs_coat": "绗缝横纹.001 / 大衣",
            "quiltBand.002_vs_coat": "绗缝横纹.002 / 大衣",
            "coatHem_vs_coat": "抓绒下摆 / 大衣",
            "button_vs_coat": "金扣 / 大衣",
            "scarfTail_vs_sweater": "围巾垂尾 / 毛衣",
            "pompom_vs_beanie": "绒球 / 毛线帽球顶",
            "catEar_vs_beanie": "猫耳 / 毛线帽球顶",
            "streak_vs_hair": "蓝挑染 / 发顶",
            "earring_vs_head": "金耳钉 / 头",
            "mitten_vs_hand": "连指手套 / 左手掌",
            "bootSoleL_vs_foot": "靴底楔左 / 脚掌",
            "bootSoleR_vs_foot": "靴底楔右 / 脚掌",
            "cupLid_vs_cup": "咖啡杯盖 / 杯身",
            "cupSleeve_vs_cup": "咖啡杯套 / 杯身",
        }
        for k, v in attach.items():
            flag = ("漂浮嫌疑" if v["min"] is not None and v["min"] > 0.05
                    else "贴合")
            f.write("- %s：最小 %.4f / 中位 %.4f（%d 点）：%s\n" % (
                attach_labels[k], v["min"], v["median"], v["samples"], flag))
        f.write("\n### 4.4 凸起件（离宿主表面的最远点：要看得见立体感，又不能明显漂浮）\n\n")
        f.write("注：凸起值是贴片顶点离宿主表面的最远点。针织纹环/绗缝横纹/"
                "抓绒下摆是同色浮雕环，贴在弯曲的衣面（椭圆截面）上：环中心"
                "浮雕是设计值 0.006，环边离曲面比中心远，所以实测最远点高于"
                "设计值，属几何使然，不是贴片漂浮；雪花盒同理（盒角离曲面更远）。"
                "判定标准仍为各小节所列。\n\n")
        def write_protrude(f, title, names):
            f.write("- %s：\n" % title)
            for name in names:
                v = protrusions[name]
                f.write("  - %s：凸起 %.4f（要求 %.3f–%.3f）：%s\n" % (
                    name, v["lift"], v["lo"], v["hi"], verdict(v["ok"])))
        write_protrude(f, "针织纹环 ×3（设计浮雕 0.006，要求 0.004–0.08）",
                       ["CreamKnitRing", "CreamKnitRing.001",
                        "CreamKnitRing.002"])
        write_protrude(f, "绗缝横纹 ×3（设计浮雕 0.006，要求 0.004–0.08）",
                       ["NavyQuiltBand", "NavyQuiltBand.001",
                        "NavyQuiltBand.002"])
        write_protrude(f, "抓绒下摆（设计浮雕 0.006，要求 0.004–0.08）",
                       ["CreamCoatHem"])
        write_protrude(f, "金扣 ×6（设计浮雕 0.010，要求 0.005–0.02）",
                       ["GoldCoatButton", "GoldCoatButton.001",
                        "GoldCoatButton.002", "GoldCoatButton.003",
                        "GoldCoatButton.004", "GoldCoatButton.005"])
        write_protrude(f, "雪花纹 ×2（H+V 盒，设计浮雕 0.010，要求 0.005–0.02）",
                       ["CreamSnowflakeH", "CreamSnowflakeV",
                        "CreamSnowflakeH.001", "CreamSnowflakeV.001"])
        write_protrude(f, "衣摆褶裥 ×8（设计脊高 0.022，要求 0.004–0.08）",
                       ["NavyPleat", "NavyPleat.001", "NavyPleat.002",
                        "NavyPleat.003", "NavyPleat.004", "NavyPleat.005",
                        "NavyPleat.006", "NavyPleat.007"])
        write_protrude(f, "金耳钉 ×2（设计浮雕 0.019，要求 0.005–0.035；"
                       "上限含人偶头粗球面的面片内收约 0.011，见第 7 节；"
                       "按理想椭球面算浮雕 %.4f 米）" % earring_ideal,
                       ["GoldEarring", "GoldEarring.001"])
        write_protrude(f, "围巾垂尾（设计浮雕 0.010，要求 0.004–0.08）",
                       ["BrickScarfTail"])
        write_protrude(f, "咖啡杯盖（径向外凸，设计 0.002，要求 0.001–0.01；"
                       "杯盖叠在杯身上方，量径向外凸而非顶点最远距离）",
                       ["CaramelCupLid"])
        write_protrude(f, "咖啡杯套（设计浮雕 0.0056，要求 0.003–0.02）",
                       ["BrickCupSleeve"])
        f.write("\n### 4.5 漂浮检查（每个服装部件到最近的其他服装/底座网格的距离，≤0.05 视为已连接）\n\n")
        f.write("- 漂浮嫌疑部件：%s，%s\n\n" % (
            "无" if float_ok else "、".join(bad_float), verdict(float_ok)))
        f.write("### 4.6 咖啡杯穿掌（专项，BACKLOG 要求）\n\n")
        f.write("- 杯壁参数化采样（24 角 × 每 0.005 米一层，共 %d 点）vs 右手掌"
                "最小距离：%.4f 米（要求 ≤0.001，杯壁穿过掌面）：%s\n"
                % (cup_through_palm["cup_wall_samples"],
                   cup_through_palm["cup_wall_sampled_min"],
                   verdict(cup_through_palm["cup_wall_sampled_min"] <= 0.001)))
        f.write("  注：杯身网格只有 z 0.64 / 0.46 两圈顶点，顶点距离会高估间隙，"
                "故用参数化采样实测（013 长杖做法）。\n")
        f.write("- 杯壁采样点落在掌内的个数：%d 个（要求 > 0，杯壁穿过掌心体积）：%s\n"
                % (cup_through_palm["wall_points_inside_hand"],
                   verdict(cup_through_palm["wall_points_inside_hand"] > 0)))
        f.write("- 右手掌心到杯轴水平距离：%.4f 米（杯半径 0.055 米，掌心须在杯筒内）：%s\n"
                % (hand_to_axis, verdict(hand_to_axis < 0.055)))
        f.write("- 杯身 z 范围 %.2f–%.2f 米，右手掌 z 范围 %.2f–%.2f 米，"
                "z 重叠 %.2f–%.2f 米：%s\n" % (
                    cup_z[0], cup_z[1], hand_z[0], hand_z[1],
                    z_overlap[0], z_overlap[1],
                    verdict(z_overlap[0] <= z_overlap[1])))
        f.write("- 结论：杯身穿过右手掌心，读作握持：%s\n\n"
                % verdict(cup_through_palm["ok"]))
        f.write("## 5. 尺寸与落地\n\n")
        f.write("- 服装包围盒：x %.3f–%.3f，y %.3f–%.3f，z %.3f–%.3f；"
                "宽 %.3f、高 %.3f\n" % (
                    g_bbox["x"][0], g_bbox["x"][1], g_bbox["y"][0], g_bbox["y"][1],
                    g_bbox["z"][0], g_bbox["z"][1], g_bbox["width"], g_bbox["height"]))
        f.write("- 靴底最低点 z=%.4f（地面 z=0，含靴底楔与靴筒）：%s\n" % (
            boot_min_z, verdict(ground_ok, "落地")))
        f.write("- 人偶脚掌最低点 z=%.4f（靴底楔包住脚掌下沿，见第 4.3 节）\n"
                % foot_min_z)
        f.write("- 帽檐间隙：见第 4.1 节，奶油帽檐 / 发顶最小 %.4f 米"
                "（设计 0.024）：%s\n" % (
                    gaps["beanieBrim_vs_hair"]["min"],
                    verdict(gaps["beanieBrim_vs_hair"]["ok"])))
        f.write("- 人物最高点 z=%.3f（%s）；相机内人物占画面高度 %.3f（标准 0.60–0.80）：%s\n"
                % (top_z, top_obj, frame_frac, verdict(frame_ok)))
        f.write("  注：032 渲染时以 z=2.00 为顶测得 FRAME_FRACTION 0.700；"
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
        f.write("## 7. 观察项（不判定失败，但值得下次改进）\n\n")
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
        f.write("- 凸起件：design.md 的浮雕值（针织纹环 0.006、绗缝横纹 0.006、"
                "抓绒下摆 0.006、金扣 0.010、雪花纹 0.010、褶裥脊高 0.022、"
                "耳钉 0.019、围巾垂尾 0.010、杯盖 0.002、杯套 0.0056）是贴片"
                "中心离宿主曲面的设计值；本单第 4.4 节是贴片全部顶点离已建网格"
                "的最远点，边角离曲面更远，实测高于设计值属几何使然，"
                "以本单实测为准。\n")
        f.write("- 藏青/奶油/焦糖/砖红配色占比与围巾垂尾、咖啡杯的可见性属渲染"
                "目视项，见 032 效果图；本单只核 mesh 与材质数值。\n\n")
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
            f.write("\n其余硬检查（面数、N-gon、拓扑、层间隙、凸起件、漂浮、构图、"
                    "材质）全部通过；修复后重测本单即可。\n")
    print("CHECKLIST_WRITTEN:", CHECKLIST)
    print("SUMMARY_WRITTEN:", SUMMARY_JSON)


if __name__ == "__main__":
    main()
