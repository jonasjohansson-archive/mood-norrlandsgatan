"""Per-panel fabrication package for the through-slot + back-clip method.

Reads out/panels.json (panel grid) + out/paths.json (registered figures) and, per panel,
writes a 1:1 mm SVG containing:
  - outline   : the panel cut shape (supplier "shape upload")
  - channels  : the figure lines clipped to this panel = the through-slots to cut on the Shaper
  - clips     : back-clip screw positions along each channel (~CLIP_MM apart, + ends)
  - power     : power-injection points (where a run crosses a panel edge)
Plus out/panels/_key.svg (placement map with panel IDs) and out/panels/schedule.csv.

    uv run python export_panels.py
"""
import json, math, csv
from pathlib import Path

HERE = Path(__file__).parent; OUT = HERE / "out"; PDIR = OUT / "panels"; PDIR.mkdir(exist_ok=True)
CLIP_MM = 200.0                                   # back-clip spacing along a run
SLOT_W  = 6.0                                     # neon body width (slot width)

P = json.load(open(OUT / "panels.json"))
panels = P["panels"]; pw, ph = P["panel_w"], P["panel_h"]
strokes = [(b["color"], b["points"]) for b in json.load(open(OUT / "paths.json")) if b.get("color") != "#f2f2f2"]

def clip(p, q, r):
    """Liang-Barsky: clip segment p->q to rect r=(xmin,ymin,xmax,ymax). Returns (s,e) or None."""
    x0, y0 = p; x1, y1 = q; xmin, ymin, xmax, ymax = r
    dx, dy = x1-x0, y1-y0; t0, t1 = 0.0, 1.0
    for pe, qe in ((-dx, x0-xmin), (dx, xmax-x0), (-dy, y0-ymin), (dy, ymax-y0)):
        if pe == 0:
            if qe < 0: return None
        else:
            t = qe/pe
            if pe < 0:
                if t > t1: return None
                t0 = max(t0, t)
            else:
                if t < t0: return None
                t1 = min(t1, t)
    return ((x0+t0*dx, y0+t0*dy), (x0+t1*dx, y0+t1*dy))

def clip_stroke(pts, r):
    """clip a polyline to rect -> list of sub-polylines inside the rect."""
    out, cur = [], []
    for k in range(len(pts)-1):
        c = clip(pts[k], pts[k+1], r)
        if c is None:
            if len(cur) >= 2: out.append(cur)
            cur = []
        else:
            s, e = c
            if cur and abs(cur[-1][0]-s[0]) < 0.5 and abs(cur[-1][1]-s[1]) < 0.5:
                cur.append(e)
            else:
                if len(cur) >= 2: out.append(cur)
                cur = [s, e]
    if len(cur) >= 2: out.append(cur)
    return out

def along(poly, d):
    """points every d mm of arc length along a polyline (incl. both ends) = clip positions."""
    out = [poly[0]]; carry = 0.0                 # carry = arc distance since the last emitted point
    for i in range(1, len(poly)):
        a, b = poly[i-1], poly[i]; seg = math.dist(a, b)
        if seg <= 0: continue
        pos = d - carry
        while pos <= seg:
            t = pos/seg
            out.append((a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t))
            pos += d
        carry = (carry + seg) % d
    if math.dist(out[-1], poly[-1]) > d*0.4: out.append(poly[-1])
    return out

def path_d(poly, a, e):   # local coords, y flipped to SVG (panel top = 0)
    return "M " + " L ".join(f"{x-a:.1f} {e-y:.1f}" for x, y in poly)

WEB_MIN = 26.0            # 6 mm slot + 20 mm phenolic web: closer than this needs a bridge
def thin_spots(chans):
    """spots where two slots run closer than WEB_MIN -> leave a ~30 mm bridge (slot uncut)."""
    from collections import defaultdict as dd
    G = 50; H = dd(list)
    for ci, (_, poly) in enumerate(chans):
        for pi, p in enumerate(poly): H[(int(p[0]//G), int(p[1]//G))].append((ci, pi, p[0], p[1]))
    spots, seen = [], set()
    for (gx, gy), pl in H.items():
        near = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1): near += H.get((gx+dx, gy+dy), [])
        for (ci, pi, x, y) in pl:
            for (cj, pj, x2, y2) in near:
                if cj == ci and abs(pj - pi) < 20: continue
                if (x-x2)**2 + (y-y2)**2 < WEB_MIN**2:
                    k = (round(x/60), round(y/60))
                    if k not in seen: seen.add(k); spots.append(((x+x2)/2, (y+y2)/2))
    return spots

rows = []; tot_clips = tot_feeds = 0; tot_len = 0.0; all_clips = []
for idx, (a, b, c, e) in enumerate(panels):
    r = (a, b, c, e); w, h = c-a, e-b
    chans = [(col, sp) for col, pts in strokes for sp in clip_stroke(pts, r)]
    if not chans: continue                       # blank panel (no figure) — no channel SVG needed
    clips = [pt for _, poly in chans for pt in along(poly, CLIP_MM)]
    feeds = [pt for pt in P["breaks"] if a-1 <= pt[0] <= c+1 and b-1 <= pt[1] <= e+1]
    webs  = thin_spots(chans)
    plen = sum(math.dist(poly[i], poly[i+1]) for _, poly in chans for i in range(len(poly)-1)) / 1000
    pid = f"P{idx:02d}"
    g_ch  = "".join(f'<path d="{path_d(poly,a,e)}" fill="none" stroke="{col}" stroke-width="{SLOT_W}" stroke-opacity="0.9"/>' for col, poly in chans)
    g_cl  = "".join(f'<circle cx="{x-a:.1f}" cy="{e-y:.1f}" r="2" fill="none" stroke="#0b5" stroke-width="0.6"/>' for x, y in clips)
    g_pw  = "".join(f'<circle cx="{x-a:.1f}" cy="{e-y:.1f}" r="5" fill="none" stroke="#e33" stroke-width="1"/>' for x, y in feeds)
    g_wb  = "".join(f'<circle cx="{x-a:.1f}" cy="{e-y:.1f}" r="9" fill="none" stroke="#e6a817" stroke-width="1.5"/>' for x, y in webs)
    (PDIR / f"{pid}.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}mm" height="{h:.0f}mm" viewBox="0 0 {w:.0f} {h:.0f}">'
        f'<g id="outline"><rect x="0" y="0" width="{w:.0f}" height="{h:.0f}" fill="none" stroke="#000" stroke-width="1"/></g>'
        f'<g id="channels">{g_ch}</g><g id="clips">{g_cl}</g><g id="power">{g_pw}</g><g id="bridges">{g_wb}</g></svg>')
    rows.append([pid, f"{w:.0f}x{h:.0f}", round(w*h/1e6, 2), round(w*h*6*1.45e-6, 1),
                 len(chans), round(plen, 2), len(clips), len(feeds), len(webs)])
    tot_clips += len(clips); tot_feeds += len(feeds); tot_len += plen
    all_clips += [[round(x,1), round(y,1)] for x, y in clips]

json.dump({"clips": all_clips, "power": P["breaks"]}, open(OUT / "clips.json", "w"))

with open(PDIR / "schedule.csv", "w", newline="") as f:
    wtr = csv.writer(f); wtr.writerow(["panel", "size_mm", "area_m2", "kg", "runs", "led_m", "clips", "power_feeds", "bridges"]); wtr.writerows(rows)

# placement key: all panels + IDs + faint figures
kx0 = min(p[0] for p in panels); ky0 = min(p[1] for p in panels)
kx1 = max(p[2] for p in panels); ky1 = max(p[3] for p in panels); KW, KH = kx1-kx0, ky1-ky0
figs = "".join(f'<polyline points="{" ".join(f"{x-kx0:.0f},{ky1-y:.0f}" for x,y in pts)}" fill="none" stroke="{col}" stroke-width="8" stroke-opacity="0.5"/>' for col, pts in strokes)
recs = ""
for idx, (a, b, c, e) in enumerate(panels):
    recs += (f'<rect x="{a-kx0:.0f}" y="{ky1-e:.0f}" width="{c-a:.0f}" height="{e-b:.0f}" fill="none" stroke="#333" stroke-width="4"/>'
             f'<text x="{a-kx0+40:.0f}" y="{ky1-e+120:.0f}" font-size="90" fill="#333">P{idx:02d}</text>')
(PDIR / "_key.svg").write_text(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {KW:.0f} {KH:.0f}"><rect width="{KW:.0f}" height="{KH:.0f}" fill="#fff"/>{figs}{recs}</svg>')

print(f"{len(rows)} panels with figures  |  {tot_len:.0f} m LED  |  {tot_clips} clips  |  {tot_feeds} power feeds")
print(f"wrote {PDIR}/  (per-panel SVGs + _key.svg + schedule.csv)")
