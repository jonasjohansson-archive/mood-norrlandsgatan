"""Shaper Origin test coupon — 1:1 mm grooves to prototype the mounting:
 - 3 straight grooves (dial in bit/depth + snap fit)
 - arcs at r = 120 / 90 / 60 mm (bend test: 90 = assumed min, 60 should fail)

    uv run python shaper_coupon.py   ->  out/shaper/coupon.svg
Cut ON-LINE with the dovetail bit, then push a length of FN-ESJT-B0612 in.
"""
from pathlib import Path

OUT = Path(__file__).parent / "out" / "shaper"; OUT.mkdir(parents=True, exist_ok=True)
W, H = 540, 380
def line(x1, y1, x2, y2):
    return f'<path d="M {x1} {y1} L {x2} {y2}" fill="none" stroke="#ff7a1a" stroke-width="1"/>'
def semi(x, y, r):   # vertical semicircle bulging right, radius r
    return f'<path d="M {x} {y} A {r} {r} 0 0 1 {x} {y+2*r}" fill="none" stroke="#ff7a1a" stroke-width="1"/>'

parts = [line(20, 20 + i*24, 220, 20 + i*24) for i in range(3)]   # straight trials
x = 60
for r in (120, 90, 60):                                          # bend trials
    parts.append(semi(x, 110, r)); x += r + 50

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" '
       f'viewBox="0 0 {W} {H}">\n' + "\n".join(parts) + "\n</svg>\n")
(OUT / "coupon.svg").write_text(svg)
print(f"wrote out/shaper/coupon.svg  ({W}x{H} mm: 3 straight grooves + arcs r=120/90/60 mm)")
