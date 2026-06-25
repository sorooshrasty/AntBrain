"""Draw corrected Slide 5 centered feed-leg geometry."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


OUT = Path("results")
OUT.mkdir(exist_ok=True)

TOTAL_LENGTH = 165.0
WIDTH = 4.0
GAP = 2.0
ARM = (TOTAL_LENGTH - GAP) / 2.0
FEED_LEG_LENGTH = 35.0


def dim_arrow(ax, xy0, xy1, text, *, color="navy", offset=(0, 0)):
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
        fontsize=9,
    )


def main() -> None:
    fig, ax = plt.subplots(figsize=(10, 5.5))

    left_x0 = -GAP / 2 - ARM
    right_x0 = GAP / 2

    ax.add_patch(Rectangle((left_x0, -WIDTH / 2), ARM, WIDTH, facecolor="#9a9a9a", edgecolor="black", lw=1.3))
    ax.add_patch(Rectangle((right_x0, -WIDTH / 2), ARM, WIDTH, facecolor="#9a9a9a", edgecolor="black", lw=1.3))

    # Centered port/feed leg.  This is a lumped-port surface, not PEC metal.
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

    ax.scatter([0], [0], s=90, color="#c43c39", zorder=5)
    ax.annotate(
        "feed point at start of centered leg\n(x=0, y=0, z=0)",
        xy=(0, 0),
        xytext=(25, -12),
        arrowprops=dict(arrowstyle="->", color="#c43c39", lw=1.3),
        color="#c43c39",
        fontsize=10,
        ha="left",
    )

    dim_arrow(ax, (-TOTAL_LENGTH / 2, 12), (TOTAL_LENGTH / 2, 12), "dipole total length = 165 mm", offset=(0, 4))
    dim_arrow(ax, (92, -WIDTH / 2), (92, WIDTH / 2), "width = 4 mm", offset=(12, 0))
    dim_arrow(ax, (-10, -FEED_LEG_LENGTH), (-10, 0), "centered feed leg = 35 mm", color="#c43c39", offset=(-18, 0))
    dim_arrow(ax, (-GAP / 2, 7), (GAP / 2, 7), "gap = 2 mm", color="#c43c39", offset=(0, 3))

    ax.text(-42, 4.3, "left PEC arm\n81.5 mm", ha="center", fontsize=9)
    ax.text(42, 4.3, "right PEC arm\n81.5 mm", ha="center", fontsize=9)
    ax.text(0, -22, "centered lumped-port/feed leg\nnot PEC metal", color="#c43c39", ha="center", fontsize=9)

    ax.set_title("Corrected Slide 5 geometry: feed point at start of centered feed leg")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-105, 105)
    ax.set_ylim(-45, 25)
    ax.grid(True, alpha=0.25)

    fig.tight_layout()
    fig.savefig(OUT / "slide5_centered_feedleg_geometry.png", dpi=180)
    plt.close(fig)
    print(f"Wrote {OUT / 'slide5_centered_feedleg_geometry.png'}")


if __name__ == "__main__":
    main()
