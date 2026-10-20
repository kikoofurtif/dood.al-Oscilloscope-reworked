import json
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from json_to_audio import convert_json_to_wav, load_strokes


class JsonToAudioTests(unittest.TestCase):
    def write_trace(self, folder: Path, data: object) -> Path:
        path = folder / "trace.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_loads_converter_sample(self) -> None:
        sample = Path(__file__).parents[1] / "test.json"
        strokes = load_strokes(sample)
        self.assertEqual(len(strokes), 1)
        self.assertEqual(len(strokes[0]), 43)

    def test_writes_stereo_pcm_and_preserves_stroke_gap(self) -> None:
        trace_data = {
            "format": "svg-xy-trace-v1",
            "points": [
                {"x": -1, "y": 0, "stroke_id": 0, "pen_down": True},
                {"x": 1, "y": 0, "stroke_id": 0, "pen_down": True, "end_stroke": True},
                {"x": 0, "y": -1, "stroke_id": 1, "pen_down": True},
                {"x": 0, "y": 1, "stroke_id": 1, "pen_down": True, "end_stroke": True},
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            source = self.write_trace(folder, trace_data)
            target = folder / "trace.wav"
            frame_count = convert_json_to_wav(
                source, target, sample_rate=8_000, duration=0.1, amplitude=1, gap_ms=10
            )

            with wave.open(str(target), "rb") as audio:
                self.assertEqual(audio.getnchannels(), 2)
                self.assertEqual(audio.getsampwidth(), 2)
                self.assertEqual(audio.getframerate(), 8_000)
                self.assertEqual(audio.getnframes(), frame_count)
                samples = struct.unpack("<" + "h" * (frame_count * 2), audio.readframes(frame_count))

        # The 80-frame inter-stroke gap should be silent in both channels.
        self.assertEqual(samples[360 * 2:440 * 2], (0,) * (80 * 2))
        self.assertGreater(samples[359 * 2], 32_000)
        self.assertLess(samples[440 * 2 + 1], -32_000)

    def test_rejects_unknown_format(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = self.write_trace(Path(temp_dir), {"format": "unknown", "points": []})
            with self.assertRaisesRegex(ValueError, "Unsupported JSON format"):
                load_strokes(source)

    def test_rejects_non_finite_coordinates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = self.write_trace(Path(temp_dir), {
                "format": "svg-xy-trace-v1",
                "points": [{"x": float("nan"), "y": 0}],
            })
            with self.assertRaisesRegex(ValueError, "non-finite"):
                load_strokes(source)


if __name__ == "__main__":
    unittest.main()
