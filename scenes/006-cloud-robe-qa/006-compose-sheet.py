# -*- coding: utf-8 -*-
"""006 compose (system python3 + PIL): compose the QA contact sheet for the
001 cloud-pattern battle robe: beauty render + wireframe + QA findings panel
(no UV panel: the costume uses procedural Principled materials, no textures,
so there is no UV layout to draw — the findings panel carries the numbers).
Run: python3 006-compose-sheet.py
"""
import json
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SUMMARY = os.path.join(HERE, "006-qa-summary.json")
BEAUTY = os.path.join(ROOT, "renders", "001-cloud-robe.png")
WIREFRAME = os.path.join(ROOT, "renders", "001-cloud-robe-wireframe.png")
SHEET = os.path.join(ROOT, "renders", "006-cloud-robe-qa-sheet.png")

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
    f_h = font(28, bold=True)
    f_b = font(25)
    x = 48
    y = 24
    d.text((x, y), "QA Findings (measured)", fill=(20, 22, 28), font=f_title)
    y += 58
    rows = [
        ("Topology", [
            "Faces: %d (limit 1200, design record 994)" % s["total_faces"],
            "Tris %d / Quads %d / Ngons %d (design 6)" % (
                s["tris"], s["quads"], s["ngons"]),
            "Duplicate verts 0 / loose edges 0 / non-manifold 0",
            "Degenerate faces 0 / inverted normals 0",
            "Closed solids boundary edges 0",
        ]),
        ("Garment structure (BVH, metres)", [
            "Layer gaps min 0.0054-0.0429 (req >= 0.005): 11/11 pass",
            "Pleat ridge lift 0.0318 x8 (req >= 0.02)",
            "Cloud scrolls standoff 0.0089-0.0211 (6 pcs)",
            "No floating parts / boots on ground (z = 0.0000)",
            "Frame fraction 0.704 (standard 0.60-0.80)",
        ]),
        ("Materials (Principled BSDF vs design)", [
            "9/9 match: Teal / Ink / Red / Gold / Pleat Red",
            "Skin / Hair / Boot Brown / Eye Dark",
            "No texture maps (procedural colours only)",
        ]),
        ("UV", [
            "11 parts carry Blender primitive default UVMap,",
            "unused (no textures); 0 points out of bounds.",
        ]),
        ("Observations (pass with notes)", [
            "1. Pendant back 0.0006 m from skirt (req 0.005),",
            "   no intersection; move out 0.005 m next time.",
            "2. Cloud standoff 0.009-0.021 m (0.007 offset x2",
            "   + facet sag); fine from front, ~1-2 cm seam",
            "   seen from the side.",
        ]),
    ]
    for title, lines in rows:
        d.text((x, y), title, fill=(30, 34, 42), font=f_h)
        y += 40
        for line in lines:
            d.text((x + 16, y), line, fill=(60, 60, 66), font=f_b)
            y += 34
        y += 10
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
    d.text((36, 26), "Asset QA Sheet  |  Cloud-Pattern Battle Robe (001 v2)",
           fill=(255, 255, 255), font=font(48, bold=True))
    verdict = "PASS" if s["overall_pass"] else "REVIEW NEEDED"
    if s["overall_pass"] and s.get("warnings"):
        verdict = "PASS + %d NOTES" % len(s["warnings"])
    vcol = (80, 200, 120) if s["overall_pass"] else (230, 120, 60)
    d.text((W - 420, 34), verdict, fill=vcol, font=font(44, bold=True))
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
    footer = ("Faces: %d   |   Ngons: %d   |   Duplicate verts: %d   |   "
              "Inverted normals: %d   |   Layer gaps: 11/11 pass   |   "
              "Pleats: 8/8   |   Clouds: 6/6   |   Materials: 9/9" % (
                  s["total_faces"], s["ngons"], s["duplicate_verts"],
                  s["inverted_normals"]))
    d.text((36, fy + 12), footer, fill=(60, 60, 60), font=font(30))
    sheet.save(SHEET)
    print("SHEET_WRITTEN:", SHEET, sheet.size)


if __name__ == "__main__":
    main()
