"""Draw Slide 5 geometry with two thin metal connectors to the feed point.

This is a geometry review only.  It does not run RapidFEM.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


OUT = Path("results")
OUT.mkdir(exist_ok=True)

TOTAL_LENGTH = 165.0  # mm
WIDTH = 4.0  # mm
GAP = 2.0  # mm
ARM = (TOTAL_LENGTH - GAP) / 2.0
FEED_Y = -35.0  # mm
CONNECTOR_W = 0.5  # mm; assumed thin feed metal width


def strip_polygon(p0, p1, width):
    """Return a rectangular strip polygon around line p0->p1."""
    x0, y0 = p0
    x1, y1 = p1
    dx = x1 - x0
    dy = y1 - y0
    length = (dx * dx + dy * dy) ** 0.5
    nx = -dy / length * width / 2.0
    ny = dx / length * width / 2.0
    return [
        (x0 + nx, y0 + ny),
        (x1 + nx, y1 + ny),
        (x1 - nx, y1 - ny),
        (x0 - nx, y0 - ny),
    ]


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


def add_plate3d(ax, pts, z=0.0, color="#9a9a9a", edge="black", alpha=0.95):
    verts = [[(x, y, z) for x, y in pts]]
    ax.add_collection3d(
        Poly3DCollection(verts, facecolor=color, edgecolor=edge, linewidth=1.2, alpha=alpha)
    )


def main() -> None:
    fig = plt.figure(figsize=(14, 6))

    left_x0 = -GAP / 2 - ARM
    left_x1 = -GAP / 2
    right_x0 = GAP / 2
    right_x1 = GAP / 2 + ARM

    # Inner connection points at the two dipole-arm feed edges.
    left_feed_edge = (-GAP / 2, 0.0)
    right_feed_edge = (GAP / 2, 0.0)
    feed_point = (0.0, FEED_Y)

    left_connector = strip_polygon(left_feed_edge, feed_point, CONNECTOR_W)
    right_connector = strip_polygon(right_feed_edge, feed_point, CONNECTOR_W)

    # Top view.
    ax = fig.add_subplot(1, 2, 1)
    ax.add_patch(Rectangle((left_x0, -WIDTH / 2), ARM, WIDTH, facecolor="#9a9a9a", edgecolor="black", lw=1.3))
    ax.add_patch(Rectangle((right_x0, -WIDTH / 2), ARM, WIDTH, facecolor="#9a9a9a", edgecolor="black", lw=1.3))
    ax.add_patch(Polygon(left_connector, closed=True, facecolor="#707070", edgecolor="black", lw=1.2))
    ax.add_patch(Polygon(right_connector, closed=True, facecolor="#707070", edgecolor="black", lw=1.2))

    # Small feed/port marker at the end, not a large conductor.
    ax.scatter([feed_point[0]], [feed_point[1]], s=95, color="#c43c39", zorder=5)
    ax.add_patch(Rectangle((-GAP / 2, FEED_Y - 0.6), GAP, 1.2, facecolor="#ffcccc", edgecolor="#c43c39", lw=1.2, hatch="//"))

    ax.annotate(
        "feed point / port\n(x=0, y=-35 mm, z=0)",
        xy=feed_point,
        xytext=(25, -31),
        arrowprops=dict(arrowstyle="->", color="#c43c39", lw=1.3),
        color="#c43c39",
        fontsize=10,
        ha="left",
    )

    dim_arrow(ax, (-TOTAL_LENGTH / 2, 12), (TOTAL_LENGTH / 2, 12), "dipole total length = 165 mm", offset=(0, 4))
    dim_arrow(ax, (92, -WIDTH / 2), (92, WIDTH / 2), "width = 4 mm", offset=(12, 0))
    dim_arrow(ax, (-10, FEED_Y), (-10, 0), "feed drop = 35 mm", color="#c43c39", offset=(-14, 0))
    dim_arrow(ax, (-GAP / 2, 7), (GAP / 2, 7), "center gap = 2 mm", color="#c43c39", offset=(0, 3))

    ax.text(-42, 4.3, "left PEC arm\n81.5 mm", ha="center", fontsize=9)
    ax.text(42, 4.3, "right PEC arm\n81.5 mm", ha="center", fontsize=9)
    ax.text(0, -18, f"two thin metal connectors\nassumed width = {CONNECTOR_W:.1f} mm", color="#444444", ha="center", fontsize=9)

    ax.set_title("Top view: two thin metals connect to feed point")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-105, 105)
    ax.set_ylim(-45, 25)
    ax.grid(True, alpha=0.25)

    # 3D view.
    ax3 = fig.add_subplot(1, 2, 2, projection="3d")
    add_plate3d(ax3, [(left_x0, -WIDTH / 2), (left_x1, -WIDTH / 2), (left_x1, WIDTH / 2), (left_x0, WIDTH / 2)])
    add_plate3d(ax3, [(right_x0, -WIDTH / 2), (right_x1, -WIDTH / 2), (right_x1, WIDTH / 2), (right_x0, WIDTH / 2)])
    add_plate3d(ax3, left_connector, color="#707070")
    add_plate3d(ax3, right_connector, color="#707070")
    ax3.scatter([feed_point[0]], [feed_point[1]], [0.25], color="#c43c39", s=60)
    ax3.text(0, FEED_Y - 4, 2.5, "feed point\n(0, -35, 0)", color="#c43c39", ha="center")
    ax3.text(0, -16, 2.5, "two thin feed metals", color="#444444", ha="center")

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

    fig.suptitle("Slide 5 corrected geometry: two thin metal connectors to feed point")
    fig.tight_layout()
    fig.savefig(OUT / "slide5_feedpoint_two_connectors_geometry.png", dpi=180)
    plt.close(fig)
    print(f"Wrote {OUT / 'slide5_feedpoint_two_connectors_geometry.png'}")


if __name__ == "__main__":
    main()
