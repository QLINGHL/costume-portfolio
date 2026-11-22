# -*- coding: utf-8 -*-
"""013 compose (system python3 + PIL): compose the QA contact sheet for the
011 snow priest robe: beauty render + wireframe + QA findings panel
(no UV panel: the costume uses procedural Principled materials, no textures,
so there is no UV layout to draw — the findings panel carries the numbers).
Run: python3 013-compose-sheet.py
"""
import json
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SUMMARY = os.path.join(HERE, "013-qa-summary.json")
BEAUTY = os.path.join(ROOT, "renders", "011-snow-priest-robe.png")
WIREFRAME = os.path.join(ROOT, "renders", "011-snow-priest-robe-wireframe.png")
SHEET = os.path.join(ROOT, "renders", "013-snow-priest-qa-sheet.png")

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
    y += 54
    rows = [
        ("Topology", [
            "Faces: %d (limit 1500, design record 617)" % s["total_faces"],
            "Tris %d / Quads %d / Ngons %d (design 0)" % (
                s["tris"], s["quads"], s["ngons"]),
            "Duplicate verts 0 / loose edges 0 / non-manifold 0",
            "Degenerate faces 0 / inverted normals 0 (solids)",
            "Closed solids boundary edges 0 (46 parts)",
        ]),
        ("Garment structure (BVH, metres)", [
            "Layer gaps min 0.006-0.042 (req >= 0.005): 14/14 pass",
            "Staff vs overskirt 0.0133 (sampled, 1704 pts)",
            "Snowflakes 0.0196-0.0242 x4 / pleats 0.0093-0.0162 x8",
            "Belt buckle 0.0177 / no floating parts / frame 0.618",
        ]),
        ("Materials (Principled BSDF vs design)", [
            "8/8 match: Snow White / Ice Blue / Deep Blue",
            "Gold / Fur White / Skin / Hair Silver / Eye Dark",
            "No texture maps (procedural colours only)",
        ]),
        ("UV", [
            "13 parts carry Blender primitive default UVMap,",
            "unused (no textures); 0 points out of bounds.",
        ]),
        ("FAIL + observations", [
            "FAIL: boots float 0.02 m (wedge centre z=0.02;",
            "   002 had a sole at z=0). Fix: centre z -> 0.0.",
            "1. Belt crosses overskirt at lower edge (6 verts",
            "   inside skirt cone, z=0.70, +/-x); belt reads",
            "   tucked into skirt.",
            "2. Staff tip floats 0.05 m (shaft starts z=0.05);",
            "   start at z=0.0 if it should plant.",
        ]),
    ]
    for title, lines in rows:
        d.text((x, y), title, fill=(30, 34, 42), font=f_h)
        y += 38
        for line in lines:
            d.text((x + 16, y), line, fill=(60, 60, 66), font=f_b)
            y += 32
        y += 8
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
    d.text((36, 26), "Asset QA Sheet  |  Snow Priest Robe (011)",
           fill=(255, 255, 255), font=font(48, bold=True))
    verdict = "PASS" if s["overall_pass"] else "REVIEW NEEDED"
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
    footer = ("Faces: %d   |   Ngons: %d   |   Dup verts: %d   |   "
              "Inv normals: %d (solids)   |   Gaps: 14/14 pass   |   "
              "Staff: 0.0133   |   Snowflakes 4/4   |   Pleats 8/8   |   "
              "Mats 8/8   |   Ground: FAIL (boots +0.02 m)" % (
                  s["total_faces"], s["ngons"], s["duplicate_verts"],
                  s["inverted_normals_solids"]))
    d.text((36, fy + 12), footer, fill=(60, 60, 60), font=font(30))
    sheet.save(SHEET)
    print("SHEET_WRITTEN:", SHEET, sheet.size)


if __name__ == "__main__":
    main()
