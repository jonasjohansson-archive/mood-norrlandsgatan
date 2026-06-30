"""People in Orbit — one ceiling module: a glossy snap-groove HOST panel carrying
neon-flex bodies, bracketed to the existing ceiling STEEL PROFILES.

    uv run python figure.py

If `paths.json` exists (next to this file or in out/), the bodies are taken from
it — that's what the web ideation tool (ideate.html) exports. Otherwise the
stylised placeholders below are used. Paths are in mm, centred on the canopy.
"""
import json
from pathlib import Path
from build123d import (
    BuildSketch, RectangleRounded, Rectangle, Circle, Box, Cylinder, Align, Pos, Locations,
    extrude, export_stl, export_step,
)
from channel import HostParams, path_line, groove, neon, bracket

HERE = Path(__file__).parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
CEIL = HERE / "ceiling.json"   # real soffit footprint (from ceiling_import.py)

P = HostParams()

# Real canopy footprint: 9 x 5 m (from the 14 juni deck).
MW, MH = 9000.0, 5000.0
SCALE = 5.0  # blow up the small placeholder coords into the 9x5 m space

# existing steel profiles run in X; brackets land on this grid (mm)
PROFILE_YS = [-1600.0, 0.0, 1600.0]
BRACKET_XS = [-3000.0, -1000.0, 1000.0, 3000.0]

COLS = [(-300.0, 0.0, 42.0), (300.0, 0.0, 42.0)]  # entrance columns (× SCALE)

# name, kind, points, RGB (addressable palette from the Mix render)
PLACEHOLDER = [
    ("body_a", "spline", [(-650, 280), (-480, 200), (-360, 300), (-470, 380), (-560, 300)], "#ff2bd6"),
    ("body_b", "spline", [(-120, -360), (40, -260), (180, -360), (60, -440), (-120, -360)], "#00e5ff"),
    ("body_c", "spline", [(420, 320), (560, 220), (660, 340), (540, 420), (420, 320)], "#39ff88"),
    ("body_d", "spline", [(-560, -120), (-360, -60), (-120, -140), (140, -40), (420, -160)], "#ff7a1a"),
    ("ring_l", "circle", [COLS[0]], "#2b6bff"),
    ("ring_r", "circle", [COLS[1]], "#ffe23d"),
]


def load_bodies():
    for cand in (HERE / "paths.json", OUT / "paths.json"):
        if cand.exists():
            data = json.loads(cand.read_text())
            print(f"using drawn paths from {cand} ({len(data)} bodies)")
            return [(b["name"], b["kind"],
                     [tuple(pt) for pt in b["points"]], b.get("color", "#ff7a1a"))
                    for b in data], 1.0
    print("using placeholder bodies (draw your own in ideate.html)")
    return PLACEHOLDER, SCALE


def scaled(kind, pts, s):
    if s == 1.0:
        return kind, pts
    if kind == "circle":
        cx, cy, r = pts[0]
        return kind, [(cx * s, cy * s, r * s)]
    return kind, [(x * s, y * s) for x, y in pts]


def col_centers(s):
    return [(cx * s, cy * s) for cx, cy, _ in COLS]


def thin(pts, step=80.0):
    """Resample a dense path to ~step-mm spacing so the neon spline/trace is
    OCC-friendly (hundreds of points make trace() fail)."""
    if len(pts) < 3:
        return pts
    import math
    cum = [0.0]
    for i in range(1, len(pts)):
        cum.append(cum[-1] + math.dist(pts[i], pts[i - 1]))
    L = cum[-1] or 1.0
    n = max(3, int(L / step))
    out = []; j = 0
    for i in range(n + 1):
        t = L * i / n
        while j < len(pts) - 2 and cum[j + 1] < t:
            j += 1
        f = (t - cum[j]) / ((cum[j + 1] - cum[j]) or 1)
        out.append((pts[j][0] + (pts[j + 1][0] - pts[j][0]) * f,
                    pts[j][1] + (pts[j + 1][1] - pts[j][1]) * f))
    return out


def build():
    global MW, MH
    bodies, s = load_bodies()
    manifest = []

    # --- glossy host + columns: real soffit footprint if ceiling.json exists ---
    if CEIL.exists():
        d = json.loads(CEIL.read_text()); cs = d["cell_mm"]
        MW, MH = d["w_mm"], d["h_mm"]
        cols = [tuple(c["c"]) for c in d["columns"]]
        print(f"using ceiling footprint: {len(d['cells'])} tiles, {len(cols)} columns, "
              f"{MW/1000:.1f}x{MH/1000:.1f} m")
        with BuildSketch() as sk:
            with Locations(*[(x, y) for x, y in d["cells"]]):
                Rectangle(cs, cs)
        host = extrude(sk.sketch, amount=P.panel_t)
        for col in d["columns"]:
            with BuildSketch(Pos(col["c"][0], col["c"][1], 0)) as h:
                Circle(col["r"])
            host -= extrude(h.sketch, amount=P.panel_t)
    else:
        cols = col_centers(s)
        with BuildSketch() as sk:
            RectangleRounded(MW, MH, 250)
        host = extrude(sk.sketch, amount=P.panel_t)
        for by in PROFILE_YS:
            for bx in BRACKET_XS:
                host += bracket(bx, by, P)
    export_stl(host, str(OUT / "host.stl"))
    export_step(host, str(OUT / "host.step"))
    manifest.append(dict(name="host", file="host.stl", color="#15171c",
                         kind="host", group="host", orbit=[0, 0],
                         pos=[0, 0, 0], rot=[0, 0, 0]))

    # --- neon bodies (emissive, orbiting nearest column) ---
    for name, kind, pts, color in bodies:
        k, p = scaled(kind, pts, s)
        cx = sum(q[0] for q in p) / len(p)
        cy = sum(q[1] for q in p) / len(p)
        orbit = min(cols, key=lambda c: (c[0] - cx) ** 2 + (c[1] - cy) ** 2) if cols else [0, 0]
        f = f"{name}_neon.stl"
        line_pts = thin(p) if k == "spline" else p
        try:
            export_stl(neon(path_line(k, line_pts), P), str(OUT / f))
        except Exception as e:
            print(f"  ! skipped {name}: {type(e).__name__} (path too tight/self-intersecting)")
            continue
        manifest.append(dict(name=name, file=f, color=color, kind="neon",
                             group=name, orbit=list(orbit), pos=[0, 0, 0], rot=[0, 0, 0]))

    # --- columns: visible pillars hanging from the ceiling into the room ---
    if CEIL.exists():
        pil = None
        for col in json.loads(CEIL.read_text())["columns"]:
            c = Pos(col["c"][0], col["c"][1], 0) * Cylinder(
                col["r"], 1800, align=(Align.CENTER, Align.CENTER, Align.MAX))
            pil = c if pil is None else pil + c
        export_stl(pil, str(OUT / "columns.stl"))
        manifest.append(dict(name="columns", file="columns.stl", color="#aab2bb",
                             kind="column", group="columns", orbit=[0, 0], pos=[0, 0, 0], rot=[0, 0, 0]))

    # --- mounting: existing ceiling steel + the brackets that hang the host off it,
    #     laid out across the REAL footprint so the mounting reads on the actual design ---
    STEEL_GAP = 250.0          # host is bracketed up to the ceiling steel in the void
    if CEIL.exists():
        dd = json.loads(CEIL.read_text()); cs2 = dd["cell_mm"]
        xs = [c[0] for c in dd["cells"]]; ys = [c[1] for c in dd["cells"]]
        hx0, hx1, hy0, hy1 = min(xs)-cs2/2, max(xs)+cs2/2, min(ys)-cs2/2, max(ys)+cs2/2
    else:
        hx0, hx1, hy0, hy1 = -MW/2, MW/2, -MH/2, MH/2
    cxm = (hx0 + hx1) / 2
    prof_ys = [hy0 + (hy1 - hy0) * i / 4 for i in range(5)]   # 5 steel runs across the depth
    brk_xs  = [hx0 + (hx1 - hx0) * i / 6 for i in range(7)]   # brackets along each run

    steel = None
    for py in prof_ys:
        bar = Pos(cxm, py, P.panel_t + STEEL_GAP) * Box(hx1 - hx0 + 400, 80, 80,
                                                        align=(Align.CENTER, Align.CENTER, Align.MIN))
        steel = bar if steel is None else steel + bar
    export_stl(steel, str(OUT / "steel.stl"))
    manifest.append(dict(name="steel profiles", file="steel.stl", color="#5b6470",
                         kind="steel", group="steel", orbit=[0, 0], pos=[0, 0, 0], rot=[0, 0, 0]))

    brk = None
    for py in prof_ys:
        for bx in brk_xs:
            post = Pos(bx, py, P.panel_t) * Box(60, 60, STEEL_GAP,
                                                align=(Align.CENTER, Align.CENTER, Align.MIN))
            brk = post if brk is None else brk + post
    export_stl(brk, str(OUT / "brackets.stl"))
    manifest.append(dict(name="brackets (host→steel)", file="brackets.stl", color="#8a929c",
                         kind="bracket", group="brackets", orbit=[0, 0], pos=[0, 0, 0], rot=[0, 0, 0]))

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
    (OUT / "canopy.manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"wrote {len(manifest)} parts ({len(bodies)} bodies) + manifest.json to {OUT}")


if __name__ == "__main__":
    build()
