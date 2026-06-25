"""Draw Slide 5 geometry with port connected to feed-metal edges.

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
PORT_DEPTH = 0.5  # mm; small visual/model port depth along y


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

    left_conn_x0 = left_arm_x1 - CONNECTOR_W
    left_conn_x1 = left_arm_x1
    right_conn_x0 = right_arm_x0
    right_conn_x1 = right_arm_x0 + CONNECTOR_W

    # Port is edge-attached at the lower feed end, from y=-35 to y=-34.5.
    port_x0 = left_conn_x1
    port_x1 = right_conn_x0
    port_y0 = FEED_Y
    port_y1 = FEED_Y + PORT_DEPTH

    ax = fig.add_subplot(1, 2, 1)
    ax.add_patch(Rectangle((left_arm_x0, -DIPOLE_WIDTH / 2), ARM, DIPOLE_WIDTH, facecolor="#9a9a9a", edgecolor="black", lw=1.3))
    ax.add_patch(Rectangle((right_arm_x0, -DIPOLE_WIDTH / 2), ARM, DIPOLE_WIDTH, facecolor="#9a9a9a", edgecolor="black", lw=1.3))
    ax.add_patch(Rectangle((left_conn_x0, FEED_Y), CONNECTOR_W, -FEED_Y, facecolor="#707070", edgecolor="black", lw=1.2))
    ax.add_patch(Rectangle((right_conn_x0, FEED_Y), CONNECTOR_W, -FEED_Y, facecolor="#707070", edgecolor="black", lw=1.2))

    ax.add_patch(
        Rectangle(
            (port_x0, port_y0),
            port_x1 - port_x0,
            port_y1 - port_y0,
            facecolor="#ffcccc",
            edgecolor="#c43c39",
            lw=1.4,
            hatch="//",
            zorder=4,
        )
    )

    # Reference point at the port center; the physical contacts are the red edges.
    ref_x = 0.0
    ref_y = (port_y0 + port_y1) / 2
    ax.scatter([ref_x], [ref_y], s=65, color="#c43c39", zorder=5)
    ax.scatter([port_x0, port_x1], [FEED_Y, FEED_Y], s=55, color="#c43c39", zorder=5)

    ax.annotate(
        "port touches inner metal edges\nat feed end",
        xy=(port_x0, FEED_Y),
        xytext=(-55, -31),
        arrowprops=dict(arrowstyle="->", color="#c43c39", lw=1.3),
        color="#c43c39",
        fontsize=10,
        ha="left",
    )
    ax.annotate(
        "port reference center\n(not the only contact point)",
        xy=(ref_x, ref_y),
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

    ax.text(-42, 4.3, "left PEC arm\n81.5 mm", ha="center", fontsize=9)
    ax.text(42, 4.3, "right PEC arm\n81.5 mm", ha="center", fontsize=9)
    ax.text(0, -22, f"edge-connected 50 Ω lumped port\nport depth = {PORT_DEPTH:.1f} mm", color="#444444", ha="center", fontsize=9)

    ax.set_title("Top view: port connected to metal edges at feed end")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-105, 105)
    ax.set_ylim(-45, 25)
    ax.grid(True, alpha=0.25)

    ax3 = fig.add_subplot(1, 2, 2, projection="3d")
    add_plate3d(ax3, left_arm_x0, left_arm_x1, -DIPOLE_WIDTH / 2, DIPOLE_WIDTH / 2)
    add_plate3d(ax3, right_arm_x0, right_arm_x1, -DIPOLE_WIDTH / 2, DIPOLE_WIDTH / 2)
    add_plate3d(ax3, left_conn_x0, left_conn_x1, FEED_Y, 0.0, color="#707070")
    add_plate3d(ax3, right_conn_x0, right_conn_x1, FEED_Y, 0.0, color="#707070")
    add_plate3d(ax3, port_x0, port_x1, port_y0, port_y1, z=0.05, color="#ffcccc", edge="#c43c39", alpha=0.85)
    ax3.scatter([port_x0, port_x1], [FEED_Y, FEED_Y], [0.25, 0.25], color="#c43c39", s=55)
    ax3.text(0, FEED_Y - 4, 2.5, "edge-connected\nlumped port", color="#c43c39", ha="center")

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

    fig.suptitle("Slide 5 correction: feed port connected to metal edges, not just center")
    fig.tight_layout()
    fig.savefig(OUT / "slide5_feedpoint_edge_port_geometry.png", dpi=180)
    plt.close(fig)
    print(f"Wrote {OUT / 'slide5_feedpoint_edge_port_geometry.png'}")


if __name__ == "__main__":
    main()
