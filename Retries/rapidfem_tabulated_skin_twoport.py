"""Two-port dipole simulation above skin using tabulated skin properties.

This version reads ``skin_Er.tab`` and ``skin_cond.tab`` and interpolates the
skin relative permittivity and conductivity at each simulated frequency.

Because frequency-dependent material values are static inside a RapidFEM
geometry, the script rebuilds/solves one geometry per frequency.  It also uses
two identical dipoles so both S11 and S21 are physically defined:

* port 1: transmit dipole
* port 2: receive dipole, parallel to port 1
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
DIPOLE_SEPARATION = 35.0e-3

STANDOFF = 8.0e-3
SKIN_T = 3.0e-3
FAT_T = 5.0e-3
MUSCLE_T = 10.0e-3
TISSUE_X = 120.0e-3
TISSUE_Y = 75.0e-3

PAD = 0.06 * LAMBDA0
AIR_MAXH = rf.lambda_maxh(f_max=1.05e9, per_lambda=5)
FREQUENCIES = np.array([0.85e9, 0.95e9, 1.05e9])

OUT = Path("results")
OUT.mkdir(exist_ok=True)


def db20(x: np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.abs(x), 1.0e-15))


def load_tissue_table(path: str) -> np.ndarray:
    table = np.loadtxt(path, skiprows=1)
    # First column is GHz in the provided files; convert to Hz.
    table[:, 0] *= 1.0e9
    return table


skin_er_table = load_tissue_table("skin_Er.tab")
skin_cond_table = load_tissue_table("skin_cond.tab")


def skin_values(freq_hz: float) -> tuple[float, float]:
    er = float(np.interp(freq_hz, skin_er_table[:, 0], skin_er_table[:, 1]))
    cond = float(np.interp(freq_hz, skin_cond_table[:, 0], skin_cond_table[:, 1]))
    return er, cond


def add_dipole(g: rf.Geometry, y_center: float):
    left = g.xy_plate(
        ARM_LENGTH,
        STRIP_WIDTH,
        position=(-GAP / 2.0 - ARM_LENGTH, y_center - STRIP_WIDTH / 2.0, 0.0),
        maxh=5.0e-3,
    )
    right = g.xy_plate(
        ARM_LENGTH,
        STRIP_WIDTH,
        position=(GAP / 2.0, y_center - STRIP_WIDTH / 2.0, 0.0),
        maxh=5.0e-3,
    )
    feed = g.xy_plate(
        GAP,
        STRIP_WIDTH,
        position=(-GAP / 2.0, y_center - STRIP_WIDTH / 2.0, 0.0),
        maxh=1.0e-3,
    )
    return left, right, feed


def build_problem(freq_hz: float) -> tuple[rf.Problem, float, float]:
    er_skin, cond_skin = skin_values(freq_hz)
    g = rf.Geometry(maxh=AIR_MAXH)

    domain_x = max(TOTAL_LENGTH + 2.0 * PAD, TISSUE_X + 2.0 * PAD)
    domain_y = max(DIPOLE_SEPARATION + STRIP_WIDTH + 2.0 * PAD, TISSUE_Y + 2.0 * PAD)
    tissue_bottom = -STANDOFF - SKIN_T - FAT_T - MUSCLE_T
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
        position=(-TISSUE_X / 2.0, -TISSUE_Y / 2.0, -STANDOFF - SKIN_T),
        material=rf.Dielectric(er=er_skin, conductivity=cond_skin, maxh=3.5e-3),
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

    tx_left, tx_right, tx_feed = add_dipole(g, -DIPOLE_SEPARATION / 2.0)
    rx_left, rx_right, rx_feed = add_dipole(g, DIPOLE_SEPARATION / 2.0)

    g.fragment(air, skin, fat, muscle, tx_left, tx_right, tx_feed, rx_left, rx_right, rx_feed)

    rf.LumpedPort(tx_feed, direction=(1, 0, 0), z0=50.0)
    rf.LumpedPort(rx_feed, direction=(1, 0, 0), z0=50.0)
    rf.PEC(tx_left, tx_right, rx_left, rx_right)
    rf.ABC(*air.faces.outer)

    g.mesh(optimize=False)
    return rf.Problem(g), er_skin, cond_skin


print("Running two-port tabulated-skin simulation...")

s_matrices: list[np.ndarray] = []
skin_props: list[tuple[float, float]] = []
best_result = None
best_problem = None
best_idx = 0

for idx, freq in enumerate(FREQUENCIES):
    problem, er_skin, cond_skin = build_problem(float(freq))
    result = problem.sweep([float(freq)])
    s = np.asarray(result.sparams[0])
    s_matrices.append(s)
    skin_props.append((er_skin, cond_skin))
    print(
        f"f={freq/1e9:.3f} GHz, skin er={er_skin:.3f}, sigma={cond_skin:.4f} S/m, "
        f"S11={db20(s[0, 0]):.2f} dB, S21={db20(s[1, 0]):.2f} dB, "
        f"mesh={problem.n_tets} tets/{problem.n_dofs} DOFs"
    )
    if idx == 0 or abs(s[0, 0]) < abs(s_matrices[best_idx][0, 0]):
        best_idx = idx
        best_result = result
        best_problem = problem

s_matrices_arr = np.asarray(s_matrices)
s11 = s_matrices_arr[:, 0, 0]
s21 = s_matrices_arr[:, 1, 0]
s11_db = db20(s11)
s21_db = db20(s21)
best_freq = FREQUENCIES[best_idx]

np.savetxt(
    OUT / "tabulated_skin_twoport_sparams.csv",
    np.column_stack(
        (
            FREQUENCIES,
            [p[0] for p in skin_props],
            [p[1] for p in skin_props],
            s11.real,
            s11.imag,
            s11_db,
            s21.real,
            s21.imag,
            s21_db,
        )
    ),
    delimiter=",",
    header="frequency_hz,skin_er,skin_conductivity_s_per_m,s11_real,s11_imag,s11_db,s21_real,s21_imag,s21_db",
    comments="",
)

fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))

axes[0].plot(FREQUENCIES / 1e9, s11_db, "o-", lw=2, label=r"$S_{11}$")
axes[0].plot(FREQUENCIES / 1e9, s21_db, "s-", lw=2, label=r"$S_{21}$")
axes[0].axhline(-10.0, color="0.65", ls=":", lw=1)
axes[0].set(
    xlabel="Frequency (GHz)",
    ylabel="Magnitude (dB)",
    title="Two-port S-parameters with tabulated skin",
)
axes[0].grid(True, alpha=0.25)
axes[0].legend()

axes[1].plot(FREQUENCIES / 1e9, [p[0] for p in skin_props], "o-", label=r"$\epsilon_r$")
ax2 = axes[1].twinx()
ax2.plot(FREQUENCIES / 1e9, [p[1] for p in skin_props], "s-", color="#c43c39", label=r"$\sigma$")
axes[1].set(xlabel="Frequency (GHz)", ylabel="Skin relative permittivity", title="Interpolated skin table values")
ax2.set_ylabel("Skin conductivity (S/m)")
axes[1].grid(True, alpha=0.25)

lines1, labels1 = axes[1].get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
axes[1].legend(lines1 + lines2, labels1 + labels2, loc="best")

fig.suptitle(
    f"Two parallel dipoles, separation={DIPOLE_SEPARATION*1e3:.0f} mm, "
    f"standoff={STANDOFF*1e3:.0f} mm; best S11 at {best_freq/1e9:.3f} GHz"
)
fig.tight_layout()
fig.savefig(OUT / "tabulated_skin_twoport_result.png", dpi=180)
plt.close(fig)

print(f"Best sampled S11: {s11_db[best_idx]:.2f} dB at {best_freq/1e9:.3f} GHz")
print(f"Corresponding S21: {s21_db[best_idx]:.2f} dB")
print(f"Wrote {OUT / 'tabulated_skin_twoport_result.png'}")
print(f"Wrote {OUT / 'tabulated_skin_twoport_sparams.csv'}")
