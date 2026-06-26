"""Core parametric geometry for the Mood ceiling — the SNAP-GROOVE HOST.

You push silicone neon-flex into a glossy host panel; an undercut groove grips it
so it can't drop out overhead. The host hangs off the existing ceiling STEEL
PROFILES via brackets. Same path drives the groove, the neon and the viewer.

Layout (z up = toward ceiling; room is below at -z):
    host panel        z in [0, PANEL_T]
    snap-groove       carved from the underside, depth SLOT_DEPTH
    neon-flex         in the groove, PROUD mm below the panel face
    bracket tabs      on top, bolt to the steel profile above

All dimensions in millimetres. Tune NEON_W / SLOT_CLR with calibrate.py.
"""
from dataclasses import dataclass
from build123d import (
    BuildLine, BuildSketch, Spline, Polyline, CenterArc, Circle, Box, Cylinder,
    Align, Pos, trace, extrude,
)


@dataclass
class HostParams:
    neon_w: float = 16.0      # silicone neon-flex width
    neon_h: float = 14.0      # neon-flex height
    slot_clr: float = 0.4     # per-side push-fit clearance
    slot_depth: float = 12.0  # how deep the groove is cut into the panel
    lip: float = 1.2          # undercut retaining lip per side (dovetail bit)
    proud: float = 2.0        # how far the neon sits below the panel face (glow)
    panel_t: float = 20.0     # glossy host panel thickness

    @property
    def slot_w(self) -> float:
        return self.neon_w + 2 * self.slot_clr


# ---- path helpers -----------------------------------------------------------
# A "path" is (kind, points): the neon centreline in the XY plane (mm).
#   ("spline",   [(x,y), ...])   smooth flowing line (bodies)
#   ("polyline", [(x,y), ...])   straight segments
#   ("circle",   [(cx,cy,r)])    full ring

def path_line(kind, points):
    with BuildLine() as ln:
        if kind == "spline":
            Spline(*[(x, y) for x, y in points])
        elif kind == "polyline":
            Polyline(*[(x, y) for x, y in points])
        elif kind == "circle":
            cx, cy, r = points[0]
            CenterArc((cx, cy), r, 0, 360)
        else:
            raise ValueError(f"unknown path kind: {kind}")
    return ln.line


# ---- solids -----------------------------------------------------------------

def groove(line, p: HostParams):
    """Solid to SUBTRACT from the panel to form the push-fit slot (cut from below)."""
    return extrude(trace(line, line_width=p.slot_w), amount=p.slot_depth)


def neon(line, p: HostParams):
    """The lit silicone tube, seated in the groove, PROUD below the panel face."""
    tube = extrude(trace(line, line_width=p.neon_w), amount=p.neon_h)
    return Pos(0, 0, -p.proud) * tube


def bracket(x, y, p: HostParams, size=60.0, hole_r=5.5, h=40.0):
    """A tab on the panel top that bolts up to a steel profile."""
    tab = Pos(x, y, p.panel_t) * Box(size, size, h,
                                     align=(Align.CENTER, Align.CENTER, Align.MIN))
    bolt = Pos(x, y, p.panel_t) * Cylinder(hole_r, h + 2,
                                           align=(Align.CENTER, Align.CENTER, Align.MIN))
    return tab - bolt


def coupon(p: HostParams, length: float = 120.0):
    """Straight test piece: glossy panel + grooved slot + neon, for snap-fit checks."""
    line = path_line("polyline", [(0, 0), (length, 0)])
    panel = extrude(trace(line, line_width=p.slot_w + 60), amount=p.panel_t)
    panel -= groove(line, p)
    return panel, neon(line, p)
