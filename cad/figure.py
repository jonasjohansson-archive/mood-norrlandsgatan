"""People in Orbit — one ceiling module: a glossy snap-groove HOST panel carrying
neon-flex bodies, bracketed to the existing ceiling STEEL PROFILES.

    cd cad && uv run python figure.py

If `paths.json` exists (next to this file or in out/), the bodies are taken from
it — that's what the web ideation tool (ideate.html) exports. Otherwise the
stylised placeholders below are used. Paths are in mm, centred on the canopy.
"""
import json
from pathlib import Path
from build123d import (
    BuildSketch, RectangleRounded, Box, Align, Pos,
    extrude, export_stl, export_step,
)
from channel import HostParams, path_line, groove, neon, bracket

HERE = Path(__file__).parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

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


def build():
    bodies, s = load_bodies()
    cols = col_centers(s)
    manifest = []

    # --- glossy host: panel + brackets ---
    # NB: the snap-groove is a fab detail (invisible at canopy scale) and the
    # boolean-cut of every body path across the full 9x5 m panel is pathologically
    # slow/unstable in OCC. The real grooved cross-section lives in calibrate.py's
    # coupon (channel.coupon), where you verify the snap fit. The neon paths here
    # double as the groove centrelines (= the router toolpath / DXF) for the shop.
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

    # --- neon bodies (emissive, animated, orbiting nearest column) ---
    for name, kind, pts, color in bodies:
        k, p = scaled(kind, pts, s)
        cx = sum(q[0] for q in p) / len(p)
        cy = sum(q[1] for q in p) / len(p)
        orbit = min(cols, key=lambda c: (c[0] - cx) ** 2 + (c[1] - cy) ** 2) if cols else [0, 0]
        f = f"{name}_neon.stl"
        export_stl(neon(path_line(k, p), P), str(OUT / f))
        manifest.append(dict(name=name, file=f, color=color, kind="neon",
                             group=name, orbit=list(orbit), pos=[0, 0, 0], rot=[0, 0, 0]))

    # --- existing steel profiles (grey context, above the panel) ---
    steel = None
    for by in PROFILE_YS:
        bar = Pos(0, by, P.panel_t + 40) * Box(MW + 400, 80, 80,
                                               align=(Align.CENTER, Align.CENTER, Align.MIN))
        steel = bar if steel is None else steel + bar
    export_stl(steel, str(OUT / "steel.stl"))
    manifest.append(dict(name="steel profiles", file="steel.stl", color="#5b6470",
                         kind="steel", group="steel", orbit=[0, 0], pos=[0, 0, 0], rot=[0, 0, 0]))

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"wrote {len(manifest)} parts ({len(bodies)} bodies) + manifest.json to {OUT}")


if __name__ == "__main__":
    build()
