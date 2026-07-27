"""
Copyright (c) 2026, UChicago Argonne, LLC
See LICENSE file.
"""

import importlib.resources
import os

import pytest

from rsMap3D.workflows import parametric_scan


class _FakeDataSource:
    instances = []

    def __init__(self, projectDir, projectName, projectExtension, instConfigFile, detConfigFile, **kwargs):
        self.kwargs = kwargs
        self.imageToBeUsed = {1: [True, True, True]}
        _FakeDataSource.instances.append(self)

    def setCurrentDetector(self, name):
        self.currentDetector = name

    def setProgressUpdater(self, updater):
        pass

    def loadSource(self, mapHKL=False):
        pass

    def getOverallRanges(self):
        return (0, 1, 0, 1, 0, 1)

    def setRangeBounds(self, bounds):
        pass

    def getImageToBeUsed(self):
        return self.imageToBeUsed


class _FakeGridMapper:
    instances = []

    def __init__(self, dataSource, outputFileName, **kwargs):
        self.dataSource = dataSource
        self.outputFileName = outputFileName
        self.maskSnapshot = list(dataSource.imageToBeUsed[1])
        _FakeGridMapper.instances.append(self)

    def setProgressUpdater(self, updater):
        pass

    def doMap(self):
        pass


@pytest.fixture(autouse=True)
def _reset_fakes():
    _FakeDataSource.instances.clear()
    _FakeGridMapper.instances.clear()
    yield


@pytest.fixture
def config():
    resources_dir = str(importlib.resources.files("rsMap3D") / "resources")
    return {
        "project_dir": "/tmp/does-not-need-to-exist",
        "config_dir": resources_dir,
        "spec_file": "CB_140303A_1.spec",
        "scan_list": ["1"],
        "use_HKL": False,
        "detector_config": "33bmDetectorGeometry.xml",
        "instrument_config": "33BM-instForXrayutilities.xml",
        "detector_name": "Pilatus",
        "binning": [1, 1],
        "roi_setting": [1, 487, 1, 195],
        "nx": 300,
        "ny": 300,
        "nz": 10,
    }


def test_run_masks_one_image_per_line_and_restores_mask(monkeypatch, config):
    monkeypatch.setattr(parametric_scan, "Sector33SpecDataSource", _FakeDataSource)
    monkeypatch.setattr(parametric_scan, "QGridMapper", _FakeGridMapper)

    parametric_scan.run(config)

    ds = _FakeDataSource.instances[0]
    # 3 fake images -> one grid map per image, 0-indexed internally
    assert len(_FakeGridMapper.instances) == 3
    for mapper in _FakeGridMapper.instances:
        # exactly one image is isolated (mask=True) per pass; the rest are excluded
        assert mapper.maskSnapshot.count(True) == 1
    # the mask must be restored to the original after every line runs
    assert ds.imageToBeUsed[1] == [True, True, True]


def test_run_names_output_files_1_indexed(monkeypatch, config):
    monkeypatch.setattr(parametric_scan, "Sector33SpecDataSource", _FakeDataSource)
    monkeypatch.setattr(parametric_scan, "QGridMapper", _FakeGridMapper)

    parametric_scan.run(config)

    names = sorted(m.outputFileName for m in _FakeGridMapper.instances)
    assert names == [
        os.path.join(config["project_dir"], "CB_140303A_1_N1.vti"),
        os.path.join(config["project_dir"], "CB_140303A_1_N2.vti"),
        os.path.join(config["project_dir"], "CB_140303A_1_N3.vti"),
    ]
