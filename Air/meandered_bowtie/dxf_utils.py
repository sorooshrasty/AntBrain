"""Small ASCII DXF parser for the antenna DXF files in this workspace.

The current DXFs are simple AC1009 files containing closed POLYLINE entities.
This parser intentionally supports only the entity subset we need for geometry
review and RapidFEM conversion.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Polyline:
    layer: str
    closed: bool
    points_mm: list[tuple[float, float]]

    @property
    def bbox_mm(self) -> tuple[float, float, float, float]:
        xs = [p[0] for p in self.points_mm]
        ys = [p[1] for p in self.points_mm]
        return min(xs), min(ys), max(xs), max(ys)

    @property
    def area_mm2(self) -> float:
        pts = self.points_mm
        area = 0.0
        for i, (x0, y0) in enumerate(pts):
            x1, y1 = pts[(i + 1) % len(pts)]
            area += x0 * y1 - x1 * y0
        return 0.5 * area

    def ccw_points_mm(self) -> list[tuple[float, float]]:
        pts = list(self.points_mm)
        if self.area_mm2 < 0.0:
            pts.reverse()
        return pts


def read_group_pairs(path: Path) -> list[tuple[str, str]]:
    lines = path.read_text(errors="ignore").splitlines()
    pairs: list[tuple[str, str]] = []
    for idx in range(0, len(lines) - 1, 2):
        pairs.append((lines[idx].strip(), lines[idx + 1].strip()))
    return pairs


def parse_polylines(path: str | Path) -> list[Polyline]:
    pairs = read_group_pairs(Path(path))
    polylines: list[Polyline] = []
    i = 0

    while i < len(pairs):
        code, value = pairs[i]
        if code == "0" and value == "POLYLINE":
            layer = ""
            closed = False
            points: list[tuple[float, float]] = []
            i += 1

            while i < len(pairs):
                code, value = pairs[i]
                if code == "8":
                    layer = value
                elif code == "70":
                    try:
                        closed = bool(int(value) & 1)
                    except ValueError:
                        closed = False
                elif code == "0" and value == "VERTEX":
                    x = None
                    y = None
                    i += 1
                    while i < len(pairs):
                        vcode, vvalue = pairs[i]
                        if vcode == "0":
                            i -= 1
                            break
                        if vcode == "10":
                            x = float(vvalue)
                        elif vcode == "20":
                            y = float(vvalue)
                        i += 1
                    if x is not None and y is not None:
                        points.append((x, y))
                elif code == "0" and value == "SEQEND":
                    break
                i += 1

            clean: list[tuple[float, float]] = []
            for point in points:
                if not clean or point != clean[-1]:
                    clean.append(point)
            if len(clean) > 1 and clean[0] == clean[-1]:
                clean = clean[:-1]
            if len(clean) >= 3:
                polylines.append(Polyline(layer=layer, closed=closed, points_mm=clean))
        i += 1

    return polylines


def layer_polylines(path: str | Path, layer: str) -> list[Polyline]:
    return [poly for poly in parse_polylines(path) if poly.layer.lower() == layer.lower()]


def mm_points_to_m(points_mm: list[tuple[float, float]]) -> list[tuple[float, float]]:
    return [(x * 1.0e-3, y * 1.0e-3) for x, y in points_mm]
