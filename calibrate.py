"""Slot-fit calibration coupon — print/cut these and find the neon snap-fit you
like before committing the whole canopy. Each segment uses a different per-side
clearance; pick the one where the neon-flex pushes in and stays put overhead.

    uv run python calibrate.py
"""
import json
from pathlib import Path
from dataclasses import replace
from build123d import Pos, export_stl

from channel import HostParams, coupon

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

CLEARANCES = [0.2, 0.3, 0.4, 0.5, 0.6]   # mm per side
PITCH = 60.0                              # spacing between coupons (mm)
LENGTH = 120.0


def build():
    manifest = []
    base = HostParams()
    for i, clr in enumerate(CLEARANCES):
        p = replace(base, slot_clr=clr)
        alu, tube = coupon(p, LENGTH)
        y = i * PITCH
        alu, tube = Pos(0, y, 0) * alu, Pos(0, y, 0) * tube
        af, nf = f"coupon_{clr:.1f}_alu.stl", f"coupon_{clr:.1f}_neon.stl"
        export_stl(alu, str(OUT / af))
        export_stl(tube, str(OUT / nf))
        manifest.append(dict(name=f"coupon {clr:.1f}mm", file=af, color="#9aa0a6",
                             emissive=False, pos=[0, 0, 0], rot=[0, 0, 0]))
        manifest.append(dict(name=f"neon {clr:.1f}mm", file=nf, color="#ff5a36",
                             emissive=True, pos=[0, 0, 0], rot=[0, 0, 0]))
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"wrote {len(CLEARANCES)} coupons ({CLEARANCES}) to {OUT}")


if __name__ == "__main__":
    build()
