"""Procurement cut list — metres of coloured silicone per colour, segment/feed
count, and power, from the figures. Hand the per-colour totals to Flex-Neon.

    uv run python order.py

Reads paths.json if present (from Bend Lab / svgcheck), else the placeholder bodies.
ASSUMPTIONS (change at the top when you get supplier numbers):
"""
import csv, math
from pathlib import Path
from collections import defaultdict
from figure import load_bodies, scaled
from shaper import catmull

OUT = Path(__file__).parent / "out"; OUT.mkdir(exist_ok=True)

PROFILE   = "FN-ESJT-B0612 6x12 COB, white LED in coloured silicone"
MIN_BEND  = 90.0     # mm  (6x12 COB, assumed — confirm with supplier)
W_PER_M   = 10.0     # W/m (white LED, assumed)
VOLT      = 24       # V
REEL_M    = 100.0    # m per reel/carton (from catalog)
PSU_HEADROOM = 1.25  # size drivers 25% over


def circumR(a, b, c):
    A = abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/2
    if A < 1e-6: return math.inf
    return (math.dist(b,c)*math.dist(a,c)*math.dist(a,b))/(4*A)

def length(pts):
    return sum(math.dist(pts[i], pts[i+1]) for i in range(len(pts)-1))

def resample_d(pts, d=25.0):             # fixed-spacing resample (stable curvature)
    if len(pts) < 2: return list(pts)
    cum = [0.0]
    for i in range(1, len(pts)): cum.append(cum[-1] + math.dist(pts[i], pts[i-1]))
    L = cum[-1] or 1.0; n = max(2, int(L / d)); out = []; j = 0
    for i in range(n + 1):
        t = L*i/n
        while j < len(pts)-2 and cum[j+1] < t: j += 1
        f = (t-cum[j])/((cum[j+1]-cum[j]) or 1)
        out.append((pts[j][0]+(pts[j+1][0]-pts[j][0])*f, pts[j][1]+(pts[j+1][1]-pts[j][1])*f))
    return out

def n_pieces(raw):                       # split where a bend is genuinely too tight
    pts = resample_d(raw)                # measure at ~25 mm, not at noisy dense spacing
    rs = [math.inf] + [circumR(pts[i-1],pts[i],pts[i+1]) for i in range(1,len(pts)-1)] + [math.inf]
    pieces, cur = 0, 0
    for r in rs:
        if r < MIN_BEND:
            if cur > 1: pieces += 1
            cur = 0
        else: cur += 1
    if cur > 1: pieces += 1
    return max(1, pieces)

def samples(kind, pts):
    if kind == "circle":
        cx, cy, r = pts[0]
        return [(cx+r*math.cos(2*math.pi*t/60), cy+r*math.sin(2*math.pi*t/60)) for t in range(61)]
    return catmull(pts)


def build():
    bodies, s = load_bodies()
    rows, by_color, tot_m, tot_seg = [], defaultdict(float), 0.0, 0
    for name, kind, pts, color in bodies:
        k, p = scaled(kind, pts, s)
        sp = samples(k, p)
        Lm = length(sp) / 1000.0
        seg = n_pieces(sp)
        rows.append((name, color, Lm, seg))
        by_color[color] += Lm; tot_m += Lm; tot_seg += seg

    print(f"PROFILE   {PROFILE}")
    print(f"ASSUME    min bend {MIN_BEND:.0f} mm · {W_PER_M:.0f} W/m @ {VOLT} V · {REEL_M:.0f} m reels\n")
    print(f"{'figure':<14}{'colour':<10}{'length':>9}{'segments':>10}")
    for name, color, Lm, seg in rows:
        print(f"{name:<14}{color:<10}{Lm:>7.2f} m{seg:>10}")
    print(f"\n{'ORDER by colour':<14}{'':10}{'metres':>9}{'reels':>10}")
    for color, m in sorted(by_color.items(), key=lambda x:-x[1]):
        print(f"{'':<14}{color:<10}{m:>7.1f} m{math.ceil(m/REEL_M):>10}")

    watts = tot_m * W_PER_M
    print(f"\nTOTAL     {tot_m:.1f} m flex · {len(rows)} figures · {tot_seg} segments/feeds")
    print(f"POWER     {watts:.0f} W draw → size PSU ≥ {watts*PSU_HEADROOM:.0f} W @ {VOLT} V "
          f"({watts*PSU_HEADROOM/VOLT:.0f} A)")

    with open(OUT/"order.csv","w",newline="") as f:
        w = csv.writer(f); w.writerow(["figure","colour","length_m","segments"])
        w.writerows(rows)
        w.writerow([]); w.writerow(["colour","metres","reels"])
        for color, m in sorted(by_color.items(), key=lambda x:-x[1]):
            w.writerow([color, round(m,1), math.ceil(m/REEL_M)])
    print(f"\nwrote {OUT/'order.csv'}")


if __name__ == "__main__":
    build()
