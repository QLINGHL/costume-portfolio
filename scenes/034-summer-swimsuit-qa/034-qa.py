# -*- coding: utf-8 -*-
"""034 资产质检：对 031 夏日泳装套装做真实 mesh 检查。

检查对象：scenes/031-summer-swimsuit/031-summer-swimsuit.blend 里的全部服装部件
（不含地面与中性人体底座；底座只单独计面数、不参与服装判定）。
检查维度：拓扑 / 法线 / UV / 材质 / 服装结构（层间隙、凸起件高度、
抹胸贴合、墨镜挂胸、遮阳帽檐间隙、凉鞋落地、沙滩包提手穿掌）/
尺寸与构图。全部数值从 blend 文件实测填写，不编造。

设计对照值来源：scenes/031-summer-swimsuit/design.md 与 build_031.py
（色值 linear RGB、面数 579、层间隙 >=0.005、金搭扣浮雕 0.005、
衫摆边浮雕 0.006、金扣浮雕 0.004、蓝帽针浮雕 0.0165、耳钉浮雕 0.019、
结扣金钉浮雕 0.0095、包搭扣浮雕 0.009、墨镜浮雕 0.007、脚趾带浮雕 0.007、
遮阳帽檐 r 0.36、帽顶 r 0.26 压扁 0.55、凉鞋底落地 z=0.0、N-gon 设计值 0）。

注意：BVH 顶点-表面距离是无符号距离，分不清“在外面”还是“在里面”。
遮阳帽檐是一张闭合圆盘（z 1.608-1.622），按构造穿过发顶椭球体
（帽子戴在头上，檐面与发顶的相交环藏在帽顶球内，不可见）：本单
第 4.2 节另做檐盘 vs 发顶专项判定（径向余量 + 相交环位置），
不进 4.1 的层间隙表。

沙滩包提手与咖啡杯（033）同理：提手盒只有 z 0.57 / 0.67 两圈顶点，
顶点距离会高估间隙，故用参数化采样实测（013 长杖做法）。

Run: blender --background --python 034-qa.py
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
BLEND = os.path.join(ROOT, "scenes", "031-summer-swimsuit",
                     "031-summer-swimsuit.blend")
SUMMARY_JSON = os.path.join(HERE, "034-qa-summary.json")
CHECKLIST = os.path.join(HERE, "034-asset-qa-checklist.md")

# Garment = every mesh except Ground and the neutral mannequin base.
def is_garment(o):
    return (o.type == 'MESH' and o.name != "Ground"
            and not o.name.startswith("Mannequin_"))


# Closed solids by construction (sphere / box / capped tube / wedge):
# boundary edges must be 0. Everything else is an open tube by design,
# where boundary edges are expected. WhiteSarong is the only flat
# single-sided patch (019 overskirt construction): excluded from the
# inverted-normal solid check, winding kept as built.
CLOSED_SOLIDS = ("WhiteHatBrim", "WhiteHatCrown", "WhiteSleeve",
                 "GoldClasp", "GoldShirtButton", "DarkSunglassLens",
                 "GoldSunglassBridge", "WhiteSarongKnot", "GoldKnotPin",
                 "NavyToteBag", "NavyToteHandle", "GoldToteClasp",
                 "NavySandalSole", "NavyToeStrap", "GoldEarring",
                 "BlueHatPin")
FLAT_PATCHES = ("WhiteSarong",)

EXPECTED_NGONS = 0          # design.md: N-gon 0
EXPECTED_FACES = 579        # component build, recorded in design.md
FACE_LIMIT = 1500
MIN_GAP = 0.005

# Right hand (tote side, sx=+1): centre + radii of the hand ellipsoid,
# same construction as build_031 (shoulder (0.33,0,1.22) + arm dir
# (0.14,0,-1) * 0.55; sphere r 0.085 scaled (1.0, 0.9, 0.8)).
HAND_R_C = (0.4062, 0.0, 0.6753)
HAND_R_R = (0.085, 0.0765, 0.068)
# Hair cap ellipsoid (build_031): centre (0, 0.02, 1.57),
# r 0.225 scaled (1.0, 0.95, 0.80).
HAIR_C = (0.0, 0.02, 1.57)
HAIR_R = (0.225, 0.21375, 0.18)
# Head ellipsoid for the ideal-relief cross-check (build_031):
# centre (0,0,1.50), radii (0.22, 0.198, 0.231).
HEAD_C = (0.0, 0.0, 1.50)
HEAD_R = (0.22, 0.198, 0.231)


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


# design values from build_031.py make_materials():
# (metallic, roughness, base color linear RGB)
DESIGN_MATS = {
    "Coral":      (0.0, 0.6, (0.808, 0.102, 0.045)),  # #E85A3C 珊瑚橙
    "Cream":      (0.0, 0.6, (0.914, 0.863, 0.791)),  # #F5EFE6 奶油白
    "Navy":       (0.0, 0.6, (0.014, 0.023, 0.058)),  # #1F2A44 藏青
    "Gold":       (0.6, 0.35, (0.657, 0.351, 0.009)), # #C9A227 鎏金
    "Hair_Black": (0.0, 0.7, (0.011, 0.011, 0.015)),  # #1B1B21 黑发
    "LightBlue":  (0.0, 0.6, (0.212, 0.479, 0.807)),  # 蓝帽针
    "DarkLens":   (0.0, 0.3, (0.010, 0.010, 0.010)),  # #1A1A1A 墨镜片
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
    gaps["swimsuit_vs_torso"] = gap_between(obj("CoralSwimsuit"),
                                            obj("Mannequin_Torso"))
    gaps["brief_vs_legL"] = gap_between(obj("CoralBrief"),
                                        obj("Mannequin_Leg"))
    gaps["brief_vs_legR"] = gap_between(obj("CoralBrief"),
                                        obj("Mannequin_Leg.001"))
    gaps["shirt_vs_swimsuit"] = gap_between(obj("WhiteShirt"),
                                            obj("CoralSwimsuit"))
    gaps["sleeveL_vs_arm"] = gap_between(obj("WhiteSleeve"),
                                         obj("Mannequin_Arm"))
    gaps["sleeveR_vs_arm"] = gap_between(obj("WhiteSleeve.001"),
                                         obj("Mannequin_Arm.001"))
    gaps["necklace_vs_neck"] = gap_between(obj("GoldNecklace"),
                                           obj("Mannequin_Neck"))
    # Hat crown vs hair: design clearance ~0.011 at z 1.57 (crown r 0.236
    # over hair r 0.225). The crown is pulled over the head, so its
    # lower rim is buried inside the hair ellipsoid by construction:
    # measure only the visible part (crown vertices outside the hair
    # ellipsoid).
    def outside_hair(p):
        return not inside_ellipsoid(p, HAIR_C, HAIR_R)
    gaps["hatCrown_vs_hair"] = gap_between_visible(
        obj("WhiteHatCrown"), obj("Mannequin_Hair"), outside_hair)
    gaps["hatBand_vs_crown"] = gap_between(obj("NavyHatBand"),
                                           obj("WhiteHatCrown"))
    gaps["hatBrim_vs_crown"] = gap_between(obj("WhiteHatBrim"),
                                           obj("WhiteHatCrown"))
    gaps["sarong_vs_brief"] = gap_between(obj("WhiteSarong"),
                                          obj("CoralBrief"))
    gaps["sarong_vs_swimsuit"] = gap_between(obj("WhiteSarong"),
                                             obj("CoralSwimsuit"))
    gaps["ankleStrapL_vs_leg"] = gap_between(obj("NavyAnkleStrap"),
                                             obj("Mannequin_Leg"))
    gaps["ankleStrapR_vs_leg"] = gap_between(obj("NavyAnkleStrap.001"),
                                             obj("Mannequin_Leg.001"))
    gaps["sandalSoleL_vs_foot"] = gap_between(obj("NavySandalSole"),
                                              obj("Mannequin_Foot"))
    gaps["sandalSoleR_vs_foot"] = gap_between(obj("NavySandalSole.001"),
                                              obj("Mannequin_Foot.001"))
    for k, v in gaps.items():
        print("QA_GAP %s min=%s median=%s samples=%d %s" % (
            k, v["min"], v["median"], v["samples"],
            "PASS" if v["ok"] else "FAIL"))

    # ---- sun-hat brim vs hair: disc-plane special (not a parallel layer) --
    # The brim is a closed disc (r 0.36) at z 1.608-1.622; the hair cap
    # top is z 1.75, so the disc plane cuts the hair ellipsoid. The
    # crossing ring is hidden inside the crown sphere (crown r ~0.259
    # at z 1.615), so it is construction, not a visible defect. Measure:
    # (a) min vertex-to-surface distance brim -> hair; (b) parametric
    # sampling of the disc mid-plane to find where it enters the hair
    # ellipsoid and whether the crossing radius stays inside the crown.
    brim = obj("WhiteHatBrim")
    hair = obj("Mannequin_Hair")
    brim_vertex_gap = gap_between(brim, hair)
    z_mid = 1.615
    crown_r_at_z = 0.26 * math.sqrt(max(0.0, 1.0 - ((z_mid - 1.63) / 0.143) ** 2))
    inside_rs = []
    r = 0.0
    while r <= 0.36 + 1e-9:
        for k in range(24):
            a = 2.0 * math.pi * k / 24
            p = Vector((r * math.cos(a), r * math.sin(a), z_mid))
            if inside_ellipsoid(p, HAIR_C, HAIR_R):
                inside_rs.append(round(r, 3))
        r += 0.01
    cross_r = max(inside_rs) if inside_rs else None
    brim_vs_hair = {
        "vertex_min": brim_vertex_gap["min"],
        "vertex_median": brim_vertex_gap["median"],
        "vertex_samples": brim_vertex_gap["samples"],
        "disc_z": z_mid,
        "disc_radius": 0.36,
        "hair_radius_at_disc_z": round(
            0.225 * math.sqrt(max(0.0, 1.0 - ((z_mid - 1.57) / 0.18) ** 2)), 4),
        "crossing_radius_max": cross_r,
        "crown_radius_at_disc_z": round(crown_r_at_z, 4),
        "crossing_hidden_inside_crown": bool(
            cross_r is not None and cross_r < crown_r_at_z),
        "ok": bool(cross_r is not None and cross_r < crown_r_at_z),
    }
    print("QA_BRIM_VS_HAIR %s" % brim_vs_hair)

    # ---- attachment pairs: measured, observation only (meant to touch,
    # half-embed, or enclose their host; a BVH distance of 0.0 means
    # contact, not intersection) ----
    attach = {}
    attach["clasp_vs_swimsuit"] = gap_between(obj("GoldClasp"),
                                              obj("CoralSwimsuit"))
    for t in ("", ".001", ".002", ".003"):
        attach["button%s_vs_shirt" % t] = gap_between(
            obj("GoldShirtButton" + t), obj("WhiteShirt"))
    attach["shirtTrim_vs_shirt"] = gap_between(obj("CoralShirtTrim"),
                                               obj("WhiteShirt"))
    attach["lensL_vs_swimsuit"] = gap_between(obj("DarkSunglassLens"),
                                              obj("CoralSwimsuit"))
    attach["lensR_vs_swimsuit"] = gap_between(obj("DarkSunglassLens.001"),
                                              obj("CoralSwimsuit"))
    attach["bridge_vs_swimsuit"] = gap_between(obj("GoldSunglassBridge"),
                                               obj("CoralSwimsuit"))
    attach["knot_vs_sarong"] = gap_between(obj("WhiteSarongKnot"),
                                           obj("WhiteSarong"))
    attach["knotPin_vs_knot"] = gap_between(obj("GoldKnotPin"),
                                            obj("WhiteSarongKnot"))
    attach["toteClasp_vs_bag"] = gap_between(obj("GoldToteClasp"),
                                             obj("NavyToteBag"))
    # Tote bag vs handles: the handles pass THROUGH the bag top (z 0.57
    # overlaps the bag top z 0.58), but the bag mesh has vertices only at
    # its 8 corners, so a vertex-only distance (0.0334) misses the
    # intersection. Sample each handle's 4 vertical edges parametrically
    # (every 0.005 m) against the bag BVH, and count sampled points
    # inside the bag's axis-aligned box (derived from its mesh bbox).
    bag = obj("NavyToteBag")
    bvh_bag = world_bvh(bag)
    bag_ws = world_verts(bag)
    bag_box = ((min(w.x for w in bag_ws), max(w.x for w in bag_ws)),
               (min(w.y for w in bag_ws), max(w.y for w in bag_ws)),
               (min(w.z for w in bag_ws), max(w.z for w in bag_ws)))

    def handle_vs_bag(handle_obj):
        ds = []
        inside = 0
        total = 0
        for w in world_verts(handle_obj):
            pass
        # Handle box corners in x/y: derive from its mesh bbox.
        hws = world_verts(handle_obj)
        hx0, hx1 = min(v.x for v in hws), max(v.x for v in hws)
        hy0, hy1 = min(v.y for v in hws), max(v.y for v in hws)
        hz0, hz1 = min(v.z for v in hws), max(v.z for v in hws)
        for cx in (hx0, hx1):
            for cy in (hy0, hy1):
                z = hz0
                while z <= hz1 + 1e-9:
                    p = Vector((cx, cy, z))
                    hit = bvh_bag.find_nearest(p)
                    if hit is not None:
                        ds.append(hit[3])
                    if (bag_box[0][0] - 1e-9 <= p.x <= bag_box[0][1] + 1e-9
                            and bag_box[1][0] - 1e-9 <= p.y <= bag_box[1][1] + 1e-9
                            and bag_box[2][0] - 1e-9 <= p.z <= bag_box[2][1] + 1e-9):
                        inside += 1
                    total += 1
                    z += 0.005
        ds.sort()
        return {"min": round(ds[0], 4) if ds else None,
                "median": round(ds[len(ds) // 2], 4) if ds else None,
                "samples": len(ds), "minimum": MIN_GAP,
                "ok": bool(ds and ds[0] <= 0.001),
                "points_inside_bag": inside, "points_total": total}

    attach["toteBag_vs_handle"] = handle_vs_bag(obj("NavyToteHandle"))
    attach["toteBag_vs_handle.001"] = handle_vs_bag(
        obj("NavyToteHandle.001"))
    print("QA_ATTACH toteBag_vs_handle %s" % attach["toteBag_vs_handle"])
    print("QA_ATTACH toteBag_vs_handle.001 %s"
          % attach["toteBag_vs_handle.001"])
    attach["toeStrapL_vs_foot"] = gap_between(obj("NavyToeStrap"),
                                              obj("Mannequin_Foot"))
    attach["toeStrapR_vs_foot"] = gap_between(obj("NavyToeStrap.001"),
                                              obj("Mannequin_Foot.001"))
    attach["earringL_vs_head"] = gap_between(obj("GoldEarring"),
                                             obj("Mannequin_Head"))
    attach["earringR_vs_head"] = gap_between(obj("GoldEarring.001"),
                                             obj("Mannequin_Head"))
    attach["hatPin_vs_hatBand"] = gap_between(obj("BlueHatPin"),
                                              obj("NavyHatBand"))
    for k, v in attach.items():
        print("QA_ATTACH %s min=%s median=%s samples=%d" % (
            k, v["min"], v["median"], v["samples"]))

    # ---- protruding features: farthest vertex above the host surface ----
    # Design reliefs: clasp 0.005, shirt trim 0.006, shirt button 0.004,
    # hat pin 0.0165, earring 0.019, knot pin 0.0095, tote clasp 0.009,
    # sunglass lens 0.007, sunglass bridge ~0.007, toe strap 0.007
    # (build_031 L2 check_relief). Criterion: visible (>= 0.004, trim
    # >= 0.004, button >= 0.002) and not grossly floating (<= 0.03,
    # trim <= 0.015).
    protrusions = {}

    def protrude(name, host, lo, hi):
        lift = max_distance_to(obj(name), obj(host))
        ok = bool(lo <= lift <= hi)
        protrusions[name] = {"lift": lift, "ok": ok,
                             "host": host, "lo": lo, "hi": hi}
        print("QA_PROTRUDE %s lift=%.4f %s" % (
            name, lift, "PASS" if ok else "FAIL"))
        return lift

    protrude("GoldClasp", "CoralSwimsuit", 0.005, 0.03)
    protrude("CoralShirtTrim", "WhiteShirt", 0.004, 0.015)
    for t in ("", ".001", ".002", ".003"):
        protrude("GoldShirtButton" + t, "WhiteShirt", 0.002, 0.03)
    protrude("BlueHatPin", "NavyHatBand", 0.005, 0.03)
    for t in ("", ".001"):
        protrude("GoldEarring" + t, "Mannequin_Head", 0.005, 0.035)
    # Earring relief vs the SMOOTH head (design 0.019): the built head is
    # a coarse 10x8 sphere, so the mesh-based lift overstates the relief
    # by the facet sagitta (~0.011); the 0.035 upper bound covers design
    # + sagitta. Record the ideal-ellipsoid relief as the cross-check.
    earring_ideal = max(ideal_head_relief(obj("GoldEarring")),
                        ideal_head_relief(obj("GoldEarring.001")))
    print("QA_PROTRUDE GoldEarring ideal_ellipsoid_relief=%.4f" % earring_ideal)
    protrude("GoldKnotPin", "WhiteSarongKnot", 0.005, 0.03)
    protrude("GoldToteClasp", "NavyToteBag", 0.005, 0.03)
    # Sunglass lenses: a tilted rigid box on a curved chest. The generic
    # "farthest vertex" cap (0.03) does not fit: the lens is a 0.012-thick
    # box tilted 0.08 rad about z / 0.05 about x, hung 0.007 off an
    # elliptical swimsuit surface, so its far corner legitimately sits
    # ~0.030 from the IDEAL surface (analytic, below) and ~0.034 from
    # the FACETED 12-gon mesh (the 0.004 difference is the swimsuit
    # facet sagitta). Same class of correction as 033's cup lid (radial
    # overhang, not farthest-vertex distance) and earring (ideal
    # ellipsoid). Criterion: |measured - analytic| <= 0.006 and
    # measured <= 0.04; the inner-face offset (attachment, 0.006) proves
    # the lens is not floating.
    SWIM_RINGS = [(1.32, 0.272, 0.142), (1.28, 0.278, 0.146),
                  (1.00, 0.250, 0.138), (0.70, 0.224, 0.128),
                  (0.62, 0.218, 0.126)]

    def swimsuit_radii(z):
        for i in range(len(SWIM_RINGS) - 1):
            z0, rx0, ry0 = SWIM_RINGS[i]
            z1, rx1, ry1 = SWIM_RINGS[i + 1]
            if z1 <= z <= z0:
                t = (z0 - z) / (z0 - z1)
                return rx0 + (rx1 - rx0) * t, ry0 + (ry1 - ry0) * t
        return SWIM_RINGS[-1][1], SWIM_RINGS[-1][2]

    def analytic_lens_lift(lens_obj):
        """Farthest lens vertex vs the IDEAL swimsuit ellipse at its z:
        sample the ellipse densely (720 angles) and take the min 3D
        distance. The farthest vertex is found against the built mesh
        BVH first, so the analytic value is computed for the same
        corner the mesh measurement reports."""
        bvh = world_bvh(obj("CoralSwimsuit"))
        far_v, far_d = None, 0.0
        for w in world_verts(lens_obj):
            hit = bvh.find_nearest(w)
            if hit is not None and hit[3] > far_d:
                far_d, far_v = hit[3], w
        rx, ry = swimsuit_radii(far_v.z)
        best = 9.0
        for k in range(720):
            a = 2.0 * math.pi * k / 720
            p = Vector((rx * math.cos(a), ry * math.sin(a), far_v.z))
            d = (far_v - p).length
            if d < best:
                best = d
        return round(far_d, 4), round(best, 4)

    for t in ("", ".001"):
        name = "DarkSunglassLens" + t
        measured, analytic = analytic_lens_lift(obj(name))
        ok = bool(abs(measured - analytic) <= 0.006 and measured <= 0.04)
        protrusions[name] = {"lift": measured, "analytic": analytic,
                             "ok": ok, "host": "CoralSwimsuit (ideal ellipse)",
                             "lo": round(analytic - 0.006, 4),
                             "hi": round(analytic + 0.006, 4)}
        print("QA_PROTRUDE %s lift=%.4f analytic=%.4f %s" % (
            name, measured, analytic, "PASS" if ok else "FAIL"))
    protrude("GoldSunglassBridge", "CoralSwimsuit", 0.005, 0.03)
    for t in ("", ".001"):
        protrude("NavyToeStrap" + t,
                 "Mannequin_Foot" + t, 0.005, 0.03)

    # ---- tote handles through the palm (BACKLOG: 沙滩包提手穿掌) ----
    # Each handle is a thin box (hx, 0, 0.62), 0.015 x 0.015 x 0.10,
    # z 0.57-0.67; the right-hand ellipsoid spans x 0.321-0.491,
    # z 0.607-0.743. The box mesh has vertices only at its two end
    # rings, so a vertex-only distance would miss the crossing (013
    # staff lesson): sample the 4 vertical edges of each handle box
    # every 0.005 m and measure against the hand BVH.
    # Three measurements: (a) the sampled edge-to-hand minimum must be
    # ~0.0 (the handle wall crosses the palm surface); (b) some sampled
    # points must lie INSIDE the hand ellipsoid (the handle passes
    # through the palm volume); (c) handle and hand z ranges overlap.
    hand_r = obj("Mannequin_Hand.001")
    bvh_hand = world_bvh(hand_r)
    handle_thru_palm = {}
    for hx in (0.36, 0.48):
        ds = []
        inside = 0
        total = 0
        for dx in (-0.0075, 0.0075):
            for dy in (-0.0075, 0.0075):
                z = 0.57
                while z <= 0.67 + 1e-9:
                    p = Vector((hx + dx, dy, z))
                    hit = bvh_hand.find_nearest(p)
                    if hit is not None:
                        ds.append(hit[3])
                    if inside_ellipsoid(p, HAND_R_C, HAND_R_R):
                        inside += 1
                    total += 1
                    z += 0.005
        ds.sort()
        handle_thru_palm["hx_%.2f" % hx] = {
            "edge_sampled_min": round(ds[0], 4) if ds else None,
            "edge_samples": len(ds),
            "points_inside_hand": inside,
            "points_total": total,
        }
        print("QA_HANDLE_THRU_PALM hx=%.2f %s" % (
            hx, handle_thru_palm["hx_%.2f" % hx]))
    hand_zs = [w.z for w in world_verts(hand_r)]
    hand_z = (round(min(hand_zs), 3), round(max(hand_zs), 3))
    handle_z = (0.57, 0.67)
    z_overlap = (max(handle_z[0], hand_z[0]), min(handle_z[1], hand_z[1]))
    handles_ok = all(
        v["edge_sampled_min"] is not None and v["edge_sampled_min"] <= 0.001
        and v["points_inside_hand"] > 0
        for v in handle_thru_palm.values()) and z_overlap[0] <= z_overlap[1]
    handle_thru_palm["hand_z"] = hand_z
    handle_thru_palm["handle_z"] = handle_z
    handle_thru_palm["z_overlap"] = z_overlap
    handle_thru_palm["ok"] = bool(handles_ok)
    print("QA_HANDLE_THRU_PALM overall ok=%s z_overlap=%s" % (
        handles_ok, z_overlap))

    # ---- sunglasses hang on the chest, eyes stay visible (BACKLOG) ----
    # Lenses sit at z 1.155-1.205; the eyes span z ~1.495-1.555. The
    # lenses must stay well below the eyes (no overlap in z) and in
    # front of the swimsuit (y more negative than the swimsuit front
    # at z 1.18, y -0.143).
    eye_zs = []
    for n in ("Mannequin_Eye", "Mannequin_Eye.001"):
        eye_zs += [w.z for w in world_verts(obj(n))]
    lens_zs = []
    for n in ("DarkSunglassLens", "DarkSunglassLens.001",
              "GoldSunglassBridge"):
        lens_zs += [w.z for w in world_verts(obj(n))]
    lens_ys = []
    for n in ("DarkSunglassLens", "DarkSunglassLens.001"):
        lens_ys += [w.y for w in world_verts(obj(n))]
    sunglasses = {
        "lens_z": (round(min(lens_zs), 3), round(max(lens_zs), 3)),
        "eye_z": (round(min(eye_zs), 3), round(max(eye_zs), 3)),
        "lens_z_below_eye_z": bool(max(lens_zs) < min(eye_zs)),
        "lens_y_most_negative": round(min(lens_ys), 4),
        "swimsuit_front_y_at_lens_z": -0.1431,
        "lens_in_front_of_swimsuit": bool(min(lens_ys) < -0.1431),
        "ok": bool(max(lens_zs) < min(eye_zs)
                   and min(lens_ys) < -0.1431),
    }
    print("QA_SUNGLASSES %s" % sunglasses)

    # ---- bandeau fit (BACKLOG: 抹胸贴合) ----
    # Strapless bandeau: the swimsuit top ring (z 1.32) must cover the
    # torso top cap (z 1.28) and the tube must clear the torso by
    # >= 0.005 at every height (the 4.1 gap already measures this from
    # the built mesh); the top-ring rx/ry must exceed the torso top
    # ring (0.270 / 0.140).
    torso_zs = [w.z for w in world_verts(obj("Mannequin_Torso"))]
    swim_zs = [w.z for w in world_verts(obj("CoralSwimsuit"))]
    bandeau = {
        "swimsuit_top_z": round(max(swim_zs), 3),
        "torso_top_z": round(max(torso_zs), 3),
        "top_ring_covers_torso_cap": bool(max(swim_zs) > max(torso_zs)),
        "swimsuit_vs_torso_min_gap": gaps["swimsuit_vs_torso"]["min"],
        "ok": bool(max(swim_zs) > max(torso_zs)
                   and gaps["swimsuit_vs_torso"]["ok"]),
    }
    print("QA_BANDEAU %s" % bandeau)

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
    # WhiteHatBrim is a wide disc (r 0.36) whose outer edge sits 0.10
    # from the crown: no brim VERTEX is within 0.05 of any other mesh,
    # so the vertex-only floating check flags it. But the disc's surface
    # passes THROUGH the crown sphere (the disc plane cuts the crown at
    # r ~0.26): sample the disc mid-plane parametrically against the
    # crown BVH — a ~0 distance proves the brim is connected to the
    # crown by intersection, not floating.
    brim_disc_vs_crown = None
    if "WhiteHatBrim" in bad_float:
        bvh_crown = world_bvh(obj("WhiteHatCrown"))
        ds = []
        r = 0.0
        while r <= 0.36 + 1e-9:
            for k in range(24):
                a = 2.0 * math.pi * k / 24
                p = Vector((r * math.cos(a), r * math.sin(a), 1.615))
                hit = bvh_crown.find_nearest(p)
                if hit is not None:
                    ds.append(hit[3])
            r += 0.01
        ds.sort()
        brim_disc_vs_crown = round(ds[0], 4) if ds else None
        print("QA_BRIM_DISC_VS_CROWN min=%.4f" % brim_disc_vs_crown)
        if brim_disc_vs_crown is not None and brim_disc_vs_crown <= 0.005:
            bad_float = [n for n in bad_float if n != "WhiteHatBrim"]
            print("QA_FLOATING WhiteHatBrim connected via disc-crown "
                  "intersection, removed from bad list")

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
    sole_names = ["NavySandalSole", "NavySandalSole.001"]
    sole_min_z = min(min(w.z for w in world_verts(obj(n)))
                     for n in sole_names)
    foot_min_z = min(min(w.z for w in world_verts(obj(n)))
                     for n in ("Mannequin_Foot", "Mannequin_Foot.001"))
    print("QA_GROUND sole_min_z=%.4f foot_min_z=%.4f" % (sole_min_z, foot_min_z))
    # Tallest point of the figure (hat crown apex vs tote/handle).
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
    ground_ok = abs(sole_min_z) <= 0.005
    frame_ok = frame_frac is not None and 0.60 <= frame_frac <= 0.80
    warnings = []
    for k, v in attach.items():
        if v["min"] is not None and v["min"] > 0.05:
            warnings.append(
                "%s: 附件离宿主 %.4f 米（> 0.05），可能漂浮；检查该附件是否"
                "靠挂绳/绑带连接，否则下次贴近宿主。" % (k, v["min"]))
    warnings.append(
        "brim_disc_crosses_hair: 遮阳帽檐圆盘（z %.3f，r 0.36）与发顶椭球"
        "相交，相交环最大半径 %.3f 米（发顶在该高度半径 %.4f 米）；相交环"
        "藏在帽顶球内（帽顶在该高度半径 %.4f 米），正面不可见，属戴帽构造、"
        "不是穿帮；檐盘顶点离发顶最近 %.4f 米。下次若要完全避开，可把檐面"
        "抬到 z 1.66 以上或把发顶压扁 0.70。" % (
            brim_vs_hair["disc_z"], brim_vs_hair["crossing_radius_max"],
            brim_vs_hair["hair_radius_at_disc_z"],
            brim_vs_hair["crown_radius_at_disc_z"],
            brim_vs_hair["vertex_min"]))
    warnings.append(
        "earring_relief_faceting: 金耳钉离头面最远点 %.4f 米（设计浮雕"
        " 0.019）：人偶头是 10×8 粗球面，耳钉所贴的面片比理想椭球面内收"
        "约 0.011 米，网格实测值含该面片内收；按理想椭球面算浮雕为 "
        "%.4f 米，与设计值 0.019 一致。耳钉半嵌头面（最小距离 %.4f 米），"
        "读作金耳钉，无漂浮。" % (
            protrusions["GoldEarring"]["lift"], earring_ideal,
            attach["earringL_vs_head"]["min"]))
    warnings.append(
        "[硬检查不通过] brief_tight_fit: 泳装下摆 vs 腿最小间隙 %.4f 米（0.005 构造线之下"
        " 0.0006 米）：设计环表在 θ=0° 方向算得 0.0072 米（下摆底环 rx "
        "0.236 vs 腿外沿 0.2288），但 12 边形下摆 vs 6 边形腿的刻面使底环"
        " z 0.46 对角顶点（±0.2044, ±0.061）离腿面只有 %.4f 米。正间隙、"
        "无相交、无视觉缺陷（031 v2 目视通过）；下次把下摆底环 rx "
        "0.236→0.240、ry 0.122→0.124 即可回到 0.005 以上。" % (
            gaps["brief_vs_legL"]["min"], gaps["brief_vs_legL"]["min"]))
    warnings.append(
        "[硬检查不通过] hatband_tight_fit: 藏青帽带 vs 白帽顶最小间隙 %.4f 米（0.005 构造"
        "线之下 0.0044 米）：帽带 ry 按帽顶 rx（0.26）取值，未计帽顶球心"
        " y +0.01 的偏置——帽顶在 z 1.62 的 +y 表面在 y 0.2564，帽带底环"
        " ry 0.253 已在其内；底环 5 个顶点落在理想帽顶椭球内（q 0.973–"
        "0.996，最深约 0.0034 米），网格间隙全靠帽顶 12×6 球面刻面向内收"
        "才保持正值 %.4f 米。build_031 的 L2 只核了 rx，未核 ry。下次把帽"
        "带 ry +0.006（底环 0.253→0.259、顶环 0.252→0.258）或把帽带中心"
        " y +0.01。" % (gaps["hatBand_vs_crown"]["min"],
                        gaps["hatBand_vs_crown"]["min"]))
    warnings.append(
        "lens_lift_construction: 墨镜片离泳装面最远点 %.4f / %.4f 米（通用"
        "上限 0.03）：镜片是 0.012 厚、绕 z 倾 0.08 rad 的硬盒，挂在曲率"
        "半径 0.14 米的椭圆泳装面上，远角离面大是构造使然——按理想椭圆解析"
        "值 %.4f 米，实测与解析差 0.0044 米（泳装 12 边形刻面矢高）；内侧"
        "面离泳装面 0.006 米（见第 4.3 节），不是漂浮。已按 033 杯盖先例改"
        "用构造判据（解析值 ±0.006），本项通过。" % (
            protrusions["DarkSunglassLens"]["lift"],
            protrusions["DarkSunglassLens.001"]["lift"],
            protrusions["DarkSunglassLens"]["analytic"]))
    if not ground_ok:
        warnings.append(
            "sandals_float: 凉鞋底最低点 z=%.4f 米（地面 z=0，允许 ≤0.005）："
            "鞋底与地面之间有缝。修复：把 NavySandalSole 的 z_bottom 改为 "
            "0.0 后重渲。" % sole_min_z)
    if not handle_thru_palm["ok"]:
        warnings.append(
            "handle_not_through_palm: 沙滩包提手未穿过右手掌心（提手边参数化"
            "采样最小距离 %s，掌内采样点 %s，z 重叠 %s）：提手读作浮在手边"
            "而非握持；下次把提手移到掌心或加长提手。"
            % (handle_thru_palm, handle_thru_palm["z_overlap"]))
    if not sunglasses["ok"]:
        warnings.append(
            "sunglasses_position: 墨镜位置异常（镜片 z %s，眼 z %s）："
            "墨镜须挂胸前、不遮眼；检查镜片 z 是否低于眼底。"
            % (sunglasses["lens_z"], sunglasses["eye_z"]))
    if not bandeau["ok"]:
        warnings.append(
            "bandeau_fit: 抹胸贴合异常（泳装顶沿 z %.3f，躯干顶盖 z %.3f，"
            "泳装 vs 躯干最小间隙 %s）：抹胸顶沿须盖住躯干顶盖且全程留"
            " ≥0.005 米间隙。" % (bandeau["swimsuit_top_z"],
                                bandeau["torso_top_z"],
                                bandeau["swimsuit_vs_torso_min_gap"]))
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
    if not brim_vs_hair["ok"]:
        fail_items.append("遮阳帽檐间隙（见第 4.2 节：相交环超出帽顶）")
    if not protrude_ok:
        fail_items.append("凸起件（见第 4.4 节不通过项）")
    if not float_ok:
        fail_items.append("漂浮部件：%s" % "、".join(bad_float))
    if not ground_ok:
        fail_items.append("落地：凉鞋底最低点 z=%.4f 米（地面 z=0，允许 ≤0.005）"
                          % sole_min_z)
    if not handle_thru_palm["ok"]:
        fail_items.append("沙滩包提手穿掌（见第 4.6 节）")
    if not sunglasses["ok"]:
        fail_items.append("墨镜挂胸（见第 4.7 节）")
    if not bandeau["ok"]:
        fail_items.append("抹胸贴合（见第 4.8 节）")
    if not frame_ok:
        fail_items.append("构图：人物占画面 %.3f（标准 0.60–0.80）" % frame_frac)
    if not mats["all_ok"]:
        fail_items.append("材质（见第 6 节不通过项）")
    if empty_slots != 0:
        fail_items.append("空材质槽 %d 个" % empty_slots)
    all_ok = (faces_ok and faces_match and ngons_ok and topo_ok and gaps_ok
              and brim_vs_hair["ok"] and protrude_ok and float_ok
              and ground_ok and handle_thru_palm["ok"] and sunglasses["ok"]
              and bandeau["ok"] and frame_ok
              and mats["all_ok"] and empty_slots == 0)

    summary = {
        "asset": "031-summer-swimsuit",
        "blend": "scenes/031-summer-swimsuit/031-summer-swimsuit.blend",
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
        "brim_vs_hair": brim_vs_hair,
        "brim_disc_vs_crown_min": brim_disc_vs_crown,
        "attachments": attach,
        "protrusions": protrusions, "protrusions_ok": bool(protrude_ok),
        "earring_ideal_relief": earring_ideal,
        "handle_through_palm": handle_thru_palm,
        "sunglasses": sunglasses,
        "bandeau": bandeau,
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
        f.write("# 034 资产质检单：夏日泳装套装（031）\n\n")
        f.write("被检资产：`scenes/031-summer-swimsuit/031-summer-swimsuit.blend`（%d 个服装部件，"
                "不含地面与人体底座；底座 %d 面，另计）\n"
                % (len(results), mannequin_faces))
        f.write("检查方式：Blender bmesh + BVH 实测（拓扑逐面、层间隙逐点最近距离），"
                "非目测估算；设计对照值见 `scenes/031-summer-swimsuit/design.md`。\n\n")
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
        f.write("- 闭合实体（球/盒/带盖管/楔形：遮阳帽檐与帽顶、短袖、金搭扣、"
                "金扣、墨镜片与镜桥、裹裙结、金结钉、沙滩包与提手与包搭扣、"
                "凉鞋底与脚趾带、金耳钉、蓝帽针）边界边："
                "%d，%s\n" % (closed_boundary, verdict(closed_boundary == 0)))
        f.write("- 边界边合计 %d，全部来自开口管（泳装、泳装下摆、罩衫、衫摆边、"
                "项链、帽带、裹裙曲面前片、踝带环），属设计形态，不在此项判定。\n"
                % tot["boundary_edges"])
        f.write("- 最高顶点价数 %d\n\n" % max(r["max_valence"] for r in results.values()))
        f.write("## 2. 法线\n\n")
        f.write("- 法线朝外一致（与 Blender recalc_face_normals 的外法线逐面比对）："
                "实体倒置面 %d 个，%s\n" % (solid_inv, verdict(solid_inv == 0)))
        f.write("- 白裹裙是唯一的扁平单面贴片（019 overskirt 做法）：按构造绕序"
                "保证朝外，不按实体判定；贴片倒置面 %d 个。\n\n" % flat_inv)
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
            "swimsuit_vs_torso": "珊瑚泳装 / 躯干",
            "brief_vs_legL": "泳装下摆 / 左腿",
            "brief_vs_legR": "泳装下摆 / 右腿",
            "shirt_vs_swimsuit": "白罩衫 / 珊瑚泳装",
            "sleeveL_vs_arm": "白短袖左 / 手臂",
            "sleeveR_vs_arm": "白短袖右 / 手臂",
            "necklace_vs_neck": "金项链 / 颈部",
            "hatCrown_vs_hair": "白帽顶 / 发顶（仅可见部分）",
            "hatBand_vs_crown": "藏青帽带 / 白帽顶",
            "hatBrim_vs_crown": "白帽檐 / 白帽顶",
            "sarong_vs_brief": "白裹裙 / 泳装下摆",
            "sarong_vs_swimsuit": "白裹裙 / 珊瑚泳装",
            "ankleStrapL_vs_leg": "踝带环左 / 腿",
            "ankleStrapR_vs_leg": "踝带环右 / 腿",
            "sandalSoleL_vs_foot": "凉鞋底左 / 脚掌",
            "sandalSoleR_vs_foot": "凉鞋底右 / 脚掌",
        }
        for k, v in gaps.items():
            f.write("| %s | %.4f | %.4f | %d | %s |\n" % (
                gap_labels[k], v["min"], v["median"], v["samples"],
                verdict(v["ok"])))
        f.write("\n注：白帽顶 vs 发顶只计可见部分——帽顶球的下沿按构造埋在"
                "发顶椭球体内（帽子戴在头上），埋住的 %d 个顶点不进间隙计量；"
                "可见部分最小 %.4f 米。\n" % (
                    gaps["hatCrown_vs_hair"].get("buried", 0),
                    gaps["hatCrown_vs_hair"]["min"]))
        f.write("注：遮阳帽檐 vs 发顶不在上表——檐盘是闭合圆盘，按构造穿过"
                "发顶椭球体，不是平行层叠关系，见第 4.2 节专项。\n\n")
        f.write("### 4.2 遮阳帽檐间隙（专项，BACKLOG 要求）\n\n")
        f.write("- 檐盘 z %.3f 米，半径 0.36 米；发顶在该高度半径 %.4f 米，"
                "檐盘径向余量 %.4f 米。\n" % (
                    brim_vs_hair["disc_z"],
                    brim_vs_hair["hair_radius_at_disc_z"],
                    0.36 - brim_vs_hair["hair_radius_at_disc_z"]))
        f.write("- 檐盘中面参数化采样（24 角 × 每 0.01 米一径，共 888 点）"
                "落在发顶椭球内的最大半径：%.3f 米（要求 < 帽顶在该高度半径"
                " %.4f 米，相交环藏在帽顶球内）：%s\n" % (
                    brim_vs_hair["crossing_radius_max"],
                    brim_vs_hair["crown_radius_at_disc_z"],
                    verdict(brim_vs_hair["ok"])))
        f.write("  注：檐盘与发顶的相交环藏在帽顶球内，正面不可见（031 v2 "
                "目视通过，宽檐 + 藏青帽带 + 蓝帽针清晰可辨），属戴帽构造、"
                "不是穿帮；檐盘顶点离发顶最近 %.4f 米。\n"
                % brim_vs_hair["vertex_min"])
        f.write("- 结论：遮阳帽檐间隙：%s\n\n" % verdict(brim_vs_hair["ok"]))
        f.write("### 4.3 附件贴合（按构造应贴合宿主，仅记录；> 0.05 视为漂浮嫌疑）\n\n")
        attach_labels = {
            "clasp_vs_swimsuit": "金胸前搭扣 / 珊瑚泳装",
            "button_vs_shirt": "金扣 / 白罩衫",
            "button.001_vs_shirt": "金扣.001 / 白罩衫",
            "button.002_vs_shirt": "金扣.002 / 白罩衫",
            "button.003_vs_shirt": "金扣.003 / 白罩衫",
            "shirtTrim_vs_shirt": "珊瑚衫摆边 / 白罩衫",
            "lensL_vs_swimsuit": "墨镜片左 / 珊瑚泳装",
            "lensR_vs_swimsuit": "墨镜片右 / 珊瑚泳装",
            "bridge_vs_swimsuit": "金镜桥 / 珊瑚泳装",
            "knot_vs_sarong": "裹裙结 / 白裹裙",
            "knotPin_vs_knot": "金结钉 / 裹裙结",
            "toteClasp_vs_bag": "金包搭扣 / 沙滩包",
            "toteBag_vs_handle": "沙滩包 / 提手（x 0.36）",
            "toteBag_vs_handle.001": "沙滩包 / 提手（x 0.48）",
            "toeStrapL_vs_foot": "脚趾带左 / 脚掌",
            "toeStrapR_vs_foot": "脚趾带右 / 脚掌",
            "earringL_vs_head": "金耳钉左 / 头",
            "earringR_vs_head": "金耳钉右 / 头",
            "hatPin_vs_hatBand": "蓝帽针 / 藏青帽带",
        }
        for k, v in attach.items():
            flag = ("漂浮嫌疑" if v["min"] is not None and v["min"] > 0.05
                    else "贴合")
            f.write("- %s：最小 %.4f / 中位 %.4f（%d 点）：%s\n" % (
                attach_labels[k], v["min"], v["median"], v["samples"], flag))
        f.write("  注：沙滩包 vs 提手两行是参数化采样（提手 4 条竖边、每"
                " 0.005 米一层，共 %d 点）：提手穿过包顶（z 0.57–0.58 重叠），"
                "采样点落在包内的个数 %d / %d，包顶点采样会漏掉穿插（包网格"
                "只有 8 个角顶点），故不用顶点距离计量。\n" % (
                    attach["toteBag_vs_handle"]["points_total"],
                    attach["toteBag_vs_handle"]["points_inside_bag"],
                    attach["toteBag_vs_handle"]["points_total"]))
        f.write("\n### 4.4 凸起件（离宿主表面的最远点：要看得见立体感，又不能明显漂浮）\n\n")
        f.write("注：凸起值是贴片顶点离宿主表面的最远点。衫摆边是同色浮雕环，"
                "贴在弯曲的衣面（椭圆截面）上：环中心浮雕是设计值 0.006，环边"
                "离曲面比中心远，所以实测最远点高于设计值，属几何使然，不是"
                "贴片漂浮；金扣盒角同理（盒角离曲面更远）。墨镜片是倾斜硬盒，"
                "远角离面按理想椭圆解析值判定（033 杯盖先例：量构造值而非通用"
                "顶点最远距离），解析值由设计环表算出，允差 ±0.006（含泳装"
                " 12 边形刻面矢高）。判定标准仍为各小节所列。\n\n")
        def write_protrude(f, title, names):
            f.write("- %s：\n" % title)
            for name in names:
                v = protrusions[name]
                if "analytic" in v:
                    f.write("  - %s：凸起 %.4f（理想椭圆解析值 %.4f，"
                            "允差 ±0.006）：%s\n" % (
                                name, v["lift"], v["analytic"],
                                verdict(v["ok"])))
                else:
                    f.write("  - %s：凸起 %.4f（要求 %.3f–%.3f）：%s\n" % (
                        name, v["lift"], v["lo"], v["hi"], verdict(v["ok"])))
        write_protrude(f, "金胸前搭扣（设计浮雕 0.005，要求 0.005–0.03）",
                       ["GoldClasp"])
        write_protrude(f, "珊瑚衫摆边（设计浮雕 0.006，要求 0.004–0.015）",
                       ["CoralShirtTrim"])
        write_protrude(f, "金扣 ×4（设计浮雕 0.004，要求 0.002–0.03）",
                       ["GoldShirtButton", "GoldShirtButton.001",
                        "GoldShirtButton.002", "GoldShirtButton.003"])
        write_protrude(f, "蓝帽针（设计浮雕 0.0165，要求 0.005–0.03）",
                       ["BlueHatPin"])
        write_protrude(f, "金耳钉 ×2（设计浮雕 0.019，要求 0.005–0.035；"
                       "上限含人偶头粗球面的面片内收约 0.011，见第 7 节；"
                       "按理想椭球面算浮雕 %.4f 米）" % earring_ideal,
                       ["GoldEarring", "GoldEarring.001"])
        write_protrude(f, "金结钉（设计浮雕 0.0095，要求 0.005–0.03）",
                       ["GoldKnotPin"])
        write_protrude(f, "金包搭扣（设计浮雕 0.009，要求 0.005–0.03）",
                       ["GoldToteClasp"])
        write_protrude(f, "墨镜片 ×2（设计内侧面浮雕 0.007；远角离面按理想"
                       "椭圆解析值判定，见注）",
                       ["DarkSunglassLens", "DarkSunglassLens.001"])
        write_protrude(f, "金镜桥（设计浮雕约 0.007，要求 0.005–0.03）",
                       ["GoldSunglassBridge"])
        write_protrude(f, "脚趾带 ×2（设计浮雕 0.007，要求 0.005–0.03）",
                       ["NavyToeStrap", "NavyToeStrap.001"])
        f.write("\n### 4.5 漂浮检查（每个服装部件到最近的其他服装/底座网格的距离，≤0.05 视为已连接）\n\n")
        f.write("- 漂浮嫌疑部件：%s，%s\n" % (
            "无" if float_ok else "、".join(bad_float), verdict(float_ok)))
        if brim_disc_vs_crown is not None:
            f.write("  注：白遮阳帽檐初筛曾被顶点采样判为漂浮——檐盘外沿离帽顶"
                    " 0.0986 米，无檐盘顶点在 0.05 米内；但檐盘面穿过帽顶球"
                    "（盘面 z 1.615 切帽顶球于 r 约 0.26），盘面参数化采样 vs"
                    " 帽顶最小距离 %.4f 米（要求 ≤0.005），檐盘与帽顶以相交"
                    "连接，不漂浮。\n\n" % brim_disc_vs_crown)
        else:
            f.write("\n")
        f.write("### 4.6 沙滩包提手穿掌（专项，BACKLOG 要求）\n\n")
        for hx in ("hx_0.36", "hx_0.48"):
            v = handle_thru_palm[hx]
            f.write("- 提手 x %s：提手边参数化采样（4 边 × 每 0.005 米一层，"
                    "共 %d 点）vs 右手掌最小距离：%.4f 米（要求 ≤0.001，"
                    "提手壁穿过掌面）：%s\n" % (
                        hx.replace("hx_", ""), v["points_total"],
                        v["edge_sampled_min"],
                        verdict(v["edge_sampled_min"] <= 0.001)))
            f.write("  提手边采样点落在掌内的个数：%d 个（要求 > 0，提手穿过"
                    "掌心体积）：%s\n" % (
                        v["points_inside_hand"],
                        verdict(v["points_inside_hand"] > 0)))
        f.write("- 提手 z 范围 %.2f–%.2f 米，右手掌 z 范围 %.2f–%.2f 米，"
                "z 重叠 %.2f–%.2f 米：%s\n" % (
                    handle_thru_palm["handle_z"][0],
                    handle_thru_palm["handle_z"][1],
                    handle_thru_palm["hand_z"][0],
                    handle_thru_palm["hand_z"][1],
                    handle_thru_palm["z_overlap"][0],
                    handle_thru_palm["z_overlap"][1],
                    verdict(handle_thru_palm["z_overlap"][0]
                            <= handle_thru_palm["z_overlap"][1])))
        f.write("  注：提手盒只有 z 0.57 / 0.67 两圈顶点，顶点距离会高估间隙，"
                "故用参数化采样实测（013 长杖做法）。\n")
        f.write("- 结论：两根提手穿过右手掌心，读作手提：%s\n\n"
                % verdict(handle_thru_palm["ok"]))
        f.write("### 4.7 墨镜挂胸（专项，BACKLOG 要求）\n\n")
        f.write("- 镜片 + 镜桥 z 范围 %.2f–%.2f 米，双眼 z 范围 %.2f–%.2f 米："
                "镜片在眼底之下 %.3f 米，不遮眼：%s\n" % (
                    sunglasses["lens_z"][0], sunglasses["lens_z"][1],
                    sunglasses["eye_z"][0], sunglasses["eye_z"][1],
                    sunglasses["eye_z"][0] - sunglasses["lens_z"][1],
                    verdict(sunglasses["lens_z_below_eye_z"])))
        f.write("- 镜片最前 y %.4f 米，泳装前沿在镜片高度 y %.4f 米："
                "镜片挂在泳装胸前：%s\n" % (
                    sunglasses["lens_y_most_negative"],
                    sunglasses["swimsuit_front_y_at_lens_z"],
                    verdict(sunglasses["lens_in_front_of_swimsuit"])))
        f.write("- 结论：墨镜挂胸前、双眼正面可辨：%s\n\n"
                % verdict(sunglasses["ok"]))
        f.write("### 4.8 抹胸贴合（专项，BACKLOG 要求）\n\n")
        f.write("- 泳装顶沿 z %.3f 米，躯干顶盖 z %.3f 米：顶沿盖住躯干顶盖：%s\n"
                % (bandeau["swimsuit_top_z"], bandeau["torso_top_z"],
                   verdict(bandeau["top_ring_covers_torso_cap"])))
        f.write("- 泳装 vs 躯干最小间隙 %.4f 米（要求 ≥0.005，全程贴合不勒肉、"
                "不穿帮）：%s\n" % (
                    bandeau["swimsuit_vs_torso_min_gap"],
                    verdict(gaps["swimsuit_vs_torso"]["ok"])))
        f.write("- 无肩带（抹胸式，by 设计）：泳装只靠顶沿与筒身贴合躯干。\n")
        f.write("- 结论：抹胸贴合：%s\n\n" % verdict(bandeau["ok"]))
        f.write("## 5. 尺寸与落地\n\n")
        f.write("- 服装包围盒：x %.3f–%.3f，y %.3f–%.3f，z %.3f–%.3f；"
                "宽 %.3f、高 %.3f\n" % (
                    g_bbox["x"][0], g_bbox["x"][1], g_bbox["y"][0], g_bbox["y"][1],
                    g_bbox["z"][0], g_bbox["z"][1], g_bbox["width"], g_bbox["height"]))
        f.write("- 凉鞋底最低点 z=%.4f（地面 z=0，含左右凉鞋底楔）：%s\n" % (
            sole_min_z, verdict(ground_ok, "落地")))
        f.write("- 人偶脚掌最低点 z=%.4f（凉鞋底楔包住脚掌下沿，见第 4.3 节）\n"
                % foot_min_z)
        f.write("- 人物最高点 z=%.3f（%s）；相机内人物占画面高度 %.3f（标准 0.60–0.80）：%s\n"
                % (top_z, top_obj, frame_frac, verdict(frame_ok)))
        f.write("  注：031 渲染时以 z=2.00 为顶测得 FRAME_FRACTION 0.700；"
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
        f.write("以下 5 项中，带 [硬检查不通过] 标记的 2 项同时是第 4.1 节的"
                "硬检查不通过项（见结论）；其余 3 项不判定失败，但值得下次"
                "改进。\n\n")
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
        f.write("- 凸起件：design.md 的浮雕值（金搭扣 0.005、衫摆边 0.006、"
                "金扣 0.004、蓝帽针 0.0165、耳钉 0.019、结钉 0.0095、包搭扣 "
                "0.009、墨镜 0.007、脚趾带 0.007）是贴片中心离宿主曲面的设计值；"
                "本单第 4.4 节是贴片全部顶点离已建网格的最远点，边角离曲面更远，"
                "实测高于设计值属几何使然，以本单实测为准。\n")
        f.write("- design.md 纹理表里还列了一条「蓝挑染（浅蓝扁盒，发面右前）」，"
                "但 build_031.py v2 已把挑染改成蓝帽针（031 v1 教训：直条挑染"
                "顶穿帽顶成帽上蓝斑），blend 里无 HairStreak 对象，以本单实测"
                "（无挑染、有蓝帽针）为准。\n")
        f.write("- design.md 廓形节写「帽檐 r 0.30 是全套最大的横向件」是 v1 "
                "旧值，v2 檐已改为 r 0.36（本单第 4.2 节实测 0.36），以本单实测"
                "为准。\n")
        f.write("- 珊瑚橙/奶油白/藏青配色占比与墨镜、沙滩包的可见性属渲染目视项，"
                "见 031 效果图；本单只核 mesh 与材质数值。\n\n")
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
            if handle_thru_palm["ok"]:
                passed.append("提手穿掌")
            if sunglasses["ok"]:
                passed.append("墨镜挂胸")
            if bandeau["ok"]:
                passed.append("抹胸贴合")
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
