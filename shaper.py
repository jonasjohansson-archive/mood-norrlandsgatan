"""Shaper Origin export — 1:1 mm SVG cut files for the handheld CNC.

The Origin follows SVG paths. Run each body outline as an ON-LINE cut with a
DOVETAIL bit: the bit is narrow at the surface, wider below, so one pass gives the
undercut groove the neon body snaps into. Dome then sits proud below the face.

    uv run python shaper.py

Writes out/shaper/<body>.svg (one per body, for repositioning with Shaper Tape)
and out/shaper/all.svg (the whole canopy, 1:1). SVG is in real mm.
Stroke colour = the body's neon colour (just for orientation in Shaper Studio);
set the bit, depth and cut-type (On Line) on the tool / in Studio.
"""
from pathlib import Path
from figure import load_bodies, scaled, MW, MH

OUT = Path(__file__).parent / "out" / "shaper"
OUT.mkdir(parents=True, exist_ok=True)

STROKE_MM = 1.0


def catmull(pts, n=18):
    """Sample a Catmull-Rom spline through pts -> dense point list (mm)."""
    if len(pts) < 3:
        return list(pts)
    out = []
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else pts[i + 1]
        for k in range(n + 1):
            t = k / n; t2 = t * t; t3 = t2 * t
            x = 0.5 * (2*p1[0] + (-p0[0]+p2[0])*t + (2*p0[0]-5*p1[0]+4*p2[0]-p3[0])*t2 + (-p0[0]+3*p1[0]-3*p2[0]+p3[0])*t3)
            y = 0.5 * (2*p1[1] + (-p0[1]+p2[1])*t + (2*p0[1]-5*p1[1]+4*p2[1]-p3[1])*t2 + (-p0[1]+3*p1[1]-3*p2[1]+p3[1])*t3)
            out.append((x, y))
    return out


def to_svg(x, y):
    return x + MW / 2, MH / 2 - y          # centre-origin mm -> top-left SVG mm


def body_svg_body(kind, pts, color):
    if kind == "circle":
        cx, cy, r = pts[0]; sx, sy = to_svg(cx, cy)
        return (f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="{r:.2f}" '
                f'fill="none" stroke="{color}" stroke-width="{STROKE_MM}"/>')
    closed = (abs(pts[0][0] - pts[-1][0]) < 1 and abs(pts[0][1] - pts[-1][1]) < 1)
    sp = [to_svg(x, y) for x, y in catmull(pts)]
    d = "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in sp) + (" Z" if closed else "")
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{STROKE_MM}"/>'


def wrap(inner):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{MW:.0f}mm" height="{MH:.0f}mm" '
            f'viewBox="0 0 {MW:.0f} {MH:.0f}">\n{inner}\n</svg>\n')


def build():
    bodies, s = load_bodies()
    all_parts = []
    for name, kind, pts, color in bodies:
        k, p = scaled(kind, pts, s)
        el = body_svg_body(k, p, color)
        all_parts.append(el)
        (OUT / f"{name}.svg").write_text(wrap(el))
    (OUT / "all.svg").write_text(wrap("\n".join(all_parts)))
    print(f"wrote {len(bodies)} body SVGs + all.svg (1:1 mm, {MW:.0f}x{MH:.0f}) to {OUT}")


if __name__ == "__main__":
    build()
