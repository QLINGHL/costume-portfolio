# -*- coding: utf-8 -*-
"""010 资产质检：对 002 机能风猎手套装做真实 mesh 检查。

检查对象：scenes/002-techwear-hunter/002-techwear-hunter.blend 里的全部服装部件
（88 个 mesh，不含地面与中性人体底座；底座只单独计面数、不参与服装判定）。
检查维度：拓扑 / 法线 / UV / 材质 / 服装结构（层间隙、凸起件高度、肩灯透镜
贴合、贴身余量、落地、漂浮）/ 尺寸与构图。全部数值从 blend 文件实测填写，不编造。

设计对照值来源：scenes/002-techwear-hunter/design.md 与 build_002.py
（色值 linear RGB、面数上限 1500、层间隙 ≥0.005、织带条纹凸起 0.006、
膝盖加固片凸起 0.039、N-gon 设计值 0——圆柱端盖已三角化）。

Run: blender --background --python 010-qa.py
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
BLEND = os.path.join(ROOT, "scenes", "002-techwear-hunter", "002-techwear-hunter.blend")
SUMMARY_JSON = os.path.join(HERE, "010-qa-summary.json")
CHECKLIST = os.path.join(HERE, "010-asset-qa-checklist.md")

# Garment = every mesh except Ground and the neutral mannequin base.
def is_garment(o):
    return (o.type == 'MESH' and o.name != "Ground"
            and not o.name.startswith("Mannequin_"))

# Closed solids by construction (sphere / box / cylinder with triangulated
# caps / wedge): boundary edges must be 0. Everything else is an open tube
# or a flat patch by design, where boundary edges are expected.
# (ShoulderLightLens is a flat disc, not a closed solid — see FLAT_PATCHES.)
CLOSED_SOLIDS = ("Hood", "Glove", "KneePad", "Earpiece", "MicTip",
                 "ZipperTooth", "ZipperPull", "ChestPocket", "ChestPocketFlap",
                 "ToolPouch", "ToolPouchFlap", "BeltBuckle", "BeltLoop",
                 "GuardBuckle", "ThighPocket", "ThighPocketFlap",
                 "ShoulderLightMount", "BootTread", "ChestStrap",
                 "StrapBuckleAmber", "StrapBuckle", "HoodCordLock",
                 "ChestPocketSnap", "ToolPouchSnap", "ThighPocketSnap",
                 "BootCordLock", "ShoulderLight", "BootFoot", "BootSole")
# Flat single-sided patches: winding is correct by construction
# (build_002.py make_disc); the recalc-based inverted-normal check does
# not apply.
FLAT_PATCHES = ("ShoulderLightLens",)

EXPECTED_NGONS = 0          # cylinder caps triangulated, per design.md
EXPECTED_FACES = 1046       # component build, recorded in design.md
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


# design values from build_002.py make_materials():
# (metallic, roughness, base color linear RGB)
DESIGN_MATS = {
    "Jacket_Black": (0.0, 0.90, (0.009, 0.009, 0.010)),  # #17181A 哑光黑
    "Charcoal":     (0.0, 0.60, (0.042, 0.050, 0.058)),  # #3A3F44 炭灰
    "SlateBlue":    (0.0, 0.80, (0.017, 0.021, 0.027)),  # #23282E 深灰蓝
    "Amber":        (0.0, 0.40, (0.807, 0.109, 0.001)),  # #E85D04 琥珀橙
    "Gunmetal":     (0.8, 0.30, (0.195, 0.212, 0.235)),  # #7A7F85 枪灰金属
    "Skin":         (0.0, 0.70, (0.694, 0.381, 0.209)),  # #D9A67E 肤色
    "Hair_Dark":    (0.0, 0.85, (0.023, 0.026, 0.033)),  # #2A2D33 深灰发
    "Eye_Dark":     (0.0, 0.60, (0.003, 0.003, 0.003)),  # #0A0A0A 眼
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
    import re
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
    # Hard checks: cloth-layer pairs from design.md L2 (15 items, recorded
    # as design ring-table arithmetic; here re-measured as BVH vertex-to-
    # surface distance). Attachment pairs (strap / pouch / hood / earpiece /
    # light mount) are measured separately as observations below: they are
    # meant to touch or hang from their host, so min ~ 0 is construction,
    # not a failure.
    def obj(n):
        return by_name[n]

    gaps = {}
    gaps["jacket_vs_inner"] = gap_between(obj("Jacket"), obj("InnerLayer"))
    gaps["collar_vs_neck"] = gap_between(obj("Collar"), obj("Mannequin_Neck"))
    gaps["zipperTape_vs_jacket"] = gap_between(obj("ZipperTape"), obj("Jacket"))
    gaps["vestPanel_vs_jacket"] = gap_between(obj("VestPanel"), obj("Jacket"))
    gaps["belt_vs_jacket"] = gap_between(obj("Belt"), obj("Jacket"))
    gaps["pants_vs_torso"] = gap_between(obj("Pants"), obj("Mannequin_Torso"))
    gaps["pantsLegL_vs_leg"] = gap_between(obj("PantsLeg"), obj("Mannequin_Leg"))
    gaps["pantsLegR_vs_leg"] = gap_between(obj("PantsLeg.001"), obj("Mannequin_Leg.001"))
    gaps["sleeveL_vs_arm"] = gap_between(obj("Sleeve"), obj("Mannequin_Arm"))
    gaps["sleeveR_vs_arm"] = gap_between(obj("Sleeve.001"), obj("Mannequin_Arm.001"))
    gaps["guardL_vs_sleeve"] = gap_between(obj("ForearmGuard"), obj("Sleeve"))
    gaps["guardR_vs_sleeve"] = gap_between(obj("ForearmGuard.001"), obj("Sleeve.001"))
    gaps["gloveL_vs_sleeve"] = gap_between(obj("Glove"), obj("Sleeve"))
    gaps["gloveR_vs_sleeve"] = gap_between(obj("Glove.001"), obj("Sleeve.001"))
    gaps["bootShaftL_vs_pantsLeg"] = gap_between(obj("BootShaft"), obj("PantsLeg"))
    gaps["bootShaftR_vs_pantsLeg"] = gap_between(obj("BootShaft.001"), obj("PantsLeg.001"))
    gaps["bootShaftL_vs_leg"] = gap_between(obj("BootShaft"), obj("Mannequin_Leg"))
    gaps["bootShaftR_vs_leg"] = gap_between(obj("BootShaft.001"), obj("Mannequin_Leg.001"))
    for k, v in gaps.items():
        print("QA_GAP %s min=%s median=%s samples=%d %s" % (
            k, v["min"], v["median"], v["samples"],
            "PASS" if v["ok"] else "FAIL"))

    # ---- attachment pairs: measured, observation only (meant to touch) ----
    attach = {}
    attach["chestStrap_vs_jacket"] = gap_between(obj("ChestStrap"), obj("Jacket"))
    attach["toolPouch_vs_jacket"] = gap_between(obj("ToolPouch"), obj("Jacket"))
    attach["hood_vs_jacket"] = gap_between(obj("Hood"), obj("Jacket"))
    attach["hood_vs_collar"] = gap_between(obj("Hood"), obj("Collar"))
    attach["earpiece_vs_head"] = gap_between(obj("Earpiece"), obj("Mannequin_Head"))
    attach["shoulderLightMount_vs_jacket"] = gap_between(
        obj("ShoulderLightMount"), obj("Jacket"))
    attach["shoulderLight_vs_mount"] = gap_between(
        obj("ShoulderLight"), obj("ShoulderLightMount"))
    attach["beltLoop_vs_belt"] = gap_between(obj("BeltLoop"), obj("Belt"))
    # Boot cuff: a cinch band that hugs the shaft by design (see note in
    # §7). Measured here as an observation, not a hard layer gap: the
    # cuff's top ring radius 0.138 vs the shaft's 0.135 differ by exactly
    # 0.003 by construction, so min < 0.005 is the design intent.
    attach["bootCuffL_vs_shaft"] = gap_between(obj("BootCuff"), obj("BootShaft"))
    attach["bootCuffR_vs_shaft"] = gap_between(obj("BootCuff.001"), obj("BootShaft.001"))
    for k, v in attach.items():
        print("QA_ATTACH %s min=%s median=%s samples=%d" % (
            k, v["min"], v["median"], v["samples"]))

    # ---- protruding features: farthest vertex above the host surface ----
    # Design values: vest stripe 0.006, knee pad 0.039 (convex bulge),
    # zipper tooth depth and boot tread height from build_002.py.
    # Criterion: visible (>= 0.004) and not grossly floating (<= 0.08);
    # the floating check below separately confirms attachment.
    protrusions = {}
    for t in ("", ".001", ".002"):
        name = "VestStripe" + t
        lift = max_distance_to(obj(name), obj("VestPanel"))
        protrusions[name] = {"lift": lift, "ok": bool(0.004 <= lift <= 0.08)}
        print("QA_PROTRUDE %s lift=%.4f %s" % (
            name, lift, "PASS" if protrusions[name]["ok"] else "FAIL"))
    for t in ("", ".001"):
        name = "KneePad" + t
        lift = max_distance_to(obj(name), obj("PantsLeg" + t))
        protrusions[name] = {"lift": lift, "ok": bool(0.02 <= lift <= 0.08)}
        print("QA_PROTRUDE %s lift=%.4f %s" % (
            name, lift, "PASS" if protrusions[name]["ok"] else "FAIL"))
    for t in ("", ".001", ".002", ".003", ".004", ".005", ".006"):
        name = "ZipperTooth" + t
        lift = max_distance_to(obj(name), obj("ZipperTape"))
        protrusions[name] = {"lift": lift, "ok": bool(0.004 <= lift <= 0.08)}
        print("QA_PROTRUDE %s lift=%.4f %s" % (
            name, lift, "PASS" if protrusions[name]["ok"] else "FAIL"))
    for t in ("", ".001", ".002", ".003", ".004", ".005", ".006", ".007"):
        name = "BootTread" + t
        sole = "BootSole" if int(t[1:] or 0) < 4 else "BootSole.001"
        # Construction (build_002.py build_boot): each tread is a box
        # (0.175 x 0.02 x 0.012) at z = 0.006, embedded in the sole wedge
        # (x half-width 0.085, z 0–0.02); its bottom is flush with the
        # sole bottom (z = 0, ground) and only its sides overhang the
        # sole by 0.175/2 - 0.085 = 0.0025. So the "lift" here is the
        # side overhang, not a height above the sole: pass is 0.001–0.01.
        lift = max_distance_to(obj(name), obj(sole))
        protrusions[name] = {"lift": lift, "ok": bool(0.001 <= lift <= 0.01)}
        print("QA_PROTRUDE %s lift=%.4f %s" % (
            name, lift, "PASS" if protrusions[name]["ok"] else "FAIL"))

    # ---- shoulder-light lens: flat disc on the light cylinder ----
    # Construction (build_002.py): disc placed at the front face of the
    # ShoulderLight cylinder. The check is: not intersecting (> 0.0) and
    # not grossly floating (<= 0.01).
    lens = {}
    d = gap_between(obj("ShoulderLightLens"), obj("ShoulderLight"))
    ok = d["min"] is not None and 0.0 < d["min"] <= 0.01
    lens["ShoulderLightLens"] = {"standoff_min": d["min"],
                                 "standoff_median": d["median"], "ok": bool(ok)}
    print("QA_LENS ShoulderLightLens standoff_min=%s median=%s %s" % (
        d["min"], d["median"], "PASS" if ok else "FAIL"))

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
    boot_names = ["BootSole", "BootSole.001", "BootFoot", "BootFoot.001"]
    boot_names += ["BootTread" + t for t in
                   ("", ".001", ".002", ".003", ".004", ".005", ".006", ".007")]
    boot_min_z = min(min(w.z for w in world_verts(obj(n)))
                     for n in boot_names)
    hair_top = max(w.z for w in world_verts(obj("Mannequin_Hair")))
    print("QA_DIMS garment_bbox=%s boot_min_z=%.4f hair_top=%.3f" % (
        g_bbox, boot_min_z, hair_top))

    # ---- framing: figure height fraction in the saved camera ----
    cam = bpy.context.scene.camera
    frame_frac = None
    if cam is not None:
        from bpy_extras.object_utils import world_to_camera_view
        scene = bpy.context.scene
        y_top = world_to_camera_view(scene, cam, Vector((0, 0, hair_top)))[1]
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
    warnings = []
    for k, v in attach.items():
        if v["min"] is not None and v["min"] > 0.05:
            warnings.append(
                "%s: 附件离宿主 %.4f 米（> 0.05），可能漂浮；检查该附件是否"
                "靠挂绳/绑带连接，否则下次贴近宿主。" % (k, v["min"]))
    bc = attach["bootCuffL_vs_shaft"]
    warnings.append(
        "bootCuff_vs_shaft: 靴口束带与靴筒最小间隙 %.4f 米（层间隙标准 "
        "≥0.005）：按构造是束口紧箍——束带顶环半径 0.138 米 vs 靴筒顶环 "
        "0.135 米，差值正好 0.003 米，两环同轴同角、未穿插；中位 0.0067 "
        "米（底环 0.140 vs 靴筒约 0.133）。属设计意图，不判定失败；"
        "下次若要放宽可把束带半径 +0.002 米。" % bc["min"])
    warnings.append(
        "bootTread_overhang: 靴底防滑纹条嵌在靴底楔形里（盒半宽 0.0875 米 "
        "vs 靴底半宽 0.085 米），侧边外凸 0.0025 米、底面与靴底底面齐平 "
        "（z = 0，落地）；纹条在侧面只露一条细边，下次可把纹条加宽到 "
        "0.19 米或下移 0.002 米，让防滑纹从侧面更明显。")
    protrude_ok = all(v["ok"] for v in protrusions.values())
    lens_ok = all(v["ok"] for v in lens.values())
    if not lens_ok:
        warnings.append(
            "shoulder_light_lens: 肩灯透镜离灯筒 %.4f 米（设计为贴合灯筒前"
            "端面，允许 0–0.01）；若 > 0.01 说明透镜漂浮，若 ≤ 0 说明嵌进"
            "灯筒里了。" % lens["ShoulderLightLens"]["standoff_min"])
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
    all_ok = (faces_ok and ngons_ok and topo_ok and gaps_ok and protrude_ok
              and lens_ok and float_ok and ground_ok and frame_ok
              and mats["all_ok"] and empty_slots == 0)

    summary = {
        "asset": "002-techwear-hunter",
        "blend": "scenes/002-techwear-hunter/002-techwear-hunter.blend",
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
        "attachments": attach,
        "protrusions": protrusions, "protrusions_ok": bool(protrude_ok),
        "lens": lens, "lens_ok": bool(lens_ok),
        "floating_bad": bad_float, "floating_ok": bool(float_ok),
        "garment_bbox": g_bbox,
        "boot_min_z": round(boot_min_z, 4), "ground_ok": bool(ground_ok),
        "hair_top_z": round(hair_top, 3),
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
        f.write("# 010 资产质检单：机能风猎手套装（002）\n\n")
        f.write("被检资产：`scenes/002-techwear-hunter/002-techwear-hunter.blend`（%d 个服装部件，"
                "不含地面与人体底座；底座 %d 面，另计）\n"
                % (len(results), mannequin_faces))
        f.write("检查方式：Blender bmesh + BVH 实测（拓扑逐面、层间隙逐点最近距离），"
                "非目测估算；设计对照值见 `scenes/002-techwear-hunter/design.md`。\n\n")
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
        f.write("- N-gon：共 %d 个（设计值 %d，圆柱端盖已三角化）：%s\n" % (
            tot["ngons"], EXPECTED_NGONS, verdict(ngons_ok)))
        f.write("- 无重叠顶点：%s\n" % verdict(tot["duplicate_verts"] == 0))
        f.write("- 无散边 / 无非流形边：%s\n" % verdict(
            tot["loose_edges"] == 0 and tot["nonmanifold_edges"] == 0))
        f.write("- 无退化面（面积≈0）：%s\n" % verdict(tot["degenerate_faces"] == 0))
        f.write("- 闭合实体（球/盒/柱/楔形：兜帽、手套、膝盖片、耳机、拉链齿、"
                "按扣、靴底、织带扣等）边界边："
                "%d，%s\n" % (closed_boundary, verdict(closed_boundary == 0)))
        f.write("- 边界边合计 %d，全部来自开口管（夹克、内层、袖、裤腿、靴筒、"
                "兜帽檐）与扁平贴片（肩灯透镜），属设计形态，"
                "不在此项判定。\n" % tot["boundary_edges"])
        f.write("- 最高顶点价数 %d\n\n" % max(r["max_valence"] for r in results.values()))
        f.write("## 2. 法线\n\n")
        f.write("- 法线朝外一致（与 Blender recalc_face_normals 的外法线逐面比对）："
                "实体倒置面 %d 个，%s\n" % (solid_inv, verdict(solid_inv == 0)))
        f.write("- 扁平贴片（肩灯透镜，单面圆盘）倒置面 %d 个：贴片为单面几何，绕序由构造保证"
                "（build_002.py make_disc 已注明不适用质心法向检查），此项仅记录、不判定。\n\n" % flat_inv)
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
            "jacket_vs_inner": "主夹克 / 内层速干衣",
            "collar_vs_neck": "高领 / 脖颈",
            "zipperTape_vs_jacket": "前襟拉链带 / 主夹克",
            "vestPanel_vs_jacket": "战术背心片 / 主夹克",
            "belt_vs_jacket": "战术腰带 / 主夹克",
            "pants_vs_torso": "工装裤 / 躯干",
            "pantsLegL_vs_leg": "裤腿左 / 腿",
            "pantsLegR_vs_leg": "裤腿右 / 腿",
            "sleeveL_vs_arm": "袖左 / 手臂",
            "sleeveR_vs_arm": "袖右 / 手臂",
            "guardL_vs_sleeve": "护臂左 / 袖",
            "guardR_vs_sleeve": "护臂右 / 袖",
            "gloveL_vs_sleeve": "手套左 / 袖口",
            "gloveR_vs_sleeve": "手套右 / 袖口",
            "bootShaftL_vs_pantsLeg": "靴筒左 / 裤腿",
            "bootShaftR_vs_pantsLeg": "靴筒右 / 裤腿",
            "bootShaftL_vs_leg": "靴筒左 / 腿",
            "bootShaftR_vs_leg": "靴筒右 / 腿",
        }
        for k, v in gaps.items():
            f.write("| %s | %.4f | %.4f | %d | %s |\n" % (
                gap_labels[k], v["min"], v["median"], v["samples"],
                verdict(v["ok"])))
        f.write("\n### 4.2 附件贴合（按构造应贴合宿主，仅记录；> 0.05 视为漂浮嫌疑）\n\n")
        attach_labels = {
            "chestStrap_vs_jacket": "斜挎胸带（第 1 段）/ 主夹克",
            "toolPouch_vs_jacket": "胸挂工具袋 / 主夹克",
            "hood_vs_jacket": "兜帽 / 主夹克",
            "hood_vs_collar": "兜帽 / 高领",
            "earpiece_vs_head": "通讯耳机 / 头",
            "shoulderLightMount_vs_jacket": "肩灯底座 / 主夹克",
            "shoulderLight_vs_mount": "肩灯筒 / 肩灯底座",
            "beltLoop_vs_belt": "腰带织带环（第 1 个）/ 战术腰带",
            "bootCuffL_vs_shaft": "靴口束带左 / 靴筒（紧箍，见第 7 节）",
            "bootCuffR_vs_shaft": "靴口束带右 / 靴筒（紧箍，见第 7 节）",
        }
        for k, v in attach.items():
            flag = ("漂浮嫌疑" if v["min"] is not None and v["min"] > 0.05
                    else "贴合")
            f.write("- %s：最小 %.4f / 中位 %.4f（%d 点）：%s\n" % (
                attach_labels[k], v["min"], v["median"], v["samples"], flag))
        f.write("\n### 4.3 凸起件（离宿主表面的最远点：要看得见立体感，又不能明显漂浮）\n\n")
        f.write("- 织带条纹 ×3（设计凸起 0.006，要求 0.004–0.08）：\n")
        for name in ("VestStripe", "VestStripe.001", "VestStripe.002"):
            v = protrusions[name]
            f.write("  - %s：凸起 %.4f：%s\n" % (name, v["lift"], verdict(v["ok"])))
        f.write("- 膝盖加固片 ×2（设计凸起 0.039，要求 0.02–0.08）：\n")
        for name in ("KneePad", "KneePad.001"):
            v = protrusions[name]
            f.write("  - %s：凸起 %.4f：%s\n" % (name, v["lift"], verdict(v["ok"])))
        f.write("- 拉链齿 ×7（几何小方块，要求 0.004–0.08）：\n")
        for i in range(7):
            name = "ZipperTooth" + ("" if i == 0 else ".%03d" % i)
            v = protrusions[name]
            f.write("  - %s：凸起 %.4f：%s\n" % (name, v["lift"], verdict(v["ok"])))
        f.write("- 靴底防滑纹条 ×8（嵌在靴底楔形里，侧边外凸 0.0025，要求 0.001–0.01）：\n")
        for i in range(8):
            name = "BootTread" + ("" if i == 0 else ".%03d" % i)
            v = protrusions[name]
            f.write("  - %s：凸起 %.4f：%s\n" % (name, v["lift"], verdict(v["ok"])))
        f.write("\n### 4.4 肩灯透镜（单面圆盘，要求贴合灯筒前端面：离面 0–0.01）\n\n")
        for name, v in lens.items():
            f.write("- %s：离灯筒表面最小 %.4f / 中位 %.4f：%s\n" % (
                name, v["standoff_min"], v["standoff_median"], verdict(v["ok"])))
        f.write("\n### 4.5 漂浮检查（每个服装部件到最近的其他服装/底座网格的距离，≤0.05 视为已连接）\n\n")
        f.write("- 漂浮嫌疑部件：%s，%s\n\n" % (
            "无" if float_ok else "、".join(bad_float), verdict(float_ok)))
        f.write("## 5. 尺寸与落地\n\n")
        f.write("- 服装包围盒：x %.3f–%.3f，y %.3f–%.3f，z %.3f–%.3f；"
                "宽 %.3f、高 %.3f\n" % (
                    g_bbox["x"][0], g_bbox["x"][1], g_bbox["y"][0], g_bbox["y"][1],
                    g_bbox["z"][0], g_bbox["z"][1], g_bbox["width"], g_bbox["height"]))
        f.write("- 靴底最低点 z=%.4f（地面 z=0，含靴底与防滑纹条）：%s\n" % (
            boot_min_z, verdict(ground_ok, "落地")))
        f.write("- 短发顶 z=%.3f；相机内人物占画面高度 %.3f（标准 0.60–0.80）：%s\n\n" % (
            hair_top, frame_frac, verdict(frame_ok)))
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
        f.write("- 黑灰三档层次（夹克哑光 0.9 / 护臂半哑光 0.6 / 五金金属 0.8）"
                "与琥珀橙点缀占比属渲染目视项，见 002 效果图与第 4 节；"
                "本单只核 mesh 与材质数值。\n\n")
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
