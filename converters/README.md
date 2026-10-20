# Oscilloscope converters

This folder contains two separate converters. Use the individual guide for
full instructions:

- [SVG to CSV/JSON guide](svg_to_json/README.md) — convert SVG paths into
  ordered XY points.
- [JSON to WAV guide](json_to_audio/README.md) — convert an XY JSON trace into
  stereo audio.

The SVG converter's JSON output can also be loaded into the browser
[oscilloscope](../oscilloscope.html) for continuous playback.

## Python environment

Both tools use the virtual environment at `.venv` in this folder. Create it
and install the SVG converter dependency with:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\svg_to_json\requirements.txt
```

`json_to_audio.py` itself uses only the Python standard library.
