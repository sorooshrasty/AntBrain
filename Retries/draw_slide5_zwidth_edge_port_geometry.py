"""Draw Slide 5 geometry with 4 mm dipole width along z axis.

This is a geometry review only.  It does not run RapidFEM.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


OUT = Path("results")
OUT.mkdir(exist_ok=True)

TOTAL_LENGTH = 165.0  # mm, x direction
Z_WIDTH = 4.0  # mm, z direction
CENTER_GAP = 2.0  # mm, x direction
ARM = (TOTAL_LENGTH - CENTER_GAP) / 2.0
FEED_Y = -35.0  # mm
FEED_METAL_WIDTH_X = 0.5  # mm, assumed conductor width in x
PORT_DEPTH_Y = 0.5  # mm, small port extent along y for visualization


def dim_arrow(ax, xy0, xy1, text, *, color="navy", offset=(0, 0), fontsize=9):
    ax.annotate(
        "",
        xy=xy1,
        xytext=xy0,
        arrowprops=dict(arrowstyle="<->", color=color, lw=1.3, shrinkA=0, shrinkB=0),
    )
    ax.text(
        (xy0[0] + xy1[0]) / 2 + offset[0],
        (xy0[1] + xy1[1]) / 2 + offset[1],
        text,
        ha="center",
        va="center",
        color=color,
        fontsize=fontsize,
    )


def add_plate3d(ax, pts, color="#9a9a9a", edge="black", alpha=0.95):
    ax.add_collection3d(
        Poly3DCollection([pts], facecolor=color, edgecolor=edge, linewidth=1.2, alpha=alpha)
    )


def main() -> None:
    fig = plt.figure(figsize=(14, 6.5))

    left_arm_x0 = -CENTER_GAP / 2 - ARM
    left_arm_x1 = -CENTER_GAP / 2
    right_arm_x0 = CENTER_GAP / 2
    right_arm_x1 = CENTER_GAP / 2 + ARM

    z0 = -Z_WIDTH / 2
    z1 = Z_WIDTH / 2

    left_feed_x0 = left_arm_x1 - FEED_METAL_WIDTH_X
    left_feed_x1 = left_arm_x1
    right_feed_x0 = right_arm_x0
    right_feed_x1 = right_arm_x0 + FEED_METAL_WIDTH_X

    # Left: x-z front view at y=0, showing the 4 mm z-width.
    ax = fig.add_subplot(1, 2, 1)
    ax.add_patch(Rectangle((left_arm_x0, z0), ARM, Z_WIDTH, facecolor="#9a9a9a", edgecolor="black", lw=1.3))
    ax.add_patch(Rectangle((right_arm_x0, z0), ARM, Z_WIDTH, facecolor="#9a9a9a", edgecolor="black", lw=1.3))
    ax.add_patch(Rectangle((left_feed_x0, z0), FEED_METAL_WIDTH_X, Z_WIDTH, facecolor="#707070", edgecolor="black", lw=1.2))
    ax.add_patch(Rectangle((right_feed_x0, z0), FEED_METAL_WIDTH_X, Z_WIDTH, facecolor="#707070", edgecolor="black", lw=1.2))
    ax.add_patch(Rectangle((-CENTER_GAP / 2, z0), CENTER_GAP, Z_WIDTH, facecolor="#ffcccc", edgecolor="#c43c39", lw=1.4, hatch="//", alpha=0.85))

    dim_arrow(ax, (-TOTAL_LENGTH / 2, 8), (TOTAL_LENGTH / 2, 8), "dipole total length = 165 mm", offset=(0, 3))
    dim_arrow(ax, (92, z0), (92, z1), "z width = 4 mm", offset=(12, 0))
    dim_arrow(ax, (-CENTER_GAP / 2, 5), (CENTER_GAP / 2, 5), "gap = 2 mm", color="#c43c39", offset=(0, 2), fontsize=8)
    ax.text(0, -6, "front view at y=0\nmetal width is in z", color="#444444", ha="center", fontsize=10)

    ax.set_title("Front view: dipole is 165 mm × 4 mm in x–z plane")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("z (mm)")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-105, 105)
    ax.set_ylim(-10, 14)
    ax.grid(True, alpha=0.25)

    # Right: 3D view showing feed metals extend along y.
    ax3 = fig.add_subplot(1, 2, 2, projection="3d")

    # Dipole arms: x-z plates at y=0.
    add_plate3d(
        ax3,
        [(left_arm_x0, 0, z0), (left_arm_x1, 0, z0), (left_arm_x1, 0, z1), (left_arm_x0, 0, z1)],
    )
    add_plate3d(
        ax3,
        [(right_arm_x0, 0, z0), (right_arm_x1, 0, z0), (right_arm_x1, 0, z1), (right_arm_x0, 0, z1)],
    )

    # Feed metals: y-z plates at fixed x positions, parallel, separated by 2 mm.
    add_plate3d(
        ax3,
        [(left_feed_x0, FEED_Y, z0), (left_feed_x1, FEED_Y, z0), (left_feed_x1, 0, z1), (left_feed_x0, 0, z1)],
        color="#707070",
    )
    add_plate3d(
        ax3,
        [(right_feed_x0, FEED_Y, z0), (right_feed_x1, FEED_Y, z0), (right_feed_x1, 0, z1), (right_feed_x0, 0, z1)],
        color="#707070",
    )

    # Edge-connected port: x-z plate near y=-35, spanning between inner feed edges.
    y_port = FEED_Y
    add_plate3d(
        ax3,
        [(-CENTER_GAP / 2, y_port, z0), (CENTER_GAP / 2, y_port, z0), (CENTER_GAP / 2, y_port, z1), (-CENTER_GAP / 2, y_port, z1)],
        color="#ffcccc",
        edge="#c43c39",
        alpha=0.85,
    )

    ax3.scatter([0], [FEED_Y], [0], color="#c43c39", s=60)
    ax3.text(0, FEED_Y - 4, 3.2, "edge-connected\n50 Ω port", color="#c43c39", ha="center")
    ax3.text(0, -17, 4.6, "two parallel feed metals\n2 mm clear gap", color="#444444", ha="center")
    ax3.text(45, 2, 4.6, "4 mm is z dimension", color="navy", ha="center")

    ax3.set_title("3D view: feed extends along y, metal width along z")
    ax3.set_xlabel("x (mm)")
    ax3.set_ylabel("y (mm)")
    ax3.set_zlabel("z (mm)")
    ax3.set_xlim(-95, 95)
    ax3.set_ylim(-45, 20)
    ax3.set_zlim(-8, 10)
    ax3.view_init(elev=24, azim=-58)
    ax3.set_box_aspect((190, 65, 18))
    ax3.grid(True, alpha=0.25)

    fig.suptitle("Slide 5 corrected orientation: 4 mm width is along z axis")
    fig.tight_layout()
    fig.savefig(OUT / "slide5_zwidth_edge_port_geometry.png", dpi=180)
    plt.close(fig)
    print(f"Wrote {OUT / 'slide5_zwidth_edge_port_geometry.png'}")


if __name__ == "__main__":
    main()
