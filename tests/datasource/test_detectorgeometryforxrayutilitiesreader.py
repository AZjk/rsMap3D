'''
Created on Apr 24, 2014

@author: hammonds
'''
import unittest
from rsMap3D.datasource.DetectorGeometryForXrayutilitiesReader import DetectorGeometryForXrayutilitiesReader
from rsMap3D.exception.rsmap3dexception import DetectorConfigException
import os
import logging
import logging.config
from rsMap3D.config.rsmap3dlogging import LOGGER_NAME

import importlib.resources

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
configDir = os.path.join(THIS_DIR, '../fixtures/config')
logConfigFile = os.path.join(configDir, LOGGER_NAME + 'Log.test.config')
print(logConfigFile)
logging.config.fileConfig(logConfigFile)
logger = logging.getLogger(LOGGER_NAME)



BAD_FILE_DIR = os.path.join(THIS_DIR, '../fixtures/problemFilesForTesting/')
BAD_FILE_NO_DETECTOR_LIST = BAD_FILE_DIR + 'detectorGeometryNoDetectorList.xml'
BAD_FILE_NO_DETECTOR = BAD_FILE_DIR + 'detectorGeometryNoDetector.xml'
DETECTOR_NAME = 'Pilatus'
GOOD_FILE_NAME = str(importlib.resources.files('rsMap3D') / 'resources' / '33bmDetectorGeometry.xml')


class Test(unittest.TestCase):
    

    def testGetCenterChannelPixel(self):
        config = DetectorGeometryForXrayutilitiesReader( \
                     GOOD_FILE_NAME)
        detector = config.getDetectorById("Pilatus")
        centerPix = config.getCenterChannelPixel(detector)
        pix = [210, 85]
        self.assertEqual(centerPix, pix, "getCenterChannelPixel " + 
                         str(centerPix) + " vs " + str(pix))

    def testGetDetectors(self):
        config = DetectorGeometryForXrayutilitiesReader( \
                     GOOD_FILE_NAME)
        detectors = config.getDetectors()
        self.assertNotEqual(detectors, None, "getDetector")
            
    def testGetDetectorsNoDetectors(self):
        config = DetectorGeometryForXrayutilitiesReader( \
                     BAD_FILE_NO_DETECTOR_LIST)
        self.assertRaises(DetectorConfigException, config.getDetectors)
        
    def testGetDetectorsById(self):
        config = DetectorGeometryForXrayutilitiesReader( \
                     GOOD_FILE_NAME)
        detector = config.getDetectorById(DETECTOR_NAME)
        self.assertNotEqual(detector, None, "getDetectorById")

    def testGetDetectorByIdNoDetectorList(self):
        config = DetectorGeometryForXrayutilitiesReader( \
                     BAD_FILE_NO_DETECTOR_LIST)
        self.assertRaises(DetectorConfigException, \
                          config.getDetectorById, \
                          DETECTOR_NAME)
        
    def testGetDetectorByIdNoDetector(self):
        config = DetectorGeometryForXrayutilitiesReader( \
                     BAD_FILE_NO_DETECTOR)
        self.assertRaises(DetectorConfigException, \
                          config.getDetectorById, \
                          DETECTOR_NAME)
        
        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()