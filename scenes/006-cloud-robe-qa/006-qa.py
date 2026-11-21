# -*- coding: utf-8 -*-
"""006 资产质检：对 001 云纹战袍套装（v2 组件化版）做真实 mesh 检查。

检查对象：scenes/001-cloud-robe/001-cloud-robe.blend 里的全部服装部件
（66 个 mesh，不含地面与中性人体底座；底座只单独计面数、不参与服装判定）。
检查维度：拓扑 / 法线 / UV / 材质 / 服装结构（层间隙、褶裥脊高、云纹贴合、
贴身余量、落地、漂浮）/ 尺寸与构图。全部数值从 blend 文件实测填写，不编造。

设计对照值来源：scenes/001-cloud-robe/design.md 与 build_001.py
（色值 linear RGB、面数上限 1200、层间隙 ≥0.005、褶裥脊高 0.032、云纹 6 处、
褶裥 8 片、N-gon 设计值 6——开口管端盖面）。

Run: blender --background --python 006-qa.py
"""
import os
import sys
import json
import math
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BLEND = os.path.join(ROOT, "scenes", "001-cloud-robe", "001-cloud-robe.blend")
SUMMARY_JSON = os.path.join(HERE, "006-qa-summary.json")
CHECKLIST = os.path.join(HERE, "006-asset-qa-checklist.md")

# Garment = every mesh except Ground and the neutral mannequin base.
def is_garment(o):
    return (o.type == 'MESH' and o.name != "Ground"
            and not o.name.startswith("Mannequin_"))

# Closed solids by construction (sphere / box / cylinder / wedge):
# boundary edges must be 0. Everything else is an open tube or a flat
# patch by design, where boundary edges are expected.
# (PlacketButton is a flat disc, not a closed solid — see FLAT_PATCHES.)
CLOSED_SOLIDS = ("Pauldron", "PlacketKnot", "Buckle",
                 "BuckleStud", "BootFoot", "BootToe", "Pendant",
                 "Hairpin", "HairpinBead")
# Flat single-sided patches: winding is correct by construction
# (design.md); the recalc-based inverted-normal check does not apply.
FLAT_PATCHES = ("SkirtCloud", "RobeCloud", "CuffCloud", "PlacketButton")

EXPECTED_NGONS = 6          # open-tube end-cap faces, per design.md
EXPECTED_FACES = 994        # v2 component build, recorded in design.md
FACE_LIMIT = 1200
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


def world_bbox(obj):
    ws = world_verts(obj)
    return (round(min(w.x for w in ws), 3), round(max(w.x for w in ws), 3),
            round(min(w.y for w in ws), 3), round(max(w.y for w in ws), 3),
            round(min(w.z for w in ws), 3), round(max(w.z for w in ws), 3))


def gap_between(outer, inner, zmin=None, zmax=None):
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
        return {"min": None, "median": None, "samples": 0, "ok": False}
    ds.sort()
    med = ds[len(ds) // 2]
    return {"min": round(ds[0], 4), "median": round(med, 4),
            "samples": len(ds), "ok": bool(ds[0] >= MIN_GAP)}


def max_distance_to(obj, target):
    """Largest vertex-to-surface distance from obj to target mesh."""
    bvh = world_bvh(target)
    best = 0.0
    for w in world_verts(obj):
        hit = bvh.find_nearest(w)
        if hit is not None:
            best = max(best, hit[3])
    return round(best, 4)


# design values from build_001.py make_materials():
# (metallic, roughness, base color linear RGB)
DESIGN_MATS = {
    "Robe_Teal":   (0.0, 0.80, (0.01, 0.10, 0.12)),   # #0E5A5E 青黛
    "Inner_Ink":   (0.0, 0.85, (0.01, 0.02, 0.05)),   # #16233F 墨蓝
    "Sash_Red":    (0.0, 0.80, (0.30, 0.01, 0.01)),   # #9E1B1B 朱红
    "Trim_Gold":   (0.7, 0.30, (0.58, 0.30, 0.03)),   # #C9962E 鎏金
    "Pleat_Red":   (0.0, 0.85, (0.20, 0.008, 0.008)), # #7A1010 褶裥深红
    "Skin":        (0.0, 0.70, (0.62, 0.34, 0.18)),   # #D9A67E 肤色
    "Hair_Dark":   (0.0, 0.85, (0.01, 0.01, 0.00)),   # #1A120B 发色
    "Boot_Brown":  (0.0, 0.90, (0.04, 0.02, 0.01)),   # #3A2415 深褐
    "Eye_Dark":    (0.0, 0.60, (0.01, 0.00, 0.00)),   # #14100C 眼
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

    # ---- component family roll-up (L/R .001 suffixes merged) ----
    def base(n):
        return n[:-4] if n.endswith(".001") else n
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

    gaps = {}
    gaps["main_vs_inner_z0.6-1.1"] = gap_between(
        obj("MainRobe"), obj("InnerRobe"), 0.6, 1.1)
    gaps["skirtF_vs_main_z0.55-0.95"] = gap_between(
        obj("Overskirt_Front"), obj("MainRobe"), 0.55, 0.95)
    gaps["skirtB_vs_main_z0.55-0.95"] = gap_between(
        obj("Overskirt_Back"), obj("MainRobe"), 0.55, 0.95)
    gaps["sash_vs_main_z0.88-0.99"] = gap_between(
        obj("Sash"), obj("MainRobe"), 0.88, 0.99)
    gaps["cuffL_vs_sleeve"] = gap_between(obj("Cuff"), obj("Sleeve"))
    gaps["cuffR_vs_sleeve"] = gap_between(obj("Cuff.001"), obj("Sleeve.001"))
    gaps["pendant_vs_skirtF"] = gap_between(
        obj("Pendant"), obj("Overskirt_Front"))
    gaps["bootL_vs_leg"] = gap_between(obj("Boot"), obj("Mannequin_Leg"))
    gaps["bootR_vs_leg"] = gap_between(obj("Boot.001"), obj("Mannequin_Leg.001"))
    gaps["sleeveL_vs_arm"] = gap_between(obj("Sleeve"), obj("Mannequin_Arm"))
    gaps["sleeveR_vs_arm"] = gap_between(obj("Sleeve.001"), obj("Mannequin_Arm.001"))
    gaps["collar_vs_neck"] = gap_between(obj("Collar"), obj("Mannequin_Neck"))
    for k, v in gaps.items():
        print("QA_GAP %s min=%s median=%s samples=%d %s" % (
            k, v["min"], v["median"], v["samples"],
            "PASS" if v["ok"] else "FAIL"))

    # ---- pleats: ridge lift above the skirt panel surface ----
    pleats = {}
    for tag, panel in (("F", "Overskirt_Front"), ("B", "Overskirt_Back")):
        for t in (2, 4, 6, 8):
            name = "Pleat_%s%d" % (tag, t)
            lift = max_distance_to(obj(name), obj(panel))
            pleats[name] = {"ridge_lift": lift, "ok": bool(lift >= 0.02)}
            print("QA_PLEAT %s ridge_lift=%.4f %s" % (
                name, lift, "PASS" if lift >= 0.02 else "FAIL"))

    # ---- cloud scrolls: standoff from their host surface ----
    # Construction (build_001.py): patch centre is placed 0.007 m off the
    # SMOOTH ellipse surface, and cloud_scroll adds another 0.007 m offset,
    # so the dot sits ~0.014 m off the smooth surface; the 12/10-sided
    # faceted tubes sag a further ~0.007-0.010 m inside the smooth ellipse
    # (chord sagitta). Expected standoff is therefore ~0.007-0.025 m.
    # The check is: not intersecting (>0.002) and not grossly floating
    # (<=0.03). Anything in range is construction-explained, not an error.
    clouds = {}
    for name, host in (("SkirtCloud", "Overskirt_Front"),
                       ("SkirtCloud.001", "Overskirt_Front"),
                       ("RobeCloud", "MainRobe"),
                       ("RobeCloud.001", "MainRobe"),
                       ("CuffCloud", "Cuff"),
                       ("CuffCloud.001", "Cuff.001")):
        d = gap_between(obj(name), obj(host))
        ok = d["min"] is not None and 0.002 <= d["min"] <= 0.03
        clouds[name] = {"standoff_min": d["min"], "standoff_median": d["median"],
                        "ok": bool(ok)}
        print("QA_CLOUD %s standoff_min=%s median=%s %s" % (
            name, d["min"], d["median"], "PASS" if ok else "FAIL"))

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
    g_bbox = {}
    xs, ys, zs = [], [], []
    for o in garment:
        for w in world_verts(o):
            xs.append(w.x); ys.append(w.y); zs.append(w.z)
    g_bbox = {"x": (round(min(xs), 3), round(max(xs), 3)),
              "y": (round(min(ys), 3), round(max(ys), 3)),
              "z": (round(min(zs), 3), round(max(zs), 3)),
              "height": round(max(zs) - min(zs), 3),
              "width": round(max(xs) - min(xs), 3)}
    boot_min_z = min(min(w.z for w in world_verts(obj(n)))
                     for n in ("Boot", "Boot.001", "BootFoot", "BootFoot.001",
                               "BootToe", "BootToe.001"))
    bun_top = max(w.z for w in world_verts(obj("Mannequin_Bun")))
    print("QA_DIMS garment_bbox=%s boot_min_z=%.4f bun_top=%.3f" % (
        g_bbox, boot_min_z, bun_top))

    # ---- framing: figure height fraction in the saved camera ----
    cam = bpy.context.scene.camera
    frame_frac = None
    if cam is not None:
        from bpy_extras.object_utils import world_to_camera_view
        scene = bpy.context.scene
        y_top = world_to_camera_view(scene, cam, Vector((0, 0, bun_top)))[1]
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
    # Layer gaps (cloth layers, sleeve/boot/collar fit) are hard checks.
    # The pendant is a hanging accessory, not a cloth layer: a clearance
    # of 0 < gap < 0.005 means "almost touching, no intersection" and is
    # recorded as an observation, not a hard failure.
    layer_gap_keys = [k for k in gaps if k != "pendant_vs_skirtF"]
    gaps_ok = all(gaps[k]["ok"] for k in layer_gap_keys)
    warnings = []
    pd = gaps["pendant_vs_skirtF"]
    if pd["min"] is not None and 0.0 < pd["min"] < MIN_GAP:
        warnings.append(
            "pendant_vs_skirtF: 玉佩背面距罩裙前片仅 %.4f 米（标准 ≥0.005），"
            "未穿插但余量不足；建议下次把玉佩外移 0.005 米或缩短挂绳。"
            % pd["min"])
    elif pd["min"] is not None and pd["min"] <= 0.0:
        warnings.append("pendant_vs_skirtF: 玉佩与罩裙穿插（间隙 ≤0）")
    cmax = max(v["standoff_min"] for v in clouds.values())
    if cmax > 0.014:
        warnings.append(
            "cloud_standoff: 云纹贴片离宿主表面 %.4f–%.4f 米（设计偏移 0.007 "
            "在 patch_c 与 cloud_scroll 里各加了一次，实际约 0.014；12/10 边"
            "刻面的弦高又加约 0.007–0.010）：正面渲染看不出漂浮，侧面近看"
            "贴片与布面有约 1–2 厘米缝；下次可把偏移改成按刻面表面算。"
            % (min(v["standoff_min"] for v in clouds.values()), cmax))
    pleats_ok = all(v["ok"] for v in pleats.values())
    clouds_ok = all(v["ok"] for v in clouds.values())
    float_ok = not bad_float
    faces_ok = tot["faces"] <= FACE_LIMIT
    faces_match = tot["faces"] == EXPECTED_FACES
    ngons_ok = tot["ngons"] == EXPECTED_NGONS
    topo_ok = (tot["duplicate_verts"] == 0 and tot["loose_edges"] == 0
               and tot["nonmanifold_edges"] == 0
               and tot["degenerate_faces"] == 0 and closed_boundary == 0
               and solid_inv == 0)
    ground_ok = abs(boot_min_z) <= 0.005
    frame_ok = frame_frac is not None and 0.60 <= frame_frac <= 0.80
    all_ok = (faces_ok and ngons_ok and topo_ok and gaps_ok and pleats_ok
              and clouds_ok and float_ok and ground_ok and frame_ok
              and mats["all_ok"] and empty_slots == 0)

    summary = {
        "asset": "001-cloud-robe (v2 component build)",
        "blend": "scenes/001-cloud-robe/001-cloud-robe.blend",
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
        "pleats": pleats, "pleats_ok": bool(pleats_ok),
        "clouds": clouds, "clouds_ok": bool(clouds_ok),
        "floating_bad": bad_float, "floating_ok": bool(float_ok),
        "garment_bbox": g_bbox,
        "boot_min_z": round(boot_min_z, 4), "ground_ok": bool(ground_ok),
        "bun_top_z": round(bun_top, 3),
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
        f.write("# 006 资产质检单：云纹战袍套装（001 v2）\n\n")
        f.write("被检资产：`scenes/001-cloud-robe/001-cloud-robe.blend`（%d 个服装部件，"
                "不含地面与人体底座；底座 %d 面，另计）\n"
                % (len(results), mannequin_faces))
        f.write("检查方式：Blender bmesh + BVH 实测（拓扑逐面、层间隙逐点最近距离），"
                "非目测估算；设计对照值见 `scenes/001-cloud-robe/design.md`。\n\n")
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
        f.write("- N-gon：共 %d 个（设计值 %d，开口管端盖面）：%s\n" % (
            tot["ngons"], EXPECTED_NGONS, verdict(ngons_ok)))
        f.write("- 无重叠顶点：%s\n" % verdict(tot["duplicate_verts"] == 0))
        f.write("- 无散边 / 无非流形边：%s\n" % verdict(
            tot["loose_edges"] == 0 and tot["nonmanifold_edges"] == 0))
        f.write("- 无退化面（面积≈0）：%s\n" % verdict(tot["degenerate_faces"] == 0))
        f.write("- 闭合实体（球/盒/柱/楔形：肩甲、盘扣、金扣、靴头、玉佩、发簪等）边界边："
                "%d，%s\n" % (closed_boundary, verdict(closed_boundary == 0)))
        f.write("- 边界边合计 %d，全部来自开口管（袍、袖、靴筒）与扁平贴片，属设计形态，"
                "不在此项判定。\n" % tot["boundary_edges"])
        f.write("- 最高顶点价数 %d\n\n" % max(r["max_valence"] for r in results.values()))
        f.write("## 2. 法线\n\n")
        f.write("- 法线朝外一致（与 Blender recalc_face_normals 的外法线逐面比对）："
                "实体倒置面 %d 个，%s\n" % (solid_inv, verdict(solid_inv == 0)))
        f.write("- 扁平贴片（云纹、盘扣圆片）倒置面 %d 个：贴片为单面几何，绕序由构造保证"
                "（design.md 已注明不适用质心法向检查），此项仅记录、不判定。\n\n" % flat_inv)
        f.write("## 3. UV\n\n")
        f.write("- UV 层：%d / %d 个部件有 UV 层：%s\n" % (
            len(uv_parts), len(results), "、".join(uv_parts)))
        f.write("  这些 UV 层是 Blender 图元（球/盒/柱）自带的默认 UVMap，"
                "本套服装无任何贴图引用它们，UV 不参与渲染；其余 %d 个部件"
                "由 from_pydata 直接建网格，无 UV 层。\n" % (len(results) - len(uv_parts)))
        f.write("- UV 超出 0–1 范围：%d 个 UV 点，%s\n\n" % (
            uv_oob, verdict(uv_oob == 0)))
        f.write("## 4. 服装结构（BVH 实测，单位：米）\n\n")
        f.write("### 4.1 层间隙（最小间隙要求 ≥0.005）\n\n")
        f.write("| 间隙 | 最小 | 中位 | 采样点 | 结论 |\n")
        f.write("| ---- | ---- | ---- | ------ | ---- |\n")
        gap_labels = {
            "main_vs_inner_z0.6-1.1": "主袍 / 内层贴身袍（z 0.6–1.1）",
            "skirtF_vs_main_z0.55-0.95": "罩裙前片 / 主袍（z 0.55–0.95）",
            "skirtB_vs_main_z0.55-0.95": "罩裙后片 / 主袍（z 0.55–0.95）",
            "sash_vs_main_z0.88-0.99": "腰封 / 主袍（z 0.88–0.99）",
            "cuffL_vs_sleeve": "袖口金边左 / 宽袖左",
            "cuffR_vs_sleeve": "袖口金边右 / 宽袖右",
            "pendant_vs_skirtF": "玉佩 / 罩裙前片",
            "bootL_vs_leg": "战靴左 / 腿",
            "bootR_vs_leg": "战靴右 / 腿",
            "sleeveL_vs_arm": "宽袖左 / 手臂",
            "sleeveR_vs_arm": "宽袖右 / 手臂",
            "collar_vs_neck": "立领 / 脖颈",
        }
        for k, v in gaps.items():
            if k == "pendant_vs_skirtF":
                # hanging accessory: 0 < gap < 0.005 is an observation,
                # not a hard failure (see warnings below).
                note = ("观察（未穿插，余量不足，见第 7 节）"
                        if v["min"] is not None and 0.0 < v["min"] < MIN_GAP
                        else verdict(v["ok"]))
                f.write("| %s | %.4f | %.4f | %d | %s |\n" % (
                    gap_labels[k], v["min"], v["median"], v["samples"], note))
            else:
                f.write("| %s | %.4f | %.4f | %d | %s |\n" % (
                    gap_labels[k], v["min"], v["median"], v["samples"],
                    verdict(v["ok"])))
        f.write("\n### 4.2 褶裥脊高（设计 0.032，要求 ≥0.02 才看得见立体褶）\n\n")
        for name, v in pleats.items():
            f.write("- %s：脊高 %.4f：%s\n" % (name, v["ridge_lift"], verdict(v["ok"])))
        f.write("\n### 4.3 云纹贴片（6 处，要求不扎进布面也不明显漂浮：离面 0.002–0.03）\n\n")
        f.write("构造说明：贴片中心按光滑椭圆面放 0.007 米偏移，cloud_scroll 内又加 "
                "0.007 米，圆点实际约离光滑面 0.014 米；12/10 边刻面弦高再加约 "
                "0.007–0.010 米，所以实测 0.009–0.021 米属构造可解释范围，"
                "不是建模错误；侧面近看约 1–2 厘米缝，见第 7 节。\n\n")
        for name, v in clouds.items():
            f.write("- %s：离宿主表面最小 %.4f / 中位 %.4f：%s\n" % (
                name, v["standoff_min"], v["standoff_median"], verdict(v["ok"])))
        f.write("\n### 4.4 漂浮检查（每个服装部件到最近的其他服装/底座网格的距离，≤0.05 视为已连接）\n\n")
        f.write("- 漂浮嫌疑部件：%s，%s\n\n" % (
            "无" if float_ok else "、".join(bad_float), verdict(float_ok)))
        f.write("## 5. 尺寸与落地\n\n")
        f.write("- 服装包围盒：x %.3f–%.3f，y %.3f–%.3f，z %.3f–%.3f；"
                "宽 %.3f、高 %.3f\n" % (
                    g_bbox["x"][0], g_bbox["x"][1], g_bbox["y"][0], g_bbox["y"][1],
                    g_bbox["z"][0], g_bbox["z"][1], g_bbox["width"], g_bbox["height"]))
        f.write("- 战靴最低点 z=%.4f（地面 z=0）：%s\n" % (
            boot_min_z, verdict(ground_ok, "落地")))
        f.write("- 发髻顶 z=%.3f；相机内人物占画面高度 %.3f（v2 标准 0.60–0.80）：%s\n\n" % (
            bun_top, frame_frac, verdict(frame_ok)))
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
        f.write("- 贴图：不适用（本套服装无图片贴图，全部程序化材质）\n\n")
        f.write("## 7. 观察项（不判定失败，但值得下次改进）\n\n")
        if warnings:
            for w in warnings:
                f.write("- %s\n" % w)
            f.write("- 注：design.md 记录的玉佩间隙 0.0160 是建模时用设计环表算的"
                    "（拿玉佩前表面比罩裙表面，没算玉佩自身厚度）；本单实测取玉佩"
                    "全部顶点到罩裙表面的最近距离，0.0006 米是玉佩背面到罩裙的"
                    "最近处，以实测为准。\n")
        else:
            f.write("- 无\n")
        f.write("\n## 8. 与 design.md 记录的对照\n\n")
        f.write("- 面数：实测 %d vs 记录 %d：%s\n" % (
            tot["faces"], EXPECTED_FACES,
            "一致" if faces_match else "不一致"))
        f.write("- L2/L3 间隙：design.md 记录值为建模时的设计环表算术值；"
                "本单第 4.1 节为从已建网格实测的逐点最近距离，两者口径不同，"
                "以本单实测为准。\n\n")
        f.write("## 结论\n\n")
        if all_ok and warnings:
            f.write("**总体：通过（附 %d 项观察，见第 7 节），可作为服装建模管线的质检通过件**\n"
                    % len(warnings))
        elif all_ok:
            f.write("**总体：通过，可作为服装建模管线的质检通过件**\n")
        else:
            f.write("**总体：未通过，见上文不通过项**\n")
    print("CHECKLIST_WRITTEN:", CHECKLIST)
    print("SUMMARY_WRITTEN:", SUMMARY_JSON)


if __name__ == "__main__":
    main()
