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
    Align, Axis, Pos, fillet, trace, extrude,
)


@dataclass
class HostParams:
    """Defaults: FN-ESJT-B0612 6 x 12 mm COB, white LED in COLOURED silicone
    (dome-emitting). Chosen over the 10x23 for ~half the bend radius. The host
    grips the 6 mm foot; the 12 mm body + dome hang down, dome facing the room."""
    neon_w: float = 6.0       # FN-ESJT-B0612 width (the gripped foot)
    neon_h: float = 12.0      # full profile height (foot -> dome)
    foot: float = 5.0         # depth of the foot held inside the groove
    slot_clr: float = 0.4     # per-side push-fit clearance
    slot_depth: float = 5.0   # groove depth (== foot)
    lip: float = 1.0          # undercut retaining lip per side (dovetail bit)
    proud: float = 0.0        # foot sits flush; body protrudes below
    panel_t: float = 12.0     # glossy host panel thickness

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

def neon_profile(p: HostParams, length: float, dome_down: bool = True):
    """The FN-ESJT-B1023 profile as a straight bar of `length` (mm), centred on the
    origin, running along Y. Bottom edge filleted = the emitting dome."""
    n = Box(p.neon_w, length, p.neon_h)
    groups = n.edges().filter_by(Axis.Y).group_by(Axis.Z)
    edges = groups[0] if dome_down else groups[-1]
    return fillet(edges, radius=p.neon_w / 2 - 0.1)


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
