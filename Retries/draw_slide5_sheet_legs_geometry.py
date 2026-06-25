"""Geometry review drawing for the latest slide-5 sheet-metal feed-leg model."""

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
LEG_LENGTH = 35.0  # mm
ARM = (TOTAL_LENGTH - GAP) / 2.0


def add_plate3d(ax, x0, x1, y0, y1, z=0.0, color="#9a9a9a", edge="black", alpha=0.95):
    verts = [[(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]]
    ax.add_collection3d(
        Poly3DCollection(verts, facecolor=color, edgecolor=edge, linewidth=1.2, alpha=alpha)
    )


def dim_arrow(ax, xy0, xy1, text, *, color="navy", text_offset=(0, 0), fontsize=9):
    ax.annotate(
        "",
        xy=xy1,
        xytext=xy0,
        arrowprops=dict(arrowstyle="<->", color=color, lw=1.3, shrinkA=0, shrinkB=0),
    )
    ax.text(
        (xy0[0] + xy1[0]) / 2 + text_offset[0],
        (xy0[1] + xy1[1]) / 2 + text_offset[1],
        text,
        ha="center",
        va="center",
        color=color,
        fontsize=fontsize,
    )


def main() -> None:
    fig = plt.figure(figsize=(14, 6))

    # Top view.
    ax = fig.add_subplot(1, 2, 1)
    left_x0 = -GAP / 2 - ARM
    left_x1 = -GAP / 2
    right_x0 = GAP / 2
    right_x1 = GAP / 2 + ARM

    # Dipole arms.
    ax.add_patch(Rectangle((left_x0, -WIDTH / 2), ARM, WIDTH, facecolor="#9a9a9a", edgecolor="black", lw=1.2))
    ax.add_patch(Rectangle((right_x0, -WIDTH / 2), ARM, WIDTH, facecolor="#9a9a9a", edgecolor="black", lw=1.2))

    # Feed legs.
    ax.add_patch(Rectangle((-GAP / 2 - WIDTH, -LEG_LENGTH), WIDTH, LEG_LENGTH, facecolor="#b0b0b0", edgecolor="black", lw=1.2))
    ax.add_patch(Rectangle((GAP / 2, -LEG_LENGTH), WIDTH, LEG_LENGTH, facecolor="#b0b0b0", edgecolor="black", lw=1.2))

    # Lumped port sheet across center gap.
    ax.add_patch(Rectangle((-GAP / 2, -WIDTH / 2), GAP, WIDTH, facecolor="#ffcccc", edgecolor="#c43c39", lw=1.4, hatch="//"))

    dim_arrow(ax, (-TOTAL_LENGTH / 2, 12), (TOTAL_LENGTH / 2, 12), "dipole total length = 165 mm", text_offset=(0, 4))
    dim_arrow(ax, (92, -WIDTH / 2), (92, WIDTH / 2), "width = 4 mm", text_offset=(12, 0))
    dim_arrow(ax, (14, -LEG_LENGTH), (14, 0), "feed-leg length = 35 mm", color="#444444", text_offset=(18, 0))
    dim_arrow(ax, (-GAP / 2, 7), (GAP / 2, 7), "gap = 2 mm", color="#c43c39", text_offset=(0, 3), fontsize=8)

    ax.text(0, -7, "50 Ω lumped port\nacross center gap", ha="center", va="top", color="#c43c39", fontsize=9)
    ax.text(-42, 4, "left PEC sheet arm\n81.5 mm", ha="center", fontsize=9)
    ax.text(42, 4, "right PEC sheet arm\n81.5 mm", ha="center", fontsize=9)
    ax.text(-12, -24, "left feed leg", ha="center", fontsize=9)
    ax.text(12, -24, "right feed leg", ha="center", fontsize=9)

    ax.set_title("Top view: latest feed-leg model")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-105, 105)
    ax.set_ylim(-45, 25)
    ax.grid(True, alpha=0.25)

    # 3D view.
    ax3 = fig.add_subplot(1, 2, 2, projection="3d")
    add_plate3d(ax3, left_x0, left_x1, -WIDTH / 2, WIDTH / 2)
    add_plate3d(ax3, right_x0, right_x1, -WIDTH / 2, WIDTH / 2)
    add_plate3d(ax3, -GAP / 2 - WIDTH, -GAP / 2, -LEG_LENGTH, 0)
    add_plate3d(ax3, GAP / 2, GAP / 2 + WIDTH, -LEG_LENGTH, 0)
    add_plate3d(ax3, -GAP / 2, GAP / 2, -WIDTH / 2, WIDTH / 2, z=0.03, color="#ffcccc", edge="#c43c39", alpha=0.8)

    ax3.text(0, -12, 4, "center lumped port", color="#c43c39", ha="center")
    ax3.text(0, 13, 3, "very-thin PEC sheet model\nzero metal volume thickness", color="#444444", ha="center")
    ax3.text(0, -37, 3, "two feed legs included", color="#444444", ha="center")

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

    fig.suptitle("Geometry review: Slide 5 thin-sheet dipole with center-feed legs")
    fig.tight_layout()
    fig.savefig(OUT / "slide5_sheet_legs_geometry_review.png", dpi=180)
    plt.close(fig)

    print(f"Wrote {OUT / 'slide5_sheet_legs_geometry_review.png'}")


if __name__ == "__main__":
    main()
