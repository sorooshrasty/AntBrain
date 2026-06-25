"""Center-fed half-wave strip dipole simulated with RapidFEM.

The model uses a thin PEC strip in free space, a 50-ohm lumped feed across
the center gap, and a first-order absorbing boundary around the air volume.
It writes an S11/field plot and a small CSV table into ``results/``.
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

# A practical half-wave dipole is slightly shorter than lambda/2.
TOTAL_LENGTH = 0.47 * LAMBDA0
GAP = 2.0e-3
ARM_LENGTH = (TOTAL_LENGTH - GAP) / 2.0
STRIP_WIDTH = 4.0e-3

# A compact demonstration domain. Increasing PAD and reducing MAXH improves
# open-region accuracy at the cost of a much larger solve.
PAD = 0.20 * LAMBDA0
MAXH = rf.lambda_maxh(f_max=1.2e9, per_lambda=8)
FREQUENCIES = np.linspace(0.80e9, 1.20e9, 9)

OUT = Path("results")
OUT.mkdir(exist_ok=True)

print("Building the dipole geometry...")
g = rf.Geometry(maxh=MAXH)

x0 = -(TOTAL_LENGTH / 2.0 + PAD)
y0 = -(STRIP_WIDTH / 2.0 + PAD)
z0 = -PAD
air = g.box(
    TOTAL_LENGTH + 2.0 * PAD,
    STRIP_WIDTH + 2.0 * PAD,
    2.0 * PAD,
    position=(x0, y0, z0),
    material=rf.Air(),
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

g.fragment(air, left, right, feed)

rf.LumpedPort(feed, direction=(1, 0, 0), z0=50.0)
rf.PEC(left, right)
rf.ABC(*air.faces.outer)

print("Meshing...")
g.mesh(optimize=False)

print("Solving frequency sweep...")
problem = rf.Problem(g)
result = problem.sweep(FREQUENCIES)

s11 = np.asarray([result.sparams[i, 0, 0] for i in range(len(FREQUENCIES))])
s11_db = 20.0 * np.log10(np.maximum(np.abs(s11), 1.0e-15))
res_idx = int(np.argmin(np.abs(s11)))
res_freq = FREQUENCIES[res_idx]

print(f"Mesh: {problem.n_tets} tetrahedra, {problem.n_dofs} DOFs")
print(f"Best sampled match: S11 = {s11_db[res_idx]:.2f} dB at {res_freq/1e9:.3f} GHz")

np.savetxt(
    OUT / "dipole_s11.csv",
    np.column_stack((FREQUENCIES, s11.real, s11.imag, s11_db)),
    delimiter=",",
    header="frequency_hz,s11_real,s11_imag,s11_db",
    comments="",
)

# Sample the solved electric field at mesh nodes at the best-match frequency.
efield = problem.field_at_nodes(result, freq_idx=res_idx, port_idx=0)
nodes = np.asarray(problem.native.mesh_nodes)
emag = np.linalg.norm(efield, axis=1)

# Plot nodes close to the dipole plane. The color is normalized dB magnitude,
# so the spatial structure is visible independently of the arbitrary phase.
slice_tol = max(5.0e-3, 0.08 * PAD)
mask = np.abs(nodes[:, 2]) <= slice_tol
slice_db = 20.0 * np.log10(np.maximum(emag[mask] / np.max(emag), 1.0e-8))

fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))

axes[0].plot(FREQUENCIES / 1e9, s11_db, "o-", color="#c43c39", lw=2)
axes[0].axvline(res_freq / 1e9, color="0.4", ls="--", lw=1)
axes[0].axhline(-10.0, color="0.65", ls=":", lw=1)
axes[0].set(
    xlabel="Frequency (GHz)",
    ylabel=r"$|S_{11}|$ (dB)",
    title="RapidFEM dipole input match",
)
axes[0].grid(True, alpha=0.25)

sc = axes[1].scatter(
    nodes[mask, 0] * 1e3,
    nodes[mask, 1] * 1e3,
    c=np.clip(slice_db, -50.0, 0.0),
    s=8,
    cmap="inferno",
    vmin=-50.0,
    vmax=0.0,
    linewidths=0,
)
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
    ylabel="y (mm)",
    title=f"Normalized |E| near z=0 at {res_freq/1e9:.3f} GHz",
    aspect="equal",
)
fig.colorbar(sc, ax=axes[1], label="Relative |E| (dB)")

fig.suptitle(
    f"Center-fed strip dipole: L={TOTAL_LENGTH*1e3:.1f} mm, "
    f"mesh={problem.n_tets} tets / {problem.n_dofs} DOFs"
)
fig.tight_layout()
fig.savefig(OUT / "dipole_result.png", dpi=180)
plt.close(fig)

print(f"Wrote {OUT / 'dipole_result.png'}")
print(f"Wrote {OUT / 'dipole_s11.csv'}")
