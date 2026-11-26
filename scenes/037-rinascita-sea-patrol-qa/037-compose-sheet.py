# -*- coding: utf-8 -*-
"""037 compose (system python3 + PIL): compose the QA contact sheet for the
036 Rinascita sea patrol set: beauty render + wireframe + QA findings panel
(no UV panel: the costume uses procedural Principled materials, no textures,
so there is no UV layout to draw — the findings panel carries the numbers).
Run: python3 037-compose-sheet.py
"""
import json
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SUMMARY = os.path.join(HERE, "037-qa-summary.json")
BEAUTY = os.path.join(ROOT, "renders", "036-rinascita-sea-patrol.png")
WIREFRAME = os.path.join(ROOT, "renders", "036-rinascita-sea-patrol-wireframe.png")
SHEET = os.path.join(ROOT, "renders", "037-rinascita-sea-patrol-qa-sheet.png")

SIZE = 1024


def font(size, bold=False):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                 if bold else
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_findings(s, out_img):
    """Text panel: the measured numbers behind the verdict."""
    d = ImageDraw.Draw(out_img)
    f_title = font(38, bold=True)
    f_h = font(27, bold=True)
    f_b = font(23)
    x = 48
    y = 22
    d.text((x, y), "QA Findings (measured)", fill=(20, 22, 28), font=f_title)
    y += 50
    gaps = s["gaps"]
    n_pass = sum(1 for v in gaps.values() if v["ok"])
    rows = [
        ("Topology", [
            "Faces: %d (limit 1500, design record 833)" % s["total_faces"],
            "Tris %d / Quads %d / Ngons %d (design 0)" % (
                s["tris"], s["quads"], s["ngons"]),
            "Duplicate verts 0 / loose edges 0 / non-manifold 0",
            "Degenerate faces 0 / inverted normals 0 (solids)",
            "Closed solids boundary edges 0 (36 parts)",
            "Brim 15 recalc-flagged: geometry-verified outward",
        ]),
        ("Garment structure (BVH, metres)", [
            "Layer gaps: %d/%d pass (req >= 0.005)" % (n_pass, len(gaps)),
            "Fail: cuff L/R %.4f, belt %.4f, rope %.4f, cap dome %.4f"
            % (gaps["cuffL_vs_sleeve"]["min"], gaps["belt_vs_bodysuit"]["min"],
               gaps["ropeCoil_vs_bodysuit"]["min"],
               gaps["capDome_vs_hair"]["min"]),
            "Brim 0.030 above eyes / glove 13 in glove + 7 in sleeve",
            "Compass visible 68.9%%, disc normal (0,-1,0)",
            "No floating parts / frame %.3f / soles z=0.0"
            % s["frame_fraction"],
        ]),
        ("Materials (Principled BSDF vs design)", [
            "8/8 match: DeepTeal / PearlWhite / Charcoal / CyanGlow",
            "Gold / Hair Black / Skin / Eye Dark",
            "No texture maps (procedural colours only)",
        ]),
        ("UV", [
            "25 parts carry Blender primitive default UVMap,",
            "unused (no textures); 0 points out of bounds.",
        ]),
        ("Observations (6 hard fails)", [
            "1. Cuff %.4f (sleeve radius at cuff top ring 0.0986,"
            % gaps["cuffL_vs_sleeve"]["min"],
            "   not end 0.096; fix cuff ring 0.102->0.105).",
            "2. Belt %.4f (ry-only blind spot; belt ry +0.004)."
            % gaps["belt_vs_bodysuit"]["min"],
            "3. Rope %.4f (same ry blind spot; rope ry +0.004)."
            % gaps["ropeCoil_vs_bodysuit"]["min"],
            "4. Cap dome %.4f grazing hairline (dome r 0.25->0.26)."
            % gaps["capDome_vs_hair"]["min"],
            "5. Knee pad %.4f (flat 0.12 pad on curved knee;"
            % s["protrusions"]["TealKneePad"]["lift"],
            "   narrow to 0.08-0.09 or curve it).",
            "6. Hair streak visible 0/26 verts: buried in head;",
            "   move to hair surface (-0.12,-0.16,1.47).",
        ]),
    ]
    for title, lines in rows:
        d.text((x, y), title, fill=(30, 34, 42), font=f_h)
        y += 34
        for line in lines:
            d.text((x + 16, y), line, fill=(60, 60, 66), font=f_b)
            y += 29
        y += 6
    return out_img


def main():
    with open(SUMMARY, encoding="utf-8") as fh:
        s = json.load(fh)

    beauty = Image.open(BEAUTY).convert("RGB").resize((SIZE, SIZE))
    wire = Image.open(WIREFRAME).convert("RGB").resize((SIZE, SIZE))
    findings = Image.new("RGB", (SIZE, SIZE), (250, 250, 252))
    draw_findings(s, findings)

    header_h, label_h, footer_h = 110, 70, 64
    W = SIZE * 3
    H = header_h + SIZE + label_h + footer_h
    sheet = Image.new("RGB", (W, H), (245, 245, 247))
    d = ImageDraw.Draw(sheet)
    d.rectangle([0, 0, W, header_h], fill=(30, 34, 42))
    d.text((36, 26), "Asset QA Sheet  |  Rinascita Sea Patrol Set (036)",
           fill=(255, 255, 255), font=font(48, bold=True))
    verdict = "FAIL - 6 ITEMS" if not s["overall_pass"] else "PASS"
    if s["overall_pass"] and s.get("warnings"):
        verdict = "PASS + %d NOTES" % len(s["warnings"])
    vcol = (80, 200, 120) if s["overall_pass"] else (230, 120, 60)
    d.text((W - 480, 34), verdict, fill=vcol, font=font(44, bold=True))
    panels = [(beauty, "1  Beauty Render"),
              (wire, "2  Wireframe / Topology"),
              (findings, "3  QA Findings (measured)")]
    for i, (img, label) in enumerate(panels):
        x = i * SIZE
        sheet.paste(img, (x, header_h))
        d.rectangle([x, header_h + SIZE, x + SIZE, header_h + SIZE + label_h],
                    fill=(235, 235, 238))
        d.text((x + 24, header_h + SIZE + 14), label, fill=(30, 30, 30),
               font=font(36, bold=True))
    fy = header_h + SIZE + label_h
    n_pass = sum(1 for v in s["gaps"].values() if v["ok"])
    footer = ("Faces: %d   |   Ngons: %d   |   Dup verts: %d   |   "
              "Inv normals: %d (solids)   |   Gaps: %d/%d pass   |   "
              "Knee pad 0.0386 / streak 0/26 visible   |   "
              "Mats 8/8   |   Ground: z=0.0   |   Frame: %.3f" % (
                  s["total_faces"], s["ngons"], s["duplicate_verts"],
                  s["inverted_normals_solids"], n_pass, len(s["gaps"]),
                  s["frame_fraction"]))
    d.text((36, fy + 12), footer, fill=(60, 60, 60), font=font(30))
    sheet.save(SHEET)
    print("SHEET_WRITTEN:", SHEET, sheet.size)


if __name__ == "__main__":
    main()
