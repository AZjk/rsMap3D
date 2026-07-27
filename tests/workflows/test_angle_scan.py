"""
Copyright (c) 2026, UChicago Argonne, LLC
See LICENSE file.
"""

import importlib.resources
import os
import shutil

import pytest

from rsMap3D.workflows import angle_scan

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures")


class _FakeDataSource:
    instances = []

    def __init__(self, projectDir, projectName, projectExtension, instConfigFile, detConfigFile, **kwargs):
        self.projectDir = projectDir
        self.projectName = projectName
        self.projectExtension = projectExtension
        self.instConfigFile = instConfigFile
        self.detConfigFile = detConfigFile
        self.kwargs = kwargs
        self.currentDetector = None
        _FakeDataSource.instances.append(self)

    def setCurrentDetector(self, name):
        self.currentDetector = name

    def setProgressUpdater(self, updater):
        pass

    def loadSource(self, mapHKL=False):
        self.mapHKL = mapHKL

    def getOverallRanges(self):
        return (0, 1, 0, 1, 0, 1)

    def setRangeBounds(self, bounds):
        self.rangeBounds = bounds


class _FakeGridMapper:
    instances = []

    def __init__(self, dataSource, outputFileName, **kwargs):
        self.dataSource = dataSource
        self.outputFileName = outputFileName
        self.kwargs = kwargs
        _FakeGridMapper.instances.append(self)

    def setProgressUpdater(self, updater):
        pass

    def doMap(self):
        self.mapped = True


@pytest.fixture(autouse=True)
def _reset_fakes():
    _FakeDataSource.instances.clear()
    _FakeGridMapper.instances.clear()
    yield


@pytest.fixture
def config(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    shutil.copy(
        os.path.join(FIXTURES_DIR, "spec", "CB_140303A_1.spec"),
        project_dir / "CB_140303A_1.spec",
    )
    resources_dir = str(importlib.resources.files("rsMap3D") / "resources")
    return {
        "project_dir": str(project_dir),
        "config_dir": resources_dir,
        "detector_config": "33bmDetectorGeometry.xml",
        "instrument_config": "33BM-instForXrayutilities.xml",
        "badpixel_file": os.path.join(FIXTURES_DIR, "badpixels.txt"),
        "flat_field": None,
        "detector_name": "Pilatus",
        "binning": [1, 1],
        "roi_setting": [1, 487, 1, 195],
        "nx": 10,
        "ny": 11,
        "nz": 12,
        "grid_range": None,
        "use_HKL": False,
        "real_time": False,
        "datasets": [
            {"spec_file": "CB_140303A_1.spec", "scan_list": [["1"]]},
        ],
        "maxTime_1Scan": 60,
    }


def test_run_builds_datasource_and_mapper_from_config(monkeypatch, tmp_path, config):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(angle_scan, "Sector33SpecDataSource", _FakeDataSource)
    monkeypatch.setattr(angle_scan, "QGridMapper", _FakeGridMapper)

    angle_scan.run(config)

    assert len(_FakeDataSource.instances) == 1
    ds = _FakeDataSource.instances[0]
    assert ds.projectDir == config["project_dir"]
    assert ds.projectName == "CB_140303A_1"
    assert ds.currentDetector == "Pilatus"
    assert ds.kwargs["roi"] == [1, 487, 1, 195]
    assert ds.mapHKL is False

    assert len(_FakeGridMapper.instances) == 1
    mapper = _FakeGridMapper.instances[0]
    assert mapper.kwargs["nx"] == 10
    assert mapper.kwargs["ny"] == 11
    assert mapper.kwargs["nz"] == 12
    assert mapper.outputFileName.endswith("CB_140303A_1_1_Qxyz.vti")
    assert mapper.mapped is True
