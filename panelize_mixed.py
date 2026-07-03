"""Mixed panelization v2 — brick bands + DP seams + portrait merges + stub avoidance.

1. The soffit splits into 1.0 m bands; per band a DP places vertical seams (panel widths
   0.5-2.0 m in 0.5 m modules) where they cross the fewest figure lines. Seam cost also
   penalizes cuts that would leave an LED piece < MINP mm (stubs).
2. Portrait pass: where figures still cross a horizontal band line, the two stacked
   panels are locally re-tiled into portrait boards (<=1.0 m wide x 2 bands tall) that
   swallow the horizontal seam. Accepted only where it reduces total breaks.
3. Breaks/stubs are then recomputed from the final geometry.

Writes out/panels.json (same schema the viewer + export_panels.py read).

    uv run python panelize_mixed.py
"""
import json, math, bisect, sys
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).parent; OUT = HERE / "out"
CS, BH, WMAX = 500.0, 1000.0, 4          # module, band height, max width (modules)
ALPHA, BETA = 1.0, 10.0                  # panel-count vs crossing cost
MINP, STUB_PEN = 150.0, 30.0             # min usable LED piece; penalty for stub-making cuts
VERT = "--vertical" in sys.argv          # rotate the whole band structure 90 deg
SWAP = (lambda p: (p[1], p[0])) if VERT else (lambda p: (p[0], p[1]))

d = json.load(open(HERE / "ceiling.json")); cells = [SWAP(c) for c in d["cells"]]; tcs = d["cell_mm"]
bodies = [b for b in json.load(open(OUT / "paths.json")) if b.get("color") != "#f2f2f2"]
if VERT:
    bodies = [{**b, "points": [SWAP(p) for p in b["points"]]} for b in bodies]
strokes, cums = [], []
for b in bodies:
    pts = [tuple(p) for p in b["points"]]; cum = [0.0]
    for i in range(1, len(pts)): cum.append(cum[-1] + math.dist(pts[i], pts[i-1]))
    strokes.append(pts); cums.append(cum)
xs = [c[0] for c in cells]; ys = [c[1] for c in cells]
x0, x1 = min(xs)-tcs/2, max(xs)+tcs/2; y0, y1 = min(ys)-tcs/2, max(ys)+tcs/2
NX = math.ceil((x1-x0)/CS)

def covered(a, b, c, e):
    m = tcs/2
    return any(a-m <= p[0] <= c+m and b-m <= p[1] <= e+m for p in cells)

# crossings of every vertical module line: vc[k] = sorted [(y, stroke, arc)]
vc = [[] for _ in range(NX+1)]
for s, (pts, cum) in enumerate(zip(strokes, cums)):
    for k in range(len(pts)-1):
        (ax, ay), (bx, by) = pts[k], pts[k+1]
        lo = max(0, math.ceil((min(ax,bx)-x0)/CS)); hi = min(NX, math.floor((max(ax,bx)-x0)/CS))
        for ii in range(lo, hi+1):
            X = x0+ii*CS
            if (ax-X)*(bx-X) < 0:
                t = (X-ax)/(bx-ax)
                vc[ii].append((ay + t*(by-ay), s, cum[k] + t*(cum[k+1]-cum[k])))
for L in vc: L.sort()

def hcrossings(Y):
    out = []
    for s, (pts, cum) in enumerate(zip(strokes, cums)):
        for k in range(len(pts)-1):
            (ax, ay), (bx, by) = pts[k], pts[k+1]
            if (ay-Y)*(by-Y) < 0:
                t = (Y-ay)/(by-ay)
                out.append((ax + t*(bx-ax), s, cum[k] + t*(cum[k+1]-cum[k])))
    return sorted(out)

def vslice(k, ya, yb):
    a = bisect.bisect_left(vc[k], (ya, -1, -1.0)); b = bisect.bisect_right(vc[k], (yb, 1<<30, 1e18))
    return vc[k][a:b]

# ---------------- band structure ----------------
edges = []; yb = y0
while yb < y1 - 1: edges.append((yb, min(yb+BH, y1))); yb += BH
NBAND = len(edges)
Hs = {j: hcrossings(edges[j][0]) for j in range(1, NBAND)}          # crossings on each interior band line

# fixed arc points per stroke (ends + horizontal-line crossings) for the stub penalty
fixed = defaultdict(list)
for s, cum in enumerate(cums): fixed[s] += [0.0, cum[-1]]
for j in Hs:
    for (x, s, arc) in Hs[j]: fixed[s].append(arc)
for s in fixed: fixed[s].sort()

def stubby(s, arc):
    i = bisect.bisect_left(fixed[s], arc)
    near = min([abs(arc-fixed[s][i-1]) if i > 0 else 1e18,
                abs(fixed[s][i]-arc) if i < len(fixed[s]) else 1e18])
    return near < MINP

def seam_cost(k, ya, yb):
    cr = vslice(k, ya, yb)
    return BETA*len(cr) + STUB_PEN*sum(1 for (_, s, arc) in cr if stubby(s, arc))

# per-band DP -> cuts (cut positions in cells) per covered run
bands = []   # per band: list of runs (s, e, cuts[list of interior cell cuts], consumed=[])
for j, (ba, bb) in enumerate(edges):
    runs = []; run = []
    for i in range(NX):
        ok = covered(x0+i*CS, ba, x0+(i+1)*CS, bb)
        if ok: run.append(i)
        if (not ok or i == NX-1) and run:
            s, e = run[0], run[-1]+1; n = e - s
            INF = 1e18; dp = [0.0]+[INF]*n; prev = [-1]*(n+1)
            for k in range(1, n+1):
                for w in range(1, min(WMAX, k)+1):
                    c = dp[k-w] + ALPHA + (seam_cost(s+k, ba, bb) if k < n else 0)
                    if c < dp[k]: dp[k] = c; prev[k] = k-w
            k = n; cutl = []
            while k > 0:
                if k < n: cutl.append(s+k)
                k = prev[k]
            runs.append({"s": s, "e": e, "cuts": sorted(cutl), "consumed": []})
            run = []
    bands.append({"ba": ba, "bb": bb, "runs": runs})

# ---------------- portrait pass ----------------
portraits = []
def run_at(j, col):
    for r in bands[j]["runs"]:
        if r["s"] <= col < r["e"]: return r
    return None

for j in range(1, NBAND):
    ba0, bb1 = bands[j-1]["ba"], bands[j]["bb"]
    if bb1 - ba0 > 2000 + 1: continue                    # portrait long side limit (2.0 m)
    Y = bands[j]["ba"]
    # cluster crossings into module-aligned windows (<= 4 modules wide)
    cols = sorted({int((x - x0)//CS) for (x, s, a) in Hs[j]})
    wins = []
    for c in cols:
        if wins and c <= wins[-1][1] + 1 and c - wins[-1][0] < 4: wins[-1][1] = c
        else: wins.append([c, c])
    for (wa, wb) in wins:
        wb += 1                                           # cells [wa, wb)
        while wb - wa < 2 and wb < NX: wb += 1            # widen to >= 1.0 m for tiling freedom
        rA, rB = run_at(j-1, wa), run_at(j, wa)
        if not rA or not rB: continue
        if rA is not run_at(j-1, wb-1) or rB is not run_at(j, wb-1): continue
        if any(a <= wa < b or a < wb <= b for (a, b) in rA["consumed"] + rB["consumed"]): continue
        if not (rA["s"] <= wa and wb <= rA["e"] and rB["s"] <= wa and wb <= rB["e"]): continue
        # old local breaks: horizontal crossings in window + existing seams inside window
        old = sum(1 for (x, s, a) in Hs[j] if x0+wa*CS <= x <= x0+wb*CS)
        for (r, band) in ((rA, bands[j-1]), (rB, bands[j])):
            for ccut in r["cuts"]:
                if wa <= ccut <= wb: old += len(vslice(ccut, band["ba"], band["bb"]))
        # new local: window edge seams (if interior) + portrait interior seams, full double height
        def edge_cost(col, r):
            return 0 if (col == r["s"] or col == r["e"]) else len(vslice(col, ba0, bb1))
        new = (0 if (wa == rA["s"] and wa == rB["s"]) else len(vslice(wa, ba0, bb1))) \
            + (0 if (wb == rA["e"] and wb == rB["e"]) else len(vslice(wb, ba0, bb1)))
        n = wb - wa                                       # mini-DP: portrait widths 1-2 modules
        INF = 1e18; dp = [0.0]+[INF]*n; prev = [-1]*(n+1)
        for k in range(1, n+1):
            for w in (1, 2):
                if w > k: continue
                c = dp[k-w] + ALPHA + (len(vslice(wa+k, ba0, bb1))*BETA if k < n else 0)
                if c < dp[k]: dp[k] = c; prev[k] = k-w
        k = n; pcuts = []
        while k > 0:
            if k < n: pcuts.append(wa+k)
            k = prev[k]
        new += sum(len(vslice(c, ba0, bb1)) for c in pcuts)
        if new >= old: continue
        # accept: consume window in both bands, add portraits
        for r in (rA, rB):
            r["cuts"] = sorted({c for c in r["cuts"] if not (wa < c < wb)} | ({wa} if wa > r["s"] else set()) | ({wb} if wb < r["e"] else set()))
            r["consumed"].append((wa, wb))
        for a, b in zip([wa]+sorted(pcuts), sorted(pcuts)+[wb]):
            portraits.append([round(x0+a*CS,1), round(ba0,1), round(x0+b*CS,1), round(bb1,1)])

# ---------------- assemble + final audit from geometry ----------------
panels = list(portraits)
for band in bands:
    for r in band["runs"]:
        marks = sorted({r["s"], r["e"], *r["cuts"], *[c for iv in r["consumed"] for c in iv]})
        for a, b in zip(marks, marks[1:]):
            if any(ca <= a and b <= cb for (ca, cb) in r["consumed"]): continue
            panels.append([round(x0+a*CS,1), round(band["ba"],1), round(x0+b*CS,1), round(band["bb"],1)])

# breaks: shared edges between different panels
breaks = []; cutarcs = defaultdict(list)
vedges = defaultdict(list); hedges = defaultdict(list)
for pid, (a, b, c, e) in enumerate(panels):
    vedges[round(a,1)].append((b, e, pid)); vedges[round(c,1)].append((b, e, pid))
    hedges[round(b,1)].append((a, c, pid)); hedges[round(e,1)].append((a, c, pid))
for X, ivs in vedges.items():
    k = round((X - x0)/CS)
    if not (0 <= k <= NX): continue
    for i in range(len(ivs)):
        for jj in range(i+1, len(ivs)):
            (b1, e1, p1), (b2, e2, p2) = ivs[i], ivs[jj]
            if p1 == p2: continue
            lo, hi = max(b1, b2), min(e1, e2)
            if hi - lo < 1: continue
            for (y, s, arc) in vslice(k, lo, hi):
                breaks.append([round(X,1), round(y,1)]); cutarcs[s].append(arc)
for Y, ivs in hedges.items():
    H = hcrossings(Y)
    if not H: continue
    for i in range(len(ivs)):
        for jj in range(i+1, len(ivs)):
            (a1, c1, p1), (a2, c2, p2) = ivs[i], ivs[jj]
            if p1 == p2: continue
            lo, hi = max(a1, a2), min(c1, c2)
            if hi - lo < 1: continue
            for (x, s, arc) in H:
                if lo <= x <= hi: breaks.append([round(x,1), round(Y,1)]); cutarcs[s].append(arc)
seen = set(); ub = []
for p in breaks:
    key = (round(p[0]), round(p[1]))
    if key not in seen: seen.add(key); ub.append(p)
breaks = ub

pieces = stubs = 0
for s, cum in enumerate(cums):
    cutl = sorted({0.0, cum[-1], *cutarcs.get(s, [])})
    for a, b in zip(cutl, cutl[1:]):
        pieces += 1
        if b - a < MINP: stubs += 1

if VERT:   # swap back to world coords
    panels = [[p[1], p[0], p[3], p[2]] for p in panels]
    breaks = [[p[1], p[0]] for p in breaks]
out = {"panel_w": 2000.0, "panel_h": BH, "origin": [round(x0,1), round(y0,1)],
       "panels": panels, "vlines": [], "hlines": [], "breaks": breaks, "mixed": True,
       "module_mm": CS, "orientation": "vertical" if VERT else "horizontal"}
(OUT / "panels.json").write_text(json.dumps(out))

from collections import Counter
sizes = Counter(f"{(p[2]-p[0])/1000:.1f}x{(p[3]-p[1])/1000:.1f}" for p in panels)
print(f"v2 layout ({'vertical' if VERT else 'horizontal'} bands): {len(panels)} panels ({len(portraits)} portrait), {len(breaks)} breaks, "
      f"{pieces} LED pieces, {stubs} stubs <{MINP:.0f}mm")
for sz, n in sizes.most_common():
    w, h = (float(v) for v in sz.split("x"))
    print(f"  {n:3d} x {sz} m  (~{w*h*6*1.45:.1f} kg)")
