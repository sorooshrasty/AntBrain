"""Single dipole directly attached to a layered skin phantom.

The skin layer uses frequency-dependent values interpolated from:

* ``skin_Er.tab``
* ``skin_cond.tab``

The model has one lumped feed port, so it reports S11 only.  S21 requires a
second port and is intentionally not part of this one-dipole attached model.
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

TOTAL_LENGTH = 0.47 * LAMBDA0
GAP = 2.0e-3
ARM_LENGTH = (TOTAL_LENGTH - GAP) / 2.0
STRIP_WIDTH = 4.0e-3

# "Attached" means the PEC strip lies on the top surface of the skin phantom.
SKIN_TOP_Z = 0.0
SKIN_T = 3.0e-3
FAT_T = 5.0e-3
MUSCLE_T = 10.0e-3
TISSUE_X = 110.0e-3
TISSUE_Y = 35.0e-3

PAD = 0.08 * LAMBDA0
AIR_MAXH = rf.lambda_maxh(f_max=1.05e9, per_lambda=5)
FREQUENCIES = np.array([0.85e9, 0.95e9, 1.05e9])

OUT = Path("results")
OUT.mkdir(exist_ok=True)


def db20(x: np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.abs(x), 1.0e-15))


def load_tissue_table(path: str) -> np.ndarray:
    table = np.loadtxt(path, skiprows=1)
    table[:, 0] *= 1.0e9  # GHz -> Hz
    return table


skin_er_table = load_tissue_table("skin_Er.tab")
skin_cond_table = load_tissue_table("skin_cond.tab")


def skin_values(freq_hz: float) -> tuple[float, float]:
    er = float(np.interp(freq_hz, skin_er_table[:, 0], skin_er_table[:, 1]))
    cond = float(np.interp(freq_hz, skin_cond_table[:, 0], skin_cond_table[:, 1]))
    return er, cond


def build_problem(freq_hz: float) -> tuple[rf.Problem, float, float]:
    er_skin, cond_skin = skin_values(freq_hz)
    g = rf.Geometry(maxh=AIR_MAXH)

    tissue_bottom = SKIN_TOP_Z - SKIN_T - FAT_T - MUSCLE_T
    domain_x = max(TOTAL_LENGTH + 2.0 * PAD, TISSUE_X + 2.0 * PAD)
    domain_y = max(STRIP_WIDTH + 2.0 * PAD, TISSUE_Y + 2.0 * PAD)
    domain_zmin = min(-PAD, tissue_bottom - 0.012)
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
        position=(-TISSUE_X / 2.0, -TISSUE_Y / 2.0, SKIN_TOP_Z - SKIN_T),
        material=rf.Dielectric(er=er_skin, conductivity=cond_skin, maxh=3.5e-3),
    )
    fat = g.box(
        TISSUE_X,
        TISSUE_Y,
        FAT_T,
        position=(-TISSUE_X / 2.0, -TISSUE_Y / 2.0, SKIN_TOP_Z - SKIN_T - FAT_T),
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
        position=(-GAP / 2.0 - ARM_LENGTH, -STRIP_WIDTH / 2.0, SKIN_TOP_Z),
        maxh=5.0e-3,
    )
    right = g.xy_plate(
        ARM_LENGTH,
        STRIP_WIDTH,
        position=(GAP / 2.0, -STRIP_WIDTH / 2.0, SKIN_TOP_Z),
        maxh=5.0e-3,
    )
    feed = g.xy_plate(
        GAP,
        STRIP_WIDTH,
        position=(-GAP / 2.0, -STRIP_WIDTH / 2.0, SKIN_TOP_Z),
        maxh=1.0e-3,
    )

    g.fragment(air, skin, fat, muscle, left, right, feed)

    rf.LumpedPort(feed, direction=(1, 0, 0), z0=50.0)
    rf.PEC(left, right)
    rf.ABC(*air.faces.outer)

    g.mesh(optimize=False)
    return rf.Problem(g), er_skin, cond_skin


print("Running one-port dipole attached to tabulated skin...")

s11_values: list[complex] = []
skin_props: list[tuple[float, float]] = []
best_problem = None
best_result = None
best_idx = 0

for idx, freq in enumerate(FREQUENCIES):
    problem, er_skin, cond_skin = build_problem(float(freq))
    result = problem.sweep([float(freq)])
    s11 = complex(result.sparams[0, 0, 0])
    s11_values.append(s11)
    skin_props.append((er_skin, cond_skin))
    print(
        f"f={freq/1e9:.3f} GHz, skin er={er_skin:.3f}, sigma={cond_skin:.4f} S/m, "
        f"S11={db20(np.array([s11]))[0]:.2f} dB, mesh={problem.n_tets} tets/{problem.n_dofs} DOFs"
    )
    if idx == 0 or abs(s11) < abs(s11_values[best_idx]):
        best_idx = idx
        best_problem = problem
        best_result = result

s11_arr = np.asarray(s11_values)
s11_db = db20(s11_arr)
best_freq = FREQUENCIES[best_idx]

np.savetxt(
    OUT / "attached_skin_dipole_s11.csv",
    np.column_stack(
        (
            FREQUENCIES,
            [p[0] for p in skin_props],
            [p[1] for p in skin_props],
            s11_arr.real,
            s11_arr.imag,
            s11_db,
        )
    ),
    delimiter=",",
    header="frequency_hz,skin_er,skin_conductivity_s_per_m,s11_real,s11_imag,s11_db",
    comments="",
)

assert best_problem is not None and best_result is not None
efield = best_problem.field_at_nodes(best_result, freq_idx=0, port_idx=0)
nodes = np.asarray(best_problem.native.mesh_nodes)
emag = np.linalg.norm(efield, axis=1)

slice_tol = 5.0e-3
mask = np.abs(nodes[:, 1]) <= slice_tol
slice_db = 20.0 * np.log10(np.maximum(emag[mask] / np.max(emag), 1.0e-8))

fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))

axes[0].plot(FREQUENCIES / 1e9, s11_db, "o-", color="#c43c39", lw=2)
axes[0].axhline(-10.0, color="0.65", ls=":", lw=1)
axes[0].axvline(best_freq / 1e9, color="0.4", ls="--", lw=1)
axes[0].set(
    xlabel="Frequency (GHz)",
    ylabel=r"$|S_{11}|$ (dB)",
    title="One-port attached dipole input match",
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

tissue_bottom = SKIN_TOP_Z - SKIN_T - FAT_T - MUSCLE_T
axes[1].axhspan((SKIN_TOP_Z - SKIN_T) * 1e3, SKIN_TOP_Z * 1e3, color="#f4a3a3", alpha=0.25, label="skin")
axes[1].axhspan(
    (SKIN_TOP_Z - SKIN_T - FAT_T) * 1e3,
    (SKIN_TOP_Z - SKIN_T) * 1e3,
    color="#f6d36b",
    alpha=0.25,
    label="fat",
)
axes[1].axhspan(tissue_bottom * 1e3, (SKIN_TOP_Z - SKIN_T - FAT_T) * 1e3, color="#c05a5a", alpha=0.18, label="muscle")
axes[1].plot(
    [-TOTAL_LENGTH * 500, -GAP * 500],
    [SKIN_TOP_Z * 1e3, SKIN_TOP_Z * 1e3],
    color="cyan",
    lw=4,
    solid_capstyle="butt",
)
axes[1].plot(
    [GAP * 500, TOTAL_LENGTH * 500],
    [SKIN_TOP_Z * 1e3, SKIN_TOP_Z * 1e3],
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
    "Single strip dipole attached to tabulated skin: "
    f"best S11={s11_db[best_idx]:.2f} dB at {best_freq/1e9:.3f} GHz"
)
fig.tight_layout()
fig.savefig(OUT / "attached_skin_dipole_result.png", dpi=180)
plt.close(fig)

print(f"Best sampled S11: {s11_db[best_idx]:.2f} dB at {best_freq/1e9:.3f} GHz")
print("S21: not applicable; this model has one port only.")
print(f"Wrote {OUT / 'attached_skin_dipole_result.png'}")
print(f"Wrote {OUT / 'attached_skin_dipole_s11.csv'}")
