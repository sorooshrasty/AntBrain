"""Dipole near a simplified layered human-tissue phantom using RapidFEM.

This example is intentionally a compact engineering model, not a medical
dosimetry model.  It places the same center-fed strip dipole used in
``rapidfem_dipole.py`` above a flat skin/fat/muscle stack and solves
for the antenna input match plus a vertical electric-field slice.

Tissue dielectric properties are approximate 1 GHz values:

* skin:   er=41.4, sigma=0.87 S/m
* fat:    er=5.5,  sigma=0.05 S/m
* muscle: er=54.8, sigma=0.98 S/m

For serious SAR or exposure work, replace these constants with a validated
frequency-dispersive tissue database and use a finer mesh/convergence study.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rapidfem as rf


C0 = 299_792_458.0
F0 = 1.0e9
LAMBDA0 = C0 / F0

# Dipole geometry.
TOTAL_LENGTH = 0.47 * LAMBDA0
GAP = 2.0e-3
ARM_LENGTH = (TOTAL_LENGTH - GAP) / 2.0
STRIP_WIDTH = 4.0e-3

# Tissue phantom geometry.  The dipole is in the z=0 plane; tissue is below it.
# The phantom is intentionally small/coarse so it runs quickly on a laptop.
STANDOFF = 8.0e-3
SKIN_T = 3.0e-3
FAT_T = 5.0e-3
MUSCLE_T = 10.0e-3
TISSUE_X = 100.0e-3
TISSUE_Y = 25.0e-3

# Compact demonstration domain.  Tissue volumes get their own smaller maxh.
PAD = 0.08 * LAMBDA0
AIR_MAXH = rf.lambda_maxh(f_max=1.05e9, per_lambda=5)
FREQUENCIES = np.linspace(0.85e9, 1.05e9, 3)

OUT = Path("results")
OUT.mkdir(exist_ok=True)


def db20(x: np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.abs(x), 1.0e-15))


print("Building the dipole + tissue phantom geometry...")
g = rf.Geometry(maxh=AIR_MAXH)

domain_x = max(TOTAL_LENGTH + 2.0 * PAD, TISSUE_X + 2.0 * PAD)
domain_y = max(STRIP_WIDTH + 2.0 * PAD, TISSUE_Y + 2.0 * PAD)
tissue_bottom = -STANDOFF - SKIN_T - FAT_T - MUSCLE_T
domain_zmin = min(-PAD, tissue_bottom - 0.02)
domain_zmax = PAD

air = g.box(
    domain_x,
    domain_y,
    domain_zmax - domain_zmin,
    position=(-domain_x / 2.0, -domain_y / 2.0, domain_zmin),
    material=rf.Air(),
)

skin = g.box(
    TISSUE_X,
    TISSUE_Y,
    SKIN_T,
    position=(-TISSUE_X / 2.0, -TISSUE_Y / 2.0, -STANDOFF - SKIN_T),
    material=rf.Dielectric(er=41.4, conductivity=0.87, maxh=3.5e-3),
)
fat = g.box(
    TISSUE_X,
    TISSUE_Y,
    FAT_T,
    position=(-TISSUE_X / 2.0, -TISSUE_Y / 2.0, -STANDOFF - SKIN_T - FAT_T),
    material=rf.Dielectric(er=5.5, conductivity=0.05, maxh=7.0e-3),
)
muscle = g.box(
    TISSUE_X,
    TISSUE_Y,
    MUSCLE_T,
    position=(-TISSUE_X / 2.0, -TISSUE_Y / 2.0, tissue_bottom),
    material=rf.Dielectric(er=54.8, conductivity=0.98, maxh=8.0e-3),
)

left = g.xy_plate(
    ARM_LENGTH,
    STRIP_WIDTH,
    position=(-GAP / 2.0 - ARM_LENGTH, -STRIP_WIDTH / 2.0, 0.0),
    maxh=5.0e-3,
)
right = g.xy_plate(
    ARM_LENGTH,
    STRIP_WIDTH,
    position=(GAP / 2.0, -STRIP_WIDTH / 2.0, 0.0),
    maxh=5.0e-3,
)
feed = g.xy_plate(
    GAP,
    STRIP_WIDTH,
    position=(-GAP / 2.0, -STRIP_WIDTH / 2.0, 0.0),
    maxh=1.0e-3,
)

g.fragment(air, skin, fat, muscle, left, right, feed)

rf.LumpedPort(feed, direction=(1, 0, 0), z0=50.0)
rf.PEC(left, right)
rf.ABC(*air.faces.outer)

print("Meshing...")
g.mesh(optimize=False)

print("Solving frequency sweep...")
problem = rf.Problem(g)
result = problem.sweep(FREQUENCIES)

s11 = np.asarray([result.sparams[i, 0, 0] for i in range(len(FREQUENCIES))])
s11_db = db20(s11)
best_idx = int(np.argmin(np.abs(s11)))
best_freq = FREQUENCIES[best_idx]

print(f"Mesh: {problem.n_tets} tetrahedra, {problem.n_dofs} DOFs")
print(f"Best sampled match: S11 = {s11_db[best_idx]:.2f} dB at {best_freq/1e9:.3f} GHz")

np.savetxt(
    OUT / "tissue_dipole_s11.csv",
    np.column_stack((FREQUENCIES, s11.real, s11.imag, s11_db)),
    delimiter=",",
    header="frequency_hz,s11_real,s11_imag,s11_db",
    comments="",
)

# Sample the solved electric field at mesh nodes at the best-match frequency.
efield = problem.field_at_nodes(result, freq_idx=best_idx, port_idx=0)
nodes = np.asarray(problem.native.mesh_nodes)
emag = np.linalg.norm(efield, axis=1)

# Vertical x-z slice through the dipole centerline.
slice_tol = 5.0e-3
mask = np.abs(nodes[:, 1]) <= slice_tol
slice_db = 20.0 * np.log10(np.maximum(emag[mask] / np.max(emag), 1.0e-8))

fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))

axes[0].plot(FREQUENCIES / 1e9, s11_db, "o-", color="#c43c39", lw=2)
axes[0].axvline(best_freq / 1e9, color="0.4", ls="--", lw=1)
axes[0].axhline(-10.0, color="0.65", ls=":", lw=1)
axes[0].set(
    xlabel="Frequency (GHz)",
    ylabel=r"$|S_{11}|$ (dB)",
    title="Input match near layered tissue",
)
axes[0].grid(True, alpha=0.25)

sc = axes[1].scatter(
    nodes[mask, 0] * 1e3,
    nodes[mask, 2] * 1e3,
    c=np.clip(slice_db, -50.0, 0.0),
    s=7,
    cmap="inferno",
    vmin=-50.0,
    vmax=0.0,
    linewidths=0,
)

# Tissue layer overlays.
axes[1].axhspan((-STANDOFF - SKIN_T) * 1e3, -STANDOFF * 1e3, color="#f4a3a3", alpha=0.25, label="skin")
axes[1].axhspan(
    (-STANDOFF - SKIN_T - FAT_T) * 1e3,
    (-STANDOFF - SKIN_T) * 1e3,
    color="#f6d36b",
    alpha=0.25,
    label="fat",
)
axes[1].axhspan(tissue_bottom * 1e3, (-STANDOFF - SKIN_T - FAT_T) * 1e3, color="#c05a5a", alpha=0.18, label="muscle")

axes[1].plot(
    [-TOTAL_LENGTH * 500, -GAP * 500],
    [0, 0],
    color="cyan",
    lw=4,
    solid_capstyle="butt",
)
axes[1].plot(
    [GAP * 500, TOTAL_LENGTH * 500],
    [0, 0],
    color="cyan",
    lw=4,
    solid_capstyle="butt",
)
axes[1].set(
    xlabel="x (mm)",
    ylabel="z (mm)",
    title=f"Vertical |E| slice at {best_freq/1e9:.3f} GHz",
    aspect="equal",
)
axes[1].legend(loc="lower right", fontsize=8)
fig.colorbar(sc, ax=axes[1], label="Relative |E| (dB)")

fig.suptitle(
    f"Strip dipole {STANDOFF*1e3:.0f} mm above skin/fat/muscle phantom: "
    f"mesh={problem.n_tets} tets / {problem.n_dofs} DOFs"
)
fig.tight_layout()
fig.savefig(OUT / "tissue_dipole_result.png", dpi=180)
plt.close(fig)

print(f"Wrote {OUT / 'tissue_dipole_result.png'}")
print(f"Wrote {OUT / 'tissue_dipole_s11.csv'}")
