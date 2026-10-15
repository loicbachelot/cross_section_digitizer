"""Run the QGIS integration suites with isolated settings and an offscreen UI."""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def bundle_environment(bundle, environment):
    """Configure Python shipped by either supported macOS QGIS bundle layout."""
    contents = bundle.resolve() / 'Contents'
    modern = contents / 'MacOS' / 'python3.12'
    if modern.is_file():
        executable = modern
        environment['PYTHONHOME'] = str(contents / 'Frameworks')
        python_path = contents / 'Resources' / 'qgis' / 'python'
        proj_path = contents / 'Resources' / 'qgis' / 'proj'
    else:
        executables = sorted((contents / 'MacOS' / 'bin').glob('python3.[0-9]*'))
        executables = [path for path in executables if '-' not in path.name]
        if not executables:
            raise ValueError(f'Cannot find a QGIS Python interpreter in {bundle}')
        executable = executables[-1]
        environment.pop('PYTHONHOME', None)
        python_path = contents / 'Resources' / 'python'
        proj_path = contents / 'Resources' / 'proj'
    environment['PYTHONPATH'] = str(python_path)
    environment['QT_QPA_PLATFORM_PLUGIN_PATH'] = str(contents / 'PlugIns' / 'platforms')
    environment['PROJ_DATA'] = str(proj_path)
    environment['PROJ_LIB'] = str(proj_path)
    return executable


def run_suites(expected_qt_major):
    try:
        from qgis.PyQt.QtCore import QT_VERSION_STR
    except ImportError as error:
        print(f'QGIS Python is required: {error}\n'
              'Use a QGIS-configured Python shell or --qgis-app /path/to/QGIS.app.',
              file=sys.stderr)
        return 2
    if expected_qt_major and int(QT_VERSION_STR.split('.')[0]) != expected_qt_major:
        print(f'Expected Qt {expected_qt_major}, found Qt {QT_VERSION_STR}.', file=sys.stderr)
        return 2
    sys.path.insert(0, str(ROOT / 'test'))
    suite = unittest.defaultTestLoader.loadTestsFromNames([
        'test_qt_compatibility', 'test_project_integration'])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qgis-app', type=Path, help='macOS QGIS application bundle')
    parser.add_argument('--expected-qt-major', type=int, choices=(5, 6),
                        help='Fail if the runtime uses another Qt major version')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        return run_suites(args.expected_qt_major)

    environment = os.environ.copy()
    environment['QT_QPA_PLATFORM'] = 'offscreen'
    environment['PYTHONNOUSERSITE'] = '1'
    executable = Path(sys.executable)
    if args.qgis_app:
        try:
            executable = bundle_environment(args.qgis_app, environment)
        except ValueError as error:
            parser.error(str(error))
    elif sys.platform.startswith('linux'):
        qgis_python = Path('/usr/share/qgis/python')
        if qgis_python.is_dir():
            environment['PYTHONPATH'] = os.pathsep.join(filter(None, [
                str(qgis_python), environment.get('PYTHONPATH')]))

    with tempfile.TemporaryDirectory(prefix='digitizer-integration-') as directory:
        # Set before importing QGIS/Qt. Never use the user's QGIS profile.
        environment['QGIS_CUSTOM_CONFIG_PATH'] = directory + os.sep
        environment['XDG_CONFIG_HOME'] = directory
        environment['XDG_CACHE_HOME'] = directory
        environment['XDG_RUNTIME_DIR'] = directory
        command = [str(executable), str(Path(__file__).resolve()), '--worker']
        if args.expected_qt_major:
            command.extend(['--expected-qt-major', str(args.expected_qt_major)])
        return subprocess.run(command, cwd=ROOT, env=environment).returncode


if __name__ == '__main__':
    raise SystemExit(main())
