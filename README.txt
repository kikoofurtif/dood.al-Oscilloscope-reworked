OSCILLOSCOPE - IMPROVED VERSION
==============================

INTRODUCTION
------------

Hello and welcome!

This project is a locally adapted version of Dood.al Oscilloscope:
https://dood.al/oscilloscope/

It keeps the original oscilloscope experience while fixing problems found in
the saved local copy and adding tools to create, load, and convert XY traces.

The project was developed using my own knowledge and with assistance from
Copilot SDK in Visual Studio Code.


FEATURES
--------

1. Fixes and improvements

- Fixed the JavaScript file path in the local HTML page. The saved page had an
  incorrectly encoded script filename, which caused a 404 and prevented the
  oscilloscope code, including its signal generator, from loading.
- Removed the missing noise.jpg image request. The oscilloscope now generates
  its background texture locally; no noise.jpg file is required.
- Fixed startup behavior so the first page click does not fail when the
  optional clicktostart element is absent.

2. JSON point reader

The signal generator can load an SVG XY trace in the svg-xy-trace-v1 JSON
format. It interpolates between points and plays the trace continuously in a
loop. Use the Loop seconds field and Playback speed slider to adjust playback
timing; the speed multiplier ranges from 0.25x to 10x.

The XY display cannot lift or blank its beam, so separate SVG strokes and the
end-to-start loop transition can appear as connecting lines.

3. Converters

- SVG-to-JSON converter: svg_xy.py samples visible SVG paths and exports
  ordered coordinates to both CSV and JSON.
- JSON-to-WAV converter: json_to_audio.py converts an svg-xy-trace-v1 JSON
  file into stereo PCM WAV audio, with X in the left channel and Y in the
  right channel.

Each converter has its own README.md guide in its folder. The test file for
json_to_audio.py runs checks; it is not required for normal conversion.


DOCUMENTATION
-------------

- Converter overview and shared Python setup: converters/README.md
- SVG-to-JSON usage: converters/svg_to_json/README.md
- JSON-to-WAV usage and tests: converters/json_to_audio/README.md


INSTALLATION AND USAGE
----------------------

1. Open oscilloscope.html in a modern web browser. Keep the dependencies
   folder beside the HTML file; it contains the JavaScript the page loads.
2. To create a JSON trace from an SVG, follow the setup and commands in
   converters/svg_to_json/README.md.
3. To create a WAV file from a JSON trace, follow the instructions in
   converters/json_to_audio/README.md.
4. To view a JSON trace in the browser oscilloscope, open oscilloscope.html,
   choose the JSON file in the SIGNAL GENERATOR section, enable Use loaded
   trace, then enable SIGNAL GENERATOR.

The Python tools use the virtual environment and dependency instructions
described in the converter documentation. The browser oscilloscope itself
does not require installing Python packages.


TECHNOLOGIES AND TOOLS
----------------------

- HTML, CSS, and JavaScript: oscilloscope interface and functionality.
- Python and svgpathtools: SVG path conversion.
- JSON and CSV: ordered XY point data and metadata.
- WAV: stereo audio output for XY oscilloscope inputs.
- Visual Studio Code and Copilot SDK: development environment and coding
  assistance.


PROJECT GOAL
------------

The goal is to provide a more versatile local version of the oscilloscope by
adding tools that convert vector drawings into XY coordinates and turn point
data into audio. JSON traces can also be loaded directly into the browser
oscilloscope for continuous XY playback.

The project may evolve with new features, interface improvements, and broader
support for data formats.


ACKNOWLEDGEMENTS
----------------

Thanks to the creators of Dood.al Oscilloscope for the original project,
which serves as the foundation for this local adaptation:
https://dood.al/oscilloscope/

Thanks as well to the development and assistance tools used throughout the
project.
