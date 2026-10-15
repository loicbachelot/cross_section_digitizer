"""Integration checks runnable directly with either QGIS 3 or QGIS 4 Python.

Run with QT_QPA_PLATFORM=offscreen to avoid opening desktop windows.
"""

import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from qgis.core import QgsApplication, QgsProject, Qgis
from qgis.gui import QgsMapCanvas, QgsMessageBar
from qgis.PyQt.QtCore import QPoint, QPointF, Qt, QSettings, QT_VERSION_STR
from qgis.PyQt.QtGui import QWheelEvent
from qgis.PyQt.QtTest import QTest
from qgis.PyQt.QtWidgets import QMainWindow


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT.parent))
plugin_package = importlib.import_module(PLUGIN_ROOT.name)
dock_module = importlib.import_module(
    f'{PLUGIN_ROOT.name}.cross_section_digitizer_dockwidget')


class TestInterface:
    """Minimal interface using real QGIS and Qt widgets."""

    def __init__(self):
        self.window = QMainWindow()
        self.canvas = QgsMapCanvas()
        self.window.setCentralWidget(self.canvas)
        self.message_bar = QgsMessageBar(self.window)

    def mainWindow(self):
        return self.window

    def mapCanvas(self):
        return self.canvas

    def messageBar(self):
        return self.message_bar

    def addToolBar(self, name):
        return self.window.addToolBar(name)

    def addToolBarIcon(self, action):
        pass

    def addPluginToMenu(self, menu, action):
        pass

    def addDockWidget(self, area, widget):
        self.window.addDockWidget(area, widget)

    def removePluginMenu(self, menu, action):
        pass

    def removeToolBarIcon(self, action):
        pass


class QtCompatibilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings_dir = tempfile.TemporaryDirectory()
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          cls.settings_dir.name)
        cls.app = QgsApplication.instance() or QgsApplication([], False)
        cls.app.initQgis()
        print(f'QGIS {Qgis.QGIS_VERSION}, Qt {QT_VERSION_STR}')

    def setUp(self):
        self.iface = TestInterface()
        self.plugin = plugin_package.classFactory(self.iface)
        self.plugin.initGui()
        self.plugin.run()
        self.widget = self.plugin.dockwidget
        self.assertTrue(self.widget.image_viewer.load_image(
            str(PLUGIN_ROOT / 'icon.png')))

    def tearDown(self):
        self.widget.close()
        self.plugin.unload()
        self.iface.window.deleteLater()
        QgsProject.instance().removeAllMapLayers()
        self.app.processEvents()

    def test_plugin_lifecycle_and_icon(self):
        self.assertTrue(self.plugin.pluginIsActive)
        self.assertFalse(self.plugin.actions[0].icon().isNull())
        self.widget.close()
        self.assertFalse(self.plugin.pluginIsActive)
        self.plugin.run()
        self.assertTrue(self.plugin.pluginIsActive)

    def test_digitizing_mouse_button_signal(self):
        viewer = self.widget.image_viewer
        clicks = []
        viewer.mouseClicked.connect(lambda x, y, button: clicks.append(button))
        viewer.toggle_digitize_mode(True)
        position = viewer.view.mapFromScene(viewer.image_item.boundingRect().center())
        QTest.mouseClick(viewer.view.viewport(), Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier, position)
        self.assertEqual(clicks, [Qt.MouseButton.LeftButton])
        viewer.toggle_digitize_mode(False)
        viewer.toggle_digitize_mode(True)

    def test_wheel_zoom_and_orientation(self):
        view = self.widget.image_viewer.view
        event = QWheelEvent(QPointF(20, 20), QPointF(20, 20), QPoint(),
                            QPoint(0, 120), Qt.MouseButton.NoButton,
                            Qt.KeyboardModifier.NoModifier,
                            Qt.ScrollPhase.NoScrollPhase, False)
        scale = view.transform().m11()
        view.wheelEvent(event)
        self.assertGreater(view.transform().m11(), scale)
        self.widget.toggle_orientation()
        self.assertEqual(self.widget.splitter.orientation(), Qt.Orientation.Horizontal)
        self.widget.toggle_orientation()
        self.assertEqual(self.widget.splitter.orientation(), Qt.Orientation.Vertical)

    def test_georeferenced_layers_and_update(self):
        widget = self.widget
        widget.image_path = str(PLUGIN_ROOT / 'icon.png')
        widget.reference_points = {
            'origin': (0, 0), 'x_ref': (100, 0), 'y_ref': (0, 100)}
        widget.spin_origin_x.setValue(0)
        widget.spin_origin_y.setValue(0)
        widget.spin_x_ref.setValue(10)
        widget.spin_y_ref.setValue(-10)
        widget.plot_georef_points = {'start_plot': (0, 0), 'end_plot': (10, 0)}
        widget.spin_start_lon.setValue(-120)
        widget.spin_start_lat.setValue(46)
        widget.spin_end_lon.setValue(-119.9)
        widget.spin_end_lat.setValue(46)
        widget.data_series = {'fault': [(0, -1), (10, -2)]}
        with patch.object(dock_module.QMessageBox, 'information'):
            widget.create_georeferenced_polygon()
            widget.georeference_digitized_points()
            # Exercise the existing-layer branch and its layer-type enum.
            widget.georeference_digitized_points()
        layers = list(QgsProject.instance().mapLayers().values())
        self.assertEqual(len(layers), 2)
        points = next(layer for layer in layers if layer.name() == 'Georeferenced_fault')
        self.assertEqual(points.featureCount(), 2)
        self.assertEqual(points.fields().names(), ['series', 'point_id'])
        polygon = next(layer for layer in layers if layer.name() == 'Cross_Section_Polygon')
        self.assertEqual(polygon.featureCount(), 1)
        self.assertEqual(polygon.fields().names(), ['name', 'image_path'])
        self.assertTrue(next(points.getFeatures()).geometry().constGet().is3D())

    def test_project_load_and_export_with_message_bar(self):
        project = {
            'type': 'cross_section_project',
            'version': '1.0',
            'image': {'path': str(PLUGIN_ROOT / 'icon.png')},
            'coordinate_system': {'reference_points': {
                'origin': {'pixel': [0, 0], 'plot': [0.001, 0]},
                'x_ref': {'pixel': [100, 0], 'value': 10},
                'y_ref': {'pixel': [0, 100], 'value': -10},
            }},
            'georeferencing': {
                'plot_coordinates': {'start_plot': [0, 0], 'end_plot': [10, 0]},
                'geographic_coordinates': {
                    'start': {'longitude': -120, 'latitude': 46, 'elevation': 0},
                    'end': {'longitude': -119.9, 'latitude': 46, 'elevation': 0},
                },
            },
            'data_series': {'active_series': 'fault', 'series': {
                'fault': [[0, -1], [10, -2]],
            }},
        }
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'project.json'
            exported = Path(directory) / 'exported.json'
            source.write_text(json.dumps(project))
            with patch.object(dock_module.QFileDialog, 'getOpenFileName',
                              return_value=(str(source), '')), \
                    patch.object(dock_module.QMessageBox, 'question',
                                 return_value=dock_module.QMessageBox.StandardButton.Yes), \
                    patch.object(dock_module.QMessageBox, 'information'), \
                    patch.object(dock_module.QMessageBox, 'warning') as warning, \
                    patch.object(dock_module.QMessageBox, 'critical') as critical:
                self.widget.load_project()
                critical.assert_not_called()
                warning.assert_not_called()
                # Both informational and success messages use a real QgsMessageBar.
                self.widget._handle_geo_coordinate_result('start', -120, 46, None)
                critical.assert_not_called()
            self.assertIsNotNone(self.iface.message_bar.currentItem())
            self.assertEqual(self.widget.data_series, project['data_series']['series'])
            self.assertEqual(self.widget.current_series, 'fault')
            self.assertEqual(self.widget.reference_points['x_ref'], (100, 0))
            with patch.object(dock_module.QFileDialog, 'getSaveFileName',
                              return_value=(str(exported), '')), \
                    patch.object(dock_module.QMessageBox, 'information'), \
                    patch.object(dock_module.QMessageBox, 'critical') as critical:
                self.widget.export_project()
                critical.assert_not_called()
            result = json.loads(exported.read_text())
            self.assertEqual(result['data_series'], project['data_series'])
            self.assertEqual(result['georeferencing'], project['georeferencing'])


if __name__ == '__main__':
    unittest.main()
