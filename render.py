"""Headless preview of an STL -> PNG (matplotlib, no GL needed).

    uv run python render.py out/panel.stl out/_panel.png
"""
import sys
import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

stl = sys.argv[1] if len(sys.argv) > 1 else "out/panel.stl"
out = sys.argv[2] if len(sys.argv) > 2 else "out/_panel.png"

m = trimesh.load(stl)
tris = m.triangles

light = np.array([0.4, -0.5, 0.8]); light /= np.linalg.norm(light)
shade = 0.35 + 0.65 * np.clip(m.face_normals @ light, 0, 1)
base = np.array([0.62, 0.65, 0.70])
colors = np.clip(shade[:, None] * base, 0, 1)

fig = plt.figure(figsize=(11, 7))
ax = fig.add_subplot(111, projection="3d")
ax.add_collection3d(Poly3DCollection(tris, facecolors=colors,
                                     edgecolors=(0, 0, 0, 0.12), linewidths=0.05))
mn, mx = m.bounds
ax.set_xlim(mn[0], mx[0]); ax.set_ylim(mn[1], mx[1]); ax.set_zlim(mn[2], mx[2])
ax.set_box_aspect(mx - mn)
ax.view_init(elev=55, azim=-90)
ax.set_axis_off()
fig.tight_layout()
fig.savefig(out, dpi=130, bbox_inches="tight")
print("wrote", out)
