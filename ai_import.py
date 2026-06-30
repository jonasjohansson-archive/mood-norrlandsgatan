"""Import the figures from the Illustrator file into figures/composition.svg.

The .ai has named layers: each figure layer (Layer 2-9) = one neon figure; LINES /
OUTLINE are references (NOT neon); PILLARS = the 2 ring circles (kept as neon + used
to register to the building). We render EACH figure layer on its own so every figure
gets ONE colour, bake pdftocairo's per-path transforms into absolute coords, and write
a clean composition.svg (coloured polyline paths + 2 coloured pillar circles).

    uv run --with pikepdf,svgpathtools python ai_import.py "/path/192 MOOD Figures.ai"
"""
import sys, re, subprocess
from pathlib import Path
import pikepdf
from svgpathtools import svg2paths

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "/Users/jonas/Desktop/192 MOOD Figures.ai")
HERE = Path(__file__).parent
OUTSVG = HERE / "figures" / "composition.svg"
REFS = {"LINES", "OUTLINE"}          # not neon
RING = "#f2f2f2"                      # pillar rings colour
PALETTE = ["#ff3ea5", "#ffd23d", "#00e5ff", "#ff7a1a", "#a05bff",
           "#39ff88", "#2b6bff", "#ff2bd6", "#7CFF3D", "#ff5252"]

def all_names():
    pdf = pikepdf.open(str(SRC))
    return [str(g.Name) for g in pdf.Root.OCProperties.OCGs]

def render(off_names, tag):
    pdf = pikepdf.open(str(SRC)); ocp = pdf.Root.OCProperties
    ocp.D.OFF = pikepdf.Array([g for g in ocp.OCGs if str(g.Name) in off_names])
    p = f"/tmp/ai_{tag}.pdf"; s = f"/tmp/ai_{tag}.svg"
    pdf.save(p); subprocess.run(["pdftocairo", "-svg", p, s], check=True)
    return s

def mat(attr):
    m = re.search(r"matrix\(([^)]+)\)", attr.get("transform", "") or "")
    return tuple(float(x) for x in m.group(1).replace(",", " ").split()) if m else (1,0,0,1,0,0)

def apply(a, b, c, d, e, f, z):
    return complex(a*z.real + c*z.imag + e, b*z.real + d*z.imag + f)

def strokes(svg, color):
    paths, attrs = svg2paths(svg); out = []
    for p, at in zip(paths, attrs):
        m = mat(at)
        for sub in p.continuous_subpaths():
            L = sub.length()
            if L < 6: continue
            n = max(8, int(L / 1.5))
            pts = [apply(*m, sub.point(i/n)) for i in range(n+1)]
            out.append((color, "M " + " L ".join(f"{z.real:.2f} {z.imag:.2f}" for z in pts)))
    return out

names = all_names()
fig_layers = [n for n in names if n not in REFS and n != "PILLARS"]   # Layer 2-9, one figure each
allset = set(names)

body = []
for i, layer in enumerate(fig_layers):
    svg = render(allset - {layer}, f"L{i}")
    s = strokes(svg, PALETTE[i % len(PALETTE)])
    body += s
    print(f"  {layer}: {len(s)} strokes  {PALETTE[i % len(PALETTE)]}")

# pillars (registration anchors + kept as neon rings)
pil = render(allset - {"PILLARS"}, "pil")
pil_paths, pil_attrs = svg2paths(pil); centres = []
for p, at in zip(pil_paths, pil_attrs):
    bb = p.bbox(); z = apply(*mat(at), complex((bb[0]+bb[1])/2, (bb[2]+bb[3])/2))
    centres.append((z.real, z.imag))
centres.sort()

vb = re.search(r'viewBox="([^"]+)"', Path(pil).read_text()).group(1)
circles = "".join(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="62.85" fill="none" stroke="{RING}"/>' for x, y in centres)
paths = "".join(f'<path d="{d}" fill="none" stroke="{c}"/>' for c, d in body)
OUTSVG.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">{circles}{paths}</svg>')
print(f"wrote {OUTSVG}  ({len(body)} figure strokes in {len(fig_layers)} figures + {len(centres)} pillar rings)")
print("pillar centres:", [(round(x), round(y)) for x, y in centres])
