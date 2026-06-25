"""Slide 5 verification with very-thin PEC sheet metal and center-feed legs.

This model treats the metal as a very thin PEC sheet, which is the stable
thin-metal limit in this RapidFEM workflow.  It includes two feed legs at the
center and drives the dipole at the center gap.
"""

from pathlib import Path
import zipfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import rapidfem as rf


PPTX = Path("BR_Report_22062026_Ant.pptx")
OUT = Path("results")
ASSET_OUT = OUT / "slide5_assets"
OUT.mkdir(exist_ok=True)
ASSET_OUT.mkdir(exist_ok=True)

SLIDE_CURVE_IMAGE_IN_PPTX = "ppt/media/image12.png"
SLIDE_CURVE_IMAGE = ASSET_OUT / "slide5_reference_s11.png"

TOTAL_LENGTH = 165.0e-3
WIDTH = 4.0e-3
GAP = 2.0e-3
LEG_LENGTH = 35.0e-3
ARM_LENGTH = (TOTAL_LENGTH - GAP) / 2.0

F_MIN = 0.5e9
F_MAX = 1.5e9
DB_TOP = 0.0
DB_BOTTOM = -16.0
FREQUENCIES = np.array([0.50e9, 0.60e9, 0.70e9, 0.75e9, 0.80e9, 0.825e9, 0.85e9, 0.90e9, 1.00e9, 1.20e9, 1.50e9])

PLOT_LEFT = 71
PLOT_RIGHT = 670
PLOT_TOP = 49
PLOT_BOTTOM = 430

PAD = 0.14 * (299_792_458.0 / 0.8e9)
MAXH = rf.lambda_maxh(f_max=F_MAX, per_lambda=5)


def db20(x: np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.abs(x), 1.0e-15))


def extract_slide_reference_image() -> None:
    if SLIDE_CURVE_IMAGE.exists():
        return
    with zipfile.ZipFile(PPTX) as z:
        SLIDE_CURVE_IMAGE.write_bytes(z.read(SLIDE_CURVE_IMAGE_IN_PPTX))


def digitize_slide_curve() -> tuple[np.ndarray, np.ndarray]:
    extract_slide_reference_image()
    arr = np.asarray(Image.open(SLIDE_CURVE_IMAGE).convert("RGB"))
    crop = arr[PLOT_TOP:PLOT_BOTTOM + 1, PLOT_LEFT:PLOT_RIGHT + 1, :]
    red = (crop[:, :, 0] > 170) & (crop[:, :, 1] < 90) & (crop[:, :, 2] < 90)
    xs, ys = [], []
    for x in range(red.shape[1]):
        y_idx = np.flatnonzero(red[:, x])
        if y_idx.size:
            xs.append(x + PLOT_LEFT)
            ys.append(float(np.median(y_idx + PLOT_TOP)))
    xs = np.asarray(xs)
    ys = np.asarray(ys)
    freq_hz = F_MIN + (xs - PLOT_LEFT) / (PLOT_RIGHT - PLOT_LEFT) * (F_MAX - F_MIN)
    s11_db = DB_TOP + (ys - PLOT_TOP) / (PLOT_BOTTOM - PLOT_TOP) * (DB_BOTTOM - DB_TOP)
    order = np.argsort(freq_hz)
    return freq_hz[order], s11_db[order]


def run_rapidfem() -> tuple[np.ndarray, np.ndarray, int, int]:
    print("Building sheet-metal slide-5 dipole with feed legs...")
    g = rf.Geometry(maxh=MAXH)

    domain_x = TOTAL_LENGTH + 2.0 * PAD
    domain_y = WIDTH + LEG_LENGTH + 2.0 * PAD
    domain_z = 2.0 * PAD
    air = g.box(
        domain_x,
        domain_y,
        domain_z,
        position=(-domain_x / 2.0, -LEG_LENGTH - PAD, -domain_z / 2.0),
        material=rf.Air(),
    )

    left_arm = g.xy_plate(
        ARM_LENGTH,
        WIDTH,
        position=(-GAP / 2.0 - ARM_LENGTH, -WIDTH / 2.0, 0.0),
        maxh=4.0e-3,
    )
    right_arm = g.xy_plate(
        ARM_LENGTH,
        WIDTH,
        position=(GAP / 2.0, -WIDTH / 2.0, 0.0),
        maxh=4.0e-3,
    )
    left_leg = g.xy_plate(
        WIDTH,
        LEG_LENGTH,
        position=(-GAP / 2.0 - WIDTH, -LEG_LENGTH, 0.0),
        maxh=3.0e-3,
    )
    right_leg = g.xy_plate(
        WIDTH,
        LEG_LENGTH,
        position=(GAP / 2.0, -LEG_LENGTH, 0.0),
        maxh=3.0e-3,
    )
    feed = g.xy_plate(
        GAP,
        WIDTH,
        position=(-GAP / 2.0, -WIDTH / 2.0, 0.0),
        maxh=1.0e-3,
    )

    g.fragment(air, left_arm, right_arm, left_leg, right_leg, feed)
    rf.LumpedPort(feed, direction=(1, 0, 0), z0=50.0)
    rf.PEC(left_arm, right_arm, left_leg, right_leg)
    rf.ABC(*air.faces.outer)

    print("Meshing...")
    g.mesh(optimize=False)

    print("Solving frequency sweep...")
    problem = rf.Problem(g)
    result = problem.sweep(FREQUENCIES)
    s11 = np.asarray([result.sparams[i, 0, 0] for i in range(len(FREQUENCIES))])
    return FREQUENCIES, db20(s11), problem.n_tets, problem.n_dofs


def main() -> None:
    ref_f, ref_s11 = digitize_slide_curve()
    fem_f, fem_s11, n_tets, n_dofs = run_rapidfem()
    ref_interp = np.interp(fem_f, ref_f, ref_s11)
    err = fem_s11 - ref_interp
    rms_err = float(np.sqrt(np.mean(err**2)))
    ref_best_idx = int(np.argmin(ref_s11))
    fem_best_idx = int(np.argmin(fem_s11))

    np.savetxt(
        OUT / "slide5_sheet_legs_fem_comparison.csv",
        np.column_stack((fem_f, fem_s11, ref_interp, err)),
        delimiter=",",
        header="frequency_hz,rapidfem_sheet_legs_s11_db,slide5_reference_s11_db,error_db",
        comments="",
    )

    fig, ax = plt.subplots(figsize=(9, 5.4))
    ax.plot(ref_f / 1e9, ref_s11, color="#d62728", lw=2.0, label="Slide 5 reference")
    ax.plot(fem_f / 1e9, fem_s11, "o-", color="#1f77b4", lw=2.0, ms=4.5, label="RapidFEM thin sheet + feed legs")
    ax.axhline(-10.0, color="0.65", ls=":", lw=1)
    ax.set(
        xlabel="Frequency (GHz)",
        ylabel=r"$|S_{11}|$ (dB)",
        title=(
            "Slide 5 verification: very-thin PEC sheet dipole with center-feed legs\n"
            f"leg={LEG_LENGTH*1e3:.0f} mm; RMS difference: {rms_err:.2f} dB"
        ),
        xlim=(0.5, 1.5),
        ylim=(-16, 0),
    )
    ax.grid(True, alpha=0.25)
    ax.legend()
    ax.annotate(
        f"Slide min ≈ {ref_s11[ref_best_idx]:.2f} dB @ {ref_f[ref_best_idx]/1e9:.3f} GHz",
        xy=(ref_f[ref_best_idx] / 1e9, ref_s11[ref_best_idx]),
        xytext=(0.53, -14.8),
        arrowprops={"arrowstyle": "->", "color": "#d62728"},
        color="#d62728",
        fontsize=9,
    )
    ax.annotate(
        f"FEM min = {fem_s11[fem_best_idx]:.2f} dB @ {fem_f[fem_best_idx]/1e9:.3f} GHz",
        xy=(fem_f[fem_best_idx] / 1e9, fem_s11[fem_best_idx]),
        xytext=(1.00, -12.9),
        arrowprops={"arrowstyle": "->", "color": "#1f77b4"},
        color="#1f77b4",
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(OUT / "slide5_sheet_legs_fem_comparison.png", dpi=180)
    plt.close(fig)

    print(f"RapidFEM mesh: {n_tets} tets / {n_dofs} DOFs")
    print(f"Feed legs: length={LEG_LENGTH*1e3:.1f} mm, center gap={GAP*1e3:.1f} mm")
    print(f"Slide reference min: {ref_s11[ref_best_idx]:.2f} dB at {ref_f[ref_best_idx]/1e9:.3f} GHz")
    print(f"RapidFEM sheet-leg min: {fem_s11[fem_best_idx]:.2f} dB at {fem_f[fem_best_idx]/1e9:.3f} GHz")
    print(f"RMS difference at FEM points: {rms_err:.2f} dB")
    print(f"Wrote {OUT / 'slide5_sheet_legs_fem_comparison.png'}")
    print(f"Wrote {OUT / 'slide5_sheet_legs_fem_comparison.csv'}")


if __name__ == "__main__":
    main()
