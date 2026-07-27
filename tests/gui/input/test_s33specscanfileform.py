"""
Copyright (c) 2017, UChicago Argonne, LLC
See LICENSE file.
"""

import sys
import unittest

import PySide6.QtWidgets as qtWidgets

from rsMap3D.config.rsmap3dconfigparser import RSMap3DConfigParser
from rsMap3D.gui.input.s33specscanfileform import S33SpecScanFileForm

app = qtWidgets.QApplication.instance() or qtWidgets.QApplication(sys.argv)


class TestS33SpecScanFileForm(unittest.TestCase):
    def setUp(self):
        self.appConfig = RSMap3DConfigParser()

    def tearDown(self):
        form = None
        form = S33SpecScanFileForm.createInstance(parent=None, appConfig=self.appConfig)
        self.assertIsNot(form, None)

    def testCreateForm(self):
        pass


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
