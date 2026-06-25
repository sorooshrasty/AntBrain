"""3D review drawing for the revised slide-5 finite-thickness dipole model."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


OUT = Path("results")
OUT.mkdir(exist_ok=True)

TOTAL_LENGTH = 165.0
WIDTH = 4.0
THICKNESS = 4.0
GAP = 2.0
ARM = (TOTAL_LENGTH - GAP) / 2.0


def box_faces(x0, x1, y0, y1, z0, z1):
    return [
        [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)],
        [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
        [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
        [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)],
        [(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)],
        [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
    ]


def add_box(ax, x0, x1, y0, y1, z0, z1, color="#9a9a9a", alpha=0.95, edge="black"):
    ax.add_collection3d(
        Poly3DCollection(
            box_faces(x0, x1, y0, y1, z0, z1),
            facecolor=color,
            edgecolor=edge,
            linewidth=1.1,
            alpha=alpha,
        )
    )


def add_port_sheet(ax):
    x0, x1 = -GAP / 2, GAP / 2
    y = 0.0
    z0, z1 = -THICKNESS / 2, THICKNESS / 2
    verts = [[(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]]
    ax.add_collection3d(
        Poly3DCollection(verts, facecolor="#ffb3b3", edgecolor="#c43c39", linewidth=1.5, alpha=0.8)
    )


def main():
    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection="3d")

    add_box(ax, -GAP / 2 - ARM, -GAP / 2, -WIDTH / 2, WIDTH / 2, -THICKNESS / 2, THICKNESS / 2)
    add_box(ax, GAP / 2, GAP / 2 + ARM, -WIDTH / 2, WIDTH / 2, -THICKNESS / 2, THICKNESS / 2)
    add_port_sheet(ax)

    ax.plot([-TOTAL_LENGTH / 2, TOTAL_LENGTH / 2], [7, 7], [4, 4], color="navy", lw=1.8)
    ax.scatter([-TOTAL_LENGTH / 2, TOTAL_LENGTH / 2], [7, 7], [4, 4], color="navy", s=25)
    ax.text(0, 8.5, 5.2, "total length = 165 mm", color="navy", ha="center")
    ax.text(0, -9, 4.8, "center lumped port only\n2 mm gap; no metal leg", color="#c43c39", ha="center")
    ax.text(-42, 4.2, 3.2, "left PEC bar\n81.5 mm", ha="center")
    ax.text(42, 4.2, 3.2, "right PEC bar\n81.5 mm", ha="center")
    ax.text(88, 0, 2, "4 mm × 4 mm\nsection", color="navy")

    ax.set_title("Revised slide 5 geometry: finite-thickness dipole, no feed leg")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_zlabel("z (mm)")
    ax.set_xlim(-95, 95)
    ax.set_ylim(-18, 18)
    ax.set_zlim(-10, 14)
    ax.view_init(elev=24, azim=-58)
    ax.set_box_aspect((190, 36, 24))
    ax.grid(True, alpha=0.25)

    fig.tight_layout()
    fig.savefig(OUT / "slide5_thick_geometry_3d_review.png", dpi=180)
    plt.close(fig)
    print(f"Wrote {OUT / 'slide5_thick_geometry_3d_review.png'}")


if __name__ == "__main__":
    main()
