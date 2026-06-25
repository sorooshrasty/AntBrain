"""Verify RapidFEM against slide 5 of BR_Report_22062026_Ant.pptx.

Slide 5 describes a free-space simple dipole:

* antenna type: dipole
* dimensions: 165 x 4 mm^2
* resonance: around 0.8 GHz

The slide contains the reference S11 curve as a bitmap image, not numerical
chart data.  This script extracts/digitizes the red curve from the slide image,
runs a matching RapidFEM strip-dipole model, and saves one overlay comparison.
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

# Slide 5 geometry.
TOTAL_LENGTH = 165.0e-3
STRIP_WIDTH = 4.0e-3
GAP = 2.0e-3
ARM_LENGTH = (TOTAL_LENGTH - GAP) / 2.0

# Slide plot range.
F_MIN = 0.5e9
F_MAX = 1.5e9
DB_TOP = 0.0
DB_BOTTOM = -16.0
FREQUENCIES = np.linspace(F_MIN, F_MAX, 21)

# Plot-area pixel bounds of the embedded slide bitmap.
# These are measured from slide5 image12.png.
PLOT_LEFT = 71
PLOT_RIGHT = 670
PLOT_TOP = 49
PLOT_BOTTOM = 430

PAD = 0.18 * (299_792_458.0 / 0.8e9)
MAXH = rf.lambda_maxh(f_max=F_MAX, per_lambda=7)


def db20(x: np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.abs(x), 1.0e-15))


def extract_slide_reference_image() -> None:
    if SLIDE_CURVE_IMAGE.exists():
        return
    with zipfile.ZipFile(PPTX) as z:
        SLIDE_CURVE_IMAGE.write_bytes(z.read(SLIDE_CURVE_IMAGE_IN_PPTX))


def digitize_slide_curve() -> tuple[np.ndarray, np.ndarray]:
    """Return frequency Hz and S11 dB digitized from the red curve bitmap."""
    extract_slide_reference_image()
    img = Image.open(SLIDE_CURVE_IMAGE).convert("RGB")
    arr = np.asarray(img)

    crop = arr[PLOT_TOP:PLOT_BOTTOM + 1, PLOT_LEFT:PLOT_RIGHT + 1, :]

    # Red curve pixels: high red, low green/blue.  This excludes black grid and
    # most anti-aliased gray text.  Restricting to the plot area excludes legend.
    red = (crop[:, :, 0] > 170) & (crop[:, :, 1] < 90) & (crop[:, :, 2] < 90)

    xs = []
    ys = []
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
    print("Building slide-5 dipole geometry...")
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
        maxh=4.0e-3,
    )
    right = g.xy_plate(
        ARM_LENGTH,
        STRIP_WIDTH,
        position=(GAP / 2.0, -STRIP_WIDTH / 2.0, 0.0),
        maxh=4.0e-3,
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
        OUT / "slide5_fem_comparison.csv",
        np.column_stack((fem_f, fem_s11, ref_interp, err)),
        delimiter=",",
        header="frequency_hz,rapidfem_s11_db,slide5_reference_s11_db,error_db",
        comments="",
    )

    fig, ax = plt.subplots(figsize=(9, 5.4))
    ax.plot(ref_f / 1e9, ref_s11, color="#d62728", lw=2.0, label="Slide 5 reference")
    ax.plot(fem_f / 1e9, fem_s11, "o-", color="#1f77b4", lw=2.0, ms=4.5, label="RapidFEM")
    ax.axhline(-10.0, color="0.65", ls=":", lw=1)
    ax.set(
        xlabel="Frequency (GHz)",
        ylabel=r"$|S_{11}|$ (dB)",
        title=(
            "Slide 5 dipole verification: 165 × 4 mm² free-space strip dipole\n"
            f"RMS difference at FEM sweep points: {rms_err:.2f} dB"
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
        xytext=(1.02, -12.7),
        arrowprops={"arrowstyle": "->", "color": "#1f77b4"},
        color="#1f77b4",
        fontsize=9,
    )

    fig.tight_layout()
    fig.savefig(OUT / "slide5_fem_comparison.png", dpi=180)
    plt.close(fig)

    print(f"RapidFEM mesh: {n_tets} tets / {n_dofs} DOFs")
    print(f"Slide reference min: {ref_s11[ref_best_idx]:.2f} dB at {ref_f[ref_best_idx]/1e9:.3f} GHz")
    print(f"RapidFEM min: {fem_s11[fem_best_idx]:.2f} dB at {fem_f[fem_best_idx]/1e9:.3f} GHz")
    print(f"RMS difference at FEM points: {rms_err:.2f} dB")
    print(f"Wrote {OUT / 'slide5_fem_comparison.png'}")
    print(f"Wrote {OUT / 'slide5_fem_comparison.csv'}")


if __name__ == "__main__":
    main()
