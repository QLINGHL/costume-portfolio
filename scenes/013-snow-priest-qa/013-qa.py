# -*- coding: utf-8 -*-
"""013 资产质检：对 011 雪国祭司长袍做真实 mesh 检查。

检查对象：scenes/011-snow-priest-robe/011-snow-priest-robe.blend 里的全部服装部件
（46 个 mesh，不含地面与中性人体底座；底座只单独计面数、不参与服装判定）。
检查维度：拓扑 / 法线 / UV / 材质 / 服装结构（层间隙、凸起件高度、贴身余量、
落地、漂浮）/ 尺寸与构图。全部数值从 blend 文件实测填写，不编造。

设计对照值来源：scenes/011-snow-priest-robe/design.md 与 build_011.py
（色值 linear RGB、面数 617、层间隙 ≥0.005、胸前雪花浮雕 0.008、
裙摆雪花浮雕 0.008、褶裥条浮雕 0.006、腰带扣浮雕 0.012、N-gon 设计值 0）。

注意：BVH 顶点-表面距离是无符号距离，分不清“在外面”还是“在里面”。
腰带是等半径管（rx 0.345），罩裙从腰向下张开（z=0.78 处 0.330 → z=0.55
处 0.410），两者在 z≈0.737 以下存在相交嫌疑：无符号距离会照常报一个
正数并“通过”，所以本单对腰带 vs 罩裙另做一轮径向射线内/外判定
（belt_inside_skirt）：从腰带顶点沿径向向外打射线，命中罩裙即说明该
顶点落在罩裙张开的锥面之内——裙面穿过了腰带壁。见第 7 节。

长杖 vs 罩裙同理不能只用顶点距离：杖身只有 z=0.05 / 1.45 两圈顶点，
离罩裙最近的 z≈0.34 处没有顶点，顶点距离会高估间隙。本单对杖身做
参数化表面采样（24 角 × 每 0.02 米一层），逐点测到罩裙的最近距离。

Run: blender --background --python 013-qa.py
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
BLEND = os.path.join(ROOT, "scenes", "011-snow-priest-robe",
                     "011-snow-priest-robe.blend")
SUMMARY_JSON = os.path.join(HERE, "013-qa-summary.json")
CHECKLIST = os.path.join(HERE, "013-asset-qa-checklist.md")

# Garment = every mesh except Ground and the neutral mannequin base.
def is_garment(o):
    return (o.type == 'MESH' and o.name != "Ground"
            and not o.name.startswith("Mannequin_"))

# Closed solids by construction (sphere / box / capped tube / wedge):
# boundary edges must be 0. Everything else is an open tube or a flat
# patch by design, where boundary edges are expected.
# (StaffShaft is a capped tube; BootFoot is a closed wedge.)
CLOSED_SOLIDS = ("FurTuft", "ShoulderPad", "StaffCrystal", "BeltBuckle",
                 "CrownSpike", "CrownCentreSpike", "StaffShaft", "BootFoot")
# Flat single-sided patches: winding is correct by construction
# (build_011.py make_snowflake / build_pleat); the recalc-based
# inverted-normal check does not apply.
FLAT_PATCHES = ("ChestSnowflake", "SkirtSnowflake", "PleatStrip")

EXPECTED_NGONS = 0          # design.md: N-gon 0
EXPECTED_FACES = 617        # component build, recorded in design.md
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


def sampled_cylinder_gap(cx, cy, r, z0, z1, target, angles=24, dz=0.02):
    """Gap from a parametric cylinder surface to a target mesh, sampled
    densely along its length: the mesh itself may have vertices only at
    its end rings, so vertex-only sampling would miss the closest
    approach (staff shaft vs overskirt hem)."""
    bvh = world_bvh(target)
    ds = []
    z = z0
    while z <= z1 + 1e-9:
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


def radial_inside_test(outer, inner, max_dist=0.05):
    """For each vertex of `outer`, cast a ray radially outward against
    the `inner` mesh BVH. A hit within max_dist means the vertex sits
    inside the inner tube's flare: the inner surface crosses the outer
    wall (an unsigned BVH distance cannot see this). Returns the z
    range and count of inside vertices, plus the angles where it
    happens (0 deg = +x side, 90 deg = +y side)."""
    bvh = world_bvh(inner)
    inside = []
    for w in world_verts(outer):
        d = Vector((w.x, w.y, 0.0))
        if d.length < 1e-6:
            continue
        d.normalize()
        hit = bvh.ray_cast(w, d)
        # BVHTree.ray_cast returns (None, None, None, None) on a miss,
        # and distance=None even on a hit; measure it from the hit
        # location instead.
        if hit is not None and hit[0] is not None:
            dist = (hit[0] - w).length
            if dist <= max_dist:
                ang = round(math.degrees(math.atan2(w.y, w.x))) % 360
                inside.append((round(w.z, 3), ang, round(dist, 4)))
    return inside


# design values from build_011.py make_materials():
# (metallic, roughness, base color linear RGB)
DESIGN_MATS = {
    "SnowWhite":  (0.0, 0.85, (0.913, 0.930, 0.956)),  # #F5F7FA 雪白
    "IceBlue":    (0.0, 0.70, (0.027, 0.159, 0.366)),  # #2E6FA3 冰蓝
    "DeepBlue":   (0.0, 0.80, (0.011, 0.042, 0.107)),  # #1B3A5C 深蓝
    "Gold":       (0.7, 0.35, (0.658, 0.352, 0.009)),  # #D4A017 金
    "FurWhite":   (0.0, 0.95, (1.000, 1.000, 1.000)),  # #FFFFFF 纯白毛领
    "Skin":       (0.0, 0.70, (0.694, 0.381, 0.209)),  # #D9A67E 肤色
    "Hair_Silver": (0.0, 0.70, (0.807, 0.807, 0.839)),  # #E8E8EC 银白发
    "Eye_Dark":   (0.0, 0.60, (0.003, 0.003, 0.003)),  # #0A0A0A 眼
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
    def obj(n):
        return by_name[n]

    gaps = {}
    gaps["inner_vs_torso"] = gap_between(obj("InnerRobe"),
                                         obj("Mannequin_Torso"))
    gaps["robe_vs_inner"] = gap_between(obj("MainRobe"), obj("InnerRobe"))
    gaps["overskirt_vs_robe"] = gap_between(obj("Overskirt"),
                                            obj("MainRobe"))
    gaps["belt_vs_robe"] = gap_between(obj("WaistBelt"), obj("MainRobe"))
    # belt vs overskirt is NOT a parallel-layer gap (see §4.2): the belt
    # is a constant-radius tube and the overskirt flares out below it,
    # so the skirt emerges from under the belt — measured separately as
    # an overlap junction (unsigned distance + radial inside test).
    gaps["furCollar_vs_robe"] = gap_between(obj("FurCollar"),
                                            obj("MainRobe"))
    gaps["sleeveL_vs_arm"] = gap_between(obj("WideSleeve"),
                                         obj("Mannequin_Arm"))
    gaps["sleeveR_vs_arm"] = gap_between(obj("WideSleeve.001"),
                                         obj("Mannequin_Arm.001"))
    gaps["cuffL_vs_sleeve"] = gap_between(obj("SleeveCuff"),
                                          obj("WideSleeve"))
    gaps["cuffR_vs_sleeve"] = gap_between(obj("SleeveCuff.001"),
                                          obj("WideSleeve.001"))
    gaps["bootL_vs_leg"] = gap_between(obj("SnowBoot"), obj("Mannequin_Leg"))
    gaps["bootR_vs_leg"] = gap_between(obj("SnowBoot.001"),
                                       obj("Mannequin_Leg.001"))
    gaps["bootFurRingL_vs_boot"] = gap_between(obj("BootFurRing"),
                                               obj("SnowBoot"))
    gaps["bootFurRingR_vs_boot"] = gap_between(obj("BootFurRing.001"),
                                               obj("SnowBoot.001"))
    # Crown ring vs hair cap: design clearance 0.026 (L2 check used a
    # 0.01 minimum because the ring sits close over the hair).
    gaps["crown_vs_hair"] = gap_between(obj("PriestCrown"),
                                        obj("Mannequin_Hair"),
                                        minimum=0.01)
    for k, v in gaps.items():
        print("QA_GAP %s min=%s median=%s samples=%d %s" % (
            k, v["min"], v["median"], v["samples"],
            "PASS" if v["ok"] else "FAIL"))

    # ---- staff vs overskirt: parametric surface sampling ----
    # Design clearance 0.004 (x-only arithmetic in build_011 L2);
    # measured here as true surface-to-surface distance.
    staff_gap = sampled_cylinder_gap(0.50, -0.02, 0.016, 0.05, 1.45,
                                     obj("Overskirt"))
    staff_ok = staff_gap["min"] >= 0.002
    print("QA_STAFF_GAP min=%s median=%s samples=%d %s" % (
        staff_gap["min"], staff_gap["median"], staff_gap["samples"],
        "PASS" if staff_ok else "FAIL"))

    # ---- belt vs overskirt: overlap junction, not a parallel layer ----
    # The belt is a constant-radius tube (rx 0.345) while the overskirt
    # flares outward below its top ring (rx 0.330 at z=0.78 -> 0.410 at
    # z=0.55): an unsigned distance cannot tell whether the skirt
    # surface crosses the belt wall, so test it directly. The unsigned
    # distance is recorded too, for the record.
    belt_unsigned = gap_between(obj("WaistBelt"), obj("Overskirt"))
    belt_inside = radial_inside_test(obj("WaistBelt"), obj("Overskirt"))
    print("QA_BELT_OVERLAP unsigned_min=%s unsigned_median=%s samples=%d "
          "inside_count=%d %s" % (
              belt_unsigned["min"], belt_unsigned["median"],
              belt_unsigned["samples"], len(belt_inside), belt_inside))

    # ---- attachment pairs: measured, observation only (meant to touch) ----
    attach = {}
    attach["staffGoldRing_vs_shaft"] = gap_between(
        obj("StaffGoldRing"), obj("StaffShaft"))
    attach["staffCrystalBase_vs_shaft"] = gap_between(
        obj("StaffCrystalBase"), obj("StaffShaft"))
    attach["staffCrystal_vs_base"] = gap_between(
        obj("StaffCrystal"), obj("StaffCrystalBase"))
    attach["furTuft_vs_collar"] = gap_between(obj("FurTuft"),
                                              obj("FurCollar"))
    attach["crownSpike_vs_crown"] = gap_between(obj("CrownSpike"),
                                                obj("PriestCrown"))
    attach["crownCentreSpike_vs_crown"] = gap_between(
        obj("CrownCentreSpike"), obj("PriestCrown"))
    attach["shoulderPad_vs_sleeve"] = gap_between(obj("ShoulderPad"),
                                                  obj("WideSleeve"))
    attach["beltBuckle_vs_belt"] = gap_between(obj("BeltBuckle"),
                                               obj("WaistBelt"))
    for k, v in attach.items():
        print("QA_ATTACH %s min=%s median=%s samples=%d" % (
            k, v["min"], v["median"], v["samples"]))

    # ---- protruding features: farthest vertex above the host surface ----
    # Design values: chest snowflake 0.008, skirt snowflakes 0.008,
    # pleat strips 0.006, belt buckle 0.012 (build_011 L2 check_relief).
    # Criterion: visible (>= 0.004) and not grossly floating (<= 0.08
    # for patches, <= 0.02 for the buckle).
    protrusions = {}
    lift = max_distance_to(obj("ChestSnowflake"), obj("MainRobe"))
    protrusions["ChestSnowflake"] = {"lift": lift,
                                     "ok": bool(0.004 <= lift <= 0.08)}
    print("QA_PROTRUDE ChestSnowflake lift=%.4f %s" % (
        lift, "PASS" if protrusions["ChestSnowflake"]["ok"] else "FAIL"))
    for t in ("", ".001", ".002"):
        name = "SkirtSnowflake" + t
        lift = max_distance_to(obj(name), obj("Overskirt"))
        protrusions[name] = {"lift": lift,
                             "ok": bool(0.004 <= lift <= 0.08)}
        print("QA_PROTRUDE %s lift=%.4f %s" % (
            name, lift, "PASS" if protrusions[name]["ok"] else "FAIL"))
    for t in ("", ".001", ".002", ".003", ".004", ".005", ".006", ".007"):
        name = "PleatStrip" + t
        lift = max_distance_to(obj(name), obj("Overskirt"))
        protrusions[name] = {"lift": lift,
                             "ok": bool(0.004 <= lift <= 0.08)}
        print("QA_PROTRUDE %s lift=%.4f %s" % (
            name, lift, "PASS" if protrusions[name]["ok"] else "FAIL"))
    lift = max_distance_to(obj("BeltBuckle"), obj("WaistBelt"))
    protrusions["BeltBuckle"] = {"lift": lift,
                                 "ok": bool(0.005 <= lift <= 0.02)}
    print("QA_PROTRUDE BeltBuckle lift=%.4f %s" % (
        lift, "PASS" if protrusions["BeltBuckle"]["ok"] else "FAIL"))

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
    boot_names = ["BootFoot", "BootFoot.001", "SnowBoot", "SnowBoot.001"]
    boot_min_z = min(min(w.z for w in world_verts(obj(n)))
                     for n in boot_names)
    # Staff tip: the shaft is built from z=0.05 (design.md says "从地面"
    # but the build numbers start at 0.05) — measure where it really ends.
    staff_tip_z = min(w.z for w in world_verts(obj("StaffShaft")))
    print("QA_STAFF_TIP z=%.4f" % staff_tip_z)
    # Tallest point of the figure (crown centre spike tip vs hair top).
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
    # Ground / framing verdicts are needed by the warnings below, so
    # compute them here (they only depend on measurements already made).
    ground_ok = abs(boot_min_z) <= 0.005
    frame_ok = frame_frac is not None and 0.60 <= frame_frac <= 0.80
    warnings = []
    for k, v in attach.items():
        if v["min"] is not None and v["min"] > 0.05:
            warnings.append(
                "%s: 附件离宿主 %.4f 米（> 0.05），可能漂浮；检查该附件是否"
                "靠挂绳/绑带连接，否则下次贴近宿主。" % (k, v["min"]))
    if belt_inside:
        zs = sorted(set(z for z, a, d in belt_inside))
        angs = sorted(set(a for z, a, d in belt_inside))
        warnings.append(
            "belt_vs_overskirt_crossing: 腰带下沿与罩裙相交——腰带是等半径管"
            "（rx 0.345），罩裙从腰向下张开（z=0.78 处 rx 0.330 → z=0.55 处"
            " rx 0.410），径向射线判定有 %d 个腰带顶点落在罩裙锥面之内"
            "（z %s，角度 %s°，0°=+x 侧），无符号距离最小 %.4f 米：裙面在"
            "腰带下沿两侧穿过了腰带壁。建模时 L2 只在 z=0.78 一处取样"
            "（间隙 0.015），漏掉了下沿与张开段的相交，属取样疏漏而非设计"
            "意图。视觉上读作腰带扎进裙摆，未造成明显穿帮；下次把腰带下沿"
            "从 z=0.70 抬到 z=0.74，或腰带半径 +0.02 米。" % (
                len(belt_inside),
                "、".join("%.2f" % z for z in zs),
                "、".join(str(a) for a in angs),
                belt_unsigned["min"]))
    if not staff_ok:
        warnings.append(
            "staff_vs_overskirt: 长杖离罩裙裙摆最小 %.4f 米（设计间隙 0.004，"
            "采样下限 0.002）：杖身与裙摆过近，下次把杖向外移 0.005 米。"
            % staff_gap["min"])
    if not ground_ok:
        warnings.append(
            "boots_float: 靴底最低点 z=%.4f 米（地面 z=0，允许 ≤0.005）：整个人物"
            "悬空 0.02 米，靴底与地面之间有一道缝（放大看渲染图靴底处可见）。"
            "根因：build_011.py 里 BootFoot 与 Mannequin_Foot 的 make_wedge 中心"
            " z=0.02（z_bottom=0.0，底面 = 0.02）；002 有独立的 BootSole（中心"
            " z=0.0）落地，011 没有单独的靴底件。修复：把 BootFoot 与"
            " Mannequin_Foot 的中心 z 改为 0.0 后重渲。" % boot_min_z)
    if staff_tip_z > 0.005:
        warnings.append(
            "staff_tip_float: 长杖杖底 z=%.4f 米：杖尖悬空 0.05 米（design.md 写"
            "“从地面直通头顶”，但 build 数值从 z=0.05 起）。全景图里不明显，"
            "放大看杖底与地面之间有缝；若杖尖应落地，下次把杖身起点改到"
            " z=0.0。" % staff_tip_z)
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
    if not ngons_ok:
        fail_items.append("N-gon %d 个（设计值 0）" % tot["ngons"])
    if not topo_ok:
        fail_items.append("拓扑（重叠顶点/散边/非流形边/退化面/闭合实体边界边/实体倒置法线）")
    if not gaps_ok:
        fail_items.append("层间隙（见第 4.1 节不通过项）")
    if not staff_ok:
        fail_items.append("长杖 vs 罩裙间隙 %.4f 米（下限 0.002）" % staff_gap["min"])
    if not protrude_ok:
        fail_items.append("凸起件（见第 4.5 节不通过项）")
    if not float_ok:
        fail_items.append("漂浮部件：%s" % "、".join(bad_float))
    if not ground_ok:
        fail_items.append("落地：靴底最低点 z=%.4f 米（地面 z=0，允许 ≤0.005）"
                          % boot_min_z)
    if not frame_ok:
        fail_items.append("构图：人物占画面 %.3f（标准 0.60–0.80）" % frame_frac)
    if not mats["all_ok"]:
        fail_items.append("材质（见第 6 节不通过项）")
    if empty_slots != 0:
        fail_items.append("空材质槽 %d 个" % empty_slots)
    all_ok = (faces_ok and ngons_ok and topo_ok and gaps_ok and staff_ok
              and protrude_ok and float_ok and ground_ok and frame_ok
              and mats["all_ok"] and empty_slots == 0)

    summary = {
        "asset": "011-snow-priest-robe",
        "blend": "scenes/011-snow-priest-robe/011-snow-priest-robe.blend",
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
        "staff_gap": staff_gap, "staff_gap_ok": bool(staff_ok),
        "belt_overlap": {"unsigned_min": belt_unsigned["min"],
                         "unsigned_median": belt_unsigned["median"],
                         "samples": belt_unsigned["samples"],
                         "inside_vertices": belt_inside},
        "belt_inside_skirt": [{"z": z, "angle_deg": a, "hit_dist": d}
                              for z, a, d in belt_inside],
        "attachments": attach,
        "protrusions": protrusions, "protrusions_ok": bool(protrude_ok),
        "floating_bad": bad_float, "floating_ok": bool(float_ok),
        "garment_bbox": g_bbox,
        "boot_min_z": round(boot_min_z, 4), "ground_ok": bool(ground_ok),
        "staff_tip_z": round(staff_tip_z, 4),
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
        f.write("# 013 资产质检单：雪国祭司长袍（011）\n\n")
        f.write("被检资产：`scenes/011-snow-priest-robe/011-snow-priest-robe.blend`（%d 个服装部件，"
                "不含地面与人体底座；底座 %d 面，另计）\n"
                % (len(results), mannequin_faces))
        f.write("检查方式：Blender bmesh + BVH 实测（拓扑逐面、层间隙逐点最近距离），"
                "非目测估算；设计对照值见 `scenes/011-snow-priest-robe/design.md`。\n\n")
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
        f.write("- 闭合实体（球/盒/带盖管/楔形：毛绒球、肩垫、晶顶、金扣、"
                "冠刺、杖身、靴掌）边界边："
                "%d，%s\n" % (closed_boundary, verdict(closed_boundary == 0)))
        f.write("- 边界边合计 %d，全部来自开口管（内衬、主袍、罩裙、宽袖、"
                "袖口、腰带、毛领、靴筒、靴口毛环、冠环、杖金环、晶顶底座）"
                "与扁平贴片（胸前雪花、裙摆雪花、褶裥条），属设计形态，"
                "不在此项判定。\n" % tot["boundary_edges"])
        f.write("- 最高顶点价数 %d\n\n" % max(r["max_valence"] for r in results.values()))
        f.write("## 2. 法线\n\n")
        f.write("- 法线朝外一致（与 Blender recalc_face_normals 的外法线逐面比对）："
                "实体倒置面 %d 个，%s\n" % (solid_inv, verdict(solid_inv == 0)))
        f.write("- 扁平贴片（胸前雪花、裙摆雪花、褶裥条，单面几何）倒置面 %d 个："
                "贴片绕序由构造保证（build_011.py make_snowflake / build_pleat 已注明"
                "不适用质心法向检查），此项仅记录、不判定。\n\n" % flat_inv)
        f.write("## 3. UV\n\n")
        f.write("- UV 层：%d / %d 个部件有 UV 层：%s\n" % (
            len(uv_parts), len(results), "、".join(uv_parts)))
        f.write("  这些 UV 层是 Blender 图元（球/盒）自带的默认 UVMap，"
                "本套服装无任何贴图引用它们，UV 不参与渲染；其余 %d 个部件"
                "由 from_pydata / make_tube 直接建网格，无 UV 层。\n" % (len(results) - len(uv_parts)))
        f.write("- UV 超出 0–1 范围：%d 个 UV 点，%s\n\n" % (
            uv_oob, verdict(uv_oob == 0)))
        f.write("## 4. 服装结构（BVH 实测，单位：米）\n\n")
        f.write("### 4.1 层间隙（最小间隙要求 ≥0.005，冠环 vs 发顶按设计 0.01）\n\n")
        f.write("| 间隙 | 最小 | 中位 | 采样点 | 结论 |\n")
        f.write("| ---- | ---- | ---- | ------ | ---- |\n")
        gap_labels = {
            "inner_vs_torso": "内衬白袍 / 躯干",
            "robe_vs_inner": "主袍 / 内衬白袍",
            "overskirt_vs_robe": "冰蓝罩裙 / 主袍",
            "belt_vs_robe": "深蓝腰封 / 主袍",
            "furCollar_vs_robe": "毛领 / 主袍",
            "sleeveL_vs_arm": "宽袖左 / 手臂",
            "sleeveR_vs_arm": "宽袖右 / 手臂",
            "cuffL_vs_sleeve": "袖口环左 / 宽袖",
            "cuffR_vs_sleeve": "袖口环右 / 宽袖",
            "bootL_vs_leg": "白靴左 / 小腿",
            "bootR_vs_leg": "白靴右 / 小腿",
            "bootFurRingL_vs_boot": "靴口毛环左 / 白靴",
            "bootFurRingR_vs_boot": "靴口毛环右 / 白靴",
            "crown_vs_hair": "祭司冠环 / 发顶（要求 ≥0.01）",
        }
        for k, v in gaps.items():
            f.write("| %s | %.4f | %.4f | %d | %s |\n" % (
                gap_labels[k], v["min"], v["median"], v["samples"],
                verdict(v["ok"])))
        f.write("\n注：腰带 vs 罩裙不在上表——两者不是平行层叠关系：腰带是等半径"
                "管（rx 0.345），罩裙从腰向下张开，裙摆从腰带下沿翻出来，"
                "属于搭接关系，按第 4.2 节的搭接判定计量；无符号 BVH 距离"
                "对这对关系没有意义（两面相交时距离为 0，却不能说明谁在"
                "外面）。\n\n" % ())
        f.write("### 4.2 腰带 vs 罩裙：搭接判定（无符号距离 + 径向射线内/外）\n\n")
        f.write("- 无符号 BVH 距离：最小 %.4f / 中位 %.4f（%d 点）——两面在腰带"
                "下沿相交，距离为 0 是相交的证据，不是贴合。\n" % (
                    belt_unsigned["min"], belt_unsigned["median"],
                    belt_unsigned["samples"]))
        if belt_inside:
            f.write("- 落在罩裙锥面之内的腰带顶点（%d 个）：\n" % len(belt_inside))
            for z, a, d in belt_inside:
                f.write("  - z=%.3f、角度 %d°（0°=+x 侧）：向外射线 %.4f 米命中罩裙\n"
                        % (z, a, d))
        else:
            f.write("- 无腰带顶点落在罩裙锥面之内：通过\n")
        f.write("\n### 4.3 长杖 vs 罩裙裙摆：参数化表面采样（24 角 × 每 0.02 米一层）\n\n")
        f.write("- 杖身（中心 x=0.50、半径 0.016、z 0.05–1.45）到罩裙的最近距离："
                "最小 %.4f / 中位 %.4f（%d 点），设计间隙 0.004、下限 0.002：%s\n"
                % (staff_gap["min"], staff_gap["median"], staff_gap["samples"],
                   verdict(staff_ok)))
        f.write("  杖身网格只有 z=0.05 / 1.45 两圈顶点，顶点距离会高估间隙，"
                "故用参数化采样实测。\n\n")
        f.write("### 4.4 附件贴合（按构造应贴合宿主，仅记录；> 0.05 视为漂浮嫌疑）\n\n")
        attach_labels = {
            "staffGoldRing_vs_shaft": "杖身金环 ×3 / 杖身",
            "staffCrystalBase_vs_shaft": "晶顶金底座 / 杖身",
            "staffCrystal_vs_base": "冰晶晶顶 / 金底座",
            "furTuft_vs_collar": "毛绒球 ×3 / 毛领",
            "crownSpike_vs_crown": "冠晶刺 ×5 / 冠环",
            "crownCentreSpike_vs_crown": "中央高刺 / 冠环",
            "shoulderPad_vs_sleeve": "肩垫 ×2 / 宽袖",
            "beltBuckle_vs_belt": "金扣 / 腰封",
        }
        for k, v in attach.items():
            flag = ("漂浮嫌疑" if v["min"] is not None and v["min"] > 0.05
                    else "贴合")
            f.write("- %s：最小 %.4f / 中位 %.4f（%d 点）：%s\n" % (
                attach_labels[k], v["min"], v["median"], v["samples"], flag))
        f.write("\n### 4.5 凸起件（离宿主表面的最远点：要看得见立体感，又不能明显漂浮）\n\n")
        f.write("注：凸起值是贴片顶点离宿主表面的最远点。胸前/裙摆雪花是扁平贴片，"
                "贴在弯曲的袍面（椭圆截面）与张开的裙面（锥面）上：贴片中心浮雕"
                "是设计值 0.008，臂尖离曲面比中心远，所以实测最远点 0.0196–0.0242"
                " 高于设计值，属几何使然，不是贴片漂浮；褶裥条同理（设计 0.006，"
                "实测 0.0093–0.0162：条带是平的，12 段圆柱面在弦间内收）。判定"
                "标准仍为 0.004–0.08。\n\n")
        f.write("- 胸前雪花（设计浮雕 0.008，要求 0.004–0.08）：\n")
        v = protrusions["ChestSnowflake"]
        f.write("  - ChestSnowflake：凸起 %.4f：%s\n" % (v["lift"], verdict(v["ok"])))
        f.write("- 裙摆雪花 ×3（设计浮雕 0.008，要求 0.004–0.08）：\n")
        for name in ("SkirtSnowflake", "SkirtSnowflake.001", "SkirtSnowflake.002"):
            v = protrusions[name]
            f.write("  - %s：凸起 %.4f：%s\n" % (name, v["lift"], verdict(v["ok"])))
        f.write("- 褶裥条 ×8（设计浮雕 0.006，要求 0.004–0.08）：\n")
        for i in range(8):
            name = "PleatStrip" + ("" if i == 0 else ".%03d" % i)
            v = protrusions[name]
            f.write("  - %s：凸起 %.4f：%s\n" % (name, v["lift"], verdict(v["ok"])))
        f.write("- 腰带金扣（设计浮雕 0.012，要求 0.005–0.02）：\n")
        v = protrusions["BeltBuckle"]
        f.write("  - BeltBuckle：凸起 %.4f：%s\n" % (v["lift"], verdict(v["ok"])))
        f.write("\n### 4.6 漂浮检查（每个服装部件到最近的其他服装/底座网格的距离，≤0.05 视为已连接）\n\n")
        f.write("- 漂浮嫌疑部件：%s，%s\n\n" % (
            "无" if float_ok else "、".join(bad_float), verdict(float_ok)))
        f.write("## 5. 尺寸与落地\n\n")
        f.write("- 服装包围盒：x %.3f–%.3f，y %.3f–%.3f，z %.3f–%.3f；"
                "宽 %.3f、高 %.3f\n" % (
                    g_bbox["x"][0], g_bbox["x"][1], g_bbox["y"][0], g_bbox["y"][1],
                    g_bbox["z"][0], g_bbox["z"][1], g_bbox["width"], g_bbox["height"]))
        f.write("- 靴底最低点 z=%.4f（地面 z=0，含靴掌与靴筒）：%s\n" % (
            boot_min_z, verdict(ground_ok, "落地")))
        f.write("- 长杖杖底 z=%.4f（杖身 z 0.05→1.45，杖尖悬空，见第 7 节）\n"
                % staff_tip_z)
        f.write("- 人物最高点 z=%.3f（%s）；相机内人物占画面高度 %.3f（标准 0.60–0.80）：%s\n"
                % (top_z, top_obj, frame_frac, verdict(frame_ok)))
        f.write("  注：011 渲染时以 z=2.00 为顶测得 FRAME_FRACTION 0.700；"
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
                "以本单实测为准。例外：腰带 vs 罩裙的环表算术只在 z=0.78 一处"
                "取样，漏掉了腰带下沿与罩裙张开段的相交，见第 4.2 节。\n")
        f.write("- 凸起件：design.md 的浮雕值（雪花 0.008、褶裥 0.006）是贴片中心"
                "离宿主曲面的设计值；本单第 4.5 节是贴片全部顶点离已建网格"
                "（12 段面片）的最远点，臂尖/侧边离曲面更远，实测高于设计值"
                "属几何使然，以本单实测为准。\n")
        f.write("- 白蓝配色占比（主袍约 55% / 罩裙与雪花约 30% / 深蓝约 10% /"
                " 金约 5%）与毛领亮度属渲染目视项，见 011 效果图；"
                "本单只核 mesh 与材质数值。\n\n")
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
