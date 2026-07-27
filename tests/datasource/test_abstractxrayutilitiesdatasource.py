"""
Copyright (c) 2012, UChicago Argonne, LLC
See LICENSE file.
"""

import unittest

from rsMap3D.config.rsmap3dconfigparser import RSMap3DConfigParser
from rsMap3D.datasource.AbstractXrayUtilitiesDataSource import AbstractXrayutilitiesDataSource


class Test(unittest.TestCase):
    def setUp(self):
        appConfig = RSMap3DConfigParser()
        self.dataSource = TestDataSource(appConfig=appConfig)

    def tearDown(self):
        pass

    def testGetMonitorName(self):
        monitorName = self.dataSource.getMonitorName()
        self.assertEqual(monitorName, None, "getMonitorName")

    def testGetMonitorScaleFactor(self):
        scaleFactor = self.dataSource.getMonitorScaleFactor()
        self.assertEqual(scaleFactor, 1, "getMonitorScaleFactor")

    def testGetFilterName(self):
        filterName = self.dataSource.getFilterName()
        self.assertEqual(filterName, None, "getFilterName")

    def testGetFilterScaleFactor(self):
        scaleFactor = self.dataSource.getFilterScaleFactor()
        self.assertEqual(scaleFactor, 1, "getFilterScaleFactor")


class TestDataSource(AbstractXrayutilitiesDataSource):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def loadSource(self):
        return

    def getImage(self):
        return

    def getReferenceNames(self):
        return AbstractXrayutilitiesDataSource.getReferenceNames(self)

    def getReferenceValues(self):
        return AbstractXrayutilitiesDataSource.getReferenceValues(self)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
