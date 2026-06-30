"""Import the ceiling layout SVG (50 cm tile grid + columns) -> ceiling.json,
which figure.py uses to build the real soffit footprint at true scale.

    uv run python ceiling_import.py "/path/Asset 8.svg"
"""
import re, json, sys
from pathlib import Path

src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Desktop/Asset 8.svg"
txt = src.read_text()

rects = re.findall(r'<rect[^>]*?x="([\d.]+)"\s+y="([\d.]+)"\s+width="([\d.]+)"\s+height="([\d.]+)"', txt)
circs = re.findall(r'<circle[^>]*?cx="([\d.]+)"\s+cy="([\d.]+)"\s+r="([\d.]+)"', txt)
vb = re.search(r'viewBox="([-\d.\s]+)"', txt).group(1).split()
W, H = float(vb[2]), float(vb[3])

CELL_U = float(rects[0][2])          # tile size in svg units
SCALE = 500.0 / CELL_U               # mm per svg unit (each tile = 500 mm)
cx0, cy0 = W / 2, H / 2
to_mm = lambda x, y: [round((x - cx0) * SCALE, 1), round((cy0 - y) * SCALE, 1)]

cells = [to_mm(float(x) + float(w) / 2, float(y) + float(h) / 2) for x, y, w, h in rects]
columns = [{"c": to_mm(float(cx), float(cy)), "r": round(float(r) * SCALE, 1)} for cx, cy, r in circs]

data = {"cell_mm": 500.0, "w_mm": round(W * SCALE, 1), "h_mm": round(H * SCALE, 1),
        "cells": cells, "columns": columns}
out = Path(__file__).parent / "ceiling.json"
out.write_text(json.dumps(data))
print(f"{len(cells)} tiles, {len(columns)} columns, "
      f"{W*SCALE/1000:.2f} x {H*SCALE/1000:.2f} m  ->  {out.name}")
for col in columns:
    print(f"  column at {col['c']} mm, r {col['r']} mm")
