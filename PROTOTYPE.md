# Mounting prototype — first physical test

Goal: prove the **snap-fit** and the **bend** before cutting a full sheet.

## You need
- A **panel offcut** — ideally the real exterior compact phenolic (Trespa/Fundermax);
  any flat board (MDF/acrylic) is fine for a first dry run.
- The **Shaper Origin** + a **dovetail bit** (undercut groove). For a quick first
  pass a straight bit ~0.5 mm under the flex width also friction-fits.
- A few metres of **FN-ESJT-B0612** (6×12 COB) — the actual flex.
- A **steel offcut** + a **bracket / channel-nut** (to test the connection + overhead hold).

## Cut the coupon
File: `out/shaper/coupon.svg` (1:1 mm) →
`http://localhost/mood-norrlandsgatan/out/shaper/coupon.svg`
- Import to the Origin, **On-Line** cut, **Shaper Tape** to register.
- 3 straight grooves = dial in **bit + depth + fit**.
- Arcs **r=120 / 90 / 60 mm** = bend test (90 = assumed min; 60 should kink/fail).
- Start depth ~**6 mm** (grips the foot; dome stays proud). Adjust on the straights.

## Test
1. Push the flex into the straight grooves — find the depth/fit that **holds when held upside-down** (overhead is the real test).
2. Run the flex around the arcs — confirm **90 mm** is clean; note where it kinks.
3. Bolt the coupon to the steel offcut with the bracket; **hang it**, power the flex.
   Check: overhead hold, the glow/line look, and gloss reflection off the panel.

## Report back → bake into the model
Tell me what worked and I'll set it in `channel.py → HostParams`:
- the **bit** (width) and **groove depth** that held,
- the **real min bend radius** (set the Bend Lab slider + `svgcheck.py` to it),
- the **bracket type** + spacing that felt solid.

Then `calibrate.py` / `shaper.py` regenerate against the proven numbers.
