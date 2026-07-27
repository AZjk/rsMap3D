"""
Copyright (c) 2017, UChicago Argonne, LLC
See LICENSE file.

Extracted from Scripts/powderscan_RSM3D_2.1.py so it can be driven from
rsMap3D's CLI (`rsMap3D powder-scan config.json`) instead of being run as
a standalone, hand-edited script. Originally written by Christian
Schleputz, modified by Zhan Zhang, APS, ANL.

Fix note: the original created `os.makedirs(specName)` (relative to the
current working directory) before writing output, but PowderScanWriter
actually opens its file at `project_dir/analysis_runtime/<specName>/...`
(built from output_filename_fmt) and does not create any directories
itself -- the original would raise FileNotFoundError the first time it
ran against a project directory that didn't already happen to have that
nested folder. This extraction creates the real output file's parent
directory instead.

Fix note: the original also assigned `dReader = detReader(detectorConfigName)`
*after* the `if roi is None:` block that calls `dReader.getDetectorById(...)`,
so any config with roi_setting=null raised NameError before ever reaching
the mapper. This extraction moves the dReader assignment above that block,
the same fix already applied to the sibling rsMap3D.workflows.angle_scan
(Task 8) and rsMap3D.workflows.parametric_scan (Task 9) modules, so the
auto-ROI-from-detector-config path actually works.
"""

import logging
import os
import time
from itertools import zip_longest

import numpy as np

from rsMap3D.config.rsmap3dconfigparser import RSMap3DConfigParser
from rsMap3D.datasource.DetectorGeometryForXrayutilitiesReader import (
    DetectorGeometryForXrayutilitiesReader as detReader,
)
from rsMap3D.datasource.Sector33SpecDataSource import Sector33SpecDataSource
from rsMap3D.mappers.output.powderscanwriter import PowderScanWriter
from rsMap3D.mappers.powderscanmapper import PowderScanMapper
from rsMap3D.transforms.unitytransform3d import UnityTransform3D
from rsMap3D.utils.srange import srange
from rsMap3D.workflows._common import configure_console_logging

logger = logging.getLogger(__name__)


def _updateDataSourceProgress(value1, value2):
    logger.info(f"\t\tDataLoading Progress {value1:.3f}%/{value2}%")


def _updateMapperProgress(value1):
    logger.info(f"\t\tMapper Progress -- Current Curve {value1:.3f}%")


def _normalizeScanList(scan_list):
    if not isinstance(scan_list, list):
        if isinstance(scan_list, (int, float)):
            scan_list = [int(scan_list)]
        elif isinstance(scan_list, str):
            scan_list = srange(scan_list).list()
        elif isinstance(scan_list, range):
            scan_list = list(scan_list)
    return scan_list


def run(config):
    """
    Reduce one or more spec scans per dataset into 1D powder-diffraction
    curves (.xye files), one curve per scan (or per combined scan-range).
    """
    configure_console_logging()

    projectDir = config["project_dir"]
    configDir = config["config_dir"]
    detectorName = config["detector_name"]
    bin = config["binning"]
    roi = config["roi_setting"]
    data_coordinate = config["data_coordinate"]
    x_min_0 = config["x_min"]
    x_max_0 = config["x_max"]
    x_step = config["x_step"]
    do_plot = config["do_plot"]
    plot_y = config["plot_y"]
    write_file = config["write_file"]
    output_filename_fmt = os.path.join(projectDir, config["output_filename_fmt"])

    instConfigName = os.path.join(configDir, config["instrument_config"])
    detectorConfigName = os.path.join(configDir, config["detector_config"])
    badPixelFile = config["badpixel_file"]
    if badPixelFile is not None:
        badPixelFile = os.path.join(configDir, badPixelFile)
    flatfieldFile = config["flat_field"]
    if flatfieldFile is not None:
        flatfieldFile = os.path.join(configDir, flatfieldFile)

    if not os.path.exists(detectorConfigName):
        raise Exception(f"Detector Config file does not exist: {detectorConfigName}")
    if not os.path.exists(instConfigName):
        raise Exception(f"Instrument Config file does not exist: {instConfigName}")
    if badPixelFile is not None and not os.path.exists(badPixelFile):
        raise Exception(f"Bad Pixel file does not exist: {badPixelFile}")
    if flatfieldFile is not None and not os.path.exists(flatfieldFile):
        raise Exception(f"Flat field file does not exist: {flatfieldFile}")

    dReader = detReader(detectorConfigName)
    if roi is None:
        detector = dReader.getDetectorById(detectorName)
        nPixels = dReader.getNpixels(detector)
        roi = [1, nPixels[0], 1, nPixels[1]]
    logger.info(f"  ROI: {roi} ")

    datasets = config["datasets"]
    specFileList = [dataset["spec_file"] for dataset in datasets]
    scanLists = [dataset["scan_list"] for dataset in datasets]
    slicesNotUsedLists = [dataset.get("slices_not_used", []) for dataset in datasets]

    for specfile, scan_list, slicesNotUsed_list in zip_longest(specFileList, scanLists, slicesNotUsedLists):
        specName, specExt = os.path.splitext(specfile)
        logger.info("=============================")
        logger.info(f"  Starting SPEC file : {specfile}")
        logger.info(f"    Scans            : {scan_list}")

        scan_list = _normalizeScanList(scan_list)

        slicesNotUsed_scanN = []
        slicesNotUsed_sliceN = []
        for slicesNotUsed_oneset in slicesNotUsed_list:
            scan_num = srange(slicesNotUsed_oneset[0]).list()
            slice_nums = srange(slicesNotUsed_oneset[1]).list()
            if slice_nums:
                slicesNotUsed_scanN.extend(scan_num)
                slicesNotUsed_sliceN.append(slice_nums * len(scan_num))

        num_curves = len(scan_list)
        progress = 0
        for scans in scan_list:
            logger.info("  --------------------------------")
            logger.info(f"      Reading scans # {str(scans)}")

            scans = _normalizeScanList(scans)
            fileNameMarker = scans[0]

            outputFileName = output_filename_fmt % (specName, specName, fileNameMarker)
            os.makedirs(os.path.dirname(outputFileName), exist_ok=True)

            x_min = x_min_0
            x_max = x_max_0

            _start_time = time.time()

            appConfig = RSMap3DConfigParser()
            ds = Sector33SpecDataSource(
                projectDir,
                specName,
                specExt,
                instConfigName,
                detectorConfigName,
                roi=roi,
                pixelsToAverage=bin,
                scanList=scans,
                badPixelFile=badPixelFile,
                flatFieldFile=flatfieldFile,
                appConfig=appConfig,
            )
            ds.setCurrentDetector(detectorName)
            ds.setProgressUpdater(_updateDataSourceProgress)
            ds.loadSource()
            ds.setRangeBounds(ds.getOverallRanges())
            logger.info("  --------------------------------")

            for onescan in scans:
                if onescan in slicesNotUsed_scanN:
                    myindex = slicesNotUsed_scanN.index(onescan)
                    slice_list = slicesNotUsed_sliceN[myindex]
                    logger.info(f"      Points #{str(slice_list)} in scan #{str(onescan)} ignored.  ")
                    my_len = len(ds.imageToBeUsed[onescan])
                    for slice_ in slice_list:
                        if slice_ in range(-my_len, my_len):
                            ds.imageToBeUsed[onescan][slice_] = False
                else:
                    logger.info("       No slice removed. ")
            logger.info("  --------------------------------")

            powderMapper = PowderScanMapper(
                ds,
                outputFileName,
                transform=UnityTransform3D(),
                gridWriter=PowderScanWriter(),
                appConfig=appConfig,
                dataCoord=data_coordinate,
                xCoordMin=x_min,
                xCoordMax=x_max,
                xCoordStep=x_step,
                plotResults=do_plot,
                yScaling=plot_y,
                writeXyeFile=write_file,
            )

            powderMapper.setProgressUpdater(_updateMapperProgress)
            powderMapper.doMap()

            x_min_output = powderMapper.getXCoordMin()
            x_max_output = powderMapper.getXCoordMax()
            nbins = np.round((x_max_output - x_min_output) / x_step)
            logger.info(f"  \t {data_coordinate} minimum : {x_min_output:.3f}")
            logger.info(f"  \t {data_coordinate} maximum : {x_max_output:.3f}")
            logger.info(f"  \t {data_coordinate} stepsize: {x_step:.3f}")
            logger.info(f"  \t {data_coordinate} nbins   : {nbins:.3f}")

            progress += 100.0 / num_curves
            logger.info("  Elapsed time for current curve: %.3f seconds" % (time.time() - _start_time))
            logger.info(f"  Mapper Progress -- Current File : {progress:.1f}%")
            if write_file:
                logger.info(f"  Output filename : {outputFileName}")
            else:
                logger.info(f"  Output file {outputFileName} disabled. ")
        logger.info("  --------------------------------")
    logger.info("=============================")
