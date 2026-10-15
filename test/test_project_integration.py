"""End-to-end project regressions derived from the supplied MHT cross-section."""

import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from qgis.core import QgsProject
from qgis.PyQt.QtCore import QPointF, Qt
from qgis.PyQt.QtGui import QColor, QImage
from qgis.PyQt.QtTest import QTest

from integration_support import IntegrationTestCase, PLUGIN_ROOT, dock_module


class ProjectIntegrationTest(IntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        fixtures = PLUGIN_ROOT / 'test' / 'fixtures'
        self.project = json.loads((fixtures / 'long_a_aprime.json').read_text())
        self.expected = json.loads((fixtures / 'long_a_aprime_expected.json').read_text())
        self.image_path = self.root / self.project['image']['path']
        # The geographic regression uses original coordinates, not copyrighted pixels.
        image = QImage(self.project['image']['width'], self.project['image']['height'],
                       QImage.Format.Format_RGB32)
        image.fill(QColor('white'))
        self.assertTrue(image.save(str(self.image_path)))
        self.project['image']['path'] = str(self.image_path)
        self.series_name = self.project['data_series']['active_series']
        self.points = self.project['data_series']['series'][self.series_name]
        self.dialogs = {}
        for name in ('information', 'warning', 'critical', 'question'):
            patcher = patch.object(dock_module.QMessageBox, name)
            self.dialogs[name] = patcher.start()
            self.addCleanup(patcher.stop)
        self.dialogs['question'].return_value = dock_module.QMessageBox.StandardButton.Yes

    def tearDown(self):
        try:
            # Methods catch exceptions and display dialogs: a lack of raised
            # exceptions alone would let failed imports/exports pass unnoticed.
            self.dialogs['critical'].assert_not_called()
            self.dialogs['warning'].assert_not_called()
        finally:
            super().tearDown()

    def load_project(self, data=None):
        path = self.root / 'project.json'
        path.write_text(json.dumps(self.project if data is None else data))
        with patch.object(dock_module.QFileDialog, 'getOpenFileName',
                          return_value=(str(path), '')):
            self.widget.btn_load_project.click()

    def export_project(self, name='exported.json'):
        path = self.root / name
        with patch.object(dock_module.QFileDialog, 'getSaveFileName',
                          return_value=(str(path), '')):
            self.widget.btn_export_project.click()
        return json.loads(path.read_text())

    def snapshot(self):
        return {
            'reference_points': copy.deepcopy(self.widget.reference_points),
            'plot_georef_points': copy.deepcopy(self.widget.plot_georef_points),
            'series': copy.deepcopy(self.widget.data_series),
            'active': self.widget.current_series,
            'image': self.widget.image_path,
            'scene_items': len(self.widget.image_viewer.scene.items()),
        }

    def assert_coordinates(self, actual, expected):
        self.assertAlmostEqual(actual[0], expected[0], delta=1e-8)
        self.assertAlmostEqual(actual[1], expected[1], delta=1e-8)
        self.assertAlmostEqual(actual[2], expected[2], delta=1e-6)

    def test_load_restores_all_project_state(self):
        self.load_project()
        self.assertEqual(self.widget.image_path, str(self.image_path))
        self.assertEqual(self.widget.image_viewer.get_image_size(), (2193, 566))
        for name, control in self.project['coordinate_system']['reference_points'].items():
            self.assertEqual(self.widget.reference_points[name], tuple(control['pixel']))
        self.assertEqual(self.widget.plot_georef_points, {
            key: tuple(value) for key, value in
            self.project['georeferencing']['plot_coordinates'].items()})
        self.assertEqual(self.widget.data_series, {self.series_name: self.points})
        self.assertEqual(self.widget.current_series, self.series_name)
        self.assertEqual(self.widget.combo_series.currentText(), self.series_name)
        self.assertEqual(self.widget.list_points.count(), 11)
        self.assertEqual(len(self.widget.image_viewer.reference_markers), 3)
        self.assertEqual(len(self.widget.image_viewer.georef_markers), 2)
        self.assertEqual(len(self.widget.image_viewer.series_markers[self.series_name]), 11)
        self.assertIsNotNone(self.iface.message_bar.currentItem())
        self.assertIsNotNone(self.widget.image_viewer.coordinate_transform_callback)

    def test_export_and_reload_preserve_every_coordinate(self):
        self.load_project()
        exported = self.export_project()
        for key in ('type', 'version', 'image', 'coordinate_system',
                    'georeferencing', 'data_series'):
            self.assertEqual(exported[key], self.project[key], key)
        self.widget.btn_clear_project.click()
        self.load_project(exported)
        reexported = self.export_project('reexported.json')
        for key in ('coordinate_system', 'georeferencing', 'data_series'):
            self.assertEqual(reexported[key], exported[key], key)

    def test_pixel_section_transforms_against_independent_values(self):
        self.load_project()
        for plot, pixel in zip(self.points, self.expected['points_pixel']):
            with self.subTest(plot=plot):
                transformed = self.widget.pixel_to_plot_coords(*pixel)
                self.assertAlmostEqual(transformed[0], plot[0], delta=1e-9)
                self.assertAlmostEqual(transformed[1], plot[1], delta=1e-9)
                inverse = self.widget.plot_to_pixel_coords(*plot)
                self.assertAlmostEqual(inverse[0], pixel[0], delta=1e-8)
                self.assertAlmostEqual(inverse[1], pixel[1], delta=1e-8)

    def test_georeferenced_point_values_and_layer_update(self):
        self.load_project()
        self.widget.georeference_digitized_points()
        layers = QgsProject.instance().mapLayersByName(f'Georeferenced_{self.series_name}')
        self.assertEqual(len(layers), 1)
        layer = layers[0]
        self.assertTrue(layer.isValid())
        self.assertEqual(layer.crs().authid(), 'EPSG:4326')
        self.assertEqual(layer.featureCount(), 11)
        self.assertEqual(layer.fields().names(), ['series', 'point_id'])
        features = sorted(layer.getFeatures(), key=lambda feature: feature['point_id'])
        for index, (feature, expected) in enumerate(
                zip(features, self.expected['points_geographic']), start=1):
            point = feature.geometry().constGet()
            self.assertTrue(point.is3D())
            self.assertEqual(feature['series'], self.series_name)
            self.assertEqual(feature['point_id'], index)
            self.assert_coordinates((point.x(), point.y(), point.z()), expected)
        # Replace rather than append features when data are exported again.
        self.widget.data_series[self.series_name] = self.points[:3]
        self.widget.georeference_digitized_points()
        self.assertEqual(layer.featureCount(), 3)
        self.assertEqual(len(QgsProject.instance().mapLayers()), 1)

    def test_polygon_extent_and_image_attribute(self):
        self.load_project()
        self.widget.create_georeferenced_polygon()
        layers = QgsProject.instance().mapLayersByName('Cross_Section_Polygon')
        self.assertEqual(len(layers), 1)
        layer = layers[0]
        self.assertEqual(layer.crs().authid(), 'EPSG:4326')
        self.assertEqual(layer.featureCount(), 1)
        feature = next(layer.getFeatures())
        self.assertEqual(feature['image_path'], str(self.image_path))
        self.assertEqual(feature['name'], 'Cross_Section')
        geometry = feature.geometry()
        self.assertTrue(geometry.constGet().is3D())
        vertices = list(geometry.vertices())
        self.assertEqual(len(vertices), 5)
        for point, expected in zip(vertices, self.expected['polygon_corners_geographic']):
            self.assert_coordinates((point.x(), point.y(), point.z()), expected)

    def test_csv_contains_every_original_point(self):
        self.load_project()
        path = self.root / 'series.csv'
        with patch.object(dock_module.QFileDialog, 'getSaveFileName',
                          return_value=(str(path), '')):
            self.widget.save_series_to_file()
        with path.open(newline='') as stream:
            rows = list(csv.reader(stream))
        self.assertEqual(rows[0], ['X', 'Y'])
        self.assertEqual([[float(value) for value in row] for row in rows[1:]], self.points)

    def test_reloading_does_not_duplicate_markers(self):
        self.load_project()
        before = self.snapshot()
        self.load_project()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(len(self.widget.image_viewer.series_markers[self.series_name]), 11)

    def test_replacing_project_clears_absent_data(self):
        self.load_project()
        replacement = copy.deepcopy(self.project)
        replacement['coordinate_system'] = None
        replacement['georeferencing'] = None
        replacement['data_series'] = None
        self.load_project(replacement)
        self.assertEqual(self.widget.reference_points, {})
        self.assertEqual(self.widget.plot_georef_points, {})
        self.assertEqual(self.widget.data_series, {})
        self.assertIsNone(self.widget.current_series)
        self.assertEqual(self.widget.combo_series.count(), 0)
        self.assertEqual(self.widget.list_points.count(), 0)
        self.assertEqual(self.widget.image_viewer.series_markers, {})
        self.assertIsNone(self.widget.image_viewer.coordinate_transform_callback)

    def test_multiple_series_restore_selection_and_create_separate_layers(self):
        self.load_project()
        multiple = copy.deepcopy(self.project)
        multiple['data_series']['series']['second_fault'] = self.points[3:6]
        multiple['data_series']['active_series'] = 'second_fault'
        self.load_project(multiple)
        self.assertEqual(self.widget.combo_series.count(), 2)
        self.assertEqual(self.widget.current_series, 'second_fault')
        self.assertEqual(self.widget.list_points.count(), 3)
        self.assertEqual(len(self.widget.image_viewer.series_markers[self.series_name]), 11)
        self.assertEqual(len(self.widget.image_viewer.series_markers['second_fault']), 3)
        self.widget.georeference_digitized_points()
        layers = list(QgsProject.instance().mapLayers().values())
        self.assertEqual(sorted(layer.featureCount() for layer in layers), [3, 11])
        self.widget.combo_series.setCurrentText(self.series_name)
        self.assertEqual(self.widget.current_series, self.series_name)
        self.assertEqual(self.widget.list_points.count(), 11)

    def test_incomplete_reference_points_leave_coordinate_tracking_disabled(self):
        incomplete = copy.deepcopy(self.project)
        del incomplete['coordinate_system']['reference_points']['x_ref']
        self.load_project(incomplete)
        self.assertEqual(len(self.widget.reference_points), 2)
        self.assertIsNone(self.widget.image_viewer.coordinate_transform_callback)
        self.assertIn('Reference points incomplete',
                      self.dialogs['information'].call_args.args[2])

    def test_add_and_delete_point_after_clear_and_reload(self):
        self.load_project()
        self.widget.btn_clear_project.click()
        self.load_project()
        before = len(self.widget.data_series[self.series_name])
        self.widget.btn_digitize_points.click()
        viewer = self.widget.image_viewer
        position = viewer.view.mapFromScene(QPointF(500, 250))
        QTest.mouseClick(viewer.view.viewport(), Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier, position)
        self.assertEqual(len(self.widget.data_series[self.series_name]), before + 1)
        self.widget.list_points.setCurrentRow(before)
        self.widget.delete_selected_point()
        self.assertEqual(len(self.widget.data_series[self.series_name]), before)

    def test_cancelled_load_leaves_project_unchanged(self):
        self.load_project()
        before = self.snapshot()
        self.dialogs['question'].return_value = dock_module.QMessageBox.StandardButton.No
        self.load_project()
        self.assertEqual(self.snapshot(), before)
        with patch.object(dock_module.QFileDialog, 'getOpenFileName', return_value=('', '')):
            self.widget.btn_load_project.click()
        self.assertEqual(self.snapshot(), before)

    def test_invalid_json_reports_error_without_changing_project(self):
        self.load_project()
        before = self.snapshot()
        path = self.root / 'broken.json'
        path.write_text('{broken')
        with patch.object(dock_module.QFileDialog, 'getOpenFileName',
                          return_value=(str(path), '')):
            self.widget.btn_load_project.click()
        self.dialogs['critical'].assert_called_once()
        self.assertIn('Failed to load project', self.dialogs['critical'].call_args.args[2])
        self.dialogs['critical'].reset_mock()
        self.assertEqual(self.snapshot(), before)

    def test_wrong_project_type_reports_warning(self):
        self.load_project()
        before = self.snapshot()
        self.load_project({'type': 'unrelated_data'})
        self.dialogs['warning'].assert_called_once()
        self.assertIn('Invalid project file format', self.dialogs['warning'].call_args.args[2])
        self.dialogs['warning'].reset_mock()
        self.assertEqual(self.snapshot(), before)

    def test_missing_image_does_not_partially_replace_project(self):
        self.load_project()
        before = self.snapshot()
        missing = copy.deepcopy(self.project)
        missing['image']['path'] = str(self.root / 'missing.png')
        missing['coordinate_system']['reference_points']['origin']['pixel'] = [1, 2]
        self.load_project(missing)
        self.dialogs['warning'].assert_called_once()
        self.assertIn('not found', self.dialogs['warning'].call_args.args[2])
        self.dialogs['warning'].reset_mock()
        self.assertEqual(self.snapshot(), before)

    def test_unreadable_image_does_not_partially_replace_project(self):
        self.load_project()
        before = self.snapshot()
        path = self.root / 'invalid.png'
        path.write_text('This is not a PNG image.')
        invalid = copy.deepcopy(self.project)
        invalid['image']['path'] = str(path)
        self.load_project(invalid)
        self.dialogs['warning'].assert_called_once()
        self.assertIn('Failed to load image', self.dialogs['warning'].call_args.args[2])
        self.dialogs['warning'].reset_mock()
        self.assertEqual(self.snapshot(), before)


if __name__ == '__main__':
    unittest.main()
