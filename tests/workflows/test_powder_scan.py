'''
 Copyright (c) 2026, UChicago Argonne, LLC
 See LICENSE file.
'''
import importlib.resources
import os

import pytest

from rsMap3D.workflows import powder_scan


class _FakeDataSource:
    instances = []

    def __init__(self, projectDir, projectName, projectExtension,
                 instConfigFile, detConfigFile, **kwargs):
        self.kwargs = kwargs
        self.imageToBeUsed = {1: [True, True, True]}
        _FakeDataSource.instances.append(self)

    def setCurrentDetector(self, name):
        self.currentDetector = name

    def setProgressUpdater(self, updater):
        pass

    def loadSource(self):
        pass

    def getOverallRanges(self):
        return (0, 1, 0, 1, 0, 1)

    def setRangeBounds(self, bounds):
        pass


class _FakePowderMapper:
    instances = []

    def __init__(self, dataSource, outputFileName, **kwargs):
        self.dataSource = dataSource
        self.outputFileName = outputFileName
        self.kwargs = kwargs
        _FakePowderMapper.instances.append(self)

    def setProgressUpdater(self, updater):
        pass

    def doMap(self):
        pass

    def getXCoordMin(self):
        return self.kwargs["xCoordMin"]

    def getXCoordMax(self):
        return self.kwargs["xCoordMax"]


@pytest.fixture(autouse=True)
def _reset_fakes():
    _FakeDataSource.instances.clear()
    _FakePowderMapper.instances.clear()
    yield


@pytest.fixture
def config(tmp_path):
    resources_dir = str(importlib.resources.files("rsMap3D") / "resources")
    return {
        "project_dir": str(tmp_path),
        "config_dir": resources_dir,
        "instrument_config": "33BM-instForXrayutilities.xml",
        "detector_config": "33bmDetectorGeometry.xml",
        "badpixel_file": None,
        "flat_field": None,
        "detector_name": "Pilatus",
        "binning": [1, 1],
        "roi_setting": [1, 487, 1, 195],
        "data_coordinate": "tth",
        "x_min": 15, "x_max": 75, "x_step": 0.05,
        "do_plot": False,
        "plot_y": "Linear",
        "write_file": True,
        "output_filename_fmt": "analysis_runtime/%s/%s_S%03d.xye",
        "datasets": [
            {"spec_file": "CB_140303A_1.spec", "scan_list": ["1"], "slices_not_used": []},
        ],
    }


def test_run_builds_datasource_and_powdermapper_and_creates_output_dir(monkeypatch, tmp_path, config):
    monkeypatch.setattr(powder_scan, "Sector33SpecDataSource", _FakeDataSource)
    monkeypatch.setattr(powder_scan, "PowderScanMapper", _FakePowderMapper)

    powder_scan.run(config)

    assert len(_FakeDataSource.instances) == 1
    ds = _FakeDataSource.instances[0]
    assert ds.currentDetector == "Pilatus"
    assert ds.kwargs["roi"] == [1, 487, 1, 195]

    assert len(_FakePowderMapper.instances) == 1
    mapper = _FakePowderMapper.instances[0]
    assert mapper.kwargs["dataCoord"] == "tth"
    assert mapper.kwargs["xCoordMin"] == 15
    assert mapper.kwargs["xCoordMax"] == 75
    expected_output = os.path.join(
        str(tmp_path), "analysis_runtime", "CB_140303A_1", "CB_140303A_1_S001.xye")
    assert mapper.outputFileName == expected_output
    # the fix under test: the *actual* output directory must exist, not a
    # same-named directory relative to the current working directory.
    assert os.path.isdir(os.path.dirname(expected_output))
