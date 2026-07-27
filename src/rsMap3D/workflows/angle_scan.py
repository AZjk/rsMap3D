"""
Copyright (c) 2017, UChicago Argonne, LLC
See LICENSE file.

Extracted from Scripts/mapSpecAngleScan_v4.2.py so it can be driven from
rsMap3D's CLI (`rsMap3D map-angle-scan config.json`) instead of being run
as a standalone, hand-edited script.

Fix note: the original assigned `dReader = detReader(detectorConfigName)`
*after* the `if roi is None:` block that calls `dReader.getDetectorById(...)`,
so any config with roi_setting=null raised NameError before ever reaching
the mapper. This extraction moves the dReader assignment above that block
so the auto-ROI-from-detector-config path actually works.
"""

import datetime
import logging
import os
import time
from pathlib import Path

from spec2nexus import spec

from rsMap3D.config.rsmap3dconfigparser import RSMap3DConfigParser
from rsMap3D.datasource.DetectorGeometryForXrayutilitiesReader import (
    DetectorGeometryForXrayutilitiesReader as detReader,
)
from rsMap3D.datasource.Sector33SpecDataSource import Sector33SpecDataSource
from rsMap3D.gui.rsm3dcommonstrings import BINARY_OUTPUT
from rsMap3D.mappers.gridmapper import QGridMapper
from rsMap3D.mappers.output.vtigridwriter import VTIGridWriter
from rsMap3D.transforms.unitytransform3d import UnityTransform3D
from rsMap3D.utils.srange import srange
from rsMap3D.workflows._common import configure_console_logging

logger = logging.getLogger(__name__)


def reindex_specfile(fullFilename):
    logger.info("=============================")
    logger.info("  Re-indexing the SPEC file...")
    spec_data = spec.SpecDataFile(fullFilename)
    scansInFile_list = spec_data.getScanNumbers()
    logger.info(f"  Done. The lastest scan # is {scansInFile_list[-1]}")
    return scansInFile_list, spec_data


def generateScanLists(inputScanList):
    num_cycles = inputScanList["cycles"]
    scans_in_1_cycle = inputScanList["scans_per_cycle"]
    SetsOfRSM = inputScanList["rsm_sets"]

    scanListTop = []
    for i in range(0, num_cycles):
        for oneSetRSM in SetsOfRSM:
            scan_s = oneSetRSM["start"]
            scan_e = oneSetRSM["end"]
            scans_in_1_rsm = scan_e - scan_s + 1
            scanListTop = scanListTop + (
                [
                    [f"{x}" if scans_in_1_rsm == 1 else f"{x}-{x + scans_in_1_rsm - 1}"]
                    for x in range(scan_s + i * scans_in_1_cycle, scan_e + i * scans_in_1_cycle + 1, scans_in_1_rsm)
                ]
            )
    return scanListTop


def _is_scan_done(specfile_full, curr_scan=1):
    """
    Poll EPICS PVs at 33-ID-D to check whether a scan has finished. Imports
    epics lazily so that config["real_time"]=False (the common case) does
    not require pyepics to be installed.
    """
    from epics import PV

    specfile_pv = PV("33idSIS:spec:SPECFileName")
    scann_pv = PV("33idSIS:spec:SCANNUM")
    scanDone_pv = PV("33idSIS:spec:ISSCANDONE")

    if (
        (not scann_pv.wait_for_connection(timeout=2))
        or (not scanDone_pv.wait_for_connection(timeout=2))
        or (not specfile_pv.wait_for_connection(timeout=2))
    ):
        return -1

    if specfile_full != specfile_pv.char_value:
        return 1
    if curr_scan < scann_pv.value:
        return 1
    elif curr_scan == scann_pv.value:
        if scanDone_pv.value == 1:
            return 1
        else:
            return 0
    else:
        return 0


def checkGridRange(gridRange, fullRange):
    if gridRange is None:
        tmp = fullRange
    elif len(gridRange) != 6:
        tmp = fullRange
    else:
        h_min = max(fullRange[0], min(gridRange[0], gridRange[1]))
        h_max = min(fullRange[1], max(gridRange[0], gridRange[1]))
        k_min = max(fullRange[2], min(gridRange[2], gridRange[3]))
        k_max = min(fullRange[3], max(gridRange[2], gridRange[3]))
        l_min = max(fullRange[4], min(gridRange[4], gridRange[5]))
        l_max = min(fullRange[5], max(gridRange[4], gridRange[5]))
        tmp = h_min, h_max, k_min, k_max, l_min, l_max
    return tmp


def _updateDataSourceProgress(value1, value2):
    logger.info(f"\t\tDataLoading Progress -- Current set: {value1:.3f}%/{value2}%")


def _updateMapperProgress(value1):
    logger.info(f"\t\tMapper Progress -- Current volume: {value1:.3f}%")


def run(config):
    """
    Grid one or more spec angle-scan datasets into reciprocal space maps.
    `config` has the same shape as the rsmconfig.json files consumed by
    the historical Scripts/mapSpecAngleScan_v4.2.py script.
    """
    configure_console_logging()

    startTime = datetime.datetime.now()
    with open("time.log", "a") as time_log:
        time_log.write(f"Start: {startTime}\n")

    projectDir = config["project_dir"]
    configDir = config["config_dir"]
    if configDir is None:
        configDir = projectDir

    detectorConfigName = os.path.join(configDir, config["detector_config"])
    instConfigName = os.path.join(configDir, config["instrument_config"])
    badPixelFile = os.path.join(configDir, config["badpixel_file"])
    flatfieldFile = config["flat_field"]

    detectorName = config["detector_name"]
    bin = config["binning"]
    roi = config["roi_setting"]
    nx = config["nx"]
    ny = config["ny"]
    nz = config["nz"]
    gridRange_input = config["grid_range"]
    mapHKL = config["use_HKL"]
    realtime_flag = config["real_time"]

    datasets = config["datasets"]

    if not os.path.exists(detectorConfigName):
        raise Exception(f"Detector Config file does not exist: {detectorConfigName}")
    if not os.path.exists(instConfigName):
        raise Exception(f"Instrument Config file does not exist: {instConfigName}")
    if not os.path.exists(badPixelFile):
        raise Exception(f"Bad Pixel file does not exist: {badPixelFile}")
    if flatfieldFile is not None:
        flatfieldFile = os.path.join(configDir, flatfieldFile)
        if not os.path.exists(flatfieldFile):
            raise Exception(f"Flat field file does not exist: {flatfieldFile}")

    dReader = detReader(detectorConfigName)

    if roi is None:
        detector = dReader.getDetectorById(detectorName)
        nPixels = dReader.getNpixels(detector)
        roi = [1, nPixels[0], 1, nPixels[1]]
    logger.info(f"ROI: {roi} ")

    for idx, dataset in enumerate(datasets, 1):
        specFile = dataset["spec_file"]
        scanListTop = dataset["scan_list"]

        if scanListTop is None:
            inputScanList = dataset["scan_range"]
            scanListTop = generateScanLists(inputScanList)

        specfile_full = os.path.join(projectDir, specFile)
        if not os.path.exists(specfile_full):
            print(f"File not found.  Please check the path and name {specFile} is correct.")
            print("Moving on...in a couple of seconds. ")
            time.sleep(2)
            continue

        specName, specExt = os.path.splitext(specFile)
        outputFilePath = os.path.join(projectDir, "analysis_runtime", specName)
        Path(outputFilePath).mkdir(parents=True, exist_ok=True)

        logger.info("=============================")
        logger.info(f"SPEC file #{idx}: {specfile_full}")
        logger.info(f"Generated Scan List #{idx}: {scanListTop}")

        scansInFile_list, spec_data = reindex_specfile(specfile_full)

        for scanList1 in scanListTop:
            outputFileName = os.path.join(outputFilePath, f"{specName}_{str(scanList1[0])}")

            if mapHKL:
                outputFileName += "_hkl.vti"
            else:
                outputFileName += "_Qxyz.vti"

            appConfig = RSMap3DConfigParser()

            scanRange = []
            for scans in scanList1:
                scanRange += srange(scans).list()
            logger.info("  --------------------------------")
            logger.info(f"scanRange {scanRange}")

            curr_scan = max(scanRange)
            _accu = 1
            last_len = 0
            while realtime_flag:
                _scanDone_flag = _is_scan_done(specfile_full, curr_scan)
                if _scanDone_flag == 1:
                    break
                elif _scanDone_flag == 0:
                    sleep_time = 5
                else:
                    if str(curr_scan) not in scansInFile_list:
                        sleep_time = _accu * 5
                        logger.info(
                            "  Scan #%d not available yet.  \
                            Wait %d seconds"
                            % (curr_scan, sleep_time)
                        )
                    elif scansInFile_list.index(str(curr_scan)) == (len(scansInFile_list) - 1):
                        scan = spec_data.getScan(curr_scan)
                        if len(scan.data) > 0:
                            curr_len = len(scan.data[scan.L[0]])
                        else:
                            curr_len = 0
                        logger.info("   Data points current in the scan #%d is %d" % (curr_scan, curr_len))
                        if curr_len == 0:
                            pass
                        elif curr_len != last_len:
                            last_len = curr_len
                        else:
                            if _accu > 4:
                                break
                        sleep_time = 5 * _accu
                        logger.info("  Scan #%d may not be finished.  Wait %d seconds..." % (curr_scan, sleep_time))
                    else:
                        logger.info("\t--------------------------------")
                        logger.info("  Scan #%d ready.\n" % curr_scan)
                        break
                    _accu += 1
                    scansInFile_list, spec_data = reindex_specfile(specfile_full)

                time.sleep(sleep_time)

            ds = Sector33SpecDataSource(
                projectDir,
                specName,
                specExt,
                instConfigName,
                detectorConfigName,
                roi=roi,
                pixelsToAverage=bin,
                scanList=scanRange,
                badPixelFile=badPixelFile,
                flatFieldFile=flatfieldFile,
                appConfig=appConfig,
            )
            ds.setCurrentDetector(detectorName)
            ds.setProgressUpdater(_updateDataSourceProgress)
            ds.loadSource(mapHKL=mapHKL)

            fullRange = ds.getOverallRanges()
            if gridRange_input is None:
                gridRange = fullRange
            else:
                gridRange = checkGridRange(gridRange_input, fullRange)

            ds.setRangeBounds(gridRange)

            logger.info("  --------------------------------")

            gridMapper = QGridMapper(
                ds,
                outputFileName,
                outputType=BINARY_OUTPUT,
                nx=nx,
                ny=ny,
                nz=nz,
                transform=UnityTransform3D(),
                gridWriter=VTIGridWriter(),
                appConfig=appConfig,
            )

            gridMapper.setProgressUpdater(_updateMapperProgress)
            gridMapper.doMap()

        with open("time.log", "a") as time_log:
            endTime = datetime.datetime.now()
            time_log.write(f"End: {endTime}\n")
            time_log.write(f"Diff: {endTime - startTime}\n")

        logger.info("  --------------------------------")
    logger.info("=============================")
