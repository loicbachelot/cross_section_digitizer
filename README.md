# Cross-Section Digitizer

CrossSectionDigitizer is a QGIS plugin for extracting spatial data from geological
cross-sections, depth-migrated seismic sections, and other vertical images. It
transforms image pixels into section coordinates (distance and depth or elevation)
and geographic coordinates (longitude, latitude, and elevation).

Use it to digitize faults, horizons, and other subsurface features; export data
series as CSV or georeferenced 3D point layers; and create a 3D polygon representing
the cross-section image extent. Project settings, control points, and digitized
data can be saved to JSON and restored in a later session.

## Installation

Version 1.1.0 supports QGIS 3.40.1 through QGIS 4.x. Integration checks have
passed on QGIS 3.40.1 with Qt5 and QGIS 4.2.3 with Qt6.

Download the plugin ZIP from the
[GitHub releases page](https://github.com/cascadiaquakes/cross_section_digitizer/releases).
In QGIS, open **Plugins > Manage and Install Plugins > Install from ZIP**, select
the downloaded ZIP, and install it. Enable CrossSectionDigitizer if necessary.
The plugin uses the QGIS Python environment and requires no additional Python
packages.

## Basic workflow

1. Open Cross-Section Digitizer from the Plugins menu or its toolbar icon and
   load a cross-section image.
2. Define an origin and reference points for the horizontal and vertical section
   axes, enter their values, and validate the plot coordinates. Use positive-up
   elevation values when the original image labels positive-down depths.
3. In the Georeference tab, tie two points on the section to known geographic
   locations, entering their coordinates and elevations or selecting their
   locations on the QGIS map. Create a georeferenced polygon to represent the
   image extent.
4. In the Digitize tab, create a named data series and click points along a fault,
   horizon, or other feature. Export the series as CSV or use **Georeference
   Digitized Points** to create 3D point layers in QGIS.
5. Use **Export Project** to save the digitizing session as JSON. Save generated
   QGIS layers separately if you want to preserve them as files.

The [step-by-step tutorial](https://cascadiaquakes.github.io/fault-geometry-building-tutorial/QGIS_plugin.html)
includes example cross-section images, control-point setup, digitizing, and a
complete workflow for building 3D fault surfaces.

## Related tools

This plugin is part of CRESCENT's tools for constructing complex 3D fault
geometries. Two optional companion plugins extend the workflow:

- [CRESCENT's modified Qgis2threejs](https://github.com/cascadiaquakes/Qgis2threejs)
  displays georeferenced cross-section images alongside other 3D geospatial data.
- [Contours2Mesh](https://github.com/cascadiaquakes/cfm-qgis-contours2mesh)
  builds triangular fault-surface meshes from contours drawn using the digitized
  cross-section data and other geological constraints.

Neither companion plugin is required for CrossSectionDigitizer's digitizing and
georeferencing functions.

## Support and source code

- [Source code](https://github.com/cascadiaquakes/cross_section_digitizer)
- [Report an issue](https://github.com/cascadiaquakes/cross_section_digitizer/issues)
- Contact: crescentcfm@cascadiaquakes.org

## Releases

The current version is 1.1.0. Release tags use the matching `v1.1.0` format.
Before creating a release, update `version` and `changelog` in `metadata.txt`
and the version references in this README. The documentation reads its version
from the metadata automatically. The release workflow checks that the tag matches
the metadata before building and attaching the plugin ZIP.

## Licensing

Original CRESCENT contributions are available under the
[BSD 3-Clause License](LICENSE.md), except where a file states otherwise.
Plugin Builder-derived files and several test files retain their existing GPL
notices. Those notices continue to apply; the BSD license does not replace them.

See [LICENSE_NOTICES.txt](LICENSE_NOTICES.txt) for license scope, attribution,
and dependency information. Copies of [GPLv2](COPYING.GPL-2.0.txt) and
[GPLv3](COPYING.GPL-3.0.txt) are included with the plugin.

QGIS and PyQt are separately installed dependencies and retain their own
licenses. BSD 3-Clause is GPL-compatible; use with these dependencies remains
subject to the applicable GPL terms.

Original CRESCENT contributions copyright CRESCENT, 2025 onward.
Other copyright notices are retained in the relevant files.
