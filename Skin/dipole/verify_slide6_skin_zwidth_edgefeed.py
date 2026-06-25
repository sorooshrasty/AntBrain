"""Slide 6 verification: corrected dipole geometry located on tabulated skin.

This script reuses the corrected Slide-5 geometry that was moved to
``Air/dipole/verify_slide5_zwidth_edgefeed.py`` and places it directly on a
single skin block, matching Slide 6's "Simple Dipole (Located on Body) / Skin"
setup.

Skin material values are interpolated from:

* ``skin_Er.tab``
* ``skin_cond.tab``

RapidFEM conductors are modeled as PEC sheets, consistent with the previous
air-run script.  The one-port model reports S11 only.
"""

from __future__ import annotations

from pathlib import Path
import zipfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import rapidfem as rf


ROOT = Path(__file__).resolve().parents[2]
PPTX = ROOT / "BR_Report_22062026_Ant.pptx"
OUT = ROOT / "results"
ASSET_OUT = OUT / "slide6_assets"
OUT.mkdir(exist_ok=True)
ASSET_OUT.mkdir(exist_ok=True)

SLIDE_CURVE_IMAGE_IN_PPTX = "ppt/media/image14.png"
SLIDE_CURVE_IMAGE = ASSET_OUT / "slide6_reference_s11.png"

C0 = 299_792_458.0

# Corrected dipole/feed geometry from the latest air run.
TOTAL_LENGTH = 165.0e-3
Z_WIDTH = 4.0e-3
CENTER_GAP = 2.0e-3
ARM_LENGTH = (TOTAL_LENGTH - CENTER_GAP) / 2.0
FEED_LENGTH = 35.0e-3

# Single skin/body block.  The antenna sits on the y=0 skin surface; the block
# occupies y>0, so the feed legs extend outward into air for this geometry.
SKIN_X = 175.0e-3
SKIN_DEPTH_Y = 35.0e-3
SKIN_Z = 45.0e-3
SKIN_SURFACE_Y = 0.0

F_MIN = 0.1e9
F_MAX = 1.0e9
DB_TOP = -5.0
DB_BOTTOM = -16.0
FREQUENCIES = np.array(
    [
        0.10e9,
        0.15e9,
        0.20e9,
        0.25e9,
        0.30e9,
        0.325e9,
        0.35e9,
        0.375e9,
        0.40e9,
        0.45e9,
        0.50e9,
        0.60e9,
        0.70e9,
        0.80e9,
        0.90e9,
        1.00e9,
    ]
)

# Pixel coordinates of the plot area inside Slide 6's S11 image.
PLOT_LEFT = 70
PLOT_RIGHT = 670
PLOT_TOP = 49
PLOT_BOTTOM = 430

PAD = 30.0e-3
AIR_MAXH = rf.lambda_maxh(f_max=F_MAX, per_lambda=3)


def db20(x: np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.abs(x), 1.0e-15))


def load_tissue_table(path: Path) -> np.ndarray:
    table = np.loadtxt(path, skiprows=1)
    table[:, 0] *= 1.0e9  # GHz -> Hz
    return table


SKIN_ER_TABLE = load_tissue_table(ROOT / "skin_Er.tab")
SKIN_COND_TABLE = load_tissue_table(ROOT / "skin_cond.tab")


def skin_values(freq_hz: float) -> tuple[float, float]:
    er = float(np.interp(freq_hz, SKIN_ER_TABLE[:, 0], SKIN_ER_TABLE[:, 1]))
    cond = float(np.interp(freq_hz, SKIN_COND_TABLE[:, 0], SKIN_COND_TABLE[:, 1]))
    return er, cond


def extract_slide_reference_image() -> None:
    if SLIDE_CURVE_IMAGE.exists():
        return
    with zipfile.ZipFile(PPTX) as z:
        SLIDE_CURVE_IMAGE.write_bytes(z.read(SLIDE_CURVE_IMAGE_IN_PPTX))


def digitize_slide_curve() -> tuple[np.ndarray, np.ndarray]:
    extract_slide_reference_image()
    arr = np.asarray(Image.open(SLIDE_CURVE_IMAGE).convert("RGB"))
    crop = arr[PLOT_TOP : PLOT_BOTTOM + 1, PLOT_LEFT : PLOT_RIGHT + 1, :]

    # Red S11 curve inside the plot area.  The legend line lies outside the
    # crop, so it is naturally ignored.
    red = (crop[:, :, 0] > 170) & (crop[:, :, 1] < 105) & (crop[:, :, 2] < 105)

    xs: list[int] = []
    ys: list[float] = []
    for x in range(red.shape[1]):
        y_idx = np.flatnonzero(red[:, x])
        if y_idx.size:
            xs.append(x + PLOT_LEFT)
            ys.append(float(np.median(y_idx + PLOT_TOP)))

    xs_arr = np.asarray(xs)
    ys_arr = np.asarray(ys)
    freq_hz = F_MIN + (xs_arr - PLOT_LEFT) / (PLOT_RIGHT - PLOT_LEFT) * (F_MAX - F_MIN)
    s11_db = DB_TOP + (ys_arr - PLOT_TOP) / (PLOT_BOTTOM - PLOT_TOP) * (DB_BOTTOM - DB_TOP)
    order = np.argsort(freq_hz)
    return freq_hz[order], s11_db[order]


def build_problem(freq_hz: float) -> tuple[rf.Problem, float, float]:
    er_skin, cond_skin = skin_values(freq_hz)

    g = rf.Geometry(maxh=AIR_MAXH)

    domain_x = max(TOTAL_LENGTH, SKIN_X) + 2.0 * PAD
    domain_y = FEED_LENGTH + SKIN_DEPTH_Y + 2.0 * PAD
    domain_z = SKIN_Z + 2.0 * PAD
    air = g.box(
        domain_x,
        domain_y,
        domain_z,
        position=(
            -domain_x / 2.0,
            -FEED_LENGTH - PAD,
            -domain_z / 2.0,
        ),
        material=rf.Air(),
    )

    skin = g.box(
        SKIN_X,
        SKIN_DEPTH_Y,
        SKIN_Z,
        position=(-SKIN_X / 2.0, SKIN_SURFACE_Y, -SKIN_Z / 2.0),
        material=rf.Dielectric(er=er_skin, conductivity=cond_skin, maxh=12.0e-3),
    )

    z0 = -Z_WIDTH / 2.0

    # Main dipole arms: x-z PEC plates lying on the skin surface y=0.
    left_arm = g.xz_plate(
        ARM_LENGTH,
        Z_WIDTH,
        position=(-CENTER_GAP / 2.0 - ARM_LENGTH, SKIN_SURFACE_Y, z0),
        maxh=6.0e-3,
    )
    right_arm = g.xz_plate(
        ARM_LENGTH,
        Z_WIDTH,
        position=(CENTER_GAP / 2.0, SKIN_SURFACE_Y, z0),
        maxh=6.0e-3,
    )

    # Corrected parallel feed sheets from the last geometry.
    left_feed = g.yz_plate(
        FEED_LENGTH,
        Z_WIDTH,
        position=(-CENTER_GAP / 2.0, -FEED_LENGTH, z0),
        maxh=2.0e-3,
    )
    right_feed = g.yz_plate(
        FEED_LENGTH,
        Z_WIDTH,
        position=(CENTER_GAP / 2.0, -FEED_LENGTH, z0),
        maxh=2.0e-3,
    )

    # 50-ohm lumped port at the feed-leg start/end point: x=0, y=-35 mm.
    feed_port = g.xz_plate(
        CENTER_GAP,
        Z_WIDTH,
        position=(-CENTER_GAP / 2.0, -FEED_LENGTH, z0),
        maxh=1.0e-3,
    )

    g.fragment(air, skin, left_arm, right_arm, left_feed, right_feed, feed_port)
    rf.LumpedPort(feed_port, direction=(1, 0, 0), z0=50.0)
    rf.PEC(left_arm, right_arm, left_feed, right_feed)
    rf.ABC(*air.faces.outer)

    g.mesh(optimize=False)
    return rf.Problem(g), er_skin, cond_skin


def run_rapidfem() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[tuple[int, int]]]:
    s11_values: list[complex] = []
    skin_props: list[tuple[float, float]] = []
    mesh_stats: list[tuple[int, int]] = []

    for idx, freq in enumerate(FREQUENCIES, start=1):
        print(f"[{idx}/{len(FREQUENCIES)}] Building skin model at {freq/1e9:.3f} GHz...")
        problem, er_skin, cond_skin = build_problem(float(freq))
        print(f"    skin er={er_skin:.3f}, sigma={cond_skin:.4f} S/m")
        result = problem.sweep([float(freq)])
        s11 = complex(result.sparams[0, 0, 0])
        s11_values.append(s11)
        skin_props.append((er_skin, cond_skin))
        mesh_stats.append((problem.n_tets, problem.n_dofs))
        print(
            f"    S11={db20(np.asarray([s11]))[0]:.2f} dB, "
            f"mesh={problem.n_tets} tets/{problem.n_dofs} DOFs"
        )

    s11_arr = np.asarray(s11_values)
    skin_arr = np.asarray(skin_props)
    return FREQUENCIES, s11_arr, skin_arr[:, 0], skin_arr[:, 1], mesh_stats


def main() -> None:
    ref_f, ref_s11 = digitize_slide_curve()
    fem_f, fem_s11_complex, skin_er, skin_cond, mesh_stats = run_rapidfem()
    fem_s11 = db20(fem_s11_complex)

    ref_interp = np.interp(fem_f, ref_f, ref_s11)
    err = fem_s11 - ref_interp
    rms_err = float(np.sqrt(np.mean(err**2)))
    max_abs_err = float(np.max(np.abs(err)))
    ref_best_idx = int(np.argmin(ref_s11))
    fem_best_idx = int(np.argmin(fem_s11))

    csv_out = OUT / "slide6_skin_zwidth_edgefeed_comparison.csv"
    png_out = OUT / "slide6_skin_zwidth_edgefeed_comparison.png"

    np.savetxt(
        csv_out,
        np.column_stack(
            (
                fem_f,
                skin_er,
                skin_cond,
                fem_s11_complex.real,
                fem_s11_complex.imag,
                fem_s11,
                ref_interp,
                err,
                [m[0] for m in mesh_stats],
                [m[1] for m in mesh_stats],
            )
        ),
        delimiter=",",
        header=(
            "frequency_hz,skin_er,skin_conductivity_s_per_m,"
            "s11_real,s11_imag,rapidfem_skin_s11_db,"
            "slide6_reference_s11_db,error_db,n_tets,n_dofs"
        ),
        comments="",
    )

    fig, ax = plt.subplots(figsize=(9, 5.4))
    ax.plot(ref_f / 1e9, ref_s11, color="#d62728", lw=2.0, label="Slide 6 reference")
    ax.plot(
        fem_f / 1e9,
        fem_s11,
        "o-",
        color="#1f77b4",
        lw=2.0,
        ms=4.5,
        label="RapidFEM + tabulated skin",
    )
    ax.axhline(-10.0, color="0.65", ls=":", lw=1)
    ax.set(
        xlabel="Frequency (GHz)",
        ylabel=r"$|S_{11}|$ (dB)",
        title=(
            "Slide 6 verification: corrected dipole located on tabulated skin\n"
            f"RMS difference: {rms_err:.2f} dB, max difference: {max_abs_err:.2f} dB"
        ),
        xlim=(0.1, 1.0),
        ylim=(-16, -5),
    )
    ax.grid(True, alpha=0.25)
    ax.legend()
    ax.annotate(
        f"Slide min ≈ {ref_s11[ref_best_idx]:.2f} dB @ {ref_f[ref_best_idx]/1e9:.3f} GHz",
        xy=(ref_f[ref_best_idx] / 1e9, ref_s11[ref_best_idx]),
        xytext=(0.13, -15.4),
        arrowprops={"arrowstyle": "->", "color": "#d62728"},
        color="#d62728",
        fontsize=9,
    )
    ax.annotate(
        f"FEM min = {fem_s11[fem_best_idx]:.2f} dB @ {fem_f[fem_best_idx]/1e9:.3f} GHz",
        xy=(fem_f[fem_best_idx] / 1e9, fem_s11[fem_best_idx]),
        xytext=(0.47, -14.7),
        arrowprops={"arrowstyle": "->", "color": "#1f77b4"},
        color="#1f77b4",
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(png_out, dpi=180)
    plt.close(fig)

    print("Slide 6 skin comparison complete.")
    print(f"Geometry source: Air/dipole/verify_slide5_zwidth_edgefeed.py")
    print(f"Skin block: {SKIN_X*1e3:.1f} x {SKIN_DEPTH_Y*1e3:.1f} x {SKIN_Z*1e3:.1f} mm")
    print(f"Slide reference min: {ref_s11[ref_best_idx]:.2f} dB at {ref_f[ref_best_idx]/1e9:.3f} GHz")
    print(f"RapidFEM min: {fem_s11[fem_best_idx]:.2f} dB at {fem_f[fem_best_idx]/1e9:.3f} GHz")
    print(f"RMS difference at FEM points: {rms_err:.2f} dB")
    print(f"Max absolute difference at FEM points: {max_abs_err:.2f} dB")
    print("S21: not applicable; this is a one-port Slide 6 model.")
    print(f"Wrote {png_out}")
    print(f"Wrote {csv_out}")


if __name__ == "__main__":
    main()
