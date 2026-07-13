"""One-command rebuild: a (simplified) SVG -> viewer + panels + service + BOM.

    uv run python rebuild.py                       # rebuild from figures/composition.svg
    uv run python rebuild.py ~/Downloads/foo.svg   # adopt a new SVG, then rebuild
    uv run python rebuild.py --optimize            # also run the figure nudge (seam-dodging; changes art)
    uv run python rebuild.py --export              # also emit the per-sheet cut files

Runs, in order:
  svgcheck  -> out/paths.json (registered to the pillars)
  outline_close -> continuous closed runs (merges the per-figure fragments)
  [optimize_layout]  (off by default — seam-dodging is moot with continuous neon)
  panelize_mixed --vertical -> out/panels.json (mounting boards)
  channels / service / bom  -> out/channels.json, out/service.json, BOM.md
  [export_panels]  -> per-sheet SVGs + schedule.csv

The viewer + neon-check read the out/*.json live, so a reload shows the result.
"""
import subprocess, sys, shutil, time
from pathlib import Path

HERE = Path(__file__).parent
COMP = HERE / "figures" / "composition.svg"
args = [a for a in sys.argv[1:]]
DO_OPT = "--optimize" in args
DO_EXPORT = "--export" in args
svg_in = next((a for a in args if not a.startswith("--")), None)

# adopt a new SVG as the master composition (back up the old one)
if svg_in:
    src = Path(svg_in).expanduser()
    if not src.exists(): sys.exit(f"no such SVG: {src}")
    if src.resolve() != COMP.resolve():
        shutil.copy(COMP, COMP.with_suffix(".svg.bak"))
        shutil.copy(src, COMP)
        print(f"adopted {src.name} -> figures/composition.svg (old kept as composition.svg.bak)")

STEPS = [
    ("register",  ["uv","run","--with","svgpathtools","python","svgcheck.py","figures/composition.svg"]),
    ("close runs",["uv","run","python","outline_close.py"]),
]
if DO_OPT: STEPS.append(("nudge figures", ["uv","run","python","optimize_layout.py","--vertical"]))
STEPS += [
    ("panelize",  ["uv","run","python","panelize_mixed.py","--vertical"]),
    ("channels",  ["uv","run","python","channels.py"]),
    ("service",   ["uv","run","python","service.py"]),
    ("BOM",       ["uv","run","python","bom.py"]),
]
if DO_EXPORT: STEPS.append(("cut files", ["uv","run","python","export_panels.py"]))

def tail(txt, n=1):
    lines = [l for l in txt.strip().splitlines() if l.strip()]
    return " · ".join(lines[-n:]) if lines else ""

print(f"\nrebuild — {len(STEPS)} steps\n" + "-"*52)
t0 = time.time()
for i, (name, cmd) in enumerate(STEPS, 1):
    r = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[{i}/{len(STEPS)}] {name}: FAILED\n{r.stdout}\n{r.stderr}")
        sys.exit(f"\nstopped at '{name}'. Fix and re-run.")
    print(f"[{i}/{len(STEPS)}] {name:13s} ok  {tail(r.stdout)}")
print("-"*52)
print(f"done in {time.time()-t0:.0f}s — reload the viewer / neon-check to see it.")
