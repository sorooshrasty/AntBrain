"""Draw the current RapidFEM interpretation of slide 5 geometry.

This is a review/communication figure only.  It documents the geometry used
by ``verify_slide5_dipole.py`` before any further tuning.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


OUT = Path("results")
OUT.mkdir(exist_ok=True)

# Geometry currently used in verify_slide5_dipole.py
TOTAL_LENGTH_MM = 165.0
STRIP_WIDTH_MM = 4.0
GAP_MM = 2.0
ARM_LENGTH_MM = (TOTAL_LENGTH_MM - GAP_MM) / 2.0

# Air/domain choices from verify_slide5_dipole.py
C0 = 299_792_458.0
F_REF = 0.8e9
LAMBDA_REF_MM = C0 / F_REF * 1e3
PAD_MM = 0.18 * LAMBDA_REF_MM
DOMAIN_X_MM = TOTAL_LENGTH_MM + 2.0 * PAD_MM
DOMAIN_Y_MM = STRIP_WIDTH_MM + 2.0 * PAD_MM
DOMAIN_Z_MM = 2.0 * PAD_MM


def dim_arrow(ax, xy0, xy1, text, *, text_offset=(0, 0), color="navy", size=10):
    ax.annotate(
        "",
        xy=xy1,
        xytext=xy0,
        arrowprops=dict(arrowstyle="<->", lw=1.4, color=color, shrinkA=0, shrinkB=0),
    )
    tx = (xy0[0] + xy1[0]) / 2.0 + text_offset[0]
    ty = (xy0[1] + xy1[1]) / 2.0 + text_offset[1]
    ax.text(tx, ty, text, color=color, ha="center", va="center", fontsize=size)


def main() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.8), gridspec_kw={"width_ratios": [1.35, 1]})
    ax = axes[0]

    # Top view of the conductive plates.
    y0 = -STRIP_WIDTH_MM / 2.0
    left_x = -GAP_MM / 2.0 - ARM_LENGTH_MM
    right_x = GAP_MM / 2.0

    ax.add_patch(Rectangle((left_x, y0), ARM_LENGTH_MM, STRIP_WIDTH_MM, facecolor="#9a9a9a", edgecolor="black", lw=1.2))
    ax.add_patch(Rectangle((right_x, y0), ARM_LENGTH_MM, STRIP_WIDTH_MM, facecolor="#9a9a9a", edgecolor="black", lw=1.2))
    ax.add_patch(Rectangle((-GAP_MM / 2.0, y0), GAP_MM, STRIP_WIDTH_MM, facecolor="#ffcccc", edgecolor="#c43c39", lw=1.4, hatch="//"))

    ax.plot([left_x, left_x + ARM_LENGTH_MM], [0, 0], color="cyan", lw=1.2)
    ax.plot([right_x, right_x + ARM_LENGTH_MM], [0, 0], color="cyan", lw=1.2)

    # Dimension arrows.
    dim_arrow(ax, (-TOTAL_LENGTH_MM / 2.0, -14), (TOTAL_LENGTH_MM / 2.0, -14), "total length = 165 mm", text_offset=(0, -4))
    dim_arrow(ax, (-GAP_MM / 2.0, 10), (GAP_MM / 2.0, 10), "feed gap = 2 mm", text_offset=(0, 4), color="#c43c39", size=9)
    dim_arrow(ax, (TOTAL_LENGTH_MM / 2.0 + 8, -STRIP_WIDTH_MM / 2.0), (TOTAL_LENGTH_MM / 2.0 + 8, STRIP_WIDTH_MM / 2.0), "width = 4 mm", text_offset=(12, 0))

    ax.text(left_x + ARM_LENGTH_MM / 2.0, 5.5, f"left PEC arm\n{ARM_LENGTH_MM:.1f} mm", ha="center", va="bottom", fontsize=9)
    ax.text(right_x + ARM_LENGTH_MM / 2.0, 5.5, f"right PEC arm\n{ARM_LENGTH_MM:.1f} mm", ha="center", va="bottom", fontsize=9)
    ax.text(0, -6.5, "50 Ω lumped port\nE direction: +x", ha="center", va="top", color="#c43c39", fontsize=9)

    ax.set_title("Top view: conductive dipole model used for slide 5 verification")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-110, 110)
    ax.set_ylim(-28, 24)
    ax.grid(True, alpha=0.25)

    # Modeling choices / side schematic.
    ax2 = axes[1]
    ax2.set_title("Modeling choices")
    ax2.axis("off")

    notes = [
        "Geometry source: slide 5 text/image",
        "Antenna type: simple dipole in free space",
        "Conductor: zero-thickness PEC plates",
        "Total plate length: 165 mm",
        "Plate width: 4 mm",
        "Center feed: 2 mm lumped-port gap",
        "Port reference impedance: 50 Ω",
        "Air boundary: rectangular box + first-order ABC",
        f"Air padding used: {PAD_MM:.1f} mm each side",
        f"Air domain approx: {DOMAIN_X_MM:.1f} × {DOMAIN_Y_MM:.1f} × {DOMAIN_Z_MM:.1f} mm",
        "No finite metal thickness included",
        "No coax/probe feed included",
        "No substrate or tissue included",
    ]

    y = 0.98
    for note in notes:
        ax2.text(0.02, y, f"• {note}", transform=ax2.transAxes, fontsize=10.5, va="top")
        y -= 0.07

    ax2.text(
        0.02,
        0.02,
        "If the slide model includes a probe, finite metal thickness, or a different feed gap,\n"
        "those choices can shift the resonance. Mark the corrections and I’ll rerun.",
        transform=ax2.transAxes,
        fontsize=10,
        color="#444444",
        va="bottom",
    )

    fig.tight_layout()
    fig.savefig(OUT / "slide5_geometry_review.png", dpi=180)
    plt.close(fig)

    print(f"Wrote {OUT / 'slide5_geometry_review.png'}")


if __name__ == "__main__":
    main()
