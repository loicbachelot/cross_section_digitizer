"""Integration checks runnable directly with either QGIS 3 or QGIS 4 Python.

Shared setup for the integration suites. Use scripts/run_integration_tests.py.
"""

import importlib
from pathlib import Path
import sys
import tempfile
import unittest

from qgis.core import QgsApplication, QgsProject, Qgis
from qgis.gui import QgsMapCanvas, QgsMessageBar
from qgis.PyQt.QtCore import QSettings, QT_VERSION_STR
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


class IntegrationTestCase(unittest.TestCase):
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
