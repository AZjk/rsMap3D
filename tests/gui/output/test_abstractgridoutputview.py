"""
Copyright (c) 2017 UChicago Argonne, LLC
See LICENSE file.
"""

import sys
import unittest

import PySide6.QtWidgets as qtWidgets

from rsMap3D.config.rsmap3dconfigparser import RSMap3DConfigParser
from rsMap3D.gui.output.abstractgridoutputform import INITIAL_DIM as INITIAL_DIM
from rsMap3D.gui.output.abstractgridoutputform import AbstractGridOutputForm as AGOutForm

app = qtWidgets.QApplication.instance() or qtWidgets.QApplication(sys.argv)

ZERO_INT = 0


class TestAbstractGridOutputView(unittest.TestCase):
    def setUp(self):
        self.appConfig = RSMap3DConfigParser()
        self.form = TestGridFileForm(parent=None, appConfig=self.appConfig)

    def test_defaults(self):
        self.assertEqual(self.form.runButton.isEnabled(), True)
        self.assertEqual(self.form.cancelButton.isEnabled(), False)
        self.assertEqual(self.form.progressBar.value(), ZERO_INT)
        self.assertEqual(self.form.progressBar.minimum(), ZERO_INT)
        self.assertEqual(self.form.progressBar.value(), ZERO_INT)
        self.assertEqual(int(self.form.xDimTxt.text()), INITIAL_DIM)
        self.assertEqual(int(self.form.yDimTxt.text()), INITIAL_DIM)
        self.assertEqual(int(self.form.zDimTxt.text()), INITIAL_DIM)

    def test_setCancelOK(self):
        self.form.setCancelOK()
        self.assertEqual(self.form.runButton.isEnabled(), False)
        self.assertEqual(self.form.cancelButton.isEnabled(), True)
        self.assertEqual(self.form.dataBox.isEnabled(), False)

    def test_setRunOK(self):
        self.form.setRunOK()
        self.assertEqual(self.form.runButton.isEnabled(), True)
        self.assertEqual(self.form.cancelButton.isEnabled(), False)
        self.assertEqual(self.form.dataBox.isEnabled(), True)
        self.form.setRunOK()

    def test_setDimensionsRunOK(self):
        VALUE_STR = "500"
        BAD_VALUE_STR = "5kX"
        self.form.setRunOK()
        self.form.xDimTxt.setText(VALUE_STR)
        self.assertEqual(self.form.xDimTxt.text(), VALUE_STR)
        self.form.xDimTxt.setText(BAD_VALUE_STR)


class TestGridFileForm(AGOutForm):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = qtWidgets.QVBoxLayout()
        self.dataBox = self._createDataBox()
        controlBox = self._createControlBox()

        layout.addWidget(self.dataBox)
        layout.addWidget(controlBox)
        self.setLayout(layout)


if __name__ == "__main__":
    unittest.main()
