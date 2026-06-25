"""Build an interactive RapidFEM fem-viewer page for the Slide 5 dipole geometry.

The generated JSON follows the mesh display_event format used by
https://fem.rapidpassives.org/embed/test and can be rendered by
fem-viewer.js.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote


OUT = Path("results")
OUT.mkdir(exist_ok=True)

JSON_OUT = OUT / "slide5_interactive_geometry.json"
HTML_OUT = OUT / "slide5_interactive_geometry.html"
STANDALONE_HTML_OUT = OUT / "slide5_interactive_geometry_standalone.html"

# Geometry dimensions in millimetres.
TOTAL_LENGTH = 165.0
Z_WIDTH = 4.0
CENTER_GAP = 2.0
ARM_LENGTH = (TOTAL_LENGTH - CENTER_GAP) / 2.0
FEED_Y = -35.0
METAL_THICKNESS_Y = 0.2
FEED_METAL_WIDTH_X = 0.5
PORT_DEPTH_Y = 0.25


def mm(value: float) -> float:
    """Convert millimetres to metres for the FEM viewer payload."""
    return value * 1e-3


nodes: list[list[float]] = []
tris: list[list[int]] = []
tri_phys: list[int] = []


def add_box(
    *,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    z0: float,
    z1: float,
    tag: int,
) -> None:
    """Add a rectangular solid surface mesh.

    Coordinates are in millimetres.  The output mesh is only the visible
    boundary, which is exactly what fem-viewer needs for a geometry review.
    """
    base = len(nodes)
    corners_mm = [
        (x0, y0, z0),
        (x1, y0, z0),
        (x1, y1, z0),
        (x0, y1, z0),
        (x0, y0, z1),
        (x1, y0, z1),
        (x1, y1, z1),
        (x0, y1, z1),
    ]
    nodes.extend([[mm(x), mm(y), mm(z)] for x, y, z in corners_mm])

    # Two triangles per face.  Winding is not critical for fem-viewer, but it is
    # kept consistent enough for lighting and edge rendering.
    faces = [
        (0, 1, 2, 3),  # z-
        (4, 7, 6, 5),  # z+
        (0, 4, 5, 1),  # y-
        (3, 2, 6, 7),  # y+
        (0, 3, 7, 4),  # x-
        (1, 5, 6, 2),  # x+
    ]
    for a, b, c, d in faces:
        tris.append([base + a, base + b, base + c])
        tris.append([base + a, base + c, base + d])
        tri_phys.extend([tag, tag])


def build_notebook() -> dict:
    left_arm_x0 = -TOTAL_LENGTH / 2.0
    left_arm_x1 = -CENTER_GAP / 2.0
    right_arm_x0 = CENTER_GAP / 2.0
    right_arm_x1 = TOTAL_LENGTH / 2.0

    y0 = -METAL_THICKNESS_Y / 2.0
    y1 = METAL_THICKNESS_Y / 2.0
    z0 = -Z_WIDTH / 2.0
    z1 = Z_WIDTH / 2.0

    # Main dipole arms: 165 mm total length with a 2 mm center gap.
    add_box(x0=left_arm_x0, x1=left_arm_x1, y0=y0, y1=y1, z0=z0, z1=z1, tag=100001)
    add_box(x0=right_arm_x0, x1=right_arm_x1, y0=y0, y1=y1, z0=z0, z1=z1, tag=100002)

    # Two parallel feed metals running from the arm inner edges down to y=-35 mm.
    # They are separated by the same 2 mm center gap and touch the port at their
    # inner x-edges.
    add_box(
        x0=left_arm_x1 - FEED_METAL_WIDTH_X,
        x1=left_arm_x1,
        y0=FEED_Y,
        y1=0.0,
        z0=z0,
        z1=z1,
        tag=100003,
    )
    add_box(
        x0=right_arm_x0,
        x1=right_arm_x0 + FEED_METAL_WIDTH_X,
        y0=FEED_Y,
        y1=0.0,
        z0=z0,
        z1=z1,
        tag=100004,
    )

    # Red lumped-port visual body at the start of the centered feed legs:
    # x=0, y=-35 mm.  It spans the 2 mm center gap and touches the two feed-metal
    # inner edges at x=-1 mm and x=+1 mm.
    add_box(
        x0=-CENTER_GAP / 2.0,
        x1=CENTER_GAP / 2.0,
        y0=FEED_Y - PORT_DEPTH_Y / 2.0,
        y1=FEED_Y + PORT_DEPTH_Y / 2.0,
        z0=z0,
        z1=z1,
        tag=100005,
    )

    xs = [p[0] for p in nodes]
    ys = [p[1] for p in nodes]
    zs = [p[2] for p in nodes]
    flat_nodes = [coord for point in nodes for coord in point]
    flat_tris = [index for tri in tris for index in tri]

    payload = {
        "kind": "mesh",
        "bbox": {
            "min": [min(xs), min(ys), min(zs)],
            "max": [max(xs), max(ys), max(zs)],
        },
        "nodes": flat_nodes,
        "tris": flat_tris,
        "tri_phys": tri_phys,
        "tets": [],
        "tet_phys": [],
        "phys_names": {
            "100001": "left_arm_conductor",
            "100002": "right_arm_conductor",
            "100003": "left_feed_conductor",
            "100004": "right_feed_conductor",
            "100005": "port_1_50ohm_edge_feed",
        },
        "phys_dim": {
            "100001": 2,
            "100002": 2,
            "100003": 2,
            "100004": 2,
            "100005": 2,
        },
        "name_to_tag": {
            "left_arm_conductor": 100001,
            "right_arm_conductor": 100002,
            "left_feed_conductor": 100003,
            "right_feed_conductor": 100004,
            "port_1_50ohm_edge_feed": 100005,
        },
        "stats": {
            "n_nodes": len(nodes),
            "n_tris": len(tris),
            "n_tets": 0,
            "n_phys": 5,
        },
    }

    return {
        "name": "slide5_thick_edge_feed_geometry",
        "cells": [
            {
                "type": "markdown",
                "source": "# Slide 5 dipole geometry review\\nFinite-thickness metal model for visual review.",
                "outputs": [],
                "display_events": [
                    {
                        "kind": "mesh",
                        "name": "slide5_geometry",
                        "payload": payload,
                    }
                ],
            }
        ],
    }


def build_html() -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Slide 5 dipole geometry - RapidFEM viewer</title>
  <script src="./fem-viewer.js"></script>
  <style>
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: #f6f7fb;
      color: #20242a;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 22px;
    }}
    .card {{
      background: white;
      border: 1px solid #d9dee8;
      border-radius: 14px;
      box-shadow: 0 8px 28px rgba(20, 31, 50, 0.08);
      overflow: hidden;
    }}
    fem-viewer {{
      display: block;
      width: 100%;
      height: 680px;
      background: linear-gradient(180deg, #ffffff 0%, #eef2f8 100%);
    }}
    .notes {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
      gap: 10px;
      margin-top: 14px;
      font-size: 14px;
      line-height: 1.4;
    }}
    .note {{
      background: #ffffff;
      border: 1px solid #d9dee8;
      border-radius: 10px;
      padding: 10px 12px;
    }}
    .legend {{
      display: inline-block;
      width: 12px;
      height: 12px;
      border-radius: 3px;
      margin-right: 6px;
      vertical-align: -1px;
    }}
    .metal {{ background: #c57c3f; }}
    .port {{ background: #e74b4b; }}
  </style>
</head>
<body>
  <main>
    <h2>Slide 5 dipole geometry review</h2>
    <p>
      Drag with the mouse to rotate. Scroll to zoom. This uses the same
      RapidFEM <code>&lt;fem-viewer&gt;</code> component pattern as
      <code>https://fem.rapidpassives.org/embed/test</code>.
    </p>
    <div class="card">
      <fem-viewer
        src="./{JSON_OUT.name}"
        interactive
        rotate
        mode="geometry"
        width="100%"
        height="680px">
      </fem-viewer>
    </div>
    <div class="notes">
      <div class="note"><span class="legend metal"></span>Dipole arms: 165 mm total x length, 4 mm z width, 0.2 mm y thickness.</div>
      <div class="note"><span class="legend metal"></span>Parallel feed strips: x-width 0.5 mm, y = 0 to -35 mm, separated by 2 mm center gap.</div>
      <div class="note"><span class="legend port"></span>Port visual: centered at x=0, y=-35 mm, touching the inner feed-strip edges.</div>
    </div>
  </main>
</body>
</html>
"""


def build_standalone_html(notebook: dict) -> str:
    data_url = "data:application/json;charset=utf-8," + quote(
        json.dumps(notebook, separators=(",", ":")),
        safe="",
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Slide 5 dipole geometry - standalone RapidFEM viewer</title>
  <script src="./fem-viewer.js"></script>
  <style>
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: #f6f7fb;
      color: #20242a;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 22px;
    }}
    .card {{
      background: white;
      border: 1px solid #d9dee8;
      border-radius: 14px;
      box-shadow: 0 8px 28px rgba(20, 31, 50, 0.08);
      overflow: hidden;
    }}
    fem-viewer {{
      display: block;
      width: 100%;
      height: 680px;
      background: linear-gradient(180deg, #ffffff 0%, #eef2f8 100%);
    }}
    .notes {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
      gap: 10px;
      margin-top: 14px;
      font-size: 14px;
      line-height: 1.4;
    }}
    .note {{
      background: #ffffff;
      border: 1px solid #d9dee8;
      border-radius: 10px;
      padding: 10px 12px;
    }}
  </style>
</head>
<body>
  <main>
    <h2>Slide 5 dipole geometry review - standalone file</h2>
    <p>
      This version does not need an IP address or local HTTP server. Drag to
      rotate, scroll to zoom.
    </p>
    <div class="card">
      <fem-viewer
        id="viewer"
        interactive
        rotate
        mode="geometry"
        width="100%"
        height="680px">
      </fem-viewer>
    </div>
    <div class="notes">
      <div class="note">Dipole arms: 165 mm total x length, 4 mm z width, 0.2 mm y thickness.</div>
      <div class="note">Parallel feed strips: x-width 0.5 mm, y = 0 to -35 mm, separated by 2 mm center gap.</div>
      <div class="note">Port visual: centered at x=0, y=-35 mm, touching the inner feed-strip edges.</div>
    </div>
  </main>
  <script>
    document.getElementById("viewer").setAttribute("src", "{data_url}");
  </script>
</body>
</html>
"""


def main() -> None:
    notebook = build_notebook()
    JSON_OUT.write_text(json.dumps(notebook, indent=2), encoding="utf-8")
    HTML_OUT.write_text(build_html(), encoding="utf-8")
    STANDALONE_HTML_OUT.write_text(build_standalone_html(notebook), encoding="utf-8")
    print(f"Wrote {JSON_OUT}")
    print(f"Wrote {HTML_OUT}")
    print(f"Wrote {STANDALONE_HTML_OUT}")
    print("Geometry summary:")
    print(f"  total length x: {TOTAL_LENGTH} mm")
    print(f"  conductor width z: {Z_WIDTH} mm")
    print(f"  conductor thickness y: {METAL_THICKNESS_Y} mm")
    print(f"  feed point: x=0 mm, y={FEED_Y} mm")
    print(f"  feed strip separation: {CENTER_GAP} mm")


if __name__ == "__main__":
    main()
