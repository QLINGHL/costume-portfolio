# -*- coding: utf-8 -*-
"""043 compose (system python3 + PIL): compose the QA contact sheet for the
039 autumn-maple urban set: beauty render + wireframe + QA findings panel
(no UV panel: the costume uses procedural Principled materials, no textures,
so there is no UV layout to draw — the findings panel carries the numbers).
Run: python3 043-compose-sheet.py
"""
import json
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SUMMARY = os.path.join(HERE, "043-qa-summary.json")
BEAUTY = os.path.join(ROOT, "renders", "039-autumn-maple-urban.png")
WIREFRAME = os.path.join(ROOT, "renders", "039-autumn-maple-urban-wireframe.png")
SHEET = os.path.join(ROOT, "renders", "043-autumn-maple-qa-sheet.png")

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
            "Faces: %d (limit 1500, design record 744)" % s["total_faces"],
            "Tris %d / Quads %d / Ngons %d (design 0)" % (
                s["tris"], s["quads"], s["ngons"]),
            "Duplicate verts 0 / loose edges 0 / non-manifold 0",
            "Degenerate 0 / inv normals 0 (solids; band recalc 48 excl., geo 48/48 out)",
            "Closed solids boundary edges 0 (39 parts)",
            "UV: 6 parts carry unused default UVMap, 0 out of bounds",
        ]),
        ("Garment structure (BVH, metres)", [
            "Layer gaps: %d/%d pass (req >= 0.005)" % (n_pass, len(gaps)),
            "Tightest: band %.4f, belt %.4f, cuff %.4f,"
            % (gaps["band_vs_beret"]["min"], gaps["belt_vs_coat"]["min"],
               gaps["cuffL_vs_sleeve"]["min"]),
            "trousers %.4f, beret vs hair %.4f (visible part only)."
            % (gaps["trousers_vs_legL"]["min"],
               gaps["beret_vs_hair"]["min"]),
            "Beret 0.016 above eyes / glove 13 in glove + 7 in sleeve",
            "Cat ears 4 in / 1 out, apex +0.071 above beret top",
            "No floating parts / frame %.3f / soles z=0.0"
            % s["frame_fraction"],
        ]),
        ("Beret band (3 rings follow the dome)", [
            "Bottom ring 0.0042 vs dome (req 0.005): FAIL",
            "Design 0.006 vs ideal sphere; faceted ring 0.2252 > bottom 0.2232.",
            "Fix: bottom ring 0.2232 -> 0.230, then re-run QA (044).",
        ]),
        ("Maple leaves & pleats", [
            "Leaves x5: 0.0092-0.0117 relief (req 0.005-0.02)",
            "Brooch 0.0087 / pin 0.0272, analytic 0.0201 (diff 0.0071)",
            "Pleats x8: 0.0263-0.0304 (req 0.020-0.032)",
            "Leaves at 270/262/278/220/320 deg, brooch z 1.22",
            "Pin 300 deg z 1.70 / buckle 0.0139 / earring 0.0189",
            "Boot cuff 0.006 / leaf held 0.0178 off palm",
        ]),
        ("Materials (Principled BSDF vs design)", [
            "9/9 match: Caramel / Cream / Navy / MapleRed",
            "Gold / LightBlue / Hair Black / Skin / Eye Dark",
            "No texture maps (procedural colours only)",
        ]),
        ("FAIL: hair streak invisible", [
            "Streak visible 1/26 verts, lift 0.0000 (req >= 0.005):",
            "the streak sits inside the head sphere (front y -0.146",
            "vs head surface -0.164) — nothing shows under the beret.",
            "Fix: move the streak to (0.11, -0.175, 1.44) (042-proven).",
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
    d.text((36, 26), "Asset QA Sheet  |  Autumn-Maple Urban Set (039)",
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
              "Band 0.0042 / Streak 1/26 visible, lift 0.0000   |   "
              "Mats 9/9   |   Ground: z=0.0   |   Frame: %.3f" % (
                  s["total_faces"], s["ngons"], s["duplicate_verts"],
                  s["inverted_normals_solids"], n_pass, len(s["gaps"]),
                  s["frame_fraction"]))
    d.text((36, fy + 12), footer, fill=(60, 60, 60), font=font(30))
    sheet.save(SHEET)
    print("SHEET_WRITTEN:", SHEET, sheet.size)


if __name__ == "__main__":
    main()
