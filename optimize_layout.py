"""Per-figure transform search: translate / rotate / scale-down so seams cut less.

Coordinate descent per figure (colour group): translation (100 mm steps, max +/-300 mm),
rotation about the figure centroid (max +/-10 deg), uniform scale (shrink only, >=0.88).
Every candidate re-runs the band-DP seam placement; keep the transform with fewest
breaks (ties -> fewer panels -> smallest change). Rings stay locked to the pillars;
figures must stay on the soffit.

Applies winners to out/paths.json (original is out/paths_prenudge.json from the first
run). Then re-run panelize_mixed.py + export_panels.py.

    uv run python optimize_layout.py
"""
import json, math, bisect
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).parent; OUT = HERE / "out"
CS, BH, WMAX = 500.0, 1000.0, 4
ALPHA, BETA = 1.0, 10.0
TR = [-300, -200, -100, 0, 100, 200, 300]
ROT = [-10, -6, -3, 0, 3, 6, 10]
SC = [1.0, 0.96, 0.92, 0.88]
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

figs = defaultdict(list)
for i, b in enumerate(bodies):
    if b.get("color") != "#f2f2f2": figs[b["color"]].append(i)
cent = {}
for c, idxs in figs.items():
    px = [p for i in idxs for p in bodies[i]["points"]]
    cent[c] = (sum(q[0] for q in px)/len(px), sum(q[1] for q in px)/len(px))
state = {c: [0.0, 0.0, 0.0, 1.0] for c in figs}      # dx, dy, deg, scale

def xf(c, p):
    dx, dy, deg, s = state[c]; cx, cy = cent[c]
    a = math.radians(deg); ca, sa = math.cos(a), math.sin(a)
    ux, uy = p[0]-cx, p[1]-cy
    return (cx + s*(ux*ca - uy*sa) + dx, cy + s*(ux*sa + uy*ca) + dy)

def build_strokes():
    out = []
    for c, idxs in figs.items():
        for i in idxs: out.append([xf(c, p) for p in bodies[i]["points"]])
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
    edges = []; yb = y0
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
                        cc = dp[k-w] + ALPHA + BETA*seam
                        if cc < dp[k]: dp[k] = cc; prev[k] = k-w
                k = n
                while k > 0:
                    np += 1
                    if k < n: nb += bisect.bisect_right(vcross[s+k], bb) - bisect.bisect_left(vcross[s+k], ba)
                    k = prev[k]
                run = []
        if ba > y0 + 1: nb += hcount(ba)
    return (nb, np)

def fig_ok(c):
    bad = tot = 0
    for i in figs[c]:
        for p in bodies[i]["points"][::12]:
            tot += 1
            q = xf(c, p)
            if not on_soffit(*q): bad += 1
    return bad <= tot * 0.005

def change_mag(st):
    return abs(st[0]) + abs(st[1]) + 30*abs(st[2]) + 4000*(1.0-st[3])

def descend(c, axis_vals, setter):
    best = (evaluate(), change_mag(state[c]), list(state[c]))
    for v in axis_vals:
        old = list(state[c]); setter(v)
        if state[c] == old or not fig_ok(c):
            state[c] = old; continue
        sc = evaluate(); mag = change_mag(state[c])
        if (sc, mag) < (best[0], best[1]): best = (sc, mag, list(state[c]))
        state[c] = old
    state[c] = best[2]
    return best[0]

base = evaluate()
print(f"start: {base[0]} breaks, {base[1]} panels")
for p in range(PASSES):
    for c in figs:
        # translation (grid), then rotation, then scale
        cur = tuple(state[c])
        best = (evaluate(), change_mag(state[c]), list(state[c]))
        for dx in TR:
            for dy in TR:
                cand = [cur[0]+dx, cur[1]+dy, cur[2], cur[3]]
                if abs(cand[0]) > 300 or abs(cand[1]) > 300 or (dx == 0 and dy == 0): continue
                state[c] = cand
                if not fig_ok(c): state[c] = list(cur); continue
                sc = evaluate(); mag = change_mag(state[c])
                if (sc, mag) < (best[0], best[1]): best = (sc, mag, list(state[c]))
                state[c] = list(cur)
        state[c] = best[2]
        sc = descend(c, ROT, lambda v: state[c].__setitem__(2, v))
        sc = descend(c, SC,  lambda v: state[c].__setitem__(3, v))
        print(f"  pass {p+1}  {c}: dx={state[c][0]:.0f} dy={state[c][1]:.0f} rot={state[c][2]:.0f}° scale={state[c][3]:.2f} -> {sc[0]} breaks")

final = evaluate()
print(f"final: {final[0]} breaks, {final[1]} panels  (was {base[0]} / {base[1]})")

for c, idxs in figs.items():
    if state[c] == [0.0, 0.0, 0.0, 1.0]: continue
    for i in idxs:
        bodies[i]["points"] = [[round(q[0], 1), round(q[1], 1)] for q in (xf(c, p) for p in bodies[i]["points"])]
(OUT / "paths.json").write_text(json.dumps(bodies, indent=1))
print("applied transforms to out/paths.json")
print({c: tuple(state[c]) for c in state if state[c] != [0.0, 0.0, 0.0, 1.0]})
