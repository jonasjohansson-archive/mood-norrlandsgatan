# Mood Norrlandsgatan — "People in Orbit"

CAD + browser ideation for the **AMF / Mood Gallerian** entrance light installation
(Norrlandsgatan, Stockholm). Replaces Peter Hagdahl's *Liquid Sky*. Concept:
**glowing human-like bodies that orbit the entrance columns**, made of colored
**silicone neon-flex**, pushed into a **glossy snap-groove host** that is bracketed
to the **existing ceiling steel profiles**. Addressable RGB, animated like a school
of carp; a hand-sensor on a column lets visitors make the lights react.

Brief: ceiling-mounted, light-bearing, weather-resistant, **10-year** life, 3 m
clearance, fire (PBL — bygglov granted). Canopy ≈ **9 × 5 m**.

## The system
```
  existing steel profile  ═══════════════════
           │ bracket (bolts to the profile)
  ┌────────┴───────────────────────────────┐
  │  GLOSSY HOST PANEL (dark, high-gloss)   │  reflects the neon
  │     ╲__╱  snap-groove (undercut)        │
  └───────┐(○)┌────────────────────────────┘
          neon-flex pushed in, light down
```
One set of **paths** drives everything: you draw the bodies in the web tool, it
exports `paths.json`, and the CAD turns those exact paths into the grooved host +
neon + brackets for fabrication.

## Layout
```
cad/
  channel.py    # core: snap-groove host, neon, bracket, test coupon (HostParams)
  figure.py     # one 9x5 m module -> STL/STEP + manifest.json (reads paths.json if present)
  calibrate.py  # neon snap-fit coupons across slot clearances
  render.py     # headless STL -> PNG
  ideate.html   # WEB TOOL: draw neon bodies on a glossy ceiling, glow + animate, export paths.json
  index.html    # 3D preview: glossy host + animated neon + steel, toggles/explode/bloom
  out/          # exported .stl/.step + manifest.json  (gitignored)
```
`out/` and `.venv/` are gitignored — the `.py` files are the source of truth.

## Workflow
```sh
cd cad
python3 -m http.server 8000              # then open the two tools:
#   ideate:  http://localhost:8000/cad/ideate.html   (draw -> Export paths.json)
#   move the downloaded paths.json into cad/
uv run python figure.py                  # regenerates host+neon around your paths
#   preview: http://localhost:8000/cad/  (3D, animated)
uv run python calibrate.py               # neon snap-fit coupons to print/cut & tune
```

## Parameters (`cad/channel.py` → `HostParams`, mm)
| param | default | meaning |
|---|---|---|
| `neon_w` / `neon_h` | 16 / 14 | silicone neon-flex cross-section |
| `slot_clr` | 0.4 | per-side push-fit clearance — **tune with `calibrate.py`** |
| `slot_depth` | 12 | groove depth into the panel |
| `lip` | 1.2 | undercut retaining lip (dovetail bit) so it can't drop out |
| `proud` | 2 | how far the neon sits below the panel face |
| `panel_t` | 20 | glossy host thickness |

## Open questions / next
- [ ] **Real bodies** — draw them in `ideate.html`, or import the `.ai` outlines (SVG → `paths.json`).
- [ ] Confirm a real neon-flex product (IP, fire class, addressable) + back its datasheet in `04 Production`.
- [ ] Real **steel-profile** spacing/section from site → set `PROFILE_YS` + bracket type.
- [ ] Undercut groove is a parameter today but modelled as a straight slot — add the true dovetail section.
- [ ] Split the 9×5 m host into transport/install modules; match the faceted soffit planes.
- [ ] Gloss + marbled finish spec for the panel.
