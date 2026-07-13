"""Serviceability plan: cluster power feeds into zones, pick removable access
hatches, and mark pillar cutouts. Writes out/service.json for the viewer.

Idea (from the mounting brief):
- Neon runs continuously; power is injected at feed points (every ~MAXRUN).
- Group the feeds into ZONES so one location serves many — each zone gets a PSU
  and a removable ACCESS HATCH (a screwed, figure-free panel you lift to get above
  the ceiling and manage the wiring for that zone).
- Panels the pillars pass through need a CUTOUT.

    uv run python service.py
"""
import json, math
from pathlib import Path

HERE = Path(__file__).parent; OUT = HERE / "out"
P = json.load(open(OUT / "panels.json"))["panels"]
paths = [b for b in json.load(open(OUT / "paths.json")) if b.get("color") != "#f2f2f2"]
cols = json.load(open(HERE / "ceiling.json"))["columns"]

MAXRUN = 5000.0          # feed spacing at 24 V (mm)
# Service is anchored on the PILLARS: that's where building power comes up and
# where a ladder reaches. Each pillar = one service core (PSU + access hatch);
# feeds route to their nearest pillar. Per-feed current is ~2 A so the fan-out
# cable runs are electrically fine even at several metres.
ZCOL   = ["#ffb020", "#38b6ff", "#39ff88", "#c07bff", "#ff5d5d"]   # per-zone colour

# --- feed points along each continuous run (matches the viewer) ---
feeds = []
for b in paths:
    pts = b["points"]; cum = [0.0]; L = 0.0
    for i in range(1, len(pts)):
        L += math.dist(pts[i], pts[i-1]); cum.append(L)
    nf = max(1, math.ceil(L / MAXRUN))
    for f in range(nf):
        t = (f + 0.5) * L / nf
        i = 1
        while i < len(cum) and cum[i] < t: i += 1
        u = (t - cum[i-1]) / ((cum[i] - cum[i-1]) or 1)
        feeds.append([pts[i-1][0] + u*(pts[i][0]-pts[i-1][0]),
                      pts[i-1][1] + u*(pts[i][1]-pts[i-1][1])])

# --- service cores anchored on the pillars ---
# HATCHES = how many below-ceiling access hatches. If there's climb-up access above the
# soffit, ONE token hatch is enough (wire the rest from above); else one per pillar.
HATCHES = 1
cent = [list(col["c"]) for col in cols][:max(1, HATCHES)]
ZONES = len(cent)
assign = [min(range(ZONES), key=lambda k: (f[0]-cent[k][0])**2 + (f[1]-cent[k][1])**2) for f in feeds]

# --- pillar cutouts: panels each column passes through (computed first so hatches avoid them) ---
cutouts = []
for col in cols:
    cx, cy = col["c"]; r = col["r"]
    for i, (a, b, c, e) in enumerate(P):
        if a - r <= cx <= c + r and b - r <= cy <= e + r:
            cutouts.append([i, round(cx, 1), round(cy, 1), round(r + 20, 1)])   # +20 mm clearance
cutout_panels = {c[0] for c in cutouts}

# --- figure-free panels (hatch candidates) + panel centres ---
def crosses(pn):
    a, b, c, e = pn
    return any(a <= x <= c and b <= y <= e for bd in paths for x, y in bd["points"])
def pc(pn): return ((pn[0]+pn[2])/2, (pn[1]+pn[3])/2)
free = [i for i, pn in enumerate(P) if not crosses(pn) and i not in cutout_panels]

# one hatch per zone: nearest unused figure-free panel to the zone centroid
hatches = {}; used = set()
for k in range(ZONES):
    cand = sorted((i for i in free if i not in used),
                  key=lambda i: (pc(P[i])[0]-cent[k][0])**2 + (pc(P[i])[1]-cent[k][1])**2)
    if cand: hatches[k] = cand[0]; used.add(cand[0])

zones = []
for k in range(ZONES):
    zf = [feeds[i] for i in range(len(feeds)) if assign[i] == k]
    hp = hatches.get(k)
    psu = list(pc(P[hp])) if hp is not None else list(cent[k])   # PSU sits above its access hatch
    zones.append({"id": k, "colour": ZCOL[k % len(ZCOL)], "psu": [round(psu[0],1), round(psu[1],1)],
                  "hatch": hp, "hatch_rect": [round(v,1) for v in P[hp]] if hp is not None else None,
                  "feeds": [[round(x,1), round(y,1)] for x, y in zf], "n_feeds": len(zf)})

out = {"maxrun": MAXRUN, "zones": zones, "hatches": sorted(used),
       "cutouts": cutouts, "colours": ZCOL[:ZONES]}
json.dump(out, open(OUT / "service.json", "w"), indent=1)

print(f"{len(feeds)} feeds -> {ZONES} pillar-anchored zones · hatches (panels): {sorted(used)}")
for z in zones:
    reach = max((math.dist(z["psu"], f) for f in z["feeds"]), default=0) / 1000
    print(f"  zone {z['id']}: {z['n_feeds']} feeds · hatch panel {z['hatch']} @ "
          f"({z['psu'][0]:.0f},{z['psu'][1]:.0f}) · farthest feed {reach:.1f} m")
print(f"pillar cutouts on panels: {sorted({c[0] for c in cutouts})}")
