'''
 Copyright (c) 2017, UChicago Argonne, LLC
 See LICENSE file.

 Extracted from Scripts/mapSpecParametricScan.py so it can be driven from
 rsMap3D's CLI (`rsMap3D map-parametric-scan config.json`) instead of being
 run as a standalone, hand-edited script.

 The original script never ran successfully under any Python version:
   - It used Python 2 `print` statements (a SyntaxError under Python 3),
     replaced here with logger calls.
   - `tmpImageUsed` and `savImageUsed` were assigned from the same list
     object (`imageToBeUsed[scanRange[0]]`), so "restoring" the per-line
     image mask after doMap() was a no-op; fixed here with explicit
     copies.
   - The per-image loop ran `range(1, len(imageToBeUsed[...])+1)` and used
     the loop variable directly as a 0-based list index, guaranteeing an
     IndexError on its last (and, for a single-image scan, only)
     iteration; fixed here by looping 0-based over the mask while keeping
     1-based numbering in filenames/log messages, matching the evident
     intent of the original `_N%d.vti` naming.

 This extraction also preserves the original's `roi_setting: null` ->
 auto-detect-ROI-from-detector-config fallback (via
 DetectorGeometryForXrayutilitiesReader), the same pattern already used by
 the sibling rsMap3D.workflows.angle_scan module for Task 8: `dReader` is
 built before the `if roi is None:` check so that path actually works.
'''
import logging
import os

from rsMap3D.config.rsmap3dconfigparser import RSMap3DConfigParser
from rsMap3D.datasource.DetectorGeometryForXrayutilitiesReader import \
    DetectorGeometryForXrayutilitiesReader as detReader
from rsMap3D.datasource.Sector33SpecDataSource import Sector33SpecDataSource
from rsMap3D.gui.rsm3dcommonstrings import BINARY_OUTPUT
from rsMap3D.mappers.gridmapper import QGridMapper
from rsMap3D.mappers.output.vtigridwriter import VTIGridWriter
from rsMap3D.transforms.unitytransform3d import UnityTransform3D
from rsMap3D.utils.srange import srange

logger = logging.getLogger(__name__)


def _updateDataSourceProgress(value1, value2):
    logger.info("DataSource Progress %s/%s" % (value1, value2))


def _updateMapperProgress(value1):
    logger.info("Mapper Progress %s" % (value1))


def run(config):
    '''
    Grid a parametric scan: each image within the scan represents a
    different sample-environment condition with all angles held constant,
    so one output file is produced per image in the scan.
    '''
    projectDir = config["project_dir"]
    configDir = config["config_dir"]
    specFile = config["spec_file"]
    scanList1 = config["scan_list"]
    mapHKL = config["use_HKL"]
    detectorConfigName = os.path.join(configDir, config["detector_config"])
    instConfigName = os.path.join(configDir, config["instrument_config"])
    detectorName = config["detector_name"]
    bin = config["binning"]
    roi = config["roi_setting"]
    nx = config["nx"]
    ny = config["ny"]
    nz = config["nz"]

    if not os.path.exists(detectorConfigName):
        raise Exception("Detector Config file does not exist: %s" %
                        detectorConfigName)
    if not os.path.exists(instConfigName):
        raise Exception("Instrument Config file does not exist: %s" %
                        instConfigName)

    dReader = detReader(detectorConfigName)

    if roi is None:
        detector = dReader.getDetectorById(detectorName)
        nPixels = dReader.getNpixels(detector)
        roi = [1, nPixels[0], 1, nPixels[1]]
    logger.info("ROI: %s " % roi)

    specName, specExt = os.path.splitext(specFile)
    appConfig = RSMap3DConfigParser()

    for scans in scanList1:
        scanRange = srange(scans).list()
        logger.info("scanRange %s" % scanRange)
        logger.info("specName, specExt: %s, %s" % (specName, specExt))
        ds = Sector33SpecDataSource(projectDir, specName, specExt,
                                    instConfigName, detectorConfigName, roi=roi,
                                    pixelsToAverage=bin, scanList=scanRange,
                                    appConfig=appConfig)
        ds.setCurrentDetector(detectorName)
        ds.setProgressUpdater(_updateDataSourceProgress)
        ds.loadSource(mapHKL=mapHKL)
        ds.setRangeBounds(ds.getOverallRanges())
        imageToBeUsed = ds.getImageToBeUsed()
        logger.info("imageToBeUsed %s" % imageToBeUsed)

        numImages = len(imageToBeUsed[scanRange[0]])
        for zeroBasedIndex in range(numImages):
            imageInScan = zeroBasedIndex + 1
            logger.info("Scan Line %d" % imageInScan)

            outputFileName = os.path.join(projectDir, specName +
                                          ('_N%d.vti' % imageInScan))
            gridWriter = VTIGridWriter()

            savedImageUsed = list(imageToBeUsed[scanRange[0]])
            tmpImageUsed = list(savedImageUsed)
            tmpImageUsed[zeroBasedIndex] = False
            ds.imageToBeUsed[scanRange[0]] = [not used for used in tmpImageUsed]

            gridMapper = QGridMapper(ds,
                                     outputFileName,
                                     outputType=BINARY_OUTPUT,
                                     transform=UnityTransform3D(),
                                     gridWriter=gridWriter,
                                     appConfig=appConfig,
                                     nx=nx, ny=ny, nz=nz)

            gridMapper.setProgressUpdater(_updateMapperProgress)
            gridMapper.doMap()
            ds.imageToBeUsed[scanRange[0]] = savedImageUsed
