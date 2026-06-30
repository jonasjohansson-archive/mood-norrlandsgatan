"""Mounting-option comparison — three ways to "slot it into something", side by side.
Toggle / explode them in the viewer to choose how the FN-ESJT-B1023 neon is held.

    uv run python options.py     # then open the viewer

Each row is a 120 mm cross-section, neon dome facing DOWN (into the room):
  A  routed lipped groove in a glossy host  — continuous grip, any CNC curve  (recommended)
  B  aluminium mounting track               — neon presses in; straight/limited-bend
  C  discrete clips on a host plate         — screw-fixed every 200-300 mm
"""
import json
from pathlib import Path
from build123d import (
    BuildSketch, BuildLine, Polyline, make_face, Plane,
    Box, Cylinder, Pos, Align, extrude, export_stl,
)
from channel import HostParams, neon_profile

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

P = HostParams()
LEN = 120.0
LIP = 1.6        # how far the lip pinches the 10 mm body
ROW = 160.0      # Y spacing between options

manifest = []
def emit(name, solid, color, kind, yoff):
    f = f"opt_{name.replace(' ', '_')}.stl"
    export_stl(Pos(0, yoff, 0) * solid, str(OUT / f))
    manifest.append(dict(name=name, file=f, color=color, kind=kind,
                         group=name, orbit=[0, 0], pos=[0, 0, 0], rot=[0, 0, 0]))

def neon(grip_top_z):
    """neon with the top of its body at grip_top_z (dome hangs below)."""
    n = neon_profile(P, LEN)
    return Pos(0, 0, grip_top_z - P.neon_h / 2) * n


# ---- A: routed lipped groove in a glossy host -------------------------------
GA = 14.0  # groove depth (grips the upper body)
def grooveA():
    mw = P.neon_w / 2 - LIP                 # pinch lip at the mouth
    iw = P.neon_w / 2 + P.slot_clr
    pts = [(-mw, 0), (-mw, 2.5), (-iw, 2.5), (-iw, GA),
           (iw, GA), (iw, 2.5), (mw, 2.5), (mw, 0)]
    with BuildSketch(Plane.XZ) as sk:
        with BuildLine():
            Polyline(*pts, close=True)
        make_face()
    return extrude(sk.sketch, amount=LEN, both=True)

hostA = Pos(0, 0, 9) * Box(120, LEN, 18) - grooveA()
emit("A glossy host", hostA, "#cfd5db", "host", 0)
emit("A neon", neon(GA), "#ff7a1a", "neon", 0)

# ---- B: aluminium mounting track --------------------------------------------
GB = 14.0
trackB = Box(16, LEN, 18) - (Pos(0, 0, -1) * Box(P.neon_w + 0.8, LEN, 16)) \
         - (Pos(0, 0, -9) * Box(P.neon_w - 2 * LIP, LEN, 6))   # open mouth + lip
trackB = Pos(0, 0, 9) * trackB
plateB = Pos(0, 0, 19) * Box(120, LEN, 4)
emit("B alu track", trackB + plateB, "#aeb6c0", "bracket", ROW)
emit("B neon", neon(GB), "#ff7a1a", "neon", ROW)

# ---- C: discrete clips on a host plate --------------------------------------
plateC = Pos(0, 0, 13) * Box(120, LEN, 6)
clips = None
for cy in (-35.0, 35.0):
    c = Pos(0, cy, 0) * (Box(18, 9, 30, align=(Align.CENTER, Align.CENTER, Align.MIN))
                         - Pos(0, 0, 0) * Box(P.neon_w + 0.6, 11, 22,
                                              align=(Align.CENTER, Align.CENTER, Align.MIN)))
    clips = c if clips is None else clips + c
emit("C plate", plateC, "#cfd5db", "host", 2 * ROW)
emit("C clips", clips, "#aeb6c0", "bracket", 2 * ROW)
emit("C neon", neon(9.0), "#ff7a1a", "neon", 2 * ROW)

(OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
(OUT / "options.manifest.json").write_text(json.dumps(manifest, indent=1))
print(f"wrote {len(manifest)} parts (A groove / B track / C clips) + manifest.json to {OUT}")
