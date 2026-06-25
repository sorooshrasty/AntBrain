"""Skin-loaded RapidFEM comparison for Meandered_Bowtie_v1.0.dxf.

This is the skin version of ``Air/meandered_bowtie/simulate_meandered_bowtie_air.py``.

Material interpretation:

* gray board rectangle = Rogers RT/duroid 6010LM dielectric substrate
* orange metal = smaller inner PEC loop plus side-metal region
  ``Rogers rectangle - larger gray-region loop``
* body loading = tabulated skin block under the Rogers substrate

The DXF does not explicitly define the solver port.  For the Slide-12
comparison below, the feed is a calibrated vertical CPW-style lumped port.
This is not a generic 50-ohm delta-gap: the parameters were tuned against the
Slide-12 resonance depth near 0.648 GHz.
"""

from __future__ import annotations

from pathlib import Path
import sys
import zipfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import rapidfem as rf


ROOT = Path(__file__).resolve().parents[2]
AIR_BOWTIE = ROOT / "Air" / "meandered_bowtie"
sys.path.insert(0, str(AIR_BOWTIE))

from dxf_utils import Polyline, layer_polylines, mm_points_to_m  # noqa: E402


DXF = ROOT / "dxf" / "Meandered_Bowtie_v1.0.dxf"
PPTX = ROOT / "BR_Report_22062026_Ant.pptx"
OUT = Path(__file__).resolve().parent
OUT.mkdir(exist_ok=True)
ASSET_OUT = ROOT / "results" / "slide12_assets"
ASSET_OUT.mkdir(parents=True, exist_ok=True)

SLIDE_CURVE_IMAGE_IN_PPTX = "ppt/media/image22.png"
SLIDE_CURVE_IMAGE = ASSET_OUT / "slide12_reference_s11.png"

C0 = 299_792_458.0

FREQUENCIES = np.array(
    [
        0.20e9,
        0.25e9,
        0.30e9,
        0.35e9,
        0.40e9,
        0.50e9,
        0.55e9,
        0.60e9,
        0.625e9,
        0.648e9,
        0.65e9,
        0.675e9,
        0.70e9,
        0.75e9,
        0.80e9,
        0.90e9,
        1.00e9,
        1.20e9,
        1.40e9,
        1.60e9,
        1.80e9,
        2.00e9,
    ]
)
F_MAX = float(np.max(FREQUENCIES))

F_MIN_REF = 0.2e9
F_MAX_REF = 2.0e9
DB_TOP = -5.0
DB_BOTTOM = -35.0
PLOT_LEFT = 70
PLOT_RIGHT = 629
PLOT_TOP = 49
PLOT_BOTTOM = 430

# Tuned Slide-12 CPW/discrete-feed approximation.
#
# Geometry: vertical x-z port plane at a fixed y reference plane.  This is much
# closer to the CPW feed in Slide 12 than a horizontal xy sheet in the metal
# plane.  The Z0 and height override are calibration parameters selected to
# reproduce the Slide-12 resonance depth near 0.648 GHz.
PORT_X0_MM = -0.8925
PORT_X1_MM = 0.8925
PORT_Y_MM = 1.4500
PORT_ZREF_OHM = 10.0
PORT_HEIGHT_OVERRIDE = 0.62e-3
PORT_MAXH = 0.50e-3

# First-pass substrate/skin assumptions.
ROGERS_ER = 10.2
ROGERS_TAND = 0.0023
ROGERS_T = 1.27e-3
SKIN_MARGIN_XY = 12.0e-3
SKIN_T = 20.0e-3
AIR_PAD_XY = 25.0e-3
AIR_PAD_TOP = 35.0e-3
AIR_PAD_BOTTOM = 10.0e-3
AIR_MAXH = rf.lambda_maxh(f_max=F_MAX, per_lambda=2)


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


def digitize_slide12_curve() -> tuple[np.ndarray, np.ndarray]:
    extract_slide_reference_image()
    arr = np.asarray(Image.open(SLIDE_CURVE_IMAGE).convert("RGB"))
    crop = arr[PLOT_TOP : PLOT_BOTTOM + 1, PLOT_LEFT : PLOT_RIGHT + 1, :]
    red = (crop[:, :, 0] > 170) & (crop[:, :, 1] < 100) & (crop[:, :, 2] < 100)

    xs: list[int] = []
    ys: list[float] = []
    for x in range(red.shape[1]):
        y_idx = np.flatnonzero(red[:, x])
        if y_idx.size:
            xs.append(x + PLOT_LEFT)
            ys.append(float(np.median(y_idx + PLOT_TOP)))

    xs_arr = np.asarray(xs)
    ys_arr = np.asarray(ys)
    freq_hz = F_MIN_REF + (xs_arr - PLOT_LEFT) / (PLOT_RIGHT - PLOT_LEFT) * (F_MAX_REF - F_MIN_REF)
    s11_db = DB_TOP + (ys_arr - PLOT_TOP) / (PLOT_BOTTOM - PLOT_TOP) * (DB_BOTTOM - DB_TOP)
    order = np.argsort(freq_hz)
    return freq_hz[order], s11_db[order]


def dxf_bbox_m() -> tuple[float, float, float, float]:
    polys = layer_polylines(DXF, "PEC") + layer_polylines(DXF, "ROGERS RT-DUROID 6010LM (LOSSY)")
    xs: list[float] = []
    ys: list[float] = []
    for poly in polys:
        for x, y in poly.points_mm:
            xs.append(x * 1.0e-3)
            ys.append(y * 1.0e-3)
    return min(xs), min(ys), max(xs), max(ys)


def classify_geometry() -> tuple[Polyline, Polyline, Polyline]:
    rogers = layer_polylines(DXF, "ROGERS RT-DUROID 6010LM (LOSSY)")
    if not rogers:
        raise RuntimeError("No Rogers material outline found in DXF.")
    pec_polys = layer_polylines(DXF, "PEC")
    if not pec_polys:
        raise RuntimeError("No PEC polylines found in DXF.")
    main_trace = min(pec_polys, key=lambda p: abs(p.area_mm2))
    gray_region = max(pec_polys, key=lambda p: abs(p.area_mm2))
    return rogers[0], main_trace, gray_region


def build_problem(freq_hz: float) -> tuple[rf.Problem, float, float]:
    er_skin, cond_skin = skin_values(freq_hz)
    xmin, ymin, xmax, ymax = dxf_bbox_m()
    geom_w = xmax - xmin
    geom_h = ymax - ymin

    domain_x = geom_w + 2.0 * AIR_PAD_XY
    domain_y = geom_h + 2.0 * AIR_PAD_XY
    domain_z = AIR_PAD_TOP + ROGERS_T + SKIN_T + AIR_PAD_BOTTOM
    z_min = -(ROGERS_T + SKIN_T + AIR_PAD_BOTTOM)

    g = rf.Geometry(maxh=AIR_MAXH)
    air = g.box(
        domain_x,
        domain_y,
        domain_z,
        position=(xmin - AIR_PAD_XY, ymin - AIR_PAD_XY, z_min),
        material=rf.Air(),
    )

    rogers_poly, main_trace, gray_region = classify_geometry()

    substrate = g.box(
        geom_w,
        geom_h,
        ROGERS_T,
        position=(xmin, ymin, -ROGERS_T),
        material=rf.Dielectric(er=ROGERS_ER, tand=ROGERS_TAND, maxh=4.0e-3),
    )

    skin = g.box(
        geom_w + 2.0 * SKIN_MARGIN_XY,
        geom_h + 2.0 * SKIN_MARGIN_XY,
        SKIN_T,
        position=(xmin - SKIN_MARGIN_XY, ymin - SKIN_MARGIN_XY, -(ROGERS_T + SKIN_T)),
        material=rf.Dielectric(er=er_skin, conductivity=cond_skin, maxh=15.0e-3),
    )

    # Metal is on top of the Rogers substrate at z=0.
    main_metal = g.polygon(mm_points_to_m(main_trace.ccw_points_mm()), maxh=2.0e-3)
    side_metal = g.polygon(
        mm_points_to_m(rogers_poly.ccw_points_mm()),
        holes=[mm_points_to_m(gray_region.ccw_points_mm())],
        maxh=2.0e-3,
    )

    feed_port = g.xz_plate(
        (PORT_X1_MM - PORT_X0_MM) * 1.0e-3,
        ROGERS_T,
        position=(PORT_X0_MM * 1.0e-3, PORT_Y_MM * 1.0e-3, -ROGERS_T),
        maxh=PORT_MAXH,
    )

    g.fragment(air, substrate, skin, main_metal, side_metal, feed_port)
    rf.PEC(main_metal, side_metal)
    rf.LumpedPort(
        feed_port,
        direction=(1, 0, 0),
        z0=PORT_ZREF_OHM,
        height=PORT_HEIGHT_OVERRIDE,
    )
    rf.ABC(*air.faces.outer)

    g.mesh(optimize=False)
    return rf.Problem(g), er_skin, cond_skin


def run_rapidfem() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[tuple[int, int]]]:
    s11_values: list[complex] = []
    skin_props: list[tuple[float, float]] = []
    mesh_stats: list[tuple[int, int]] = []

    for idx, freq in enumerate(FREQUENCIES, start=1):
        print(f"[{idx}/{len(FREQUENCIES)}] Building skin-loaded bowtie at {freq/1e9:.3f} GHz...")
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
    ref_f, ref_s11 = digitize_slide12_curve()
    fem_f, s11_complex, skin_er, skin_cond, mesh_stats = run_rapidfem()
    s11_db = db20(s11_complex)

    ref_interp = np.interp(fem_f, ref_f, ref_s11)
    err = s11_db - ref_interp
    rms_err = float(np.sqrt(np.mean(err**2)))
    max_abs_err = float(np.max(np.abs(err)))
    ref_best_idx = int(np.argmin(ref_s11))
    fem_best_idx = int(np.argmin(s11_db))

    csv_out = OUT / "meandered_bowtie_skin_slide12_tunedfeed_comparison.csv"
    png_out = OUT / "meandered_bowtie_skin_slide12_tunedfeed_comparison.png"

    np.savetxt(
        csv_out,
        np.column_stack(
            (
                fem_f,
                skin_er,
                skin_cond,
                s11_complex.real,
                s11_complex.imag,
                s11_db,
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
            "slide12_reference_s11_db,error_db,n_tets,n_dofs"
        ),
        comments="",
    )

    fig, ax = plt.subplots(figsize=(9.0, 5.4))
    ax.plot(ref_f / 1.0e9, ref_s11, color="#d62728", lw=2.0, label="Slide 12 reference")
    ax.plot(
        fem_f / 1.0e9,
        s11_db,
        "o-",
        color="#1f77b4",
        lw=2.0,
        ms=4.2,
        label="RapidFEM + Rogers + skin + tuned Slide-12 CPW feed",
    )
    ax.axhline(-10.0, color="0.65", ls=":", lw=1)
    ax.set(
        xlabel="Frequency (GHz)",
        ylabel=r"$|S_{11}|$ (dB)",
        title=(
            "Slide 12 comparison: Meandered Bowtie on tabulated skin, tuned feed\n"
            f"RMS difference: {rms_err:.2f} dB, max difference: {max_abs_err:.2f} dB"
        ),
        xlim=(0.2, 2.0),
        ylim=(-35, -5),
    )
    ax.grid(True, alpha=0.25)
    ax.legend()
    ax.annotate(
        f"Slide min ≈ {ref_s11[ref_best_idx]:.2f} dB @ {ref_f[ref_best_idx]/1e9:.3f} GHz",
        xy=(ref_f[ref_best_idx] / 1.0e9, ref_s11[ref_best_idx]),
        xytext=(0.82, -32.0),
        arrowprops={"arrowstyle": "->", "color": "#d62728"},
        color="#d62728",
        fontsize=9,
    )
    ax.annotate(
        f"FEM min = {s11_db[fem_best_idx]:.2f} dB @ {fem_f[fem_best_idx]/1e9:.3f} GHz",
        xy=(fem_f[fem_best_idx] / 1.0e9, s11_db[fem_best_idx]),
        xytext=(1.05, -28.0),
        arrowprops={"arrowstyle": "->", "color": "#1f77b4"},
        color="#1f77b4",
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(png_out, dpi=180)
    plt.close(fig)

    print("Skin-loaded Slide 12 comparison complete.")
    print(f"Rogers assumption: er={ROGERS_ER}, tand={ROGERS_TAND}, thickness={ROGERS_T*1e3:.2f} mm")
    print(
        "Tuned feed: vertical xz port, "
        f"x={PORT_X0_MM:.4f}..{PORT_X1_MM:.4f} mm, y={PORT_Y_MM:.4f} mm, "
        f"Zref={PORT_ZREF_OHM:.2f} ohm, height_override={PORT_HEIGHT_OVERRIDE*1e3:.3f} mm, "
        f"port_maxh={PORT_MAXH*1e3:.3f} mm"
    )
    print(f"Slide 12 reference min: {ref_s11[ref_best_idx]:.2f} dB at {ref_f[ref_best_idx]/1e9:.3f} GHz")
    print(f"RapidFEM skin min: {s11_db[fem_best_idx]:.2f} dB at {fem_f[fem_best_idx]/1e9:.3f} GHz")
    print(f"RMS difference at FEM points: {rms_err:.2f} dB")
    print(f"Max absolute difference at FEM points: {max_abs_err:.2f} dB")
    print(f"Wrote {png_out}")
    print(f"Wrote {csv_out}")


if __name__ == "__main__":
    main()
