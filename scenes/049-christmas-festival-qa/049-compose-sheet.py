# -*- coding: utf-8 -*-
"""049 compose (system python3 + PIL): compose the QA contact sheet for the
048 christmas-festival urban set: beauty render + wireframe + QA findings panel
(no UV panel: the costume uses procedural Principled materials, no textures,
so there is no UV layout to draw — the findings panel carries the numbers).
Run: python3 049-compose-sheet.py
"""
import json
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SUMMARY = os.path.join(HERE, "049-qa-summary.json")
BEAUTY = os.path.join(ROOT, "renders", "048-christmas-festival.png")
WIREFRAME = os.path.join(ROOT, "renders", "048-christmas-festival-wireframe.png")
SHEET = os.path.join(ROOT, "renders", "049-christmas-festival-qa-sheet.png")

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
    f_b = font(21)
    x = 48
    y = 22
    d.text((x, y), "QA Findings (measured)", fill=(20, 22, 28), font=f_title)
    y += 50
    gaps = s["gaps"]
    n_pass = sum(1 for v in gaps.values() if v["ok"])
    rows = [
        ("Topology", [
            "Faces: %d (limit 1500, design record 725)" % s["total_faces"],
            "Tris %d / Quads %d / Ngons %d (design 0)" % (
                s["tris"], s["quads"], s["ngons"]),
            "Duplicate verts 0 / loose edges 0 / non-manifold 0",
            "Degenerate 0 / inv normals 0 solids (fix_normals all)",
            "UV: 12 parts carry unused default UVMap, 0 out of bounds",
            "Hat cone r 0.235 @z1.64, 0.2213 @z1.66 (measured taper)",
        ]),
        ("Garment structure (BVH, metres)", [
            "Layer gaps: %d/%d pass (req >= 0.005)" % (n_pass, len(gaps)),
            "Tightest: cone vs brim %.4f, trousers %.4f, cuff %.4f,"
            % (gaps["hatcone_vs_brim"]["min"],
               gaps["trousers_vs_legL"]["min"],
               gaps["cuffL_vs_sleeve"]["min"]),
            "belt %.4f, cone vs hair %.4f (z1.66 ring %.4f)."
            % (gaps["belt_vs_coat"]["min"],
               gaps["hatcone_vs_hair"]["min"],
               gaps["hatcone_vs_hair_z166"]["min"]),
            "Brim 0.035 above eyes / glove 13 in glove + 7 in sleeve",
            "Collar 0 verts in front wedge, 4 arc-end verts on 240/300",
            "No floating parts / frame %.3f / soles z=0.0"
            % s["frame_fraction"],
        ]),
        ("Two FAILs (see checklist ss.4.7-4.8)", [
            "Gift box floats 0.0194 off the palm, 0/8 verts inside",
            "the hand ellipsoid (L2 spherical approx hid it).",
            "Boot cuff top ring 6/10 verts pierce the trouser wall,",
            "max 0.0436 (round cuff vs elliptical trouser tube).",
        ]),
        ("Stars & pleats", [
            "Stars x5: 0.0089-0.0113 relief (req 0.005-0.02)",
            "Hat star 0.0099, analytic 0.0065 (diff 0.0034)",
            "Pleats x8: analytic 0.0260-0.0261 (req 0.020-0.032)",
            "mesh 0.0263-0.0307 (16-seg facet sagitta, corrected)",
            "Stars at 270/262/278/225/320 deg, hat star on cone",
            "Buckle 0.0139 / boot buckle 0.0157 / earring 0.0189",
        ]),
        ("Materials (Principled BSDF vs design)", [
            "9/9 match: ChristmasRed / SnowWhite / PineGreen",
            "Navy / Gold / LightBlue / Hair Black / Skin / Eye Dark",
            "No texture maps (procedural colours only)",
        ]),
        ("Hair streak visible", [
            "Streak visible 22/26 verts, lift 0.0397 (req 0.005-0.045): PASS",
            "042-proven position (0.11, -0.175, 1.44), flat on hair.",
        ]),
    ]
    for title, lines in rows:
        d.text((x, y), title, fill=(30, 34, 42), font=f_h)
        y += 30
        for line in lines:
            d.text((x + 16, y), line, fill=(60, 60, 66), font=f_b)
            y += 25
        y += 4
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
    d.text((36, 26), "Asset QA Sheet  |  Christmas-Festival Urban Set (048)",
           fill=(255, 255, 255), font=font(48, bold=True))
    n_fail = len(s["fail_items"])
    verdict = "FAIL - %d ITEMS" % n_fail if not s["overall_pass"] else "PASS"
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
              "Gift box floats 0.0194 / cuff pierces 0.0436   |   "
              "Mats 9/9   |   Ground: z=0.0   |   Frame: %.3f" % (
                  s["total_faces"], s["ngons"], s["duplicate_verts"],
                  s["inverted_normals_solids"], n_pass, len(s["gaps"]),
                  s["frame_fraction"]))
    d.text((36, fy + 12), footer, fill=(60, 60, 60), font=font(30))
    sheet.save(SHEET)
    print("SHEET_WRITTEN:", SHEET, sheet.size)


if __name__ == "__main__":
    main()
