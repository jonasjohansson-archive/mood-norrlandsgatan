"""Nudge figures slightly so panel seams cut them less, re-optimizing seams each time.

Coordinate descent: for each figure (colour group), try small offsets (multiples of
100 mm, max +/-300 mm); for every candidate the band-DP re-places all seams and we keep
the offset with the fewest total breaks (ties -> fewer panels, then smallest move).
Rings (#f2f2f2) stay locked to the pillars. Figures must stay on the soffit.

Applies the winning offsets to out/paths.json (original backed up once to
out/paths_prenudge.json). Then re-run panelize_mixed.py + export_panels.py.

    uv run python optimize_layout.py
"""
import json, math, bisect
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).parent; OUT = HERE / "out"
CS, BH, WMAX = 500.0, 1000.0, 4
ALPHA, BETA = 1.0, 10.0
STEPS = [-300, -200, -100, 0, 100, 200, 300]
PASSES = 2

d = json.load(open(HERE / "ceiling.json")); cells = d["cells"]; tcs = d["cell_mm"]
bodies = json.load(open(OUT / "paths.json"))
xs = [c[0] for c in cells]; ys = [c[1] for c in cells]
x0, x1 = min(xs)-tcs/2, max(xs)+tcs/2; y0, y1 = min(ys)-tcs/2, max(ys)+tcs/2
NX = math.ceil((x1-x0)/CS)

def covered(a, b, c, e):
    m = tcs/2
    return any(a-m <= p[0] <= c+m and b-m <= p[1] <= e+m for p in cells)
def on_soffit(x, y):
    m = tcs/2
    return any(abs(x-p[0]) <= m+1 and abs(y-p[1]) <= m+1 for p in cells)

figs = defaultdict(list)     # colour -> [body index]
for i, b in enumerate(bodies):
    if b.get("color") != "#f2f2f2": figs[b["color"]].append(i)
offsets = {c: (0.0, 0.0) for c in figs}

def build_strokes():
    out = []
    for c, idxs in figs.items():
        dx, dy = offsets[c]
        for i in idxs:
            out.append([(p[0]+dx, p[1]+dy) for p in bodies[i]["points"]])
    return out

def evaluate():
    strokes = build_strokes()
    vcross = [[] for _ in range(NX+1)]
    for pts in strokes:
        for k in range(len(pts)-1):
            (ax, ay), (bx, by) = pts[k], pts[k+1]
            lo = max(0, math.ceil((min(ax,bx)-x0)/CS)); hi = min(NX, math.floor((max(ax,bx)-x0)/CS))
            for ii in range(lo, hi+1):
                X = x0+ii*CS
                if (ax-X)*(bx-X) < 0: vcross[ii].append(ay + (X-ax)/(bx-ax)*(by-ay))
    for L in vcross: L.sort()
    def hcount(Y):
        n = 0
        for pts in strokes:
            for k in range(len(pts)-1):
                if (pts[k][1]-Y)*(pts[k+1][1]-Y) < 0: n += 1
        return n
    best = None
    for phase in (0.0, 500.0):
        edges = []; yb = y0 + (phase if phase else 0)
        if yb > y0: edges.append((y0, yb))
        while yb < y1 - 1: edges.append((yb, min(yb+BH, y1))); yb += BH
        nb = np = 0
        for (ba, bb) in edges:
            run = []
            for i in range(NX):
                ok = covered(x0+i*CS, ba, x0+(i+1)*CS, bb)
                if ok: run.append(i)
                if (not ok or i == NX-1) and run:
                    s, e = run[0], run[-1]+1; n = e - s
                    INF = 1e18; dp = [0.0]+[INF]*n; prev = [-1]*(n+1)
                    for k in range(1, n+1):
                        for w in range(1, min(WMAX, k)+1):
                            seam = 0 if k == n else bisect.bisect_right(vcross[s+k], bb) - bisect.bisect_left(vcross[s+k], ba)
                            c = dp[k-w] + ALPHA + BETA*seam
                            if c < dp[k]: dp[k] = c; prev[k] = k-w
                    k = n; cuts = []
                    while k > 0: cuts.append(k); k = prev[k]
                    for c in cuts:
                        np += 1
                        if c < n: nb += bisect.bisect_right(vcross[s+c], bb) - bisect.bisect_left(vcross[s+c], ba)
                    run = []
            if ba > y0 + 1: nb += hcount(ba)
        if best is None or (nb, np) < best: best = (nb, np)
    return best

def fig_ok(c, dx, dy):
    bad = tot = 0
    for i in figs[c]:
        for p in bodies[i]["points"][::12]:
            tot += 1
            if not on_soffit(p[0]+dx, p[1]+dy): bad += 1
    return bad <= tot * 0.005

base = evaluate()
print(f"start: {base[0]} breaks, {base[1]} panels")
for p in range(PASSES):
    for c in figs:
        cur = offsets[c]; best = (evaluate(), 0.0, cur)
        for dx in STEPS:
            for dy in STEPS:
                cand = (cur[0]+dx, cur[1]+dy)
                if abs(cand[0]) > 300 or abs(cand[1]) > 300: continue
                if (dx, dy) == (0, 0) or not fig_ok(c, *cand): continue
                offsets[c] = cand
                sc = evaluate()
                move = abs(cand[0])+abs(cand[1])
                if (sc, move) < (best[0], best[1]): best = (sc, move, cand)
        offsets[c] = best[2]
        print(f"  pass {p+1}  {c}: offset {offsets[c]} -> {best[0][0]} breaks")

final = evaluate()
print(f"final: {final[0]} breaks, {final[1]} panels  (was {base[0]} / {base[1]})")

bak = OUT / "paths_prenudge.json"
if not bak.exists(): bak.write_text(json.dumps(bodies, indent=1))
for c, idxs in figs.items():
    dx, dy = offsets[c]
    if dx == 0 and dy == 0: continue
    for i in idxs:
        bodies[i]["points"] = [[round(p[0]+dx, 1), round(p[1]+dy, 1)] for p in bodies[i]["points"]]
(OUT / "paths.json").write_text(json.dumps(bodies, indent=1))
print("applied offsets to out/paths.json (backup: out/paths_prenudge.json)")
print({c: offsets[c] for c in offsets if offsets[c] != (0.0, 0.0)})
