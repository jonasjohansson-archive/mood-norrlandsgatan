"""Panelize the soffit into ~1-2 m boards whose seams dodge the figures.

Reads the registered figures (out/paths.json) + soffit footprint (ceiling.json), lays a
grid of panels over the covered area, and SLIDES the grid origin to the offset that makes
the seams cross the fewest neon lines (so cuts fall in gaps / thin limbs). Every seam
crossing is a place the LED strip must break + a natural power-injection point.

Writes out/panels.json (panels, seams, break points, stats) for the viewer.

    uv run python panelize.py [panel_w_mm] [panel_h_mm]      # default 1400 x 1400
"""
import sys, json
from pathlib import Path

HERE = Path(__file__).parent; OUT = HERE / "out"
PW = float(sys.argv[1]) if len(sys.argv) > 1 else 1400.0
PH = float(sys.argv[2]) if len(sys.argv) > 2 else PW
THICK_MM, DENSITY = 6.0, 1.45e-6   # Trespa Meteon 6 mm black RAL 9005 (~1.45 g/cm^3 -> kg)
MAX_W, MAX_H = 2300.0, 1100.0      # supplier cut-to-size limit

cells = json.load(open(HERE / "ceiling.json"))["cells"]
cs = json.load(open(HERE / "ceiling.json"))["cell_mm"]
strokes = [b["points"] for b in json.load(open(OUT / "paths.json")) if b.get("color") != "#f2f2f2"]

xs = [c[0] for c in cells]; ys = [c[1] for c in cells]
x0, x1, y0, y1 = min(xs)-cs/2, max(xs)+cs/2, min(ys)-cs/2, max(ys)+cs/2
tiles = {(round((c[0]-x0)//cs), round((c[1]-y0)//cs)) for c in cells}   # not used; keep coverage by point test

def covered(px0, py0, px1, py1):   # rect (or point) overlaps a soffit tile? expand by half a tile
    m = cs/2
    for c in cells:
        if px0-m <= c[0] <= px1+m and py0-m <= c[1] <= py1+m:
            return True
    return False

def crossings(ox, oy):
    """count neon points that sit within ~1 cell of a grid line at offset (ox,oy)."""
    n = 0
    for pts in strokes:
        for x, y in pts:
            gx = (x - ox) % PW; gy = (y - oy) % PH
            near_v = min(gx, PW-gx) < 20; near_h = min(gy, PH-gy) < 20
            if near_v or near_h: n += 1
    return n

# slide the grid origin to the offset with the fewest crossings (dodge figures)
best = None
STEPS = 10
for i in range(STEPS):
    for j in range(STEPS):
        ox, oy = x0 + PW*i/STEPS, y0 + PH*j/STEPS
        c = crossings(ox, oy)
        if best is None or c < best[0]: best = (c, ox, oy)
_, ox, oy = best

# build covered panels on that grid
import math
i0 = math.floor((x0 - ox)/PW); i1 = math.ceil((x1 - ox)/PW)
j0 = math.floor((y0 - oy)/PH); j1 = math.ceil((y1 - oy)/PH)
panels = []
for i in range(i0, i1):
    for j in range(j0, j1):
        a, b, cc, d = ox+i*PW, oy+j*PH, ox+(i+1)*PW, oy+(j+1)*PH
        if covered(a, b, cc, d):
            panels.append([round(a,1), round(b,1), round(cc,1), round(d,1)])

# break points: where a neon segment crosses a grid line inside the covered area
def seg_cross_line(p, q, coord, axis):
    a, b = (p[axis], q[axis])
    if (a-coord)*(b-coord) >= 0: return None
    t = (coord-a)/(b-a)
    return [round(p[0]+(q[0]-p[0])*t,1), round(p[1]+(q[1]-p[1])*t,1)]
lines_v = [ox+k*PW for k in range(i0, i1+1)]
lines_h = [oy+k*PH for k in range(j0, j1+1)]
breaks = []
for pts in strokes:
    for k in range(len(pts)-1):
        p, q = pts[k], pts[k+1]
        for L in lines_v:
            if min(p[0],q[0]) < L < max(p[0],q[0]):
                pt = seg_cross_line(p,q,L,0)
                if pt and covered(pt[0],pt[1],pt[0],pt[1]): breaks.append(pt)
        for L in lines_h:
            if min(p[1],q[1]) < L < max(p[1],q[1]):
                pt = seg_cross_line(p,q,L,1)
                if pt and covered(pt[0],pt[1],pt[0],pt[1]): breaks.append(pt)

area = PW*PH/1e6
kg = PW*PH*THICK_MM*DENSITY
out = {"panel_w": PW, "panel_h": PH, "origin": [round(ox,1), round(oy,1)],
       "panels": panels, "vlines": [round(v,1) for v in lines_v], "hlines": [round(h,1) for h in lines_h],
       "breaks": breaks}
(OUT / "panels.json").write_text(json.dumps(out))
warn = "  ⚠ EXCEEDS 230x110 cm supplier max!" if (PW > MAX_W or PH > MAX_H) else ""
print(f"panel {PW:.0f}x{PH:.0f} mm ({area:.1f} m^2, ~{kg:.1f} kg @ {THICK_MM:.0f}mm Trespa){warn}")
print(f"panels: {len(panels)}   seam breaks/power points: {len(breaks)}   grid offset {ox-x0:.0f},{oy-y0:.0f} mm (dodges figures)")
