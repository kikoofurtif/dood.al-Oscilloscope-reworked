#!/usr/bin/env python3
"""Convert an svg-xy-trace-v1 JSON file to stereo PCM WAV audio."""
from __future__ import annotations

import argparse
import json
import math
import struct
import sys
import wave
from pathlib import Path
from typing import Any


def load_strokes(json_path: Path) -> list[list[tuple[float, float]]]:
    """Load pen-down XY strokes, splitting at pen-up and end-stroke markers."""
    try:
        data: Any = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read JSON file '{json_path}': {exc}") from exc

    if not isinstance(data, dict) or data.get("format") != "svg-xy-trace-v1":
        raise ValueError("Unsupported JSON format; expected 'svg-xy-trace-v1'.")

    points = data.get("points")
    if not isinstance(points, list) or not points:
        raise ValueError("JSON must contain a non-empty 'points' array.")

    strokes: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    previous_stroke_id: Any = None
    for index, point in enumerate(points):
        if not isinstance(point, dict):
            raise ValueError(f"Point {index} must be a JSON object.")
        pen_down = point.get("pen_down", True)
        stroke_id = point.get("stroke_id")
        if pen_down is not True and pen_down is not False:
            raise ValueError(f"Point {index} has an invalid 'pen_down' value.")
        if current and (not pen_down or (
            stroke_id is not None and previous_stroke_id is not None
            and stroke_id != previous_stroke_id
        )):
            strokes.append(current)
            current = []
        if pen_down:
            coords: list[float] = []
            for axis in ("x", "y"):
                value = point.get(axis)
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError(f"Point {index} must have numeric '{axis}' coordinates.")
                coordinate = float(value)
                if not math.isfinite(coordinate):
                    raise ValueError(f"Point {index} has a non-finite '{axis}' coordinate.")
                coords.append(coordinate)
            current.append((coords[0], coords[1]))
        previous_stroke_id = stroke_id
        if point.get("end_stroke") is True and current:
            strokes.append(current)
            current = []
            previous_stroke_id = None
    if current:
        strokes.append(current)
    if not strokes:
        raise ValueError("JSON does not contain any pen-down points.")
    return strokes


def _frames_per_stroke(
    strokes: list[list[tuple[float, float]]],
    active_frames: int,
) -> list[int]:
    """Allocate active output frames across strokes, weighted by their edges."""
    if active_frames < len(strokes):
        raise ValueError("Duration is too short to allocate one audio frame per stroke.")
    weights = [max(len(stroke) - 1, 1) for stroke in strokes]
    remaining = active_frames - len(strokes)
    total_weight = sum(weights)
    quotas = [remaining * weight / total_weight for weight in weights]
    allocations = [1 + int(quota) for quota in quotas]
    leftover = active_frames - sum(allocations)
    order = sorted(
        range(len(strokes)),
        key=lambda i: quotas[i] - int(quotas[i]),
        reverse=True,
    )
    for index in order[:leftover]:
        allocations[index] += 1
    return allocations


def _encode_stroke(
    stroke: list[tuple[float, float]],
    frame_count: int,
    amplitude: float,
) -> bytes:
    """Linearly resample one stroke to stereo signed 16-bit PCM."""
    pcm = bytearray(frame_count * 4)
    last_point = len(stroke) - 1
    for frame in range(frame_count):
        position = frame * last_point / max(frame_count - 1, 1)
        segment = min(int(position), max(last_point - 1, 0))
        fraction = position - segment if last_point else 0.0
        if last_point:
            x0, y0 = stroke[segment]
            x1, y1 = stroke[segment + 1]
            x = x0 + (x1 - x0) * fraction
            y = y0 + (y1 - y0) * fraction
        else:
            x, y = stroke[0]
        left = round(max(-1.0, min(1.0, x * amplitude)) * 32767)
        right = round(max(-1.0, min(1.0, y * amplitude)) * 32767)
        struct.pack_into("<hh", pcm, frame * 4, left, right)
    return bytes(pcm)


def convert_json_to_wav(
    json_path: Path,
    wav_path: Path,
    sample_rate: int = 48_000,
    duration: float = 5.0,
    amplitude: float = 0.8,
    gap_ms: float = 20.0,
) -> int:
    """Write one pass of the trace as a stereo WAV and return its frame count."""
    if sample_rate < 8_000 or sample_rate > 192_000:
        raise ValueError("Sample rate must be between 8000 and 192000 Hz.")
    if not math.isfinite(duration) or not 0.05 <= duration <= 600:
        raise ValueError("Duration must be between 0.05 and 600 seconds.")
    if not math.isfinite(amplitude) or not 0 < amplitude <= 1:
        raise ValueError("Amplitude must be greater than 0 and no more than 1.")
    if not math.isfinite(gap_ms) or not 0 <= gap_ms <= 1000:
        raise ValueError("Stroke gap must be between 0 and 1000 milliseconds.")

    strokes = load_strokes(json_path)
    total_frames = round(sample_rate * duration)
    gap_frames = round(sample_rate * gap_ms / 1000)
    all_gap_frames = gap_frames * (len(strokes) - 1)
    active_frames = total_frames - all_gap_frames
    if active_frames < len(strokes):
        raise ValueError("Duration is too short for the requested stroke gaps.")
    stroke_frames = _frames_per_stroke(strokes, active_frames)

    wav_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(wav_path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        for index, (stroke, frame_count) in enumerate(zip(strokes, stroke_frames)):
            output.writeframesraw(_encode_stroke(stroke, frame_count, amplitude))
            if index < len(strokes) - 1 and gap_frames:
                output.writeframesraw(bytes(gap_frames * 4))
    return total_frames


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert SVG XY trace JSON to stereo WAV (X=left, Y=right)."
    )
    parser.add_argument("json", type=Path, help="Input svg-xy-trace-v1 JSON file")
    parser.add_argument("-o", "--output", type=Path, default=None,
                        help="Output WAV path (default: same path as JSON with .wav)")
    parser.add_argument("--sample-rate", type=int, default=48_000,
                        help="Output sample rate in Hz (default: 48000)")
    parser.add_argument("--duration", type=float, default=5.0,
                        help="Duration of one complete trace in seconds (default: 5)")
    parser.add_argument("--amplitude", type=float, default=0.8,
                        help="Output level between 0 and 1 (default: 0.8)")
    parser.add_argument("--gap-ms", type=float, default=20.0,
                        help="Silence between separate strokes in milliseconds (default: 20)")
    args = parser.parse_args()

    output = args.output or args.json.with_suffix(".wav")
    try:
        frame_count = convert_json_to_wav(
            args.json, output, args.sample_rate, args.duration, args.amplitude, args.gap_ms
        )
    except (OSError, ValueError, wave.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(
        f"WAV: {output} ({frame_count} stereo frames, "
        f"{args.sample_rate} Hz, {args.duration:g} seconds)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
