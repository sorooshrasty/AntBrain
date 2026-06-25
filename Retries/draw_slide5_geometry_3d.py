"""3D review drawing of the current slide-5 RapidFEM dipole geometry.

This is not a solver mesh; it is a visual check of the modeling choices used
in ``verify_slide5_dipole.py``.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


OUT = Path("results")
OUT.mkdir(exist_ok=True)

TOTAL_LENGTH = 165.0  # mm
WIDTH = 4.0  # mm
GAP = 2.0  # mm
ARM = (TOTAL_LENGTH - GAP) / 2.0

C0 = 299_792_458.0
F_REF = 0.8e9
LAMBDA_REF_MM = C0 / F_REF * 1e3
PAD = 0.18 * LAMBDA_REF_MM

DOMAIN_X = TOTAL_LENGTH + 2.0 * PAD
DOMAIN_Y = WIDTH + 2.0 * PAD
DOMAIN_Z = 2.0 * PAD


def box_faces(x0, x1, y0, y1, z0, z1):
    return [
        [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)],
        [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
        [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
        [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)],
        [(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)],
        [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
    ]


def add_box(ax, x0, x1, y0, y1, z0, z1, color, alpha, edge="black", lw=0.8):
    coll = Poly3DCollection(
        box_faces(x0, x1, y0, y1, z0, z1),
        facecolor=color,
        edgecolor=edge,
        linewidth=lw,
        alpha=alpha,
    )
    ax.add_collection3d(coll)


def add_plate(ax, x0, x1, y0, y1, z=0.0, color="#9a9a9a", edge="black"):
    verts = [[(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]]
    coll = Poly3DCollection(verts, facecolor=color, edgecolor=edge, linewidth=1.4, alpha=0.95)
    ax.add_collection3d(coll)


def main() -> None:
    fig = plt.figure(figsize=(11, 8))
    ax = fig.add_subplot(111, projection="3d")

    # Air domain as a transparent box.
    add_box(
        ax,
        -DOMAIN_X / 2,
        DOMAIN_X / 2,
        -DOMAIN_Y / 2,
        DOMAIN_Y / 2,
        -DOMAIN_Z / 2,
        DOMAIN_Z / 2,
        color="#9ecae1",
        alpha=0.055,
        edge="#3182bd",
        lw=0.7,
    )

    y0 = -WIDTH / 2
    y1 = WIDTH / 2
    left_x0 = -GAP / 2 - ARM
    left_x1 = -GAP / 2
    right_x0 = GAP / 2
    right_x1 = GAP / 2 + ARM

    add_plate(ax, left_x0, left_x1, y0, y1, 0.0)
    add_plate(ax, right_x0, right_x1, y0, y1, 0.0)
    add_plate(ax, -GAP / 2, GAP / 2, y0, y1, 0.10, color="#ffb3b3", edge="#c43c39")

    # Centerline, feed direction, and labels.
    ax.plot([-TOTAL_LENGTH / 2, TOTAL_LENGTH / 2], [0, 0], [0.35, 0.35], color="cyan", lw=2)
    ax.quiver(-GAP / 2, -7, 0.5, GAP, 0, 0, color="#c43c39", linewidth=2, arrow_length_ratio=0.35)

    ax.text(0, -13, 2.5, "50 Ω lumped port\n2 mm gap, E → +x", color="#c43c39", ha="center", fontsize=10)
    ax.text(-42, 6, 2.0, "left PEC arm\n81.5 mm", ha="center", fontsize=9)
    ax.text(42, 6, 2.0, "right PEC arm\n81.5 mm", ha="center", fontsize=9)
    ax.text(0, 15, 4.0, "total length = 165 mm", color="navy", ha="center", fontsize=10)
    ax.text(89, 0, 2.0, "width = 4 mm", color="navy", fontsize=10)

    # Dimension guide lines.
    ax.plot([-TOTAL_LENGTH / 2, TOTAL_LENGTH / 2], [12, 12], [1, 1], color="navy", lw=1.4)
    ax.scatter([-TOTAL_LENGTH / 2, TOTAL_LENGTH / 2], [12, 12], [1, 1], color="navy", s=18)

    ax.set_title(
        "3D geometry review: slide 5 free-space strip dipole interpretation\n"
        "zero-thickness PEC plates + center lumped feed; transparent box = ABC air domain"
    )
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_zlabel("z (mm)")

    ax.set_xlim(-105, 105)
    ax.set_ylim(-45, 45)
    ax.set_zlim(-25, 35)
    ax.view_init(elev=23, azim=-58)
    ax.set_box_aspect((210, 90, 60))
    ax.grid(True, alpha=0.25)

    fig.tight_layout()
    fig.savefig(OUT / "slide5_geometry_3d_review.png", dpi=180)
    plt.close(fig)

    print(f"Wrote {OUT / 'slide5_geometry_3d_review.png'}")


if __name__ == "__main__":
    main()
