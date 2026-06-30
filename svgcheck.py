"""Bend-radius check + register a figure SVG to the real building pillars.

The composition SVG carries TWO column circles. We register those onto the survey
building's two pillars (a 2-point similarity: scale + rotation + translation), so the
figures land at true scale and orientation in the building frame. Then we low-pass /
simplify and flag bends tighter than the LED-flex minimum. Writes:
  out/check_<name>.svg     overlay (green ok / red too tight)
  out/<name>.paths.json    registered points (mm, building frame)
  out/paths.json           canonical (pipeline reads this)

    uv run --with svgpathtools python svgcheck.py figures/composition.svg [simplify_mm]
"""
import sys, json, math, re
from pathlib import Path
from svgpathtools import svg2paths

MIN_BEND_MM = 90.0
PILLARS = [(286.0, 0.0), (286.0, -4803.0)]   # building pillars in the canopy/model frame (mm)

src = Path(sys.argv[1])
simplify_mm = float(sys.argv[2]) if len(sys.argv) > 2 else 120.0
name = src.stem.replace(" ", "_")
OUT = Path(__file__).parent / "out"; OUT.mkdir(exist_ok=True)

txt = src.read_text()
circles = re.findall(r'<circle[^>]*?cx="([-\d.]+)"\s+cy="([-\d.]+)"', txt)
if len(circles) < 2:
    raise SystemExit("need 2 column circles in the SVG to register to the pillars")
S = sorted([(float(circles[0][0]), float(circles[0][1])), (float(circles[1][0]), float(circles[1][1]))])

def register(S, T):
    """2-point similarity with REFLECTION + SWAPPED pairing — the orientation that makes the
    .ai OUTLINE match the real soffit (the plan is mirrored on the ceiling, viewed from below).
    Verified against the building footprint: this option lands the OUTLINE centre on the soffit."""
    s0, s1 = complex(*S[0]), complex(*S[1])
    t0, t1 = complex(*T[1]), complex(*T[0])              # swapped pairing
    a = (t1 - t0) / (s1.conjugate() - s0.conjugate())    # reflection (conjugate)
    b = t0 - a * s0.conjugate()
    def tf(x, y):
        z = a * complex(x, y).conjugate() + b
        return (z.real, z.imag)
    return tf, abs(a)

tf, scale = register(S, PILLARS)     # scale = mm per svg unit
paths, attribs = svg2paths(str(src))   # attribs carry per-figure stroke colour

def dense(path, step=1.2):
    L = path.length(); n = max(3, int(L/step))
    return [(z.real, z.imag) for z in (path.point(path.ilength(min(L, i/n*L))) for i in range(n+1))]
def resample(pts, N):
    if len(pts) < 2 or N < 2: return list(pts)
    cum=[0.0]
    for i in range(1,len(pts)): cum.append(cum[-1]+math.dist(pts[i],pts[i-1]))
    L=cum[-1] or 1.0; out=[]; j=0
    for i in range(N):
        d=L*i/(N-1)
        while j<len(pts)-2 and cum[j+1]<d: j+=1
        t=(d-cum[j])/((cum[j+1]-cum[j]) or 1)
        out.append((pts[j][0]+(pts[j+1][0]-pts[j][0])*t, pts[j][1]+(pts[j+1][1]-pts[j][1])*t))
    return out
def boxsmooth(pts, w, passes=2):
    if w<2 or len(pts)<3: return list(pts)
    h=w//2
    for _ in range(passes):
        n=len(pts); out=[]
        for i in range(n):
            a=max(0,i-h); b=min(n,i+h+1); c=b-a
            out.append((sum(p[0] for p in pts[a:b])/c, sum(p[1] for p in pts[a:b])/c))
        pts=out
    return pts
def catmull(A, per=16):
    if len(A)<3: return list(A)
    out=[]
    for i in range(len(A)-1):
        p0=A[i-1] if i>0 else A[i]; p1=A[i]; p2=A[i+1]; p3=A[i+2] if i+2<len(A) else A[i+1]
        for k in range(per+1):
            t=k/per; t2=t*t; t3=t2*t
            out.append((0.5*(2*p1[0]+(-p0[0]+p2[0])*t+(2*p0[0]-5*p1[0]+4*p2[0]-p3[0])*t2+(-p0[0]+3*p1[0]-3*p2[0]+p3[0])*t3),
                        0.5*(2*p1[1]+(-p0[1]+p2[1])*t+(2*p0[1]-5*p1[1]+4*p2[1]-p3[1])*t2+(-p0[1]+3*p1[1]-3*p2[1]+p3[1])*t3)))
    return out
def circumR(a,b,c):
    A=abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/2
    if A<1e-9: return math.inf
    return (math.dist(b,c)*math.dist(a,c)*math.dist(a,b))/(4*A)

thr_svg = MIN_BEND_MM/scale; simplify_svg = simplify_mm/scale
W = max(3, round(thr_svg/1.2*1.6))
curves=[]; cols=[]; minR=math.inf
for p, at in zip(paths, attribs):
    d=boxsmooth(dense(p), W); N=max(4, round(p.length()/simplify_svg)); sm=catmull(resample(d,N))
    rs=[math.inf]+[circumR(sm[i-1],sm[i],sm[i+1]) for i in range(1,len(sm)-1)]+[math.inf]
    minR=min(minR, min(rs)); curves.append((sm,rs)); cols.append(at.get("stroke") or PALETTE[len(cols)%len(PALETTE)])

tight=sum(1 for _,rs in curves for r in rs if r<thr_svg); tot=sum(len(rs) for _,rs in curves)
total_m=sum(sum(math.dist(sm[i],sm[i+1]) for i in range(len(sm)-1)) for sm,_ in curves)*scale/1000
print(f"figure: {src.name}  paths: {len(paths)}  registered to pillars  scale {scale:.2f} mm/unit")
print(f"LED run {total_m:.1f} m   tightest bend {minR*scale:.0f} mm (need >= {MIN_BEND_MM:.0f})   too tight {tight}/{tot}")

# overlay in svg units (visual only)
b=[1e9,1e9,-1e9,-1e9]
for p in paths:
    bb=p.bbox(); b=[min(b[0],bb[0]),min(b[1],bb[2]),max(b[2],bb[1]),max(b[3],bb[3])]
seg=lambda sm,rs:"".join(
    f'<line x1="{sm[i][0]:.1f}" y1="{sm[i][1]:.1f}" x2="{sm[i+1][0]:.1f}" y2="{sm[i+1][1]:.1f}" '
    f'stroke="{"#e6194b" if min(rs[i],rs[i+1])<thr_svg else "#1aaf5d"}" stroke-width="{3 if min(rs[i],rs[i+1])<thr_svg else 1.6}"/>'
    for i in range(len(sm)-1))
(OUT/f"check_{name}.svg").write_text(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{b[0]:.0f} {b[1]:.0f} {b[2]-b[0]:.0f} {b[3]-b[1]:.0f}">'
    f'<rect x="{b[0]:.0f}" y="{b[1]:.0f}" width="{b[2]-b[0]:.0f}" height="{b[3]-b[1]:.0f}" fill="#0e1116"/>'
    + "".join(seg(sm,rs) for sm,rs in curves) + "</svg>")

PALETTE=["#ff3ea5","#ffe23d","#00e5ff","#ff7a1a","#ff2bd6","#39ff88","#2b6bff"]
bodies=[{"name":f"{name}_{i}","kind":"spline",
         "points":[[round(v,1) for v in tf(x,y)] for x,y in sm],"color":cols[i]}
        for i,(sm,_) in enumerate(curves)]
(OUT/f"{name}.paths.json").write_text(json.dumps(bodies,indent=1))
(OUT/"paths.json").write_text(json.dumps(bodies,indent=1))
print(f"wrote out/check_{name}.svg, out/{name}.paths.json and out/paths.json (registered to building)")
