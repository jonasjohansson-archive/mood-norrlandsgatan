"""Engineering detail — the snap mechanism + steel-profile connection, as a clear
short cross-section you can inspect and explode. This is the part to ideate the
ENGINEERING on (not the pattern).

    uv run python detail.py     # then open the viewer (light theme)

Shows, bottom to top:
    neon-flex        pushed up into ...
    dovetail groove  in the glossy host panel (undercut lip retains it overhead)
    bracket          bolted from the host top up to ...
    steel profile    the existing ceiling member you connect to
"""
import json
from pathlib import Path
from build123d import (
    BuildSketch, BuildLine, Polyline, make_face, Plane, Axis,
    Box, Cylinder, Pos, Align, fillet, extrude, export_stl, export_step,
)
from channel import HostParams

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

P = HostParams()
LEN = 240.0          # length of the slice (mm)
PANEL_W = 360.0      # width of the host slice
LIP = 1.4            # retaining lip per side at the mouth
LIP_H = 2.5          # height of the lip before the slot opens out


def dovetail_slot():
    """Keyhole/undercut slot: narrow mouth, wider inside, so the squishy neon
    snaps past the lip and can't drop out overhead."""
    mw = P.neon_w / 2 - LIP                 # mouth half-width (the retaining lip)
    iw = P.neon_w / 2 + P.slot_clr          # inner half-width (clearance fit)
    d = P.slot_depth
    pts = [(-mw, 0), (-mw, LIP_H), (-iw, LIP_H), (-iw, d),
           (iw, d), (iw, LIP_H), (mw, LIP_H), (mw, 0)]
    with BuildSketch(Plane.XZ) as sk:
        with BuildLine():
            Polyline(*pts, close=True)
        make_face()
    return extrude(sk.sketch, amount=LEN, both=True)


def build():
    manifest = []

    def emit(name, solid, color, kind, pos=(0, 0, 0)):
        f = f"detail_{name.replace(' ', '_')}.stl"
        export_stl(solid, str(OUT / f))
        manifest.append(dict(name=name, file=f, color=color, kind=kind,
                             group=name, orbit=[0, 0], pos=list(pos), rot=[0, 0, 0]))

    # host slice with the dovetail groove (z in [0, panel_t], slot cut from below)
    host = Pos(0, 0, P.panel_t / 2) * Box(PANEL_W, LEN, P.panel_t)
    host -= dovetail_slot()
    emit("host", host, "#ccd2d8", "host")

    # neon-flex (FN-ESJT-B1023, 10x23, dome down): foot in the groove, body+dome below
    neon = Box(P.neon_w, LEN, P.neon_h)
    neon = fillet(neon.edges().filter_by(Axis.Y).group_by(Axis.Z)[0], radius=P.neon_w / 2 - 0.1)
    neon = Pos(0, 0, P.foot - P.neon_h / 2) * neon   # top of foot flush with groove top
    emit("neon", neon, "#ff7a1a", "neon")

    # bracket: post from host top up to the steel, with a bolt hole
    bx = PANEL_W / 2 - 60
    post = Pos(bx, 0, P.panel_t) * Box(46, 70, 120, align=(Align.CENTER, Align.CENTER, Align.MIN))
    post -= Pos(bx, 0, P.panel_t + 95) * Cylinder(5.5, 80, rotation=(90, 0, 0))
    emit("bracket", post, "#8a929c", "bracket")

    # existing steel profile (RHS box section) running across, above the bracket
    steel = Pos(0, 0, P.panel_t + 140) * Box(PANEL_W + 120, 80, 80,
                                             align=(Align.CENTER, Align.CENTER, Align.MIN))
    hollow = Pos(0, 0, P.panel_t + 146) * Box(PANEL_W + 200, 64, 68,
                                              align=(Align.CENTER, Align.CENTER, Align.MIN))
    steel -= hollow
    emit("steel profile", steel, "#5b6470", "steel")

    export_step(host, str(OUT / "detail_host.step"))
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
    (OUT / "detail.manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"wrote detail ({len(manifest)} parts) + manifest.json to {OUT}")


if __name__ == "__main__":
    build()
