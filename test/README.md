# Integration tests

Run the maintained integration suite from the repository root:

```bash
python3 scripts/run_integration_tests.py
```

Use Python configured for QGIS. On Linux this is usually the system Python after
installing QGIS and its Python bindings; on Windows use the QGIS/OSGeo4W shell.
The runner uses `unittest` and requires no additional test framework.

On macOS, any Python 3 can launch the Python bundled with QGIS:

```bash
python3 scripts/run_integration_tests.py --qgis-app /Applications/QGIS.app
python3 scripts/run_integration_tests.py --qgis-app /Applications/QGIS-final-4_2_3.app
```

Use your installed bundle paths. The runner supports the two bundle layouts
tested here: QGIS 3.40.1/Python 3.9 and QGIS 4.2.3/Python 3.12. With other macOS
bundle layouts, use a QGIS-configured Python environment directly.
Add `--expected-qt-major 5` or `--expected-qt-major 6` to catch accidental use
of a different runtime. Every run prints its QGIS and Qt versions.

The Makefile runs the same suite and propagates failures:

```bash
make test TEST_ARGS="--qgis-app /Applications/QGIS.app --expected-qt-major 5"
```

The runner sets up temporary settings/profile/cache directories before importing
QGIS and uses Qt's `offscreen` platform. It does not install the plugin, modify
the desktop QGIS profile, or edit the original research files. It exits nonzero
when any test fails or the runtime is missing or incorrect.

## Coverage

- `test_qt_compatibility.py`: factory and dock lifecycle, icon, mouse-button
  signals, zoom, orientation, message bars, and basic 3D layer creation.
- `test_project_integration.py`: the supplied project fixture, complete state
  restoration, JSON round trips, CSV output, numeric coordinate transforms,
  3D points and polygon corners, layer updates, repeated loads, project
  replacement, digitizing after clearing, and failed/cancelled imports.

Tests use real QGIS layers, canvas, message bar, Qt widgets, and mouse events.
The small interface adapter replaces QGIS's main application interface. Modal
dialogs are answered automatically; file choosers receive temporary paths.
Unexpected warning/error dialogs fail the project tests, including errors that
the plugin catches instead of raising.

See [fixture provenance and numeric expectations](fixtures/README.md). Fixtures
are kept in the repository and are not shipped in the plugin ZIP. The runner
selects only the maintained suites; older Plugin Builder scaffold tests remain
outside this runner.

## Continuous integration

The QGIS Integration Tests GitHub workflow runs on pushes and pull requests,
using official QGIS Docker images for Qt5 (`ltr-noble`) and Qt6 (`stable-trixie`).
Runtime assertions prevent a moving image tag from silently testing a different
Qt major version. The release workflow also calls these tests and waits for
both jobs before packaging and attaching its ZIP. Docker jobs need their first
GitHub run to verify the Linux environment; local validation uses the installed
macOS QGIS applications.

Offscreen tests verify behavior and data, not visual layout. Review the panel
interactively in QGIS when changing its appearance.
