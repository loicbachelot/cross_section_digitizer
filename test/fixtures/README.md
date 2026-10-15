# Cross-section project fixture

`long_a_aprime.json` derives from the project supplied for the MHT/Bhutan
cross-section regression. It retains all three image control points, both
geographic endpoints, the active series, and all 11 digitized points.
The creation timestamp was removed and the machine-specific image path replaced
with `cross_section.png`.

Tests create a blank PNG at the original 2193 by 566 pixel dimensions in a temporary
directory and write a temporary copy of the JSON pointing to it. The original
figure is not included or required. The fixture's `version: "1.0"` describes the
project file format, independently of the plugin release version.

`long_a_aprime_expected.json` contains fixed numeric expectations calculated
independently of the plugin:

- PROJ's `pyproj.Geod(a=6371000, b=6371000)` produced geographic point positions
  and polygon corners on a spherical Earth, matching the plugin's documented
  6371 km radius. This is a reference calculation, not a requirement to install
  pyproj to run the tests.
- Python decimal arithmetic produced the expected pixel coordinates from the
  saved section coordinates and control points.
- Geographic coordinates use a tolerance of `1e-8` degrees, elevations `1e-6`
  meters, and image coordinates `1e-8` pixels.

These expectations preserve the current coordinate model: section X is distance
in kilometers from the geographic start at X=0, and section Z is elevation in
kilometers converted to meters. The test deliberately includes the point beyond
the section endpoint and negative elevations. It checks numerical behavior;
it does not establish the geological accuracy of the interpretation or change
the projection to an ellipsoidal Earth model.
