# -*- coding: utf-8 -*-
"""Draw a wireframe overlay (projected edge segments) on top of a beauty
render. System python3 + PIL.
Usage: python3 draw_wireframe.py <beauty.png> <segments.json> <output.png>
"""
import json
import sys
from PIL import Image, ImageDraw

beauty_path, seg_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
img = Image.open(beauty_path).convert("RGB")
W, H = img.size
with open(seg_path, encoding="utf-8") as fh:
    segments = json.load(fh)
d = ImageDraw.Draw(img)
for x0, y0, x1, y1 in segments:
    d.line([(x0 * W, y0 * H), (x1 * W, y1 * H)],
           fill=(25, 25, 30), width=2)
img.save(out_path)
print("WIREFRAME_DRAWN:", out_path, "segments:", len(segments))
