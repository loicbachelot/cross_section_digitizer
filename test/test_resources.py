# coding=utf-8
"""Resources test.

.. note:: This program is free software; you can redistribute it and/or modify
     it under the terms of the GNU General Public License as published by
     the Free Software Foundation; either version 2 of the License, or
     (at your option) any later version.

"""

__author__ = 'crescentcfm@cascadiaquakes.org'
__date__ = '2025-06-18'
__copyright__ = 'Copyright 2025, Cascadia Regional Earthquake Science Center (CRESCENT)'

import unittest
from pathlib import Path

from qgis.PyQt.QtGui import QIcon



class CrossSectionDigitizerDialogTest(unittest.TestCase):
    """Test rerources work."""

    def setUp(self):
        """Runs before each test."""
        pass

    def tearDown(self):
        """Runs after each test."""
        pass

    def test_icon_png(self):
        """Test we can click OK."""
        path = Path(__file__).resolve().parents[1] / 'icon.png'
        icon = QIcon(str(path))
        self.assertFalse(icon.isNull())

if __name__ == "__main__":
    unittest.main()



