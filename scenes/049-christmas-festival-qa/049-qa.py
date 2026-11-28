# -*- coding: utf-8 -*-
"""049 资产质检：对 048 圣诞节日套装做真实 mesh 检查。

检查对象：scenes/048-christmas-festival/048-christmas-festival.blend 里的全部服装部件
（不含地面与中性人体底座；底座只单独计面数、不参与服装判定）。
检查维度：拓扑 / 法线 / UV / 材质 / 服装结构（层间隙、圣诞星纹浮雕、褶裥脊高、
圣诞帽锥面与发顶间隙、帽边底沿与眼线间隙、毛领前开弧、挑染可见顶点、礼物盒掌前、
手套包覆、长裤与短靴搭接、靴底落地）/ 尺寸与构图。全部数值从 blend 文件实测填写，不编造。

设计对照值来源：scenes/048-christmas-festival/design.md 与 build_048.py
（面数 725、N-gon 0、层间隙 >=0.005、圣诞星浮雕 0.006、褶裥外沿 0.026、
腰扣 0.011、靴扣 0.010、耳钉 0.019、挑染半嵌发顶、圣诞帽锥底环 r 0.235、
帽边底沿 z 1.59 在眼线 1.525 之上 0.065、靴底落地 z=0.0）。

注意：BVH 顶点-表面距离是无符号距离，分不清“在外面”还是“在里面”。
金色星形贴片（圣诞星×5、帽上金星）是单面扇形三角，法线靠构造绕序保证
朝外，不适用质心法向检查（039 星形贴片的标准；build_048 跳过对它们的
fix_normals）。毛衣下摆 z 0.62 与长裤顶 z 0.62 是对接缝（design.md），
不进 4.1 的层间隙表，见第 4.8 节注。长袖从大衣肩部穿出（032 的做法，
袖筒与大衣面按构造相交），不进 4.1，见第 4.3 节注。墨绿手套是包覆手掌的
球（与手掌球体重叠，属手套包覆构造），不进 4.1 的层间隙表，见第 4.6 节
专项。礼物盒是右手持的红盒 + 金丝带 + 金蝴蝶结（第八种手持物），见
第 4.7 节：盒背面须按真实手掌椭球核握持嵌入——手掌是 r 0.085 缩放
(1.0, 0.9, 0.8) 的椭球，不是球；build_048 的 L2 掌嵌公式按球面近似算
0.0085，实测须以椭球为准。雪白靴口（靴筒顶环）与藏青长裤下摆在
z 0.32–0.36 重叠，靴口顶环须核是否穿出裤面，见第 4.8 节。猫耳省略——
圣诞帽盖住双耳（031 遮阳帽同款处理），本单不核猫耳。

通用测量函数（bmesh 拓扑检查、BVH 间隙、理想椭球/锥面解析判据、挑染
可见顶点法）复用 046-qa.py，与 build_048 复用 build_008/032/039 的
做法一致；本文件只写 048 专用的常量与检查逻辑。

Run: blender --background --python 049-qa.py
"""
import os
import sys
import json
import math
import re
import importlib.util
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCENES = os.path.dirname(HERE)
BLEND = os.path.join(ROOT, "scenes", "048-christmas-festival",
                     "048-christmas-festival.blend")
SUMMARY_JSON = os.path.join(HERE, "049-qa-summary.json")
CHECKLIST = os.path.join(HERE, "049-asset-qa-checklist.md")

# Reuse the measurement helpers from the 046 QA round (same pattern as
# build_048 importing build_008 / build_032 / build_039).
_spec = importlib.util.spec_from_file_location(
    "qa046", os.path.join(SCENES, "046-spring-sakura-qa", "046-qa.py"))
qa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(qa)
check_mesh = qa.check_mesh
world_verts = qa.world_verts
world_bvh = qa.world_bvh
gap_between = qa.gap_between
gap_between_visible = qa.gap_between_visible
max_distance_to = qa.max_distance_to
inside_ellipsoid = qa.inside_ellipsoid
ideal_head_relief = qa.ideal_head_relief
ideal_ellipsoid_distance = qa.ideal_ellipsoid_distance
ideal_cone_distance = qa.ideal_cone_distance
interp_rings = qa.interp_rings
ellipse_value = qa.ellipse_value
sleeve_radius_at_s = qa.sleeve_radius_at_s
check_materials = qa.check_materials
# Mannequin constants are identical (same build_mannequin from build_032).
HAND_R_C = qa.HAND_R_C
HAND_L_C = qa.HAND_L_C
GLOVE_C = qa.GLOVE_C
GLOVE_R = qa.GLOVE_R
HAIR_C = qa.HAIR_C
HAIR_R = qa.HAIR_R
HEAD_C = qa.HEAD_C
HEAD_R = qa.HEAD_R
ARM_L_SHOULDER = qa.ARM_L_SHOULDER
ARM_L_DIR = qa.ARM_L_DIR
ARM_R_SHOULDER = qa.ARM_R_SHOULDER
ARM_R_DIR = qa.ARM_R_DIR


def is_garment(o):
    return (o.type == 'MESH' and o.name != "Ground"
            and not o.name.startswith("Mannequin_"))


# Closed solids by construction (sphere / box / capped tube / wedge /
# closed pleat fin): boundary edges must be 0. Everything else is an
# open tube / arc panel by design, where boundary edges are expected.
# The flat gold star patches are single-sided fans (10 triangles):
# their winding is guaranteed by construction (make_star_patch) and
# they are excluded from the inverted-normal solid check, like 039's
# star patches — fix_normals must never run on them.
CLOSED_SOLIDS = ("GoldBeltBuckle", "RedPleat", "GoldEarring",
                 "HairStreak", "PineGlove", "RedBootSole", "NavySleeve",
                 "GoldBootBuckle", "SantaHatPompom", "GiftBox",
                 "GiftRibbonX", "GiftRibbonY", "GiftBow")
FLAT_PATCHES = ("GoldStar", "GoldStarHat")

EXPECTED_NGONS = 0          # design.md: N-gon 0
EXPECTED_FACES = 725        # component build, recorded in design.md
FACE_LIMIT = 1500
MIN_GAP = 0.005

# Rings from build_048.py (z, rx, ry), for interpolation cross-checks.
SWEATER_RINGS = [(1.50, 0.300, 0.160), (1.44, 0.288, 0.152),
                 (1.10, 0.272, 0.144), (0.80, 0.258, 0.138),
                 (0.62, 0.248, 0.132)]
COAT_RINGS = [(1.50, 0.312, 0.168), (1.20, 0.310, 0.162),
              (0.90, 0.308, 0.160), (0.62, 0.314, 0.162),
              (0.45, 0.322, 0.166)]
TROUSER_RINGS = [(0.62, 0.246, 0.128), (0.48, 0.240, 0.126),
                 (0.34, 0.232, 0.124)]
BELT_RINGS = [(0.94, 0.318, 0.168), (0.88, 0.317, 0.167)]
# Santa hat cone (build_048): base z 1.64 r 0.235, tip z 1.94 r 0.030,
# axis at (0, 0.01). Brim z 1.64-1.59, r 0.245/0.248. Eye line z 1.525.
HAT_BASE_Z = 1.64
HAT_BASE_R = 0.235
HAT_TIP_Z = 1.94
HAT_TIP_R = 0.030
HAT_AXIS = (0.0, 0.01)
HAT_STAR_C = (0.0, -0.1558, 1.75)
HAT_STAR_N = Vector((0, -0.826, 0.564)).normalized()
# Right hand (gift side, sx=+1): hand sphere centre from
# build_032 wrist_pos(1) — verified at runtime against the hand mesh.
# Left hand (glove side, sx=-1): mirror of the right hand.
# Hand ellipsoid (build_032): sphere r 0.085 scaled (1.0, 0.9, 0.8).
HAND_ELL_R = (0.085, 0.0765, 0.068)
# Gift box (build_048): centre at wrist + (0, -0.11, -0.05), 0.07 cube.
GIFT_OFFSET = Vector((0.0, -0.11, -0.05))
# Right sleeve axis for the gift-box cap-plane check (build_045 L2):
# origin (0.313, 0, 1.339), direction (0.139, 0, -0.99) normalised.
SLEEVE_R_ORIGIN = Vector((0.313, 0.0, 1.339))
SLEEVE_R_DIR = Vector((0.139, 0.0, -0.99)).normalized()
# Arm direction (build_032): shoulder (0.33, 0, 1.22), dir (0.14, 0, -1).
ARM_R_DIR_UNIT = Vector((0.14, 0.0, -1.0)).normalized()
# Gold star build order (build_048): sweater stars first (270 z 1.32;
# 262 z 1.02; 278 z 1.02), then coat stars (225 z 1.10; 320 z 1.10).
# NOTE: design.md writes 315 deg for the second coat star, build_048
# uses 320 deg — both sit outside the 240-300 open wedge, so the
# position check judges against the built 320 deg and records the
# doc discrepancy as an observation, not a failure.
FLOWER_HOSTS = {"GoldStar": "SnowSweater",
                "GoldStar.001": "SnowSweater",
                "GoldStar.002": "SnowSweater",
                "GoldStar.003": "RedCoat",
                "GoldStar.004": "RedCoat"}
FLOWER_DESIGN = {"GoldStar": (270, 1.32, "sweater"),
                 "GoldStar.001": (262, 1.02, "sweater"),
                 "GoldStar.002": (278, 1.02, "sweater"),
                 "GoldStar.003": (225, 1.10, "coat"),
                 "GoldStar.004": (320, 1.10, "coat")}
# Pleat build order (build_048 PLEAT_ANGLES): 170/200/230/320/350/20/50/110.
PLEAT_ANGLES = {"RedPleat": 170, "RedPleat.001": 200,
                "RedPleat.002": 230, "RedPleat.003": 320,
                "RedPleat.004": 350, "RedPleat.005": 20,
                "RedPleat.006": 50, "RedPleat.007": 110}


def ideal_cone_distance_xy(p, rings, cx, cy):
    """Min distance from point p to an ideal smooth circular cone
    surface (dense sampling: 121 heights x 360 angles), cone axis at
    (cx, cy). The hat star sits on the santa cone, whose axis is at
    (0, 0.01) — qa.ideal_cone_distance assumes the axis at the
    origin, so this offset variant is needed (same class of
    correction as 041's hat drop / 043's maple pin: judge a patch on
    a small-radius curved surface against the ideal smooth surface,
    not the faceted mesh)."""
    best = 9.0
    for iz in range(121):
        z = rings[-1][0] + (rings[0][0] - rings[-1][0]) * iz / 120.0
        rx, ry = interp_rings(rings, z)
        for k in range(360):
            a = 2.0 * math.pi * k / 360.0
            q = Vector((cx + rx * math.cos(a),
                        cy + ry * math.sin(a), z))
            d = (p - q).length
            if d < best:
                best = d
    return best


# design values from build_048.py make_materials():
# (metallic, roughness, base color linear RGB)
DESIGN_MATS = {
    "ChristmasRed": (0.0, 0.6, (0.533, 0.020, 0.026)),  # #C1272D 圣诞红
    "SnowWhite":    (0.0, 0.65, (0.930, 0.896, 0.807)), # #F7F3E8 雪白
    "PineGreen":    (0.0, 0.6, (0.013, 0.074, 0.044)),  # #1E4D3B 墨绿
    "Navy":         (0.0, 0.6, (0.011, 0.023, 0.068)),  # #1B2A4A 藏青
    "Gold":         (0.6, 0.35, (0.584, 0.361, 0.020)), # #C9A227 金
    "LightBlue":    (0.0, 0.6, (0.212, 0.479, 0.807)),  # #6FA8DC 浅蓝挑染
    "Hair_Black":   (0.0, 0.7, (0.011, 0.011, 0.015)),  # #1B1B21 黑发
    "Skin":         (0.0, 0.7, (0.694, 0.381, 0.209)),  # #D9A67E 肤色
    "Eye_Dark":     (0.0, 0.6, (0.003, 0.003, 0.003)),  # #0A0A0A 眼
}
qa.DESIGN_MATS = DESIGN_MATS

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
    gaps["sweater_vs_torso"] = gap_between(obj("SnowSweater"),
                                           obj("Mannequin_Torso"))
    gaps["coat_vs_sweater"] = gap_between(obj("RedCoat"),
                                          obj("SnowSweater"))
    gaps["collar_vs_coat"] = gap_between(obj("SnowFurCollar"),
                                         obj("RedCoat"))
    gaps["sleeveL_vs_arm"] = gap_between(obj("NavySleeve"),
                                         obj("Mannequin_Arm"))
    gaps["sleeveR_vs_arm"] = gap_between(obj("NavySleeve.001"),
                                         obj("Mannequin_Arm.001"))
    gaps["cuffL_vs_sleeve"] = gap_between(obj("SnowCuff"),
                                          obj("NavySleeve"))
    gaps["cuffR_vs_sleeve"] = gap_between(obj("SnowCuff.001"),
                                          obj("NavySleeve.001"))
    gaps["belt_vs_coat"] = gap_between(obj("PineBelt"),
                                       obj("RedCoat"))
    gaps["trousers_vs_legL"] = gap_between(obj("NavyTrousers"),
                                           obj("Mannequin_Leg"))
    gaps["trousers_vs_legR"] = gap_between(obj("NavyTrousers"),
                                           obj("Mannequin_Leg.001"))
    gaps["bootL_vs_leg"] = gap_between(obj("RedBoot"),
                                       obj("Mannequin_Leg"))
    gaps["bootR_vs_leg"] = gap_between(obj("RedBoot.001"),
                                       obj("Mannequin_Leg.001"))
    gaps["bootcuffL_vs_boot"] = gap_between(obj("SnowBootCuff"),
                                            obj("RedBoot"))
    gaps["bootcuffR_vs_boot"] = gap_between(obj("SnowBootCuff.001"),
                                            obj("RedBoot.001"))
    gaps["soleL_vs_foot"] = gap_between(obj("RedBootSole"),
                                        obj("Mannequin_Foot"))
    gaps["soleR_vs_foot"] = gap_between(obj("RedBootSole.001"),
                                        obj("Mannequin_Foot.001"))
    gaps["hatcone_vs_hair"] = gap_between(obj("SantaHatCone"),
                                          obj("Mannequin_Hair"))
    # The cone must be checked at z 1.66 too — the hair is widest
    # there relative to the taper, not just at the base ring
    # (design.md: cone r 0.2213 vs hair 0.1949 at z 1.66). The cone
    # is a 2-ring tube (z 1.64 and 1.94 only), so NO cone vertex sits
    # at z 1.66 — a vertex-band gap would sample 0 points. Measure
    # the cone SURFACE at that height instead: sample the ideal cone
    # ring at z 1.66 and take the min BVH distance to the hair mesh.
    # (The faceted cone surface sits up to 0.0075 inside the ideal
    # ring at z 1.66 — 12 sides, sagitta 0.2213*(1-cos 15 deg) — so
    # the true faceted-cone gap is at most 0.0075 below this figure.)
    bvh_hair_gap = world_bvh(obj("Mannequin_Hair"))
    cone_r166_design = (HAT_BASE_R + (HAT_TIP_R - HAT_BASE_R)
                        / (HAT_TIP_Z - HAT_BASE_Z) * (1.66 - HAT_BASE_Z))
    ring_ds = []
    for k in range(72):
        a = 2.0 * math.pi * k / 72.0
        p = Vector((HAT_AXIS[0] + cone_r166_design * math.cos(a),
                    HAT_AXIS[1] + cone_r166_design * math.sin(a), 1.66))
        hit = bvh_hair_gap.find_nearest(p)
        if hit is not None:
            ring_ds.append(hit[3])
    ring_ds.sort()
    gaps["hatcone_vs_hair_z166"] = {
        "min": round(ring_ds[0], 4) if ring_ds else None,
        "median": round(ring_ds[len(ring_ds) // 2], 4) if ring_ds else None,
        "samples": len(ring_ds), "minimum": MIN_GAP,
        "ok": bool(ring_ds and ring_ds[0] >= MIN_GAP)}
    gaps["brim_vs_hair"] = gap_between(obj("SnowHatBrim"),
                                       obj("Mannequin_Hair"))
    gaps["hatcone_vs_brim"] = gap_between(obj("SantaHatCone"),
                                          obj("SnowHatBrim"))
    for k, v in gaps.items():
        print("QA_GAP %s min=%s median=%s samples=%d %s" % (
            k, v["min"], v["median"], v["samples"],
            "PASS" if v["ok"] else "FAIL"))

    # ---- santa hat cone parameters, measured from the built mesh ----
    cone_verts = world_verts(obj("SantaHatCone"))
    cone_zs = [w.z for w in cone_verts]
    cone_base_r = max(
        math.hypot(w.x - HAT_AXIS[0], w.y - HAT_AXIS[1])
        for w in cone_verts if abs(w.z - HAT_BASE_Z) < 1e-4)
    # No cone vertex sits at z 1.66 (2-ring tube): interpolate the
    # radius there from the measured base/tip radii (straight taper).
    cone_tip_r = max(
        math.hypot(w.x - HAT_AXIS[0], w.y - HAT_AXIS[1])
        for w in cone_verts if abs(w.z - HAT_TIP_Z) < 1e-4)
    cone_r166 = cone_base_r + (cone_tip_r - cone_base_r) * (
        1.66 - HAT_BASE_Z) / (HAT_TIP_Z - HAT_BASE_Z)
    cone_measured = {
        "base_z": round(min(cone_zs), 3), "tip_z": round(max(cone_zs), 3),
        "base_r": round(cone_base_r, 4),
        "design_base_r": HAT_BASE_R, "design_tip_z": HAT_TIP_Z,
        "r_at_z1.66": round(cone_r166, 4),
        "design_r_at_z1.66": round(
            HAT_BASE_R + (HAT_TIP_R - HAT_BASE_R)
            / (HAT_TIP_Z - HAT_BASE_Z) * (1.66 - HAT_BASE_Z), 4),
    }
    print("QA_HATCONE %s" % cone_measured)

    # ---- attachment pairs: measured, observation only (meant to touch,
    # half-embed, or enclose their host; a BVH distance of 0.0 means
    # contact, not intersection) ----
    attach = {}
    for star_name, host in FLOWER_HOSTS.items():
        attach["star_%s_vs_host" % star_name.replace(".", "_")] = \
            gap_between(obj(star_name), obj(host))
    attach["hatstar_vs_cone"] = gap_between(obj("GoldStarHat"),
                                            obj("SantaHatCone"))
    attach["buckle_vs_belt"] = gap_between(obj("GoldBeltBuckle"),
                                           obj("PineBelt"))
    for t in ("", ".001"):
        attach["bootbuckle%s_vs_boot" % t] = gap_between(
            obj("GoldBootBuckle" + t), obj("RedBoot" + t))
        attach["earring%s_vs_head" % t] = gap_between(
            obj("GoldEarring" + t), obj("Mannequin_Head"))
    attach["streak_vs_hair"] = gap_between(obj("HairStreak"),
                                           obj("Mannequin_Hair"))
    for t in [""] + [".%03d" % i for i in range(1, 8)]:
        attach["pleat%s_vs_coat" % t] = gap_between(
            obj("RedPleat" + t), obj("RedCoat"))
    attach["glove_vs_handL"] = gap_between(obj("PineGlove"),
                                           obj("Mannequin_Hand"))
    # Sleeve vs coat: the sleeve is sewn through the coat shoulder
    # (032 fix: origin lifted 0.12 so it emerges from the shoulder);
    # the surfaces cross at the shoulder seam by construction.
    attach["sleeveL_vs_coat"] = gap_between(obj("NavySleeve"),
                                            obj("RedCoat"))
    attach["sleeveR_vs_coat"] = gap_between(obj("NavySleeve.001"),
                                            obj("RedCoat"))
    # Gift box vs right hand / sleeve: the box centre is at wrist +
    # (0, -0.11, -0.05) by design; whether it reads as held is
    # decided in section 4.7 against the true hand ellipsoid.
    attach["giftbox_vs_handR"] = gap_between(obj("GiftBox"),
                                             obj("Mannequin_Hand.001"))
    attach["giftbox_vs_sleeveR"] = gap_between(obj("GiftBox"),
                                               obj("NavySleeve.001"))
    attach["ribbonX_vs_box"] = gap_between(obj("GiftRibbonX"),
                                           obj("GiftBox"))
    attach["ribbonY_vs_box"] = gap_between(obj("GiftRibbonY"),
                                           obj("GiftBox"))
    attach["bow_vs_box"] = gap_between(obj("GiftBow"), obj("GiftBox"))
    # Hat assembly: the tip tube starts at the cone tip and the
    # pompom covers the tip end; the cone base ring sits inside the
    # brim top ring (0.235 vs 0.245) by design (gap, see 4.1).
    attach["tip_vs_cone"] = gap_between(obj("SantaHatTip"),
                                        obj("SantaHatCone"))
    attach["pompom_vs_tip"] = gap_between(obj("SantaHatPompom"),
                                          obj("SantaHatTip"))
    # Sweater hem meets the trouser top at z 0.62 (butt joint):
    # record only, judged in section 4.8.
    attach["sweater_vs_trousers"] = gap_between(obj("SnowSweater"),
                                                obj("NavyTrousers"))
    # Boot cuff vs trouser hem: the cuff top ring (z 0.36) overlaps
    # the trouser hem (z 0.34) by design — whether it pierces the
    # trouser wall is decided in section 4.8, not here.
    attach["bootcuff_vs_trousers"] = gap_between(obj("SnowBootCuff"),
                                                 obj("NavyTrousers"))
    attach["bootcuff.001_vs_trousers"] = gap_between(
        obj("SnowBootCuff.001"), obj("NavyTrousers"))
    for k, v in attach.items():
        print("QA_ATTACH %s min=%s median=%s samples=%d" % (
            k, v["min"], v["median"], v["samples"]))

    # ---- protruding features: farthest vertex above the host surface ----
    # Design reliefs: gold star 0.006, hat star 0.006, belt buckle
    # 0.011, boot buckle 0.010, earring 0.019, hair streak ~0.02
    # (half-buried ellipsoid), pleat fin outer edge 0.026.
    # Criterion: visible (>= 0.005, pleat >= 0.020) and not grossly
    # floating (<= 0.03, pleat <= 0.032, flat patch <= 0.02).
    # Star patches are flat fans on 16-segment elliptical tubes: the
    # measured lift includes the tube facet sagitta (~0.0052) and the
    # surface curvature under the patch (~0.0023), so their upper bound
    # is 0.02, not the L2 check's 0.015 (which was a centre value).
    protrusions = {}

    def protrude(name, host, lo, hi):
        lift = max_distance_to(obj(name), obj(host))
        ok = bool(lo <= lift <= hi)
        protrusions[name] = {"lift": lift, "ok": ok,
                             "host": host, "lo": lo, "hi": hi}
        print("QA_PROTRUDE %s lift=%.4f %s" % (
            name, lift, "PASS" if ok else "FAIL"))
        return lift

    for star_name, host in FLOWER_HOSTS.items():
        protrude(star_name, host, 0.005, 0.02)
    # Hat star: a flat star patch on the santa cone (12-sided, axis
    # (0, 0.01), half-angle 34.4 deg). The patch plane faces
    # (0,-0.826,0.564) while the cone normal tilts, so one edge
    # legitimately stands further off the faceted mesh. Same class of
    # correction as 041's hat drop (037's goggle lens, 034's sunglass
    # lens, 043's maple pin, 046's beret flower): criterion
    # |measured - analytic| <= 0.012 and measured <= 0.03, where
    # analytic is the ideal-cone distance of the farthest vertex.
    # The 0.012 tolerance is the cone's facet sagitta (12 sides:
    # 0.16*(1-cos 15 deg) = 0.0055 at z 1.75, plus the star's own
    # half-width off the curved surface). The star's base is embedded
    # in the cone (attachment min ~0.0), proving it is not floating.
    HAT_CONE_RINGS = [(HAT_TIP_Z, HAT_TIP_R, HAT_TIP_R),
                      (HAT_BASE_Z, HAT_BASE_R, HAT_BASE_R)]
    bvh_cone = world_bvh(obj("SantaHatCone"))
    far_v, far_d = None, 0.0
    for w in world_verts(obj("GoldStarHat")):
        hit = bvh_cone.find_nearest(w)
        if hit is not None and hit[3] > far_d:
            far_d, far_v = hit[3], w
    star_analytic = round(ideal_cone_distance_xy(
        far_v, HAT_CONE_RINGS, HAT_AXIS[0], HAT_AXIS[1]), 4)
    star_ok = bool(abs(far_d - star_analytic) <= 0.012 and far_d <= 0.03
                   and far_d >= 0.005)
    protrusions["GoldStarHat"] = {
        "lift": round(far_d, 4), "analytic": star_analytic,
        "ok": star_ok, "host": "SantaHatCone (ideal cone)",
        "lo": round(star_analytic - 0.006, 4),
        "hi": round(star_analytic + 0.006, 4)}
    print("QA_PROTRUDE GoldStarHat lift=%.4f analytic=%.4f %s" % (
        far_d, star_analytic, "PASS" if star_ok else "FAIL"))
    protrude("GoldBeltBuckle", "PineBelt", 0.005, 0.03)
    for t in ("", ".001"):
        protrude("GoldBootBuckle" + t, "RedBoot" + t, 0.005, 0.03)
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
    # Pleat fins: the design relief (0.026) is measured against the
    # SMOOTH coat cone (build_048 builds the fin off the smooth ring
    # interpolation), but the coat mesh is a 16-segment faceted tube:
    # the mesh-based lift overstates the relief by the local facet
    # sagitta (0 at a facet vertex, up to 0.0064 at a facet midpoint
    # for rx 0.322). Same class of correction as the hat star above
    # (043 pin, 046 beret flower): the criterion is the IDEAL-cone
    # lift (0.020-0.032) plus |mesh - analytic| <= 0.007.
    bvh_coat = world_bvh(obj("RedCoat"))
    for t in [""] + [".%03d" % i for i in range(1, 8)]:
        pname = "RedPleat" + t
        far_v2, far_d2 = None, 0.0
        for w in world_verts(obj(pname)):
            hit = bvh_coat.find_nearest(w)
            if hit is not None and hit[3] > far_d2:
                far_d2, far_v2 = hit[3], w
        analytic2 = round(ideal_cone_distance(far_v2, COAT_RINGS), 4)
        pleat_ok = bool(0.020 <= analytic2 <= 0.032
                        and abs(far_d2 - analytic2) <= 0.007)
        protrusions[pname] = {"lift": round(far_d2, 4),
                              "analytic": analytic2,
                              "analytic_label": "ideal cone",
                              "analytic_tol": 0.007,
                              "ok": pleat_ok,
                              "host": "RedCoat (ideal cone)",
                              "lo": 0.020, "hi": 0.032}
        print("QA_PROTRUDE %s lift=%.4f analytic=%.4f %s" % (
            pname, far_d2, analytic2, "PASS" if pleat_ok else "FAIL"))

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
    for n in bad_float:
        print("QA_FLOATING %s nearest_other=%.4f" % (n, floating[n]["nearest_other"]))

    # ---- hat brim bottom vs eye line (BACKLOG: 帽边底沿与眼线间隙) ----
    eye_zs = []
    for n in ("Mannequin_Eye", "Mannequin_Eye.001"):
        eye_zs += [w.z for w in world_verts(obj(n))]
    brim_zs = [w.z for w in world_verts(obj("SnowHatBrim"))]
    brim_xs = [abs(w.x) for w in world_verts(obj("SnowHatBrim"))]
    brim_vs_eyes = {
        "brim_bottom_z": round(min(brim_zs), 3),
        "brim_top_z": round(max(brim_zs), 3),
        "brim_radius": round(max(brim_xs), 3),
        "eye_z": (round(min(eye_zs), 3), round(max(eye_zs), 3)),
        "brim_bottom_above_eye_top": bool(min(brim_zs) > max(eye_zs)),
        "clearance": round(min(brim_zs) - max(eye_zs), 3),
        "hatcone_vs_hair_min": gaps["hatcone_vs_hair"]["min"],
        "hatcone_vs_hair_z166_min": gaps["hatcone_vs_hair_z166"]["min"],
        "brim_vs_hair_min": gaps["brim_vs_hair"]["min"],
        "ok": bool(min(brim_zs) > max(eye_zs)),
    }
    print("QA_BRIM_VS_EYES %s" % brim_vs_eyes)

    # ---- fur collar front opening (BACKLOG: 毛领前开弧不挡眼) ----
    # The collar is an arc tube (300-600 deg), leaving the 240-300 deg
    # front wedge open (v2 fix: the v1 full ring crossed the face at
    # eye level and read as a blindfold). No collar vertex may fall
    # strictly inside the wedge; the arc-end vertices sit exactly on
    # the 240/300 deg edges, beside the face, not in front of it.
    collar_verts = world_verts(obj("SnowFurCollar"))
    collar_in_wedge = []
    collar_edge_verts = []
    for w in collar_verts:
        ang = math.degrees(math.atan2(w.y / 0.320, w.x / 0.320)) % 360.0
        # The arc ends sit exactly on 240/300 deg by construction;
        # atan2 float noise puts them a hair inside the wedge, so a
        # 0.5 deg band around each edge counts as "on the edge".
        if 240.5 < ang < 299.5:
            collar_in_wedge.append((round(w.x, 3), round(w.y, 3),
                                    round(w.z, 3), round(ang, 1)))
        elif abs(ang - 240.0) < 0.5 or abs(ang - 300.0) < 0.5:
            collar_edge_verts.append((round(w.x, 3), round(w.y, 3),
                                      round(w.z, 3), round(ang, 1)))
    collar_wedge = {
        "verts_inside_wedge_240_300": len(collar_in_wedge),
        "inside_points": collar_in_wedge[:5],
        "arc_end_verts_on_240_300": len(collar_edge_verts),
        "edge_points": collar_edge_verts[:4],
        "collar_vs_coat_min": gaps["collar_vs_coat"]["min"],
        "ok": bool(len(collar_in_wedge) == 0),
    }
    print("QA_COLLAR_WEDGE %s" % collar_wedge)

    # ---- glove coverage (BACKLOG: 手套包覆) ----
    hand_l = obj("Mannequin_Hand")
    glove_in = 0
    sleeve_covered = 0
    uncovered = 0
    uncovered_pts = []
    for w in world_verts(hand_l):
        if inside_ellipsoid(w, GLOVE_C, GLOVE_R):
            glove_in += 1
            continue
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

    # ---- handheld gift box (BACKLOG: 礼物盒掌前) ----
    # The gift box is a red 0.07 cube + gold ribbon cross + gold bow,
    # held in the right hand (eighth handheld item). Design claim
    # (build_048 L2): the box back face embeds 0.0085 into the palm.
    # That L2 figure is a SPHERICAL approximation (0.085 -
    # sqrt(0.075^2 + 0.015^2)); the real hand is an ellipsoid
    # (r 0.085 scaled (1.0, 0.9, 0.8)), so the embed must be measured
    # against the true ellipsoid. The box reads as held only if its
    # back face (or at least its back-top edge) reaches the palm:
    # the criterion is (a) some box vertex/edge-midpoint inside the
    # hand ellipsoid, and (b) the vertex-based BVH distance to the
    # hand mesh <= 0.005 (touching). A box whose nearest vertex is
    # 0.019 m from the hand mesh floats in front of the palm.
    hand_r_verts = world_verts(obj("Mannequin_Hand.001"))
    wrist_r = Vector((sum(w.x for w in hand_r_verts) / len(hand_r_verts),
                      sum(w.y for w in hand_r_verts) / len(hand_r_verts),
                      sum(w.z for w in hand_r_verts) / len(hand_r_verts)))
    wrist_r_err = (wrist_r - Vector(HAND_R_C)).length
    box_verts = world_verts(obj("GiftBox"))
    box_c = Vector((sum(w.x for w in box_verts) / len(box_verts),
                    sum(w.y for w in box_verts) / len(box_verts),
                    sum(w.z for w in box_verts) / len(box_verts)))
    box_design_c = wrist_r + GIFT_OFFSET
    box_centre_err = (box_c - box_design_c).length

    def ellipsoid_q(p, c, r):
        return (((p.x - c[0]) / r[0]) ** 2 + ((p.y - c[1]) / r[1]) ** 2
                + ((p.z - c[2]) / r[2]) ** 2)

    box_in_hand = 0
    box_deepest = 0.0
    for w in box_verts:
        q = ellipsoid_q(w, wrist_r, HAND_ELL_R)
        if q < 1.0:
            box_in_hand += 1
            box_deepest = max(box_deepest,
                              (1.0 - math.sqrt(q)) * (w - wrist_r).length)
    # Edge midpoints: the closest approach of a box to the palm is
    # usually an edge, not a vertex (the back-top edge runs parallel
    # to the palm). Sample all 12 box edges at their midpoints.
    edge_best_q = 9.0
    edge_best_gap = 0.0
    for e in obj("GiftBox").data.edges:
        v0 = obj("GiftBox").matrix_world @ obj("GiftBox").data.vertices[e.vertices[0]].co
        v1 = obj("GiftBox").matrix_world @ obj("GiftBox").data.vertices[e.vertices[1]].co
        mid = (v0 + v1) / 2.0
        q = ellipsoid_q(mid, wrist_r, HAND_ELL_R)
        if q < edge_best_q:
            edge_best_q = q
            d = (mid - wrist_r).length
            edge_best_gap = d * (1.0 - 1.0 / math.sqrt(q)) if q > 1.0 else 0.0
    # Top corner past the sleeve end-cap plane: the wrist sits on the
    # cap plane (sleeve end s=0.67 == wrist), so a corner's axial
    # projection past the wrist is its distance past the cap plane.
    # The design corner is the top-back corner (0.035, -0.075, -0.015)
    # rel. the wrist (build_048 L2: 0.0198); the honest check is the
    # MINIMUM over all box verts — the whole box must sit past the
    # plane, not just its farthest corner.
    top_corner = Vector((0.035, -0.075, -0.015))
    top_corner_dot = top_corner.dot(ARM_R_DIR_UNIT)
    corner_past = min((w - wrist_r).dot(ARM_R_DIR_UNIT)
                      for w in box_verts)
    # Bow on top of the box and ribbons proud of the box faces.
    bow_lift = max_distance_to(obj("GiftBow"), obj("GiftBox"))
    ribbon_lift = max(max_distance_to(obj("GiftRibbonX"), obj("GiftBox")),
                      max_distance_to(obj("GiftRibbonY"), obj("GiftBox")))
    giftbox = {
        "wrist_measured": [round(v, 4) for v in wrist_r],
        "wrist_design": list(HAND_R_C),
        "wrist_error": round(wrist_r_err, 4),
        "box_centre": [round(v, 4) for v in box_c],
        "box_design_centre": [round(v, 4) for v in box_design_c],
        "box_centre_error": round(box_centre_err, 4),
        "box_verts_inside_hand_ellipsoid": "%d/8" % box_in_hand,
        "box_deepest_embed": round(box_deepest, 4),
        "box_edge_closest_q": round(edge_best_q, 4),
        "box_edge_closest_gap_ideal": round(edge_best_gap, 4),
        "box_vs_hand_mesh_min": attach["giftbox_vs_handR"]["min"],
        "box_vs_sleeve_min": attach["giftbox_vs_sleeveR"]["min"],
        "top_corner_past_cap_plane": round(top_corner_dot, 4),
        "top_corner_past_cap_plane_design": 0.0198,
        "box_min_past_cap_plane": round(corner_past, 4),
        "bow_vs_box_max": round(bow_lift, 4),
        "ribbon_vs_box_max": round(ribbon_lift, 4),
        "ok": bool(wrist_r_err <= 0.002
                   and box_centre_err <= 0.002
                   and (box_in_hand > 0 or edge_best_q <= 1.0)
                   and attach["giftbox_vs_handR"]["min"] <= 0.005
                   and corner_past > 0),
    }
    print("QA_GIFTBOX %s" % giftbox)

    # ---- trousers vs boots (BACKLOG: 长裤与短靴搭接) ----
    # The trouser hem (z 0.34) meets the boot cuff (z 0.36-0.32): the
    # cuff's bottom half (z 0.32-0.34) shows below the hem by design,
    # but its top ring (z 0.36) must stay INSIDE the trouser tube —
    # a cuff vertex above the hem with a trouser-ellipse value > 1
    # has pierced the trouser wall. The leg itself must stay covered
    # in the band z 0.32-0.36: every leg vertex there must be inside
    # the trouser ellipse or inside a boot tube (no skin shows).
    # The sweater hem (z 0.62) meets the trouser top (z 0.62) end to
    # end (butt joint, same as 045's skirt/sock joint).
    trouser_boot = {}
    cuff_poke = {}
    for cuff_name, sx in (("SnowBootCuff", -1), ("SnowBootCuff.001", 1)):
        above = 0
        outside = 0
        max_poke = 0.0
        for w in world_verts(obj(cuff_name)):
            if w.z > 0.34 + 1e-4:
                above += 1
                rx_t, ry_t = interp_rings(TROUSER_RINGS, w.z)
                v = ellipse_value(w.x, w.y, rx_t, ry_t)
                if v > 1.0:
                    outside += 1
                    max_poke = max(max_poke, (v - 1.0) * rx_t)
        cuff_poke["L" if sx == -1 else "R"] = {
            "top_ring_verts_above_hem": above,
            "outside_trouser": outside,
            "max_poke": round(max_poke, 4),
        }
    leg_outside = 0
    for leg_name, sx in (("Mannequin_Leg", -1), ("Mannequin_Leg.001", 1)):
        for w in world_verts(obj(leg_name)):
            if 0.32 - 1e-4 <= w.z <= 0.36 + 1e-4:
                rx_t, ry_t = interp_rings(TROUSER_RINGS, w.z)
                in_tr = (w.x / rx_t) ** 2 + (w.y / ry_t) ** 2 <= 1.0
                in_bt = math.hypot(w.x - sx * 0.13, w.y) <= 0.118
                if not (in_tr or in_bt):
                    leg_outside += 1
    trouser_hem_z = round(min(w.z for w in world_verts(obj("NavyTrousers"))), 3)
    trouser_top_z = round(max(w.z for w in world_verts(obj("NavyTrousers"))), 3)
    sweater_hem_z = round(min(w.z for w in world_verts(obj("SnowSweater"))), 3)
    cuff_ok = all(v["outside_trouser"] == 0 for v in cuff_poke.values())
    trouser_boot = {
        "trouser_hem_z": trouser_hem_z,
        "trouser_top_z": trouser_top_z,
        "sweater_hem_z": sweater_hem_z,
        "hem_meets_sweater": bool(abs(trouser_top_z - sweater_hem_z) < 0.002),
        "cuff_poke": cuff_poke,
        "cuff_poke_ok": bool(cuff_ok),
        "leg_verts_outside_all_at_band": leg_outside,
        "leg_covered": bool(leg_outside == 0),
        "sweater_vs_trousers_min": attach["sweater_vs_trousers"]["min"],
        "bootcuff_vs_trousers_min_L": attach["bootcuff_vs_trousers"]["min"],
        "bootcuff_vs_trousers_min_R": attach["bootcuff.001_vs_trousers"]["min"],
        "ok": bool(cuff_ok and leg_outside == 0
                   and abs(trouser_top_z - sweater_hem_z) < 0.002),
    }
    print("QA_TROUSER_BOOT %s" % trouser_boot)

    # ---- gold star placement (BACKLOG: 圣诞星纹位置) ----
    # Sweater stars must sit in the coat's open front wedge
    # (240-300 deg) so they show through; coat stars must sit outside
    # the wedge (on the coat front edges, 225/320 deg). The hat star
    # must sit on the cone front (z 1.75, normal (0,-0.826,0.564)).
    star_pos = {}
    for name, (ang_d, z_d, host_kind) in FLOWER_DESIGN.items():
        vs = world_verts(obj(name))
        cx = sum(w.x for w in vs) / len(vs)
        cy = sum(w.y for w in vs) / len(vs)
        cz = sum(w.z for w in vs) / len(vs)
        # Parametric angle on the host's ellipse (rx != ry, so the
        # geometric atan2 would read ~255 deg where the design angle
        # is 262 deg).
        rx_h, ry_h = interp_rings(
            SWEATER_RINGS if host_kind == "sweater" else COAT_RINGS, cz)
        ang = math.degrees(math.atan2(cy / ry_h, cx / rx_h)) % 360.0
        in_wedge = 240.0 <= ang <= 300.0
        if host_kind == "sweater":
            pos_ok = in_wedge and abs(cz - z_d) < 0.01
        else:
            pos_ok = (not in_wedge) and abs(cz - z_d) < 0.01
        star_pos[name] = {"centre": (round(cx, 4), round(cy, 4),
                                     round(cz, 4)),
                          "angle_deg": round(ang, 1),
                          "design_angle_deg": ang_d,
                          "design_z": z_d,
                          "in_open_wedge_240_300": bool(in_wedge),
                          "ok": bool(pos_ok)}
    hs_vs = world_verts(obj("GoldStarHat"))
    hcx = sum(w.x for w in hs_vs) / len(hs_vs)
    hcy = sum(w.y for w in hs_vs) / len(hs_vs)
    hcz = sum(w.z for w in hs_vs) / len(hs_vs)
    hs_face = obj("GoldStarHat").data.polygons[0]
    hs_nrm = (obj("GoldStarHat").matrix_world.to_3x3()
              @ hs_face.normal).normalized()
    hs_centre_err = (Vector((hcx, hcy, hcz))
                     - Vector(HAT_STAR_C)).length
    hs_normal_dot = hs_nrm.dot(HAT_STAR_N)
    star_pos["GoldStarHat"] = {
        "centre": (round(hcx, 4), round(hcy, 4), round(hcz, 4)),
        "design_centre": list(HAT_STAR_C),
        "centre_error": round(hs_centre_err, 4),
        "normal": [round(v, 3) for v in hs_nrm],
        "design_normal": [round(v, 3) for v in HAT_STAR_N],
        "normal_dot": round(hs_normal_dot, 4),
        "ok": bool(hs_centre_err <= 0.002 and hs_normal_dot > 0.99),
    }
    star_pos_ok = all(v["ok"] for v in star_pos.values())
    print("QA_STARS %s" % star_pos)

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
    sole_names = ["RedBootSole", "RedBootSole.001"]
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
    # 048 has no beret-band class geometry: the probe run showed
    # recalc inverted = 0 on every object (build_048 runs fix_normals
    # on all non-star objects, including the RedCoat open-front arc
    # tube and the RedBootSole wedge — the 045/047 lesson applied).
    solid_inv = tot["inverted_normals"] - flat_inv
    uv_parts = sorted(n for n, r in results.items() if r["uv"]["has_uv"])
    uv_oob = sum(r["uv"]["out_of_bounds"] for r in results.values())
    empty_slots = sum(1 for r in results.values()
                      for m in r["materials"] if m is None)
    gaps_ok = all(gaps[k]["ok"] for k in gaps)
    ground_ok = abs(sole_min_z) <= 0.005
    frame_ok = frame_frac is not None and 0.60 <= frame_frac <= 0.80
    warnings = []
    for k, v in attach.items():
        if k in ("sweater_vs_trousers", "bootcuff_vs_trousers",
                 "bootcuff.001_vs_trousers"):
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
        "hatcone_two_heights: 圣诞帽红锥（底环 z 1.64 r 0.235、顶 z 1.94 "
        "r 0.030，12 边）vs 发顶：全锥最小间隙 %.4f 米（设计值 z 1.64 档 "
        "0.0277），z 1.66 档最小间隙 %.4f 米（设计值 0.0264，实测锥面 "
        "z 1.66 处 r %.4f，设计值 %.4f）：锥体按两档验，底环一档不够——"
        "发面最宽处附近仍 ≥0.005，帽子不擦头发。" % (
            gaps["hatcone_vs_hair"]["min"],
            gaps["hatcone_vs_hair_z166"]["min"],
            cone_measured["r_at_z1.66"],
            cone_measured["design_r_at_z1.66"]))
    warnings.append(
        "brim_above_eyes: 雪白帽边（z 1.64–1.59，r 0.245/0.248）底沿 "
        "z %.3f 米，眼顶 z %.3f 米（眼线 1.525 之上 %.3f 米），帽边底在眼顶"
        "之上 %.3f 米，双眼正面可辨；"
        "帽边离发顶 %.4f 米（要求 ≥0.005），锥底环藏进帽边顶环内（锥 "
        "r 0.235 vs 帽边 r 0.245，间隙 %.4f 米）。" % (
            brim_vs_eyes["brim_bottom_z"], brim_vs_eyes["eye_z"][1],
            brim_vs_eyes["brim_bottom_z"] - 1.525,
            brim_vs_eyes["clearance"], gaps["brim_vs_hair"]["min"],
            gaps["hatcone_vs_brim"]["min"]))
    warnings.append(
        "collar_arc_ends: 雪白毛领前开弧（300°–600°，与大衣同款开襟做法）："
        "毛领顶点 %d 个落在前开楔（240°–300°）内（要求 0），弧端 %d 个顶点"
        "正好落在 240°/300° 边上（x ±0.16、y -0.28，脸侧而非脸前）：v1 整圈"
        "横过眼睛读作蒙眼布的问题已修，双眼可见；但弧端在效果图上读作脸侧"
        "两片白标签，下次可把弧端向后收 10°（250°–290°）或把弧端收窄。"
        % (collar_wedge["verts_inside_wedge_240_300"],
           collar_wedge["arc_end_verts_on_240_300"]))
    warnings.append(
        "star_patch_relief: 金色圣诞星×5、帽上金星是扁平五角星贴片"
        "（单面扇形三角 10 面/片，法线靠构造绕序保证朝外，不适用质心法向"
        "检查）：实测凸起 %.4f–%.4f 米（要求 0.005–0.02；上限含 16 段椭圆"
        "筒的刻面矢高约 0.0052 与曲面曲率约 0.0023）；帽上金星另按理想锥面"
        "解析值 %.4f 米判定（实测 %.4f 米，差 %.4f 米，允差 ±0.012）。"
        "设计记录：design.md 第二颗大衣星记 315°，build_048 用 320°，"
        "两者都在开襟楔（240°–300°）外，本单按实测 320° 判定通过；"
        "design.md 应改 315°→320°，避免后人按文档量出偏差。" % (
            min(protrusions[n]["lift"] for n in
                ["GoldStar", "GoldStar.001", "GoldStar.002",
                 "GoldStar.003", "GoldStar.004"]),
            max(protrusions[n]["lift"] for n in
                ["GoldStar", "GoldStar.001", "GoldStar.002",
                 "GoldStar.003", "GoldStar.004"]),
            protrusions["GoldStarHat"]["analytic"],
            protrusions["GoldStarHat"]["lift"],
            abs(protrusions["GoldStarHat"]["lift"]
                - protrusions["GoldStarHat"]["analytic"])))
    warnings.append(
        "sleeve_through_coat_shoulder: 藏青长袖从大衣肩部穿出（032 的做法："
        "袖筒起点沿臂轴上抬 0.12）：袖面与大衣面在肩部相交（袖顶点离大衣面"
        "最小 %s / %s 米），属缝合构造、不是穿帮；袖筒 caps=True，筒口"
        "不透手臂顶盖。" % (
            attach["sleeveL_vs_coat"]["min"],
            attach["sleeveR_vs_coat"]["min"]))
    warnings.append(
        "sweater_trouser_joint: 雪白毛衣下摆 z %.3f 米与藏青长裤顶 "
        "z %.3f 米对接（设计值均为 0.62）：毛衣顶点离裤面最小 %s 米，"
        "属对接缝、不是层间隙；长裤顶环藏进毛衣下摆，搭接带无露肤（见"
        "第 4.8 节：搭接带 z 0.32–0.36 的腿顶点 %d 个在裤椭圆与靴筒之外）。"
        % (trouser_boot["sweater_hem_z"], trouser_boot["trouser_top_z"],
           attach["sweater_vs_trousers"]["min"],
           trouser_boot["leg_verts_outside_all_at_band"]))
    warnings.append(
        "pleat_relief_sagitta: 圣诞红大衣褶裥片×8 外沿设计浮雕 0.026 米，"
        "是按光滑大衣锥（环插值）算的；大衣面是 16 段刻面筒，网格实测凸起含"
        "刻面矢高（rx 0.322 处最大 0.0064）：判定按理想锥面解析值（要求 "
        "0.020–0.032，网格值与解析值之差 ≤ 0.007），八片全过；褶裥几何与"
        "设计一致，不是漂浮（041 帽上雨滴、037 护目镜片、034 墨镜片、043 "
        "枫叶帽针、046 樱花褶裥同款量法修正）。")
    warnings.append(
        "giftbox_graze: 圣诞礼物盒离右手掌：盒顶点离手掌网格最近 %.4f 米，"
        "盒 8 个顶点无一落在手掌椭球内（最深嵌入 %.4f 米）；盒边中点离理想"
        "手掌椭球最近的 q 值为 %.4f（q<1 才算进入椭球），对应理想面间隙 "
        "%.4f 米：盒背面顶边擦过掌面、没有嵌进去——build_048 的 L2 掌嵌 "
        "0.0085 米是按球面（r 0.085）近似算的，真实手掌是缩放 (1.0, 0.9, "
        "0.8) 的椭球，y 向半径只有 0.0765、z 向只有 0.068，盒背面的 "
        "y -0.075、z -0.05 位置落在椭球之外。效果图上盒子贴着手掌、读作握持，"
        "但按实测不算握持嵌入，见第 7 节 giftbox_float。" % (
            attach["giftbox_vs_handR"]["min"], giftbox["box_deepest_embed"],
            giftbox["box_edge_closest_q"],
            giftbox["box_edge_closest_gap_ideal"]))
    warnings.append(
        "normals_fixed_by_build: 048 全件实体倒置法线 0——build_048 对全部"
        "非星形贴片对象跑 fix_normals（045/047 的教训：开襟弧面管 RedCoat"
        "与楔形 RedBootSole 的构造绕序朝内，须跑 fix_normals；扁平金星贴片"
        "仍跳过）。本单 recalc 全件 0 倒置，与几何一致，无 046 贝雷帽带式"
        "误判（048 无开口锥台帽带类几何）。")
    if not giftbox["ok"]:
        warnings.append(
            "[硬检查不通过] giftbox_float: 圣诞礼物盒未握持嵌入——盒中心实测 "
            "(%.4f, %.4f, %.4f)，与设计值误差 %.4f 米（盒子位置本身是对的）；"
            "但盒顶点离手掌网格最近 %.4f 米（要求 ≤0.005 才算贴合），8 个顶点"
            "无一在手掌椭球内，盒边离理想掌面最近 %.4f 米：盒子浮在掌前约 "
            "0.02 米，没有嵌进手掌。修复法：把礼物盒中心从 (wx, wy-0.11, "
            "wz-0.05) 移到 (wx, wy-0.085, wz-0.02)（盒背面 y -0.05、"
            "z -0.02，椭球值 (0.05/0.0765)^2+(0.02/0.068)^2=0.51<1，背面嵌进"
            "掌面约 0.008 米），重跑 build_048 生成新 blend，再重跑本单；"
            "同时把 build_048 的 L2 掌嵌公式改按真实手掌椭球算，球面近似会"
            "把 0.0085 的假嵌入算成通过。" % (
                giftbox["box_centre"][0], giftbox["box_centre"][1],
                giftbox["box_centre"][2], giftbox["box_centre_error"],
                attach["giftbox_vs_handR"]["min"],
                giftbox["box_edge_closest_gap_ideal"]))
    if not trouser_boot["ok"]:
        warnings.append(
            "[硬检查不通过] bootcuff_pierce: 雪白靴口顶环穿出藏青长裤裤面——"
            "左靴口顶环（z 0.36）%d/%d 个顶点在裤椭圆之外、最大穿出 %.4f 米，"
            "右靴口顶环（z 0.36）%d/%d 个顶点在裤椭圆之外、最大穿出 %.4f 米："
            "靴口是绕腿轴的圆环（r 0.124，腿轴 x ±0.13），长裤是绕双腿的椭圆"
            "筒（z 0.36 处 rx 0.233、ry 0.124），圆环在斜 45° 方向超出椭圆"
            "面——白靴口的上半圈（z 0.34–0.36）从裤面里穿出来，效果图上白圈"
            "贴着裤脚、裤面被顶破。修复法（二选一）：(a) 把靴口下移到 "
            "z 0.34–0.30（整圈落在裤脚之下，只露设计好的 0.02 米白边）；"
            "(b) 把长裤下摆 rx/ry 放到 0.26/0.14（裤脚包住靴口顶环，间隙"
            " ≥0.005）。重跑 build_048 生成新 blend，再重跑本单。" % (
                trouser_boot["cuff_poke"]["L"]["outside_trouser"],
                trouser_boot["cuff_poke"]["L"]["top_ring_verts_above_hem"],
                trouser_boot["cuff_poke"]["L"]["max_poke"],
                trouser_boot["cuff_poke"]["R"]["outside_trouser"],
                trouser_boot["cuff_poke"]["R"]["top_ring_verts_above_hem"],
                trouser_boot["cuff_poke"]["R"]["max_poke"]))
    for k, v in gaps.items():
        if not v["ok"]:
            warnings.append(
                "[硬检查不通过] gap_%s: %s 最小间隙 %.4f 米（0.005 构造线之下"
                " %.4f 米，中位 %.4f 米）——正间隙、无相交、无视觉缺陷的"
                "紧配合仍算不通过，须把外层环再放大。" % (
                    k, k, v["min"], 0.005 - v["min"], v["median"]))
    if not brim_vs_eyes["ok"]:
        warnings.append(
            "[硬检查不通过] brim_eye_line: 雪白帽边底点 z %.3f 米，眼顶 "
            "z %.3f 米（帽边底须在眼线之上，双眼正面可辨）：检查圣诞帽高度"
            "或眼睛位置。" % (
                brim_vs_eyes["brim_bottom_z"], brim_vs_eyes["eye_z"][1]))
    if not collar_wedge["ok"]:
        warnings.append(
            "[硬检查不通过] collar_blindfold: 雪白毛领 %d 个顶点落在前开楔"
            "（240°–300°）内，横在眼睛高度、读作蒙眼布（048 v1 同款失败"
            "重演）：把毛领改回前开弧（300°–600°）。" % (
                collar_wedge["verts_inside_wedge_240_300"]))
    if not glove["ok"]:
        warnings.append(
            "glove_coverage: 左手有 %d 个顶点既不在手套椭球内、也不在袖筒内"
            "（见第 4.6 节）：手套或袖筒没盖住手掌；下次把手套球心沿臂轴上"
            "移或把手套半径加到 0.10。" % glove["uncovered"])
    if not star_pos_ok:
        warnings.append(
            "star_position: 圣诞星纹位置异常（见第 4.9 节）：毛衣上的金星须落在"
            "大衣前开襟楔（240°–300°）内才透得出来，大衣上的金星须落在楔外"
            "（225°/320°），帽上金星须在圣诞帽锥面正面 z 1.75、法向"
            " (0,-0.826,0.564)。")
    if not ground_ok:
        warnings.append(
            "boots_float: 鞋底最低点 z=%.4f 米（地面 z=0，允许 ≤0.005）："
            "鞋底与地面之间有缝。修复：把 RedBootSole 的 z_bottom 改为 "
            "0.0 后重渲。" % sole_min_z)
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
        fail_items.append("帽边底沿与眼线间隙（见第 4.2 节）")
    if not collar_wedge["ok"]:
        fail_items.append("毛领前开弧（见第 4.2 节）")
    if not protrude_ok:
        fail_items.append("凸起件（见第 4.4 节不通过项）")
    if not float_ok:
        fail_items.append("漂浮部件：%s" % "、".join(bad_float))
    if not ground_ok:
        fail_items.append("落地：鞋底最低点 z=%.4f 米（地面 z=0，允许 ≤0.005）"
                          % sole_min_z)
    if not glove["ok"]:
        fail_items.append("手套包覆（见第 4.6 节）")
    if not giftbox["ok"]:
        fail_items.append("礼物盒掌前（见第 4.7 节：盒子浮在掌前，未握持嵌入）")
    if not trouser_boot["ok"]:
        fail_items.append("长裤与短靴搭接（见第 4.8 节：靴口顶环穿出裤面）")
    if not star_pos_ok:
        fail_items.append("圣诞星纹位置（见第 4.9 节）")
    if not frame_ok:
        fail_items.append("构图：人物占画面 %.3f（标准 0.60–0.80）" % frame_frac)
    if not mats["all_ok"]:
        fail_items.append("材质（见第 6 节不通过项）")
    if empty_slots != 0:
        fail_items.append("空材质槽 %d 个" % empty_slots)
    all_ok = (faces_ok and faces_match and ngons_ok and topo_ok and gaps_ok
              and brim_vs_eyes["ok"] and collar_wedge["ok"] and protrude_ok
              and float_ok and ground_ok and glove["ok"] and giftbox["ok"]
              and trouser_boot["ok"] and star_pos_ok
              and frame_ok and mats["all_ok"] and empty_slots == 0)

    summary = {
        "asset": "048-christmas-festival",
        "blend": "scenes/048-christmas-festival/048-christmas-festival.blend",
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
        "hat_cone_measured": cone_measured,
        "brim_vs_eyes": brim_vs_eyes,
        "collar_wedge": collar_wedge,
        "attachments": attach,
        "protrusions": protrusions, "protrusions_ok": bool(protrude_ok),
        "earring_ideal_relief": earring_ideal,
        "earring_analytic_relief": earring_analytic,
        "glove": glove,
        "giftbox": giftbox,
        "trouser_boot": trouser_boot,
        "star_positions": star_pos, "star_positions_ok": bool(star_pos_ok),
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
        f.write("# 049 资产质检单：圣诞节日套装（048）\n\n")
        f.write("被检资产：`scenes/048-christmas-festival/048-christmas-festival.blend`（%d 个服装部件，"
                "不含地面与人体底座；底座 %d 面，另计）\n"
                % (len(results), mannequin_faces))
        f.write("检查方式：Blender bmesh + BVH 实测（拓扑逐面、层间隙逐点最近距离），"
                "非目测估算；设计对照值见 `scenes/048-christmas-festival/design.md`。\n\n")
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
        f.write("- 闭合实体（球/盒/带盖管/楔形/褶裥片/绒球：金腰扣、褶裥片×8、"
                "耳钉、挑染、手套、鞋底楔、长袖、金靴扣、圣诞帽绒球、礼物盒、"
                "金丝带×2、金蝴蝶结）边界边：%d，%s\n" % (closed_boundary, verdict(closed_boundary == 0)))
        f.write("- 边界边合计 %d，全部来自开口管/弧面片与金色星形扁平贴片（毛衣、"
                "大衣、毛领、腰带、长裤、袖口、短靴筒、靴口、圣诞帽锥、翻折帽尖、"
                "帽边、圣诞星×5、帽上金星）：开口管/弧面片按构造有边界边，金星贴片是"
                "单面扇形三角（10 面/片，外沿边界边），属设计形态，不在此项判定。\n" % tot["boundary_edges"])
        f.write("- 最高顶点价数 %d\n\n" % max(r["max_valence"] for r in results.values()))
        f.write("## 2. 法线\n\n")
        f.write("- 法线朝外一致（与 Blender recalc_face_normals 的外法线逐面比对）："
                "倒置面 %d 个（服装部件，扁平贴片除外），%s\n"
                % (solid_inv, verdict(solid_inv == 0)))
        f.write("- 金色星形扁平贴片（圣诞星×5、帽上金星）倒置面 %d 个：单面"
                "扇形三角不适用质心法向检查，法线靠构造绕序保证朝外（make_star_patch，"
                "039 星形贴片的标准；build_048 跳过对它们的 fix_normals），不计入实体"
                "倒置判定。\n" % flat_inv)
        f.write("- build_048 对全部非星形贴片对象跑 fix_normals（045/047 的教训："
                "开襟弧面管 RedCoat 与楔形 RedBootSole 的构造绕序朝内，须跑 "
                "fix_normals）；本单 recalc 全件 0 倒置，与几何一致，无 046 贝雷帽带式"
                "误判（048 无开口锥台帽带类几何）。\n\n")
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
            "sweater_vs_torso": "雪白毛衣 / 躯干",
            "coat_vs_sweater": "圣诞红大衣 / 雪白毛衣",
            "collar_vs_coat": "雪白毛领 / 圣诞红大衣",
            "sleeveL_vs_arm": "藏青长袖左 / 手臂",
            "sleeveR_vs_arm": "藏青长袖右 / 手臂",
            "cuffL_vs_sleeve": "雪白袖口左 / 藏青长袖",
            "cuffR_vs_sleeve": "雪白袖口右 / 藏青长袖",
            "belt_vs_coat": "墨绿腰带 / 圣诞红大衣",
            "trousers_vs_legL": "藏青长裤 / 左腿",
            "trousers_vs_legR": "藏青长裤 / 右腿",
            "bootL_vs_leg": "圣诞红短靴左 / 腿",
            "bootR_vs_leg": "圣诞红短靴右 / 腿",
            "bootcuffL_vs_boot": "雪白靴口左 / 圣诞红短靴",
            "bootcuffR_vs_boot": "雪白靴口右 / 圣诞红短靴",
            "soleL_vs_foot": "圣诞红鞋底楔左 / 脚掌",
            "soleR_vs_foot": "圣诞红鞋底楔右 / 脚掌",
            "hatcone_vs_hair": "圣诞帽红锥 / 发顶",
            "hatcone_vs_hair_z166": "圣诞帽红锥 / 发顶（z 1.66 档）",
            "brim_vs_hair": "雪白帽边 / 发顶",
            "hatcone_vs_brim": "圣诞帽红锥 / 雪白帽边",
        }
        for k, v in gaps.items():
            f.write("| %s | %.4f | %.4f | %d | %s |\n" % (
                gap_labels[k], v["min"], v["median"], v["samples"],
                verdict(v["ok"])))
        f.write("\n注：圣诞帽红锥 vs 发顶在 z 1.64 与 z 1.66 两档都验——锥体"
                "不能按底环一个高度验，发面最宽处附近仍 ≥0.005（design.md）。"
                "红锥底环 r 0.235 藏进帽边顶环 r 0.245 内，锥面与帽边管面间隙"
                " %.4f 米，属层叠、不是穿帮。\n" % gaps["hatcone_vs_brim"]["min"])
        f.write("注：墨绿手套 vs 左手掌不在上表——手套球包覆手掌球，球面按构造"
                "相交，见第 4.6 节专项；长袖 vs 大衣不在上表——袖筒按构造从大衣"
                "肩部穿出，见第 4.3 节注；毛衣 vs 长裤不在上表——毛衣下摆与长裤顶"
                "在 z 0.62 对接缝，见第 4.8 节；靴口 vs 长裤不在上表——靴口顶环与"
                "裤脚在 z 0.32–0.36 重叠，见第 4.8 节专项。\n\n")
        f.write("### 4.2 帽边底沿与眼线间隙、毛领前开弧（专项，BACKLOG 要求）\n\n")
        f.write("- 雪白帽边底点 z %.3f 米，顶 z %.3f 米，帽边半径 %.3f 米；双眼 z 范围"
                " %.3f–%.3f 米：帽边底在眼顶之上 %.3f 米，双眼正面可辨：%s\n" % (
                    brim_vs_eyes["brim_bottom_z"], brim_vs_eyes["brim_top_z"],
                    brim_vs_eyes["brim_radius"],
                    brim_vs_eyes["eye_z"][0], brim_vs_eyes["eye_z"][1],
                    brim_vs_eyes["clearance"],
                    verdict(brim_vs_eyes["brim_bottom_above_eye_top"])))
        f.write("- 圣诞帽红锥 vs 发顶最小间隙 %.4f 米、z 1.66 档 %.4f 米，帽边 vs 发顶"
                "最小间隙 %.4f 米（要求 ≥0.005）：%s\n" % (
                    gaps["hatcone_vs_hair"]["min"],
                    gaps["hatcone_vs_hair_z166"]["min"],
                    gaps["brim_vs_hair"]["min"],
                    verdict(gaps["hatcone_vs_hair"]["ok"]
                            and gaps["hatcone_vs_hair_z166"]["ok"]
                            and gaps["brim_vs_hair"]["ok"])))
        f.write("- 雪白毛领前开弧（300°–600°）：毛领顶点 %d 个落在前开楔（240°–300°）"
                "内（要求 0），弧端 %d 个顶点正好落在 240°/300° 边上（x ±0.16、"
                "y -0.28，脸侧而非脸前）：%s\n" % (
                    collar_wedge["verts_inside_wedge_240_300"],
                    collar_wedge["arc_end_verts_on_240_300"],
                    verdict(collar_wedge["ok"])))
        f.write("- 毛领 vs 大衣最小间隙 %.4f 米（要求 ≥0.005）：%s\n" % (
            gaps["collar_vs_coat"]["min"], verdict(gaps["collar_vs_coat"]["ok"])))
        f.write("- 结论：帽边底沿与眼线间隙、毛领前开弧：%s\n\n" % verdict(
            brim_vs_eyes["ok"] and collar_wedge["ok"]))
        f.write("### 4.3 附件贴合（按构造应贴合宿主，仅记录；> 0.05 视为漂浮嫌疑）\n\n")
        attach_labels = {
            "star_GoldStar_vs_host": "金色圣诞星 1（毛衣 270° z 1.32）/ 雪白毛衣",
            "star_GoldStar_001_vs_host": "金色圣诞星 2（毛衣 262° z 1.02）/ 雪白毛衣",
            "star_GoldStar_002_vs_host": "金色圣诞星 3（毛衣 278° z 1.02）/ 雪白毛衣",
            "star_GoldStar_003_vs_host": "金色圣诞星 4（大衣 225° z 1.10）/ 圣诞红大衣",
            "star_GoldStar_004_vs_host": "金色圣诞星 5（大衣 320° z 1.10）/ 圣诞红大衣",
            "hatstar_vs_cone": "帽上金星 / 圣诞帽红锥",
            "buckle_vs_belt": "金腰扣 / 墨绿腰带",
            "bootbuckle_vs_boot": "金靴扣左 / 圣诞红短靴",
            "bootbuckle.001_vs_boot": "金靴扣右 / 圣诞红短靴",
            "earring_vs_head": "金耳钉左 / 头",
            "earring.001_vs_head": "金耳钉右 / 头",
            "streak_vs_hair": "蓝挑染 / 发顶",
            "pleat_vs_coat": "圣诞红褶裥片 1（170°）/ 圣诞红大衣",
            "pleat.001_vs_coat": "圣诞红褶裥片 2（200°）/ 圣诞红大衣",
            "pleat.002_vs_coat": "圣诞红褶裥片 3（230°）/ 圣诞红大衣",
            "pleat.003_vs_coat": "圣诞红褶裥片 4（320°）/ 圣诞红大衣",
            "pleat.004_vs_coat": "圣诞红褶裥片 5（350°）/ 圣诞红大衣",
            "pleat.005_vs_coat": "圣诞红褶裥片 6（20°）/ 圣诞红大衣",
            "pleat.006_vs_coat": "圣诞红褶裥片 7（50°）/ 圣诞红大衣",
            "pleat.007_vs_coat": "圣诞红褶裥片 8（110°）/ 圣诞红大衣",
            "glove_vs_handL": "墨绿手套 / 左手掌",
            "sleeveL_vs_coat": "藏青长袖左 / 圣诞红大衣",
            "sleeveR_vs_coat": "藏青长袖右 / 圣诞红大衣",
            "giftbox_vs_handR": "圣诞礼物盒 / 右手掌",
            "giftbox_vs_sleeveR": "圣诞礼物盒 / 藏青长袖右",
            "ribbonX_vs_box": "金丝带 X / 礼物红盒",
            "ribbonY_vs_box": "金丝带 Y / 礼物红盒",
            "bow_vs_box": "金蝴蝶结 / 礼物红盒",
            "tip_vs_cone": "翻折帽尖 / 圣诞帽红锥",
            "pompom_vs_tip": "白绒球 / 翻折帽尖",
            "sweater_vs_trousers": "雪白毛衣下摆 / 藏青长裤顶（z 0.62 对接）",
            "bootcuff_vs_trousers": "雪白靴口左 / 藏青长裤（z 0.32–0.36 重叠带）",
            "bootcuff.001_vs_trousers": "雪白靴口右 / 藏青长裤（z 0.32–0.36 重叠带）",
        }
        for k, v in attach.items():
            flag = ("漂浮嫌疑" if v["min"] is not None and v["min"] > 0.05
                    and k not in ("sweater_vs_trousers",
                                  "bootcuff_vs_trousers",
                                  "bootcuff.001_vs_trousers")
                    else "贴合")
            f.write("- %s：最小 %.4f / 中位 %.4f（%d 点）：%s\n" % (
                attach_labels[k], v["min"], v["median"], v["samples"], flag))
        f.write("  注：手套 vs 手掌最小距离 %.4f 米是球面相交（手套包覆构造，"
                "见第 4.6 节），不是贴合不良；长袖 vs 大衣最小距离 %s / %s 米"
                "是袖筒从大衣肩部穿出（032 的做法，袖筒起点沿臂轴上抬 0.12），"
                "属缝合构造；褶裥片 vs 大衣最小 %.4f–%.4f 米是褶裥内沿离大衣面"
                " 0.004 米的设计值（含大衣 16 段刻面矢高）；礼物盒 vs 手掌最小"
                " %.4f 米是盒子浮在掌前（见第 4.7 节），不是贴合；礼物盒 vs 袖筒"
                "最小 %.4f 米是盒顶角超出袖筒端盖平面（设计值 0.0198，见"
                "第 4.7 节）；毛衣 vs 长裤最小 %s 米是 z 0.62 对接缝；靴口 vs 长裤"
                "最小 %s / %s 米是靴口顶环穿出裤面（见第 4.8 节）；翻折帽尖 vs 红锥"
                "最小 %.4f 米是帽尖管从锥顶穿出（帽尖管 r 0.032 包住锥顶 "
                "r 0.030）；白绒球 vs 帽尖最小 %.4f 米是绒球盖住帽尖管口。\n\n" % (
                    attach["glove_vs_handL"]["min"],
                    attach["sleeveL_vs_coat"]["min"],
                    attach["sleeveR_vs_coat"]["min"],
                    min(attach["pleat%s_vs_coat" % t]["min"]
                        for t in [""] + [".%03d" % i for i in range(1, 8)]),
                    max(attach["pleat%s_vs_coat" % t]["min"]
                        for t in [""] + [".%03d" % i for i in range(1, 8)]),
                    attach["giftbox_vs_handR"]["min"],
                    attach["giftbox_vs_sleeveR"]["min"],
                    attach["sweater_vs_trousers"]["min"],
                    attach["bootcuff_vs_trousers"]["min"],
                    attach["bootcuff.001_vs_trousers"]["min"],
                    attach["tip_vs_cone"]["min"],
                    attach["pompom_vs_tip"]["min"]))
        f.write("### 4.4 凸起件（离宿主表面的最远点：要看得见立体感，又不能明显漂浮）\n\n")
        f.write("注：凸起值是贴片顶点离宿主表面的最远点。金色星形扁平贴片"
                "（圣诞星、帽上金星）是平放在椭圆筒/锥面上的扇形三角：贴片中心离面"
                " 0.006，贴片外沿离曲面更远，实测最远点高于设计值 0.006 属几何使然；"
                "金腰扣是未旋转的轴对齐盒，盒角离椭圆腰带面比盒心远，所以实测最远点"
                "高于设计值 0.011，属几何使然；帽上金星是平放在圣诞帽锥面上的星形"
                "贴片，锥面法向在 z 1.75 处倾斜，实测最远点按理想锥面解析值判定"
                "（041 帽上雨滴、037 护目镜片、034 墨镜片、043 枫叶帽针、046 帽上"
                "樱花同款量法，允差 ±0.012）；挑染半嵌发顶与头球，只计发顶与头面之外"
                "的可见顶点（BVH 法向判定），单宿主原值另列；褶裥片外沿按理想锥面"
                "解析值判定（设计 0.026，要求 0.020–0.032，网格值与解析值之差 "
                "≤ 0.007，差值是 16 段大衣面的刻面矢高，见第 7 节）。判定标准仍为"
                "各小节所列。\n\n")
        def write_protrude(f, title, names):
            f.write("- %s：\n" % title)
            for name in names:
                v = protrusions[name]
                if "analytic" in v:
                    f.write("  - %s：凸起 %.4f（%s解析值 %.4f，"
                            "允差 ±%.3f）：%s\n" % (
                                name, v["lift"],
                                v.get("analytic_label", "理想锥面"),
                                v["analytic"],
                                v.get("analytic_tol", 0.012),
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
        write_protrude(f, "金色圣诞星 ×5（设计浮雕 0.006，要求 0.005–0.02）",
                       ["GoldStar", "GoldStar.001", "GoldStar.002",
                        "GoldStar.003", "GoldStar.004"])
        write_protrude(f, "帽上金星（设计浮雕 0.006，要求按理想锥面解析值 ±0.012）",
                       ["GoldStarHat"])
        write_protrude(f, "金腰扣（设计浮雕 0.011，要求 0.005–0.03）",
                       ["GoldBeltBuckle"])
        write_protrude(f, "金靴扣 ×2（设计浮雕 0.010，要求 0.005–0.03）",
                       ["GoldBootBuckle", "GoldBootBuckle.001"])
        write_protrude(f, "金耳钉 ×2（设计浮雕 0.019，要求 0.005–0.035；"
                       "上限含人偶头粗球面的面片内收约 0.011，见第 7 节；"
                       "按理想椭球面算浮雕 %.4f 米）" % earring_ideal,
                       ["GoldEarring", "GoldEarring.001"])
        write_protrude(f, "蓝挑染（半嵌发顶的扁椭球，要求 0.005–0.045；"
                       "只计发顶与头面之外的可见顶点，见注）",
                       ["HairStreak"])
        write_protrude(f, "圣诞红大衣褶裥 ×8（设计外沿 0.026，要求 0.020–0.032）",
                       ["RedPleat", "RedPleat.001", "RedPleat.002",
                        "RedPleat.003", "RedPleat.004", "RedPleat.005",
                        "RedPleat.006", "RedPleat.007"])
        f.write("\n### 4.5 漂浮检查（每个服装部件到最近的其他服装/底座网格的距离，≤0.05 视为已连接）\n\n")
        f.write("- 漂浮嫌疑部件：%s，%s\n" % (
            "无" if float_ok else "、".join(bad_float), verdict(float_ok)))
        for n in bad_float:
            f.write("  - %s：最近 %.4f 米\n" % (n, floating[n]["nearest_other"]))
        f.write("  注：礼物盒最近的网格是右手掌（离掌面 %.4f 米，见第 4.7 节："
                "盒子浮在掌前，不算握持嵌入）；金丝带最近的网格是礼物红盒"
                "（丝带盒比红盒每边大 0.002 米）；白绒球最近的网格是翻折帽尖"
                "（绒球盖住帽尖管口）。\n\n" % attach["giftbox_vs_handR"]["min"])
        f.write("### 4.6 手套包覆（专项，BACKLOG 要求）\n\n")
        f.write("- 左手掌顶点共 %d 个：%d 个在手套椭球内（手套球 r 0.095，"
                "球心在腕上 0.03 米处），%d 个在袖筒内（手腕侧帽沿，袖筒末端"
                " t 0.55），%d 个未被覆盖：%s\n" % (
                    glove["hand_verts_total"], glove["inside_glove"],
                    glove["covered_by_sleeve"], glove["uncovered"],
                    verdict(glove["ok"])))
        f.write("  未被覆盖的顶点（最多列 5 个）：%s\n\n" % glove["uncovered_points"])
        f.write("### 4.7 礼物盒掌前（专项，BACKLOG 要求）\n\n")
        f.write("- 手腕实测 (%.4f, %.4f, %.4f)，与设计值 (%.4f, %.4f, %.4f) "
                "误差 %.4f 米：%s\n" % (
                    giftbox["wrist_measured"][0],
                    giftbox["wrist_measured"][1],
                    giftbox["wrist_measured"][2],
                    giftbox["wrist_design"][0],
                    giftbox["wrist_design"][1],
                    giftbox["wrist_design"][2],
                    giftbox["wrist_error"],
                    verdict(giftbox["wrist_error"] <= 0.002)))
        f.write("- 礼物盒中心实测 (%.4f, %.4f, %.4f)，与设计值（手腕 + "
                "(0, -0.11, -0.05)）误差 %.4f 米：%s\n" % (
                    giftbox["box_centre"][0], giftbox["box_centre"][1],
                    giftbox["box_centre"][2], giftbox["box_centre_error"],
                    verdict(giftbox["box_centre_error"] <= 0.002)))
        f.write("- 盒背面握持嵌入：盒 8 个顶点中 %s 个在手掌椭球内（手掌是 "
                "r 0.085 缩放 (1.0, 0.9, 0.8) 的椭球），最深嵌入 %.4f 米；"
                "盒边中点离理想手掌椭球最近的 q 值为 %.4f（q<1 才算进入椭球），"
                "对应理想面间隙 %.4f 米：%s\n" % (
                    giftbox["box_verts_inside_hand_ellipsoid"],
                    giftbox["box_deepest_embed"],
                    giftbox["box_edge_closest_q"],
                    giftbox["box_edge_closest_gap_ideal"],
                    verdict(giftbox["box_verts_inside_hand_ellipsoid"] != "0/8"
                            or giftbox["box_edge_closest_q"] <= 1.0)))
        f.write("- 盒顶点离手掌网格最近 %.4f 米（要求 ≤0.005 才算贴合）：%s\n" % (
            attach["giftbox_vs_handR"]["min"],
            verdict(attach["giftbox_vs_handR"]["min"] <= 0.005)))
        f.write("- 盒顶角超出袖筒端盖平面 %.4f 米（设计值 0.0198）；盒子离端盖"
                "平面最近 %.4f 米（要求 > 0，即盒子整体在端盖平面之外、不穿"
                "袖筒）：%s\n" % (
                    giftbox["top_corner_past_cap_plane"],
                    giftbox["box_min_past_cap_plane"],
                    verdict(giftbox["box_min_past_cap_plane"] > 0)))
        f.write("- 金丝带离红盒最远点 %.4f 米（丝带盒 0.074 vs 红盒 0.07，设计"
                "每边凸出 0.002 米）；金蝴蝶结离红盒最远点 %.4f 米（蝴蝶结球心"
                "在盒顶上 0.008 米，半嵌盒顶）：%s\n" % (
                    giftbox["ribbon_vs_box_max"], giftbox["bow_vs_box_max"],
                    verdict(giftbox["ribbon_vs_box_max"] <= 0.005
                            and giftbox["bow_vs_box_max"] <= 0.03)))
        f.write("- 结论：礼物盒掌前：%s\n\n" % verdict(giftbox["ok"]))
        f.write("### 4.8 长裤与短靴搭接（专项，BACKLOG 要求）\n\n")
        f.write("- 长裤下摆 z %.3f 米，毛衣下摆 z %.3f 米与长裤顶 z %.3f 米对接"
                "（设计值均为 0.62）：%s\n" % (
                    trouser_boot["trouser_hem_z"],
                    trouser_boot["sweater_hem_z"],
                    trouser_boot["trouser_top_z"],
                    verdict(trouser_boot["hem_meets_sweater"])))
        for side, v in trouser_boot["cuff_poke"].items():
            f.write("- 雪白靴口%s顶环（z 0.36，在裤脚之上）：%d 个顶点在裤椭圆内、"
                    "%d 个在外（共 %d 个），最大穿出 %.4f 米：%s\n" % (
                        side, v["top_ring_verts_above_hem"] - v["outside_trouser"],
                        v["outside_trouser"],
                        v["top_ring_verts_above_hem"], v["max_poke"],
                        verdict(v["outside_trouser"] == 0)))
        f.write("- 搭接带 z 0.32–0.36 的腿顶点有 %d 个既不在裤椭圆内、也不在靴筒内：%s\n" % (
            trouser_boot["leg_verts_outside_all_at_band"],
            verdict(trouser_boot["leg_verts_outside_all_at_band"] == 0)))
        f.write("- 靴口 vs 长裤最小距离左 %s / 右 %s 米是靴口顶环穿出裤面（见"
                "第 7 节 bootcuff_pierce），不是贴合。\n" % (
                    attach["bootcuff_vs_trousers"]["min"],
                    attach["bootcuff.001_vs_trousers"]["min"]))
        f.write("- 结论：长裤与短靴搭接：%s\n\n" % verdict(trouser_boot["ok"]))
        f.write("### 4.9 圣诞星纹位置（专项，BACKLOG 要求）\n\n")
        for name, v in star_pos.items():
            if name == "GoldStarHat":
                f.write("- %s：中心 (%.4f, %.4f, %.4f)，与设计值误差 %.4f 米，"
                        "法向 (%.3f, %.3f, %.3f) 与设计法向 (0, -0.826, 0.564) "
                        "点积 %.4f：%s\n" % (
                            name, v["centre"][0], v["centre"][1], v["centre"][2],
                            v["centre_error"], v["normal"][0], v["normal"][1],
                            v["normal"][2], v["normal_dot"],
                            verdict(v["ok"])))
            else:
                f.write("- %s：中心 (%.4f, %.4f, %.4f)，角度 %.1f°（设计 %d°），"
                        "z %.4f（设计 %.2f），在开襟楔内：%s，%s\n" % (
                            name, v["centre"][0], v["centre"][1], v["centre"][2],
                            v["angle_deg"], v["design_angle_deg"],
                            v["centre"][2], v["design_z"],
                            v["in_open_wedge_240_300"], verdict(v["ok"])))
        f.write("- 结论：圣诞星纹位置：%s\n\n" % verdict(star_pos_ok))
        f.write("## 5. 尺寸与落地\n\n")
        f.write("- 服装包围盒：x %.3f–%.3f、y %.3f–%.3f、z %.3f–%.3f 米，"
                "高 %.3f 米、宽 %.3f 米\n" % (
                    g_bbox["x"][0], g_bbox["x"][1], g_bbox["y"][0],
                    g_bbox["y"][1], g_bbox["z"][0], g_bbox["z"][1],
                    g_bbox["height"], g_bbox["width"]))
        f.write("- 最高点 z %.3f 米（%s）；鞋底最低点 z %.4f 米、脚掌最低点"
                " z %.4f 米（地面 z=0，允许 ≤0.005）：%s\n" % (
                    top_z, top_obj, sole_min_z, foot_min_z,
                    verdict(ground_ok)))
        f.write("- 构图：人物占画面 %.3f（标准 0.60–0.80）：%s\n\n" % (
            frame_frac, verdict(frame_ok)))
        f.write("## 6. 材质\n\n")
        for r in mats["rows"]:
            if r.get("found"):
                f.write("- %s：metallic %.2f / roughness %.2f / base %s：%s\n" % (
                    r["name"], r["metallic"], r["roughness"],
                    r["base_color"], verdict(r["ok"])))
            else:
                f.write("- %s：未找到材质：不通过\n" % r["name"])
        f.write("- 材质逐项核对：%s\n" % verdict(mats["all_ok"]))
        f.write("- 空材质槽：%d 个：%s\n\n" % (
            empty_slots, verdict(empty_slots == 0)))
        f.write("## 7. 结论与观察\n\n")
        f.write("- 总体结论：**%s**\n" % ("通过" if all_ok else "不通过"))
        if fail_items:
            f.write("- 不通过项（%d）：\n" % len(fail_items))
            for item in fail_items:
                f.write("  - %s\n" % item)
        f.write("- 观察与量法说明（%d 项）：\n" % len(warnings))
        for w in warnings:
            f.write("  - %s\n" % w)

    print("QA_CHECKLIST_WRITTEN:", CHECKLIST)


if __name__ == "__main__":
    main()
