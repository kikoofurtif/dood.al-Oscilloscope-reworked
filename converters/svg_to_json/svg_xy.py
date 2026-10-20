#!/usr/bin/env python3
"""
SVG -> oscilloscope XY point-path converter.

Exports:
  - CSV: index, stroke_id, pen_down, x, y
  - JSON: metadata and ordered points
  - Optional JavaScript X/Y expressions for generators that support
    Math.floor, arrays are NOT assumed to be supported by the target.

Important:
  CSV/JSON are the reliable outputs. The XXY guide describes independent
  JavaScript expressions but does not document array literals or a point
  playback API, so generated expressions are only offered as an optional
  compatibility experiment and can be very long.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

try:
    import svgpathtools
    from svgpathtools import svg2paths2
except ImportError:
    print("Missing dependency. Install with: python -m pip install svgpathtools", file=sys.stderr)
    raise SystemExit(2)


def parse_color_opacity(style: dict[str, str], key: str, default: float = 1.0) -> float:
    raw = style.get(key)
    if raw is None:
        return default
    try:
        return max(0.0, min(1.0, float(raw)))
    except ValueError:
        return default


def parse_style(style_text: str | None) -> dict[str, str]:
    result: dict[str, str] = {}
    if not style_text:
        return result
    for item in style_text.split(";"):
        if ":" in item:
            key, value = item.split(":", 1)
            result[key.strip().lower()] = value.strip()
    return result


def parse_svg_number(value: str | None, fallback: float) -> float:
    if not value:
        return fallback
    value = value.strip()
    # SVG dimensions may carry units. viewBox is preferred for coordinates.
    number = ""
    for ch in value:
        if ch.isdigit() or ch in ".+-eE":
            number += ch
        else:
            break
    try:
        return float(number)
    except ValueError:
        return fallback


def get_viewbox(svg_attributes: dict[str, str]) -> tuple[float, float, float, float]:
    vb = svg_attributes.get("viewBox") or svg_attributes.get("viewbox")
    if vb:
        parts = vb.replace(",", " ").split()
        if len(parts) == 4:
            try:
                x, y, w, h = map(float, parts)
                if w > 0 and h > 0:
                    return x, y, w, h
            except ValueError:
                pass
    w = parse_svg_number(svg_attributes.get("width"), 100.0)
    h = parse_svg_number(svg_attributes.get("height"), 100.0)
    return 0.0, 0.0, max(w, 1.0), max(h, 1.0)


def sample_path(path_obj: Any, spacing: float, min_points_per_path: int) -> list[complex]:
    """Sample by approximate arc length; preserve curve detail using spacing."""
    try:
        length = float(path_obj.length(error=1e-4))
    except Exception:
        length = 0.0
    if not math.isfinite(length) or length <= 1e-12:
        try:
            return [path_obj.point(0), path_obj.point(1)]
        except Exception:
            return []
    count = max(min_points_per_path - 1, int(math.ceil(length / spacing)))
    count = min(count, 200_000)
    # svgpathtools' inverse arc length parameterization yields even-ish spacing.
    points: list[complex] = []
    for i in range(count + 1):
        distance = length * i / count
        try:
            t = path_obj.ilength(distance, s_tol=1e-5)
            points.append(path_obj.point(t))
        except Exception:
            # Fallback to uniform parameter sampling.
            points.append(path_obj.point(i / count))
    return points


def read_svg(svg_file: Path) -> tuple[list[Any], dict[str, str], list[dict[str, str]]]:
    paths, attributes, svg_attributes = svg2paths2(str(svg_file))
    return paths, svg_attributes, attributes


def load_svg(svg_file: Path, spacing: float, min_points: int,
             include_unpainted: bool) -> tuple[list[dict[str, Any]], tuple[float, float, float, float]]:
    paths, svg_attrs, path_attrs = read_svg(svg_file)
    viewbox = get_viewbox(svg_attrs)
    strokes: list[dict[str, Any]] = []
    for i, (path_obj, attrs) in enumerate(zip(paths, path_attrs)):
        style = parse_style(attrs.get("style"))
        stroke = style.get("stroke", attrs.get("stroke", "black"))
        display = style.get("display", attrs.get("display", "inline")).lower()
        visibility = style.get("visibility", attrs.get("visibility", "visible")).lower()
        opacity = parse_color_opacity(style, "opacity", parse_color_opacity(attrs, "opacity", 1.0))
        stroke_opacity = parse_color_opacity(style, "stroke-opacity", parse_color_opacity(attrs, "stroke-opacity", 1.0))
        if display == "none" or visibility == "hidden" or opacity <= 0 or stroke_opacity <= 0:
            continue
        # Ignore filled-only shapes because this program traces outlines/paths.
        if not include_unpainted and (stroke is None or stroke.strip().lower() in ("none", "")):
            continue
        points = sample_path(path_obj, spacing, min_points)
        if len(points) < 2:
            continue
        strokes.append({
            "stroke_id": len(strokes),
            "source_path_index": i,
            "points_complex": points,
            "svg_attributes": attrs,
        })
    return strokes, viewbox


def transform_points(strokes: list[dict[str, Any]], viewbox: tuple[float, float, float, float],
                     padding: float) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    vx, vy, vw, vh = viewbox
    all_points = [p for stroke in strokes for p in stroke["points_complex"]]
    if not all_points:
        raise ValueError("No drawable SVG paths found. Ensure the SVG contains visible stroked paths.")
    xs = [p.real for p in all_points]
    ys = [p.imag for p in all_points]
    # Preserve original viewBox aspect ratio, mapping the full viewBox to [-1,1].
    scale = 2.0 / max(vw, vh)
    pad_scale = max(0.0, min(padding, 0.45))
    usable = 1.0 - pad_scale
    cx = vx + vw / 2.0
    cy = vy + vh / 2.0

    result: list[dict[str, Any]] = []
    idx = 0
    for stroke in strokes:
        pts = stroke["points_complex"]
        for j, p in enumerate(pts):
            x = (p.real - cx) * scale * usable
            # SVG y increases downwards; invert it for conventional oscilloscope coordinates.
            y = -(p.imag - cy) * scale * usable
            result.append({
                "index": idx,
                "stroke_id": stroke["stroke_id"],
                "pen_down": True,
                "x": round(x, 8),
                "y": round(y, 8),
                "point_in_stroke": j,
            })
            idx += 1
        # Add a pen-up marker at the end of each path. This tells downstream
        # playback code not to connect this path to the next one.
        result[-1]["end_stroke"] = True

    metadata = {
        "source_viewBox": {"x": vx, "y": vy, "width": vw, "height": vh},
        "coordinate_range": {"x": [-1.0, 1.0], "y": [-1.0, 1.0]},
        "aspect_ratio_preserved": True,
        "padding_fraction": pad_scale,
        "path_count": len(strokes),
        "point_count": len(result),
        "note": "Separate SVG paths must be drawn as separate strokes; do not connect path ends.",
    }
    return result, metadata


def write_csv(path: Path, points: list[dict[str, Any]]) -> None:
    fields = ["index", "stroke_id", "pen_down", "x", "y", "point_in_stroke", "end_stroke"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for p in points:
            row = dict(p)
            row.setdefault("end_stroke", False)
            writer.writerow(row)


def write_json(path: Path, points: list[dict[str, Any]], metadata: dict[str, Any], source: Path) -> None:
    data = {
        "format": "svg-xy-trace-v1",
        "source_file": source.name,
        "metadata": metadata,
        "points": points,
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def js_array_expression(points: list[dict[str, Any]], axis: str, max_points: int) -> str:
    """
    Optional test export for JavaScript evaluators that allow array literals.
    Uses nearest index based on n, not t, because the guide provides sample counter n.
    This is not guaranteed compatible with XXY: array syntax isn't documented.
    """
    if len(points) > max_points:
        raise ValueError(f"Refusing JS expression with {len(points)} points; limit is {max_points}.")
    values = [p[axis] for p in points]
    # Array literals plus n are valid JavaScript, but the target may reject arrays.
    return "[" + ",".join(f"{v:.8f}" for v in values) + "][Math.floor(n)%"+str(len(values))+"]"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert SVG paths into ordered XY points for an oscilloscope."
    )
    parser.add_argument("svg", type=Path, help="Input SVG file")
    parser.add_argument("-o", "--output", type=Path, default=None,
                        help="Output base path (default: input filename without extension)")
    parser.add_argument("--spacing", type=float, default=1.5,
                        help="Approximate spacing between sampled points in SVG user units (default: 1.5)")
    parser.add_argument("--min-points", type=int, default=24,
                        help="Minimum samples per path (default: 24)")
    parser.add_argument("--padding", type=float, default=0.08,
                        help="Padding fraction inside normalized coordinate bounds (default: 0.08)")
    parser.add_argument("--include-unpainted", action="store_true",
                        help="Also trace paths with stroke='none' (usually not desired)")
    parser.add_argument("--js", action="store_true",
                        help="Also export experimental X.js.txt and Y.js.txt expressions")
    parser.add_argument("--js-max-points", type=int, default=500,
                        help="Safety cap for optional JS expressions (default: 500)")
    args = parser.parse_args()

    if not args.svg.exists():
        parser.error(f"Input file does not exist: {args.svg}")
    if args.spacing <= 0:
        parser.error("--spacing must be greater than zero")
    if args.min_points < 2:
        parser.error("--min-points must be at least 2")

    base = args.output or args.svg.with_suffix("")
    try:
        strokes, viewbox = load_svg(args.svg, args.spacing, args.min_points, args.include_unpainted)
        points, metadata = transform_points(strokes, viewbox, args.padding)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    csv_path = Path(str(base) + ".csv")
    json_path = Path(str(base) + ".json")
    write_csv(csv_path, points)
    write_json(json_path, points, metadata, args.svg)
    print(f"CSV:  {csv_path} ({len(points)} points)")
    print(f"JSON: {json_path} ({len(points)} points)")

    if args.js:
        try:
            x_expr = js_array_expression(points, "x", args.js_max_points)
            y_expr = js_array_expression(points, "y", args.js_max_points)
            Path(str(base) + ".X.js.txt").write_text(x_expr + "\n", encoding="utf-8")
            Path(str(base) + ".Y.js.txt").write_text(y_expr + "\n", encoding="utf-8")
            print("Experimental JavaScript expressions written.")
            print("WARNING: XXY's guide does not document array literals; these may be rejected.")
        except ValueError as exc:
            print(f"Skipping optional JS export: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
