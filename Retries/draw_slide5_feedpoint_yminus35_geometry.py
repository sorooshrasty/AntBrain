"""Draw Slide 5 geometry with feed point at x=0 mm, y=-35 mm.

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
WIDTH = 4.0  # mm
GAP = 2.0  # mm
ARM = (TOTAL_LENGTH - GAP) / 2.0
FEED_LEG_LENGTH = 35.0  # mm


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

    left_x0 = -GAP / 2 - ARM
    right_x0 = GAP / 2

    # Top view.
    ax = fig.add_subplot(1, 2, 1)
    ax.add_patch(Rectangle((left_x0, -WIDTH / 2), ARM, WIDTH, facecolor="#9a9a9a", edgecolor="black", lw=1.3))
    ax.add_patch(Rectangle((right_x0, -WIDTH / 2), ARM, WIDTH, facecolor="#9a9a9a", edgecolor="black", lw=1.3))

    # Centered feed leg.  Shown as port/feed object, not PEC metal yet.
    ax.add_patch(
        Rectangle(
            (-GAP / 2, -FEED_LEG_LENGTH),
            GAP,
            FEED_LEG_LENGTH,
            facecolor="#ffcccc",
            edgecolor="#c43c39",
            lw=1.5,
            hatch="//",
            alpha=0.85,
        )
    )

    # Corrected feed point: distal end of centered leg.
    ax.scatter([0], [-FEED_LEG_LENGTH], s=95, color="#c43c39", zorder=5)
    ax.annotate(
        "corrected feed point\n(x=0, y=-35 mm, z=0)",
        xy=(0, -FEED_LEG_LENGTH),
        xytext=(25, -31),
        arrowprops=dict(arrowstyle="->", color="#c43c39", lw=1.3),
        color="#c43c39",
        fontsize=10,
        ha="left",
    )

    dim_arrow(ax, (-TOTAL_LENGTH / 2, 12), (TOTAL_LENGTH / 2, 12), "dipole total length = 165 mm", offset=(0, 4))
    dim_arrow(ax, (92, -WIDTH / 2), (92, WIDTH / 2), "width = 4 mm", offset=(12, 0))
    dim_arrow(ax, (-10, -FEED_LEG_LENGTH), (-10, 0), "centered feed leg = 35 mm", color="#c43c39", offset=(-18, 0))
    dim_arrow(ax, (-GAP / 2, 7), (GAP / 2, 7), "center gap = 2 mm", color="#c43c39", offset=(0, 3))

    ax.text(-42, 4.3, "left PEC arm\n81.5 mm", ha="center", fontsize=9)
    ax.text(42, 4.3, "right PEC arm\n81.5 mm", ha="center", fontsize=9)
    ax.text(0, -18, "centered feed leg", color="#c43c39", ha="center", fontsize=9)

    ax.set_title("Top view: feed point at x=0, y=-35 mm")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-105, 105)
    ax.set_ylim(-45, 25)
    ax.grid(True, alpha=0.25)

    # 3D view.
    ax3 = fig.add_subplot(1, 2, 2, projection="3d")
    add_plate3d(ax3, left_x0, -GAP / 2, -WIDTH / 2, WIDTH / 2)
    add_plate3d(ax3, right_x0, right_x0 + ARM, -WIDTH / 2, WIDTH / 2)
    add_plate3d(ax3, -GAP / 2, GAP / 2, -FEED_LEG_LENGTH, 0.0, z=0.03, color="#ffcccc", edge="#c43c39", alpha=0.85)
    ax3.scatter([0], [-FEED_LEG_LENGTH], [0.2], color="#c43c39", s=55)
    ax3.text(0, -FEED_LEG_LENGTH - 4, 2.5, "feed point\n(0, -35, 0)", color="#c43c39", ha="center")
    ax3.text(0, 8, 2.5, "dipole center gap", color="#444444", ha="center")

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

    fig.suptitle("Slide 5 corrected feed coordinate: x=0 mm, y=-35 mm")
    fig.tight_layout()
    fig.savefig(OUT / "slide5_feedpoint_yminus35_geometry.png", dpi=180)
    plt.close(fig)
    print(f"Wrote {OUT / 'slide5_feedpoint_yminus35_geometry.png'}")


if __name__ == "__main__":
    main()
