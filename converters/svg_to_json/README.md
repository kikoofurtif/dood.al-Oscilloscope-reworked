# SVG to CSV/JSON converter

`svg_xy.py` samples visible SVG path outlines and converts them into ordered,
normalized oscilloscope coordinates. It writes both CSV and JSON files.

## Requirements

- Python 3.10 or newer
- `svgpathtools`

From the `converters` folder, install the dependency into its `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\svg_to_json\requirements.txt
```

If you have not created the environment yet, see the
[converters setup guide](../README.md#python-environment).

## Basic use

Run commands from the `converters` folder:

```powershell
.\.venv\Scripts\python.exe .\svg_to_json\svg_xy.py .\drawing.svg
```

This creates `drawing.csv` and `drawing.json` next to the input. The JSON
format is `svg-xy-trace-v1`; it includes metadata and ordered points with
`x`, `y`, and stroke markers. Coordinates are scaled to approximately
`[-1, 1]`, preserve the SVG viewBox aspect ratio, and have Y inverted for
conventional oscilloscope orientation.

Choose another output basename:

```powershell
.\.venv\Scripts\python.exe .\svg_to_json\svg_xy.py .\drawing.svg -o .\output\shape
```

## Options

```text
-o, --output PATH         Output base path (input name by default)
--spacing VALUE           Approximate point spacing in SVG units (default 1.5)
--min-points COUNT        Minimum samples per path (default 24)
--padding FRACTION        Border fraction (default 0.08; limited to 0–0.45)
--include-unpainted       Also trace paths with stroke="none"
--js                      Write optional experimental JavaScript expressions
--js-max-points COUNT     Point limit for those expressions (default 500)
```

Smaller spacing and a larger minimum point count capture more curve detail,
but produce larger output:

```powershell
.\.venv\Scripts\python.exe .\svg_to_json\svg_xy.py .\drawing.svg --spacing 0.7 --min-points 40
```

To inspect all command-line arguments:

```powershell
.\.venv\Scripts\python.exe .\svg_to_json\svg_xy.py --help
```

## SVG preparation tips

1. Use a vector editor such as Inkscape and convert text to paths.
2. Prefer SVG files with a `viewBox` and visible strokes.
3. This tool follows path outlines/centerlines; it does not fill solid shapes.
4. Each separate SVG path becomes a separate stroke.

## Use the JSON in the browser oscilloscope

Open [`../../oscilloscope.html`](../../oscilloscope.html), choose the generated
JSON under **JSON points**, enable **Use loaded trace**, then enable **SIGNAL
GENERATOR**. The trace loops continuously; **Loop seconds** and **Playback
speed** control its timing.

The browser XY generator cannot blank its beam. Multiple SVG strokes will
therefore be joined by visible lines.
