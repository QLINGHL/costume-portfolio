# -*- coding: utf-8 -*-
"""041 compose (system python3 + PIL): compose the QA contact sheet for the
040 rainy-day urban set: beauty render + wireframe + QA findings panel
(no UV panel: the costume uses procedural Principled materials, no textures,
so there is no UV layout to draw — the findings panel carries the numbers).
Run: python3 041-compose-sheet.py
"""
import json
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SUMMARY = os.path.join(HERE, "041-qa-summary.json")
BEAUTY = os.path.join(ROOT, "renders", "040-rainy-day-urban.png")
WIREFRAME = os.path.join(ROOT, "renders", "040-rainy-day-urban-wireframe.png")
SHEET = os.path.join(ROOT, "renders", "041-rainy-day-urban-qa-sheet.png")

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
    u = s["umbrella"]
    h = s["hood"]
    rows = [
        ("Topology", [
            "Faces: %d (limit 1500, design record 1022)" % s["total_faces"],
            "Tris %d / Quads %d / Ngons %d (design 0)" % (
                s["tris"], s["quads"], s["ngons"]),
            "Duplicate verts 0 / loose edges 0 / non-manifold 0",
            "Degenerate faces 0 / inverted normals 0 (solids)",
            "Closed solids boundary edges 0 (43 parts)",
            "UV: 13 parts carry unused default UVMap, 0 out of bounds",
        ]),
        ("Garment structure (BVH, metres)", [
            "Layer gaps: %d/%d pass (req >= 0.005)" % (n_pass, len(gaps)),
            "Tightest: trousers %.4f, belt %.4f, cuff %.4f,"
            % (gaps["trousers_vs_legL"]["min"], gaps["belt_vs_raincoat"]["min"],
               gaps["cuffL_vs_sleeve"]["min"]),
            "hat crown vs hair %.4f (visible part only)."
            % gaps["hatcrown_vs_hair"]["min"],
            "Brim 0.053 above eyes / glove 13 in glove + 7 in sleeve",
            "Hood 15-165 deg, 6 verts inside hair / 42 outside",
            "No floating parts / frame %.3f / soles z=0.0"
            % s["frame_fraction"],
        ]),
        ("Umbrella (6th handheld item)", [
            "Shaft ellipse @z=0.90: %.3f (> 1.15)" % u["shaft_at_z090_ellipse"],
            "Canopy rim ellipse: %.3f (> 1.15)" % u["canopy_rim_ellipse"],
            "Rim radial clearance vs sleeve: %.4f (baseline 0.1837)"
            % u["canopy_rim_radial_clearance"],
            "Grip/shaft axes: %.3f deg, offset %.4f"
            % (u["grip_axis_angle_deg"], u["grip_axis_offset"]),
            "Grip 9 verts in hand / 9 out; tip centred (offset 0.0)",
        ]),
        ("Raindrops & pleats", [
            "Drops x5: 0.0174-0.0214 relief (req 0.005-0.03)",
            "Hat drop: 0.0330, analytic 0.0293 (diff 0.0037, tol 0.012)",
            "Pleats x8: 0.0263-0.0305 (req 0.020-0.032)",
            "Drops at 270/262/278/225/315 deg, hat drop clears band",
            "Buckle 0.0144 / earring 0.0189 analytic / boot cuff 0.006",
        ]),
        ("Materials (Principled BSDF vs design)", [
            "10/10 match: RainYellow / Cream / Navy / RainBlue",
            "Silver / Gold / LightBlue / Hair Black / Skin / Eye Dark",
            "No texture maps (procedural colours only)",
        ]),
        ("FAIL: hair streak invisible", [
            "Streak visible 1/26 verts, lift 0.0000 (req >= 0.005):",
            "the streak sits inside the head sphere (front y -0.146",
            "vs head surface -0.164) — nothing shows under the brim.",
            "Fix: move the streak out to (0.11, -0.185, 1.44), or",
            "raise it above z 1.50. Then re-run this QA (042).",
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
    d.text((36, 26), "Asset QA Sheet  |  Rainy-Day Urban Set (040)",
           fill=(255, 255, 255), font=font(48, bold=True))
    verdict = "FAIL - 1 ITEM" if not s["overall_pass"] else "PASS"
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
              "Streak 1/26 visible, lift 0.0000   |   "
              "Mats 10/10   |   Ground: z=0.0   |   Frame: %.3f" % (
                  s["total_faces"], s["ngons"], s["duplicate_verts"],
                  s["inverted_normals_solids"], n_pass, len(s["gaps"]),
                  s["frame_fraction"]))
    d.text((36, fy + 12), footer, fill=(60, 60, 60), font=font(30))
    sheet.save(SHEET)
    print("SHEET_WRITTEN:", SHEET, sheet.size)


if __name__ == "__main__":
    main()
