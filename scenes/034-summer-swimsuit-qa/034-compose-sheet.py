# -*- coding: utf-8 -*-
"""034 compose (system python3 + PIL): compose the QA contact sheet for the
031 summer swimsuit set: beauty render + wireframe + QA findings panel
(no UV panel: the costume uses procedural Principled materials, no textures,
so there is no UV layout to draw — the findings panel carries the numbers).
Run: python3 034-compose-sheet.py
"""
import json
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SUMMARY = os.path.join(HERE, "034-qa-summary.json")
BEAUTY = os.path.join(ROOT, "renders", "031-summer-swimsuit.png")
WIREFRAME = os.path.join(ROOT, "renders", "031-summer-swimsuit-wireframe.png")
SHEET = os.path.join(ROOT, "renders", "034-summer-swimsuit-qa-sheet.png")

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
            "Faces: %d (limit 1500, design record 579)" % s["total_faces"],
            "Tris %d / Quads %d / Ngons %d (design 0)" % (
                s["tris"], s["quads"], s["ngons"]),
            "Duplicate verts 0 / loose edges 0 / non-manifold 0",
            "Degenerate faces 0 / inverted normals 0 (solids)",
            "Closed solids boundary edges 0 (34 parts)",
        ]),
        ("Garment structure (BVH, metres)", [
            "Layer gaps: %d/%d pass (req >= 0.005)" % (n_pass, len(gaps)),
            "035 fix: brief vs leg %.4f / hat band %.4f" % (
                gaps["brief_vs_legL"]["min"],
                gaps["hatBand_vs_crown"]["min"]),
            "Brim disc crosses hair, hidden in crown (0.22<0.259)",
            "Handles thru palm: 0.0004/0.0005, 42+22 pts inside",
            "Sunglasses 0.29 below eyes / bandeau top 1.32>1.28",
            "No floating parts / frame %.3f / soles z=0.0"
            % s["frame_fraction"],
        ]),
        ("Materials (Principled BSDF vs design)", [
            "9/9 match: Coral / Cream / Navy / Gold",
            "Hair Black / Light Blue / Dark Lens / Skin / Eye Dark",
            "No texture maps (procedural colours only)",
        ]),
        ("UV", [
            "20 parts carry Blender primitive default UVMap,",
            "unused (no textures); 0 points out of bounds.",
        ]),
        ("Observations (5: 2 fixed in 035 + 3 notes)", [
            "1. Brief vs leg %.4f (035: bottom ring rx 0.236->0.240,"
            % gaps["brief_vs_legL"]["min"],
            "   ry 0.122->0.124; was 0.0044).",
            "2. Hat band %.4f (035: band ry +0.006; was 0.0006)."
            % gaps["hatBand_vs_crown"]["min"],
            "3. Brim disc/hair crossing hidden in crown.",
            "4. Lens 0.034 = analytic 0.0296 + faceting.",
            "5. Earring 0.0303 (smooth-head 0.0161, design 0.019).",
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
    d.text((36, 26), "Asset QA Sheet  |  Summer Swimsuit Set (031)",
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
    n_pass = sum(1 for v in s["gaps"].values() if v["ok"])
    footer = ("Faces: %d   |   Ngons: %d   |   Dup verts: %d   |   "
              "Inv normals: %d (solids)   |   Gaps: %d/%d pass   |   "
              "Handles thru palm   |   Sunglasses below eyes   |   "
              "Mats 9/9   |   Ground: z=0.0   |   Frame: %.3f" % (
                  s["total_faces"], s["ngons"], s["duplicate_verts"],
                  s["inverted_normals_solids"], n_pass, len(s["gaps"]),
                  s["frame_fraction"]))
    d.text((36, fy + 12), footer, fill=(60, 60, 60), font=font(30))
    sheet.save(SHEET)
    print("SHEET_WRITTEN:", SHEET, sheet.size)


if __name__ == "__main__":
    main()
