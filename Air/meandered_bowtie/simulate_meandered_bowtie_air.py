"""Air-only RapidFEM task for ``Meandered_Bowtie_v1.0.dxf``.

The DXF contains:

* one substrate outline layer: ``ROGERS RT-DUROID 6010LM (LOSSY)``
* two closed polylines on layer ``PEC``

This first conversion follows the user's request for an air simulation.  Slide
12 makes the material interpretation clearer than the raw DXF layer names:
the Rogers rectangle is the substrate plane, the smaller inner PEC loop is the
main metal/meander/bowtie trace, and the side metal lines are the Rogers
rectangle minus the larger gray-region PEC loop.

The DXF does not contain a named port/feed layer, so the lumped port below is
still provisional, but it is placed at the central CPW throat shown by the red
feed marker in Slide 12.
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

from dxf_utils import Polyline, layer_polylines, mm_points_to_m


ROOT = Path(__file__).resolve().parents[2]
DXF = ROOT / "dxf" / "Meandered_Bowtie_v1.0.dxf"
PPTX = ROOT / "BR_Report_22062026_Ant.pptx"
OUT = Path(__file__).resolve().parent
OUT.mkdir(exist_ok=True)
ASSET_OUT = ROOT / "results" / "slide12_assets"
ASSET_OUT.mkdir(parents=True, exist_ok=True)

SLIDE_CURVE_IMAGE_IN_PPTX = "ppt/media/image22.png"
SLIDE_CURVE_IMAGE = ASSET_OUT / "slide12_reference_s11.png"

C0 = 299_792_458.0

# DXF dimensions appear to be millimetres.
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
AIR_PAD = 0.16 * (C0 / F_MAX)
MAXH = rf.lambda_maxh(f_max=F_MAX, per_lambda=5)

F_MIN_REF = 0.2e9
F_MAX_REF = 2.0e9
DB_TOP = -5.0
DB_BOTTOM = -35.0

# Pixel coordinates of the Slide-12 S11 plot area in image22.png.
PLOT_LEFT = 70
PLOT_RIGHT = 629
PLOT_TOP = 49
PLOT_BOTTOM = 430

# Provisional 50-ohm feed port in DXF millimetre coordinates.
# This spans the central CPW throat/cutout near the red feed marker in Slide 12.
PORT_X0_MM = -0.8925
PORT_X1_MM = 0.8925
PORT_Y0_MM = 0.8575
PORT_Y1_MM = 1.7500


def db20(x: np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.abs(x), 1.0e-15))


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
    """Return Rogers plane, main metal trace, and gray-region boundary."""
    rogers = layer_polylines(DXF, "ROGERS RT-DUROID 6010LM (LOSSY)")
    if not rogers:
        raise RuntimeError("No Rogers material outline found in DXF.")
    pec_polys = layer_polylines(DXF, "PEC")
    if not pec_polys:
        raise RuntimeError("No PEC polylines found in DXF.")
    main_trace = min(pec_polys, key=lambda p: abs(p.area_mm2))
    gray_region = max(pec_polys, key=lambda p: abs(p.area_mm2))
    return rogers[0], main_trace, gray_region


def build_problem() -> rf.Problem:
    print(f"Reading DXF: {DXF}")
    xmin, ymin, xmax, ymax = dxf_bbox_m()
    geom_w = xmax - xmin
    geom_h = ymax - ymin

    g = rf.Geometry(maxh=MAXH)
    air = g.box(
        geom_w + 2.0 * AIR_PAD,
        geom_h + 2.0 * AIR_PAD,
        2.0 * AIR_PAD,
        position=(xmin - AIR_PAD, ymin - AIR_PAD, -AIR_PAD),
        material=rf.Air(),
    )

    rogers_poly, main_trace, gray_region = classify_geometry()
    print(
        "Metal definition: smaller inner PEC loop is main trace; "
        "side metal lines are Rogers rectangle minus larger gray-region loop."
    )
    print(
        f"Main metal trace: {len(main_trace.points_mm)} vertices, "
        f"bbox_mm={main_trace.bbox_mm}, area={main_trace.area_mm2:.3f} mm^2"
    )
    print(
        f"Side metal region: Rogers bbox_mm={rogers_poly.bbox_mm} "
        f"minus gray-region bbox_mm={gray_region.bbox_mm}"
    )
    pec_faces = [
        g.polygon(mm_points_to_m(main_trace.ccw_points_mm()), maxh=1.2e-3),
        g.polygon(
            mm_points_to_m(rogers_poly.ccw_points_mm()),
            holes=[mm_points_to_m(gray_region.ccw_points_mm())],
            maxh=1.2e-3,
        ),
    ]

    feed_port = g.xy_plate(
        (PORT_X1_MM - PORT_X0_MM) * 1.0e-3,
        (PORT_Y1_MM - PORT_Y0_MM) * 1.0e-3,
        position=(PORT_X0_MM * 1.0e-3, PORT_Y0_MM * 1.0e-3, 0.0),
        maxh=0.25e-3,
    )

    g.fragment(air, *pec_faces, feed_port)
    rf.PEC(*pec_faces)
    rf.LumpedPort(feed_port, direction=(1, 0, 0), z0=50.0)
    rf.ABC(*air.faces.outer)

    print("Meshing...")
    g.mesh(optimize=False)
    return rf.Problem(g)


def main() -> None:
    ref_f, ref_s11 = digitize_slide12_curve()
    problem = build_problem()
    print("Solving frequency sweep...")
    result = problem.sweep(FREQUENCIES)
    s11 = np.asarray([result.sparams[i, 0, 0] for i in range(len(FREQUENCIES))])
    s11_db = db20(s11)
    best_idx = int(np.argmin(s11_db))
    ref_interp = np.interp(FREQUENCIES, ref_f, ref_s11)
    err = s11_db - ref_interp
    rms_err = float(np.sqrt(np.mean(err**2)))
    max_abs_err = float(np.max(np.abs(err)))
    ref_best_idx = int(np.argmin(ref_s11))

    csv_out = OUT / "meandered_bowtie_air_s11.csv"
    png_out = OUT / "meandered_bowtie_air_s11.png"
    cmp_csv_out = OUT / "meandered_bowtie_air_slide12_comparison.csv"
    cmp_png_out = OUT / "meandered_bowtie_air_slide12_comparison.png"

    np.savetxt(
        csv_out,
        np.column_stack((FREQUENCIES, s11.real, s11.imag, s11_db)),
        delimiter=",",
        header="frequency_hz,s11_real,s11_imag,s11_db",
        comments="",
    )
    np.savetxt(
        cmp_csv_out,
        np.column_stack((FREQUENCIES, s11.real, s11.imag, s11_db, ref_interp, err)),
        delimiter=",",
        header="frequency_hz,s11_real,s11_imag,rapidfem_air_s11_db,slide12_reference_s11_db,error_db",
        comments="",
    )

    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    ax.plot(FREQUENCIES / 1.0e9, s11_db, "o-", color="#1f77b4", lw=2.0)
    ax.axhline(-10.0, color="0.65", ls=":", lw=1)
    ax.axvline(FREQUENCIES[best_idx] / 1.0e9, color="0.45", ls="--", lw=1)
    ax.set(
        xlabel="Frequency (GHz)",
        ylabel=r"$|S_{11}|$ (dB)",
        title=(
            "Meandered Bowtie DXF in air "
            f"(provisional port): best {s11_db[best_idx]:.2f} dB "
            f"@ {FREQUENCIES[best_idx]/1e9:.3f} GHz"
        ),
    )
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(png_out, dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9.0, 5.4))
    ax.plot(ref_f / 1.0e9, ref_s11, color="#d62728", lw=2.0, label="Slide 12 reference")
    ax.plot(
        FREQUENCIES / 1.0e9,
        s11_db,
        "o-",
        color="#1f77b4",
        lw=2.0,
        ms=4.2,
        label="RapidFEM air DXF geometry",
    )
    ax.axhline(-10.0, color="0.65", ls=":", lw=1)
    ax.set(
        xlabel="Frequency (GHz)",
        ylabel=r"$|S_{11}|$ (dB)",
        title=(
            "Slide 12 comparison: Meandered Bowtie DXF in air\n"
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
        f"FEM min = {s11_db[best_idx]:.2f} dB @ {FREQUENCIES[best_idx]/1e9:.3f} GHz",
        xy=(FREQUENCIES[best_idx] / 1.0e9, s11_db[best_idx]),
        xytext=(1.05, -28.0),
        arrowprops={"arrowstyle": "->", "color": "#1f77b4"},
        color="#1f77b4",
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(cmp_png_out, dpi=180)
    plt.close(fig)

    print(f"Mesh: {problem.n_tets} tets / {problem.n_dofs} DOFs")
    print(
        "Provisional Slide-12 CPW port: "
        f"x={PORT_X0_MM:.4f}..{PORT_X1_MM:.4f} mm, "
        f"y={PORT_Y0_MM:.4f}..{PORT_Y1_MM:.4f} mm, z=0"
    )
    print(f"Slide 12 reference min: {ref_s11[ref_best_idx]:.2f} dB at {ref_f[ref_best_idx]/1e9:.3f} GHz")
    print(f"Best sampled S11: {s11_db[best_idx]:.2f} dB at {FREQUENCIES[best_idx]/1e9:.3f} GHz")
    print(f"RMS difference at FEM points: {rms_err:.2f} dB")
    print(f"Max absolute difference at FEM points: {max_abs_err:.2f} dB")
    print(f"Wrote {png_out}")
    print(f"Wrote {csv_out}")
    print(f"Wrote {cmp_png_out}")
    print(f"Wrote {cmp_csv_out}")


if __name__ == "__main__":
    main()
