# Mood Norrlandsgatan — "People in Orbit"

CAD + browser tooling for the **AMF / Mood Gallerian** entrance light installation
(Norrlandsgatan, Stockholm), replacing Peter Hagdahl's *Liquid Sky*. Glowing
human-like bodies that orbit the entrance columns, made of LED-in-silicone flex
pushed into a **glossy snap-groove host**, bracketed to the **existing ceiling
steel profiles**. Canopy ≈ **9 × 5 m**. Brief: 10-yr life, low maintenance, fire
(PBL — bygglov granted).

## Settled spec (assumptions until supplier confirms)
- **Light:** FN-ESJT-B0612 **6×12 COB**, **white LED in coloured silicone** — colour
  is a stable pigment, no RGB controller (the *Liquid Sky* lesson: minimal electronics).
  Fixed colour per figure; 2-core + white driver. Min bend radius assumed **90 mm**.
- **Host:** glossy panel with a routed **dovetail snap-groove** (undercut grips the
  6 mm foot; 12 mm body + dome hang down, light into the room).
- **Material:** exterior **compact phenolic** (Trespa Meteon / Fundermax), high-gloss
  — outdoor/UV/fire-rated, routable.
- **Cut:** **Shaper Origin** + dovetail bit, on-line along the figure paths.
- **Mount:** brackets to the existing steel profiles; modules with expansion gaps.

## The loop
```
figure .ai ─▶ Bend Lab (edit shape, all-green) ─▶ paths.json
   ─▶ shaper.py (1:1 dovetail-groove SVG)  ─▶ Shaper Origin cut
   ─▶ figure.py (3D canopy preview) · order.py (cut list / BOM)
```

## Layout
```
  index.html    the 3D viewer (served at http://localhost/mood-norrlandsgatan/)
  ai_import.py  import figures from the Illustrator file (per-layer colour) -> composition.svg
  channel.py    core params (HostParams = 6x12 profile), snap-groove, neon, coupon
  detail.py     engineering detail: dovetail snap + bracket + steel profile
  options.py    mounting-option comparison (groove vs alu track vs clips)
  figure.py     full 9x5 m canopy module -> STL/STEP + manifest (reads paths.json)
  svgcheck.py   bend-radius check on a figure SVG -> overlay + paths.json
  shaper.py     1:1 mm Shaper Origin cut SVGs (on-line dovetail grooves)
  order.py      procurement cut list: metres per colour, segments, power
  calibrate.py  neon snap-fit coupons across slot clearances
  render.py     headless STL -> PNG
  index.html    3D viewer (light, static): toggles + explode
  bendlab.html  SHAPE + BEND editor: load/draw, edit anchors, smoothing slider,
                break-at-fingers, live bend check, export SVG + paths.json
  ideate.html   (optional) freehand pattern sketcher
  out/          exports + manifest.json + order.csv  (gitignored)
```

## Use
Served by the local web server (docroot = `~/Documents/GitHub`):
```
  bend lab:  http://localhost/mood-norrlandsgatan/bendlab.html   (edit a figure -> Export)
  3D view:   http://localhost/mood-norrlandsgatan/               (run figure.py first)
  bend map:  http://localhost/mood-norrlandsgatan/out/check_<name>.svg
```
```sh
cd cad
uv run python figure.py         # canopy preview  (or detail.py for the snap detail)
uv run python shaper.py         # 1:1 groove SVGs for the Origin
uv run python order.py          # cut list / bill of materials
uv run python calibrate.py      # snap-fit coupons to tune the push-fit
```

## Parameters (`channel.py` → `HostParams`, mm)
| param | default | meaning |
|---|---|---|
| `neon_w` / `neon_h` | 6 / 12 | FN-ESJT-B0612 foot width / full height |
| `foot` / `slot_depth` | 5 / 5 | foot gripped in the groove / groove depth |
| `slot_clr` | 0.4 | per-side push-fit clearance — **tune with `calibrate.py`** |
| `lip` | 1.0 | undercut retaining lip (dovetail bit) |
| `panel_t` | 12 | glossy host thickness |

## To confirm with the supplier / site
- [ ] FN-ESJT-B0612 **COB availability**, **silicone jacket colours**, IP rating, **real min bend radius**.
- [ ] White LED **CCT** (tunes the filtered colour) + output (colour filter costs brightness).
- [ ] Steel-profile section/spacing on site → bracket type + `PROFILE_YS`.
- [ ] Real figures: edit in Bend Lab to all-green, export `paths.json`.
- [ ] Sweep the dovetail groove along curved paths (today exact only on the straight detail/coupon).
