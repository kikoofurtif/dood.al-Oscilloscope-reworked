# JSON XY trace to WAV converter

`json_to_audio.py` converts an `svg-xy-trace-v1` point-trace JSON file into
stereo PCM WAV audio. The left channel carries X and the right channel carries
Y. The output can be routed to a stereo hardware XY oscilloscope input.

The converter uses only the Python standard library; it does not need
`svgpathtools` or an audio package.

## Run it

Commands below assume the working directory is the `converters` folder:

```powershell
.\.venv\Scripts\python.exe .\json_to_audio\json_to_audio.py .\test.json
```

This writes `test.wav` next to the JSON. Defaults: 48 kHz, 5 seconds,
amplitude 0.8, and 20 ms of silence between separate strokes.

Choose an output file and adjust playback parameters:

```powershell
.\.venv\Scripts\python.exe .\json_to_audio\json_to_audio.py .\test.json `
  --duration 3 --sample-rate 48000 --amplitude 0.8 --gap-ms 20 `
  --output .\output\test.wav
```

## Options

```text
-o, --output PATH        Output WAV path (default: JSON path with .wav suffix)
--sample-rate HZ         8000–192000 Hz (default 48000)
--duration SECONDS       0.05–600 seconds (default 5)
--amplitude LEVEL        Greater than 0 and at most 1 (default 0.8)
--gap-ms MILLISECONDS    Silence between strokes, 0–1000 ms (default 20)
```

Display all options:

```powershell
.\.venv\Scripts\python.exe .\json_to_audio\json_to_audio.py --help
```

Each stroke is linearly resampled to fit the requested total duration. Silence
is inserted between strokes, but zero volts is generally the center of an XY
display; the WAV cannot blank the beam without hardware support.

## Tests

`test_json_to_audio.py` checks the WAV converter, including output channels,
sample rate, duration, stroke gaps, and handling of invalid trace data. It is
only a test and does not process or alter real input files. Run from the
`converters` folder:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s .\json_to_audio -v
```

For continuous browser-based playback instead of a WAV file, use the JSON
player in [`../../oscilloscope.html`](../../oscilloscope.html).
