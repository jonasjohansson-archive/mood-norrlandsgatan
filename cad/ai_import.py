"""Import the figures from the Illustrator file into figures/composition.svg.

The .ai has named layers: FIGURES (Layer 2-9) = the neon; LINES / OUTLINE / PILLARS
= references (NOT neon). We render the figure layers on their own + the PILLARS layer
on its own (for the 2 registration circles), bake the per-path transforms that
pdftocairo emits into absolute coords, and write a clean composition.svg
(polyline paths + 2 <circle>) that svgcheck.py can register to the building pillars.

    cd cad && uv run --with pikepdf,svgpathtools python ai_import.py "/path/192 MOOD Figures.ai"
"""
import sys, re, subprocess
from pathlib import Path
import pikepdf
from svgpathtools import svg2paths

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "/Users/jonas/Desktop/192 MOOD Figures.ai")
HERE = Path(__file__).parent
OUTSVG = HERE / "figures" / "composition.svg"
REFS = {"LINES", "OUTLINE", "PILLARS"}

def render(off_names, tag):
    pdf = pikepdf.open(str(SRC)); ocp = pdf.Root.OCProperties
    ocp.D.OFF = pikepdf.Array([g for g in ocp.OCGs if str(g.Name) in off_names])
    p = f"/tmp/ai_{tag}.pdf"; s = f"/tmp/ai_{tag}.svg"
    pdf.save(p); subprocess.run(["pdftocairo", "-svg", p, s], check=True)
    return s

def names(src):
    pdf = pikepdf.open(str(src)); return [str(g.Name) for g in pdf.Root.OCProperties.OCGs]

def mat(attr):
    m = re.search(r"matrix\(([^)]+)\)", attr.get("transform", "") or "")
    if not m: return (1, 0, 0, 1, 0, 0)
    return tuple(float(x) for x in m.group(1).replace(",", " ").split())

def apply(a, b, c, d, e, f, z):
    return complex(a*z.real + c*z.imag + e, b*z.real + d*z.imag + f)

ALL = set(names(SRC))
fig_svg = render(REFS, "fig")                       # figures only
pil_svg = render(ALL - {"PILLARS"}, "pil")          # pillars only

# pillar centres (apply transform to each circle's local bbox centre)
pil_paths, pil_attrs = svg2paths(pil_svg)
centres = []
for p, at in zip(pil_paths, pil_attrs):
    bb = p.bbox(); z = apply(*mat(at), complex((bb[0]+bb[1])/2, (bb[2]+bb[3])/2))
    centres.append((z.real, z.imag))
centres.sort()
print("pillar centres:", [(round(x), round(y)) for x, y in centres])

# figures: bake transforms, split continuous subpaths, sample to polylines
fig_paths, fig_attrs = svg2paths(fig_svg)
vb = re.search(r'viewBox="([^"]+)"', Path(fig_svg).read_text()).group(1)
poly = []
for p, at in zip(fig_paths, fig_attrs):
    m = mat(at)
    for sub in p.continuous_subpaths():
        L = sub.length()
        if L < 6: continue
        n = max(8, int(L / 1.5))
        pts = [apply(*m, sub.point(i/n)) for i in range(n+1)]
        d = "M " + " L ".join(f"{z.real:.2f} {z.imag:.2f}" for z in pts)
        poly.append(d)

r = 62.85
circles = "".join(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r}"/>' for x, y in centres)
paths = "".join(f'<path d="{d}" fill="none" stroke="black"/>' for d in poly)
OUTSVG.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">{circles}{paths}</svg>')
print(f"wrote {OUTSVG}  ({len(poly)} figure strokes + {len(centres)} pillars)")
