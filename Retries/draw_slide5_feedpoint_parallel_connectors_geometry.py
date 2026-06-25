"""Draw Slide 5 geometry with two parallel feed metals separated by the gap.

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

TOTAL_LENGTH = 165.0  # mm
DIPOLE_WIDTH = 4.0  # mm
CENTER_GAP = 2.0  # mm
ARM = (TOTAL_LENGTH - CENTER_GAP) / 2.0
FEED_Y = -35.0  # mm
CONNECTOR_W = 0.5  # mm; assumed thin feed-metal width


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


def add_plate3d(ax, x0, x1, y0, y1, z=0.0, color="#9a9a9a", edge="black", alpha=0.95):
    verts = [[(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]]
    ax.add_collection3d(
        Poly3DCollection(verts, facecolor=color, edgecolor=edge, linewidth=1.2, alpha=alpha)
    )


def main() -> None:
    fig = plt.figure(figsize=(14, 6))

    left_arm_x0 = -CENTER_GAP / 2 - ARM
    left_arm_x1 = -CENTER_GAP / 2
    right_arm_x0 = CENTER_GAP / 2
    right_arm_x1 = CENTER_GAP / 2 + ARM

    # Parallel connector interpretation:
    # The two inner connector edges remain separated by CENTER_GAP=2 mm.
    left_conn_x0 = left_arm_x1 - CONNECTOR_W
    left_conn_x1 = left_arm_x1
    right_conn_x0 = right_arm_x0
    right_conn_x1 = right_arm_x0 + CONNECTOR_W

    # Top view.
    ax = fig.add_subplot(1, 2, 1)
    ax.add_patch(Rectangle((left_arm_x0, -DIPOLE_WIDTH / 2), ARM, DIPOLE_WIDTH, facecolor="#9a9a9a", edgecolor="black", lw=1.3))
    ax.add_patch(Rectangle((right_arm_x0, -DIPOLE_WIDTH / 2), ARM, DIPOLE_WIDTH, facecolor="#9a9a9a", edgecolor="black", lw=1.3))

    # Two parallel feed metals.
    ax.add_patch(Rectangle((left_conn_x0, FEED_Y), CONNECTOR_W, -FEED_Y, facecolor="#707070", edgecolor="black", lw=1.2))
    ax.add_patch(Rectangle((right_conn_x0, FEED_Y), CONNECTOR_W, -FEED_Y, facecolor="#707070", edgecolor="black", lw=1.2))

    # Port/feed marker at the lower end across the center gap.
    ax.add_patch(
        Rectangle(
            (-CENTER_GAP / 2, FEED_Y - 0.6),
            CENTER_GAP,
            1.2,
            facecolor="#ffcccc",
            edgecolor="#c43c39",
            lw=1.2,
            hatch="//",
            zorder=4,
        )
    )
    ax.scatter([0], [FEED_Y], s=95, color="#c43c39", zorder=5)
    ax.annotate(
        "feed point / port centered\nbetween parallel metals\n(x=0, y=-35 mm)",
        xy=(0, FEED_Y),
        xytext=(25, -31),
        arrowprops=dict(arrowstyle="->", color="#c43c39", lw=1.3),
        color="#c43c39",
        fontsize=10,
        ha="left",
    )

    dim_arrow(ax, (-TOTAL_LENGTH / 2, 12), (TOTAL_LENGTH / 2, 12), "dipole total length = 165 mm", offset=(0, 4))
    dim_arrow(ax, (92, -DIPOLE_WIDTH / 2), (92, DIPOLE_WIDTH / 2), "width = 4 mm", offset=(12, 0))
    dim_arrow(ax, (-10, FEED_Y), (-10, 0), "parallel feed length = 35 mm", color="#c43c39", offset=(-18, 0))
    dim_arrow(ax, (-CENTER_GAP / 2, 7), (CENTER_GAP / 2, 7), "gap = 2 mm", color="#c43c39", offset=(0, 3))
    dim_arrow(ax, (left_conn_x1, -18), (right_conn_x0, -18), "2 mm spacing", color="#c43c39", offset=(0, -3), fontsize=8)

    ax.text(-42, 4.3, "left PEC arm\n81.5 mm", ha="center", fontsize=9)
    ax.text(42, 4.3, "right PEC arm\n81.5 mm", ha="center", fontsize=9)
    ax.text(0, -24, f"two parallel feed metals\nassumed metal width = {CONNECTOR_W:.1f} mm", color="#444444", ha="center", fontsize=9)

    ax.set_title("Top view: parallel feed metals separated by center gap")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-105, 105)
    ax.set_ylim(-45, 25)
    ax.grid(True, alpha=0.25)

    # 3D view.
    ax3 = fig.add_subplot(1, 2, 2, projection="3d")
    add_plate3d(ax3, left_arm_x0, left_arm_x1, -DIPOLE_WIDTH / 2, DIPOLE_WIDTH / 2)
    add_plate3d(ax3, right_arm_x0, right_arm_x1, -DIPOLE_WIDTH / 2, DIPOLE_WIDTH / 2)
    add_plate3d(ax3, left_conn_x0, left_conn_x1, FEED_Y, 0.0, color="#707070")
    add_plate3d(ax3, right_conn_x0, right_conn_x1, FEED_Y, 0.0, color="#707070")
    add_plate3d(ax3, -CENTER_GAP / 2, CENTER_GAP / 2, FEED_Y - 0.6, FEED_Y + 0.6, z=0.05, color="#ffcccc", edge="#c43c39", alpha=0.85)
    ax3.scatter([0], [FEED_Y], [0.25], color="#c43c39", s=60)
    ax3.text(0, FEED_Y - 4, 2.5, "feed point / port\n(0, -35, 0)", color="#c43c39", ha="center")
    ax3.text(0, -16, 2.5, "parallel feed metals\n2 mm clear gap", color="#444444", ha="center")

    ax3.set_title("3D view")
    ax3.set_xlabel("x (mm)")
    ax3.set_ylabel("y (mm)")
    ax3.set_zlabel("z (mm)")
    ax3.set_xlim(-95, 95)
    ax3.set_ylim(-45, 25)
    ax3.set_zlim(-8, 10)
    ax3.view_init(elev=28, azim=-60)
    ax3.set_box_aspect((190, 70, 18))
    ax3.grid(True, alpha=0.25)

    fig.suptitle("Slide 5 corrected geometry: two parallel feed metals, 2 mm spacing")
    fig.tight_layout()
    fig.savefig(OUT / "slide5_feedpoint_parallel_connectors_geometry.png", dpi=180)
    plt.close(fig)
    print(f"Wrote {OUT / 'slide5_feedpoint_parallel_connectors_geometry.png'}")


if __name__ == "__main__":
    main()
